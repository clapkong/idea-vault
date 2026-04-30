# AI 파이프라인 비동기 실행 레이어
#
# 역할:
#   POST /generate 요청이 오면 즉시 job_id를 반환하고, orchestrator는 백그라운드에서 실행.
#   실행 중 발생하는 SSE 이벤트를 asyncio.Queue에 넣어 /stream 엔드포인트로 흘려줌.
#   완료/실패/중단 시 result.json, prd.md, meta.json을 data/jobs/{job_id}/ 에 저장.
#
# 사용처:
#   routers/generate.py — run_pipeline 호출, job_queues/running_jobs 등록
#   routers/stream.py   — job_queues 조회 (SSE 연결)
#   routers/jobs.py     — running_jobs 조회 (stop 요청 시 task 취소)
#
# 주의: job_queues/running_jobs는 메모리 딕셔너리이므로 프로세스 재시작 시 초기화됨.
#       실행 중 재시작하면 해당 job의 /stream 연결이 끊김.
import asyncio
import json
import logging
from pathlib import Path

from services.storage import DATA_DIR, write_meta

# asyncio.Queue: 생산자(orchestrator)와 소비자(/stream)를 잇는 비동기 채널.
# orchestrator가 이벤트를 put() → /stream이 get()해서 SSE로 전송.
job_queues: dict[str, asyncio.Queue] = {}

# asyncio.Task: 백그라운드로 돌고 있는 파이프라인 핸들.
# task.cancel()을 호출하면 실행 중인 await 지점에서 CancelledError가 발생해 파이프라인을 중단시킴.
running_jobs: dict[str, asyncio.Task] = {}

def compute_tokens(events: list) -> int:
    """agent_done 이벤트에서 총 토큰 수 집계."""
    total = 0
    for event in events:
        if event.get("type") != "agent_done":
            continue
        t = event.get("tokens", 0)
        total += t.get("total", 0) if isinstance(t, dict) else t
    return total


def _make_run_logger(log_path: Path) -> logging.Logger:
    """run.log 전용 파일 로거 생성 — %(message)s 포맷으로 prefix 없이 블록만 기록."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # 로거 이름에 경로를 포함해 job마다 독립적인 인스턴스 생성
    logger = logging.getLogger(f"run_log.{log_path}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


async def run_pipeline(job_id: str, user_input: str, queue: asyncio.Queue) -> None:
    """orchestrator를 백그라운드에서 실행하고 결과를 data/jobs/{job_id}/ 에 저장.

    흐름:
      1. run.log 로거 주입 → orchestrator.run() 호출 → 내부에서 queue에 SSE 이벤트 emit
      2. 완료 시 result.json 저장 후 meta.json 갱신
      3. CancelledError (stop 요청) → meta status = 'stopped'
      4. 기타 예외 → meta status = 'failed'
      5. finally 블록에서 반드시 {'type': 'done'} 큐에 삽입 → /stream 연결 정상 종료 보장
    """
    # 함수 안에서 import하는 이유: orchestrator는 무겁고 mock 모드에서는 아예 불필요.
    # 모듈 상단에 두면 앱 시작 시 항상 로드되므로 필요한 시점에만 import.
    from agents.llm import set_block_logger, set_token_logger
    from agents.orchestrator import run as orchestrator_run

    job_dir = DATA_DIR / job_id
    start_time = asyncio.get_event_loop().time()

    run_logger = _make_run_logger(job_dir / "run.log")
    set_block_logger(run_logger)
    set_token_logger(run_logger)

    _final_status = "failed"

    try:
        # asyncio.wait_for: timeout 초 안에 완료되지 않으면 자동으로 CancelledError 발생.
        result = await asyncio.wait_for(
            orchestrator_run(user_input, job_id=job_id, event_queue=queue),
            timeout=1800,  # 최대 30분
        )
        duration = round(asyncio.get_event_loop().time() - start_time, 1)

        # prd + loop_history + events를 단일 result.json으로 통합 저장
        (job_dir / "result.json").write_text(
            json.dumps(
                {
                    "prd": result["prd"],
                    "loop_history": result["loop_history"],
                    "events": result["events"],
                    "duration_sec": duration,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        # 최종 산출물 — 사람이 직접 읽을 수 있는 마크다운 형태로 별도 보존
        (job_dir / "prd.md").write_text(result["prd"], encoding="utf-8")

        total_tokens = compute_tokens(result.get("events", []))

        meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
        meta.update({
            "status": "done",
            "duration_sec": duration,
            "tokens": total_tokens,
        })
        write_meta(job_id, meta)
        _final_status = "done"

    except asyncio.CancelledError:
        # /jobs/{id}/stop 에서 task.cancel() 호출 시 진입
        meta_path = job_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["status"] = "stopped"
            write_meta(job_id, meta)
        _final_status = "stopped"
        raise  # CancelledError를 삼키면 asyncio가 태스크가 취소됐는지 알 수 없어서 반드시 재전파해야 함

    except Exception as e:
        logging.exception("[pipeline] job=%s failed", job_id)
        meta_path = job_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.update({"status": "failed", "error": str(e)})
            write_meta(job_id, meta)

    finally:
        set_block_logger(None)
        set_token_logger(None)
        running_jobs.pop(job_id, None)
        # status 포함 — 프런트가 성공/실패/중단을 구분할 수 있도록
        await queue.put({"type": "done", "job_id": job_id, "status": _final_status})
        job_queues.pop(job_id, None)
