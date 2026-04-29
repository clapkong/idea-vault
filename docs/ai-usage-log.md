# IdeaVault — AI 활용 로그

작업 순서: **에이전트 구현** → **Mock FastAPI** → **프론트엔드 Ralph Loop** → **백엔드 Real Mode** → **통합 및 버그 수정**

---

## 개요

| 단계 | AI 도구 | 주요 산출물 |
|---|---|---|
| 1. 에이전트 구현 | Claude 세션 (프롬프트 설계) + Claude Code (코드 구현) | `backend/agents/` 전체 |
| 2. Mock FastAPI | Claude Code | `backend/main.py` (mock 전용) |
| 3. 프론트엔드 Ralph Loop | Claude Code × 11회 반복 | `frontend/src/` 5페이지 |
| 4. 백엔드 Real Mode | Claude Code | `backend/routers/`, `backend/services/` |
| 5. 통합 및 버그 수정 | Claude Code | 전체 |

---

---

# 단계 1 — 에이전트 구현 (`backend/agents/`)

--- 
## 2026-04-23 — 에이전트 프롬프트 Prompt Engineering (클로드 세션)

**배경**
Claude 세션에서 6개 에이전트 프롬프트 설계 및 최적화. 프롬프트 설명 + 프로젝트 흐름 구조 설명 문서(`PROMPT.md` 참고) 작성 후 Claude Code에 전달하여 구현. `.claudeignore`로 `/venv`, `__pycache__`, `.env` 제외.

**프롬프트** 
이 프로젝트는 {프로젝트 설명}. 이 프로젝트는 6개의 에이전트로 구성되어 있으며 {에이전트 구조 설명}. 이 에이전트는 {역할}을 수행한다.
작성한 {agent}.md 파일을 기준으로, claude sonnet/haiku 실행 조건에서 최적의 프롬프트로 구조화.

**작업 내용**
- 프롬프트 자연어 구조에서 실제 md 형식으로 구조화 
- 모호한 지시사항 구체적으로 수정

**검수 방식**
`run.log`로 에이전트별 I/O 직접 분석 → 프롬프트 수정 → 코드 재반영 반복. 토큰 효율을 위해 AI 초안의 핵심 섹션만 선별 검토하고, 최종본은 직접 수정한 파일로만 에이전트를 실행하였다.

**AI가 만든 코드 중 수정이 필요했던 부분**
- 특정 표현을 과도하게 강조하거나 임의로 생략하는 경우 발생
- 의도와 다른 방향으로 문구를 변경하는 경우 발생
- 리팩토링 시 기존 코드를 최대한 보존하려는 경향 — 새 방식으로 전환되어 기존 코드가 불필요해진 경우에도 덧대는 방식을 고수해 코드베이스가 복잡해지는 문제 발생. 실행 전 직접 검토 후 불필요한 코드 제거를 명시적으로 지시하는 방식으로 해소.

**수정된 파일**
- `backend/agents/prompts/analyst.md`, `critic.md`, `planner.md`, `gate.md`, `prd_writer.md`, `orchestrator.md`

---

---

## 2026-04-27 — 서브에이전트 create_deep_agent 패턴 전환

**프롬프트** (`docs/prompts/` — Claude 세션 직접 작성)
> 서브에이전트 5개를 create_deep_agent 패턴으로 리팩토링. 역할 정의는 system_prompt에, 데이터는 HumanMessage로 분리. ainvoke 결과는 extract_content()로 추출.
> extract_content를 public으로 변경. create_deep_agent 인수 타입 확인 — 모델 문자열이 아닌 ChatOpenAI 객체 전달.
> 리팩토링 후 기존 기능과의 동등성 검증.

**작업 내용**

`llm.py` 재구성 — `call_llm()`, `_get_client()` 등 구형 OpenAI 직접 호출 제거, `create_llm(model, max_tokens)` / `load_prompt(agent_name)` / `extract_content(result)` 추가.

서브에이전트 5개 (critic, analyst, planner, gate, prd_writer) 전환 — 모듈 레벨에서 `create_deep_agent` 인스턴스 생성, `HumanMessage`로 데이터 전달. `analyst.py`의 `**kwargs` → 명시적 파라미터 (`researcher_result: str = "없음"`, `critic_feedback: str = "없음"`). `planner.py`의 프롬프트 내 `{critic_feedback}` 버그 → `gate_feedback`으로 수정.

**AI가 만든 코드 중 수정이 필요했던 부분**
- `extract_content`가 `_extract_content`로 private 명명 — 5개 서브에이전트에서 외부 참조하는 함수임에도 private 처리. 직접 발견 후 수정 요청.
- 데이터를 HumanMessage로 이동하면서 시스템 프롬프트에 입력 구조 안내 누락 → LLM이 어떤 형식으로 입력을 받는지 인지하지 못하는 문제. 직접 발견 후 `## 입력 형식` 섹션 추가 요청.
- `analyst.py`의 선택 파라미터(`researcher_result`, `critic_feedback`) 처리 방식이 orchestrator 프롬프트에 명시되지 않음 → 실행 로그 분석 중 orchestrator LLM이 필수 인자처럼 취급하는 패턴 확인. 이후 세션에서 보완.
- 토큰 로깅 부재로 실행 비용 추적 불가 — 리팩토링 과정에서 누락. 이후 세션에서 복원.

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/subagents/analyst.py`, `critic.py`, `planner.py`, `gate.py`, `prd_writer.py`
- `backend/agents/prompts/analyst.md`, `critic.md`, `planner.md`, `gate.md`, `prd_writer.md`

---

## 2026-04-27 — orchestrator.py 정리 및 버그픽스

**프롬프트** (Claude Code)
> 래핑 계층 과다 중첩 — `_call` 래퍼 포함 불필요한 계층 전부 제거 후 단순화.
> `llm.py`와 `orchestrator.py` 각 함수의 존재 이유 감사 및 불필요 함수 제거.
> `utils.py`의 `check_loop_limit` 로직을 orchestrator로 인라인 후 파일 병합.
> `check_loop_limit` 로그 포맷 수정 — outer/inner 카운트 누락. 플래그 → `outer=X inner=Y` 순으로 출력.
> `_last_critic_result` 제거 여부 검토 — FORCE_GATE 시 이전 critic 결과 전달 흐름 확인 후 결정.
> `tool_get_last_critic_result` 불필요 — 제거.

**작업 내용**

`_call()` 래퍼 함수 제거, `check_loop_limit` 툴 orchestrator에 인라인 (CONTINUE / FORCE_GATE / FORCE_PRD). `utils.py` 삭제.

**AI가 만든 코드 중 수정이 필요했던 부분**
- `_last_critic_result` 전역 변수를 이유 없이 제거 → FORCE_GATE 시 이전 critic 결과 전달 여부 검토 필요. 직접 실행 로그 분석 후 orchestrator 컨텍스트에 이미 보존됨을 확인하고 제거 결정.
- tool_get_last_critic_result를 불필요하게 추가 → 직접 발견 후 제거 요청.

**수정된 파일**
- `backend/agents/orchestrator.py`
- `backend/agents/utils.py` (삭제)

---

## 2026-04-27 — 후속 수정 및 프롬프트 보강

**프롬프트** (Claude Code)
> 토큰 로깅 복원 — 각 LLM 호출마다 토큰 수를 job별 logger에 기록하도록 연결.
> `tool_analyst`의 `researcher_result`, `critic_feedback`가 orchestrator 프롬프트에서 필수 인자로 취급되는 문제 — 선택 파라미터임을 명시하고, 없을 경우 생략 가능하다고 추가.
> researcher → analyst 결과 전달 명시가 병렬 실행 원칙과 충돌 — 해당 라인 롤백.
> 출력 형식 섹션과 동일하게 각 프롬프트에 `## 입력 형식` 섹션 추가. (선택) 항목은 없어도 처리 가능하다는 규칙 명시.

**작업 내용**

토큰 로깅 복원 (`llm.py`, `orchestrator.py`)
- `_TokenHandler(BaseCallbackHandler)` 추가 — `on_llm_end`에서 `response.llm_output["token_usage"]` 파싱, prompt/completion/total 로깅
- `set_token_logger(logger)` 추가 — 전역 `_token_logger`에 job별 logger 주입
- `create_llm()`에 `callbacks=[_handler]` 연결, `run()` 시작 시 `set_token_logger()` 호출

`orchestrator.md` 수정
- `tool_analyst`의 `researcher_result`, `critic_feedback`는 선택 파라미터이며 병렬 호출 시 생략 가능하다고 명시
- researcher → analyst 전달 명시 라인 추가 후 롤백 — 두 에이전트는 독립적으로 동작해야 하며, 결과 통합은 critic 단계에서 이루어짐. 병렬 실행 원칙과 충돌함을 직접 파악 후 롤백 지시.

