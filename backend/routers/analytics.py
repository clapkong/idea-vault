# GET /analytics?range=all|today|7days|30days — 토큰 사용량 통계 (real mode)
import json
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter

from services.storage import DATA_DIR, load_history

router = APIRouter()


@router.get("/analytics")
async def analytics(range: str = "all"):
    done_items = [
        i for i in load_history()
        if i.get("status") == "done" and not i.get("deleted", False)
    ]
    if not done_items:
        return {"summary": {"total_jobs": 0, "total_tokens": 0}, "data": []}

    # job별 result.json events에서 model별 토큰 집계
    rows = []
    for item in done_items:
        job_id = item["job_id"]
        result_path = DATA_DIR / job_id / "result.json"
        if not result_path.exists():
            continue

        events = json.loads(result_path.read_text(encoding="utf-8")).get("events", [])
        model_tokens: dict[str, int] = defaultdict(int)
        for event in events:
            if event.get("type") == "agent_done":
                model = event.get("model")
                t = event.get("tokens", 0)
                tokens = t.get("total", 0) if isinstance(t, dict) else t
                if model and tokens > 0:
                    model_tokens[model] += tokens

        if not model_tokens:
            continue

        for model, tokens in model_tokens.items():
            rows.append({
                "job_id": job_id,
                "date": item.get("created_at", "")[:10],
                "title": item.get("title", ""),
                "model": model,
                "tokens": tokens,
            })

    if not rows:
        return {"summary": {"total_jobs": 0, "total_tokens": 0}, "data": []}

    df = pd.DataFrame(rows)
    today_str = datetime.now().strftime("%Y-%m-%d")
    if range == "today":
        df = df[df["date"] == today_str]
    elif range == "7days":
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        df = df[df["date"] >= cutoff]
    elif range == "30days":
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        df = df[df["date"] >= cutoff]

    if df.empty:
        return {"summary": {"total_jobs": 0, "total_tokens": 0}, "data": []}

    return {
        "summary": {
            "total_jobs": df["job_id"].nunique(),
            "total_tokens": int(df["tokens"].sum()),
        },
        "data": df[["job_id", "date", "title", "model", "tokens"]].to_dict("records"),
    }
