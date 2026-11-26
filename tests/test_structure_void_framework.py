"""Structure Void's framework pages as a `documented` cross-check (plan 0001 step 6, Decision 51).

The search index below is written here in the shape of the site's MkDocs search index (one
entry per heading, in page order); its names are our own or the hand index's, not copied from
the site. Nothing is fetched: `import_framework` gets a fake `fetch`.
"""

import json

import pytest
from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.query import get_class, structure_void_check
from ableton_remote_script_mcp.structure_void_framework import (
    compare_class,
    import_framework,
    load_framework,
    parse_search_index,
)

SITE = "https://midiremotescripts.structure-void.com"
COMP_PAGE = "reference/live12/ableton.v3.control_surface.component/"
COMP = "ableton.v3.control_surface.component.Component"


def e(location, title, text=""):
    return {"location": location, "title": title, "text": text}


SEARCH_INDEX = {"config": {}, "docs": [
    e("", "Home"),
    e(COMP_PAGE, "<code>ableton.v3.control_surface.component</code>"),
    e(COMP_PAGE + "#classes", "Classes"),
    e(COMP_PAGE + "#class-componentcontrolmanager", "class <code>Component(ControlManager)</code>",
      "<p>Bases: <code>ControlManager</code></p>"),
    e(COMP_PAGE + "#attributes", "Attributes", "<ul><li><code>num_layers = 0</code></li>"
      "<li><code>__doc__</code></li><li><code>only_on_the_page = 1</code></li></ul>"),
    e(COMP_PAGE + "#__init__", "<code>__init__(self, name, *a, **k)</code>"),
    e(COMP_PAGE + "#disconnect", "<code>disconnect(self)</code>"),
    e(COMP_PAGE + "#is_enabled", "<code>is_enabled(self)</code>"),  # the index has `explicit` too
    e(COMP_PAGE + "#layer", "<code>layer(self)</code>"),
    e(COMP_PAGE + "#layer-1", "<code>layer(self, value)</code>"),  # getter and setter
    e(COMP_PAGE + "#__on_thing_changed", "<code>__on_thing_changed(self)</code>"),
    e(COMP_PAGE + "#functions", "Functions"),
    e(COMP_PAGE + "#helper", "<code>helper(x, *rest)</code>"),
    # a class the index doesn't have, and a module it doesn't have
    e("reference/live12/ableton.v3.control_surface.components.session_ring/", "<code>…session_ring</code>"),
    e("reference/live12/ableton.v3.control_surface.components.session_ring/#classes", "Classes"),
    e("reference/live12/ableton.v3.control_surface.components.session_ring/#class-gone", "class <code>Gone</code>"),
    e("reference/live12/Not_Here/", "<code>Not_Here</code>"),
    # skipped: a runtime page, another Live version
    e("reference/live12/Live.Song.runtime/", "<code>Live.Song</code> (runtime)"),
    e("reference/live11/ableton.v3.control_surface.component/", "<code>…</code>"),
]}


def test_parse_reads_classes_members_attributes_and_functions():
    modules = parse_search_index(SEARCH_INDEX, "12")
    assert set(modules) == {"ableton.v3.control_surface.component",
                            "ableton.v3.control_surface.components.session_ring", "Not_Here"}
    comp = modules["ableton.v3.control_surface.component"]
    assert comp["url"] == f"{SITE}/{COMP_PAGE}"
    c = comp["classes"]["Component"]
    assert c["bases"] == ["ControlManager"] and c["url"].endswith("#class-componentcontrolmanager")
    assert c["members"]["__init__"] == {"kind": "method", "args": ["self", "name", "a", "k"]}
    assert c["members"]["num_layers"] == {"kind": "attribute"}
    assert c["members"]["layer"]["kind"] == "property" and c["members"]["layer"]["setter"]
    assert comp["functions"] == {"helper": {"args": ["x", "rest"]}}