프롬프트 `.md` 5개에 `## 입력 형식` 섹션 추가
- 각 에이전트가 받을 입력 항목과 (선택) 여부 목록화
- `## 규칙`에 "(선택) 항목이 없거나 비어 있으면 해당 정보 없이 판단할 것" 추가

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/orchestrator.py`
- `backend/agents/prompts/orchestrator.md`
- `backend/agents/prompts/analyst.md`, `critic.md`, `planner.md`, `gate.md`, `prd_writer.md`

---

## 2026-04-27 — 서브에이전트 vanilla LLM 전환 및 analyst 맥락 보강

**프롬프트** (Claude Code)
> create_deep_agent 미들웨어의 선택 파라미터 빈 값 처리 문제 확인 — analyst, critic 등 단순 텍스트 입출력 서브에이전트를 `create_llm().ainvoke()` 방식으로 전환. analyst에 `current_topic` 주입.
> analyst에 전달하는 planner 결과를 TOPIC과 DESCRIPTION으로 슬라이싱.
> create_deep_agent 코드 제거 후 llm.py에 제거 사유 한 줄 주석 추가.

**작업 내용**

서브에이전트 5개 `create_deep_agent` → `ChatOpenAI` 직접 호출로 전환. `_llm.ainvoke([SystemMessage(_prompt), HumanMessage(...)])` 패턴. `analyst`에 `current_topic: str = ""` 파라미터 추가.

**AI가 만든 코드 중 수정이 필요했던 부분**
- create_deep_agent 선택 파라미터 빈 값 처리 문제는 **AI가 아닌 직접 발견** — 실행 로그(`run.log`) 비교 분석을 통해 동일 입력에서 deepagent만 빈 출력 재현 (job `ed3d518c` vanilla vs `e0d224ae` deepagent). 원인: create_deep_agent 내부 미들웨어가 선택 파라미터 빈 값 시 응답 생성 포기. vanilla LLM 최종 확정 후 Claude Code에 전환 요청.
- researcher.py: `async def researcher_agent` → `def researcher_agent` (sync 복원). Tavily 클라이언트가 sync API인데 async 함수로 정의하면 코루틴 객체가 반환되어 결과 유실. 직접 실행 중 발견.
- analyst가 어떤 프로젝트를 분석하는지 맥락(TOPIC/DESCRIPTION) 없이 INTERNAL 포인트만 받는 구조적 취약점 — critic 보강 방향만 받는 재호출 시 맥락 유실. 직접 파악 후 `current_topic` 주입 및 planner 결과 슬라이싱 지시.

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/orchestrator.py`
- `backend/agents/subagents/analyst.py`, `critic.py`, `planner.py`, `gate.py`, `prd_writer.py`
- `backend/agents/prompts/analyst.md`
- `backend/agents/subagents/researcher.py`

---

## 2026-04-27 — orchestrator 주석 추가 및 researcher async 버그 수정

**프롬프트** (Claude Code)
> orchestrator.py 함수별 주석 추가. 기능이 여러 단계로 구성된 함수는 단계별로 분리해 내부 주석 처리. @tool 내부 docstring은 LLM이 tool description으로 참조하므로 수정 금지.

**작업 내용**

`researcher.py` 버그 수정
- `async def researcher_agent` → `def researcher_agent` (sync 복원)
- 사유: Tavily 클라이언트가 sync API이고, orchestrator `tool_researcher`에서 `await` 없이 직접 호출 중 — `async def`로 두면 코루틴 객체가 반환되어 결과가 유실됨. 직접 실행 중 발견.

`orchestrator.py` 주석 작업
- 모든 함수/툴 위에 `#` 한 줄 역할 주석 추가 (15개 함수 전체)
- `@tool` 내부 docstring은 LLM이 tool description으로 읽으므로 수정하지 않음
- `tool_update_loop_history`, `run()` 내부를 기능 단위로 분리해 주석 구조화

**수정된 파일**
- `backend/agents/subagents/researcher.py`
- `backend/agents/orchestrator.py`

---

---

# 단계 2 — Mock FastAPI 구현

**배경**: 실제 에이전트 실행을 프론트엔드 개발 단계에서 매번 할 수 없어, 이전 실행 로그를 에이전트 실행처럼 SSE 스트리밍으로 반환하는 Mock API 구현.

---

## 2026-04-27 — FastAPI Mock API 구현

**프롬프트** (`docs/coding_prompts/backend_mock_server.md`)

**작업 내용**

`backend/main.py` 생성 — 5개 엔드포인트(POST /generate, GET /stream/{job_id}, GET /result/{job_id}, GET /history, GET /analytics). SSE 스트리밍 시 `delay_sec` 필드 제외하고 전송. `ensure_ascii=False`로 한글 처리.

**검증**

SwaggerUI에서 직접 엔드포인트 실행 후 sanity check 진행.

| 엔드포인트 | 상태 | 비고 |
|---|---|---|
| POST /generate | ✅ | 항상 job_id: 92b2d589 반환 |
| GET /stream/{job_id} | ✅ | SSE, delay_sec 반영 & 제외, 한글 정상 |
| GET /result/{job_id} | ✅ | prd + loop_history 반환 |
| GET /history | ✅ | history.json 그대로 반환 |
| GET /analytics | ✅ | 하드코딩 Mock, range 파라미터 수용 |

실행: `venv/bin/uvicorn main:app --reload` (venv의 uvicorn 사용)

**AI가 만든 코드 중 수정이 필요했던 부분**
- Mock 데이터 경로를 프롬프트의 `mock/`가 아닌 `mock_agents/`로 자동 감지 — 실행 전 직접 확인.
- analytics 응답이 하드코딩 — 이후 real mode 전환 시 수정사항이 많다는 한계 직접 파악.

**수정된 파일**
- `backend/main.py` (신규)
- `backend/requirements.txt`

---

## 2026-04-27 — Mock/Real 모드 전환 구조 추가

**프롬프트** (`docs/coding_prompts/backend_mode_switch.md`)

**작업 내용**

`USE_MOCK_MODE` 환경변수로 모드 구분. Mock 모드는 현재 동작 유지, Real 모드는 501 반환. 함수명에 `mock_` prefix 추가.

**변경 전후 비교**

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| 모드 구분 | 없음 | USE_MOCK_MODE 환경변수 (기본값 "true") |
| event_stream | Mock 전용 함수 | mock_event_stream으로 이름 변경 |
| POST /generate | Mock만 | Mock/Real 분기 (Real → 501) |
| GET /stream/{job_id} | Mock만 | Mock/Real 분기 (Real → 501) |
| GET /result/{job_id} | Mock만 | Mock/Real 분기 (Real → 501) |
| GET /history, GET /analytics | Mock만 | 변경 없음 |

**실행 방법**

```bash
# Mock 모드 (현재와 동일)
USE_MOCK_MODE=true uvicorn main:app --reload

# Real 모드 (501 반환)
USE_MOCK_MODE=false uvicorn main:app --reload
```

**AI가 만든 코드 중 수정이 필요했던 부분**
- USE_MOCK_MODE 기본값이 `false`로 설정되어 프론트엔드 개발 중 실행하면 모든 엔드포인트 501 반환. 직접 발견 후 `true`로 수정.

**수정된 파일**
- `backend/main.py`

---

---

# 단계 3 — 프론트엔드 Ralph Loop

**Ralph Loop 선정 이유**
- 자동화 루프로 반복 구현을 진행하되, 매 루프 결과를 직접 검증하며 방향을 제어하는 방식 채택
- 코드 생성과 시각적 검증을 단계별로 분리하여 구현 품질을 직접 통제할 수 있다는 장점

**완전한 Ralph Loop와의 차이점**
- 구현 기획 및 프롬프트를 Claude 세션에서 사전에 완성 후 진입 (`docs/ralph_mode/ralph_prompt.md`)
- 구체적인 요구사항 명세를 기반으로 Claude Code가 세부 디자인 및 코드 구현만 담당
- `ralph_mode.sh`로 자동 실행: 루프 번호 누적 추적, `FRONTEND_COMPLETE` 태그로 완료 감지, 각 루프마다 git commit 자동화
- **실제 Ralph Loop는 3회만 진행** — 백엔드 구조가 확정된 상태에서 구체적인 구현 계획이 이미 정리되어 있었고, 프롬프트가 충분히 구체적이었기에 Loop 3에서 `FRONTEND_COMPLETE` 선언 후 종료.

**주요 효과**
- 사전 기획한 디자인 방향과 높은 일치도 달성
- 프롬프트에 명시한 대로 매 루프마다 git commit 자동 실행
- 루프를 거치며 기능이 점진적으로 확장되는 구조
- 루프 실행 중 병렬로 다른 작업 진행 가능 — 관련 파일만 정확히 선별하여 커밋

**Ralph Loop 실행 요약 (Loop 1~3) — 2026-04-26**

