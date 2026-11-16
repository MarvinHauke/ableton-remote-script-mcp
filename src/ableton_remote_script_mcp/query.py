"""Query core: the one interface the CLI, the skill scripts and the MCP tools use.

Answers are plain dicts with a `status` of "ok", "index_missing" or "not_found", so every
adapter can pass them through and no caller has to guess.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .index_store import (
    GENERATIONS,
    PUSH3_HELPER_ROOT,
    SCHEMA_VERSION,
    SCRIPTS_ROOT,
    attach_statements,
    fact_key,
    generation,
    index_path,
    indexed_builds,
    load_index,
    load_statements,
    statements_path,
)
from .live_install import LiveInstall
from .outline import find_script, outline_package
from .resolve import Resolver, lineage
from .validator import validate_folder

BUILD_INDEX_HINT = "run `uv run ableton-remote-script-mcp build-index` (or `--app <Live.app>` for a specific build)"


def _index_missing(index_dir: Path, live_build: str | None, reason: str | None = None) -> dict:
    where = index_path(index_dir, live_build) if live_build else index_dir
    what = reason or (f"no API index for Live {live_build}" if live_build else "no API index")
    return {"status": "index_missing", "message": f"{what} at {where}; {BUILD_INDEX_HINT}"}


def _open(index_dir: Path, live_build: str | None) -> tuple[dict | None, dict | None]:
    """(index, None) or (None, an index_missing answer)."""
    builds = indexed_builds(index_dir)
    if live_build is None:
        if not builds:
            return None, _index_missing(index_dir, None)
        live_build = builds[0]
    elif live_build not in builds:
        return None, _index_missing(index_dir, live_build)
    try:
        index = load_index(index_dir, live_build)
    except (OSError, json.JSONDecodeError) as e:
        return None, _index_missing(index_dir, live_build, f"the index for Live {live_build} is unreadable ({e})")
    if index.get("schema") != SCHEMA_VERSION:
        return None, _index_missing(
            index_dir,
            live_build,
            f"the index for Live {live_build} has schema {index.get('schema')}; this tool reads schema {SCHEMA_VERSION}",
        )
    return index, None


def _proxies(index: dict) -> dict[str, str]:
    """`Live.Song.Song` -> the key of its proxy model class in the Push 3 helper."""
    return {c["proxy_of"]: k for k, c in index["classes"].items() if c.get("proxy_of")}


def _class_answer(index: dict, resolver: Resolver, key: str, proxies: dict[str, str]) -> dict:
    cls = index["classes"][key]
    lin = lineage(resolver, key, proxies)
    answer = {"qualified_name": key, **cls}
    answer["bases"] = [
        {**b, "defined_in": node["name"], "status": node["status"]} for b, node in zip(cls["bases"], lin.bases)
    ]
    answer["mro"] = lin.mro
    answer["mro_method"] = lin.method
    answer["complete"] = lin.complete
    answer["all_members"] = lin.members
    return answer


def get_class(name: str, index_dir: Path, live_build: str | None = None) -> dict:
    """Classes by short name (`Component`), qualname, key (`ableton.v3….component.Component`,
    `push3-helper:live_model.Live.Song.Song`) or a re-exported name
    (`ableton.v3.control_surface.Component`). Matches from the Remote Scripts come first.

    Each base gets `defined_in` (the class key, or the external name, it resolves to, following
    re-exports, aliases and star imports) and a `status` (indexed, external or unresolved). Each
    class comes with its MRO and `all_members`: every member it has, own and inherited,
    with the class it comes from (`origin`) and the classes further along the MRO whose member
    of that name it hides (`overrides`). `complete` is False when a base along the MRO could
    not be resolved, so inherited members may be missing.
    """
    index, missing = _open(index_dir, live_build)
    if missing:
        return missing
    live_build = index["live_build"]
    classes = index["classes"]
    resolver = Resolver(index)
    resolved_from = None
    if name in classes:
        keys = [name]
    else:
        keys = [k for k, c in classes.items() if name in (c["name"], c["qualname"], f"{c['module']}.{c['qualname']}")]
    if not keys and "." in name:
        root, _, bare = name.rpartition(":") if name.startswith(PUSH3_HELPER_ROOT + ":") else (SCRIPTS_ROOT, "", name)
        found = resolver.resolve(bare, root)
        if found.status == "class":
            keys, resolved_from = [found.key], {"name": name, "via": list(found.via)}
    if not keys:
        return _not_found(live_build, f"class {name!r}")
    keys.sort(key=lambda k: (classes[k]["root"] != SCRIPTS_ROOT, k))
    proxies = _proxies(index)
    answer = {
        "status": "ok",
        "live_build": live_build,
        "classes": [_class_answer(index, resolver, k, proxies) for k in keys],
    }
    if resolved_from:
        answer["resolved_from"] = resolved_from
    return answer


def _not_found(live_build: str, what: str) -> dict:
    return {"status": "not_found", "live_build": live_build, "message": f"{what} not found in Live {live_build}"}


_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")
_KIND_ORDER = {"class": 0, "module": 1, "method": 2, "property": 2, "classmethod": 2, "staticmethod": 2,
               "function": 3, "attribute": 4}
SEARCH_KINDS = ("class", "module", "member", "method", "property", "classmethod", "staticmethod",
                "function", "attribute")


def words(text: str) -> list[str]:
    """`SessionRingComponent` / `session_ring` / `session ring` -> ["session", "ring", ...]."""
    return [w.lower() for w in _WORD.findall(text or "")]


def _package_rank(index: dict, root: str, module: str) -> int:
    """Framework first (newest generation first), then libraries, then Remote Scripts; the Push 3
    helper's copies after the Remote Scripts folder."""
    pkg = index["packages"].get(fact_key(root, module.split(".")[0]), {})
    gen = generation(module)
    if pkg.get("kind") == "framework" or gen:
        rank = len(GENERATIONS) - 1 - GENERATIONS.index(gen) if gen else len(GENERATIONS)
    else:
        rank = {"library": 4, "script": 5}.get(pkg.get("kind"), 6)
    return rank + (10 if root != SCRIPTS_ROOT else 0)


