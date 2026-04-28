# AI Usage Log — feature/backend

> 이 로그는 `feature/backend` 브랜치 작업부터 기록합니다.

---

## 2026-04-27 — orchestrator 이벤트 우선 구조 전환

**작업 내용**

orchestrator.py의 출력 구조를 로그 파일 중심에서 이벤트 스트림 중심으로 전환.
기존에는 `_log_block` + 파일 핸들러가 주된 출력 경로였으나, FastAPI SSE 연동을 위해
`_emit()`이 1차 출력이 되고 로그는 나중에 이벤트에서 파생하는 구조로 변경.

- 제거: `logging`, `_logger`, `_setup_logger`, `_log_block`, `set_token_logger`, `LOGS_DIR` import
- 추가: `asyncio`, `datetime` import
- 추가: `_event_queue: asyncio.Queue | None` — SSE 브릿지 (None이면 CLI 모드)
- 추가: `_events: list` — 전체 이벤트 수집, `run()` 반환값에 포함
- 추가: `_emit(event)` — `_events` append + queue.put (queue 없으면 리스트만)
- 수정: `tool_planner / tool_researcher / tool_analyst / tool_critic / tool_gate / tool_prd_writer` — 각 호출 전후에 `agent_start / agent_progress / agent_done` emit
- 수정: `tool_update_loop_history`, `check_loop_limit` — `_logger.info` 제거
- 수정: `run()` 시그니처 — `event_queue` 파라미터 추가, 반환에 `events` 포함
- 추가: `MODEL_LIGHT` import (analyst/gate 모델명 이벤트 기록용)

**수정된 파일**
- `backend/agents/orchestrator.py`

**발견된 문제점**
초기 Write에서 WHY 주석 전체 삭제 — 기존 주석을 그대로 보존해야 했음.
두 번째 Write에서 복원 완료.

**프롬프트**
orchestrator의 출력 구조를 로그 파일 중심에서 이벤트 스트림 중심으로 재설계.
각 에이전트 호출 시 agent_start/agent_progress/agent_done 이벤트를 emit하고,
run() 반환값에 events 리스트를 포함시킨다. 기존 주석과 로직은 그대로 유지.

---

## 2026-04-27 — FastAPI real mode 구현 (Phase 1)

**작업 내용**

`USE_MOCK_MODE=false` 시 501을 반환하던 엔드포인트에 실제 동작 구현.
`asyncio.Queue` 기반 이벤트 브릿지로 orchestrator ↔ SSE 스트림 연결.

- 추가: `DATA_DIR = Path / "data" / "jobs"` — job별 파일 저장 경로
- 추가: `job_queues: dict[str, asyncio.Queue]` — SSE 스트림용 큐 (인메모리)
- 추가: `running_jobs: dict[str, asyncio.Task]` — 실행 중 태스크 추적
- 추가: `_run_pipeline(job_id, user_input, queue)` — orchestrator 백그라운드 실행, 결과 파일 저장, 예외/취소 처리, finally에서 done 이벤트 보장
- 수정: `POST /generate` real mode — uuid4 job_id 생성, data/jobs/{id}/ 폴더 초기화, asyncio.create_task로 백그라운드 실행
- 추가: `real_event_stream(queue)` — queue에서 pop하여 done까지 SSE 스트리밍
- 수정: `GET /stream/{job_id}` real mode — job_queues에서 큐 조회, 없으면 404
- 수정: `GET /result/{job_id}` real mode — prd.md 없으면 404, loop_history.json + events.json 함께 반환
- 수정: `POST /jobs/{job_id}/stop` real mode — running_jobs에서 task.cancel()
- 유지: `GET /history`, `GET /analytics`, `PATCH /jobs/:id/favorite`, `DELETE /jobs/:id` — 모드 무관하게 mock 데이터 사용 (TODO 명시)

저장 구조 (`data/jobs/{job_id}/`):
- `input.txt` — 사용자 입력
- `meta.json` — status, created_at, duration_sec (완료 시), error (실패 시)
- `prd.md` — 최종 PRD
- `loop_history.json` — 루프 히스토리
- `events.json` — 전체 이벤트 로그

**수정된 파일**
- `backend/main.py`

**프롬프트**
asyncio.Queue 기반 이벤트 브릿지를 사용하여 FastAPI real mode를 구현한다.
POST /generate는 백그라운드 태스크를 시작하고, GET /stream/{job_id}는 큐에서
이벤트를 SSE로 스트리밍한다. 30분 타임아웃, 취소/실패 처리 포함.
history/analytics/favorite/delete는 Phase 2에서 real mode 전환 예정.

---

## 2026-04-27 — FastAPI real mode 구현 (Phase 2)

**작업 내용**

나머지 4개 엔드포인트 real mode 전환 + pandas 기반 analytics 구현.