| 루프 | 주요 변화 | 개선 포인트 |
|---|---|---|
| Loop 1 | 5개 페이지 전체 초기 생성 (Home, Analyze, History, Result, Analytics) | 기본 구조·레이아웃·SSE 연결·react-markdown 적용 |
| Loop 2 | API 연동 수정 (Vite 프록시, POST body 필드명, CORS 포트) | analytics 응답 형식 대응, stop/favorite/delete 엔드포인트 추가 |
| Loop 3 | connecting 상태 UI, NotFound 페이지, 빌드 최종 확인 | `FRONTEND_COMPLETE` 태그로 1차 완료 선언 |

**후속 디버깅 세션 요약 — 2026-04-27**

> Loop 3 이후 `FRONTEND_COMPLETE` 선언. 이후 작업은 Ralph Loop 방식이 아닌 일반 Claude Code 세션. 기록 편의상 Loop 4~11 번호가 붙어 있음.

| 세션 | 주요 변화 | 개선 포인트 |
|---|---|---|
| Loop 4 | remark-gfm으로 테이블 수정, TOC sticky, Chip 이모티콘화, 하트 SVG화 | 즐겨찾기 필터 구현, ctrl+s 세션 종료 방지 |
| Loop 5 | TOC sticky → flex min-height:0 방식 재수정, PRD Writer 버튼 교체 | ChatBubble MD 헤더 bold만 적용, Vite proxy bypass |
| Loop 6 | TOC overflow:hidden 고정, AGENT_MESSAGES·AGENT_COLORS 상수 추가 | bubble-wrapper 65%로 축소, prdReady 중복 제거 |
| Loop 7 | **html/body height:100% + overflow:hidden — 스크롤 근본 원인 해결** | 자동 PRD 이동 제거 (버튼 클릭으로만), user 아바타 우측 고정 |
| Loop 8 | bubble 65%로 재조정, 에이전트 이미지 public/ 동기화 | ColumnChart 도입, prd_writer 중복 버블 제거 |
| Loop 9 | SVG 기반 ColumnChart 전면 교체 (hover 툴팁, 애니메이션) | 파이차트 레이아웃 개선, PRD Viewer 좌우 여백 |
| Loop 10 | analytics 동적 집계 (model별 토큰), soft delete 영구화 | 비용 컬럼 제거, history.json 구조 개선 |
| Loop 11 | 날짜별 모델 스택 막대차트, 파이차트 hover 툴팁 | 전체 페이지 2컬럼 레이아웃 재구성 |
| CSS 주석 + 구조 정리 | index.css/App.css 역할 분리, 전체 CSS 파일 주석 추가 | btn-primary App.css로 이동 |
| JSX 파일 주석 추가 | 전체 JSX 파일 7가지 주석 규칙 일괄 적용 | 명사구 스타일, 첫 등장 패턴 설명 |

---

**AI가 만든 코드 중 수정이 필요했던 부분**

1. **스크롤 버그 — 4회 반복 끝에 근본 원인 해결** (후속 디버깅 세션 Loop 4~7)
   - 컴포넌트 레벨(`position: sticky`, `min-height: 0 + overflow: hidden`, `overflow: hidden`)에서 반복 접근했으나 모두 부분 개선에 그침.
   - 실제 원인: 브라우저가 body 레벨에서 스크롤바를 그리고 있었음. 하위 컴포넌트에서 `overflow: hidden`을 걸어도 body의 네이티브 스크롤은 차단 불가. DevTools로 레이아웃 레이어를 직접 확인 후 파악.
   - 해결: `html/body { height: 100%; overflow: hidden; }` — min-height: 100vh → height: 100% 전환.

2. **git commit 범위 문제** — 일부 파일만 스테이징되어 변경사항 누락. 이후 커밋 전 직접 `git status` 확인을 루틴으로 추가.

3. **node_modules gitignore 누락** — .gitignore이 Python 기준으로만 되어 있어 node_modules가 'U'로 표시됨. 루프 실행 중 직접 .gitignore에 추가.

4. **USE_MOCK_MODE 기본값** — Loop 실행 중 실제 에이전트 실행 없이도 FastAPI에 연결되어야 하는데 real mode(501)가 기본값이라 모든 API 호출이 실패. 직접 .env 수정으로 해결.

---

## 2026-04-26 — Ralph Loop 1: 5개 페이지 초기 생성

**프롬프트** (`docs/ralph_mode/ralph_prompt.md`)

**작업 내용**
- Vite + React 프로젝트 초기화 (기존 `public/agents` 이미지 유지)
- react-router-dom, react-markdown 패키지 설치
- 전역 CSS 변수 설정 (테마 컬러: 로스팅 브라운, 크래프트지 등)
- NavBar 컴포넌트 (네비게이션 바, 활성 링크 강조)
- ChatBubble 컴포넌트 (agent/user 말풍선, 로딩 애니메이션 ●●●○○○)
- Home 페이지 (아이디어 입력 textarea, 예시 chip 3개, 추천 받기 버튼)
- Analyze 페이지 (SSE 스트리밍, agent 말풍선, 세션 멈추기)
- History 페이지 (좌우 분할, 히스토리 카드, 즐겨찾기/삭제, 채팅 재현)
- Result 페이지 (목차 사이드바, react-markdown 렌더링, PRD 다운로드)
- Analytics 페이지 (날짜 범위 필터, 요약 카드, 테이블, 파이/바 차트, CSV)
- 빌드 성공 확인

**생성/수정된 파일**
- `frontend/index.html`
- `frontend/src/index.css`, `App.css`, `App.jsx`, `main.jsx`
- `frontend/src/components/NavBar.jsx`, `NavBar.css`
- `frontend/src/components/ChatBubble.jsx`, `ChatBubble.css`
- `frontend/src/pages/Home.jsx`, `Home.css`
- `frontend/src/pages/Analyze.jsx`, `Analyze.css`
- `frontend/src/pages/History.jsx`, `History.css`
- `frontend/src/pages/Result.jsx`, `Result.css`
- `frontend/src/pages/Analytics.jsx`, `Analytics.css`

---

## 2026-04-26 — Ralph Loop 2: API 연동 수정

**프롬프트** (`docs/ralph_mode/ralph_prompt.md`)

**작업 내용**
- Vite 프록시 설정 (localhost:8000 하드코딩 제거, 상대경로로 변경)
- Home.jsx: POST body 필드명 수정 (`idea` → `user_input`)
- Analytics.jsx: 백엔드 응답 형식 대응 (`{summary, data}` 또는 flat array)
- History.jsx: events 배열 기반 채팅 재구성 (loop_history 비어있을 때)
- ChatBubble: analyst 에이전트 추가, 아이콘 fallback 처리
- `backend/main.py`: CORS에 5173 포트 추가, 누락 엔드포인트 추가 (stop/favorite/delete)
- `backend/main.py`: analytics 날짜 범위 필터링 구현, result 엔드포인트에 events 필드 포함
- `frontend/.gitignore` 추가

**생성/수정된 파일**
- `frontend/vite.config.js`
- `frontend/.gitignore`
- `frontend/src/pages/Home.jsx`, `Analyze.jsx`, `History.jsx`, `Result.jsx`, `Analytics.jsx`
- `frontend/src/components/ChatBubble.jsx`
- `backend/main.py`

---

## 2026-04-26 — Ralph Loop 3: 빌드 확인 및 1차 완료

**프롬프트** (`docs/ralph_mode/ralph_prompt.md`)

**작업 내용**
- `btn-primary` 공통 스타일을 `index.css`로 이동 (Home/Analyze/History 전체에 적용)
- Home.css에서 중복 `btn-primary` 제거
- Analyze 페이지: 연결 중 상태(connecting) 추가, `fade-pulse` 애니메이션
- NotFound 페이지 추가 (404 fallback)
- App.jsx: `*` 와일드카드 라우트 추가
- 빌드 최종 확인 (197 모듈, 오류 없음) → `FRONTEND_COMPLETE` 선언

**생성/수정된 파일**
- `frontend/src/index.css`
- `frontend/src/App.jsx`
- `frontend/src/pages/Home.css`
- `frontend/src/pages/Analyze.jsx`, `Analyze.css`
- `frontend/src/pages/NotFound.jsx` (신규)
- `frontend/package.json`

---

## 2026-04-27 — 후속 디버깅 (Loop 4): 기능 버그 수정 및 UI 개선

**프롬프트**

`<Function>` 이슈:
> [Analyze] ctrl+s 등 키보드 단축키로 인한 세션 종료 방지 — 세션 종료는 버튼 클릭으로만.
> [History] 즐겨찾기 필터 미구현 — `favOnly` 상태 추가 및 필터링 구현.
> [Token Analytics] 세션 내 복수 모델 지원을 위한 통계 구조 개편 — 백엔드 events 구조 변경 필요, 우선 TODO로 분리.
> [Analyze][History] Researcher `tokens=0` 케이스 처리 — 다른 에이전트와 동일 포맷으로 표시.
> [PRD Viewer] PRD 본문 스크롤 시 목차도 함께 이동하는 버그 수정.
> [PRD Viewer] remark-gfm 미설치로 인한 테이블 렌더링 오류 수정.
> [Analyze][History] 채팅 버블 텍스트 클리핑 방지 — `overflow-wrap` 처리.

