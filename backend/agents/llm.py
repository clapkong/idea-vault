"""
Shared LLM client — OpenRouter (OpenAI-compatible API).
All agents import call_llm() from here instead of touching SDK directly.
"""
from typing import Callable

from openai import OpenAI

from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PROMPTS_DIR

_client: OpenAI | None = None # OpenAI API 클라이언트
_usage_callback: Callable | None = None  # 토큰 사용량 추적 콜백

# 최초 호출 시에 클라이언트 생성, 이후 재사용
def _get_client() -> OpenAI:
    global _client # 전역변수
    if _client is None:
        _client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
    return _client

# 토큰 사용량 콜백 등록 (None 전달 시 비활성화)
def set_usage_callback(cb: Callable | None) -> None:
    global _usage_callback # 현재 기준 토큰 사용량 로깅만 해주는 함수
    _usage_callback = cb

# prompts/{agent_name}.md 파일을 읽어 subagent 프롬프트 반환
def load_prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text(encoding="utf-8")

# subagent 호출용 공통 함수
def call_llm(model: str, prompt: str, max_tokens: int = 1024) -> str:
    # 클라이언트 객체 생성/불러오기 + OpenAI.chat.completions()
    response = _get_client().chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    # 토큰 로깅 함수로 토큰 사용량 로깅
    if _usage_callback and response.usage:
        u = response.usage
        _usage_callback(model, u.prompt_tokens, u.completion_tokens, u.total_tokens)
    
    # 모델 response 돌려주기
    return response.choices[0].message.content or ""
