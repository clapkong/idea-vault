# IdeaVault Frontend - Ralph Mode

## Ralph Mode 실행
이 프롬프트를 N번 반복 실행하여 점진적으로 완성합니다.

**각 루프 완료 후 반드시:**
1. ai-usage-log.md 파일에 **append** (기존 내용 유지, 맨 아래 추가)
   - Loop 번호
   - 날짜/시간
   - 작업 내용
   - 생성/수정된 파일 목록
2. `git add .`
3. `git commit -m "ralph-loop-N: [작업 내용 요약]"`
4. 다음 루프 진행

**3번 루프 완료 시:**
- ai-usage-log.md 마지막에 `<promise>FRONTEND_COMPLETE</promise>` 출력

---

## 프로젝트 개요
초보 개발자가 아이디어를 입력하면 AI 에이전트들이 검증/개선하여 PRD 문서를 생성하는 웹 서비스의 프론트엔드.

**캐치프레이즈**: "막연한 아이디어도 괜찮아요. AI가 함께 다듬어 PRD로 만들어드립니다"

---

## 기술 스택
- React (Vite)
- React Router
- react-markdown
- 순수 CSS

---

## 테마 컬러
```css
:root {
  --primary: #8B6F47;      /* 로스팅 브라운 */
  --secondary: #A68A64;    /* 라떼 베이지 */
  --background: #F5F1E8;   /* 크래프트지 */
  --card: #FDFBF7;         /* 화이트 크림 */
  --border: #DED4C0;       /* 부드러운 경계 */
  --text: #3D2E1F;         /* 다크 초콜릿 */
}
```

---

## Mock API (localhost:8000)

**엔드포인트:**
- `POST /generate` → `{job_id: string, status: "processing"}`
- `GET /stream/:jobId` (SSE) → 실시간 로그 스트리밍
- `GET /result/:jobId` → `{prd: string, loop_history: object[]}`
- `GET /history` → `[{job_id, created_at, title, input_preview, favorite}, ...]`
- `GET /analytics` → `[{job_id, date, model, tokens, cost}, ...]`
- `PATCH /jobs/:jobId/favorite` → `{favorite: boolean}`
- `DELETE /jobs/:jobId` → `{deleted: boolean}`

**SSE 메시지 형식:**
```json
{"type": "agent_start", "agent": "planner", "timestamp": "11:39:15"}
{"type": "agent_progress", "agent": "planner", "message": "주제 발굴 중..."}
{"type": "agent_done", "agent": "planner", "output": "...", "tokens": 1234}
{"type": "done", "prd_url": "/result/abc123"}
```

---

## 페이지 구조

### 1. 홈 페이지 (`/`)

**레이아웃:**
- 상단: 네비게이션 바 (Idea Vault | 추천 받기 | 히스토리 | 토큰 사용량 통계)
- 중앙:
  - 캐치프레이즈: "막연한 아이디어도 괜찮아요. AI가 함께 다듬어 PRD로 만들어드립니다"
  - 큰 Textarea (회색 placeholder, 최소 20자, 최대 500자)
  - 우측 하단: "추천 받기" 버튼 (primary 컬러)
  - 하단: 글자 수 카운터 (xxx/500자)
  - 예시 프롬프트 3개 chip 버튼 (클릭 시 textarea 채움):
    1. "취업 포트폴리오 만들어야 해요. 백엔드 개발자 (주로 사용하는 언어: JavaSpring) 지망생이에요. 프로젝트에 취업할 때 제 역량이 최대한 부각될 수 있는 요소가 많이 있었으면 좋겠어요. 시간은 한 3주 정도 잡고 있어요"
    2. "소프트웨어 3학년 전공 캡스톤 수업 프로젝트인데 팀이 3명이고 한 학기 동안 해야 해요. 교수님께서 실생활과 연관된 주제를 원하세요. 팀원은 JavaScript 포함한 웹 프론트 1명, Swift 경력자 1명, 나머지 한명은 SQLD가 있고 백엔드를 공부하고 싶어해요. 디자인 하기 싫고 ML은 너무 어려워요. 투두앱 같은 뻔한 건 만들기 싫어요."
    3. "저 개발 시작한 지 한 달 됐어요. 유튜브로 파이썬 기초만 봤고요. 뭔가 제가 쓸 수 있는걸 만들어보고 싶은데 뭘 만들 수 있는지도 모르겠어요. 저 음악 진짜 좋아하는데 음악이랑 개발 연결하고 싶어요. 근데 꼭 음악이 아니여도 괜찮아요. 돈 없어서 유료 API 못 써요. 2주 안에 끝내야 하고 혼자예요."

**동작:**
- [추천 받기] 클릭 → `POST /generate` → `{job_id}` 받음 → `navigate to /analyze/:jobId`

---

### 2. 분석 진행 페이지 (`/analyze/:jobId`)

**레이아웃:**
- 상단: 네비게이션 바
- 채팅 영역 (전체 너비, 세션 멈추기 영역 제외):
  - 맨 위: 사용자 입력 말풍선 (우측 정렬, User 아이콘)
  - 이후: Agent별 말풍선 (좌측 정렬):
    - Agent 이름 + 아이콘 (말풍선 왼쪽, 채팅 유저처럼)
    - 출력 내용 (말풍선 내)
    - 타임스탬프 (H:MM AM/PM) + 토큰 수 (말풍선 밑/옆에 연하게)
    - 진행 중: 로딩 애니메이션 (●●●○○○) + 간단 설명
    - 완료: 전체 텍스트
  - PRD Writer 완료 시: [완성된 PRD 보기] 버튼
