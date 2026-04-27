#!/bin/bash

MAX=${1:-3}
PROMPT="docs/ralph_mode/ralph_prompt.md"
LOG="docs/ralph_mode/ai-usage-log.md"

[ ! -f "$PROMPT" ] && echo "❌ $PROMPT 없음" && exit 1

# 로그 초기화 또는 기존 Loop 번호 확인
if [ ! -f "$LOG" ]; then
  echo "# IdeaVault Frontend - Ralph Mode Log" > "$LOG"
  echo "" >> "$LOG"
  echo "시작: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
  echo "" >> "$LOG"
  START_LOOP=0
else
  # 기존 로그에서 마지막 Loop 번호 찾기
  LAST_LOOP=$(grep -oP '(?<=## Loop )\d+' "$LOG" | tail -1)
  START_LOOP=${LAST_LOOP:-0}
  echo "기존 Loop $START_LOOP 발견. Loop $((START_LOOP+1))부터 시작합니다."
fi

i=$START_LOOP
END_LOOP=$((START_LOOP + MAX))

while [ $i -lt $END_LOOP ]; do
  CURRENT=$((i+1))
  echo "=== Loop $CURRENT ==="
  
  # 로그 append
  echo "## Loop $CURRENT" >> "$LOG"
  echo "시작: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
  echo "" >> "$LOG"
  
  # Claude Code 실행 (frontend 폴더에서)
  cd frontend && cat "../$PROMPT" | claude code && cd ..
  
  # 완료 체크
  grep -q "FRONTEND_COMPLETE" "$LOG" && echo "✅ 완료!" && exit 0
  
  i=$((i+1))
done

echo "⚠️  Loop $END_LOOP 도달"
exit 1