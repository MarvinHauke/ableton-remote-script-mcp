"""Seam B: the diff between two builds over the hand-written index (tests/hand_index.py)."""

import json

import pytest
from hand_index import NEW, OLD, write_hand_index

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.diff import describe_member, diff_builds

COMP = "ableton.v3.control_surface.component.Component"


@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


def test_a_changed_default_is_a_changed_member(index_dir):
    d = diff_builds(OLD, NEW, index_dir)
    assert d["status"] == "ok" and (d["from"], d["to"]) == (OLD, NEW) and d["confidence"] == "observed"
    [comp] = [c for c in d["classes"]["changed"] if c["name"] == COMP]
    assert comp["members"]["changed"] == [{"name": "is_enabled", "from": "method(self, explicit=False)",
                                           "to": "method(self, explicit=True)"}]
    assert not comp["members"]["added"] and not comp["members"]["removed"] and "bases" not in comp


def test_added_and_removed_modules_classes_and_packages(index_dir):
    d = diff_builds(OLD, NEW, index_dir)
    assert d["modules"]["added"] == ["ableton.v3.control_surface.new_thing"]
    assert "ableton.v3.control_surface.components.session_ring" in d["modules"]["removed"]
    assert d["classes"]["added"] == ["ableton.v3.control_surface.new_thing.NewThing"]
    assert "ableton.v3.control_surface.components.session_ring.SessionRingComponent" in d["classes"]["removed"]
    assert {p["name"] for p in d["packages"]["removed"]} >= {"_Framework", "Fake_Script"}
    assert not d["packages"]["added"]
    # unchanged classes are not listed, whatever their lines or docstrings
    assert [c["name"] for c in d["classes"]["changed"]] == [COMP]
    ableton = next(r for r in d["by_package"] if r["package"] == "ableton")
    assert ableton["modules_added"] == 1 and ableton["classes_changed"] == 1 and ableton["members_changed"] == 1


def test_under_narrows_to_a_package_or_module(index_dir):
    d = diff_builds(OLD, NEW, index_dir, under="ableton.v3.control_surface.component")
    assert [c["name"] for c in d["classes"]["changed"]] == [COMP]
    assert not d["modules"]["added"] and not d["classes"]["removed"] and not d["packages"]["removed"]
    assert diff_builds(OLD, NEW, index_dir, under="ableton.v3.control")["classes"]["changed"] == []
    same = diff_builds(OLD, OLD, index_dir)
    assert not same["by_package"] and not any(same["classes"].values())


def test_a_missing_build_is_index_missing(index_dir):
    d = diff_builds(OLD, "12.9.9", index_dir)
    assert d["status"] == "index_missing" and "12.9.9" in d["message"]


def test_describe_member():
    assert describe_member({"kind": "method", "params": [
        {"name": "self", "kind": "positional_or_keyword"}, {"name": "a", "kind": "var_positional"},
        {"name": "k", "kind": "var_keyword"}, {"name": "x", "kind": "keyword_only", "default": "1"}]}) \
        == "method(self, *a, **k, x=1)"
    assert describe_member({"kind": "property", "setter": True}) == "property (setter)"
    assert describe_member({"kind": "attribute", "value": "0"}) == "attribute = 0"


def test_cli_prints_counts_then_details(index_dir, capsys):
    base = ["--index-dir", str(index_dir), "diff", OLD, NEW]
    assert main(base) == 0
    out = capsys.readouterr().out
    assert f"Live {OLD} -> Live {NEW} (beta)" in out and "ableton: modules +1 -12" in out and "package removed: Fake_Script" in out
    assert main([*base, "--under", "ableton.v3"]) == 0
    out = capsys.readouterr().out
    assert f"class changed: {COMP}" in out and "~ is_enabled: method(self, explicit=False) -> method(self, explicit=True)" in out
    assert "module added: ableton.v3.control_surface.new_thing" in out
    assert main([*base, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["to"] == NEW
    assert main(["--index-dir", str(index_dir), "diff", OLD, "12.9.9"]) == 3