`<Design>` 이슈:
> [Home] 예시 Chip을 이모티콘 + 키워드 형태로 교체 (전체 텍스트 가독성 문제).
> [Analyze] 채팅 버블 가로 길이를 85-90%로 축소.
> [Analyze] 채팅 버블 내 Markdown 렌더링 적용.
> [PRD Writer] 뒤로가기 버튼 가로 길이 확장 (텍스트 줄바꿈 방지).
> [History] 하트 이모티콘을 테마에 맞는 SVG 아이콘으로 교체.

**작업 내용**
- Analyze: ctrl+s 등 키보드 단축키로 세션 종료되는 현상 방지 (keydown 이벤트 차단)
- ChatBubble: Researcher tokens=0 미표시 버그 수정 (`typeof tokens === 'number'` 조건)
- ChatBubble: 버블 내 텍스트 클리핑 방지 (`overflow-wrap: break-word`), 가로 70% → 88%
- ChatBubble: 에이전트 버블에 ReactMarkdown + remark-gfm 렌더링 적용
- PRD Viewer: remark-gfm 설치 및 적용으로 테이블 깨짐 수정
- PRD Viewer: TOC 스크롤 오류 수정 (`position: sticky`)
- PRD Viewer: 다운로드 버튼 헤더 우측으로 이동
- History: ❤️/🤍 이모티콘 → SVG 하트 아이콘으로 교체
- History: 즐겨찾기만 보기 필터 버튼 구현 (`favOnly` 상태)
- Home: 예시 Chip을 이모티콘+키워드 형태로 개선

**생성/수정된 파일**
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/History.jsx`, `History.css`
- `frontend/src/pages/Result.jsx`, `Result.css`
- `frontend/src/components/ChatBubble.jsx`, `ChatBubble.css`
- `frontend/package.json` (remark-gfm 추가)

**TODO**
- Token Analytics: 세션 내 복수 모델/에이전트별 통계 — 백엔드 구조 개편 필요 (각 events에 model 필드 추가, /analytics가 agent×model×tokens 단위로 집계, researcher는 tokens=0/model="n/a" 처리)

---

## 2026-04-27 — 후속 디버깅 (Loop 5): 스크롤 재수정 및 PRD Viewer 개선

**프롬프트**
> [PRD Viewer] Loop 4 수정 후 목차 높이 축소 및 스크롤 고정 미작동 — 목차 높이 복원 및 스크롤 고정 재수정.
> [PRD Viewer] 테이블 헤더/본문 색상 구분 — 채팅 버블에는 적용되어 있으나 viewer에는 미반영.
> [History] 좌측 히스토리 목록 고정, 우측 채팅 영역만 스크롤.
> [Analytics][History] 버블 내 MD 렌더링 — font-size 변경 없이 글자 스타일만 반영. header 태그는 bold만 적용.
> [Analytics][History] PRD Writer 출력을 PRD 전문 대신 'IdeaVault가 만들어준 나만의 PRD 보기!' 버튼으로 교체.
> [PRD Viewer] 다운로드 버튼을 하단에서 제목 우측으로 이동.
> Vite dev에서 `/analytics` 등 경로 직접 접근 시 React 앱 대신 JSON 반환 — `bypassNav` 처리 추가.
> `index.css` 텍스트 색상 #3D2E1F → #4A3B2A 변경 후 전체 파일 반영.

**작업 내용**
- PRD Viewer: TOC 스크롤 고정 재수정 — sticky 방식 제거, flex `min-height: 0` 방식으로 교체 + `App.jsx` main에 `minHeight: 0, overflow: hidden` 추가
- History: 좌측 사이드바 고정, 우측 채팅만 스크롤 — `min-height: 0` 방식 적용
- PRD Viewer: 테이블 헤더 배경색 구분 (`var(--background)` → `var(--border)`)
- ChatBubble: 버블 내 MD 헤더 — 글자 크기 유지, bold만 적용 (`font-size: inherit`)
- ChatBubble: PRD Writer 버블 → 'IdeaVault가 만들어준 나만의 PRD 보기!' 버튼으로 교체 (jobId prop 추가)
- Vite proxy: `/analytics`, `/history`, `/result` 직접 접근 시 JSON 반환 문제 수정 — bypass 함수로 text/html 요청은 프록시 우회

**생성/수정된 파일**
- `frontend/src/App.jsx`
- `frontend/src/pages/Result.jsx`, `Result.css`
- `frontend/src/pages/History.jsx`, `History.css`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/components/ChatBubble.jsx`, `ChatBubble.css`
- `frontend/vite.config.js`

**TODO**
- (이전 TODO인 Token Analytics 백엔드 구조 개편은 계속 유효)

---

## 2026-04-27 — 후속 디버깅 (Loop 6): UI 폴리싱

**프롬프트**
> [PRD Viewer] 좌측 목차 완전 고정 — 우측 PRD 본문 스크롤 시에도 이동하지 않도록.
> [History] 좌측 목록과 우측 채팅 스크롤 분리 — 두 영역이 독립적으로 스크롤되도록.
> [History][Analytics] 채팅 버블 max-width 축소 — 가독성 개선.
> [History][Analytics] PRD Writer 완료 버블 → 'IdeaVault가 만들어준 나만의 PRD 보기!' 버튼으로 교체.
> [History][Analytics] 에이전트별 진행 메시지 & 완료 메시지 상수 추가 (`AGENT_MESSAGES`): planner/researcher/critic/gate/analyst/prd_writer 각각 progress/done 메시지.
> (1) critic done 메시지 추가. (2) 'IdeaVault가 만들어준 나만의 PRD 보기!' 중복 출력 버그 수정. (3) 에이전트별 레이블 색상(`AGENT_COLORS`) 추가 — moss green/terracotta/dusty blue/lavender gray/mustard/sage green 팔레트, 에이전트 이름 태그에 적용.

**작업 내용**

**[PRD Viewer]**
- 좌측 목차(TOC) 패널 고정: `overflow-y: auto` → `overflow: hidden` (스크롤 비활성화)
- 우측 PRD 콘텐츠 영역에 `overscroll-behavior: contain` 추가 (스크롤 이벤트 전파 차단)

**[History]**
- job-list / chat-messages-history 양쪽에 `overscroll-behavior: contain` 추가 → 목록/대화 스크롤 독립화

**[ChatBubble — History & Analyze 공통]**
- `bubble-wrapper` max-width `88%` → `65%` (버블 가로 길이 축소)
- `AGENT_MESSAGES` 상수 추가: 에이전트별 loading 진행 메시지 & 완료 메시지(done)
  - loading 시 백엔드 progress 없으면 상수 fallback 사용
  - done 시 완료 메시지를 출력 상단에 표시 (`.done-msg`)
- `AGENT_COLORS` 상수 추가: 에이전트별 레이블 색상 (moss green, terracotta, dusty blue 등)
- `prd_writer` done 버블: "PRD 작성이 완료되었습니다!" + "IdeaVault가 만들어준 나만의 PRD 보기!" 버튼
- critic done 메시지: `"..."` → `"추가 정보 확인을 완료했습니다!"`
- "IdeaVault가 만들어준 나만의 PRD 보기!" 중복 제거: Analyze.jsx의 `prdReady` 배너/상태 제거 (ChatBubble이 커버)

**수정된 파일**
- `frontend/src/pages/Result.css`
- `frontend/src/pages/History.css`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/pages/Analyze.css`
- `frontend/src/components/ChatBubble.jsx`
- `frontend/src/components/ChatBubble.css`

---

## 2026-04-27 — 후속 디버깅 (Loop 7): 스크롤 근본 원인 해결

**프롬프트**
> [PRD Viewer] Loop 6 수정 후 우측 PRD 본문 freeze 및 목차 스크롤 시 페이지 전체 이동 문제 잔존 — 요구사항 재정의: (1) 페이지 전체 스크롤 없음, (2) 우측 PRD 본문 독립 스크롤, (3) 좌측 목차 고정.
> [History] Loop 6 수정으로 인해 페이지 전체 고정 — 좌측 목록/우측 채팅 각각 독립 스크롤로 복원.
> [History] PRD Writer 완료 버블 중복 표시 수정 — "PRD 작성이 완료되었습니다!" + "IdeaVault가 만들어준 나만의 PRD 보기!" 2회 출력.
> [Analyze] PRD 완성 시 자동 이동 제거 — "PRD 보기" 버튼 클릭으로만 이동.
> [Home][History] 채팅 버블 max-width 80%로 통일. 좌우 여백 확보. user/agent 버블 크기 통일.
> user 아바타 우측 배치.

**스크롤 버그 원인 분석**

| 시도 | 수정 위치 | 방법 | 결과 |
|---|---|---|---|
| Loop 4 | `.result-toc` | `position: sticky` | 실패 |
| Loop 5 | 각 페이지 컴포넌트 | `min-height: 0 + overflow: hidden` | 부분 개선 |
| Loop 6 | `.result-toc` | `overflow: hidden` | 오히려 악화 |
| Loop 7 | `html / body / #root` | `height: 100% + overflow: hidden` | 해결 |

