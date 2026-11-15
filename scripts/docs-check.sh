#!/usr/bin/env bash
# The docs check, the same steps CI runs: the committed CLI reference matches the argument parser
# (never writes), then the site builds with --strict (fails on broken links and anchors).
set -euo pipefail
cd "$(dirname "$0")/.."

uv run python scripts/gen_cli_reference.py --check
uv run zensical build --strict --clean
