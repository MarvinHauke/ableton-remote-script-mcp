"""Seam B: the outline of a Remote Script, over the hand-written index (tests/hand_index.py)."""

import pytest
from hand_index import NEW, OLD, write_hand_index

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.query import outline_script


@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


def outline(name, index_dir):
    answer = outline_script(name, index_dir, OLD)
    assert answer["status"] == "ok", answer
    assert answer["live_build"] == OLD and answer["confidence"] == "observed"
    return answer


def by(entries, key="name"):
    return {e[key]: e for e in entries}


def test_classes_have_roles_from_their_mro(index_dir):
    o = outline("Fake_V3", index_dir)
    assert (o["script"], o["kind"], o["framework"]) == ("Fake_V3", "script", "ableton.v3")
    roles = {c["qualified_name"]: c["role"] for c in o["classes"]}
    assert roles == {"Fake_V3.Specification": "specification", "Fake_V3.FakeV3": "control surface",
                     "Fake_V3.elements.Elements": "elements"}
    surface = by(o["classes"], "qualified_name")["Fake_V3.FakeV3"]
    assert surface["bases"] == [{"expr": "ControlSurface", "status": "indexed",
                                 "defined_in": "ableton.v3.control_surface.control_surface.ControlSurface"}]
    setup = by(surface["members"])["setup"]
    assert setup["overrides"] == "ableton.v3.control_surface.control_surface.ControlSurface"
    assert "statements" not in setup  # an outline shows no function bodies
    assert o["create_instance"] == ["return FakeV3(specification=Specification, c_instance=c_instance)"]


def test_specification_fields_with_framework_defaults(index_dir):
    spec = outline("Fake_V3", index_dir)["specification"]
    assert spec["class"] == "Fake_V3.Specification"
    fields = by(spec["fields"])
    assert fields["num_tracks"]["value"] == "8" and fields["num_tracks"]["default"] == "1"
    assert fields["num_tracks"]["known"] is True
    assert fields["led_brightness"]["known"] is False and "default" not in fields["led_brightness"]
    assert list(fields) == ["elements_type", "num_tracks", "component_map", "create_mappings_function",
                            "led_brightness"]


def test_component_map_merges_framework_defaults_and_the_script(index_dir):
    o = outline("Fake_V3", index_dir)
    cmap = by(o["component_map"])
    assert set(cmap) == {"Mixer", "Session", "Transport", "Looper", "Background", "Clock"}
    assert cmap["Mixer"]["from"] == "framework"
    assert cmap["Mixer"]["defined_in"] == "ableton.v3.control_surface.components.MixerComponent"
    assert cmap["Session"]["from"] == "script"
    assert cmap["Session"]["replaces_default"] == "partial(SessionComponent, snap=specification.snap)"
    assert cmap["Looper"]["defined_in"] is None  # LooperThing is not imported anywhere
    assert {n for n, e in cmap.items() if e["used_by_mappings"]} == {"Session"}
    # names added while the control surface sets up, by the framework and by the script
    assert (cmap["Background"]["from"], cmap["Background"]["set_in"]) == (
        "framework", "ableton.v3.control_surface.control_surface.ControlSurface.setup")
    assert cmap["Clock"]["from"] == "script"
    assert cmap["Clock"]["defined_in"] == "ableton.v3.control_surface.components.TransportComponent"
    assert o["unknown_components"] == ["Drum_Group"]


def test_mappings_connect_controls_to_elements_and_name_modes(index_dir):
    m = outline("Fake_V3", index_dir)["mappings"]
    assert m["function"] == "Fake_V3.mappings.create_mappings"
    entries = by(m["mappings"])
    assert entries["Session"]["kind"] == "component" and entries["Session"]["in_component_map"] is True
    assert entries["Session"]["controls"] == {"clip_launch_buttons": "pads"}
    modes = entries["Pad_Modes"]
    assert modes["kind"] == "modes"
    assert modes["controls"] == {"mode_selection_control": "shift_button"}
    assert modes["modes"] == {"session": {"component": "Session", "clip_launch_buttons": "pads"},
                              "drum": {"component": "Drum_Group", "matrix": "pads"}, "note": None}
    assert modes["options"] == {"priority": "HIGH_PRIORITY"}


def test_v3_elements_are_the_add_calls_with_named_arguments(index_dir):
    elements = by(outline("Fake_V3", index_dir)["elements"])
    assert set(elements) == {"Shift_Button", "Pads"}  # not self.not_a_framework_method(...)
    pads = elements["Pads"]
    assert pads["defined_by"] == "ableton.v3.control_surface.elements_base.ElementsBase.add_button_matrix"
    assert pads["arguments"] == {"identifiers": "[range(36, 44)]", "base_name": "'Pads'", "channels": "9"}
    assert (pads["in"], pads["line"]) == ("Fake_V3.elements.Elements.__init__", 9)


