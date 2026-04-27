
backend/agents

기획: 클로드 세션
에이전트가 사용할 prompt를 claude와 상의하면서 prompt optimization 진행. 
해당 세션에서 prompt 설명 및 프로젝트 요약문 간단하게 부탁 -> {prompt 설명} {프로젝트 및 에이전트 흐름 구조 설명}

코드: 클로드 코드
{prompt 설명} {프로젝트 및 에이전트 흐름 구조 설명}을 구현하고 싶어. 프롬프트는 미리 생성해두었고, /backend/agents/prompts에 있어. 
이 때, 파일이 많은 /venv, __pycache__와 중요한 키가 있는 .env는 .claudeignore에 사전 정의하여 참조하지 않도록 하였다. 

직접 수정한 사항: 
클로드 코드는 전반적으로 이 부분에서 코드를 잘 작성해주었다. 실행 시 오류가 있을 부분을
그러나 한 가지 단점이 있었다면 수정사항이 생길 때 기존 작성되어 있는 코드의 삭제를 최소화 하는 경향을 보였다.  
새 방식으로 인해 기존 코드가 크게 필요하지 않아졌더라도 계속 덧대는 방식을 고수하였다. 


검수: .log로 각 에이전트 별 결과물 검수. 보통 서브에이전트 프롬프트의 문제가 많았음. -> 클로드와 

{Prompt 수정 사항} 서브에이전트 {agent}의 {agent}.md를 {이전}에서 {이후}로 변경했어. 여기에 맞게 코드를 수정해줘. 

---
backend/

---

## 2026-04-27 — 서브에이전트 create_deep_agent 패턴 전환

**작업 내용**

`llm.py` 재구성
- 제거: `call_llm()`, `_get_client()`, `_client`, `set_usage_callback()`, `_usage_callback`, OpenAI 직접 import, `Callable` import
- 추가: `create_llm(model, max_tokens)` — ChatOpenAI 인스턴스 반환
- 추가: `load_prompt(agent_name)` — 프롬프트 .md 파일 로드
- 추가: `extract_content(result)` — `ainvoke` 결과에서 텍스트 추출 (기존 `_extract_content`를 public으로 전환)

서브에이전트 5개 (critic, analyst, planner, gate, prd_writer) 전환
- 모듈 레벨에서 `_*_subagent = create_deep_agent(model=create_llm(...), tools=[], system_prompt=load_prompt(...))` 생성
- 각 함수: `await _*_subagent.ainvoke({"messages": [HumanMessage(user_message)]})` 후 `extract_content()` 반환
- `analyst.py`: `**kwargs` → 명시적 파라미터 (`researcher_result: str = "없음"`, `critic_feedback: str = "없음"`)
- `planner.py`: 프롬프트 내 `{critic_feedback}` 버그 → `gate_feedback`으로 수정

