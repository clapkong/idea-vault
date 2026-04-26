# 작업: Mock/Real 모드 전환 구조 추가

## 목표
현재 Mock 전용 코드를 나중에 Real 모드로 쉽게 전환할 수 있도록 구조 개선

## 현재 상황
- `backend/main.py`가 Mock 데이터만 사용
- 모든 엔드포인트가 Mock 파일을 직접 읽음
- Real orchestrator 연결 시 전체 수정 필요

## 요구사항

### 1. 환경변수로 모드 구분
- `USE_MOCK_MODE` 환경변수 추가
- true면 Mock 모드, false면 Real 모드
- 기본값은 "true"

### 2. 각 엔드포인트에 모드 분기 추가
모든 엔드포인트에서:
- Mock 모드일 때: 현재 로직 그대로 유지
- Real 모드일 때: 501 에러 (Not Implemented) 반환

**분기가 필요한 엔드포인트**:
- POST /generate
- GET /stream/{job_id}
- GET /result/{job_id}

**분기 불필요** (Mock만 지원):
- GET /history
- GET /analytics

### 3. 함수명 명확화
- Mock 전용 함수는 이름에 "mock" 포함
- 예: `event_stream` → `mock_event_stream`
- 나중에 `real_event_stream` 추가하기 쉽게

### 4. Real 모드 준비
Real 모드에서는 다음 로직이 필요 (TODO 주석으로 표시):
- **POST /generate**: uuid 생성, orchestrator.run() Background 실행
- **GET /stream**: 로그 파일 tail -f 방식으로 읽기
- **GET /result**: data/jobs/{job_id}/ 폴더에서 파일 읽기

## 실행 테스트

### Mock 모드 (현재와 동일하게 작동)
```bash
USE_MOCK_MODE=true uvicorn main:app --reload
```

### Real 모드 (501 에러 반환)
```bash
USE_MOCK_MODE=false uvicorn main:app --reload
```

## 주의사항
- Mock 모드 동작은 현재와 100% 동일하게 유지
- Real 모드는 구현하지 않고 501 에러만
- 코드 구조만 개선, 기능 변경 없음