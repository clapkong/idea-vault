# GET /stream/{job_id} — SSE 스트림 (real mode)
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from services.pipeline import job_queues

router = APIRouter()


async def _event_stream(queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """queue에서 이벤트를 꺼내 yield. done 이벤트 수신 시 루프 종료 → SSE 연결 닫힘."""
    while True:
        event = await queue.get()
        yield json.dumps(event, ensure_ascii=False)
        if event.get("type") == "done":
            break


@router.get("/stream/{job_id}")
async def stream(job_id: str):
    queue = job_queues.get(job_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return EventSourceResponse(_event_stream(queue))
