"""Query core: the one interface the CLI, the skill scripts and the MCP tools use.

Answers are plain dicts with a `status` of "ok", "index_missing" or "not_found", so every
adapter can pass them through and no caller has to guess.
"""

from __future__ import annotations

import json
from pathlib import Path

from .index_store import SCHEMA_VERSION, SCRIPTS_ROOT, index_path, indexed_builds, load_index
from .live_install import LiveInstall

BUILD_INDEX_HINT = "run `uv run ableton-remote-script-mcp build-index` (or `--app <Live.app>` for a specific build)"


def _index_missing(index_dir: Path, live_build: str | None, reason: str | None = None) -> dict:
    where = index_path(index_dir, live_build) if live_build else index_dir
    what = reason or (f"no API index for Live {live_build}" if live_build else "no API index")
    return {"status": "index_missing", "message": f"{what} at {where}; {BUILD_INDEX_HINT}"}


def _open(index_dir: Path, live_build: str | None) -> tuple[dict | None, dict | None]:
    """(index, None) or (None, an index_missing answer)."""
    builds = indexed_builds(index_dir)
    if live_build is None:
        if not builds:
            return None, _index_missing(index_dir, None)
        live_build = builds[0]
    elif live_build not in builds:
        return None, _index_missing(index_dir, live_build)
    try:
        index = load_index(index_dir, live_build)
    except (OSError, json.JSONDecodeError) as e:
        return None, _index_missing(index_dir, live_build, f"the index for Live {live_build} is unreadable ({e})")
    if index.get("schema") != SCHEMA_VERSION:
        return None, _index_missing(
            index_dir,
            live_build,
            f"the index for Live {live_build} has schema {index.get('schema')}; this tool reads schema {SCHEMA_VERSION}",
        )
    return index, None


def lookup_class(name: str, index_dir: Path, live_build: str | None = None) -> dict:
    """Find classes by short name (`Component`), qualname, or key (`ableton.v3….Component`,
    `push3-helper:live_model.Live.Song.Song`). Matches from the Remote Scripts come first."""
    index, missing = _open(index_dir, live_build)
    if missing:
        return missing
    live_build = index["live_build"]
    classes = index["classes"]
    if name in classes:
        keys = [name]
    else:
        keys = [k for k, c in classes.items() if name in (c["name"], c["qualname"], f"{c['module']}.{c['qualname']}")]
    if not keys:
        return {
            "status": "not_found",
            "live_build": live_build,
            "message": f"class {name!r} not found in Live {live_build}",
        }
    keys.sort(key=lambda k: (classes[k]["root"] != SCRIPTS_ROOT, k))
    return {
        "status": "ok",
        "live_build": live_build,
        "classes": [{"qualified_name": k, **classes[k]} for k in keys],
    }


def list_builds(index_dir: Path, installs: list[LiveInstall] | None = None) -> dict:
    """The indexed builds, newest first, with their counts; and installed builds with no index."""
    builds = []
    for live_build in indexed_builds(index_dir):
        entry: dict = {"live_build": live_build, "path": str(index_path(index_dir, live_build))}
        try:
            index = load_index(index_dir, live_build)
        except (OSError, json.JSONDecodeError) as e:
            entry.update(usable=False, problem=f"unreadable: {e}")
            builds.append(entry)
            continue
        entry.update(
            created=index.get("created"),
            app=index.get("source", {}).get("app"),
            bundle_version=index.get("source", {}).get("bundle_version"),
            schema=index.get("schema"),
            usable=index.get("schema") == SCHEMA_VERSION,
            summary=index.get("summary"),
        )
        if not entry["usable"]:
            entry["problem"] = f"schema {index.get('schema')}, this tool reads schema {SCHEMA_VERSION}; rebuild it"
        builds.append(entry)
    indexed = {b["live_build"] for b in builds}
    not_indexed = [
        {"live_build": i.live_build, "app": str(i.app), "beta": i.is_beta}
        for i in (installs or [])
        if i.live_build not in indexed
    ]
    if not builds:
        answer = _index_missing(index_dir, None)
        answer["installed_not_indexed"] = not_indexed
        return answer
    return {"status": "ok", "builds": builds, "installed_not_indexed": not_indexed}
