# IdeaVault — Claude Code 작업 컨텍스트

사용자가 막연한 아이디어(한국어)를 입력하면 멀티 에이전트 AI 파이프라인이 처리하여 완성된 PRD를 생성하는 앱.

## 현재 상태 (2026-04-28)

- 프론트엔드(Vite+React 5페이지) + FastAPI 목업 백엔드 — 완료
- 에이전트 파이프라인(`backend/agents/`) — 완료
- `feature/backend` 브랜치: FastAPI ↔ 에이전트 파이프라인 연결 — **완료**
- 다음 작업: Docker + CI/CD

## 프로젝트 구조

```
ideavault-backend/
  backend/
    main.py               # FastAPI 앱 생성 + CORS + 라우터 등록 + /health + /ready
    config.py             # 환경변수 로딩 (필수값 미설정 시 EnvironmentError)
    routers/              # 엔드포인트별 라우터
      generate.py         # POST /generate
      stream.py           # GET /stream/{job_id}
      jobs.py             # GET /result/{job_id}, GET /result/{job_id}/prd.md, PATCH/POST/DELETE /jobs/
      history.py          # GET /history
      analytics.py        # GET /analytics, GET /analytics/csv
      mock.py             # USE_MOCK_MODE=true 시 위 라우터 대체 (data/jobs/ 완료 job 재생)
    services/             # 비즈니스 로직
      storage.py          # 파일 I/O (real mode), USE_MOCK_MODE, DATA_DIR
      pipeline.py         # 백그라운드 러너, job_queues, running_jobs, compute_cost (최대 1800s)
    agents/
      orchestrator.py     # create_deep_agent 기반 오케스트레이터 (툴 12개)
      llm.py              # ChatOpenAI 팩토리, ContextVar 기반 블록/토큰 로거, 프롬프트 로더
      run.py              # CLI 진입점 (python -m agents.run "조건")
      subagents/          # planner, researcher, analyst, critic, gate, prd_writer
      prompts/            # 각 에이전트 시스템 프롬프트 .md
  frontend/
    src/
      api/
        client.js         # 모든 fetch 호출 중앙화 (generateIdea, getResult, ...)
      pages/              # Home, Analyze, Result, History, Analytics, NotFound
      components/         # NavBar, ChatBubble
    vite.config.js        # API 경로 → localhost:8000 프록시
  data/                   # 런타임 데이터
    jobs/                 # job별 디렉토리 (아래 데이터 파일 구조 참고)
  docs/
    generated_prds/       # prd_{job_id}.md (CLI 실행 시)
    ai-usage-log-backend.md
  tools/
    agent_profile_color.py
```

## 환경변수 (.env)

```
MODEL_STRONG=          # orchestrator·planner·critic·prd_writer
MODEL_LIGHT=           # analyst·gate
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
TAVILY_API_KEY=        # 미설정 시 researcher 비활성
MAX_OUTER_LOOPS=3
MAX_INNER_LOOPS=3
USE_MOCK_MODE=true     # 기본값 true — false로 전환해야 실제 파이프라인 실행 (API 키 필요)
```

## 에이전트 파이프라인

### 진입점

```
orchestrator.run(user_conditions, job_id?, event_queue?)
  → returns { job_id, prd, loop_history, events }
```

### Orchestrator (`backend/agents/orchestrator.py`)

`create_deep_agent` 기반. 전역 상태(run() 호출마다 초기화):
`_event_queue` / `_events` / `_user_conditions` / `_current_topic` / `_loop_history` / `_outer` / `_inner` / `_prd_result`

**루프 흐름**:
```
planner(INIT)
  → researcher + analyst (병렬)
  → critic → [RESEARCHER/ANALYST/BOTH → 재호출] or [GATE]
  → gate → [REFINE → planner(REFINE)] or [PIVOT → planner(PIVOT)] or [DONE → prd_writer]
```

**툴** (12개): `tool_planner` / `tool_researcher` / `tool_analyst` / `tool_critic` / `tool_gate` / `tool_prd_writer` / `tool_update_loop_history` / `tool_get_current_state` / `tool_get_loop_history` / `tool_get_previous_findings` / `tool_get_gate_decisions` / `check_loop_limit`

### Subagents (`backend/agents/subagents/`)

모두 `ChatOpenAI.ainvoke([SystemMessage(prompt), HumanMessage(data)])` 패턴.
반환값은 `(content: str, tokens: dict)` 튜플 — `tokens`는 `{input, output, total}`.
`create_deep_agent` 미사용 — 선택 파라미터 빈 값 시 빈 출력 문제 확인됨 (`llm.py` 주석 참고).

