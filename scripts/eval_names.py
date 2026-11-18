"""Count the API names a Remote Script uses that Live's build does not know (plan 0001 step 9a).

    uv run python scripts/eval_names.py <script folder> [--build 12.4.16] [--json]

The skill evals score each generated script with this. It reads the script's `.py` sources with
Python's parser (never runs them) and puts every attribute name (`x.name`) and every keyword
argument of a framework constructor into one of these:

- `own`: the script defines it (a def, a class, an assigned attribute, a `setattr` name, also one
  built from a literal start such as `"set_" + key`; a parameter defines none)
- `index`: a class, module or member name in the build's API index (observed)
- `used`: not a member in the index, but Ableton's own scripts use it in a call
  (the statement summaries), which covers most `Live` object attributes (`song().tracks`)
- `documented`: none of these, but on Structure Void's runtime pages of the `Live` module
  (`import-structure-void`), which have the listener methods and properties the Push 3 helper's
  model lacks: `documented`, not observed
- `python`: a method of Python's containers and strings (`append`, `format`), a dunder, or any
  attribute of a name bound by `import` of a standard-library module (`logging.getLogger`)
- `unknown`: none of these. An invented name, or a `Live` object attribute that no Ableton
  script uses in a call: read each one before counting it as invented.

The check works by name, not by class: a name that any indexed class has counts as known on
every object, and an invented name that is also a string or list method (`title`, `count`,
`index`) counts as `python`.

Keyword arguments are checked only on constructor calls of a class imported by name
(`from m import C; C(...)`, not `m.C(...)` or method calls), and only when its `__init__` chain
names its parameters; a chain that ends in `**k` passed to a class outside the index cannot be
decided and is skipped, and so is one whose `__init__` keeps `**k` instead of passing it on
(`Layer`). Imported names are the validator's job (`unresolved-import`).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

from ableton_remote_script_mcp.index_store import (
    attach_statements,
    default_index_dir,
    indexed_builds,
    load_index,
    load_statements,
)
from ableton_remote_script_mcp.resolve import Resolver, lineage
from ableton_remote_script_mcp.structure_void import live_major, load_document

# Not int, range or slice: they bring `start`, `stop`, `real`, names a script may invent on Live objects.
CONTAINER_TYPES = (str, bytes, list, tuple, dict, set, frozenset)
PYTHON_ATTRS = ({name for t in CONTAINER_TYPES for name in dir(t)}
                | {name for t in (object, type) for name in dir(t) if name.startswith("__")})
_ATTR_IN_TEXT = re.compile(r"\.([A-Za-z_]\w*)")


def known_names(index: dict, statements: dict | None) -> tuple[set[str], set[str]]:
    """(names the index defines, attribute names Ableton's scripts use in calls)."""
    defined: set[str] = set()
    for table in ("classes", "modules"):
        for fact in index[table].values():
            defined.add(fact["name"].split(".")[-1])
            defined.update(fact.get("members", {}))
            for member in fact.get("members", {}).values():
                defined.update(p["name"] for p in member.get("params", []))
            defined.update(event_methods(fact.get("members", {})))
    used: set[str] = set()
    for table in (statements or {}).get("classes", {}), (statements or {}).get("modules", {}):
        for functions in table.values():
            for calls in functions.values():
                for call in calls:
                    text = " ".join([call.get("call", ""), *call.get("args", []),
                                     *map(str, call.get("kwargs", {}).values()), call.get("target", "")])
                    used.update(_ATTR_IN_TEXT.findall(text))
    return defined, used - defined


EVENT_LISTS = ("__subject_events__", "__events__")


def event_methods(members: dict) -> set[str]:
    """The listener methods the framework makes at run time from a class's event list:
    `__subject_events__ = ('offset',)` (`_Framework`) or `__events__` (v2, v3) gives
    `add_offset_listener`, `remove_offset_listener`, `offset_has_listener` and `notify_offset`
    (documented, decompiled 12.0 framework). Only events written as plain strings are read."""
    names: set[str] = set()
    for key in EVENT_LISTS:
        member = members.get(key)
        if not member or not member.get("value_literal"):
            continue
        try:
            events = ast.literal_eval(member["value"])
        except (ValueError, SyntaxError):
            continue
        for event in events if isinstance(events, tuple | list) else ():
            if isinstance(event, str):
                names |= {f"add_{event}_listener", f"remove_{event}_listener",
                          f"{event}_has_listener", f"notify_{event}"}
    return names


def own_names(trees: list[ast.Module]) -> set[str]:
    names: set[str] = set()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                names.add(node.attr)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                names.add(node.id)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr" \
                    and len(node.args) > 1:
                key = node.args[1]
                if isinstance(key, ast.Constant):
                    names.add(str(key.value))
                elif isinstance(key, ast.BinOp) and isinstance(key.left, ast.Constant) and isinstance(key.left.value, str):
                    names.add(PREFIX + key.left.value)  # setattr(self, "set_B_" + key, …)
                elif isinstance(key, ast.JoinedStr) and key.values and isinstance(key.values[0], ast.Constant):
                    names.add(PREFIX + str(key.values[0].value))
    return names


PREFIX = "\0prefix:"  # an own name that `setattr` builds from this literal start


def is_own(name: str, own: set[str]) -> bool:
    return name in own or any(o.startswith(PREFIX) and name.startswith(o[len(PREFIX):]) for o in own)


def documented_names(doc: dict | None) -> set[str]:
    """Names on Structure Void's runtime pages of the `Live` module (`structure_void.py`)."""
    if not doc:
        return set()
    names = {c["name"] for c in doc["classes"].values()}
    names |= {n for c in doc["classes"].values() for n in c["members"]}
    return names | {k.rsplit(".", 1)[-1] for k in doc["functions"]} | {c["module"].rsplit(".", 1)[-1]
                                                                       for c in doc["classes"].values()}


def _init_params(index: dict, resolver: Resolver, class_key: str) -> set[str] | None:
    """Every keyword `class_key(...)` accepts, or None when the chain cannot be decided."""
    chain = lineage(resolver, class_key).mro
    if not chain or any(e["status"] != "indexed" and e["name"] != "builtins.object" for e in chain):
        return None  # a base outside the index may take keywords the index does not show
    names: set[str] = set()
    for entry in chain:
        init = index["classes"].get(entry["name"], {}).get("members", {}).get("__init__")
        if init is None:
            continue
        params = init.get("params", [])
        names.update(p["name"] for p in params if p["kind"] not in ("var_positional", "var_keyword"))
        rest = next((p["name"] for p in params if p["kind"] == "var_keyword"), None)
        if rest is None:
            break  # this __init__ takes nothing more: the chain ends here
        if not any(st.get("call", "").endswith("__init__") and st.get("kwargs", {}).get("**") == rest
                   for st in init.get("statements", [])):
            return None  # it keeps **k itself (Layer takes any control name): cannot be decided
    return names  # the rest of **k reaches object.__init__, which takes no keywords


def stdlib_names(tree: ast.Module) -> set[str]:
    """Names bound by `import x` of a standard-library module; never imported, only named."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in sys.stdlib_module_names:
                    found.add(alias.asname or top)
    return found


def framework_imports(tree: ast.Module) -> dict[str, str]:
    """Bound name → qualified name, for `from <absolute module> import Name`."""
    bound = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                if alias.name != "*":
                    bound[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return bound


def check(folder: Path, index: dict, statements: dict | None, doc: dict | None = None) -> dict:
    sources = sorted(p for p in folder.rglob("*.py") if "__pycache__" not in p.parts)
    trees, broken = [], []
    for path in sources:
        try:
            trees.append((path, ast.parse(path.read_text(encoding="utf-8"), str(path))))
        except (SyntaxError, UnicodeDecodeError) as e:
            broken.append({"file": str(path.relative_to(folder)), "error": str(e)})
    defined, used = known_names(index, statements)
    own = own_names([t for _, t in trees])
    resolver = Resolver(index)
    documented = documented_names(doc)
    counts = {"own": 0, "python": 0, "index": 0, "used": 0, "documented": 0, "unknown": 0}
    unknown, used_only, kwargs_unknown, kwargs_checked = [], [], [], 0
    for path, tree in trees:
        rel = str(path.relative_to(folder))
        stdlib = stdlib_names(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and not isinstance(node.ctx, ast.Store):
                name = node.attr
                of_stdlib = isinstance(node.value, ast.Name) and node.value.id in stdlib
                bucket = ("own" if is_own(name, own) else "index" if name in defined else "used" if name in used
                          else "documented" if name in documented
                          else "python" if name in PYTHON_ATTRS or of_stdlib else "unknown")
                counts[bucket] += 1
                if bucket == "unknown":
                    unknown.append({"file": rel, "line": node.lineno, "name": name, "expr": ast.unparse(node)})
                elif bucket == "used":
                    used_only.append(name)
        bound = framework_imports(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in bound):
                continue
            found = resolver.resolve(bound[node.func.id])
            if found.status != "class" or found.key not in index["classes"]:
                continue
            accepted = _init_params(index, resolver, found.key)
            if accepted is None:
                continue
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                kwargs_checked += 1
                if kw.arg not in accepted:
                    kwargs_unknown.append({"file": rel, "line": node.lineno, "class": found.key, "keyword": kw.arg})
    return {"live_build": index["live_build"], "folder": str(folder), "files": len(sources), "broken": broken,
            "attribute_counts": counts, "unknown": unknown, "used_only": sorted(set(used_only)),
            "kwargs_checked": kwargs_checked, "kwargs_unknown": kwargs_unknown,
            "invented_candidates": len(unknown) + len(kwargs_unknown)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--build", default="12.4.16", help="Live build (default: 12.4.16, plan step 9a)")
    parser.add_argument("--index-dir", type=Path, default=default_index_dir())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    builds = indexed_builds(args.index_dir)
    build = args.build
    if build not in builds:
        print(f"no index for Live {build} in {args.index_dir}", file=sys.stderr)
        return 2
    index = load_index(args.index_dir, build)
    statements = load_statements(args.index_dir, index)
    if statements:
        attach_statements(index, statements)  # keyword checks need to see where **k goes
    result = check(args.folder.resolve(), index, statements, load_document(args.index_dir, live_major(build)))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['folder']} against Live {build}: {result['invented_candidates']} unknown names")
        print("  attributes: " + ", ".join(f"{k} {v}" for k, v in result["attribute_counts"].items()))
        for u in result["unknown"]:
            print(f"  {u['file']}:{u['line']}: unknown attribute {u['name']} in {u['expr']}")
        for k in result["kwargs_unknown"]:
            print(f"  {k['file']}:{k['line']}: {k['class']} takes no keyword {k['keyword']}")
        for b in result["broken"]:
            print(f"  {b['file']}: not parsed ({b['error']})")
    return 1 if result["invented_candidates"] or result["broken"] else 0


if __name__ == "__main__":
    sys.exit(main())
