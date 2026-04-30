# 실시간 티켓 예매 시스템 (Concert Ticket Booking System)

## 1. 한 줄 정의
대규모 동시 접속 환경에서 Redis 기반 선착순 티켓 예매와 재고 관리를 구현한 Java/Spring 백엔드 시스템

## 2. 문제 정의
인기 공연 티켓 오픈 시 수만 명이 동시 접속하면서 발생하는 **오버부킹**, **데이터 불일치**, **서버 과부하** 문제를 해결합니다. 실무에서 반드시 마주치는 동시성 제어, 캐싱 전략, 성능 최적화 역량을 종합적으로 보여줄 수 있는 주제입니다. 취업 시장에서 백엔드 개발자에게 요구되는 **대용량 트래픽 처리 경험**을 포트폴리오로 증명할 수 있습니다.

## 3. 타겟 사용자
- **1차 사용자**: 티켓을 구매하려는 일반 사용자 (동시 접속 1,000~10,000명 가정)
- **2차 사용자**: 공연 정보를 등록/관리하는 어드민
- **평가자**: 백엔드 개발자 채용 담당자 (동시성 처리, Redis 활용, 테스트 코드 작성 능력 평가)

## 4. 핵심 기능
1. **실시간 좌석 조회**: Redis 캐싱으로 DB 부하 최소화 + 좌석 잔여 정보 실시간 반영
2. **동시성 제어 예매**: Redis 분산 락(Redisson)으로 오버부킹 방지 + 낙관적 락 병행
3. **대기열 시스템**: 티켓 오픈 시 Redis Sorted Set 기반 순번 부여 (FIFO 보장)
4. **부하 테스트 자동화**: JMeter 시나리오 작성 + TPS/응답시간 측정 결과 문서화
5. **예매 취소/환불**: 트랜잭션 롤백 + 좌석 재고 복구 로직

## 5. 기술 스택
- **Backend**: Java 17, Spring Boot 3.x, Spring Data JPA
- **Database**: MySQL 8.0 (메인), H2 (테스트)
- **Cache**: Redis 7.x (Redisson 분산 락, Sorted Set 대기열)
- **Test**: JUnit 5, Mockito, JMeter (부하 테스트)
- **Infra**: Docker, Docker Compose (로컬 환경 구성)
- **문서화**: Swagger/Spring REST Docs, GitHub README

## 6. 예상 일정
- **1주차**: 프로젝트 세팅 + Redis 학습
  - Docker 환경 구성 (MySQL, Redis)
  - 공연/좌석 도메인 모델링 + CRUD API
  - Redis 기본 연동 (Lettuce) + 캐싱 적용
- **2주차**: 핵심 로직 구현
  - Redisson 분산 락 학습 및 예매 API 구현
  - 대기열 시스템 (Sorted Set) 구현
  - 동시성 테스트 케이스 작성 (JUnit)
- **3주차**: 성능 검증 + 문서화
  - JMeter 부하 테스트 시나리오 작성 (1-3일)
  - 성능 개선 (쿼리 튜닝, 인덱스 추가)
  - README 작성 (아키텍처 다이어그램, 테스트 결과, 트러블슈팅)

## 7. 주요 리스크
| 리스크 | 대응 방안 |
|--------|-----------|
| **Redis 학습 곡선** (1주 소요) | 공식 문서 + Redisson GitHub 예제 중심 학습. 복잡한 Lua 스크립트는 제외하고 제공되는 API 활용 |
| **분산 락 디버깅 어려움** | 로컬 단일 Redis로 시작. 락 타임아웃 설정을 짧게(3초) 하여 데드락 방지 |
| **JMeter 미경험** | 기본 HTTP 요청 시나리오만 작성 (Thread Group 100~1000). 결과는 Summary Report로 단순화 |
| **3주 내 미완성 가능성** | MVP 기준: 예매 API + Redis 캐싱 + 간단한 부하 테스트. 대기열은 선택 사항으로 조정 |
| **DB 병목 현상** | 조회 API는 Redis 캐싱 100% 적용. 쓰기 작업은 비동기 처리 고려 (시간 여유 시) |

## 8. 참고 자료
- [Redisson 공식 문서 - 분산 락 가이드](https://github.com/redisson/redisson/wiki/8.-Distributed-locks-and-synchronizers): Lock/Semaphore 사용법, 타임아웃 설정 예제
- [우아한테크 - 선착순 쿠폰 시스템](https://techblog.woowahan.com/2631/): Redis 재고 관리 실전 적용 사례
- [NHN Cloud - 대규모 트래픽 처리](https://meetup.nhncloud.com/posts/344): 캐싱 전략과 DB 부하 분산 기법
- [JMeter 튜토리얼](https://jmeter.apache.org/usermanual/get-started.html): Thread Group 설정, Summary Report 해석법
- [Spring Data Redis 공식 가이드](https://docs.spring.io/spring-data/redis/reference/): Lettuce 설정, 캐시 추상화 적용 방법