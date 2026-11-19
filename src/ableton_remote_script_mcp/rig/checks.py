"""Check files (plan 0002 Decision 8) and `rig run`: play a controller to a Remote Script as a
`checks.yaml` says and decide each step from what Live sends back and from `Log.txt`.

A check file sits beside (or names) the script folder:

    script: .            # the script folder, relative to this file (default: the file's folder)
    build: 12.4.16       # the Live build whose index reads the script (default: newest indexed)
    settle: 1.5          # seconds without MIDI before the first step (the script's start-up state)
    quiet: 0.15          # seconds without MIDI that end a step (default for every step)
    wait: 0.5            # the least a step listens (Live's value feedback comes late)
    timeout: 3.0         # the longest a step waits for Live to go quiet
    steps:
      - id: fader-1
        description: fader 1 sets track 1's volume and Live sends the value back
        send:
          faders[0]: 100   # element name: value
        expect:
          faders[0]: 100   # the last reply on that element: a value, a list of values, any, none
        log: clean       # no new traceback of the script during the step
      - id: session-box
        depends_on: [fader-1]
        ask_user: Is there a box around tracks 1-8, scene 1?

`send` is a mapping (sent in order) or a list of mappings and raw messages (`cc 13 40 100`, hex).
A value is a number; `press` sends 127 then 0 to a button; on a relative encoder a number is
steps up (positive) or down (negative), encoded as its map mode says. A matrix's elements are
`<matrix>[i]`, counted row by row from 0. A step passes when every expectation holds; a step with
`ask_user` reports its question (after sending, if it sends). A failure doesn't stop the run; a
step whose `depends_on` failed or was skipped is skipped.

Only the last reply per element counts: Live sends a control's value more than once (step 1).

With AbletonMCP running, a step can also `do` a command in Live first (the Live → controller
direction), and expect Live's `state` and AbletonMCP's listener `events`; the file's `requires`
is checked before the first step. See `state.py`. Without AbletonMCP, a step that does something
is skipped, and its state and event expectations are listed as not checked.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .controller import Controller, Element
from .ports import describe, parse_message, wait_quiet
from .abletonmcp import TESTED
from .state import (
    StateError,
    check_events,
    check_state,
    parse_do,
    parse_events,
    parse_requires,
    parse_state,
)

STEP_KEYS = {"id", "description", "send", "expect", "log", "depends_on", "ask_user", "quiet", "timeout", "wait",
             "do", "state", "events"}
FILE_KEYS = {"script", "build", "settle", "quiet", "timeout", "wait", "steps", "requires"}
# wait: Live sends a value back to an element later than 150 ms after it arrives (12.4.16, the
# UC4 run of 2026-11-18: each echo came in the next step), so a step listens at least this long
DEFAULTS = {"settle": 1.5, "quiet": 0.15, "timeout": 3.0, "wait": 0.5}
RESULT_NAME = "checks.result.json"
PRESS_GAP = 0.02  # seconds between a press's 127 and 0


class CheckFileError(ValueError):
    pass


@dataclass
class Step:
    id: str
    description: str = ""
    send: list = field(default_factory=list)  # [("element", value) | [raw bytes]]
    expect: dict = field(default_factory=dict)
    log_clean: bool = False
    depends_on: list[str] = field(default_factory=list)
    ask_user: str | None = None
    quiet: float = DEFAULTS["quiet"]
    timeout: float = DEFAULTS["timeout"]
    wait: float = DEFAULTS["wait"]
    do: list = field(default_factory=list)  # [(command, AbletonMCP params)]
    state: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    @property
    def needs_live_state(self) -> bool:
        return bool(self.do or self.state or self.events)


@dataclass
class CheckFile:
    path: Path
    script_folder: Path
    build: str | None
    settle: float
    steps: list[Step]
    requires: dict = field(default_factory=dict)


def load_check_file(path: Path) -> CheckFile:
    import yaml

    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise CheckFileError(f"{path}: {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("steps"), list):
        raise CheckFileError(f"{path}: a check file is a mapping with a list of `steps`")
    _unknown(data, FILE_KEYS, str(path))
    opts = {k: float(data.get(k, v)) for k, v in DEFAULTS.items()}
    steps, seen = [], set()
    for i, raw in enumerate(data["steps"], 1):
        where = f"{path}, step {i}"
        if not isinstance(raw, dict) or "id" not in raw:
            raise CheckFileError(f"{where}: each step is a mapping with an `id`")
        _unknown(raw, STEP_KEYS, where)
        sid = str(raw["id"])
        if sid in seen:
            raise CheckFileError(f"{where}: the id `{sid}` is used twice")
        deps = raw.get("depends_on") or []
        deps = [deps] if isinstance(deps, str) else [str(d) for d in deps]
        missing = [d for d in deps if d not in seen]
        if missing:
            raise CheckFileError(f"{where}: depends_on {', '.join(missing)}, which no earlier step has as id")
        seen.add(sid)
        log = raw.get("log")
        if log not in (None, "clean"):
            raise CheckFileError(f"{where}: `log` takes only `clean`")
        expect = raw.get("expect") or {}
        if not isinstance(expect, dict):
            raise CheckFileError(f"{where}: `expect` is a mapping of element name to value")
        if not (raw.get("send") or expect or log or raw.get("ask_user") or raw.get("do") or raw.get("state")
                or raw.get("events")):
            raise CheckFileError(f"{where}: a step sends, does, expects, checks the log or asks the user")
        try:
            live = {"do": parse_do(raw["do"], where) if raw.get("do") else [],
                    "state": parse_state(raw["state"], where) if raw.get("state") else {},
                    "events": parse_events(raw["events"], where) if raw.get("events") else []}
        except StateError as e:
            raise CheckFileError(str(e)) from e
        steps.append(Step(**live,
            id=sid, description=str(raw.get("description", "")), send=_sends(raw.get("send"), where),
            expect={str(k): v for k, v in expect.items()}, log_clean=log == "clean", depends_on=deps,
            ask_user=raw.get("ask_user"), quiet=float(raw.get("quiet", opts["quiet"])),
            timeout=float(raw.get("timeout", opts["timeout"])), wait=float(raw.get("wait", opts["wait"]))))
    folder = (path.parent / str(data.get("script", "."))).resolve()
    try:
        requires = parse_requires(data.get("requires"), str(path))
    except StateError as e:
        raise CheckFileError(str(e)) from e
    return CheckFile(path, folder, data.get("build") and str(data["build"]), opts["settle"], steps, requires)


def _unknown(data: dict, allowed: set[str], where: str) -> None:
    extra = sorted(set(map(str, data)) - allowed)
    if extra:
        raise CheckFileError(f"{where}: unknown key(s) {', '.join(extra)}; known: {', '.join(sorted(allowed))}")


def _sends(raw, where: str) -> list:
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    out = []
    for item in items:
        if isinstance(item, dict):
            out += [(str(k), v) for k, v in item.items()]
        elif isinstance(item, str):
            try:
                out.append(parse_message(item))
            except ValueError as e:
                raise CheckFileError(f"{where}: {e}") from e
        else:
            raise CheckFileError(f"{where}: `send` takes element: value pairs or raw messages")
    return out


def check_names(checks: CheckFile, ctl: Controller) -> list[str]:
    """Element names in the check file that the controller doesn't have."""
    problems = []
    for step in checks.steps:
        names = [s[0] for s in step.send if isinstance(s, tuple)] + list(step.expect)
        for name in names:
            try:
                ctl.element(name)
            except KeyError as e:
                problems.append(f"step {step.id}: {e.args[0]}")
    return problems


