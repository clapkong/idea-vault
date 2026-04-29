# 작업: FastAPI Real Mode 구현 (Phase 1)

## 시작 전 필수
아래 파일들을 먼저 전부 읽어라. 코드 작성 전에 읽기 완료 확인할 것.
- backend/main.py
- backend/agents/orchestrator.py
- backend/config.py
- backend/mock_agents/92b2d589.json (SSE 이벤트 형식 파악용)

---

## 배경
- USE_MOCK_MODE=false 이면 현재 모든 엔드포인트가 501
- orchestrator는 독립 실행 가능한 상태 (python run.py로 테스트됨)
- 프론트엔드는 SSE EventSource로 /stream/{job_id}를 수신 중

---

## 구현 목표

### 1. asyncio.Queue 기반 이벤트 브릿지
orchestrator.py를 수정해서 run() 함수가 event_queue를 선택적으로 받을 수 있게 한다.
- 시그니처: `async def run(user_conditions, job_id=None, event_queue=None)`
- 에이전트 호출 완료 시마다 queue에 이벤트 push
- event_queue가 None이면 기존 동작 유지 (CLI 호환성 보존)

프론트가 기대하는 이벤트 타입 (mock 파일에서 형식 확인):
- agent_start: { type, agent, timestamp }
- agent_progress: { type, agent }  
- agent_done: { type, agent, output, tokens }
- done: { type, job_id }

### 2. POST /generate (Real)
- uuid4().hex[:8]로 job_id 생성
- data/jobs/{job_id}/ 폴더 생성
- input.txt, meta.json 저장 (status: "processing")
- asyncio.create_task()로 orchestrator 백그라운드 실행
- running_jobs: Dict[str, asyncio.Task] 딕셔너리로 추적
- 반환: { job_id, status: "processing" }

### 3. orchestrator 완료 후 파일 저장
백그라운드 태스크 안에서:
- data/jobs/{job_id}/prd.md
- data/jobs/{job_id}/loop_history.json
- data/jobs/{job_id}/meta.json 업데이트 (status, duration_sec, tokens, cost)
- 실패 시 meta.json status: "failed", error 필드 추가
- 타임아웃 30분 (asyncio.wait_for, timeout=1800)

비용 계산:
- sonnet: prompt $3/1M, completion $15/1M
- haiku: prompt $0.25/1M, completion $1.25/1M

### 4. GET /stream/{job_id} (Real)
- job_queues[job_id]에서 이벤트 pop
- EventSourceResponse로 스트리밍
- type=="done" 이벤트 받으면 스트림 종료
- job_id 없으면 404

### 5. GET /result/{job_id} (Real)
- data/jobs/{job_id}/prd.md 읽기
- data/jobs/{job_id}/loop_history.json 읽기
- 파일 없으면 404

### 6. POST /jobs/{job_id}/stop (Real)
- running_jobs[job_id] 태스크 cancel
- meta.json status: "stopped"

---

## 주의사항
- USE_MOCK_MODE 분기는 반드시 유지. Mock 모드 건드리지 말 것
- 모든 파일 I/O는 encoding="utf-8"
- orchestrator import: `from agents.orchestrator import run as orchestrator_run`
- asyncio import 추가 필요
- data/jobs/ 디렉토리가 없으면 자동 생성

---

## 완료 기준
1. USE_MOCK_MODE=false 상태에서 uvicorn 실행 후 에러 없음
2. POST /generate → job_id 반환 확인
3. GET /stream/{job_id} → SSE 연결 확인 (실제 orchestrator 실행 안 해도 됨)
4. GET /result/없는ID → 404 확인