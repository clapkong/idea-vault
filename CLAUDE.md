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
    main.py               # FastAPI 앱 생성 + CORS + 라우터 등록 (진입점만)
    config.py             # 환경변수 로딩
    routers/              # 엔드포인트별 라우터
      generate.py         # POST /generate
      stream.py           # GET /stream/{job_id}
      jobs.py             # GET /result, PATCH/POST/DELETE /jobs/
      history.py          # GET /history
      analytics.py        # GET /analytics
      mock.py             # USE_MOCK_MODE=true 시 위 라우터 대체 (fixtures/ 기반)
    services/             # 비즈니스 로직
      storage.py          # 파일 I/O (real mode), USE_MOCK_MODE, DATA_DIR
      pipeline.py         # 백그라운드 러너, job_queues, running_jobs, compute_cost
    agents/
      orchestrator.py     # create_deep_agent 기반 오케스트레이터 (툴 12개)
      llm.py              # ChatOpenAI 팩토리, ContextVar 기반 블록/토큰 로거, 프롬프트 로더
      run.py              # CLI 진입점 (python -m agents.run "조건")
      subagents/          # planner, researcher, analyst, critic, gate, prd_writer
      prompts/            # 각 에이전트 시스템 프롬프트 .md
    fixtures/             # 목업 JSON 데이터 (history.json, {job_id}.json)
  frontend/
    src/
      api/
        client.js         # 모든 fetch 호출 중앙화 (generateIdea, getResult, ...)
      pages/              # Home, Analyze, Result, History, Analytics, NotFound
      components/         # NavBar, ChatBubble
    vite.config.js        # API 경로 → localhost:8000 프록시
  data/                   # 런타임 데이터 (mock 모드 샘플 job 포함)
    jobs/                 # job별 디렉토리 (아래 데이터 파일 구조 참고)
  docs/
    generated_prds/       # prd_{job_id}.md (CLI 실행 시)
    ai-usage-log-backend.md
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
USE_MOCK_MODE=false    # true로 전환하면 fixtures/ 목업 데이터 사용 (API 키 불필요)
```

## 에이전트 파이프라인

### 진입점

```
orchestrator.run(user_conditions, job_id?)
  → returns { job_id, prd, loop_history }
```

### Orchestrator (`backend/agents/orchestrator.py`)

`create_deep_agent` 기반. 전역 상태(run() 호출마다 초기화):
`_user_conditions` / `_current_topic` / `_loop_history` / `_outer` / `_inner` / `_prd_result`

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
`create_deep_agent` 미사용 — 선택 파라미터 빈 값 시 빈 출력 문제 확인됨 (`llm.py` 주석 참고).

| 파일 | 모델 | 역할 |
|---|---|---|
| `planner.py` | MODEL_STRONG | 주제 발굴, EXTERNAL/INTERNAL 항목 생성 |
| `researcher.py` | (LLM 없음) | Tavily 검색, URL 보존 |
| `analyst.py` | MODEL_LIGHT | INTERNAL 항목 분석, 적합성 판단 |
| `critic.py` | MODEL_STRONG | 정보 충분성 평가, 점수(feasibility/fit/clarity) |
| `gate.py` | MODEL_LIGHT | REFINE/PIVOT/DONE 결정 |
| `prd_writer.py` | MODEL_STRONG | 8섹션 마크다운 PRD 작성 |

### 공통 유틸 (`backend/agents/llm.py`)

- `create_llm(model, max_tokens, agent_name)` — ChatOpenAI 인스턴스 (OpenRouter). `agent_name` 지정 시 run.log에 블록 형식으로 I/O 기록
- `load_prompt(agent_name)` — `backend/agents/prompts/{name}.md` 로드
- `extract_content(result)` — AIMessage 텍스트 추출
- `set_block_logger(logger)` / `set_token_logger(logger)` — pipeline.py에서 job 시작 시 주입, 종료 시 None 해제. ContextVar 기반이라 동시 실행 안전
- `_token_counts` — orchestrator 전용 per-agent 델타 계산용 (pipeline.py 총합은 events에서 직접 합산)

## Frontend ↔ Backend API

Vite dev 서버(`:5173`) → FastAPI(`:8000`) 프록시 (`frontend/vite.config.js`):

```
POST /generate            { user_input } → { job_id, status: "processing" }
GET  /stream/{job_id}     SSE 이벤트 스트림
GET  /result/{job_id}     { prd, loop_history, events }
GET  /history             Job[]
GET  /analytics           { summary: { total_jobs, total_tokens }, data: Row[] }
PATCH /jobs/:id/favorite  { favorite: bool }
POST  /jobs/:id/stop
DELETE /jobs/:id          소프트 삭제
```

### SSE 이벤트 타입

| type | 필수 필드 | 설명 |
|---|---|---|
| `agent_start` | `agent`, `timestamp` | 에이전트 시작 |
| `agent_progress` | `agent` | 처리 중 (로딩 표시용) |
| `agent_done` | `agent`, `output`, `tokens`, `model` | 에이전트 완료 |
| `done` | — | 전체 파이프라인 완료 |

## TODO(backend) — 남은 작업

1. Docker + CI/CD
2. SQLite 전환 — 현재 `data/jobs/` 파일 스캔 방식은 job 수 증가 시 느려짐. `storage.py` + `pipeline.py` 교체로 전환 가능하도록 설계됨

## 개발 컨벤션

- **UI 언어**: 모든 사용자 노출 텍스트 한국어
- **스타일**: CSS 커스텀 변수 기반 (`--color-primary: #8B6F47`, `--color-bg: #F5F1E8`), CSS-in-JS 없음
- **에이전트 색상**: `ChatBubble.jsx`의 `AGENT_CONFIG`에서 중앙 관리
- **소프트 삭제**: `deleted: true` 플래그, 물리 삭제 금지 (analytics 데이터 보존)
- **낙관적 업데이트**: 프런트에서 먼저 반영 후 API 호출

## 데이터 파일 구조

API 실행(real mode) 시 `data/jobs/{job_id}/` 아래 생성:

```
meta.json      — job 메타데이터 (항상 존재)
input.txt      — 사용자 입력 원문
result.json    — 파이프라인 완료 시 생성
prd.md         — 최종 PRD 마크다운 (사람이 읽는 용)
run.log        — 에이전트별 I/O 블록 로그
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
  "cost": 0.142
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
  "events": [ /* SSE 이벤트 전체 목록 */ ]
}
```

### run.log 형식
```
────────────────────────────────────────────────────────────
[planner]

<입력>
## 모드
INIT
...

<출력>
TOPIC: ...
────────────────────────────────────────────────────────────
[token] model-name | prompt=820 completion=310 total=1130
```

에이전트 블록(`────` + `[name]` + `<입력>` + `<출력>`)과 `[token]` 줄이 번갈아 기록됨.

### GET /analytics → data 행 구조
```json
{ "job_id": "...", "date": "2026-04-28", "title": "...", "model": "claude-sonnet", "tokens": 4500 }
```
job별 `result.json` events에서 model별로 쪼개 반환 (job당 N행). 프론트 파이·막대 차트 모두 이 구조 기준.

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
