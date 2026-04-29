"""
Critic Agent
  Input : planner_result (str), researcher_result (str),
          analyst_result (str), user_conditions (str),
          previous_findings (str, optional)
  Output: str  — evaluation text + direction (RESEARCHER/ANALYST/BOTH/GATE)
                 + feasibility/fit/clarity scores
  Model : MODEL_STRONG
"""
from langchain_core.messages import HumanMessage, SystemMessage

from config import MODEL_STRONG
from agents.llm import load_prompt, create_llm, extract_content, extract_tokens

_llm = create_llm(MODEL_STRONG, max_tokens=2048, agent_name="critic")
_prompt = load_prompt("critic")


# researcher·analyst 결과를 종합해 정보 충분성 평가, 다음 방향 결정
async def critic_agent(
    planner_result: str,
    researcher_result: str,
    analyst_result: str,
    user_conditions: str,
    previous_findings: str = "",
) -> str:
    user_message = (
        f"## 사용자 조건\n{user_conditions}\n\n"
        f"## Planner 결과\n{planner_result}\n\n"
        f"## Researcher 결과\n{researcher_result}\n\n"
        f"## Analyst 결과\n{analyst_result}\n\n"
        f"## 이전 루프 Critics 결과 (있을 경우)\n{previous_findings}"
    )
    result = await _llm.ainvoke([SystemMessage(_prompt), HumanMessage(user_message)])
    return extract_content(result), extract_tokens(result)
