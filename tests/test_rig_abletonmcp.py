"""The rig's AbletonMCP client and Live-state checks (plan 0002 step 3), over a fake socket (seam C)."""

import json

import pytest

from ableton_remote_script_mcp.rig.abletonmcp import (
    AbletonMCP,
    AbletonMCPError,
    Forbidden,
)
from ableton_remote_script_mcp.rig.checks import load_check_file, run_checks
from ableton_remote_script_mcp.rig.ports import MemoryPort, wait_quiet
from ableton_remote_script_mcp.rig.state import (
    StateError,
    check_events,
    check_requires,
    parse_do,
    to_params,
)

pytest.importorskip("yaml")

INFO = {"name": "AbletonMCP", "script_version": "1.7.1", "protocol_version": 1}


class FakeLive:
    """A socket that answers like AbletonMCP 1.7.1, in chunks, over a small Set."""

    def __init__(self, fail_first=0):
        self.sent: list[dict] = []
        self.out = b""
        self.fail_first = fail_first
        self.tracks = [{"index": i, "name": f"{i + 1}", "mute": False, "solo": False, "arm": False, "volume": 0.5,
                        "panning": 0.0, "is_midi_track": True,
                        "devices": [{"name": "Drum Rack", "type": "drum_machine"}] if i == 0 else [],
                        "clip_slots": [{"index": s, "has_clip": False, "clip": None} for s in range(2)]}
                       for i in range(2)]
        self.notes: dict[tuple[int, int], list[dict]] = {}
        self.looping = True
        self.events = []
        self.macro = 0.0

    def settimeout(self, _):
        pass

    def close(self):
        pass

    def sendall(self, data):
        request = json.loads(data)
        self.sent.append(request)
        self.out += json.dumps(self.answer(request["type"], request["params"])).encode()

    def recv(self, n):
        chunk, self.out = self.out[:7], self.out[7:]  # split answers: the client reads until whole
        return chunk

    def answer(self, command, params):
        if command == "get_script_info":
            return {"status": "success", "result": INFO}
        if self.fail_first:
            self.fail_first -= 1
            return {"status": "error", "message": "Python argument types in None(Song)"}
        if command == "get_session_info":
            return {"status": "success", "result": {"track_count": 2, "return_track_count": 1, "tempo": 120.0,
                                                     "is_playing": False,
                                                     "master_track": {"name": "Master", "volume": 0.85,
                                                                      "panning": 0.0}}}
        if command == "get_track_info":
            return {"status": "success", "result": self.tracks[params["track_index"]]}
        if command == "get_device_parameters":
            return {"status": "success", "result": {"device": {"parameters": [
                {"name": "Device On", "value": 1.0}, {"name": "Macro 1", "value": self.macro}]}}}
        if command == "drain_passive_events":
            events, self.events = self.events, []
            return {"status": "success", "result": {"events": events, "count": len(events)}}
        if command == "create_clip":
            slot = self.tracks[params["track_index"]]["clip_slots"][params["clip_index"]]
            slot["has_clip"], slot["clip"] = True, {"name": "", "length": params["length"], "is_playing": False}
            return {"status": "success", "result": {}}
        if command in ("get_clip_notes", "add_notes_to_clip", "clear_notes_from_clip"):
            t, s = params["track_index"], params["clip_index"]
            if not self.tracks[t]["clip_slots"][s]["has_clip"]:
                return {"status": "error", "message": "No clip in slot"}
            notes = self.notes.setdefault((t, s), [])
            if command == "add_notes_to_clip":
                notes += [{"mute": False, **n} for n in params["notes"]]
            elif command == "clear_notes_from_clip":
                notes.clear()
            clip = self.tracks[t]["clip_slots"][s]["clip"]
            return {"status": "success", "result": {"clip_name": clip["name"], "length": clip["length"],
                                                     "note_count": len(notes), "notes": list(notes)}}
        if command == "get_session_snapshot":
            assert params == {"include_notes": False, "include_params": False}
            self.song_time = getattr(self, "song_time", 0.0) + 1.0
            return {"status": "success", "result": {"session": {"current_song_time": self.song_time}, "tracks": [
                {"clip_slots": [{**slot, "clip": slot["clip"] and {**slot["clip"], "looping": self.looping,
                                                                   "loop_start": 0.0, "loop_end": slot["clip"]["length"]}}
                                for slot in track["clip_slots"]]} for track in self.tracks]}}
        if command == "set_device_parameter":
            self.macro = params["value"]
            return {"status": "success", "result": {}}
        return {"status": "error", "message": f"unknown {command}"}


