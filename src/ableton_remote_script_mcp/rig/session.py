"""What `rig run` and `rig panel` read before they play (plan 0001 Decision 59): the script's
controller model, its device profile, and a check that every element name the profile (and a
check file) uses is one the script has.

A step that fails raises `SessionError` with the reason; both commands exit 4 on it. A missing
PyYAML (the rig extra) raises `ports.RigExtraMissing`; both exit 3 on it (plan 0001 Decision 61).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .controller import Controller, controller_for_folder
from .profile import (
    Profile,
    ProfileError,
    check_profile_names,
    load_profile,
    profile_beside,
)


class SessionError(Exception):
    """The script, its profile, or an element name can't be read; the message says which."""


@dataclass
class Session:
    controller: Controller
    profile: Profile | None


def prepare(folder: Path, index_dir: Path, build: str | None, *, profile: Path | None = None,
            beside: Path | None = None, names: Callable[[Controller], list[str]] | None = None) -> Session:
    """The controller model of the script in `folder` and its profile: the file `profile`, else
    the `device.yaml` beside `beside` (default: the script folder), if any. `names(controller)`
    gives more problems with element names (a check file's). A missing PyYAML raises
    `RigExtraMissing`."""
    controller, why = controller_for_folder(Path(folder), Path(index_dir), build)
    if controller is None:
        raise SessionError(why)
    try:
        loaded = load_profile(Path(profile)) if profile else profile_beside(Path(beside or folder))
    except ProfileError as e:
        raise SessionError(str(e)) from e
    problems = (names(controller) if names else []) + (check_profile_names(loaded, controller) if loaded else [])
    if problems:
        raise SessionError("\n".join(problems))
    return Session(controller, loaded)
