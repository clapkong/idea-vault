"""
Critic Agent
  Input : planner_result (str), researcher_result (str),
          analyst_result (str), user_conditions (str)
  Output: str  — evaluation text + direction (RESEARCHER/ANALYST/BOTH/GATE)
                 + feasibility/fit/clarity scores
  Model : MODEL_STRONG
"""
from backend.config import MODEL_STRONG
from backend.agents.llm import call_llm, load_prompt

def critic_agent(
    planner_result: str,
    researcher_result: str,
    analyst_result: str,
    user_conditions: str,
) -> str:
    prompt = (
        load_prompt("critic")
        .replace("{user_conditions}", user_conditions)
        .replace("{planner_result}", planner_result)
        .replace("{researcher_result}", researcher_result)
        .replace("{analyst_result}", analyst_result)
    )
    return call_llm(MODEL_STRONG, prompt, max_tokens=1024)
