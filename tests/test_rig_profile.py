"""Device profiles and the identity reply (plan 0002 step 4), over in-memory ports (seam C)."""

import threading
import time

import pytest

from ableton_remote_script_mcp.rig.ports import MemoryPort, wait_quiet
from ableton_remote_script_mcp.rig.profile import (
    COLOURS,
    IDENTITY_REQUEST,
    RIG_IDENTITY_BYTES,
    RIG_IDENTITY_REPLY,
    IdentityResponder,
    Led,
    ProfileError,
    RespondingPort,
    load_profile,
)
from ableton_remote_script_mcp.rig.serve import RigServer, ServedPort

pytest.importorskip("yaml")


class WaitingScript:
    """A v3 script with identity_response_id_bytes, as the 12.4.16 framework checks the reply:
    it asks for the identity, and only a reply `F0 7E <device> 06 02 <its bytes> …` makes it send
    its start-up state."""

    def __init__(self, port: MemoryPort, id_bytes):
        self.port, self.id_bytes, self.identified = port, tuple(id_bytes), False
        port._reply = self.receive
        port.receive(list(IDENTITY_REQUEST))  # the request Live sends when the script starts

    def receive(self, message):
        if message[:2] == [0xF0, 0x7E] and message[3:5] == [0x06, 0x02]:
            got = tuple(message[5:5 + len(self.id_bytes)])
            if all(want in (-1, have) for want, have in zip(self.id_bytes, got)):
                self.identified = True
                return [[0xBF, 20, 88]]  # start-up state: fader 1's value
        return []


def _profile(tmp_path, text):
    path = tmp_path / "device.yaml"
    path.write_text(text)
    return load_profile(path)


def test_a_script_waiting_for_identity_starts_only_with_the_reply(tmp_path):
    silent = MemoryPort()
    script = WaitingScript(silent, RIG_IDENTITY_BYTES)
    no_reply = RespondingPort(silent, IdentityResponder(silent, _profile(tmp_path, "identity: {reply: none}")))
    assert [r.message for r in wait_quiet(no_reply, 0.01, 0.1)] == [IDENTITY_REQUEST]
    assert not script.identified and silent.sent == []

    live = MemoryPort()
    script = WaitingScript(live, RIG_IDENTITY_BYTES)
    port = RespondingPort(live, IdentityResponder(live, _profile(tmp_path, "identity: {reply: rig}")))
    got = [r.message for r in wait_quiet(port, 0.01, 0.2)]
    assert live.sent == [RIG_IDENTITY_REPLY] and script.identified
    assert got == [IDENTITY_REQUEST, [0xBF, 20, 88]]


def test_a_reply_for_another_device_does_not_identify(tmp_path):
    live = MemoryPort()
    script = WaitingScript(live, (0x47, 0x4F, 0x00, 0x19))  # a script expecting another manufacturer
    port = RespondingPort(live, IdentityResponder(live, _profile(tmp_path, "identity: {reply: rig}")))
    wait_quiet(port, 0.01, 0.1)
    assert not script.identified


def test_profile_parsing(tmp_path):
    p = _profile(tmp_path, """\
name: Box
identity:
  reply: F0 7E 7F 06 02 47 4F 00 19 00 00 00 00 F7
  request: F0 7E 00 06 01 F7
layout:
  - [faders, crossfader]
display:
  pan_encoders: bipolar
""")
    assert p.reply[:9] == [0xF0, 0x7E, 0x7F, 0x06, 0x02, 0x47, 0x4F, 0x00, 0x19]
    assert p.request == [0xF0, 0x7E, 0x00, 0x06, 0x01, 0xF7]
    assert p.layout == [["faders", "crossfader"]] and p.display == {"pan_encoders": "bipolar"}
    assert _profile(tmp_path, "name: Box\n").reply is None  # no reply by default (Decision 11)
    with pytest.raises(ProfileError, match="SysEx"):
        _profile(tmp_path, "identity: {request: cc 1 2 3}\n")
    with pytest.raises(ProfileError, match="display"):
        _profile(tmp_path, "display: {faders: sideways}\n")
    assert RIG_IDENTITY_REPLY[5] == 0x7D  # the non-commercial manufacturer ID, never a real one


def test_rig_serve_answers_identity_without_a_client(tmp_path):
    midi = MemoryPort()
    script = WaitingScript(midi, RIG_IDENTITY_BYTES)
    port = RespondingPort(midi, IdentityResponder(midi, _profile(tmp_path, "identity: {reply: rig}")))
    server = RigServer(port, ("127.0.0.1", 0))
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    try:
        end = time.monotonic() + 2
        while not script.identified and time.monotonic() < end:
            time.sleep(0.01)
        assert script.identified  # answered by the pump, before any client connected
        client = ServedPort(*server.server_address)
        assert client.hello["identity_reply"].startswith("F0 7E 7F 06 02 7D")
        assert client.hello["identity_answered"] == 1
        client.close()
    finally:
        server.shutdown()
        server.server_close()


def test_led_colours(tmp_path):
    """Decision 26: value -> colour and blinking, per element or matrix; a YAML anchor shares a map."""
    p = _profile(tmp_path, """\
leds:
  steps: &grid {0: off, 1: green, 2: green blink, 5: '#FFAA00'}
  pads: *grid
""")
    assert p.leds["steps"] == {0: Led(None), 1: Led(COLOURS["green"]), 2: Led(COLOURS["green"], True),
                               5: Led("#ffaa00")}
    assert p.leds["pads"] == p.leds["steps"]
    assert _profile(tmp_path, "name: Box\n").leds == {}
    for bad, why in [("{steps: {1: mauve}}", "mauve"), ("{steps: {128: red}}", "0-127"),
                     ("{steps: {1: red fast}}", "blink"), ("{steps: {0: off blink}}", "doesn't blink"),
                     ("{steps: {1: on}}", "name the colour"), ("{steps: {1: }}", "quote"),
                     ("{steps: {'1': red}}", "without quotes"), ("{steps: red}", "value -> colour"), ("[steps]", "names")]:
        with pytest.raises(ProfileError, match=why):
            _profile(tmp_path, f"leds: {bad}\n")
