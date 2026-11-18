#!/bin/sh
# Look up the API index of a Live build.
#   lookup.sh builds                     the indexed Live builds
#   lookup.sh class <Name> [--own]       a class with its members (inherited ones with their origin)
#             [--member <m> ...]         only whether it has these members
#   lookup.sh search <words> [--kind K]  classes, modules and members by name or words (--offset N: next page)
#   lookup.sh outline <Script>           one of Ableton's scripts: elements, components, layers
#             [--section <name>]         one section of a large outline
#   lookup.sh names <folder>             where each API name a script uses is known (observed, documented, unknown)
#   lookup.sh names --names <A.b> ...    the same for a list: Class, Class.member or a bare name
# Every form takes --build <build> and --json. Answers are capped at about 4,000 tokens; --full gives all.
. "$(dirname "$0")/_cli.sh"
what="${1:-}"
[ $# -gt 0 ] && shift
case "$what" in
    builds) arsm list builds "$@" ;;
    class) arsm lookup class "$@" ;;
    search) arsm search "$@" ;;
    outline) arsm outline "$@" ;;
    names) arsm check-names "$@" ;;
    *) sed -n '2,/^[^#]/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