- 추가: `_read_meta(job_id)` / `_write_meta(job_id, meta)` — meta.json 읽기/쓰기 공통 헬퍼
- 추가: `_extract_title(job_dir)` — prd.md 첫 번째 `# ` 줄에서 제목 추출
- 추가: `_load_real_history()` — data/jobs/ 전체 스캔, created_at 내림차순 정렬
- 추가: `_real_analytics(range_param)` — pandas DataFrame 집계, range 필터 지원
- 추가: `_mock_analytics(range_param)` — 기존 analytics 로직 분리
- 수정: `GET /history` real mode — `_load_real_history()` 호출, deleted 제외
- 수정: `GET /analytics` real mode — `_real_analytics()` 호출 (status=="done" 필터)
- 수정: `PATCH /jobs/{job_id}/favorite` real mode — meta.json favorite 토글
- 수정: `DELETE /jobs/{job_id}` real mode — meta.json deleted: true 소프트 삭제
- 수정: `_run_pipeline` — events에서 total_tokens 집계, meta.json에 tokens/cost 저장
- 수정: `POST /generate` — meta.json 초기값에 favorite/deleted 필드 포함
- 추가: `requirements.txt` — pandas>=2.0.0

**수정된 파일**
- `backend/main.py`
- `backend/requirements.txt`

**프롬프트**
GET /history, GET /analytics, PATCH favorite, DELETE 엔드포인트를 data/jobs/ 기반 real mode로 전환한다.
analytics는 pandas DataFrame으로 집계하고 range 파라미터(today/7days/30days/all)를 지원한다.
mock mode 분기는 반드시 유지. data/jobs/ 없으면 빈 배열 반환.

---

## 2026-04-27 — 토큰 집계 수정 (Phase 2.5)

**작업 내용**

`meta.json`의 tokens/cost가 항상 0으로 저장되던 문제 수정.
`llm.py`의 `_TokenHandler`가 logging만 하고 누산하지 않던 구조를 개선.

- 수정: `llm.py` — `_token_counts: dict[str, dict[str, int]]` 모듈 상태 추가
- 수정: `_TokenHandler.on_llm_end` — `_token_counts`에 prompt/completion/total 누산 (logging 유지)
- 추가: `reset_token_counts()` / `get_token_counts()` / `get_total_tokens()`
- 추가: `_token_delta(tokens_before)` 헬퍼 — 호출 전후 스냅샷 차이로 per-agent 토큰 계산
- 수정: `tool_planner / tool_analyst / tool_critic / tool_gate / tool_prd_writer` — agent_done의 tokens 필드 실제값으로 업데이트
- 수정: `run()` — `reset_token_counts()` 추가, 반환값에 `token_counts` 포함
- 추가: `main.py` — `_PRICING` + `_compute_cost(token_counts)` (haiku/sonnet 단가 분기)
- 수정: `_run_pipeline` — `result["token_counts"]`에서 tokens/cost 계산, meta.json 저장

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/orchestrator.py`
- `backend/main.py`

**프롬프트**
llm.py의 _TokenHandler를 수정해 토큰 누산 카운터를 추가하고,
orchestrator 각 tool에서 호출 전후 스냅샷으로 per-agent 토큰을 계산한다.
run() 반환값에 token_counts를 포함시키고, main.py에서 sonnet/haiku 단가로 cost를 계산해 meta.json에 저장한다.

---

## 2026-04-27 — 프로젝트 트리 구조 재편 (routers/services 분리 + 프론트엔드 API 레이어)

**작업 내용**

`backend/main.py` 449줄 단일 파일을 routers/ · services/ 레이어로 분리.
프론트엔드 각 페이지의 inline fetch를 `api/client.js`로 중앙화.
`mock_agents/` → `fixtures/` 이름 변경 (git mv).

- 슬림화: `backend/main.py` 449줄 → 24줄 (앱 생성 + CORS 설정 + 라우터 등록만)
- 추가: `backend/services/storage.py` — 파일 I/O 전담. `USE_MOCK_MODE` · `MOCK_DIR` · `DATA_DIR` 상수, mock 헬퍼(load_mock / load_history / save_history), real 헬퍼(read_meta / write_meta / extract_title / load_real_history)
- 추가: `backend/services/pipeline.py` — 백그라운드 실행 전담. `job_queues` · `running_jobs` 인메모리 상태, `_BLENDED_RATE` · `compute_cost`, `run_pipeline` (orchestrator 호출, 결과 파일 저장, 예외/취소 처리, done 이벤트 보장)
- 추가: `backend/routers/generate.py` — `POST /generate`
- 추가: `backend/routers/stream.py` — `GET /stream/{job_id}` (mock 딜레이 시뮬레이션 · real Queue 스트림)
- 추가: `backend/routers/jobs.py` — `GET /result/{job_id}` · `PATCH /jobs/{id}/favorite` · `POST /jobs/{id}/stop` · `DELETE /jobs/{id}`
- 추가: `backend/routers/history.py` — `GET /history`
- 추가: `backend/routers/analytics.py` — `GET /analytics` (`_mock_analytics` · `_real_analytics` 포함)
- 추가: `frontend/src/api/client.js` — `generateIdea` · `createEventStream` · `stopJob` · `getResult` · `getHistory` · `toggleFavorite` · `deleteJob` · `getAnalytics` 8개 함수
- 수정: `frontend/src/pages/Home.jsx` — inline fetch → `generateIdea` 호출
- 수정: `frontend/src/pages/Analyze.jsx` — `new EventSource` → `createEventStream`, inline fetch → `stopJob`
- 수정: `frontend/src/pages/Result.jsx` — inline fetch → `getResult`
- 수정: `frontend/src/pages/History.jsx` — inline fetch 3곳 → `getHistory` · `getResult` · `toggleFavorite` · `deleteJob`
- 수정: `frontend/src/pages/Analytics.jsx` — inline fetch → `getAnalytics`
- 이름 변경: `backend/mock_agents/` → `backend/fixtures/` (git mv, 히스토리 보존)
- 수정: `CLAUDE.md` 프로젝트 구조 섹션

**수정된 파일**
- `backend/main.py`
- `backend/services/storage.py` (신규)
- `backend/services/pipeline.py` (신규)
- `backend/routers/generate.py` (신규)
- `backend/routers/stream.py` (신규)
- `backend/routers/jobs.py` (신규)
- `backend/routers/history.py` (신규)
- `backend/routers/analytics.py` (신규)
- `frontend/src/api/client.js` (신규)
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/pages/Result.jsx`
- `frontend/src/pages/History.jsx`
- `frontend/src/pages/Analytics.jsx`
- `backend/mock_agents/` → `backend/fixtures/` (이름 변경)
- `CLAUDE.md`

