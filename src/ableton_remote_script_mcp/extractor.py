"""Read the .pyc files of one Live build into index facts.

Code objects are loaded with marshal under CPython 3.11, never decompiled or executed.
Module and class bodies are read by simulating their stack symbolically: each STORE_NAME
becomes a binding (a class, a function, or an attribute with its value as source-like text).
Function bodies are not run; a function's parameters come from its code object and its
defaults from the MAKE_FUNCTION that created it.
"""

from __future__ import annotations

import dis
import importlib.util
import inspect
import marshal
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

PYC_HEADER_SIZE = 16
FRAMEWORK_PACKAGES = ("_Framework", "ableton")
MAX_VALUE_TEXT = 4000  # attribute values and defaults longer than this are cut, ending in "…"


class UnreadablePyc(Exception):
    pass


def load_code(path: Path) -> types.CodeType:
    data = path.read_bytes()
    if len(data) < PYC_HEADER_SIZE:
        raise UnreadablePyc("file shorter than the 16-byte .pyc header")
    magic = data[:4]
    if magic != importlib.util.MAGIC_NUMBER:
        raise UnreadablePyc(
            f"bytecode magic {magic!r} does not match this Python {sys.version_info[0]}."
            f"{sys.version_info[1]} ({importlib.util.MAGIC_NUMBER!r})"
        )
    try:
        code = marshal.loads(data[PYC_HEADER_SIZE:])
    except (ValueError, EOFError, TypeError) as e:
        raise UnreadablePyc(f"marshal could not load the code object: {e}") from e
    if not isinstance(code, types.CodeType):
        raise UnreadablePyc("marshal data is not a code object")
    return code


