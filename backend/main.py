# FastAPI 앱 진입점 — 앱 생성, CORS 설정, 라우터 등록만 담당
# USE_MOCK_MODE 분기는 여기서 한 번만 수행 — real mode가 기본 경로
from pathlib import Path

import os

import requests
from dotenv import load_dotenv

# storage.py가 import될 때 os.getenv로 USE_MOCK_MODE를 읽으므로,
# 반드시 다른 import보다 먼저 .env를 로드해야 한다
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.storage import USE_MOCK_MODE

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 이 서버가 살아있는지 확인
@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": USE_MOCK_MODE}


# AI 모델(OpenRouter)과 검색(Tavily) 서버가 지금 접속 가능한지 확인
@app.get("/ready")
def ready():
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    try:
        r = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=3,
        )
        openrouter_status = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        openrouter_status = "degraded"

    try:
        requests.get("https://tavily.com", timeout=3)
        tavily_status = "ok"
    except Exception:
        tavily_status = "degraded"

    return {"openrouter": openrouter_status, "tavily": tavily_status}


# Agent 사용 모드
if not USE_MOCK_MODE:
    from routers.analytics import router as analytics_router
    from routers.generate import router as generate_router
    from routers.history import router as history_router
    from routers.jobs import router as jobs_router
    from routers.stream import router as stream_router

    app.include_router(generate_router)
    app.include_router(stream_router)
    app.include_router(jobs_router)
    app.include_router(history_router)
    app.include_router(analytics_router)

# Agent를 실제로 실행하지 않고, 기존 로그를 agent를 실행하듯이 불러오는 모드 (디버깅용)
else:
    from routers.mock import router as mock_router
    app.include_router(mock_router)
