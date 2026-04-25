"""
Planner Agent
  Input : mode (INIT | REFINE | PIVOT), user_conditions (str), **kwargs
            REFINE → current_topic (str), critic_feedback (str)
            PIVOT  → rejected_topics (list[str])
  Output: str  — TOPIC / DESCRIPTION / EXTERNAL / INTERNAL sections
  Model : MODEL_STRONG
"""
from backend.config import MODEL_STRONG
from backend.agents.llm import call_llm, load_prompt

def planner_agent(mode: str, user_conditions: str, **kwargs) -> str:
    prompt = (
        load_prompt("planner")
        .replace("{mode}", mode)
        .replace("{user_conditions}", user_conditions)
        .replace("{current_topic}", kwargs.get("current_topic", ""))
        .replace("{critic_feedback}", kwargs.get("critic_feedback", ""))
        .replace("{rejected_topics}", "\n".join(f"- {t}" for t in kwargs.get("rejected_topics", [])))
    )
    return call_llm(MODEL_STRONG, prompt, max_tokens=1024)
