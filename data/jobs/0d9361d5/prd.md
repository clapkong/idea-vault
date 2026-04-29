# 대용량 트래픽 대비 쿠폰 발급 시스템

## 1. 한 줄 정의
동시 접속 상황에서 선착순 쿠폰을 정확하게 발급하고, Redis 기반 동시성 제어와 비동기 처리로 대용량 트래픽을 안정적으로 처리하는 백엔드 시스템

## 2. 문제 정의
이커머스 이벤트에서 수만 명이 동시에 쿠폰을 요청할 때, 데이터베이스 락만으로는 성능 병목과 중복 발급 문제가 발생합니다. 이 프로젝트는 Redis 분산락과 원자적 연산(INCR)을 활용해 **동시성 제어**, **성능 최적화**, **시스템 안정성**을 보장하는 현업 수준의 쿠폰 시스템을 구현합니다. 백엔드 개발자 면접에서 자주 등장하는 "대용량 트래픽 처리" 역량을 직접 증명할 수 있습니다.

## 3. 타겟 사용자
- **1차 사용자**: 쿠폰 이벤트에 참여하는 일반 고객 (선착순 발급 요청)
- **2차 사용자**: 쿠폰 이벤트를 관리하는 운영 담당자 (발급 현황 조회, 이벤트 설정)
- **기술 검증 대상**: 백엔드 개발 직무 면접관 (동시성 제어, Redis 활용, 부하 테스트 이해도 평가)

## 4. 핵심 기능
1. **쿠폰 이벤트 생성**: 발급 수량, 기간, 조건을 설정한 이벤트 등록 API
2. **선착순 쿠폰 발급**: Redis INCR로 재고 차감 + Redisson 분산락으로 중복 방지 + DB 비동기 저장
3. **쿠폰 발급 내역 조회**: 사용자별 발급 이력 조회 (Redis 캐싱으로 조회 성능 최적화)
4. **실시간 발급 현황 모니터링**: Redis 기반 남은 수량 실시간 조회 + 이벤트 종료 자동 처리
5. **부하 테스트 환경**: JMeter 시나리오 스크립트 + 동시 1만 요청 시뮬레이션 결과 문서화

## 5. 기술 스택
- **Language**: Java 17
- **Framework**: Spring Boot 3.2, Spring Data JPA, Spring Data Redis
- **Database**: MySQL 8.0 (쿠폰 영구 저장), Redis 7.x (재고 관리 + 분산락)
- **Concurrency**: Redisson 3.25.0 (분산락 구현), Redis INCR (원자적 재고 차감)
- **Testing**: JUnit 5, JMeter (부하 테스트), Testcontainers (통합 테스트)
- **Infra**: Docker Compose (로컬 환경), GitHub Actions (CI/CD)
- **Monitoring**: Spring Actuator + Prometheus (선택 사항)

## 6. 예상 일정
- **Week 1 (기본 구조)**: 
  - Day 1-2: 프로젝트 세팅, ERD 설계, Redis/MySQL 환경 구성
  - Day 3-5: 쿠폰 이벤트 생성 API + 기본 발급 로직 (DB 락 버전)
  - Day 6-7: Redis 연동 + INCR 기반 재고 관리 구현
  
- **Week 2 (핵심 기능)**: 
  - Day 8-10: Redisson 분산락 적용 + 중복 발급 방지 로직
  - Day 11-12: 비동기 DB 저장 (CompletableFuture 또는 @Async)
  - Day 13-14: 발급 내역 조회 API + Redis 캐싱 최적화
  
- **Week 3 (테스트 & 문서화)**: 
  - Day 15-17: JMeter 시나리오 작성 + 부하 테스트 (1만 동시 요청)
  - Day 18-19: 성능 개선 (커넥션 풀 튜닝, 쿼리 최적화)
  - Day 20-21: README 작성 (아키텍처 다이어그램, 성능 비교 표, 면접 예상 질문 정리)

## 7. 주요 리스크
- **리스크 1: Redisson 학습 곡선**  
  *대응*: Lettuce 대신 Redisson 선택 근거는 분산락 구현의 단순함. 공식 문서 예제 (tryLock) 기반으로 2일 내 구현 가능
  
- **리스크 2: 비동기 처리 중 예외 발생 시 데이터 정합성**  
  *대응*: Redis 재고 차감 성공 시 쿠폰 ID를 임시 키로 저장, DB 저장 실패 시 보상 트랜잭션으로 Redis 재고 복구
  
- **리스크 3: 3주 내 메시지 큐(Kafka) 도입 어려움**  
  *대응*: 1차는 Redis + @Async로 구현, README에 "Kafka 도입 시 개선 방안" 섹션 추가해 확장 가능성 어필
  
- **리스크 4: 부하 테스트 환경 구성 시간 소요**  
  *대응*: JMeter GUI로 1시간 내 기본 시나리오 작성 가능. Docker Compose로 Redis/MySQL 격리 환경 즉시 구성

## 8. 참고 자료
1. **[Redisson Distributed Lock 가이드](https://redisson.org/)**: Redisson 공식 문서, tryLock 메서드 사용법 및 분산 환경 설정 예제
2. **[Redis INCR 성능 분석 (Stack Overflow)](https://stackoverflow.com/)**: Redis INCR 명령어의 원자적 특성과 동시성 환경에서 우수성 설명
3. **[Baeldung - Spring Data Redis](https://www.baeldung.com/spring-data-redis-tutorial)**: Spring Boot에서 Redis 연동 및 RedisTemplate 사용 예제
4. **[JMeter 부하 테스트 튜토리얼](https://jmeter.apache.org/)**: HTTP 요청 시뮬레이션, Thread Group 설정, 결과 분석 방법
5. **[백엔드 면접 동시성 문제 트렌드](https://github.com/)**: 쿠폰 시스템, 재고 관리 등 실무 케이스 기반 면접 질문 모음
6. **[Redisson vs Lettuce 비교](https://docs.spring.io/spring-data/redis/reference/)**: Spring Data Redis 공식 문서, 두 클라이언트의 특징과 선택 기준
7. **[MySQL 커넥션 풀 튜닝](https://dev.mysql.com/)**: HikariCP 설정 최적화 및 병목 해결 사례