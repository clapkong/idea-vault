# IdeaVault 백엔드 연결 + 배포 작업 브리핑

## 프로젝트 개요

사용자가 한국어 아이디어를 입력하면 멀티 에이전트 파이프라인(planner → researcher → analyst → critic → gate → prd_writer)이 처리해 PRD를 생성하는 앱. Vite+React 프론트엔드 + FastAPI 백엔드 + LangChain 에이전트 구조.

- **레포**: `ideavault-backend/`
- **현재 브랜치**: `feature/backend`
- **메인 브랜치**: `main` (현재 거의 비어있음, feature/backend에 모든 작업 누적)

---

## 완료된 것

| 영역 | 상태 |
|---|---|
| 프론트엔드 (5페이지: Home/Analyze/Result/History/Analytics) | 완료 |
| FastAPI 목업 백엔드 (`backend/main.py`) | 완료 |
| 에이전트 파이프라인 (`backend/agents/`) | 완료 |
| CLI 실행 (`run.py`) | 완료 |

에이전트 파이프라인은 `python run.py "조건"` 으로 독립 실행 가능한 상태. FastAPI와 아직 연결 안 됨.

---

## 핵심 파일

```
backend/
  main.py               ← FastAPI, USE_MOCK_MODE 분기, TODO(backend) 주석 4곳
  config.py             ← 환경변수 (MODEL_STRONG, MODEL_LIGHT, OPENROUTER_API_KEY 등)
  agents/
    orchestrator.py     ← create_deep_agent 기반, run(user_conditions) async 함수
    llm.py              ← create_llm(), load_prompt(), extract_content(), set_token_logger()
    subagents/          ← planner, researcher, analyst, critic, gate, prd_writer
    prompts/            ← 각 에이전트 시스템 프롬프트 .md
  mock_agents/          ← 목업 JSON (history.json, {job_id}.json)
frontend/
  vite.config.js        ← /generate /stream /result 등 → localhost:8000 프록시
  src/pages/Analyze.jsx ← SSE EventSource 수신, 에이전트 채팅 UI
```

---

## 지금 해야 할 작업

### 1. FastAPI 실제 모드 구현 (`backend/main.py`)

현재 `USE_MOCK_MODE=false`이면 모든 엔드포인트가 `501 Not Implemented`.

**TODO 4곳**:

```python
# POST /generate
# 현재: return {"job_id": "92b2d589", "status": "processing"}
# 목표: UUID job_id 생성 → asyncio.create_task로 orchestrator.run() 백그라운드 시작
#       job 상태를 메모리(dict) 또는 파일에 저장

# GET /stream/{job_id}
# 현재: mock JSON 이벤트 재생
# 목표: orchestrator 실행 중 SSE 이벤트 실시간 스트리밍
#       asyncio.Queue 패턴: orchestrator가 Queue에 push → stream 엔드포인트가 pop

# GET /history, GET /analytics
# 현재: mock_agents/history.json 읽기
# 목표: 실제 job 결과를 영속화 (JSON 파일 유지 또는 SQLite)

# PATCH /jobs/:id/favorite, DELETE /jobs/:id
# 현재: history.json 직접 수정
# 목표: 실제 job 저장소에 반영
```

**SSE 스트리밍 방식 (권장)**:
`orchestrator.py`의 `_log_block` 함수가 에이전트 호출 완료 시마다 실행됨.
여기에 `asyncio.Queue`를 주입해서 이벤트를 emit하는 패턴이 가장 자연스러움.

```python
# 개념 구조
job_queues: dict[str, asyncio.Queue] = {}

async def run_agent(job_id, user_input, queue):
    await orchestrator.run(user_input, job_id=job_id, event_queue=queue)
    await queue.put({"type": "done"})

@app.post("/generate")
async def generate(body: GenerateRequest):
    job_id = str(uuid.uuid4())[:8]
    q = asyncio.Queue()
    job_queues[job_id] = q
    asyncio.create_task(run_agent(job_id, body.user_input, q))
    return {"job_id": job_id, "status": "processing"}

@app.get("/stream/{job_id}")
async def stream(job_id: str):
    async def event_gen():
        q = job_queues[job_id]
        while True:
            event = await q.get()
            yield json.dumps(event)
            if event.get("type") == "done":
                break
    return EventSourceResponse(event_gen())
```

**SSE 이벤트 형식** (프론트가 기대하는 타입):
- `agent_start`: `{ type, agent, timestamp }`
- `agent_progress`: `{ type, agent }`
- `agent_done`: `{ type, agent, output, tokens, model }`
- `done`: `{ type }`

### 2. Docker

```
Dockerfile.backend    ← Python 3.12, uvicorn
Dockerfile.frontend   ← Node 20 build → nginx serve
docker-compose.yml    ← backend:8000, frontend:80, 환경변수 주입
```

고려사항:
- `.env` 파일은 compose에서 `env_file`로 주입
- 프론트엔드 빌드 시 Vite proxy는 dev 전용 → 프로덕션에서는 nginx가 `/generate` 등을 backend로 reverse proxy
- `docs/agent_logs/`, `docs/generated_prds/` volume mount 필요 (로그/PRD 파일 영속화)

### 3. CI/CD (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
# push to main → build images → push to registry → deploy
```

고려사항:
- Secrets: `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `MODEL_STRONG`, `MODEL_LIGHT`
- 배포 타겟 미정 (fly.io / Railway / EC2 등)

---

## 환경변수 전체 목록

```
MODEL_STRONG=          # orchestrator·planner·critic·prd_writer
MODEL_LIGHT=           # analyst·gate
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
TAVILY_API_KEY=        # 미설정 시 researcher 비활성 (검색 없이도 동작)
MAX_OUTER_LOOPS=3
MAX_INNER_LOOPS=3
USE_MOCK_MODE=true     # false로 전환하면 실제 에이전트 모드
```

---

## 에이전트 반환값 구조

`orchestrator.run(user_conditions)` 반환:
```python
{
    "job_id": "xxxxxxxx",
    "prd": "# PRD\n...",          # 마크다운 문자열
    "loop_history": [...]          # 루프별 critic/gate 결과
}
```

---

## 로컬 실행

```bash
# 백엔드 (목업 모드)
cd backend && uvicorn main:app --reload --port 8000

# 프런트엔드
cd frontend && npm run dev

# 에이전트 단독 CLI 테스트
python run.py "B2B SaaS, 1인 개발, AI 활용, 월 100만원 수익 목표"
```

---

## 컨벤션

- UI 텍스트 한국어
- CSS 커스텀 변수 (`--color-primary: #8B6F47`, `--color-bg: #F5F1E8`)
- 소프트 삭제 (`deleted: true`), 물리 삭제 금지
- `docs/ai-usage-log.md` append only 기록 유지