| 파일 | 모델 | max_tokens | 역할 |
|---|---|---|---|
| `planner.py` | MODEL_STRONG | 1024 | 주제 발굴, EXTERNAL/INTERNAL 항목 생성 |
| `researcher.py` | (LLM 없음) | — | Tavily 검색, URL 보존 |
| `analyst.py` | MODEL_LIGHT | 1536 | INTERNAL 항목 분석, 적합성 판단 |
| `critic.py` | MODEL_STRONG | 2048 | 정보 충분성 평가, 점수(feasibility/fit/clarity) |
| `gate.py` | MODEL_LIGHT | 512 | REFINE/PIVOT/DONE 결정 |
| `prd_writer.py` | MODEL_STRONG | 4096 | 8섹션 마크다운 PRD 작성 |

### 공통 유틸 (`backend/agents/llm.py`)

- `create_llm(model, max_tokens, agent_name)` — ChatOpenAI 인스턴스 (OpenRouter). `agent_name` 지정 시 run.log에 블록 형식으로 I/O 기록
- `load_prompt(agent_name)` — `backend/agents/prompts/{name}.md` 로드
- `extract_content(result)` — AIMessage 텍스트 추출 (content가 list이면 text 블록만 이어붙임)
- `extract_tokens(result)` — AIMessage에서 `{input, output, total}` 토큰 딕셔너리 추출 (`usage_metadata` 우선, 없으면 `response_metadata` 폴백)
- `set_block_logger(logger)` / `set_token_logger(logger)` — pipeline.py에서 job 시작 시 주입, 종료 시 None 해제. ContextVar 기반이라 동시 실행 안전
- `log_line(text)` / `log_block(agent_name, input, output)` — orchestrator·researcher에서 직접 호출

## Frontend ↔ Backend API

Vite dev 서버(`:5173`) → FastAPI(`:8000`) 프록시 (`frontend/vite.config.js`):

```
GET  /health              { status: "ok", mock_mode: bool }
GET  /ready               { openrouter: "ok"/"degraded", tavily: "ok"/"degraded" }
POST /generate            { user_input } → { job_id, status: "processing" }
GET  /stream/{job_id}     SSE 이벤트 스트림
GET  /result/{job_id}     { prd, loop_history, events }
GET  /result/{job_id}/prd.md   PRD 마크다운 파일 다운로드 (attachment)
GET  /history             Job[]  (search, sort, favorite 쿼리파라미터)
GET  /analytics           { summary, data, modelAggregates, dateAggregates }
GET  /analytics/csv       CSV 다운로드 (range 쿼리파라미터)
PATCH /jobs/:id/favorite  { favorite: bool }
POST  /jobs/:id/stop
DELETE /jobs/:id          소프트 삭제
```

> **주의**: Vite proxy에 `/health`·`/ready` 미등록. 개발 환경에서 client.js가 이 경로를 fetch하므로, 직접 호출하거나 proxy 추가 필요.

### SSE 이벤트 타입

| type | 필수 필드 | 설명 |
|---|---|---|
| `agent_start` | `agent`, `timestamp` | 에이전트 시작 |
| `agent_progress` | `agent` | 처리 중 (로딩 표시용) |
| `agent_done` | `agent`, `output`, `tokens`, `model`, `timestamp` | 에이전트 완료 |
| `done` | `job_id`, `status` | 전체 파이프라인 완료 (status: done/stopped/failed) |

`agent_done.tokens` 필드: 구버전 정수, 신버전 `{input, output, total}` 딕셔너리 — 양쪽 모두 처리해야 함.

## mock 모드 동작 (`routers/mock.py`)

`USE_MOCK_MODE=true`이면 real 라우터 대신 mock 라우터 등록.

- `POST /generate`: 실제 파이프라인 실행 없음. `data/jobs/`에서 가장 최근 완료 job을 찾아 `mock_source`로 저장.
- `GET /stream/{job_id}`: `mock_source` job의 `result.json` events를 에이전트별 딜레이로 재생 (planner 5s, researcher 2s, analyst 4s, critic 8s, gate 3s, prd_writer 10s). 재생 완료 후 `result.json`·`prd.md` 기록.
- 나머지 엔드포인트: real storage 함수에 위임.
- `POST /jobs/:id/stop`: no-op (실제 task 없음).
- **전제조건**: `data/jobs/`에 완료 job(`status: done`)이 1개 이상 있어야 함 — 없으면 `/generate` 500 에러.

