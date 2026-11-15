"""Read the .pyc files of one Live build into index facts.

Code objects are loaded with marshal under CPython 3.11, never decompiled or executed.
Classes are found by simulating the few instructions between LOAD_BUILD_CLASS and its CALL.
"""

from __future__ import annotations

import dis
import importlib.util
import marshal
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

PYC_HEADER_SIZE = 16

# Framework generations. Controller scripts come in plan 0001 step 2.
FRAMEWORK_PACKAGES = ("_Framework", "ableton")


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


def _resolve_relative(module: str, is_package: bool, level: int, name: str) -> str:
    if level == 0:
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


# --- classes -------------------------------------------------------------------------------


class _Expr(str):
    """A base expression as written in the source, e.g. 'ControlSurface' or 'v3.Component'."""


_BUILD_CLASS = object()


@dataclass
class _Func:
    code: types.CodeType


@dataclass
class ClassFact:
    name: str
    qualname: str
    bases: list[str]
    line: int
    keywords: dict[str, str] = field(default_factory=dict)  # e.g. {"metaclass": "Meta"}
    bases_parsed: bool = True  # False: a base expression we don't model; bases is then empty
    nested: list["ClassFact"] = field(default_factory=list)


def _simulate_class(
    instrs: list[dis.Instruction], start: int, consts: tuple
) -> tuple[ClassFact | None, int]:
    """Run the stack from LOAD_BUILD_CLASS at `start` to its CALL. Returns (fact, next index)."""
    stack: list[object] = [_BUILD_CLASS]
    kw_names: tuple = ()
    i = start + 1
    while i < len(instrs):
        ins = instrs[i]
        op = ins.opname
        if op in ("PUSH_NULL", "PRECALL", "CACHE", "EXTENDED_ARG", "NOP"):
            pass
        elif op in ("LOAD_NAME", "LOAD_GLOBAL", "LOAD_DEREF", "LOAD_FAST", "LOAD_CLASSDEREF"):
            stack.append(_Expr(ins.argval))
        elif op in ("LOAD_ATTR", "LOAD_METHOD"):
            stack.append(_Expr(f"{stack.pop()}.{ins.argval}"))
        elif op == "LOAD_CONST":
            stack.append(ins.argval if isinstance(ins.argval, types.CodeType) else _Expr(repr(ins.argval)))
        elif op == "LOAD_CLOSURE":
            stack.append(None)
        elif op == "BINARY_SUBSCR":  # Generic[T]
            index = stack.pop()
            stack.append(_Expr(f"{stack.pop()}[{index}]"))
        elif op == "BUILD_TUPLE":
            n = ins.arg
            items = stack[len(stack) - n :] if n else []
            del stack[len(stack) - n :]
            stack.append(_Expr("(" + ", ".join(map(str, items)) + ")"))
        elif op == "MAKE_FUNCTION":
            code = stack.pop()
            flags = ins.arg or 0
            for bit in (0x08, 0x04, 0x02, 0x01):  # closure, annotations, kwdefaults, defaults
                if flags & bit:
                    stack.pop()
            stack.append(_Func(code) if isinstance(code, types.CodeType) else _Expr("<function>"))
        elif op == "KW_NAMES":
            # 3.11's dis leaves argval unresolved; arg indexes co_consts
            kw = ins.argval if isinstance(ins.argval, tuple) else consts[ins.arg]
            kw_names = kw if isinstance(kw, tuple) else ()
        elif op == "CALL":
            n = ins.arg
            args = stack[len(stack) - n :] if n else []
            del stack[len(stack) - n :]
            callee = stack.pop()
            if callee is _BUILD_CLASS:
                n_kw = len(kw_names)
                positional = args[: len(args) - n_kw] if n_kw else args
                keywords = dict(zip(kw_names, map(str, args[len(args) - n_kw :]))) if n_kw else {}
                func, bases = positional[0], positional[2:]
                if not isinstance(func, _Func):
                    return None, i + 1
                return _fact(func.code, [str(b) for b in bases], keywords), i + 1
            stack.append(_Expr(f"{callee}(...)"))
            kw_names = ()
        else:
            break  # an expression we don't model
        i += 1
    # Keep the class, without its bases, rather than lose it.
    body = next(
        (x.argval for x in instrs[start + 1 :] if x.opname == "LOAD_CONST" and isinstance(x.argval, types.CodeType)),
        None,
    )
    if body is None:
        return None, i + 1
    fact = _fact(body, [], {})
    fact.bases_parsed = False
    return fact, i + 1


def _fact(body: types.CodeType, bases: list[str], keywords: dict[str, str]) -> ClassFact:
    fact = ClassFact(
        name=body.co_name,
        qualname=body.co_qualname,
        bases=bases,
        line=body.co_firstlineno,
        keywords=keywords,
    )
    fact.nested = find_classes(body)
    return fact


def find_classes(code: types.CodeType) -> list[ClassFact]:
    """Classes defined in a module or class body (not inside functions)."""
    instrs = [i for i in dis.get_instructions(code) if i.opname != "CACHE"]
    found = []
    i = 0
    while i < len(instrs):
        if instrs[i].opname == "LOAD_BUILD_CLASS":
            fact, i = _simulate_class(instrs, i, code.co_consts)
            if fact:
                found.append(fact)
        else:
            i += 1
    return found


# --- one module ----------------------------------------------------------------------------


@dataclass
class ModuleFacts:
    name: str
    is_package: bool
    source: str  # path relative to the Remote Scripts folder's parent, e.g. "MIDI Remote Scripts/…"
    classes: list[ClassFact]
    imports: dict[str, str]


def _flatten(classes: list[ClassFact]) -> list[ClassFact]:
    out = []
    for c in classes:
        out.append(c)
        out.extend(_flatten(c.nested))
    return out


def read_module(path: Path, scripts_root: Path) -> ModuleFacts:
    rel = path.relative_to(scripts_root)
    name, is_package = module_name(rel)
    code = load_code(path)
    return ModuleFacts(
        name=name,
        is_package=is_package,
        source=str(Path(scripts_root.name) / rel),
        classes=_flatten(find_classes(code)),
        imports=collect_imports(code, name, is_package),
    )


def iter_pyc(scripts_root: Path, packages: tuple[str, ...] = FRAMEWORK_PACKAGES):
    for pkg in packages:
        root = scripts_root / pkg
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.pyc")):
            if "__pycache__" in path.parts:
                continue
            yield path


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
    if head in ("object", "Exception", "dict", "list", "tuple", "str", "int", "float", "type", "property"):
        return f"builtins.{base}"
    return None
