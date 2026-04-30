"""
Orchestrator — deepagents LLM agent that reads orchestrator.md and calls tools.
Pattern mirrors the user's create_deep_agent + @tool structure.
"""
import asyncio
import json
import uuid
from datetime import datetime

from deepagents import create_deep_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from config import (
    MAX_OUTER_LOOPS, MAX_INNER_LOOPS,
    MODEL_STRONG, MODEL_LIGHT,
    PROMPTS_DIR,
)
from agents.llm import log_line, log_block, create_llm
from agents.subagents.planner import planner_agent
from agents.subagents.researcher import researcher_agent
from agents.subagents.analyst import analyst_agent
from agents.subagents.critic import critic_agent
from agents.subagents.gate import gate_agent
from agents.subagents.prd_writer import prd_writer_agent


# ── Module state (initialized fresh in each run()) ───────────────────────────
# @tool 함수들은 인자를 LLM이 결정하므로 job별 공유 상태를 인자로 넘길 수 없음.
# 대신 모듈 전역 변수로 두고 run() 시작 시 초기화. job이 순차 실행되는 한 안전.
_event_queue: asyncio.Queue | None = None  # SSE 브릿지 (None이면 CLI 모드)
_events: list = []                         # 전체 이벤트 수집 (run() 반환용)
_user_conditions: str = ""                 # 사용자 입력 조건
_loop_history: list = []                   # 루프별 결과 누적
_prd_result: str = ""                      # 최종 PRD 텍스트
_outer: int = 0                            # 외부 루프 카운터 (Gate)
_inner: int = 0                            # 내부 루프 카운터 (Critic)
_current_topic: str = ""                   # 현재 진행 중인 주제


# ── Event emission ────────────────────────────────────────────────────────────

# SSE 이벤트 큐 + 내부 수집 리스트에 동시 추가
async def _emit(event: dict) -> None:
    _events.append(event)
    if _event_queue is not None:
        await _event_queue.put(event)


# ── Tools ─────────────────────────────────────────────────────────────────────
# @tool: LangChain 데코레이터. 함수를 LLM이 호출할 수 있는 도구로 등록.
# LLM이 어떤 툴을 언제 어떤 인자로 부를지 스스로 판단해서 실행함 (함수 시그니처와 docstring 기반).

# planner_agent 호출 후 결과를 _current_topic에 저장
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
    await _emit({"type": "agent_start", "agent": "planner", "timestamp": datetime.now().strftime("%H:%M:%S")})
    await _emit({"type": "agent_progress", "agent": "planner"})
    inputs = dict(mode=mode, user_conditions=_user_conditions,
                  current_topic=current_topic, gate_feedback=gate_feedback,
                  rejected_topics=rejected_topics or [])
    log_line("[planner] CALL")
    result, tokens = await planner_agent(**inputs)
    _current_topic = result
    await _emit({"type": "agent_done", "agent": "planner", "output": result, "tokens": tokens, "model": MODEL_STRONG, "timestamp": datetime.now().strftime("%H:%M:%S")})
    return result


# Tavily 검색 실행 — researcher_agent는 sync이므로 await 없이 직접 호출
@tool
async def tool_researcher(queries: list) -> str:
    """Tavily 외부 검색. LLM 없음.
    Planner EXTERNAL 항목 또는 Critic 보강 방향을 구체적인 검색 쿼리로 변환해서 전달."""
    await _emit({"type": "agent_start", "agent": "researcher", "timestamp": datetime.now().strftime("%H:%M:%S")})
    await _emit({"type": "agent_progress", "agent": "researcher"})
    log_line("[researcher] CALL")
    result = researcher_agent(queries=queries)
    log_line(f"[researcher] DONE | {result[:200]}")
    log_line()
    log_block("researcher", "queries:\n" + "\n".join(f"  - {q}" for q in queries), result)
    await _emit({"type": "agent_done", "agent": "researcher", "output": result, "tokens": 0, "model": None, "timestamp": datetime.now().strftime("%H:%M:%S")})
    return result


