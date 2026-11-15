"""Seam A: build-index over a fake Live bundle, then the CLI's answers over that index."""

import json

import pytest
from conftest import FAKE_BUILD

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.live_install import LiveInstall
from ableton_remote_script_mcp.query import get_class, list_builds

SPEC = "ableton.v3.control_surface.specification"
COMP = "ableton.v3.control_surface.component"
HELPER = "push3-helper:"


def build(app, index_dir):
    assert main(["--index-dir", str(index_dir), "build-index", "--app", str(app)]) == 0
    return json.loads((index_dir / f"live-{FAKE_BUILD}.json").read_text())


@pytest.fixture
def index(fake_live_app, tmp_path):
    return build(fake_live_app, tmp_path / "index")


@pytest.fixture
def statements(index, tmp_path):
    return json.loads((tmp_path / "index" / f"live-{FAKE_BUILD}.statements.json").read_text())


def test_index_records_build_and_source(index, fake_live_app):
    assert index["schema"] == 5
    assert index["live_build"] == FAKE_BUILD
    assert index["source"]["app"] == str(fake_live_app)
    assert index["source"]["bundle_version"].startswith(FAKE_BUILD)
    assert set(index["roots"]) == {"scripts", "push3-helper"}


def test_index_lists_the_python_modules_live_ships(index):
    assert index["python"] == {"path": "Contents/App-Resources/Python", "modules": {
        "functools": "lib", "json": "lib",
        "future": "site-packages/future-0.18.3", "past": "site-packages/future-0.18.3"}}


def test_index_covers_framework_scripts_and_push3_helper(index):
    modules = index["modules"]
    assert {
        "_Framework.ControlSurface",
        COMP,
        SPEC,
        "Fake_Mk1",
        "Fake_Mk1.Fake_Mk1",
        "Fake_Mk2",
        "_Shared",
        "Fake_Generic_User",
        f"{HELPER}live_model.Live.Song",
        f"{HELPER}ableton.v3.control_surface.component",
    } <= set(modules)
    assert not any("__pycache__" in m["source"] for m in modules.values())
    assert modules["ableton.v3.control_surface"]["package"] is True
    assert modules[SPEC]["source"] == "MIDI Remote Scripts/ableton/v3/control_surface/specification.pyc"
    assert modules[f"{HELPER}live_model.Live.Song"]["source"] == (
        "Helpers/Push3.app/Contents/Resources/python/live_model/Live/Song.pyc"
    )
    assert modules["ableton.v3.control_surface"]["imports"]["Component"] == f"{COMP}.Component"
    assert index["summary"] == {
        "packages": len(index["packages"]),
        "scripts": 3,
        "modules": len(modules),
        "classes": len(index["classes"]),
        "errors": 1,
    }


def test_classes_with_bases_and_every_fact_labelled(index):
    classes = index["classes"]
    framework = {k for k, c in classes.items() if c["root"] == "scripts" and c["module"].startswith(("_Framework", "ableton"))}
    assert framework == {
        "_Framework.ControlSurface.ControlSurface",
        f"{COMP}.Component",
        f"{COMP}.CompoundComponent",
        f"{COMP}.CompoundComponent.State",
        f"{SPEC}.Meta",
        f"{SPEC}.ControlSurfaceSpecification",
        f"{SPEC}.Deep",
        f"{SPEC}.Typed",
        f"{SPEC}.Unpacked",
    }  # HiddenInFunction is defined inside a function: not part of the module's API
    for c in classes.values():
        assert c["live_build"] == FAKE_BUILD
        assert c["confidence"] == "observed"
        assert c["source"].endswith(".pyc")

    def bases(key):
        return [(b["expr"], b["resolved"]) for b in classes[key]["bases"]]

    assert bases(f"{COMP}.CompoundComponent") == [("Component", f"{COMP}.Component")]
    assert bases(f"{SPEC}.Deep") == [
        ("Base", f"{COMP}.Component"),
        ("comp.CompoundComponent", f"{COMP}.CompoundComponent"),
        ("ableton.v3.Thing", "ableton.v3.Thing"),
    ]
    assert bases(f"{SPEC}.Typed") == [("Base", f"{COMP}.Component"), ("Generic[T]", "typing.Generic[T]")]
    # A base expression the extractor doesn't model keeps the class, flagged, without bases.
    assert classes[f"{SPEC}.Unpacked"]["bases_parsed"] is False
    assert classes[f"{SPEC}.Unpacked"]["bases"] == []
    assert classes[f"{SPEC}.Deep"]["bases_parsed"] is True
    spec = classes[f"{SPEC}.ControlSurfaceSpecification"]
    assert spec["bases"] == []  # metaclass= is a keyword, not a base
    assert spec["keywords"] == {"metaclass": "Meta"}
    assert bases("_Framework.ControlSurface.ControlSurface") == [("object", "builtins.object")]
    assert bases("Fake_Mk1.Fake_Mk1.FakeMk1") == [("ControlSurface", "_Framework.ControlSurface.ControlSurface")]