def _score(query: str, qwords: list[str], name: str, qualified: str, docstring: str | None) -> tuple[int, str]:
    q, n = query.lower(), name.lower()
    if n == q:
        return 100, "name"
    if "." in q and qualified.lower().endswith(q):
        return 90, "qualified name"
    if n.startswith(q):
        return 70, "name starts with"
    if len(q) >= 3 and q in n:
        return 50, "name contains"
    if qwords:
        name_words = words(name)
        if all(any(w.startswith(qw) for w in name_words) for qw in qwords):
            return 40, "words in name"
        context = name_words + words(qualified) + words(docstring)
        if all(any(w.startswith(qw) for w in context) for qw in qwords):
            return 20, "words in name, module or docstring"
    return 0, ""


def search(query: str, index_dir: Path, live_build: str | None = None, kind: str | None = None,
           limit: int = 20) -> dict:
    """Classes, modules and members by name or words, best first.

    Ranking: exact name, qualified-name suffix, name prefix, name substring, all words in the
    name, all words in name + module + docstring. Ties: classes before modules before members;
    framework (newest generation first) before libraries before Remote Scripts; shorter names first.
    `kind` narrows to one of SEARCH_KINDS ("member" = any class member).
    """
    index, missing = _open(index_dir, live_build)
    if missing:
        return missing
    live_build = index["live_build"]
    query = query.strip()
    qwords = words(query)
    hits = []

    def consider(item_kind, name, key, root, module, docstring, extra):
        if kind and not (kind == item_kind or (kind == "member" and extra.get("in_class"))):
            return
        score, match = _score(query, qwords, name, key, docstring)
        if score:
            rank = (-score, _KIND_ORDER.get(item_kind, 9), _package_rank(index, root, module), len(key), key)
            hits.append((rank, {"kind": item_kind, "name": name, "qualified_name": key, "match": match,
                                "score": score, **extra, "live_build": live_build, "confidence": "observed"}))

    for key, c in index["classes"].items():
        consider("class", c["name"], key, c["root"], c["module"], c.get("docstring"),
                 {"source": c["source"], "line": c["line"], **({"proxy_of": c["proxy_of"]} if c.get("proxy_of") else {})})
        for mname, m in c["members"].items():
            consider(m["kind"], mname, f"{key}.{mname}", c["root"], c["module"], m.get("docstring"),
                     {"in_class": key, "source": c["source"], "line": m.get("line")})
    for key, mod in index["modules"].items():
        consider("module", mod["name"].rsplit(".", 1)[-1], key, mod["root"], mod["name"], mod.get("docstring"),
                 {"source": mod["source"]})
        for mname, m in mod.get("members", {}).items():
            consider(m["kind"], mname, f"{key}.{mname}", mod["root"], mod["name"], m.get("docstring"),
                     {"in_module": key, "source": mod["source"], "line": m.get("line")})
    if not hits:
        return _not_found(live_build, f"{kind + ' ' if kind else ''}{query!r}")
    hits.sort(key=lambda h: h[0])
    return {"status": "ok", "live_build": live_build, "query": query, "total": len(hits),
            "results": [h for _, h in hits[:limit]]}


