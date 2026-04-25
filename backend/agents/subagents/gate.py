"""
Gate Agent
  Input : critic_result (str), user_conditions (str)
  Output: str  — judgment text + 결정: REFINE | PIVOT | DONE
  Model : MODEL_LIGHT
"""
from backend.config import MODEL_LIGHT
from backend.agents.llm import call_llm, load_prompt

def gate_agent(critic_result: str, user_conditions: str, gate_decisions: str = "") -> str:
    prompt = (
        load_prompt("gate")
        .replace("{user_conditions}", user_conditions)
        .replace("{critic_result}", critic_result)
        .replace("{gate_decisions}", gate_decisions)
    )
    return call_llm(MODEL_LIGHT, prompt, max_tokens=512)