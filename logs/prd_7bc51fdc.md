# BookMind - AI 기반 개인 독서 기록 및 추천 웹 서비스

## 1. 한 줄 정의
독서 기록과 메모를 관리하고, AI가 사용자의 독서 취향을 분석하여 다음 책을 추천해주는 웹 서비스

## 2. 문제 정의
독서를 즐기는 사람들은 읽은 책을 기록하고 싶어하지만, 기존 서비스들은 단순 기록에 그치거나 개인화되지 않은 일반적인 추천만 제공합니다. 또한 자신의 독서 패턴이나 취향 변화를 시각적으로 확인하기 어렵습니다. BookMind는 개인의 독서 이력과 메모를 분석하여 맞춤형 추천을 제공하고, 독서 습관을 인사이트로 제공함으로써 더 나은 독서 경험을 만듭니다.

## 3. 타겟 사용자
- 독서를 취미로 즐기며 읽은 책을 체계적으로 기록하고 싶은 사람
- 다음에 읽을 책을 고민하는 독서가
- 자신의 독서 취향과 패턴을 분석하고 싶은 사람
- 독서 모임이나 스터디에서 책 추천을 주고받는 사람

## 4. 핵심 기능
- **독서 기록 관리**: 읽은 책, 읽고 있는 책, 읽고 싶은 책을 분류하고 개인 메모 및 별점 기록
- **AI 기반 맞춤 추천**: 사용자의 독서 이력과 메모를 분석하여 취향에 맞는 책 추천 (Sentence Transformers 활용)
- **도서 검색 및 정보 조회**: 네이버/알라딘 책 API를 통한 도서 검색 및 상세 정보 제공
- **독서 통계 대시보드**: 월별 독서량, 선호 장르, 독서 트렌드 시각화
- **독서 메모 아카이브**: 책별 인상 깊은 문구, 생각, 리뷰를 타임라인으로 관리

## 5. 기술 스택
**프론트엔드**
- React 18 + Vite
- Material-UI (MUI)
- Recharts (데이터 시각화)

**백엔드**
- Python FastAPI
- SQLAlchemy (ORM)
- PostgreSQL

**AI/ML**
- Hugging Face Transformers (Sentence-BERT)
- model2vec (경량화 대안)

**외부 API**
- 네이버 책 검색 API (무료, 25,000회/일)
- 알라딘 도서 API (보조)

**배포**
- Frontend: Vercel
- Backend: Railway / Render
- ML Model: Hugging Face Spaces

## 6. 예상 일정
**Week 1-2: 환경 설정 및 백엔드 기초**
- 프로젝트 초기 설정, DB 스키마 설계
- FastAPI 기본 CRUD API 구현 (도서, 기록, 메모)

**Week 3-5: React 프론트엔드 개발**
- Week 3: React 기초 학습 + MyReads boilerplate 분석
- Week 4: Material-UI 컴포넌트 구성 (도서 목록, 카드, 폼)
- Week 5: API 연동 및 상태 관리

**Week 6: 외부 API 연동**
- 네이버/알라딘 API 통합
- 도서 검색 기능 구현

**Week 7: AI 추천 시스템 MVP**
- model2vec를 활용한 텍스트 임베딩
- 유사도 기반 추천 로직 구현

**Week 8: 통계 및 시각화**
- 독서 통계 대시보드
- Recharts를 활용한 그래프 구현

**Week 9-10: 배포 및 최적화**
- Vercel, Railway 배포
- 성능 테스트 및 버그 수정
- 포트폴리오 문서화

## 7. 주요 리스크
**리스크 1: React 학습 곡선**
- 대응: MyReads boilerplate 활용, Material-UI로 컴포넌트 재사용성 극대화, 3주 집중 학습 기간 확보

**리스크 2: AI 추천 품질**
- 대응: model2vec로 MVP 시작, 데이터 쌓이면 Sentence-BERT로 업그레이드, 협업 필터링 보조 추가

**리스크 3: 무료 API 요청 제한**
- 대응: 검색 결과 캐싱, 네이버 API 25,000회/일 제한 모니터링, 알라딘 API 백업

**리스크 4: 배포 비용 및 성능**
- 대응: Railway 무료 플랜 활용, Hugging Face Spaces로 ML 모델 분리 배포, 초기 사용자 수 제한

**리스크 5: 일정 지연**
- 대응: Week 5까지 React 기본 기능 완성을 마일스톤으로 설정, AI 추천은 선택적 기능으로 우선순위 조정 가능

## 8. 참고 자료
- [네이버 책 검색 API 문서](https://developers.naver.com/docs/serviceapi/search/book/book.md) - 무료 도서 검색 API (25,000회/일)
- [Railway 배포 가이드](https://docs.railway.app/) - 무료 백엔드 배포 플랫폼
- [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces) - 무료 ML 모델 호스팅
- [Sentence Transformers 문서](https://www.sbert.net/) - 텍스트 임베딩 라이브러리
- [MyReads GitHub](https://github.com/udacity/reactnd-project-myreads-starter) - React 독서 앱 boilerplate
- [Material-UI 컴포넌트](https://mui.com/material-ui/getting-started/) - React UI 프레임워크
- [model2vec](https://github.com/MinishLab/model2vec) - 경량화 임베딩 모델 (CPU 최적화)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/) - Python 웹 프레임워크
- [Recharts](https://recharts.org/) - React 차트 라이브러리