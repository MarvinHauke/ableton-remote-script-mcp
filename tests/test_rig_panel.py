"""`rig panel` (plan 0002 step 5): the model the page draws, the WebSocket protocol, and the
panel playing through `rig serve` over an in-memory port (seam C)."""

import base64
import io
import json
import os
import socket
import threading
import time

import pytest

from ableton_remote_script_mcp.rig.checks import CheckFileError
from ableton_remote_script_mcp.rig.controller import build_controller
from ableton_remote_script_mcp.rig.panel import (
    NOTICE,
    PanelServer,
    accept_key,
    local_origin,
    midi_event,
    panel_model,
    play,
    ws_frame,
    ws_read,
)
from ableton_remote_script_mcp.rig.ports import MemoryPort
from ableton_remote_script_mcp.rig.profile import Led, Profile, check_profile_names
from ableton_remote_script_mcp.rig.serve import RigServer, ServedPort

ELEMENTS = '''\
from ableton.v3.control_surface import MIDI_NOTE_TYPE, ElementsBase, MapMode


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=12, **k)
        self.add_encoder_matrix([range(40, 42)], "Faders", is_feedback_enabled=True)
        self.add_encoder(60, "Quant_Encoder", map_mode=MapMode.LinearTwoCompliment)
        self.add_button_matrix([[64, 65]], "Pads", msg_type=MIDI_NOTE_TYPE)
        self.add_button(122, "Play_Button", msg_type=MIDI_NOTE_TYPE)
'''


def _entry(method, line):
    return {"defined_by": f"ableton.v3.control_surface.elements_base.ElementsBase.{method}", "line": line,
            "in": "Box.elements.Elements.__init__"}


@pytest.fixture
def ctl(tmp_path):
    folder = tmp_path / "Box"
    folder.mkdir()
    (folder / "__init__.py").write_text("")
    (folder / "elements.py").write_text(ELEMENTS)
    outline = {"script": "Box", "elements": [_entry("add_encoder_matrix", 7), _entry("add_encoder", 8),
                                             _entry("add_button_matrix", 9), _entry("add_button", 10)]}
    return build_controller(outline, folder)


def _rows(model):
    return [[g["name"] for g in row] for row in model["rows"]]


def test_plain_layout_puts_matrices_first_then_buttons_and_encoders(ctl):
    model = panel_model(ctl)
    assert _rows(model) == [["faders"], ["pads"], ["play_button"], ["quant_encoder"]]
    assert model["notice"] == NOTICE and model["profile"] is None
    quant = model["rows"][3][0]["elements"][0]
    assert quant["display"] == "relative" and quant["kind"] == "encoder"
    fader = model["rows"][0][0]["elements"][0]
    assert fader["name"] == "faders[0]" and fader["feedback"] and fader["midi"] == "CC 40, channel 13"


def test_profile_layout_and_hints_and_nothing_left_out(ctl):
    profile = Profile(name="Box", layout=[["pads", "play_button"]], display={"faders": "bipolar"})
    model = panel_model(ctl, profile)
    assert _rows(model) == [["pads", "play_button"], ["faders"], ["quant_encoder"]]
    assert {e["display"] for e in model["rows"][1][0]["elements"]} == {"bipolar"}


def test_led_colours_reach_the_model_and_only_where_the_profile_gives_them(ctl):
    """Decision 26: an optional `leds` field per element; an element's own map wins over its matrix's."""
    grid = {0: Led(None), 1: Led("#2fb344", True)}
    profile = Profile(leds={"pads": grid, "pads[1]": {3: Led("#e5322d")}})
    pads = {e["name"]: e for e in panel_model(ctl, profile)["rows"][1][0]["elements"]}
    assert pads["pads[0]"]["leds"] == {"0": {"colour": None, "blink": False}, "1": {"colour": "#2fb344", "blink": True}}
    assert pads["pads[1]"]["leds"] == {"3": {"colour": "#e5322d", "blink": False}}
    assert all("leds" not in e for row in panel_model(ctl)["rows"] for g in row for e in g["elements"])
    assert all("leds" not in e for g in panel_model(ctl, profile)["rows"][0] for e in g["elements"])  # faders
    json.dumps(panel_model(ctl, profile))  # it goes to the page as JSON


