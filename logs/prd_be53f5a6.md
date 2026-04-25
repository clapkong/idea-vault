# AI 뉴스 큐레이터 (AI News Curator)

## 1. 한 줄 정의
RSS 피드를 자동 수집하고 AI로 요약·분류하여 개인 맞춤형 뉴스를 제공하는 웹 서비스

## 2. 문제 정의
매일 수십 개의 뉴스 사이트를 확인하는 것은 시간 낭비이며, 중요한 정보를 놓치기 쉽습니다. 기존 뉴스 앱은 광고와 클릭베이트로 가득하고, 관심사에 맞는 콘텐츠를 필터링하기 어렵습니다. 이 프로젝트는 여러 RSS 피드를 한 곳에서 모아 AI가 자동으로 요약하고 중요도를 판단해, 사용자가 5분 안에 하루 뉴스를 파악할 수 있게 합니다.

## 3. 타겟 사용자
- **정보 과부하를 겪는 직장인**: 업계 뉴스를 빠르게 파악하고 싶은 사람
- **뉴스 큐레이션에 관심 있는 개발자**: RSS와 AI를 활용한 자동화 시스템을 원하는 사람
- **포트폴리오 리뷰어**: Python, React, AI API 연동 역량을 확인하려는 채용 담당자

## 4. 핵심 기능
- **RSS 피드 자동 수집**: GitHub Actions로 매일 정해진 시간에 RSS 피드를 크롤링하여 JSON 파일로 저장
- **AI 요약 생성**: HuggingFace Inference API를 사용해 각 기사를 2-3문장으로 요약
- **카테고리별 분류**: 기술, 경제, 사회 등 사전 정의된 키워드 기반으로 기사를 자동 분류
- **개인화 필터**: 사용자가 선택한 관심 키워드에 따라 기사를 필터링하고 우선순위 표시
- **반응형 웹 UI**: React로 구현한 카드 형태의 뉴스 피드 (모바일/데스크탑 대응)

## 5. 기술 스택
- **백엔드**: Python 3.10+, FastAPI (API 서버), feedparser (RSS 파싱), requests (HTTP 호출)
- **프론트엔드**: React 18, Axios (API 통신), TailwindCSS (스타일링)
- **데이터베이스**: SQLite (로컬 개발), PostgreSQL (배포, Render 무료 tier)
- **AI**: HuggingFace Inference API (facebook/bart-large-cnn 영어 요약, eenzeenee/t5-base-korean-summarization 한국어 요약)
- **자동화**: GitHub Actions (RSS 수집 스케줄러, cron 일 1회 실행)
- **배포**: Vercel (React 프론트엔드), Render (FastAPI 백엔드)

## 6. 예상 일정
- **Week 1-2**: 환경 설정 + RSS 수집 파이프라인 구현 (feedparser, GitHub Actions cron job 설정)
- **Week 3-4**: FastAPI 백엔드 개발 (RSS 데이터 CRUD API, SQLite 스키마 설계)
- **Week 5**: HuggingFace API 연동 (요약 기능, 에러 핸들링, 무료 한도 관리)
- **Week 6**: React 프론트엔드 기본 UI (기사 목록, 필터, 검색 기능)
- **Week 7**: 개인화 기능 (키워드 저장, 우선순위 정렬) + 스타일링
- **Week 8**: 배포 및 최적화 (Vercel + Render 배포, 문서 작성, 포트폴리오 정리)

## 7. 주요 리스크
- **HuggingFace 무료 API 한도 초과**: 일 1,000회 제한 → 배치 처리로 하루 50개 기사만 처리, 캐싱으로 재요약 방지, 한도 초과 시 로컬 모델(transformers 라이브러리) 대체
- **GitHub Actions 실행 시간 제약**: 월 2,000분 제한 → 일 1회 10분 이내 실행으로 월 300분 사용 (여유 있음), 실패 시 Render Cron Jobs (유료 전환 시 대안)
- **React 초급 수준 학습 곡선**: 복잡한 상태 관리 어려움 → 기능 단순화 (Redux 제외, useState/useEffect만 사용), ChatGPT 활용 디버깅
- **Vercel Serverless 10초 실행 제한**: RSS+AI 파이프라인 타임아웃 → GitHub Actions에서 사전 처리 후 결과만 Vercel에서 제공 (정적 JSON 배포)
- **한국어 AI 요약 품질 저하**: 소형 모델 정확도 문제 → 영어 기사 우선 지원, 한국어는 원문 링크 제공으로 폴백

## 8. 참고 자료
- **HuggingFace Inference API**: https://huggingface.co/docs/api-inference/index - 무료 tier 사용법 및 한도 확인
- **feedparser 문서**: https://feedparser.readthedocs.io/ - RSS 파싱 라이브러리 사용법
- **GitHub Actions Cron**: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule - 스케줄 작업 설정 가이드
- **Vercel + FastAPI 배포**: https://vercel.com/docs/frameworks/more-frameworks - Serverless Python 함수 배포 방법
- **Render 무료 tier**: https://render.com/docs/free - PostgreSQL 및 웹 서비스 무료 호스팅 스펙
- **한국어 RSS 피드 목록**: https://www.kbs.co.kr/rss/ - KBS 뉴스 RSS (30개 이상 공개 피드 확인)
- **KoBART 요약 모델**: https://huggingface.co/gogamza/kobart-summarization - 한국어 요약 모델 대안