"""What `rig run` and `rig panel` read before they play (`rig/session.py`, plan 0001 Decision 59)."""

import pytest

from ableton_remote_script_mcp.rig import session
from ableton_remote_script_mcp.rig.session import SessionError, prepare


class Ctl:
    def __init__(self):
        self.script, self.elements, self.matrices = "Box", {"play_button": object()}, {"pads": ["pads[0]"]}


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(session, "controller_for_folder",
                        lambda f, i, b: (Ctl(), "") if (f / "__init__.py").is_file() else (None, f"no script in {f}"))
    box = tmp_path / "Box"
    box.mkdir()
    (box / "__init__.py").write_text("")
    return box


def test_the_controller_and_the_profile_beside_the_script(folder):
    (folder / "device.yaml").write_text("layout:\n  - [pads, play_button]\n")
    s = prepare(folder, folder, None)
    assert isinstance(s.controller, Ctl) and s.profile.layout == [["pads", "play_button"]]


def test_no_profile_is_no_problem(folder):
    assert prepare(folder, folder, None).profile is None


def test_each_step_that_fails_says_why(folder, tmp_path):
    with pytest.raises(SessionError, match="no script in"):
        prepare(tmp_path / "Nothing", folder, None)
    (folder / "device.yaml").write_text("layout:\n  - [pads, nope]\n")
    with pytest.raises(SessionError, match="`nope`"):
        prepare(folder, folder, None)
    checks = tmp_path / "checks"
    checks.mkdir()
    (checks / "device.yaml").write_text("layout: [not a list of rows\n")
    with pytest.raises(SessionError):
        prepare(folder, folder, None, beside=checks / "checks.yaml")


def test_a_check_files_names_come_before_the_profiles(folder):
    (folder / "device.yaml").write_text("layout:\n  - [nope]\n")
    with pytest.raises(SessionError) as e:
        prepare(folder, folder, None, names=lambda ctl: ["checks.yaml names `gone`"])
    assert str(e.value).splitlines() == ["checks.yaml names `gone`",
                                         "device.yaml names `nope`, which Box has no element or matrix of"]


def test_an_explicit_profile_wins_over_the_one_beside(folder, tmp_path):
    (folder / "device.yaml").write_text("layout:\n  - [nope]\n")
    other = tmp_path / "other.yaml"
    other.write_text("layout:\n  - [play_button]\n")
    assert prepare(folder, folder, None, profile=other).profile.layout == [["play_button"]]
