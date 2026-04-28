# 에이전트 파이프라인 CLI 실행 진입점
# 실행: backend/ 디렉토리에서 python -m agents.run "아이디어 텍스트"
# (-m 없이 python agents/run.py 로 실행하면 상대 import 오류 발생)
import asyncio
import sys
from pathlib import Path

from .orchestrator import run


# CLI 진입점 — 인자 파싱 후 orchestrator.run() 호출, 결과 콘솔 출력 + PRD 파일 저장
def main():
    # CLI 인자가 있으면 그대로 사용, 없으면 빈 줄 입력까지 대화형으로 수집
    if len(sys.argv) > 1:
        user_conditions = " ".join(sys.argv[1:])
    else:
        print("사용자 조건을 입력하세요 (빈 줄로 종료):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        user_conditions = "\n".join(lines)

    # 사용자 입력이 없다면 종료
    if not user_conditions.strip():
        print("조건이 비어 있습니다.")
        sys.exit(1)

    # 오케스트레이터 실행 (비동기 → 동기 진입점)
    print("\n실행 중...\n")
    result = asyncio.run(run(user_conditions))

    # 루프 요약 출력
    print("\n" + "=" * 60)
    print(f"job_id : {result['job_id']}")
    print(f"loops  : {len(result['loop_history'])}")
    print("=" * 60)

    # 각 루프의 gate 결정 및 평가 점수 출력
    for entry in result["loop_history"]:
        critics = entry.get("critics", [])
        last_score = critics[-1].get("score", {}) if critics else {}
        score_str = f"feasibility={last_score.get('feasibility', '-')} fit={last_score.get('fit', '-')} clarity={last_score.get('clarity', '-')}"
        print(f"  loop {entry['loop']} | gate: {entry.get('gate_decision', '-')} | {score_str}")

    # 최종 PRD 앞부분 미리보기
    print("\n── PRD (first 800 chars) ──")
    print(result["prd"][:800])
    print("...")

    # 전체 PRD를 logs/ 디렉터리에 마크다운 파일로 저장
    logs_dir = Path(__file__).parent.parent.parent / "docs" / "generated_prds"
    logs_dir.mkdir(parents=True, exist_ok=True)
    out_path = logs_dir / f"prd_{result['job_id']}.md"
    out_path.write_text(result["prd"], encoding="utf-8")
    print(f"\n전체 PRD 저장됨 → {out_path}")


if __name__ == "__main__":
    main()
