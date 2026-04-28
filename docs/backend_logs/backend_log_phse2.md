# 작업: FastAPI Real Mode 구현 (Phase 2)

## 시작 전 필수
아래 파일들을 먼저 읽어라.
- backend/main.py
- backend/mock_agents/history.json  (응답 형식 파악용)
- backend/mock_agents/92b2d589.json (analytics 데이터 구조 파악용)
- data/jobs/ 디렉토리 구조 (있으면)

---

## 배경
Phase 1에서 POST /generate, GET /stream, GET /result, POST /stop 구현 완료.
data/jobs/{job_id}/ 에 prd.md, loop_history.json, events.json, meta.json 저장됨.
이번 Phase는 나머지 4개 엔드포인트 real mode 전환.

---

## 구현 목표

### 1. GET /history (Real)
data/jobs/ 폴더 전체 스캔 → meta.json 읽기 → 응답 조합.

응답 형식은 mock_agents/history.json과 동일하게 맞출 것.

- prd.md 첫 번째 `# ` 줄에서 title 추출
- input.txt에서 input_preview 앞 100자
- meta.json의 favorite, status, duration_sec, created_at
- deleted: true인 job은 제외
- 최신순 정렬 (created_at 기준)

### 2. GET /analytics (Real)
pandas 사용 필수 (과제 요구사항).

데이터 소스: data/jobs/*/meta.json의 tokens, cost 필드.

- range 쿼리파라미터: today / 7days / 30days / all
- 날짜 필터는 meta.json의 created_at 기준
- 응답: { summary: { total_jobs, total_tokens, total_cost }, data: Row[] }
- Row: { job_id, date, title, tokens, cost }
- status가 completed인 job만 포함
- pandas DataFrame으로 집계 후 to_dict('records')

### 3. PATCH /jobs/{job_id}/favorite (Real)
- data/jobs/{job_id}/meta.json의 favorite 토글
- 반환: { favorite: bool }
- job 없으면 404

### 4. DELETE /jobs/{job_id} (Real)
소프트 삭제 — 물리 삭제 금지 (analytics 데이터 보존).
- meta.json에 deleted: true 추가
- 반환: { deleted: true }
- job 없으면 404

---

## 주의사항
- USE_MOCK_MODE 분기 반드시 유지
- encoding="utf-8" 전체 적용
- data/jobs/ 없으면 빈 배열 반환 (에러 아님)
- pandas import 추가