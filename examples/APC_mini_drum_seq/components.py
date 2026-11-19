"""Our own parts: the clip preset for a clip the sequencer creates, the grid resolutions, a pad
bank that selects the pad it plays, and the step sequencer with a note editor that draws the
playhead and the loop end, and loop buttons of one page each.

v3's `StepSequenceComponent` depends on a `grid_resolution` and its note editor on a
`sequencer_clip`, which the framework doesn't build: the control surface hands them in
(`APC_mini_drum_seq._get_additional_dependencies`).
"""

from ableton.v3.base import listens
from ableton.v3.control_surface.controls import ButtonControl
from ableton.v3.control_surface.components import (
    DrumGroupComponent,
    GridResolutionComponent,
    LoopSelectorComponent,
    NoteEditorComponent,
    PlayheadComponent,
    SequencerClip,
    SessionRingComponent,
    StepSequenceComponent,
)
from ableton.v3.control_surface.components.grid_resolution import GRID_RESOLUTIONS
from ableton.v3.control_surface.skin import LiveObjSkinEntry
from ableton.v3.live import get_bar_length, liveobj_valid

# The clip preset (plan 0003 Decision 16): a clip created on an empty slot
CLIP_BARS = 2  # 8 beats in 4/4
CLIP_NAME = "Drum Seq"

# Scene buttons 1-2 step through these, finer and coarser (Decision 29); the steps start at 1/16,
# so 32 steps are 2 bars in 4/4
RESOLUTIONS = tuple(r for r in GRID_RESOLUTIONS if not r.is_triplet)  # 1/32, 1/16, 1/8, 1/4
DEFAULT_RESOLUTION = 1  # 1/16


class StepResolutionComponent(GridResolutionComponent):
    """v3's grid resolution with a finer and a coarser button instead of one button per
    resolution (12.4.16 has no such buttons, observed; its `index` setter does the rest). Each is
    lit while there is a resolution to move to, like the scroll buttons."""

    finer_button = ButtonControl(color="NoteEditor.Resolution.Step",
                                 pressed_color="NoteEditor.Resolution.StepPressed")
    coarser_button = ButtonControl(color="NoteEditor.Resolution.Step",
                                   pressed_color="NoteEditor.Resolution.StepPressed")

    @finer_button.pressed
    def finer_button(self, _):
        self.index = max(self.index - 1, 0)

    @coarser_button.pressed
    def coarser_button(self, _):
        self.index = min(self.index + 1, len(self._resolutions) - 1)

    def _update_resolution_buttons(self):
        # the base calls this from its __init__ and whenever the index changes; `_resolutions`
        # is the base's own list
        super()._update_resolution_buttons()
        self.finer_button.enabled = self.index > 0
        self.coarser_button.enabled = self.index < len(self._resolutions) - 1


def create_grid_resolution():
    return StepResolutionComponent(resolutions=RESOLUTIONS, default_index=DEFAULT_RESOLUTION)


def has_drum_rack(track):
    """Whether a Drum Rack sits directly on the track (one inside another rack is not found)."""
    return liveobj_valid(track) and any(device.can_have_drum_pads for device in track.devices)


class FaderRingComponent(SessionRingComponent):
    """The framework's session ring: tracks 1-8 for the faders (the mixer reads its tracks from
    it) and the track pager of the scene buttons. It is built disabled and enabled only for a
    controller that answers Live's identity request, which the mk1 script doesn't ask for; so it
    enables itself, and Live draws a box around the faders' tracks. Nothing moves it."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.set_enabled(True)


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
    plays the pad (on an armed track) and picks the pitch the steps write; a held pad is red."""

    def __init__(self, *a, **k):
        self._held = set()  # the pads held now (their controls' ids)
        super().__init__(*a, matrix_always_listenable=True, **k)

    def set_matrix(self, matrix):
        self._held.clear()  # a release lost with the old matrix must not keep a pad red
        super().set_matrix(matrix)

    def _on_matrix_pressed(self, button):
        self._held.add(id(button))
        pad = self._pad_for_button(button)
        if liveobj_valid(pad):
            self._do_select_pad(pad, str(pad.name))
        super()._on_matrix_pressed(button)
        self._update_button_color(button)

    def _on_matrix_released(self, button):
        self._held.discard(id(button))
        super()._on_matrix_released(button)
        self._update_button_color(button)

    def _update_button_color(self, button):
        """Red while held: Live sends no feedback for a played pad here (12.4.16, tested)."""
        super()._update_button_color(button)
        if id(button) in self._held and liveobj_valid(self._drum_group_device):
            button.color = "DrumGroup.PadPressed"  # without a Drum Rack the pads stay dark


class DrumNoteEditorComponent(NoteEditorComponent):
    """v3's note editor with the playhead and the loop end drawn on the steps.

    Live's own playhead (v3's `PlayheadComponent`) sent nothing to the mk1's port in 12.4.16, on
    the step notes and on v3's default ones (tested, plan 0003 step 2), so this editor lights the
    playing step itself from the clip's `playing_position` (Decision 17). v3 shows the whole page
    of steps even past the loop end, where a press extends the loop (`extend_loop_for_region`);
    an empty step outside the loop is red here (Decision 10). On a track without a Drum Rack
    directly on it the steps have no clip, so they stay dark and a press does nothing
    (Decision 8). A step's time is page time + index x step length: no triplet resolutions
    (the resolution buttons offer none).
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

    def _has_clip(self):
        return super()._has_clip() and has_drum_rack(self._target_track.target_track)

    def refresh_clip(self):
        """Read the clip again: v3 reads the notes only when the clip changes, and with no Drum
        Rack `_has_clip` is false, so a rack added to the track would leave the steps empty.
        The control surface calls this when the track's Drum Rack changes."""
        clip = self._sequencer_clip.clip
        self.set_clip(None)
        self.set_clip(clip)

    def _on_pad_pressed(self, pad):
        # without a Drum Rack a step is inert: v3 would try to create a clip and drop its own
        if has_drum_rack(self._target_track.target_track):
            super()._on_pad_pressed(pad)

    def _update_editor_matrix(self):
        # a page or resolution change redraws every step: the playhead's step moves with it
        self._playhead_step = self._playing_step()
        super()._update_editor_matrix()

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
        return index if 0 <= index < self.step_count else None

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


class NoPlayheadComponent(PlayheadComponent):
    """Live's own playhead stays off: the note editor draws the playhead (Decision 25), and a
    later build where Live's would reach the mk1 must not draw a second one."""

    def update(self):
        super().update()
        self._playhead.clip = None


class DrumStepSequenceComponent(StepSequenceComponent):
    """v3's step sequencer with the note editor that draws the playhead, pages on the loop
    buttons, a finer and a coarser resolution button, and Live's own playhead off."""

    def __init__(self, *a, **k):
        super().__init__(
            *a,
            note_editor_component_type=DrumNoteEditorComponent,
            loop_selector_component_type=PageLoopSelectorComponent,
            playhead_component_type=NoPlayheadComponent,
            **k,
        )

    def set_finer_resolution_button(self, button):
        self._grid_resolution.finer_button.set_control_element(button)

    def set_coarser_resolution_button(self, button):
        self._grid_resolution.coarser_button.set_control_element(button)