# _current_topic에서 TOPIC+DESCRIPTION만 추출해 analyst context로 주입
@tool
async def tool_analyst(
    internal_points: str,
    researcher_result: str = "",
    critic_feedback: str = "",
) -> str:
    """사용자 조건 대비 프로젝트 적합성 분석.
    internal_points: Planner INTERNAL 항목 전체"""
    await _emit({"type": "agent_start", "agent": "analyst", "timestamp": datetime.now().strftime("%H:%M:%S")})
    await _emit({"type": "agent_progress", "agent": "analyst"})
    topic_desc = _current_topic.split("EXTERNAL:")[0].strip()
    inputs = dict(internal_points=internal_points, user_conditions=_user_conditions,
                  current_topic=topic_desc, researcher_result=researcher_result, critic_feedback=critic_feedback)
    log_line("[analyst] CALL")
    result, tokens = await analyst_agent(**inputs)
    await _emit({"type": "agent_done", "agent": "analyst", "output": result, "tokens": tokens, "model": MODEL_LIGHT, "timestamp": datetime.now().strftime("%H:%M:%S")})
    return result


# 수집 정보 충분성 평가 — 다음 방향(RESEARCHER/ANALYST/BOTH/GATE)과 점수 반환
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
    await _emit({"type": "agent_start", "agent": "critic", "timestamp": datetime.now().strftime("%H:%M:%S")})
    await _emit({"type": "agent_progress", "agent": "critic"})
    inputs = dict(planner_result=planner_result, researcher_result=researcher_result,
                  analyst_result=analyst_result, user_conditions=_user_conditions,
                  previous_findings=previous_findings)
    log_line("[critic] CALL")
    result, tokens = await critic_agent(**inputs)
    await _emit({"type": "agent_done", "agent": "critic", "output": result, "tokens": tokens, "model": MODEL_STRONG, "timestamp": datetime.now().strftime("%H:%M:%S")})
    return result


# critic 결과를 받아 REFINE/PIVOT/DONE 결정
@tool
async def tool_gate(critic_result: str, gate_decisions: str = "") -> str:
    """주제 계속 여부 심사.
    결정: REFINE(포인트 수정) | PIVOT(주제 전환) | DONE(완료)
    gate_decisions: tool_get_gate_decisions 결과를 그대로 전달"""
    await _emit({"type": "agent_start", "agent": "gate", "timestamp": datetime.now().strftime("%H:%M:%S")})
    await _emit({"type": "agent_progress", "agent": "gate"})
    inputs = dict(critic_result=critic_result, user_conditions=_user_conditions,
                  gate_decisions=gate_decisions)
    log_line("[gate] CALL")
    result, tokens = await gate_agent(**inputs)
    await _emit({"type": "agent_done", "agent": "gate", "output": result, "tokens": tokens, "model": MODEL_LIGHT, "timestamp": datetime.now().strftime("%H:%M:%S")})
    return result


# loop_history 전체를 JSON 직렬화해 prd_writer에 전달, 결과를 _prd_result에 저장
@tool
async def tool_prd_writer() -> str:
    """최종 PRD 작성 (8섹션 마크다운). DONE 결정 후 호출."""
    global _prd_result
    await _emit({"type": "agent_start", "agent": "prd_writer", "timestamp": datetime.now().strftime("%H:%M:%S")})
    await _emit({"type": "agent_progress", "agent": "prd_writer"})
    log_line("[prd_writer] CALL")
    inputs = dict(user_conditions=_user_conditions,
                  final_loop=json.dumps(_loop_history, ensure_ascii=False))
    result, tokens = await prd_writer_agent(**inputs)
    _prd_result = result
    await _emit({"type": "agent_done", "agent": "prd_writer", "output": result, "tokens": tokens, "model": MODEL_STRONG, "timestamp": datetime.now().strftime("%H:%M:%S")})
    return result


