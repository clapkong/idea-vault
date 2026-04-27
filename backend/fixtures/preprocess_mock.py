import json
import re
from datetime import datetime
from pathlib import Path

TIMESTAMP_RE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (.*)$')
AGENT_CALL_RE = re.compile(r'^\[([^\]]+)\] CALL \|')
AGENT_DONE_RE = re.compile(r'^\[([^\]]+)\] DONE \| (.*)$')
TOKENS_RE = re.compile(r'^\[tokens\] .+ \| .*total=(\d+)')
ORCH_START_RE = re.compile(r'^\[orchestrator\] START \| job_id=(\S+)')
ORCH_END_RE = re.compile(r'^\[orchestrator\] END')

SEPARATOR = "────────────────────────────────────────────────────────────"
REAL_AGENTS = {'planner', 'researcher', 'analyst', 'critic', 'gate', 'prd_writer'}


def normalize_agent(raw: str) -> str:
    # "gate(forced)" → "gate", "prd_writer(forced)" → "prd_writer"
    return raw.split('(')[0]


def parse_log_file(log_path: str) -> dict:
    path = Path(log_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    lines = path.read_text(encoding='utf-8').splitlines()

    job_id = ""
    events = []
    last_tokens = 0
    prev_ts = None

    for raw in lines:
        m = TIMESTAMP_RE.match(raw)
        if not m:
            continue

        ts_str, content = m.group(1), m.group(2).strip()
        if not content:
            continue

        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"WARNING: bad timestamp: {ts_str!r}")
            continue

        m_start = ORCH_START_RE.match(content)
        if m_start:
            job_id = m_start.group(1)
            continue

        if ORCH_END_RE.match(content):
            delay = 0 if prev_ts is None else int((ts - prev_ts).total_seconds())
            events.append({"delay_sec": delay, "type": "done", "prd_url": f"/result/{job_id}"})
            break

        m_tok = TOKENS_RE.match(content)
        if m_tok:
            last_tokens = int(m_tok.group(1))
            continue

        m_call = AGENT_CALL_RE.match(content)
        if m_call:
            agent = normalize_agent(m_call.group(1))
            if agent not in REAL_AGENTS:
                continue
            delay = 0 if prev_ts is None else int((ts - prev_ts).total_seconds())
            events.append({"delay_sec": delay, "type": "agent_start", "agent": agent, "timestamp": ts.strftime("%H:%M:%S")})
            events.append({"delay_sec": 0, "type": "agent_progress", "agent": agent})
            prev_ts = ts
            continue

        m_done = AGENT_DONE_RE.match(content)
        if m_done:
            agent = normalize_agent(m_done.group(1))
            if agent not in REAL_AGENTS:
                continue
            output_text = m_done.group(2)
            delay = 0 if prev_ts is None else int((ts - prev_ts).total_seconds())
            events.append({
                "delay_sec": delay,
                "type": "agent_done",
                "agent": agent,
                "output": output_text,
                "tokens": last_tokens,
            })
            prev_ts = ts
            last_tokens = 0
            continue

    prd = _extract_prd_from_output_block(lines)

    return {
        "job_id": job_id,
        "events": events,
        "prd": prd.strip(),
        "loop_history": [],
    }


def _extract_prd_from_output_block(lines: list[str]) -> str:
    """마지막 [prd_writer] 상세 블록의 <출력> 섹션 추출."""
    block_starts = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in ('[prd_writer]', '[prd_writer(forced)]'):
            if i > 0 and lines[i - 1].strip() == SEPARATOR:
                block_starts.append(i)

    if not block_starts:
        return ""

    in_output = False
    prd_lines = []

    for line in lines[block_starts[-1]:]:
        stripped = line.strip()
        if stripped == SEPARATOR:
            if in_output:
                break
            continue
        if stripped == '<출력>':
            in_output = True
            continue
        if in_output:
            prd_lines.append(line)

    return "\n".join(prd_lines)


def main():
    log_path = "../../docs/agent_logs/run_92b2d589.log"
    output_path = "backend/mock_agents/data.json"

    mock_data = parse_log_file(log_path)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mock_data, f, ensure_ascii=False, indent=2)

    print(f"Mock 데이터 생성 완료: {output_path}")
    print(f"  - events 개수: {len(mock_data['events'])}")
    print(f"  - PRD 길이: {len(mock_data['prd'])} 문자")
    print(f"  - job_id: {mock_data['job_id']}")

    print("\n첫 5개 이벤트:")
    for ev in mock_data['events'][:5]:
        print(f"  {ev}")

    delays = [e["delay_sec"] for e in mock_data["events"]]
    total = sum(delays)
    print(f"\ndelay_sec 합계: {total}s ({total // 60}분 {total % 60}초)")


if __name__ == "__main__":
    main()
