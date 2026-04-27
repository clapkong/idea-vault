import logging

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PROMPTS_DIR


_token_logger: logging.Logger | None = None


class _TokenHandler(BaseCallbackHandler):
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        if _token_logger is None:
            return
        usage = (response.llm_output or {}).get("token_usage", {})
        if usage:
            _token_logger.info(
                f"[token] prompt={usage.get('prompt_tokens', 0)} "
                f"completion={usage.get('completion_tokens', 0)} "
                f"total={usage.get('total_tokens', 0)}"
            )


_handler = _TokenHandler()


def set_token_logger(logger: logging.Logger) -> None:
    global _token_logger
    _token_logger = logger


def load_prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text(encoding="utf-8")


def create_llm(model: str, max_tokens: int = 1024) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        max_tokens=max_tokens,
        callbacks=[_handler],
    )


def extract_content(result) -> str:
    # subagent는 create_deep_agent 대신 ChatOpenAI 직접 호출 — 선택 파라미터 빈 값 시 빈 출력 문제 확인
    content = result.content
    if isinstance(content, list):
        return "\n".join(b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content