**프롬프트**
프로젝트를 웹 서비스 구조로 재편한다. `backend/main.py`의 모든 라우터·헬퍼 로직을 엔드포인트별 `routers/` 파일과 역할별 `services/` 파일로 분리. 프론트엔드에 `src/api/client.js` API 레이어를 추가해 각 페이지의 inline fetch를 제거. `mock_agents/` → `fixtures/`로 이름 변경.

---

## 2026-04-27 — 신규 파일 주석 추가

**작업 내용**

구조 재편으로 신규 생성된 9개 파일에 한국어 WHY 주석 추가.
설계 결정 이유, 비직관적 동작, 주의사항 위주로 작성.

- `backend/main.py`: 진입점 역할 명시 (로직 없음)
- `backend/services/storage.py`: `USE_MOCK_MODE` 기본값 true 이유, 경로 상수 설명, 함수별 docstring, `load_real_history` 파일 스캔 방식 성능 경고
- `backend/services/pipeline.py`: `job_queues` · `running_jobs` 재시작 시 초기화 경고, blended rate 계산식(30/70 가정) 명시, `run_pipeline` 전체 흐름 docstring, `CancelledError` 재전파 이유, `finally` done 이벤트 보장 이유
- `backend/routers/generate.py`: `uuid4().hex[:8]` 8자리 선택 이유, `asyncio.create_task` fire-and-forget 패턴, mock 고정 job_id 설명
- `backend/routers/stream.py`: `delay_sec` 클라이언트 노출 제거 이유, `done` 이벤트로 루프 종료 조건
- `backend/routers/jobs.py`: 파일 상단 엔드포인트 목록 주석, 소프트 삭제 정책, `stop`이 `CancelledError`로 연결되는 흐름
- `backend/routers/history.py`: `deleted` 필터링 소프트 삭제 정책 명시
- `backend/routers/analytics.py`: cutoff 날짜 문자열 lexicographic 비교 방식, 0토큰 mock 항목 rows 포함 이유
- `frontend/src/api/client.js`: Vite 프록시로 baseURL 불필요한 이유, 각 함수의 엔드포인트·반환형·사용처, 낙관적 업데이트 연결 설명, `stopJob` 응답값 미사용 이유

**수정된 파일**
- `backend/main.py`
- `backend/services/storage.py`
- `backend/services/pipeline.py`
- `backend/routers/generate.py`
- `backend/routers/stream.py`
- `backend/routers/jobs.py`
- `backend/routers/history.py`
- `backend/routers/analytics.py`
- `frontend/src/api/client.js`

**프롬프트**
구조 재편으로 신규 생성된 9개 파일에 한국어 주석을 추가한다. 각 파일의 역할, 설계 결정 이유, 비직관적 동작을 설명하는 WHY 주석 위주. 함수·상수·모듈 단위로 구체적으로 작성.

---

## 2026-04-28 — 파일 저장 구조 통합 (result.json)

**작업 내용**

파이프라인 완료 시 생성되던 `prd.md` + `loop_history.json` + `events.json` 3개 파일을 `result.json` 단일 파일로 통합. `prd.md`는 최종 산출물로 별도 보존.

- 수정: `pipeline.py` — `result.json` 저장으로 변경, `prd.md` 별도 저장 유지
- 수정: `routers/jobs.py` — `GET /result/{job_id}` 가 `result.json` 에서 읽도록 변경 (기존 prd.md + loop_history.json + events.json 3파일 개별 읽기 제거)
- 수정: `services/storage.py` — `extract_title()` 이 `result.json` 의 prd 필드에서 제목 추출하도록 변경 (기존 prd.md 직접 읽기 제거)

**수정된 파일**
- `backend/services/pipeline.py`
- `backend/routers/jobs.py`
- `backend/services/storage.py`

**프롬프트**
파이프라인 완료 시 생성 파일을 result.json으로 통합한다. { prd, loop_history, events } 구조. GET /result와 extract_title도 result.json 기준으로 수정. prd.md는 최종 산출물로 별도 유지.

---

## 2026-04-28 — run.log 블록 로깅 추가

**작업 내용**

에이전트별 I/O를 `data/jobs/{job_id}/run.log`에 블록 형식으로 기록하는 기능 추가. orchestrator.py 수정 없이 `llm.py` 콜백 주입 방식으로 구현.

