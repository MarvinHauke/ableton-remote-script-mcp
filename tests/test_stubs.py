"""`build-stubs` (plan 0001, after step 11; Decision 49 Q9): type stubs of a build for a language
server, from the hand-written index."""

import ast

import pytest
from hand_index import OLD, write_hand_index
from test_structure_void import documented_index

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.query import build_stubs
from ableton_remote_script_mcp.stubs import MARKER


@pytest.fixture
def stubs(tmp_path):
    index_dir = write_hand_index(tmp_path / "index")
    answer = build_stubs(index_dir, OLD)
    assert answer["status"] == "ok" and answer["files"] > 0
    return index_dir, tmp_path / "index" / "stubs" / OLD


def read(out, path):
    return (out / path).read_text(encoding="utf-8")


def test_every_stub_parses_and_says_it_stays_local(stubs):
    _, out = stubs
    files = list(out.rglob("*.pyi"))
    assert files and (out / MARKER).is_file()
    for f in files:
        ast.parse(f.read_text(encoding="utf-8"), str(f))
        assert "never publish it" in f.read_text(encoding="utf-8")
    assert (out / "ableton" / "__init__.pyi").is_file()  # a package folder with no module of its own


def test_classes_members_and_re_exports(stubs):
    _, out = stubs
    ring = read(out, "ableton/v3/control_surface/components/session_ring.pyi")
    assert "from ableton.v3.control_surface import Component as Component" in ring
    assert "class SessionRingComponent(Component):" in ring
    assert '    """Moves a red box over the clip grid of the Session View."""' in ring
    # a default the index doesn't mark as a literal is `...`
    assert "def __init__(self, num_tracks: Any = ..., num_scenes: Any = ..., *a: Any, **k: Any) -> Any: ..." in ring
    assert "def set_offsets(self, track_offset: Any, scene_offset: Any) -> Any: ..." in ring
    comp = read(out, "ableton/v3/control_surface/component.pyi")
    assert "    num_layers: Any" in comp
    assert "    @property\n    def layer(self) -> Any: ...\n    @layer.setter" in comp
    package = read(out, "ableton/v3/control_surface/__init__.pyi")
    assert "from ableton.v3.control_surface.component import Component as Component" in package
    assert "BaseComponent: Any" in package
    notifications = read(out, "ableton/v3/control_surface/display/notifications.pyi")
    assert "class Notifications:\n    class Device:\n        bank: Any" in notifications
    star = read(out, "Fake_Script/mixer.pyi")
    assert "from _Framework.ControlSurfaceComponent import *" in star


def test_the_live_package_with_documented_members(tmp_path):
    index_dir = documented_index(tmp_path)
    build_stubs(index_dir, OLD)
    song = read(index_dir / "stubs" / OLD, "Live/Song.pyi")
    assert "class Song:" in song  # live_model's own base classes are left out
    assert "def tempo(self) -> Any: ..." in song and "@tempo.setter" in song
    assert "def add_tempo_listener(self, *a: Any, **k: Any) -> Any: ...  # documented: Structure Void" in song
    build_stubs(index_dir, OLD, observed_only=True)  # the folder of earlier stubs is replaced
    song = read(index_dir / "stubs" / OLD, "Live/Song.pyi")
    assert "tempo" in song and "documented" not in song


def test_a_folder_of_other_files_is_refused(stubs, tmp_path, capsys):
    index_dir, _ = stubs
    mine = tmp_path / "mine"
    mine.mkdir()
    (mine / "notes.txt").write_text("keep me")
    assert main(["--index-dir", str(index_dir), "build-stubs", "--build", OLD, "--out", str(mine)]) == 2
    assert "not stubs of this tool" in capsys.readouterr().out and (mine / "notes.txt").exists()
    assert main(["--index-dir", str(index_dir), "build-stubs", "--build", OLD]) == 0
    assert '"stubPath"' in capsys.readouterr().out
    assert main(["--index-dir", str(tmp_path / "empty"), "build-stubs"]) == 3


def test_parameters_defaults_and_stored_functions():
    from ableton_remote_script_mcp.stubs import (
        _params,
        _stored_function,
        instance_attributes,
    )

    params = [{"name": "self"}, {"name": "a", "kind": "positional_only"},
              {"name": "b", "default": "'x'", "default_literal": True},
              {"name": "c", "default": "nop", "default_literal": False}, {"name": "d", "kind": "keyword_only"}]
    assert _params(params) == "self, a: Any, /, b: Any = 'x', c: Any = ..., *, d: Any"
    assert _stored_function({"kind": "method", "params": [{"name": "x", "kind": "var_positional"}]})
    assert not _stored_function({"kind": "method", "params": [{"name": "self"}]})
    members = {"__init__": {"statements": [{"store": "self._x", "value": "1"},
                                           {"call": "f", "target": "self._y, self._z"},
                                           {"store": "self._x.child", "value": "2"}]}}
    assert instance_attributes(members) == ["_x", "_y", "_z"]
