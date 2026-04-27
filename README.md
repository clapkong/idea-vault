# Idea Vault

막연한 프로젝트 아이디어를 입력하면 다중 에이전트 AI 파이프라인이 정제·검증하여 완성된 PRD(Product Requirements Document)를 생성해주는 앱입니다.

---

## Architecture

```
사용자 입력
    │
    ▼
Frontend (React + Vite)
    │  POST /generate
    │  GET  /stream/:job_id  ── SSE 실시간 스트리밍
    ▼
Backend (FastAPI)
    │
    ▼
에이전트 파이프라인 (백엔드 merge 예정)
  planner → researcher → analyst → critic → prd_writer
    │
    ▼
PRD 결과물 (Markdown)
```

- **Frontend**: React 19 + Vite, Server-Sent Events로 에이전트 진행상황 실시간 수신
- **Backend**: FastAPI + sse-starlette, 현재는 목업 모드(`USE_MOCK_MODE=true`)로 동작
- **에이전트 루프**: 별도 백엔드 브랜치에서 구현 중이며 이 저장소에 merge될 예정

---

## Getting Started

### 1. 환경 설정

```bash
# Python 가상환경 생성 및 의존성 설치
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# .env 파일 생성 (.env.example 복사 후 API 키 입력)
cp .env.example .env
```

### 2. 백엔드 실행

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**목업 모드** (API 키 없이 UI 확인): `.env`에서 `USE_MOCK_MODE=true` 설정

### 3. 프론트엔드 실행 (새 터미널)

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

> 백엔드가 `localhost:8000`에서 실행 중이어야 프런트엔드 API 프록시가 정상 작동합니다.

---

## Features

- **아이디어 입력**: 20-500자 자유 텍스트로 프로젝트 아이디어 제출
- **실시간 에이전트 스트리밍**: SSE를 통해 각 에이전트의 처리 과정을 채팅 형태로 확인
- **PRD 뷰어**: 생성된 PRD를 Markdown 렌더링 + 사이드 목차 네비게이션으로 열람, `.md` 다운로드
- **히스토리**: 과거 세션 목록, 검색·정렬, 즐겨찾기, 소프트 삭제
- **애널리틱스**: 모델별 토큰 사용량(파이 차트), 날짜별 추이(막대 차트), CSV 내보내기

---

## API Endpoints

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/generate` | 아이디어 제출 → `{ job_id, status }` 반환 |
| `GET` | `/stream/{job_id}` | SSE 스트림 — 에이전트 이벤트 순차 전송 |
| `GET` | `/result/{job_id}` | 완료된 PRD + 이벤트 기록 조회 |
| `GET` | `/history` | 전체 세션 목록 (삭제 제외) |
| `GET` | `/analytics?range=` | 토큰 사용 통계 (`today` / `7days` / `30days` / `all`) |
| `PATCH` | `/jobs/{job_id}/favorite` | 즐겨찾기 토글 |
| `POST` | `/jobs/{job_id}/stop` | 실행 중인 세션 중단 |
| `DELETE` | `/jobs/{job_id}` | 소프트 삭제 |

### SSE 이벤트 스키마

```json
// agent_start
{ "type": "agent_start", "agent": "planner", "timestamp": "11:39:15" }

// agent_progress
{ "type": "agent_progress", "agent": "planner" }

// agent_done
{ "type": "agent_done", "agent": "planner", "output": "...", "tokens": 1615, "model": "claude-sonnet" }

// 완료
{ "type": "done" }
```

---

## Tech Stack

| 영역 | 기술 |
|------|------|
| Frontend | React 19, Vite 8, React Router 7, react-markdown |
| Backend | FastAPI, uvicorn, sse-starlette, Pydantic 2 |
| Python | 3.12.2 |

---

## Project Structure

```
ideavault-frontend/
├── frontend/
│   ├── src/
│   │   ├── pages/          # Home, Analyze, Result, History, Analytics, NotFound
│   │   ├── components/     # NavBar, ChatBubble
│   │   ├── App.jsx         # 라우터 정의
│   │   └── main.jsx
│   ├── public/             # 에이전트 아이콘 이미지
│   ├── vite.config.js      # API 프록시 설정 (→ localhost:8000)
│   └── package.json
├── backend/
│   ├── main.py             # FastAPI 엔드포인트 + 목업 모드 분기
│   ├── requirements.txt
│   └── mock_agents/        # 목업 JSON 데이터 및 생성된 PRD 샘플
└── docs/                   # AI 사용 로그
```
