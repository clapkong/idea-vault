# LLM 공통 유틸 — ChatOpenAI 팩토리, 프롬프트 로더, 콜백 핸들러, run.log 로거 주입
import contextvars
import logging
from datetime import datetime

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

from config import OPENROUTER_API_KEY, PROMPTS_DIR

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# ContextVar — asyncio task마다 독립적인 로거 유지 (동시 실행 안전)
_token_logger_ctx: contextvars.ContextVar[logging.Logger | None] = contextvars.ContextVar(
    "token_logger", default=None
)
_block_logger_ctx: contextvars.ContextVar[logging.Logger | None] = contextvars.ContextVar(
    "block_logger", default=None
)

_SEP = "─" * 60


# run.log 타임스탬프 포맷
def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_line(text: str = "") -> None:
    """block_logger에 타임스탬프 포함 한 줄 기록. orchestrator의 START/CALL/DONE에 사용."""
    logger = _block_logger_ctx.get()
    if logger is None:
        return
    logger.info(f"{_ts()} | {text}")


def log_block(agent_name: str, input_text: str, output_text: str) -> None:
    """LLM 없는 에이전트(researcher)용 — ────·<입력>·<출력> 전체 블록을 block_logger에 기록."""
    logger = _block_logger_ctx.get()
    if logger is None:
        return
    block = (
        f"\n{_SEP}\n"
        f"[{agent_name}]\n\n"
        f"<입력>\n{input_text}\n\n"
        f"<출력>\n{output_text}\n"
        f"{_SEP}"
    )
    logger.info(block)


# LangChain 콜백 핸들러 — LLM 호출마다 토큰 카운트·입출력 블록을 run.log에 기록
class _TokenHandler(BaseCallbackHandler):
    def __init__(self, model: str, agent_name: str = ""):
        self.model = model
        self.agent_name = agent_name
        # run_id → HumanMessage 내용 임시 저장 (on_chat_model_start → on_llm_end 구간)
        self._pending: dict[str, str] = {}

    # LLM 호출 직전 — HumanMessage 내용을 run_id 키로 임시 저장
    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:
        if _block_logger_ctx.get() is None or not self.agent_name:
            return
        run_id = str(kwargs.get("run_id", ""))
        human_content = ""
        for msg_list in messages:
            for msg in msg_list:
                if hasattr(msg, "type") and msg.type == "human":
                    human_content = msg.content
        self._pending[run_id] = human_content

    # LLM 응답 수신 후 — 토큰 카운트 + 입출력 블록 run.log 기록
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        ts = _ts()
        usage = (response.llm_output or {}).get("token_usage", {})

        # [tokens] 줄 — 어느 에이전트의 토큰인지 agent_name 포함, 타임스탬프 추가
        if usage:
            token_logger = _token_logger_ctx.get()
            if token_logger is not None:
                agent_tag = f"[{self.agent_name}] " if self.agent_name else ""
                token_logger.info(
                    f"{ts} | [tokens] {agent_tag}{self.model} | "
                    f"prompt={usage.get('prompt_tokens', 0)} "
                    f"completion={usage.get('completion_tokens', 0)} "
                    f"total={usage.get('total_tokens', 0)}"
                )

        block_logger = _block_logger_ctx.get()
        if block_logger is not None and self.agent_name:
            run_id = str(kwargs.get("run_id", ""))
            input_text = self._pending.pop(run_id, "")
            output_text = ""
            if response.generations and response.generations[0]:
                output_text = response.generations[0][0].text

            # DONE 한 줄 → 빈 줄 → 전체 블록 순서
            block_logger.info(f"{ts} | [{self.agent_name}] DONE | {output_text[:200]}")
            block_logger.info(f"{ts} | ")
            block = (
                f"\n{_SEP}\n"
                f"[{self.agent_name}]\n\n"
                f"<입력>\n{input_text}\n\n"
                f"<출력>\n{output_text}\n"
                f"{_SEP}"
            )
            block_logger.info(block)

    # LLM 오류 시 pending 입력 제거
    def on_llm_error(self, error, **kwargs) -> None:
        run_id = str(kwargs.get("run_id", ""))
        self._pending.pop(run_id, None)


# pipeline.py에서 job 시작 시 주입, 종료 시 None으로 해제
def set_token_logger(logger: logging.Logger | None) -> None:
    _token_logger_ctx.set(logger)


# pipeline.py에서 job 시작 시 주입, 종료 시 None으로 해제
def set_block_logger(logger: logging.Logger | None) -> None:
    _block_logger_ctx.set(logger)


# backend/agents/prompts/{agent_name}.md를 읽어 시스템 프롬프트 문자열로 반환
def load_prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text(encoding="utf-8")


# OpenRouter 백엔드로 ChatOpenAI 인스턴스 생성
# agent_name 지정 시 run.log에 에이전트별 블록 형식으로 I/O 기록
def create_llm(model: str, max_tokens: int | None = None, agent_name: str = "") -> ChatOpenAI:
    kwargs: dict = dict(model=model, api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if agent_name:
        kwargs["callbacks"] = [_TokenHandler(model, agent_name)]
    return ChatOpenAI(**kwargs)


# AIMessage에서 텍스트 추출, content가 list(멀티모달)이면 text 블록만 이어붙임
# subagent는 create_deep_agent 대신 ChatOpenAI 직접 호출 — 선택 파라미터 빈 값 시 빈 출력 문제 확인
def extract_content(result) -> str:
    content = result.content
    if isinstance(content, list):
        return "\n".join(b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content or ""


# AIMessage에서 input/output/total 토큰 수 추출 — usage_metadata(LangChain 표준) 우선, 없으면 response_metadata 폴백
def extract_tokens(result) -> dict:
    if hasattr(result, "usage_metadata") and result.usage_metadata:
        um = result.usage_metadata
        return {
            "input": um.get("input_tokens", 0),
            "output": um.get("output_tokens", 0),
            "total": um.get("total_tokens", 0),
        }
    usage = (getattr(result, "response_metadata", None) or {}).get("token_usage", {})
    return {
        "input": usage.get("prompt_tokens", 0),
        "output": usage.get("completion_tokens", 0),
        "total": usage.get("total_tokens", 0),
    }