## TODO(backend) — 남은 작업

1. Docker + CI/CD
2. FORCE_PRD 버그 — critics 직후 FORCE_PRD가 실행되는 문제 (job `42378efb` 재현). CI/CD 이후 처리.

## 개발 컨벤션

- **UI 언어**: 모든 사용자 노출 텍스트 한국어
- **스타일**: CSS 커스텀 변수 기반 (`--color-primary: #8B6F47`, `--color-bg: #F5F1E8`), CSS-in-JS 없음
- **에이전트 색상**: `ChatBubble.jsx`의 `AGENT_COLORS`에서 중앙 관리
- **소프트 삭제**: `deleted: true` 플래그, 물리 삭제 금지 (analytics 데이터 보존)
- **낙관적 업데이트**: 프런트에서 먼저 반영 후 API 호출

## 데이터 파일 구조

`data/jobs/{job_id}/` 아래 생성 (real mode · mock mode 공통):

```
meta.json      — job 메타데이터 (항상 존재)
input.txt      — 사용자 입력 원문
result.json    — 파이프라인 완료 시 생성
prd.md         — 최종 PRD 마크다운 (사람이 읽는 용)
run.log        — 에이전트별 I/O 블록 로그 (real mode만)
```

### meta.json
```json
{
  "job_id": "a1b2c3d4",
  "status": "processing | done | stopped | failed",
  "created_at": "2026-04-28T12:00:00",
  "user_input": "사용자 입력 전문",
  "favorite": false,
  "deleted": false,
  "duration_sec": 120.5,
  "tokens": 12500,
  "cost": 0.142,
  "mock_source": "b2c3d4e5"  // mock mode 전용
}
```

### result.json
```json
{
  "prd": "# PRD 제목\n...",
  "loop_history": [
    {
      "loop": 1,
      "gate_decision": "DONE | REFINE | PIVOT",
      "critics": [
        {
          "inner": 1,
          "summary": "...",
          "score": { "feasibility": 8, "fit": 7, "clarity": 9 }
        }
      ]
    }
  ],
  "events": [ /* SSE 이벤트 전체 목록 */ ],
  "duration_sec": 120.5
}
```

### run.log 형식
```
2026-04-28 12:00:00 | [orchestrator] START | job_id=a1b2c3d4
2026-04-28 12:00:01 | [planner] CALL
────────────────────────────────────────────────────────────
[planner]

<입력>
## 모드
INIT
...

<출력>
TOPIC: ...
────────────────────────────────────────────────────────────
2026-04-28 12:00:06 | [tokens] [planner] model-name | prompt=820 completion=310 total=1130
```

### GET /analytics 응답 구조
```json
{
  "summary": { "total_jobs": 3, "total_tokens": 45000 },
  "data": [
    { "job_id": "...", "date": "2026-04-28", "title": "...", "model": "claude-sonnet", "tokens": 4500 }
  ],
  "modelAggregates": [{ "label": "claude-sonnet", "value": 40000 }],
  "dateAggregates": [{ "label": "2026-04-28", "total": 45000, "segments": [{ "model": "...", "value": 45000 }] }]
}
```
`data`는 job별·model별로 분리된 행 (job당 N행). `modelAggregates`는 파이 차트, `dateAggregates`는 스택 막대 차트용.

---

## 실행 (개발)

```bash
# 백엔드
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 프런트엔드
cd frontend && npm install && npm run dev  # http://localhost:5173

# CLI (에이전트 단독)
cd backend && python -m agents.run "조건 텍스트"
```

---

## ai-usage-log.md 작성법

파일: `docs/ai-usage-log.md` — **append only**

### 항목 형식

```
## YYYY-MM-DD — 작업 제목

**작업 내용**
파일/컴포넌트별 구체적인 변경 사항 (추가/제거/수정 구분)

**수정된 파일**
- 경로 목록 (삭제 파일은 뒤에 (삭제) 표기)

**발견된 문제점**  ← 있을 경우에만
원인까지 기술

**프롬프트**
요청 의도를 정제한 언어로 작성. 구어체 제거.

**TODO**
이번 세션에서 끝내지 못한 일이나 이후 처리를 고려하는 일이 존재할 때 
```

### 작성 규칙
- 날짜 `YYYY-MM-DD` 형식
- 롤백한 내용도 포함 (시도 → 원인 확인 → 결정 흐름)
- 파일 경로는 프로젝트 루트 기준 상대경로
