# 나만의 일상 기록 챗봇

## 1. 한 줄 정의
매일 하루를 되돌아보며 터미널에서 대화하듯 기록하고, 나중에 날짜/키워드로 검색할 수 있는 파이썬 일기장

## 2. 문제 정의
일기를 쓰고 싶지만 노트는 귀찮고, 앱은 복잡하고, 블로그는 부담스럽다. 터미널에서 간단히 "오늘 뭐 했어?" 같은 질문에 답하듯 기록하고, 나중에 "지난주 금요일에 뭐 했더라?" 검색할 수 있으면 실제로 매일 쓰게 된다. 개발 초보가 파일 저장, 입력 처리, 검색 같은 실용 기능을 직접 만들어보며 "내가 쓸 수 있는 것"을 경험할 수 있다.

## 3. 타겟 사용자
- 개발 시작 한 달차, 파이썬 기초 학습 완료한 본인
- 일기/메모 습관을 만들고 싶지만 기존 도구가 맞지 않는 사람
- 터미널 사용에 익숙해지고 싶은 입문자

## 4. 핵심 기능

**1. 대화형 기록 작성**
`python diary.py write` 실행 시 "오늘 어땠어?", "뭐 했어?" 같은 질문에 답하는 형식으로 텍스트 입력 → JSON 파일로 자동 저장

**2. 날짜별 조회**
`python diary.py read 2024-01-15` 입력 시 해당 날짜 기록 출력

**3. 키워드 검색**
`python diary.py search 음악` 입력 시 "음악" 포함된 모든 기록 날짜와 내용 출력

**4. 최근 기록 보기**
`python diary.py recent 7` 입력 시 최근 7일 기록 요약 출력

## 5. 기술 스택

- **언어**: Python 3.8+
- **데이터 저장**: JSON (파일 기반, 별도 DB 불필요)
- **CLI 구현**: argparse (Python 표준 라이브러리)
- **날짜 처리**: datetime (Python 표준 라이브러리)
- **텍스트 입력**: input() 내장 함수
- **파일 관리**: os, pathlib (Python 표준 라이브러리)

*모든 기술이 Python 기본 설치에 포함되어 추가 설치 불필요*

## 6. 예상 일정

**1주차**
- 1-2일: 기본 파일 저장/읽기 구현 (write, read 기능)
- 3-4일: 날짜 자동 생성, JSON 구조 설계
- 5-7일: 키워드 검색 기능 구현

**2주차**
- 8-10일: recent 기능, 에러 처리 (파일 없을 때 등)
- 11-12일: 사용자 인터페이스 개선 (질문 문구, 출력 포맷)
- 13-14일: 실제 사용하며 버그 수정, README 작성

## 7. 주요 리스크

**리스크 1: JSON 파일 깨짐**
- 원인: 작성 중 프로그램 강제 종료
- 대응: 임시 파일에 먼저 쓰고 완료 후 원본 파일에 복사하는 방식

**리스크 2: 한글 인코딩 문제**
- 원인: Windows 환경에서 기본 인코딩 차이
- 대응: 파일 열 때 `encoding='utf-8'` 명시

**리스크 3: 검색 속도 느림 (기록 많아질 경우)**
- 원인: JSON 전체를 매번 읽어서 검색
- 대응: 초기엔 무시, 나중에 필요시 인덱스 파일 추가 (2주 내 불필요)

**리스크 4: 명령어 사용법 헷갈림**
- 원인: CLI 처음 사용
- 대응: `python diary.py --help` 기능 구현, 예시 포함된 README 작성

## 8. 참고 자료

**Python 파일 입출력**
https://docs.python.org/ko/3/tutorial/inputoutput.html#reading-and-writing-files
(파일 저장/읽기 기본 문법)

**JSON 처리**
https://docs.python.org/ko/3/library/json.html
(데이터를 JSON 형식으로 저장하고 불러오는 방법)

**argparse 튜토리얼**
https://docs.python.org/ko/3/howto/argparse.html
(명령줄 인자 처리, write/read/search 명령 구현)

**datetime 사용법**
https://docs.python.org/ko/3/library/datetime.html
(날짜 자동 생성 및 비교)

**초보자를 위한 CLI 앱 만들기**
https://realpython.com/command-line-interfaces-python-argparse/
(실제 구현 예제 포함)