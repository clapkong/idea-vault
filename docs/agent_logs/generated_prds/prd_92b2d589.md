# 내 음악 취향 분석기

## 1. 한 줄 정의
YouTube Music 재생 목록을 불러와 장르·아티스트 분포를 그래프로 시각화하는 CLI 도구

## 2. 문제 정의
음악을 좋아하지만 내가 주로 듣는 장르나 아티스트가 무엇인지 한눈에 파악하기 어렵다. Spotify는 연말 Wrapped를 제공하지만 YouTube Music 사용자는 이런 통계를 볼 방법이 없고, 유료 서비스는 부담스럽다. 직접 만든 도구로 내 취향을 분석하면 개발 실력도 키우고 음악 감상도 더 재미있어진다.

## 3. 타겟 사용자
- YouTube Music을 주로 사용하는 개발 입문자
- 파이썬 기초(변수, 반복문, 함수)를 배웠고 실전 프로젝트를 원하는 사람
- 자신의 음악 취향을 데이터로 확인하고 싶은 사람

## 4. 핵심 기능
1. **YouTube Music 인증**: 브라우저 헤더 복사로 ytmusicapi 인증 설정
2. **재생목록 불러오기**: 좋아요/재생목록에서 곡 제목·아티스트 추출
3. **장르 분류**: 아티스트명 기준 수동 태깅으로 장르 집계
4. **시각화**: matplotlib로 장르 분포 파이 차트, 상위 아티스트 막대 그래프 생성

## 5. 기술 스택
- **언어**: Python 3.8+
- **라이브러리**: ytmusicapi (인증·API), pandas (데이터 집계), matplotlib (그래프)
- **환경**: 로컬 CLI, requirements.txt
- **참고 코드**: conorbranagan/personalized-youtube 등 GitHub 오픈소스

## 6. 예상 일정
- **1주차**
  - 1-2일: ytmusicapi 설치, 헤더 복사 인증, 재생목록 불러오기 예제 실행
  - 2-3일: pandas 튜토리얼 학습, CSV 저장·집계 연습
  - 1-2일: matplotlib 막대·파이 차트 튜토리얼 실습
- **2주차**
  - 2일: 장르 태깅 로직 구현 (딕셔너리 매핑), 집계 함수 작성
  - 2일: 그래프 생성 코드 작성, 색상·레이블 조정
  - 2-3일: 버그 수정, 예외 처리(빈 재생목록, 미분류 아티스트), README 작성

## 7. 주요 리스크
| 리스크 | 대응 방안 |
|--------|-----------|
| **ytmusicapi 인증 실패** | 공식 문서 헤더 복사 단계 반복, GitHub 이슈 검색, 안 되면 CSV 샘플 데이터로 먼저 집계·그래프 로직 구현 |
| **학습 시간 부족** | pandas/matplotlib 전체 학습 대신 필요 기능(read_csv, groupby, bar/pie)만 튜토리얼 실습 |
| **장르 분류 복잡도** | 자동 분류 제외, 본인이 아는 아티스트 10-20개만 수동 태깅, 나머지는 '기타'로 묶음 |
| **2주 초과 가능성** | 1주차 말에 재생목록 불러오기까지 완료 목표, 안 되면 장르 분류 생략하고 아티스트 빈도 그래프만 구현 |

## 8. 참고 자료
- **ytmusicapi 공식 문서**: https://ytmusicapi.readthedocs.io/en/stable/setup.html - 헤더 복사 인증 방법
- **Spotipy OAuth 가이드**: https://spotipy.readthedocs.io/en/2.22.1/#authorization-code-flow - OAuth 복잡도 비교 참고
- **pandas 10분 튜토리얼**: https://pandas.pydata.org/docs/user_guide/10min.html - 집계 기초
- **matplotlib 파이 차트 예제**: https://matplotlib.org/stable/gallery/pie_and_polar_charts/pie_features.html - 그래프 생성
- **conorbranagan/personalized-youtube**: https://github.com/conorbranagan/personalized-youtube - 오픈소스 참고 (~150줄, requests/pandas 의존)
- **Stack Overflow ytmusicapi 질문**: https://stackoverflow.com/questions/tagged/ytmusicapi - 인증 오류 해결