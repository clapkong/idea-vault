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
