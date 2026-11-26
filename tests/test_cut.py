"""The cut cuts declared collections only (plan 0001 Decision 62): never a record's own fields,
a list keeps its first record, and a named list says which records it dropped."""

from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp import api
from ableton_remote_script_mcp.answers import DROPPED_LISTED, bounded, tokens
from ableton_remote_script_mcp.cli import _cut_note


def _cls(i: int, members: int = 3, bases: int = 1) -> dict:
    return {"qualified_name": f"pkg.mod{i}.Thing", "bases": [f"pkg.Base{j}" for j in range(bases)],
            "all_members": {f"m{j}": {"kind": "method", "origin": "x" * 30} for j in range(members)}}


def test_only_declared_collections_are_cut():
    answer = {"status": "ok", "classes": [_cls(0, bases=200)], "notes": ["n" * 40] * 50}
    out = bounded(answer, 300, collections={"classes": "qualified_name", "classes[].all_members": None})
    assert len(out["classes"][0]["bases"]) == 200 and len(out["notes"]) == 50  # a record's fields, undeclared
    assert "cut" not in out or all(f["field"] != "classes[0].bases" for f in out["cut"]["fields"])


def test_a_list_keeps_its_first_record_and_cuts_inside_it():
    answer = {"status": "ok", "classes": [_cls(0, members=300), _cls(1, members=300)]}
    out = bounded(answer, 1000, collections={"classes": "qualified_name", "classes[].all_members": None})
    assert [c["qualified_name"] for c in out["classes"]] == ["pkg.mod0.Thing"]
    fields = {f["field"]: f for f in out["cut"]["fields"]}
    assert fields["classes"]["kept"] == 1 and fields["classes"]["dropped"] == ["pkg.mod1.Thing"]
    assert 0 < fields["classes[0].all_members"]["kept"] < 300 and "dropped" not in fields["classes[0].all_members"]
    assert tokens(out) <= 1000 and "asked for on its own" in out["cut"]["how"]
    assert len(answer["classes"][0]["all_members"]) == 300  # the caller's answer stays whole


def test_dropped_names_are_listed_up_to_a_limit():
    answer = {"status": "ok", "results": [{"qualified_name": f"pkg.r{i}", "text": "x" * 80} for i in range(300)]}
    out = bounded(answer, 2000, collections={"results": "qualified_name"})
    [f] = out["cut"]["fields"]
    assert len(f["dropped"]) == DROPPED_LISTED and f["more"] == 300 - f["kept"] - DROPPED_LISTED
    assert f["dropped"][0] == f"pkg.r{f['kept']}" and tokens(out) <= 2000
    assert "left out of results: pkg.r" in _cut_note(out) and f"and {f['more']} more" in _cut_note(out)


def test_lookup_names_the_classes_it_left_out(tmp_path):
    index_dir = write_hand_index(tmp_path / "index")
    whole = api.lookup("NoteEditorComponent", OLD, full=True, index_dir=index_dir)
    assert len(whole["classes"]) > 1
    small = api.lookup("NoteEditorComponent", OLD, max_tokens=200, index_dir=index_dir)
    [f] = [f for f in small["cut"]["fields"] if f["field"] == "classes"]
    assert f["dropped"] == [c["qualified_name"] for c in whole["classes"][f["kept"]:]]
    assert small["classes"][0]["bases"] == whole["classes"][0]["bases"]


def test_a_record_section_is_cut_only_in_its_lists(tmp_path):
    """Review: `specification` and `mappings` of an outline, and a diff's `members`, are records."""
    from ableton_remote_script_mcp.api import DIFF_CUTS, OUTLINE_CUTS

    record = {"class": "x" * 30, "framework_class": "y" * 30, "fields": [{"n": "f" * 40}] * 60}
    out = bounded({"status": "ok", "specification": record}, 300, collections=OUTLINE_CUTS)
    assert set(out["specification"]) == set(record) and 0 < len(out["specification"]["fields"]) < 60
    members = {"added": ["a" * 40] * 40, "removed": ["r" * 40] * 40, "changed": ["c" * 40] * 40}
    diff = {"status": "ok", "classes": {"added": [], "removed": [], "changed": [{"name": "pkg.T", "members": members}]}}
    out = bounded(diff, 400, collections=DIFF_CUTS)
    assert set(out["classes"]["changed"][0]["members"]) == {"added", "removed", "changed"}
    assert all(f["field"].startswith("classes.changed[0].members.") for f in out["cut"]["fields"])