# critic 결과 또는 gate 결정을 현재 outer 루프 항목에 기록
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

    # 현재 outer 루프 항목 조회 — 없으면 신규 생성
    entry = next((e for e in _loop_history if e["loop"] == _outer), None)
    if entry is None:
        entry = {"loop": _outer, "gate_decision": None, "critics": []}
        _loop_history.append(entry)

    # critic 모드: inner 카운터 증가 후 요약·점수 기록
    if mode == "critic":
        _inner += 1
        entry["critics"].append({
            "inner": _inner,
            "summary": summary,
            "score": score or {},
        })
        log_line(f"[tool_update_loop_history] critic | loop={_outer} inner={_inner}")
        return f"Critic 기록 완료. 루프 {_outer}, inner {_inner}"

    # gate 모드: 결정 저장 후 outer 증가·inner 리셋
    elif mode == "gate":
        entry["gate_decision"] = gate_decision
        msg = f"Gate 기록 완료. 루프 {_outer}, decision={gate_decision}. 누적 loops: {len(_loop_history)}"
        log_line(f"[tool_update_loop_history] gate | loop={_outer} decision={gate_decision}")
        _outer += 1
        _inner = 0
        return msg

    return f"알 수 없는 mode: {mode}"


# 현재 루프 카운터·주제·마지막 gate 결정을 텍스트로 반환
@tool
def tool_get_current_state() -> str:
    """현재 루프 진행 상태 반환. 언제든 호출 가능."""
    last_decision = ""
    if _loop_history:
        last_decision = _loop_history[-1].get("gate_decision") or "-"
    return (
        f"outer_loop: {_outer}/{MAX_OUTER_LOOPS}\n"
        f"inner_loop: {_inner}/{MAX_INNER_LOOPS}\n"
        f"current_topic: {_current_topic[:120]}\n"
        f"last_gate_decision: {last_decision}"
    )


# 전체 loop_history를 JSON으로 반환
@tool
def tool_get_loop_history() -> str:
    """저장된 loop_history 전체 리스트를 JSON으로 반환."""
    return json.dumps(_loop_history, ensure_ascii=False, indent=2)


# 이전 루프들의 critic 요약을 하나의 텍스트로 병합해 반환
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


# 이전 루프들의 gate 결정만 추출해 텍스트로 반환
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


# outer/inner 카운터 확인 → CONTINUE / FORCE_GATE / FORCE_PRD
@tool
def check_loop_limit() -> str:
    """루프 한계 확인. Force일 경우 logging
    반환: CONTINUE / FORCE_GATE / FORCE_PRD"""
    global _inner

    if _outer >= MAX_OUTER_LOOPS:
        log_line(f"[check_loop_limit] outer={_outer} inner={_inner} → FORCE_PRD")
        return "FORCE_PRD"

    if _inner >= MAX_INNER_LOOPS:
        log_line(f"[check_loop_limit] outer={_outer} inner={_inner} → FORCE_GATE")
        _inner = 0
        return "FORCE_GATE"

    log_line(f"[check_loop_limit] outer={_outer} inner={_inner} → CONTINUE")
    return "CONTINUE"


# ── Main entry point ──────────────────────────────────────────────────────────

# IdeaVault 전체 파이프라인 실행 진입점 — event_queue가 있으면 SSE 브릿지, 없으면 CLI 모드
async def run(
    user_conditions: str,
    job_id: str | None = None,
    event_queue: asyncio.Queue | None = None,
) -> dict:
    """
    Run the full IdeaVault pipeline.

    Returns:
        {
          "job_id": str,
          "prd": str,
          "loop_history": list[dict],
          "events": list[dict],
        }
    """
    global _event_queue, _events, _user_conditions, _loop_history, _prd_result, _outer, _inner, _current_topic

    if not job_id:
        job_id = uuid.uuid4().hex[:8]

    _event_queue = event_queue
    _events = []
    _user_conditions = user_conditions
    _loop_history = []
    _prd_result = ""
    _outer = 0
    _inner = 0
    _current_topic = ""

    log_line(f"[orchestrator] START | job_id={job_id}")

    system_prompt = (
        (PROMPTS_DIR / "orchestrator.md")
        .read_text(encoding="utf-8")
        .replace("{user_conditions}", user_conditions)
    )

    llm = create_llm(MODEL_STRONG)
    
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

    return {
        "job_id": job_id,
        "prd": _prd_result,
        "loop_history": _loop_history,
        "events": _events,
    }