- 수정: `llm.py` — `ContextVar` 기반 `_block_logger_ctx` / `_token_logger_ctx` 추가 (동시 job 실행 안전). `_TokenHandler`에 `on_chat_model_start` 추가 (입력 캡처), `on_llm_end`에 블록 조립·기록 추가. `create_llm(agent_name)` 파라미터 추가
- 수정: `subagents/planner.py` / `analyst.py` / `critic.py` / `gate.py` / `prd_writer.py` — `create_llm(agent_name=...)` 지정
- 수정: `pipeline.py` — `_make_run_logger()` 추가, `run_pipeline` 시작 시 `set_block_logger` + `set_token_logger` 주입, finally에서 해제

블록 형식: `────` 구분선 + `[agent명]` + `<입력>` + `<출력>` 섹션. `[token]` 줄은 별도 기록.

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/subagents/planner.py`
- `backend/agents/subagents/analyst.py`
- `backend/agents/subagents/critic.py`
- `backend/agents/subagents/gate.py`
- `backend/agents/subagents/prd_writer.py`
- `backend/services/pipeline.py`

**프롬프트**
orchestrator.py를 수정하지 않고 llm.py 콜백 주입으로 에이전트별 I/O를 run.log에 블록 형식으로 기록한다. ContextVar로 동시 job 격리. 블록: [agent] + <입력> + <출력>. 토큰은 [token] 줄로 분리.

---

## 2026-04-28 — 토큰 집계 구조 정리

**작업 내용**

`pipeline.py`가 `result["token_counts"]`(orchestrator 내부 누산값)에 의존하던 구조를 제거. events에서 직접 합산하도록 변경. `<토큰>` 블록 섹션 제거, `[token]` 한 줄 형식으로 통일.

- 수정: `pipeline.py` — `compute_cost(events, token_counts)` → `compute_cost(events)`. 총합은 agent_done events의 tokens 합산으로 계산. `token_counts` 파라미터 제거
- 수정: `llm.py` — 블록 내 `<토큰>` 섹션 제거. `_token_counts` 주석을 orchestrator 델타 계산 전용임을 명시
- 수정: `llm.py` — `_token_logger_ctx` / `_block_logger_ctx` 를 global 변수에서 ContextVar로 교체 (동시 실행 안전)

**발견된 문제점**
`_token_counts`는 orchestrator의 per-agent 델타 패턴(`get_total_tokens()` 전후 스냅샷)에 필요하므로 제거 불가. pipeline.py만 분리.

**수정된 파일**
- `backend/services/pipeline.py`
- `backend/agents/llm.py`

**프롬프트**
pipeline.py의 compute_cost를 events에서 직접 토큰 합산하도록 변경한다. token_counts 파라미터 제거. run.log의 토큰 표기를 블록 내 <토큰> 섹션 대신 [token] 한 줄로 통일.

---

## 2026-04-28 — Dead code 제거 및 버그 수정

**작업 내용**

코드 전체 의존성 감사 후 발견된 dead code 제거와 구조 불일치 버그 수정.

- 수정: `config.py` — `LOGS_DIR` 제거 (정의만 있고 어디서도 import 안 됨)
- 수정: `agents/run.py` — loop summary 출력 코드 수정. `entry.get("score")` / `entry.get("topic")` 는 loop_history 실제 구조에 없는 키 → `entry["critics"][-1]["score"]` 로 수정, topic 출력 제거
- 수정: `services/storage.py` — `input_preview` 에서 `[:100]` 제거. 프론트 History.jsx가 이미 `.slice(0, 100)` 하므로 백엔드에서 이중 절삭 불필요
- 수정: `routers/analytics.py` — real mode analytics를 mock과 동일한 per-model 행 구조로 수정. 기존 job 단위 반환에서 `result.json` events 기반 model별 행으로 변경. pandas 필터링·집계 유지, `job_id.nunique()` / `tokens.sum()` 활용

**발견된 문제점**
- `run.py`의 `entry["score"]` / `entry["topic"]` 접근이 항상 `-` / 빈 문자열을 출력하고 있었음. orchestrator `tool_update_loop_history`가 만드는 구조(`critics[].score`)와 불일치
- real analytics가 `model` 필드 없이 job 단위 행을 반환해 프론트 파이 차트·테이블 모델 컬럼이 모두 `undefined`였음

**수정된 파일**
- `backend/config.py`
- `backend/agents/run.py`
- `backend/services/storage.py`
- `backend/routers/analytics.py`

**프롬프트**
코드 전체 의존성 감사. LOGS_DIR dead code 제거, run.py loop summary를 실제 loop_history 구조에 맞게 수정, input_preview 이중 절삭 제거, real analytics를 mock과 동일한 per-model 행 구조로 수정.

---

## 2026-04-28 — Real mode 버그 수정 (dotenv 로딩·채팅 버블·PRD 뷰어·analytics)

**작업 내용**

실제 실행 중 발견된 버그 6종 수정.

- 수정: `backend/main.py` — `load_dotenv(Path(__file__).parent.parent / ".env")` 를 모든 import보다 먼저 호출. `storage.py`가 import될 때 `os.getenv("USE_MOCK_MODE", "true")`를 평가하므로, 그 전에 .env가 로드되어야 함. 미수정 시 `.env`의 `USE_MOCK_MODE=false`가 무시되고 항상 mock mode로 실행됨
- 수정: `frontend/src/pages/Analyze.jsx` — `onerror` 핸들러의 stale closure 버그 수정. `sessionStatus`가 항상 초기값 `'connecting'`으로 캡처되어 SSE 연결 종료 시 상태가 잘못 설정됨. `doneRef` 추가 후 `done` 이벤트 수신 여부로 판별하도록 변경
- 수정: `backend/agents/orchestrator.py` — 모든 에이전트 `agent_done` 이벤트의 `output: result[:400]` 에서 `[:400]` 제거. 채팅 버블·history 미리보기에 노출되는 출력이 400자에서 잘리던 문제. researcher의 `model: "none"` (문자열) → `model: None` 으로 변경
- 수정: `frontend/src/pages/History.jsx` — `buildChatFromResult`의 `loop_history` 분기 버그 수정. `loop_history` 항목에 `agent`/`output` 필드가 없어서 `if (lh.length > 0)` 진입 후 아무것도 추가하지 않고 `else if (data.events)` 브랜치가 실행되지 않음. filter로 먼저 걸러낸 뒤 length 체크하도록 수정
- 수정: `frontend/src/pages/Result.jsx` — `getResult` 404 시 2초마다 재시도 로직 추가. `prd_writer` `agent_done` 시점에 PRD 보기 버튼을 클릭하면 `result.json`이 아직 없어 404가 반환됨 (result.json은 orchestrator 전체 완료 후 작성)
- 수정: `backend/routers/analytics.py` — `model`이 None이거나 `tokens`가 0인 이벤트 제외. researcher가 `model: None`, `tokens: 0`으로 emit해 analytics에 의미 없는 행이 포함되던 문제. 0토큰 job은 행 추가 없이 skip
- 수정: `frontend/src/pages/Home.jsx` — 에러 메시지에서 "Mock API 서버" 문구 제거
- 수정: `backend/services/pipeline.py` — `finally` 블록에 `job_queues.pop(job_id, None)` 추가. 파이프라인 종료 후 큐가 메모리에서 해제되지 않던 누수 수정

**발견된 문제점**
- `storage.py`가 `os.getenv("USE_MOCK_MODE", "true")`를 import 시점에 평가하는데, `config.py`의 `load_dotenv()`는 에이전트 코드에서만 호출되어 `main.py` import 순서상 `.env`가 로드되기 전에 평가됨 → 항상 mock mode
- `loop_history` 구조(`loop`, `gate_decision`, `critics`)에 `agent`/`output` 필드가 없어 history 채팅 미리보기가 빈 화면으로 표시됨
- `prd_writer` `agent_done` → `result.json` 작성 사이에 타이밍 간격이 있어 PRD 뷰어 즉시 진입 시 404

**수정된 파일**
- `backend/main.py`
- `backend/agents/orchestrator.py`
- `backend/services/pipeline.py`
- `backend/routers/analytics.py`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/pages/History.jsx`
- `frontend/src/pages/Result.jsx`
- `frontend/src/pages/Home.jsx`

