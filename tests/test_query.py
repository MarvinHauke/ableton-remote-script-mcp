"""Seam B: the query core over a hand-written index (tests/hand_index.py)."""

import pytest
from hand_index import NEW, OLD, write_hand_index

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.query import check_names, get_class, search

COMP = "ableton.v3.control_surface.component.Component"
CM = "ableton.v2.control_surface.control.control.ControlManager"
EVENT = "ableton.v2.base.event.EventObject"
RING = "ableton.v3.control_surface.components.session_ring.SessionRingComponent"


@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


def one(answer):
    assert answer["status"] == "ok", answer
    [c] = answer["classes"]
    return c


def mro(c):
    return [e["name"] for e in c["mro"]]


def test_inherited_members_carry_their_origin_across_three_levels(index_dir):
    c = one(get_class("SessionRingComponent", index_dir, OLD))
    assert mro(c) == [f"{RING}", COMP, CM, EVENT, "builtins.object"]
    assert c["complete"] is True and c["mro_method"] == "c3"
    members = c["all_members"]
    assert members["set_offsets"]["origin"] == RING
    assert members["num_layers"]["origin"] == COMP
    assert members["control_notifications_enabled"]["origin"] == CM
    assert members["register_disconnectable"]["origin"] == EVENT
    # the nearest definition wins and names what it hides, nearest first
    assert members["__init__"]["origin"] == RING
    assert members["__init__"]["overrides"] == [COMP, CM]
    assert members["disconnect"]["origin"] == COMP and members["disconnect"]["overrides"] == [EVENT]
    assert c["live_build"] == OLD and c["confidence"] == "observed"


def test_bases_resolve_through_re_exports_to_the_defining_class(index_dir):
    c = one(get_class(COMP, index_dir, OLD))
    # imported as ableton.v3.control_surface.controls.ControlManager, a re-export of a re-export
    assert c["bases"][0]["resolved"] == "ableton.v3.control_surface.controls.ControlManager"
    assert c["bases"][0]["defined_in"] == CM and c["bases"][0]["status"] == "indexed"


def test_a_re_exported_name_finds_the_class(index_dir, capsys):
    answer = get_class("ableton.v3.control_surface.Component", index_dir, OLD)
    assert one(answer)["qualified_name"] == COMP
    assert answer["resolved_from"]["name"] == "ableton.v3.control_surface.Component"
    assert main(["--index-dir", str(index_dir), "lookup", "class", "ableton.v3.control_surface.Component"]) == 0
    assert f"is a re-export: {COMP}" in capsys.readouterr().out


def test_a_module_level_alias_is_followed(index_dir):
    assert one(get_class("ableton.v3.control_surface.BaseComponent", index_dir, OLD))["qualified_name"] == COMP


def test_a_base_from_a_star_import_resolves(index_dir):
    c = one(get_class("MixerStrip", index_dir, OLD))
    assert c["bases"][0]["resolved"] is None  # the module binds it only through `import *`
    assert c["bases"][0]["defined_in"] == "_Framework.ControlSurfaceComponent.ControlSurfaceComponent"
    assert c["all_members"]["set_enabled"]["origin"] == "_Framework.ControlSurfaceComponent.ControlSurfaceComponent"


def test_a_base_named_like_the_class_is_the_imported_one(index_dir):
    [c] = [c for c in get_class("DrumGroupComponent", index_dir, OLD)["classes"]
           if c["qualified_name"] == "Fake_Script.drums.DrumGroupComponent"]
    framework = "ableton.v3.control_surface.components.drum_group.DrumGroupComponent"
    assert mro(c)[:3] == ["Fake_Script.drums.DrumGroupComponent", framework, COMP]
    assert c["all_members"]["set_pads"]["overrides"] == [framework]


def test_a_nested_class_inherited_from_a_base_resolves_along_its_mro(index_dir):
    c = one(get_class("Fake_Script.display.Notifications.Device", index_dir, OLD))
    assert c["bases"][0]["defined_in"] == "ableton.v3.control_surface.display.notifications.Notifications.Device"
    assert c["all_members"]["bank"]["origin"] == "ableton.v3.control_surface.display.notifications.Notifications.Device"


def test_a_diamond_follows_c3(index_dir):
    c = one(get_class("Bottom", index_dir, OLD))
    d = "Fake_Script.diamond."
    assert mro(c)[:5] == [f"{d}Bottom", f"{d}Left", f"{d}Right", f"{d}Top", COMP]
    assert c["all_members"]["hello"]["origin"] == f"{d}Left"
    assert c["all_members"]["hello"]["overrides"] == [f"{d}Right", f"{d}Top"]
    assert c["all_members"]["right_only"]["origin"] == f"{d}Right"


def test_an_unresolved_base_marks_the_members_incomplete(index_dir, capsys):
    c = one(get_class("Orphan", index_dir, OLD))
    assert c["complete"] is False
    assert c["bases"][0]["status"] == "unresolved"
    assert c["mro"][1] == {"name": "Mystery", "status": "unresolved", "in_module": "Fake_Script.broken"}
    assert main(["--index-dir", str(index_dir), "lookup", "class", "Orphan", "--build", OLD]) == 0
    out = capsys.readouterr().out
    assert "Mystery (unresolved)" in out and "inherited members may be missing" in out


def test_a_base_from_the_live_module_is_external_and_names_its_proxy_model(index_dir):
    c = one(get_class("SongProxy", index_dir, OLD))
    assert c["mro"][1] == {"name": "Live.Song.Song", "status": "external", "proxy": "push3-helper:live_model.Live.Song.Song"}
    assert c["complete"] is True


