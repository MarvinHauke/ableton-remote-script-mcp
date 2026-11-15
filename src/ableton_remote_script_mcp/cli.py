"""Command line: `build-index`, `list builds` and `lookup class`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .index_store import build_index, default_index_dir, write_index
from .live_install import default_install, find_installs, read_install
from .query import list_builds, lookup_class


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


def _format_class(c: dict) -> str:
    bases = ", ".join(b["resolved"] or f"{b['expr']} (unresolved)" for b in c["bases"]) or "-"
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
    if c["members"]:
        lines.append(f"  own members ({len(c['members'])}):")
        lines.extend(f"    {_format_member(n, m)}" for n, m in c["members"].items())
    return "\n".join(lines)


def _cmd_lookup_class(args: argparse.Namespace) -> int:
    answer = lookup_class(args.name, Path(args.index_dir), args.build)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        print("\n".join(_format_class(c) for c in answer["classes"]))
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
    lc = lk_sub.add_parser("class", help="a class by short or qualified name")
    lc.add_argument("name")
    lc.add_argument("--build", help="Live build, e.g. 12.4.16 (default: newest indexed)")
    lc.add_argument("--json", action="store_true", help="print the query core's answer as JSON")
    lc.set_defaults(func=_cmd_lookup_class)
    return p


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
