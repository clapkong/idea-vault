#!/usr/bin/env python3
"""
Parse an agent run log and produce meta.json + result.json + input.txt
under data/jobs/{job_id}/.

Usage:
    python tools/parse_log_to_job.py docs/agent_logs/run_e0d224ae.log
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


# ── block helpers ──────────────────────────────────────────────────────────────

def parse_block_input(text: str) -> dict:
    """Parse the indented key: value section of a block into a dict."""
    result = {}
    key = None
    val_lines = []
    for line in text.splitlines():
        m = re.match(r"  (\w+):\s*(.*)", line)
        if m:
            if key is not None:
                result[key] = "\n".join(val_lines).strip()
            key, val_lines = m.group(1), [m.group(2)]
        elif key is not None:
            val_lines.append(line)
    if key is not None:
        result[key] = "\n".join(val_lines).strip()
    return result


def extract_critic_summary(output: str) -> str:
    """Drop direction/score lines; return the evaluation text."""
    keep = []
    for line in output.splitlines():
        if re.match(r"(보강\s*방향|방향|feasibility|fit|clarity)\s*:", line.strip(), re.I):
            break
        keep.append(line)
    text = "\n".join(keep).strip()
    return re.sub(r"^평가:\s*", "", text)


def extract_scores(output: str) -> dict:
    scores = {}
    for key in ("feasibility", "fit", "clarity"):
        m = re.search(rf"^{key}\s*:\s*(\d+)", output, re.M | re.I)
        if m:
            scores[key] = int(m.group(1))
    return scores


def parse_blocks(lines: list) -> list:
    """
    Return [{agent, input_text, output_text}] in log order.
    Each block is delimited by ─── lines with [AgentName] right after the opener.
    """
    result = []
    i = 0
    while i < len(lines):
        if not re.match(r"^─{20,}$", lines[i]):
            i += 1
            continue

        # skip blank lines after separator
        j = i + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        if j >= len(lines):
            i += 1
            continue

        agent_m = re.match(r"^\[(\w+)\]$", lines[j].strip())
        if not agent_m:
            i += 1
            continue

        agent = agent_m.group(1)
        input_lines, output_lines = [], []
        section = None
        k = j + 1
        found_end = False

        while k < len(lines):
            if re.match(r"^─{20,}$", lines[k]):
                found_end = True
                break
            stripped = lines[k].strip()
            if stripped == "<입력>":
                section = "input"
            elif stripped == "<출력>":
                section = "output"
            elif section == "input":
                input_lines.append(lines[k])
            elif section == "output":
                output_lines.append(lines[k])
            k += 1

        result.append({
            "agent": agent,
            "input_text": "\n".join(input_lines).strip(),
            "output_text": "\n".join(output_lines).strip(),
        })
        i = (k + 1) if found_end else k

    return result


# ── log parser ─────────────────────────────────────────────────────────────────

def parse_log(log_path: Path) -> dict:
    lines = log_path.read_text(encoding="utf-8").splitlines()

    job_id = None
    start_dt = end_dt = None
    total_tokens = 0
    # per-agent token info: {agent: [{input, output, total, model}, ...]}
    agent_tokens: dict[str, list] = {}
    timeline = []

    for line in lines:
        m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (.*)", line)
        if not m:
            continue
        ts_str, rest = m.group(1), m.group(2).strip()
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        hms = dt.strftime("%H:%M:%S")

        if mm := re.match(r"\[orchestrator\] START \| job_id=(\w+)", rest):
            job_id, start_dt = mm.group(1), dt

        elif re.match(r"\[orchestrator\] END", rest):
            end_dt = dt

        # new format: [tokens] [agent] model | prompt=X completion=Y total=Z
        elif mm := re.match(
            r"\[tokens\] \[(\w+)\] (\S+) \| prompt=(\d+) completion=(\d+) total=(\d+)", rest
        ):
            agent, model = mm.group(1), mm.group(2)
            tok = {
                "input": int(mm.group(3)),
                "output": int(mm.group(4)),
                "total": int(mm.group(5)),
                "model": model,
            }
            agent_tokens.setdefault(agent, []).append(tok)
            total_tokens += tok["total"]

        elif mm := re.match(r"\[(\w+)\] CALL", rest):
            timeline.append({"event": "call", "agent": mm.group(1), "ts": hms})

        elif mm := re.match(r"\[(\w+)\] DONE", rest):
            timeline.append({"event": "done", "agent": mm.group(1), "ts": hms})

        elif mm := re.match(r"\[tool_update_loop_history\] critic \| loop=(\d+) inner=(\d+)", rest):
            timeline.append({"event": "critic_logged", "loop": int(mm.group(1)), "inner": int(mm.group(2))})

        elif mm := re.match(r"\[tool_update_loop_history\] gate \| loop=(\d+) decision=(\w+)", rest):
            timeline.append({"event": "gate_logged", "loop": int(mm.group(1)), "decision": mm.group(2)})

    return {
        "job_id": job_id,
        "start_dt": start_dt,
        "end_dt": end_dt,
        "total_tokens": total_tokens,
        "agent_tokens": agent_tokens,
        "timeline": timeline,
        "blocks": parse_blocks(lines),
    }


# ── output builder ─────────────────────────────────────────────────────────────

def build_outputs(p: dict) -> tuple[dict, dict]:
    job_id = p["job_id"]
    duration_sec = (
        round((p["end_dt"] - p["start_dt"]).total_seconds(), 1)
        if p["start_dt"] and p["end_dt"]
        else 0.0
    )

    # group blocks by agent in order
    agent_blocks: dict[str, list] = {}
    for b in p["blocks"]:
        agent_blocks.setdefault(b["agent"], []).append(b)

    # user_input: first planner block → user_conditions field
    user_input = ""
    for b in agent_blocks.get("planner", []):
        inp = parse_block_input(b["input_text"])
        user_input = inp.get("user_conditions", "")
        break

    # ── events ────────────────────────────────────────────────
    done_idx: dict[str, int] = {}
    tok_idx: dict[str, int] = {}
    events = []

    for ev in p["timeline"]:
        if ev["event"] == "call":
            a = ev["agent"]
            events.append({"type": "agent_start", "agent": a, "timestamp": ev["ts"]})
            events.append({"type": "agent_progress", "agent": a})

        elif ev["event"] == "done":
            a = ev["agent"]
            idx = done_idx.get(a, 0)
            done_idx[a] = idx + 1
            ab = agent_blocks.get(a, [])
            output = ab[idx]["output_text"] if idx < len(ab) else ""

            # pick up the next token entry for this agent
            t_idx = tok_idx.get(a, 0)
            tok_list = p["agent_tokens"].get(a, [])
            if t_idx < len(tok_list):
                tok = tok_list[t_idx]
                tok_idx[a] = t_idx + 1
                tokens = {"input": tok["input"], "output": tok["output"], "total": tok["total"]}
                model = tok["model"]
            else:
                tokens = 0
                model = None

            events.append({
                "type": "agent_done",
                "agent": a,
                "output": output,
                "tokens": tokens,
                "model": model,
                "timestamp": ev["ts"],
            })

    events.append({"type": "done", "job_id": job_id, "status": "done"})

    # ── loop_history ──────────────────────────────────────────
    critic_blocks = agent_blocks.get("critic", [])
    critic_idx = 0
    loop_map: dict[int, dict] = {}

    for ev in p["timeline"]:
        if ev["event"] == "critic_logged":
            loop_num, inner = ev["loop"], ev["inner"]
            loop_map.setdefault(loop_num, {"loop": loop_num, "gate_decision": "UNKNOWN", "critics": []})
            output = critic_blocks[critic_idx]["output_text"] if critic_idx < len(critic_blocks) else ""
            critic_idx += 1
            loop_map[loop_num]["critics"].append({
                "inner": inner,
                "summary": extract_critic_summary(output),
                "score": extract_scores(output),
            })

        elif ev["event"] == "gate_logged":
            loop_num = ev["loop"]
            loop_map.setdefault(loop_num, {"loop": loop_num, "gate_decision": ev["decision"], "critics": []})
            loop_map[loop_num]["gate_decision"] = ev["decision"]

    loop_history = [loop_map[k] for k in sorted(loop_map)]

    # ── PRD ───────────────────────────────────────────────────
    prd_blocks = agent_blocks.get("prd_writer", [])
    prd = prd_blocks[-1]["output_text"] if prd_blocks else ""

    # ── assemble ──────────────────────────────────────────────
    meta = {
        "job_id": job_id,
        "status": "done",
        "created_at": p["start_dt"].isoformat() if p["start_dt"] else "",
        "user_input": user_input,
        "favorite": False,
        "deleted": False,
        "duration_sec": duration_sec,
        "tokens": p["total_tokens"],
        "cost": 0.0,
    }
    result = {
        "prd": prd,
        "loop_history": loop_history,
        "events": events,
        "duration_sec": duration_sec,
    }
    return meta, result


# ── entry point ────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/parse_log_to_job.py <log_file>", file=sys.stderr)
        sys.exit(1)

    log_path = Path(sys.argv[1])
    if not log_path.exists():
        print(f"Not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    parsed = parse_log(log_path)
    if not parsed["job_id"]:
        print("Could not extract job_id from log", file=sys.stderr)
        sys.exit(1)

    meta, result = build_outputs(parsed)

    out_dir = Path("data/jobs") / parsed["job_id"]
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "input.txt").write_text(meta["user_input"], encoding="utf-8")

    print(f"Created: {out_dir}/")
    print(f"  meta.json   job_id={meta['job_id']}  duration={meta['duration_sec']}s  tokens={meta['tokens']}")
    print(f"  result.json prd={len(result['prd'])} chars  loops={len(result['loop_history'])}  events={len(result['events'])}")
    print(f"  input.txt")


if __name__ == "__main__":
    main()
