"""Command line: `build-index`, `import-structure-void`, `list builds`, `lookup class`, `search`, `outline`, `validate`, `install` and
`log`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .index_store import build_index, default_index_dir, write_index
from .install import default_user_library, install_script
from .live_install import default_install, find_installs, read_install
from .live_log import find_log, read_log
from .query import (
    SEARCH_KINDS,
    get_class,
    list_builds,
    outline_script,
    search,
    validate_script,
)
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
    try:
        import_pages(Path(args.index_dir), args.live, args.refresh)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"facts from it are `documented` ({LICENCE}: they stay on this machine)")
    return 0


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
    if own:
        lines.append(f"  own members ({len(own)}):")
        lines.extend(f"    {t}" for t in own)
    if not own_only:
        for origin, texts in by_origin.items():
            lines.append(f"  inherited from {origin} ({len(texts)}):")
            lines.extend(f"    {t}" for t in texts)
    return "\n".join(lines)


def _cmd_lookup_class(args: argparse.Namespace) -> int:
    answer = get_class(args.name, Path(args.index_dir), args.build)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        if answer.get("resolved_from"):
            r = answer["resolved_from"]
            print(f"{r['name']} is a re-export: " + " -> ".join(r["via"][1:] + [answer["classes"][0]["qualified_name"]]))
        print("\n".join(_format_class(c, args.own) for c in answer["classes"]))
        for d in answer.get("documented", []):
            print("\n".join(_format_documented(d, f"not in the index of Live {answer['live_build']}; documented")))
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


def _cmd_search(args: argparse.Namespace) -> int:
    answer = search(" ".join(args.query), Path(args.index_dir), args.build, args.kind, args.limit)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        print(f"{answer['total']} matches in Live {answer['live_build']} (observed, or documented as marked); "
              f"best {len(answer['results'])}:")
        for r in answer["results"]:
            where = f"{r['source']}:{r['line']}" if r.get("line") else r["source"]
            mark = ", documented" if r["confidence"] == "documented" else ""
            print(f"  {r['kind']:<12} {r['qualified_name']}  ({r['match']}{mark}; {where})")
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


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
    what = "Remote Script" if o["kind"] == "script" else o["kind"]
    lines = [f"{o['script']}: {what} on {o['framework'] or 'no framework'}  [Live {o['live_build']}, {o['confidence']}]",
             f"  source:  {o['source']}",
             f"  modules: {', '.join(o['modules'])}",
             f"  uses:    {', '.join(o['uses']) or '-'}"]
    for text in o["create_instance"]:
        lines.append(f"  create_instance: {_short(text)}")
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
    if spec:
        lines.append(f"\nspecification: {spec['class']} (fields it sets; framework default after #)")
        for f in spec["fields"]:
            note = f"  # {_short(f.get('default'), 50)}" if f["known"] else "  # not a framework field"
            origin = "" if f["set_in"] == spec["class"] else f"  (set in {f['set_in']})"
            lines.append(f"  {f['name']} = {_short(f['value'], 70)}{note}{origin}")
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
    lines.append(f"\nelements ({len(o['elements'])}):")
    for e in o["elements"]:
        made = e["defined_by"].rsplit(".", 1)[-1] if e.get("defined_by") else (
            f"{e['via']} -> {e['class'].rsplit('.', 1)[-1]}" if e.get("via") else e["class"].rsplit(".", 1)[-1])
        name = e.get("name") or e.get("target") or "(unnamed)"
        target = f"  -> {e['target']}" if e.get("target") and e.get("name") else ""
        lines.append(f"  {_short(name, 40)}: {made}({_short(_arguments(e['arguments']), 70)}){target}  [{_where(e)}]"
                     + _condition(e))
    lines.append(f"\ncomponents ({len(o['components'])}):")
    for e in o["components"]:
        name = e.get("name") or e.get("target") or "(unnamed)"
        args = {k: v for k, v in e["arguments"].items() if k != "layer"}
        target = f"  -> {e['target']}" if e.get("target") and e.get("name") else ""
        lines.append(f"  {_short(name, 40)}: {e['class']}({_short(_arguments(args), 60)}){target}  [{_where(e)}]"
                     + _condition(e))
    lines.append(f"\nlayers ({len(o['layers'])}):")
    for e in o["layers"]:
        owner = e.get("target") or (f"{e['within']}(…)" if e.get("within") else "(not stored)")
        prio = f", priority={e['priority']}" if e.get("priority") else ""
        lines.append(f"  {owner}: {_short(_arguments(e['controls']) + prio, 100)}  [{_where(e)}]" + _condition(e))
    return "\n".join(lines)


def _cmd_outline(args: argparse.Namespace) -> int:
    answer = outline_script(args.script, Path(args.index_dir), args.build)
    if args.json:
        print(json.dumps(answer, indent=1, ensure_ascii=False))
    elif answer["status"] == "ok":
        print(format_outline(answer, args.all_components))
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


def format_findings(answer: dict) -> str:
    findings = answer["findings"]
    count = f"{len(findings)} finding{'s' * (len(findings) != 1)} in {answer['files']} file{'s' * (answer['files'] != 1)}"
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
    answer = validate_script(Path(args.folder), Path(args.index_dir), args.build)
    if args.json:
        print(json.dumps(answer, indent=1, ensure_ascii=False))
    elif answer["status"] == "ok":
        print(format_findings(answer))
    else:
        print(answer["message"])
    if answer["status"] == "ok":
        return 1 if answer["findings"] else 0
    return {"not_found": 2, "index_missing": 3}[answer["status"]]


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
                     "ControlSurface class named like the folder?)")
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
    answer = list_builds(Path(args.index_dir), find_installs())
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
    lb.set_defaults(func=_cmd_list_builds)

    sv = sub.add_parser("import-structure-void",
                        help="fetch Structure Void's runtime pages of the Live module as a documented source")
    sv.add_argument("--live", default="12", help="Live major version (default: 12)")
    sv.add_argument("--refresh", action="store_true", help="fetch the pages again instead of reusing the local copies")
    sv.set_defaults(func=_cmd_import_structure_void)

    lk = sub.add_parser("lookup", help="look something up in the index")
    lk_sub = lk.add_subparsers(dest="kind", required=True)
    lc = lk_sub.add_parser("class", help="a class by short, qualified or re-exported name, with inherited members")
    lc.add_argument("name", help="the class: short (Component), qualified or re-exported name")
    lc.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    lc.add_argument("--own", action="store_true", help="only the class's own members, not inherited ones")
    lc.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    lc.set_defaults(func=_cmd_lookup_class)

    se = sub.add_parser("search", help="classes, modules and members by name or words")
    se.add_argument("query", nargs="+", help="a name (SessionRing) or words (session ring)")
    se.add_argument("--kind", choices=SEARCH_KINDS, help="only this kind (member = any class member)")
    se.add_argument("--limit", type=int, default=20, help="how many results to show (default: %(default)s)")
    se.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    se.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    se.set_defaults(func=_cmd_search)

    ol = sub.add_parser("outline", help="a Remote Script's classes, Specification, component map, mappings and elements")
    ol.add_argument("script", help="the Remote Script's folder name, e.g. APC_mini_mk2")
    ol.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    ol.add_argument("--all-components", action="store_true",
                    help="list every name in the v3 component map, not only those the mappings use")
    ol.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    ol.set_defaults(func=_cmd_outline)

    va = sub.add_parser("validate", help="check a Remote Script folder against a Live build's API index")
    va.add_argument("folder", help="the Remote Script's folder (its __init__.py defines create_instance)")
    va.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    va.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    va.set_defaults(func=_cmd_validate)

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
    return p


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.index_dir is None:  # resolved here, not in the parser, so `--help` shows no home path
        args.index_dir = str(default_index_dir())
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
