"""Read Live's `Log.txt`: the tracebacks and messages of Remote Scripts in the last Live session.

Live writes a script's traceback in fragments, one log record per `write` call:
`<time>: error: RemoteScriptError: <fragment>`. A fragment that ended with a newline is followed by
an empty line in the file, and a repeated fragment becomes `Last message repeated N time(s): …`.
Joining the fragments gives the traceback back as Python printed it. A script's `log_message`
appears as `<time>: info: RemoteScriptMessage: (<Script>) <text>`.

Only the user runs Live; this module only reads the file.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

RECORD = re.compile(r"^(\d{4}-\d\d-\d\dT[\d:.]+): (\w+): (.*)$")
REPEATED = re.compile(r"^Last message repeated (\d+) time\(s\): (.*)$")
STARTED = re.compile(r"^Started: Live (\S+)")
MESSAGE = re.compile(r"^\((.+?)\) (.*)$")
SCRIPT_PATH = re.compile(r"Remote Scripts/([^/\"]+)/")
IMPORT_LINE = re.compile(r"^\s*import (\S+)\s*$", re.MULTILINE)  # Live's `import <folder>` when the name breaks it
ERROR_TAG = "RemoteScriptError: "
MESSAGE_TAG = "RemoteScriptMessage: "
TRACEBACK_HEAD = "Traceback (most recent call last):"
# the line before the next traceback of one chained exception
CHAINED = ("another exception occurred:", "the direct cause of the following exception:")


def preferences_dir() -> Path:
    """Where Live keeps one folder per build (`Live 12.4.16/`) with its `Log.txt`."""
    return Path(os.environ.get("ABLETON_PREFERENCES", Path.home() / "Library/Preferences/Ableton"))


def find_log(live_build: str | None = None, prefs: Path | None = None) -> Path | None:
    """The `Log.txt` of one Live build, or the most recently written one."""
    prefs = prefs or preferences_dir()
    if live_build:
        path = prefs / f"Live {live_build}" / "Log.txt"
        return path if path.is_file() else None
    logs = [p for p in prefs.glob("Live */Log.txt") if p.is_file()]
    return max(logs, key=lambda p: p.stat().st_mtime) if logs else None


def _records(lines: list[str]):
    """Yield (line number, level, text, ends_line) for each log record; a record whose text ended
    with a newline is followed by an empty line in the file."""
    for i, line in enumerate(lines):
        m = RECORD.match(line)
        if not m:
            continue
        ends = i + 1 < len(lines) and lines[i + 1] == ""
        yield i + 1, m.group(2), m.group(3), ends


def read_log(path: Path, script: str | None = None) -> dict:
    """The tracebacks and messages since Live last started, as the query core answers.

    With `script`, only the tracebacks that pass through that script's folder and the messages it
    logged; `others` counts the tracebacks left out.
    """
    if not path.is_file():
        return {"status": "not_found", "message": f"no Live log at {path}"}
    lines = path.read_text(errors="replace").splitlines()
    start, live_build = 0, None
    for i, line in enumerate(lines):
        m = RECORD.match(line)
        if m and (s := STARTED.match(m.group(3))):
            start, live_build = i, s.group(1)
    session = lines[start:]
    tracebacks: list[dict] = []
    messages: list[dict] = []
    current: dict | None = None
    for n, _level, text, ends in _records(session):
        times = 1
        if r := REPEATED.match(text):
            times, text = int(r.group(1)), r.group(2)
        if text.startswith(ERROR_TAG):
            fragment = text[len(ERROR_TAG):]
            if current is not None and fragment.startswith(TRACEBACK_HEAD):
                so_far = "".join(current["parts"]).strip()
                if so_far and not so_far.endswith(CHAINED):
                    current = None  # a second traceback written right after the first
            if current is None:
                current = {"line": start + n, "parts": []}
                tracebacks.append(current)
            current["parts"].append((fragment + ("\n" if ends else "")) * times)
            continue
        current = None
        if text.startswith(MESSAGE_TAG) and (m := MESSAGE.match(text[len(MESSAGE_TAG):])):
            messages.append({"line": start + n, "script": m.group(1), "text": m.group(2)})
    for t in tracebacks:
        t["text"] = "".join(t.pop("parts")).strip("\n")
        t["scripts"] = sorted(set(SCRIPT_PATH.findall(t["text"]))
                              | (set(IMPORT_LINE.findall(t["text"])) if '"<string>"' in t["text"] else set()))
    others = 0
    if script:
        kept = [t for t in tracebacks if script in t["scripts"]]
        others = len(tracebacks) - len(kept)
        tracebacks = kept
        messages = [m for m in messages if m["script"] == script]
    return {
        "status": "ok",
        "log": str(path),
        "live_build": live_build,
        "session_line": start + 1,
        "script": script,
        "tracebacks": tracebacks,
        "messages": messages,
        "others": others,
    }
