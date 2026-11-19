"""Our own parts: the clip preset for a clip the sequencer creates, the grid resolutions, a pad
bank that selects the pad it plays, and the step sequencer with a note editor that draws the
playhead and the loop end, and loop buttons of one page each.

v3's `StepSequenceComponent` depends on a `grid_resolution` and its note editor on a
`sequencer_clip`, which the framework doesn't build: the control surface hands them in
(`APC_mini_drum_seq._get_additional_dependencies`).
"""

from ableton.v3.base import listens
from ableton.v3.control_surface.components import (
    DrumGroupComponent,
    GridResolutionComponent,
    LoopSelectorComponent,
    NoteEditorComponent,
    SequencerClip,
    StepSequenceComponent,
)
from ableton.v3.control_surface.components.grid_resolution import GRID_RESOLUTIONS
from ableton.v3.control_surface.skin import LiveObjSkinEntry
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


STEPS = 32  # the step buttons, one page


class DrumNoteEditorComponent(NoteEditorComponent):
    """v3's note editor with the playhead and the loop end drawn on the steps.

    Live's own playhead (v3's `PlayheadComponent`) sent nothing to the mk1's port in 12.4.16, on
    the step notes and on v3's default ones (tested, plan 0003 step 2), so this editor lights the
    playing step itself from the clip's `playing_position` (Decision 17). v3 shows the whole page
    of steps even past the loop end, where a press extends the loop (`extend_loop_for_region`);
    an empty step outside the loop is red here (Decision 10).
    """

    def __init__(self, *a, **k):
        self._playhead_step = None
        super().__init__(*a, **k)
        self.register_slot(self.song, self._update_playhead, "is_playing")
        # the sequencer clip notifies `length` when the loop start or end moves
        self.register_slot(self._sequencer_clip, self._update_editor_matrix, "length")

    def set_clip(self, clip):
        super().set_clip(clip)
        self.__on_playing_position_changed.subject = self._clip
        self.__on_playing_status_changed.subject = self._clip
        self._update_playhead()

    def _get_alternate_color_for_step(self, index, visible_steps):
        if index == self._playhead_step:
            return "NoteEditor.Playhead"
        if self._has_clip() and index in visible_steps:
            start = self._page_time + index * self.step_length
            outside = not self._clip.loop_start <= start < self._clip.loop_end
            if outside and not visible_steps[index].filter_notes(self._clip_notes):
                return "NoteEditor.StepOutsideLoop"
        return None

    def _playing_step(self):
        clip = self._clip
        if not (self._has_clip() and self.song.is_playing and clip.is_playing):
            return None
        index = int((clip.playing_position - self._page_time) // self.step_length)
        return index if 0 <= index < STEPS else None

    def _update_playhead(self):
        step = self._playing_step()
        if step != self._playhead_step:
            changed = {self._playhead_step, step} - {None}
            self._playhead_step = step
            self._update_steps(changed)

    def _update_steps(self, indices):
        """Only the steps that changed, so the moving playhead sends two LED messages a step."""
        if not (self.is_enabled() and indices):
            return
        visible_steps = self._visible_steps()
        for index, button in enumerate(self.matrix):
            if index in indices:
                button.color = LiveObjSkinEntry(
                    self._get_color_for_step(index, visible_steps), self._target_track.target_track
                )

    @listens("playing_position")
    def __on_playing_position_changed(self):
        self._update_playhead()

    @listens("playing_status")
    def __on_playing_status_changed(self):
        self._update_playhead()


class PageLoopSelectorComponent(LoopSelectorComponent):
    """v3's loop selector gives each button one bar. Here each button is one page of 32 steps
    (2 bars at 1/16), so track button N shows page N at every resolution; holding two buttons or
    double-clicking one sets the clip's loop in pages (plan 0003 Decision 24)."""

    @property
    def bar_length(self):
        return self._paginator.page_length


class DrumStepSequenceComponent(StepSequenceComponent):
    """v3's step sequencer with the note editor that draws the playhead, and pages on the loop
    buttons."""

    def __init__(self, *a, **k):
        super().__init__(
            *a,
            note_editor_component_type=DrumNoteEditorComponent,
            loop_selector_component_type=PageLoopSelectorComponent,
            **k,
        )
