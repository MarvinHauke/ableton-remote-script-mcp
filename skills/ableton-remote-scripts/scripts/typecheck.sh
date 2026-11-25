#!/bin/sh
# Type-check a script folder with basedpyright (or pyright) and its project's stubs.
#   typecheck.sh <folder> [--stubs <dir>]
# The stubs are the ones `ableton-remote-script-mcp build-stubs --project <project>` wrote:
# <project>/stubs, where <project> is the folder that holds the script folder (--stubs names
# another). Runs in standard mode, whatever the project's own settings say.
# Exit 0: no errors; 1: the checker reported errors in the script; 2: no such folder or a bad
# option; 3: no stubs (ask the user to build them); 4: no checker installed (skipped);
# 5: the checker itself failed (its own error, not the script's: nothing to fix in the code).
[ $# -eq 0 ] && { sed -n '2,/^[^#]/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2; }
folder="$1"; shift
stubs=""
while [ $# -gt 0 ]; do
    case "$1" in
        --stubs) [ $# -ge 2 ] || { echo "--stubs needs a folder" >&2; exit 2; }
                 stubs="$2"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
[ -d "$folder" ] || { echo "no such folder: $folder" >&2; exit 2; }
folder=$(cd "$folder" && pwd)
project=$(dirname "$folder")
[ -n "$stubs" ] || stubs="$project/stubs"
if [ ! -d "$stubs" ]; then
    echo "no stubs at $stubs." >&2
    echo "ask the user to build them (their Live build; it also gives their editor completion):" >&2
    echo "  ableton-remote-script-mcp build-stubs --build <build> --project '$project'" >&2
    exit 3
fi
stubs=$(cd "$stubs" && pwd)
if command -v basedpyright >/dev/null 2>&1; then checker=basedpyright
elif command -v pyright >/dev/null 2>&1; then checker=pyright
else
    echo "skipped: neither basedpyright nor pyright is installed." >&2
    exit 4
fi
json() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
tmp=$(mktemp -d) || exit 2
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/pyrightconfig.json" <<EOF
{
  "include": ["$(json "$folder")"],
  "stubPath": "$(json "$stubs")",
  "pythonVersion": "3.11",
  "reportMissingModuleSource": false,
  "typeCheckingMode": "standard"
}
EOF
"$checker" -p "$tmp/pyrightconfig.json"
status=$?
case $status in
    0) exit 0 ;;
    1) exit 1 ;;   # errors in the script
    *) echo "$checker failed on its own (exit $status): not an error in the script" >&2; exit 5 ;;
esac
