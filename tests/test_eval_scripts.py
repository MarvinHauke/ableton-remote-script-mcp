"""The skill evals' scoring scripts (plan 0001 step 9a) over the hand-written index.

`scripts/eval_names.py` sorts a script's attribute names and constructor keywords; Decision 42's
conclusion rests on it, so its known false negatives are pinned here. `scripts/eval_score.py`
reads traces and opens the sealed sandboxes.
"""

import json
import os
import sys
from pathlib import Path

import pytest
from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp.index_store import (
    attach_statements,
    load_index,
    load_statements,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import eval_names
import eval_score


@pytest.fixture(scope="module")
def hand(tmp_path_factory):
    index_dir = write_hand_index(tmp_path_factory.mktemp("index"))
    index = load_index(index_dir, OLD)
    statements = load_statements(index_dir, index)
    attach_statements(index, statements)
    return index, statements


def names_of(tmp_path: Path, hand, source: str) -> dict:
    folder = tmp_path / "Probe"
    folder.mkdir()
    (folder / "__init__.py").write_text(source)
    return eval_names.check(folder, *hand)


def unknown(result: dict) -> set[str]:
    return {u["name"] for u in result["unknown"]}


def test_invented_attribute_is_unknown(tmp_path, hand):
    result = names_of(tmp_path, hand, "def f(x):\n    return x.view.selected_clipz\n")
    assert "selected_clipz" in unknown(result)


def test_a_parameter_does_not_hide_an_attribute(tmp_path, hand):
    source = "def f(song, selected_clipz):\n    return song.selected_clipz\n"
    assert "selected_clipz" in unknown(names_of(tmp_path, hand, source))


def test_range_and_slice_names_are_not_python(tmp_path, hand):
    source = "def f(song):\n    song.start()\n    song.stop()\n    return song.real\n"
    assert {"start", "stop", "real"} <= unknown(names_of(tmp_path, hand, source))


def test_own_index_used_and_python(tmp_path, hand):
    source = """\
import logging

class Surface:
    def go(self, ring, items):
        self._shift = 1
        logging.made_up_by_logging
        items.append(ring.set_offsets)
        return self._shift, self.go, ring.not_a_framework_method
"""
    result = names_of(tmp_path, hand, source)
    assert result["unknown"] == []
    assert result["used_only"] == ["not_a_framework_method"]
    counts = result["attribute_counts"]
    assert counts["own"] == 2 and counts["index"] == 1 and counts["used"] == 1 and counts["python"] == 2


def test_keyword_to_a_class_whose_init_chain_ends_is_flagged(tmp_path, hand):
    source = "from _Framework.SessionComponent import SessionComponent\nSessionComponent(num_trackz=8)\n"
    result = names_of(tmp_path, hand, source)
    assert [k["keyword"] for k in result["kwargs_unknown"]] == ["num_trackz"]


def test_keyword_through_a_keeper_of_k_is_skipped(tmp_path, hand):
    # Elements passes **k to ElementsBase, which keeps it: any keyword may be fine.
    source = "from Fake_V3.elements import Elements\nElements(anything=1)\n"
    result = names_of(tmp_path, hand, source)
    assert result["kwargs_unknown"] == [] and result["kwargs_checked"] == 0


def test_keyword_to_a_class_with_a_base_outside_the_index_is_skipped(tmp_path, hand):
    source = "from Fake_Script.broken import Orphan\nOrphan(anything=1)\n"
    result = names_of(tmp_path, hand, source)
    assert result["kwargs_unknown"] == [] and result["kwargs_checked"] == 0


def test_stdlib_modules_are_named_not_imported(tmp_path, hand, monkeypatch):
    monkeypatch.setattr("importlib.import_module", lambda *a: pytest.fail("imported a module"))
    result = names_of(tmp_path, hand, "import antigravity\nantigravity.fly\n")
    assert result["attribute_counts"]["python"] == 1


def trace_with(tmp_path: Path, *inputs: dict) -> Path:
    trace = tmp_path / "trace.jsonl"
    events = [{"message": {"content": [{"type": "tool_use", "name": "Bash", "input": i}]}} for i in inputs]
    trace.write_text("\n".join(json.dumps(e) for e in events) + "\nnot json\n")
    return trace


def test_repo_reads(tmp_path):
    skill, repo = eval_score.SKILL_DIR, str(eval_score.REPO)
    clean = trace_with(tmp_path, {"command": f"cat {skill}/SKILL.md"}, {"command": "ls"})
    assert eval_score.repo_reads(clean) == []
    for bad in (f"cat {repo}/examples/x.py", f"cat {skill}/evals/uc4-mixer-v3/case.yaml"):
        assert len(eval_score.repo_reads(trace_with(tmp_path, {"command": bad}))) == 1
    try:
        rel = eval_score.REPO.relative_to(Path.home())
    except ValueError:
        pytest.skip("the repo is not under the home folder")
    assert len(eval_score.repo_reads(trace_with(tmp_path, {"command": f"ls ~/{rel}/docs"}))) == 1


def test_repo_reads_flags_the_cli_only_without_the_skill(tmp_path):
    trace = trace_with(tmp_path, {"command": "ableton-remote-script-mcp lookup class Component"})
    assert eval_score.repo_reads(trace, "with") == []
    assert len(eval_score.repo_reads(trace, "without")) == 1


def test_unseal_opens_sealed_folders_and_leaves_links(tmp_path):
    kept = tmp_path / "e-abc"
    cwd = kept / "sealed" / "home" / "cwd"
    (cwd / "Script").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (cwd / "link").symlink_to(outside)
    os.chmod(outside, 0o500)
    for path in (cwd / "Script", cwd, cwd.parent, kept / "sealed", kept):
        os.chmod(path, 0)
    try:
        assert eval_score.unseal(kept) == cwd
        assert (cwd / "Script").is_dir()
        assert outside.stat().st_mode & 0o777 == 0o500
    finally:
        os.chmod(outside, 0o700)


def test_kept_sandbox_only_in_the_temp_folder(tmp_path):
    assert eval_score.kept_sandbox(Path("/private/tmp/e-xyz/out/trace.jsonl")) == Path("/private/tmp/e-xyz")
    assert eval_score.kept_sandbox(tmp_path / "e-xyz" / "out" / "trace.jsonl") is None
    assert eval_score.kept_sandbox(Path("/private/tmp/other/out/trace.jsonl")) is None


def test_script_graders_get_the_computed_verdict():
    out = {"judge": {"06-validator-clean": False, "07-no-unknown-names": False, "01-launch": True},
           "scripts": [{"validator_findings": [], "unknown_names": ["x.py:3 a.b"]}]}
    eval_score._overwrite_script_graders(out)
    assert out["judge"] == {"06-validator-clean": True, "07-no-unknown-names": False, "01-launch": True}