**프롬프트**
real mode 실행 시 발견된 버그 수정. (1) USE_MOCK_MODE가 항상 true로 평가되는 dotenv 로딩 순서 문제 (2) History 채팅 버블 미표시 (loop_history 분기 버그) (3) PRD 뷰어 즉시 404 (result.json 타이밍) (4) 채팅 버블 400자 잘림 (5) analytics none 모델 포함 (6) onerror stale closure

---

## 2026-04-28 — agent_done timestamp 추가 및 analyst 아이콘 버그 수정

**작업 내용**

- 수정: `backend/agents/orchestrator.py` — 6개 `agent_done` emit에 `"timestamp": datetime.now().strftime("%H:%M:%S")` 추가. 기존에는 `agent_start`에만 timestamp가 있어 ChatBubble의 `bubble-meta`(시간·토큰 표시 영역)가 완료 후에도 시간을 표시하지 못하는 문제가 있었음. History 페이지 재구성(`buildChatFromResult`) 시 events의 `agent_done`에서 timestamp를 읽으므로 Analyze·History 둘 다 해결
- 수정: `frontend/src/components/ChatBubble.jsx` — `AGENT_ICON_MAP`에서 `analyst: 'critic'` 매핑 제거. `analyst.png`가 존재함에도 `public/agents/` 업로드 누락을 가정하고 critic 이미지를 공유하도록 설정된 상태였음. 파일 존재 확인 후 매핑 삭제, `AGENT_ICON_MAP`은 빈 객체로 유지

**수정된 파일**
- `backend/agents/orchestrator.py`
- `frontend/src/components/ChatBubble.jsx`

**프롬프트**
(1) Analyze·History 채팅 버블에 완료 시각이 표시되지 않는 문제: agent_done 이벤트에 timestamp 필드 추가.
(2) analyst 에이전트 버블에 critic 프로필 이미지가 표시되는 문제: AGENT_ICON_MAP의 잘못된 매핑 제거.

---

## 2026-04-28 — run.log 복원 및 mock 모드 data/jobs/ 전환

**작업 내용**

run.log 로그 포맷 복원과 mock 모드 아키텍처 전면 교체.

