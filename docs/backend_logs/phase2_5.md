# 작업: 토큰 집계 수정 (Phase 2.5)

## 시작 전 필수
아래 파일 먼저 읽어라.
- backend/agents/llm.py       ← set_token_logger, 토큰 핸들러 구조 파악
- backend/agents/orchestrator.py
- backend/main.py             ← run_orchestrator_background 함수 위치 확인

---

## 문제
meta.json의 tokens, cost가 0으로 저장되고 있음.
llm.py에 set_token_logger()가 이미 있는데 orchestrator 백그라운드 태스크에서
연결이 안 된 상태.

## 구현
1. llm.py의 set_token_logger() 및 토큰 핸들러 동작 방식 파악
2. run_orchestrator_background()에서 job 시작 시 토큰 카운터 주입
3. orchestrator 완료 후 누적 토큰 합산 → meta.json 업데이트

비용 계산:
- sonnet: prompt $3/1M, completion $15/1M
- haiku: $0.25/1M, $1.25/1M

## 완료 기준
실제 orchestrator 실행 후 meta.json의 tokens, cost가 0이 아닌 값으로 저장됨