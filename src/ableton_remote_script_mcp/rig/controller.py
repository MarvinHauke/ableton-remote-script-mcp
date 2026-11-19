"""The controller model (plan 0002 Decision 3): which MIDI message each of a script's elements
sends and receives, read from the script folder without running it.

`outline` of the folder finds the calls that build elements (a v3 Elements class's
`self.add_button(...)`, `add_encoder`, `add_button_matrix`, `add_encoder_matrix`, along the
framework's own methods). The arguments come from that call in the script's source, with the
module's constants filled in: the outline's statement summary drops the keywords of a call that
also passes `**k` (`channel=CH14` next to `**SHOWS_VALUE`), so it can't give the channel.

Defaults, observed in the 12.4.16 index: `add_button` and `add_encoder` take `channel` from their
keywords, else the Elements' `global_channel` (`ElementsBase.__init__` default 0); `ButtonElement`
and `EncoderElement` default to `msg_type=MIDI_CC_TYPE`. A matrix takes `channels` as one number
or one per element (rows like `identifiers`), else the global channel (`add_matrix`; its body as
documented in the decompiled 11/12.0 framework, `is_iterable(channels)` observed in 12.4.16). A
matrix's elements are named `<matrix>[i]`, counted row by row from 0, like `<matrix>_raw[i]`.
`add_submatrix(matrix, name, columns=(start, stop), rows=(start, stop))` builds no elements: it
names a part of a matrix built before it (`submatrices`; the slices as `ElementsBase.add_submatrix`
takes them, observed 12.4.16; their meaning documented in the decompiled 12.0 framework).

Only v3 Elements classes are read; an element whose numbers can't be worked out is listed in
`unresolved` with the reason, never guessed.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
from pathlib import Path

MSG_TYPES = {"MIDI_NOTE_TYPE": "note", "MIDI_CC_TYPE": "cc", "MIDI_PB_TYPE": "pitchbend"}
STATUS = {"note": 0x90, "cc": 0xB0, "pitchbend": 0xE0}
RELATIVE_MODES = {"LinearTwoCompliment", "LinearSignedBit", "LinearSignedBit2", "LinearBinaryOffset",
                  "AccelTwoCompliment", "AccelSignedBit1", "AccelSignedBit2", "AccelBinaryOffset"}
ADDERS = {"add_button": "button", "add_encoder": "encoder", "add_modifier_button": "button",
          "add_button_matrix": "button", "add_encoder_matrix": "encoder"}


class Unresolved(Exception):
    pass


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


class _Constants:
    """Module-level names of a script module, evaluated on demand."""

    def __init__(self, tree: ast.Module, modules: dict[str, ast.Module], module: str, packages: set[str]):
        self.binds: dict[str, ast.expr] = {}
        self.imported: dict[str, tuple[str, str]] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self.binds[node.targets[0].id] = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
                self.binds[node.target.id] = node.value
            elif isinstance(node, ast.ImportFrom):
                base = _absolute(module, node.module, node.level, module in packages)
                for a in node.names:
                    self.imported[a.asname or a.name] = (base, a.name)
        self.modules = modules
        self.packages = packages
        self.seen: set[str] = set()

    def lookup(self, name: str):
        if name in MSG_TYPES:
            return MSG_TYPES[name]
        if name in self.binds:
            if name in self.seen:
                raise Unresolved(f"`{name}` refers to itself")
            self.seen.add(name)
            try:
                return self.eval(self.binds[name])
            finally:
                self.seen.discard(name)
        if name in self.imported:
            base, real = self.imported[name]
            if real in MSG_TYPES:
                return MSG_TYPES[real]
            if base in self.modules:  # a constant from the script's own module
                return _Constants(self.modules[base], self.modules, base, self.packages).lookup(real)
        raise Unresolved(f"`{name}` is not a constant of the script")

    def eval(self, node: ast.expr):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.lookup(node.id)
        if isinstance(node, (ast.List, ast.Tuple)):
            out = []
            for item in node.elts:
                if isinstance(item, ast.Starred):
                    out += list(self.eval(item.value))
                else:
                    out.append(self.eval(item))
            return out
        if isinstance(node, ast.Dict):
            out = {}
            for k, v in zip(node.keys, node.values):
                if k is None:
                    out.update(self.eval(v))
                else:
                    out[self.eval(k)] = self.eval(v)
            return out
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "MapMode":
            return node.attr
        if isinstance(node, ast.Attribute) and node.attr in MSG_TYPES:
            return MSG_TYPES[node.attr]
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            a, b = self.eval(node.left), self.eval(node.right)
            if isinstance(a, range):
                a = list(a)
            if isinstance(b, range):
                b = list(b)
            return {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b}[type(node.op)]()
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self.eval(node.operand)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            args = [self.eval(a) for a in node.args]
            if node.func.id == "range":
                return range(*args)
            if node.func.id in ("list", "tuple") and len(args) == 1:
                return list(args[0])
            if node.func.id == "dict" and not args:
                return {}
        if isinstance(node, ast.ListComp) and len(node.generators) == 1 and not node.generators[0].ifs:
            gen = node.generators[0]
            if isinstance(gen.target, ast.Name):
                out = []
                for value in self.eval(gen.iter):
                    out.append(_Local(self, gen.target.id, value).eval(node.elt))
                return out
        raise Unresolved(f"`{ast.unparse(node)}` can't be worked out without running the script")


class _Local(_Constants):
    """A comprehension's variable over the module's constants."""

    def __init__(self, outer: _Constants, name: str, value):
        self.__dict__.update(outer.__dict__)
        self.outer, self.name, self.value = outer, name, value

    def lookup(self, name: str):
        return self.value if name == self.name else self.outer.lookup(name)


def _absolute(module: str, name: str | None, level: int, is_package: bool) -> str:
    """The module a `from <dots><name> import` in `module` reads."""
    if level == 0:
        return name or ""
    parts = module.split(".")
    base = parts[: len(parts) - level + (1 if is_package else 0)]
    return ".".join([*base, name] if name else base)


def _attribute_name(name: str) -> str:
    return name.lower().replace(" ", "_")


def _call_at(tree: ast.Module, line: int, method: str) -> ast.Call | None:
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and node.lineno == line and isinstance(node.func, ast.Attribute)
                and node.func.attr == method):
            return node
    return None


def _bind(call: ast.Call, params: list[str], consts: _Constants) -> dict:
    """The call's arguments by parameter name (`**d` and `*seq` resolved through constants)."""
    positional = []
    for a in call.args:
        if isinstance(a, ast.Starred):
            positional += list(consts.eval(a.value))
        else:
            positional.append(a)
    bound: dict = {}
    for name, value in zip(params, positional):
        bound[name] = value
    for kw in call.keywords:
        if kw.arg is None:
            for k, v in consts.eval(kw.value).items():
                bound[k] = ast.Constant(v)
        else:
            bound[kw.arg] = kw.value
    return bound


