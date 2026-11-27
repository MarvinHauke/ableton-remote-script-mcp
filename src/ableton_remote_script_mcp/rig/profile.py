"""Device profiles (plan 0002 Decisions 10, 11): `device.yaml` beside a check file tells the rig
how the controller answers an identity request, how its controls are laid out and how each
shows its value.

    name: Faderfox UC4, setup SE17
    identity:
      reply: none                     # default: the rig doesn't answer (Decision 11)
      # reply: rig                    # the rig's own identity, non-commercial manufacturer 7D
      # reply: F0 7E 7F 06 02 47 4F 00 19 00 00 00 00 F7   # what the device sends, in hex
      # request: F0 7E 7F 06 01 F7    # default: MIDI's identity request, as v3 sends it
    layout:                           # rows of element or matrix names, for the panel (step 5)
      - [faders, crossfader]
      - [pan_encoders]
    display:                          # how a control shows its value: absolute (default),
      pan_encoders: bipolar           # bipolar or relative
      track_select_encoder: relative
    leds:                             # what a button's LED shows for a value Live sends (Decision 26):
      steps: &grid                    # an element or matrix name -> value -> colour, `off`, and
        0: off                        # ` blink` after the colour; a YAML anchor shares a map
        1: green
        2: green blink
      pads: *grid

A colour is a name from `COLOURS` or a quoted `'#rrggbb'` (a bare `#` starts a YAML comment). A value the map doesn't name shows as before (the
LED lit by the value). An element's own map wins over its matrix's.

How v3 checks an identity reply (12.4.16 index, `ableton.v3.control_surface.identification`,
observed): the script sends `identity_request` (default `F0 7E 7F 06 01 F7`) and, with
`identity_response_id_bytes` set, accepts a reply `F0 7E <device> 06 02 <those bytes> …`; a `-1`
among the bytes matches any byte there. With `custom_identity_response` it waits for that exact
message instead. A profile's reply is sent as written, whenever the request arrives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ports import load_yaml, parse_message

IDENTITY_REQUEST = [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]  # midi.SYSEX_IDENTITY_REQUEST_MESSAGE, 12.4.16
# The rig's own identity (Decision 11): manufacturer 7D (MIDI's non-commercial ID, never a real
# manufacturer's), family 00 01, model 00 01. A script for the rig sets these five bytes as its
# `identity_response_id_bytes`; the four version bytes follow in the reply.
RIG_IDENTITY_BYTES = (0x7D, 0x00, 0x01, 0x00, 0x01)
RIG_IDENTITY_REPLY = [0xF0, 0x7E, 0x7F, 0x06, 0x02, *RIG_IDENTITY_BYTES, 0x00, 0x01, 0x00, 0x00, 0xF7]
DISPLAYS = {"absolute", "bipolar", "relative"}
# LED colours a profile may name; what the page draws for each (the panel sends the hex).
COLOURS = {"red": "#e5322d", "green": "#2fb344", "yellow": "#f2c12e", "amber": "#f59a1b",
           "orange": "#f0701f", "blue": "#3a7bd5", "cyan": "#2bb7c9", "purple": "#9b5bd6",
           "pink": "#ec5fa4", "white": "#f4f4f0"}
PROFILE_KEYS = {"name", "identity", "layout", "display", "leds"}
PROFILE_NAME = "device.yaml"


class ProfileError(ValueError):
    pass


@dataclass
class Profile:
    name: str = ""
    request: list[int] = field(default_factory=lambda: list(IDENTITY_REQUEST))
    reply: list[int] | None = None
    layout: list[list[str]] = field(default_factory=list)
    display: dict[str, str] = field(default_factory=dict)
    leds: dict[str, dict[int, Led]] = field(default_factory=dict)


@dataclass(frozen=True)
class Led:
    colour: str | None  # "#rrggbb", or None for off
    blink: bool = False

    def to_json(self) -> dict:
        return {"colour": self.colour, "blink": self.blink}


def load_profile(path: Path) -> Profile:
    yaml = load_yaml()

    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise ProfileError(f"{path}: {e}") from e
    if not isinstance(data, dict) or set(data) - PROFILE_KEYS:
        raise ProfileError(f"{path}: a device profile takes {', '.join(sorted(PROFILE_KEYS))}")
    identity = data.get("identity") or {}
    profile = Profile(name=str(data.get("name", "")))
    try:
        if identity.get("request"):
            profile.request = _sysex(identity["request"])
        reply = identity.get("reply", "none")
        if reply == "rig":
            profile.reply = list(RIG_IDENTITY_REPLY)
        elif reply not in (None, "none"):
            profile.reply = parse_message(str(reply))
    except ValueError as e:
        raise ProfileError(f"{path}: identity: {e}") from e
    layout = data.get("layout") or []
    if not isinstance(layout, list) or not all(isinstance(row, list) for row in layout):
        raise ProfileError(f"{path}: `layout` is a list of rows, each a list of element or matrix names")
    profile.layout = [[str(x) for x in row] for row in layout]
    display = data.get("display") or {}
    bad = {k: v for k, v in display.items() if v not in DISPLAYS}
    if bad:
        raise ProfileError(f"{path}: `display` takes {', '.join(sorted(DISPLAYS))}; not {bad}")
    profile.display = {str(k): str(v) for k, v in display.items()}
    try:
        profile.leds = _leds(data.get("leds") or {})
    except ValueError as e:
        raise ProfileError(f"{path}: leds: {e}") from e
    return profile


def _leds(data) -> dict[str, dict[int, Led]]:
    if not isinstance(data, dict):
        raise ValueError("a map of element or matrix names, each a map of value -> colour")  # noqa: TRY004
    leds = {}
    for name, values in data.items():
        if not isinstance(values, dict) or not values:
            raise ValueError(f"`{name}` takes a map of value -> colour, such as `1: green`")
        leds[str(name)] = {_value(name, v): _led(name, v, text) for v, text in values.items()}
    return leds


def _value(name, value) -> int:
    if isinstance(value, str) and value.isdigit():
        raise ValueError(f"`{name}`: `'{value}'` is text; write the value without quotes")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 127:
        raise ValueError(f"`{name}`: `{value}` is not a value 0-127")
    return value


def _led(name, value, text) -> Led:
    if text is False:  # YAML 1.1 reads a bare `off` (and `no`, `false`) as false: all mean off
        return Led(None)
    if text is None:  # nothing after the colon, or an unquoted `#rrggbb`, which YAML reads as a comment
        raise ValueError(f"`{name}` {value}: no colour; quote a hex colour, such as '#ff0000'")
    if text is True:  # `on`, `yes`, `true`
        raise ValueError(f"`{name}` {value}: YAML reads this as true; name the colour, such as `red`")
    words = str(text).lower().split()
    blink = words[1:] == ["blink"]
    if not words or len(words) > 2 or (len(words) == 2 and not blink):
        raise ValueError(f"`{name}` {value}: `{text}` is not `<colour>` or `<colour> blink`")
    colour = words[0]
    if colour == "off":
        if blink:
            raise ValueError(f"`{name}` {value}: `off` doesn't blink")
        return Led(None)
    if colour in COLOURS:
        return Led(COLOURS[colour], blink)
    if len(colour) == 7 and colour[0] == "#" and all(c in "0123456789abcdef" for c in colour[1:]):
        return Led(colour, blink)
    raise ValueError(f"`{name}` {value}: `{colour}` is not off, #rrggbb or one of {', '.join(sorted(COLOURS))}")


def _sysex(text) -> list[int]:
    message = parse_message(str(text))
    if message[0] != 0xF0 or message[-1] != 0xF7:
        raise ValueError(f"`{text}` is not a SysEx message (F0 … F7)")
    return message


def profile_beside(path: Path) -> Profile | None:
    """The `device.yaml` in the same folder as `path` (a check file or a script folder), if any."""
    path = Path(path)
    folder = path if path.is_dir() else path.parent
    candidate = folder / PROFILE_NAME
    return load_profile(candidate) if candidate.is_file() else None


def check_profile_names(profile: Profile, ctl) -> list[str]:
    """Names in the profile's layout, display hints and LED maps that the controller doesn't have,
    and LED maps on controls that aren't buttons (only a button's LED is drawn)."""
    known = set(ctl.elements) | set(ctl.matrices)
    names = [n for row in profile.layout for n in row] + list(profile.display) + list(profile.leds)
    problems = [f"device.yaml names `{n}`, which {ctl.script} has no element or matrix of"
                for n in names if n not in known]
    for n in profile.leds:
        if n in known and any(ctl.elements[e].kind != "button" for e in ctl.matrices.get(n, [n])):
            problems.append(f"device.yaml gives `{n}` LED colours, and only buttons have LEDs on the panel")
    return problems


class IdentityResponder:
    """Answers the profile's identity request on a port; `handle` is called with every message
    Live sends, and says whether it answered."""

    def __init__(self, port, profile: Profile | None, log=lambda _: None):
        self.port = port
        self.profile = profile
        self.log = log
        self.answered = 0

    def handle(self, message: list[int]) -> bool:
        if not self.profile or self.profile.reply is None or list(message) != self.profile.request:
            return False
        self.port.send(self.profile.reply)
        self.answered += 1
        self.log(f"answered Live's identity request ({self.answered})")
        return True


class RespondingPort:
    """A port that answers the identity request while it is drained (the same interface)."""

    def __init__(self, port, responder: IdentityResponder):
        self._port = port
        self.responder = responder
        self.name = port.name

    def send(self, message: list[int]) -> None:
        self._port.send(message)

    def drain(self):
        got = self._port.drain()
        for r in got:
            self.responder.handle(r.message)
        return got

    def close(self) -> None:
        self._port.close()
