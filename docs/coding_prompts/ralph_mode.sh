#!/bin/bash

MAX=${1:-3}
PROMPT="docs/ralph_mode/ralph_prompt.md"
LOG="docs/ralph_mode/ai-usage-log.md"

[ ! -f "$PROMPT" ] && echo "❌ $PROMPT 없음" && exit 1

# 로그 초기화 (append 방식)
if [ ! -f "$LOG" ]; then
  echo "# IdeaVault Frontend - Ralph Mode Log" > "$LOG"
  echo "" >> "$LOG"
  echo "시작: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
  echo "" >> "$LOG"
fi

i=0
while [ $i -lt $MAX ]; do
  echo "=== Loop $((i+1))/$MAX ==="
  
  # 로그 append
  echo "## Loop $((i+1))" >> "$LOG"
  echo "시작: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
  echo "" >> "$LOG"
  
  # Claude Code 실행 (frontend 폴더에서)
  cd frontend && cat "../$PROMPT" | claude code && cd ..
  
  # 완료 체크
  grep -q "FRONTEND_COMPLETE" "$LOG" && echo "✅ 완료!" && exit 0
  
  i=$((i+1))
done

echo "⚠️  최대 반복 도달 ($MAX)"
exit 1