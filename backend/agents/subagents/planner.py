"""
Planner Agent
  Input : mode (INIT | REFINE | PIVOT), user_conditions (str)
            REFINE → current_topic (str), gate_feedback (str)
            PIVOT  → rejected_topics (list[str])
  Output: str  — TOPIC / DESCRIPTION / EXTERNAL / INTERNAL sections
  Model : MODEL_STRONG
"""
from langchain_core.messages import HumanMessage, SystemMessage

from config import MODEL_STRONG
from agents.llm import load_prompt, create_llm, extract_content, extract_tokens

_llm = create_llm(MODEL_STRONG, max_tokens=1024, agent_name="planner")
_prompt = load_prompt("planner")


# 모드에 따라 주제를 발굴(INIT), 포인트 정제(REFINE), 새 주제 탐색(PIVOT)
# 출력의 EXTERNAL은 researcher 쿼리로, INTERNAL은 analyst 분석 포인트로 사용됨
async def planner_agent(
    mode: str,
    user_conditions: str,
    current_topic: str = "",
    gate_feedback: str = "",
    rejected_topics: list = None,
) -> str:
    parts = [f"## 모드\n{mode}", f"## 사용자 조건\n{user_conditions}"]

    # 모드별 추가 컨텍스트 — REFINE은 현재 주제·피드백, PIVOT은 기각 목록 전달
    if mode == "REFINE":
        parts.append(f"현재 주제: {current_topic}")
        parts.append(f"Gate 피드백: {gate_feedback}")
    elif mode == "PIVOT":
        rejected = "\n".join(f"- {t}" for t in (rejected_topics or []))
        parts.append(f"기각된 주제들:\n{rejected}")

    user_message = "\n\n".join(parts)
    result = await _llm.ainvoke([SystemMessage(_prompt), HumanMessage(user_message)])
    return extract_content(result), extract_tokens(result)