def test_methods_with_parameters_and_defaults(index):
    members = index["classes"][f"{COMP}.Component"]["members"]
    init = members["__init__"]
    assert init["kind"] == "method"
    assert init["params"] == [
        {"name": "self", "kind": "positional_or_keyword"},
        {"name": "name", "kind": "positional_or_keyword", "default": "''", "default_literal": True},
        {"name": "parent", "kind": "positional_or_keyword", "default": "None", "default_literal": True},
        {"name": "layer", "kind": "positional_or_keyword", "default": "DEFAULT_LAYER", "default_literal": False},
        {"name": "a", "kind": "var_positional"},
        {"name": "is_enabled", "kind": "keyword_only", "default": "True", "default_literal": True},
        {"name": "k", "kind": "var_keyword"},
    ]
    assert members["make"]["kind"] == "staticmethod"
    assert members["make"]["params"] == [
        {"name": "x", "kind": "positional_only"},
        {"name": "y", "kind": "positional_or_keyword", "default": "(1, 'a')", "default_literal": True},
    ]
    assert members["create"]["kind"] == "classmethod"
    assert members["create"]["params"][1] == {
        "name": "size", "kind": "keyword_only", "default": "8", "default_literal": True,
    }
    assert members["_on_value"]["decorators"] == ["listens('value')"]
    assert members["on_selected"]["kind"] == "method"  # a lambda bound in the class body
    assert members["disconnect"]["params"] == [{"name": "self", "kind": "positional_or_keyword"}]


def test_properties_and_class_attributes(index):
    members = index["classes"][f"{COMP}.Component"]["members"]
    assert members["is_enabled"]["kind"] == "property" and members["is_enabled"]["setter"] is True
    assert members["song"]["kind"] == "property" and members["song"]["setter"] is False

    def attr(name):
        m = members[name]
        assert m["kind"] == "attribute"
        return m["value"], m["value_literal"]

    assert attr("num_layers") == ("0", True)
    assert attr("canonical_parent") == ("None", True)
    assert attr("__events__") == ("('enabled',)", True)
    assert attr("sizes") == ("[1, 2, 3]", True)
    assert attr("layer_type") == ("DEFAULT_LAYER", False)
    assert "__module__" not in members and "__qualname__" not in members
    assert index["classes"][f"{SPEC}.ControlSurfaceSpecification"]["members"]["num_tracks"]["value"] == "8"
    spec = index["classes"]["Fake_Mk2.Specification"]["members"]
    assert spec["component_map"]["value"] == "{'Mixer': Component}"
    assert "State" not in index["classes"][f"{COMP}.CompoundComponent"]["members"]  # a class, not a member


def test_docstrings(index):
    component = index["classes"][f"{COMP}.Component"]
    assert component["docstring"] == "A unit of behaviour.\n\nSecond paragraph."
    assert component["members"]["__init__"]["docstring"] == "Make a component."
    assert "docstring" not in component["members"]["disconnect"]
    assert index["modules"][COMP]["docstring"] == "Fake v3 components, written for the tests."


def test_module_functions_and_attributes(index):
    module = index["modules"][COMP]["members"]
    assert module["listens"]["kind"] == "function"
    assert [p["name"] for p in module["listens"]["params"]] == ["event_name", "a"]
    assert module["DEFAULT_LAYER"] == {"kind": "attribute", "line": 3, "value": "None", "value_literal": True}
    assert index["modules"]["Fake_Mk1"]["members"]["create_instance"]["kind"] == "function"
    assert "FakeMk1" not in index["modules"]["Fake_Mk1"]["members"]  # an import, not a member


def test_packages_with_kind_and_framework(index):
    packages = index["packages"]

    def kind(key):
        return packages[key]["kind"], packages[key]["framework"]

    assert kind("_Framework") == ("framework", None)
    assert kind("ableton") == ("framework", None)
    assert kind("Fake_Mk1") == ("script", "_Framework")
    assert kind("Fake_Mk2") == ("script", "ableton.v3")
    assert kind("_Shared") == ("library", "_Framework")
    # imports no framework itself: takes the framework of the library it builds on
    assert kind("Fake_Generic_User") == ("script", "_Framework")
    assert packages["Fake_Generic_User"]["uses"] == ["_Shared"]
    assert packages["Fake_Mk2"]["framework_imports"] == {"ableton.v3": 2}  # two names bound


