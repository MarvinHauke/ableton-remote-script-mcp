"""Command line: `build-index`, `list builds`, `lookup class` and `search`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .index_store import build_index, default_index_dir, write_index
from .live_install import default_install, find_installs, read_install
from .query import SEARCH_KINDS, get_class, list_builds, search


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
    path = write_index(index, Path(args.index_dir))
    n = index["summary"]
    print(
        f"wrote {path}: {n['packages']} packages ({n['scripts']} Remote Scripts), "
        f"{n['modules']} modules, {n['classes']} classes, {n['errors']} unreadable files"
    )
    for err in index["errors"]:
        print(f"  unreadable: {err['source']}: {err['error']}")
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
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


def _cmd_search(args: argparse.Namespace) -> int:
    answer = search(" ".join(args.query), Path(args.index_dir), args.build, args.kind, args.limit)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        print(f"{answer['total']} matches in Live {answer['live_build']} (observed); best {len(answer['results'])}:")
        for r in answer["results"]:
            where = f"{r['source']}:{r['line']}" if r.get("line") else r["source"]
            print(f"  {r['kind']:<12} {r['qualified_name']}  ({r['match']}; {where})")
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


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
                    f"{n['classes']} classes, {n['errors']} unreadable  (indexed {b['created']})"
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
        default=str(default_index_dir()),
        help="where the per-build JSON index lives (default: %(default)s; env ABLETON_REMOTE_SCRIPT_INDEX)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build-index", help="index an installed Live build (default: newest release)")
    b.add_argument("--app", help="path to an Ableton Live .app bundle")
    b.set_defaults(func=_cmd_build_index)

    ls = sub.add_parser("list", help="list what the index holds")
    ls_sub = ls.add_subparsers(dest="kind", required=True)
    lb = ls_sub.add_parser("builds", help="the indexed Live builds, and installed ones with no index")
    lb.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    lb.set_defaults(func=_cmd_list_builds)

    lk = sub.add_parser("lookup", help="look something up in the index")
    lk_sub = lk.add_subparsers(dest="kind", required=True)
    lc = lk_sub.add_parser("class", help="a class by short, qualified or re-exported name, with inherited members")
    lc.add_argument("name")
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
