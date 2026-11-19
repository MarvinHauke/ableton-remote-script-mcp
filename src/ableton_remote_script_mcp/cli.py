"""Command line: `build-index`, `import-structure-void`, `list builds`, `lookup class`, `search`, `outline`,
`validate`, `check-names`, `diff`, `install`, `log`, `mcp` and `rig`.

The lookup commands print the same answers as the Python API (`api.py`) and the MCP tools;
`--json` prints them as they are, capped at about 4,000 tokens unless `--full`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import api
from .index_store import build_index, default_index_dir, write_index
from .install import default_user_library, install_script
from .live_install import default_install, find_installs, read_install
from .live_log import find_log, read_log
from .query import SEARCH_KINDS, validate_script
from .structure_void import LICENCE, import_pages


def _cmd_build_index(args: argparse.Namespace) -> int:
    if args.app:
        try:
            install = read_install(Path(args.app))
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    else:
        installs = find_installs()
        install = default_install(installs)
        if install is None:
            print("error: no Ableton Live app found in /Applications; pass --app <Live.app>", file=sys.stderr)
            return 2
        others = [i.live_build for i in installs if i is not install]
        if others:
            print(f"also installed: {', '.join(others)} (use --app to index one of them)")
    print(f"indexing Live {install.live_build} from {install.scripts_root}")
    index = build_index(install)
    path, spath = write_index(index, Path(args.index_dir), with_statements=not args.no_statements)
    n = index["summary"]
    print(
        f"wrote {path}: {n['packages']} packages ({n['scripts']} Remote Scripts), "
        f"{n['modules']} modules, {n['classes']} classes, {n['errors']} unreadable files"
    )
    print(f"wrote {spath}: statement summaries for outlines" if spath
          else "no statement summaries (--no-statements): `outline` is not available for this build")
    for err in index["errors"]:
        print(f"  unreadable: {err['source']}: {err['error']}")
    return 0


def _cmd_import_structure_void(args: argparse.Namespace) -> int:
    from .structure_void_framework import import_framework

    try:
        import_pages(Path(args.index_dir), args.live, args.refresh)
        import_framework(Path(args.index_dir), args.live, args.refresh)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"facts from it are `documented` ({LICENCE}: they stay on this machine)")
    return 0


def _cmd_check_structure_void(args: argparse.Namespace) -> int:
    """Exit 0: compared; 2: no framework pages imported; 3: no index."""
    from .query import structure_void_check

    answer = structure_void_check(Path(args.index_dir), args.build, args.under)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        print(_format_sv_check(answer))
    else:
        print(answer["message"])
    return {"ok": 0, "not_imported": 2, "index_missing": 3}[answer["status"]]


def _format_sv_check(a: dict) -> str:
    scope = f" under {a['under']}" if a["under"] else ""
    lines = [(f"Structure Void's framework pages ({a['covers']}, documented) against Live {a['live_build']}{scope} "
             f"(observed): {a['pages']} pages, {a['classes_agree']} classes agree, {len(a['classes_differ'])} differ, "
             f"{len(a['classes_missing'])} not found here, {len(a['modules_missing'])} modules not found here; "
             f"{len(a['modules_not_on_pages'])} modules here have no page."),
             "A difference may be Structure Void's other Live build or a gap in this index: look at both."]
    for c in a["classes_differ"]:
        lines.append(f"  {c['class']}")
        lines += [f"    {t}" for t in _sv_differences(c)]
    for c in a["classes_missing"]:
        lines.append(f"  not found here: {c['class']} ({c['reason']}; {c['source']})")
    for m in a["modules_missing"]:
        lines.append(f"  module not found here: {m['module']} ({m['source']})")
    if a["modules_not_on_pages"]:
        lines.append("  no page: " + ", ".join(a["modules_not_on_pages"]))
    return "\n".join(lines)


def _sv_differences(c: dict) -> list[str]:
    out = []
    if c["only_documented"]:
        out.append("only on the page: " + ", ".join(c["only_documented"]))
    if c["only_observed"]:
        out.append("only in the index: " + ", ".join(c["only_observed"]))
    for d in c["args_differ"]:
        out.append(f"{d['name']}: index ({', '.join(d['observed'])}), page ({', '.join(d['documented'])})")
    if "bases_differ" in c:
        out.append(f"bases: index ({', '.join(c['bases_differ']['observed'])}), "
                   f"page ({', '.join(c['bases_differ']['documented'])})")
    return out


def format_signature(params: list[dict]) -> str:
    parts, kw_marker = [], False
    for i, p in enumerate(params):
        kind = p["kind"]
        if kind == "keyword_only" and not kw_marker:
            if not any(q["kind"] == "var_positional" for q in params):
                parts.append("*")
            kw_marker = True
        text = {"var_positional": "*", "var_keyword": "**"}.get(kind, "") + p["name"]
        if "default" in p:
            text += f"={p['default']}"
        parts.append(text)
        if kind == "positional_only" and (i + 1 == len(params) or params[i + 1]["kind"] != "positional_only"):
            parts.append("/")
    return f"({', '.join(parts)})"


def _format_member(name: str, m: dict) -> str:
    deco = "".join(f"@{d} " for d in m.get("decorators", []) if d not in ("property", m["kind"]))
    if m["kind"] == "attribute":
        return f"{name} = {m['value']}"
    if m["kind"] == "property":
        return f"{deco}{name}  [property{', settable' if m.get('setter') else ''}]"
    prefix = f"[{m['kind']}] " if m["kind"] in ("classmethod", "staticmethod") else ""
    return f"{deco}{prefix}{name}{format_signature(m['params'])}"


def _mro_entry(e: dict) -> str:
    if e["status"] == "indexed":
        return e["name"]
    if e["status"] == "external":
        return e["name"] + (f" (proxy model: {e['proxy']})" if e.get("proxy") else "")
    return f"{e['name']} (unresolved in {e['in_module']}{'; ' + e['note'] if e.get('note') else ''})"


def _format_documented(d: dict, title: str) -> list[str]:
    lines = [f"{title}: {d['qualified_name']}  [{d['covers']}, documented; {d['source']}]"]
    if d.get("bases"):
        lines.append("    bases: " + ", ".join(d["bases"]))
    for n, m in d["members"].items():
        lines.append(f"    {m.get('signature') or n}  [{m['kind']}]")
    return lines


def _format_class(c: dict, own_only: bool) -> str:
    bases = ", ".join(
        b["expr"] if b["defined_in"] == b["expr"] and b["status"] != "unresolved"
        else f"{b['expr']} (unresolved)" if b["status"] == "unresolved"
        else f"{b['expr']} = {b['defined_in']}"
        for b in c["bases"]
    ) or "-"
    if not c["bases_parsed"]:
        bases = "(not read: a base expression the extractor does not model)"
    lines = [f"{c['qualified_name']}  [Live {c['live_build']}, {c['confidence']}]"]
    if c.get("proxy_model"):
        lines.append(f"  proxy model of {c.get('proxy_of', 'the Live module')} (Push 3 helper's live_model, not Live itself)")
    lines.append(f"  bases:  {bases}")
    if c["keywords"]:
        lines.append("  keywords: " + ", ".join(f"{k}={v}" for k, v in c["keywords"].items()))
    if c["decorators"]:
        lines.append("  decorators: " + ", ".join(f"@{d}" for d in c["decorators"]))
    lines.append(f"  source: {c['source']}:{c['line']}")
    if c.get("docstring"):
        lines.append("  doc:    " + c["docstring"].splitlines()[0])
    lines.append("  mro:    " + " -> ".join(_mro_entry(e) for e in c["mro"])
                 + ("" if c["mro_method"] == "c3" else "  (depth-first: the bases admit no C3 order)"))
    if not c["complete"]:
        lines.append("  incomplete: a base along the MRO is not resolved or not read; inherited members may be missing")
    by_origin: dict[str, list[str]] = {}
    for n, m in c["all_members"].items():
        text = _format_member(n, m) + (f"  (overrides {', '.join(m['overrides'])})" if m["overrides"] else "")
        by_origin.setdefault(m["origin"], []).append(text)
    own = by_origin.pop(c["qualified_name"], [])
    lines += _format_documented(c["documented"], "  also on Structure Void's page") if c.get("documented") else []
    if c.get("structure_void"):
        sv = c["structure_void"]
        verdict = "agrees" if sv["agrees"] else "differs"
        lines.append(f"  Structure Void's page ({sv['covers']}, documented) {verdict}; {sv['source']}")
        lines += [f"    {t}" for t in _sv_differences(sv)]
    if own:
        lines.append(f"  own members ({len(own)}):")
        lines.extend(f"    {t}" for t in own)
    if not own_only:
        for origin, texts in by_origin.items():
            lines.append(f"  inherited from {origin} ({len(texts)}):")
            lines.extend(f"    {t}" for t in texts)
    return "\n".join(lines)


def _cut_note(answer: dict) -> str:
    """What a capped answer left out, for the text output."""
    cut = answer.get("cut")
    if not cut:
        return ""
    fields = ", ".join(f"{f['field']} {f['kept']} of {f['total']}" for f in cut["fields"])
    return f"(cut to about {cut['max_tokens']} tokens: kept {fields}; {cut['how']})"


def _print_cut(answer: dict) -> None:
    if note := _cut_note(answer):
        print(note)


def _cmd_lookup_class(args: argparse.Namespace) -> int:
    answer = api.lookup(args.name, args.build, own=args.own, members=args.member, full=args.full,
                        index_dir=args.index_dir)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        if answer.get("resolved_from"):
            r = answer["resolved_from"]
            print(f"{r['name']} is a re-export: " + " -> ".join(r["via"][1:] + [answer["classes"][0]["qualified_name"]]))
        print("\n".join(_format_class(c, args.own) for c in answer["classes"]))
        for d in answer.get("documented", []):
            print("\n".join(_format_documented(d, f"not in the index of Live {answer['live_build']}; documented")))
        for c in answer["classes"]:
            if c.get("missing_members"):
                print(f"{c['qualified_name']} has no member " + ", ".join(c["missing_members"])
                      + f" in Live {answer['live_build']}")
        _print_cut(answer)
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


def _cmd_search(args: argparse.Namespace) -> int:
    answer = api.search(" ".join(args.query), args.build, kind=args.kind, limit=args.limit, offset=args.offset,
                        full=args.full, index_dir=args.index_dir)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        print(f"{answer['total']} matches in Live {answer['live_build']} (observed, or documented as marked); "
              f"best {len(answer['results'])}:")
        for r in answer["results"]:
            where = f"{r['source']}:{r['line']}" if r.get("line") else r["source"]
            mark = ", documented" if r["confidence"] == "documented" else ""
            print(f"  {r['kind']:<12} {r['qualified_name']}  ({r['match']}{mark}; {where})")
        if answer.get("next_offset") is not None and not answer.get("cut"):
            print(f"(more: --offset {answer['next_offset']})")
        _print_cut(answer)
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


def _cmd_diff(args: argparse.Namespace) -> int:
    from .diff import diff_builds

    if args.json:
        answer = api.diff(args.from_build, args.to_build, under=args.under, full=args.full, index_dir=args.index_dir)
        print(json.dumps(answer, indent=1))
        return {"ok": 0, "index_missing": 3}[answer["status"]]
    answer = diff_builds(args.from_build, args.to_build, Path(args.index_dir), args.under)  # the text counts it all
    if answer["status"] != "ok":
        print(answer["message"])
        return 3
    print(_format_diff(answer))
    return 0


def _format_diff(d: dict) -> str:
    scope = f" under {d['under']}" if d["under"] else ""
    lines = [f"Live {d['from']} -> {d['to']}{scope} (observed in each build)"]
    if not d["under"]:
        if not d["by_package"]:
            return lines[0] + "\n  no differences"
        lines.append("  package: modules +added -removed, classes +added -removed ~changed, members changed")
        for r in d["by_package"]:
            lines.append(f"  {r['package']}: modules +{r['modules_added']} -{r['modules_removed']}, "
                         f"classes +{r['classes_added']} -{r['classes_removed']} ~{r['classes_changed']}, "
                         f"members {r['members_changed']}")
        for what in ("added", "removed", "changed"):
            for pkg in d["packages"][what]:
                extra = (f" ({pkg['framework']['from']} -> {pkg['framework']['to']})" if what == "changed"
                         else f" ({pkg['kind']})")
                lines.append(f"  package {what}: {pkg['name']}{extra}")
        lines.append("  details: --under <package or module>")
        return "\n".join(lines)
    for what in ("added", "removed"):
        for pkg in d["packages"][what]:
            lines.append(f"  package {what}: {pkg['name']} ({pkg['kind']})")
        for k in d["modules"][what]:
            lines.append(f"  module {what}: {k}")
        for k in d["classes"][what]:
            lines.append(f"  class {what}: {k}")
    for pkg in d["packages"]["changed"]:
        lines.append(f"  package {pkg['name']}: framework {pkg['framework']['from']} -> {pkg['framework']['to']}")
    for kind, label in (("modules", "module"), ("classes", "class")):
        for c in d[kind]["changed"]:
            lines.append(f"  {label} changed: {c['name']}")
            if "bases" in c:
                lines.append(f"    bases: {', '.join(map(str, c['bases']['from']))} -> "
                             f"{', '.join(map(str, c['bases']['to']))}")
            members = c.get("members", {})
            for m in members.get("added", []):
                lines.append(f"    + {m['name']}: {m['to']}")
            for m in members.get("removed", []):
                lines.append(f"    - {m['name']}: {m['from']}")
            for m in members.get("changed", []):
                lines.append(f"    ~ {m['name']}: {m['from']} -> {m['to']}")
    if len(lines) == 1:
        lines.append("  no differences")
    return "\n".join(lines)


def _short(text: str | None, width: int = 110) -> str:
    text = "" if text is None else " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _arguments(arguments: dict) -> str:
    return ", ".join(v if k.startswith("#") else f"{k}={v}" for k, v in arguments.items())


def _condition(e: dict) -> str:
    """What an entry is made under: not made for this script, or only under a condition."""
    if e.get("runs") is False:
        return f"  NOT BUILT for this script ({e['decided_by']})"
    if e.get("runs") is None and e.get("under"):
        return "  only " + "; ".join(u for u in e["under"] if not u.startswith("for "))
    return ""


def _where(e: dict) -> str:
    where = f"{e['in'].rsplit('.', 2)[-2]}.{e['in'].rsplit('.', 1)[-1]}:{e['line']}"
    if e.get("inside"):
        where += f" {e['inside']}"
    if e.get("within"):
        where += f", in {e['within']}(…)"
    if e.get("returned_by"):
        where += f", returned by {e['returned_by']}()"
    return where


def _format_mode(value) -> str:
    if value is None:
        return "(no mappings)"
    if isinstance(value, dict):
        return ", ".join(f"{k}={_format_mode(v) if isinstance(v, dict) else v}" for k, v in value.items())
    return str(value)


def format_outline(o: dict, all_components: bool = False) -> str:
    """The outline as text; a section the answer left out (one section asked for, or cut) is
    not shown, and the cut note says so."""
    left_out = {f["field"] for f in o.get("cut", {}).get("fields", []) if f["kept"] == 0}
    o = {k: v for k, v in o.items() if k not in left_out}
    defaults = {"modules": [], "create_instance": [], "classes": [], "specification": None, "component_map": [],
                "mappings": None, "unknown_components": [], "elements": [], "components": [], "layers": []}
    has = {k for k in defaults if k in o}
    o = {**defaults, **o}
    what = "Remote Script" if o["kind"] == "script" else o["kind"]
    lines = [f"{o['script']}: {what} on {o['framework'] or 'no framework'}  [Live {o['live_build']}, {o['confidence']}]",
             f"  source:  {o['source']}"]
    if "modules" in has:
        lines.append(f"  modules: {', '.join(o['modules'])}")
    lines.append(f"  uses:    {', '.join(o['uses']) or '-'}")
    for text in o["create_instance"]:
        lines.append(f"  create_instance: {_short(text)}")
    if "classes" in has:
        lines.append(f"\nclasses ({len(o['classes'])}):")
    for c in o["classes"]:
        bases = ", ".join(b["expr"] if b["defined_in"] == b["expr"] else f"{b['expr']} = {b['defined_in']}"
                          for b in c["bases"]) or "-"
        lines.append(f"  [{c['role'] or 'other'}] {c['qualified_name']}({bases})  line {c['line']}")
        for m in c["members"]:
            if m["kind"] == "attribute":
                text = f"{m['name']} = {_short(m['value'], 90)}"
            else:
                kind = "" if m["kind"] in ("method", "function") else f"[{m['kind']}] "
                text = f"{kind}{m['name']}{format_signature(m.get('params', []))}"
            lines.append(f"      {text}" + (f"  (overrides {m['overrides']})" if m.get("overrides") else ""))
    spec = o["specification"]
    if spec and "specification" in has:
        lines.append(f"\nspecification: {spec['class']} (fields it sets; framework default after #)")
        for f in spec["fields"]:
            note = f"  # {_short(f.get('default'), 50)}" if f["known"] else "  # not a framework field"
            origin = "" if f["set_in"] == spec["class"] else f"  (set in {f['set_in']})"
            lines.append(f"  {f['name']} = {_short(f['value'], 70)}{note}{origin}")
    if "component_map" in has and (spec or o.get("section") == "component_map"):
        shown = [e for e in o["component_map"] if all_components or e["used_by_mappings"] or e["from"] == "script"]
        hidden = len(o["component_map"]) - len(shown)
        lines.append(f"\ncomponent map ({len(shown)} of {len(o['component_map'])}"
                     + (": the names the mappings use and the script's own; --all-components for every name)" if hidden else ")"))
        for e in shown:
            src = "framework default" if e["from"] == "framework" else "set by the script"
            if e.get("replaces_default"):
                src += f", replaces {e['replaces_default']}"
            lines.append(f"  {e['name']}: {_short(e['component'], 60)}  -> {e['defined_in'] or '(not resolved)'}  ({src})")
    if o["unknown_components"]:
        lines.append("  not in the component map, but named by the mappings: " + ", ".join(o["unknown_components"]))
    m = o["mappings"]
    if m:
        lines.append(f"\nmappings ({m['function']}):")
        for entry in m["mappings"]:
            head = f"  {entry['name']}" + (" [modes]" if entry["kind"] == "modes" else "")
            if entry["kind"] == "component" and not entry.get("in_component_map"):
                head += "  (not in the component map)"
            lines.append(head + ":")
            for control, element in entry["controls"].items():
                lines.append(f"      {control} <- {element}")
            for mode, value in entry["modes"].items():
                lines.append(f"      mode {mode}: {_short(_format_mode(value), 100)}")
            for k, v in entry["options"].items():
                lines.append(f"      {k} = {_short(v, 100)}")
    for section in ("elements", "components", "layers"):
        if section in has:
            lines += _outline_part(o, section)
    return "\n".join(lines)


def _outline_part(o: dict, section: str) -> list[str]:
    lines = [f"\n{section} ({len(o[section])}):"]
    for e in o[section]:
        name = e.get("name") or e.get("target") or "(unnamed)"
        target = f"  -> {e['target']}" if e.get("target") and e.get("name") else ""
        if section == "elements":
            made = e["defined_by"].rsplit(".", 1)[-1] if e.get("defined_by") else (
                f"{e['via']} -> {e['class'].rsplit('.', 1)[-1]}" if e.get("via") else e["class"].rsplit(".", 1)[-1])
            lines.append(f"  {_short(name, 40)}: {made}({_short(_arguments(e['arguments']), 70)}){target}"
                         f"  [{_where(e)}]" + _condition(e))
        elif section == "components":
            args = {k: v for k, v in e["arguments"].items() if k != "layer"}
            lines.append(f"  {_short(name, 40)}: {e['class']}({_short(_arguments(args), 60)}){target}  [{_where(e)}]"
                         + _condition(e))
        else:
            owner = e.get("target") or (f"{e['within']}(…)" if e.get("within") else "(not stored)")
            prio = f", priority={e['priority']}" if e.get("priority") else ""
            lines.append(f"  {owner}: {_short(_arguments(e['controls']) + prio, 100)}  [{_where(e)}]" + _condition(e))
    return lines


def _cmd_outline(args: argparse.Namespace) -> int:
    answer = api.outline(args.script, args.build, section=args.section, offset=args.offset, full=args.full,
                         index_dir=args.index_dir)
    if args.json:
        print(json.dumps(answer, indent=1, ensure_ascii=False))
    elif answer["status"] == "ok":
        print(format_outline(answer, args.all_components))
        _print_cut(answer)
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


def format_findings(answer: dict) -> str:
    findings = answer["findings"]
    n = answer.get("counts", {}).get("findings", len(findings))
    count = f"{n} finding{'s' * (n != 1)} in {answer['files']} file{'s' * (answer['files'] != 1)}"
    lines = [f"{answer['script']}  [Live {answer['live_build']}, {answer['confidence']}]  {count}"]
    for f in findings:
        where = f["file"] + (f":{f['line']}" if f["line"] else "")
        lines += [f"  {where}: {f['severity']} [{f['rule']}] {f['message']}", f"      fix: {f['fix']}"]
    if answer["not_checked"]:
        lines.append(f"not checked ({len(answer['not_checked'])}):")
        lines += [f"  {n['file']}:{n['line']}: [{n['rule']}] `{n['what']}`: {n['reason']}" if n["line"]
                  else f"  {n['file']}: [{n['rule']}] `{n['what']}`: {n['reason']}" for n in answer["not_checked"]]
    return "\n".join(lines)


def _cmd_validate(args: argparse.Namespace) -> int:
    answer = api.validate(args.folder, args.build, full=args.full, index_dir=args.index_dir)
    if args.json:
        print(json.dumps(answer, indent=1, ensure_ascii=False))
    elif answer["status"] == "ok":
        print(format_findings(answer))
        _print_cut(answer)
    else:
        print(answer["message"])
    if answer["status"] == "ok":
        return 1 if answer["counts"]["findings"] else 0
    return {"not_found": 2, "index_missing": 3}[answer["status"]]


def format_names(answer: dict) -> str:
    if "names" in answer:
        lines = [f"{len(answer['names'])} names in Live {answer['live_build']}: "
                 + ", ".join(f"{k} {v}" for k, v in answer["counts"].items())]
        for r in answer["names"]:
            if r["known"] == "not_a_member":
                lines.append(f"  {r['name']}: not a member ({r['message']})")
            elif r["kind"] == "class":
                lines.append(f"  {r['name']}: class, observed ({', '.join(r['classes'])})")
            elif r["kind"] == "name":
                where = f" (in {', '.join(r['in'])})" if r.get("in") else ""
                lines.append(f"  {r['name']}: {r['known']}" + (f", {r['confidence']}" if r["confidence"] else "")
                             + where)
            else:
                via = f", from {r['origin']}" if r.get("origin") else ""
                proxy = f"; the Push 3 helper's model of {r['proxy_of']}" if r.get("proxy_of") else ""
                lines.append(f"  {r['name']}: {r['kind']} of {r['class']}, {r['confidence']}{via}{proxy}")
        return "\n".join(lines)
    lines = [f"{answer['folder']} against Live {answer['live_build']}: {answer['invented_candidates']} unknown names",
             "  attributes: " + ", ".join(f"{k} {v}" for k, v in answer["attribute_counts"].items())]
    lines += [f"  {u['file']}:{u['line']}: unknown attribute {u['name']} in {u['expr']}" for u in answer["unknown"]]
    lines += [f"  {k['file']}:{k['line']}: {k['class']} takes no keyword {k['keyword']}"
              for k in answer["kwargs_unknown"]]
    lines += [f"  {b['file']}: not parsed ({b['error']})" for b in answer["broken"]]
    return "\n".join(lines)


def _cmd_check_names(args: argparse.Namespace) -> int:
    if (args.folder is None) == (args.names is None):
        print("check-names takes a script folder or --names, not both", file=sys.stderr)
        return 2
    answer = api.check_names(args.folder, args.names, args.build, full=args.full, index_dir=args.index_dir)
    if args.json:
        print(json.dumps(answer, indent=1, ensure_ascii=False))
    elif answer["status"] == "ok":
        print(format_names(answer))
        _print_cut(answer)
    else:
        print(answer["message"])
    if answer["status"] != "ok":
        return {"not_found": 2, "index_missing": 3}[answer["status"]]
    unknown = answer["unknown"] if "names" in answer else answer["invented_candidates"] + len(answer["broken"])
    return 1 if unknown else 0


def _cmd_build_stubs(args: argparse.Namespace) -> int:
    from .query import build_stubs

    answer = build_stubs(Path(args.index_dir), args.build, args.out, args.observed_only)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        out = answer["out"]
        marked = "" if not answer["documented"] else " (documented members marked `# documented`)"
        print(f"wrote {answer['files']} stub files of Live {answer['live_build']} to {out}{marked}")
        print("They are built from Ableton's code: keep them on this machine.")
        print("basedpyright / pyright: in your script project's pyrightconfig.json (or [tool.basedpyright])")
        print(f'  "stubPath": "{out}",')
        print('  "reportMissingModuleSource": false   (Live has the modules; the stubs stand in for them)')
        print("pylsp (jedi): in its settings")
        print(f'  pylsp.plugins.jedi.extra_paths = ["{out}"]')
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 2, "index_missing": 3}[answer["status"]]


def _cmd_mcp(args: argparse.Namespace) -> int:  # pragma: no cover - serves stdio until the client closes it
    from .mcp_server import make_server

    make_server(Path(args.index_dir)).run("stdio")
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    folder = Path(args.folder).resolve()  # `install .` names the folder, not ''
    if not args.no_validate:
        answer = validate_script(folder, Path(args.index_dir), args.build)
        if answer["status"] != "ok":
            print(answer["message"] + ("" if answer["status"] == "not_found" else
                                       "\n(or install unchecked with --no-validate)"))
            return {"not_found": 2, "index_missing": 3}[answer["status"]]
        if answer["findings"]:
            print(format_findings(answer))
            print("not installed: fix the findings first (or install unchecked with --no-validate)")
            return 1
    library = Path(args.user_library) if args.user_library else default_user_library()
    result = install_script(folder, library, args.replace)
    if result["status"] != "ok":
        print(result["message"])
        return 2
    if result.get("message"):
        print(result["message"])
    else:
        verb = "replaced" if result["replaced"] else "installed"
        print(f"{verb} {result['destination']} ({len(result['files'])} files)")
    print(f"next, in Live (the user's step): restart Live, then pick '{folder.name}' as a Control Surface "
          "under Settings → Link, Tempo & MIDI, with the controller's input and output ports")
    return 0


def format_log(answer: dict) -> str:
    who = f" for {answer['script']}" if answer["script"] else ""
    lines = [(f"Live {answer['live_build'] or '(build not named)'} log{who}: {answer['log']}  "
              f"(the session that starts at line {answer['session_line']})")]
    tbs = answer["tracebacks"]
    lines.append(f"tracebacks ({len(tbs)}):" if tbs else "no tracebacks")
    for t in tbs:
        lines.append(f"  line {t['line']}:")
        lines += [f"    {text}" for text in t["text"].splitlines()]
    framework_only = answer.get("framework_only", [])
    if framework_only:
        lines.append(f"framework-only tracebacks ({len(framework_only)}): no frame names a script, so they may "
                     f"come from {answer['script']} or from another script using the framework")
        seen: dict[str, list[int]] = {}
        for t in framework_only:
            seen.setdefault(t["text"], []).append(t["line"])
        for text, at in seen.items():
            more = f" and {len(at) - 1} more the same" if len(at) > 1 else ""
            lines.append(f"  line {at[0]}{more}:")
            lines += [f"    {row}" for row in text.splitlines()]
    if answer["others"]:
        lines.append(f"({answer['others']} traceback{'s' * (answer['others'] != 1)} from other scripts or Live "
                     "not shown; run without --script to see them)")
    msgs = answer["messages"]
    if msgs:
        shown = msgs[-20:]
        lines.append(f"messages ({len(msgs)}" + (f", last {len(shown)}" if len(shown) < len(msgs) else "") + "):")
        lines += [f"  line {m['line']}: ({m['script']}) {m['text']}" for m in shown]
    elif answer["script"]:
        lines.append(f"no messages from {answer['script']} (is it selected as a Control Surface, and is its "
                     "ControlSurface class named like the folder, or a v3 script's logger named by its module?)")
    return "\n".join(lines)


def _cmd_log(args: argparse.Namespace) -> int:
    path = Path(args.log) if args.log else find_log(args.build)
    if path is None:
        where = f"Live {args.build}" if args.build else "any Live build"
        message = f"no Log.txt found for {where}; pass --log <path to Log.txt>"
        print(json.dumps({"status": "not_found", "message": message}) if args.json else message)
        return 2
    answer = read_log(path, args.script)
    if args.json:
        print(json.dumps(answer, indent=1, ensure_ascii=False))
    elif answer["status"] == "ok":
        print(format_log(answer))
    else:
        print(answer["message"])
    if answer["status"] != "ok":
        return 2
    return 1 if answer["tracebacks"] or answer["framework_only"] else 0


def _cmd_list_builds(args: argparse.Namespace) -> int:
    answer = api.list_builds(full=args.full, index_dir=args.index_dir, installs=find_installs())
    if args.json:
        print(json.dumps(answer, indent=1))
        return 0 if answer["status"] == "ok" else 3
    if answer["status"] == "ok":
        for b in answer["builds"]:
            if b["usable"]:
                n = b["summary"]
                print(
                    f"Live {b['live_build']}  {n['scripts']} Remote Scripts, {n['modules']} modules, "
                    f"{n['classes']} classes, {n['errors']} unreadable  (indexed {b['created']}"
                    + ("" if b["statements"] else "; no statement summaries") + ")"
                )
            else:
                print(f"Live {b['live_build']}  not usable: {b['problem']}")
    else:
        print(answer["message"])
    for i in answer["installed_not_indexed"]:
        print(f"installed, not indexed: Live {i['live_build']}  (build-index --app \"{i['app']}\")")
    return 0 if answer["status"] == "ok" else 3


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ableton-remote-script-mcp",
        description="API index of Ableton Live's Remote Script framework (unofficial).",
    )
    p.add_argument(
        "--index-dir",
        help="where the per-build JSON index lives (default: $ABLETON_REMOTE_SCRIPT_INDEX, else "
        "$XDG_DATA_HOME/ableton-remote-script-mcp/index, else ~/.local/share/ableton-remote-script-mcp/index)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build-index", help="index an installed Live build (default: newest release)")
    b.add_argument("--app", help="path to an Ableton Live .app bundle")
    b.add_argument("--no-statements", action="store_true",
                   help="leave out the statement summaries of function bodies (then `outline` is unavailable)")
    b.set_defaults(func=_cmd_build_index)

    ls = sub.add_parser("list", help="list what the index holds")
    ls_sub = ls.add_subparsers(dest="kind", required=True)
    lb = ls_sub.add_parser("builds", help="the indexed Live builds, and installed ones with no index")
    lb.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    lb.add_argument("--full", action="store_true", help="the whole answer, not capped at about 4,000 tokens")
    lb.set_defaults(func=_cmd_list_builds)

    sv = sub.add_parser("import-structure-void",
                        help="fetch Structure Void's reference (the Live module's runtime pages and the framework "
                        "pages) as a documented source")
    sv.add_argument("--live", default="12", help="Live major version (default: 12)")
    sv.add_argument("--refresh", action="store_true", help="fetch the pages again instead of reusing the local copies")
    sv.set_defaults(func=_cmd_import_structure_void)

    cs = sub.add_parser("check-structure-void", help="compare Structure Void's framework pages with a build's index: "
                        "classes, members, arguments and bases that differ")
    cs.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    cs.add_argument("--under", help="only this package or module and what is in it, e.g. ableton.v3")
    cs.add_argument("--json", action="store_true", help="print the answer as JSON")
    cs.set_defaults(func=_cmd_check_structure_void)

    lk = sub.add_parser("lookup", help="look something up in the index")
    lk_sub = lk.add_subparsers(dest="kind", required=True)
    lc = lk_sub.add_parser("class", help="a class by short, qualified or re-exported name, with inherited members")
    lc.add_argument("name", help="the class: short (Component), qualified or re-exported name")
    lc.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    lc.add_argument("--own", action="store_true", help="only the class's own members, not inherited ones")
    lc.add_argument("--member", action="append", metavar="NAME",
                    help="only this member (repeatable): whether the class has it, own or inherited")
    lc.add_argument("--full", action="store_true", help="the whole answer, not capped at about 4,000 tokens")
    lc.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    lc.set_defaults(func=_cmd_lookup_class)

    se = sub.add_parser("search", help="classes, modules and members by name or words")
    se.add_argument("query", nargs="+", help="a name (SessionRing) or words (session ring)")
    se.add_argument("--kind", choices=SEARCH_KINDS, help="only this kind (member = any class member)")
    se.add_argument("--limit", type=int, default=20, help="how many results to show (default: %(default)s)")
    se.add_argument("--offset", type=int, default=0, help="skip this many results: the next page")
    se.add_argument("--full", action="store_true", help="the whole answer, not capped at about 4,000 tokens")
    se.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    se.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    se.set_defaults(func=_cmd_search)

    df = sub.add_parser("diff", help="what changed between two Live builds: packages, modules, classes and members "
                        "added, removed or changed")
    df.add_argument("from_build", metavar="from", help="the older build, e.g. 12.4.16")
    df.add_argument("to_build", metavar="to", help="the newer build, e.g. 12.4.25b1")
    df.add_argument("--under", help="only this package or module and what is in it, e.g. ableton.v3 or APC_mini "
                    "(without it: counts per package)")
    df.add_argument("--full", action="store_true", help="with --json: the whole answer, not capped at about "
                    "4,000 tokens")
    df.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    df.set_defaults(func=_cmd_diff)

    ol = sub.add_parser("outline", help="a Remote Script's classes, Specification, component map, mappings and elements")
    ol.add_argument("script", help="the Remote Script's folder name, e.g. APC_mini_mk2")
    ol.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    ol.add_argument("--all-components", action="store_true",
                    help="list every name in the v3 component map, not only those the mappings use")
    ol.add_argument("--section", choices=api.OUTLINE_SECTIONS, help="only this section of the outline")
    ol.add_argument("--offset", type=int, default=0, help="with --section: skip this many items of a long section")
    ol.add_argument("--full", action="store_true", help="the whole answer, not capped at about 4,000 tokens")
    ol.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    ol.set_defaults(func=_cmd_outline)

    va = sub.add_parser("validate", help="check a Remote Script folder against a Live build's API index")
    va.add_argument("folder", help="the Remote Script's folder (its __init__.py defines create_instance)")
    va.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    va.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    va.add_argument("--full", action="store_true", help="the whole answer, not capped at about 4,000 tokens")
    va.set_defaults(func=_cmd_validate)

    cn = sub.add_parser("check-names", help="where each API name a script folder uses, or each name given, is known "
                        "in a Live build: observed, documented, or unknown")
    cn.add_argument("folder", nargs="?", help="a Remote Script folder (or give --names)")
    cn.add_argument("--names", nargs="+", metavar="NAME",
                    help="names to check instead of a folder: Class, Class.member or a bare name")
    cn.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    cn.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    cn.add_argument("--full", action="store_true", help="the whole answer, not capped at about 4,000 tokens")
    cn.set_defaults(func=_cmd_check_names)

    bs = sub.add_parser("build-stubs", help="write type stubs (.pyi) of a Live build for your editor's Python "
                        "language server (local only)")
    bs.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    bs.add_argument("--out", help="the folder to write (default: <index dir>/stubs/<build>); a folder of earlier "
                    "stubs is replaced")
    bs.add_argument("--observed-only", action="store_true",
                    help="leave out the documented members (listener methods, Structure Void's Live members)")
    bs.add_argument("--json", action="store_true", help="print the answer as JSON")
    bs.set_defaults(func=_cmd_build_stubs)

    mc = sub.add_parser("mcp", help="run the MCP server over stdio (the lookup commands as tools)")
    mc.set_defaults(func=_cmd_mcp)

    ins = sub.add_parser("install", help="validate a Remote Script folder, then copy it into the User Library")
    ins.add_argument("folder", help="the Remote Script's folder")
    ins.add_argument("--build", help="Live build to validate against (default: newest indexed)")
    ins.add_argument("--user-library",
                     help="the User Library folder (default: $ABLETON_USER_LIBRARY, else ~/Music/Ableton/User Library)")
    ins.add_argument("--replace", action="store_true", help="overwrite an installed copy of the same script")
    ins.add_argument("--no-validate", action="store_true", help="copy without validating first")
    ins.set_defaults(func=_cmd_install)

    lg = sub.add_parser("log", help="tracebacks and messages of Remote Scripts in Live's Log.txt (last session)")
    lg.add_argument("--script", help="only this script's tracebacks and messages (its folder name), plus the "
                    "framework-only tracebacks that may be its own; exit 1 for either")
    lg.add_argument("--build", help="read the log of this Live build (default: the most recently written log)")
    lg.add_argument("--log", help="path to a Log.txt (default: found under $ABLETON_PREFERENCES, else "
                    "~/Library/Preferences/Ableton)")
    lg.add_argument("--json", action="store_true", help="print the answer as JSON")
    lg.set_defaults(func=_cmd_log)

    rg = sub.add_parser("rig", help="the test rig: play a controller to a Remote Script over a virtual MIDI port "
                        "(needs the `rig` extra)")
    rg_sub = rg.add_subparsers(dest="rig_command", required=True)
    rp = rg_sub.add_parser("ports", help="the MIDI ports the system shows now")
    rp.add_argument("--json", action="store_true", help="print the answer as JSON")
    rp.set_defaults(func=_cmd_rig_ports)
    pr = rg_sub.add_parser("probe", help="open the rig's virtual port, wait until Live sends on it, send one "
                           "message and show the replies")
    pr.add_argument("--name", default=None, help="the virtual port's name (default: ARS Test Rig)")
    pr.add_argument("--wait", type=float, default=120.0, help="seconds to wait for Live to connect (default: 120)")
    pr.add_argument("--send", default="cc 13 40 100",
                    help="the message to send: `cc|note|noteoff <channel 1-16> <number> <value>` or hex bytes "
                    "(default: cc 13 40 100, the Faderfox UC4's fader 1 in SE17)")
    pr.add_argument("--json", action="store_true", help="print the answer as JSON")
    pr.set_defaults(func=_cmd_rig_probe)
    el = rg_sub.add_parser("elements", help="the controller model of a script folder: each element's name and MIDI "
                           "message, as check files name them")
    el.add_argument("folder", help="the Remote Script's folder")
    el.add_argument("--build", help="Live build whose index reads the script (default: newest indexed)")
    el.add_argument("--json", action="store_true", help="print the answer as JSON")
    el.set_defaults(func=_cmd_rig_elements)
    sv = rg_sub.add_parser("serve", help="hold the rig's virtual port open (across Live restarts) for `rig run`")
    sv.add_argument("--name", default=None, help="the virtual port's name (default: ARS Test Rig)")
    sv.add_argument("--port", type=int, default=None, help="the local TCP port clients use (default: 9878)")
    sv.add_argument("--profile", help="a device.yaml whose identity reply the rig sends when Live asks (default: "
                    "no reply)")
    sv.set_defaults(func=_cmd_rig_serve)
    rr = rg_sub.add_parser("run", help="run a check file against a script in Live, over `rig serve` or a port of "
                           "its own; writes checks.result.json beside it")
    rr.add_argument("checks", help="the check file (checks.yaml)")
    rr.add_argument("--build", help="Live build whose index reads the script (default: the check file's, else "
                    "newest indexed)")
    rr.add_argument("--name", default=None, help="without `rig serve`: the virtual port's name (default: ARS Test Rig)")
    rr.add_argument("--port", type=int, default=None, help="the local TCP port of `rig serve` (default: 9878)")
    rr.add_argument("--wait", type=float, default=120.0,
                    help="without `rig serve`: seconds to wait for Live to connect (default: 120)")
    rr.add_argument("--log", help="the Log.txt to read for `log: clean` (default: the Live build's, else the "
                    "most recently written)")
    rr.add_argument("--no-abletonmcp", action="store_true",
                    help="don't use AbletonMCP even when it runs (state, events and do steps are not checked)")
    rr.add_argument("--json", action="store_true", help="print the result as JSON")
    rr.set_defaults(func=_cmd_rig_run)
    pn = rg_sub.add_parser("panel", help="a web page of the controller on 127.0.0.1, played through `rig serve` "
                           "(a parallel view: the driver is in charge)")
    pn.add_argument("folder", help="the Remote Script's folder (a device.yaml beside it gives the layout)")
    pn.add_argument("--build", help="Live build whose index reads the script (default: newest indexed)")
    pn.add_argument("--profile", help="the device.yaml to use (default: the one in the script folder, if any)")
    pn.add_argument("--port", type=int, default=None, help="the local TCP port of `rig serve` (default: 9878)")
    pn.add_argument("--http", type=int, default=None, help="the panel's local port (default: 9879)")
    pn.add_argument("--open", action="store_true", help="open the page in the browser")
    pn.set_defaults(func=_cmd_rig_panel)
    rl = rg_sub.add_parser("restart-live", help="quit Live without saving and start it again (only when Live shows "
                           "just the unsaved test Set; needs the terminal's Accessibility permission)")
    rl.add_argument("--app", default="/Applications/Ableton Live 12 Suite.app", help="the Live app (default: %(default)s)")
    rl.add_argument("--build", default="12.4.16", help="its build, for Log.txt (default: %(default)s)")
    rl.add_argument("--title", default="Untitled", help="the test Set's window title (default: %(default)s)")
    rl.add_argument("--wait-for", help="also wait until a script logs this text")
    rl.set_defaults(func=_cmd_rig_restart_live)
    am = rg_sub.add_parser("abletonmcp", help="what the rig reads through AbletonMCP now: its version, the song and "
                           "each track (for checking reads against what the user sees in Live)")
    am.add_argument("--json", action="store_true", help="print the answer as JSON")
    am.set_defaults(func=_cmd_rig_abletonmcp)
    return p


def _cmd_rig_ports(args: argparse.Namespace) -> int:
    from .rig.ports import RigUnavailable, list_ports

    try:
        ports = list_ports()
    except RigUnavailable as e:
        print(e, file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(ports, indent=2))
    else:
        for kind in ("inputs", "outputs"):
            print(f"{kind}: " + (", ".join(ports[kind]) or "none"))
    return 0


def _cmd_rig_probe(args: argparse.Namespace) -> int:
    """Exit 0: Live connected and replied on the sent control; 1: connected, no such reply;
    2: Live sent nothing on the port; 3: the rig extra is missing; 4: a bad --send."""
    from .rig.ports import DEFAULT_NAME, RigUnavailable, parse_message
    from .rig.probe import run_probe

    try:
        message = parse_message(args.send)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 4
    log = (lambda *_: None) if args.json else (lambda text: print(text, flush=True))
    try:
        result = run_probe(args.name or DEFAULT_NAME, args.wait, message, log=log)
    except RigUnavailable as e:
        print(e, file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(result, indent=2))
    elif not result["connected"]:
        print(f"Live sent nothing on `{result['port']}` within {args.wait:.0f} s: is it picked as a Control "
              "Surface's Input and Output, with a script that sends at start?")
    else:
        print("first from Live: " + "; ".join(result["first"][:8]) + (" …" if len(result["first"]) > 8 else ""))
        print("replies: " + ("; ".join(result["replies"]) or "none"))
    if not result["connected"]:
        return 2
    return 0 if result["echo"] else 1


def _cmd_rig_elements(args: argparse.Namespace) -> int:
    from .rig.controller import controller_for_folder

    ctl, why = controller_for_folder(Path(args.folder), Path(args.index_dir), args.build)
    if ctl is None:
        print(why, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(ctl.as_dict(), indent=1))
        return 0
    print(f"{ctl.script}: {len(ctl.elements)} elements ({ctl.folder})")
    single = [e for e in ctl.elements.values() if "[" not in e.name]
    for name, items in ctl.matrices.items():
        first, last = ctl.elements[items[0]], ctl.elements[items[-1]]
        print(f"  {name}[0..{len(items) - 1}]  {first.kind}  {first.describe()} .. {last.describe()}"
              + _element_flags(first))
    for e in single:
        print(f"  {e.name}  {e.kind}  {e.describe()}" + _element_flags(e))
    for u in ctl.unresolved:
        print(f"  not read: line {u['line']} in {u['in']}: {u['reason']}")
    return 0


def _element_flags(e) -> str:
    flags = (["relative " + e.map_mode] if e.relative else []) + (["sends values back"] if e.feedback else [])
    return f"  ({', '.join(flags)})" if flags else ""


def _cmd_rig_abletonmcp(args: argparse.Namespace) -> int:
    """Exit 0: read; 2: no AbletonMCP the rig can use."""
    from .rig.abletonmcp import TESTED, connect

    mcp, why = connect()
    if mcp is None:
        print(why, file=sys.stderr)
        return 2
    try:
        song = mcp.read("get_session_info")
        tracks = [mcp.read("get_track_info", track_index=i) for i in range(song["track_count"])]
    finally:
        mcp.close()
    if args.json:
        print(json.dumps({"script_info": mcp.info, "song": song, "tracks": tracks, "tested": TESTED}, indent=1))
        return 0
    print(f"AbletonMCP {mcp.info['script_version']} (protocol {mcp.info['protocol_version']})")
    print(f"song: tempo {song['tempo']:g}, {'playing' if song['is_playing'] else 'stopped'}, "
          f"{song['track_count']} tracks, {song['return_track_count']} returns, "
          f"main volume {song['master_track']['volume']:.3f}")
    for t in tracks:
        flags = [f for f in ("mute", "solo", "arm") if t[f]]
        clips = [str(c["index"] + 1) for c in t["clip_slots"] if c["has_clip"]]
        playing = [str(c["index"] + 1) for c in t["clip_slots"] if c["has_clip"] and c["clip"]["is_playing"]]
        print(f"  track {t['index'] + 1} {t['name']!r}: volume {t['volume']:.3f}, pan {t['panning']:+.2f}"
              + (f", {' '.join(flags)}" if flags else "")
              + f"; devices: {', '.join(d['name'] for d in t['devices']) or 'none'}"
              + f"; clips in scenes {','.join(clips) or '-'}" + (f" (playing: {','.join(playing)})" if playing else ""))
    print("tested reads: " + "; ".join(f"{k} ({v})" for k, v in TESTED.items()))
    return 0


def _cmd_rig_restart_live(args: argparse.Namespace) -> int:  # pragma: no cover - drives Live
    """Exit 0: restarted; 2: not done or stopped (the reason is printed)."""
    from .live_log import find_log
    from .rig.live_app import RestartError, restart_live

    log = find_log(args.build)
    if log is None:
        print(f"no Log.txt for Live {args.build}", file=sys.stderr)
        return 2
    try:
        restart_live(Path(args.app), log, args.title, args.wait_for, say=lambda t: print(t, flush=True))
    except RestartError as e:
        print(f"restart-live: {e}", file=sys.stderr)
        return 2
    return 0


def _cmd_rig_serve(args: argparse.Namespace) -> int:  # pragma: no cover - needs MIDI
    from .rig.ports import DEFAULT_NAME, RigUnavailable
    from .rig.profile import ProfileError, load_profile
    from .rig.serve import DEFAULT_PORT, serve

    try:
        profile = load_profile(Path(args.profile)) if args.profile else None
    except (ProfileError, ImportError) as e:
        print(e, file=sys.stderr)
        return 4
    try:
        serve(args.name or DEFAULT_NAME, ("127.0.0.1", args.port or DEFAULT_PORT), log=lambda t: print(t, flush=True),
              profile=profile)
    except RigUnavailable as e:
        print(e, file=sys.stderr)
        return 3
    except OSError as e:
        print(f"rig serve: {e} (is another `rig serve` running?)", file=sys.stderr)
        return 2
    return 0


def _cmd_rig_panel(args: argparse.Namespace) -> int:  # pragma: no cover - serves until Ctrl-C
    """Exit 2: no `rig serve` (it owns the port, Decision 9); 4: the script or its profile can't be read."""
    from .rig.controller import controller_for_folder
    from .rig.panel import DEFAULT_PORT as PANEL_PORT
    from .rig.panel import PanelServer
    from .rig.profile import (
        ProfileError,
        check_profile_names,
        load_profile,
        profile_beside,
    )
    from .rig.serve import DEFAULT_PORT, connect

    ctl, why = controller_for_folder(Path(args.folder), Path(args.index_dir), args.build)
    if ctl is None:
        print(why, file=sys.stderr)
        return 4
    try:
        profile = load_profile(Path(args.profile)) if args.profile else profile_beside(Path(args.folder))
    except (ProfileError, ImportError) as e:
        print(e, file=sys.stderr)
        return 4
    problems = check_profile_names(profile, ctl) if profile else []
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 4
    port = connect(port=args.port or DEFAULT_PORT)
    if port is None:
        print("no `rig serve` is running: start it first (`ableton-remote-script-mcp rig serve`); the panel plays "
              "through it", file=sys.stderr)
        return 2
    try:
        server = PanelServer(ctl, port, profile, ("127.0.0.1", args.http or PANEL_PORT),
                             reconnect=lambda: connect(port=args.port or DEFAULT_PORT))
    except OSError as e:
        port.close()
        print(f"rig panel: {e} (is another `rig panel` running?)", file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"rig panel: {ctl.script} ({len(ctl.elements)} elements) on {url}, playing through `{port.name}`. "
          "Stop with Ctrl-C.", flush=True)
    if args.open:
        import webbrowser

        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        port.close()
    return 0


