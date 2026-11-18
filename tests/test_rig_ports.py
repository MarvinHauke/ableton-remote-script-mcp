"""The test rig's port layer and `rig probe` (plan 0002 step 1), over an in-memory port."""

import pytest

from ableton_remote_script_mcp.rig.ports import (
    MemoryPort,
    describe,
    parse_message,
    wait_for,
)
from ableton_remote_script_mcp.rig.probe import probe


def test_parse_and_describe_messages():
    assert parse_message("cc 13 40 100") == [0xBC, 40, 100]
    assert parse_message("note 14 123 127") == [0x9D, 123, 127]
    assert parse_message("BC 28 64") == [0xBC, 0x28, 0x64]
    assert describe([0xBC, 40, 100]) == "CC 40 = 100, channel 13"
    with pytest.raises(ValueError):
        parse_message("cc 17 40 100")


def test_probe_waits_for_live_then_reports_the_echo():
    def live(message):  # the script sends the parameter's value back (is_feedback_enabled)
        return [[message[0], message[1], 99]] if message[0] & 0xF0 == 0xB0 else []

    port = MemoryPort(reply=live)
    port.receive([0x9C, 64, 0])  # an LED the script turns off when it starts
    result = probe(port, 5, [0xBC, 40, 100], log=lambda *_: None)
    assert result["connected"] and port.sent == [[0xBC, 40, 100]]
    assert result["first"] == ["note 64 = 0, channel 13"]
    assert result["echo"] == ["CC 40 = 99, channel 13"]


def test_probe_says_when_live_never_connects():
    clock = iter(range(1000)).__next__
    port = MemoryPort()

    def wait(p, seconds, **k):
        return wait_for(p, seconds, sleep=lambda _: None, clock=clock, **k)

    result = probe(port, 3, [0xBC, 40, 100], wait=wait, log=lambda *_: None)
    assert result == {"connected": False, "port": "ARS Test Rig", "first": [], "sent": None, "replies": []}
    assert port.sent == []
