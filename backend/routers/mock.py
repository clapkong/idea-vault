# USE_MOCK_MODE=true 일 때 등록되는 라우터
# fixtures/ 대신 data/jobs/ 의 실제 완료 job을 소스로 삼아 스트림을 재생한다.
# generate + stream 만 mock 구현 — 나머지는 real storage 함수에 위임.
import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from services.storage import DATA_DIR, load_history, read_meta, write_meta

router = APIRouter()

# fixtures/92b2d589.json 패턴 분석 기반 에이전트별 딜레이(초)
# agent_start: 0.3s, agent_progress: 0s, agent_done: 에이전트별 하드코딩
_START_DELAY = 0.3
_DONE_DELAYS: dict[str, float] = {
    "planner":    5.0,
    "researcher": 2.0,
    "analyst":    4.0,
    "critic":     8.0,
    "gate":       3.0,
    "prd_writer": 10.0,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_source_job() -> str | None:
    """data/jobs/ 에서 가장 최근 완료된 job_id 반환. 없으면 None."""
    for item in load_history():
        if item.get("status") == "done" and not item.get("deleted"):
            return item["job_id"]
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    user_input: str


@router.post("/generate")
async def generate(body: GenerateRequest):
    source_id = _find_source_job()
    if not source_id:
        raise HTTPException(
            status_code=500,
            detail="Mock 모드: data/jobs/ 에 완료된 job이 없습니다. 먼저 real 모드로 한 번 실행하세요.",
        )

    job_id = uuid.uuid4().hex[:8]
    job_dir = DATA_DIR / job_id
    job_dir.mkdir(parents=True)

    meta = {
        "job_id": job_id,
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "user_input": body.user_input,
        "favorite": False,
        "deleted": False,
        "mock_source": source_id,
    }
    write_meta(job_id, meta)
    (job_dir / "input.txt").write_text(body.user_input, encoding="utf-8")

    return {"job_id": job_id, "status": "processing"}


async def _replay(job_id: str) -> AsyncGenerator[str, None]:
    """source job의 events를 에이전트별 딜레이로 재생 후 result.json 기록."""
    meta = read_meta(job_id)
    source_id = meta.get("mock_source")
    if not source_id:
        raise HTTPException(status_code=400, detail="mock_source 없음")

    source_result_path = DATA_DIR / source_id / "result.json"
    if not source_result_path.exists():
        raise HTTPException(status_code=500, detail="소스 job result.json 없음")

    source_data = json.loads(source_result_path.read_text(encoding="utf-8"))
    events = source_data.get("events", [])

    start = asyncio.get_event_loop().time()

    for event in events:
        ev_type = event.get("type")
        agent = event.get("agent", "")

        if ev_type == "agent_start":
            await asyncio.sleep(_START_DELAY)
        elif ev_type == "agent_done":
            await asyncio.sleep(_DONE_DELAYS.get(agent, 5.0))

        yield json.dumps(event, ensure_ascii=False)

    duration = round(asyncio.get_event_loop().time() - start, 1)

    # result.json + prd.md 기록
    job_dir = DATA_DIR / job_id
    result_data = {
        "prd": source_data.get("prd", ""),
        "loop_history": source_data.get("loop_history", []),
        "events": events,
        "duration_sec": duration,
    }
    (job_dir / "result.json").write_text(
        json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (job_dir / "prd.md").write_text(source_data.get("prd", ""), encoding="utf-8")

    source_meta = read_meta(source_id)
    meta.update({
        "status": "done",
        "duration_sec": duration,
        "tokens": source_meta.get("tokens", 0),
        "cost": source_meta.get("cost", 0.0),
    })
    write_meta(job_id, meta)

    yield json.dumps({"type": "done", "job_id": job_id}, ensure_ascii=False)


@router.get("/stream/{job_id}")
async def stream(job_id: str):
    return EventSourceResponse(_replay(job_id))


@router.get("/result/{job_id}")
async def result(job_id: str):
    result_path = DATA_DIR / job_id / "result.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="아직 완료되지 않음")
    data = json.loads(result_path.read_text(encoding="utf-8"))
    return {
        "prd": data.get("prd", ""),
        "loop_history": data.get("loop_history", []),
        "events": data.get("events", []),
    }


@router.get("/history")
async def history():
    return [i for i in load_history() if not i.get("deleted")]


@router.get("/analytics")
async def analytics(range: str = "all"):
    from routers.analytics import analytics as real_analytics
    return await real_analytics(range)


@router.patch("/jobs/{job_id}/favorite")
async def toggle_favorite(job_id: str, body: dict):
    meta = read_meta(job_id)
    meta["favorite"] = body.get("favorite", False)
    write_meta(job_id, meta)
    return {"favorite": meta["favorite"]}


@router.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    return {"stopped": True}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    meta = read_meta(job_id)
    meta["deleted"] = True
    write_meta(job_id, meta)
    return {"deleted": True}
