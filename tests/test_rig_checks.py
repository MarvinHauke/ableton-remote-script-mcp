"""The rig's controller model, check files, `rig run` and `rig serve` (plan 0002 step 2), over an
in-memory port that plays a scripted Live (seam C)."""

import textwrap
import time

import pytest

from ableton_remote_script_mcp.rig.checks import (
    CheckFileError,
    LogWatch,
    check_names,
    encode,
    load_check_file,
    run_checks,
)
from ableton_remote_script_mcp.rig.controller import build_controller
from ableton_remote_script_mcp.rig.ports import MemoryPort, wait_quiet
from ableton_remote_script_mcp.rig.serve import RigServer, ServedPort

pytest.importorskip("yaml")

ELEMENTS = '''\
from ableton.v3.control_surface import MIDI_NOTE_TYPE, ElementsBase, MapMode
from .constants import CH2

CH = 12
FEEDBACK = {"is_feedback_enabled": True}


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=CH, **k)
        self.add_encoder_matrix([range(40, 44)], "Faders", **FEEDBACK)
        self.add_encoder(48, "Crossfader", channel=CH2, **FEEDBACK)
        self.add_encoder(60, "Quant_Encoder", map_mode=MapMode.LinearTwoCompliment)
        self.add_button_matrix([[64, 65], [66, 67]], "Pads", msg_type=MIDI_NOTE_TYPE)
        self.add_button(122, "Play_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(7, name_of_button(), msg_type=MIDI_NOTE_TYPE)
'''
LINES = {"faders": 11, "crossfader": 12, "quant": 13, "pads": 14, "play": 15, "computed": 16}


def _entry(method, line):
    return {"defined_by": f"ableton.v3.control_surface.elements_base.ElementsBase.{method}", "line": line,
            "in": "Box.elements.Elements.__init__"}


@pytest.fixture
def controller(tmp_path):
    folder = tmp_path / "Box"
    folder.mkdir()
    (folder / "__init__.py").write_text("")
    (folder / "constants.py").write_text("CH2 = 13\n")
    (folder / "elements.py").write_text(ELEMENTS)
    outline = {"script": "Box", "elements": [
        _entry("add_encoder_matrix", LINES["faders"]), _entry("add_encoder", LINES["crossfader"]),
        _entry("add_encoder", LINES["quant"]), _entry("add_button_matrix", LINES["pads"]),
        _entry("add_button", LINES["play"]), _entry("add_button", LINES["computed"])]}
    return build_controller(outline, folder)


def test_controller_model_reads_the_elements_calls(controller):
    c = controller
    assert c.element("faders[0]").key == (0xBC, 40) and c.element("faders[3]").key == (0xBC, 43)
    assert c.element("faders[0]").feedback and c.element("faders[0]").kind == "encoder"
    assert c.element("crossfader").key == (0xBD, 48)  # channel from the imported constant
    assert c.element("quant_encoder").relative
    assert [c.element(n).identifier for n in c.matrices["pads"]] == [64, 65, 66, 67]  # row by row
    assert c.element("play_button").key == (0x9C, 122)
    assert len(c.unresolved) == 1 and "name_of_button()" in c.unresolved[0]["reason"]
    with pytest.raises(KeyError, match="did you mean"):
        c.element("faders[9]")


def test_encode_press_relative_and_range(controller):
    assert encode(controller.element("play_button"), "press") == [[0x9C, 122, 127], [0x9C, 122, 0]]
    assert encode(controller.element("quant_encoder"), 1) == [[0xBC, 60, 1]]
    assert encode(controller.element("quant_encoder"), -1) == [[0xBC, 60, 127]]
    with pytest.raises(CheckFileError):
        encode(controller.element("faders[0]"), 200)


def _write(tmp_path, text):
    path = tmp_path / "checks.yaml"
    path.write_text(textwrap.dedent(text))
    return path


def test_check_file_errors(tmp_path):
    with pytest.raises(CheckFileError, match="unknown key"):
        load_check_file(_write(tmp_path, "steps:\n  - id: a\n    sned: {x: 1}\n"))
    with pytest.raises(CheckFileError, match="no earlier step"):
        load_check_file(_write(tmp_path, "steps:\n  - id: a\n    ask_user: ok?\n    depends_on: b\n"))
    with pytest.raises(CheckFileError, match="used twice"):
        load_check_file(_write(tmp_path, "steps:\n  - id: a\n    ask_user: x\n  - id: a\n    ask_user: y\n"))


def test_check_names_lists_unknown_elements(tmp_path, controller):
    checks = load_check_file(_write(tmp_path, """\
        steps:
          - id: a
            send:
              fader[0]: 1
    """))
    assert check_names(checks, controller) == ["step a: no element `fader[0]` in Box"]


