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
        "class Specification(ControlSurfaceSpecification):\n    pass\n\n\n"
        "def create_instance(c_instance):\n    return ControlSurface(specification=Specification, c_instance=c_instance)\n")
    answer = validate_script(folder, index_dir, "12.4.16")
    assert answer["findings"] == [] and [n["what"] for n in answer["not_checked"] if n["rule"] == "unresolved-import"] == ["import Live"]
    (folder / "__init__.py").write_text("from ableton.v3.control_surface import NoSuchName\n")
    rules = [f["rule"] for f in validate_script(folder, index_dir, "12.4.16")["findings"]]
    assert rules == ["create-instance", "unresolved-import"]


@pytest.mark.local_live
def test_skill_template_is_clean_in_12_4_16(index_dir, tmp_path):
    template = Path(__file__).parent.parent / "skills/ableton-remote-scripts/assets/framework_template"
    folder = tmp_path / "Template_Check"
    shutil.copytree(template, folder)
    answer = validate_script(folder, index_dir, "12.4.16")
    assert answer["status"] == "ok" and answer["findings"] == [], answer["findings"]


@pytest.mark.local_live
def test_apc_mini_mk1_example_is_clean_in_12_4_16(index_dir):
    folder = Path(__file__).parent.parent / "examples/APC_mini_mk1"
    answer = validate_script(folder, index_dir, "12.4.16")
    assert answer["status"] == "ok" and answer["findings"] == [], answer["findings"]
