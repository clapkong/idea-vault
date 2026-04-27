"""
Planner Agent
  Input : mode (INIT | REFINE | PIVOT), user_conditions (str), **kwargs
            REFINE → current_topic (str), gate_feedback (str)
            PIVOT  → rejected_topics (list[str])
  Output: str  — TOPIC / DESCRIPTION / EXTERNAL / INTERNAL sections
  Model : MODEL_STRONG
"""
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import MODEL_STRONG
from backend.agents.llm import load_prompt, create_llm, extract_content

_llm = create_llm(MODEL_STRONG, max_tokens=1024)
_prompt = load_prompt("planner")


async def planner_agent(
    mode: str,
    user_conditions: str,
    current_topic: str = "",
    gate_feedback: str = "",
    rejected_topics: list = None,
) -> str:
    parts = [f"## 모드\n{mode}", f"## 사용자 조건\n{user_conditions}"]
    if mode == "REFINE":
        parts.append(f"현재 주제: {current_topic}")
        parts.append(f"Gate 피드백: {gate_feedback}")
    elif mode == "PIVOT":
        rejected = "\n".join(f"- {t}" for t in (rejected_topics or []))
        parts.append(f"기각된 주제들:\n{rejected}")
    user_message = "\n\n".join(parts)
    result = await _llm.ainvoke([SystemMessage(_prompt), HumanMessage(user_message)])
    return extract_content(result)
