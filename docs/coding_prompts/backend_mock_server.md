# 작업: FastAPI Mock API 구현

## 목표
Frontend 개발을 위한 Mock API 서버 구축. Mock 데이터 파일을 읽어서 SSE 스트리밍 및 REST API 제공.
실제 Agent 실행을 매번 할 수 없기 때문에, 기존 로그를 agent를 실행하듯이 streaming처럼 반환

## 파일 위치
- `backend/main.py` - 여기에 작성
- Mock 데이터: `backend/mock/` 폴더
  - `92b2d589.json` - 실제 분석 데이터 (events, prd, loop_history)
  - `abc12345.json` - 다른 작업 데이터
  - `def67890.json` - 또 다른 작업 데이터
  - `ghi11111.json` - 추가 작업 데이터
  - `history.json` - 히스토리 목록

## 기술 스택
- FastAPI
- sse-starlette (SSE용)
- uvicorn
- CORS 미들웨어

## 구현할 엔드포인트

### 1. POST /generate
**역할**: 분석 시작 요청

**요청 Body**:
```json
{"user_input": "저 개발 시작한 지..."}
```

**응답**:
```json
{"job_id": "92b2d589", "status": "processing"}
```

**로직**:
- user_input은 무시
- 항상 "92b2d589" 반환 (Mock이니까)

---

### 2. GET /stream/{job_id}
**역할**: SSE로 실시간 이벤트 스트리밍

**동작**:
1. job_id로 `backend/mock/{job_id}.json` 파일 찾기
2. 파일 없으면 404
3. events 배열 순회하면서:
   - `event["delay_sec"]`만큼 `asyncio.sleep()`
   - delay_sec 필드는 **제외**하고 나머지만 전송
   - SSE 형식: `data: {json}\n\n`

**중요**:
- EventSourceResponse 사용
- async generator 패턴
- `ensure_ascii=False` (한글 깨짐 방지)

**예시 전송 데이터**:
```json
{"type": "agent_start", "agent": "planner", "timestamp": "11:39:15"}
```
(delay_sec는 빠짐)

---

### 3. GET /result/{job_id}
**역할**: PRD와 분석 히스토리 반환

**동작**:
1. `backend/mock/{job_id}.json` 파일 읽기
2. prd, loop_history만 추출해서 반환

**응답**:
```json
{
  "prd": "# 제목\n\n## 1. ...",
  "loop_history": []
}
```

---

### 4. GET /history
**역할**: 전체 작업 목록 반환

**동작**:
- `backend/mock/history.json` 읽어서 그대로 반환

**응답**: history.json 내용 전체

---

### 5. GET /analytics
**역할**: 토큰 사용량 통계 반환

**쿼리 파라미터** (선택):
- `range`: "all" (기본값), "7days", "30days", "today"

**응답**:
```json
{
  "summary": {
    "total_jobs": 4,
    "total_tokens": 45231,
    "total_cost": 0.87
  },
  "data": [
    {
      "job_id": "92b2d589",
      "date": "2026-04-26",
      "title": "내 음악 취향 분석기",
      "model": "sonnet",
      "tokens": 23666,
      "cost": 0.42
    }
  ]
}
```

**로직**:
- 하드코딩된 Mock 데이터 반환
- range 파라미터는 일단 무시해도 됨 (나중에 필터링 추가)
- history.json에서 job 정보 가져와서 조합

---

## CORS 설정
- allow_origins: `["http://localhost:3000"]`
- allow_credentials: True
- allow_methods: `["*"]`
- allow_headers: `["*"]`

**이유**: Frontend React 앱이 localhost:3000에서 실행됨

---

## 에러 처리
- 파일 없으면 404 + `{"detail": "Job not found"}`
- JSON 파싱 실패하면 500

---

## 실행 후 테스트
```bash
uvicorn main:app --reload
```

브라우저에서:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/history
- http://localhost:8000/result/92b2d589
- http://localhost:8000/stream/92b2d589 (EventSource 연결 필요)

---

## 주의사항
- Mock 파일 경로는 `Path(__file__).parent / "mock"` 사용
- SSE에서 delay_sec 필드 반드시 제외
- 한글 깨지지 않게 `ensure_ascii=False`
- async/await 패턴 사용

구현해주세요!