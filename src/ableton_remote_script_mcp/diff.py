"""The diff between two builds' API indexes (plan 0001 step 4): what a script written for one
Live build may find added, removed or changed in another.

Compared: packages (added, removed, a script's framework generation), modules, module-level
members, classes (added, removed, their bases) and class members. A member has changed when its
kind, its parameters (name, kind, default), its setter (a property) or its value (an attribute)
differ. Line numbers, docstrings and statement summaries are not compared: they move with every
build without changing the API.

Every fact in the answer is `observed` in the build it names. The diff of a beta build holds
facts from that beta (CLAUDE.md: Live 13 beta findings stay local), so it is printed, never
written into the repo.
"""

from __future__ import annotations

from pathlib import Path


def _signature(member: dict) -> dict:
    sig = {"kind": member.get("kind")}
    if "params" in member:
        sig["params"] = [(p.get("name"), p.get("kind"), p.get("default")) for p in member["params"]]
    if member.get("setter") is not None:
        sig["setter"] = member["setter"]
    if member.get("kind") == "attribute":
        sig["value"] = member.get("value")
    return sig


def describe_member(member: dict) -> str:
    """`method(self, explicit=True)`, `property (setter)`, `attribute = 0`: what a diff shows."""
    kind = member.get("kind", "?")
    if kind == "attribute":
        return f"attribute = {member.get('value')}"
    if kind == "property":
        return "property (setter)" if member.get("setter") else "property"
    params = []
    for p in member.get("params", []):
        name = {"var_positional": "*", "var_keyword": "**"}.get(p.get("kind"), "") + p.get("name", "")
        params.append(f"{name}={p['default']}" if p.get("default") is not None else name)
    return f"{kind}({', '.join(params)})"


def _members(old: dict, new: dict) -> dict:
    out: dict = {"added": [], "removed": [], "changed": []}
    for name in sorted(set(old) | set(new)):
        if name not in old:
            out["added"].append({"name": name, "to": describe_member(new[name])})
        elif name not in new:
            out["removed"].append({"name": name, "from": describe_member(old[name])})
        elif _signature(old[name]) != _signature(new[name]):
            out["changed"].append({"name": name, "from": describe_member(old[name]), "to": describe_member(new[name])})
    return out


def _empty(members: dict) -> bool:
    return not any(members.values())


def _bases(c: dict) -> list[str]:
    return [b.get("resolved") or b.get("expr") for b in c.get("bases", [])]


def _top(fact_key: str) -> str:
    """The package a fact key belongs to (`push3-helper:` facts keep their prefix)."""
    prefix, _, name = fact_key.rpartition(":")
    top = name.split(".")[0]
    return f"{prefix}:{top}" if prefix else top


def _within(key: str, name: str, under: str | None) -> bool:
    if not under:
        return True
    return any(x == under or x.startswith(under + ".") for x in (key, name))


def diff_indexes(old: dict, new: dict, under: str | None = None) -> dict:
    """The diff of two loaded indexes (`under`: only this package or module and what is in it)."""
    def keep(entries: dict) -> dict:
        return {k: v for k, v in entries.items() if _within(k, v.get("name", k), under)}

    packages: dict = {"added": [], "removed": [], "changed": []}
    po, pn = keep(old.get("packages", {})), keep(new.get("packages", {}))
    for k in sorted(set(po) | set(pn)):
        if k not in po:
            packages["added"].append({"name": k, "kind": pn[k].get("kind"), "framework": pn[k].get("framework")})
        elif k not in pn:
            packages["removed"].append({"name": k, "kind": po[k].get("kind"), "framework": po[k].get("framework")})
        elif po[k].get("framework") != pn[k].get("framework"):
            packages["changed"].append({"name": k, "framework": {"from": po[k].get("framework"),
                                                                  "to": pn[k].get("framework")}})

    modules: dict = {"added": [], "removed": [], "changed": []}
    mo, mn = keep(old.get("modules", {})), keep(new.get("modules", {}))
    for k in sorted(set(mo) | set(mn)):
        if k not in mo:
            modules["added"].append(k)
        elif k not in mn:
            modules["removed"].append(k)
        else:
            members = _members(mo[k].get("members", {}), mn[k].get("members", {}))
            if not _empty(members):
                modules["changed"].append({"name": k, "members": members})

    classes: dict = {"added": [], "removed": [], "changed": []}
    co, cn = keep(old.get("classes", {})), keep(new.get("classes", {}))
    for k in sorted(set(co) | set(cn)):
        if k not in co:
            classes["added"].append(k)
        elif k not in cn:
            classes["removed"].append(k)
        else:
            entry: dict = {"name": k}
            if _bases(co[k]) != _bases(cn[k]):
                entry["bases"] = {"from": _bases(co[k]), "to": _bases(cn[k])}
            members = _members(co[k].get("members", {}), cn[k].get("members", {}))
            if not _empty(members):
                entry["members"] = members
            if len(entry) > 1:
                classes["changed"].append(entry)

    return {"status": "ok", "from": old["live_build"], "to": new["live_build"], "under": under,
            "packages": packages, "modules": modules, "classes": classes,
            "by_package": _by_package(modules, classes), "confidence": "observed"}


def _by_package(modules: dict, classes: dict) -> list[dict]:
    """Counts per top-level package, the most changed first."""
    counts: dict[str, dict] = {}

    def bump(key: str, what: str) -> None:
        counts.setdefault(_top(key), {"package": _top(key), "modules_added": 0, "modules_removed": 0,
                                      "classes_added": 0, "classes_removed": 0, "classes_changed": 0,
                                      "members_changed": 0})[what] += 1

    for k in modules["added"]:
        bump(k, "modules_added")
    for k in modules["removed"]:
        bump(k, "modules_removed")
    for c in modules["changed"]:
        for _ in range(sum(len(v) for v in c["members"].values())):
            bump(c["name"], "members_changed")
    for k in classes["added"]:
        bump(k, "classes_added")
    for k in classes["removed"]:
        bump(k, "classes_removed")
    for c in classes["changed"]:
        bump(c["name"], "classes_changed")
        for _ in range(sum(len(v) for v in c.get("members", {}).values())):
            bump(c["name"], "members_changed")
    total = lambda r: sum(v for k, v in r.items() if k != "package")
    return sorted(counts.values(), key=lambda r: (-total(r), r["package"]))


def diff_builds(from_build: str, to_build: str, index_dir: Path, under: str | None = None) -> dict:
    """The query core's diff: `index_missing` when either build has no index."""
    from .query import _open

    old, missing = _open(index_dir, from_build)
    if missing:
        return missing
    new, missing = _open(index_dir, to_build)
    if missing:
        return missing
    return diff_indexes(old, new, under)
