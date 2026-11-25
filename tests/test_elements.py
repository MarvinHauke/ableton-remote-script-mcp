"""The Elements reader (plan 0001 Decision 57) over the hand-written index: one reading of a v3
Elements class for the validator, the rig and `check_names`."""

import sys

import pytest
from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp import api
from ableton_remote_script_mcp.elements import read_elements
from ableton_remote_script_mcp.framework_checks import compile_sources, overlay_index
from ableton_remote_script_mcp.outline import Outliner
from ableton_remote_script_mcp.query import _with_statements
from ableton_remote_script_mcp.validator import read_sources

pytestmark = pytest.mark.skipif(sys.version_info[:2] != (3, 11), reason="compiles the script as Live's Python")

ELEMENTS = """\
from ableton.v3.control_surface.elements_base import ElementsBase

NOTE = {"msg_type": 0}


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=2, **k)
        self.add_button(98, "Shift_Button", **NOTE)
        self.add_button_matrix([range(36, 40), range(40, 44)], "Scene Buttons", **NOTE)
        self.add_modified_control(control=self.scene_buttons, modifier=self.shift_button)
        self.add_button(7, name_of_button())
        self.lights = None
"""


@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


def _script(tmp_path, elements=ELEMENTS):
    folder = tmp_path / "My_Box"
    folder.mkdir()
    (folder / "__init__.py").write_text("")
    (folder / "elements.py").write_text(elements)
    return folder


def _read(folder, index_dir):
    index, _ = _with_statements(index_dir, OLD)
    findings, not_checked = [], []
    sources, _ = read_sources(folder, findings)
    overlay = overlay_index(index, folder.name, sources, compile_sources(sources, findings, not_checked), not_checked)
    return read_elements(Outliner(overlay, folder.name), sources)


def test_reads_names_and_midi_through_double_star_keywords(tmp_path, index_dir):
    """Finding 3: with `**NOTE` the statement summary has no name; the source has it."""
    read = _read(_script(tmp_path), index_dir)
    shift, scenes, modified, computed = read.built
    assert (shift.name, shift.msg_type, shift.channel, shift.identifier) == ("Shift_Button", "note", 2, 98)
    assert scenes.width == 4 and [i.identifier for i in scenes.items] == list(range(36, 44))
    assert scenes.items[5].name == "scene_buttons[5]" and scenes.names == ["scene_buttons", "scene_buttons_raw"]
    assert modified.method == "add_modified_control" and modified.names == []
    assert computed.why and "name_of_button()" in computed.why
    assert {"shift_button", "scene_buttons", "scene_buttons_raw", "scene_buttons_with_shift",
            "scene_buttons_with_shift_raw", "lights"} <= read.names
    assert read.computed  # name_of_button(): the set is not complete


def test_a_call_through_the_scripts_own_override_gives_its_name(tmp_path, index_dir):
    """`self.add_button(…)` where the Elements class overrides `add_button`: named by the
    framework's signature, as the validator read it before the reader; no MIDI from it."""
    elements = ELEMENTS + "\n    def add_button(self, *a, **k):\n        super().add_button(*a, **k)\n"
    read = _read(_script(tmp_path, elements), index_dir)
    shift = read.built[0]
    assert shift.name == "Shift_Button" and "shift_button" in read.names
    assert shift.identifier is None and "through the script's own add_button" in shift.why


def test_no_elements_class(tmp_path, index_dir):
    read = _read(_script(tmp_path, "X = 1\n"), index_dir)
    assert read.names is None and "no Elements class" in read.why


def test_check_names_knows_the_attributes_the_elements_class_builds(tmp_path, index_dir):
    """Finding 16: `self.scene_buttons` comes from `add_button_matrix(…, "Scene Buttons")`."""
    folder = _script(tmp_path)
    answer = api.check_names(folder, build=OLD, index_dir=index_dir)
    assert answer["status"] == "ok"
    assert "scene_buttons" not in [u["name"] for u in answer["unknown"]]


@pytest.mark.parametrize("files, why", [
    ({"elements.py": "from .consts import NOTE\nIDS = (7,)\n", "consts.py": "from .elements import NOTE\n"},
     "`NOTE` refers to itself"),  # modules that import it from each other
    ({"elements.py": "NOTE = 'x'\nIDS = (7,)\n"}, "`**NOTE` is not a dict"),
    ({"elements.py": "NOTE = {}\nIDS = 5\n"}, "`*IDS` is not a sequence"),
], ids=["cyclic-import", "not-a-dict", "not-a-sequence"])
def test_constants_it_cant_use_are_unresolved_not_a_crash(tmp_path, index_dir, files, why):
    body = ELEMENTS.replace('NOTE = {"msg_type": 0}\n', "").replace(
        'self.add_button(7, name_of_button())', 'self.add_button(*IDS, "Odd_Button")')
    folder = _script(tmp_path, files["elements.py"] + body)
    for rel, text in files.items():
        if rel != "elements.py":
            (folder / rel).write_text(text)
    read = _read(folder, index_dir)
    assert any(b.why and why in b.why for b in read.built), [b.why for b in read.built]
    assert api.check_names(folder, build=OLD, index_dir=index_dir)["status"] == "ok"
