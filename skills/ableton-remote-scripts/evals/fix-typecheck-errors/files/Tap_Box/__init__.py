"""Tap_Box: a small controller with two buttons on ableton.v3, for Live 12.4.

- Note 60 (channel 1): Tap Tempo.
- Note 61 (channel 1): jumps the selected scene down by one and fires it.
"""

import logging

from ableton.v3.control_surface import (
    MIDI_NOTE_TYPE,
    ControlSurface,
    ControlSurfaceSpecification,
    ElementsBase,
)

from .components import SceneJumpComponent

logger = logging.getLogger(__name__)


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=0, **k)
        self.add_button(60, "Tap_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(61, "Jump_Button", msg_type=MIDI_NOTE_TYPE)


def create_mappings(control_surface):
    return {
        "Transport": {"tap_tempo_button": "tap_button"},
        "Scene_Jump": {"jump_button": "jump_button"},
    }


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    create_mappings_function = create_mappings
    component_map = {"Scene_Jump": SceneJumpComponent}


def create_instance(c_instance):
    return Tap_Box(specification=Specification, c_instance=c_instance)


class Tap_Box(ControlSurface):
    def setup(self):
        super().setup()
        logger.info("Tap_Box ready")
