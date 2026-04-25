from backend.config import MAX_OUTER_LOOPS, MAX_INNER_LOOPS

# Gate/Critic 등에서 LLM 기반 제어가 수렴하지 않아 생기는 무한 루프를 대비한 안전 장치
def check_loop_limit(outer: int, inner: int) -> str:
    """
    Returns:
      FORCE_PRD   — outer exhausted; write PRD immediately
      FORCE_GATE  — inner exhausted; skip to Gate
      CONTINUE    — still within limits
    """
    if outer >= MAX_OUTER_LOOPS:
        return "FORCE_PRD"
    if inner >= MAX_INNER_LOOPS:
        return "FORCE_GATE"
    return "CONTINUE"
