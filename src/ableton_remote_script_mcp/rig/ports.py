"""MIDI ports for the test rig (plan 0002 Decision 7).

The rig opens a pair of virtual CoreMIDI ports with one name (default `ARS Test Rig`): Live
lists it as an input (what the rig sends) and as an output (what the rig receives). The user
picks that name as a Control Surface's input and output (Decision 1); the rig never opens the
user's hardware ports. `rtmidi2` is imported only here, so the rest of the package works without
the `rig` extra; tests use `MemoryPort`.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

DEFAULT_NAME = "ARS Test Rig"
INSTALL_HINT = "the test rig needs the `rig` extra: `uv sync --extra rig` (or `pip install 'ableton-remote-script-mcp[rig]'`)"


class RigUnavailable(RuntimeError):
    pass


class RigExtraMissing(ImportError):
    """PyYAML, which the rig's check files and device profiles need, isn't installed: the CLI
    exits 3 (plan 0001 Decision 61). Any other import error is a bug and exits 5."""


def load_yaml():
    """The `yaml` module, or `RigExtraMissing` with the install hint."""
    try:
        import yaml
    except ModuleNotFoundError as e:
        if e.name != "yaml":
            raise
        raise RigExtraMissing(f"PyYAML is missing: {INSTALL_HINT}") from e
    return yaml


def _rtmidi2():
    try:
        import rtmidi2
    except ImportError as e:  # pragma: no cover - depends on the environment
        raise RigUnavailable(INSTALL_HINT) from e
    return rtmidi2


def list_ports() -> dict[str, list[str]]:
    """The MIDI ports the system shows now, as Live would see them."""
    rt = _rtmidi2()
    return {"inputs": list(rt.get_in_ports()), "outputs": list(rt.get_out_ports())}


@dataclass
class Received:
    time: float  # seconds since the port opened
    message: list[int]


@dataclass
class _Inbox:
    start: float = field(default_factory=time.monotonic)
    items: list[Received] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def put(self, message) -> None:
        with self.lock:
            self.items.append(Received(time.monotonic() - self.start, list(message)))

    def drain(self) -> list[Received]:
        with self.lock:
            items, self.items = self.items, []
        return items


class VirtualPort:
    """The rig's virtual port pair. `send` goes to Live; `drain` returns what Live sent."""

    def __init__(self, name: str = DEFAULT_NAME):
        rt = _rtmidi2()
        self.name = name
        self._inbox = _Inbox()
        self._out = rt.MidiOut()
        self._out.open_virtual_port(name)
        self._in = rt.MidiIn()
        self._in.ignore_types(midi_sysex=False, midi_time=True, midi_sense=True)
        self._in.callback = lambda message, _t: self._inbox.put(message)
        self._in.open_virtual_port(name)

    def send(self, message: list[int]) -> None:
        self._out.send_raw(*message)

    def drain(self) -> list[Received]:
        return self._inbox.drain()

    def close(self) -> None:
        self._in.close_port()
        self._out.close_port()


class MemoryPort:
    """A port for tests: `reply` decides what "Live" answers to each message sent."""

    def __init__(self, name: str = DEFAULT_NAME, reply=None):
        self.name = name
        self.sent: list[list[int]] = []
        self._inbox = _Inbox()
        self._reply = reply

    def receive(self, message: list[int]) -> None:
        """Something Live sends on its own (an LED it lights at start)."""
        self._inbox.put(message)

    def send(self, message: list[int]) -> None:
        self.sent.append(list(message))
        for answer in (self._reply(message) if self._reply else []) or []:
            self._inbox.put(answer)

    def drain(self) -> list[Received]:
        return self._inbox.drain()

    def close(self) -> None:
        pass


def wait_for(port, seconds: float, until_any: bool = False, quiet: float | None = None,
             sleep=time.sleep, clock=time.monotonic) -> list[Received]:
    """Collect what arrives for up to `seconds`; stop at the first message (`until_any`) or after
    `quiet` seconds without one once something arrived."""
    got: list[Received] = []
    end = clock() + seconds
    last = None
    while clock() < end:
        new = port.drain()
        if new:
            got += new
            last = clock()
            if until_any:
                break
        elif quiet is not None and last is not None and clock() - last >= quiet:
            break
        sleep(0.01)
    return got + port.drain()


def wait_quiet(port, quiet: float, limit: float, sleep=time.sleep, clock=time.monotonic,
               at_least: float = 0.0) -> list[Received]:
    """Collect until nothing has arrived for `quiet` seconds (counted from the start too), but
    not before `at_least` seconds, or until `limit` seconds have passed."""
    got: list[Received] = []
    start = last = clock()
    while clock() - start < limit:
        new = port.drain()
        if new:
            got += new
            last = clock()
        elif clock() - last >= quiet and clock() - start >= at_least:
            break
        sleep(0.005)
    return got + port.drain()


def describe(message: list[int]) -> str:
    """`CC 40 = 100, channel 13` style text (channels counted from 1, as controllers show them)."""
    if not message:
        return "(empty)"
    status = message[0]
    if status == 0xF0:
        return "SysEx " + " ".join(f"{b:02X}" for b in message)
    kind, channel = status & 0xF0, (status & 0x0F) + 1
    data = message[1:]
    names = {0x80: "note off", 0x90: "note", 0xA0: "poly pressure", 0xB0: "CC", 0xC0: "program",
             0xD0: "pressure", 0xE0: "pitch bend"}
    name = names.get(kind, f"status {status:02X}")
    if kind in (0x80, 0x90, 0xA0, 0xB0) and len(data) >= 2:
        return f"{name} {data[0]} = {data[1]}, channel {channel}"
    return f"{name} {' '.join(map(str, data))}, channel {channel}"


def parse_message(text: str) -> list[int]:
    """`cc 13 40 100` or `note 13 64 127` (channel 1-16, as controllers show it), or raw hex bytes
    (`BC 28 64`)."""
    parts = text.replace(",", " ").split()
    if not parts:
        raise ValueError("empty message")
    kind = parts[0].lower()
    if kind in ("cc", "note", "noteoff"):
        if len(parts) != 4:
            raise ValueError(f"`{text}`: write `{kind} <channel 1-16> <number> <value>`")
        channel, number, value = (int(p) for p in parts[1:])
        if not (1 <= channel <= 16 and 0 <= number <= 127 and 0 <= value <= 127):
            raise ValueError(f"`{text}`: channel 1-16, number and value 0-127")
        status = {"cc": 0xB0, "note": 0x90, "noteoff": 0x80}[kind] | (channel - 1)
        return [status, number, value]
    try:
        return [int(p, 16) for p in parts]
    except ValueError as e:
        raise ValueError(f"`{text}`: write `cc|note|noteoff <channel> <number> <value>` or hex bytes") from e
