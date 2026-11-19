"""Local-only checks against the installed Live 12.4.16; skipped when it is absent.

Each asserts a fact seen in 12.4.16 (plan 0001, Testing Decisions).
"""

import json
import shutil
from pathlib import Path

import pytest

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.live_install import read_install
from ableton_remote_script_mcp.query import (
    get_class,
    outline_script,
    search,
    validate_script,
)

LIVE_12_4_16 = Path("/Applications/Ableton Live 12 Suite.app")
SPEC = "ableton.v3.control_surface.control_surface_specification.ControlSurfaceSpecification"


@pytest.fixture(scope="module")
def live_12_4_16():
    try:
        install = read_install(LIVE_12_4_16)
    except (ValueError, OSError):
        pytest.skip("Ableton Live 12 Suite is not installed")
    if install.live_build != "12.4.16":
        pytest.skip(f"installed Live 12 Suite is {install.live_build}, not 12.4.16")
    return install


@pytest.fixture(scope="module")
def index_dir(live_12_4_16, tmp_path_factory):
    index_dir = tmp_path_factory.mktemp("index")
    assert main(["--index-dir", str(index_dir), "build-index", "--app", str(live_12_4_16.app)]) == 0
    return index_dir


@pytest.fixture(scope="module")
def index(index_dir):
    return json.loads((index_dir / "live-12.4.16.json").read_text())


@pytest.mark.local_live
def test_control_surface_specification_in_12_4_16(index_dir, capsys):
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "ControlSurfaceSpecification"]) == 0
    out = capsys.readouterr().out
    assert f"{SPEC}  [Live 12.4.16, observed]" in out
    assert "session_ring_selection_linking_type = SessionRingSelectionLinking" in out


@pytest.mark.local_live
def test_specification_fields_in_12_4_16(index):
    members = index["classes"][SPEC]["members"]
    assert members["session_ring_selection_linking_type"]["kind"] == "attribute"
    assert members["num_tracks"]["value"] == "8"


@pytest.mark.local_live
def test_generic_base_in_12_4_16(index_dir, capsys):
    # Seen in 12.4.16: DisplayLineElement(NotifyingControlElement, Generic[DisplayDataType])
    capsys.readouterr()
    assert main(["--index-dir", str(index_dir), "lookup", "class", "DisplayLineElement"]) == 0
    assert "Generic[DisplayDataType] = typing.Generic" in capsys.readouterr().out


@pytest.mark.local_live
def test_apc_mini_frameworks_in_12_4_16(index):
    packages = index["packages"]
    assert (packages["APC_mini"]["kind"], packages["APC_mini"]["framework"]) == ("script", "_Framework")
    assert (packages["APC_mini_mk2"]["kind"], packages["APC_mini_mk2"]["framework"]) == ("script", "ableton.v3")


@pytest.mark.local_live
def test_push3_helper_and_live_model_in_12_4_16(index):
    assert index["errors"] == []
    song = index["classes"]["push3-helper:live_model.Live.Song.Song"]
    assert song["proxy_model"] is True and song["proxy_of"] == "Live.Song.Song"
    assert "tempo" in song["members"]


@pytest.mark.local_live
def test_every_base_resolves_in_12_4_16(index_dir):
    # 12.4.16: through re-exports, star imports and nested classes inherited along the MRO
    # (MackieControlComponent, DefaultNotifications.Device), every base resolves
    for name in ("MackieControl.ChannelStrip.ChannelStrip", "Move.display.Notifications.Device",
                 "pushbase.drum_group_component.DrumGroupComponent"):
        [c] = get_class(name, index_dir)["classes"]
        assert c["complete"] is True and c["mro_method"] == "c3", name
        assert all(b["status"] != "unresolved" for b in c["bases"]), name


@pytest.mark.local_live
def test_inherited_members_in_12_4_16(index_dir):
    # seen in 12.4.16: the v3 SessionRingComponent, re-exported by v3.control_surface.components
    [c] = get_class("ableton.v3.control_surface.components.SessionRingComponent", index_dir)["classes"]
    members = c["all_members"]
    assert members["set_enabled"]["origin"] == "ableton.v3.control_surface.component.Component"
    assert members["register_disconnectable"]["origin"] == "ableton.v2.base.disconnectable.CompoundDisconnectable"
    assert members["disconnect"]["overrides"][-1] == "ableton.v2.base.disconnectable.Disconnectable"


@pytest.mark.local_live
def test_search_in_12_4_16(index_dir):
    first = search("SessionRingComponent", index_dir)["results"][0]
    assert first["qualified_name"] == "ableton.v3.control_surface.components.session_ring.SessionRingComponent"


