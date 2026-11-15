"""The API index on disk: one JSON document per Live build (plan 0001, Decision 22).

Schema 2 (plan 0001 step 2). Keys of `packages`, `modules` and `classes` are qualified names;
facts from the Push 3 helper's own Python carry the prefix `push3-helper:`, because it ships
its own, different copies of packages such as `ableton` and `Push2`.

    {
      "schema": 2,
      "live_build": "12.4.16",
      "source": {"kind": "installed-app", "app": "...", "bundle_version": "..."},
      "extractor": {"tool_version": "...", "python": "3.11.12"},
      "created": "2026-11-15T12:00:00+00:00",
      "roots": {"scripts": {"path": "Contents/App-Resources/MIDI Remote Scripts"},
                "push3-helper": {"path": "Contents/Helpers/Push3.app/Contents/Resources/python"}},
      "summary": {"packages": n, "scripts": n, "modules": n, "classes": n, "errors": n},
      "packages": {"APC_mini": {"name", "root", "kind": "framework" | "script" | "library",
                   "framework": "_Framework" | "ableton.v2" | "ableton.v3" | null,
                   "framework_imports": {"_Framework": 12}, "uses": ["_APC"],
                   "source", "live_build", "confidence"}},
      "modules": {"<key>": {"name", "root", "source", "package": bool, "docstring",
                  "imports": {"<bound name>": "<qualified name>"},
                  "members": {"<name>": <member>}, "live_build", "confidence"}},
      "classes": {"<key>": {"name", "qualname", "module", "root", "line",
                  "bases": [{"expr": "Component", "resolved": "ableton.v3….Component" | null}],
                  "keywords": {"metaclass": "Meta"}, "bases_parsed": true, "decorators": [...],
                  "docstring", "members": {"<name>": <member>},
                  "source", "live_build", "confidence": "observed"}},
      "errors": [{"source": "...", "root": "...", "error": "..."}]
    }

A member is {"kind": "method" | "property" | "classmethod" | "staticmethod" | "function" |
"attribute", "line", "params": [{"name", "kind", "default", "default_literal"}], "decorators",
"setter" (properties), "value" and "value_literal" (attributes), "docstring"}. Defaults and
values are source-like text; "…" marks an expression the extractor does not model.

Everything under `live_model` (Push 3 helper) is a pure-Python proxy of the `Live` module,
not Live itself: it carries "proxy_model": true, and its classes under `live_model.Live` name
the class they model in "proxy_of" (e.g. "Live.Song.Song").

The index holds facts extracted from Ableton's code, so it lives outside git.
"""

from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .extractor import FRAMEWORK_PACKAGES, ModuleFacts, UnreadablePyc, iter_pyc, read_module, resolve_base
from .live_install import PUSH3_HELPER_SUBPATH, SCRIPTS_SUBPATH, LiveInstall, build_sort_key

SCHEMA_VERSION = 2
INDEX_DIR_ENV = "ABLETON_REMOTE_SCRIPT_INDEX"
SCRIPTS_ROOT = "scripts"
PUSH3_HELPER_ROOT = "push3-helper"
GENERATIONS = ("_Framework", "ableton.v2", "ableton.v3")  # oldest first
PROXY_PACKAGE = "live_model"


def default_index_dir() -> Path:
    if os.environ.get(INDEX_DIR_ENV):
        return Path(os.environ[INDEX_DIR_ENV]).expanduser()
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return data_home / "ableton-remote-script-mcp" / "index"


def index_path(index_dir: Path, live_build: str) -> Path:
    return index_dir / f"live-{live_build}.json"


def fact_key(root: str, name: str) -> str:
    return name if root == SCRIPTS_ROOT else f"{root}:{name}"


def _generation(module: str) -> str | None:
    for gen in reversed(GENERATIONS):
        if module == gen or module.startswith(gen + "."):
            return gen
    return None


def _packages(mods: list[ModuleFacts], root: str, build: str, source_prefix: str) -> dict[str, dict]:
    """Top-level packages of one root: their kind and the framework generation they build on.

    A package's framework is the generation its own module-level imports bind most often
    (newest wins a tie). A package that imports no framework itself takes the framework of
    the libraries it imports, e.g. a script built on `_Generic`.
    """
    by_pkg: dict[str, list[ModuleFacts]] = {}
    for m in mods:
        by_pkg.setdefault(m.name.split(".")[0], []).append(m)
    counts: dict[str, dict[str, int]] = {}
    deps: dict[str, list[str]] = {}
    for pkg, pkg_mods in by_pkg.items():
        c = {g: 0 for g in GENERATIONS}
        dep: set[str] = set()
        for m in pkg_mods:
            for target in m.imports.values():
                gen = _generation(target)
                if gen:
                    c[gen] += 1
                elif target.split(".")[0] in by_pkg and target.split(".")[0] != pkg:
                    dep.add(target.split(".")[0])
        counts[pkg] = {g: n for g, n in c.items() if n}
        deps[pkg] = sorted(dep - set(FRAMEWORK_PACKAGES))

    primary: dict[str, str | None] = {}

    def framework_of(pkg: str, seen: frozenset = frozenset()) -> str | None:
        if pkg in primary:
            return primary[pkg]
        c = counts[pkg]
        if c:
            result = max(c, key=lambda g: (c[g], GENERATIONS.index(g)))
        else:
            found = [framework_of(d, seen | {pkg}) for d in deps[pkg] if d not in seen]
            found = [f for f in found if f]
            result = max(found, key=GENERATIONS.index) if found else None
        primary[pkg] = result
        return result

    out = {}
    for pkg, pkg_mods in sorted(by_pkg.items()):
        init = next((m for m in pkg_mods if m.name == pkg), None)
        create = init.members.get("create_instance") if init else None
        if pkg in FRAMEWORK_PACKAGES:
            kind = "framework"
        elif create is not None and create.kind == "function":
            kind = "script"
        else:
            kind = "library"
        entry = {
            "name": pkg,
            "root": root,
            "kind": kind,
            "framework": None if kind == "framework" else framework_of(pkg),
            "framework_imports": counts[pkg],
            "uses": deps[pkg],
            "source": f"{source_prefix}/{pkg}",
            "live_build": build,
            "confidence": "observed",
        }
        if pkg == PROXY_PACKAGE and root == PUSH3_HELPER_ROOT:
            entry["proxy_model"] = True
        out[fact_key(root, pkg)] = entry
    return out


