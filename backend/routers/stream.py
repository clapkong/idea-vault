# GET /stream/{job_id} — 실행 중인 job의 이벤트를 SSE로 스트리밍 (real mode)
#
# pipeline.py의 job_queues[job_id] 큐에서 이벤트를 꺼내 클라이언트에 실시간 전송.
# orchestrator가 각 에이전트 시작/완료 시 큐에 push → 여기서 꺼내서 SSE로 내보냄.
# type=done 이벤트 수신 시 루프 종료 → SSE 연결 닫힘.
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from services.pipeline import job_queues

router = APIRouter()


# AsyncGenerator[str, None]: yield로 값을 하나씩 내보내는 async 함수의 반환 타입.
# str = yield하는 값의 타입, None = 외부에서 send()로 주입하는 값의 타입(여기선 안 씀).
# EventSourceResponse가 이 제너레이터를 받아서 SSE 형식으로 클라이언트에 스트리밍함.
async def _event_stream(queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """queue에서 이벤트를 꺼내 yield. done 이벤트 수신 시 루프 종료 → SSE 연결 닫힘."""
    while True:
        event = await queue.get()
        yield json.dumps(event, ensure_ascii=False)
        if event.get("type") == "done":
            break


@router.get("/stream/{job_id}")
# job_id에 해당하는 큐를 조회해 SSE 스트림 응답 반환
async def stream(job_id: str):
    queue = job_queues.get(job_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return EventSourceResponse(_event_stream(queue))
