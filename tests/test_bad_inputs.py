"""Every API entry point answers a bad input with the status the exit-code table names (plan 0001
Decisions 61 and 66): a missing folder `folder_missing`, an unknown section or kind `refused`, a
build with no index `index_missing`. The code review of Decision 61 found `outline` of a missing
path answering `not_found` and the API's `search` taking an unknown kind: each was checked by
hand for one command. This test walks every entry point, so a new one fails here until it is
listed with its bad inputs."""

import pytest
from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp import api
from ableton_remote_script_mcp.cli import STATUS_EXIT

NO_BUILD = "9.9.9"
MISSING = "./no_such_folder"


def _cases():
    """(entry point, call, the status it must answer): `kw` is the index folder and options."""
    return {
        "lookup": [
            (lambda kw: api.lookup("Component", NO_BUILD, **kw), "index_missing"),
        ],
        "search": [
            (lambda kw: api.search("Component", NO_BUILD, **kw), "index_missing"),
            (lambda kw: api.search("Component", OLD, kind="bogus", **kw), "refused"),
        ],
        "outline": [
            (lambda kw: api.outline("Fake_V3", NO_BUILD, **kw), "index_missing"),
            (lambda kw: api.outline("Fake_V3", OLD, section="bogus", **kw), "refused"),
            (lambda kw: api.outline(MISSING, OLD, **kw), "folder_missing"),
        ],
        "validate": [
            (lambda kw: api.validate(".", NO_BUILD, **kw), "index_missing"),
            (lambda kw: api.validate(MISSING, OLD, **kw), "folder_missing"),
        ],
        "check_names": [
            (lambda kw: api.check_names(names=["Component"], build=NO_BUILD, **kw), "index_missing"),
            (lambda kw: api.check_names(MISSING, build=OLD, **kw), "folder_missing"),
        ],
        "list_builds": [
            (lambda kw: api.list_builds(installs=[], index_dir=kw["index_dir"] / "empty"), "index_missing"),
        ],
        "diff": [
            (lambda kw: api.diff(OLD, NO_BUILD, **kw), "index_missing"),
            (lambda kw: api.diff(NO_BUILD, OLD, **kw), "index_missing"),
        ],
    }


ENTRY_POINTS = [name for name in api.__all__ if callable(getattr(api, name))]


def test_every_entry_point_has_bad_inputs():
    assert sorted(_cases()) == sorted(ENTRY_POINTS)


@pytest.mark.parametrize("name", ENTRY_POINTS)
def test_a_bad_input_gets_the_status_of_the_table(name, tmp_path, monkeypatch):
    index_dir = write_hand_index(tmp_path / "index")
    monkeypatch.chdir(tmp_path)  # MISSING is relative to here, and not there
    for i, (call, status) in enumerate(_cases()[name]):
        answer = call({"index_dir": index_dir})
        assert answer["status"] == status, (name, i, answer)
        assert status in STATUS_EXIT and answer.get("message"), (name, i, answer)