def _cmd_rig_run(args: argparse.Namespace) -> int:
    """Exit 0: no step failed; 1: a step failed; 2: Live sent nothing on the port; 3: the rig extra
    is missing; 4: the check file, the script or its element names can't be read."""
    from .live_log import find_log
    from .rig.checks import (
        CheckFileError,
        LogWatch,
        check_names,
        load_check_file,
        run_checks,
    )
    from .rig.controller import controller_for_folder
    from .rig.ports import DEFAULT_NAME, RigUnavailable, wait_for
    from .rig.report import format_report, write_result
    from .rig.serve import DEFAULT_PORT, connect

    say = (lambda *_: None) if args.json else (lambda text: print(text, flush=True))
    try:
        checks = load_check_file(Path(args.checks))
    except (CheckFileError, ImportError) as e:
        print(e, file=sys.stderr)
        return 3 if isinstance(e, ImportError) else 4
    ctl, why = controller_for_folder(checks.script_folder, Path(args.index_dir), args.build or checks.build)
    if ctl is None:
        print(why, file=sys.stderr)
        return 4
    from .rig.profile import ProfileError, check_profile_names, profile_beside

    try:
        profile = profile_beside(checks.path)
    except ProfileError as e:
        print(e, file=sys.stderr)
        return 4
    problems = check_names(checks, ctl) + (check_profile_names(profile, ctl) if profile else [])
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 4
    log_path = Path(args.log) if args.log else find_log(args.build or checks.build)
    if any(s.log_clean for s in checks.steps) and log_path is None:
        print("the check file asks for `log: clean`, and no Log.txt was found; pass --log", file=sys.stderr)
        return 4
    from .rig import abletonmcp

    mcp, mcp_note = (None, "--no-abletonmcp") if args.no_abletonmcp else abletonmcp.connect()
    say(f"AbletonMCP {mcp.info['script_version']}: Live's state is checked too" if mcp else
        f"without AbletonMCP ({mcp_note}): state, events and do steps are not checked")
    port = connect(port=args.port or DEFAULT_PORT)
    own = port is None
    try:
        if own:
            from .rig.ports import VirtualPort

            port = VirtualPort(args.name or DEFAULT_NAME)
            if profile is not None and profile.reply is not None:
                from .rig.profile import IdentityResponder, RespondingPort

                port = RespondingPort(port, IdentityResponder(port, profile, log=say))
            say(f"no `rig serve` running: opened `{port.name}` for this run; waiting up to {args.wait:.0f} s for "
                "Live to send on it (pick it as the Control Surface's Input and Output)")
            if not wait_for(port, args.wait, until_any=True):
                print(f"Live sent nothing on `{port.name}` within {args.wait:.0f} s", file=sys.stderr)
                return 2
        else:
            say(f"using `rig serve`'s port `{port.name}` ({port.hello['received']} message(s) from Live so far)")
            if profile is not None and profile.reply is not None and not port.hello.get("identity_reply"):
                say("note: device.yaml has an identity reply, but `rig serve` was started without --profile, so "
                    "Live's identity request goes unanswered")
        say(f"sending MIDI only to `{port.name}`; stop with Ctrl-C")
        result = run_checks(checks, ctl, port, LogWatch(log_path, ctl.script), say=say, mcp=mcp, mcp_note=mcp_note)
    except RigUnavailable as e:
        print(e, file=sys.stderr)
        return 3
    except CheckFileError as e:
        print(e, file=sys.stderr)
        return 4
    finally:
        if port is not None:
            port.close()
        if mcp is not None:
            mcp.close()
    path = write_result(result, checks.path)
    if args.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        print(format_report(result))
        print(f"full result: {path}")
    return 1 if result["counts"]["failed"] else 0


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.index_dir is None:  # resolved here, not in the parser, so `--help` shows no home path
        args.index_dir = str(default_index_dir())
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