def list_builds(index_dir: Path, installs: list[LiveInstall] | None = None) -> dict:
    """The indexed builds, newest first, with their counts; and installed builds with no index."""
    builds = []
    for live_build in indexed_builds(index_dir):
        entry: dict = {"live_build": live_build, "path": str(index_path(index_dir, live_build))}
        try:
            index = load_index(index_dir, live_build)
        except (OSError, json.JSONDecodeError) as e:
            entry.update(usable=False, problem=f"unreadable: {e}")
            builds.append(entry)
            continue
        entry.update(
            statements=load_statements(index_dir, index) is not None,
            created=index.get("created"),
            app=index.get("source", {}).get("app"),
            bundle_version=index.get("source", {}).get("bundle_version"),
            schema=index.get("schema"),
            usable=index.get("schema") == SCHEMA_VERSION,
            summary=index.get("summary"),
        )
        if not entry["usable"]:
            entry["problem"] = f"schema {index.get('schema')}, this tool reads schema {SCHEMA_VERSION}; rebuild it"
        builds.append(entry)
    indexed = {b["live_build"] for b in builds}
    not_indexed = [
        {"live_build": i.live_build, "app": str(i.app), "beta": i.is_beta}
        for i in (installs or [])
        if i.live_build not in indexed
    ]
    if not builds:
        answer = _index_missing(index_dir, None)
        answer["installed_not_indexed"] = not_indexed
        return answer
    return {"status": "ok", "builds": builds, "installed_not_indexed": not_indexed}


def outline_script(name: str, index_dir: Path, live_build: str | None = None) -> dict:
    """The outline of one Remote Script (or library): its classes with their roles and own
    members, the Specification fields it sets, its component map and mappings (v3), and the
    elements, components and layers its code creates, without function bodies.
    See `outline.py` for how each part is found."""
    index, missing = _open(index_dir, live_build)
    if missing:
        return missing
    live_build = index["live_build"]
    statements = load_statements(index_dir, index)
    if statements is None:
        return _index_missing(index_dir, live_build,
                              f"no statement summaries for Live {live_build} at {statements_path(index_dir, live_build)}"
                              " (an outline needs them; build-index writes them unless --no-statements)")
    attach_statements(index, statements)
    key = find_script(index, name)
    if key is None:
        return _not_found(live_build, f"Remote Script {name!r}")
    if index["packages"][key]["kind"] == "framework":
        answer = _not_found(live_build, f"Remote Script {name!r}")
        answer["message"] = f"{name} is a framework package in Live {live_build}, not a Remote Script; look up its classes instead"
        return answer
    return {"status": "ok", "live_build": live_build, "confidence": "observed", **outline_package(index, key)}


def validate_script(folder: Path, index_dir: Path, live_build: str | None = None) -> dict:
    """Static findings for one Remote Script folder against one build's API index: each with a
    file, a line, a rule, a severity, a message and a fix. See `validator.py` for the rules."""
    folder = Path(folder).expanduser()
    if not folder.is_dir():
        return {"status": "not_found", "live_build": live_build, "message": f"no script folder at {folder}"}
    index, missing = _open(index_dir, live_build)
    if missing:
        return missing
    statements = load_statements(index_dir, index)
    if statements:
        attach_statements(index, statements)  # the framework checks read the framework's code
    return {"status": "ok", "live_build": index["live_build"], "confidence": "observed",
            **validate_folder(folder.resolve(), index)}
