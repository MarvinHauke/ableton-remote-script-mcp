"""Seam B: the validator's framework checks (plan 0001 step 8, Decision 43) over the hand-written
index. The clean v3 sample is our own and uses every form the rules read; each bad sample changes
one thing in it.
"""

import pytest
from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp import framework_checks
from ableton_remote_script_mcp.query import validate_script

FRAMEWORK_RULES = {"mapping-key", "element-name", "unknown-component", "specification-field",
                   "override-signature", "component-guard", "disconnect-base"}

INIT = """\
from ableton.v3.control_surface.control_surface import ControlSurface
from ableton.v3.control_surface.control_surface_specification import ControlSurfaceSpecification
from ableton.v3.control_surface.components import TransportComponent
from .elements import Elements
from .mappings import create_mappings


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    num_tracks = 8
    component_map = {"Transport": TransportComponent}
    create_mappings_function = create_mappings


class MySurface(ControlSurface):
    def __init__(self, *a, **k):
        super().__init__(Specification, *a, **k)

    def setup(self):
        super().setup()

    def receive_midi(self, data):
        super().receive_midi(data)

    def disconnect(self):
        self._extra = None
        super().disconnect()


def create_instance(c_instance):
    return MySurface(c_instance=c_instance)
"""

ELEMENTS = """\
from ableton.v3.control_surface.elements_base import ElementsBase


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.add_button(98, "Shift_Button")
        self.add_button(91, "Play_Button")
        self.add_button_matrix([range(36, 44)], "Pads")
        self.add_modified_control(control=self.pads, modifier=self.shift_button)
"""

MAPPINGS = """\
def create_mappings(control_surface):
    mappings = {}
    mappings["Transport"] = dict(play_button="play_button")
    mappings["Mixer"] = dict(volume_controls="pads_raw[0]", send_controls="pads")
    mappings["Session"] = dict(stop_all_clips_button="pads_with_shift_raw[1]", enable=False)
    mappings["Main_Modes"] = dict(
        cycle_mode_button="shift_button",
        session=dict(component="Session", clip_launch_buttons="pads"),
        mixer=dict(modes=[dict(component="Mixer", volume_controls="pads_with_shift")], behaviour=None),
        off=None,
    )
    mappings["Shift_Modes"] = dict(
        default=None,
        shift=dict(component="Main_Modes", session_button="play_button", priority=2),
        is_private=True,
    )
    return mappings
"""

@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


def check(tmp_path, index_dir, name="My_Script", init=INIT, elements=ELEMENTS, mappings=MAPPINGS):
    folder = tmp_path / "scripts" / name
    folder.mkdir(parents=True)
    for rel, text in {"__init__.py": init, "elements.py": elements, "mappings.py": mappings}.items():
        (folder / rel).write_text(text)
    answer = validate_script(folder, index_dir, OLD)
    assert answer["status"] == "ok", answer
    return answer


def found(answer):
    return [(f["rule"], f["severity"], f["file"], f["line"]) for f in answer["findings"]]


def skipped(answer):
    return [(n["rule"], n["what"]) for n in answer["not_checked"] if n["rule"] in FRAMEWORK_RULES]


def test_clean_v3_sample_has_no_findings(tmp_path, index_dir):
    answer = check(tmp_path, index_dir)
    assert answer["findings"] == []
    # MixerComponent answers set_send… itself (__getattr__): that key is listed, not judged
    assert skipped(answer) == [("mapping-key", "send_controls in mappings['Mixer'] (component Mixer)")]


def test_a_script_named_like_an_indexed_one_is_read_from_its_folder(tmp_path, index_dir):
    # the index's Fake_V3 has a field and mappings the clean sample does not have
    assert check(tmp_path, index_dir, name="Fake_V3")["findings"] == []


