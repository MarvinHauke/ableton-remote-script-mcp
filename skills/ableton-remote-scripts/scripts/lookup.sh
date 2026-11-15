#!/bin/sh
# Look up the API index of a Live build.
#   lookup.sh builds                     the indexed Live builds
#   lookup.sh class <Name> [--own]       a class with its members (inherited ones with their origin)
#   lookup.sh search <words> [--kind K]  classes, modules and members by name or words
#   lookup.sh outline <Script>           one of Ableton's scripts: elements, components, layers
# Every form takes --build <build> and --json.
. "$(dirname "$0")/_cli.sh"
what="${1:-}"
[ $# -gt 0 ] && shift
case "$what" in
    builds) arsm list builds "$@" ;;
    class) arsm lookup class "$@" ;;
    search) arsm search "$@" ;;
    outline) arsm outline "$@" ;;
    *) sed -n '2,/^[^#]/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
