# 환경변수 로딩 + 필수값 검증 — .env 기반, 누락 시 즉시 EnvironmentError
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv() #.env 파일을 읽어서 환경변수로 등록

# 필수 환경변수가 없으면 즉시 에러
def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Required env var {key!r} is not set. Check your .env file.")
    return val


# 사용할 모델 종류 정보(필수)
MODEL_STRONG: str = _require("MODEL_STRONG")
MODEL_LIGHT: str = _require("MODEL_LIGHT")

# OpenRouter API 접속 정보
OPENROUTER_API_KEY: str = _require("OPENROUTER_API_KEY") # Key = 필수
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")  # 웹 검색용, 미설정 시 검색 비활성화

# 오케스트레이터 루프 횟수 상한 (기본값 각 3회)
MAX_OUTER_LOOPS: int = int(os.getenv("MAX_OUTER_LOOPS", "3"))
MAX_INNER_LOOPS: int = int(os.getenv("MAX_INNER_LOOPS", "3"))

BASE_DIR: Path = Path(__file__).parent                  # backend/
PROJECT_ROOT: Path = BASE_DIR.parent                    # ideavault/
PROMPTS_DIR: Path = BASE_DIR / "agents" / "prompts"    # backend/agents/prompts/