def test_push3_helper_is_namespaced_and_live_model_is_a_proxy(index):
    classes = index["classes"]
    helper_component = classes[f"{HELPER}{COMP}.Component"]
    assert helper_component["root"] == "push3-helper"
    assert "helper_only" in helper_component["members"]
    assert "helper_only" not in classes[f"{COMP}.Component"]["members"]  # two different copies
    song = classes[f"{HELPER}live_model.Live.Song.Song"]
    assert song["proxy_model"] is True
    assert song["proxy_of"] == "Live.Song.Song"
    assert song["members"]["file_path"]["value"] == "ValueProperty(writeable=False)"
    assert song["members"]["stop_playing"]["kind"] == "method"
    assert index["modules"][f"{HELPER}live_model.model"]["proxy_model"] is True
    assert index["packages"][f"{HELPER}live_model"]["proxy_model"] is True
    assert "proxy_model" not in helper_component


def test_unreadable_file_is_an_error_not_a_crash(index):
    assert index["errors"] == [
        {
            "source": "MIDI Remote Scripts/_Framework/Broken.pyc",
            "root": "scripts",
            "error": index["errors"][0]["error"],
        }
    ]
    assert "magic" in index["errors"][0]["error"] or "header" in index["errors"][0]["error"]


def test_lookup_class_answers_with_build_confidence_and_members(fake_live_app, tmp_path, capsys):
    index_dir = tmp_path / "index"
    build(fake_live_app, index_dir)
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "Component"]) == 0
    out = capsys.readouterr().out
    assert f"{COMP}.Component  [Live {FAKE_BUILD}, observed]" in out
    assert "__init__(self, name='', parent=None, layer=DEFAULT_LAYER, *a, is_enabled=True, **k)" in out
    assert "is_enabled  [property, settable]" in out
    assert "[staticmethod] make(x, /, y=(1, 'a'))" in out
    assert "[classmethod] create(cls, *, size=8)" in out
    assert "num_layers = 0" in out
    # the Remote Scripts' copy comes before the Push 3 helper's
    assert out.index(f"\n{HELPER}{COMP}.Component") > out.index(f"{COMP}.Component")


def test_lookup_class_shows_a_proxy_model(fake_live_app, tmp_path, capsys):
    index_dir = tmp_path / "index"
    build(fake_live_app, index_dir)
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "Song"]) == 0
    assert "proxy model of Live.Song.Song" in capsys.readouterr().out


def test_lookup_class_not_found(fake_live_app, tmp_path, capsys):
    index_dir = tmp_path / "index"
    build(fake_live_app, index_dir)
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "NoSuchThing"]) == 1
    assert f"not found in Live {FAKE_BUILD}" in capsys.readouterr().out


def test_lookup_class_index_missing(tmp_path, capsys):
    assert main(["--index-dir", str(tmp_path / "empty"), "lookup", "class", "Component"]) == 3
    out = capsys.readouterr().out
    assert "no API index" in out and "build-index" in out


def test_an_index_with_an_older_schema_asks_for_a_rebuild(fake_live_app, tmp_path):
    index_dir = tmp_path / "index"
    index = build(fake_live_app, index_dir)
    index["schema"] = 1
    (index_dir / f"live-{FAKE_BUILD}.json").write_text(json.dumps(index))
    answer = get_class("Component", index_dir)
    assert answer["status"] == "index_missing"
    assert "schema 1" in answer["message"] and "build-index" in answer["message"]
    listed = list_builds(index_dir)["builds"][0]
    assert listed["usable"] is False and "rebuild" in listed["problem"]


def test_list_builds(fake_live_app, tmp_path, capsys):
    index_dir = tmp_path / "index"
    not_installed = LiveInstall(app=tmp_path / "Ableton Live 13 Beta.app", live_build="13.0b99", bundle_version="13.0b99")
    assert list_builds(index_dir, [not_installed])["status"] == "index_missing"
    build(fake_live_app, index_dir)
    answer = list_builds(index_dir, [not_installed])
    assert answer["status"] == "ok"
    [entry] = answer["builds"]
    assert entry["live_build"] == FAKE_BUILD and entry["usable"] is True
    assert entry["summary"]["scripts"] == 3
    assert answer["installed_not_indexed"] == [
        {"live_build": "13.0b99", "app": str(not_installed.app), "beta": True}
    ]
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "list", "builds"]) == 0
    assert f"Live {FAKE_BUILD}  3 Remote Scripts" in capsys.readouterr().out


def test_list_builds_with_no_index(tmp_path, capsys):
    assert main(["--index-dir", str(tmp_path / "empty"), "list", "builds"]) == 3
    assert "no API index" in capsys.readouterr().out


