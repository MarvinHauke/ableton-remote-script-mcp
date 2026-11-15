"""Names resolved to what defines them, and a class's lineage, over one build's index.

A name such as `ableton.v3.control_surface.Component` is often a re-export: the package binds
`Component` by importing it from `.component`. `resolve` follows those imports, module-level
aliases (`Foo = Bar`) and star imports (`from m import *`) to the class or module that defines
the name. Resolution stays inside one root: the Push 3 helper's Python cannot see the Remote
Scripts folder, and the other way round.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .extractor import BUILTINS
from .index_store import SCRIPTS_ROOT, fact_key

_DOTTED = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
_MAX_DEPTH = 32
OBJECT = "external:builtins.object"


@dataclass(frozen=True)
class Resolved:
    """What a name points at.

    status: "class" or "module" (`key` is the index key), "external" (outside the index: builtins,
    `typing`, the C++ `Live` module…; `name` is the qualified name) or "unresolved".
    """

    status: str
    name: str
    key: str | None = None
    via: tuple[str, ...] = ()  # the names passed through on the way, e.g. a re-export


def _strip_subscript(name: str) -> str:
    return name.split("[", 1)[0]


class Resolver:
    def __init__(self, index: dict):
        self.classes: dict = index["classes"]
        self.modules: dict = index["modules"]
        self._tops: dict[str, set[str]] = {}
        for m in self.modules.values():
            self._tops.setdefault(m["root"], set()).add(m["name"].split(".")[0])
        self._mro: dict[str, list[str]] = {}
        self._busy: set[str] = set()

    def mro(self, key: str) -> list[str] | None:
        """The indexed classes along a class's MRO (itself first); None while it is being computed."""
        if key not in self._mro:
            if key in self._busy:
                return None
            self._busy.add(key)
            try:
                self._mro[key] = [e["name"] for e in lineage(self, key).mro if e["status"] == "indexed"]
            finally:
                self._busy.discard(key)
        return self._mro[key]

    def resolve(self, name: str, root: str = SCRIPTS_ROOT) -> Resolved:
        """A qualified name (`pkg.module.Name`) resolved to its definition."""
        return self._resolve(_strip_subscript(name), root, (), 0)

    def resolve_in_module(self, expr: str, module: str, root: str) -> Resolved:
        """A name as written inside `module` (a base expression, an alias value)."""
        expr = _strip_subscript(expr)
        found = self._resolve(f"{module}.{expr}", root, (), 0)
        if found.status == "unresolved" and expr.split(".")[0] in BUILTINS:
            return Resolved("external", f"builtins.{expr}")
        return found

    def _resolve(self, name: str, root: str, via: tuple[str, ...], depth: int) -> Resolved:
        name = name.replace(".__init__", "")  # `import pkg.__init__` runs the package's own code
        if depth > _MAX_DEPTH or name in via:
            return Resolved("unresolved", name, via=via)
        key = fact_key(root, name)
        if key in self.classes:
            return Resolved("class", name, key, via)
        if key in self.modules:
            return Resolved("module", name, key, via)
        parts = name.split(".")
        if parts[0] == "builtins" or parts[0] not in self._tops.get(root, set()):
            return Resolved("external", name, via=via)
        for i in range(len(parts) - 1, 0, -1):  # the longest prefix that is a class or a module
            prefix = fact_key(root, ".".join(parts[:i]))
            if prefix in self.classes:
                return self._in_class(prefix, parts[i:], root, via + (name,), depth + 1)
            if prefix in self.modules:
                return self._in_module(prefix, parts[i:], root, via + (name,), depth + 1)
        return Resolved("unresolved", name, via=via)

    def _alias(self, value: str, module: str, suffix: str, root: str, via, depth) -> Resolved:
        """`Foo = Bar` in `module`: resolve `Bar` there."""
        target = self._resolve(f"{module}.{value}{suffix}", root, via, depth)
        if target.status == "unresolved" and value.split(".")[0] in BUILTINS:
            return Resolved("external", f"builtins.{value}{suffix}", via=via)
        return target

    def _in_module(self, key: str, rest: list[str], root: str, via, depth) -> Resolved:
        mod = self.modules[key]
        module = mod["name"]
        head, suffix = rest[0], "".join(f".{t}" for t in rest[1:])
        unresolved = Resolved("unresolved", f"{module}.{head}{suffix}", via=via)
        if head in mod.get("imports", {}):
            return self._resolve(mod["imports"][head] + suffix, root, via, depth)
        member = mod.get("members", {}).get(head)
        if member:  # an alias (Foo = Bar), or a function or value that is not a class
            value = member.get("value") or ""
            if member["kind"] == "attribute" and _DOTTED.match(value) and value != head:
                return self._alias(value, module, suffix, root, via, depth)
            return unresolved
        if not head.startswith("_"):
            for star in reversed(mod.get("star_imports", [])):  # the last star import wins
                found = self._resolve(f"{star}.{head}{suffix}", root, via, depth)
                if found.status in ("class", "module"):
                    return found
        return unresolved

    def _in_class(self, key: str, rest: list[str], root: str, via, depth) -> Resolved:
        """`Class.Name`: a nested class or alias in the class body, else along its MRO, as Python
        looks up a class attribute."""
        head, suffix = rest[0], "".join(f".{t}" for t in rest[1:])
        cls = self.classes[key]
        start = f"{cls['module']}.{cls['qualname']}"
        order = self.mro(key)
        if order is None:  # inside this class's own MRO computation: its bases, depth-first
            order, stack = [], [key]
            while stack:
                k = stack.pop(0)
                if k in order:
                    continue
                order.append(k)
                bases = [self.resolve_base(self.classes[k], b) for b in self.classes[k]["bases"]]
                stack[:0] = [b.key for b in bases if b.status == "class" and b.key not in order]
        for k in order:
            c = self.classes[k]
            qualified = f"{c['module']}.{c['qualname']}"
            if fact_key(root, f"{qualified}.{head}") in self.classes:
                return self._resolve(f"{qualified}.{head}{suffix}", root, via, depth)
            member = c["members"].get(head)
            if member:
                value = member.get("value") or ""
                if member["kind"] == "attribute" and _DOTTED.match(value) and value != head:
                    return self._alias(value, c["module"], suffix, root, via, depth)
                break
        return Resolved("unresolved", f"{start}.{head}{suffix}", via=via)

    def resolve_base(self, cls: dict, base: dict) -> Resolved:
        """A class's base: in the enclosing class body first (nested classes), then the module."""
        expr, root = _strip_subscript(base["expr"]), cls["root"]
        if "." in cls["qualname"]:
            enclosing = f"{cls['module']}.{cls['qualname'].rsplit('.', 1)[0]}"
            if fact_key(root, f"{enclosing}.{expr.split('.')[0]}") in self.classes:
                return self.resolve(f"{enclosing}.{expr}", root)
        found = self.resolve_in_module(expr, cls["module"], root)
        if found.key == fact_key(root, f"{cls['module']}.{cls['qualname']}"):
            # `class X(Y, X)`: while the class body runs, `X` still names what was imported as X
            imported = self.modules.get(fact_key(root, cls["module"]), {}).get("imports", {})
            head, _, tail = expr.partition(".")
            if head in imported:
                return self.resolve(imported[head] + (f".{tail}" if tail else ""), root)
            return Resolved("unresolved", expr)
        if found.status == "unresolved" and base.get("resolved"):
            found = self.resolve(base["resolved"], root)
        return found


