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
