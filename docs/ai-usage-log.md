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

**기획**: Claude 세션에서 6개 에이전트 프롬프트 설계 및 최적화. 프롬프트 설명 + 프로젝트 흐름 구조 설명 문서(`PROMPT.md` 참고) 작성.

**코드**: Claude Code에 위 문서를 전달하여 구현. `.claudeignore`로 `/venv`, `__pycache__`, `.env` 제외.

**검수 방식**: `run.log`로 에이전트별 I/O 직접 분석 → 프롬프트 수정 → 코드 재반영 반복.

---

## 2026-04-27 — 서브에이전트 create_deep_agent 패턴 전환

**프롬프트** (`docs/prompts/` — Claude 세션 직접 작성)
> 서브에이전트 5개를 create_deep_agent 패턴으로 리팩토링해줘. 역할 정의는 system_prompt에, 데이터는 HumanMessage로 분리하고, ainvoke 결과는 extract_content()로 추출해줘.

**작업 내용**

`llm.py` 재구성 — `call_llm()`, `_get_client()` 등 구형 OpenAI 직접 호출 제거, `create_llm(model, max_tokens)` / `load_prompt(agent_name)` / `extract_content(result)` 추가.

서브에이전트 5개 (critic, analyst, planner, gate, prd_writer) 전환 — 모듈 레벨에서 `create_deep_agent` 인스턴스 생성, `HumanMessage`로 데이터 전달. `analyst.py`의 `**kwargs` → 명시적 파라미터 (`researcher_result: str = "없음"`, `critic_feedback: str = "없음"`). `planner.py`의 프롬프트 내 `{critic_feedback}` 버그 → `gate_feedback`으로 수정.

**AI가 만든 코드 중 수정이 필요했던 부분**
- `extract_content`가 `_extract_content`로 private 명명 — 5개 서브에이전트에서 외부 참조하는 함수임에도 private 처리. 직접 발견 후 수정 요청.
- 데이터를 HumanMessage로 이동하면서 시스템 프롬프트에 입력 구조 안내 누락 → LLM이 어떤 형식으로 입력을 받는지 인지하지 못하는 문제. 직접 발견 후 `## 입력 형식` 섹션 추가 요청.

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/subagents/analyst.py`, `critic.py`, `planner.py`, `gate.py`, `prd_writer.py`
- `backend/agents/prompts/analyst.md`, `critic.md`, `planner.md`, `gate.md`, `prd_writer.md`

---

## 2026-04-27 — orchestrator.py 정리 및 버그픽스

**프롬프트** (Claude Code)
> 래핑 계층이 너무 중첩되어 있어. _call 래퍼를 포함해서 불필요한 계층 전부 제거하고 단순하게 정리해줘.
> utils.py의 check_loop_limit 로직을 orchestrator로 인라인해서 파일을 합쳐줘.

**작업 내용**

`_call()` 래퍼 함수 제거, `check_loop_limit` 툴 orchestrator에 인라인 (CONTINUE / FORCE_GATE / FORCE_PRD). `utils.py` 삭제.

**AI가 만든 코드 중 수정이 필요했던 부분**
- `_last_critic_result` 전역 변수를 이유 없이 제거 → FORCE_GATE 시 이전 critic 결과 전달 여부 검토 필요. 직접 실행 로그 분석 후 orchestrator 컨텍스트에 이미 보존됨을 확인하고 제거 결정.
- tool_get_last_critic_result를 불필요하게 추가 → 직접 발견 후 제거 요청.

**수정된 파일**
- `backend/agents/orchestrator.py`
- `backend/agents/utils.py` (삭제)

---

## 2026-04-27 — 서브에이전트 vanilla LLM 전환 및 analyst 맥락 보강

**프롬프트** (Claude Code)
> create_deep_agent 미들웨어 문제로 빈 출력 발생 확인. analyst, critic 등 단순 텍스트 입출력 서브에이전트를 create_llm().ainvoke() 방식으로 교체해줘. analyst에 current_topic도 주입해줘.
> analyst한테 넣어주는 planner 결과는 TOPIC과 DESCRIPTION만 전달하자.
> create_deep_agent 코드 흔적 지우고, llm.py에 한 줄로 이유만 남겨줘.

**작업 내용**

서브에이전트 5개 `create_deep_agent` → `ChatOpenAI` 직접 호출로 전환. `_llm.ainvoke([SystemMessage(_prompt), HumanMessage(...)])` 패턴. `analyst`에 `current_topic: str = ""` 파라미터 추가.

**AI가 만든 코드 중 수정이 필요했던 부분**
- create_deep_agent 선택 파라미터 빈 값 처리 문제는 **AI가 아닌 직접 발견** — 실행 로그(`run.log`) 비교 분석을 통해 동일 입력에서 deepagent만 빈 출력 재현. 원인: create_deep_agent 내부 미들웨어가 선택 파라미터 빈 값 시 응답 생성 포기. vanilla LLM 최종 확정 후 Claude Code에 전환 요청.
- researcher.py: `async def researcher_agent` → `def researcher_agent` (sync 복원). Tavily 클라이언트가 sync API인데 async 함수로 정의하면 코루틴 객체가 반환되어 결과 유실. 직접 실행 중 발견.

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/orchestrator.py`
- `backend/agents/subagents/analyst.py`, `critic.py`, `planner.py`, `gate.py`, `prd_writer.py`
- `backend/agents/prompts/analyst.md`
- `backend/agents/subagents/researcher.py`