def test_client_refuses_commands_outside_the_allow_list():
    live = FakeLive()
    mcp = AbletonMCP(sock=live)
    for command in ("rate_last_action", "set_dataset_consent", "get_browser_tree", "load_instrument_or_effect"):
        with pytest.raises(Forbidden):
            mcp.call(command)
    assert {r["type"] for r in live.sent} == {"get_script_info"}  # nothing forbidden reached the socket


def test_the_note_commands_are_allowed_and_tested():
    # plan 0002 Decision 25: reading and setting a clip's notes, for the drum sequencer's checks
    from ableton_remote_script_mcp.rig.abletonmcp import ALLOWED, READS, TESTED, WRITES

    assert "get_clip_notes" in READS
    assert {"add_notes_to_clip", "clear_notes_from_clip"} <= WRITES
    assert parse_do([{"clear_notes_from_clip": {"track": 1, "clip": 1}}], "t") == [
        ("clear_notes_from_clip", {"track_index": 0, "clip_index": 0})]
    notes = [{"pitch": 36, "start_time": 0.0, "duration": 0.25, "velocity": 100}]
    assert parse_do({"add_notes_to_clip": {"track": 2, "clip": 1, "notes": [[36, 0.0, 0.25, 100]]}}, "t") == [
        ("add_notes_to_clip", {"track_index": 1, "clip_index": 0, "notes": notes})]
    assert {"get_clip_notes", "add_notes_to_clip", "clear_notes_from_clip", "get_session_snapshot"} <= set(TESTED)
    assert "delete_clip" not in ALLOWED


def test_reads_repeat_until_two_agree_and_survive_a_first_error():
    live = FakeLive(fail_first=1)
    mcp = AbletonMCP(sock=live)
    assert mcp.read("get_track_info", track_index=0)["volume"] == 0.5
    assert [r["type"] for r in live.sent[2:]] == ["get_track_info"] * 3  # error, answer, same answer
    live.fail_first = 9
    with pytest.raises(AbletonMCPError):
        mcp.read("get_session_info")


def test_params_count_from_one():
    assert to_params({"track": 2, "clip": 1, "value": 64}, "x") == {"track_index": 1, "clip_index": 0, "value": 64}
    with pytest.raises(StateError):
        to_params({"track": 0}, "x")
    with pytest.raises(StateError, match="do"):
        parse_do([{"get_browser_tree": {}}], "x")


def test_requires_creates_missing_clips_and_lists_the_rest():
    live = FakeLive()
    mcp = AbletonMCP(sock=live)
    missing = check_requires(mcp, {"tracks": 3, "returns": 1, "devices": [1, 2], "clips": [{"track": 2, "scene": 1}]},
                             log=lambda *_: None)
    assert missing == ["3 tracks (the Set has 2)", "a device on track 2"]
    assert live.tracks[1]["clip_slots"][0]["has_clip"]
    assert any(r["type"] == "create_clip" and r["params"] == {"track_index": 1, "clip_index": 0, "length": 4.0}
               for r in live.sent)


def test_events_match_by_type_track_and_detail():
    events = [{"type": "mute_changed", "track_index": 0, "clip_index": None, "detail": {"mute": True}}]
    assert check_events([{"type": "mute_changed", "track": 1, "mute": True}], events)[0]["ok"]
    assert not check_events([{"type": "mute_changed", "track": 2}], events)[0]["ok"]


CHECKS = """\
settle: 0.01
requires: {devices: [1]}
steps:
  - id: mute
    send: ["note 13 104 127"]
    state:
      track 1: {mute: true}
    events:
      - {type: mute_changed, track: 1}
  - id: macro
    do:
      - set_device_parameter: {track: 1, device: 1, parameter: 2, value: 64}
    state:
      track 1 device 1: {Macro 1: 64}
"""


