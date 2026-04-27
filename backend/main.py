import asyncio
import json
import os
from collections import defaultdict
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

USE_MOCK_MODE = os.getenv("USE_MOCK_MODE", "true").lower() == "true"

MOCK_DIR = Path(__file__).parent / "mock_agents"

# TODO(backend): /generate should create a real job_id (UUID) and return it.
#   Currently hardcoded to "92b2d589" for mock mode.


def load_mock(job_id: str) -> dict:
    path = MOCK_DIR / f"{job_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse mock data")


def load_history() -> list[dict]:
    path = MOCK_DIR / "history.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_history(items: list[dict]) -> None:
    path = MOCK_DIR / "history.json"
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


class GenerateRequest(BaseModel):
    user_input: str


@app.post("/generate")
async def generate(body: GenerateRequest):
    if USE_MOCK_MODE:
        # TODO(backend): replace with real job creation logic.
        #   Should generate a unique job_id, persist the job, and kick off the agent pipeline.
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
    # TODO(backend): replace with DB query.
    #   Filter: WHERE deleted = false, ORDER BY created_at DESC.
    #   Support query params: ?search=, ?sort=newest|oldest, ?favorite=true
    items = load_history()
    return [item for item in items if not item.get("deleted", False)]


@app.get("/analytics")
async def analytics(range: str = "all"):
    # TODO(backend): replace with pandas + CSV pipeline.
    #   Read from analytics CSV (one row per agent_done event), aggregate with groupby,
    #   support ?range= filtering, return {summary, data} shape.
    #   CSV columns: job_id, date, title, agent, model, tokens
    from datetime import date, timedelta
    today = date.today()
    if range == "today":
        cutoff = str(today)
    elif range == "7days":
        cutoff = str(today - timedelta(days=7))
    elif range == "30days":
        cutoff = str(today - timedelta(days=30))
    else:
        cutoff = None

    history_items = load_history()
    rows = []

    for item in history_items:
        if item.get("deleted", False):
            continue

        job_id = item["job_id"]
        date_str = item.get("created_at", "")[:10]
        title = item.get("title", "")

        if cutoff and date_str < cutoff:
            continue

        job_path = MOCK_DIR / f"{job_id}.json"
        if not job_path.exists():
            continue

        job_data = json.loads(job_path.read_text(encoding="utf-8"))
        events = job_data.get("events", [])

        # Aggregate tokens per model within this session
        model_tokens: dict[str, int] = defaultdict(int)
        for event in events:
            if event.get("type") == "agent_done":
                # TODO(backend): each event should carry a `model` field from the real pipeline.
                #   Fall back to "claude-sonnet" for older sessions that predate this field.
                model = event.get("model", "claude-sonnet")
                model_tokens[model] += event.get("tokens", 0)

        if not model_tokens:
            model_tokens["claude-sonnet"] = 0

        for model, tokens in model_tokens.items():
            rows.append({
                "job_id": job_id,
                "date": date_str,
                "title": title,
                "model": model,
                "tokens": tokens,
            })

    unique_jobs = len({r["job_id"] for r in rows})
    total_tokens = sum(r["tokens"] for r in rows)
    return {
        "summary": {
            "total_jobs": unique_jobs,
            "total_tokens": total_tokens,
        },
        "data": rows,
    }


@app.patch("/jobs/{job_id}/favorite")
async def toggle_favorite(job_id: str, body: dict):
    # TODO(backend): replace with DB UPDATE jobs SET favorite=? WHERE job_id=?
    favorite = body.get("favorite", False)
    items = load_history()
    found = False
    for item in items:
        if item["job_id"] == job_id:
            item["favorite"] = favorite
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="Job not found")
    save_history(items)
    return {"favorite": favorite}


@app.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    return {"stopped": True}


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    # TODO(backend): replace with DB UPDATE jobs SET deleted=true WHERE job_id=?
    #   Soft delete — never physically remove the record so analytics data stays intact.
    items = load_history()
    found = False
    for item in items:
        if item["job_id"] == job_id:
            item["deleted"] = True
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="Job not found")
    save_history(items)
    return {"deleted": True}
