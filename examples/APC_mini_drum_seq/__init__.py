"""A drum step sequencer for the Akai APC mini mk1 on `ableton.v3`, for Live 12.4 or later
(plan 0003). Select a track with a Drum Rack: the sequencer edits the clip that plays on it, or,
when none plays, its clip in the selected scene (v3's target track, plan 0003 Decision 22).

- Top four rows: 32 steps of the selected drum pad, step 1 top left. A press sets or clears a
  note (one step long, velocity 100); on an empty slot the first press creates a 2-bar clip
  named "Drum Seq". Green: a note; yellow: the playhead; red: beyond the clip's loop end.
- Bottom four rows, left half: a 4x4 bank of the Drum Rack's pads. A press plays the pad and
  selects it for the steps. Green blinking: selected; yellow: a pad with a sound; red: held.
  Scene buttons 5-6 scroll the bank up and down by a row, lit when they can.
- A track without a Drum Rack directly on it: pads and steps dark, a step press does nothing.
- The selected MIDI track is armed for the pads (Live's auto-arm).
- Track buttons 1-8: pages of 32 steps. The page shown is on, the playhead's page blinks.
- Scene buttons 1-4: the steps' resolution, 1/32, 1/16 (at the start), 1/8, 1/4; the active one
  is on. Scene buttons 7-8: the previous and next track, lit when there is one.
- Faders 1-8: the volumes of tracks 1-8 (Live's box shows them); fader 9: the master volume.

Device facts are in `elements.py`, LED values in `skin.py`.
"""

import logging

from ableton.v3.base import const
from ableton.v3.control_surface import (
    ControlSurface,
    ControlSurfaceSpecification,
    create_skin,
)
from ableton.v3.control_surface.components import AutoArmComponent

from .components import (
    DrumSequencerClip,
    FaderRingComponent,
    DrumStepSequenceComponent,
    PadBankComponent,
    create_grid_resolution,
)
from .elements import Elements
from .mappings import create_mappings
from .skin import Skin

logger = logging.getLogger(__name__)


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    control_surface_skin = create_skin(skin=Skin)
    create_mappings_function = create_mappings
    session_ring_component_type = FaderRingComponent  # on without an identity reply: a box on tracks 1-8
    link_session_ring_to_track_selection = False  # the default (observed 12.4.16): the faders stay on 1-8
    component_map = {"Step_Sequence": DrumStepSequenceComponent, "Drum_Group": PadBankComponent}


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

    def drum_group_changed(self, drum_group):
        super().drum_group_changed(drum_group)
        # the steps work only on a Drum Rack track: read the clip again when the track's rack
        # changes (defensive: in 12.4.16 the framework first calls this right after setup())
        note_editor = getattr(self, "_note_editor", None)
        if note_editor is not None:
            note_editor.refresh_clip()

    def setup(self):
        super().setup()
        # the pad bank's selected pad is the pitch the steps write
        self.component_map["Step_Sequence"].set_pitch_provider(self.component_map["Drum_Group"])
        self._note_editor = self.component_map["Step_Sequence"].note_editor
        # Pads play only on an armed track. v3 builds its auto-arm only for a controller that
        # answers Live's identity request; the mk1 script doesn't ask, so it builds its own:
        # the selected MIDI track gets Live's implicit arm (plan 0003 Decision 26).
        self._drum_auto_arm = AutoArmComponent(is_enabled=True)  # not `_auto_arm`: the base uses it
        logger.info("APC mini drum sequencer ready")
