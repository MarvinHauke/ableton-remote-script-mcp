"""Akai APC mini (mk1) Remote Script on `_Framework`, for Live 12.4.16 or later.

Device facts: Akai's APC mini communication protocol (documented), cross-checked against the MIDI
numbers of Ableton's own APC_mini script in the Live 12.4.16 API index (observed). Every number
below comes from there; see docs/feature-plans/milestone-1/apc-mini-mk1.md.

What it does:
- an 8 tracks x 8 scenes session box, drawn in Session View, starting at track 1, scene 1
- the 8x8 grid launches clips (top row = first scene of the box), with clip state LEDs
- the scene launch buttons launch the scenes of the box, with scene LEDs
- the track buttons stop the clips of their track, lit while it plays and blinking while the stop
  waits (a group track's button while any track in the group plays); with Shift held, track
  buttons 1-4 move the box up, down, left and right by one, each lit while its move is possible
- Shift + the bottom scene button stops all clips; Shift + the other buttons does nothing yet
- faders 1-8 set the volume of the tracks in the box, fader 9 the master volume
"""

from _Framework.ButtonElement import ButtonElement
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ComboElement import ComboElement
from _Framework.ControlSurface import OptimizedControlSurface
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE
from _Framework.Layer import Layer
from _Framework.MixerComponent import MixerComponent
from _Framework.Resource import SharedResource
from _Framework.SessionComponent import SessionComponent
from _Framework.SliderElement import SliderElement
from _Framework.SubjectSlot import subject_slot, subject_slot_group

CHANNEL = 0  # MIDI channel 1; channels count from 0

# Device facts
NUM_TRACKS = 8
NUM_SCENES = 8
# The hardware numbers the pads from the bottom row (0-7) up to the top row (56-63);
# the session wants the top row first.
GRID_NOTES = [[row * 8 + col for col in range(8)] for row in reversed(range(8))]
TRACK_NOTES = list(range(64, 72))  # the 8 buttons below the grid, left to right
SCENE_NOTES = list(range(82, 90))  # the 8 buttons right of the grid, top to bottom
SHIFT_NOTE = 98
FADER_CCS = list(range(48, 56))  # faders 1-8, left to right
MASTER_FADER_CC = 56  # fader 9, the rightmost

# Grid LED velocities
LED_OFF = 0
GRID_GREEN = 1
GRID_GREEN_BLINK = 2
GRID_RED = 3
GRID_RED_BLINK = 4
GRID_YELLOW = 5
# Scene (green) and track (red) button LED velocities
SCENE_ON = TRACK_ON = 1
SCENE_BLINK = TRACK_BLINK = 2


def make_button(note, name, **k):
    return ButtonElement(True, MIDI_NOTE_TYPE, CHANNEL, note, name=name, **k)


def make_fader(cc, name):
    return SliderElement(MIDI_CC_TYPE, CHANNEL, cc, name=name)


def _in_group(track, group):
    """Whether `track` sits in `group`, directly or in a nested group."""
    parent = track.group_track if track.is_grouped else None
    while parent is not None:
        if parent == group:
            return True
        parent = parent.group_track if parent.is_grouped else None
    return False


class GroupAwareSession(SessionComponent):
    """A session whose stop buttons also show group tracks.

    Live reports a playing clip only on the track that holds it, so the framework never lights a
    group track's stop button while the tracks in it play (seen in Live 12.4.16). Here a group's
    button is lit while any track in it plays and blinks while a stop waits on it or in it.
    """

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._listen_to_all_tracks()

    def _listen_to_all_tracks(self):
        tracks = list(self.song().tracks)
        self._on_any_playing_slot.replace_subjects(tracks)
        self._on_any_fired_slot.replace_subjects(tracks)

    def on_track_list_changed(self):
        super().on_track_list_changed()
        self._listen_to_all_tracks()
        self._update_stop_track_clip_buttons()

    @subject_slot_group("playing_slot_index")
    def _on_any_playing_slot(self, *a):
        self._update_stop_track_clip_buttons()

    @subject_slot_group("fired_slot_index")
    def _on_any_fired_slot(self, *a):
        self._update_stop_track_clip_buttons()

    def _update_stop_clips_led(self, index):
        buttons = self._stop_track_clip_buttons
        if buttons is not None and index < len(buttons) and buttons[index] is not None \
                and not buttons.owns_control_element(buttons[index]):
            return  # another component holds the button now (Shift is held): leave its LED alone
        tracks = self.tracks_to_use()
        track_index = index + self.track_offset()
        group = tracks[track_index] if track_index < len(tracks) else None
        members = [t for t in self.song().tracks if _in_group(t, group)] if group is not None else []
        if not (self.is_enabled() and buttons is not None and index < len(buttons)
                and buttons[index] is not None and members):
            super()._update_stop_clips_led(index)  # not a group track: the framework's own LED
            return
        value = None  # None means dark, as in the framework (its stop value starts as None)
        if group.fired_slot_index == -2 or any(t.fired_slot_index == -2 for t in members):
            value = self._stop_clip_triggered_value
        elif any(t.playing_slot_index >= 0 for t in members):
            value = self._stop_clip_value
        if value is None:
            buttons[index].turn_off()
        else:
            buttons[index].send_value(value)