def _run(tmp_path, mcp, live):
    path = tmp_path / "checks.yaml"
    path.write_text(CHECKS)

    def reply(message):
        if live is not None and message[1] == 104:
            live.tracks[0]["mute"] = True
            live.events.append({"type": "mute_changed", "track_index": 0, "clip_index": None, "detail": {}})
        return []

    from ableton_remote_script_mcp.rig.controller import Controller
    return run_checks(load_check_file(path), Controller("Box", str(tmp_path)), MemoryPort(reply=reply),
                      quiet_wait=lambda p, q, t, **k: wait_quiet(p, 0.01, 0.1), sleep=lambda _: None,
                      say=lambda *_: None, mcp=mcp, mcp_note="no AbletonMCP on 127.0.0.1:9877")


def test_run_checks_state_events_and_do(tmp_path):
    live = FakeLive()
    result = _run(tmp_path, AbletonMCP(sock=live), live)
    assert {s["id"]: s["verdict"] for s in result["steps"]} == {"mute": "passed", "macro": "passed"}
    assert live.macro == 64
    assert result["steps"][1]["live"][0]["tested"]  # get_device_parameters is on the tested list
    assert result["steps"][1]["untested_commands"] == ["set_device_parameter"]  # a write, not yet seen in Live


def test_without_abletonmcp_do_steps_skip_and_state_is_not_checked(tmp_path):
    result = _run(tmp_path, None, None)
    mute, macro = result["steps"]
    assert mute["verdict"] == "passed" and mute["not_checked"] == ["state track 1", "event mute_changed"]
    assert macro["verdict"] == "skipped" and "needs AbletonMCP" in macro["reasons"][0]


# plan 0002 step 6b (Decision 25, 27): a clip's notes in check files

def _clip(live, track=0, slot=0, name="Drum Seq", length=8.0):
    live.tracks[track]["clip_slots"][slot].update(has_clip=True,
                                                   clip={"name": name, "length": length, "is_playing": False})


def test_add_notes_takes_the_check_files_note_lists():
    assert parse_do({"add_notes_to_clip": {"track": 1, "clip": 1, "notes": [[36, 0, 0.25, 100], [38, 1, 0.25]]}},
                    "t") == [("add_notes_to_clip", {"track_index": 0, "clip_index": 0, "notes": [
                        {"pitch": 36, "start_time": 0, "duration": 0.25, "velocity": 100},
                        {"pitch": 38, "start_time": 1, "duration": 0.25, "velocity": 100}]})]
    with pytest.raises(StateError, match="pitch, start, length"):
        parse_do({"add_notes_to_clip": {"track": 1, "clip": 1, "notes": [[36]]}}, "t")
    with pytest.raises(StateError, match="pitch, start, length"):
        parse_do({"add_notes_to_clip": {"track": 1, "clip": 1, "notes": [{"pitch": 36}]}}, "t")
    from ableton_remote_script_mcp.rig.state import parse_requires
    with pytest.raises(StateError, match="clip and an empty slot"):
        parse_requires({"clips": [{"track": 1, "scene": 1}], "empty_slots": [{"track": 1, "scene": 1}]}, "t")


def test_clip_state_keys_and_fields_are_checked_when_the_file_loads():
    from ableton_remote_script_mcp.rig.state import parse_state

    assert parse_state({"track 1 clip 2": {"notes": [[36, 0, 0.25, 100]], "looping": True}}, "t")
    with pytest.raises(StateError, match="mute"):
        parse_state({"track 1 clip 1": {"mute": True}}, "t")
    with pytest.raises(StateError, match="pitch, start, length"):
        parse_state({"track 1 clip 1": {"notes": [[36, 0]]}}, "t")
    with pytest.raises(StateError, match="clip M"):
        parse_state({"track 1 scene 1": {"name": "x"}}, "t")


