import logging

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PROMPTS_DIR


_token_logger: logging.Logger | None = None


# LLM 호출 완료 시마다 토큰 사용량을 _token_logger에 기록
class _TokenHandler(BaseCallbackHandler):
    def __init__(self, model: str):
        self.model = model

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        if _token_logger is None:
            return
        usage = (response.llm_output or {}).get("token_usage", {})
        if usage:
            _token_logger.info(
                f"[token] {self.model} | prompt={usage.get('prompt_tokens', 0)} "
                f"completion={usage.get('completion_tokens', 0)} "
                f"total={usage.get('total_tokens', 0)}"
            )


# orchestrator.run() 시작 시 job별 logger를 주입 — 이후 모든 LLM 호출 토큰이 해당 로그에 기록
def set_token_logger(logger: logging.Logger) -> None:
    global _token_logger
    _token_logger = logger


# backend/agents/prompts/{agent_name}.md를 읽어 시스템 프롬프트 문자열로 반환
def load_prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text(encoding="utf-8")


# OpenRouter 백엔드로 ChatOpenAI 인스턴스 생성, 모델명을 핸들러에 직접 전달해 토큰 로그에 정확히 기록
def create_llm(model: str, max_tokens: int = 1024) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        max_tokens=max_tokens,
        callbacks=[_TokenHandler(model)],
    )


# AIMessage에서 텍스트 추출, content가 list(멀티모달)이면 text 블록만 이어붙임
# subagent는 create_deep_agent 대신 ChatOpenAI 직접 호출 — 선택 파라미터 빈 값 시 빈 출력 문제 확인
def extract_content(result) -> str:
    content = result.content
    if isinstance(content, list):
        return "\n".join(b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content or ""