def test_compare_names_what_each_side_has():
    page = parse_search_index(SEARCH_INDEX, "12")["ableton.v3.control_surface.component"]["classes"]["Component"]
    ours = {"qualname": "Component", "bases": [{"expr": "ControlManager"}], "keywords": {},
            "members": {"num_layers": {"kind": "attribute"}, "__events__": {"kind": "attribute"},
                        "__init__": {"kind": "method", "params": [{"name": n} for n in ("self", "name", "a", "k")]},
                        "disconnect": {"kind": "method", "params": [{"name": "self"}]},
                        "is_enabled": {"kind": "method", "params": [{"name": "self"}, {"name": "explicit"}]},
                        "layer": {"kind": "property", "setter": True},
                        "_Component__on_thing_changed": {"kind": "method", "params": [{"name": "self"}]},
                        "only_here": {"kind": "method", "params": [{"name": "self"}]}}}
    r = compare_class(ours, page)
    assert r["only_documented"] == ["only_on_the_page"]  # `__doc__` and `__events__` are left out
    assert r["only_observed"] == ["only_here"]  # `__on_thing_changed` is the mangled name
    assert r["args_differ"] == [{"name": "is_enabled", "observed": ["self", "explicit"], "documented": ["self"]}]
    assert "bases_differ" not in r and not r["agrees"]

    generic = {"qualname": "View", "bases": [{"expr": "Generic[ContentType]"}], "keywords": {"metaclass": "Meta"},
               "members": {}}
    assert compare_class(generic, {"bases": ["Generic", "ContentType", "Meta"], "members": {}, "url": "u"})["agrees"]
    moved = compare_class({"qualname": "X", "bases": [{"expr": "ScrollComponent"}], "members": {}},
                          {"bases": ["Component"], "members": {}, "url": "u"})
    assert moved["bases_differ"] == {"observed": ["ScrollComponent"], "documented": ["Component"]}


@pytest.fixture
def index_dir(tmp_path):
    index_dir = write_hand_index(tmp_path / "index")
    fetched = []

    def fetch(url):
        fetched.append(url)
        return json.dumps(SEARCH_INDEX)

    import_framework(index_dir, "12", fetch=fetch, log=lambda _: None)
    import_framework(index_dir, "12", fetch=fetch, log=lambda _: None)  # reuses the local copy
    assert fetched == [f"{SITE}/search/search_index.json"]
    return index_dir


def test_import_writes_a_documented_document(index_dir):
    doc = load_framework(index_dir, "12")
    assert doc["confidence"] == "documented" and doc["licence"] == "CC BY-NC-SA 4.0"
    assert doc["covers"] == "an unstated Live 12.x build"


def test_the_check_lists_differences_and_what_is_missing(index_dir):
    r = structure_void_check(index_dir, OLD)
    assert r["status"] == "ok" and r["live_build"] == OLD and r["classes_agree"] == 0
    [comp] = r["classes_differ"]
    assert comp["class"] == COMP and comp["args_differ"][0]["name"] == "is_enabled"
    assert r["classes_missing"] == [{"class": "ableton.v3.control_surface.components.session_ring.Gone",
                                     "source": f"{SITE}/reference/live12/"
                                               "ableton.v3.control_surface.components.session_ring/#class-gone",
                                     "reason": "no class of that name"}]
    assert [m["module"] for m in r["modules_missing"]] == ["Not_Here"]
    assert "Fake_Script.drums" in r["modules_not_on_pages"]
    assert structure_void_check(index_dir, OLD, under="Fake_Script")["pages"] == 0


def test_not_imported(tmp_path):
    index_dir = write_hand_index(tmp_path / "index")
    assert structure_void_check(index_dir, OLD)["status"] == "not_imported"
    assert main(["--index-dir", str(index_dir), "check-structure-void", "--build", OLD]) == 3


def test_lookup_shows_where_the_page_disagrees(index_dir, capsys):
    [c] = get_class(COMP, index_dir, OLD)["classes"]
    sv = c["structure_void"]
    assert sv["confidence"] == "documented" and not sv["agrees"]
    assert sv["only_documented"] == ["_Component__on_thing_changed", "only_on_the_page"]
    assert main(["--index-dir", str(index_dir), "lookup", "class", COMP, "--build", OLD]) == 0
    out = capsys.readouterr().out
    assert "Structure Void's page (an unstated Live 12.x build, documented) differs" in out
    assert "is_enabled: index (self, explicit), page (self)" in out
    assert main(["--index-dir", str(index_dir), "check-structure-void", "--build", OLD]) == 0
    out = capsys.readouterr().out
    assert "0 classes agree, 1 differ, 1 not found here, 1 modules not found here" in out
    assert "module not found here: Not_Here" in out
