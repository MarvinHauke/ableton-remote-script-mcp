"""The one reading of a v3 script's Elements class (plan 0001 Decision 57): what each of its
`self.add_…(...)` calls builds, and the names the mappings may use for it. The validator's
`element-name` rule, the rig's controller model and `check_names` all read it from here.

Where the calls are: the `self.add_…(...)` statements in the Elements classes' methods (the
statement summaries), each bound to the framework method it calls or that the script's own
method of that name overrides; such a call through an override gives its name, not its MIDI
messages. The rig starts from `outline`'s element entries instead (`read_calls`). What they pass: the call in the script's source at that line,
with the module's constants filled in (`Constants`). The statement summary can't give it when a
call also passes `**k`: Python compiles that call with all its positional arguments in one tuple,
so `add_button_matrix(ids, "Pads", **NOTE)` has no name there (finding 3). Without a source (an
Ableton script read from its `.pyc`) only the summary's literal names are read.

Names, as the framework's `ElementsBase` makes them (`_create_attribute_name`, documented in the
decompiled 12.0 framework): `name.lower()` with spaces as `_`; a matrix (or `base_name`, or a
modified control) also as `<name>_raw`; `add_sysex_display_line` also as `<name>_command`; an
`add_modified_control` without a name as `<control>_with_<modifier without "_button">`. Names a
class sets on `self` are added. A name the reader can't work out makes the set `computed`.

MIDI, observed in the 12.4.16 index: `add_button` and `add_encoder` take `channel` from their
keywords, else the Elements' `global_channel` (`ElementsBase.__init__` default 0); `ButtonElement`
and `EncoderElement` default to `msg_type=MIDI_CC_TYPE`. A matrix takes `channels` as one number
or one per element (rows like `identifiers`), else the global channel (`add_matrix`; its body as
documented in the decompiled 11/12.0 framework, `is_iterable(channels)` observed in 12.4.16). A
matrix's elements are named `<matrix>[i]`, counted row by row from 0, like `<matrix>_raw[i]`.
`add_submatrix(matrix, name, columns=(start, stop), rows=(start, stop))` builds no elements: it
names a part of a matrix built before it (the slices as `ElementsBase.add_submatrix` takes them,
observed 12.4.16; their meaning documented in the decompiled 12.0 framework). Anything that
can't be worked out is given with the reason in `why`, never guessed.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .outline import Outliner, bind_arguments, literal_str

MSG_TYPES = {"MIDI_NOTE_TYPE": "note", "MIDI_CC_TYPE": "cc", "MIDI_PB_TYPE": "pitchbend"}
ADDERS = {"add_button": "button", "add_encoder": "encoder", "add_modifier_button": "button",
          "add_button_matrix": "button", "add_encoder_matrix": "encoder"}
# The parameters the reader binds a call to when it has no index to take them from (the rig's
# tests): as `ElementsBase` names them, observed 12.4.16.
PARAMS = {**{m: ["identifier", "name"] for m in ("add_button", "add_encoder", "add_modifier_button")},
          **{m: ["identifiers", "base_name", "channels"] for m in ("add_button_matrix", "add_encoder_matrix")},
          "add_submatrix": ["matrix", "name", "columns", "rows"]}


class Unresolved(Exception):
    pass


@dataclass
class Item:
    """One element of a matrix."""
    name: str  # `<matrix>[i]`
    identifier: int
    channel: int


@dataclass
class Built:
    """What one `self.add_…(...)` call builds."""
    method: str  # add_button, add_button_matrix, add_submatrix, … (or the class or factory, for others)
    line: int | None
    unit: str  # the method it is written in, `Script.elements.Elements.__init__`
    name: str | None = None  # as written: "Shift Button"
    names: list[str] = field(default_factory=list)  # what the mappings may call it: shift_button, …
    kind: str | None = None  # button | encoder
    msg_type: str | None = None  # note | cc | pitchbend
    channel: int | None = None  # 0-15, as the framework counts
    identifier: int | None = None  # note or CC number
    feedback: bool = False
    map_mode: str = "absolute"
    items: list[Item] = field(default_factory=list)  # a matrix's elements, row by row
    width: int = 0  # a matrix's columns
    part_of: str | None = None  # a submatrix: the matrix it names a part of
    part: list[str] = field(default_factory=list)  # a submatrix: the items of that matrix it names
    why: str | None = None  # what the reader couldn't work out, and why
    arguments: dict | None = field(default=None, repr=False)  # by parameter, from the source; None: not read


@dataclass
class Elements:
    """A script's Elements class(es), read."""
    built: list[Built] = field(default_factory=list)
    names: set[str] | None = None  # every name the mappings may use; None: no Elements class
    computed: bool = False  # some names can't be worked out without running the script
    why: str = ""  # why there are no names