@dataclass
class Lineage:
    """A class's method resolution order and every member it has, each with its origin."""

    mro: list[dict] = field(default_factory=list)
    bases: list[dict] = field(default_factory=list)  # the class's direct bases, as MRO entries
    members: dict[str, dict] = field(default_factory=dict)
    method: str = "c3"  # or "depth-first" when the bases admit no C3 order
    complete: bool = True  # False when a base along the way could not be resolved


def _c3(seqs: list[list[str]]) -> list[str] | None:
    seqs = [list(s) for s in seqs if s]
    out: list[str] = []
    while seqs:
        for seq in seqs:
            head = seq[0]
            if not any(head in s[1:] for s in seqs):
                break
        else:
            return None
        out.append(head)
        seqs = [s[1:] if s[0] == head else s for s in seqs]
        seqs = [s for s in seqs if s]
    return out


def lineage(resolver: Resolver, class_key: str, proxies: dict[str, str] | None = None) -> Lineage:
    """The class's MRO over the index, and its members resolved along it."""
    classes = resolver.classes
    nodes: dict[str, dict] = {}  # node id -> description
    bases_of: dict[str, list[str]] = {}

    def node_for_base(cls: dict, base: dict) -> str:
        found = resolver.resolve_base(cls, base)
        if found.status == "class":
            return found.key
        if found.status == "external":
            nid = f"external:{found.name}"
            desc = {"name": found.name, "status": "external"}
            if proxies and found.name in proxies:
                desc["proxy"] = proxies[found.name]
        else:
            nid = f"unresolved:{cls['module']}.{base['expr']}"
            desc = {"name": base["expr"], "status": "unresolved", "in_module": cls["module"]}
            if found.status == "module":
                desc["note"] = f"names the module {found.name}, not a class"
        nodes.setdefault(nid, desc)
        bases_of.setdefault(nid, [])
        return nid

    def visit(key: str) -> None:
        if key in bases_of:
            return
        cls = classes[key]
        nodes[key] = {"name": key, "status": "indexed"}
        bases_of[key] = []
        bases_of[key] = [node_for_base(cls, b) for b in cls["bases"]]
        for b in bases_of[key]:
            if b in classes:
                visit(b)

    visit(class_key)
    lin: dict[str, list[str] | None] = {}

    def linearize(nid: str, stack: frozenset = frozenset()) -> list[str] | None:
        if nid in lin:
            return lin[nid]
        if nid in stack:
            return None
        bases = bases_of.get(nid, [])
        if not bases and nid in classes and classes[nid].get("bases_parsed", True):
            bases = [OBJECT]  # `class X:` is an `object` subclass
            nodes.setdefault(OBJECT, {"name": "builtins.object", "status": "external"})
        parts = [linearize(b, stack | {nid}) for b in bases]
        result = None if any(p is None for p in parts) else _c3([*parts, list(bases)])
        lin[nid] = None if result is None else [nid, *result]
        return lin[nid]

    order = linearize(class_key)
    method = "c3"
    if order is None:  # inconsistent bases or a cycle: left-to-right depth-first, first visit wins
        method, order, seen = "depth-first", [], set()

        def dfs(nid: str) -> None:
            if nid in seen:
                return
            seen.add(nid)
            order.append(nid)
            for b in bases_of.get(nid, []):
                dfs(b)

        dfs(class_key)
    result = Lineage(method=method, bases=[nodes[b] for b in bases_of[class_key]])
    for nid in order:
        result.mro.append(nodes[nid])
        if nodes[nid]["status"] == "unresolved" or (
            nid in classes and not classes[nid].get("bases_parsed", True)
        ):
            result.complete = False
        if nid not in classes:
            continue
        for name, member in classes[nid]["members"].items():
            if name in result.members:
                result.members[name]["overrides"].append(nid)
            else:
                result.members[name] = {**member, "origin": nid, "overrides": []}
    return result