def test_clip_state_reads_notes_in_any_order_and_velocity_is_optional():
    from ableton_remote_script_mcp.rig.state import check_state

    live = FakeLive()
    _clip(live)
    live.notes[(0, 0)] = [{"pitch": 38, "start_time": 1.0, "duration": 0.25, "velocity": 90.0, "mute": False},
                          {"pitch": 36, "start_time": 0.0, "duration": 0.25, "velocity": 100.0, "mute": False}]
    mcp = AbletonMCP(sock=live)
    results = check_state(mcp, {"track 1 clip 1": {"notes": [[36, 0, 0.25, 100], [38, 1, 0.25]], "name": "Drum Seq",
                                                   "length": 8, "looping": True}})
    assert [(r["state"], r["ok"], r["command"]) for r in results] == [
        ("track 1 clip 1 notes", True, "get_clip_notes"), ("track 1 clip 1 name", True, "get_track_info"),
        ("track 1 clip 1 length", True, "get_track_info"), ("track 1 clip 1 looping", True, "get_session_snapshot")]
    assert results[0]["got"] == [[36, 0.0, 0.25, 100.0], [38, 1.0, 0.25, 90.0]]
    assert results[0]["tested"] and results[1]["tested"]
    assert sum(r["type"] == "get_session_snapshot" for r in live.sent) == 2  # the song time moved; the loop didn't
    live.looping = False
    bad = check_state(mcp, {"track 1 clip 1": {"notes": [[36, 0, 0.25, 100]], "looping": True}})
    assert [r["ok"] for r in bad] == [False, False]
    live.notes[(0, 0)] = [{"pitch": 36, "start_time": 0.0, "duration": 0.25, "velocity": 100.0, "mute": True}]
    muted, = check_state(mcp, {"track 1 clip 1": {"notes": [[36, 0, 0.25]]}})
    assert not muted["ok"] and muted["got"] == [[36, 0.0, 0.25, 100.0, "muted"]]


def test_a_nested_field_matches_the_fields_it_names_within_the_tolerance():
    from ableton_remote_script_mcp.rig.state import check_state

    mcp = AbletonMCP(sock=FakeLive())
    good, bad = check_state(mcp, {"song": {"master_track": {"volume": 0.852}, "tempo": 120}}), \
        check_state(mcp, {"song": {"master_track": {"volume": 1.0}}})
    assert [(r["state"], r["ok"]) for r in good] == [("song master_track", True), ("song tempo", True)]
    assert not bad[0]["ok"] and bad[0]["got"]["volume"] == 0.85
    missing, = check_state(mcp, {"song": {"master_track": {"mute": False}}})
    assert not missing["ok"]


def test_an_empty_slot_reads_as_no_clip_and_reads_no_notes():
    from ableton_remote_script_mcp.rig.state import check_state

    live = FakeLive()
    mcp = AbletonMCP(sock=live)
    results = check_state(mcp, {"track 1 clip 1": {"has_clip": False}, "track 1 clip 2": {"notes": []}})
    assert [(r["ok"], r["got"]) for r in results] == [(True, False), (False, "(no clip)")]
    assert not any(r["type"] in ("get_clip_notes", "get_session_snapshot") for r in live.sent)


def test_requires_names_a_missing_drum_rack_and_a_filled_slot_and_creates_neither():
    live = FakeLive()
    _clip(live, track=0, slot=1)
    mcp = AbletonMCP(sock=live)
    missing = check_requires(mcp, {"drum_racks": [1, 2], "empty_slots": [{"track": 1, "scene": 1},
                                                                          {"track": 1, "scene": 2}]},
                             log=lambda *_: None)
    assert len(missing) == 2
    assert "Drum Rack on track 2" in missing[0] and "by hand" in missing[0]
    assert "empty slot on track 1, scene 2" in missing[1] and "by hand" in missing[1]
    assert {r["type"] for r in live.sent} <= {"get_script_info", "get_session_info", "get_track_info"}


def test_a_check_file_adds_reads_back_and_clears_notes(tmp_path):
    path = tmp_path / "checks.yaml"
    path.write_text("""\
settle: 0.01
requires: {drum_racks: [1], clips: [{track: 1, scene: 1}]}
steps:
  - id: add
    do:
      - add_notes_to_clip: {track: 1, clip: 1, notes: [[36, 0, 0.25, 100]]}
    state:
      track 1 clip 1: {notes: [[36, 0, 0.25, 100]], looping: true}
  - id: clear
    do:
      - clear_notes_from_clip: {track: 1, clip: 1}
    state:
      track 1 clip 1: {notes: []}
""")
    from ableton_remote_script_mcp.rig.controller import Controller

    live = FakeLive()
    result = run_checks(load_check_file(path), Controller("Box", str(tmp_path)), MemoryPort(reply=lambda m: []),
                        quiet_wait=lambda p, q, t, **k: wait_quiet(p, 0.01, 0.1), sleep=lambda _: None,
                        say=lambda *_: None, mcp=AbletonMCP(sock=live))
    assert {s["id"]: s["verdict"] for s in result["steps"]} == {"add": "passed", "clear": "passed"}
    assert "untested_commands" not in result["steps"][0]
    assert live.notes[(0, 0)] == []