def _global_channel(tree: ast.Module, cls: str, consts: _Constants) -> int:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls:
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "__init__"
                        and isinstance(sub.func.value, ast.Call)):
                    for kw in sub.keywords:
                        if kw.arg == "global_channel":
                            return int(consts.eval(kw.value))
    return 0  # ElementsBase.__init__(global_channel=0), observed 12.4.16


def build_controller(outline: dict, folder: Path) -> Controller:
    """The controller model from `outline` of a script folder (see the module docstring)."""
    from ..validator import read_sources

    folder = Path(folder)
    sources, _ = read_sources(folder, [])
    trees = {m: s.tree for m, s in sources.items() if s.tree is not None}
    packages = {m for m, s in sources.items() if s.is_package}
    ctl = Controller(outline.get("script", folder.name), str(folder))
    for entry in outline.get("elements", []):
        defined_by = entry.get("defined_by") or ""
        method = defined_by.rsplit(".", 1)[-1]
        where = entry.get("in", "")
        if method not in ADDERS and method != "add_submatrix":
            if defined_by or entry.get("class"):
                ctl.unresolved.append({"line": entry.get("line"), "in": where,
                                       "reason": f"built by {method or entry.get('class')}, which the rig doesn't read"})
            continue
        module = next((m for m in sorted(trees, key=len, reverse=True) if where.startswith(m + ".")), None)
        cls = where[len(module) + 1:].split(".")[0] if module else None
        call = _call_at(trees[module], entry["line"], method) if module else None
        if call is None:
            ctl.unresolved.append({"line": entry.get("line"), "in": where, "reason": "the call isn't in the source"})
            continue
        consts = _Constants(trees[module], trees, module, packages)
        try:
            _add(ctl, method, call, consts, _global_channel(trees[module], cls, consts), entry["line"])
        except (Unresolved, TypeError, ValueError, KeyError) as e:
            ctl.unresolved.append({"line": entry["line"], "in": where, "reason": str(e)})
    return ctl


