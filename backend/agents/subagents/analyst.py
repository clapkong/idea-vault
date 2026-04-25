"""
Analyst Agent
  Input : internal_points (str), user_conditions (str),
          researcher_result (str, optional), critic_feedback (str, optional)
  Output: str  — per-point judgments + conflict summary + one-line conclusion
  Model : MODEL_LIGHT
"""
from backend.config import MODEL_LIGHT
from backend.agents.llm import call_llm, load_prompt

def analyst_agent(internal_points: str, user_conditions: str, **kwargs) -> str:
    prompt = (
        load_prompt("analyst")
        .replace("{user_conditions}", user_conditions)
        .replace("{internal_points}", internal_points)
        .replace("{researcher_result}", kwargs.get("researcher_result", "없음"))
        .replace("{critic_feedback}", kwargs.get("critic_feedback", "없음"))
    )
    return call_llm(MODEL_LIGHT, prompt, max_tokens=1536)
