"""Moved into the package as `ableton-remote-script-mcp check-names` (plan 0001 step 11).

This name stays for the evals' graders and older notes; it runs the same check.

    uv run python scripts/eval_names.py <script folder> [--build 12.4.16] [--json]
"""

from __future__ import annotations

import sys

from ableton_remote_script_mcp.cli import main as cli_main
from ableton_remote_script_mcp.names import check, event_methods, known_names  # noqa: F401  the evals import these


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--build" not in argv:
        argv += ["--build", "12.4.16"]  # the evals' build (plan step 9a)
    return cli_main(["check-names", *argv])


if __name__ == "__main__":
    sys.exit(main())