def encode(element: Element, value) -> list[list[int]]:
    """The messages that play `value` on `element`."""
    if value == "press":
        return [element.message(127), element.message(0)]
    if not isinstance(value, int) or isinstance(value, bool):
        raise CheckFileError(f"{element.name}: send a number or `press`, not {value!r}")
    if element.relative:
        return [element.message(_relative(element.map_mode, value))]
    if not 0 <= value <= 127:
        raise CheckFileError(f"{element.name}: value {value} is outside 0-127")
    return [element.message(value)]


def _relative(mode: str, steps: int) -> int:
    """One relative message for `steps` (the sign is the direction), as the map mode reads it.
    Only two's complement so far: 1 up, 127 down (tested with the UC4's CCr1, Live 12.4.16);
    the other relative modes wait for a script that uses them."""
    if steps == 0 or abs(steps) > 63:
        raise CheckFileError(f"a relative step of {steps} (use -63..-1 or 1..63)")
    if mode in ("LinearTwoCompliment", "AccelTwoCompliment"):
        return steps if steps > 0 else 128 + steps
    raise CheckFileError(f"the rig can't play the map mode {mode} yet; send a raw message instead")


def _key(message: list[int]) -> tuple[tuple[int, int], int] | None:
    """((status, number), value) of a reply, a note off read as velocity 0."""
    if len(message) < 3 or message[0] >= 0xF0:
        return None
    status, number, value = message[0], message[1], message[2]
    if status & 0xF0 == 0x80:
        status, value = 0x90 | (status & 0x0F), 0
    if status & 0xF0 == 0xE0:
        return (status, 0), number | (value << 7)
    return (status, number), value