**run.log 복원**
- 추가: `backend/agents/llm.py` — `_ts()`, `log_line()`, `log_block()` 함수 추가. `_TokenHandler.on_llm_end`에 `[agent] DONE | preview` 한 줄 + 빈 줄 + 전체 블록(────) 순서로 기록 추가. `on_chat_model_start`에서 HumanMessage 내용 임시 저장(run_id → pending dict) 후 `on_llm_end`에서 블록 입력부로 사용
- 수정: `backend/agents/orchestrator.py` — `log_line` / `log_block` import 추가. 각 tool 함수에 `[agent] CALL` 로그 추가. researcher에 수동 `log_block()` 추가 (LLM 없어 콜백 미사용). `check_loop_limit`에 FORCE_PRD / FORCE_GATE / CONTINUE 세 경우 모두 `[check_loop_limit] outer=X inner=Y → RESULT` 형식 로그 추가. `tool_update_loop_history` critic/gate 모드에 각각 `[tool_update_loop_history] critic | loop=X inner=Y`, `[tool_update_loop_history] gate | loop=X decision=Y` 로그 추가
- 수정: `backend/services/pipeline.py` — `result.json`에 `duration_sec` 필드 추가. history UI에 실행 시간 표시를 위해 누락되어 있었음
- 수정: `frontend/src/pages/History.jsx` — `formatDuration(sec)` 함수 추가, 세션 카드 날짜 줄에 실행 시간 표시

**CALL 로그 포맷 결정 과정**
처음에 파라미터 값을 인라인으로 넣었으나, 블록(────)에 전체 I/O가 기록되므로 CALL 줄은 타임스탬프 마커로만 사용하기로 결정. 최종 포맷: `12:34:56 | [planner] CALL`

**mock 모드 전면 교체**
- 수정: `backend/routers/mock.py` — fixtures/ 기반에서 data/jobs/ 기반으로 전환
  - `POST /generate`: `data/jobs/`에서 가장 최근 완료 job을 source로 선택, 새 job_id 생성, `meta.json`에 `mock_source` 필드로 source job_id 저장
  - `GET /stream/{job_id}`: source job의 `result.json` events를 에이전트별 하드코딩 딜레이로 재생. `agent_start` 0.3s, `agent_done` planner 5s / researcher 2s / analyst 4s / critic 8s / gate 3s / prd_writer 10s (fixtures/92b2d589.json 패턴 기반). 재생 완료 후 새 job dir에 `result.json` + `prd.md` 기록, meta → done
  - `GET /history`, `GET /result`, `GET /analytics`, `PATCH/POST/DELETE /jobs/`: real storage 함수에 위임 (fixtures/ 완전 제거)

**발견된 문제점**
- fixtures/ JSON이 구 버전 포맷이라 채팅 버블·analytics가 깨지는 문제가 mock 모드 교체의 원인
- `data/jobs/4fac6565/result.json`은 `tokens`가 int 형식(구 포맷)이나, analytics.py가 이미 int/dict 양쪽을 처리하므로 별도 변환 불필요

**수정된 파일**
- `backend/agents/llm.py`
- `backend/agents/orchestrator.py`
- `backend/services/pipeline.py`
- `backend/routers/mock.py`
- `frontend/src/pages/History.jsx`

**프롬프트**
(1) run.log에서 에이전트별 CALL/DONE/START 타임스탬프 줄과 token 로그의 에이전트 태그가 사라진 문제 복원. llm.py에 log_line/log_block 인프라 추가 후 orchestrator.py 각 tool에 로그 삽입.
(2) mock 모드를 fixtures/ 기반에서 data/jobs/ 실제 완료 job 재생 방식으로 전환. generate는 새 job_id 생성, stream은 에이전트별 딜레이 하드코딩 재생, 나머지 엔드포인트는 real storage 위임.

---

## 2026-04-28 — 프론트 → 백엔드 로직 이전 및 UX 개선

**작업 내용**

프론트엔드에 박혀 있던 비즈니스 로직을 백엔드로 이전하고, 에이전트 간 갭 구간 UX 개선.

**오케스트레이터 갭 인디케이터 (Analyze.jsx)**
- 추가: `isOrchestratorThinking` 파생 상태 — `sessionStatus === 'running'` 이고 `loading: true`인 버블이 없는 구간 감지
- 추가: `.orchestrator-thinking` + `.thinking-dot` CSS — 점 3개 순차 페이드 애니메이션. `agent_done` → `agent_start` 사이 빈 구간에 자동 표시/소멸

**CSV 내보내기 → 백엔드 전환 (analytics.py, Analytics.jsx)**
- 추가: `GET /analytics/csv?range=...` — 기존 `analytics()` 재호출 후 pandas `df.to_csv(encoding='utf-8-sig')`로 파일 생성, `StreamingResponse` 반환. BOM·쌍따옴표 이스케이프 자동 처리
- 수정: `Analytics.jsx` `handleCSV()` 13줄 → `window.location.href = /analytics/csv?range=...` 1줄

