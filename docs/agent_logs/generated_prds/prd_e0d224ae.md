# Spotify 음악 추천 도구

## 1. 한 줄 정의
내가 좋아하는 곡을 입력하면 Spotify API가 비슷한 곡을 추천해주는 파이썬 CLI 프로그램

## 2. 문제 정의
음악을 좋아하지만 매번 비슷한 곡만 듣게 되고, 새로운 음악을 발견하는 데 시간이 오래 걸림. 
기존 스트리밍 앱의 추천 알고리즘은 내 취향을 정확히 반영하지 못할 때가 많고, 특정 곡 기준으로 유사곡을 찾기 어려움.
직접 만든 도구로 원하는 기준곡을 입력해 즉시 추천받을 수 있다면 음악 발견 경험을 개선하고, 동시에 API 사용법과 파이썬 실전 능력을 키울 수 있음.

## 3. 타겟 사용자
- 파이썬 기초를 막 배운 초보 개발자 (본인)
- 음악을 좋아하고 새로운 곡 발견에 관심 있는 사람
- 간단한 명령어 도구를 터미널에서 사용할 수 있는 사용자

## 4. 핵심 기능
1. **Spotify 인증** - OAuth 2.0으로 Spotify API 접근 권한 획득
2. **곡 검색** - 아티스트명 + 곡명으로 Spotify에서 곡 ID 찾기
3. **유사곡 추천** - Spotify Recommendations API로 입력곡 기반 추천 목록 받기
4. **결과 출력** - 추천된 곡 제목, 아티스트, 미리듣기 링크를 터미널에 표시

## 5. 기술 스택
- **언어**: Python 3.8 이상
- **라이브러리**: 
  - `spotipy` (Spotify API 파이썬 래퍼)
  - `python-dotenv` (API 키 환경변수 관리)
- **API**: Spotify Web API (무료, 하루 최대 요청 수 제한 있지만 개인 사용 충분)
- **실행 환경**: 터미널 (CLI)

## 6. 예상 일정
- **1-4일차**: Spotify 개발자 계정 생성, API 키 발급, OAuth 인증 구현 및 테스트
- **5-7일차**: spotipy로 곡 검색 기능 구현 (곡명 → Track ID 변환)
- **8-10일차**: Recommendations 엔드포인트 호출 및 결과 파싱
- **11-12일차**: CLI 입력/출력 정리, 에러 처리 (곡을 못 찾았을 때 등)
- **13-14일차**: 테스트, 버그 수정, README 작성

## 7. 주요 리스크
| 리스크 | 확률 | 대응 방안 |
|--------|------|-----------|
| **OAuth 인증 막힘** | 50-60% | spotipy 공식 문서 튜토리얼 따라하기, Stack Overflow `[spotipy] oauth` 태그 검색, 2-3일 안에 해결 안 되면 커뮤니티에 질문 |
| **API 응답 JSON 파싱 어려움** | 30% | `print(response)` 로 전체 구조 확인 후 필요한 키만 추출, 온라인 JSON formatter 활용 |
| **spotipy 설치 오류** | 20% | `pip install spotipy` 실패 시 파이썬 버전 확인 (3.7 이상), 가상환경 사용 권장 |
| **곡 검색 결과 없음** | 20% | 검색어 오타 방지 안내 메시지, 여러 결과 중 선택 옵션 추가 |
| **Spotify 무료 계정 제한** | 10% | 개인 사용 범위 내 하루 수천 건 요청 가능, 문제 발생 시 요청 횟수 줄이기 |

## 8. 참고 자료
- [Spotify for Developers 공식 문서](https://developer.spotify.com/documentation/web-api) - API 엔드포인트 명세, 인증 가이드
- [spotipy 공식 문서](https://spotipy.readthedocs.io/) - 파이썬 래퍼 사용법, OAuth 예제
- [Spotify API Recommendations 엔드포인트](https://developer.spotify.com/documentation/web-api/reference/get-recommendations) - 유사곡 추천 파라미터 설명
- [OAuth 2.0 Authorization Code Flow 튜토리얼](https://developer.spotify.com/documentation/general/guides/authorization-guide/) - 인증 흐름 단계별 가이드
- [spotipy GitHub Examples](https://github.com/spotipy-dev/spotipy/tree/master/examples) - 실전 코드 샘플 (검색, 추천 등)