@pytest.mark.local_live
def test_outline_of_apc_mini_mk2_in_12_4_16(index_dir):
    """A v3 Remote Script: Specification, framework component map, mappings, Elements."""
    o = outline_script("APC_mini_mk2", index_dir)
    assert (o["status"], o["framework"]) == ("ok", "ableton.v3")
    roles = {c["qualified_name"]: c["role"] for c in o["classes"]}
    assert roles["APC_mini_mk2.Specification"] == "specification"
    assert roles["APC_mini_mk2.APC_mini_mk2"] == "control surface"
    assert roles["APC_mini_mk2.elements.Elements"] == "elements"
    fields = {f["name"]: f for f in o["specification"]["fields"]}
    assert (fields["num_scenes"]["value"], fields["num_scenes"]["default"]) == ("8", "1")
    assert all(f["known"] for f in fields.values())
    cmap = {e["name"]: e for e in o["component_map"]}
    assert cmap["Session"]["defined_in"] == "ableton.v3.control_surface.components.session.SessionComponent"
    assert {n for n, e in cmap.items() if e["used_by_mappings"]} >= {"Mixer", "Session", "Drum_Group"}
    assert o["unknown_components"] == []
    mappings = {m["name"]: m for m in o["mappings"]["mappings"]}
    assert mappings["Mixer"]["controls"] == {"master_track_volume_control": "master_fader"}
    assert mappings["Pad_Modes"]["kind"] == "modes"
    assert mappings["Pad_Modes"]["modes"]["drum"] == {"component": "Drum_Group", "matrix": "drum_pads"}
    elements = {e["name"]: e for e in o["elements"]}
    assert set(elements) >= {"Shift_Button", "Clip_Launch_Buttons", "Drum_Pads", "Faders", "Master_Fader"}
    assert elements["Master_Fader"]["arguments"]["identifier"] == "56"


@pytest.mark.local_live
def test_outline_of_apc_mini_in_12_4_16(index_dir, capsys):
    """A _Framework Remote Script built on APC_Key_25 and _APC: elements, components, layers."""
    o = outline_script("APC_mini", index_dir)
    assert (o["status"], o["framework"], o["uses"]) == ("ok", "_Framework", ["APC_Key_25", "_APC"])
    assert o["specification"] is None
    assert [c["role"] for c in o["classes"]] == ["control surface"]
    elements = {e["name"]: e for e in o["elements"] if e["name"]}
    assert elements["Shift_Button"]["class"] == "_Framework.ButtonElement.ButtonElement"
    assert elements["Shift_Button"]["in"] == "APC_Key_25.APC_Key_25.APC_Key_25._create_controls"
    assert elements["Master_Volume"]["class"] == "_Framework.SliderElement.SliderElement"
    assert elements["Button_Matrix"]["class"] == "_Framework.ButtonMatrixElement.ButtonMatrixElement"
    # APC_Key_25 builds its transport only `if self.HAS_TRANSPORT:`; APC_mini sets it False
    assert elements["Play_Button"]["runs"] is False
    assert elements["Play_Button"]["decided_by"] == "HAS_TRANSPORT = False in APC_mini.APC_mini.APC_mini"
    assert "runs" not in elements["Shift_Button"]
    components = {e["class"].rsplit(".", 1)[-1] for e in o["components"]}
    assert {"SessionComponent", "MixerComponent", "TransportComponent"} <= components
    assert any(layer["controls"].get("volume_control") == "self._master_volume_control" for layer in o["layers"])
    assert main(["--index-dir", str(index_dir), "outline", "APC_mini"]) == 0
    assert "Shift_Button: make_button -> ButtonElement(" in capsys.readouterr().out


@pytest.mark.local_live
def test_live_python_and_a_clean_script_in_12_4_16(index_dir, index, tmp_path):
    modules = index["python"]["modules"]
    assert modules["json"] == "lib" and modules["future"].startswith("site-packages/future-")
    assert "ctypes" not in modules
    folder = tmp_path / "My_Script"
    folder.mkdir()
    (folder / "__init__.py").write_text(
        "from future.moves.itertools import zip_longest\n"
        "from ableton.v3.control_surface import ControlSurface, ControlSurfaceSpecification\n"
        "from _Framework.ButtonElement import ButtonElement\n"
        "import Live\n\n\n"
        "class Specification(ControlSurfaceSpecification):\n    identity_response_id_bytes = (0, 32, 41)\n\n\n"
        "def create_instance(c_instance):\n    return ControlSurface(specification=Specification, c_instance=c_instance)\n")
    answer = validate_script(folder, index_dir, "12.4.16")
    assert answer["findings"] == [] and [n["what"] for n in answer["not_checked"] if n["rule"] == "unresolved-import"] == ["import Live"]
    (folder / "__init__.py").write_text("from ableton.v3.control_surface import NoSuchName\n")
    rules = [f["rule"] for f in validate_script(folder, index_dir, "12.4.16")["findings"]]
    assert rules == ["create-instance", "unresolved-import"]