---

---

# 단계 2 — Mock FastAPI 구현

**배경**: 실제 에이전트 실행을 프론트엔드 개발 단계에서 매번 할 수 없어, 이전 실행 로그를 에이전트 실행처럼 SSE 스트리밍으로 반환하는 Mock API 구현.

---

## 2026-04-27 — FastAPI Mock API 구현

**프롬프트** (`docs/prompts/mock_fastapi.md`)

**작업 내용**

`backend/main.py` 생성 — 5개 엔드포인트(POST /generate, GET /stream/{job_id}, GET /result/{job_id}, GET /history, GET /analytics). SSE 스트리밍 시 `delay_sec` 필드 제외하고 전송. `ensure_ascii=False`로 한글 처리.

**AI가 만든 코드 중 수정이 필요했던 부분**
- Mock 데이터 경로를 프롬프트의 `mock/`가 아닌 `mock_agents/`로 자동 감지 — 실행 전 직접 확인.
- analytics 응답이 하드코딩 — 이후 real mode 전환 시 수정사항이 많다는 한계 직접 파악.

**수정된 파일**
- `backend/main.py` (신규)
- `backend/requirements.txt`

---

## 2026-04-27 — Mock/Real 모드 전환 구조 추가

**프롬프트** (`docs/prompts/mock_fastapi_refactor.md`)

**작업 내용**

`USE_MOCK_MODE` 환경변수로 모드 구분. Mock 모드는 현재 동작 유지, Real 모드는 501 반환. 함수명에 `mock_` prefix 추가.

**AI가 만든 코드 중 수정이 필요했던 부분**
- USE_MOCK_MODE 기본값이 `false`로 설정되어 프론트엔드 개발 중 실행하면 모든 엔드포인트 501 반환. 직접 발견 후 `true`로 수정.

**수정된 파일**
- `backend/main.py`

---

---

# 단계 3 — 프론트엔드 Ralph Loop

**Ralph Loop 선정 이유**
- 전체를 직접 구현해보고 싶기도 하고, Claude Code Pro 요금제 제약 존재
- 바이브 코딩의 결과물을 시각적으로 확인하고 검증할 수 있다는 장점

**완전한 Ralph Loop와의 차이점**
- 프롬프트 및 구현 기획을 Claude 세션과 대화하며 사전에 구체적으로 작성 (`docs/prompts/ralph_prompt.md`)
- 프롬프트가 상당히 구체적이어서 Claude Code는 세부 디자인과 코드 구현만 담당
- `ralph_mode.sh`로 자동 실행: 루프 번호 누적 추적, `FRONTEND_COMPLETE` 태그로 완료 감지, 각 루프마다 git commit 자동화

**Ralph Loop 전체 변화 요약 (`docs/ralph-log.md` 참고)**

