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
from backend.agents.llm import set_usage_callback

from backend.agents.subagents.planner import planner_agent
from backend.agents.subagents.researcher import researcher_agent
from backend.agents.subagents.analyst import analyst_agent
from backend.agents.subagents.critic import critic_agent
from backend.agents.subagents.gate import gate_agent
from backend.agents.subagents.prd_writer import prd_writer_agent
from backend.agents.utils import check_loop_limit as _check_limit_fn


# ── Module state (initialized fresh in each run()) ───────────────────────────
# run() 호출마다 초기화되는 전역 상태 (멀티 run 지원을 위해 run() 시작 시 리셋)
_logger: logging.Logger | None = None
_user_conditions: str = "" # 사용자 입력 조건
_loop_history: list = [] # 루프별 결과 누적
_prd_result: str = ""  # 최종 PRD 텍스트
_outer: int = 1 # 외부 루프 카운터 (Gate)
_inner: int = 0 # 내부 루프 카운터 (Critic)
_last_critic_result: str = "" # FORCE_GATE 시 재사용할 마지막 Critic 결과
_current_topic: str = "" # 현재 진행 중인 주제


# ── Logger setup ──────────────────────────────────────────────────────────────

def _setup_logger(job_id: str) -> logging.Logger:
    # job_id별 로그 파일 + 콘솔 동시 출력 설정
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"run_{job_id}.log"

    logger = logging.getLogger(f"ideavault.{job_id}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # 상위 루트 logger로 전파 방지

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
    # 에이전트 호출을 래핑해 입출력 로깅 및 에러 처리를 일원화
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
) -> str:
    """수집 정보 충분성 평가.
    방향: RESEARCHER / ANALYST / BOTH / GATE
    점수: feasibility / fit / clarity (0-10)"""
    global _last_critic_result, _inner
    result = _call(_logger, "critic", critic_agent,
                   planner_result=planner_result,
                   researcher_result=researcher_result,
                   analyst_result=analyst_result,
                   user_conditions=_user_conditions)
    _last_critic_result = result
    _inner += 1
    return result


@tool
async def tool_gate(critic_result: str) -> str:
    """주제 계속 여부 심사.
    결정: REFINE(포인트 수정) | PIVOT(주제 전환) | DONE(완료)"""
    return _call(_logger, "gate", gate_agent,
                 critic_result=critic_result,
                 user_conditions=_user_conditions)


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
    topic: str,
    score: dict,
    gate_decision: str,
    agent_summaries: str = "",
) -> str:
    """Gate 결정 후 루프 결과 기록.
    전달: topic, 최종 score (마지막 Critic 결과), gate 결정, 각 에이전트 요약본"""
    global _outer, _inner

    entry = {
        "loop": _outer,
        "topic": topic,
        "score": score or {},
        "gate_decision": gate_decision,
        "agent_summaries": agent_summaries,
    }
    _loop_history.append(entry)
    _logger.info(f"[tool_update_loop_history] loop={_outer} decision={gate_decision}")
    msg = f"루프 {_outer} 기록 완료. decision={gate_decision}. 누적 loops: {len(_loop_history)}"
    _outer += 1
    _inner = 0
    return msg



@tool
def check_loop_limit() -> str:
    """루프 한계 확인. 한계 초과 시 강제 실행 후 결과 반환.
    반환: CONTINUE / FORCE_GATE 처리 완료 (Gate 결정 포함) / FORCE_PRD 처리 완료"""
    global _outer, _inner, _prd_result

    status = _check_limit_fn(_outer, _inner)
    _logger.info(f"[check_loop_limit] outer={_outer} inner={_inner} → {status}")

    if status == "FORCE_GATE":
        # 내부 루프 한계 도달 → Gate를 강제 실행해 주제 계속 여부 결정
        gate_result = _call(_logger, "gate(forced)", gate_agent,
                            critic_result=_last_critic_result,
                            user_conditions=_user_conditions)
        m = re.search(r"결정:\s*(REFINE|PIVOT|DONE)", gate_result)
        decision = m.group(1) if m else "PIVOT"  # 파싱 실패 시 PIVOT으로 안전하게 처리

        _loop_history.append({"loop": _outer, "gate_decision": decision})
        _outer += 1
        _inner = 0
        _logger.info(f"[check_loop_limit] FORCE_GATE 완료 | decision={decision}")
        return f"FORCE_GATE 처리 완료 | Gate 결정: {decision}\n{gate_result}"

    if status == "FORCE_PRD":
        # 외부 루프 한계 도달 → PRD를 강제 작성하고 종료
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

    # job_id 미전달 시 랜덤 8자리 생성
    if not job_id:
        job_id = uuid.uuid4().hex[:8]

    # 전역 상태 초기화 (이전 run 잔여값 제거)
    _logger = _setup_logger(job_id)
    _user_conditions = user_conditions
    _loop_history = []
    _prd_result = ""
    _outer = 1
    _inner = 0
    _last_critic_result = ""
    _current_topic = ""

    _logger.info(f"[orchestrator] START | job_id={job_id}")

    # 토큰 사용량을 로그 파일에 기록하는 콜백 등록
    set_usage_callback(
        lambda model, prompt, completion, total:
            _logger.info(f"[tokens] {model} | prompt={prompt} completion={completion} total={total}")
    )

    # orchestrator.md 프롬프트에 사용자 조건 주입
    system_prompt = (
        (PROMPTS_DIR / "orchestrator.md")
        .read_text(encoding="utf-8")
        .replace("{user_conditions}", user_conditions)
        .replace("{current_state}", "없음")
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
            check_loop_limit,
        ],
        system_prompt=system_prompt,
        name="orchestrator",
    )

    await orchestrator.ainvoke({"messages": [HumanMessage(user_conditions)]})

    _logger.info(f"[orchestrator] END | prd_length={len(_prd_result)} loops={len(_loop_history)}")
    return {"job_id": job_id, "prd": _prd_result, "loop_history": _loop_history}