- **근본 레이어 진단**: 증상이 "TOC가 같이 스크롤됨"으로 나타나 컴포넌트 레벨에서만 반복 접근했으나, 실제 원인은 브라우저가 body 레벨에서 스크롤바를 그리고 있었음 — 하위에서 아무리 `overflow: hidden`을 걸어도 body의 네이티브 스크롤은 차단 불가.
- **`min-height: 100vh` vs `height: 100%`**: `min-height`는 콘텐츠가 뷰포트보다 커지면 body가 무한정 늘어남. `height: 100%`는 뷰포트에 고정. flex 자식의 `overflow: hidden`은 부모 체인이 `height`로 고정되어 있을 때만 유효.
- **CSS 스크롤 격리 원칙**: `html → body → #root → main` 전체 체인이 `height`로 고정되어야 하위 컴포넌트의 독립 스크롤이 동작. DevTools로 브라우저 레이아웃 레이어를 먼저 확인하는 것이 핵심.

**작업 내용**
- `html`, `body`, `#root`: `min-height: 100vh` → `height: 100%; overflow: hidden`으로 전환 — 브라우저 네이티브 스크롤 차단
- PRD Viewer: 좌측 TOC 완전 고정, 우측 PRD 본문 독립 스크롤
- History: 전체 페이지 고정 해제 — 좌측 목록 / 우측 채팅 각각 독립 스크롤
- PRD Writer 완료 버블 중복 제거 (History)
- Analyze: PRD 완성 시 자동 이동 제거 → "PRD 보기" 버튼 클릭으로만 이동
- ChatBubble: `bubble-wrapper` 80%로 조정, user 아바타 우측 배치

**생성/수정된 파일**
- `frontend/src/index.css` (html/body/root height 전환)
- `frontend/src/pages/Result.jsx`, `Result.css`
- `frontend/src/pages/History.jsx`, `History.css`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/components/ChatBubble.jsx`, `ChatBubble.css`

---

## 2026-04-27 — 후속 디버깅 (Loop 8): 버블 재조정 및 Analytics 개선

**프롬프트**
> (1) 채팅 버블 max-width 65%로 재조정 — 80% 설정 후에도 가독성 부족.
> (2) 에이전트 프로필 이미지 교체 후 브라우저 미반영 — 원인 파악 및 수정.
> (3) Analytics 날짜별 사용량을 x축 날짜 / y축 토큰 수 ColumnChart로 전환.
> (4) Analyze 페이지의 prd_writer 완료 버블 중복 — History에서 적용한 수정 누락분 반영.

**작업 내용**
- ChatBubble: `bubble-wrapper` max-width 재조정 → `65%`
- 에이전트 이미지 미반영 원인 분석 및 수정: Vite가 `public/` 이미지를 빌드 시 해시로 번들링하지 않아 브라우저 캐시가 남아 있었음 → `public/agents/` 이미지를 올바른 경로로 동기화
- Analytics: 날짜별 집계를 x축 날짜 / y축 토큰 수 ColumnChart로 전환
- Analyze: `prd_writer` done 버블 중복 제거 (Loop 7에서 History만 고쳐 Analyze 미반영분 처리)

**생성/수정된 파일**
- `frontend/src/components/ChatBubble.jsx`, `ChatBubble.css`
- `frontend/src/pages/Analytics.jsx`, `Analytics.css`
- `frontend/src/pages/Analyze.jsx`
- `frontend/public/agents/` (이미지 동기화)

---

## 2026-04-27 — 후속 디버깅 (Loop 9): SVG ColumnChart 전면 교체

**프롬프트**
> 날짜별 사용량 그래프를 레이아웃에 맞게 재조정. x축 날짜, y축 토큰 수, 명확한 축 레이블 추가. 토큰 수는 막대 위가 아닌 hover 시 툴팁으로 표시.
> [PRD Viewer] 본문 가로 여백 추가.

**작업 내용**
- Analytics: SVG 기반 ColumnChart 전면 재구현 — x축 날짜 레이블, y축 명시적 격자선, 막대 hover 시 툴팁으로 토큰 수 표시, 애니메이션 적용
- 파이차트 레이아웃 개선 및 여백 재조정
- PRD Viewer: 본문 좌우 여백 추가 (`padding` 보강)

**생성/수정된 파일**
- `frontend/src/pages/Analytics.jsx`, `Analytics.css`
- `frontend/src/pages/Result.css`

---

## 2026-04-27 — 후속 디버깅 (Loop 10): Analytics 동적 집계 및 소프트 삭제

**프롬프트**
> mock 데이터를 백엔드 응답 구조에 맞게 수정. 대상 파일: `92b2d589.json`, `history.json`만 업데이트. 나머지 JSON은 수동 수정 예정. 백엔드 연동 시 처리 필요한 항목은 TODO로 명시.
> (1) token analytics에서 세션 내 모델별 토큰 합산.
> (2) 히스토리 삭제 시 `deleted: true` 방식으로 소프트 삭제 영속화. 즐겨찾기 상태도 동일 meta 구조로 통합.
> (3) token analytics에서 비용 컬럼 제거 및 여백 재조정. 이후 백엔드 pandas CSV 연동을 고려한 구조로 설계.
> (4) Analyze 페이지 job_id 하드코딩 제거 — SSE 응답에서 동적 수신.

**발견된 문제점 — 프론트에 하드코딩된 백엔드 작업 목록**

1. **검색/정렬/즐겨찾기 필터 (`History.jsx:79-88`)** — `jobs.filter(...).sort(...)` 전체를 프론트가 처리. 실제로는 `GET /history?search=...&sort=newest&favorite=true` 형태로 백엔드 쿼리 파라미터 처리 필요.
2. **삭제가 프론트 state에만 반영 (`History.jsx:126`)** — `setJobs(prev => prev.filter(...))`. 페이지 새로고침 시 삭제 항목 재등장. 백엔드 `DELETE /jobs/{job_id}`로 `deleted: true` 영속화 필요.
3. **Analytics 집계 (`Analytics.jsx:112-137`)** — `useMemo`로 프론트가 직접 토큰 합계·모델별·날짜별 집계. 실제로는 `/analytics?range=7days` 응답에 집계 결과 포함 필요.
4. **ANALYTICS_DATA 하드코딩 (`backend/main.py:26-31`)** — 집계 데이터 자체가 하드코딩. 실제로는 각 세션의 events에서 agent별 tokens를 읽어 동적 계산 필요.

**작업 내용**
- Analytics: 세션별 events에서 agent×model×tokens 단위로 동적 집계 (프론트 useMemo)
- Analytics: 비용 컬럼 제거, 여백 재조정
- History: 삭제 시 `deleted: true` 플래그로 영속화, 즐겨찾기도 동일 구조에서 관리
- Analyze: job_id 하드코딩 제거 → SSE 응답에서 동적으로 수신

**생성/수정된 파일**
- `frontend/src/pages/Analytics.jsx`, `Analytics.css`
- `frontend/src/pages/History.jsx`
- `frontend/src/pages/Analyze.jsx`
- `data/92b2d589.json`, `data/history.json` (mock 데이터 구조 개선)

**TODO**
- 백엔드 연동 시 처리 필요 (위 4가지 하드코딩 항목):
  - `GET /history`: search/sort/favorite 쿼리 파라미터 지원
  - `DELETE /jobs/{job_id}`: `deleted: true` 영속화
  - `GET /analytics`: 집계 결과 포함 응답 구조
  - 각 events에 model 필드 추가, researcher는 `tokens=0 / model="n/a"` 처리

---

## 2026-04-27 — 후속 디버깅 (Loop 11): 날짜별 스택 차트 및 hover 개선

**프롬프트**
> (1) 그래프 영역 위치 재조정 — 레이아웃 하단으로 밀린 문제 수정. (2) 날짜별 hover 툴팁에 모델별 토큰 수(각각) + 총합 동시 표시. (3) 파이차트 hover 시 모델명 + 토큰 수 표시. (4) 툴팁 내 모델별 색상 사각형(legend dot) 추가.

**작업 내용**
- Analytics: 그래프 영역 위치 조정 (레이아웃 padding 보정)
- 날짜별 막대차트: hover 툴팁에 모델별 토큰 수(각각) + 총합 동시 표시
- 날짜별 막대를 모델별 색상 스택 막대로 전환
- 파이차트: hover 시 모델명 + 토큰 수 툴팁 표시
- 툴팁 내 모델별 색상 사각형(legend dot) 추가

**생성/수정된 파일**
- `frontend/src/pages/Analytics.jsx`, `Analytics.css`

---

## 2026-04-27 — CSS 주석 + 구조 정리

**프롬프트** (Claude Code)
> `index.css`는 CSS 변수 + html/body/root 리셋 전담으로 재정의. `.btn-primary` 공통 버튼 스타일을 `App.css`로 이동. 전체 CSS 파일 주석 추가: 파일 상단 역할 한 줄, 셀렉터별 한 줄, 비직관적인 속성은 파일 내 첫 등장 시에만 인라인 설명.

**작업 내용**
- `App.css` / `index.css` 역할 분리: `index.css`는 CSS 변수 + html/body/root 리셋만, `.btn-primary`는 `App.css`로 이동
- 전체 CSS 파일에 주석 추가: 파일 상단 역할 한 줄, 셀렉터마다 한 줄, 비직관적인 CSS 속성(flex 축약값, var(), overflow, position 등)은 첫 등장 시에만 인라인 설명

**생성/수정된 파일**
- `frontend/src/App.css`, `index.css`, `main.jsx`, `App.jsx`
- `frontend/src/pages/Analyze.css`, `Analytics.css`, `History.css`, `Home.css`, `Result.css`
- `frontend/src/components/NavBar.css`, `ChatBubble.css`

**TODO**
- JSX 파일 주석 미완료 (CSS만 완료) → 다음 세션에서 완료

---

## 2026-04-27 — JSX 파일 주석 추가

**프롬프트** (Claude Code)
> 전체 JSX 파일 주석 추가. 규칙: (1) 파일 상단 — 컴포넌트 역할 한 줄 (2) 상수/설정 객체 — 각각 한 줄 (3) 함수/컴포넌트 선언 전 — 한 줄 (4) 훅(useState, useRef, useEffect, useMemo) — 각각 한 줄 (5) JSX 내 주요 블록 — 한 줄 (6) 비직관적 패턴 — 파일 내 첫 등장 시에만, 이후 동일 파일·다른 파일 재등장 생략 (7) 파일 내 일관성 유지. 주석 스타일: 명사구/라벨형, 서술형 금지.

**작업 내용**
전체 JSX 파일에 7가지 주석 규칙 일괄 적용. 비직관적인 React 패턴(useRef, scrollIntoView, EventSource 등)은 파일 내 첫 등장 시에만 설명, 이후 같은 패턴 및 다른 파일 재등장도 모두 생략.

**생성/수정된 파일**
- `frontend/src/App.jsx`, `main.jsx`
- `frontend/src/pages/Analytics.jsx`, `Analyze.jsx`, `History.jsx`, `Home.jsx`, `NotFound.jsx`, `Result.jsx`
- `frontend/src/components/ChatBubble.jsx`, `NavBar.jsx`

---

---

# 단계 4 — 백엔드 Real Mode 구현 (`feature/backend`)

**사전 계획**: `docs/coding_prompts/backend_real_mode_plan.md` — 백엔드 작업 시작 전 작성. FastAPI real mode 구조(asyncio.Queue SSE 패턴, job 저장 구조), Docker, CI/CD 계획 포함. Phase별 상세 구현 프롬프트는 별도 파일로 분리 작성.

---

## 2026-04-27 — orchestrator 이벤트 우선 구조 전환

**프롬프트** (Claude Code)
> orchestrator의 출력 구조를 로그 파일 중심에서 이벤트 스트림 중심으로 재설계. 각 에이전트 호출 시 agent_start/agent_progress/agent_done 이벤트를 emit하고, run() 반환값에 events 리스트를 포함시킨다. 기존 주석과 로직은 그대로 유지.

**작업 내용**

`_emit()` 1차 출력 구조로 변경. `_event_queue: asyncio.Queue | None` 추가 (None이면 CLI 모드). 각 tool 호출 전후에 `agent_start / agent_progress / agent_done` emit. `run()` 시그니처에 `event_queue` 파라미터 추가.

**AI가 만든 코드 중 수정이 필요했던 부분**
- 첫 Write에서 WHY 주석 전체 삭제. 기존 주석 보존 명시가 필요했으나 누락. 직접 발견 후 두 번째 Write에서 복원.

**수정된 파일**
- `backend/agents/orchestrator.py`

---

## 2026-04-27 — FastAPI real mode 구현 (Phase 1)

**프롬프트** (`docs/coding_prompts/backend_real_mode_phase1.md`)
> asyncio.Queue 기반 이벤트 브릿지를 사용하여 FastAPI real mode를 구현한다. POST /generate는 uuid4 job_id 생성 후 asyncio.create_task로 orchestrator 백그라운드 실행. GET /stream/{job_id}는 큐에서 이벤트를 SSE로 스트리밍. GET /result, POST /stop 포함. 30분 타임아웃, 취소/실패 처리. history/analytics/favorite/delete는 Phase 2에서 real mode 전환 예정.

**작업 내용**

asyncio.Queue 기반 이벤트 브릿지로 orchestrator ↔ SSE 스트림 연결. `job_queues`, `running_jobs` 인메모리 상태 추가. `_run_pipeline()` — orchestrator 백그라운드 실행, 결과 파일 저장, 예외/취소 처리, finally에서 done 이벤트 보장. 30분 타임아웃.

저장 구조 (`data/jobs/{job_id}/`): `input.txt`, `meta.json`, `prd.md`, `loop_history.json`, `events.json`

**수정된 파일**
- `backend/main.py`

---

## 2026-04-27 — FastAPI real mode 구현 (Phase 2)

**프롬프트** (`docs/coding_prompts/backend_real_mode_phase2.md`)
> GET /history, GET /analytics, PATCH favorite, DELETE 엔드포인트를 data/jobs/ 기반 real mode로 전환한다. analytics는 pandas DataFrame으로 집계하고 range 파라미터(today/7days/30days/all)를 지원한다. mock mode 분기 반드시 유지. data/jobs/ 없으면 빈 배열 반환.

**작업 내용**

나머지 4개 엔드포인트 real mode 전환. pandas DataFrame으로 analytics 집계, range 필터(`today/7days/30days/all`) 지원. `GET /history` — data/jobs/ 전체 스캔, deleted 제외. `PATCH favorite`, `DELETE` — meta.json 기반 소프트 삭제.

**수정된 파일**
- `backend/main.py`
- `backend/requirements.txt`

---

## 2026-04-27 — 토큰 집계 수정 (Phase 2.5)

**프롬프트** (`docs/coding_prompts/backend_real_mode_phase2_5.md`)
> llm.py의 _TokenHandler를 수정해 토큰 누산 카운터를 추가하고, orchestrator 각 tool에서 호출 전후 스냅샷으로 per-agent 토큰을 계산한다. run() 반환값에 token_counts를 포함시키고, main.py에서 sonnet/haiku 단가로 cost를 계산해 meta.json에 저장한다.

**작업 내용**

meta.json의 tokens/cost가 항상 0으로 저장되는 문제 수정. `_TokenHandler`가 logging만 하고 누산하지 않던 구조를 개선. `_token_counts` 모듈 상태 추가, `reset_token_counts()` / `get_total_tokens()` 추가. `_PRICING` + `_compute_cost()` (haiku/sonnet 단가 분기).

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/orchestrator.py`
- `backend/main.py`