def _add_submatrix(ctl: Controller, call: ast.Call, consts: _Constants) -> None:
    args = _bind(call, ["matrix", "name", "columns", "rows"], consts)
    source = args.get("matrix")
    if not (isinstance(source, ast.Attribute) and isinstance(source.value, ast.Name) and source.value.id == "self"):
        raise Unresolved("the submatrix's matrix is not an attribute of the Elements")
    if source.attr not in ctl.matrices:
        raise Unresolved(f"no matrix `{source.attr}` built before it")
    items, width = ctl.matrices[source.attr], ctl.widths[source.attr]
    height = len(items) // width if width else 0
    columns = consts.eval(args["columns"]) if "columns" in args else None
    rows = consts.eval(args["rows"]) if "rows" in args else None
    # as Python slices: a range past the matrix stops at its edge
    columns = range(*slice(*(columns or (0, width))).indices(width))
    rows = range(*slice(*(rows or (0, height))).indices(height))
    name = consts.eval(args["name"])
    ctl.submatrices[_attribute_name(name)] = [items[r * width + c] for r in rows for c in columns]


def _add(ctl: Controller, method: str, call: ast.Call, consts: _Constants, global_channel: int, line: int) -> None:
    if method == "add_submatrix":
        return _add_submatrix(ctl, call, consts)
    kind = ADDERS[method]
    matrix = method.endswith("_matrix")
    params = ["identifiers", "base_name", "channels"] if matrix else ["identifier", "name"]
    args = _bind(call, params, consts)
    name = consts.eval(args["base_name" if matrix else "name"])
    if not isinstance(name, str):
        raise Unresolved("the element's name is not a string")
    msg_type = consts.eval(args["msg_type"]) if "msg_type" in args else "cc"  # MIDI_CC_TYPE, observed 12.4.16
    if isinstance(msg_type, int):
        msg_type = {0: "note", 1: "cc", 2: "pitchbend"}[msg_type]
    feedback = bool(consts.eval(args["is_feedback_enabled"])) if "is_feedback_enabled" in args else False
    map_mode = consts.eval(args["map_mode"]) if "map_mode" in args else "absolute"
    common = {"kind": kind, "msg_type": msg_type, "feedback": feedback, "map_mode": str(map_mode), "line": line}
    attr = _attribute_name(name)
    if not matrix:
        channel = consts.eval(args["channel"]) if "channel" in args else global_channel
        ctl.elements[attr] = Element(attr, channel=int(channel), identifier=int(consts.eval(args["identifier"])),
                                     **common)
        return
    rows = [list(r) for r in consts.eval(args["identifiers"])]
    if len({len(r) for r in rows}) > 1:
        raise Unresolved("the matrix's rows have different lengths")
    channels = consts.eval(args["channels"]) if "channels" in args else None
    if channels is None:
        channels = global_channel
    if isinstance(channels, int):
        channels = [[channels] * len(r) for r in rows]
    names = []
    for row, chans in zip(rows, channels):
        for identifier, channel in zip(row, chans):
            item = f"{attr}[{len(names)}]"
            ctl.elements[item] = Element(item, channel=int(channel), identifier=int(identifier), **common)
            names.append(item)
    ctl.matrices[attr] = names
    ctl.widths[attr] = len(rows[0]) if rows else 0


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
