#!/bin/sh
# Check a Remote Script folder against a Live build's API index.
#   validate.sh <folder> [--build <build>] [--json]
# Exit 0: no findings; 1: findings; 2: no such folder; 3: no index for the build.
. "$(dirname "$0")/_cli.sh"
[ $# -eq 0 ] && { sed -n '2,/^[^#]/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2; }
arsm validate "$@"
