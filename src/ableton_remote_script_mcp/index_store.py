"""The API index on disk: one JSON document per Live build (plan 0001, Decision 22).

Schema 1 (plan 0001 step 1):

    {
      "schema": 1,
      "live_build": "12.4.16",
      "source": {"kind": "installed-app", "app": "...", "bundle_version": "..."},
      "extractor": {"tool_version": "...", "python": "3.11.12"},
      "created": "2026-11-15T12:00:00+00:00",
      "modules": {"<module>": {"source": "MIDI Remote Scripts/…pyc", "package": bool,
                              "live_build": ..., "confidence": "observed"}},
      "classes": {"<module>.<qualname>": {"name", "qualname", "module", "line",
                  "bases": [{"expr": "Component", "resolved": "ableton.v3….Component" | null}],
                  "keywords": {"metaclass": "Meta"}, "bases_parsed": true,
                  "source", "live_build", "confidence": "observed"}},
      "errors": [{"source": "...", "error": "..."}]
    }

The index holds facts extracted from Ableton's code, so it lives outside git.
"""

from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .extractor import UnreadablePyc, iter_pyc, read_module, resolve_base
from .live_install import LiveInstall, build_sort_key

SCHEMA_VERSION = 1
INDEX_DIR_ENV = "ABLETON_REMOTE_SCRIPT_INDEX"


def default_index_dir() -> Path:
    if os.environ.get(INDEX_DIR_ENV):
        return Path(os.environ[INDEX_DIR_ENV]).expanduser()
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return data_home / "ableton-remote-script-mcp" / "index"


def index_path(index_dir: Path, live_build: str) -> Path:
    return index_dir / f"live-{live_build}.json"


def build_index(install: LiveInstall) -> dict:
    build = install.live_build
    modules: dict[str, dict] = {}
    classes: dict[str, dict] = {}
    errors: list[dict] = []
    root = install.scripts_root
    for path in iter_pyc(root):
        rel = str(Path(root.name) / path.relative_to(root))
        try:
            mod = read_module(path, root)
        except (UnreadablePyc, OSError) as e:
            errors.append({"source": rel, "error": str(e)})
            continue
        modules[mod.name] = {
            "source": mod.source,
            "package": mod.is_package,
            "live_build": build,
            "confidence": "observed",
        }
        top_level = {c.qualname for c in mod.classes}
        for c in mod.classes:
            key = f"{mod.name}.{c.qualname}"
            classes[key] = {
                "name": c.name,
                "qualname": c.qualname,
                "module": mod.name,
                "line": c.line,
                "bases": [
                    {"expr": b, "resolved": resolve_base(b, mod.imports, mod.name, top_level)}
                    for b in c.bases
                ],
                "keywords": c.keywords,
                "bases_parsed": c.bases_parsed,
                "source": mod.source,
                "live_build": build,
                "confidence": "observed",
            }
    return {
        "schema": SCHEMA_VERSION,
        "live_build": build,
        "source": {"kind": "installed-app", "app": str(install.app), "bundle_version": install.bundle_version},
        "extractor": {"tool_version": __version__, "python": platform.python_version()},
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modules": dict(sorted(modules.items())),
        "classes": dict(sorted(classes.items())),
        "errors": errors,
    }


def write_index(index: dict, index_dir: Path) -> Path:
    index_dir.mkdir(parents=True, exist_ok=True)
    path = index_path(index_dir, index["live_build"])
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def indexed_builds(index_dir: Path) -> list[str]:
    """Builds with an index on disk, newest first."""
    if not index_dir.is_dir():
        return []
    builds = [p.name[len("live-") : -len(".json")] for p in index_dir.glob("live-*.json")]
    return sorted(builds, key=build_sort_key, reverse=True)


def load_index(index_dir: Path, live_build: str) -> dict:
    return json.loads(index_path(index_dir, live_build).read_text(encoding="utf-8"))
