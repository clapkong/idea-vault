# IdeaVault Frontend - Ralph Mode Log

시작: 2026-04-26 21:14:02

---

## Loop 1 (Ralph Mode 재실행)
날짜/시간: 2026-04-26

### 작업 내용
- Vite + React 프로젝트 초기화 (기존 public/agents 이미지 유지)
- react-router-dom, react-markdown 패키지 설치
- 전역 CSS 변수 설정 (테마 컬러: 로스팅 브라운, 크래프트지 등)
- NavBar 컴포넌트 (네비게이션 바, 활성 링크 강조)
- ChatBubble 컴포넌트 (agent/user 말풍선, 로딩 애니메이션 ●●●○○○)
- Home 페이지 (아이디어 입력 textarea, 예시 chip 3개, 추천 받기 버튼)
- Analyze 페이지 (SSE 스트리밍, agent 말풍선, 세션 멈추기)
- History 페이지 (좌우 분할, 히스토리 카드, 즐겨찾기/삭제, 채팅 재현)
- Result 페이지 (목차 사이드바, react-markdown 렌더링, PRD 다운로드)
- Analytics 페이지 (날짜 범위 필터, 요약 카드, 테이블, 파이/바 차트, CSV)
- 빌드 성공 확인

### 생성/수정된 파일
- frontend/index.html
- frontend/src/index.css
- frontend/src/App.css
- frontend/src/App.jsx
- frontend/src/main.jsx
- frontend/src/components/NavBar.jsx
- frontend/src/components/NavBar.css
- frontend/src/components/ChatBubble.jsx
- frontend/src/components/ChatBubble.css
- frontend/src/pages/Home.jsx
- frontend/src/pages/Home.css
- frontend/src/pages/Analyze.jsx
- frontend/src/pages/Analyze.css
- frontend/src/pages/History.jsx
- frontend/src/pages/History.css
- frontend/src/pages/Result.jsx
- frontend/src/pages/Result.css
- frontend/src/pages/Analytics.jsx
- frontend/src/pages/Analytics.css

---

## Loop 2
날짜/시간: 2026-04-26

### 작업 내용
- Vite 프록시 설정 (localhost:8000 하드코딩 제거, 상대경로로 변경)
- Home.jsx: POST body 필드명 수정 (idea → user_input)
- Analytics.jsx: 백엔드 응답 형식 대응 ({summary, data} 또는 flat array)
- History.jsx: events 배열 기반 채팅 재구성 (loop_history 비어있을 때)
- ChatBubble: analyst 에이전트 추가, 아이콘 fallback 처리
- backend/main.py: CORS에 5173 포트 추가, 누락 엔드포인트 추가 (stop/favorite/delete)
- backend/main.py: analytics 날짜 범위 필터링 구현
- backend/main.py: result 엔드포인트에 events 필드 포함
- frontend/.gitignore 추가

### 생성/수정된 파일
- frontend/vite.config.js
- frontend/.gitignore
- frontend/src/pages/Home.jsx
- frontend/src/pages/Analyze.jsx
- frontend/src/pages/History.jsx
- frontend/src/pages/Result.jsx
- frontend/src/pages/Analytics.jsx
- frontend/src/components/ChatBubble.jsx
- backend/main.py

---

## Loop 3
날짜/시간: 2026-04-26

### 작업 내용
- btn-primary 공통 스타일을 index.css로 이동 (Home/Analyze/History 전체에 적용)
- Home.css에서 중복 btn-primary 제거
- Analyze 페이지: 연결 중 상태(connecting) 추가, fade-pulse 애니메이션
- NotFound 페이지 추가 (404 fallback)
- App.jsx: * 와일드카드 라우트 추가
- package.json name 수정 (ideavault-app → ideavault-frontend)
- 빌드 최종 확인 (197 모듈, 오류 없음)

### 생성/수정된 파일
- frontend/src/index.css
- frontend/src/App.jsx
- frontend/src/pages/Home.css
- frontend/src/pages/Analyze.jsx
- frontend/src/pages/Analyze.css
- frontend/src/pages/NotFound.jsx (신규)
- frontend/package.json

<promise>FRONTEND_COMPLETE</promise>

---

## Loop 4
날짜/시간: 2026-04-27