def _members(members: dict) -> dict:
    return {name: m.as_dict() for name, m in members.items()}


def build_index(install: LiveInstall) -> dict:
    build = install.live_build
    roots = [(SCRIPTS_ROOT, install.scripts_root, SCRIPTS_SUBPATH)]
    if install.push3_helper_root:
        roots.append((PUSH3_HELPER_ROOT, install.push3_helper_root, PUSH3_HELPER_SUBPATH))
    packages: dict[str, dict] = {}
    modules: dict[str, dict] = {}
    classes: dict[str, dict] = {}
    errors: list[dict] = []
    for root, root_path, subpath in roots:
        prefix = root_path.name if root == SCRIPTS_ROOT else str(subpath.relative_to("Contents"))
        read: list[ModuleFacts] = []
        for path in iter_pyc(root_path):
            try:
                read.append(read_module(path, root_path, prefix))
            except (UnreadablePyc, OSError) as e:
                errors.append({"source": f"{prefix}/{path.relative_to(root_path)}", "root": root, "error": str(e)})
        packages.update(_packages(read, root, build, prefix))
        for mod in read:
            proxy = root == PUSH3_HELPER_ROOT and mod.name.split(".")[0] == PROXY_PACKAGE
            entry = {
                "name": mod.name,
                "root": root,
                "source": mod.source,
                "package": mod.is_package,
                "imports": mod.imports,
                "members": _members(mod.members),
                "live_build": build,
                "confidence": "observed",
            }
            if mod.docstring:
                entry["docstring"] = mod.docstring
            if proxy:
                entry["proxy_model"] = True
            modules[fact_key(root, mod.name)] = entry
            top_level = {c.qualname for c in mod.classes}
            for c in mod.classes:
                fact = {
                    "name": c.name,
                    "qualname": c.qualname,
                    "module": mod.name,
                    "root": root,
                    "line": c.line,
                    "bases": [
                        {"expr": b, "resolved": resolve_base(b, mod.imports, mod.name, top_level)}
                        for b in c.bases
                    ],
                    "keywords": c.keywords,
                    "bases_parsed": c.bases_parsed,
                    "decorators": c.decorators,
                    "members": _members(c.members),
                    "source": mod.source,
                    "live_build": build,
                    "confidence": "observed",
                }
                if c.docstring:
                    fact["docstring"] = c.docstring
                if proxy:
                    fact["proxy_model"] = True
                    if mod.name.startswith(PROXY_PACKAGE + ".Live."):
                        fact["proxy_of"] = f"{mod.name[len(PROXY_PACKAGE) + 1 :]}.{c.qualname}"
                classes[fact_key(root, f"{mod.name}.{c.qualname}")] = fact
    return {
        "schema": SCHEMA_VERSION,
        "live_build": build,
        "source": {"kind": "installed-app", "app": str(install.app), "bundle_version": install.bundle_version},
        "extractor": {"tool_version": __version__, "python": platform.python_version()},
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "roots": {root: {"path": str(subpath)} for root, _, subpath in roots},
        "summary": {
            "packages": len(packages),
            "scripts": sum(p["kind"] == "script" for p in packages.values()),
            "modules": len(modules),
            "classes": len(classes),
            "errors": len(errors),
        },
        "packages": packages,
        "modules": dict(sorted(modules.items())),
        "classes": dict(sorted(classes.items())),
        "errors": errors,
    }


def write_index(index: dict, index_dir: Path) -> Path:
    index_dir.mkdir(parents=True, exist_ok=True)
    path = index_path(index_dir, index["live_build"])
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def indexed_builds(index_dir: Path) -> list[str]:
    """Builds with an index on disk, newest first."""
    if not index_dir.is_dir():
        return []
    builds = [p.name[len("live-") : -len(".json")] for p in index_dir.glob("live-*.json")]
    return sorted(builds, key=build_sort_key, reverse=True)


def load_index(index_dir: Path, live_build: str) -> dict:
    return json.loads(index_path(index_dir, live_build).read_text(encoding="utf-8"))
