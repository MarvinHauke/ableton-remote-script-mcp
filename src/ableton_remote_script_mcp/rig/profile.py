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

How v3 checks an identity reply (12.4.16 index, `ableton.v3.control_surface.identification`,
observed): the script sends `identity_request` (default `F0 7E 7F 06 01 F7`) and, with
`identity_response_id_bytes` set, accepts a reply `F0 7E <device> 06 02 <those bytes> …`; a `-1`
among the bytes matches any byte there. With `custom_identity_response` it waits for that exact
message instead. A profile's reply is sent as written, whenever the request arrives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ports import parse_message

IDENTITY_REQUEST = [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]  # midi.SYSEX_IDENTITY_REQUEST_MESSAGE, 12.4.16
# The rig's own identity (Decision 11): manufacturer 7D (MIDI's non-commercial ID, never a real
# manufacturer's), family 00 01, model 00 01. A script for the rig sets these five bytes as its
# `identity_response_id_bytes`; the four version bytes follow in the reply.
RIG_IDENTITY_BYTES = (0x7D, 0x00, 0x01, 0x00, 0x01)
RIG_IDENTITY_REPLY = [0xF0, 0x7E, 0x7F, 0x06, 0x02, *RIG_IDENTITY_BYTES, 0x00, 0x01, 0x00, 0x00, 0xF7]
DISPLAYS = {"absolute", "bipolar", "relative"}
PROFILE_KEYS = {"name", "identity", "layout", "display"}
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


def load_profile(path: Path) -> Profile:
    import yaml

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
    return profile


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
    """Names in the profile's layout and display hints that the controller doesn't have."""
    known = set(ctl.elements) | set(ctl.matrices)
    names = [n for row in profile.layout for n in row] + list(profile.display)
    return [f"device.yaml names `{n}`, which {ctl.script} has no element or matrix of" for n in names if n not in known]


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
