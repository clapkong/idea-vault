# POST /generate — 새 job 생성 및 AI 파이프라인 백그라운드 실행 (real mode)
#
# 흐름: 요청 수신 → job 디렉토리/meta.json 생성 → asyncio.Task로 파이프라인 띄움 → job_id 즉시 반환
# 클라이언트는 반환받은 job_id로 GET /stream/{job_id} 에 연결해 진행 상황을 SSE로 수신.
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from services.pipeline import job_queues, run_pipeline, running_jobs
from services.storage import DATA_DIR, write_meta

router = APIRouter()
logger = logging.getLogger(__name__)


class GenerateRequest(BaseModel):
    user_input: str


@router.post("/generate")
# 새 job 생성, 파이프라인을 백그라운드 task로 실행 후 job_id 즉시 반환
async def generate(body: GenerateRequest):
    # hex[:8]: 8자리 축약 UUID — URL 노출용, 가독성 우선
    job_id = uuid4().hex[:8]
    job_dir = DATA_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # 원문 저장 — history 목록의 input_preview 생성에 활용
    (job_dir / "input.txt").write_text(body.user_input, encoding="utf-8")
    meta = {
        "job_id": job_id,
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "user_input": body.user_input,
        "favorite": False,
        "deleted": False,
    }
    write_meta(job_id, meta)

    # fire-and-forget — 응답을 기다리지 않고 즉시 job_id 반환
    queue: asyncio.Queue = asyncio.Queue()
    job_queues[job_id] = queue
    running_jobs[job_id] = asyncio.create_task(run_pipeline(job_id, body.user_input, queue))

    return {"job_id": job_id, "status": "processing"}
