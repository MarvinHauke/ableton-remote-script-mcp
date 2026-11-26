#!/bin/sh
# Validate a Remote Script folder, then copy it into the User Library's Remote Scripts folder.
#   install.sh <folder> [--replace] [--build <build>] [--user-library <path>] [--no-validate]
# Exit 0: installed; 1: validator findings; 2: refused (exists, not a script folder, a link, a bad
# name) or no folder or User Library; 3: no index for the build; 5: the tool failed.
# Selecting it in Live is the user's step.
. "$(dirname "$0")/_cli.sh"
[ $# -eq 0 ] && { sed -n '2,/^[^#]/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2; }
arsm install "$@"
