#!/bin/sh
# The test rig: play a script over a virtual MIDI port and check what Live sends back.
#   rig.sh serve                      hold the port `ARS Test Rig` open (leave it running)
#   rig.sh elements <folder>          the script's elements and their MIDI messages
#   rig.sh run <checks.yaml>          run a check file; writes checks.result.json beside it
#   rig.sh restart-live --wait-for <text>   only with the user's go (references/test-rig.md)
# Each takes --help. Needs the tool's `rig` extra.
# Exit of run: 0: no step failed; 1: a step failed; 2: Live silent; 3: no rig extra;
# 4: a bad check file or profile; 5: the tool failed.
. "$(dirname "$0")/_cli.sh"
[ $# -eq 0 ] && { sed -n '2,/^[^#]/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2; }
arsm rig "$@"