---

## 2026-04-27 — 프로젝트 구조 재편 (routers/services 분리)

**프롬프트** (Claude Code)
> 프로젝트를 웹 서비스 구조로 재편한다. backend/main.py의 모든 라우터·헬퍼 로직을 엔드포인트별 routers/ 파일과 역할별 services/ 파일로 분리. 프론트엔드에 src/api/client.js API 레이어를 추가해 각 페이지의 inline fetch를 제거. mock_agents/ → fixtures/로 이름 변경.

**작업 내용**

`backend/main.py` 449줄 → 24줄 (앱 생성 + CORS + 라우터 등록만). `services/storage.py` — 파일 I/O 전담. `services/pipeline.py` — 백그라운드 실행 전담. `routers/` 5개 파일 분리. `frontend/src/api/client.js` 8개 API 함수 중앙화. 5개 페이지 inline fetch 제거.

**수정된 파일**
- `backend/main.py` (슬림화)
- `backend/services/storage.py` (신규)
- `backend/services/pipeline.py` (신규)
- `backend/routers/generate.py`, `stream.py`, `jobs.py`, `history.py`, `analytics.py` (신규)
- `frontend/src/api/client.js` (신규)
- `frontend/src/pages/Home.jsx`, `Analyze.jsx`, `Result.jsx`, `History.jsx`, `Analytics.jsx`

---

## 2026-04-27 — 신규 파일 주석 추가

**프롬프트** (Claude Code)
> 구조 재편으로 신규 생성된 9개 파일에 한국어 주석을 추가한다. 각 파일의 역할, 설계 결정 이유, 비직관적 동작을 설명하는 WHY 주석 위주. 함수·상수·모듈 단위로 구체적으로 작성.