@pytest.mark.local_live
@pytest.mark.parametrize("name", ["framework_template", "v3_template"])
def test_skill_template_is_clean_in_12_4_16(index_dir, tmp_path, name):
    template = Path(__file__).parent.parent / "skills/ableton-remote-scripts/assets" / name
    folder = tmp_path / "Template_Check"
    shutil.copytree(template, folder)
    answer = validate_script(folder, index_dir, "12.4.16")
    assert answer["status"] == "ok" and answer["findings"] == [], answer["findings"]


@pytest.mark.local_live
@pytest.mark.parametrize("name", ["APC_mini_mk1", "Faderfox_UC4", "Rig_Identity", "APC_mini_drum_seq"])
def test_example_is_clean_in_12_4_16(index_dir, name):
    folder = Path(__file__).parent.parent / "examples" / name
    answer = validate_script(folder, index_dir, "12.4.16")
    assert answer["status"] == "ok" and answer["findings"] == [], answer["findings"]


@pytest.mark.local_live
def test_session_ring_warning_without_identity_in_12_4_16(index_dir, tmp_path):
    """The UC4 load test's first bug: no identity reply and the framework's ring, so no box."""
    folder = tmp_path / "Faderfox_UC4"
    shutil.copytree(Path(__file__).parent.parent / "examples/Faderfox_UC4", folder)
    init = folder / "__init__.py"
    init.write_text(init.read_text().replace(
        "    session_ring_component_type = SessionRingComponent", "    pass"))
    findings = validate_script(folder, index_dir, "12.4.16")["findings"]
    assert [(f["rule"], f["severity"]) for f in findings] == [("session-ring", "warning")]


@pytest.mark.local_live
def test_session_ring_warning_only_with_a_component_that_needs_the_ring_in_12_4_16(index_dir, tmp_path):
    """plan 0003 step 1: the drum sequencer without its mixer, track choice and own ring maps no
    component that depends on the session ring, so the missing identity reply draws no warning;
    a mixer section brings it back."""
    folder = tmp_path / "APC_mini_drum_seq"
    shutil.copytree(Path(__file__).parent.parent / "examples/APC_mini_drum_seq", folder)
    init = folder / "__init__.py"
    init.write_text("\n".join(line for line in init.read_text().splitlines()
                              if not line.lstrip().startswith("session_ring_component_type")))
    mappings = folder / "mappings.py"
    text = mappings.read_text()
    mappings.write_text(text[:text.index('    mappings["View_Control"]')] + "    return mappings\n")
    assert validate_script(folder, index_dir, "12.4.16")["findings"] == []
    mappings.write_text(mappings.read_text().replace(
        "    return mappings", '    mappings["Mixer"] = {"volume_controls": "faders"}\n    return mappings'))
    findings = validate_script(folder, index_dir, "12.4.16")["findings"]
    assert [(f["rule"], f["severity"]) for f in findings] == [("session-ring", "warning")]
    # a mode written as a dict literal counts too
    mappings.write_text(mappings.read_text().replace(
        'mappings["Mixer"] = {"volume_controls": "faders"}',
        'mappings["Fader_Modes"] = {"volume": {"component": "Mixer", "volume_controls": "faders"}}'))
    findings = validate_script(folder, index_dir, "12.4.16")["findings"]
    assert [(f["rule"], f["severity"]) for f in findings] == [("session-ring", "warning")]


@pytest.mark.local_live
def test_outline_of_a_script_folder(index_dir):
    answer = outline_script(str(Path(__file__).parent.parent / "examples" / "Faderfox_UC4"), index_dir, "12.4.16")
    assert answer["status"] == "ok" and answer["script"] == "Faderfox_UC4"
    assert answer["folder"].endswith("Faderfox_UC4") and answer["specification"]
    names = {m["name"] for m in answer["mappings"]["mappings"]}
    assert {"Mixer", "Session", "Quantization"} <= names


@pytest.mark.local_live
def test_uc4_controller_model(index_dir):
    """plan 0002 step 2: the rig's controller model of the UC4 example matches its elements.py."""
    from ableton_remote_script_mcp.rig.controller import controller_for_folder

    ctl, why = controller_for_folder(Path(__file__).parent.parent / "examples/Faderfox_UC4", index_dir, "12.4.16")
    assert ctl is not None, why
    assert len(ctl.elements) == 142 and not ctl.unresolved
    assert ctl.element("faders[0]").key == (0xBC, 40) and ctl.element("faders[0]").feedback
    assert ctl.element("crossfader").key == (0xBD, 48)
    assert ctl.element("bank_left_button").key == (0x9D, 123)
    assert ctl.element("quantization_encoder").relative
    assert ctl.matrices["active_buttons"][7] == "active_buttons[7]"
    assert ctl.element("active_buttons[7]").key == (0x9C, 111)


