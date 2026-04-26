import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USE_MOCK_MODE = os.getenv("USE_MOCK_MODE", "false").lower() == "true"

MOCK_DIR = Path(__file__).parent / "mock_agents"

ANALYTICS_DATA = [
    {"job_id": "92b2d589", "date": "2026-04-26", "title": "내 음악 취향 분석기", "model": "sonnet", "tokens": 23666, "cost": 0.42},
    {"job_id": "abc12345", "date": "2026-04-25", "title": "간단한 번역 도구", "model": "sonnet", "tokens": 11200, "cost": 0.21},
    {"job_id": "def67890", "date": "2026-04-24", "title": "파일 정리 자동화 스크립트", "model": "sonnet", "tokens": 6800, "cost": 0.14},
    {"job_id": "ghi11111", "date": "2026-04-23", "title": "날씨 알림 봇", "model": "haiku", "tokens": 3565, "cost": 0.10},
]

# In-memory store for favorite state (mirrors mock data)
_favorites: dict[str, bool] = {}


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
    if USE_MOCK_MODE:
        return {"job_id": "92b2d589", "status": "processing"}
    raise HTTPException(status_code=501, detail="Real mode not implemented")


async def mock_event_stream(job_id: str) -> AsyncGenerator[str, None]:
    data = load_mock(job_id)
    for event in data.get("events", []):
        delay = event.get("delay_sec", 0)
        if delay:
            await asyncio.sleep(delay)
        payload = {k: v for k, v in event.items() if k != "delay_sec"}
        yield json.dumps(payload, ensure_ascii=False)


@app.get("/stream/{job_id}")
async def stream(job_id: str):
    if USE_MOCK_MODE:
        return EventSourceResponse(mock_event_stream(job_id))
    raise HTTPException(status_code=501, detail="Real mode not implemented")


@app.get("/result/{job_id}")
async def result(job_id: str):
    if USE_MOCK_MODE:
        data = load_mock(job_id)
        return {
            "prd": data.get("prd", ""),
            "loop_history": data.get("loop_history", []),
            "events": data.get("events", []),
        }
    raise HTTPException(status_code=501, detail="Real mode not implemented")


@app.get("/history")
async def history():
    path = MOCK_DIR / "history.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="History not found")
    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        job_id = item.get("job_id")
        if job_id in _favorites:
            item["favorite"] = _favorites[job_id]
    return items


@app.get("/analytics")
async def analytics(range: str = "all"):
    from datetime import date, timedelta
    today = date.today()
    if range == "today":
        cutoff = today
    elif range == "7days":
        cutoff = today - timedelta(days=7)
    elif range == "30days":
        cutoff = today - timedelta(days=30)
    else:
        cutoff = None

    data = ANALYTICS_DATA
    if cutoff:
        data = [d for d in data if d["date"] >= str(cutoff)]

    total_tokens = sum(d["tokens"] for d in data)
    total_cost = round(sum(d["cost"] for d in data), 2)
    return {
        "summary": {
            "total_jobs": len(data),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        },
        "data": data,
    }


@app.patch("/jobs/{job_id}/favorite")
async def toggle_favorite(job_id: str, body: dict):
    favorite = body.get("favorite", False)
    _favorites[job_id] = favorite
    return {"favorite": favorite}


@app.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    return {"stopped": True}


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    return {"deleted": True}