| 루프 | 주요 변화 | 개선 포인트 |
|---|---|---|
| Loop 1 | 5개 페이지 전체 초기 생성 (Home, Analyze, History, Result, Analytics) | 기본 구조·레이아웃·SSE 연결·react-markdown 적용 |
| Loop 2 | API 연동 수정 (Vite 프록시, POST body 필드명, CORS 포트) | analytics 응답 형식 대응, stop/favorite/delete 엔드포인트 추가 |
| Loop 3 | connecting 상태 UI, NotFound 페이지, 빌드 최종 확인 | `FRONTEND_COMPLETE` 태그로 1차 완료 선언 |
| Loop 4 | remark-gfm으로 테이블 수정, TOC sticky, Chip 이모티콘화, 하트 SVG화 | 즐겨찾기 필터 구현, ctrl+s 세션 종료 방지 |
| Loop 5 | TOC sticky → flex min-height:0 방식 재수정, PRD Writer 버튼 교체 | ChatBubble MD 헤더 bold만 적용, Vite proxy bypass |
| Loop 6 | TOC overflow:hidden 고정, AGENT_MESSAGES·AGENT_COLORS 상수 추가 | bubble-wrapper 65%로 축소, prdReady 중복 제거 |
| Loop 7 | **html/body height:100% + overflow:hidden — 스크롤 근본 원인 해결** | 자동 PRD 이동 제거 (버튼 클릭으로만), user 아바타 우측 고정 |
| Loop 8 | bubble 65%로 재조정, 에이전트 이미지 public/ 동기화 | ColumnChart 도입, prd_writer 중복 버블 제거 |
| Loop 9 | SVG 기반 ColumnChart 전면 교체 (hover 툴팁, 애니메이션) | 파이차트 레이아웃 개선, PRD Viewer 좌우 여백 |
| Loop 10 | analytics 동적 집계 (model별 토큰), soft delete 영구화 | 비용 컬럼 제거, history.json 구조 개선 |
| Loop 11 | 날짜별 모델 스택 막대차트, 파이차트 hover 툴팁 | 전체 페이지 2컬럼 레이아웃 재구성 |

---

**AI가 만든 코드 중 수정이 필요했던 부분**

1. **스크롤 버그 — 7회 반복 끝에 근본 원인 해결** (Loop 4~7)
   - Claude Code가 증상("TOC가 같이 스크롤됨")을 보고 컴포넌트 레벨에서만 반복 시도 — `position: sticky`, `min-height: 0 + overflow: hidden`, `overflow: hidden` 등 매번 안쪽에서 접근
   - 실제 원인: 브라우저가 body 레벨에서 스크롤바를 그리고 있었음. 하위 컴포넌트에서 아무리 `overflow: hidden`을 걸어도 body의 네이티브 스크롤은 차단 불가.
   - 해결: `html/body { height: 100%; overflow: hidden; }` — min-height: 100vh → height: 100% 전환.
   - 교훈: CSS 스크롤 격리는 html → body → #root → main 전체 체인이 height로 고정되어야 동작. 브라우저 DevTools 확인 없이 추론만으로 판단하는 한계.

2. **git commit 범위 문제** — 본인이 수정한 파일만 commit하고 나머지는 누락. 롤백 요청 시 확인 없이 reset 진행. 다행히 브라우저 탭이 열려있어 ctrl+z로 복구. 이후 commit 전 직접 `git status` 확인.

3. **node_modules gitignore 누락** — .gitignore이 Python 기준으로만 되어 있어 node_modules가 'U'로 표시됨. 루프 실행 중 직접 .gitignore에 추가.

4. **USE_MOCK_MODE 기본값** — Loop 실행 중 실제 에이전트 실행 없이도 FastAPI에 연결되어야 하는데 real mode(501)가 기본값이라 모든 API 호출이 실패. 직접 .env 수정으로 해결.

---

---

# 단계 4 — 백엔드 Real Mode 구현 (`feature/backend`)

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

**프롬프트** (`docs/prompts/backend_log_phse1.md`)

**작업 내용**

asyncio.Queue 기반 이벤트 브릿지로 orchestrator ↔ SSE 스트림 연결. `job_queues`, `running_jobs` 인메모리 상태 추가. `_run_pipeline()` — orchestrator 백그라운드 실행, 결과 파일 저장, 예외/취소 처리, finally에서 done 이벤트 보장. 30분 타임아웃.

저장 구조 (`data/jobs/{job_id}/`): `input.txt`, `meta.json`, `prd.md`, `loop_history.json`, `events.json`

**수정된 파일**
- `backend/main.py`

---

## 2026-04-27 — FastAPI real mode 구현 (Phase 2)

**프롬프트** (`docs/prompts/backend_log_phse2.md`)

**작업 내용**

나머지 4개 엔드포인트 real mode 전환. pandas DataFrame으로 analytics 집계, range 필터(`today/7days/30days/all`) 지원. `GET /history` — data/jobs/ 전체 스캔, deleted 제외. `PATCH favorite`, `DELETE` — meta.json 기반 소프트 삭제.

**수정된 파일**
- `backend/main.py`
- `backend/requirements.txt`

---

## 2026-04-27 — 토큰 집계 수정 (Phase 2.5)

**프롬프트** (`docs/prompts/backend_log_phse2_5.md`)

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