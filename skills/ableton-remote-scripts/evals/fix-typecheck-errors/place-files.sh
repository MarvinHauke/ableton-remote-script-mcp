#!/usr/bin/env bash
# The user's project: the script, and the stubs they built (when the CLI is reachable; without
# it the case tests the skill's question for the stubs instead).
set -eu
cp -R "$(dirname "$0")/files/." .
if command -v ableton-remote-script-mcp >/dev/null 2>&1; then
    ableton-remote-script-mcp build-stubs --build "${EVAL_BUILD:-12.4.16}" --project . >/dev/null || true
fi