def test_led_maps_name_buttons_the_script_has(ctl):
    profile = Profile(leds={"pads": {1: Led("#2fb344")}, "faders": {1: Led("#2fb344")}, "nope": {1: Led(None)}})
    problems = check_profile_names(profile, ctl)
    assert len(problems) == 2 and "`nope`" in problems[0] and "`faders`" in problems[1]


def test_midi_event_names_the_element_and_its_value(ctl):
    assert midi_event(ctl, [0xBC, 41, 99], "in", None)["elements"] == ["faders[1]"]
    off = midi_event(ctl, [0x8C, 64, 0], "in", None)  # a note off lights the pad off
    assert off["elements"] == ["pads[0]"] and off["value"] == 0
    other = midi_event(ctl, [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7], "in", None)
    assert other["elements"] == [] and other["value"] is None and other["text"].startswith("SysEx")


def test_play_encodes_moves(ctl):
    assert play(ctl, "pads[1]", 127) == [[0x9C, 65, 127]]
    assert play(ctl, "quant_encoder", -1) == [[0xBC, 60, 127]]
    with pytest.raises(CheckFileError, match="did you mean"):
        play(ctl, "pads[9]", 127)
    with pytest.raises(CheckFileError, match="outside 0-127"):
        play(ctl, "faders[0]", 200)


def test_websocket_frames():
    assert accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="  # RFC 6455's example
    text = "x" * 300
    assert ws_read(io.BytesIO(ws_frame(text))) == (0x1, text.encode())
    assert ws_read(io.BytesIO(_masked('{"op": "play"}'))) == (0x1, b'{"op": "play"}')
    assert ws_read(io.BytesIO(b"")) is None


def _masked(text: str, opcode: int = 0x1) -> bytes:
    data, mask = text.encode(), os.urandom(4)
    assert len(data) < 126
    return bytes([0x80 | opcode, 0x80 | len(data)]) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


class _Page:
    """A browser's side of the WebSocket."""

    def __init__(self, address, origin=None):
        self.sock = socket.create_connection(address, timeout=2)
        key = base64.b64encode(os.urandom(16)).decode()
        extra = f"Origin: {origin}\r\n" if origin else ""
        self.sock.sendall((f"GET /ws HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n{extra}\r\n").encode())
        self.file = self.sock.makefile("rb")
        head = b""
        while not head.endswith(b"\r\n\r\n"):
            head += self.file.read(1)
        assert b" 101 " in head.split(b"\r\n")[0] and accept_key(key).encode() in head

    def next(self, want=lambda e: True, seconds=2.0):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            event = json.loads(ws_read(self.file)[1])
            if want(event):
                return event
        raise AssertionError("no such event")

    def play(self, element, value):
        self.sock.sendall(_masked(json.dumps({"op": "play", "element": element, "value": value})))

    def close(self):
        self.sock.sendall(bytes([0x88, 0x80]) + b"\0\0\0\0")
        self.sock.close()


def live(message):
    """Live echoes a fader as a script with feedback does."""
    return [list(message)] if message[0] == 0xBC and message[1] in (40, 41) else []


