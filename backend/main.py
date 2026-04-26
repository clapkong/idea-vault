import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_DIR = Path(__file__).parent / "mock_agents"

ANALYTICS_DATA = [
    {"job_id": "92b2d589", "date": "2026-04-26", "title": "내 음악 취향 분석기", "model": "sonnet", "tokens": 23666, "cost": 0.42},
    {"job_id": "abc12345", "date": "2026-04-25", "title": "간단한 번역 도구", "model": "sonnet", "tokens": 11200, "cost": 0.21},
    {"job_id": "def67890", "date": "2026-04-24", "title": "파일 정리 자동화 스크립트", "model": "sonnet", "tokens": 6800, "cost": 0.14},
    {"job_id": "ghi11111", "date": "2026-04-23", "title": "날씨 알림 봇", "model": "sonnet", "tokens": 3565, "cost": 0.10},
]


def load_mock(job_id: str) -> dict:
    path = MOCK_DIR / f"{job_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse mock data")


class GenerateRequest(BaseModel):
    user_input: str


@app.post("/generate")
async def generate(body: GenerateRequest):
    return {"job_id": "92b2d589", "status": "processing"}


async def event_stream(job_id: str) -> AsyncGenerator[str, None]:
    data = load_mock(job_id)
    for event in data.get("events", []):
        delay = event.get("delay_sec", 0)
        if delay:
            await asyncio.sleep(delay)
        payload = {k: v for k, v in event.items() if k != "delay_sec"}
        yield json.dumps(payload, ensure_ascii=False)


@app.get("/stream/{job_id}")
async def stream(job_id: str):
    return EventSourceResponse(event_stream(job_id))


@app.get("/result/{job_id}")
async def result(job_id: str):
    data = load_mock(job_id)
    return {"prd": data.get("prd", ""), "loop_history": data.get("loop_history", [])}


@app.get("/history")
async def history():
    path = MOCK_DIR / "history.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="History not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/analytics")
async def analytics(range: str = "all"):
    total_tokens = sum(d["tokens"] for d in ANALYTICS_DATA)
    total_cost = round(sum(d["cost"] for d in ANALYTICS_DATA), 2)
    return {
        "summary": {
            "total_jobs": len(ANALYTICS_DATA),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        },
        "data": ANALYTICS_DATA,
    }
