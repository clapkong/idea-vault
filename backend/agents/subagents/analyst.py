"""
Analyst Agent
  Input : internal_points (str), user_conditions (str), current_topic (str, optional),
          researcher_result (str, optional), critic_feedback (str, optional)
  Output: str  — per-point judgments + conflict summary + one-line conclusion
  Model : MODEL_LIGHT
"""
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import MODEL_LIGHT
from backend.agents.llm import load_prompt, create_llm, extract_content

_llm = create_llm(MODEL_LIGHT, max_tokens=1536)
_prompt = load_prompt("analyst")


async def analyst_agent(
    internal_points: str,
    user_conditions: str,
    current_topic: str = "",
    researcher_result: str = "없음",
    critic_feedback: str = "없음",
) -> str:
    parts = [f"## 사용자 조건\n{user_conditions}"]
    if current_topic:
        parts.append(f"## 현재 주제\n{current_topic}")
    parts += [
        f"## 분석 포인트\n{internal_points}",
        f"## Researcher 결과 (선택)\n{researcher_result}",
        f"## Critic 보강 방향 (선택)\n{critic_feedback}",
    ]
    user_message = "\n\n".join(parts)
    result = await _llm.ainvoke([SystemMessage(_prompt), HumanMessage(user_message)])
    return extract_content(result)
