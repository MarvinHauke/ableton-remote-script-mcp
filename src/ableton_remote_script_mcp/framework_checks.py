"""The validator's framework checks (plan 0001 step 8, Decision 43).

The script's sources are compiled by this Python 3.11 (Live's Python) and read by the same
extractor that reads Live's `.pyc` files; their facts are laid over a copy of the index, in place
of any indexed script of the same name, so the outline's reading of Specifications, component
maps, mappings and elements works on the script as it does on Ableton's own. Nothing is run.

Rules, with their severity:
- `mapping-key` (error): a key of a mappings section must be a member `<key>` or a setter
  `set_<key>` of that component's class through its MRO (or `enable`, `priority`, a `_name`).
  Modes sections: their own keys against the modes component's class, each mode's keys against
  the class of the component it names.
- `element-name` (error): a value on the right of a mapping must be an element the script's
  Elements class builds (`name.lower()` with spaces as `_`, `<matrix>_raw`, `name[i]`).
- `unknown-component` (warning): a section that is not in the component map and has no modes.
  A mode naming a component that is neither in the component map nor a modes section, or a mode
  with no `component=`, is an error (the framework raises a KeyError while it sets up).
- `specification-field` (warning): a Specification field the framework class doesn't have.
- `override-signature` (error): an overridden framework method that cannot take the arguments
  the framework's own signature allows it to be called with (`__init__` is the script's to call).
- `component-guard` (error): an element or component built in a control surface's `__init__`
  outside `with self.component_guard():`, also through a method `__init__` calls (one level);
  v3's `setup()` and the Elements class are exempt, the framework runs both inside the guard.
- `disconnect-base` (warning): a `disconnect` override that does not call the one it overrides.
- `session-ring` (warning): a v3 Specification with neither `identity_response_id_bytes` nor
  `custom_identity_response` and the framework's own session ring: the framework enables the
  ring only when the controller answers the identity request, so Live draws no session box
  (observed in 12.4.16's `ControlSurface`, tested on the Faderfox UC4; plan 0001 step 10). Only
  when a component the mappings name depends on the ring (`@depends(session_ring=…)` on an
  `__init__` along its MRO), or the mappings can't be read (plan 0003 step 1).

What a rule cannot decide is listed in `not_checked` with the reason.
"""

from __future__ import annotations

import ast
import difflib
import re
import sys
import warnings

from .extractor import read_code
from .index_store import SCRIPTS_ROOT, add_module_facts, package_facts
from .outline import _bind, _callee_text, _literal_str, _Outliner, _parse

LIVE_PYTHON = (3, 11)
MODES_SECTION_OPTIONS = {"modes_component_type", "is_private", "default_behaviour",
                         "support_momentary_mode_cycling", "enable"}
MODE_OPTIONS = {"behaviour", "selector", "index"}
LAYER_OPTIONS = {"enable", "priority"}
MODES_COMPONENT = "ableton.v3.control_surface.mode.ModesComponent"
_LIST_ACCESS = re.compile(r"^(\w+)\[(\d+)\]$")
_NOT_OVERRIDES = {"__init__", "__new__", "__init_subclass__", "__class_getitem__"}
_POSITIONAL = ("positional_only", "positional_or_keyword")


def _finding(rule, file, line, message, fix, severity="error") -> dict:
    return {"file": file, "line": line, "rule": rule, "severity": severity, "message": message, "fix": fix}


def _is_str(text: str) -> bool:
    node = _parse(text)
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _close(name: str, names) -> str:
    near = difflib.get_close_matches(name, sorted(set(names)), n=3, cutoff=0.6)
    return f" (close: {', '.join(near)})" if near else ""


def _dict_of(text: str) -> dict[str, str] | None:
    """`dict(a='x', b=...)` or `{'a': 'x'}` as {key: value text}; None for anything else."""
    node = _parse(text)
    if isinstance(node, ast.Call) and _callee_text(node.func) == "dict" and not node.args:
        if any(k.arg is None for k in node.keywords):
            return None
        return {k.arg: ast.unparse(k.value) for k in node.keywords}
    if isinstance(node, ast.Dict) and all(isinstance(k, ast.Constant) and isinstance(k.value, str)
                                          for k in node.keys):
        return {k.value: ast.unparse(v) for k, v in zip(node.keys, node.values)}
    return None