def test_mapping_keys(tmp_path, index_dir):
    mappings = (MAPPINGS.replace('play_button="play_button"', 'play_buton="play_button"')
                .replace('volume_controls="pads_raw[0]"', 'volume_controlz="pads_raw[0]"')
                .replace('cycle_mode_button="shift_button"', 'cycle_mode_buton="shift_button"')
                .replace('clip_launch_buttons="pads"', 'clip_launch_butons="pads"')
                .replace('session_button="play_button"', 'sesion_button="play_button"'))
    answer = check(tmp_path, index_dir, mappings=mappings)
    assert found(answer) == [("mapping-key", "error", "mappings.py", line) for line in (3, 4, 6, 6, 12)]
    messages = [f["message"] for f in answer["findings"]]
    assert "TransportComponent (component Transport) has no control `play_buton`" in messages[0]
    assert messages[0].endswith("(close: play_button)")
    assert "ModesComponent (modes component Main_Modes)" in messages[2]
    assert "SessionComponent (component Session (mode session))" in messages[3]
    assert "(close: session_button," in messages[4]  # a modes component's <mode>_button
    assert all("lookup class" in f["fix"] for f in answer["findings"])


def test_element_names(tmp_path, index_dir):
    mappings = MAPPINGS.replace('play_button="play_button"', 'play_button="play"').replace(
        '"pads_with_shift_raw[1]"', '"pads_with_shif_raw[1]"')
    answer = check(tmp_path, index_dir, mappings=mappings)
    assert found(answer) == [("element-name", "error", "mappings.py", 3), ("element-name", "error", "mappings.py", 5)]
    assert "builds no element `play`" in answer["findings"][0]["message"]
    assert "(close: pads_with_shift_raw," in answer["findings"][1]["message"]


def test_element_names_built_in_a_loop_are_not_checked(tmp_path, index_dir):
    elements = ELEMENTS + "        for i in range(4):\n            self.add_button(i, 'Knob_{}'.format(i))\n"
    mappings = MAPPINGS.replace('play_button="play_button"', 'play_button="knob_2"')
    answer = check(tmp_path, index_dir, elements=elements, mappings=mappings)
    assert answer["findings"] == []
    assert ("element-name", "play_button='knob_2'") in skipped(answer)


def test_unknown_components(tmp_path, index_dir):
    mappings = (MAPPINGS.replace('mappings["Transport"]', 'mappings["Transprt"]')
                .replace('component="Session", clip', 'component="Sesion", clip')
                .replace("off=None", "off=dict(behaviour=None, volume_controls='pads')"))
    answer = check(tmp_path, index_dir, mappings=mappings)
    assert found(answer) == [("unknown-component", "warning", "mappings.py", 3),
                             ("unknown-component", "error", "mappings.py", 6),
                             ("unknown-component", "error", "mappings.py", 6)]
    messages = [f["message"] for f in answer["findings"]]
    assert messages[0].endswith("(close: Transport)")
    assert "names component 'Sesion'" in messages[1] and "KeyError" in messages[1]
    assert "mode `off`" in messages[2] and "has no `component=`" in messages[2]


def test_component_map_that_is_not_a_literal_is_not_checked(tmp_path, index_dir):
    init = INIT.replace('component_map = {"Transport": TransportComponent}',
                        'component_map = dict(Transport=TransportComponent)')
    answer = check(tmp_path, index_dir, init=init,
                   mappings=MAPPINGS.replace('mappings["Transport"]', 'mappings["Transprt"]'))
    assert answer["findings"] == []
    assert ("unknown-component", "mappings['Transprt']") in skipped(answer)


def test_specification_field(tmp_path, index_dir):
    answer = check(tmp_path, index_dir, init=INIT.replace("num_tracks = 8", "num_trackz = 8"))
    assert found(answer) == [("specification-field", "warning", "__init__.py", 10)]
    assert answer["findings"][0]["message"].endswith("(close: num_tracks)")


@pytest.mark.parametrize("override, why", [
    ("def receive_midi(self):", "it takes at most 0 positional arguments, and the framework's always passes 1"),
    ("def receive_midi(self, midi_bytes, extra):", "it needs 2 positional arguments, and the framework's passes at most 1"),
    ("def receive_midi(self, midi_bytes, *, force):", "it needs the keyword argument force, which the framework's never passes"),
])
def test_override_signature(tmp_path, index_dir, override, why):
    init = INIT.replace("def receive_midi(self, data):\n        super().receive_midi(data)",
                        f"{override}\n        pass")
    answer = check(tmp_path, index_dir, init=init)
    assert found(answer) == [("override-signature", "error", "__init__.py", 22)]
    assert answer["findings"][0]["message"].endswith(why)
    assert "def receive_midi(self, midi_bytes)" in answer["findings"][0]["fix"]


