"""
Orchestrator — deepagents LLM agent that reads orchestrator.md and calls tools.
Pattern mirrors the user's create_deep_agent + @tool structure.
"""
import json
import logging
import uuid

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from backend.config import LOGS_DIR, MAX_OUTER_LOOPS, MAX_INNER_LOOPS, MODEL_STRONG, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PROMPTS_DIR
from backend.agents.llm import set_token_logger

from backend.agents.subagents.planner import planner_agent
from backend.agents.subagents.researcher import researcher_agent
from backend.agents.subagents.analyst import analyst_agent
from backend.agents.subagents.critic import critic_agent
from backend.agents.subagents.gate import gate_agent
from backend.agents.subagents.prd_writer import prd_writer_agent


# ── Module state (initialized fresh in each run()) ───────────────────────────
# run() 호출마다 초기화되는 전역 상태 (멀티 run 지원을 위해 run() 시작 시 리셋)
_logger: logging.Logger | None = None
_user_conditions: str = "" # 사용자 입력 조건
_loop_history: list = [] # 루프별 결과 누적
_prd_result: str = "" # 최종 PRD 텍스트
_outer: int = 1 # 외부 루프 카운터 (Gate)
_inner: int = 0 # 내부 루프 카운터 (Critic)
_current_topic: str = "" # 현재 진행 중인 주제


# ── Logger setup ──────────────────────────────────────────────────────────────