def test_framework_elements_through_factories_aliases_and_comprehensions(index_dir):
    o = outline("Fake_Fw", index_dir)
    assert o["specification"] is None and o["component_map"] == [] and o["mappings"] is None
    elements = by(o["elements"])
    shift = elements["Shift_Button"]
    assert shift["class"] == "_Framework.ButtonElement.ButtonElement"
    assert (shift["via"], shift["target"], shift["in"]) == ("make_button", "self._shift_button",
                                                            "Fake_Lib.base.LibSurface._create_controls")
    pad = elements["'Pad_%d' % i"]  # make_pad = partial(make_button, ...), called in a comprehension
    assert (pad["via"], pad["class"]) == ("make_pad", "_Framework.ButtonElement.ButtonElement")
    assert (pad["inside"], pad["target"]) == ("<listcomp>", "self._pads[…]")
    assert elements["Matrix"]["class"] == "_Framework.ButtonMatrixElement.ButtonMatrixElement"
    # the script's own override, which calls super(), and the library method it overrides both count
    assert elements["Stop_Button"]["in"] == "Fake_Fw.surface.FwSurface._create_controls"
    # ButtonElement(...) inside the factory make_button is not an element of its own
    assert set(elements) == {"Shift_Button", "'Pad_%d' % i", "Matrix", "Stop_Button", "Play_Button", "Mode_Button"}


def test_conditions_are_decided_by_the_scripts_class_attributes(index_dir, capsys):
    """`if self.HAS_TRANSPORT:` in the library; the script sets HAS_TRANSPORT = False."""
    o = outline("Fake_Fw", index_dir)
    elements, components = by(o["elements"]), by(o["components"])
    assert "under" not in elements["Shift_Button"] and "runs" not in elements["Shift_Button"]
    play = elements["Play_Button"]
    assert (play["under"], play["runs"]) == (["if self.HAS_TRANSPORT"], False)
    assert play["decided_by"] == "HAS_TRANSPORT = False in Fake_Fw.surface.FwSurface"
    # made in a method whose call site is conditional: the call site's condition counts
    transport = components["Transport"]
    assert (transport["returned_by"], transport["runs"]) == ("_create_transport", False)
    [layer] = [e for e in o["layers"] if e.get("within") == "TransportComponent"]
    assert layer["runs"] is False
    mode = elements["Mode_Button"]  # a call the outline can't evaluate: only under a condition
    assert mode["runs"] is None and "decided_by" not in mode
    assert main(["--index-dir", str(index_dir), "outline", "Fake_Fw", "--build", OLD]) == 0
    out = capsys.readouterr().out
    assert "NOT BUILT for this script (HAS_TRANSPORT = False in Fake_Fw.surface.FwSurface)" in out
    assert "only if self.has_modes()" in out


def test_framework_components_and_layers(index_dir):
    o = outline("Fake_Fw", index_dir)
    session = by(o["components"])["Session"]
    assert session["class"] == "_Framework.SessionComponent.SessionComponent"
    assert (session["name"], session["target"], session["returned_by"]) == ("Session", "self._session", "_create_session")
    layers = {(e.get("target") or e.get("within")): e for e in o["layers"]}
    assert layers["SessionComponent"]["controls"] == {"clip_launch_buttons": "self._matrix"}
    assert layers["session.layer"]["controls"] == {"stop_all_clips_button": "self._stop_button"}
    assert layers["session.layer"]["priority"] == "1"


def test_outline_prints_each_part(index_dir, capsys):
    assert main(["--index-dir", str(index_dir), "outline", "Fake_V3", "--build", OLD]) == 0
    out = capsys.readouterr().out
    assert "Fake_V3: Remote Script on ableton.v3  [Live 12.4.90, observed]" in out
    assert "  num_tracks = 8  # 1" in out
    assert "  led_brightness = 3  # not a framework field" in out
    assert "  Session: SessionComponent  -> ableton.v3.control_surface.components.SessionComponent" in out
    assert "      clip_launch_buttons <- pads" in out
    assert "  Pads: add_button_matrix(identifiers=[range(36, 44)], base_name='Pads', channels=9)" in out
    assert "Mixer" not in out.split("component map")[1].split("mappings")[0]  # unused default hidden
    assert main(["--index-dir", str(index_dir), "outline", "Fake_V3", "--build", OLD, "--all-components"]) == 0
    assert "  Mixer: MixerComponent" in capsys.readouterr().out


def test_not_found_framework_and_index_missing(index_dir, tmp_path, capsys):
    assert outline_script("Nope", index_dir, OLD)["message"] == "Remote Script 'Nope' not found in Live 12.4.90"
    assert outline_script("Fake_V3", index_dir, NEW)["status"] == "not_found"  # not in the other build
    framework = outline_script("_Framework", index_dir, OLD)
    assert framework["status"] == "not_found" and "framework package" in framework["message"]
    assert outline("fake_v3", index_dir)["script"] == "Fake_V3"  # case does not matter
    assert main(["--index-dir", str(tmp_path / "none"), "outline", "Fake_V3"]) == 3
    assert "build-index" in capsys.readouterr().out
