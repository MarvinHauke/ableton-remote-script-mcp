import plistlib
import py_compile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_SCRIPTS = FIXTURES / "fake_scripts"
FAKE_PUSH3_HELPER = FIXTURES / "fake_push3_helper"
FAKE_BUILD = "12.4.99"


def _compile_tree(sources: Path, target: Path) -> None:
    for src in sources.rglob("*.py"):
        rel = src.relative_to(sources)
        py_compile.compile(str(src), cfile=str(target / rel.with_suffix(".pyc")), doraise=True)


@pytest.fixture
def fake_live_app(tmp_path: Path) -> Path:
    """A fake Live bundle: our own sources compiled to .pyc, laid out like Live's.

    The Remote Scripts folder gets a fake framework, Remote Scripts, a library and one corrupt file; the
    Push 3 helper gets its own `ableton` copy and a fake `live_model`.
    """
    app = tmp_path / "Ableton Live 12 Fake.app"
    contents = app / "Contents"
    scripts = contents / "App-Resources" / "MIDI Remote Scripts"
    _compile_tree(FAKE_SCRIPTS, scripts)
    _compile_tree(FAKE_PUSH3_HELPER, contents / "Helpers" / "Push3.app" / "Contents" / "Resources" / "python")
    (scripts / "_Framework" / "Broken.pyc").write_bytes(b"\x00\x01not a pyc")
    (scripts / "Fake_Mk2" / "__pycache__").mkdir()
    (scripts / "Fake_Mk2" / "__pycache__" / "stale.cpython-311.pyc").write_bytes(b"skipped")
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump({"CFBundleShortVersionString": f"{FAKE_BUILD} (2026-11-15_fake)"}, f)
    return app