def attribute_name(name: str) -> str:
    return name.lower().replace(" ", "_")


# --- the script's source: constants and calls ----------------------------------------------


class Constants:
    """Module-level names of a script module, evaluated on demand."""

    def __init__(self, tree: ast.Module, modules: dict[str, ast.Module], module: str, packages: set[str],
                 seen: set[tuple[str, str]] | None = None):
        self.module = module
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
        self.seen = seen if seen is not None else set()  # (module, name) being evaluated, across imports

    def lookup(self, name: str):
        if name in MSG_TYPES:
            return MSG_TYPES[name]
        if name in self.binds:
            key = (self.module, name)
            if key in self.seen:
                raise Unresolved(f"`{name}` refers to itself")
            self.seen.add(key)
            try:
                return self.eval(self.binds[name])
            finally:
                self.seen.discard(key)
        if name in self.imported:
            base, real = self.imported[name]
            if real in MSG_TYPES:
                return MSG_TYPES[real]
            if base in self.modules:  # a constant from the script's own module
                key = (self.module, name)
                if key in self.seen:  # modules that import the name from each other
                    raise Unresolved(f"`{name}` refers to itself")
                self.seen.add(key)
                try:
                    return Constants(self.modules[base], self.modules, base, self.packages, self.seen).lookup(real)
                finally:
                    self.seen.discard(key)
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


class _Local(Constants):
    """A comprehension's variable over the module's constants."""

    def __init__(self, outer: Constants, name: str, value):
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


def _call_at(tree: ast.Module, line: int, method: str) -> ast.Call | None:
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and node.lineno == line and isinstance(node.func, ast.Attribute)
                and node.func.attr == method):
            return node
    return None


def bind(call: ast.Call, params: list[str], consts: Constants) -> dict:
    """The call's arguments by parameter name (`**d` and `*seq` resolved through constants)."""
    positional = []
    for a in call.args:
        if isinstance(a, ast.Starred):
            seq = consts.eval(a.value)
            if not isinstance(seq, (list, tuple, range)):
                raise Unresolved(f"`*{ast.unparse(a.value)}` is not a sequence of the script")
            positional += [ast.Constant(v) for v in seq]
        else:
            positional.append(a)
    bound: dict = {}
    for name, value in zip(params, positional):
        bound[name] = value
    for kw in call.keywords:
        if kw.arg is None:
            values = consts.eval(kw.value)
            if not isinstance(values, dict):
                raise Unresolved(f"`**{ast.unparse(kw.value)}` is not a dict of the script")
            for k, v in values.items():
                bound[k] = ast.Constant(v)
        else:
            bound[kw.arg] = kw.value
    return bound


def _global_channel(tree: ast.Module, cls: str | None, consts: Constants) -> int:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls:
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "__init__"
                        and isinstance(sub.func.value, ast.Call)):
                    for kw in sub.keywords:
                        if kw.arg == "global_channel":
                            return int(consts.eval(kw.value))
    return 0  # ElementsBase.__init__(global_channel=0), observed 12.4.16


# --- reading the calls ---------------------------------------------------------------------


class ScriptSource:
    """The parsed modules of a script folder."""

    def __init__(self, trees: dict[str, ast.Module], packages: set[str]):
        self.trees = trees
        self.packages = packages

    @classmethod
    def of(cls, sources: dict) -> ScriptSource:
        """From the validator's `read_sources` (module -> Source with `.tree`, `.is_package`)."""
        return cls({m: s.tree for m, s in sources.items() if s.tree is not None},
                   {m for m, s in sources.items() if s.is_package})

    def locate(self, unit: str) -> tuple[str | None, str | None]:
        """(module, class) of a unit label such as `Script.elements.Elements.__init__`."""
        module = next((m for m in sorted(self.trees, key=len, reverse=True) if unit.startswith(m + ".")), None)
        return module, (unit[len(module) + 1:].split(".")[0] if module else None)


def read_calls(entries: list[dict], source: ScriptSource, params_of=None) -> list[Built]:
    """What each element entry of an outline builds, read from the script's source. `params_of`
    gives a `defined_by` method's parameter names from the index; without it, `PARAMS`."""
    built: list[Built] = []
    matrices: dict[str, Built] = {}
    for entry in entries:
        defined_by = entry.get("defined_by") or ""
        method = defined_by.rsplit(".", 1)[-1]
        unit = entry.get("in", "")
        b = Built(method or entry.get("class") or "", entry.get("line"), unit,
                  name=entry.get("name") if isinstance(entry.get("name"), str) else None)
        built.append(b)
        if not defined_by:
            b.why = f"built by {entry.get('class') or entry.get('via')}, not by an Elements class's add_… call"
            continue
        params = (params_of(defined_by) if params_of else None) or PARAMS.get(method)
        module, cls = source.locate(unit)
        call = _call_at(source.trees[module], b.line, method) if module and b.line is not None else None
        if call is None:
            b.why = "the call isn't in the source"
            continue
        consts = Constants(source.trees[module], source.trees, module, source.packages)
        try:
            b.arguments = args = bind(call, params or [], consts)
            if entry.get("through"):  # the script's own override: its name by the framework's signature
                _read_name(b, args, consts)
                b.why = (f"built through the script's own {method} ({entry['through']}), "
                         "whose MIDI messages the reader doesn't follow")
            else:
                _read(b, args, consts, source.trees[module], cls, matrices)
        except (Unresolved, TypeError, ValueError, KeyError) as e:
            b.why = str(e)
    return built


