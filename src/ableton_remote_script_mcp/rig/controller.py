"""The controller model (plan 0002 Decision 3): which MIDI message each of a script's elements
sends and receives, read from the script folder without running it.

`outline` of the folder finds the calls that build elements; the Elements reader
(`elements.py`, plan 0001 Decision 57) reads what each one passes from the script's source, with
the module's constants filled in, and says why when it can't. Its defaults and the matrix and
submatrix rules are in that module's docstring. A matrix's elements are named `<matrix>[i]`,
counted row by row from 0, like `<matrix>_raw[i]`; a submatrix builds no elements, it names a part
of a matrix (`submatrices`).

Only v3 Elements classes are read; an element whose numbers can't be worked out is listed in
`unresolved` with the reason, never guessed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..elements import ScriptSource, read_calls

STATUS = {"note": 0x90, "cc": 0xB0, "pitchbend": 0xE0}
RELATIVE_MODES = {"LinearTwoCompliment", "LinearSignedBit", "LinearSignedBit2", "LinearBinaryOffset",
                  "AccelTwoCompliment", "AccelSignedBit1", "AccelSignedBit2", "AccelBinaryOffset"}


@dataclass
class Element:
    name: str  # as mappings use it: the attribute name, `faders[0]` for one element of a matrix
    kind: str  # button | encoder
    msg_type: str  # note | cc | pitchbend
    channel: int  # 0-15, as the framework counts
    identifier: int  # note or CC number
    feedback: bool = False  # an encoder built with is_feedback_enabled=True
    map_mode: str = "absolute"
    line: int | None = None

    @property
    def relative(self) -> bool:
        return self.map_mode in RELATIVE_MODES

    @property
    def key(self) -> tuple[int, int]:
        """(status byte, number) of what it sends and what Live sends back to it."""
        return STATUS[self.msg_type] | self.channel, self.identifier

    def message(self, value: int) -> list[int]:
        if self.msg_type == "pitchbend":
            return [STATUS["pitchbend"] | self.channel, value & 0x7F, (value >> 7) & 0x7F]
        return [*self.key, value]

    def describe(self) -> str:
        what = {"note": "note", "cc": "CC", "pitchbend": "pitch bend"}[self.msg_type]
        return f"{what} {self.identifier}, channel {self.channel + 1}"


@dataclass
class Controller:
    script: str
    folder: str
    elements: dict[str, Element] = field(default_factory=dict)
    matrices: dict[str, list[str]] = field(default_factory=dict)
    unresolved: list[dict] = field(default_factory=list)
    submatrices: dict[str, list[str]] = field(default_factory=dict)  # parts of a matrix, other names
    widths: dict[str, int] = field(default_factory=dict)  # a matrix's columns

    def element(self, name: str) -> Element:
        if name in self.elements:
            return self.elements[name]
        close = [n for n in self.elements if n.split("[")[0] == name.split("[")[0]][:3]
        hint = f" (did you mean {', '.join(close)}?)" if close else ""
        raise KeyError(f"no element `{name}` in {self.script}{hint}")

    def by_key(self, key: tuple[int, int]) -> list[Element]:
        """Every element on this message (two elements may share one: different components)."""
        return [e for e in self.elements.values() if e.key == key]

    def as_dict(self) -> dict:
        return {"script": self.script, "folder": self.folder,
                "elements": [{**asdict(e), "relative": e.relative} for e in self.elements.values()],
                "matrices": self.matrices, "unresolved": self.unresolved}


def build_controller(outline: dict, folder: Path) -> Controller:
    """The controller model from `outline` of a script folder (see the module docstring)."""
    from ..validator import read_sources

    folder = Path(folder)
    sources, _ = read_sources(folder, [])
    ctl = Controller(outline.get("script", folder.name), str(folder))
    entries = [e for e in outline.get("elements", []) if e.get("defined_by") or e.get("class")]
    for b in read_calls(entries, ScriptSource.of(sources)):
        if b.role is None:
            ctl.unresolved.append({"line": b.line, "in": b.unit, "reason": f"built by {b.method}, which the rig doesn't read"})
        elif b.why:
            ctl.unresolved.append({"line": b.line, "in": b.unit, "reason": b.why})
        elif b.role == "submatrix":
            ctl.submatrices[b.attr] = b.part
        else:
            common = {"kind": b.kind, "msg_type": b.msg_type, "feedback": b.feedback, "map_mode": b.map_mode,
                      "line": b.line}
            if b.role == "element":
                ctl.elements[b.attr] = Element(b.attr, channel=b.channel, identifier=b.identifier, **common)
                continue
            for item in b.items:
                ctl.elements[item.name] = Element(item.name, channel=item.channel, identifier=item.identifier, **common)
            ctl.matrices[b.attr] = [item.name for item in b.items]
            ctl.widths[b.attr] = b.width
    return ctl


def controller_for_folder(folder: Path, index_dir: Path, live_build: str | None = None) -> tuple[Controller | None, str]:
    """(the controller model of a script folder, or None and why)."""
    from ..query import _with_statements, outline_folder

    index, missing = _with_statements(index_dir, live_build)
    if missing:
        return None, missing["message"]
    outline, why = outline_folder(Path(folder), index)
    if outline is None:
        return None, why
    return build_controller(outline, Path(folder).expanduser().resolve()), ""