class Unassigned(ControlSurfaceComponent):
    """Holds buttons that have no job, so that pressing them does nothing.

    Given Shift combos, it takes those buttons away from the session while Shift is held. It
    leaves their LEDs as they are: a scene relights its button only when it is given a different
    one (documented, decompiled 12.0 framework), so an LED darkened here would stay dark after
    Shift is let go."""

    def set_buttons(self, buttons):
        pass  # the layer hands the buttons over; holding them is the whole job


class BoxNavigation(ControlSurfaceComponent):
    """Moves the session box one track or scene per press, and lights a button while its move
    is possible.

    The session's own bank buttons repeat while held and stop only on the button's release. With
    Shift combos that release can go to the stop buttons instead (Shift let go first), and the
    box kept moving (seen in Live 12.4.16). One step per press has no such state.

    When Shift is pressed, a combo takes its button and its layer hands it to this component
    again (documented, decompiled 12.0 framework), so the setters light the buttons; when Shift is
    let go, the session takes them back and shows its stop LEDs.
    """

    def __init__(self, session, on_value=127, *a, **k):
        super().__init__(*a, **k)
        self._session = session
        self._on_value = on_value

    def set_up_button(self, button):
        self._on_up.subject = button
        self._update_lights()

    def set_down_button(self, button):
        self._on_down.subject = button
        self._update_lights()

    def set_left_button(self, button):
        self._on_left.subject = button
        self._update_lights()

    def set_right_button(self, button):
        self._on_right.subject = button
        self._update_lights()

    def _limits(self):
        session = self._session
        return (len(session.tracks_to_use()) - 1, len(self.song().scenes) - 1)

    def _update_lights(self):
        if not self.is_enabled():
            return
        session = self._session
        last_track, last_scene = self._limits()
        for slot, possible in ((self._on_up, session.scene_offset() > 0),
                               (self._on_down, session.scene_offset() < last_scene),
                               (self._on_left, session.track_offset() > 0),
                               (self._on_right, session.track_offset() < last_track)):
            button = slot.subject
            if button:  # a combo is true only while Shift is held and it owns its button
                button.send_value(self._on_value if possible else LED_OFF)

    @subject_slot("value")
    def _on_up(self, value):
        self._move(value, 0, -1)

    @subject_slot("value")
    def _on_down(self, value):
        self._move(value, 0, 1)

    @subject_slot("value")
    def _on_left(self, value):
        self._move(value, -1, 0)

    @subject_slot("value")
    def _on_right(self, value):
        self._move(value, 1, 0)

    def _move(self, value, tracks, scenes):
        session = self._session
        if value and self.is_enabled():  # on press only
            last_track, last_scene = self._limits()
            session.set_offsets(min(max(0, session.track_offset() + tracks), max(0, last_track)),
                                min(max(0, session.scene_offset() + scenes), max(0, last_scene)))
            self._update_lights()

    def update(self):
        super().update()
        self._update_lights()


