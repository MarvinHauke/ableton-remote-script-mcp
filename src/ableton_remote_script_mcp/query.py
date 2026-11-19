"""Query core: the one interface the CLI, the skill scripts and the MCP tools use.

Answers are plain dicts with a `status` of "ok", "index_missing" or "not_found", so every
adapter can pass them through and no caller has to guess.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
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
from .structure_void import live_major, load_document
from .structure_void_framework import compare_class, cross_check, load_framework
from .validator import read_sources, validate_folder

BUILD_INDEX_HINT = "run `uv run ableton-remote-script-mcp build-index` (or `--app <Live.app>` for a specific build)"


def _index_missing(index_dir: Path, live_build: str | None, reason: str | None = None) -> dict:
    where = index_path(index_dir, live_build) if live_build else index_dir
    what = reason or (f"no API index for Live {live_build}" if live_build else "no API index")
    return {"status": "index_missing", "message": f"{what} at {where}; {BUILD_INDEX_HINT}"}


_LOADED: OrderedDict = OrderedDict()  # (file, mtime, size, with statements) -> index
_KEEP_LOADED = 2


def _load(index_dir: Path, live_build: str, with_statements: bool = False) -> tuple[dict, dict | None]:
    """(index, statements) of one build, kept loaded while its files don't change, so the MCP
    server reads a build once. With statements, a separate copy carries them on its members
    (`attach_statements`), so the other answers stay as they are."""
    path = index_path(index_dir, live_build)
    st = path.stat()
    key = (str(path), st.st_mtime_ns, st.st_size, with_statements)
    if key in _LOADED:
        _LOADED.move_to_end(key)
        return _LOADED[key]
    index = load_index(index_dir, live_build)
    statements = load_statements(index_dir, index) if with_statements else None
    if statements:
        attach_statements(index, statements)
    _LOADED[key] = (index, statements)
    while len(_LOADED) > _KEEP_LOADED:
        _LOADED.popitem(last=False)
    return index, statements


def _open(index_dir: Path, live_build: str | None,
          with_statements: bool = False) -> tuple[dict | None, dict | None]:
    """(index, None) or (None, an index_missing answer)."""
    builds = indexed_builds(index_dir)
    if live_build is None:
        if not builds:
            return None, _index_missing(index_dir, None)
        live_build = builds[0]
    elif live_build not in builds:
        return None, _index_missing(index_dir, live_build)
    try:
        index, _ = _load(index_dir, live_build, with_statements)
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
    resolver = Resolver(index)
    keys, resolved_from = find_class_keys(index, resolver, name)
    doc = load_document(index_dir, live_major(live_build))
    if not keys:
        documented = _documented_classes(doc, name)
        if not documented:
            return _not_found(live_build, f"class {name!r}")
        return {"status": "ok", "live_build": live_build, "classes": [], "documented": documented}
    proxies = _proxies(index)
    answer = {
        "status": "ok",
        "live_build": live_build,
        "classes": [_class_answer(index, resolver, k, proxies) for k in keys],
    }
    framework = load_framework(index_dir, live_major(live_build))
    for c in answer["classes"]:  # a proxy model class: what Structure Void's page adds to it
        documented = doc and doc["classes"].get(c.get("proxy_of") or "")
        if documented:
            c["documented"] = _documented_entry(doc, c["proxy_of"], set(c["all_members"]))
        page = framework and c["root"] == SCRIPTS_ROOT and _framework_page(framework, c, index)
        if page:  # the class's framework page: where it disagrees with the index
            c["structure_void"] = {**compare_class(c, page), "covers": framework["covers"],
                                   "licence": framework["licence"], "confidence": "documented"}
    if resolved_from:
        answer["resolved_from"] = resolved_from
    return answer


def find_class_keys(index: dict, resolver: Resolver, name: str) -> tuple[list[str], dict | None]:
    """The class keys a class name stands for, the Remote Scripts' first, and the re-export it
    was found through (`get_class`'s name forms)."""
    classes = index["classes"]
    resolved_from = None
    if name in classes:
        keys = [name]
    else:
        keys = [k for k, c in classes.items() if name in (c["name"], c["qualname"], f"{c['module']}.{c['qualname']}")]
    if not keys:  # `Live.Song.Song`: the Push 3 helper's model of it
        keys = [k for k, c in classes.items() if c.get("proxy_of") == name]
    if not keys and "." in name:
        root, _, bare = name.rpartition(":") if name.startswith(PUSH3_HELPER_ROOT + ":") else (SCRIPTS_ROOT, "", name)
        found = resolver.resolve(bare, root)
        if found.status == "class":
            keys, resolved_from = [found.key], {"name": name, "via": list(found.via)}
    keys.sort(key=lambda k: (classes[k]["root"] != SCRIPTS_ROOT, k))
    return keys, resolved_from


def _framework_page(framework: dict, c: dict, index: dict) -> dict | None:
    """A class's entry on its module's framework page. A nested class is headed by its own name
    (`Transport` for `Notifications.Transport`), so it is matched only when no other class of
    that module has that name."""
    classes = (framework["modules"].get(c["module"]) or {}).get("classes", {})
    if c["qualname"] in classes:
        return classes[c["qualname"]]
    tail = c["qualname"].rsplit(".", 1)[-1]
    if tail not in classes:
        return None
    same = [k for k, o in index["classes"].items() if o["module"] == c["module"] and o["root"] == c["root"]
            and o["qualname"].rsplit(".", 1)[-1] == tail]
    return classes[tail] if len(same) == 1 else None


def structure_void_check(index_dir: Path, live_build: str | None = None, under: str | None = None) -> dict:
    """Structure Void's framework pages against one build's index (`cross_check`)."""
    index, missing = _open(index_dir, live_build)
    if missing:
        return missing
    framework = load_framework(index_dir, live_major(index["live_build"]))
    if framework is None:
        return {"status": "not_imported", "message": "Structure Void's framework pages are not imported; run "
                "`ableton-remote-script-mcp import-structure-void`"}
    return cross_check(index, framework, under)


def _documented_entry(doc: dict, key: str, have: set[str] = frozenset()) -> dict:
    """A class of Structure Void's runtime pages, `documented`, with the members not in `have`."""
    c = doc["classes"][key]
    return {"qualified_name": key, "kind": c["kind"], "bases": c["bases"], "doc": c.get("doc"),
            "source": c["url"], "covers": doc["covers"], "licence": doc["licence"], "confidence": "documented",
            "members": {n: m for n, m in c["members"].items() if n not in have}}


def _documented_classes(doc: dict | None, name: str) -> list[dict]:
    if not doc:
        return []
    keys = [k for k, c in doc["classes"].items()
            if name in (k, c["name"], f"{c['module'].rsplit('.', 1)[-1]}.{c['name']}")]
    return [_documented_entry(doc, k) for k in sorted(keys)]


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
           limit: int = 20, offset: int = 0) -> dict:
    """Classes, modules and members by name or words, best first.

    Ranking: exact name, qualified-name suffix, name prefix, name substring, all words in the
    name, all words in name + module + docstring. Ties: classes before modules before members;
    framework (newest generation first) before libraries before Remote Scripts; shorter names first.
    `kind` narrows to one of SEARCH_KINDS ("member" = any class member). `offset` skips that
    many results: the answer's `next_offset` is the next page, when there is one.
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
    doc = load_document(index_dir, live_major(live_build))
    for key, c in (doc or {}).get("classes", {}).items():
        extra = {"source": c["url"], "confidence": "documented"}
        before = len(hits)
        consider("class", c["name"], key, "structure-void", c["module"], c.get("doc"), extra)
        for mname, m in c["members"].items():
            consider(m["kind"], mname, f"{key}.{mname}", "structure-void", c["module"], m.get("doc"),
                     {"in_class": key, **extra})
        for _, hit in hits[before:]:
            hit["confidence"] = "documented"
            hit["rank_note"] = f"Structure Void, {doc['covers']}"
    if not hits:
        return _not_found(live_build, f"{kind + ' ' if kind else ''}{query!r}")
    hits.sort(key=lambda h: h[0])
    offset = max(offset, 0)
    page = [h for _, h in hits[offset:offset + limit]]
    answer = {"status": "ok", "live_build": live_build, "query": query, "total": len(hits), "offset": offset,
              "results": page}
    if offset + len(page) < len(hits):
        answer["next_offset"] = offset + len(page)
    return answer


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


def is_script_folder(name: str) -> bool:
    """`outline`'s argument names a folder on disk (a path), not a script in Live's install."""
    return ("/" in name or name.startswith(".")) and Path(name).expanduser().is_dir()


def outline_folder(folder: Path, index: dict) -> tuple[dict | None, str]:
    """(the outline of a script folder against a loaded index with statements, or None and why).
    The folder's sources are compiled and read like Live's own scripts (the validator's overlay),
    so the outline is the same as for an indexed script."""
    import sys

    from .framework_checks import LIVE_PYTHON, compile_sources, overlay_index
    if sys.version_info[:2] != LIVE_PYTHON:
        return None, f"an outline of a folder compiles it as Live's Python {LIVE_PYTHON[0]}.{LIVE_PYTHON[1]} does"
    folder = Path(folder).expanduser().resolve()
    findings: list[dict] = []
    not_checked: list[dict] = []
    sources, _ = read_sources(folder, findings)
    codes = compile_sources(sources, findings, not_checked)
    if not codes:
        return None, f"no readable Python sources in {folder}" + (f" ({findings[0]['message']})" if findings else "")
    overlay = overlay_index(index, folder.name, sources, codes, not_checked)
    if folder.name not in overlay["packages"]:
        return None, f"{folder} has no __init__.py: it is not a Remote Script folder"
    answer = outline_package(overlay, folder.name)
    answer["folder"] = str(folder)
    if findings or not_checked:
        answer["not_read"] = [f"{f['file']}: {f['message']}" for f in findings] + [
            f"{n['file']}: {n['reason']}" for n in not_checked]
    return answer, ""


def _with_statements(index_dir: Path, live_build: str | None) -> tuple[dict | None, dict | None]:
    index, missing = _open(index_dir, live_build, with_statements=True)
    if missing:
        return None, missing
    live_build = index["live_build"]
    if load_statements_cached(index_dir, live_build) is None:
        return None, _index_missing(
            index_dir, live_build,
            f"no statement summaries for Live {live_build} at {statements_path(index_dir, live_build)}"
            " (an outline needs them; build-index writes them unless --no-statements)")
    return index, None


def load_statements_cached(index_dir: Path, live_build: str) -> dict | None:
    """The statement summaries of a build loaded by `_open(..., with_statements=True)`."""
    return _load(index_dir, live_build, True)[1]


def outline_script(name: str, index_dir: Path, live_build: str | None = None) -> dict:
    """The outline of one Remote Script (or library): its classes with their roles and own
    members, the Specification fields it sets, its component map and mappings (v3), and the
    elements, components and layers its code creates, without function bodies. `name` is a
    script in Live's install, or a path to a script folder (`./my_script`, `examples/X`).
    See `outline.py` for how each part is found."""
    index, missing = _with_statements(index_dir, live_build)
    if missing:
        return missing
    live_build = index["live_build"]
    if is_script_folder(name):
        answer, why = outline_folder(Path(name), index)
        if answer is None:
            return {"status": "not_found", "live_build": live_build, "message": why}
        return {"status": "ok", "live_build": live_build, "confidence": "observed", **answer}
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
    index, missing = _open(index_dir, live_build, with_statements=True)  # the framework checks read its code
    if missing:
        return missing
    return {"status": "ok", "live_build": index["live_build"], "confidence": "observed",
            **validate_folder(folder.resolve(), index)}


def check_names(index_dir: Path, live_build: str | None = None, folder: Path | None = None,
                names: list[str] | None = None) -> dict:
    """Where each API name a script folder uses, or each name of a list, is known in one build:
    the index (observed), Ableton's scripts' calls (observed), Structure Void (documented), Python,
    or nowhere (`names.py`). Facts, not errors: `validate` gives those."""
    from .names import check, check_list

    if (folder is None) == (names is None):
        raise ValueError("check_names takes a folder or a list of names")
    if folder is not None:
        folder = Path(folder).expanduser()
        if not folder.is_dir():
            return {"status": "not_found", "live_build": live_build, "message": f"no script folder at {folder}"}
    index, missing = _open(index_dir, live_build, with_statements=True)
    if missing:
        return missing
    live_build = index["live_build"]
    statements = load_statements_cached(index_dir, live_build)
    doc = load_document(index_dir, live_major(live_build))
    if folder is not None:
        return {"status": "ok", "confidence": "observed", **check(folder.resolve(), index, statements, doc)}
    resolver = Resolver(index)
    return {"status": "ok", **check_list(names, index, statements, doc,
                                          lambda n: find_class_keys(index, resolver, n))}


def build_stubs(index_dir: Path, live_build: str | None = None, out: Path | None = None,
                observed_only: bool = False, project: Path | None = None) -> dict:
    """Write type stubs of one build for a language server (`stubs.py`); default folder:
    `<index dir>/stubs/<build>`. With `project` (not with `out`): into `<project>/stubs`, and the
    project gets its pyright config and ignore line (`set_up_project`, Decision 56)."""
    from .stubs import set_up_project, write_stubs

    if out and project:
        raise ValueError("out and project exclude each other")
    index, missing = _open(index_dir, live_build, with_statements=True)  # instance attributes come from them
    if missing:
        return missing
    live_build = index["live_build"]
    if project:
        project = Path(project).expanduser().resolve()
        if not project.is_dir():
            return {"status": "not_found", "live_build": live_build,
                    "message": f"no folder {project}: --project names your script project's folder"}
        out = project / "stubs"
    out = Path(out).expanduser() if out else Path(index_dir) / "stubs" / live_build
    try:
        answer = write_stubs(index, out, load_document(index_dir, live_major(live_build)), observed_only)
    except FileExistsError as e:
        return {"status": "not_found", "live_build": live_build, "message": str(e)}
    if project:
        answer["project"] = set_up_project(project)
    return answer
