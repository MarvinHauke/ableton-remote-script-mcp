"""Seam A: build-index over a fake Live bundle, then lookup through the CLI."""

import json

from ableton_remote_script_mcp.cli import main
from conftest import FAKE_BUILD

SPEC = "ableton.v3.control_surface.specification"


def build(app, index_dir):
    assert main(["--index-dir", str(index_dir), "build-index", "--app", str(app)]) == 0
    return json.loads((index_dir / f"live-{FAKE_BUILD}.json").read_text())


def test_index_records_build_and_source(fake_live_app, tmp_path):
    index = build(fake_live_app, tmp_path / "index")
    assert index["schema"] == 1
    assert index["live_build"] == FAKE_BUILD
    assert index["source"]["app"] == str(fake_live_app)
    assert index["source"]["bundle_version"].startswith(FAKE_BUILD)


def test_index_records_framework_modules_only(fake_live_app, tmp_path):
    modules = build(fake_live_app, tmp_path / "index")["modules"]
    assert set(modules) == {
        "_Framework",
        "_Framework.ControlSurface",
        "ableton",
        "ableton.v3",
        "ableton.v3.control_surface",
        "ableton.v3.control_surface.component",
        SPEC,
    }
    assert modules["ableton.v3.control_surface"]["package"] is True
    assert modules[SPEC]["source"] == "MIDI Remote Scripts/ableton/v3/control_surface/specification.pyc"


def test_classes_with_bases_and_every_fact_labelled(fake_live_app, tmp_path):
    classes = build(fake_live_app, tmp_path / "index")["classes"]
    assert set(classes) == {
        "_Framework.ControlSurface.ControlSurface",
        "ableton.v3.control_surface.component.Component",
        "ableton.v3.control_surface.component.CompoundComponent",
        "ableton.v3.control_surface.component.CompoundComponent.State",
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

    assert bases("ableton.v3.control_surface.component.CompoundComponent") == [
        ("Component", "ableton.v3.control_surface.component.Component")
    ]
    assert bases(f"{SPEC}.Deep") == [
        ("Base", "ableton.v3.control_surface.component.Component"),
        ("comp.CompoundComponent", "ableton.v3.control_surface.component.CompoundComponent"),
        ("ableton.v3.Thing", "ableton.v3.Thing"),
    ]
    assert bases(f"{SPEC}.Typed") == [
        ("Base", "ableton.v3.control_surface.component.Component"),
        ("Generic[T]", "typing.Generic[T]"),
    ]
    # A base expression the extractor doesn't model keeps the class, flagged, without bases.
    assert classes[f"{SPEC}.Unpacked"]["bases_parsed"] is False
    assert classes[f"{SPEC}.Unpacked"]["bases"] == []
    assert classes[f"{SPEC}.Deep"]["bases_parsed"] is True
    spec = classes[f"{SPEC}.ControlSurfaceSpecification"]
    assert spec["bases"] == []  # metaclass= is a keyword, not a base
    assert spec["keywords"] == {"metaclass": "Meta"}
    assert bases("_Framework.ControlSurface.ControlSurface") == [("object", "builtins.object")]


def test_unreadable_file_is_an_error_not_a_crash(fake_live_app, tmp_path):
    errors = build(fake_live_app, tmp_path / "index")["errors"]
    assert [e["source"] for e in errors] == ["MIDI Remote Scripts/_Framework/Broken.pyc"]


def test_lookup_class_answers_with_build_and_confidence(fake_live_app, tmp_path, capsys):
    index_dir = tmp_path / "index"
    build(fake_live_app, index_dir)
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "ControlSurfaceSpecification"]) == 0
    out = capsys.readouterr().out
    assert f"{SPEC}.ControlSurfaceSpecification" in out
    assert f"[Live {FAKE_BUILD}, observed]" in out


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