def test_star_imports_are_recorded_and_resolve_a_base(fake_live_app, tmp_path):
    index_dir = tmp_path / "index"
    index = build(fake_live_app, index_dir)
    assert index["modules"]["Fake_Mk1.Shim"]["star_imports"] == ["_Framework.ControlSurface"]
    [c] = get_class("ShimmedSurface", index_dir)["classes"]
    assert c["bases"][0]["resolved"] is None  # bound only through `import *`
    assert c["bases"][0]["defined_in"] == "_Framework.ControlSurface.ControlSurface"
    assert c["all_members"]["disconnect"]["overrides"] == ["_Framework.ControlSurface.ControlSurface"]


def test_function_bodies_are_summarised_as_calls_and_stores(statements):
    """Schema 4: each function's top-level calls, with where their result goes, and its stores into
    attributes and subscripts; calls inside comprehensions say so."""
    assert statements["live_build"] == FAKE_BUILD
    statements = statements["classes"]["Fake_Mk1.Fake_Mk1.FakeMk1"]["_create_controls"]
    assert statements == [
        {"line": 8, "call": "partial", "args": ["make_button"], "kwargs": {"skin": "self._skin"},
         "target": "make_color_button"},
        {"line": 9, "call": "make_button", "args": ["0", "98"], "kwargs": {"name": "'Shift_Button'"},
         "target": "self._shift_button"},
        {"line": 10, "call": "make_color_button", "args": ["0", "36 + i"], "kwargs": {"name": "'Pad_%d' % (i + 1)"},
         "inside": "<listcomp>"},
        {"line": 10, "store": "self._pads", "value": "[… for … in range(8)]"},
        {"line": 12, "call": "dict", "args": [], "kwargs": {"volume_controls": "'faders'"}, "target": "mappings['Mixer']"},
        {"line": 13, "call": "self.component_guard", "args": [], "kwargs": {}},
        {"line": 14, "call": "SessionComponent", "args": ["8", "1"],
         "kwargs": {"layer": "Layer(clip_launch_buttons=self._pads)"}, "target": "self._session"},
        {"line": 16, "store": "self._mode", "value": "None", "under": ["if self._shift_button"]},
        {"line": 17, "call": "Layer", "args": [], "kwargs": {"volume_controls": "self._faders"},
         "target": "self.mixer().layer"},
        {"line": 18, "call": "super().__init__", "args": ["*a"], "kwargs": {"**": "k"}},
        {"line": 19, "call": "ButtonMatrixElement", "args": [], "kwargs": {"rows": "[self._pads]"}, "target": "return"},
    ]


def test_statements_live_in_their_own_file_and_the_api_index_has_none(index, statements):
    """The API index holds names and signatures only (user story 14); outlines read the second file."""
    assert not any("statements" in m for part in ("classes", "modules")
                   for fact in index[part].values() for m in fact["members"].values())
    assert statements["index_created"] == index["created"]
    assert "disconnect" not in statements["classes"].get(f"{COMP}.Component", {})  # `pass` has none
    assert statements["modules"]["Fake_Mk1"]["create_instance"]  # module functions too


def test_without_statements_outline_is_unavailable_and_says_why(fake_live_app, tmp_path, capsys):
    index_dir = tmp_path / "index"
    build(fake_live_app, index_dir)
    assert (index_dir / f"live-{FAKE_BUILD}.statements.json").exists()
    assert main(["--index-dir", str(index_dir), "build-index", "--app", str(fake_live_app), "--no-statements"]) == 0
    assert not (index_dir / f"live-{FAKE_BUILD}.statements.json").exists()  # a rebuild replaces both
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "list", "builds"]) == 0
    assert "no statement summaries" in capsys.readouterr().out
    assert main(["--index-dir", str(index_dir), "lookup", "class", "FakeMk1"]) == 0  # lookups still work
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "outline", "Fake_Mk1"]) == 3
    assert "no statement summaries for Live 12.4.99" in capsys.readouterr().out


def test_statements_say_what_they_run_under(statements):
    """Branches, loops and exception handlers, outermost first; the else of an `if` is its negation."""
    statements = statements["classes"]["Fake_Mk1.Fake_Mk1.FakeMk1"]["_create_transport"]
    under = [(st.get("call") or st.get("store"), st.get("under", [])) for st in statements]
    assert under == [
        ("make_button", ["if self.HAS_TRANSPORT"]),
        ("self._play", ["if not self.HAS_TRANSPORT"]),
        ("ping", ["if self.A or self.B"]),
        ("range", []),
        ("tick", ["for … in range(2)"]),
        ("risky", []),
        ("recover", ["on an exception", "except KeyError"]),
        ("done", []),
    ]
