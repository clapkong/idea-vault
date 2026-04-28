# 백그라운드 파이프라인 실행 레이어
# job별 asyncio.Queue(이벤트 스트림)와 asyncio.Task(실행 핸들)를 메모리에서 관리
# 프로세스 재시작 시 두 딕셔너리는 초기화되므로 진행 중 재시작 → stream 연결 불가
import asyncio
import json
import logging
from pathlib import Path

from services.storage import DATA_DIR, write_meta

# job_id → asyncio.Queue: orchestrator가 emit한 SSE 이벤트를 /stream 엔드포인트로 전달
job_queues: dict[str, asyncio.Queue] = {}
# job_id → asyncio.Task: /jobs/{id}/stop 에서 task.cancel()로 파이프라인 중단
running_jobs: dict[str, asyncio.Task] = {}

# per-agent 토큰 비용 — prompt/completion 분리 없이 blended rate 적용
# 30% prompt / 70% completion 가정: haiku ≈ $0.95/1M, sonnet ≈ $11.4/1M
_BLENDED_RATE = {
    "haiku":  0.95,
    "sonnet": 11.4,
}


def compute_cost(events: list) -> tuple[int, float]:
    """agent_done 이벤트에서 모델별 토큰을 읽어 총 토큰 수와 비용($)을 계산."""
    total_tokens = 0
    total_cost = 0.0
    for event in events:
        if event.get("type") != "agent_done":
            continue
        t = event.get("tokens", 0)
        # tokens 필드 구버전: 정수, 신버전: {input, output, total} 딕셔너리
        token_total = t.get("total", 0) if isinstance(t, dict) else t
        # researcher는 LLM 없이 Tavily 검색만 하므로 model 필드가 None — .lower() 오류 방지
        model = event.get("model") or ""
        total_tokens += token_total
        key = "haiku" if "haiku" in model.lower() else "sonnet"
        total_cost += token_total * _BLENDED_RATE[key] / 1_000_000
    return total_tokens, round(total_cost, 6)


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
    from agents.llm import set_block_logger, set_token_logger
    from agents.orchestrator import run as orchestrator_run

    job_dir = DATA_DIR / job_id
    start_time = asyncio.get_event_loop().time()

    run_logger = _make_run_logger(job_dir / "run.log")
    set_block_logger(run_logger)
    set_token_logger(run_logger)

    _final_status = "failed"

    try:
        # 최대 30분 제한 — 무한 루프 방지
        result = await asyncio.wait_for(
            orchestrator_run(user_input, job_id=job_id, event_queue=queue),
            timeout=1800,
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

        total_tokens, total_cost = compute_cost(result.get("events", []))

        meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
        meta.update({
            "status": "done",
            "duration_sec": duration,
            "tokens": total_tokens,
            "cost": total_cost,
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
        raise  # CancelledError는 반드시 재전파해야 asyncio가 태스크를 정상 취소로 인식

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
