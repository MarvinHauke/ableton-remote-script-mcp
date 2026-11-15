"""Find installed Live builds and their Remote Scripts folder."""

from __future__ import annotations

import plistlib
import re
from dataclasses import dataclass
from pathlib import Path

APPLICATIONS = Path("/Applications")
SCRIPTS_SUBPATH = Path("Contents/App-Resources/MIDI Remote Scripts")


@dataclass(frozen=True)
class LiveInstall:
    app: Path
    live_build: str  # e.g. "12.4.16", "13.0b25"
    bundle_version: str  # Info.plist's full string, e.g. "12.4.16 (2026-10-30_e33287a1c7)"

    @property
    def scripts_root(self) -> Path:
        return self.app / SCRIPTS_SUBPATH

    @property
    def is_beta(self) -> bool:
        return bool(re.search(r"[ab]\d+$", self.live_build))


def read_install(app: Path) -> LiveInstall:
    """Read one Live app bundle. Raises ValueError when it is not a Live bundle."""
    plist = app / "Contents" / "Info.plist"
    if not plist.is_file():
        raise ValueError(f"{app}: no Contents/Info.plist, not an app bundle")
    with plist.open("rb") as f:
        info = plistlib.load(f)
    bundle_version = str(info.get("CFBundleShortVersionString", "")).strip()
    if not bundle_version:
        raise ValueError(f"{app}: Info.plist has no CFBundleShortVersionString")
    install = LiveInstall(app=app, live_build=bundle_version.split()[0], bundle_version=bundle_version)
    if not install.scripts_root.is_dir():
        raise ValueError(f"{app}: no {SCRIPTS_SUBPATH}")
    return install


def _build_key(live_build: str) -> tuple:
    """Sort key: 12.4.16 < 12.4.25b1 < 13.0b25; a release sorts after its betas."""
    m = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?(?:([ab])(\d+))?", live_build)
    if not m:
        return (0,)
    major, minor, patch, pre, pre_n = m.groups()
    pre_rank = {"a": 0, "b": 1, None: 2}[pre]
    return (int(major), int(minor), int(patch or 0), pre_rank, int(pre_n or 0))


def find_installs(applications: Path = APPLICATIONS) -> list[LiveInstall]:
    """Every Live app in the Applications folder, newest build first."""
    installs = []
    for app in sorted(applications.glob("Ableton Live*.app")):
        try:
            installs.append(read_install(app))
        except (ValueError, OSError, plistlib.InvalidFileException):
            continue
    return sorted(installs, key=lambda i: _build_key(i.live_build), reverse=True)


def default_install(installs: list[LiveInstall]) -> LiveInstall | None:
    """The newest release build; a beta only when no release is installed."""
    releases = [i for i in installs if not i.is_beta]
    return (releases or installs or [None])[0]


def build_sort_key(live_build: str) -> tuple:
    return _build_key(live_build)
