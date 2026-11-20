"""`build-stubs` (plan 0001, after step 11; Decision 49 Q9): type stubs of a build for a language
server, from the hand-written index."""

import ast
import json

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



def test_members_the_index_keeps_as_methods(stubs):
    """0001 Decision 56: the index keeps the last `def` of a name. A `listenable_property` with a
    setter is read from its `@<name>.setter`; a control's handler under the control's own name
    and a listener slot are objects at runtime, so attributes; a NamedTuple takes any field."""
    _, out = stubs
    grid = read(out, "ableton/v3/control_surface/components/grid_resolution.pyi")
    assert ("    @property\n    def index(self) -> Any: ...\n"
            "    @index.setter\n    def index(self, value: Any) -> None: ...") in grid
    assert "    resolution_buttons: Any" in grid
    assert "    _GridResolutionComponent__on_clip_changed: Any" in grid
    assert "class GridEntry:\n    def __init__(self, *a: Any, **k: Any) -> None: ...  # fields not in the index" in grid


def test_property_parts_and_handlers_under_another_name():
    from ableton_remote_script_mcp.stubs import _method, is_slot_or_control

    deleter = {"kind": "method", "params": [{"name": "self"}], "decorators": ["value.deleter"]}
    assert "    @value.setter" in _method("value", deleter, "    ")  # a deleter follows a setter
    # `@jog.pressed def _on_jog` is the control at runtime too; written as a method (no error)
    handler = {"kind": "method", "params": [{"name": "self"}, {"name": "b"}], "decorators": ["jog.pressed"]}
    assert not is_slot_or_control("_on_jog", handler)


def test_a_project_gets_its_stubs_config_and_ignore_line(stubs, tmp_path, capsys):
    """Decision 56 task 2: `build-stubs --project <folder>`."""
    index_dir, _ = stubs
    project = tmp_path / "My_Script"
    (project / ".git").mkdir(parents=True)  # a git repo
    (project / ".gitignore").write_text("__pycache__/", encoding="utf-8")  # no newline at its end
    assert main(["--index-dir", str(index_dir), "build-stubs", "--build", OLD, "--project", str(project)]) == 0
    out = capsys.readouterr().out
    assert (project / "stubs" / MARKER).is_file() and (project / "stubs" / "ableton" / "__init__.pyi").is_file()
    config = json.loads((project / "pyrightconfig.json").read_text(encoding="utf-8"))
    assert config == {
        "stubPath": "stubs",
        "pythonVersion": "3.11",
        "reportMissingModuleSource": False,
        "typeCheckingMode": "standard",
    }
    assert (project / ".gitignore").read_text(encoding="utf-8") == "__pycache__/\nstubs/\n"
    assert "created pyrightconfig.json" in out and "added stubs/ to .gitignore" in out
    # again: the stubs are replaced, the config and the ignore file stay as they are
    (project / "pyrightconfig.json").write_text('{"typeCheckingMode": "strict"}', encoding="utf-8")
    answer = build_stubs(index_dir, OLD, project=project)
    assert answer["status"] == "ok" and answer["out"] == str(project / "stubs")
    assert answer["project"] == {"folder": str(project), "config": "kept", "gitignore": "present"}
    assert (project / "pyrightconfig.json").read_text(encoding="utf-8") == '{"typeCheckingMode": "strict"}'
    assert (project / ".gitignore").read_text(encoding="utf-8").count("stubs") == 1
    main(["--index-dir", str(index_dir), "build-stubs", "--build", OLD, "--project", str(project)])
    out = capsys.readouterr().out
    assert "pyrightconfig.json is there, left as it is; these settings" in out and '"stubPath": "stubs"' in out
    assert '"typeCheckingMode": "standard"' in out
    (project / "pyrightconfig.json").write_text('{"stubPath": "stubs"}', encoding="utf-8")
    main(["--index-dir", str(index_dir), "build-stubs", "--build", OLD, "--project", str(project)])
    assert '"stubPath" is already "stubs"' in capsys.readouterr().out


def test_git_s_own_answer_counts_for_the_ignore_line(stubs, tmp_path):
    """A script folder in a repo whose root `.gitignore` already ignores `stubs/` gets no file."""
    import shutil
    import subprocess

    if not shutil.which("git"):
        pytest.skip("git is not on the PATH")
    index_dir, _ = stubs
    repo = tmp_path / "repo"
    (repo / "My_Script").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text("**/stubs/\n", encoding="utf-8")
    assert build_stubs(index_dir, OLD, project=repo / "My_Script")["project"]["gitignore"] == "present"
    assert not (repo / "My_Script" / ".gitignore").exists()


@pytest.mark.parametrize("line", ["stubs", "stubs/", "/stubs", "/stubs/"])
def test_an_ignore_line_for_the_stubs_counts_in_any_form(stubs, tmp_path, line):
    index_dir, _ = stubs
    project = tmp_path / "p"
    project.mkdir()
    (project / ".git").write_text("gitdir: ../.git/modules/p\n")  # a submodule's .git is a file
    (project / ".gitignore").write_text(f"# local\n{line}\n", encoding="utf-8")
    assert build_stubs(index_dir, OLD, project=project)["project"]["gitignore"] == "present"
    assert (project / ".gitignore").read_text(encoding="utf-8") == f"# local\n{line}\n"


def test_a_project_outside_git_and_one_configured_in_pyproject(stubs, tmp_path):
    index_dir, _ = stubs
    plain = tmp_path / "plain"
    plain.mkdir()
    assert build_stubs(index_dir, OLD, project=plain)["project"]["gitignore"] == "not_a_repo"
    assert not (plain / ".gitignore").exists() and (plain / "pyrightconfig.json").is_file()
    # a pyrightconfig.json would override [tool.pyright] / [tool.basedpyright], so none is made
    configured = tmp_path / "configured"
    configured.mkdir()
    (configured / "pyproject.toml").write_text('[tool.basedpyright]\nstubPath = "stubs"\n', encoding="utf-8")
    assert build_stubs(index_dir, OLD, project=configured)["project"]["config"] == "kept"
    assert not (configured / "pyrightconfig.json").exists()


def test_out_and_project_exclude_each_other(stubs, tmp_path, capsys):
    index_dir, _ = stubs
    with pytest.raises(SystemExit) as e:
        main(["--index-dir", str(index_dir), "build-stubs", "--out", str(tmp_path / "a"),
              "--project", str(tmp_path / "b")])
    assert e.value.code == 2 and "not allowed with" in capsys.readouterr().err


def test_a_project_folder_that_does_not_exist_is_refused(stubs, tmp_path, capsys):
    index_dir, _ = stubs
    assert main(["--index-dir", str(index_dir), "build-stubs", "--build", OLD,
                 "--project", str(tmp_path / "missing")]) == 2
    assert "no folder" in capsys.readouterr().out and not (tmp_path / "missing").exists()