@pytest.mark.local_live
def test_drum_seq_controller_model(index_dir):
    """plan 0003 step 1: the rig reads the sequencer's grid rows, top row first."""
    from ableton_remote_script_mcp.rig.controller import controller_for_folder

    ctl, why = controller_for_folder(Path(__file__).parent.parent / "examples/APC_mini_drum_seq", index_dir, "12.4.16")
    assert ctl is not None, why
    assert len(ctl.elements) == 74 and not ctl.unresolved
    assert ctl.element("steps[0]").key == (0x90, 56) and ctl.element("steps[31]").key == (0x90, 39)
    assert ctl.element("pads[0]").key == (0x90, 24) and ctl.element("pads[15]").key == (0x90, 3)
    assert ctl.element("master_fader").key == (0xB0, 56)
    # step 4: scene buttons 1-4 are also the resolution buttons, a submatrix (no new elements)
    assert ctl.submatrices == {"resolution_buttons": [f"scene_buttons[{i}]" for i in range(4)]}


@pytest.mark.local_live
@pytest.mark.parametrize("name", ["Faderfox_UC4", "APC_mini_drum_seq"])
def test_example_check_file_names_its_elements(index_dir, name):
    from ableton_remote_script_mcp.rig.checks import (
        check_names,
        encode,
        load_check_file,
    )
    from ableton_remote_script_mcp.rig.controller import controller_for_folder

    checks = load_check_file(Path(__file__).parent.parent / "examples" / name / "checks.yaml")
    ctl, why = controller_for_folder(checks.script_folder, index_dir, checks.build)
    assert ctl is not None, why
    assert check_names(checks, ctl) == []
    for step in checks.steps:  # every value can be played on its element
        for item in step.send:
            if isinstance(item, tuple):
                encode(ctl.element(item[0]), item[1])


@pytest.mark.local_live
@pytest.mark.parametrize("name", ["Faderfox_UC4", "Rig_Identity", "APC_mini_drum_seq"])
def test_example_device_profiles_name_their_elements(index_dir, name):
    from ableton_remote_script_mcp.rig.controller import controller_for_folder
    from ableton_remote_script_mcp.rig.profile import check_profile_names, load_profile

    folder = Path(__file__).parent.parent / "examples" / name
    ctl, why = controller_for_folder(folder, index_dir, "12.4.16")
    assert ctl is not None, why
    assert check_profile_names(load_profile(folder / "device.yaml"), ctl) == []


def test_diff_to_another_indexed_build():
    """The diff 12.4.16 -> 13.0b25 over the user's own indexes (built with `build-index`).
    It asserts only that something was added or removed, never which names: Live 13 beta
    findings stay out of the repo (CLAUDE.md)."""
    from ableton_remote_script_mcp.diff import diff_builds
    from ableton_remote_script_mcp.index_store import default_index_dir, indexed_builds

    index_dir = default_index_dir()
    if not {"12.4.16", "13.0b25"} <= set(indexed_builds(index_dir)):
        pytest.skip("the 12.4.16 and 13.0b25 indexes are not built here")
    d = diff_builds("12.4.16", "13.0b25", index_dir)
    assert d["status"] == "ok" and (d["modules"]["added"] or d["modules"]["removed"])
    same = diff_builds("12.4.16", "12.4.16", index_dir)
    assert not any(same["modules"].values()) and not any(same["classes"].values())


def test_stubs_of_the_indexed_build(tmp_path):
    """`build-stubs` over the user's 12.4.16 index: every stub parses, the framework's and the
    Live module's classes are there. The stubs go to a temporary folder and are deleted."""
    import ast

    from ableton_remote_script_mcp.index_store import default_index_dir, indexed_builds
    from ableton_remote_script_mcp.query import build_stubs

    index_dir = default_index_dir()
    if "12.4.16" not in indexed_builds(index_dir):
        pytest.skip("the 12.4.16 index is not built here")
    answer = build_stubs(index_dir, "12.4.16", tmp_path / "stubs")
    assert answer["status"] == "ok" and answer["files"] > 1000
    for f in (tmp_path / "stubs").rglob("*.pyi"):
        ast.parse(f.read_text(encoding="utf-8"), str(f))
    ring = (tmp_path / "stubs" / "ableton/v3/control_surface/components/session_ring.pyi").read_text()
    assert "class SessionRingComponent(Component, Renderable):" in ring and "def set_offsets(" in ring
    assert "class Song" in (tmp_path / "stubs" / "Live/Song.pyi").read_text()
