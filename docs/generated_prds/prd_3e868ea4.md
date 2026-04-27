# Spotify 플레이리스트 분석기

## 1. 한 줄 정의
Exportify로 내보낸 Spotify 플레이리스트 CSV 파일을 분석하여 나의 음악 취향을 시각화하는 Python 터미널 프로그램

## 2. 문제 정의
Spotify를 사용하면서 내가 어떤 음악을 주로 듣는지, 어떤 아티스트를 좋아하는지 한눈에 파악하기 어렵다. Spotify의 자체 통계 기능은 제한적이고, 개발 초보자가 API를 직접 다루기엔 OAuth 인증 등의 진입장벽이 높다. 이 프로젝트는 무료 도구(Exportify)로 내보낸 CSV 파일만으로 나만의 음악 통계를 쉽게 확인할 수 있게 한다.

## 3. 타겟 사용자
- 개발 입문 1개월차로 Python 기초 문법만 아는 본인
- Spotify를 사용하며 자신의 음악 취향을 데이터로 확인하고 싶은 사람
- 유료 API 없이 로컬에서 간단한 데이터 분석을 경험하고 싶은 초보 개발자

## 4. 핵심 기능
- **CSV 파일 읽기**: Exportify로 내보낸 플레이리스트 CSV 파일을 Python으로 파싱
- **Top 아티스트 분석**: 가장 많이 등장하는 아티스트 상위 10개를 터미널에 막대그래프로 출력
- **연도별 곡 분포**: 발매 연도별로 내 플레이리스트 곡 개수를 분석하여 막대그래프로 시각화
- **기본 통계 출력**: 전체 곡 수, 고유 아티스트 수, 평균 곡 길이 등을 터미널에 표 형식으로 출력
- **결과 저장**: 분석 결과를 PNG 이미지 파일로 저장하여 나중에 확인 가능

## 5. 기술 스택
- **언어**: Python 3.8+
- **라이브러리**:
  - `csv` (내장): CSV 파일 파싱
  - `matplotlib`: 그래프 시각화 및 이미지 저장
  - `collections.Counter` (내장): 빈도 계산
- **데이터 소스**: Exportify (https://exportify.net) - Spotify 플레이리스트를 CSV로 내보내는 무료 웹 도구
- **개발 환경**: VSCode + 터미널

## 6. 예상 일정
- **1주차**:
  - 1-2일: Exportify로 CSV 내보내기, CSV 구조 파악, Python으로 CSV 읽기 구현
  - 3-4일: matplotlib 기초 학습 (공식 튜토리얼), 간단한 막대그래프 그리기 실습
  - 5-7일: Top 아티스트 분석 기능 구현 (Counter 사용, 막대그래프 생성)
- **2주차**:
  - 1-3일: 연도별 분포 분석 기능 구현, 기본 통계 계산 및 출력
  - 4-5일: 그래프 PNG 저장 기능 추가, 파일 없음/형식 오류 예외 처리
  - 6-7일: 전체 테스트, 코드 정리, README 작성

## 7. 주요 리스크
- **matplotlib 학습 곡선**: 2주 내 그래프 라이브러리 학습이 버거울 수 있음
  - *대응*: 공식 튜토리얼의 막대그래프 예제 1-2개만 집중 학습, 복잡한 커스터마이징 배제
- **CSV 파일 형식 불일치**: Exportify CSV 구조가 예상과 다를 수 있음
  - *대응*: 첫 3일 내 실제 CSV 다운로드 후 구조 확인, 컬럼명 하드코딩 대신 인덱스 사용
- **장르 정보 부재**: Exportify CSV에 장르 정보가 포함되지 않음
  - *대응*: 장르 분석 대신 아티스트/연도 기반 분석에 집중, 추후 확장 가능성으로 남김
- **예외 처리 미흡**: 파일 없음, 빈 CSV 등의 예외 상황 처리 시간 부족
  - *대응*: 최소한의 try-except로 에러 메시지만 출력, 완벽한 처리는 추후 개선 과제로

## 8. 참고 자료
- https://exportify.net - Spotify 플레이리스트를 CSV로 내보내는 무료 도구
- https://matplotlib.org/stable/tutorials/introductory/pyplot.html - matplotlib 막대그래프 기초 튜토리얼
- https://docs.python.org/3/library/csv.html - Python 내장 csv 모듈 공식 문서
- https://realpython.com/python-csv/ - CSV 파일 읽기/쓰기 초보자 가이드
- https://www.youtube.com/results?search_query=python+csv+matplotlib+tutorial - Python CSV + matplotlib 튜토리얼 영상 모음