class SelectingLive(FakeLive):
    """The user's fork (plan 0002 Decision 29): `select_clip_slot` and the selection in session info."""

    def __init__(self, capable=True):
        super().__init__()
        self.capable, self.selection = capable, (0, 0)

    def answer(self, command, params):
        if command == "get_script_info":
            return {"status": "success", "result": {**INFO, "capabilities": ["get_session_info"]
                                                    + (["select_clip_slot"] if self.capable else [])}}
        if command == "select_clip_slot":
            track, scene = self.selection
            self.selection = (params.get("track_index", track), params.get("scene_index", scene))
            return {"status": "success", "result": {}}
        answer = super().answer(command, params)
        if command == "get_session_info":
            track, scene = self.selection
            answer["result"].update({"selected_track_index": track, "selected_track_name": "Main" if track is None else f"{track + 1}",
                                     "selected_scene_index": scene})
        return answer


def test_do_selects_a_track_and_scene_counting_from_one():
    assert parse_do({"select_clip_slot": {"track": 9, "scene": 1}}, "t") == [
        ("select_clip_slot", {"track_index": 8, "scene_index": 0})]
    assert parse_do({"select_clip_slot": {"scene": 3}}, "t") == [("select_clip_slot", {"scene_index": 2})]
    with pytest.raises(StateError, match="track.*scene"):
        parse_do({"select_clip_slot": {"clip": 1}}, "t")


def test_the_selection_is_set_and_read_back_counting_from_one():
    from ableton_remote_script_mcp.rig.state import check_state

    live = SelectingLive()
    mcp = AbletonMCP(sock=live)
    mcp.call("select_clip_slot", track_index=1, scene_index=1)
    good = check_state(mcp, {"song": {"selected_track": 2, "selected_scene": 2}})
    assert [(r["state"], r["ok"], r["tested"]) for r in good] == [
        ("song selected_track", True, False), ("song selected_scene", True, False)]  # untested until seen in Live
    live.selection = (None, 0)  # a return track or the master: no index, so its name
    master, = check_state(mcp, {"song": {"selected_track": "Main"}})
    assert master["ok"]


def test_select_needs_an_abletonmcp_that_has_it():
    live = SelectingLive(capable=False)
    mcp = AbletonMCP(sock=live)
    with pytest.raises(AbletonMCPError, match="select_clip_slot"):
        mcp.call("select_clip_slot", track_index=0)
    assert "select_clip_slot" not in {r["type"] for r in live.sent}


def test_a_run_names_the_untested_selection_fields_and_the_write(tmp_path):
    path = tmp_path / "checks.yaml"
    path.write_text("settle: 0.01\nsteps:\n  - id: select\n    do:\n      - select_clip_slot: {track: 2, scene: 1}\n"
                    "    state:\n      song: {selected_track: 2, tempo: 120}\n"
                    "  - id: only-do\n    do:\n      - select_clip_slot: {scene: 2}\n")
    from ableton_remote_script_mcp.rig.controller import Controller
    live = SelectingLive()
    result = run_checks(load_check_file(path), Controller("Box", str(tmp_path)), MemoryPort(reply=lambda m: []),
                        quiet_wait=lambda p, q, t, **k: wait_quiet(p, 0.01, 0.1), sleep=lambda _: None,
                        say=lambda *_: None, mcp=AbletonMCP(sock=live), mcp_note="")
    select, only_do = result["steps"]
    assert select["verdict"] == "passed" and live.selection == (1, 1)
    assert select["untested_commands"] == ["get_session_info selected_track", "select_clip_slot"]
    assert only_do["untested_commands"] == ["select_clip_slot"]


def test_without_the_forks_fields_the_selection_fails_and_says_why():
    from ableton_remote_script_mcp.rig.state import NO_SELECTION, check_state

    row, = check_state(AbletonMCP(sock=FakeLive()), {"song": {"selected_track": 9}})
    assert not row["ok"] and row["got"] == NO_SELECTION
