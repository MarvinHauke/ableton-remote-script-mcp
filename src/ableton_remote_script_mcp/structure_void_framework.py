"""Structure Void's framework reference as a `documented` cross-check (plan 0001 step 6,
Decisions 18 and 51).

midiremotescripts.structure-void.com has one page per module of Live's Remote Scripts (for Live
12: `reference/live12/<module>/`): its classes with their bases, each member's argument names (no
defaults) and the module's functions, from an unstated Live 12.x. The site's MkDocs search index
(`search/search_index.json`, about 34 MB) holds every heading of every page in page order, so
one download gives all of them. This reads it into `structure-void-live<N>-framework.json` next
to the API index. The search index and the document stay on this machine: the site is
CC BY-NC-SA 4.0. Every fact names its page.

The comparison with our index (`compare_class`, `cross_check`) lists, per class, the members
only one side has, the members whose argument names differ, and different bases. A difference
can be Structure Void's other Live 12.x build, or a gap in our extractor: the comparison says
where to look, it decides nothing. Our index's facts stay `observed`; Structure Void's are
`documented`.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .structure_void import LICENCE, SITE, _get, _text

SEARCH_INDEX = "search/search_index.json"
_CLASS = re.compile(r"^class\s+([A-Za-z_][\w.]*)\s*(?:\((.*)\))?\s*$")
_CALL = re.compile(r"^([A-Za-z_]\w*)\((.*)\)\s*$")
_CODE = re.compile(r"<code>(.*?)</code>", re.DOTALL)


def framework_path(index_dir: Path, live: str) -> Path:
    return Path(index_dir) / f"structure-void-live{live}-framework.json"


def _args(text: str) -> list[str]:
    return [a.strip().lstrip("*") for a in text.split(",") if a.strip()]


def parse_search_index(data: dict, live: str) -> dict:
    """{module: {"url", "classes": {name: {"bases", "members", "url"}}, "functions"}} of one
    Live version's framework pages (the runtime pages are `structure_void.py`'s)."""
    prefix = f"reference/live{live}/"
    modules: dict[str, dict] = {}
    module = section = cls = None
    for entry in data.get("docs", []):
        page, _, anchor = entry.get("location", "").partition("#")
        if not page.startswith(prefix):
            continue
        name = page[len(prefix):].rstrip("/")
        if not name or "/" in name or name.endswith(".runtime"):
            module = None
            continue
        title = _text(entry.get("title", ""))
        if not anchor:
            module = modules.setdefault(name, {"url": f"{SITE}/{page}", "classes": {}, "functions": {}})
            section = cls = None
            continue
        if module is None:
            continue
        if title in ("Classes", "Functions", "Attributes") and (title != "Attributes" or cls is None):
            section, cls = title.lower(), None
            continue
        if m := _CLASS.match(title):
            bases = _CODE.findall(entry.get("text", "")) or _args(m[2] or "")
            cls = module["classes"][m[1]] = {"bases": [_text(b) for b in bases], "members": {},
                                            "url": f"{SITE}/{page}#{anchor}"}
            section = "classes"
            continue
        if title == "Attributes" and cls is not None:
            for item in _CODE.findall(entry.get("text", "")):  # `name` or `name = value`
                cls["members"].setdefault(_text(item).split("=", 1)[0].strip(), {"kind": "attribute"})
            continue
        if not (m := _CALL.match(title)):
            continue
        if section == "functions" or cls is None:
            module["functions"][m[1]] = {"args": _args(m[2])}
        elif m[1] in cls["members"] and cls["members"][m[1]].get("args") is not None:
            cls["members"][m[1]]["kind"] = "property"  # a getter and a setter: two headings
            cls["members"][m[1]]["setter"] = True
        else:
            cls["members"][m[1]] = {"kind": "method", "args": _args(m[2])}
    return modules


def import_framework(index_dir: Path, live: str = "12", refresh: bool = False, fetch=_get, log=print) -> dict:
    """Fetch (or reuse) the site's search index and write the framework document."""
    cache = Path(index_dir) / "structure-void" / "search_index.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not cache.is_file():
        cache.write_text(fetch(f"{SITE}/{SEARCH_INDEX}"), encoding="utf-8")
    modules = parse_search_index(json.loads(cache.read_text(encoding="utf-8")), live)
    if not modules:
        raise ValueError(f"the search index of {SITE} has no framework pages for Live {live}")
    doc = {"source": "Structure Void, Live Object Model & framework reference (framework pages)",
           "site": SITE, "licence": LICENCE, "live": live, "covers": f"an unstated Live {live}.x build",
           "confidence": "documented", "fetched": datetime.now(UTC).isoformat(timespec="seconds"),
           "modules": dict(sorted(modules.items()))}
    out = framework_path(index_dir, live)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    classes = sum(len(m["classes"]) for m in modules.values())
    log(f"wrote {out}: {len(modules)} modules, {classes} classes from the framework pages")
    return doc


