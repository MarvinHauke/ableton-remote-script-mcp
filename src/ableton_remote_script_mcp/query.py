"""Query core: the one interface the CLI, the skill scripts and the MCP tools use.

Answers are plain dicts with a `status` of "ok", "index_missing" or "not_found", so every
adapter can pass them through and no caller has to guess.
"""

from __future__ import annotations

from pathlib import Path

from .index_store import index_path, indexed_builds, load_index

BUILD_INDEX_HINT = "run `uv run ableton-remote-script-mcp build-index` (or `--app <Live.app>` for a specific build)"


def _index_missing(index_dir: Path, live_build: str | None) -> dict:
    where = index_path(index_dir, live_build) if live_build else index_dir
    what = f"no API index for Live {live_build}" if live_build else "no API index"
    return {"status": "index_missing", "message": f"{what} at {where}; {BUILD_INDEX_HINT}"}


def lookup_class(name: str, index_dir: Path, live_build: str | None = None) -> dict:
    """Find classes by short name (`Component`) or qualified name (`ableton.v3….Component`)."""
    builds = indexed_builds(index_dir)
    if live_build is None:
        if not builds:
            return _index_missing(index_dir, None)
        live_build = builds[0]
    elif live_build not in builds:
        return _index_missing(index_dir, live_build)

    index = load_index(index_dir, live_build)
    classes = index["classes"]
    if name in classes:
        matches = [classes[name]]
    else:
        matches = [c for c in classes.values() if c["name"] == name or c["qualname"] == name]
    if not matches:
        return {
            "status": "not_found",
            "live_build": live_build,
            "message": f"class {name!r} not found in Live {live_build}",
        }
    return {
        "status": "ok",
        "live_build": live_build,
        "classes": [{"qualified_name": f"{c['module']}.{c['qualname']}", **c} for c in matches],
    }
