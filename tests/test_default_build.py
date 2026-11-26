"""The default build (plan 0001 Decision 63): a named build, else the setting, else the newest
indexed release, else the newest beta; beta answers say so, release answers carry no mark."""

import pytest
from hand_index import NEW, OLD, new_build, write_hand_index

from ableton_remote_script_mcp import api
from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.index_store import (
    SETTINGS_FILE,
    default_build,
    read_default_setting,
)


@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


def _cli(index_dir, *args):
    return main(["--index-dir", str(index_dir), *args])


def test_the_newest_release_before_a_newer_beta(index_dir):
    assert default_build(index_dir) == (OLD, "newest release")
    answer = api.lookup("Component", index_dir=index_dir)
    assert answer["live_build"] == OLD and "beta" not in answer


def test_a_beta_answer_says_so(index_dir, capsys):
    assert api.lookup("Component", NEW, index_dir=index_dir)["beta"] is True
    assert api.search("Component", NEW, index_dir=index_dir)["beta"] is True
    assert api.diff(OLD, NEW, index_dir=index_dir)["beta"] is True
    assert _cli(index_dir, "search", "Component", "--build", NEW) == 0
    assert f"Live {NEW} (beta)" in capsys.readouterr().out


def test_only_betas_indexed_the_newest_beta(tmp_path):
    new_build().write(tmp_path / "index")
    assert default_build(tmp_path / "index") == (NEW, "newest beta")
    assert api.lookup("Component", index_dir=tmp_path / "index")["beta"] is True


def test_the_setting_wins_and_list_builds_marks_it(index_dir, capsys):
    assert _cli(index_dir, "default-build", NEW) == 0
    assert read_default_setting(index_dir) == NEW and (index_dir / SETTINGS_FILE).is_file()
    assert api.lookup("Component", index_dir=index_dir)["live_build"] == NEW
    builds = {b["live_build"]: b for b in api.list_builds(index_dir=index_dir, installs=[])["builds"]}
    assert builds[NEW]["default"] is True and builds[NEW]["default_from"] == "setting" and builds[NEW]["beta"] is True
    assert "default" not in builds[OLD] and "beta" not in builds[OLD]
    capsys.readouterr()
    assert _cli(index_dir, "default-build") == 0
    assert f"the default build is Live {NEW} (beta) (setting)" in capsys.readouterr().out
    assert _cli(index_dir, "default-build", "--clear") == 0
    assert read_default_setting(index_dir) is None and default_build(index_dir) == (OLD, "newest release")


def test_a_setting_without_an_index_is_refused_never_replaced(index_dir, capsys):
    assert _cli(index_dir, "default-build", "9.9.9") == 3  # not set: no index for it
    assert read_default_setting(index_dir) is None
    (index_dir / SETTINGS_FILE).write_text('{"default_build": "9.9.9"}')  # its index deleted later
    answer = api.lookup("Component", index_dir=index_dir)
    assert answer["status"] == "index_missing" and "default-build --clear" in answer["message"]
    assert api.lookup("Component", OLD, index_dir=index_dir)["status"] == "ok"  # a named build still works
    assert "no index" in api.list_builds(index_dir=index_dir, installs=[])["default_problem"]
    assert _cli(index_dir, "validate", ".") == 3
    assert _cli(index_dir, "default-build") == 3


def test_a_build_and_clear_exclude_each_other(index_dir):
    assert _cli(index_dir, "default-build", OLD, "--clear") == 2
    assert read_default_setting(index_dir) is None
