"""The run's report (plan 0002 Decision 18): a short printed summary and the full result as
`checks.result.json` beside the check file (git-ignored)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .checks import RESULT_NAME


def write_result(result: dict, check_file: Path) -> Path:
    path = Path(check_file).parent / RESULT_NAME
    stamped = {"finished": datetime.now(UTC).isoformat(timespec="seconds"), **result}
    path.write_text(json.dumps(stamped, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def format_report(result: dict) -> str:
    c = result["counts"]
    lines = [(f"{result['script']} on `{result['port']}`: {c['passed']} passed, {c['failed']} failed, "
             f"{c['skipped']} skipped, {c['ask_user']} to ask the user")]
    for step in result["steps"]:
        if step["verdict"] == "failed":
            lines.append(f"failed  {step['id']}: {step['description']}")
            lines += [f"    {r}" for r in step["reasons"]]
            if step.get("sent"):
                lines.append(f"    sent: {'; '.join(step['sent'])}")
            lines.append(f"    received: {'; '.join(step.get('received') or []) or 'nothing'}")
        elif step["verdict"] == "skipped":
            lines.append(f"skipped {step['id']}: {step['reasons'][0]}")
    unchecked = [s["id"] for s in result["steps"] if s.get("not_checked")]
    if unchecked:
        lines.append(f"Live's state not checked (no AbletonMCP) in: {', '.join(unchecked)}")
    untested = sorted({c for s in result["steps"] for c in s.get("untested_commands", [])})
    if untested:
        lines.append(f"used AbletonMCP commands not yet on the tested list: {', '.join(untested)}")
    asks = [s for s in result["steps"] if s["verdict"] == "ask_user"]
    if asks:
        lines.append("ask the user:")
        lines += [f"  {s['id']}: {s['question']}" for s in asks]
    return "\n".join(lines)