**작업 내용**
- `main.py`: 진입점 역할 명시 (로직 없음)
- `services/storage.py`: `USE_MOCK_MODE` 기본값 true 이유, 경로 상수 설명, `load_real_history` 파일 스캔 성능 경고
- `services/pipeline.py`: `job_queues`·`running_jobs` 재시작 시 초기화 경고, blended rate 계산식(30/70 가정), `CancelledError` 재전파 이유, `finally` done 이벤트 보장 이유
- `routers/generate.py`: `uuid4().hex[:8]` 선택 이유, `asyncio.create_task` fire-and-forget 패턴
- `routers/stream.py`: `delay_sec` 클라이언트 노출 제거 이유, `done` 이벤트 루프 종료 조건
- `routers/jobs.py`: 소프트 삭제 정책, `stop`이 `CancelledError`로 연결되는 흐름
- `routers/analytics.py`: cutoff 날짜 lexicographic 비교 방식, 0토큰 항목 포함 이유
- `frontend/src/api/client.js`: Vite 프록시로 baseURL 불필요한 이유, 낙관적 업데이트 연결 설명

**수정된 파일**
- `backend/main.py`, `backend/services/storage.py`, `backend/services/pipeline.py`
- `backend/routers/generate.py`, `stream.py`, `jobs.py`, `history.py`, `analytics.py`
- `frontend/src/api/client.js`

---

## 2026-04-28 — 파일 저장 구조 통합 (result.json)

**프롬프트** (Claude Code)
> 파이프라인 완료 시 생성 파일을 result.json으로 통합한다. { prd, loop_history, events } 구조. GET /result와 extract_title도 result.json 기준으로 수정. prd.md는 최종 산출물로 별도 유지.

**작업 내용**

`prd.md` + `loop_history.json` + `events.json` 3개 파일 → `result.json` 단일 파일로 통합. `prd.md`는 최종 산출물로 별도 보존.

**수정된 파일**
- `backend/services/pipeline.py`
- `backend/routers/jobs.py`
- `backend/services/storage.py`

---

## 2026-04-28 — run.log 블록 로깅 추가

**프롬프트** (Claude Code)
> orchestrator.py를 수정하지 않고 llm.py 콜백 주입으로 에이전트별 I/O를 run.log에 블록 형식으로 기록한다. ContextVar로 동시 job 격리. 블록: [agent] + <입력> + <출력>. 토큰은 [token] 줄로 분리.

**작업 내용**