def module_name(rel: Path) -> tuple[str, bool]:
    """('ableton.v3.control_surface', True) for ableton/v3/control_surface/__init__.pyc."""
    parts = list(rel.with_suffix("").parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts = parts[:-1]
    return ".".join(parts), is_package


# --- imports -------------------------------------------------------------------------------


def _resolve_relative(module: str, is_package: bool, level, name: str) -> str:
    if not isinstance(level, int) or level == 0:
        return name
    base = module.split(".")
    if not is_package:
        base = base[:-1]
    if level > 1:
        base = base[: len(base) - (level - 1)]
    return ".".join(p for p in [*base, name] if p)


def collect_imports(code: types.CodeType, module: str, is_package: bool) -> dict[str, str]:
    """Map each name bound by an import in this code object to the qualified name it imports."""
    aliases: dict[str, str] = {}
    instrs = list(dis.get_instructions(code))
    for i, ins in enumerate(instrs):
        if ins.opname != "IMPORT_NAME" or i < 2:
            continue
        level = instrs[i - 2].argval if instrs[i - 2].opname == "LOAD_CONST" else 0
        fromlist = instrs[i - 1].argval if instrs[i - 1].opname == "LOAD_CONST" else None
        target = _resolve_relative(module, is_package, level or 0, ins.argval)
        j = i + 1
        if fromlist:  # from target import a as b, c
            while j + 1 < len(instrs) and instrs[j].opname == "IMPORT_FROM":
                if instrs[j + 1].opname in ("STORE_NAME", "STORE_GLOBAL"):
                    aliases[instrs[j + 1].argval] = f"{target}.{instrs[j].argval}"
                j += 2
        else:
            nxt = instrs[j] if j < len(instrs) else None
            if nxt and nxt.opname in ("STORE_NAME", "STORE_GLOBAL"):  # import a  /  import a as b
                # `import a.b` binds `a`; `import a as b` binds `b` to `a`
                top = target.split(".")[0]
                aliases[nxt.argval] = top if nxt.argval == top else target
            else:  # import a.b as c  ->  IMPORT_FROM b ... STORE_NAME c
                k = j
                while k < len(instrs) and instrs[k].opname == "IMPORT_FROM":
                    k += 1
                if k < len(instrs) and instrs[k].opname in ("STORE_NAME", "STORE_GLOBAL"):
                    aliases[instrs[k].argval] = target
    return aliases


def imported_modules(code: types.CodeType, module: str, is_package: bool) -> set[str]:
    """Every module this code object imports from (absolute names), at any depth of the body."""
    found: set[str] = set()
    instrs = list(dis.get_instructions(code))
    for i, ins in enumerate(instrs):
        if ins.opname == "IMPORT_NAME":
            level = instrs[i - 2].argval if i >= 2 and instrs[i - 2].opname == "LOAD_CONST" else 0
            found.add(_resolve_relative(module, is_package, level or 0, ins.argval))
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            found |= imported_modules(const, module, is_package)
    return found


# --- symbolic values -----------------------------------------------------------------------


def _cut(text: str) -> str:
    return text if len(text) <= MAX_VALUE_TEXT else text[: MAX_VALUE_TEXT - 1] + "…"


class _Value:
    literal = False

    def text(self) -> str:
        raise NotImplementedError


@dataclass
class _Lit(_Value):
    value: object
    literal = True

    def text(self) -> str:
        return repr(self.value)


@dataclass
class _Expr(_Value):
    source: str  # source-like text, e.g. "DEFAULT_SIZE", "BasicColors.ON.midi_value"

    def text(self) -> str:
        return self.source


UNKNOWN = _Expr("…")  # an expression the simulator doesn't model


@dataclass
class _Seq(_Value):
    kind: str  # "tuple", "list", "set"
    items: list

    @property
    def literal(self) -> bool:  # type: ignore[override]
        return all(i.literal for i in self.items)

    def text(self) -> str:
        inner = ", ".join(_text(i) for i in self.items)
        if self.kind == "tuple":
            return f"({inner},)" if len(self.items) == 1 else f"({inner})"
        if self.kind == "set":
            return "{" + inner + "}" if self.items else "set()"
        return f"[{inner}]"


@dataclass
class _Map(_Value):
    pairs: list

    @property
    def literal(self) -> bool:  # type: ignore[override]
        return all(k.literal and v.literal for k, v in self.pairs)

    def text(self) -> str:
        return "{" + ", ".join(f"{_text(k)}: {_text(v)}" for k, v in self.pairs) + "}"


@dataclass
class _Call(_Value):
    callee: str
    args: list
    kwargs: list  # [(name, value)]

    def text(self) -> str:
        parts = [_text(a) for a in self.args] + [f"{k}={_text(v)}" for k, v in self.kwargs]
        return f"{self.callee}({', '.join(parts)})"


@dataclass
class _Func(_Value):
    code: types.CodeType
    defaults: list = field(default_factory=list)  # values for the last positional parameters
    kwdefaults: dict = field(default_factory=dict)  # name -> value
    decorators: list = field(default_factory=list)  # outermost first

    def text(self) -> str:
        return "<lambda>" if self.code.co_name == "<lambda>" else f"<function {self.code.co_name}>"


@dataclass
class _ClassVal(_Value):
    fact: "ClassFact"

    def text(self) -> str:
        return self.fact.name


class _Marker(_Value):
    def __init__(self, name: str):
        self.name = name

    def text(self) -> str:
        return f"<{self.name}>"


_BUILD_CLASS = _Marker("build_class")
_IMPORTED = _Marker("import")


def _text(v) -> str:
    if isinstance(v, _Value):
        return v.text()
    if isinstance(v, types.CodeType):
        return f"<code {v.co_name}>"
    return repr(v)


def _items(v) -> list:
    """The elements of a tuple value, constant or built."""
    if isinstance(v, _Lit) and isinstance(v.value, tuple):
        return [_Lit(x) for x in v.value]
    if isinstance(v, _Seq):
        return list(v.items)
    return []


def _pairs(v) -> list:
    if isinstance(v, _Map):
        return list(v.pairs)
    if isinstance(v, _Lit) and isinstance(v.value, dict):
        return [(_Lit(k), _Lit(x)) for k, x in v.value.items()]
    return []


# --- facts ---------------------------------------------------------------------------------


@dataclass
class Param:
    name: str
    kind: str  # positional_only | positional_or_keyword | var_positional | keyword_only | var_keyword
    default: str | None = None  # source-like text; literal when default_literal
    default_literal: bool = False

    def as_dict(self) -> dict:
        d = {"name": self.name, "kind": self.kind}
        if self.default is not None:
            d["default"] = self.default
            d["default_literal"] = self.default_literal
        return d


@dataclass
class Member:
    """A name bound in a class or module body."""

    name: str
    kind: str  # method | property | classmethod | staticmethod | function | attribute
    line: int
    params: list[Param] | None = None  # functions only
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    value: str | None = None  # attributes only: source-like text of the value
    value_literal: bool = False
    setter: bool = False  # properties: a `@<name>.setter` follows

    def as_dict(self) -> dict:
        d: dict = {"kind": self.kind, "line": self.line}
        if self.params is not None:
            d["params"] = [p.as_dict() for p in self.params]
        if self.decorators:
            d["decorators"] = self.decorators
        if self.kind == "property":
            d["setter"] = self.setter
        if self.value is not None:
            d["value"] = self.value
            d["value_literal"] = self.value_literal
        if self.docstring:
            d["docstring"] = self.docstring
        return d


@dataclass
class ClassFact:
    name: str
    qualname: str
    bases: list[str]
    line: int
    keywords: dict[str, str] = field(default_factory=dict)  # e.g. {"metaclass": "Meta"}
    bases_parsed: bool = True  # False: a base expression we don't model; bases is then empty
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    members: dict[str, Member] = field(default_factory=dict)
    nested: list["ClassFact"] = field(default_factory=list)


@dataclass
class _Binding:
    name: str
    value: object
    line: int


@dataclass
class _Body:
    bindings: list[_Binding]
    classes: list[ClassFact]  # every class built in this body, in order


def _function_params(f: _Func) -> list[Param]:
    c = f.code
    names = c.co_varnames
    n_pos, n_kw, n_posonly = c.co_argcount, c.co_kwonlyargcount, c.co_posonlyargcount
    defaults = f.defaults
    first_default = n_pos - len(defaults)
    params = []
    for i in range(n_pos):
        kind = "positional_only" if i < n_posonly else "positional_or_keyword"
        p = Param(names[i], kind)
        if i >= first_default:
            d = defaults[i - first_default]
            p.default, p.default_literal = _cut(_text(d)), bool(getattr(d, "literal", False))
        params.append(p)
    idx = n_pos + n_kw
    if c.co_flags & inspect.CO_VARARGS:
        params.append(Param(names[idx], "var_positional"))
        idx += 1
    for name in names[n_pos : n_pos + n_kw]:
        p = Param(name, "keyword_only")
        if name in f.kwdefaults:
            d = f.kwdefaults[name]
            p.default, p.default_literal = _cut(_text(d)), bool(getattr(d, "literal", False))
        params.append(p)
    if c.co_flags & inspect.CO_VARKEYWORDS:
        params.append(Param(names[idx], "var_keyword"))
    return params


def _function_docstring(code: types.CodeType) -> str | None:
    # 3.11 puts a function's docstring (or None) first in co_consts; lambdas get None.
    first = code.co_consts[0] if code.co_consts else None
    return inspect.cleandoc(first) if isinstance(first, str) else None


_NOOPS = {"RESUME", "NOP", "PUSH_NULL", "PRECALL", "CACHE", "EXTENDED_ARG", "MAKE_CELL", "COPY_FREE_VARS"}
_JUMPS = {
    "JUMP_FORWARD", "JUMP_BACKWARD", "JUMP_BACKWARD_NO_INTERRUPT", "JUMP",
    "POP_JUMP_FORWARD_IF_FALSE", "POP_JUMP_FORWARD_IF_TRUE", "POP_JUMP_BACKWARD_IF_FALSE",
    "POP_JUMP_BACKWARD_IF_TRUE", "POP_JUMP_FORWARD_IF_NONE", "POP_JUMP_FORWARD_IF_NOT_NONE",
    "POP_JUMP_BACKWARD_IF_NONE", "POP_JUMP_BACKWARD_IF_NOT_NONE", "POP_JUMP_IF_FALSE",
    "POP_JUMP_IF_TRUE", "POP_JUMP_IF_NONE", "POP_JUMP_IF_NOT_NONE",
}


def _run_body(code: types.CodeType) -> _Body:
    """Simulate a module or class body. Unmodelled instructions turn values into UNKNOWN."""
    stack: list = []
    bindings: list[_Binding] = []
    classes: list[ClassFact] = []
    kw_names: tuple = ()
    line = code.co_firstlineno

    def pop():
        return stack.pop() if stack else UNKNOWN

    def pop_n(n: int) -> list:
        items = [pop() for _ in range(n)]
        items.reverse()
        return items

    for ins in dis.get_instructions(code):
        op = ins.opname
        if ins.positions and ins.positions.lineno:
            line = ins.positions.lineno
        if op in _NOOPS:
            continue
        if op in ("LOAD_NAME", "LOAD_GLOBAL", "LOAD_DEREF", "LOAD_FAST", "LOAD_CLASSDEREF"):
            stack.append(_Expr(ins.argval))
        elif op in ("LOAD_ATTR", "LOAD_METHOD"):
            stack.append(_Expr(f"{_text(pop())}.{ins.argval}"))
        elif op == "LOAD_CONST":
            stack.append(ins.argval if isinstance(ins.argval, types.CodeType) else _Lit(ins.argval))
        elif op == "LOAD_CLOSURE":
            stack.append(_Marker("cell"))
        elif op == "LOAD_BUILD_CLASS":
            stack.append(_BUILD_CLASS)
        elif op in ("BUILD_TUPLE", "BUILD_LIST", "BUILD_SET"):
            stack.append(_Seq(op[len("BUILD_") :].lower(), pop_n(ins.arg)))
        elif op == "BUILD_MAP":
            flat = pop_n(2 * ins.arg)
            stack.append(_Map(list(zip(flat[::2], flat[1::2]))))
        elif op == "BUILD_CONST_KEY_MAP":
            keys = _items(pop())
            values = pop_n(ins.arg)
            stack.append(_Map(list(zip(keys, values))))
        elif op in ("LIST_EXTEND", "SET_UPDATE"):
            extra = pop()
            target = stack[-1] if stack else None
            if isinstance(target, _Seq):
                if isinstance(extra, _Lit) and isinstance(extra.value, (tuple, list, frozenset, set)):
                    target.items.extend(_Lit(x) for x in extra.value)
                else:
                    target.items.append(_Expr(f"*{_text(extra)}"))
        elif op == "LIST_TO_TUPLE":
            top = pop()
            stack.append(_Seq("tuple", top.items) if isinstance(top, _Seq) else UNKNOWN)
        elif op == "BINARY_OP":  # a | b, X + 1
            right = pop()
            stack.append(_Expr(f"{_text(pop())} {ins.argrepr.rstrip('=')} {_text(right)}"))
        elif op == "BINARY_SUBSCR":  # Generic[T]
            index = pop()
            stack.append(_Expr(f"{_text(pop())}[{_text(index)}]"))
        elif op == "MAKE_FUNCTION":
            body = pop()
            flags = ins.arg or 0
            closure = pop() if flags & 0x08 else None  # noqa: F841
            annotations = pop() if flags & 0x04 else None  # noqa: F841
            kwdefaults = pop() if flags & 0x02 else None
            defaults = pop() if flags & 0x01 else None
            if isinstance(body, types.CodeType):
                stack.append(
                    _Func(
                        body,
                        defaults=_items(defaults) if defaults is not None else [],
                        kwdefaults={_text(k).strip("'\""): v for k, v in _pairs(kwdefaults)},
                    )
                )
            else:
                stack.append(UNKNOWN)
        elif op == "KW_NAMES":
            kw = ins.argval if isinstance(ins.argval, tuple) else code.co_consts[ins.arg]
            kw_names = kw if isinstance(kw, tuple) else ()
        elif op == "CALL":
            args = pop_n(ins.arg)
            callee = pop()
            n_kw = len(kw_names) if len(kw_names) <= len(args) else 0
            positional = args[: len(args) - n_kw]
            keywords = list(zip(kw_names, args[len(args) - n_kw :])) if n_kw else []
            kw_names = ()
            if callee is _BUILD_CLASS:
                fact = _class_from_call(positional, keywords)
                if fact:
                    classes.append(fact)
                    stack.append(_ClassVal(fact))
                else:
                    stack.append(UNKNOWN)
            elif isinstance(callee, (_Func, _ClassVal)) and not args and stack:
                # A decorator: 3.11 leaves the decorator below the function, with no NULL.
                decorator = pop()
                target = callee.decorators if isinstance(callee, _Func) else callee.fact.decorators
                target.insert(0, _text(decorator))
                stack.append(callee)
            else:
                stack.append(_Call(_text(callee), positional, keywords))
        elif op == "CALL_FUNCTION_EX":
            kwargs = pop() if (ins.arg or 0) & 1 else None
            args = pop()
            callee = pop()
            if callee is _BUILD_CLASS and isinstance(args, _Seq):
                fact = _class_from_call(args.items, [])
                if fact:
                    classes.append(fact)
                    stack.append(_ClassVal(fact))
                    continue
            extra = f", **{_text(kwargs)}" if kwargs is not None else ""
            stack.append(_Expr(f"{_text(callee)}(*{_text(args)}{extra})"))
        elif op == "COPY":
            stack.append(stack[-ins.arg] if len(stack) >= ins.arg else UNKNOWN)
        elif op == "SWAP":
            if len(stack) >= ins.arg:
                stack[-1], stack[-ins.arg] = stack[-ins.arg], stack[-1]
        elif op == "IMPORT_NAME":
            pop_n(2)
            stack.append(_IMPORTED)
        elif op == "IMPORT_FROM":
            stack.append(_IMPORTED)
        elif op in ("STORE_NAME", "STORE_GLOBAL"):
            bindings.append(_Binding(ins.argval, pop(), line))
        elif op in _JUMPS:
            if op.startswith("POP_"):
                pop()
        else:
            try:
                effect = dis.stack_effect(ins.opcode, ins.arg if ins.opcode >= dis.HAVE_ARGUMENT else None, jump=False)
            except ValueError:
                effect = 0
            if effect < 0:
                pop_n(-effect)
            if stack and effect <= 0:
                stack[-1] = UNKNOWN
            stack.extend([UNKNOWN] * max(effect, 0))
    return _Body(bindings, classes)


def _class_from_call(positional: list, keywords: list) -> ClassFact | None:
    if not positional or not isinstance(positional[0], _Func):
        return None
    func, bases = positional[0], positional[2:]
    base_texts = [_text(b) for b in bases]
    kw = {k: _text(v) for k, v in keywords}
    parsed = all(isinstance(b, (_Expr, _ClassVal)) and b is not UNKNOWN for b in bases) and not any(
        t.startswith("*") or "…" in t for t in base_texts
    )
    return _class_fact(func.code, base_texts if parsed else [], kw, parsed)


def _members(body: _Body, in_class: bool, skip: set[str]) -> tuple[dict[str, Member], str | None]:
    members: dict[str, Member] = {}
    docstring = None
    for b in body.bindings:
        if b.name == "__doc__":
            if isinstance(b.value, _Lit) and isinstance(b.value.value, str):
                docstring = inspect.cleandoc(b.value.value)
            continue
        if b.name in skip or b.value is _IMPORTED or isinstance(b.value, _ClassVal):
            continue
        v = b.value
        if isinstance(v, _Func):
            setter_of = next((d for d in v.decorators if d in (f"{b.name}.setter", f"{b.name}.deleter")), None)
            existing = members.get(b.name)
            if setter_of and existing and existing.kind == "property":
                existing.setter = existing.setter or setter_of.endswith(".setter")
                continue
            kind = "function"
            if in_class:
                kind = "method"
                for d in v.decorators:
                    if d in ("property", "classmethod", "staticmethod"):
                        kind = d
            members[b.name] = Member(
                name=b.name,
                kind=kind,
                line=v.code.co_firstlineno,
                params=_function_params(v),
                decorators=list(v.decorators),
                docstring=_function_docstring(v.code),
            )
        else:
            members[b.name] = Member(
                name=b.name,
                kind="attribute",
                line=b.line,
                value=_cut(_text(v)),
                value_literal=bool(getattr(v, "literal", False)),
            )
    return members, docstring


_CLASS_BODY_NAMES = {"__module__", "__qualname__", "__classcell__", "__static_attributes__"}


def _class_fact(body_code: types.CodeType, bases: list[str], keywords: dict[str, str], parsed: bool) -> ClassFact:
    body = _run_body(body_code)
    members, docstring = _members(body, in_class=True, skip=_CLASS_BODY_NAMES)
    return ClassFact(
        name=body_code.co_name,
        qualname=body_code.co_qualname,
        bases=bases,
        line=body_code.co_firstlineno,
        keywords=keywords,
        bases_parsed=parsed,
        docstring=docstring,
        members=members,
        nested=body.classes,
    )


def find_classes(code: types.CodeType) -> list[ClassFact]:
    """Classes defined in a module or class body (not inside functions)."""
    return _run_body(code).classes


# --- one module ----------------------------------------------------------------------------


@dataclass
class ModuleFacts:
    name: str
    is_package: bool
    source: str  # e.g. "MIDI Remote Scripts/ableton/v3/…pyc"
    classes: list[ClassFact]
    imports: dict[str, str]  # bound name -> qualified name
    imported_modules: set[str]
    members: dict[str, Member]  # module-level functions and attributes
    docstring: str | None


def _flatten(classes: list[ClassFact]) -> list[ClassFact]:
    out = []
    for c in classes:
        out.append(c)
        out.extend(_flatten(c.nested))
    return out


def read_module(path: Path, root: Path, source_prefix: str | None = None) -> ModuleFacts:
    rel = path.relative_to(root)
    name, is_package = module_name(rel)
    code = load_code(path)
    body = _run_body(code)
    imports = collect_imports(code, name, is_package)
    members, docstring = _members(body, in_class=False, skip=set(imports) | {"__all__"})
    return ModuleFacts(
        name=name,
        is_package=is_package,
        source=str(Path(source_prefix or root.name) / rel),
        classes=_flatten(body.classes),
        imports=imports,
        imported_modules=imported_modules(code, name, is_package),
        members=members,
        docstring=docstring,
    )


def iter_pyc(root: Path, packages: tuple[str, ...] | None = None):
    """Every .pyc under `root` (or under the named top-level packages), skipping __pycache__."""
    tops = [root / p for p in packages] if packages else [root]
    for top in tops:
        if not top.is_dir():
            continue
        for path in sorted(top.rglob("*.pyc")):
            if "__pycache__" in path.relative_to(root).parts:
                continue
            yield path


_BUILTINS = {"object", "Exception", "dict", "list", "tuple", "str", "int", "float", "type", "property",
             "BaseException", "RuntimeError", "ValueError", "KeyError", "IndexError", "TypeError",
             "AttributeError", "NotImplementedError", "set", "frozenset", "bool", "bytes"}


def resolve_base(base: str, imports: dict[str, str], module: str, local_classes: set[str]) -> str | None:
    """The qualified name a base expression points at, as far as this module's imports tell."""
    if "[" in base:  # Generic[T] -> typing.Generic[T]
        core, _, subscript = base.partition("[")
        resolved = resolve_base(core, imports, module, local_classes)
        return f"{resolved}[{subscript}" if resolved else None
    head, _, rest = base.partition(".")
    if base in local_classes:
        return f"{module}.{base}"
    if head in imports:
        return imports[head] + (f".{rest}" if rest else "")
    if head in _BUILTINS:
        return f"builtins.{base}"
    return None