def live(message):
    """A scripted Live: faders send their value back, except fader 2; the play button's LED
    follows the press; quant answers nothing."""
    status, number, value = message
    if status == 0xBC and number in (40, 41, 43):
        return [[status, number, 100], [status, number, value]]  # an older value first: only the last counts
    if status == 0x9C and number == 122 and value:
        return [[0x9C, 122, 127]]
    return []


def _run(tmp_path, controller, text, log=None, port=None):
    checks = load_check_file(_write(tmp_path, text))
    assert not check_names(checks, controller)
    port = port or MemoryPort(reply=live)
    return run_checks(checks, controller, port, log, quiet_wait=lambda p, q, t, **k: wait_quiet(p, 0.01, 0.2),
                      sleep=lambda _: None, say=lambda *_: None), port


FILE = """\
    settle: 0.01
    steps:
      - id: fader-1
        description: fader 1 comes back
        send:
          faders[0]: 90
        expect:
          faders[0]: 90
      - id: fader-3
        send:
          faders[2]: 90
        expect:
          faders[2]: 90
      - id: after-fader-3
        depends_on: fader-3
        send:
          faders[3]: 10
        expect:
          faders[3]: 10
      - id: play
        send:
          play_button: press
        expect:
          play_button: 127
          quant_encoder: none
      - id: box
        depends_on: play
        ask_user: Is there a box around tracks 1-4?
"""


def test_run_verdicts_skips_and_questions(tmp_path, controller):
    result, port = _run(tmp_path, controller, FILE)
    verdicts = {s["id"]: s["verdict"] for s in result["steps"]}
    assert verdicts == {"fader-1": "passed", "fader-3": "failed", "after-fader-3": "skipped", "play": "passed",
                        "box": "ask_user"}
    assert result["counts"] == {"passed": 2, "failed": 1, "skipped": 1, "ask_user": 1}
    failed = result["steps"][1]
    assert failed["reasons"] == ["faders[2]: expected 90, no reply"]
    assert failed["sent"] == ["CC 42 = 90, channel 13"]
    assert [0xBC, 43, 10] not in port.sent  # the skipped step sent nothing
    assert port.sent[-2:] == [[0x9C, 122, 127], [0x9C, 122, 0]]


def test_log_clean_fails_on_a_new_traceback(tmp_path, controller):
    log = tmp_path / "Log.txt"
    log.write_text("2026-11-18T10:00:00.000000: info: Started: Live 12.4.16\n"
                   "2026-11-18T10:00:01.000000: error: RemoteScriptError: Traceback (most recent call last):\n\n"
                   '2026-11-18T10:00:01.000001: error: RemoteScriptError:   File "Remote Scripts/Box/x.py", line 1\n\n'
                   "2026-11-18T10:00:01.000002: error: RemoteScriptError: ValueError: old\n\n")

    def breaking(message):
        if message[1] == 41:
            with log.open("a") as f:
                f.write("2026-11-18T10:00:05.000000: error: RemoteScriptError: Traceback (most recent call last):\n\n"
                        '2026-11-18T10:00:05.000001: error: RemoteScriptError:   File "Remote Scripts/Box/c.py", '
                        "line 9, in f\n\n"
                        "2026-11-18T10:00:05.000002: error: RemoteScriptError: ArgumentError: float\n\n")
        return live(message)

    result, _ = _run(tmp_path, controller, """\
        settle: 0.01
        steps:
          - id: clean
            send:
              faders[0]: 1
            log: clean
          - id: breaks
            send:
              faders[1]: 1
            log: clean
    """, log=LogWatch(log, "Box"), port=MemoryPort(reply=breaking))
    clean, breaks = result["steps"]
    assert clean["verdict"] == "passed"  # the old traceback was there before the step
    assert breaks["verdict"] == "failed" and "ArgumentError: float" in breaks["reasons"][0]


def test_served_port_relays_both_ways(controller):
    midi = MemoryPort(reply=live)
    server = RigServer(midi, ("127.0.0.1", 0))
    import threading

    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    try:
        client = ServedPort(*server.server_address)
        assert client.name == midi.name and client.hello["received"] == 0
        client.send([0xBC, 40, 90])
        got = []
        end = time.monotonic() + 2
        while len(got) < 2 and time.monotonic() < end:
            got += client.drain()
            time.sleep(0.01)
        assert [r.message for r in got] == [[0xBC, 40, 100], [0xBC, 40, 90]]
        assert midi.sent == [[0xBC, 40, 90]]
        with pytest.raises(ConnectionError, match="not a MIDI message"):
            client._ask({"op": "send", "messages": [[300]]})
        client.close()
    finally:
        server.shutdown()
        server.server_close()
