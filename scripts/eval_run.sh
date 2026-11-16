#!/usr/bin/env bash
# Run the skill evals (plan 0001 step 9a) with `claude plugin eval`, then score the scripts.
#
#     scripts/eval_run.sh <out dir> [extra `claude plugin eval` options, e.g. --case uc4-mixer-v3 --runs 1]
#
# The eval command runs each case in a sandbox that may read only the skill folder and a few bin
# folders such as ~/.local/bin: not this repo, not ~/.local/share (where the index and uv's tools
# live). So for the length of the run this puts a self-contained build of the CLI (a zipapp,
# run by a Python outside /Users) and a copy of the index into ~/.local/bin, and removes both
# afterwards. The runs without the skill never learn the CLI is there; the sandbox keeps them
# away from the repo, whose example script would answer the APC mini case.
#
# Runs use the claude.ai login (ANTHROPIC_API_KEY is unset for the eval command only), and the
# report stays local (--no-publish). Scores are against Live 12.4.16 (EVAL_BUILD to change it).
# After scoring, each run's trace is copied to <out dir>/traces and the kept sandboxes are
# deleted. The out dir must be outside this repo or in a git-ignored folder.
set -euo pipefail

out=${1:?usage: scripts/eval_run.sh <out dir> [claude plugin eval options]}
shift
repo=$(cd "$(dirname "$0")/.." && pwd)
skill="$repo/skills/ableton-remote-scripts"
python=${EVAL_PYTHON:-/opt/homebrew/bin/python3.12}  # readable inside the sandbox; lookup and validate need no 3.11
eval_build=${EVAL_BUILD:-12.4.16}
bin="$HOME/.local/bin"
app="$bin/ableton-remote-script-mcp"
index_copy="$bin/.ableton-remote-script-mcp-eval-index"
index_src=${ABLETON_REMOTE_SCRIPT_INDEX:-$HOME/.local/share/ableton-remote-script-mcp/index}

if [ -e "$app" ] || [ -e "$index_copy" ]; then
    echo "$app or $index_copy already exists; remove it (a uv tool install?) before an eval run" >&2
    exit 2
fi
mkdir -p "$out"
out=$(cd "$out" && pwd)
case "$out" in
    "$repo"/*) git -C "$repo" check-ignore -q "$out" || {
        echo "$out is in the repo but not git-ignored; use a folder such as skills/ableton-remote-scripts-workspace/<name>" >&2
        exit 2; } ;;
esac

build=$(mktemp -d)
cleanup() { rm -rf "$app" "$index_copy" "$build"; }
trap cleanup EXIT
trap 'exit 130' INT TERM HUP  # exit runs the EXIT trap

cp -R "$repo/src/ableton_remote_script_mcp" "$build/"
rm -rf "$build/ableton_remote_script_mcp/__pycache__"
cat > "$build/__main__.py" <<EOF
import os, sys
os.environ.setdefault("ABLETON_REMOTE_SCRIPT_INDEX", "$index_copy")
from ableton_remote_script_mcp.cli import main
sys.exit(main())
EOF
"$python" -m zipapp "$build" -o "$app" -p "$python"
cp -R "$index_src" "$index_copy"
"$app" list builds >/dev/null

(cd "$skill" && env -u ANTHROPIC_API_KEY claude plugin eval . --scaffold \
    --allow-tools Write Edit Bash --no-publish --keep-temp --trust-plugin \
    --output-dir "$out" --json "$out/result.json" --report "$out/report.html" "$@") \
    > "$out/eval.log" 2>&1 || echo "claude plugin eval exited $? (see $out/eval.log)" >&2
cd "$repo" && uv run python scripts/eval_score.py "$out/result.json" --build "$eval_build" --remove-kept