`ContextVar` 기반 `_block_logger_ctx` / `_token_logger_ctx` 추가 (동시 job 실행 안전). `_TokenHandler`에 `on_chat_model_start` 추가 (입력 캡처), `on_llm_end`에 블록 조립·기록 추가. 블록 형식: `────` 구분선 + `[agent명]` + `<입력>` + `<출력>` 섹션.

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/subagents/planner.py`, `analyst.py`, `critic.py`, `gate.py`, `prd_writer.py`
- `backend/services/pipeline.py`

---

## 2026-04-28 — 토큰 집계 구조 정리

**프롬프트** (Claude Code)
> pipeline.py의 compute_cost를 events에서 직접 토큰 합산하도록 변경한다. token_counts 파라미터 제거. run.log의 토큰 표기를 블록 내 <토큰> 섹션 대신 [token] 한 줄로 통일.

**작업 내용**
- `pipeline.py`: `compute_cost(events, token_counts)` → `compute_cost(events)`. 총합은 `agent_done` events의 tokens 합산으로 계산, `token_counts` 파라미터 제거
- `llm.py`: 블록 내 `<토큰>` 섹션 제거, `[token]` 한 줄 형식으로 통일. `_block_logger_ctx` / `_token_logger_ctx`를 global 변수에서 ContextVar로 교체 (동시 실행 안전)

**AI가 만든 코드 중 수정이 필요했던 부분**
- `_token_counts`는 orchestrator per-agent 델타 패턴에 필요해 제거 불가 — pipeline.py만 분리하고 llm.py의 `_token_counts`는 유지. 직접 파악.

**수정된 파일**
- `backend/services/pipeline.py`
- `backend/agents/llm.py`

---

## 2026-04-28 — Dead code 제거 및 버그 수정

**프롬프트** (Claude Code)
> 코드 전체 의존성 감사. LOGS_DIR dead code 제거, run.py loop summary를 실제 loop_history 구조에 맞게 수정, input_preview 이중 절삭 제거, real analytics를 mock과 동일한 per-model 행 구조로 수정.

**작업 내용**

`config.py` — `LOGS_DIR` 제거. `agents/run.py` — `entry.get("score")` / `entry.get("topic")` → `entry["critics"][-1]["score"]`로 수정. `storage.py` — `input_preview` 이중 절삭 제거. `routers/analytics.py` — per-model 행 구조로 수정.

**AI가 만든 코드 중 수정이 필요했던 부분**
- `run.py`의 `entry["score"]` 접근이 항상 `-` 출력. orchestrator `tool_update_loop_history`가 만드는 구조(`critics[].score`)와 불일치 — 직접 실행 로그 분석으로 발견.
- real analytics가 `model` 필드 없이 job 단위 행을 반환 → 프론트 파이 차트·테이블 모델 컬럼이 모두 `undefined` — 직접 발견.

**수정된 파일**
- `backend/config.py`
- `backend/agents/run.py`
- `backend/services/storage.py`
- `backend/routers/analytics.py`

---

## 2026-04-28 — Real mode 버그 수정 (dotenv 로딩·채팅 버블·PRD 뷰어)

**프롬프트** (Claude Code)
> real mode 실행 시 발견된 버그 수정. (1) USE_MOCK_MODE가 항상 true로 평가되는 dotenv 로딩 순서 문제 (2) History 채팅 버블 미표시 (loop_history 분기 버그) (3) PRD 뷰어 즉시 404 (result.json 타이밍) (4) 채팅 버블 400자 잘림 (5) analytics none 모델 포함 (6) onerror stale closure

**AI가 만든 코드 중 수정이 필요했던 부분**
- `storage.py`가 `os.getenv("USE_MOCK_MODE", "true")`를 import 시점에 평가. `config.py`의 `load_dotenv()`는 에이전트 코드에서만 호출되어 `.env`가 로드되기 전에 평가됨 → 항상 mock mode. **직접 실행 중 발견**. `main.py` 최상단에 `load_dotenv()` 호출 추가.
- `loop_history` 구조(`loop`, `gate_decision`, `critics`)에 `agent`/`output` 필드가 없어 history 채팅 미리보기가 빈 화면. 직접 발견.
- `onerror` 핸들러의 stale closure — `sessionStatus`가 항상 초기값 `'connecting'`으로 캡처. 직접 발견, `doneRef` 방식으로 교체 요청.

**수정된 파일**
- `backend/main.py`, `backend/agents/orchestrator.py`, `backend/services/pipeline.py`, `backend/routers/analytics.py`
- `frontend/src/pages/Analyze.jsx`, `History.jsx`, `Result.jsx`, `Home.jsx`

---

## 2026-04-28 — agent_done timestamp 추가 및 analyst 아이콘 버그 수정

**프롬프트** (Claude Code)
> (1) Analyze·History 채팅 버블에 완료 시각이 표시되지 않는 문제: agent_done 이벤트에 timestamp 필드 추가.
> (2) analyst 에이전트 버블에 critic 프로필 이미지가 표시되는 문제: AGENT_ICON_MAP의 잘못된 매핑 제거.

**작업 내용**
- `orchestrator.py`: 6개 `agent_done` emit에 `"timestamp": datetime.now().strftime("%H:%M:%S")` 추가. `agent_start`에만 timestamp가 있어 History 재구성 시 완료 시각 미표시 문제.
- `ChatBubble.jsx`: `AGENT_ICON_MAP`의 `analyst: 'critic'` 매핑 제거. `analyst.png`가 존재함에도 critic 이미지를 공유하도록 잘못 설정된 상태.

**수정된 파일**
- `backend/agents/orchestrator.py`
- `frontend/src/components/ChatBubble.jsx`

---

## 2026-04-28 — run.log 복원 및 mock 모드 data/jobs/ 전환

**프롬프트** (Claude Code)
> (1) run.log에서 에이전트별 CALL/DONE/START 타임스탬프 줄과 token 로그의 에이전트 태그가 사라진 문제 복원. llm.py에 log_line/log_block 인프라 추가 후 orchestrator.py 각 tool에 로그 삽입.
> (2) mock 모드를 fixtures/ 기반에서 data/jobs/ 실제 완료 job 재생 방식으로 전환. generate는 새 job_id 생성, stream은 에이전트별 딜레이 하드코딩 재생, 나머지 엔드포인트는 real storage 위임.

**작업 내용**

`llm.py` — `log_line()`, `log_block()` 함수 추가. `orchestrator.py` — 각 tool에 `[agent] CALL` 로그 추가, researcher에 수동 `log_block()` 추가.

mock 모드 전면 교체 — fixtures/ 기반 → data/jobs/ 실제 완료 job 재생 방식. `POST /generate`는 가장 최근 완료 job을 source로 선택, 새 job_id 생성. `GET /stream/{job_id}`는 source job의 `result.json` events를 에이전트별 딜레이로 재생 (planner 5s, researcher 2s, analyst 4s, critic 8s, gate 3s, prd_writer 10s).

**AI가 만든 코드 중 수정이 필요했던 부분**
- fixtures/ JSON이 구 버전 포맷이라 채팅 버블·analytics가 깨지는 문제 — **직접 발견**. mock 모드 전면 교체의 직접적인 원인.

**수정된 파일**
- `backend/agents/llm.py`, `backend/agents/orchestrator.py`, `backend/services/pipeline.py`
- `backend/routers/mock.py`
- `frontend/src/pages/History.jsx`

---

## 2026-04-28 — 프론트 → 백엔드 로직 이전 및 UX 개선

**프롬프트** (Claude Code)
> (1) agent_done → agent_start 사이 갭 구간에 세션 활성 표시: 로딩 버블 없는 running 상태를 감지해 점 3개 인디케이터 표시.
> (2) CSV 내보내기를 백엔드 pandas로 전환: GET /analytics/csv 엔드포인트 추가, 프론트 Blob 조립 제거.
> (3) 히스토리 검색·정렬·즐겨찾기 필터를 GET /history 쿼리 파라미터로 이전: 프론트 filter useEffect 제거, 디바운스 추가.
> (4) PRD 다운로드를 백엔드 FileResponse로 전환: GET /result/{job_id}/prd.md 추가.
> (5) Analytics 차트 집계(모델별·날짜별)를 백엔드 pandas로 전환.
> (6) POST /generate에 외부 서비스 연결 검증 추가: TAVILY, OpenRouter 둘 중 하나라도 실패 시 503 반환.

**AI가 만든 코드 중 수정이 필요했던 부분**
- `preflight_check`가 OpenRouter `/models` 200을 기준으로 통과 판정 — 실제 completions 호출은 별도 인증 검증으로 401 "User not found" 반환 가능. safeguard가 오히려 false confidence를 줌. **직접 파악** 후 `/ready` 엔드포인트로 분리 및 개선 요청.
- `compute_cost`에서 `model=None`(researcher emit)으로 `.lower()` AttributeError 발생 — PRD까지 생성된 후 비용 계산 단계에서 터져 result.json은 있지만 meta.json이 failed로 기록됨. `event.get("model") or ""`로 수정.
- analytics `status == "done"` 필터가 위 상황의 job을 집계에서 제외 — `result.json` 존재 여부로 대체.
- 날짜별 막대 차트 줄무늬 버그 — 동일 모델 색이 job 수만큼 반복. `groupby("model")["tokens"].sum()`으로 합산. 직접 발견.

**수정된 파일**
- `frontend/src/pages/Analyze.jsx`, `Analytics.jsx`, `History.jsx`, `Result.jsx`, `Home.jsx`
- `backend/routers/analytics.py`, `history.py`, `jobs.py`, `generate.py`, `mock.py`
- `frontend/src/api/client.js`
- `frontend/src/pages/Home.css`

---

## 2026-04-28 — 파이프라인 에러 처리 강화 및 서비스 상태 확인 개선

**프롬프트** (Claude Code)
> (1) 파이프라인 실패 시에도 "PRD가 완성되었습니다!" 표시되는 문제: done 이벤트에 status 필드 추가, Analyze.jsx에서 분기.
> (2) 파이프라인 에러가 조용히 삼켜지는 문제: logging.exception으로 uvicorn 콘솔에 traceback 출력.
> (3) compute_cost model=None AttributeError: `or ""` 가드 추가.
> (4) analytics가 result.json 있는 job을 status==failed로 제외하는 문제: result.json 존재 여부 기준으로 전환, JSON 파싱 방어 추가.
> (5) preflight_check 제거: /ready 엔드포인트로 대체, 홈 진입 시 서비스 상태 배너 표시.
> (6) 날짜별 막대 차트 줄무늬 버그: _compute_date_aggregates에서 모델별 groupby 합산.

**작업 내용**
- `done` 이벤트에 `status` 필드(done/stopped/failed) 추가. `Analyze.jsx` — `done.status` 값으로 sessionStatus 분기 (failed → `'error'`, stopped → `'stopped'`)
- `pipeline.py` — `except Exception` 블록에 `logging.exception` 추가 (uvicorn 콘솔 traceback 출력)
- `compute_cost` — `event.get("model", "")` → `event.get("model") or ""` (researcher model=None 대응)
- `analytics.py` — `status == "done"` 필터 → `result.json` 존재 여부로 대체, JSON 파싱 `try/except` 추가
- `preflight_check` 제거 → `GET /ready` 엔드포인트 신설. OpenRouter + Tavily 접속 가능 여부 반환. `Home.jsx` — 진입 시 `getReady()` 호출, degraded 시 경고 배너 표시
- `_compute_date_aggregates()` — 동일 날짜 모델별 `groupby("model")["tokens"].sum()` 합산 (줄무늬 버그 수정)

**발견된 문제점**
- `preflight_check`가 OpenRouter `/models` 200 응답을 기준으로 통과 판정했으나, 실제 inference 호출은 별도 인증 검증으로 401 반환 가능 — **직접 파악** 후 구조 개선 요청
- `compute_cost`에서 `model=None` AttributeError — PRD까지 생성된 후 비용 계산 단계에서 터져 result.json은 있지만 meta.json이 failed로 기록되는 상황 발생. **직접 실행 중 발견**
- analytics `status == "done"` 필터가 위 상황의 job을 집계에서 제외하는 연쇄 문제. **직접 발견**

**수정된 파일**
- `backend/services/pipeline.py`, `backend/routers/mock.py`, `backend/routers/analytics.py`
- `backend/routers/generate.py`, `backend/main.py`
- `frontend/src/pages/Analyze.jsx`, `frontend/src/components/ChatBubble.jsx`
- `frontend/src/api/client.js`, `frontend/src/pages/Home.jsx`, `frontend/src/pages/Home.css`

---

---

# 단계 5 — Docker 통합 버그 수정 및 파비콘 적용

---

## 2026-04-29 — mock 모드 `/analytics/csv` 404 수정

**프롬프트** (Claude Code)
> Docker 환경에서 analytics CSV 내보내기 클릭 시 `{"detail":"Not Found"}` 반환. 원인 파악 및 수정.

**발견된 문제점**
`routers/mock.py`에 `/analytics/csv` 엔드포인트가 누락되어 있었음. `/analytics`는 real 라우터에 위임하는 코드가 있었으나 csv만 빠진 상태. mock 모드에서 analytics 라우터 자체가 등록되지 않으므로 해당 경로가 존재하지 않아 404 반환.

**작업 내용**
`routers/mock.py`에 `GET /analytics/csv` 엔드포인트 추가 — `routers/analytics.analytics_csv`에 위임.

**수정된 파일**
- `backend/routers/mock.py`

---

## 2026-04-29 — nginx 라우팅 개선 (브라우저 직접 접근 · 파일 다운로드)

**프롬프트** (Claude Code)
> Docker 환경에서 두 가지 문제 수정. (1) `/history`, `/result/:id`, `/analytics` 등 공유 경로를 브라우저에서 직접 접근(새로고침)하면 React 앱 대신 JSON이 그대로 표시됨. (2) CSV·md 파일 다운로드 경로도 동일하게 오류 메시지만 표시됨. Vite 개발 서버의 `bypassNav` 로직과 동일하게 nginx에서 처리.

**발견된 문제점**
기존 nginx 설정은 `/history`, `/result`, `/analytics` 등을 Accept 헤더와 무관하게 무조건 백엔드로 프록시. Vite dev 서버는 `bypassNav` 함수로 `Accept: text/html`(브라우저 직접 접근)이면 프록시를 우회해 `index.html`을 서빙하고, fetch 호출이면 백엔드로 프록시하는 분기가 있었음. Docker 배포 시 이 로직이 nginx에 존재하지 않아 발생.

**작업 내용**
`nginx.conf` 전면 재작성:
- `/analytics/csv` — `^~` 수식자로 regex보다 우선 적용, 항상 백엔드 프록시 (CSV 다운로드)
- `/result/.../prd.md` — regex로 먼저 매칭, 항상 백엔드 프록시 (md 다운로드)
- `/result`, `/history`, `/analytics` — `$http_accept ~* text/html`이면 `rewrite ^ /index.html last`로 React 앱 서빙, 그 외(fetch)는 백엔드 프록시

**수정된 파일**
- `nginx.conf`

---

## 2026-04-29 — 파비콘 교체 및 여백 제거

**프롬프트** (Claude Code)
> 프로젝트 루트의 `favicon.png`를 적절한 위치로 이동하고 파비콘으로 적용. 이미지 여백 제거.

**작업 내용**
- `favicon.png`를 `frontend/public/favicon.png`로 이동 (루트 원본 삭제)
- `frontend/index.html` — `favicon.svg` → `favicon.png`로 변경 (`type="image/png"`)
- ImageMagick으로 이미지 콘텐츠 경계 분석 후 Python Pillow로 정사각형 크롭 (1500×1023 → 659×659, 여백 30px 포함)

**수정된 파일**
- `frontend/public/favicon.png` (신규, 루트 `favicon.png` 이동 후 크롭)
- `frontend/index.html`