def _shape(member: dict) -> dict:
    params = list(member.get("params") or [])
    if member["kind"] in ("method", "classmethod", "property") and params and params[0]["kind"] in _POSITIONAL:
        params = params[1:]
    pos = [p for p in params if p["kind"] in _POSITIONAL]
    return {"pos": pos, "req": [p for p in pos if "default" not in p],
            "var": any(p["kind"] == "var_positional" for p in params),
            "varkw": any(p["kind"] == "var_keyword" for p in params),
            "kwonly": {p["name"]: "default" in p for p in params if p["kind"] == "keyword_only"},
            "names": {p["name"] for p in params}}


def _signature(name: str, member: dict) -> str:
    parts, star = [], False
    for p in member.get("params") or []:
        kind = p["kind"]
        if kind == "keyword_only" and not star:
            parts.append("*")
            star = True
        text = {"var_positional": f"*{p['name']}", "var_keyword": f"**{p['name']}"}.get(kind, p["name"])
        if kind == "var_positional":
            star = True
        parts.append(text + (f"={p['default']}" if "default" in p else ""))
    return f"{name}({', '.join(parts)})"


def _args(n: int) -> str:
    return f"{n} positional argument{'' if n == 1 else 's'}"


def _incompatible(override: dict, base: dict) -> str | None:
    """Why `override` cannot be called the way `base`'s signature allows, or None."""
    o, b = _shape(override), _shape(base)
    if len(o["req"]) > len(b["pos"]) and not b["var"]:
        return f"it needs {_args(len(o['req']))}, and the framework's passes at most {len(b['pos'])}"
    if len(o["pos"]) < len(b["req"]) and not o["var"]:
        return f"it takes at most {_args(len(o['pos']))}, and the framework's always passes {len(b['req'])}"
    for name, has_default in o["kwonly"].items():
        if not has_default and name not in b["names"]:
            return f"it needs the keyword argument {name}, which the framework's never passes"
    for name, has_default in b["kwonly"].items():
        if not has_default and not o["varkw"] and name not in o["names"]:
            return f"it does not take the keyword argument {name}, which the framework's always passes"
    return None


def compile_sources(sources: dict, findings: list[dict], not_checked: list[dict]) -> dict:
    """{module: code} of every parsed source. What parses but does not compile (`return` outside
    a function) is a syntax error Live hits too; such a file is left out of the checks."""
    codes = {}
    for module, src in sources.items():
        if src.tree is None:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # SyntaxWarning: Live's import would print them
                codes[module] = compile(src.tree, src.path, "exec", dont_inherit=True)
        except (SyntaxError, ValueError) as e:
            findings.append(_finding("syntax-error", src.path, getattr(e, "lineno", None),
                                     getattr(e, "msg", None) or str(e),
                                     f"fix the syntax (Live runs Python {'.'.join(map(str, LIVE_PYTHON))})"))
    return codes


def overlay_index(index: dict, script: str, sources: dict, codes: dict, not_checked: list[dict]) -> dict:
    """A copy of the index with the script's own facts in place of any indexed package of its name."""
    def own(name: str) -> bool:
        return name == script or name.startswith(script + ".")
    modules = {k: v for k, v in index["modules"].items() if not (v["root"] == SCRIPTS_ROOT and own(v["name"]))}
    classes = {k: v for k, v in index["classes"].items() if not (v["root"] == SCRIPTS_ROOT and own(v["module"]))}
    packages = {k: v for k, v in index["packages"].items() if k != script}
    read = []
    for module, code in codes.items():
        src = sources[module]
        try:
            mod = read_code(code, src.module, src.is_package, f"{script}/{src.path}")
        except Exception as e:  # noqa: BLE001  a file the extractor can't read is listed, never a crash
            not_checked.append({"file": src.path, "line": None, "rule": "framework", "what": src.path,
                                "reason": f"the extractor could not read the compiled file ({type(e).__name__}: {e})"})
            continue
        read.append(mod)
        add_module_facts(mod, SCRIPTS_ROOT, index["live_build"], modules, classes, confidence="script")
    packages.update(package_facts(read, SCRIPTS_ROOT, index["live_build"], "script folder"))
    return {**index, "modules": modules, "classes": classes, "packages": packages}