프롬프트 `.md` 5개 수정
- system_prompt에는 역할 정의만 유지
- `{user_conditions}` 등 데이터 섹션 변수 제거 (데이터는 HumanMessage로 전달)

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/subagents/analyst.py`
- `backend/agents/subagents/critic.py`
- `backend/agents/subagents/planner.py`
- `backend/agents/subagents/gate.py`
- `backend/agents/subagents/prd_writer.py`
- `backend/agents/prompts/analyst.md`
- `backend/agents/prompts/critic.md`
- `backend/agents/prompts/planner.md`
- `backend/agents/prompts/gate.md`
- `backend/agents/prompts/prd_writer.md`

**프롬프트**
- "서브에이전트 5개를 create_deep_agent 패턴으로 리팩토링해줘. 역할 정의는 system_prompt에, 데이터는 HumanMessage로 분리하고, ainvoke 결과는 extract_content()로 추출해줘."
- "extract_content가 왜 private(_extract_content)으로 되어 있어? 외부에서 참조하는데. 그리고 create_deep_agent에는 모델 문자열이 아니라 ChatOpenAI 객체가 필요한 거 아니었어? create_llm의 역할을 설명해줘."
- "리팩토링 후 기능이 이전과 동일하게 유지되고 있는지 확인해줘."

**발견된 문제점**
- `extract_content`가 `_extract_content`로 잘못 명명됨 — 5개 서브에이전트에서 외부 참조하는 함수임에도 private 처리
- 데이터 섹션을 HumanMessage로 이동하는 과정에서 시스템 프롬프트에 입력 구조 안내가 사라짐 → LLM이 어떤 형식으로 입력을 받는지 인지하지 못하는 문제
- `analyst.py`의 선택 파라미터(`researcher_result`, `critic_feedback`) 처리 방식이 orchestrator 프롬프트에 명시되지 않아, orchestrator LLM이 필수 인자처럼 취급할 가능성
- 토큰 로깅이 없는 채로 유지됨

---

## 2026-04-27 — orchestrator.py 정리 및 버그픽스

**작업 내용**

`orchestrator.py` 정리
- 제거: `_call()` 래퍼 함수, `import re`, `_last_critic_result` 전역 변수 (FORCE_GATE 시 orchestrator 컨텍스트에 이미 보존됨), `from backend.agents.utils import check_loop_limit`
- 추가: `_log_block(agent, inputs, result)` — CALL/DONE 한 줄 + 블록 포맷 로그 통합
- 추가: `inputs = dict(...)` 패턴 — 각 툴에서 로그 입력 재사용
- `check_loop_limit` 툴 orchestrator에 인라인 (CONTINUE / FORCE_GATE / FORCE_PRD)
  - 로그 포맷: `FLAG | outer=X inner=Y` 순서로 확정

`utils.py` 삭제
- `check_loop_limit` 로직 orchestrator로 인라인

토큰 로깅 시도 및 제거
- `_TokenHandler(BaseCallbackHandler)` 추가 후 제거
- 사유: FastAPI 전환 시 데이터 전송 위주로 재설계 예정이므로 이후 정리

`tool_get_last_critic_result` 추가 후 제거
- FORCE_GATE 대응용으로 추가했으나 orchestrator LLM 컨텍스트에 이전 critic 결과가 이미 보존되어 불필요

**수정/삭제된 파일**
- `backend/agents/orchestrator.py`
- `backend/agents/utils.py` (삭제)

**프롬프트**
- "래핑 계층이 너무 중첩되어 있어. _call 래퍼를 포함해서 불필요한 계층 전부 제거하고 단순하게 정리해줘."
- "llm.py와 orchestrator.py의 각 함수가 실제로 필요한지 존재 이유를 검토해줘."
- "utils.py의 check_loop_limit 로직을 orchestrator로 인라인해서 파일을 합쳐줘."
- "check_loop_limit 로그 포맷 수정 — outer/inner 카운트가 누락됐어. 플래그 먼저, 그 다음 outer=X inner=Y 순서로 출력해줘."
- "_last_critic_result를 제거한 이유가 있어? FORCE_GATE 시 이전에는 잘 전달되고 있었는데. 제거해도 문제없는지 확인해줘."
- "tool_get_last_critic_result는 이전에도 없었고 잘 작동했었어. 제거해줘."

**발견된 문제점**
- 실행 로그 분석 결과, orchestrator LLM이 `tool_analyst` 호출 시 `researcher_result`를 비워서 전달하는 패턴 확인 — 선택 파라미터임이 프롬프트에 명시되지 않아 발생
- researcher → analyst 전달을 명시하면 병렬 실행 원칙과 충돌 — 두 에이전트는 독립적으로 동작해야 하며, 결과 통합은 critic 단계에서 이루어짐
- 토큰 로깅 부재로 실행 비용 추적 불가
- 시스템 프롬프트에 입력 구조 안내가 없어 LLM이 어떤 섹션을 받는지, (선택) 항목이 없을 때 어떻게 동작해야 하는지 불명확

---

## 2026-04-27 — 후속 수정 및 프롬프트 보강

**작업 내용**

토큰 로깅 복원 (`llm.py`, `orchestrator.py`)
- `_TokenHandler(BaseCallbackHandler)` 추가 — `on_llm_end`에서 `response.llm_output["token_usage"]` 파싱, prompt/completion/total 로깅
- `set_token_logger(logger)` 추가 — 전역 `_token_logger`에 job별 logger 주입
- `create_llm()` 에 `callbacks=[_handler]` 연결 (모듈 로드 시 handler 바인딩, logger는 run() 시점에 주입)
- `orchestrator.py` `run()` 시작 시 `set_token_logger(_logger)` 호출 추가

`orchestrator.md` 수정
- `tool_analyst`의 `researcher_result`, `critic_feedback`는 선택 파라미터이며 병렬 호출 시 생략 가능하다고 명시
- (researcher → analyst 전달 명시 라인 추가 후 롤백 — 병렬 실행 원칙과 충돌)

프롬프트 `.md` 5개에 `## 입력 형식` 섹션 추가
- 각 에이전트가 받을 입력 항목과 (선택) 여부 목록화
- `## 규칙`에 "(선택) 항목이 없거나 비어 있으면 해당 정보 없이 판단할 것" 추가
- 사유: 원래 프롬프트 최상단에 있던 입력 데이터 섹션이 HumanMessage로 이동하면서 LLM이 입력 구조를 인지하지 못하는 문제 보완

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/orchestrator.py`
- `backend/agents/prompts/orchestrator.md`
- `backend/agents/prompts/analyst.md`
- `backend/agents/prompts/critic.md`
- `backend/agents/prompts/planner.md`
- `backend/agents/prompts/gate.md`
- `backend/agents/prompts/prd_writer.md`

**프롬프트**
- "이전 방식처럼 토큰 로깅을 복원해줘. 각 LLM 호출마다 토큰 수를 job별 logger에 기록하도록 연결해줘."
- "tool_analyst의 researcher_result, critic_feedback가 필수 인자처럼 처리되고 있는 것 같아. 선택 파라미터임을 orchestrator 프롬프트에 명시하고, 없을 경우 생략 가능하다고 해줘."
- "researcher → analyst 결과 전달 명시는 병렬 실행 원칙과 충돌해. 해당 라인 롤백해줘."
- "출력 형식 섹션이 있는 것처럼 입력 형식 섹션도 각 프롬프트에 추가해줘. (선택) 항목은 없어도 처리 가능하다는 규칙도 함께 명시해줘."

---

## 2026-04-27 — 서브에이전트 vanilla LLM 전환 및 analyst 맥락 보강

**작업 내용**

서브에이전트 5개 `create_deep_agent` → `ChatOpenAI` 직접 호출로 전환
- `_agent.ainvoke({"messages": [HumanMessage(...)]})` → `_llm.ainvoke([SystemMessage(_prompt), HumanMessage(...)])`
- `llm.py` `extract_content`: dict 접근 (`result["messages"][-1].content`) → AIMessage 직접 접근 (`result.content`)
- `llm.py`에 전환 이유 한 줄 주석으로 기록

`analyst`에 현재 주제 맥락 주입
- `analyst_agent()` 시그니처에 `current_topic: str = ""` 추가
- `orchestrator.py` `tool_analyst`에서 `_current_topic` 전달
- planner 전체 결과 대신 TOPIC + DESCRIPTION만 잘라서 전달 (`EXTERNAL:` 이전 텍스트만 추출)
- `analyst.md` 입력 형식에 `현재 주제 (선택)` 추가

`create_deep_agent` 실험 및 원인 확인
- 로그 비교 (ed3d518c vanilla vs e0d224ae deepagent)
- 동일 입력 조건에서 deepagent만 빈 출력 재현 — `researcher_result` 없는 초기 호출, PIVOT 후 재호출 시
- 원인: create_deep_agent 내부 미들웨어가 선택 파라미터 빈 값 처리 시 응답 생성 포기
- vanilla LLM 최종 확정, 코드에 흔적 없이 정리

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/orchestrator.py`
- `backend/agents/subagents/analyst.py`
- `backend/agents/subagents/critic.py`
- `backend/agents/subagents/planner.py`
- `backend/agents/subagents/gate.py`
- `backend/agents/subagents/prd_writer.py`
- `backend/agents/prompts/analyst.md`

