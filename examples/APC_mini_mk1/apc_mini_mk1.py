"""Akai APC mini (mk1) Remote Script on `_Framework`, for Live 12.4.16 or later.

Device facts: Akai's APC mini communication protocol (documented), cross-checked against the MIDI
numbers of Ableton's own APC_mini script in the Live 12.4.16 API index (observed). Every number
below comes from there; see docs/feature-plans/milestone-1/apc-mini-mk1.md.

What it does:
- an 8 tracks x 8 scenes session box, drawn in Session View, starting at track 1, scene 1
- the 8x8 grid launches clips (top row = first scene of the box), with clip state LEDs
- the scene launch buttons launch the scenes of the box, with scene LEDs
- the track buttons stop the clips of their track; with Shift held, track buttons 1-4 move the
  box up, down, left and right by one
- faders 1-8 set the volume of the tracks in the box, fader 9 the master volume
"""

from _Framework.ButtonElement import ButtonElement
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ComboElement import ComboElement
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE
from _Framework.Layer import Layer
from _Framework.MixerComponent import MixerComponent
from _Framework.Resource import SharedResource
from _Framework.SessionComponent import SessionComponent
from _Framework.SliderElement import SliderElement

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
# Scene (green) LED velocities
SCENE_ON = 1
SCENE_BLINK = 2


def make_button(note, name, **k):
    return ButtonElement(True, MIDI_NOTE_TYPE, CHANNEL, note, name=name, **k)


def make_fader(cc, name):
    return SliderElement(MIDI_CC_TYPE, CHANNEL, cc, name=name)


class APC_mini_mk1(ControlSurface):
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
        self._scene_buttons = ButtonMatrixElement(
            name="Scene_Buttons",
            rows=[[make_button(note, f"Scene_{i}") for i, note in enumerate(SCENE_NOTES)]])
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
        self._faders = [make_fader(cc, f"Fader_{i}") for i, cc in enumerate(FADER_CCS)]
        self._master_fader = make_fader(MASTER_FADER_CC, "Master_Fader")

    def _create_session(self):
        self._session = SessionComponent(
            NUM_TRACKS, NUM_SCENES, name="Session",
            layer=Layer(
                clip_launch_buttons=self._grid,
                scene_launch_buttons=self._scene_buttons,
                stop_track_clip_buttons=self._track_buttons,
                scene_bank_up_button=self._up,
                scene_bank_down_button=self._down,
                track_bank_left_button=self._left,
                track_bank_right_button=self._right))
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
        self._grid.reset()
        self._scene_buttons.reset()
        self._track_buttons.reset()
        super().disconnect()
