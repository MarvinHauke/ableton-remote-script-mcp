"""Live's state in check files (plan 0002 step 3), through AbletonMCP: `do` commands, `state`
and `events` expectations, and the file's `requires`.

Everything in a check file counts from 1, as Live shows it (track 1, scene 1, device 1,
parameter 1); the rig turns it into AbletonMCP's 0-based `track_index`, `clip_index`,
`device_index` and `parameter_index`.

    requires:
      tracks: 8                        # at least this many tracks
      returns: 2                       # at least this many return tracks
      devices: [1, 2]                  # these tracks have at least one device
      clips: [{track: 2, scene: 1}]    # a clip there; created (4 beats) on a MIDI track if missing
    steps:
      - id: mute-1
        send: {active_buttons[0]: press}
        state:
          track 1: {mute: true}               # get_track_info: mute, solo, arm, volume, panning, name
          song: {is_playing: false}           # get_session_info: tempo, is_playing, ...
          track 2 device 1: {Macro 1: 64}     # get_device_parameters, by parameter name
        events:
          - {type: mute_changed, track: 1}    # one of AbletonMCP's listener events during the step
      - id: macro-to-encoder
        do:
          - set_device_parameter: {track: 2, device: 1, parameter: 2, value: 64}
        expect: {rack_encoders[0]: 64}

A number matches within `TOLERANCE`; `true`, `false` and text match exactly.
"""

from __future__ import annotations

import re

from .abletonmcp import TESTED, WRITES

TOLERANCE = 0.005
ONE_BASED = {"track": "track_index", "clip": "clip_index", "scene": "clip_index", "device": "device_index",
             "parameter": "parameter_index"}
STATE_KEY = re.compile(r"^(?:song|track (\d+)(?: device (\d+))?)$")
REQUIRE_KEYS = {"tracks", "returns", "devices", "clips"}
CLIP_LENGTH = 4.0  # beats, for a clip `requires` creates


class StateError(ValueError):
    pass


def parse_do(raw, where: str) -> list[tuple[str, dict]]:
    items = raw if isinstance(raw, list) else [raw]
    out = []
    for item in items:
        if not isinstance(item, dict) or len(item) != 1:
            raise StateError(f"{where}: each `do` item is one `command: {{params}}`")
        (command, params), = item.items()
        if command not in WRITES:
            raise StateError(f"{where}: `do` takes {', '.join(sorted(WRITES))}; not `{command}`")
        out.append((command, to_params(params or {}, where)))
    return out


def to_params(params: dict, where: str) -> dict:
    if not isinstance(params, dict):
        raise StateError(f"{where}: a command's params are a mapping")
    out = {}
    for k, v in params.items():
        if k in ONE_BASED:
            if not isinstance(v, int) or v < 1:
                raise StateError(f"{where}: `{k}` counts from 1, as Live shows it")
            out[ONE_BASED[k]] = v - 1
        else:
            out[k] = v
    return out


def parse_state(raw, where: str) -> dict:
    if not isinstance(raw, dict):
        raise StateError(f"{where}: `state` maps `song`, `track N` or `track N device M` to fields")
    for key, fields in raw.items():
        if not STATE_KEY.match(str(key)) or not isinstance(fields, dict):
            raise StateError(f"{where}: `state` key `{key}`: use `song`, `track N` or `track N device M` "
                             "with a mapping of fields")
    return {str(k): v for k, v in raw.items()}


def parse_events(raw, where: str) -> list[dict]:
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        if not isinstance(item, dict) or "type" not in item:
            raise StateError(f"{where}: each event has a `type` (mute_changed, volume_changed, ...)")
    return items


def parse_requires(raw, where: str) -> dict:
    if raw is None:
        return {}
    if not isinstance(raw, dict) or set(raw) - REQUIRE_KEYS:
        raise StateError(f"{where}: `requires` takes {', '.join(sorted(REQUIRE_KEYS))}")
    return raw


def _same(want, got) -> bool:
    if isinstance(want, bool) or isinstance(got, bool) or isinstance(want, str):
        return want == got
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return abs(want - got) <= TOLERANCE
    return want == got


def read_state(mcp, key: str) -> dict:
    """The fields of one `state` key, from AbletonMCP's reads."""
    m = STATE_KEY.match(key)
    if m[1] is None:
        return mcp.read("get_session_info")
    if m[2] is None:
        return mcp.read("get_track_info", track_index=int(m[1]) - 1)
    answer = mcp.read("get_device_parameters", track_index=int(m[1]) - 1, device_index=int(m[2]) - 1)
    return {p["name"]: p["value"] for p in answer["device"]["parameters"]}


def check_state(mcp, state: dict) -> list[dict]:
    results = []
    for key, fields in state.items():
        command = "get_session_info" if key == "song" else (
            "get_device_parameters" if "device" in key else "get_track_info")
        try:
            got = read_state(mcp, key)
        except Exception as e:  # noqa: BLE001  any read failure is this expectation's result
            results.append({"state": key, "ok": False, "got": f"read failed: {e}", "command": command})
            continue
        for name, want in fields.items():
            have = got.get(name, "(no such field)")
            results.append({"state": f"{key} {name}", "expected": want, "got": have, "ok": _same(want, have),
                            "command": command, "tested": command in TESTED})
    return results


def check_events(wanted: list[dict], events: list[dict]) -> list[dict]:
    results = []
    def matches(e, want):
        if e.get("type") != want["type"]:
            return False
        if "track" in want and e.get("track_index") != want["track"] - 1:
            return False
        if "clip" in want and e.get("clip_index") != want["clip"] - 1:
            return False
        detail = e.get("detail") or {}
        return all(_same(v, detail.get(k)) for k, v in want.items() if k not in ("type", "track", "clip"))
    for want in wanted:
        found = [e for e in events if matches(e, want)]
        results.append({"event": want, "ok": bool(found), "got": len(found)})
    return results


def check_requires(mcp, requires: dict, log=print) -> list[str]:
    """What the open Set lacks for the check file; missing clips on MIDI tracks are created."""
    if not requires:
        return []
    missing = []
    session = mcp.read("get_session_info")
    if session["track_count"] < requires.get("tracks", 0):
        missing.append(f"{requires['tracks']} tracks (the Set has {session['track_count']})")
    if session["return_track_count"] < requires.get("returns", 0):
        missing.append(f"{requires['returns']} return tracks (the Set has {session['return_track_count']})")
    tracks: dict[int, dict] = {}

    def track(n):
        if n not in tracks:
            tracks[n] = mcp.read("get_track_info", track_index=n - 1)
        return tracks[n]

    for n in requires.get("devices", []):
        if n > session["track_count"] or not track(n)["devices"]:
            missing.append(f"a device on track {n}")
    for c in requires.get("clips", []):
        n, scene = c["track"], c["scene"]
        if n > session["track_count"]:
            missing.append(f"track {n} for a clip in scene {scene}")
            continue
        slots = track(n)["clip_slots"]
        if scene > len(slots):
            missing.append(f"scene {scene} for a clip on track {n}")
        elif not slots[scene - 1]["has_clip"]:
            if track(n)["is_midi_track"]:
                mcp.call("create_clip", track_index=n - 1, clip_index=scene - 1, length=CLIP_LENGTH)
                log(f"created an empty {CLIP_LENGTH:g}-beat clip on track {n}, scene {scene} (not saved)")
            else:
                missing.append(f"a clip on audio track {n}, scene {scene}")
    return missing
