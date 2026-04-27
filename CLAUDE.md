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
