#!/bin/sh
# Read Live's Log.txt: tracebacks and messages of Remote Scripts since Live last started.
#   log.sh [--script <Folder>] [--build <build>] [--log <path>] [--json]
# Exit 0: no traceback; 1: tracebacks; 2: no log found.
. "$(dirname "$0")/_cli.sh"
arsm log "$@"
