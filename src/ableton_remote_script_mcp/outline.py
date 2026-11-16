"""The outline of one Remote Script, read from the API index (plan 0001 step 5).

What a script is made of, without its function bodies:
- its classes, each with its role (control surface, Specification, elements, component, element)
  and its own members with their signatures and what they override
- the Specification fields it sets (v3), with the framework's default for each
- its component map and mappings (v3): component names, the component each name builds, and
  which elements the mappings connect to which controls
- its elements, components and layers, found in the statement summaries of its methods and
  functions, the ones it inherits from other Remote Scripts and libraries included

Roles come from a class's MRO: the first framework class along it that is one of `ROLE_ROOTS`.
Names in statements are resolved where they are written, as `get_class` resolves bases.
"""

from __future__ import annotations

import ast
import re

from .index_store import SCRIPTS_ROOT, fact_key, generation
from .resolve import Resolver, lineage

ROLE_ROOTS = {  # a framework class name -> the role of every class that has it on its MRO
    "ControlSurface": "control surface",
    "SimpleControlSurface": "control surface",
    "ControlSurfaceSpecification": "specification",
    "ElementsBase": "elements",
    "ControlSurfaceComponent": "component",  # _Framework
    "Component": "component",  # ableton.v2, ableton.v3
    "ControlElement": "element",
    "Layer": "layer",
}
_SUBSCRIPT_TARGET = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*\[(?P<key>'[^']*'|\"[^\"]*\")\]$")
_MAX_FACTORY_DEPTH = 3
_SELF_TEST = re.compile(r"if (?P<negated>not )?self\.(?P<name>\w+)")
_COMPONENT_IN_TEXT = re.compile(r"""component=['"](\w+)['"]""")


def _literal_str(text: str | None) -> str | None:
    try:
        value = ast.literal_eval(text) if text else None
    except (ValueError, SyntaxError):
        return None
    return value if isinstance(value, str) else None


def _parse(text: str) -> ast.expr | None:
    try:
        return ast.parse(text, mode="eval").body
    except SyntaxError:  # "…" marks what the extractor did not model
        return None


def _callee_text(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _callee_text(node.value)
        return f"{owner}.{node.attr}" if owner else None
    return None


def _plain(node: ast.expr):
    """A mapping value: a string stays a string, dict(...) / {...} becomes a dict, the rest is text."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Constant) and node.value is None:
        return None
    if isinstance(node, ast.Call) and _callee_text(node.func) == "dict" and not node.args:
        return {k.arg: _plain(k.value) for k in node.keywords if k.arg}
    if isinstance(node, ast.Dict) and all(isinstance(k, ast.Constant) for k in node.keys):
        return {str(k.value): _plain(v) for k, v in zip(node.keys, node.values)}
    return ast.unparse(node)


class _Outliner:
    def __init__(self, index: dict, package_key: str):
        self.index = index
        self.classes: dict = index["classes"]
        self.modules: dict = index["modules"]
        self.package = index["packages"][package_key]
        self.root = self.package["root"]
        self.resolver = Resolver(index)
        self._roles: dict[str, str | None] = {}
        self._lineages: dict = {}
        self._factories: dict = {}
        self._units: list | None = None
        name = self.package["name"]
        self.module_keys = [k for k, m in self.modules.items()
                            if m["root"] == self.root and (m["name"] == name or m["name"].startswith(name + "."))]
        self.class_keys = [k for k, c in self.classes.items()
                           if c["root"] == self.root and fact_key(self.root, c["module"]) in self.module_keys]
        self.class_keys.sort(key=lambda k: (self.classes[k]["module"], self.classes[k]["line"]))

    # --- classes and roles ----------------------------------------------------------------

    def lineage(self, key: str):
        if key not in self._lineages:
            self._lineages[key] = lineage(self.resolver, key)
        return self._lineages[key]

    def is_framework(self, key: str) -> bool:
        return key in self.classes and generation(self.classes[key]["module"]) is not None

    def role(self, key: str) -> str | None:
        if key not in self._roles:
            self._roles[key] = None
            for k in self.resolver.mro(key) or []:
                if self.is_framework(k) and self.classes[k]["name"] in ROLE_ROOTS:
                    self._roles[key] = ROLE_ROOTS[self.classes[k]["name"]]
                    break
        return self._roles[key]

    def framework_root(self, key: str, name: str) -> str | None:
        """The framework class called `name` on the MRO of `key`."""
        return next((k for k in self.resolver.mro(key) or [] if self.is_framework(k) and self.classes[k]["name"] == name), None)

    def class_entry(self, key: str) -> dict:
        cls = self.classes[key]
        lin = self.lineage(key)
        members = []
        for name, m in cls["members"].items():
            entry = {"name": name, "kind": m["kind"], "line": m.get("line")}
            if "params" in m:
                entry["params"] = m["params"]
            if m["kind"] == "attribute":
                entry["value"] = m.get("value")
            overrides = lin.members.get(name, {}).get("overrides", [])
            if overrides:
                entry["overrides"] = overrides[0]
            members.append(entry)
        return {
            "qualified_name": key,
            "name": cls["name"],
            "module": cls["module"],
            "line": cls["line"],
            "role": self.role(key),
            "bases": [{"expr": b["expr"], "defined_in": node["name"], "status": node["status"]}
                      for b, node in zip(cls["bases"], lin.bases)],
            "members": members,
            **({"docstring": cls["docstring"]} if cls.get("docstring") else {}),
        }

    # --- the code the script runs ---------------------------------------------------------

    def units(self) -> list[dict]:
        """Every method and function the script's own code runs: the module functions of the
        package, and the methods of every class along its classes' MROs that is not the
        framework's (methods inherited from other Remote Scripts and libraries count, and so do
        overridden ones, which an override usually calls through `super()`)."""
        if self._units is not None:
            return self._units
        out, seen = [], set()
        for mkey in self.module_keys:
            mod = self.modules[mkey]
            for name, m in mod["members"].items():
                if m["kind"] == "function":
                    out.append({"label": f"{mod['name']}.{name}", "module": mod["name"], "in_class": None,
                                "name": name, "statements": m.get("statements", []),
                                "takes_arguments": _takes_arguments(m)})
        for key in self.class_keys:
            for origin in self.resolver.mro(key) or []:
                if self.is_framework(origin) or origin in seen:
                    continue
                seen.add(origin)
                c = self.classes[origin]
                for name, m in c["members"].items():
                    if "params" in m:
                        out.append({"label": f"{c['module']}.{c['qualname']}.{name}", "module": c["module"],
                                    "in_class": key, "name": name, "statements": m.get("statements", []),
                                "takes_arguments": _takes_arguments(m)})
        self._units = out
        return out

    def resolve_callee(self, callee: str, module: str, in_class: str | None, aliases: dict) -> tuple | None:
        """("class", key) | ("function", module key, name, member) | ("method", origin, name, member)."""
        if not callee or "(" in callee or "[" in callee:
            return None
        head, _, rest = callee.partition(".")
        if head == "self":
            if in_class is None or not rest or "." in rest:
                return None
            m = self.lineage(in_class).members.get(rest)
            if m and m["origin"] in self.classes and "params" in m:
                return ("method", m["origin"], rest, m)
            return None
        if head in aliases:
            callee = aliases[head] + (f".{rest}" if rest else "")
        found = self.resolver.resolve_in_module(callee, module, self.root)
        if found.status == "class":
            return ("class", found.key)
        if found.status == "function":
            name = found.name.rsplit(".", 1)[-1]
            return ("function", found.key, name, self.modules[found.key]["members"][name])
        return None

    def factory_of(self, target: tuple, in_class: str | None, depth: int = 0) -> str | None:
        """The element class a function or method returns, if it returns one (a factory)."""
        memo = (target[0], target[1], target[2], in_class)
        if memo in self._factories:
            return self._factories[memo]
        self._factories[memo] = None
        if depth >= _MAX_FACTORY_DEPTH:
            return None
        module = self.modules[target[1]]["name"] if target[0] == "function" else self.classes[target[1]]["module"]
        aliases: dict = {}
        result = None
        for st in target[3].get("statements", []):
            if "call" not in st:
                continue
            _alias(st, aliases)
            if st.get("target") != "return":
                continue
            r = self.resolve_callee(st["call"], module, in_class, aliases)
            if r and r[0] == "class" and self.role(r[1]) == "element":
                result = r[1]
            elif r and r[0] in ("function", "method"):
                result = self.factory_of(r, in_class, depth + 1)
            if result:
                break
        self._factories[memo] = result
        return result

    def scan(self) -> dict:
        elements, components, layers = [], [], []
        # method name -> (where its caller stores the result, what the call runs under)
        returned_to: dict[str, tuple[str, list]] = {}
        for unit in self.units():
            for st in unit["statements"]:
                if "call" in st and st.get("target") and st["call"].startswith("self.") and st["target"] != "return":
                    returned_to.setdefault(st["call"][len("self."):], (st["target"], st.get("under", [])))
        for unit in self.units():
            aliases: dict = {}
            filled = _comprehension_targets(unit["statements"])
            for i, st in enumerate(unit["statements"]):
                if "call" not in st:
                    continue
                _alias(st, aliases)
                calls = [(st["call"], st["args"], st["kwargs"], st.get("target"), None)]
                for text in [*st["args"], *st["kwargs"].values()]:
                    node = _parse(text)
                    for sub in ast.walk(node) if node is not None else ():
                        if isinstance(sub, ast.Call) and _callee_text(sub.func):
                            calls.append((_callee_text(sub.func), [ast.unparse(a) for a in sub.args],
                                          {k.arg or "**": ast.unparse(k.value) for k in sub.keywords}, None, st["call"]))
                caller_under = []  # self._x = self._create_x(): the call site's conditions apply too
                if st.get("target") == "return" and not unit["takes_arguments"] and unit["name"] in returned_to:
                    caller_under = returned_to[unit["name"]][1]
                for callee, args, kwargs, target, within in calls:
                    where = {"line": st["line"], "in": unit["label"], "under": caller_under + st.get("under", []),
                             "_class": unit["in_class"]}
                    if st.get("inside"):
                        where["inside"] = st["inside"]
                        if i in filled and not target:
                            where["target"] = f"{filled[i]}[…]"
                    if within:
                        where["within"] = within
                    if target and target != "return":
                        where["target"] = target
                    elif target == "return":
                        if unit["takes_arguments"]:  # a factory such as make_button(channel, identifier)
                            where["returned_by_factory"] = True  # listed where it is called instead
                        elif unit["name"] in returned_to:  # self._mixer = self._create_mixer()
                            where["target"] = returned_to[unit["name"]][0]
                            where["returned_by"] = unit["name"]
                    self._classify(unit, callee, args, kwargs, where, aliases, elements, components, layers)
        for entry in [*elements, *components, *layers]:
            cls = entry.pop("_class")
            if not entry["under"]:
                del entry["under"]
                continue
            entry["runs"], decided = self.runs(entry["under"], cls)
            if decided:
                entry["decided_by"] = decided
        return {"elements": elements, "components": components, "layers": layers}

    def runs(self, under: list[str], cls: str | None) -> tuple[bool | None, str | None]:
        """Whether code under these conditions runs for the outlined class: False when one is
        `if self.X` / `if not self.X` and X is a literal class attribute that makes it false; True
        when every condition is such a test that holds, or a loop; None when that can't be told."""
        result: bool | None = True
        decided = []
        for label in under:
            if label.startswith("for "):
                continue
            match = _SELF_TEST.fullmatch(label)
            member = self.lineage(cls).members.get(match["name"]) if match and cls else None
            if not member or member["kind"] != "attribute" or not member.get("value_literal", True):
                result = None
                continue
            try:
                value = bool(ast.literal_eval(member.get("value") or ""))
            except (ValueError, SyntaxError):
                result = None
                continue
            holds = value != bool(match["negated"])
            decided.append(f"{match['name']} = {member['value']} in {member['origin']}")
            if not holds:
                return False, decided[-1]
        return result, ("; ".join(decided) if decided and result else None)

    def _classify(self, unit, callee, args, kwargs, where, aliases, elements, components, layers) -> None:
        r = self.resolve_callee(callee, unit["module"], unit["in_class"], aliases)
        if r is None:
            return
        name = _literal_str(kwargs.get("name")) or kwargs.get("name")
        factory_result = where.pop("returned_by_factory", False)
        if r[0] == "method" and self.is_framework(r[1]) and r[2].startswith("add_") and unit["in_class"] and (
            self.role(unit["in_class"]) == "elements"
        ):  # v3: Elements.__init__ calls self.add_button(identifier, name, ...)
            bound = _bind(r[3], args, kwargs)
            elements.append({"name": _literal_str(bound.get("name") or bound.get("base_name")) or name,
                             "defined_by": f"{r[1]}.{r[2]}", "arguments": bound, **where})
            return
        if r[0] == "class":
            role = self.role(r[1])
            entry = {"class": r[1], "arguments": _arguments(args, kwargs), **where}
            if role == "element" and not factory_result:
                elements.append({"name": name, **entry})
            elif role == "component":
                components.append({"name": name, **entry})
            elif role == "layer":
                layers.append({"controls": {k: v for k, v in kwargs.items() if k != "priority"},
                               **({"priority": kwargs["priority"]} if "priority" in kwargs else {}), **where})
            return
        made = self.factory_of(r, unit["in_class"])
        if made and r[0] == "method" and not _takes_arguments(r[3]):
            return  # self._make_stop_all_button(): listed inside that method, with its name
        if made and not factory_result:
            elements.append({"name": name, "class": made, "via": callee, "arguments": _arguments(args, kwargs), **where})

    # --- v3: Specification, component map, mappings ----------------------------------------

    def specification(self, key: str) -> dict:
        lin = self.lineage(key)
        base = self.framework_root(key, "ControlSurfaceSpecification")
        defaults = self.lineage(base).members if base else {}
        fields = []
        for name, m in lin.members.items():
            if name.startswith("__") or m["origin"] not in self.classes or self.is_framework(m["origin"]):
                continue
            field = {"name": name, "line": m.get("line"), "set_in": m["origin"], "known": name in defaults}
            field["value"] = m.get("value") if m["kind"] == "attribute" else f"<{m['kind']} {name}>"
            if name in defaults:
                d = defaults[name]
                field["default"] = d.get("value") if d["kind"] == "attribute" else f"<{d['kind']}>"
            fields.append(field)
        return {"class": key, "framework_class": base, "fields": fields}

    def component_map(self, spec_key: str) -> list[dict]:
        entries: dict[str, dict] = {}
        base = self.framework_root(spec_key, "ControlSurfaceSpecification")
        gen = generation(self.classes[base]["module"]) if base else None
        for key, c in self.classes.items():  # the framework's defaults: ComponentMap fills itself
            if c["name"] != "ComponentMap" or c["root"] != self.root or generation(c["module"]) != gen:
                continue
            for m in c["members"].values():
                for st in m.get("statements", []):
                    target = st.get("store") or st.get("target") or ""
                    match = _SUBSCRIPT_TARGET.match(target)
                    if match and target.startswith("self["):
                        text = st["value"] if "store" in st else _call_text(st, with_target=False)
                        entries[ast.literal_eval(match["key"])] = self._map_entry(text, c["module"], "framework", st["line"])
        field = self.lineage(spec_key).members.get("component_map")
        if field and field["origin"] in self.classes and not self.is_framework(field["origin"]):
            node = _parse(field.get("value") or "")
            if isinstance(node, ast.Dict):
                module = self.classes[field["origin"]]["module"]
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        entry = self._map_entry(ast.unparse(v), module, "script", field.get("line"))
                        if k.value in entries:
                            entry["replaces_default"] = entries[k.value]["component"]
                        entries[k.value] = entry
        # names a control surface adds while it sets up: `self.component_map['Background'] = ...`,
        # in the framework's mapping mixin and in the script's own code
        framework_code = []
        for key in self.class_keys:
            if self.role(key) == "control surface":
                for k in self.resolver.mro(key) or []:
                    if self.is_framework(k):
                        c = self.classes[k]
                        framework_code += [(f"{c['module']}.{c['qualname']}.{n}", c["module"], m.get("statements", []))
                                           for n, m in c["members"].items()]
        script_code = [(u["label"], u["module"], u["statements"]) for u in self.units()]
        for source, code in (("framework", framework_code), ("script", script_code)):
            for label, module, statements in code:
                for st in statements:
                    target = st.get("store") or st.get("target") or ""
                    match = _SUBSCRIPT_TARGET.match(target)
                    if match and target.startswith("self.component_map["):
                        name = ast.literal_eval(match["key"])
                        text = st["value"] if "store" in st else _call_text(st, with_target=False)
                        entry = {**self._map_entry(text, module, source, st["line"]), "set_in": label}
                        if name in entries:
                            entry["replaces_default"] = entries[name]["component"]
                        entries.setdefault(name, entry) if source == "framework" else entries.update({name: entry})
        return [{"name": n, **e} for n, e in entries.items()]

    def _map_entry(self, text: str, module: str, source: str, line) -> dict:
        node = _parse(text)
        target = text
        if isinstance(node, ast.Call) and _callee_text(node.func) in ("partial", "functools.partial") and node.args:
            target = ast.unparse(node.args[0])
        elif isinstance(node, ast.Call):  # DialogComponent(): an instance of the class called
            target = ast.unparse(node.func)
        node = _parse(target)
        found = self.resolver.resolve_in_module(target, module, self.root) if node is not None and _callee_text(node) else None
        return {"component": text, "defined_in": found.key if found and found.status == "class" else None,
                "from": source, "line": line}

    def mapping_sections(self, spec_key: str) -> dict | None:
        """The sections the mappings function returns, each as (name, {key: value text}, line).
        `complete` is False when the function also fills the dict in a way this does not read
        (a computed key, `mappings.update(...)`, a value that is not a dict)."""
        field = self.lineage(spec_key).members.get("create_mappings_function")
        if not field or field["origin"] not in self.classes or self.is_framework(field["origin"]):
            return None
        module = self.classes[field["origin"]]["module"]
        if field["kind"] == "attribute":
            found = self.resolver.resolve_in_module(field.get("value") or "", module, self.root)
            if found.status != "function":
                return {"function": field.get("value"), "defined_in": None, "module": None, "sections": [],
                        "complete": False}
            name = found.name.rsplit(".", 1)[-1]
            function, statements = found.name, self.modules[found.key]["members"][name].get("statements", [])
            module = self.modules[found.key]["name"]
        else:
            function, statements = f"{field['origin']}.create_mappings_function", field.get("statements", [])
        sections, complete = [], True
        for st in statements:
            target = st.get("target") or st.get("store") or ""
            match = _SUBSCRIPT_TARGET.match(target)
            if "call" in st and st["call"] == "dict" and match:
                if "**" in st["kwargs"] or st["args"]:
                    complete = False
                sections.append((ast.literal_eval(match["key"]), dict(st["kwargs"]), st["line"]))
            elif "call" in st and st["call"] == "dict" and target == "return":
                for k, v in st["kwargs"].items():
                    node = _parse(v)
                    if isinstance(node, ast.Call) and _callee_text(node.func) == "dict":
                        sections.append((k, {kw.arg: ast.unparse(kw.value) for kw in node.keywords if kw.arg},
                                         st["line"]))
                    else:
                        complete = False
            elif "store" in st and match:
                node = _parse(st["value"])
                if isinstance(node, ast.Dict) and all(isinstance(k, ast.Constant) for k in node.keys):
                    sections.append((ast.literal_eval(match["key"]),
                                     {str(k.value): ast.unparse(v) for k, v in zip(node.keys, node.values)},
                                     st["line"]))
                else:
                    complete = False
            elif ("store" in st and st["store"].startswith("mappings[")) or (
                    "call" in st and st["call"].startswith("mappings.") and st["call"] != "mappings.items"):
                complete = False
        return {"function": function, "module": module, "sections": sections, "complete": complete}

    def mappings(self, spec_key: str) -> dict | None:
        found = self.mapping_sections(spec_key)
        if found is None:
            return None
        out = {"function": found["function"], "mappings": [_mapping(*s) for s in found["sections"]]}
        if "defined_in" in found:
            out["defined_in"] = None
        return out

    def outline(self) -> dict:
        pkg = self.package
        init = self.modules.get(fact_key(self.root, pkg["name"]), {})
        create = init.get("members", {}).get("create_instance")
        classes = [self.class_entry(k) for k in self.class_keys]
        answer = {
            "script": pkg["name"],
            "kind": pkg["kind"],
            "framework": pkg["framework"],
            "uses": pkg["uses"],
            "source": pkg["source"],
            "modules": [self.modules[k]["name"] for k in self.module_keys],
            "create_instance": [_call_text(st) for st in (create or {}).get("statements", []) if "call" in st],
            "classes": classes,
            "specification": None,
            "component_map": [],
            "mappings": None,
            "unknown_components": [],
            **self.scan(),
        }
        specs = [c["qualified_name"] for c in classes if c["role"] == "specification"]
        if specs:
            spec = self._used_spec(specs) or specs[0]
            answer["specification"] = self.specification(spec)
            answer["component_map"] = self.component_map(spec)
            answer["mappings"] = self.mappings(spec)
            names = {e["name"] for e in answer["component_map"]}
            mappings = (answer["mappings"] or {}).get("mappings", [])
            used = {m["name"] for m in mappings if m["kind"] == "component"}
            used |= _components_named(mappings)
            for m in mappings:
                if m["kind"] == "component":
                    m["in_component_map"] = m["name"] in names
            for e in answer["component_map"]:
                e["used_by_mappings"] = e["name"] in used
            # a mode may name another mappings entry (a modes component) or a component-map name
            answer["unknown_components"] = sorted(used - names - {m["name"] for m in mappings})
        return answer

    def _used_spec(self, specs: list[str]) -> str | None:
        """With several Specification classes, the one `create_instance` passes on."""
        init = self.modules.get(fact_key(self.root, self.package["name"]), {})
        create = init.get("members", {}).get("create_instance") or {}
        texts = " ".join(_call_text(st) for st in create.get("statements", []) if "call" in st)
        for key in specs:
            if re.search(rf"\b{re.escape(self.classes[key]['name'])}\b", texts):
                return key
        return None


def _alias(st: dict, aliases: dict) -> None:
    """`make_color_button = partial(make_button, skin=...)`: calls to the local name are calls to make_button."""
    target = st.get("target") or ""
    if st["call"] in ("partial", "functools.partial") and st["args"] and target.isidentifier():
        aliases[target] = st["args"][0]


def _comprehension_targets(statements: list[dict]) -> dict[int, str]:
    """`self._pads = [make_button(...) for i in range(8)]`: the comprehension's calls come first,
    then the store of its result. Index of each call inside a comprehension -> that target."""
    out, pending = {}, []
    for i, st in enumerate(statements):
        if st.get("inside", "").startswith("<") and st.get("inside") != "<lambda>":
            pending.append(i)
            continue
        made = st.get("value") if "store" in st else None
        if pending and made is not None and "… for … in" in made:
            out.update({j: st["store"] for j in pending})
        elif pending and "call" in st and st.get("target") and any("… for … in" in a for a in st["args"]):
            out.update({j: st["target"] for j in pending})
        pending = []
    return out


def _components_named(value) -> set[str]:
    """Component names a mapping refers to: `component="Session"` in a mode, at any depth."""
    if isinstance(value, dict):
        found = {value["component"]} if isinstance(value.get("component"), str) else set()
        return found.union(*(_components_named(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(_components_named(v) for v in value))
    return set(_COMPONENT_IN_TEXT.findall(value)) if isinstance(value, str) else set()


def _takes_arguments(member: dict) -> bool:
    return any(p["name"] not in ("self", "cls") for p in member.get("params", []))


def _call_text(st: dict, with_target: bool = True) -> str:
    parts = list(st["args"]) + [f"**{v}" if k == "**" else f"{k}={v}" for k, v in st["kwargs"].items()]
    text = f"{st['call']}({', '.join(parts)})"
    if not with_target or not st.get("target"):
        return text
    return f"return {text}" if st["target"] == "return" else f"{st['target']} = {text}"


def _arguments(args: list, kwargs: dict) -> dict:
    out = {f"#{i}": a for i, a in enumerate(args)}
    out.update(kwargs)
    return out


def _bind(member: dict, args: list, kwargs: dict) -> dict:
    """Arguments of a call, named by the parameters of the method it calls."""
    params = [p for p in member.get("params", []) if p["name"] not in ("self", "cls")]
    positional = [p for p in params if p["kind"] in ("positional_only", "positional_or_keyword")]
    out: dict = {}
    for i, a in enumerate(args):
        out[positional[i]["name"] if i < len(positional) else f"#{i}"] = a
    out.update(kwargs)
    return out


def _mapping(name: str, kwargs: dict, line: int) -> dict:
    """One entry of a v3 mappings dict: controls connected to elements, or modes."""
    controls, modes, options = {}, {}, {}
    for k, text in kwargs.items():
        node = _parse(text)
        value = _plain(node) if node is not None else text
        if isinstance(value, str) and isinstance(node, ast.Constant):
            controls[k] = value
        elif value is None or isinstance(value, dict):
            modes[k] = value
        else:
            options[k] = text
    return {"name": name, "kind": "modes" if modes else "component", "line": line,
            "controls": controls, "modes": modes, "options": options}


def find_script(index: dict, name: str) -> str | None:
    """The package key of a Remote Script or library by name; Remote Scripts folder first."""
    packages = index["packages"]
    for key in (name, fact_key(SCRIPTS_ROOT, name)):
        if key in packages:
            return key
    lowered = name.lower()
    matches = [k for k, p in packages.items() if p["name"].lower() == lowered]
    matches.sort(key=lambda k: (packages[k]["root"] != SCRIPTS_ROOT, k))
    return matches[0] if matches else None


def outline_package(index: dict, package_key: str) -> dict:
    return _Outliner(index, package_key).outline()