- 중앙 하단: [세션 멈추기] 버튼
- 자동 스크롤 (에이전트 출력이 쌓이면)
- 세션 중단 시: "세션이 {사용자의 요청으로 / 에러로 인해} 종료되었습니다"

**동작:**
- 마운트 시 `EventSource('/stream/:jobId')` 연결
- SSE 메시지 받을 때마다 채팅에 추가
- `type: "done"` 받으면 `navigate to /result/:jobId` (자동)
- [세션 멈추기] 클릭 → `POST /jobs/:jobId/stop`

---

### 3. 히스토리 페이지 (`/history`)

**레이아웃: 좌우 분할**

**왼쪽 사이드바 (30%):**
- 상단: 검색창
- 정렬 드롭다운 (최신순/오래된순)
- 히스토리 카드 리스트:
  - 제목 (PRD 첫 번째 헤더)
  - 날짜 + 소요 시간
  - 입력 미리보기 (첫 100자)
  - 하트 아이콘 (❤️=즐겨찾기, 🤍=일반) - 클릭 토글
  - [삭제] 버튼 - 삭제 시 확인창 필수
- 맨 위 카드 자동 선택 (선택된 카드는 배경색 강조)

**오른쪽 채팅 영역 (70%):**
- 분석 진행 페이지와 동일한 UI
- 사이드바에서 카드 클릭 → `GET /result/:jobId` → 채팅 로드
- [세션 멈추기] 버튼 없음 (이미 완료된 것)
- [완성된 PRD 보기] 버튼 → `navigate to /result/:jobId`

**동작:**
- 마운트 시 `GET /history`
- 맨 위 카드 자동 선택 → `GET /result/:jobId`
- 검색: 로컬 필터링 (제목 + 입력)
- 정렬: 로컬 정렬
- 하트 클릭: `PATCH /jobs/:jobId/favorite`
- [삭제]: `DELETE /jobs/:jobId` → 리스트에서 제거

---

### 4. PRD 뷰어 (`/result/:jobId`)

**레이아웃: 좌우 분할**

**왼쪽 목차 (20%):**
- "목차" 제목
- PRD의 ## (h2) 섹션 8개 추출
- 클릭 시 해당 섹션으로 스크롤

**오른쪽 PRD (80%):**
- [뒤로가기] 버튼 (좌측 상단)
- "PRD 뷰어" 제목 (중앙 상단)
- 마크다운 렌더링 (react-markdown)
- 스크롤 가능
- 하단: [IdeaVault가 만들어준 나만의 PRD 다운로드 하기!] 버튼

**동작:**
- 마운트 시 `GET /result/:jobId`
- 마크다운 렌더링
- 다운로드: Blob 생성 → `prd_{job_id}.md` 저장

---

### 5. 토큰 사용량 통계 (`/analytics`)

**레이아웃: 좌우 분할**

**상단:**
- 네비게이션 바
- 제목: "📊 토큰 사용량 통계"
- 날짜 범위 버튼: [오늘] [7일] [30일] [전체]
- 요약 카드: "총 12개 | 542,331 tokens | $9.87" (적절한 UI로 구현)

**왼쪽 테이블 (60%):**
- 컬럼: 날짜 | 제목 | 모델 | 토큰 | 비용
- 스크롤 가능
- 하단: [📊 CSV로 내보내기] 버튼

**오른쪽 차트 (40%):**
- 상단: 그래프 선택 chip (모델별 / 날짜별)
- 모델별 파이 차트:
  - 제목: "모델 별 사용량"
  - Sonnet: 75%
  - Haiku: 25%
- 날짜별 막대 그래프:
  - 제목: "날짜 별 사용량"
  - x축: 날짜, y축: 토큰량
  - 가능하면 모델별로 색 다르게

**동작:**
- 마운트 시 `GET /analytics`
- 날짜 범위 클릭 → `GET /analytics?range=7days`
- CSV 다운로드: 테이블 데이터 → CSV 변환 → 다운로드

---

## Agent 아이콘

**위치:** `/frontend/public/agents/`
- `planner.png`
- `researcher.png`
- `critic.png`
- `writer.png`
- `gate.png`
- `prd_writer.png`
- `user.png`

**사용:**
```jsx
<img src="/agents/planner.png" alt="Planner Agent" />
```

---

## 디자인 가이드

- 미니멀하고 깔끔한 디자인
- 그라데이션과 이모티콘은 사용하지 말 것
- 주요 버튼: primary 컬러 (#8B6F47)
- 말풍선: 둥근 모서리, 그림자 약간
- 하트: 빈 하트 (🤍) ↔ 빨간 하트 (❤️)
- Agent 아이콘: 프로필 사진 형태
- 로딩: ●●●○○○ 애니메이션

---

## 제약사항

- Mock API 우선 (실제 Backend는 나중에)
- 모바일 반응형 불필요
- 다크모드 불필요
- 간단하게 시작, 화려한 UI는 나중에