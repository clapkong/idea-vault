"""
PRD Writer Agent
  Input : user_conditions (str), final_loop (str — JSON-serialised loop_history)
  Output: str  — Markdown PRD with 8 sections
  Model : MODEL_STRONG
"""
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import MODEL_STRONG
from backend.agents.llm import load_prompt, create_llm, extract_content

_llm = create_llm(MODEL_STRONG, max_tokens=4096)
_prompt = load_prompt("prd_writer")


async def prd_writer_agent(user_conditions: str, final_loop: str) -> str:
    user_message = (
        f"## 사용자 조건\n{user_conditions}\n\n"
        f"## 최종 검증 결과\n{final_loop}"
    )
    result = await _llm.ainvoke([SystemMessage(_prompt), HumanMessage(user_message)])
    return extract_content(result)