def _holds(want, got: list[int]) -> tuple[bool, str]:
    last = got[-1] if got else None
    if want == "none":
        return not got, "no reply" if not got else f"replied {last}"
    if want == "any":
        return bool(got), f"replied {last}" if got else "no reply"
    allowed = want if isinstance(want, list) else [want]
    if not got:
        return False, "no reply"
    return last in allowed, f"last reply {last}" + (f" (all: {', '.join(map(str, got))})" if len(got) > 1 else "")


class LogWatch:
    """New tracebacks of one script in `Log.txt` since `mark()`."""

    def __init__(self, path: Path | None, script: str):
        self.path, self.script, self.line = path, script, 0

    def mark(self) -> None:
        if self.path and self.path.is_file():
            with self.path.open("rb") as f:
                self.line = sum(1 for _ in f)

    def new_tracebacks(self) -> list[dict]:
        from ..live_log import read_log

        answer = read_log(self.path, self.script)
        if answer["status"] != "ok":
            return []
        return [t for t in answer["tracebacks"] + answer["framework_only"] if t["line"] > self.line]


def run_checks(checks: CheckFile, ctl: Controller, port, log: LogWatch | None = None,
               sleep=time.sleep, quiet_wait=wait_quiet, say=print, mcp=None, mcp_note: str = "") -> dict:
    """Run every step; the result as `checks.result.json` holds it. `mcp` is an AbletonMCP
    client, or None (`mcp_note` says why)."""
    if mcp is not None:
        from .state import check_requires

        missing = check_requires(mcp, checks.requires, log=say)
        if missing:
            raise CheckFileError("the open Set lacks what the check file requires: " + "; ".join(missing))
    elif checks.requires:
        say(f"`requires` not checked: {mcp_note or 'no AbletonMCP'}")
    start = quiet_wait(port, checks.settle, max(10.0, checks.settle * 4))
    say(f"start-up: {len(start)} message(s) from Live, then {checks.settle:.1f} s quiet")
    results: dict[str, dict] = {}
    for step in checks.steps:
        blocked = [d for d in step.depends_on if results[d]["verdict"] in ("failed", "skipped")]
        if blocked:
            results[step.id] = {"id": step.id, "description": step.description, "verdict": "skipped",
                                "reasons": [f"depends on {', '.join(blocked)}"]}
        elif step.do and mcp is None:
            results[step.id] = {"id": step.id, "description": step.description, "verdict": "skipped",
                                "reasons": [(f"needs AbletonMCP to do {', '.join(c for c, _ in step.do)}: "
                                            f"{mcp_note or 'not connected'}")]}
        else:
            results[step.id] = _run_step(step, ctl, port, log, sleep, quiet_wait, mcp)
        r = results[step.id]
        say(f"{r['verdict'].upper():8} {step.id}" + (f" — {r['reasons'][0]}" if r.get("reasons") else ""))
    counts = {v: sum(r["verdict"] == v for r in results.values()) for v in ("passed", "failed", "skipped", "ask_user")}
    return {"check_file": str(checks.path), "script": ctl.script, "folder": ctl.folder, "port": port.name,
            "abletonmcp": (mcp.info.get("script_version") if mcp is not None else None) or mcp_note,
            "counts": counts, "steps": list(results.values())}


