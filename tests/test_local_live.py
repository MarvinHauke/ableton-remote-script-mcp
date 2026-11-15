"""Local-only check against the installed Live 12.4.16; skipped when it is absent."""

from pathlib import Path

import pytest

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.live_install import read_install

LIVE_12_4_16 = Path("/Applications/Ableton Live 12 Suite.app")


@pytest.fixture(scope="module")
def live_12_4_16():
    try:
        install = read_install(LIVE_12_4_16)
    except (ValueError, OSError):
        pytest.skip("Ableton Live 12 Suite is not installed")
    if install.live_build != "12.4.16":
        pytest.skip(f"installed Live 12 Suite is {install.live_build}, not 12.4.16")
    return install


@pytest.mark.local_live
def test_control_surface_specification_in_12_4_16(live_12_4_16, tmp_path, capsys):
    index_dir = tmp_path / "index"
    assert main(["--index-dir", str(index_dir), "build-index", "--app", str(live_12_4_16.app)]) == 0
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "ControlSurfaceSpecification"]) == 0
    out = capsys.readouterr().out
    assert "ableton.v3.control_surface.control_surface_specification.ControlSurfaceSpecification" in out
    assert "[Live 12.4.16, observed]" in out


@pytest.mark.local_live
def test_generic_base_in_12_4_16(live_12_4_16, tmp_path, capsys):
    # Seen in 12.4.16: DisplayLineElement(NotifyingControlElement, Generic[DisplayDataType])
    index_dir = tmp_path / "index"
    main(["--index-dir", str(index_dir), "build-index", "--app", str(live_12_4_16.app)])
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "DisplayLineElement"]) == 0
    assert "typing.Generic[DisplayDataType]" in capsys.readouterr().out
