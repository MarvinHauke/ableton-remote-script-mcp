# Sourced by the other scripts: runs the ableton-remote-script-mcp command.
# $ABLETON_REMOTE_SCRIPT_MCP overrides the command, e.g. "uv run --project /path/to/clone ableton-remote-script-mcp".
arsm() {
    if [ -n "${ABLETON_REMOTE_SCRIPT_MCP:-}" ]; then
        # shellcheck disable=SC2086  # the override is a command line, split on purpose
        $ABLETON_REMOTE_SCRIPT_MCP "$@"
    elif command -v ableton-remote-script-mcp >/dev/null 2>&1; then
        ableton-remote-script-mcp "$@"
    else
        echo "the ableton-remote-script-mcp command is not installed." >&2
        echo "install it from a clone of the repo: uv tool install <path to ableton-remote-script-mcp>" >&2
        echo "or set ABLETON_REMOTE_SCRIPT_MCP to the command that runs it." >&2
        return 127
    fi
}
