"""Read Live's `Log.txt`: the tracebacks and messages of Remote Scripts in the last Live session.

Live writes a script's traceback in fragments, one log record per `write` call:
`<time>: error: RemoteScriptError: <fragment>`. A fragment that ended with a newline is followed by
an empty line in the file, and a repeated fragment becomes `Last message repeated N time(s): …`.
Joining the fragments gives the traceback back as Python printed it. A `_Framework` script's
`log_message` appears as `<time>: info: RemoteScriptMessage: (<Script>) <text>`. A v3 script
logs with Python's `logging` (`logging.getLogger(__name__)`, as Ableton's v3 scripts do), which
Live writes as `<time>: info: Python: <LEVEL>:<logger>:<ms> - <text>` (the number is the
milliseconds of the record's time); the script is the logger name's first part (observed in
12.4.16 logs, for `_Framework`'s logger and the UC4 script's own). Loggers of Live's shared
packages and of Live itself (`licensing`) are left out.

Only the user runs Live; this module only reads the file.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

RECORD = re.compile(r"^(\d{4}-\d\d-\d\dT[\d:.]+): (\w+): (.*)$")
REPEATED = re.compile(r"^Last message repeated (\d+) time\(s\): (.*)$")
STARTED = re.compile(r"^Started: Live (\S+)")
MESSAGE = re.compile(r"^\((.+?)\) (.*)\Z", re.DOTALL)
PYTHON_LOG = re.compile(r"^Python: (DEBUG|INFO|WARNING|ERROR|CRITICAL):([\w.]+):\d+ - (.*)\Z", re.DOTALL)
NOT_SCRIPTS = {"licensing"}  # Live's own Python loggers that are not Remote Scripts
SCRIPT_PATH = re.compile(r"Remote Scripts/([^/\"]+)/")
IMPORT_LINE = re.compile(r"^\s*import (\S+)\s*$", re.MULTILINE)  # Live's `import <folder>` when the name breaks it
ERROR_TAG = "RemoteScriptError: "
MESSAGE_TAG = "RemoteScriptMessage: "
TRACEBACK_HEAD = "Traceback (most recent call last):"
# the line before the next traceback of one chained exception
CHAINED = ("another exception occurred:", "the direct cause of the following exception:")


SHARED_PACKAGES = {"ableton", "pushbase", "novation"}


def is_framework(name: str) -> bool:
    """Live's shared packages rather than a controller script: the names starting with an
    underscore (`_Framework`, `_Generic`, `_APC`, ...) and `ableton`, `pushbase`, `novation`
    (observed in the 12.4.16 install, where `iRig_Keys_IO`, `microKONTROL` and `padKONTROL` are
    controller scripts despite their lower-case first letter)."""
    return name.startswith("_") or name in SHARED_PACKAGES


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
    """Yield (line number, level, text, ends_line) for each log record. A record whose text holds
    newlines goes on over the next lines, which have no timestamp (a Boost.Python
    `ArgumentError`, observed in 12.4.16); a record whose text ended with a newline is followed by
    an empty line in the file."""
    i = 0
    while i < len(lines):
        m = RECORD.match(lines[i])
        if not m:
            i += 1
            continue
        start, text = i, m.group(3)
        i += 1
        while i < len(lines) and lines[i] != "" and not RECORD.match(lines[i]):
            text += "\n" + lines[i]
            i += 1
        ends = i < len(lines) and lines[i] == ""
        yield start + 1, m.group(2), text, ends


def read_log(path: Path, script: str | None = None) -> dict:
    """The tracebacks and messages since Live last started, as the query core answers.

    With `script`, only the tracebacks that pass through that script's folder and the messages it
    logged. `framework_only` holds the tracebacks whose frames are all in Live's shared packages:
    no frame names a script, so they may come from this script (a framework call it set up, such
    as a combo) or from another one. `others` counts the tracebacks left out.
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
        elif (p := PYTHON_LOG.match(text)):
            level, logger, said = p.groups()
            first = logger.split(".")[0]
            if is_framework(first) or first in NOT_SCRIPTS:
                continue  # Live's own; _Framework's copy of a RemoteScriptMessage among them
            messages.append({"line": start + n, "script": first,
                             "text": said if level == "INFO" else f"{level}: {said}"})
    for t in tracebacks:
        t["text"] = "".join(t.pop("parts")).strip("\n")
        t["scripts"] = sorted(set(SCRIPT_PATH.findall(t["text"]))
                              | (set(IMPORT_LINE.findall(t["text"])) if '"<string>"' in t["text"] else set()))
    others = 0
    framework_only: list[dict] = []
    if script:
        kept = [t for t in tracebacks if script in t["scripts"]]
        framework_only = [t for t in tracebacks if t["scripts"] and script not in t["scripts"]
                          and all(map(is_framework, t["scripts"]))]
        others = len(tracebacks) - len(kept) - len(framework_only)
        tracebacks = kept
        messages = [m for m in messages if m["script"] == script]
    return {
        "status": "ok",
        "log": str(path),
        "live_build": live_build,
        "session_line": start + 1,
        "script": script,
        "tracebacks": tracebacks,
        "framework_only": framework_only,
        "messages": messages,
        "others": others,
    }
