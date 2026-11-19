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
      drum_racks: [1]                  # a Drum Rack directly on these tracks (named if missing, never loaded)
      empty_slots: [{track: 1, scene: 2}]  # no clip there (named if one is, never deleted)
    steps:
      - id: mute-1
        send: {active_buttons[0]: press}
        state:
          track 1: {mute: true}               # get_track_info: mute, solo, arm, volume, panning, name
          song: {is_playing: false}           # get_session_info: tempo, is_playing, ...
          track 2 device 1: {Macro 1: 64}     # get_device_parameters, by parameter name
          track 1 clip 1:                     # the clip in scene 1's slot (step 6b, Decisions 25, 27)
            notes: [[36, 0, 0.25, 100]]       # pitch, start, length[, velocity]; in any order
            name: Drum Seq                    # also length, has_clip (get_track_info)
            looping: true                     # also loop_start, loop_end (get_session_snapshot)
        events:
          - {type: mute_changed, track: 1}    # one of AbletonMCP's listener events during the step
      - id: macro-to-encoder
        do:
          - set_device_parameter: {track: 2, device: 1, parameter: 2, value: 64}
          - add_notes_to_clip: {track: 1, clip: 1, notes: [[38, 1, 0.25, 100]]}
        expect: {rack_encoders[0]: 64}

A number matches within `TOLERANCE`; `true`, `false` and text match exactly.
"""

from __future__ import annotations

import re

from .abletonmcp import TESTED, WRITES

TOLERANCE = 0.005
ONE_BASED = {"track": "track_index", "clip": "clip_index", "scene": "clip_index", "device": "device_index",
             "parameter": "parameter_index"}
STATE_KEY = re.compile(r"^(?:song|track (\d+)(?: (device|clip) (\d+))?)$")
STATE_KEYS = "`song`, `track N`, `track N device M` or `track N clip M`"
TRACK_CLIP_FIELDS = {"has_clip", "name", "length"}  # get_track_info's clip slots
SNAPSHOT_CLIP_FIELDS = {"looping", "loop_start", "loop_end"}  # get_session_snapshot (Decision 27)
CLIP_FIELDS = TRACK_CLIP_FIELDS | SNAPSHOT_CLIP_FIELDS | {"notes"}
NO_CLIP = "(no clip)"
DEFAULT_VELOCITY = 100  # AbletonMCP's own default for a note without one
REQUIRE_KEYS = {"tracks", "returns", "devices", "clips", "drum_racks", "empty_slots"}
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
        params = to_params(params or {}, where)
        if command == "add_notes_to_clip":
            notes = params.get("notes")
            if not isinstance(notes, list) or not notes:
                raise StateError(f"{where}: add_notes_to_clip takes `notes`, a list of [pitch, start, length, velocity]")
            params["notes"] = [_live_note(n, where) for n in notes]
        out.append((command, params))
    return out


def _note(raw, where: str) -> list:
    """A check file's note: [pitch, start, length] or [pitch, start, length, velocity]."""
    if (not isinstance(raw, list) or len(raw) not in (3, 4)
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in raw)):
        raise StateError(f"{where}: a note is [pitch, start, length] or [pitch, start, length, velocity], "
                         f"in beats; not {raw!r}")
    return raw


def _live_note(raw, where: str) -> dict:
    pitch, start, length, *velocity = _note(raw, where)
    return {"pitch": pitch, "start_time": start, "duration": length,
            "velocity": velocity[0] if velocity else DEFAULT_VELOCITY}


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
        raise StateError(f"{where}: `state` maps {STATE_KEYS} to fields")
    for key, fields in raw.items():
        m = STATE_KEY.match(str(key))
        if not m or not isinstance(fields, dict):
            raise StateError(f"{where}: `state` key `{key}`: use {STATE_KEYS} with a mapping of fields")
        if m[2] == "clip":
            unknown = sorted(set(fields) - CLIP_FIELDS)
            if unknown:
                raise StateError(f"{where}: `{key}` has no field {', '.join(unknown)}; a clip has "
                                 f"{', '.join(sorted(CLIP_FIELDS))}")
            if "notes" in fields:
                if not isinstance(fields["notes"], list):
                    raise StateError(f"{where}: `{key}` notes is a list of [pitch, start, length, velocity]")
                for n in fields["notes"]:
                    _note(n, f"{where}: `{key}`")
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
    def slots(key):
        return {(c.get("track"), c.get("scene")) for c in raw.get(key, []) if isinstance(c, dict)}
    both = sorted(slots("clips") & slots("empty_slots"))
    if both:
        raise StateError(f"{where}: `requires` asks for a clip and an empty slot at track {both[0][0]}, "
                         f"scene {both[0][1]}")
    return raw