def load_framework(index_dir: Path, live: str) -> dict | None:
    try:
        return json.loads(framework_path(index_dir, live).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _our_args(member: dict) -> list[str] | None:
    params = member.get("params")
    return None if params is None else [p["name"] for p in params]


def _mangled(name: str, qualname: str) -> str:
    """A page shows a private method as written (`__on_x`); Python stores it as `_Class__on_x`."""
    if name.startswith("__") and not name.endswith("__"):
        return f"_{qualname.rsplit('.', 1)[-1].lstrip('_')}{name}"
    return name


def compare_class(ours: dict, theirs: dict) -> dict:
    """What Structure Void's page of a class says that our index doesn't, and the other way round.

    `ours` is an index class (its own members), `theirs` the page's class. Arguments are compared
    by name and order only (the pages have no defaults); a member whose page heading has no
    argument list (an attribute) is compared by name.
    """
    def dunder_attr(name: str, m: dict) -> bool:  # `__events__`, `__doc__`: the pages leave these out
        return name.startswith("__") and name.endswith("__") and m.get("kind") == "attribute"

    mine = {n: m for n, m in ours.get("members", {}).items() if not dunder_attr(n, m)}
    page = {_mangled(n, ours.get("qualname", "")): m for n, m in theirs.get("members", {}).items()
            if not dunder_attr(n, m)}
    differ = []
    for name in sorted(set(mine) & set(page)):
        a, b = _our_args(mine[name]), page[name].get("args")
        if a is not None and b is not None and a != b and page[name].get("kind") != "property":
            differ.append({"name": name, "observed": a, "documented": b})
    exprs = [b["expr"] for b in ours.get("bases", [])]
    our_bases = [e.split("[", 1)[0].rsplit(".", 1)[-1] for e in exprs]
    meta = str(ours.get("keywords", {}).get("metaclass", "")).rsplit(".", 1)[-1]
    their_bases = [b.rsplit(".", 1)[-1] for b in theirs.get("bases", []) if b.rsplit(".", 1)[-1] != meta]
    if any("[" in e for e in exprs):  # `View[ContentType]`: the pages flatten it to `View, ContentType`
        rest = iter(their_bases)
        if all(b in rest for b in our_bases):
            their_bases = our_bases
    out = {"source": theirs["url"], "only_documented": sorted(set(page) - set(mine)),
           "only_observed": sorted(set(mine) - set(page)), "args_differ": differ}
    if (ours.get("bases_parsed", True) and our_bases != their_bases and their_bases != ["object"]
            and (our_bases or their_bases)):
        out["bases_differ"] = {"observed": our_bases, "documented": their_bases}
    out["agrees"] = not (out["only_documented"] or out["only_observed"] or differ or "bases_differ" in out)
    return out


def page_class(doc: dict, module: str, qualname: str) -> dict | None:
    return (doc.get("modules", {}).get(module) or {}).get("classes", {}).get(qualname)


def _ours(classes: dict, qualname: str, bases: list[str]) -> dict | None:
    """The index's class for a page's class: by qualname, or a nested class whose page heading
    gives only its own name (`Transport` for `Notifications.Transport`): the only one of that
    name, or the only one of them with the page's bases."""
    if qualname in classes:
        return classes[qualname]
    nested = [c for q, c in classes.items() if q.endswith("." + qualname)]
    if len(nested) > 1:
        tails = [b.rsplit(".", 1)[-1] for b in bases]
        nested = [c for c in nested if [b["expr"].rsplit(".", 1)[-1] for b in c.get("bases", [])] == tails]
    return nested[0] if len(nested) == 1 else None


def cross_check(index: dict, doc: dict, under: str | None = None) -> dict:
    """Every module and class on Structure Void's pages against one build's index."""
    def within(name: str) -> bool:
        return not under or name == under or name.startswith(under + ".")

    ours_by_module: dict[str, dict] = {}
    for c in index["classes"].values():
        if c["root"] == "scripts":
            ours_by_module.setdefault(c["module"], {})[c["qualname"]] = c
    modules_missing, classes_missing, classes_differ, agree = [], [], [], 0
    for module, page in doc["modules"].items():
        if not within(module):
            continue
        if module not in index["modules"]:
            modules_missing.append({"module": module, "source": page["url"]})
            continue
        for qualname, theirs in page["classes"].items():
            ours = _ours(ours_by_module.get(module, {}), qualname, theirs["bases"])
            if ours is None:
                several = sum(q.endswith("." + qualname) for q in ours_by_module.get(module, {})) > 1
                classes_missing.append({"class": f"{module}.{qualname}", "source": theirs["url"],
                                        "reason": "several nested classes of that name" if several
                                        else "no class of that name"})
                continue
            result = compare_class(ours, theirs)
            if result["agrees"]:
                agree += 1
            else:
                classes_differ.append({"class": f"{module}.{qualname}", **result})
    pages = {m for m in doc["modules"] if within(m)}
    not_on_pages = sorted(m for m, e in index["modules"].items()
                          if e["root"] == "scripts" and within(m) and m not in doc["modules"])
    return {"status": "ok", "live_build": index["live_build"], "covers": doc["covers"], "licence": doc["licence"],
            "under": under, "pages": len(pages), "classes_agree": agree, "modules_missing": modules_missing,
            "classes_missing": classes_missing, "classes_differ": classes_differ,
            "modules_not_on_pages": not_on_pages}
