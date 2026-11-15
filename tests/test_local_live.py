"""Local-only checks against the installed Live 12.4.16; skipped when it is absent.

Each asserts a fact seen in 12.4.16 (plan 0001, Testing Decisions).
"""

import json
from pathlib import Path

import pytest

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.live_install import read_install

LIVE_12_4_16 = Path("/Applications/Ableton Live 12 Suite.app")
SPEC = "ableton.v3.control_surface.control_surface_specification.ControlSurfaceSpecification"


@pytest.fixture(scope="module")
def live_12_4_16():
    try:
        install = read_install(LIVE_12_4_16)
    except (ValueError, OSError):
        pytest.skip("Ableton Live 12 Suite is not installed")
    if install.live_build != "12.4.16":
        pytest.skip(f"installed Live 12 Suite is {install.live_build}, not 12.4.16")
    return install


@pytest.fixture(scope="module")
def index_dir(live_12_4_16, tmp_path_factory):
    index_dir = tmp_path_factory.mktemp("index")
    assert main(["--index-dir", str(index_dir), "build-index", "--app", str(live_12_4_16.app)]) == 0
    return index_dir


@pytest.fixture(scope="module")
def index(index_dir):
    return json.loads((index_dir / "live-12.4.16.json").read_text())


@pytest.mark.local_live
def test_control_surface_specification_in_12_4_16(index_dir, capsys):
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "ControlSurfaceSpecification"]) == 0
    out = capsys.readouterr().out
    assert f"{SPEC}  [Live 12.4.16, observed]" in out
    assert "session_ring_selection_linking_type = SessionRingSelectionLinking" in out


@pytest.mark.local_live
def test_specification_fields_in_12_4_16(index):
    members = index["classes"][SPEC]["members"]
    assert members["session_ring_selection_linking_type"]["kind"] == "attribute"
    assert members["num_tracks"]["value"] == "8"


@pytest.mark.local_live
def test_generic_base_in_12_4_16(index_dir, capsys):
    # Seen in 12.4.16: DisplayLineElement(NotifyingControlElement, Generic[DisplayDataType])
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "DisplayLineElement"]) == 0
    assert "typing.Generic[DisplayDataType]" in capsys.readouterr().out


@pytest.mark.local_live
def test_apc_mini_frameworks_in_12_4_16(index):
    packages = index["packages"]
    assert (packages["APC_mini"]["kind"], packages["APC_mini"]["framework"]) == ("script", "_Framework")
    assert (packages["APC_mini_mk2"]["kind"], packages["APC_mini_mk2"]["framework"]) == ("script", "ableton.v3")


@pytest.mark.local_live
def test_push3_helper_and_live_model_in_12_4_16(index):
    assert index["errors"] == []
    song = index["classes"]["push3-helper:live_model.Live.Song.Song"]
    assert song["proxy_model"] is True and song["proxy_of"] == "Live.Song.Song"
    assert "tempo" in song["members"]
