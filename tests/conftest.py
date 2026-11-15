import plistlib
import py_compile
from pathlib import Path

import pytest

FIXTURE_SOURCES = Path(__file__).parent / "fixtures" / "fake_scripts"
FAKE_BUILD = "12.4.99"


@pytest.fixture
def fake_live_app(tmp_path: Path) -> Path:
    """A fake Live bundle: our own framework sources compiled to .pyc, laid out like Live's."""
    app = tmp_path / "Ableton Live 12 Fake.app"
    contents = app / "Contents"
    scripts = contents / "App-Resources" / "MIDI Remote Scripts"
    for src in FIXTURE_SOURCES.rglob("*.py"):
        rel = src.relative_to(FIXTURE_SOURCES)
        py_compile.compile(str(src), cfile=str(scripts / rel.with_suffix(".pyc")), doraise=True)
    (scripts / "_Framework" / "Broken.pyc").write_bytes(b"\x00\x01not a pyc")
    controller = scripts / "Some_Controller"
    controller.mkdir()
    (controller / "__init__.pyc").write_bytes(b"outside the framework packages")
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump({"CFBundleShortVersionString": f"{FAKE_BUILD} (2026-11-15_fake)"}, f)
    return app
