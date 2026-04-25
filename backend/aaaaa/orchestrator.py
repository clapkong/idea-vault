"""
Orchestrator — deepagents LLM agent that reads orchestrator.md and calls tools.
Pattern mirrors the user's create_deep_agent + @tool structure.
"""
import json
import logging
import re
import uuid
from typing import Callable

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from backend.config import LOGS_DIR, MODEL_STRONG, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PROMPTS_DIR
from aaaaa.llm import set_usage_callback

from aaaaa.agents.planner import planner_agent 
from aaaaa.agents.researcher import researcher_agent
from aaaaa.agents.analyst import analyst_agent
from aaaaa.agents.critic import critic_agent
from aaaaa.agents.gate import gate_agent
from aaaaa.agents.prd_writer import prd_writer_agent
from aaaaa.utils import check_loop_limit as _check_limit_fn


# ── Module state (initialized fresh in each run()) ───────────────────────────

_logger: logging.Logger | None = None
_user_conditions: str = ""
_loop_history: list = []
_prd_result: str = ""
_outer: int = 1
_inner: int = 0
_last_critic_result: str = ""
_current_topic: str = ""


# ── Logger setup ──────────────────────────────────────────────────────────────

def _setup_logger(job_id: str) -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"run_{job_id}.log"

    logger = logging.getLogger(f"ideavault.{job_id}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


# ── Wrapped tool call with logging ────────────────────────────────────────────

def _call(logger: logging.Logger, agent: str, fn: Callable, **kwargs) -> str:
    logger.info(f"[{agent}] CALL | { {k: str(v)[:120] for k, v in kwargs.items()} }")
    try:
        result: str = fn(**kwargs)
    except Exception as exc:
        logger.error(f"[{agent}] ERROR | {type(exc).__name__}: {exc}")
        raise

    logger.info(f"[{agent}] DONE | {str(result)[:200].replace(chr(10), ' ')}")

    inp_block = "\n".join(f"  {k}: {v}" for k, v in kwargs.items())
    logger.info(
        f"\n{'─'*60}\n"
        f"[{agent}]\n\n"
        f"<입력>\n{inp_block}\n\n"
        f"<출력>\n{result}\n"
        f"{'─'*60}"
    )

    return result


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
async def tool_planner(
    mode: str,
    current_topic: str = "",
    critic_feedback: str = "",
    rejected_topics: list = None,
) -> str:
    """프로젝트 주제 발굴/정제/전환 에이전트.
    mode: INIT(처음 발굴) | REFINE(주제 유지 포인트 수정) | PIVOT(새 주제 발굴)"""
    global _current_topic
    result = _call(_logger, "planner", planner_agent,
                   mode=mode,
                   user_conditions=_user_conditions,
                   current_topic=current_topic,
                   critic_feedback=critic_feedback,
                   rejected_topics=rejected_topics or [])
    _current_topic = result
    return result


@tool
async def tool_researcher(queries: list) -> str:
    """Tavily 외부 검색. LLM 없음.
    Planner EXTERNAL 항목 또는 Critic 보강 방향을 구체적인 검색 쿼리로 변환해서 전달."""
    return _call(_logger, "researcher", researcher_agent, queries=queries)


@tool
async def tool_analyst(
    internal_points: str,
    researcher_result: str = "",
    critic_feedback: str = "",
) -> str:
    """사용자 조건 대비 프로젝트 적합성 분석.
    internal_points: Planner INTERNAL 항목 전체"""
    return _call(_logger, "analyst", analyst_agent,
                 internal_points=internal_points,
                 user_conditions=_user_conditions,
                 researcher_result=researcher_result,
                 critic_feedback=critic_feedback)


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
    global _last_critic_result
    result = _call(_logger, "critic", critic_agent,
                   planner_result=planner_result,
                   researcher_result=researcher_result,
                   analyst_result=analyst_result,
                   user_conditions=_user_conditions,
                   previous_findings=previous_findings)
    _last_critic_result = result
    return result


@tool
async def tool_gate(critic_result: str, gate_decisions: str = "") -> str:
    """주제 계속 여부 심사.
    결정: REFINE(포인트 수정) | PIVOT(주제 전환) | DONE(완료)
    gate_decisions: tool_get_gate_decisions 결과를 그대로 전달"""
    return _call(_logger, "gate", gate_agent,
                 critic_result=critic_result,
                 user_conditions=_user_conditions,
                 gate_decisions=gate_decisions)


@tool
async def tool_prd_writer() -> str:
    """최종 PRD 작성 (8섹션 마크다운). DONE 결정 후 호출."""
    global _prd_result
    result = _call(_logger, "prd_writer", prd_writer_agent,
                   user_conditions=_user_conditions,
                   final_loop=json.dumps(_loop_history, ensure_ascii=False))
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
    """루프 한계 확인. 한계 초과 시 강제 실행 후 결과 반환.
    반환: CONTINUE / FORCE_GATE 처리 완료 (Gate 결정 포함) / FORCE_PRD 처리 완료"""
    global _outer, _inner, _prd_result

    status = _check_limit_fn(_outer, _inner)
    _logger.info(f"[check_loop_limit] outer={_outer} inner={_inner} → {status}")

    if status == "FORCE_GATE":
        gate_decisions = "\n".join(
            f"루프 {e['loop']}: {e['gate_decision']}"
            for e in _loop_history if e.get("gate_decision")
        )
        gate_result = _call(_logger, "gate(forced)", gate_agent,
                            critic_result=_last_critic_result,
                            user_conditions=_user_conditions,
                            gate_decisions=gate_decisions)
        m = re.search(r"결정:\s*(REFINE|PIVOT|DONE)", gate_result)
        decision = m.group(1) if m else "PIVOT"

        entry = next((e for e in _loop_history if e["loop"] == _outer), None)
        if entry is None:
            entry = {"loop": _outer, "gate_decision": None, "critics": []}
            _loop_history.append(entry)
        entry["gate_decision"] = decision
        _outer += 1
        _inner = 0
        _logger.info(f"[check_loop_limit] FORCE_GATE 완료 | decision={decision}")
        return f"FORCE_GATE 처리 완료 | Gate 결정: {decision}\n{gate_result}"

    if status == "FORCE_PRD":
        prd = _call(_logger, "prd_writer(forced)", prd_writer_agent,
                    user_conditions=_user_conditions,
                    final_loop=json.dumps(_loop_history, ensure_ascii=False))
        _prd_result = prd
        _logger.info("[check_loop_limit] FORCE_PRD 완료")
        return "FORCE_PRD 처리 완료 | PRD 작성 완료"

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
    global _logger, _user_conditions, _loop_history, _prd_result, _outer, _inner, _last_critic_result, _current_topic

    if not job_id:
        job_id = uuid.uuid4().hex[:8]

    _logger = _setup_logger(job_id)
    _user_conditions = user_conditions
    _loop_history = []
    _prd_result = ""
    _outer = 1
    _inner = 0
    _last_critic_result = ""
    _current_topic = ""

    _logger.info(f"[orchestrator] START | job_id={job_id}")

    set_usage_callback(
        lambda model, prompt, completion, total:
            _logger.info(f"[tokens] {model} | prompt={prompt} completion={completion} total={total}")
    )

    system_prompt = (
        (PROMPTS_DIR / "orchestrator.md")
        .read_text(encoding="utf-8")
        .replace("{user_conditions}", user_conditions)
    )

    llm = ChatOpenAI(
        model=MODEL_STRONG,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

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

    await orchestrator.ainvoke({"messages": [HumanMessage(user_conditions)]})

    _logger.info(f"[orchestrator] END | prd_length={len(_prd_result)} loops={len(_loop_history)}")
    return {"job_id": job_id, "prd": _prd_result, "loop_history": _loop_history}
