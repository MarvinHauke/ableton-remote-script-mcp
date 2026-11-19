"""Our own parts: the clip preset for a clip the sequencer creates, the grid resolutions, and a
pad bank that selects the pad it plays.

v3's `StepSequenceComponent` depends on a `grid_resolution` and its note editor on a
`sequencer_clip`, which the framework doesn't build: the control surface hands them in
(`APC_mini_drum_seq._get_additional_dependencies`).
"""

from ableton.v3.control_surface.components import (
    DrumGroupComponent,
    GridResolutionComponent,
    SequencerClip,
)
from ableton.v3.control_surface.components.grid_resolution import GRID_RESOLUTIONS
from ableton.v3.live import get_bar_length, liveobj_valid

# The clip preset (plan 0003 Decision 16): a clip created on an empty slot
CLIP_BARS = 2  # 8 beats in 4/4
CLIP_NAME = "Drum Seq"

# Scene buttons 1-4 choose these (step 2); the steps start at 1/16, so 32 steps are 2 bars in 4/4
RESOLUTIONS = tuple(r for r in GRID_RESOLUTIONS if not r.is_triplet)  # 1/32, 1/16, 1/8, 1/4
DEFAULT_RESOLUTION = 1  # 1/16


def create_grid_resolution():
    return GridResolutionComponent(resolutions=RESOLUTIONS, default_index=DEFAULT_RESOLUTION)


def has_drum_rack(track):
    """Whether a Drum Rack sits directly on the track (one inside another rack is not found)."""
    return liveobj_valid(track) and any(device.can_have_drum_pads for device in track.devices)


class DrumSequencerClip(SequencerClip):
    """The clip the steps edit: the selected track's clip in the selected scene. On an empty
    slot the first step press creates one from the clip preset, on a Drum Rack track only."""

    def create_clip(self, length=None):
        track = self._target_track.target_track
        if not has_drum_rack(track):
            return None
        super().create_clip(length=CLIP_BARS * get_bar_length())
        clip = self.clip
        if liveobj_valid(clip):
            clip.name = CLIP_NAME
            clip.looping = True
        return clip


class PadBankComponent(DrumGroupComponent):
    """v3's drum group selects a pad only while its select button is held, and by default its
    pads go to Live as notes without the script seeing them (`matrix_always_listenable=False`,
    observed in 12.4.16). This one listens to its pads and selects the pressed one, so a press
    plays the pad and picks the pitch the steps write."""

    def __init__(self, *a, **k):
        super().__init__(*a, matrix_always_listenable=True, **k)

    def _on_matrix_pressed(self, button):
        pad = self._pad_for_button(button)
        if liveobj_valid(pad):
            self._do_select_pad(pad, str(pad.name))
        super()._on_matrix_pressed(button)