def _name(args: dict, key: str, consts: Constants) -> str:
    if key not in args:
        raise Unresolved(f"the call passes no {key}")
    name = consts.eval(args[key])
    if not isinstance(name, str):
        raise Unresolved("the element's name is not a string")
    return name


def _read_name(b: Built, args: dict, consts: Constants) -> None:
    for key in ("name", "base_name"):
        if key in args:
            b.name = _name(args, key, consts)


def _read(b: Built, args: dict, consts: Constants, tree: ast.Module, cls: str | None,
          matrices: dict[str, Built]) -> None:
    def global_channel() -> int:
        return _global_channel(tree, cls, consts)

    if b.method == "add_submatrix":
        b.name = _name(args, "name", consts)
        source = args.get("matrix")
        if not (isinstance(source, ast.Attribute) and isinstance(source.value, ast.Name) and source.value.id == "self"):
            raise Unresolved("the submatrix's matrix is not an attribute of the Elements")
        b.part_of = source.attr
        if source.attr not in matrices:
            raise Unresolved(f"no matrix `{source.attr}` built before it")
        m = matrices[source.attr]
        width = m.width
        height = len(m.items) // width if width else 0
        columns = consts.eval(args["columns"]) if "columns" in args else None
        rows = consts.eval(args["rows"]) if "rows" in args else None
        # as Python slices: a range past the matrix stops at its edge
        columns = range(*slice(*(columns or (0, width))).indices(width))
        rows = range(*slice(*(rows or (0, height))).indices(height))
        b.part = [m.items[r * width + c].name for r in rows for c in columns]
        return
    if b.method not in ADDERS:
        return _read_name(b, args, consts)
    matrix = b.method.endswith("_matrix")
    b.name = _name(args, "base_name" if matrix else "name", consts)
    b.kind = ADDERS[b.method]
    msg_type = consts.eval(args["msg_type"]) if "msg_type" in args else "cc"  # MIDI_CC_TYPE, observed 12.4.16
    if isinstance(msg_type, int):
        msg_type = {0: "note", 1: "cc", 2: "pitchbend"}[msg_type]
    b.msg_type = msg_type
    b.feedback = bool(consts.eval(args["is_feedback_enabled"])) if "is_feedback_enabled" in args else False
    b.map_mode = str(consts.eval(args["map_mode"])) if "map_mode" in args else "absolute"
    attr = attribute_name(b.name)
    if not matrix:
        b.channel = int(consts.eval(args["channel"]) if "channel" in args else global_channel())
        b.identifier = int(consts.eval(args["identifier"]))
        return
    rows = [list(r) for r in consts.eval(args["identifiers"])]
    if len({len(r) for r in rows}) > 1:
        raise Unresolved("the matrix's rows have different lengths")
    channels = consts.eval(args["channels"]) if "channels" in args else None
    if channels is None:
        channels = global_channel()
    if isinstance(channels, int):
        channels = [[channels] * len(r) for r in rows]
    for row, chans in zip(rows, channels):
        for identifier, channel in zip(row, chans):
            b.items.append(Item(f"{attr}[{len(b.items)}]", int(identifier), int(channel)))
    b.width = len(rows[0]) if rows else 0
    matrices[attr] = b


# --- the names the mappings may use --------------------------------------------------------