### 작업 내용
- Analyze: ctrl+s 등 키보드 단축키로 세션 종료되는 현상 방지 (keydown 이벤트 차단)
- ChatBubble: Researcher tokens=0 미표시 버그 수정 (`typeof tokens === 'number'` 조건)
- ChatBubble: 버블 내 텍스트 클리핑 방지 (overflow-wrap: break-word)
- ChatBubble: 버블 가로 길이 70% → 88%
- ChatBubble: 에이전트 버블에 ReactMarkdown + remark-gfm 렌더링 적용
- PRD Viewer: remark-gfm 설치 및 적용으로 테이블 깨짐 수정
- PRD Viewer: TOC가 콘텐츠와 함께 스크롤되는 오류 수정 (position: sticky)
- PRD Writer: 뒤로가기 버튼 두 줄로 깨지는 현상 수정 (min-width, white-space: nowrap)
- History: ❤️/🤍 이모티콘 → SVG 하트 아이콘으로 교체
- History: 즐겨찾기만 보기 필터 버튼 구현 (favOnly 상태)
- Home: 예시 Chip을 전체 텍스트에서 이모티콘+키워드 형태로 개선

### 생성/수정된 파일
- frontend/src/pages/Analyze.jsx
- frontend/src/pages/Home.jsx
- frontend/src/pages/History.jsx
- frontend/src/pages/History.css
- frontend/src/pages/Result.jsx
- frontend/src/pages/Result.css
- frontend/src/components/ChatBubble.jsx
- frontend/src/components/ChatBubble.css
- frontend/package.json (remark-gfm 추가)

### TODO
- [ ] Token Analytics: 세션 내 복수 모델/에이전트별 통계 — 백엔드 구조 개편 필요
  - 각 mock JSON events에 `model` 필드 추가
  - /analytics 엔드포인트가 agent×model×tokens 단위로 집계
  - Researcher agent는 tokens=0, model="n/a" 처리

---

## Loop 5
날짜/시간: 2026-04-27

### 작업 내용
- PRD Viewer: TOC 스크롤 고정 재수정 — sticky 방식 제거, flex `min-height: 0` 방식으로 교체 + App.jsx main에 `minHeight: 0, overflow: hidden` 추가
- History: 좌측 사이드바 고정, 우측 채팅만 스크롤 — 동일한 min-height: 0 방식 적용
- PRD Viewer: 테이블 헤더 배경색 구분 — `var(--background)` → `var(--border)`
- PRD Viewer: 다운로드 버튼 헤더로 이동 — footer 제거, 헤더 우측에 'PRD 다운로드' 버튼 배치
- ChatBubble: 버블 내 MD 헤더(h1/h2/h3) — 글자 크기 유지, bold만 적용 (font-size: inherit)
- ChatBubble: PRD Writer 버블 → 'IdeaVault가 만들어준 나만의 PRD 보기!' 버튼으로 교체 (jobId prop 추가)
- Analyze/History: jobId를 ChatBubble에 전달
- Vite proxy: /analytics, /history, /result 직접 접근 시 JSON 반환되는 문제 수정 — bypass 함수로 text/html 요청은 프록시 우회

### 생성/수정된 파일
- frontend/src/App.jsx
- frontend/src/pages/Result.jsx
- frontend/src/pages/Result.css
- frontend/src/pages/History.jsx
- frontend/src/pages/History.css
- frontend/src/pages/Analyze.jsx
- frontend/src/components/ChatBubble.jsx
- frontend/src/components/ChatBubble.css
- frontend/vite.config.js

### TODO
- (없음 — 이전 TODO인 Token Analytics 백엔드 구조 개편은 계속 유효)

---

## Loop 6
날짜/시간: 2026-04-27

### 작업 내용
- PRD Viewer: TOC 패널 `overflow: hidden`으로 고정 (스크롤 완전 비활성화)
- PRD Viewer: result-content에 `overscroll-behavior: contain` 추가
- History: job-list / chat-messages-history 양쪽에 `overscroll-behavior: contain` → 목록/대화 스크롤 독립화
- ChatBubble: `bubble-wrapper` max-width `88%` → `65%` (버블 가로 길이 축소)
- ChatBubble: `AGENT_MESSAGES` 상수 추가 — 에이전트별 progress/done 메시지
  - loading 시 백엔드 메시지 없으면 상수 fallback
  - done 시 완료 메시지를 출력 상단에 표시 (`.done-msg`)
- ChatBubble: `AGENT_COLORS` 상수 추가 — 에이전트별 레이블 색상 (palette 기반)
- ChatBubble: critic done 메시지 `"..."` → `"추가 정보 확인을 완료했습니다!"`
- ChatBubble: prd_writer done 버블 — "PRD 작성이 완료되었습니다!" + 버튼
- Analyze: `prdReady` 배너/상태 제거 — ChatBubble 버튼과 중복 표시 버그 수정

### 생성/수정된 파일
- frontend/src/pages/Result.css
- frontend/src/pages/History.css
- frontend/src/pages/Analyze.jsx
- frontend/src/pages/Analyze.css
- frontend/src/components/ChatBubble.jsx
- frontend/src/components/ChatBubble.css
- docs/claude_code/ai-usage-log.md

### TODO
- (없음)
