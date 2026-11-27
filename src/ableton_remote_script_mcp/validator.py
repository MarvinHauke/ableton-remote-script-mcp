"""Validator: a static check of a Remote Script folder against one Live build's API index.

It reads the script's `.py` sources with Python's own parser and never runs them. Each finding
has a file (relative to the folder), a line, a rule, a severity, a message and a fix. A broken
file becomes a finding, never a crash.

Basic checks (plan 0001 step 7):
- `folder-name`: the script folder's name has no spaces and is a Python name, since Live
  imports the script by it.
- `syntax-error`: every source parses as Python 3.11 (Live's Python).
- `create-instance`: `__init__.py` defines `create_instance`, and it takes the `c_instance`
  argument Live passes.
- `unresolved-import`: every import resolves in that build: to the script's own modules, the
  Remote Scripts folder, or the Python that Live ships (its `lib` and `site-packages`), all as the
  index records them. An import inside a `try` that handles `ImportError` is optional and not
  checked.

Some imports cannot be decided from the index; they are listed under `not_checked`, with the
reason: the C++ modules Live itself provides (`LIVE_MODULES`), and the C modules of Python's
standard library, which are built into Live's binary and have no file (all of the standard
library when the index has no record of Live's Python). Below a top-level Python
module (`xml.etree`), names are not checked.

Framework checks (plan 0001 step 8): see `framework_checks.py`. Their findings have the
severity `error` or `warning`; what they cannot decide is listed under `not_checked` too.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .elements import read_elements
from .framework_checks import (
    LIVE_PYTHON,
    check_framework,
    compile_sources,
    overlay_index,
)
from .index_store import SCRIPTS_ROOT
from .outline import Outliner

SKIP_DIRS = {"__pycache__"}
LIVE_MODULES = ("Live", "MidiRemoteScript")  # provided by Live's C++ code, not files
_IMPORT_ERRORS = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}


@dataclass
class Source:
    """One parsed file of the script: its module name and the names its top level binds."""

    path: str  # relative to the script folder, with forward slashes
    module: str
    is_package: bool
    tree: ast.Module | None = None
    binds: set[str] = field(default_factory=set)
    star: bool = False  # a `from … import *` at the top level: its names are not known here


def _finding(rule: str, file: str, line: int | None, message: str, fix: str, severity: str = "error") -> dict:
    return {"file": file, "line": line, "rule": rule, "severity": severity, "message": message, "fix": fix}


def _module_name(package: str, rel: Path) -> tuple[str, bool]:
    parts = list(rel.with_suffix("").parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts = parts[:-1]
    return ".".join([package, *parts]), is_package


def _top_level_binds(body: list[ast.stmt], src: Source) -> None:
    """Names the module's top level binds, also inside `if`/`try`/`with`/loops (not function bodies)."""
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            src.binds.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    src.star = True
                else:
                    src.binds.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor, ast.With,
                               ast.AsyncWith)):
            targets = node.targets if isinstance(node, ast.Assign) else [
                getattr(node, "target", None), *[i.optional_vars for i in getattr(node, "items", [])]]
            for t in targets:
                for n in ast.walk(t) if t is not None else ():
                    if isinstance(n, ast.Name):
                        src.binds.add(n.id)
        for name in ("body", "orelse", "finalbody"):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                _top_level_binds(getattr(node, name, []) or [], src)
        for handler in getattr(node, "handlers", []) or []:
            _top_level_binds(handler.body, src)