def read_elements(outliner, sources: dict | None = None) -> Elements:
    """The script's Elements class(es) as `outline`'s `Outliner` of the script sees them, with the
    arguments from `sources` (the validator's `read_sources`) where there are any."""
    classes = [k for k in outliner.class_keys if outliner.role(k) == "elements"]
    if not classes:
        return Elements(why="the script has no Elements class (an ElementsBase subclass) to read")
    entries = _entries(outliner, classes)

    def params_of(defined_by: str) -> list[str] | None:  # the positional ones, as outline binds them
        params = _params(outliner, defined_by)
        return None if params is None else [
            p["name"] for p in params
            if p["name"] not in ("self", "cls") and p["kind"] in ("positional_only", "positional_or_keyword")]

    built = read_calls(entries, ScriptSource.of(sources or {}), params_of)
    result = Elements(built=built, names=set())
    originals: dict[str, str] = {}
    pending = []
    for b, entry in zip(built, entries):
        if not {"name", "base_name"} & {p["name"] for p in _params(outliner, entry["defined_by"]) or []}:
            continue  # a method that names nothing
        args = b.arguments
        text = entry.get("arguments", {})
        if b.name is None and b.method == "add_modified_control" and not ({"name"} & set(args or text)):
            pending.append((args, text))
            continue
        if b.name is None:
            result.computed = True
            continue
        attr = attribute_name(b.name)
        b.names = [attr]
        originals[attr] = b.name
        given = set(args) if args is not None else set(text)
        if "base_name" in given or "matrix" in b.method or b.method == "add_modified_control":
            b.names.append(f"{attr}_raw")
        if b.method == "add_sysex_display_line":
            b.names.append(f"{attr}_command")
        result.names.update(b.names)
    for args, text in pending:  # create_name_for_modified_control: <control>_with_<modifier without _button>
        control, modifier = _given(args, text, "control"), _given(args, text, "modifier")
        if control not in originals or modifier not in originals:
            result.computed = True
            continue
        mod = originals[modifier][:-7] if originals[modifier].lower().endswith("button") else originals[modifier]
        prep = "With" if any(c.isupper() for c in originals[control]) else "with"
        attr = f"{originals[control]}_{prep}_{mod}".lower().replace(" ", "_")
        result.names |= {attr, f"{attr}_raw"}
    for cls in classes:
        result.names |= outliner.instance_attributes(cls)
    return result


def _entries(outliner, classes: list[str]) -> list[dict]:
    """The `self.add_…(...)` calls in the Elements classes, as outline entries: each bound to the
    framework method it is or overrides (`through`: the script's override in between). The
    script's own helpers that call no framework method are skipped: the calls inside them are read."""
    entries = []
    for unit in outliner.units():
        if unit["in_class"] not in classes:
            continue
        members = outliner.lineage(unit["in_class"]).members
        for st in unit["statements"]:
            call = st.get("call", "")
            if not call.startswith("self.add_") or call.count(".") != 1:
                continue
            method = call[len("self."):]
            found = members.get(method)
            chain = [found["origin"], *found["overrides"]] if found else []
            origin = next((k for k in chain if outliner.is_framework(k)), None)
            if origin is None:
                continue
            args = bind_arguments(outliner.classes[origin]["members"][method], st["args"], st["kwargs"])
            entry = {"name": literal_str(args.get("name") or args.get("base_name")),
                     "defined_by": f"{origin}.{method}", "arguments": args, "line": st["line"], "in": unit["label"]}
            if found["origin"] != origin:
                entry["through"] = found["origin"]
            entries.append(entry)
    return entries


def _given(args: dict | None, text: dict, key: str) -> str:
    """An argument of a call as source text without `self.`: from the source, else the summary."""
    if args is not None and key in args:
        return ast.unparse(args[key]).removeprefix("self.")
    return (text.get(key) or "").removeprefix("self.")


def _params(outliner, defined_by: str) -> list[dict] | None:
    """The parameters of a `defined_by` framework method in the index, or None."""
    key, _, method = defined_by.rpartition(".")
    member = outliner.index["classes"].get(key, {}).get("members", {}).get(method)
    return member.get("params") if member else None


def element_names_of_folder(folder: Path, index: dict) -> tuple[set[str], str]:
    """(the element names a script folder's Elements class builds, against an index with
    statements; why they couldn't be read, or ""). A script without an Elements class has none,
    and that needs no reason."""
    from .framework_checks import LIVE_PYTHON, compile_sources, overlay_index
    from .validator import read_sources

    if sys.version_info[:2] != LIVE_PYTHON:
        return set(), (f"the Elements class's names (they need Live's Python {LIVE_PYTHON[0]}.{LIVE_PYTHON[1]}; "
                       f"this is {sys.version_info[0]}.{sys.version_info[1]})")
    folder = Path(folder)
    findings: list[dict] = []
    not_checked: list[dict] = []
    sources, _ = read_sources(folder, findings)
    codes = compile_sources(sources, findings, not_checked)
    if not codes:
        return set(), "the Elements class's names (no source of the script compiles)"
    overlay = overlay_index(index, folder.name, sources, codes, not_checked)
    if folder.name not in overlay["packages"]:
        return set(), "the Elements class's names (the folder has no __init__.py: it is not a Remote Script)"
    read = read_elements(Outliner(overlay, folder.name), sources)
    why = ("some of the Elements class's names (it builds them from values that can't be read without "
           "running the script)") if read.computed else ""
    return read.names or set(), why