class _Checker:
    def __init__(self, index: dict, script: str, sources: dict, codes: dict):
        self.build = index["live_build"]
        self.script = script
        self.sources = sources
        self.findings: list[dict] = []
        self.not_checked: list[dict] = []
        self.overlay = overlay_index(index, script, sources, codes, self.not_checked)
        self.o = _Outliner(self.overlay, script)
        self.has_statements = any("statements" in m for c in index["classes"].values()
                                  if c["module"].startswith("ableton.v3.") for m in c["members"].values())
        self._elements: tuple | None = None
        self._inst: dict[str, set[str]] = {}

    # --- helpers --------------------------------------------------------------------------

    def file_of(self, module: str) -> str:
        src = self.sources.get(module)
        return src.path if src else module

    def own(self, key: str) -> bool:
        return key in self.o.class_keys

    def skip(self, rule: str, file: str, line, what: str, reason: str) -> None:
        self.not_checked.append({"file": file, "line": line, "rule": rule, "what": what, "reason": reason})

    def short(self, key: str) -> str:
        return self.overlay["classes"][key]["name"] if key in self.overlay["classes"] else key

    def instance_attributes(self, key: str) -> set[str]:
        """Names a class's methods set on `self`, along its MRO (`self.x = ...`)."""
        if key not in self._inst:
            names: set[str] = set()
            for k in self.o.resolver.mro(key) or []:
                for m in self.overlay["classes"][k]["members"].values():
                    for st in m.get("statements", []):
                        target = st.get("store") or st.get("target") or ""
                        if target.startswith("self.") and target[5:].isidentifier():
                            names.add(target[5:])
            self._inst[key] = names
        return self._inst[key]

    # --- v3: Specification, component map, mappings, elements ---------------------------

    def check_v3(self) -> None:
        specs = [k for k in self.o.class_keys if self.o.role(k) == "specification"]
        if not specs:
            return
        spec = self.o._used_spec(specs) or specs[0]
        info = self.o.specification(spec)
        base = info["framework_class"]
        for f in info["fields"]:
            if f["known"] or not self.own(f["set_in"]) or str(f["value"]).startswith("<"):
                continue
            self.findings.append(_finding(
                "specification-field", self.file_of(self.overlay["classes"][f["set_in"]]["module"]), f["line"],
                f"Specification field `{f['name']}` is not a field of {self.short(base)} in Live {self.build}: "
                "the framework never reads it" + _close(f["name"], self.o.lineage(base).members),
                f"look the fields up with `lookup class {base} --build {self.build}`; correct the name or remove it",
                severity="warning"))
        self.check_session_ring(spec, info)
        found = self.o.mapping_sections(spec)
        if found is None:
            return
        if found["module"] is None:
            self.skip("mapping-key", self.file_of(self.overlay["classes"][spec]["module"]), None,
                      f"create_mappings_function = {found['function']}",
                      "the mappings function is not a function of the script the validator can read")
            return
        file = self.file_of(found["module"])
        if not found["complete"]:
            self.skip("mapping-key", file, None, found["function"],
                      "the mappings function also fills sections in a way the validator does not read "
                      "(a computed key, `update`, a value that is not a dict); those are not checked")
        cmap = {e["name"]: e for e in self.o.component_map(spec)}
        cmap_complete = self.has_statements and self._component_map_complete(spec)
        sections = {name: kwargs for name, kwargs, _ in found["sections"]}
        modes_sections = {name for name, kwargs in sections.items() if name not in cmap}
        for name, kwargs, line in found["sections"]:
            where = (file, line, name)
            if name in cmap:
                self.layer(cmap[name]["defined_in"], {k: v for k, v in kwargs.items() if k != "enable"},
                           where, f"component {name}")
                continue
            modes = {k: v for k, v in kwargs.items() if k not in MODES_SECTION_OPTIONS and not _is_str(v)}
            if not modes:
                if cmap_complete:
                    self.findings.append(_finding(
                        "unknown-component", file, line,
                        f"mappings['{name}'] names no component in the component map and has no modes: the "
                        "framework makes it a modes component without modes, which fails while it sets up"
                        + _close(name, cmap),
                        "use a component-map name (see `outline`), add the component to the Specification's "
                        "component_map, or give the section modes", severity="warning"))
                else:
                    self.skip("unknown-component", file, line, f"mappings['{name}']",
                              "the component map is not fully known (see the other entries)")
                for k, v in kwargs.items():
                    if _is_str(v):
                        self.element(k, v, where)
                continue
            modes_cls = self.modes_class(kwargs.get("modes_component_type"), found["module"])
            controls = {k: v for k, v in kwargs.items() if k not in MODES_SECTION_OPTIONS and _is_str(v)}
            self.layer(modes_cls, controls, where, f"modes component {name}", _mode_buttons(kwargs))
            for mode, text in modes.items():
                self.mode(mode, text, where, cmap, cmap_complete, modes_sections, sections, found["module"])

    def check_session_ring(self, spec: str, info: dict) -> None:
        base = info["framework_class"]
        if not base or "identity_response_id_bytes" not in self.o.lineage(base).members:
            return  # a framework without identification: nothing to wait for
        own = {f["name"]: f for f in info["fields"]}
        if any(own.get(name, {}).get("value") not in (None, "None")
               for name in ("identity_response_id_bytes", "custom_identity_response",
                            "session_ring_component_type")):
            return  # identified (the framework enables the ring), or a ring class of the script's own
        if str(own.get("num_tracks", {}).get("value")) == "0" or str(own.get("num_scenes", {}).get("value")) == "0":
            return  # no ring to draw
        if self._mappings_use_session_ring(spec) is False:
            return  # no mapped component asks for the ring, so the framework never builds it
        fact = self.overlay["classes"][spec]
        self.findings.append(_finding(
            "session-ring", self.file_of(fact["module"]), fact.get("line"),
            f"{self.short(spec)} sets no identity_response_id_bytes: the framework enables the session ring "
            "only when the controller answers the identity request, so Live draws no session box (the "
            "mappings still work)",
            "set identity_response_id_bytes when the controller answers the identity request; otherwise set "
            "session_ring_component_type to a SessionRingComponent subclass that calls self.set_enabled(True) "
            "in __init__", severity="warning"))

    def _mappings_use_session_ring(self, spec: str) -> bool | None:
        """Whether a component the mappings name depends on the session ring (`@depends(session_ring=…)`
        on an `__init__` along its MRO); None when the mappings or the component map can't be read."""
        found = self.o.mapping_sections(spec)
        if not found or found["module"] is None or not found["complete"]:
            return None
        cmap = {e["name"]: e for e in self.o.component_map(spec)}
        used: set[str] = set()
        for name, kwargs, _ in found["sections"]:
            if name in cmap:
                used.add(name)
            for value in kwargs.values():
                text = str(value)  # a mode as dict(component='X', ...) or {'component': 'X', ...}
                used.update(n for n in re.findall(r"component['\"]?\s*[=:]\s*['\"](\w+)['\"]", text) if n in cmap)
        for name in used:
            cls = cmap[name].get("defined_in")
            if not cls:
                return None  # a component map entry the validator can't follow
            for key in self.o.resolver.mro(cls) or []:
                init = self.overlay["classes"].get(key, {}).get("members", {}).get("__init__", {})
                if any(re.match(r"depends\(.*\bsession_ring\s*=", d) for d in init.get("decorators", [])):
                    return True
        return False

    def _component_map_complete(self, spec: str) -> bool:
        field = self.o.lineage(spec).members.get("component_map")
        if field and self.own(field["origin"]):
            node = _parse(field.get("value") or "")
            if not (isinstance(node, ast.Dict) and all(isinstance(k, ast.Constant) for k in node.keys)):
                self.skip("unknown-component", self.file_of(self.overlay["classes"][field["origin"]]["module"]),
                          field.get("line"), "component_map", "the Specification's component_map is not a dict literal")
                return False
        for unit in self.o.units():
            for st in unit["statements"]:
                target = st.get("store") or st.get("target") or ""
                if target.startswith("self.component_map[") and not re.match(r"^self\.component_map\[('[^']*'|\"[^\"]*\")\]$", target):
                    return False
        return True

    def modes_class(self, text: str | None, module: str) -> str | None:
        found = (self.o.resolver.resolve_in_module(text, module, SCRIPTS_ROOT) if text
                 else self.o.resolver.resolve(MODES_COMPONENT))
        return found.key if found.status == "class" else None

    def mode(self, mode: str, text: str, where, cmap, cmap_complete, modes_sections, sections, module) -> None:
        node = _parse(text)
        if isinstance(node, ast.Constant) and node.value is None:
            return
        spec = _dict_of(text)
        if spec is None:
            return  # a component, a callable or another mode object: passed on as it is
        for option in MODE_OPTIONS:
            spec.pop(option, None)
        if "modes" in spec:
            parts = _parse(spec.pop("modes"))
            for part in parts.elts if isinstance(parts, (ast.List, ast.Tuple)) else []:
                d = _dict_of(ast.unparse(part))
                if d is not None:
                    self.mode_part(mode, d, where, cmap, cmap_complete, modes_sections, sections, module)
            return
        self.mode_part(mode, spec, where, cmap, cmap_complete, modes_sections, sections, module)

    def mode_part(self, mode, part, where, cmap, cmap_complete, modes_sections, sections, module) -> None:
        file, line, section = where
        text = part.pop("component", None)
        name = _literal_str(text)
        if text is None:
            self.findings.append(_finding(
                "unknown-component", file, line,
                f"mode `{mode}` of mappings['{section}'] has no `component=`: the framework raises a KeyError "
                "while it sets up", "add `component='<component-map name>'` to the mode"))
            return
        if name is None:
            self.skip("mapping-key", file, line, f"mode {mode} of mappings['{section}']",
                      f"component={text} is not a literal name")
            return
        if name in cmap:
            cls = cmap[name]["defined_in"]
        elif name in modes_sections:
            cls = self.modes_class(sections[name].get("modes_component_type"), module)
            self.layer(cls, part, where, f"modes component {name} (mode {mode})", _mode_buttons(sections[name]))
            return
        elif cmap_complete:
            self.findings.append(_finding(
                "unknown-component", file, line,
                f"mode `{mode}` of mappings['{section}'] names component '{name}', which is neither in the "
                "component map nor a mappings section: the framework raises a KeyError while it sets up"
                + _close(name, [*cmap, *modes_sections]),
                "use a component-map name (see `outline`) or the name of a modes section"))
            return
        else:
            self.skip("unknown-component", file, line, f"component='{name}'",
                      "the component map is not fully known")
            return
        self.layer(cls, part, where, f"component {name} (mode {mode})")

    def getattr_prefixes(self, cls: str) -> set[str] | None:
        """None when the class has no `__getattr__` of its own along the MRO; else the literal
        prefixes it tests with `name.startswith(...)` (empty: it can't be told what it answers)."""
        m = self.o.lineage(cls).members.get("__getattr__")
        if not m or m["origin"] not in self.overlay["classes"]:
            return None
        out = set()
        for st in m.get("statements", []):
            if st.get("call", "").endswith(".startswith") and st["args"]:
                value = _literal_str(st["args"][0])
                if value:
                    out.add(value)
        return out

    def layer(self, cls: str | None, keys: dict[str, str], where, label: str, extra=()) -> None:
        file, line, section = where
        if cls is None:
            if any(k not in LAYER_OPTIONS and not k.startswith("_") for k in keys):
                self.skip("mapping-key", file, line, f"mappings['{section}'] ({label})",
                          "the validator cannot tell which class the component is")
        else:
            lin = self.o.lineage(cls)
            members = lin.members
            if not lin.complete:
                self.skip("mapping-key", file, line, f"mappings['{section}'] ({label})",
                          f"{self.short(cls)} has a base the index does not have")
            else:
                inst = self.instance_attributes(cls) | set(extra)
                prefixes = self.getattr_prefixes(cls)
                for k in keys:
                    if k in LAYER_OPTIONS or k.startswith("_") or k in members or f"set_{k}" in members or k in inst:
                        continue
                    if prefixes is not None and (not prefixes or any(f"set_{k}".startswith(x) or k.startswith(x)
                                                                     for x in prefixes)):
                        self.skip("mapping-key", file, line, f"{k} in mappings['{section}'] ({label})",
                                  f"{self.short(cls)} answers names by pattern (`__getattr__`"
                                  + (f", names starting with {', '.join(sorted(prefixes))})" if prefixes else ")"))
                        continue
                    controls = [n.removeprefix("set_") for n in members if not n.startswith("__")]
                    controls += list(extra)
                    self.findings.append(_finding(
                        "mapping-key", file, line,
                        f"`{k}` in mappings['{section}']: {self.short(cls)} ({label}) has no control `{k}` "
                        f"and no `set_{k}` in Live {self.build}" + _close(k, controls),
                        f"look its controls up with `lookup class {cls} --build {self.build}` and use one of them"))
        for k, v in keys.items():
            if k not in LAYER_OPTIONS and _is_str(v):
                self.element(k, v, where)

    def element_names(self) -> tuple[set[str] | None, bool, str]:
        """(names, some names are computed, why there are none)."""
        if self._elements is not None:
            return self._elements
        classes = [k for k in self.o.class_keys if self.o.role(k) == "elements"]
        if not classes:
            self._elements = (None, False, "the script has no Elements class (an ElementsBase subclass) to read")
            return self._elements
        names: set[str] = set()
        originals: dict[str, str] = {}
        computed = False
        pending = []
        for unit in self.o.units():
            if unit["in_class"] not in classes:
                continue
            members = self.o.lineage(unit["in_class"]).members
            for st in unit["statements"]:
                call = st.get("call", "")
                if not call.startswith("self.add_") or call.count(".") != 1:
                    continue
                method = call[len("self."):]
                found = members.get(method)
                chain = [found["origin"], *found["overrides"]] if found else []
                origin = next((k for k in chain if self.o.is_framework(k)), None)
                if origin is None:
                    continue  # the script's own helper: the add_* calls inside it are read instead
                framework_method = self.overlay["classes"][origin]["members"][method]
                if not {"name", "base_name"} & {p["name"] for p in framework_method.get("params") or []}:
                    continue
                args = _bind(framework_method, st["args"], st["kwargs"])
                name = _literal_str(args.get("name") or args.get("base_name"))
                if method == "add_modified_control" and name is None and "name" not in args:
                    pending.append(args)
                    continue
                if name is None:
                    computed = True
                    continue
                attr = name.lower().replace(" ", "_")
                names.add(attr)
                originals[attr] = name
                if "base_name" in args or "matrix" in method or method == "add_modified_control":
                    names.add(f"{attr}_raw")
                if method == "add_sysex_display_line":
                    names.add(f"{attr}_command")
        for args in pending:  # create_name_for_modified_control: <control>_with_<modifier without _button>
            control = (args.get("control") or "").removeprefix("self.")
            modifier = (args.get("modifier") or "").removeprefix("self.")
            if control not in originals or modifier not in originals:
                computed = True
                continue
            mod = originals[modifier][:-7] if originals[modifier].lower().endswith("button") else originals[modifier]
            prep = "With" if any(c.isupper() for c in originals[control]) else "with"
            attr = f"{originals[control]}_{prep}_{mod}".lower().replace(" ", "_")
            names |= {attr, f"{attr}_raw"}
        for cls in classes:
            names |= self.instance_attributes(cls)
        self._elements = (names, computed, "")
        return self._elements

    def element(self, key: str, value_text: str, where) -> None:
        file, line, section = where
        value = _literal_str(value_text)
        names, computed, why = self.element_names()
        match = _LIST_ACCESS.match(value)
        base = match[1] if match else value
        if names is None:
            self.skip("element-name", file, line, f"{key}={value_text}", why)
        elif base not in names:
            if computed:
                self.skip("element-name", file, line, f"{key}={value_text}",
                          "the Elements class builds some names in a loop or by computation")
            else:
                self.findings.append(_finding(
                    "element-name", file, line,
                    f"`{key}='{value}'` in mappings['{section}']: the Elements class builds no element "
                    f"`{base}`" + _close(base, names),
                    "use an element's name as the Elements class builds it: name.lower(), spaces as _, "
                    "`<matrix>_raw[i]` for one element of a matrix"))

    # --- every framework -----------------------------------------------------------------

    def check_overrides(self) -> None:
        for key in self.o.class_keys:
            cls = self.overlay["classes"][key]
            lin = self.o.lineage(key)
            for name, m in cls["members"].items():
                if name in _NOT_OVERRIDES or "params" not in m or m.get("decorators"):
                    continue
                overrides = lin.members.get(name, {}).get("overrides", [])
                base_key = overrides[0] if overrides else None
                if base_key is None or not self.o.is_framework(base_key):
                    continue
                base = self.overlay["classes"][base_key]["members"][name]
                if base["kind"] != m["kind"] or base.get("decorators") or "params" not in base:
                    continue
                why = _incompatible(m, base)
                if why:
                    self.findings.append(_finding(
                        "override-signature", self.file_of(cls["module"]), m.get("line"),
                        f"{cls['name']}.{_signature(name, m)} overrides {self.short(base_key)}."
                        f"{_signature(name, base)} of Live {self.build}, but {why}",
                        f"take the framework's parameters (`def {_signature(name, base)}`), or add `*a, **k`"))

    def check_disconnect(self) -> None:
        for key in self.o.class_keys:
            cls = self.overlay["classes"][key]
            m = cls["members"].get("disconnect")
            overrides = self.o.lineage(key).members.get("disconnect", {}).get("overrides", [])
            if not m or m["kind"] != "method" or not overrides:
                continue
            if not self.overlay["classes"][overrides[0]]["members"]["disconnect"].get("statements"):
                continue  # the one it overrides does nothing (or its body is not known)
            calls = any(re.fullmatch(r"super\(.*\)\.disconnect", st.get("call", ""))
                        or (st.get("call", "").endswith(".disconnect") and st.get("args")[:1] == ["self"])
                        for st in m.get("statements", []))
            if not calls:
                self.findings.append(_finding(
                    "disconnect-base", self.file_of(cls["module"]), m.get("line"),
                    f"{cls['name']}.disconnect does not call the disconnect it overrides "
                    f"({self.short(overrides[0])}.disconnect): the framework's clean-up does not run, and its "
                    "listeners stay connected", "call `super().disconnect()` at the end of it", severity="warning"))

    def check_component_guard(self) -> None:
        for key in self.o.class_keys:
            if self.o.role(key) != "control surface":
                continue
            cls = self.overlay["classes"][key]
            node = _class_node(self.sources.get(cls["module"]), cls["qualname"])
            init = _method_node(node, "__init__")
            if init is None:
                continue
            file = self.file_of(cls["module"])
            for call in _unguarded_calls(init.body):
                built = self.builds(call, cls["module"], key)
                if built:
                    self.guard_finding(file, call.lineno, built)
                    continue
                callee = _callee_text(call.func) or ""
                if not callee.startswith("self.") or callee.count(".") != 1 or callee == "self.setup":
                    continue
                r = self.o.resolve_callee(callee, cls["module"], key, {})
                if not r or r[0] != "method" or self.o.is_framework(r[1]):
                    continue
                origin = self.overlay["classes"][r[1]]
                inner = _method_node(_class_node(self.sources.get(origin["module"]), origin["qualname"]), r[2])
                for sub in _unguarded_calls(inner.body) if inner is not None else ():
                    built = self.builds(sub, origin["module"], key)
                    if built:
                        self.guard_finding(file, call.lineno,
                                           f"{built} (in {r[2]}, line {sub.lineno}, which __init__ calls)")
                        break

    def builds(self, call: ast.Call, module: str, key: str) -> str | None:
        callee = _callee_text(call.func)
        r = self.o.resolve_callee(callee, module, key, {}) if callee else None
        if r is None:
            return None
        if r[0] == "class" and self.o.role(r[1]) in ("element", "component"):
            return f"{self.o.role(r[1])} {self.short(r[1])}"
        if r[0] in ("function", "method"):
            made = self.o.factory_of(r, key)
            if made:
                return f"element {self.short(made)} (through {callee})"
        return None

    def guard_finding(self, file: str, line: int, built: str) -> None:
        self.findings.append(_finding(
            "component-guard", file, line,
            f"{built} is built in __init__ outside `with self.component_guard():`: the control surface does "
            "not register it, and Live may log errors or the control may not respond",
            "build it inside `with self.component_guard():` in __init__"))