def _run_step(step: Step, ctl: Controller, port, log: LogWatch | None, sleep, quiet_wait, mcp=None) -> dict:
    stray = port.drain()
    if mcp is not None and step.needs_live_state:
        mcp.events()  # what happened before the step
    if log and step.log_clean:
        log.mark()
    done, reasons = [], []
    for command, params in step.do:
        try:
            mcp.call(command, **params)
            done.append(f"{command} {params}")
        except Exception as e:  # noqa: BLE001  a failed command is the step's result
            reasons.append(f"AbletonMCP {command} {params} failed: {e}")
    sent: list[list[int]] = []
    for item in step.send:
        messages = encode(ctl.element(item[0]), item[1]) if isinstance(item, tuple) else [item]
        for i, m in enumerate(messages):
            if i:
                sleep(PRESS_GAP)
            port.send(m)
            sent.append(m)
    listen = sent or step.expect or done or step.state or step.events
    replies = quiet_wait(port, step.quiet, step.timeout, at_least=step.wait) if listen else []
    by_key: dict[tuple[int, int], list[int]] = {}
    for r in replies:
        k = _key(r.message)
        if k:
            by_key.setdefault(k[0], []).append(k[1])
    result = {"id": step.id, "description": step.description,
              "sent": [describe(m) for m in sent], "received": [describe(r.message) for r in replies]}
    if done:
        result["done"] = done
    if stray:
        result["before_step"] = [describe(r.message) for r in stray]
    expectations = []
    for name, want in step.expect.items():
        element = ctl.element(name)
        ok, got = _holds(want, by_key.get(element.key, []))
        expectations.append({"element": name, "message": element.describe(), "expected": want, "got": got, "ok": ok})
        if not ok:
            reasons.append(f"{name}: expected {want}, {got}")
    result["expect"] = expectations
    if mcp is not None and (step.state or step.events):
        events = mcp.events() if step.events else []
        live = check_state(mcp, step.state) + check_events(step.events, events)
        result["live"] = live
        if step.events:
            result["events"] = [{k: e.get(k) for k in ("type", "track_index", "clip_index", "detail")} for e in events]
        for r in live:
            if not r["ok"]:
                what = r.get("state") or r.get("event")
                reasons.append(f"{what}: expected {r.get('expected', 'it')}, got {r['got']}"
                               if "state" in r else f"no event {what} during the step")
        result["untested_commands"] = sorted({r.get("untested_as", r["command"])
                                              for r in live if r.get("tested") is False})
    elif step.state or step.events:
        result["not_checked"] = [*(f"state {k}" for k in step.state), *(f"event {e['type']}" for e in step.events)]
    if mcp is not None:  # the writes too (plan 0002 Decision 25)
        untested = set(result.pop("untested_commands", [])) | {c for c, _ in step.do if c not in TESTED}
        if untested:
            result["untested_commands"] = sorted(untested)
    if step.log_clean and log:
        tracebacks = log.new_tracebacks()
        result["tracebacks"] = [t["text"] for t in tracebacks]
        if tracebacks:
            last = tracebacks[0]["text"].strip().splitlines()[-1]
            reasons.append(f"a traceback in Log.txt at line {tracebacks[0]['line']}: {last}")
    if reasons:
        result["verdict"], result["reasons"] = "failed", reasons
    elif step.ask_user:
        result["verdict"], result["question"] = "ask_user", step.ask_user
        result["reasons"] = [step.ask_user]
    else:
        result["verdict"] = "passed"
    return result