**히스토리 필터·정렬 → 백엔드 전환 (history.py, mock.py, client.js, History.jsx)**
- 수정: `GET /history?search=&sort=newest|oldest&favorite=true` — search(제목·입력 부분일치), sort(newest 기본, oldest는 reversed), favorite(bool 파라미터) 서버사이드 처리
- 수정: `mock.py GET /history` 동일 파라미터 대응
- 수정: `client.js getHistory()` — `{ search, sort, favorite }` 파라미터를 URLSearchParams로 전달
- 제거: `History.jsx` `filtered` state + 필터 `useEffect` (14줄)
- 추가: `History.jsx` 검색어 300ms 디바운스(`debouncedSearch` state) — 키 입력마다 API 요청 방지
- 수정: `History.jsx` `handleFavorite` — `favOnly=true` 상태에서 즐겨찾기 해제 시 로컬 state에서 즉시 제거

**analytics summary 중복 집계 제거 (Analytics.jsx)**
- 제거: `summary` useMemo (rows를 프론트에서 재집계)
- 추가: `summary` state — API 응답의 `data.summary` 그대로 사용 (`total_jobs` → `count`, `total_tokens` → `tokens`)

**PRD 다운로드 → 백엔드 전환 (jobs.py, mock.py, Result.jsx)**
- 추가: `GET /result/{job_id}/prd.md` — 서버의 `data/jobs/{job_id}/prd.md`를 `FileResponse`로 직접 서빙. `filename=prd_{job_id}.md` 헤더 포함
- 수정: `mock.py` 동일 엔드포인트 추가
- 수정: `Result.jsx` `handleDownload()` 8줄 → `window.location.href = /result/{job_id}/prd.md` 1줄

**Analytics 차트 집계 → 백엔드 pandas (analytics.py, Analytics.jsx)**
- 추가: `_compute_model_aggregates(df)` — 모델별 토큰 합계 계산
- 추가: `_compute_date_aggregates(df)` — 날짜·모델별 세그먼트 (스택 바 차트용)
- 수정: `/analytics` 응답에 `modelAggregates`, `dateAggregates` 필드 추가
- 제거: `Analytics.jsx` `modelChartData`, `dateChartData` useMemo 2개 (총 28줄)
- 추가: `Analytics.jsx` state로 `modelChartData`, `dateChartData` 저장, API 응답에서 직접 할당
- 제거: `useMemo` import (더 이상 필요 없음)

**preflight_check — 외부 서비스 연결 검증 (generate.py, client.js, Home.jsx)**
- 추가: `backend/routers/generate.py` — `preflight_check()` async 함수
  - TAVILY_API_KEY 미설정 시 HTTPException(503, detail="TAVILY_API_KEY가 설정되지 않았습니다...")
  - OpenRouter `/models` GET 요청 (Bearer auth) — status != 200 or network fail 시 HTTPException(503)
  - `asyncio.to_thread`로 blocking `requests` 호출을 event loop 밖에서 실행
- 수정: `POST /generate` 진입 직후 `await preflight_check()` 호출
- 수정: `client.js` `generateIdea()` — error JSON body 파싱해서 `detail` 필드 추출 후 throw
- 수정: `Home.jsx` catch에서 `e.message` 직접 사용 (generic "서버 연결 불가" 대신 실제 오류 메시지)

