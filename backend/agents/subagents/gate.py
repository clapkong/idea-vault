"""
Gate Agent
  Input : critic_result (str), user_conditions (str), gate_decisions (str, optional)
  Output: str  — judgment text + 결정: REFINE | PIVOT | DONE
  Model : MODEL_LIGHT
"""
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import MODEL_LIGHT
from backend.agents.llm import load_prompt, create_llm, extract_content

_llm = create_llm(MODEL_LIGHT, max_tokens=512)
_prompt = load_prompt("gate")


# critic 평가를 바탕으로 주제 계속 여부 심사
async def gate_agent(
    critic_result: str,
    user_conditions: str,
    gate_decisions: str = "",
) -> str:
    user_message = (
        f"## 사용자 조건\n{user_conditions}\n\n"
        f"## Critic 평가\n{critic_result}"
    )
    # 이전 gate 결정이 있을 때만 추가 — 첫 루프에서는 생략
    if gate_decisions:
        user_message += f"\n\n## 이전 Gate 결정\n{gate_decisions}"
    result = await _llm.ainvoke([SystemMessage(_prompt), HumanMessage(user_message)])
    return extract_content(result)
