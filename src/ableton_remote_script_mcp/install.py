"""Copy a Remote Script folder into the User Library, where Live finds user scripts.

Live loads a user script from `<User Library>/Remote Scripts/<folder>/`. Only the script's source
is copied: compiled files and caches (`__pycache__`, `.pyc`) and hidden files stay behind, so Live
compiles the copy itself. Selecting the script in Live is the user's step.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

SKIPPED_DIRS = {"__pycache__"}
SKIPPED_SUFFIXES = {".pyc", ".pyo"}


def default_user_library() -> Path:
    return Path(os.environ.get("ABLETON_USER_LIBRARY", Path.home() / "Music/Ableton/User Library"))


def _source_files(folder: Path) -> list[Path]:
    files = []
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if any(part.startswith(".") or part in SKIPPED_DIRS for part in rel.parts):
            continue
        if path.is_file() and path.suffix not in SKIPPED_SUFFIXES:
            files.append(rel)
    return files


def install_script(folder: Path, user_library: Path, replace: bool = False) -> dict:
    """Copy `folder` to `<user_library>/Remote Scripts/<folder name>/`.

    An existing copy is replaced only with `replace`, and only when it is a Remote Script folder
    (it has an `__init__.py`) and not a symbolic link, so nothing else under that name is ever
    deleted. The new copy is written next to it first and swapped in, so a failed copy leaves the
    old one in place.
    """
    folder = folder.resolve()
    if not folder.is_dir():
        return {"status": "folder_missing", "message": f"no folder {folder}"}
    if not folder.name.isidentifier():
        return {"status": "bad_name", "message": f"the folder name {folder.name!r} is not a Python name; "
                "Live imports the script by it (validate suggests a name)"}
    if not user_library.is_dir():
        return {"status": "no_user_library",
                "message": f"no User Library at {user_library}; pass --user-library or set ABLETON_USER_LIBRARY "
                           "(Live shows its location under Settings → Library)"}
    scripts = user_library / "Remote Scripts"
    destination = scripts / folder.name
    if destination.exists() and destination.resolve() == folder:
        return {"status": "ok", "destination": str(destination), "files": [], "replaced": False,
                "message": "the folder is already in the User Library; nothing copied"}
    replaced = destination.exists() or destination.is_symlink()
    if replaced:
        if not replace:
            return {"status": "exists", "destination": str(destination),
                    "message": f"{destination} exists; pass --replace to overwrite it"}
        if destination.is_symlink() or not (destination / "__init__.py").is_file():
            what = "a symbolic link" if destination.is_symlink() else "not a Remote Script folder (no __init__.py)"
            return {"status": "exists", "destination": str(destination),
                    "message": f"{destination} exists and is {what}; left as it is"}
    scripts.mkdir(exist_ok=True)
    files = _source_files(folder)
    staging = Path(tempfile.mkdtemp(prefix=f".{folder.name}-", dir=scripts))
    try:
        for rel in files:
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / rel, target)
        if replaced:
            shutil.rmtree(destination)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"status": "ok", "destination": str(destination), "files": [str(f) for f in files],
            "replaced": replaced}