def _setup_logger(job_id: str) -> logging.Logger:
    # job_id별 로그 파일 + 콘솔 동시 출력 설정
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"run_{job_id}.log"

    logger = logging.getLogger(f"ideavault.{job_id}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False # 상위 루트 logger로 전파 방지

    fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


# ── Logging helpers ───────────────────────────────────────────────────────────

def _log_block(agent: str, inputs: dict, result: str) -> None:
    _logger.info(f"[{agent}] CALL | { {k: str(v)[:120] for k, v in inputs.items()} }")
    _logger.info(f"[{agent}] DONE | {result[:200].replace(chr(10), ' ')}")
    inp_block = "\n".join(f"  {k}: {v}" for k, v in inputs.items())
    _logger.info(
        f"\n{'─'*60}\n"
        f"[{agent}]\n\n"
        f"<입력>\n{inp_block}\n\n"
        f"<출력>\n{result}\n"
        f"{'─'*60}"
    )


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
async def tool_planner(
    mode: str,
    current_topic: str = "",
    gate_feedback: str = "",
    rejected_topics: list = None,
) -> str:
    """프로젝트 주제 발굴/정제/전환 에이전트.
    mode: INIT(처음 발굴) | REFINE(주제 유지 포인트 수정) | PIVOT(새 주제 발굴)"""
    global _current_topic
    inputs = dict(mode=mode, user_conditions=_user_conditions,
                  current_topic=current_topic, gate_feedback=gate_feedback,
                  rejected_topics=rejected_topics or [])
    result = await planner_agent(**inputs)
    _log_block("planner", inputs, result)
    _current_topic = result
    return result


@tool
async def tool_researcher(queries: list) -> str:
    """Tavily 외부 검색. LLM 없음.
    Planner EXTERNAL 항목 또는 Critic 보강 방향을 구체적인 검색 쿼리로 변환해서 전달."""
    result = researcher_agent(queries=queries)
    _log_block("researcher", {"queries": queries}, result)
    return result


@tool
async def tool_analyst(
    internal_points: str,
    researcher_result: str = "",
    critic_feedback: str = "",
) -> str:
    """사용자 조건 대비 프로젝트 적합성 분석.
    internal_points: Planner INTERNAL 항목 전체"""
    topic_desc = _current_topic.split("EXTERNAL:")[0].strip()
    inputs = dict(internal_points=internal_points, user_conditions=_user_conditions,
                  current_topic=topic_desc, researcher_result=researcher_result, critic_feedback=critic_feedback)
    result = await analyst_agent(**inputs)
    _log_block("analyst", inputs, result)
    return result


@tool
async def tool_critic(
    planner_result: str,
    researcher_result: str,
    analyst_result: str,
    previous_findings: str = "",
) -> str:
    """수집 정보 충분성 평가.
    방향: RESEARCHER / ANALYST / BOTH / GATE
    점수: feasibility / fit / clarity (0-10)
    previous_findings: tool_get_previous_findings 결과를 그대로 전달"""
    inputs = dict(planner_result=planner_result, researcher_result=researcher_result,
                  analyst_result=analyst_result, user_conditions=_user_conditions,
                  previous_findings=previous_findings)
    result = await critic_agent(**inputs)
    _log_block("critic", inputs, result)
    return result


@tool
async def tool_gate(critic_result: str, gate_decisions: str = "") -> str:
    """주제 계속 여부 심사.
    결정: REFINE(포인트 수정) | PIVOT(주제 전환) | DONE(완료)
    gate_decisions: tool_get_gate_decisions 결과를 그대로 전달"""
    inputs = dict(critic_result=critic_result, user_conditions=_user_conditions,
                  gate_decisions=gate_decisions)
    result = await gate_agent(**inputs)
    _log_block("gate", inputs, result)
    return result


@tool
async def tool_prd_writer() -> str:
    """최종 PRD 작성 (8섹션 마크다운). DONE 결정 후 호출."""
    global _prd_result
    inputs = dict(user_conditions=_user_conditions,
                  final_loop=json.dumps(_loop_history, ensure_ascii=False))
    result = await prd_writer_agent(**inputs)
    _log_block("prd_writer", inputs, result)
    _prd_result = result
    return result


@tool
def tool_update_loop_history(
    mode: str,
    summary: str = "",
    score: dict = None,
    gate_decision: str = "",
) -> str:
    """루프 결과 기록. 두 가지 모드:
    - critic: Critic 결과마다 호출. mode="critic", summary, score 전달
    - gate: Gate 결정 후 호출. mode="gate", gate_decision 전달"""
    global _inner, _outer

    entry = next((e for e in _loop_history if e["loop"] == _outer), None)
    if entry is None:
        entry = {"loop": _outer, "gate_decision": None, "critics": []}
        _loop_history.append(entry)

    if mode == "critic":
        _inner += 1
        entry["critics"].append({
            "inner": _inner,
            "summary": summary,
            "score": score or {},
        })
        _logger.info(f"[tool_update_loop_history] critic | loop={_outer} inner={_inner}")
        return f"Critic 기록 완료. 루프 {_outer}, inner {_inner}"

    elif mode == "gate":
        entry["gate_decision"] = gate_decision
        _logger.info(f"[tool_update_loop_history] gate | loop={_outer} decision={gate_decision}")
        msg = f"Gate 기록 완료. 루프 {_outer}, decision={gate_decision}. 누적 loops: {len(_loop_history)}"
        _outer += 1
        _inner = 0
        return msg

    return f"알 수 없는 mode: {mode}"


@tool
def tool_get_current_state() -> str:
    """현재 루프 진행 상태 반환. 언제든 호출 가능."""
    from backend.config import MAX_OUTER_LOOPS, MAX_INNER_LOOPS
    last_decision = ""
    if _loop_history:
        last_decision = _loop_history[-1].get("gate_decision") or "-"
    return (
        f"outer_loop: {_outer}/{MAX_OUTER_LOOPS}\n"
        f"inner_loop: {_inner}/{MAX_INNER_LOOPS}\n"
        f"current_topic: {_current_topic[:120]}\n"
        f"last_gate_decision: {last_decision}"
    )


@tool
def tool_get_loop_history() -> str:
    """저장된 loop_history 전체 리스트를 JSON으로 반환."""
    return json.dumps(_loop_history, ensure_ascii=False, indent=2)


@tool
def tool_get_previous_findings() -> str:
    """이전 루프들의 critics[].summary를 텍스트로 반환. tool_critic의 previous_findings에 그대로 전달."""
    if not _loop_history:
        return ""
    lines = []
    for entry in _loop_history:
        loop_num = entry.get("loop", "?")
        for critic in entry.get("critics", []):
            inner = critic.get("inner", "?")
            s = critic.get("summary", "")
            if s:
                lines.append(f"루프 {loop_num}, critic {inner}: {s}")
    return "\n".join(lines)


@tool
def tool_get_gate_decisions() -> str:
    """이전 루프들의 gate_decision만 추출해서 반환. tool_gate의 gate_decisions에 그대로 전달."""
    if not _loop_history:
        return ""
    lines = []
    for entry in _loop_history:
        loop_num = entry.get("loop", "?")
        decision = entry.get("gate_decision")
        if decision:
            lines.append(f"루프 {loop_num}: {decision}")
    return "\n".join(lines)


@tool
def check_loop_limit() -> str:
    """루프 한계 확인. Force일 경우 logging
    반환: CONTINUE / FORCE_GATE / FORCE_PRD"""
    global _inner

    if _outer >= MAX_OUTER_LOOPS:
        _logger.info(f"[check_loop_limit] FORCE_PRD | outer={_outer} inner={_inner}")
        return "FORCE_PRD"

    if _inner >= MAX_INNER_LOOPS:
        _inner = 0
        _logger.info(f"[check_loop_limit] FORCE_GATE | outer={_outer} inner={_inner}")
        return "FORCE_GATE"

    _logger.info(f"[check_loop_limit] CONTINUE | outer={_outer} inner={_inner}")
    return "CONTINUE"


# ── Main entry point ──────────────────────────────────────────────────────────

async def run(user_conditions: str, job_id: str | None = None) -> dict:
    """
    Run the full IdeaVault pipeline.

    Returns:
        {
          "job_id": str,
          "prd": str,
          "loop_history": list[dict]
        }
    """
    global _logger, _user_conditions, _loop_history, _prd_result, _outer, _inner, _current_topic

    # job_id 미전달 시 랜덤 8자리 생성
    if not job_id:
        job_id = uuid.uuid4().hex[:8]

    # 전역 상태 초기화 (이전 run 잔여값 제거)
    _logger = _setup_logger(job_id)
    set_token_logger(_logger)
    _user_conditions = user_conditions
    _loop_history = []
    _prd_result = ""
    _outer = 0
    _inner = 0
    _current_topic = ""

    _logger.info(f"[orchestrator] START | job_id={job_id}")

    # orchestrator.md 프롬프트에 사용자 조건 주입
    system_prompt = (
        (PROMPTS_DIR / "orchestrator.md")
        .read_text(encoding="utf-8")
        .replace("{user_conditions}", user_conditions)
    )

    # OpenRouter를 백엔드로 사용하는 LLM 인스턴스 생성
    llm = ChatOpenAI(
        model=MODEL_STRONG,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    # 오케스트레이터 에이전트 생성 및 전체 파이프라인 실행
    orchestrator = create_deep_agent(
        model=llm,
        tools=[
            tool_planner,
            tool_researcher,
            tool_analyst,
            tool_critic,
            tool_gate,
            tool_prd_writer,
            tool_update_loop_history,
            tool_get_current_state,
            tool_get_loop_history,
            tool_get_previous_findings,
            tool_get_gate_decisions,
            check_loop_limit,
        ],
        system_prompt=system_prompt,
        name="orchestrator",
    )
    
    # 오케스트레이터 실행
    await orchestrator.ainvoke({"messages": [HumanMessage(user_conditions)]})

    _logger.info(f"[orchestrator] END | prd_length={len(_prd_result)} loops={len(_loop_history)}")
    return {"job_id": job_id, "prd": _prd_result, "loop_history": _loop_history}