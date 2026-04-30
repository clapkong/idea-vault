# 캠퍼스북스 (CampusBooks) - 대학생 중고 교재 거래 매칭 플랫폼

## 1. 한 줄 정의
같은 대학 학생들끼리 학기별 필요한 전공 교재를 사고팔 수 있도록 자동 매칭해주는 웹/모바일 플랫폼

## 2. 문제 정의
대학생들은 매 학기 고가의 전공 교재를 구매해야 하지만, 한 학기만 사용하고 방치되는 경우가 많습니다. 기존 중고거래 플랫폼(당근마켓, 중고나라)은 교재 검색이 어렵고, 학교/학과/과목별 필터링이 없어 원하는 책을 찾기 힘듭니다. 또한 판매자-구매자 간 직접 연락과 가격 협상이 번거롭습니다. 이 프로젝트는 학교 인증을 통해 신뢰도를 높이고, 수강 과목 기반 자동 매칭으로 거래 효율성을 극대화하여 학생들의 교재비 부담을 줄입니다.

## 3. 타겟 사용자
- **1차 타겟**: 프로젝트 팀이 속한 대학교의 재학생 (초기 MVP 검증용)
- **2차 타겟**: 수도권 4년제 대학 재학생 (확장 시나리오)
- **사용자 페르소나**:
  - 교재비 절약이 필요한 학생 (구매자)
  - 사용 안 하는 전공책을 처분하고 싶은 학생 (판매자)
  - 매 학기 여러 과목 교재를 준비해야 하는 전공 학생

## 4. 핵심 기능
1. **학교 인증 시스템**: 학교 이메일 인증으로 같은 대학 학생만 접근 가능
2. **수강 과목 기반 자동 매칭**: 사용자가 등록한 이번 학기 수강 과목에 필요한 교재를 자동으로 추천
3. **교재 등록/검색**: ISBN 바코드 스캔 또는 수동 입력으로 교재 정보 자동 완성 (교보문고 API 활용)
4. **가격 제안 시스템**: 판매자가 희망 가격 설정, 구매자가 제안 가격 입력 시 자동 알림
5. **거래 상태 관리**: 예약중/거래완료 상태 표시 및 거래 후기 기능

## 5. 기술 스택
**프론트엔드 (웹)**
- React.js + TypeScript
- TailwindCSS (디자인 시스템 최소화)
- React Query (서버 상태 관리)

**프론트엔드 (iOS)**
- Swift + SwiftUI
- Alamofire (네트워킹)

**백엔드**
- Node.js + Express.js
- PostgreSQL (교재/사용자/거래 데이터 관리)
- Prisma ORM

**인프라 및 도구**
- AWS EC2 (서버 호스팅)
- AWS RDS (데이터베이스)
- Docker (배포 환경 통일)
- GitHub Actions (CI/CD)

**외부 API**
- 교보문고 도서 검색 API (ISBN 기반 교재 정보)
- 학교 이메일 인증 (nodemailer)

## 6. 예상 일정
**Week 1-2: 기획 및 설계**
- 요구사항 정의서 작성
- DB 스키마 설계
- UI/UX 와이어프레임 (저해상도)
- API 명세서 작성

**Week 3-5: 기본 인프라 구축**
- 개발 환경 셋업 (Docker, GitHub)
- 백엔드 기본 CRUD API 구현
- 웹/iOS 프로젝트 초기화 및 라우팅 구조

**Week 6-9: 핵심 기능 개발**
- 학교 인증 시스템 (주 6-7)
- 교재 등록/검색 (주 7-8)
- 수강 과목 매칭 로직 (주 8-9)

**Week 10-12: 거래 기능 개발**
- 가격 제안 시스템
- 거래 상태 관리
- 알림 기능

**Week 13-14: 테스트 및 배포**
- 통합 테스트
- 실제 사용자 베타 테스트 (학과 친구들)
- 버그 수정 및 성능 최적화

**Week 15-16: 최종 발표 준비**
- 시연 영상 제작
- 발표 자료 작성
- 최종 보고서 작성

## 7. 주요 리스크
**리스크 1: 교재 데이터 부족**
- 초기에는 사용자가 직접 ISBN 입력 또는 교재명 수동 등록
- 대응: 교보문고 API로 자동 완성 기능 제공, 초기 시드 데이터는 팀원들이 자주 사용하는 전공 교재 50개 수동 등록

**리스크 2: 초기 사용자 확보 어려움**
- 거래 플랫폼은 양방향 시장이라 초기 활성화가 중요
- 대응: 같은 학과 학생들 대상 오프라인 홍보, 학과 단톡방 공유, 교수님께 수업 시간 홍보 요청

**리스크 3: iOS/웹 동시 개발 부담**
- 두 플랫폼 동시 개발 시 일정 지연 가능
- 대응: 1단계에서는 웹 우선 개발 후 안정화, 2단계에서 iOS는 핵심 기능만 구현 (교재 검색/등록만)

**리스크 4: 학교 이메일 인증 실패율**
- 학교 메일 서버 제한으로 인증 메일이 안 갈 수 있음
- 대응: SMS 인증 추가 또는 학생증 사진 업로드 수동 인증 병행

**리스크 5: DB 설계 변경으로 인한 마이그레이션**
- 개발 중 스키마 변경 필요 시 데이터 손실 위험
- 대응: Prisma Migrate 활용한 버전 관리, 초기에는 테스트 데이터만 사용

## 8. 참고 자료
- **중고 교재 거래 시장 분석**: [https://www.kyobo.com/used/index.laf](https://www.kyobo.com/used/index.laf) - 교보문고 중고서점 시스템 참고
- **대학생 교재비 실태**: [https://www.hankyung.com/society/article/202203141234i](https://www.hankyung.com/society/article/202203141234i) - 대학생 교재비 부담 통계 자료
- **교보문고 도서 검색 API**: [https://developers.bookk.co.kr/](https://developers.bookk.co.kr/) - ISBN 기반 교재 정보 조회
- **React + Express 풀스택 아키텍처**: [https://www.digitalocean.com/community/tutorials/react-express-full-stack](https://www.digitalocean.com/community/tutorials/react-express-full-stack) - 기술 스택 참고
- **SwiftUI + REST API 연동**: [https://www.hackingwithswift.com/books/ios-swiftui/sending-and-receiving-codable-data-with-urlsession-and-swiftui](https://www.hackingwithswift.com/books/ios-swiftui/sending-and-receiving-codable-data-with-urlsession-and-swiftui) - iOS 네트워킹 가이드
- **Prisma ORM 가이드**: [https://www.prisma.io/docs/getting-started](https://www.prisma.io/docs/getting-started) - PostgreSQL 연동 및 마이그레이션
- **당근마켓 사례 분석**: [https://www.daangn.com/](https://www.daangn.com/) - 지역 기반 중고거래 UX 참고