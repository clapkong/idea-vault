# IdeaVault — Claude Code 작업 컨텍스트

사용자가 막연한 아이디어(한국어)를 입력하면 멀티 에이전트 AI 파이프라인이 처리하여 완성된 PRD를 생성하는 앱.

## 현재 상태 (2026-04-27)

- 프론트엔드(Vite+React 5페이지) + FastAPI 목업 백엔드 — 완료
- 에이전트 파이프라인(`backend/agents/`) — 완료
- `feature/backend` 브랜치: FastAPI ↔ 에이전트 파이프라인 연결 + Docker + CI/CD 작업 예정

## 프로젝트 구조

```
ideavault-backend/
  run.py                  # CLI 진입점 (에이전트 단독 실행)
  backend/
    main.py               # FastAPI 엔드포인트 전체, USE_MOCK_MODE 분기
    config.py             # 환경변수 로딩
    agents/
      orchestrator.py     # create_deep_agent 기반 오케스트레이터 (툴 12개)
      llm.py              # ChatOpenAI 팩토리, 토큰 로깅, 프롬프트 로더
      subagents/          # planner, researcher, analyst, critic, gate, prd_writer
      prompts/            # 각 에이전트 시스템 프롬프트 .md
    mock_agents/          # 목업 JSON 데이터 (history.json, {job_id}.json)
  frontend/
    src/pages/            # Home, Analyze, Result, History, Analytics, NotFound
    src/components/       # NavBar, ChatBubble
    vite.config.js        # API 경로 → localhost:8000 프록시
  docs/
    agent_logs/           # run_{job_id}.log
    generated_prds/       # prd_{job_id}.md
    ai-usage-log.md
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
USE_MOCK_MODE=true     # false로 전환하면 실제 에이전트 모드
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

- `create_llm(model, max_tokens)` — ChatOpenAI 인스턴스 (OpenRouter)
- `load_prompt(agent_name)` — `backend/agents/prompts/{name}.md` 로드
- `extract_content(result)` — AIMessage 텍스트 추출
- `set_token_logger(logger)` — job별 토큰 로깅 주입

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

`backend/main.py`의 실제 모드 구현. 현재 `USE_MOCK_MODE=false`이면 전부 501.

1. `POST /generate`: UUID job_id 생성 → `asyncio.create_task(orchestrator.run(...))` 백그라운드 시작
2. `GET /stream/{job_id}`: orchestrator 실행 중 SSE 이벤트 스트리밍 (`asyncio.Queue` 패턴)
3. `GET /history` / `GET /analytics`: JSON 파일 기반 영속화 유지 또는 SQLite 전환
4. `PATCH /jobs/:id/favorite` / `DELETE /jobs/:id`: 동일

SSE 스트리밍 핵심: `orchestrator.py`의 `_log_block` 호출 시점에 이벤트를 emit하거나,
`asyncio.Queue`를 사용해 orchestrator → stream 엔드포인트로 이벤트를 전달하는 방식.

## 개발 컨벤션

- **UI 언어**: 모든 사용자 노출 텍스트 한국어
- **스타일**: CSS 커스텀 변수 기반 (`--color-primary: #8B6F47`, `--color-bg: #F5F1E8`), CSS-in-JS 없음
- **에이전트 색상**: `ChatBubble.jsx`의 `AGENT_CONFIG`에서 중앙 관리
- **소프트 삭제**: `deleted: true` 플래그, 물리 삭제 금지 (analytics 데이터 보존)
- **낙관적 업데이트**: 프런트에서 먼저 반영 후 API 호출

## 실행 (개발)

```bash
# 백엔드
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 프런트엔드
cd frontend && npm install && npm run dev  # http://localhost:5173

# CLI (에이전트 단독)
python run.py "조건 텍스트"
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
```

### 작성 규칙
- 날짜 `YYYY-MM-DD` 형식
- 롤백한 내용도 포함 (시도 → 원인 확인 → 결정 흐름)
- 파일 경로는 프로젝트 루트 기준 상대경로