def _mode_buttons(kwargs: dict[str, str]) -> set[str]:
    """A modes component gets a `<mode>_button` control for each mode it adds."""
    return {f"{k}_button" for k, v in kwargs.items() if k not in MODES_SECTION_OPTIONS and not _is_str(v)}


def _class_node(src, qualname: str) -> ast.ClassDef | None:
    body = src.tree.body if src is not None and src.tree is not None else []
    node = None
    for part in qualname.split("."):
        node = next((n for n in body if isinstance(n, ast.ClassDef) and n.name == part), None)
        if node is None:
            return None
        body = node.body
    return node


def _method_node(cls: ast.ClassDef | None, name: str) -> ast.FunctionDef | None:
    if cls is None:
        return None
    return next((n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)


def _is_guard(expr: ast.expr) -> bool:
    return isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute) and expr.func.attr == "component_guard"


def _unguarded_calls(body: list[ast.stmt]):
    """Calls in a function body that run outside `with ….component_guard():` (not in nested defs)."""
    for st in body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(st, (ast.With, ast.AsyncWith)):
            if any(_is_guard(item.context_expr) for item in st.items):
                continue
            for item in st.items:
                yield from _calls(item.context_expr)
            yield from _unguarded_calls(st.body)
            continue
        children = [getattr(st, f, None) for f in ("body", "orelse", "finalbody")]
        children += [h.body for h in getattr(st, "handlers", []) or []]
        children += [c.body for c in getattr(st, "cases", []) or []]
        if any(isinstance(c, list) and c and isinstance(c[0], ast.stmt) for c in children):
            for f in ("test", "iter", "subject"):
                if getattr(st, f, None) is not None:
                    yield from _calls(getattr(st, f))
            for c in children:
                if isinstance(c, list):
                    yield from _unguarded_calls(c)
            continue
        yield from _calls(st)


def _calls(node: ast.AST):
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(n, ast.Call):
            yield n
        stack.extend(ast.iter_child_nodes(n))


def check_framework(index: dict, script: str, sources: dict, findings: list[dict], not_checked: list[dict]) -> None:
    """Run the framework rules over the parsed sources (see the module docstring)."""
    if sys.version_info[:2] != LIVE_PYTHON:
        not_checked.append({
            "file": ".", "line": None, "rule": "framework", "what": "the framework checks",
            "reason": f"they compile the script as Live's Python {'.'.join(map(str, LIVE_PYTHON))} does, and this "
                      f"command runs on Python {sys.version_info[0]}.{sys.version_info[1]}"})
        return
    codes = compile_sources(sources, findings, not_checked)
    if not codes:
        return
    checker = _Checker(index, script, sources, codes)
    checker.check_v3()
    checker.check_overrides()
    checker.check_component_guard()
    checker.check_disconnect()
    findings += checker.findings
    not_checked += checker.not_checked