@pytest.mark.parametrize("override", ["def receive_midi(self, *a, **k):", "def receive_midi(self, data=None):",
                                      "def __init__(self, c_instance, extra):"])
def test_override_signature_accepted(tmp_path, index_dir, override):
    init = INIT.replace("def receive_midi(self, data):\n        super().receive_midi(data)", f"{override}\n        pass")
    assert check(tmp_path, index_dir, init=init)["findings"] == []


FRAMEWORK_SURFACE = """\
from _Framework.ControlSurface import ControlSurface
from _Framework.ButtonElement import ButtonElement
from _Framework.SessionComponent import SessionComponent
from Fake_Lib.utils import make_button


class MySurface(ControlSurface):
    def __init__(self, c_instance):
        super().__init__(c_instance)
        self._shift = ButtonElement(True, 0, 0, 98)
        self._setup_session()
        if c_instance:
            self._play = make_button(0, 91)
        with self.component_guard():
            self._ok = ButtonElement(True, 0, 0, 99)
            self._setup_session()
        self._layer_owner = object()

    def _setup_session(self):
        self._session = SessionComponent(8, 1)

    def disconnect(self):
        self._session = None
"""


def test_component_guard(tmp_path, index_dir):
    files = {"__init__.py": "from .surface import MySurface\n\n\ndef create_instance(c_instance):\n"
                            "    return MySurface(c_instance)\n", "surface.py": FRAMEWORK_SURFACE}
    folder = tmp_path / "scripts" / "Fw_Script"
    folder.mkdir(parents=True)
    for rel, text in files.items():
        (folder / rel).write_text(text)
    answer = validate_script(folder, index_dir, OLD)
    # _Framework's ControlSurface.disconnect has no body in the hand index: no disconnect-base
    assert found(answer) == [("component-guard", "error", "surface.py", line) for line in (10, 11, 13)]
    messages = [f["message"] for f in answer["findings"]]
    assert messages[0].startswith("element ButtonElement is built in __init__ outside `with self.component_guard():`")
    assert "in _setup_session, line 20, which __init__ calls" in messages[1]
    assert "through make_button" in messages[2]


def test_v3_setup_and_elements_are_exempt(tmp_path, index_dir):
    init = INIT.replace("    def setup(self):\n        super().setup()",
                        "    def setup(self):\n        super().setup()\n        self._t = TransportComponent()")
    assert check(tmp_path, index_dir, init=init)["findings"] == []


def test_disconnect_base(tmp_path, index_dir):
    answer = check(tmp_path, index_dir, init=INIT.replace("        super().disconnect()\n", ""))
    assert found(answer) == [("disconnect-base", "warning", "__init__.py", 25)]
    assert "(ControlSurface.disconnect)" not in answer["findings"][0]["message"]  # EventObject has the body
    assert "EventObject.disconnect" in answer["findings"][0]["message"]


def test_other_python_lists_the_framework_checks_as_not_checked(tmp_path, index_dir, monkeypatch):
    monkeypatch.setattr(framework_checks, "LIVE_PYTHON", (3, 99))
    answer = check(tmp_path, index_dir, init=INIT.replace("num_tracks = 8", "num_trackz = 8"))
    assert answer["findings"] == []
    assert [(n["rule"], n["file"]) for n in answer["not_checked"]] == [("framework", ".")]
    assert "Python 3.99" in answer["not_checked"][0]["reason"]


def test_code_that_parses_but_does_not_compile_is_a_syntax_error(tmp_path, index_dir):
    answer = check(tmp_path, index_dir, mappings=MAPPINGS + "\nreturn None\n")
    assert found(answer) == [("syntax-error", "error", "mappings.py", 19)]
    assert "'return' outside function" in answer["findings"][0]["message"]