class APC_mini_mk1(OptimizedControlSurface):
    # OptimizedControlSurface, not ControlSurface: with Shift combos the plain one resent most LEDs
    # on every Shift press (80-320 messages a second, about 90% unchanged) and the test controller
    # then lost button presses; with the optimized one every press arrived (tested in Live
    # 12.4.16). It applies the ownership changes once per incoming message (documented, decompiled
    # 12.0 framework); Ableton's APC_mini builds on it too.
    def __init__(self, c_instance):
        super().__init__(c_instance)
        with self.component_guard():
            self._create_elements()
            self._create_session()
            self._create_mixer()
        self.log_message("APC_mini_mk1 ready")

    def _create_elements(self):
        self._grid = ButtonMatrixElement(
            name="Grid",
            rows=[[make_button(note, f"Grid_{row}_{col}") for col, note in enumerate(notes)]
                  for row, notes in enumerate(GRID_NOTES)])
        # Keep the buttons in lists too: a matrix's get_button() returns a button only while the
        # matrix is held by a component, None before that (documented, decompiled 12.0 framework;
        # seen in Live 12.4.16: every combo built from get_button() wrapped None).
        self._scene_button_list = [
            make_button(note, f"Scene_{i}") for i, note in enumerate(SCENE_NOTES)]
        self._scene_buttons = ButtonMatrixElement(
            name="Scene_Buttons", rows=[self._scene_button_list])
        self._track_button_list = [
            make_button(note, f"Track_{i}") for i, note in enumerate(TRACK_NOTES)]
        self._track_buttons = ButtonMatrixElement(
            name="Track_Buttons", rows=[self._track_button_list])
        # Shift is a modifier of four combos at once, so its resource must be shared.
        self._shift = make_button(SHIFT_NOTE, "Shift", resource_type=SharedResource)
        # With Shift held, a combo takes its track button away from the stop buttons
        # (it grabs the button at a higher priority); without Shift they stop clips.
        up, down, left, right = (
            ComboElement(button, modifiers=[self._shift], name=name)
            for button, name in zip(self._track_button_list, ("Up", "Down", "Left", "Right")))
        self._up, self._down, self._left, self._right = up, down, left, right
        # Shift + the bottom scene button stops all clips, as on Ableton's own APC mini script
        self._stop_all = ComboElement(self._scene_button_list[7], modifiers=[self._shift],
                                      name="Stop_All")
        # Shift + the other track and scene buttons has no job yet: those combos do nothing
        self._shift_unassigned = ButtonMatrixElement(name="Shift_Unassigned", rows=[
            [ComboElement(button, modifiers=[self._shift], name=f"Shift_Track_{i}")
             for i, button in enumerate(self._track_button_list) if i >= 4]
            + [ComboElement(button, modifiers=[self._shift], name=f"Shift_Scene_{i}")
               for i, button in enumerate(self._scene_button_list[:-1])]])
        self._faders = [make_fader(cc, f"Fader_{i}") for i, cc in enumerate(FADER_CCS)]
        self._master_fader = make_fader(MASTER_FADER_CC, "Master_Fader")

    def _create_session(self):
        self._session = GroupAwareSession(NUM_TRACKS, NUM_SCENES, name="Session")
        # A track button is lit while its track plays and blinks while a (quantized) stop waits.
        # Set the values before the layer: the layer hands over the buttons at once and the
        # session lights them with these values (the stop value starts as None, documented).
        self._session.set_stop_clip_value(TRACK_ON)
        self._session.set_stop_clip_triggered_value(TRACK_BLINK)
        # Set the layer after construction: a layer passed to the constructor of a component that
        # starts enabled is never grabbed (tested in Live 12.4.16: no pad worked, no LED lit).
        self._session.layer = Layer(
                clip_launch_buttons=self._grid,
                scene_launch_buttons=self._scene_buttons,
                stop_track_clip_buttons=self._track_buttons,
                stop_all_clips_button=self._stop_all)
        self._navigation = BoxNavigation(self._session, on_value=TRACK_ON, name="Box_Navigation")
        self._unassigned = Unassigned(name="Shift_Unassigned")
        self._unassigned.layer = Layer(buttons=self._shift_unassigned)
        self._navigation.layer = Layer(up_button=self._up, down_button=self._down,
                                       left_button=self._left, right_button=self._right)
        for scene_index in range(NUM_SCENES):
            scene = self._session.scene(scene_index)
            scene.set_scene_value(SCENE_ON)
            scene.set_triggered_value(SCENE_BLINK)
            scene.set_no_scene_value(LED_OFF)
            for track_index in range(NUM_TRACKS):
                slot = scene.clip_slot(track_index)
                slot.set_stopped_value(GRID_YELLOW)
                slot.set_started_value(GRID_GREEN)
                slot.set_triggered_to_play_value(GRID_GREEN_BLINK)
                slot.set_recording_value(GRID_RED)
                slot.set_triggered_to_record_value(GRID_RED_BLINK)
                slot.set_record_button_value(LED_OFF)  # empty slot on an armed track: dark
        self.set_highlighting_session_component(self._session)

    def _create_mixer(self):
        self._mixer = MixerComponent(NUM_TRACKS, name="Mixer")
        self._session.set_mixer(self._mixer)  # faders follow the session box
        for index, fader in enumerate(self._faders):
            self._mixer.channel_strip(index).set_volume_control(fader)
        self._mixer.master_strip().set_volume_control(self._master_fader)

    def disconnect(self):
        # Turn off every LED the script lit, then let the framework release what it built.
        # reset() turns a lit LED off (tested in Live 12.4.16, Control Surface set to None). If the
        # user removes the output port instead, no script can reach the device: the LEDs stay lit.
        for matrix in (self._grid, self._scene_buttons, self._track_buttons):
            matrix.reset()
        super().disconnect()
