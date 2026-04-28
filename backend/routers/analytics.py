# GET /analytics?range=all|today|7days|30days — 토큰 사용량 통계 (real mode)
import io
import json
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.storage import DATA_DIR, load_history

router = APIRouter()


def _compute_model_aggregates(df: pd.DataFrame) -> list:
    """모델별 토큰 합계 집계 (파이 차트용)."""
    result = df.groupby("model")["tokens"].sum().reset_index()
    return [{"label": row["model"], "value": int(row["tokens"])} for _, row in result.iterrows()]


def _compute_date_aggregates(df: pd.DataFrame) -> list:
    """날짜·모델별 세그먼트 집계 (스택 막대 차트용).
    같은 날짜에 여러 job이 있을 경우 모델별로 합산해 segment를 만든다.
    합산 없이 row를 그대로 넘기면 같은 모델 색이 교차 반복되는 줄무늬가 생김.
    """
    result = []
    for date in sorted(df["date"].unique()):
        day_data = df[df["date"] == date]
        total = int(day_data["tokens"].sum())
        model_totals = day_data.groupby("model")["tokens"].sum()
        segments = [
            {"model": model, "value": int(tokens)}
            for model, tokens in model_totals.items()
        ]
        result.append({"label": date, "total": total, "segments": segments})
    return result


@router.get("/analytics")
# result.json이 존재하는 job의 events에서 model별 토큰 집계 후 차트 데이터 반환
async def analytics(range: str = "all"):
    all_items = [
        i for i in load_history()
        if not i.get("deleted", False)
    ]

    # job별 result.json events에서 model별 토큰 집계
    # status 대신 result.json 존재 여부로 판단 — compute_cost 실패 등으로 status가
    # failed여도 PRD가 완성된 경우 집계에 포함하기 위함
    rows = []
    for item in all_items:
        job_id = item["job_id"]
        result_path = DATA_DIR / job_id / "result.json"
        # result.json 없으면 파이프라인 미완료 — 스킵
        if not result_path.exists():
            continue

        # JSON 파싱 실패(파일 손상 등) 시 해당 job만 스킵
        try:
            events = json.loads(result_path.read_text(encoding="utf-8")).get("events", [])
        except Exception:
            continue
        model_tokens: dict[str, int] = defaultdict(int)
        for event in events:
            if event.get("type") == "agent_done":
                model = event.get("model")
                t = event.get("tokens", 0)
                # tokens 필드 구버전: 정수, 신버전: {input, output, total} 딕셔너리
                tokens = t.get("total", 0) if isinstance(t, dict) else t
                # researcher(model=None)와 토큰 0인 이벤트는 집계 의미 없으므로 제외
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
        return {
            "summary": {"total_jobs": 0, "total_tokens": 0},
            "data": [],
            "modelAggregates": [],
            "dateAggregates": [],
        }

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
        return {
            "summary": {"total_jobs": 0, "total_tokens": 0},
            "data": [],
            "modelAggregates": [],
            "dateAggregates": [],
        }

    return {
        "summary": {
            "total_jobs": df["job_id"].nunique(),
            "total_tokens": int(df["tokens"].sum()),
        },
        "data": df[["job_id", "date", "title", "model", "tokens"]].to_dict("records"),
        "modelAggregates": _compute_model_aggregates(df),
        "dateAggregates": _compute_date_aggregates(df),
    }


@router.get("/analytics/csv")
# analytics() 결과를 CSV로 직렬화해 첨부 파일로 반환 — GET /analytics/csv?range=...
async def analytics_csv(range: str = "all"):
    result = await analytics(range)
    df = pd.DataFrame(result["data"])
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )
