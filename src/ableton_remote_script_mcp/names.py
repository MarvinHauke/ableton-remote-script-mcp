"""The API names a Remote Script uses, each with where it is known (plan 0001 step 9a; moved into
the package as `check-names` in step 11, Decision 49 Q3).

    ableton-remote-script-mcp check-names <script folder> [--build 12.4.16] [--json]
    ableton-remote-script-mcp check-names --names Component.set_enabled song.tracks …

The skill runs it on each draft, and the skill evals score each generated script with it. It
reports facts, not errors: that is `validate`'s job. For a folder it reads the script's `.py` sources with
Python's parser (never runs them) and puts every attribute name (`x.name`) and every keyword
argument of a framework constructor into one of these:

- `own`: the script defines it (a def, a class, an assigned attribute, a `setattr` name, also one
  built from a literal start such as `"set_" + key`; a parameter defines none), or its v3
  Elements class builds it (`self.scene_buttons` from `add_button_matrix(…, "Scene_Buttons")`,
  read by the Elements reader, `elements.py`; only on Live's Python, 3.11: elsewhere, and
  when the script doesn't compile or builds some names from values read only at run time,
  the answer's `not_read` says so)
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

For a list of names (`check_list`), each name is one of:
- a class (`Component`, `ableton.v3.control_surface.Component`): `class`, observed;
- `Class.member`: the member, own or inherited (with its `origin`), observed; or documented on
  Structure Void's runtime pages; or `not_a_member` of that class, with the bucket the bare name
  falls in anywhere else;
- a bare name: its bucket as above (`index` with up to five classes that have it).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from .resolve import Resolver, lineage
from .validator import element_names_of_folder

# Not int, range or slice: they bring `start`, `stop`, `real`, names a script may invent on Live objects.
CONTAINER_TYPES = (str, bytes, list, tuple, dict, set, frozenset)
PYTHON_ATTRS = ({name for t in CONTAINER_TYPES for name in dir(t)}
                | {name for t in (object, type) for name in dir(t) if name.startswith("__")})
_ATTR_IN_TEXT = re.compile(r"\.([A-Za-z_]\w*)")


_KNOWN: list = []  # [(index, statements, result)] of the last call


def known_names(index: dict, statements: dict | None) -> tuple[set[str], set[str]]:
    """(names the index defines, attribute names Ableton's scripts use in calls). Kept for the
    last index and statements it was made from, so a loaded index builds it once."""
    if _KNOWN and _KNOWN[0][0] is index and _KNOWN[0][1] is statements:
        return _KNOWN[0][2]
    result = _known_names(index, statements)
    _KNOWN[:] = [(index, statements, result)]
    return result


def _known_names(index: dict, statements: dict | None) -> tuple[set[str], set[str]]:
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
    elements, not_read = element_names_of_folder(folder, index)
    own = own_names([t for _, t in trees]) | elements
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
    answer = {"live_build": index["live_build"], "folder": str(folder), "files": len(sources), "broken": broken,
              "attribute_counts": counts, "unknown": unknown, "used_only": sorted(set(used_only)),
              "kwargs_checked": kwargs_checked, "kwargs_unknown": kwargs_unknown,
              "invented_candidates": len(unknown) + len(kwargs_unknown)}
    if not_read:  # what the check couldn't read, so an `unknown` may be one of those names
        answer["not_read"] = [not_read]
    return answer




def bucket(name: str, defined: set[str], used: set[str], documented: set[str]) -> str:
    return ("index" if name in defined else "used" if name in used else "documented" if name in documented
            else "python" if name in PYTHON_ATTRS else "unknown")


_CONFIDENCE = {"index": "observed", "used": "observed", "documented": "documented"}


def _holders(index: dict, resolver: Resolver, name: str, limit: int = 5) -> list[str]:
    from .query import class_rank  # one ranking with `get_class`

    found = [k for k, c in index["classes"].items() if name in c["members"]]
    found.sort(key=lambda k: class_rank(index, resolver, k))
    return found[:limit]


def check_list(names: list[str], index: dict, statements: dict | None, doc: dict | None, resolver: Resolver,
               find) -> dict:
    """Each name of `names` with where it is known (see the module's docstring). `find(name)`
    gives the index's class keys for a class name, best first (`query.class_rank`), and the
    re-export path if any."""
    defined, used = known_names(index, statements)
    documented = documented_names(doc)
    results = []
    for raw in names:
        name = raw.strip()
        if not name:
            continue
        keys, _ = find(name)
        if keys:
            results.append({"name": name, "kind": "class", "known": "index", "confidence": "observed",
                            "classes": keys[:5]})
            continue
        owner, _, member = name.rpartition(".")
        keys, _ = find(owner) if owner else ([], None)
        if keys:  # the first class of that name that has the member (`Component`: v2, v3, …)
            lineages = {k: lineage(resolver, k).members for k in keys}
            key = next((k for k in keys if member in lineages[k]), keys[0])
            members = lineages[key]
            entry = {"name": name, "class": key}
            if len(keys) > 1:
                entry["classes"] = keys[:5]
            if member in members:
                m = members[member]
                entry.update(kind=m["kind"], known="index", confidence="observed", origin=m["origin"])
                if "params" in m:
                    entry["params"] = [p["name"] for p in m["params"]]
                if index["classes"][key].get("proxy_of"):  # observed in a model of it, not in Live itself
                    entry["proxy_of"] = index["classes"][key]["proxy_of"]
            elif doc and _documented_member(doc, index["classes"][key], member):
                entry.update(kind="member", known="documented", confidence="documented")
            else:
                b = bucket(member, defined, used, documented)
                entry.update(kind="member", known="not_a_member", confidence=None, elsewhere=b,
                             message=f"{key} has no member {member!r} in Live {index['live_build']}"
                             + ("" if b == "unknown" else f"; the name is {b} elsewhere"))
            results.append(entry)
            continue
        bare = name.rsplit(".", 1)[-1]
        b = bucket(bare, defined, used, documented)
        entry = {"name": name, "kind": "name", "known": b, "confidence": _CONFIDENCE.get(b)}
        if b == "index":
            entry["in"] = _holders(index, resolver, bare)
        results.append(entry)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["known"]] = counts.get(r["known"], 0) + 1
    return {"live_build": index["live_build"], "names": results, "counts": counts,
            "unknown": [r["name"] for r in results if r["known"] in ("unknown", "not_a_member")]}


def _documented_member(doc: dict, cls: dict, member: str) -> bool:
    """A member on Structure Void's runtime page of the class this proxy model stands for."""
    page = doc.get("classes", {}).get(cls.get("proxy_of") or "")
    return bool(page and member in page["members"])
