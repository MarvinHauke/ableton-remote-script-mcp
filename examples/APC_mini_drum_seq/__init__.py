"""A drum step sequencer for the Akai APC mini mk1 on `ableton.v3`, for Live 12.4 or later
(plan 0003). Select a track with a Drum Rack: the sequencer edits the clip that plays on it, or,
when none plays, its clip in the selected scene (v3's target track, plan 0003 Decision 22).

- Top four rows: 32 steps of the selected drum pad, step 1 top left. A press sets or clears a
  note (one step long, velocity 100); on an empty slot the first press creates a 2-bar clip
  named "Drum Seq". Green: a note.
- Bottom four rows, left half: a 4x4 bank of the Drum Rack's pads. A press plays the pad and
  selects it for the steps. Green: selected; yellow: a pad with a sound.

Device facts are in `elements.py`, LED values in `skin.py`.
"""

import logging

from ableton.v3.base import const
from ableton.v3.control_surface import (
    ControlSurface,
    ControlSurfaceSpecification,
    create_skin,
)
from ableton.v3.control_surface.components import StepSequenceComponent

from .components import DrumSequencerClip, PadBankComponent, create_grid_resolution
from .elements import Elements
from .mappings import create_mappings
from .skin import Skin

logger = logging.getLogger(__name__)


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    control_surface_skin = create_skin(skin=Skin)
    create_mappings_function = create_mappings
    component_map = {"Step_Sequence": StepSequenceComponent, "Drum_Group": PadBankComponent}


def create_instance(c_instance):
    """Live calls this once when the script is chosen as a Control Surface."""
    return APC_mini_drum_seq(specification=Specification, c_instance=c_instance)


class APC_mini_drum_seq(ControlSurface):
    def _get_additional_dependencies(self):
        """What v3's step sequencer depends on and the framework doesn't build. The framework
        calls each value to get the dependency, so each is wrapped in `const`."""
        dependencies = super()._get_additional_dependencies() or {}
        dependencies["grid_resolution"] = const(create_grid_resolution())
        dependencies["sequencer_clip"] = const(
            self.register_disconnectable(DrumSequencerClip(target_track=self._target_track))
        )
        return dependencies

    def setup(self):
        super().setup()
        # the pad bank's selected pad is the pitch the steps write
        self.component_map["Step_Sequence"].set_pitch_provider(self.component_map["Drum_Group"])
        logger.info("APC mini drum sequencer ready")