@pytest.fixture
def rig(ctl):
    midi = MemoryPort(reply=live)
    serve = RigServer(midi, ("127.0.0.1", 0))
    threading.Thread(target=serve.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    panel = PanelServer(ctl, ServedPort(*serve.server_address), address=("127.0.0.1", 0))
    threading.Thread(target=panel.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield midi, serve, panel
    for s in (panel, serve):
        s.shutdown()
        s.server_close()


def test_page_plays_through_rig_serve_and_sees_live_and_the_driver(rig):
    midi, serve, panel = rig
    page = _Page(panel.server_address)
    model = page.next()
    assert model["type"] == "model" and model["script"] == "Box" and model["protocol"] == 1
    page.play("faders[0]", 90)
    out = page.next(lambda e: e.get("dir") == "out")
    assert out["by"] == "panel" and out["elements"] == ["faders[0]"] and out["value"] == 90
    back = page.next(lambda e: e.get("dir") == "in")
    assert back["elements"] == ["faders[0]"] and back["value"] == 90
    assert midi.sent == [[0xBC, 40, 90]]

    driver = ServedPort(*serve.server_address)  # what `rig run` plays shows up on the page
    driver.send([0x9C, 122, 127])
    seen = page.next(lambda e: e.get("by") == "driver")
    assert seen["elements"] == ["play_button"] and seen["value"] == 127
    driver.close()

    late = _Page(panel.server_address)  # a page opened later sees the values so far
    late.next()
    replayed = {(e["elements"][0], e["dir"]): e["value"] for e in [late.next(), late.next(), late.next()]}
    assert replayed == {("faders[0]", "out"): 90, ("faders[0]", "in"): 90, ("play_button", "out"): 127}
    late.close()

    page.sock.sendall(_masked(json.dumps({"op": "send", "message": [0xBC, 41, 33]})))
    raw = page.next(lambda e: e.get("dir") == "out" and e["message"] == [0xBC, 41, 33])
    assert raw["by"] == "panel" and raw["elements"] == ["faders[1]"]
    page.sock.sendall(_masked(json.dumps({"op": "send", "message": [300]})))
    assert "not a MIDI message" in page.next(lambda e: e["type"] == "error")["text"]

    page.play("nothing", 1)
    assert "no element `nothing`" in page.next(lambda e: e["type"] == "error")["text"]
    page.close()


def test_page_is_served(rig):
    _, _, panel = rig
    with socket.create_connection(panel.server_address, timeout=2) as s:
        s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        body = b""
        while chunk := s.recv(65536):
            body += chunk
    assert b"200 OK" in body.split(b"\r\n")[0] and b"<title>Test Rig Panel</title>" in body


def _serve(midi):
    server = RigServer(midi, ("127.0.0.1", 0))
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    return server


def test_panel_reconnects_when_rig_serve_is_restarted(ctl):
    first = _serve(MemoryPort(reply=live))
    second_midi = MemoryPort(reply=live)
    second: list = []

    def reconnect():
        if not second:
            second.append(_serve(second_midi))
        return ServedPort(*second[0].server_address)

    panel = PanelServer(ctl, ServedPort(*first.server_address), address=("127.0.0.1", 0), reconnect=reconnect,
                        retry=0.05)
    threading.Thread(target=panel.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    try:
        page = _Page(panel.server_address)
        page.next()
        first.shutdown()
        first.server_close()
        panel.port._sock.shutdown(socket.SHUT_RDWR)  # as when the `rig serve` process ends
        assert "lost `rig serve`" in page.next(lambda e: e["type"] == "error", seconds=5)["text"]
        assert page.next(lambda e: e["type"] == "status", seconds=5)["text"].startswith("connected to `rig serve`")
        page.play("faders[1]", 70)
        assert page.next(lambda e: e.get("dir") == "in")["value"] == 70
        assert second_midi.sent == [[0xBC, 41, 70]]
        page.close()
    finally:
        panel.shutdown()
        panel.server_close()
        for s in second:
            s.shutdown()
            s.server_close()


def test_only_pages_from_this_machine_may_connect(rig):
    assert local_origin(None) and local_origin("http://localhost:5173") and local_origin("http://127.0.0.1:9879")
    assert local_origin("http://[::1]:5173") and local_origin("http://uc4.localhost:5173")
    assert not local_origin("https://example.com") and not local_origin("http://localhost.example.com")
    _, _, panel = rig
    assert _Page(panel.server_address, origin="http://localhost:5173").next()["type"] == "model"
    with pytest.raises(AssertionError):
        _Page(panel.server_address, origin="https://example.com")
