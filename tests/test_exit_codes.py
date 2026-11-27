"""One exit-code table for every command (plan 0001 Decision 61): the statuses map onto it, a
crash exits 5 and never 1, and the skill's scripts name only its codes."""

import re
from pathlib import Path

import pytest
from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp import cli
from ableton_remote_script_mcp.cli import EXIT_CODES, STATUS_EXIT, main

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "ableton-remote-scripts" / "scripts"
WRAPPERS = ("install.sh", "log.sh", "lookup.sh", "rig.sh", "validate.sh")  # they run the CLI


@pytest.fixture
def index_dir(tmp_path):
    return str(write_hand_index(tmp_path / "index"))


def test_every_status_has_a_code_of_the_table():
    assert set(STATUS_EXIT.values()) <= set(EXIT_CODES)
    assert sorted(EXIT_CODES) == [0, 1, 2, 3, 4, 5]


def _header_codes(script: Path) -> set[int]:
    """The codes the script's header names: `# Exit 0: …; 1: …` and its continuation lines."""
    header = []
    for line in script.read_text().splitlines()[1:]:
        if not line.startswith("#"):
            break
        header.append(line)
    text = " ".join(header)
    at = text.find("Exit")
    assert at >= 0, f"{script.name} names no exit codes"
    return {int(c) for c in re.findall(r"\b(\d): ", text[at:])}


@pytest.mark.parametrize("script", sorted(p.name for p in SCRIPTS.glob("*.sh") if not p.name.startswith("_")))
def test_the_skill_scripts_name_only_codes_of_the_table(script):
    codes = _header_codes(SCRIPTS / script)
    assert codes and codes <= set(EXIT_CODES), codes
    if script in WRAPPERS:
        assert 5 in codes and 0 in codes


def test_a_crash_exits_5_not_the_code_of_findings(index_dir, monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("a bug")
    monkeypatch.setattr(cli.api, "validate", boom)
    assert main(["--index-dir", index_dir, "validate", ".", "--build", OLD]) == 5
    err = capsys.readouterr().err
    assert "the tool failed on its own (RuntimeError: a bug)" in err and "Traceback" in err


def test_no_match_is_1_and_no_folder_is_2(index_dir, tmp_path):
    assert main(["--index-dir", index_dir, "search", "zzzqqq", "--build", OLD]) == 1
    assert main(["--index-dir", index_dir, "validate", str(tmp_path / "nope"), "--build", OLD]) == 2
    assert main(["--index-dir", index_dir, "check-names", str(tmp_path / "nope"), "--build", OLD]) == 2
    with pytest.raises(SystemExit) as usage:  # argparse's usage error
        main(["--index-dir", index_dir, "outline", "Fake_V3", "--section", "nope", "--build", OLD])
    assert usage.value.code == 2
    assert main(["--index-dir", index_dir, "validate", ".", "--build", "9.9.9"]) == 3


def test_a_missing_log_file_is_folder_missing(tmp_path, capsys):
    from ableton_remote_script_mcp.live_log import read_log

    assert read_log(tmp_path / "Log.txt")["status"] == "folder_missing"
    assert main(["log", "--log", str(tmp_path / "Log.txt"), "--json"]) == 2


def test_outline_of_a_missing_path_is_folder_missing(index_dir, tmp_path):
    """Review: a path that isn't there fell through to the search by name (`not_found`, exit 1)."""
    from ableton_remote_script_mcp import api

    answer = api.outline(str(tmp_path / "no_such_dir"), OLD, index_dir=index_dir)
    assert answer["status"] == "folder_missing" and "no script folder" in answer["message"]
    assert main(["--index-dir", index_dir, "outline", "./no_such_dir", "--build", OLD]) == 2
    assert main(["--index-dir", index_dir, "outline", "No_Such_Script", "--build", OLD]) == 1  # a name: no match


def test_an_unknown_search_kind_is_refused_in_the_api(index_dir):
    from ableton_remote_script_mcp import api

    answer = api.search("Component", OLD, kind="bogus", index_dir=index_dir)
    assert answer["status"] == "refused" and "kind must be one of" in answer["message"]


def test_the_rig_exits_3_without_pyyaml(index_dir, monkeypatch, tmp_path):
    """The rig extra is missing: 3 for `rig panel` too, as for `rig run` (Decision 61, the table)."""
    from ableton_remote_script_mcp.rig import session

    def no_yaml(*a, **k):
        raise ImportError("PyYAML is missing: uv sync --extra rig")
    monkeypatch.setattr(session, "prepare", no_yaml)
    assert main(["--index-dir", index_dir, "rig", "panel", str(tmp_path), "--build", OLD]) == 3


def test_a_default_setting_without_an_index_exits_3(index_dir, capsys):
    from ableton_remote_script_mcp.index_store import write_default_setting

    write_default_setting(Path(index_dir), "9.9.9")
    assert main(["--index-dir", index_dir, "default-build"]) == 3
    assert "9.9.9, which has no index" in capsys.readouterr().out
    assert main(["--index-dir", index_dir, "list", "builds"]) == 0  # the builds are there; it names the problem


ANSWERS_PAGE = Path(__file__).resolve().parent.parent / "docs" / "answers.md"


def _section(text: str, heading: str, until: str = "\n#") -> str:
    start = text.index(heading)
    end = text.find(until, start + len(heading))
    return text[start:end if end >= 0 else None]


def test_the_answers_page_names_every_status_and_code():
    """The page drifted from the tables once (the code review of Decision 61: `not_imported`
    and exit 4 were missing). Every status and every code of the table is on it (Decision 66)."""
    page = ANSWERS_PAGE.read_text()
    statuses = _section(page, "- `status`:", until="\n- `answer_version`")
    codes = _section(page, "### Exit codes")
    assert [s for s in STATUS_EXIT if f"`{s}`" not in statuses] == []
    assert [s for s in STATUS_EXIT if f"`{s}`" not in codes] == []
    assert [c for c in EXIT_CODES if not re.search(rf"\b{c}\b", codes)] == []
