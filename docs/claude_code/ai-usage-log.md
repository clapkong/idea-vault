backend/
1. mock_fastapi.md
실제 Agent 실행을 백엔드/프론트엔드 디버깅 단계에서 매번 할 수 없기 때문에, 
이전 실행 로그를 agent를 실행하듯이 streaming처럼 반환해주는 mockAPI

검증: swaggerUI에서 직접 엔드포인트 (/generate, /stream, /result, /history, /analytics) 실행해보고 sanity check 진행

실행 결과: 
완료입니다. 구현 내용 요약:

  backend/main.py 생성됨

  ┌──────────────────────┬──────┬───────────────────────────────────────┐
  │      엔드포인트      │ 상태 │                 비고                  │
  ├──────────────────────┼──────┼───────────────────────────────────────┤
  │ POST /generate       │ ✅   │ 항상 job_id: 92b2d589 반환            │
  ├──────────────────────┼──────┼───────────────────────────────────────┤
  │ GET /stream/{job_id} │ ✅   │ SSE, delay_sec 반영 & 제외, 한글 정상 │
  ├──────────────────────┼──────┼───────────────────────────────────────┤
  │ GET /result/{job_id} │ ✅   │ prd + loop_history 반환               │
  ├──────────────────────┼──────┼───────────────────────────────────────┤
  │ GET /history         │ ✅   │ history.json 그대로 반환              │
  ├──────────────────────┼──────┼───────────────────────────────────────┤
  │ GET /analytics       │ ✅   │ 하드코딩 Mock, range 파라미터 수용    │
  └──────────────────────┴──────┴───────────────────────────────────────┘

  주요 사항
  - Mock 폴더 경로는 mock_agents/로 자동 감지 (프롬프트의 mock/와 다름)
  - sse-starlette, uvicorn[standard] 설치 완료 및 requirements.txt 갱신
  - 실행: venv/bin/uvicorn main:app --reload (venv의 uvicorn 사용)

평가: 각 엔드포인트는 잘 실행이 되나, mock 구조가 하드코딩되어 있어, 이후 교체를 하려면 수정사항이 많다는 아쉬운 점 존재

2. mock_frontapi_refactor.md
수정 내용                                                                                          
   ──────────────────────────────────────────────────────────────────────────────────────────────────
  ┌──────────────────────────────┬────────────────┬────────────────────────────────────────┐         
  │             항목             │    변경 전     │                변경 후                 │         
  ├──────────────────────────────┼────────────────┼────────────────────────────────────────┤         
  │ 모드 구분                    │ 없음           │ USE_MOCK_MODE 환경변수 (기본값 "true") │         
  ├──────────────────────────────┼────────────────┼────────────────────────────────────────┤         
  │ event_stream                 │ Mock 전용 함수 │ mock_event_stream으로 이름 변경        │         
  ├──────────────────────────────┼────────────────┼────────────────────────────────────────┤         
  │ POST /generate               │ Mock만         │ Mock/Real 분기 (Real → 501)            │         
  ├──────────────────────────────┼────────────────┼────────────────────────────────────────┤         
  │ GET /stream/{job_id}         │ Mock만         │ Mock/Real 분기 (Real → 501)            │         
  ├──────────────────────────────┼────────────────┼────────────────────────────────────────┤         
  │ GET /result/{job_id}         │ Mock만         │ Mock/Real 분기 (Real → 501)            │       
  ├──────────────────────────────┼────────────────┼────────────────────────────────────────┤         
  │ GET /history, GET /analytics │ Mock만         │ 변경 없음                              │
  └──────────────────────────────┴────────────────┴────────────────────────────────────────┘         
  실행 방법                                                              
  # Mock 모드 (현재와 동일)
  USE_MOCK_MODE=true uvicorn main:app --reload                                                       
                                                                                                   
  # Real 모드 (501 반환)                                                                             
  USE_MOCK_MODE=false uvicorn main:app --reload

---

## 3. frontend_ui_polish — 2026-04-27

### 작업 내용

**[PRD Viewer]**
- 좌측 목차(TOC) 패널 고정: `overflow-y: auto` → `overflow: hidden` (스크롤 비활성화)
- 우측 PRD 콘텐츠 영역에 `overscroll-behavior: contain` 추가 (스크롤 이벤트 전파 차단)

**[History]**
- job-list / chat-messages-history 양쪽에 `overscroll-behavior: contain` 추가 → 목록/대화 스크롤 독립화

**[ChatBubble — History & Analysis 공통]**
- `bubble-wrapper` max-width `88%` → `65%` (버블 가로 길이 축소)
- `AGENT_MESSAGES` 상수 추가: 에이전트별 loading 진행 메시지 & 완료 메시지(done)
  - loading 시 백엔드 progress 없으면 상수 fallback 사용
  - done 시 완료 메시지를 출력 상단에 표시 (`.done-msg`)
- `AGENT_COLORS` 상수 추가: 에이전트별 레이블 색상 (moss green, terracotta, dusty blue 등)
- `prd_writer` done 버블: "PRD 작성이 완료되었습니다!" + "IdeaVault가 만들어준 나만의 PRD 보기!" 버튼
- critic done 메시지: `"..."` → `"추가 정보 확인을 완료했습니다!"`
- "IdeaVault가 만들어준 나만의 PRD 보기!" 중복 제거: Analyze.jsx의 `prdReady` 배너/상태 제거 (ChatBubble이 커버)

### 생성/수정된 파일
- `frontend/src/pages/Result.css`
- `frontend/src/pages/History.css`
- `frontend/src/pages/Analyze.jsx`
- `frontend/src/pages/Analyze.css`
- `frontend/src/components/ChatBubble.jsx`
- `frontend/src/components/ChatBubble.css`

### TODO
- (없음 — 이번 세션 모든 항목 완료)
