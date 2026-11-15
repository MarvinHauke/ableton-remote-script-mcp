"""Command line: `build-index` and `lookup class`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .index_store import build_index, default_index_dir, write_index
from .live_install import default_install, find_installs, read_install
from .query import lookup_class


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
    print(
        f"wrote {path}: {len(index['modules'])} modules, {len(index['classes'])} classes, "
        f"{len(index['errors'])} unreadable files"
    )
    for err in index["errors"]:
        print(f"  unreadable: {err['source']}: {err['error']}")
    return 0


def _format_class(c: dict) -> str:
    bases = ", ".join(b["resolved"] or f"{b['expr']} (unresolved)" for b in c["bases"]) or "-"
    return (
        f"{c['qualified_name']}  [Live {c['live_build']}, {c['confidence']}]\n"
        f"  bases:  {bases}\n"
        f"  source: {c['source']}:{c['line']}"
    )


def _cmd_lookup_class(args: argparse.Namespace) -> int:
    answer = lookup_class(args.name, Path(args.index_dir), args.build)
    if args.json:
        print(json.dumps(answer, indent=1))
    elif answer["status"] == "ok":
        print("\n".join(_format_class(c) for c in answer["classes"]))
    else:
        print(answer["message"])
    return {"ok": 0, "not_found": 1, "index_missing": 3}[answer["status"]]


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
