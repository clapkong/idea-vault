# IdeaVault

사용자 조건을 입력받아 프로젝트 아이디어를 검증하고 PRD를 생성하는 멀티 에이전트 시스템.

## 실행

```bash
python run.py "조건 텍스트"
# 또는 대화형
python run.py
```

결과물: `docs/agent_logs/run_{job_id}.log`, `docs/generated_prds/prd_{job_id}.md`

## 환경변수 (.env)

```
MODEL_STRONG=      # 오케스트레이터·플래너·크리틱·PRD 작성용 강력한 모델
MODEL_LIGHT=       # 애널리스트·게이트용 경량 모델
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1   # 기본값
TAVILY_API_KEY=    # 웹 검색용, 미설정 시 researcher 비활성
MAX_OUTER_LOOPS=3  # Gate 루프 상한
MAX_INNER_LOOPS=3  # Critic 루프 상한
```

## 에이전트 구조

### 진입점

```
run.py
└── asyncio.run(orchestrator.run(user_conditions))
    └── returns { job_id, prd, loop_history }
```

### Orchestrator (`backend/agents/orchestrator.py`)

`create_deep_agent` 기반. 루프 전체를 관리하는 LLM 에이전트.
툴을 통해 subagent를 호출하고 결과를 판단해 다음 행동을 결정.

**전역 상태** (run() 호출마다 초기화):
- `_user_conditions` — 사용자 입력
- `_current_topic` — 현재 검토 중인 주제 (planner 결과)
- `_loop_history` — 루프별 critic/gate 결과 누적
- `_outer` / `_inner` — 루프 카운터
- `_prd_result` — 최종 PRD

**툴 목록**:
| 툴 | 역할 |
|---|---|
| `tool_planner` | 주제 발굴/정제/전환 (INIT/REFINE/PIVOT) |
| `tool_researcher` | Tavily 웹 검색 (LLM 없음) |
| `tool_analyst` | 사용자 조건 대비 프로젝트 적합성 분석 |
| `tool_critic` | 정보 충분성 평가 → 방향 결정 (RESEARCHER/ANALYST/BOTH/GATE) |
| `tool_gate` | 주제 계속 여부 심사 (REFINE/PIVOT/DONE) |
| `tool_prd_writer` | 최종 PRD 작성 |
| `tool_update_loop_history` | 루프 기록 저장 |
| `tool_get_current_state` | 현재 루프 상태 조회 |
| `tool_get_loop_history` | 전체 루프 기록 조회 |
| `tool_get_previous_findings` | 이전 critic 요약 조회 |
| `tool_get_gate_decisions` | 이전 gate 결정 조회 |
| `check_loop_limit` | 루프 한계 확인 → CONTINUE/FORCE_GATE/FORCE_PRD |

**루프 흐름**:
```
planner(INIT)
  → researcher + analyst (병렬)
  → critic → [RESEARCHER/ANALYST/BOTH → 재호출] or [GATE → gate]
  → gate → [REFINE → planner(REFINE)] or [PIVOT → planner(PIVOT)] or [DONE → prd_writer]
```

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

- `create_llm(model, max_tokens)` — ChatOpenAI 인스턴스 반환 (OpenRouter)
- `load_prompt(agent_name)` — `backend/agents/prompts/{name}.md` 로드
- `extract_content(result)` — AIMessage에서 텍스트 추출
- `_TokenHandler` + `set_token_logger(logger)` — job별 토큰 로깅

## FastAPI 연동 시 참고

`orchestrator.run(user_conditions, job_id)` 는 완전한 async 함수.
반환값 `{ job_id, prd, loop_history }` 를 그대로 응답으로 사용 가능.

```python
@app.post("/generate")
async def generate(req: Request):
    result = await orchestrator.run(req.user_conditions)
    return result
```

스트리밍이 필요하면 `_log_block` 호출 시점마다 SSE 이벤트를 emit하는 방식으로 확장 가능.

---

## ai-usage-log.md 작성법

파일 위치: `docs/ai-usage-log.md`
작성 방식: **append only** — 기존 내용 유지, 맨 아래에 추가

### 항목 구분 기준
논리적으로 묶이는 작업 단위마다 항목 하나. 같은 세션이라도 목적이 다르면 분리.

### 항목 형식

```
## YYYY-MM-DD — 작업 제목

**작업 내용**
파일/컴포넌트별 구체적인 변경 사항을 bullet로 작성.
추가/제거/수정 구분해서 기술.

**수정된 파일**
- 경로 목록 (삭제된 파일은 뒤에 (삭제) 표기)

**발견된 문제점**  ← 있을 경우에만
이 단계에서 발견된 문제 — 다음 항목에서 해결된 것들.
문제가 생긴 원인까지 기술.

**프롬프트**
실제 요청을 정제한 언어로 작성. 구어체 그대로 옮기지 말 것.
```