**발견된 문제점**
- create_deep_agent는 tools=[] 설정에도 불구하고 내부 미들웨어(TodoList, filesystem 등)가 완전히 비활성화되지 않음
- 선택 파라미터가 비어있을 때 미들웨어 처리 과정에서 응답 생성 없이 종료하는 케이스 존재
- analyst가 어떤 프로젝트를 분석하는지 맥락(TOPIC/DESCRIPTION) 없이 INTERNAL 포인트만 받는 구조적 취약점 — critic 보강 방향만 받는 재호출 시 맥락 유실

**프롬프트**
- "create_deep_agent 미들웨어 문제로 빈 출력 발생 확인. analyst, critic 등 단순 텍스트 입출력 서브에이전트를 create_llm().ainvoke() 방식으로 교체해줘. analyst에 current_topic도 주입해줘."
- "analyst한테 넣어주는 planner 결과는 TOPIC과 DESCRIPTION만 전달하자."
- "create_deep_agent 코드 흔적 지우고, llm.py에 한 줄로 이유만 남겨줘."

---

## 2026-04-27 — orchestrator 주석 추가 및 researcher async 버그 수정

**작업 내용**

`researcher.py` 버그 수정
- `async def researcher_agent` → `def researcher_agent` (sync 복원)
- 사유: Tavily 클라이언트가 sync API이고, orchestrator `tool_researcher`에서 `await` 없이 직접 호출 중 — `async def`로 두면 코루틴 객체가 반환되어 결과가 유실됨

`orchestrator.py` 주석 작업
- 모든 함수/툴 위에 `#` 한 줄 역할 주석 추가 (15개 함수 전체)
- `@tool` 내부 docstring은 LLM이 tool description으로 읽으므로 수정하지 않음
- `tool_update_loop_history` 내부 기능 단위 분리
  - 현재 outer 루프 항목 조회/신규 생성
  - critic 모드: inner 카운터 증가 후 요약·점수 기록
  - gate 모드: 결정 저장 후 outer 증가·inner 리셋
- `run()` 내부 기능 단위 분리
  - logger 초기화 (파일 + 콘솔, job별 격리) / 전역 상태 초기화를 별도 섹션으로 분리
  - LLM 인스턴스 생성 + deep agent 생성 + ainvoke 호출을 하나의 섹션으로 통합
- `_setup_logger` 내부 주석 → 함수 위로 이동 (주석 포맷 일관성 유지)

**수정된 파일**
- `backend/agents/subagents/researcher.py`
- `backend/agents/orchestrator.py`

**프롬프트**
- "orchestrator에 대해서도 함수별, 함수가 수행하는 게 많을 때에는 기능 단위로 내부 나눠서 주석. @tool 내부 docstring은 tool 호출할 때 쓰는 거라 건드리면 안 돼."