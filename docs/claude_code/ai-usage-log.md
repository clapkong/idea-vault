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

## 2026-04-27 — ralph-loop-4: 기능 버그 수정 및 디자인 개선

### 백엔드에서 수정해야 하는 부분 (미구현, TODO)

**[Token Analytics] 세션 내 복수 모델/에이전트별 통계**
- 현재 문제: `ANALYTICS_DATA`가 job 당 단일 모델·단일 토큰 행으로 하드코딩됨. 실제로는 한 세션에서 planner/analyst/critic 등 여러 에이전트가 각각 다른 토큰을 소비함
- 필요한 변경:
  1. 각 mock JSON의 events에 `model` 필드 추가 (현재 누락)
  2. `/analytics` 엔드포인트가 각 mock JSON의 events를 순회해 `agent × model × tokens` 단위로 집계
  3. 프론트엔드 Analytics 테이블 행 단위를 `세션` → `에이전트 호출`로 전환, 또는 세션 내 모델별 breakdown을 별도 컬럼으로 노출
  4. researcher agent는 토큰 0으로, `model` 필드도 따로 두거나 "n/a"로 처리

### 수정사항 체크리스트 및 구현 결과

- [x] **[Analyze] ctrl+s 등 키보드 단축키로 세션 종료 방지** — Analyze.jsx에 `keydown` 이벤트 리스너 추가, ctrl/meta + s/p/r/u/d/f/g/j/k/l 차단
- [x] **[Analyze][History] Researcher tokens=0 표시** — ChatBubble.jsx: `typeof tokens === 'number'` 조건으로 0도 표시되도록 수정
- [x] **[Analyze][History] 채팅 버블 텍스트 클리핑** — `overflow-wrap: break-word; word-break: break-word` 추가
- [x] **[Analyze] 채팅 버블 가로 길이 축소** — `max-width: 70%` → `88%`
- [x] **[Analyze] 채팅 버블 MD 렌더링** — ChatBubble에 ReactMarkdown + remark-gfm 적용 (에이전트 버블만)
- [x] **[PRD Viewer] react-markdown 테이블 지원** — remark-gfm 설치 및 Result.jsx에 적용
- [x] **[PRD Viewer] TOC 스크롤 고정** — `.result-toc`에 `position: sticky; top: 0; height: 100%; max-height: calc(100vh - 56px)` 추가
- [x] **[PRD Writer] 뒤로가기 버튼 너비** — `width: 80px` → `min-width: 100px; white-space: nowrap`
- [x] **[History] 즐겨찾기 필터 기능** — `favOnly` 상태 추가, 즐겨찾기만 보기 필터 버튼 구현
- [x] **[History] 하트 디자인** — ❤️/🤍 이모티콘 → SVG 하트 아이콘으로 교체
- [x] **[Home] 예시 Chip 가독성 개선** — 전체 텍스트 → 이모티콘 + 키워드 형태

### 생성/수정된 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/pages/Analyze.jsx` | 키보드 단축키 차단 useEffect 추가 |
| `frontend/src/pages/Home.jsx` | EXAMPLE_PROMPTS 구조 변경 (label+text), 칩 렌더링 수정 |
| `frontend/src/pages/History.jsx` | HeartIcon SVG 컴포넌트, favOnly 필터 상태 및 UI 추가 |
| `frontend/src/pages/History.css` | fav-btn SVG 스타일, fav-filter-btn, sidebar-controls 추가 |
| `frontend/src/pages/Result.jsx` | remark-gfm import 및 ReactMarkdown에 적용 |
| `frontend/src/pages/Result.css` | TOC sticky 고정, btn-back min-width/white-space 수정 |
| `frontend/src/components/ChatBubble.jsx` | ReactMarkdown+remarkGfm 적용, tokens=0 표시 수정 |
| `frontend/src/components/ChatBubble.css` | max-width 88%, overflow-wrap, bubble-markdown 스타일 추가 |
| `frontend/package.json` | remark-gfm 의존성 추가 |

### TODO (미구현)
- [ ] **[Token Analytics] 백엔드 구조 전면 개편** — 상기 백엔드 TODO 참조
- [ ] **[Token Analytics] mock JSON에 model 필드 추가** — 각 agent_done 이벤트에 model 필드 필요