### 작성 규칙
- 날짜는 `YYYY-MM-DD` 형식
- 프롬프트는 요청 의도가 명확하게 드러나도록 정제. 구어/비격식 표현 제거
- 발견된 문제점은 다음 항목과 인과관계가 보이도록 작성 — 마지막 항목은 생략 가능
- 실험 후 롤백한 내용도 작업 내용에 포함 (시도 → 원인 확인 → 결정 흐름으로)
- 파일 경로는 프로젝트 루트 기준 상대경로
# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 필요한 맥락을 담고 있습니다.

## 프로젝트 개요

**Idea Vault** — 사용자가 막연한 아이디어(한국어)를 입력하면 다중 에이전트 AI 파이프라인(planner → researcher → analyst → critic → prd_writer)이 순차적으로 처리하여 완성된 PRD를 생성하는 앱. 현재는 목업 백엔드로 동작하며, 실제 에이전트 루프 구현체는 별도 브랜치에서 개발 중이고 추후 merge될 예정이다.

---

## 핵심 파일 맵

```
frontend/src/
  pages/
    Home.jsx          # 아이디어 입력 폼 (20-500자, 예시 프롬프트)
    Analyze.jsx       # SSE 수신 + 실시간 에이전트 채팅 UI, 세션 중단
    Result.jsx        # PRD Markdown 렌더링 + 사이드 TOC + .md 다운로드
    History.jsx       # 좌측 목록(검색/정렬/즐겨찾기/삭제) + 우측 미리보기
    Analytics.jsx     # 토큰 통계 대시보드 (파이·막대 차트, CSV 내보내기)
    NotFound.jsx      # 404 폴백
  components/
    NavBar.jsx        # 상단 네비게이션
    ChatBubble.jsx    # 에이전트별 색상·아이콘·토큰 표시 공용 버블

backend/
  main.py             # FastAPI 엔드포인트 전체, USE_MOCK_MODE 분기
  mock_agents/
    history.json      # 세션 메타데이터 (job_id, title, favorite, deleted 등)
    {job_id}.json     # 세션별 events 배열 + prd 전문
    prd_*.md          # 생성된 PRD 마크다운 샘플
```

---

## Frontend ↔ Backend 계약

Vite dev 서버(`localhost:5173`)는 아래 경로를 `localhost:8000`으로 프록시한다 (`frontend/vite.config.js`):

```
/generate   → POST  — { user_input } → { job_id, status: "processing" }
/stream     → GET   — EventSource, SSE 이벤트 스트림
/result     → GET   — { prd, loop_history, events }
/history    → GET   — Job[]
/analytics  → GET   — { summary: { total_jobs, total_tokens }, data: Row[] }
/jobs       → PATCH /jobs/:id/favorite  — { favorite: bool }
             POST  /jobs/:id/stop
             DELETE /jobs/:id           — 소프트 삭제
```

### SSE 이벤트 타입

| type | 필수 필드 | 설명 |
|------|-----------|------|
| `agent_start` | `agent`, `timestamp` | 에이전트 시작 |
| `agent_progress` | `agent` | 처리 중 (로딩 표시용) |
| `agent_done` | `agent`, `output`, `tokens`, `model` | 에이전트 완료 |
| `done` | — | 전체 파이프라인 완료 |

---

## 에이전트 파이프라인 (백엔드 merge 후 구현)

실제 에이전트 루프는 이 저장소에 없다. `backend/main.py`의 `TODO(backend)` 주석이 붙은 곳이 실제 구현으로 교체될 지점이다.

주요 교체 지점:
- `POST /generate`: 실제 UUID job_id 생성 + DB 저장 + 에이전트 루프 시작
- `GET /stream/{job_id}`: 실제 에이전트 실행 결과를 SSE로 스트리밍
- `GET /history`, `GET /analytics`: DB 쿼리로 교체 (현재는 JSON 파일 읽기)
- 에이전트 이벤트에 `model` 필드 포함 필수 (analytics 집계에 사용됨)

`USE_MOCK_MODE` 환경변수로 목업/실제 모드 전환:
```bash
USE_MOCK_MODE=false uvicorn backend.main:app --reload --port 8000
```

---

## 개발 컨벤션

- **UI 언어**: 모든 사용자 노출 텍스트는 한국어
- **스타일**: CSS 커스텀 변수 기반, CSS-in-JS 없음
  - 주요 변수: `--color-primary: #8B6F47`, `--color-bg: #F5F1E8`
  - 각 페이지마다 동명의 `.css` 파일 (`Analytics.css` 등)
- **에이전트 색상**: `ChatBubble.jsx`의 `AGENT_CONFIG` 객체에서 중앙 관리
- **소프트 삭제**: `deleted: true` 플래그로 처리, 물리 삭제 금지 (analytics 데이터 보존)
- **즐겨찾기·삭제 영속화**: 프런트에서 낙관적 업데이트 후 API 호출, 새로고침 후에도 유지됨

---

## 실행 (개발)

```bash
# 백엔드
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 프런트엔드
cd frontend
npm install
npm run dev      # http://localhost:5173
```

목업 데이터는 `backend/mock_agents/`에 있으며, 모든 `/generate` 요청은 `job_id: "92b2d589"`를 반환한다.