def test_lookup_prints_inherited_members_grouped_by_origin(index_dir, capsys):
    assert main(["--index-dir", str(index_dir), "lookup", "class", "SessionRingComponent", "--build", OLD]) == 0
    out = capsys.readouterr().out
    assert f"mro:    {RING} -> {COMP} -> {CM} -> {EVENT} -> builtins.object" in out
    assert "  own members (3):" in out
    assert f"__init__(self, num_tracks=0, num_scenes=0, *a, **k)  (overrides {COMP}, {CM})" in out
    assert f"  inherited from {COMP} (" in out and "    layer  [property, settable]" in out
    assert main(["--index-dir", str(index_dir), "lookup", "class", "SessionRingComponent", "--build", OLD, "--own"]) == 0
    assert "inherited from" not in capsys.readouterr().out


def test_search_ranks_exact_name_then_prefix_then_words(index_dir):
    answer = search("SessionRing", index_dir, OLD)
    assert answer["status"] == "ok" and answer["live_build"] == OLD
    assert answer["results"][0]["qualified_name"] == RING
    assert answer["results"][0]["match"] == "name starts with"
    exact = search("Component", index_dir, OLD)["results"]
    assert exact[0]["qualified_name"] == COMP and exact[0]["match"] == "name"
    assert all(r["confidence"] == "observed" and r["live_build"] == OLD for r in exact)


def test_search_by_words_matches_names_and_docstrings(index_dir):
    by_name = search("session ring", index_dir, OLD)["results"]
    assert by_name[0]["qualified_name"] == RING and by_name[0]["match"] == "words in name"
    by_doc = search("red box", index_dir, OLD)["results"]
    assert [r["qualified_name"] for r in by_doc] == [RING]
    assert by_doc[0]["match"] == "words in name, module or docstring"


def test_search_finds_members_and_narrows_by_kind(index_dir):
    results = search("set_offsets", index_dir, OLD)["results"]
    assert results[0] == {**results[0], "kind": "method", "in_class": RING, "qualified_name": f"{RING}.set_offsets"}
    assert {r["kind"] for r in search("set", index_dir, OLD, kind="member")["results"]} == {"method"}
    assert [r["kind"] for r in search("Component", index_dir, OLD, kind="class")["results"]] == ["class"] * len(
        search("Component", index_dir, OLD, kind="class")["results"])


def test_search_ranks_framework_before_remote_scripts(index_dir):
    results = search("DrumGroupComponent", index_dir, OLD)["results"]
    assert [r["qualified_name"] for r in results[:2]] == [
        "ableton.v3.control_surface.components.drum_group.DrumGroupComponent",
        "Fake_Script.drums.DrumGroupComponent",
    ]


def test_not_found_names_the_build(index_dir, capsys):
    answer = get_class("NewThing", index_dir, OLD)
    assert answer == {"status": "not_found", "live_build": OLD,
                      "message": f"class 'NewThing' not found in Live {OLD}"}
    assert one(get_class("NewThing", index_dir, NEW))["live_build"] == NEW
    assert search("NewThing", index_dir, OLD)["message"] == f"'NewThing' not found in Live {OLD}"
    assert main(["--index-dir", str(index_dir), "search", "NewThing", "--build", OLD]) == 1
    assert f"not found in Live {OLD}" in capsys.readouterr().out


def test_the_newest_release_is_the_default_and_builds_differ(index_dir):
    """NEW is a beta (13.0b90): without a build the tools use the release (Decision 63)."""
    c = one(get_class("Component", index_dir))
    assert c["live_build"] == OLD
    assert c["all_members"]["is_enabled"]["params"][1]["default"] == "False"
    new = one(get_class("Component", index_dir, NEW))
    assert new["all_members"]["is_enabled"]["params"][1]["default"] == "True"


def test_index_missing(tmp_path, capsys):
    for answer in (get_class("Component", tmp_path / "none"), search("Component", tmp_path / "none"),
                   get_class("Component", tmp_path / "none", "12.4.16")):
        assert answer["status"] == "index_missing" and "build-index" in answer["message"]
    assert main(["--index-dir", str(tmp_path / "none"), "search", "Component"]) == 3


def test_classes_of_one_name_rank_module_level_live_and_re_exported_first(index_dir):
    """One ranking for `get_class` and `check_names` (plan 0001 Decision 58)."""
    names = [c["qualified_name"] for c in get_class("Device", index_dir, OLD)["classes"]]
    assert names == ["push3-helper:live_model.Live.Device.Device",
                     "ableton.v3.control_surface.display.notifications.Notifications.Device",
                     "Fake_Script.display.Notifications.Device"]
    exported = "ableton.v3.control_surface.components.note_editor_component.NoteEditorComponent"
    assert [c["qualified_name"] for c in get_class("NoteEditorComponent", index_dir, OLD)["classes"]] == [
        exported, "ableton.v3.control_surface.components.sequence.NoteEditorComponent"]
    answer = check_names(index_dir, OLD, names=["NoteEditorComponent", "NoteEditorComponent.set_pitches"])
    first, member = answer["names"]
    assert first["classes"][0] == exported
    # the first class of that name that has the member
    assert member["class"] == "ableton.v3.control_surface.components.sequence.NoteEditorComponent"
    # a bare name's holders in the same order: the re-exported class, though its key is longer
    assert check_names(index_dir, OLD, names=["set_steps"])["names"][0]["in"] == [
        exported, "ableton.v3.control_surface.components.sequence.NoteEditorComponent"]