**수정된 파일**
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/pages/Analyze.css`
- `backend/routers/analytics.py`
- `frontend/src/pages/Analytics.jsx`
- `backend/routers/history.py`
- `backend/routers/mock.py`
- `frontend/src/api/client.js`
- `frontend/src/pages/History.jsx`
- `backend/routers/jobs.py`
- `frontend/src/pages/Result.jsx`
- `backend/routers/generate.py`
- `frontend/src/pages/Home.jsx`

**프롬프트**
(1) agent_done → agent_start 사이 갭 구간에 세션 활성 표시: 로딩 버블 없는 running 상태를 감지해 점 3개 인디케이터 표시.
(2) CSV 내보내기를 백엔드 pandas로 전환: GET /analytics/csv 엔드포인트 추가, 프론트 Blob 조립 제거.
(3) 히스토리 검색·정렬·즐겨찾기 필터를 GET /history 쿼리 파라미터로 이전: 프론트 filter useEffect 제거, 디바운스 추가.
(4) analytics summary를 API 응답값 직접 사용: 프론트 useMemo 재집계 제거.
(5) PRD 다운로드를 백엔드 FileResponse로 전환: GET /result/{job_id}/prd.md 추가, 프론트 Blob 조립 제거.
(6) Analytics 차트 집계(모델별·날짜별)를 백엔드 pandas로 전환: 프론트 useMemo 제거, API 응답에서 직접 받음.
(7) POST /generate에 외부 서비스 연결 검증 추가: TAVILY, OpenRouter 둘 중 하나라도 실패 시 503 반환. 프론트에서 error detail 파싱해 사용자 친화적 메시지 표시.

---

## 2026-04-28 — 파이프라인 에러 처리 강화 및 서비스 상태 확인 개선

**작업 내용**

실 실행 중 발견된 버그 수정, 에러 가시성 개선, preflight 구조 재설계.

**done 이벤트 status 필드 추가 (pipeline.py, mock.py, Analyze.jsx)**
- 수정: `pipeline.py` — `_final_status` 변수로 성공(done)/중단(stopped)/실패(failed) 추적. `done` 이벤트에 `status` 필드 포함
- 수정: `mock.py` — `done` 이벤트에 `status: "done"` 추가 (real 모드와 통일)
- 수정: `Analyze.jsx` — `done` 이벤트의 `status` 값으로 sessionStatus 분기. failed → `'error'`(세션이 에러로 인해 종료), stopped → `'stopped'`(사용자 요청으로 종료), done → `'done'`. 기존에는 파이프라인 실패 시에도 "PRD가 완성되었습니다!" 표시됨

**파이프라인 에러 가시성 (pipeline.py)**
- 추가: `except Exception` 블록에 `logging.exception("[pipeline] job=%s failed", job_id)` — 파이프라인 실패 시 uvicorn 콘솔에 full traceback 출력. 기존에는 에러가 조용히 삼켜져 meta.json에만 기록됨

**compute_cost model=None 버그 수정 (pipeline.py)**
- 수정: `event.get("model", "")` → `event.get("model") or ""` — researcher는 LLM 없이 Tavily 검색만 수행해 model 필드가 None으로 기록됨. `get("model", "")` 은 키가 있고 값이 None이면 None을 그대로 반환해 `.lower()` 호출 시 AttributeError 발생

**analytics 필터 완화 (analytics.py)**
- 수정: `status == "done"` 필터 제거 → `result.json` 존재 여부로 대체. compute_cost 실패로 status가 "failed"로 기록됐어도 result.json이 완전한 job을 analytics에서 제외하던 문제 수정
- 추가: `result.json` 파싱 시 `try/except` — 파일 손상 시 해당 job만 스킵. `if not model_tokens: continue` (기존)와 함께 3중 방어

**tokens 필드 이중 포맷 주석 추가 (pipeline.py, analytics.py, ChatBubble.jsx)**
- 추가: 구버전(정수) / 신버전({input, output, total} 딕셔너리) 처리 분기마다 주석. orchestrator 개편 전 저장된 job과 이후 job의 포맷이 달라 방어 코드가 필요한 이유 명시
- 추가: researcher model=None 처리 이유 주석 (analytics.py, pipeline.py)

**mock duration_sec 처리 (mock.py)**
- 수정: `_replay()` — source `result.json`에 `duration_sec`가 있으면 사용, 없으면 재생 실제 경과 시간으로 대체. 구버전 result.json에는 duration_sec 필드 없음

**preflight_check 제거 + GET /ready 추가 (generate.py, main.py, client.js, Home.jsx, Home.css)**
- 제거: `generate.py` — `preflight_check()` 함수 및 `POST /generate` 호출부, 관련 import(requests, OPENROUTER_API_KEY 등) 제거. OpenRouter `/models` 200 응답이 실제 inference 성공을 보장하지 않아 safeguard로서 의미 없음
- 수정: `GET /health` — 서버 생존 여부만 반환, OpenRouter 체크 제거. 주석 "이 서버가 살아있는지 확인" 추가
- 추가: `GET /ready` — OpenRouter(Bearer auth 포함) + Tavily 접속 가능 여부 확인. `{ openrouter: "ok"/"degraded", tavily: "ok"/"degraded" }` 반환
- 추가: `client.js` — `getReady()` 함수
- 수정: `Home.jsx` — 진입 시 `getReady()` 호출, 하나라도 degraded면 경고 배너 표시. 정상이면 배너 미표시
- 추가: `Home.css` — `.service-warning` 스타일 (amber 계열, 기존 warm brown 팔레트)

**날짜별 막대 차트 모델 합산 수정 (analytics.py)**
- 수정: `_compute_date_aggregates()` — 같은 날짜에 여러 job이 있을 때 모델별로 합산하지 않고 row를 그대로 segments로 넘기던 버그 수정. 동일 모델 색이 job 수만큼 반복되어 줄무늬처럼 보이는 시각적 오류 발생. `groupby("model")["tokens"].sum()` 으로 날짜 내 모델별 토큰 합산

**수정된 파일**
- `backend/services/pipeline.py`
- `backend/routers/mock.py`
- `backend/routers/analytics.py`
- `backend/routers/generate.py`
- `backend/main.py`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/components/ChatBubble.jsx`
- `frontend/src/api/client.js`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Home.css`

**발견된 문제점**
- `preflight_check`가 OpenRouter `/models` 200을 기준으로 통과 판정했으나, 실제 completions 호출은 별도 인증 검증으로 401 "User not found" 반환 가능. safeguard가 오히려 false confidence를 줌
- `compute_cost`에서 `model=None`(researcher emit)으로 `.lower()` AttributeError 발생 — PRD까지 생성된 후 비용 계산 단계에서 터져 result.json은 있지만 meta.json이 failed로 기록되는 상황 발생
- analytics `status == "done"` 필터가 위 상황의 job을 집계에서 제외함

**프롬프트**
(1) 파이프라인 실패 시에도 "PRD가 완성되었습니다!" 표시되는 문제: done 이벤트에 status 필드 추가, Analyze.jsx에서 분기.
(2) 파이프라인 에러가 조용히 삼켜지는 문제: logging.exception으로 uvicorn 콘솔에 traceback 출력.
(3) compute_cost model=None AttributeError: `or ""` 가드 추가.
(4) analytics가 result.json 있는 job을 status==failed로 제외하는 문제: result.json 존재 여부 기준으로 전환, JSON 파싱 방어 추가.
(5) preflight_check 제거: /ready 엔드포인트로 대체, 홈 진입 시 서비스 상태 배너 표시.
(6) 날짜별 막대 차트 줄무늬 버그: _compute_date_aggregates에서 모델별 groupby 합산.