def _same_notes(want: list, got) -> bool:
    """The same notes in any order; a wanted note without velocity matches any velocity, and a
    muted note in the clip (shown with `muted` after it) matches none."""
    if not isinstance(got, list) or len(want) != len(got):
        return False
    order = lambda n: (round(n[1], 3), n[0])
    return all("muted" not in g and all(_same(a, b) for a, b in zip(w, g))
               for w, g in zip(sorted(want, key=order), sorted(got, key=order)))


def _same(want, got) -> bool:
    if isinstance(want, bool) or isinstance(got, bool) or isinstance(want, str):
        return want == got
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return abs(want - got) <= TOLERANCE
    return want == got


def field_command(key: str, name: str) -> str:
    """The AbletonMCP read a `state` field comes from."""
    m = STATE_KEY.match(key)
    if m[1] is None:
        return "get_session_info"
    if m[2] == "device":
        return "get_device_parameters"
    if m[2] == "clip" and name == "notes":
        return "get_clip_notes"
    if m[2] == "clip" and name in SNAPSHOT_CLIP_FIELDS:
        return "get_session_snapshot"
    return "get_track_info"


def read_clip(mcp, track: int, slot: int, names) -> dict:
    """A clip slot's fields (counting from 1); only the reads `names` need. An empty slot has
    `has_clip: false` and nothing else."""
    slots = mcp.read("get_track_info", track_index=track - 1)["clip_slots"]
    if slot > len(slots):
        raise StateError(f"track {track} has {len(slots)} clip slots")
    if not slots[slot - 1]["has_clip"]:
        return {"has_clip": False}
    clip = slots[slot - 1].get("clip") or {}
    got = {"has_clip": True, "name": clip.get("name"), "length": clip.get("length")}
    if "notes" in names:
        answer = mcp.read("get_clip_notes", track_index=track - 1, clip_index=slot - 1)
        got["notes"] = sorted(([n["pitch"], n["start_time"], n["duration"], n["velocity"]]
                               + (["muted"] if n.get("mute") else []) for n in answer["notes"]),
                              key=lambda n: (n[1], n[0]))
    if SNAPSHOT_CLIP_FIELDS & set(names):
        def loop(snapshot):
            clip = snapshot["tracks"][track - 1]["clip_slots"][slot - 1].get("clip") or {}
            return {f: clip.get(f) for f in SNAPSHOT_CLIP_FIELDS}
        got.update(mcp.read("get_session_snapshot", project=loop, include_notes=False, include_params=False))
    return got


def read_state(mcp, key: str, names=()) -> dict:
    """The fields of one `state` key, from AbletonMCP's reads."""
    m = STATE_KEY.match(key)
    if m[1] is None:
        return mcp.read("get_session_info")
    if m[2] is None:
        return mcp.read("get_track_info", track_index=int(m[1]) - 1)
    if m[2] == "clip":
        return read_clip(mcp, int(m[1]), int(m[3]), names)
    answer = mcp.read("get_device_parameters", track_index=int(m[1]) - 1, device_index=int(m[3]) - 1)
    return {p["name"]: p["value"] for p in answer["device"]["parameters"]}


def check_state(mcp, state: dict) -> list[dict]:
    results = []
    for key, fields in state.items():
        try:
            got = read_state(mcp, key, set(fields))
        except Exception as e:  # noqa: BLE001  any read failure is this expectation's result
            results.append({"state": key, "ok": False, "got": f"read failed: {e}",
                            "command": field_command(key, next(iter(fields), ""))})
            continue
        empty_slot = got.get("has_clip") is False and " clip " in key
        for name, want in fields.items():
            command = field_command(key, name)
            have = got.get(name, NO_CLIP if empty_slot else "(no such field)")
            ok = _same_notes(want, have) if name == "notes" and " clip " in key else _same(want, have)
            results.append({"state": f"{key} {name}", "expected": want, "got": have, "ok": ok,
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
    for n in requires.get("drum_racks", []):
        if n > session["track_count"] or not any(d.get("type") == "drum_machine" for d in track(n)["devices"]):
            missing.append(f"a Drum Rack on track {n} (add one by hand; the rig never loads devices)")
    for c in requires.get("empty_slots", []):
        n, scene = c["track"], c["scene"]
        if n > session["track_count"]:
            missing.append(f"track {n} for an empty slot in scene {scene}")
        elif scene > len(track(n)["clip_slots"]):
            missing.append(f"scene {scene} for an empty slot on track {n}")
        elif track(n)["clip_slots"][scene - 1]["has_clip"]:
            missing.append(f"an empty slot on track {n}, scene {scene} (delete its clip by hand; "
                           "the rig never deletes clips)")
    return missing