def _optional_imports(tree: ast.Module) -> set[int]:
    """ids of import nodes inside a `try` whose handlers catch an import failure."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Try, ast.TryStar)):
            continue
        caught = set()
        for h in node.handlers:
            types = h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]
            caught |= {"BaseException" if t is None else ast.unparse(t).rsplit(".", 1)[-1] for t in types}
        if caught & _IMPORT_ERRORS:
            for stmt in node.body:
                out |= {id(n) for n in ast.walk(stmt) if isinstance(n, (ast.Import, ast.ImportFrom))}
    return out


class _Imports:
    """Where an imported module comes from: the script itself, the index, the standard library."""

    def __init__(self, index: dict, script: str, sources: dict[str, Source]):
        self.index = index
        self.script = script
        self.local = sources  # module name -> Source
        self.tops = {m["name"].split(".")[0] for m in index["modules"].values() if m["root"] == SCRIPTS_ROOT}
        self.python = index.get("python", {}).get("modules")  # None: the bundle had no Python folder
        self.build = index["live_build"]

    def where(self, module: str) -> str:
        """local, index, python (Live's Python files), builtin (compiled into the interpreter
        itself), live (LIVE_MODULES), c-stdlib (a C extension module of Python's standard library:
        Live's files cannot show it), not-shipped (a pure-Python standard library module Live
        leaves out) or missing."""
        top = module.split(".")[0]
        if top == self.script:
            return "local"
        if top in LIVE_MODULES:
            return "live"
        if top in self.tops:
            return "index"
        if self.python is None:
            if top in sys.stdlib_module_names or top in sys.builtin_module_names:
                return "c-stdlib"  # no record of Live's Python: the standard library is not checked
            return "missing"
        if top in self.python:
            return "python"
        if top in sys.builtin_module_names:
            return "builtin"  # compiled into every CPython 3.11 (sys, builtins, itertools, …)
        if top in sys.stdlib_module_names:
            spec = importlib.util.find_spec(top)
            origin = (spec.origin or "") if spec else ""
            return "c-stdlib" if origin.endswith((".so", ".pyd")) else "not-shipped"
        return "missing"

    def module_exists(self, module: str) -> bool:
        where = self.where(module)
        if where == "local":
            return module in self.local
        if where == "index":
            return module in self.index["modules"]
        return where in ("python", "builtin", "live", "c-stdlib")

    def binds(self, module: str, name: str, seen: frozenset = frozenset()) -> bool:
        """Does `from module import name` find something?"""
        if f"{module}.{name}" in self.local or f"{module}.{name}" in self.index["modules"]:
            return True  # a submodule
        if module in seen:
            return False
        if module in self.local:
            src = self.local[module]
            return src.tree is None or src.star or name in src.binds  # unparsed: its error is the finding
        mod = self.index["modules"].get(module)
        if mod is None:
            return True  # outside the Remote Scripts folder: names are not checked
        if name in mod.get("imports", {}) or name in mod.get("members", {}):
            return True
        if f"{module}.{name}" in self.index["classes"]:  # classes are kept apart from module members
            return True
        return any(self.binds(star, name, seen | {module}) for star in mod.get("star_imports", []))


def _check_imports(src: Source, imports: _Imports, findings: list[dict], not_checked: list[dict]) -> None:
    optional = _optional_imports(src.tree)
    package = src.module if src.is_package else src.module.rpartition(".")[0]
    build = imports.build

    def missing_module(node: ast.stmt, module: str, text: str) -> None:
        where = imports.where(module)
        if where == "local" and module == imports.script:
            return  # no __init__.py: the create-instance finding covers it
        if where == "local":
            message = f"`{text}`: the script has no module {module}"
            fix = f"add {module[len(imports.script) + 1:].replace('.', '/')}.py to the script, or correct the name"
        elif where == "index":
            message = f"`{text}`: no module {module} in Live {build}"
            fix = (f"look the name up with `search {module.rsplit('.', 1)[-1]} --build {build}` "
                   "and import it from the module that has it")
        elif where == "not-shipped":
            message = f"`{text}`: {module.split('.')[0]} is in Python's standard library, but Live {build} does not ship it"
            fix = "do without it, or put the code you need inside the script's folder"
        else:
            message = (f"`{text}`: {module.split('.')[0]} is neither in Live {build}'s Remote Scripts folder "
                       "nor in the Python that Live ships")
            fix = "use a module Live ships, or put the code inside the script's folder"
        if where != "local":  # Python 2's implicit relative import: a module next to this one
            parts = package.split(".")
            for i in range(len(parts), 0, -1):
                if ".".join([*parts[:i], module]) in imports.local:
                    dots = "." * (len(parts) - i + 1)
                    form = (f"from {dots} import {module}" if isinstance(node, ast.Import)
                            else f"from {dots}{module} import …")
                    fix = f"it is a module of this script: import it relatively (`{form}`)"
                    break
        findings.append(_finding("unresolved-import", src.path, node.lineno, message, fix))

    def unchecked(node: ast.stmt, module: str, text: str) -> bool:
        where = imports.where(module)
        reasons = {"live": f"{module.split('.')[0]} is provided by Live's own C++ code, not by files the index reads",
                   "c-stdlib": f"{module.split('.')[0]} is a C module of Python's standard library: "
                               "Live's files cannot show whether its binary has it built in"}
        if where in reasons:
            not_checked.append({"file": src.path, "line": node.lineno, "rule": "unresolved-import", "what": text,
                                "import": text, "reason": reasons[where]})
        return where in reasons

    for node in ast.walk(src.tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)) or id(node) in optional:
            continue
        text = ast.unparse(node)
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.replace(".__init__", "")
                if not unchecked(node, module, text) and not imports.module_exists(module):
                    missing_module(node, module, text)
            continue
        if node.level:
            base = package.split(".")
            if node.level - 1 >= len(base):
                findings.append(_finding(
                    "unresolved-import", src.path, node.lineno,
                    f"`{text}` goes above the script's own package",
                    "use fewer dots, or import the module by its absolute name"))
                continue
            base = base[: len(base) - (node.level - 1)]
            module = ".".join(base + ([node.module] if node.module else []))
        else:
            module = node.module or ""
        module = module.replace(".__init__", "")  # `pkg.__init__` is the package itself
        if unchecked(node, module, text):
            continue
        if not imports.module_exists(module):
            missing_module(node, module, text)
            continue
        if imports.where(module) == "python":
            continue
        for alias in node.names:
            if alias.name != "*" and not imports.binds(module, alias.name):
                where = "the script's" if imports.where(module) == "local" else f"Live {build}'s"
                fix = (f"look the name up with `search {alias.name} --build {build}` and import it from "
                       "the module that defines it" if imports.where(module) == "index"
                       else f"define {alias.name} in {module}, or correct the name")
                findings.append(_finding(
                    "unresolved-import", src.path, node.lineno,
                    f"`{text}`: {where} module {module} has no name {alias.name}", fix))


def _check_create_instance(init: Source | None, folder: Path, findings: list[dict]) -> None:
    if init is None:
        compiled = (folder / "__init__.pyc").is_file()
        findings.append(_finding(
            "create-instance", "__init__.py", None,
            "the folder has no __init__.py, so Live cannot load it as a Remote Script"
            + (" (it has only compiled .pyc files; the validator reads .py sources)" if compiled else ""),
            "add an __init__.py that defines `def create_instance(c_instance):` returning the control surface"))
        return
    if init.tree is None:
        return  # its syntax error is already a finding
    fn = next((n for n in init.tree.body if isinstance(n, ast.FunctionDef) and n.name == "create_instance"), None)
    if fn is None:
        if "create_instance" in init.binds:
            return  # imported or assigned: Live only needs the name
        findings.append(_finding(
            "create-instance", init.path, 1,
            "__init__.py does not define create_instance, so Live cannot create the control surface",
            "add `def create_instance(c_instance):` that returns the control surface, built with c_instance"))
        return
    a = fn.args
    positional = a.posonlyargs + a.args
    required_kw = [k for k, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]
    takes_one = (len(positional) - len(a.defaults) <= 1 and (len(positional) >= 1 or a.vararg)) and not required_kw
    if not takes_one:
        findings.append(_finding(
            "create-instance", init.path, fn.lineno,
            f"create_instance({ast.unparse(a)}) cannot be called with the one argument Live passes",
            "declare it as `def create_instance(c_instance):`"))


def read_sources(folder: Path, findings: list[dict]) -> tuple[dict[str, Source], list[Path]]:
    """Parse every `.py` file of a script folder as Live's Python would; a file that can't be read
    or parsed is a `syntax-error` finding and has no tree."""
    script = folder.name
    sources: dict[str, Source] = {}
    paths = sorted(p for p in folder.rglob("*.py")
                   if not (set(p.relative_to(folder).parts[:-1]) & SKIP_DIRS)
                   and not any(part.startswith(".") for part in p.relative_to(folder).parts))
    for path in paths:
        rel = path.relative_to(folder)
        module, is_package = _module_name(script, rel)
        src = Source(rel.as_posix(), module, is_package)
        sources[module] = src
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            findings.append(_finding("syntax-error", src.path, None, f"cannot be read as UTF-8 source ({e})",
                                     "save the file as UTF-8"))
            continue
        try:
            src.tree = ast.parse(text, filename=src.path, feature_version=LIVE_PYTHON)
        except (SyntaxError, ValueError) as e:  # Python 3.11 raises ValueError for null bytes
            findings.append(_finding("syntax-error", src.path, getattr(e, "lineno", None),
                                     getattr(e, "msg", None) or str(e),
                                     f"fix the syntax (Live runs Python {'.'.join(map(str, LIVE_PYTHON))})"))
            continue
        _top_level_binds(src.tree.body, src)
    return sources, paths


def element_names_of_folder(folder: Path, index: dict) -> tuple[set[str], str]:
    """(the element names a script folder's Elements class builds, against an index with
    statements; why they couldn't be read, or ""). A script without an Elements class has none,
    and that needs no reason."""
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


def validate_folder(folder: Path, index: dict) -> dict:
    """The findings for one script folder against one loaded index (see the module docstring)."""
    script = folder.name
    findings: list[dict] = []
    not_checked: list[dict] = []
    if " " in script:
        suggested = "_".join(script.split())
        findings.append(_finding(
            "folder-name", ".", None,
            f"the folder name {script!r} has spaces: Live does not list it as a control surface",
            f"rename the folder to {suggested!r}"))
    elif not script.isidentifier():
        suggested = re.sub(r"\W", "_", script)
        suggested = suggested if suggested.isidentifier() else f"_{suggested}"
        findings.append(_finding(
            "folder-name", ".", None,
            f"the folder name {script!r} is not a Python name: Live imports the script by its folder name, "
            "and the import fails with a SyntaxError",
            f"rename the folder to {suggested!r}"))
    sources, paths = read_sources(folder, findings)
    _check_create_instance(sources.get(script), folder, findings)
    imports = _Imports(index, script, sources)
    for src in sources.values():
        if src.tree is not None:
            _check_imports(src, imports, findings, not_checked)
    check_framework(index, script, sources, findings, not_checked)
    findings.sort(key=lambda f: (f["file"] != ".", f["file"], f["line"] or 0, f["rule"]))
    not_checked.sort(key=lambda n: (n["file"], n["line"] or 0))
    return {"script": script, "folder": str(folder), "files": len(paths), "findings": findings,
            "not_checked": not_checked}
