"""
PRD Writer Agent
  Input : user_conditions (str), final_loop (str — JSON-serialised loop_history)
  Output: str  — Markdown PRD with 8 sections
  Model : MODEL_STRONG
"""
from backend.config import MODEL_STRONG
from backend.agents.llm import call_llm, load_prompt

def prd_writer_agent(user_conditions: str, final_loop: str) -> str:
    prompt = (
        load_prompt("prd_writer")
        .replace("{user_conditions}", user_conditions)
        .replace("{final_loop}", final_loop)
    )
    return call_llm(MODEL_STRONG, prompt, max_tokens=4096)
