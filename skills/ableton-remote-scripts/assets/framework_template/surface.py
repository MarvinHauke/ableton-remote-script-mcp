"""<Controller name> Remote Script on `_Framework`, for Live 12.4 or later.

Device facts: <where the MIDI numbers come from: the manual's MIDI chart, page …, or the
controller's editor>. Every number below comes from there.
"""

from _Framework.ButtonElement import ButtonElement
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE
from _Framework.MixerComponent import MixerComponent
from _Framework.SessionComponent import SessionComponent
from _Framework.SliderElement import SliderElement

CHANNEL = 0  # MIDI channel 1; channels count from 0

# Device facts. Replace each None with the controller's numbers; never guess one.
NUM_TRACKS = 8
NUM_SCENES = 8
GRID_NOTES = None  # one list of notes per row, top row first: [[56, 57, …], …]
SCENE_NOTES = None  # one note per row, top first
FADER_CCS = None  # one CC per track fader
MASTER_FADER_CC = None
LEFT_NOTE = RIGHT_NOTE = UP_NOTE = DOWN_NOTE = None

# LED values the controller accepts (from the same source)
LED_OFF = 0
LED_CLIP_STOPPED = None
LED_CLIP_PLAYING = None
LED_CLIP_TRIGGERED = None
LED_CLIP_RECORDING = None


def make_button(note, name):
    return ButtonElement(True, MIDI_NOTE_TYPE, CHANNEL, note, name=name)


def make_fader(cc, name):
    return SliderElement(MIDI_CC_TYPE, CHANNEL, cc, name=name)


# Rename the class to the script's folder name: the framework starts each log message with the
# class name (documented: decompiled 12.0 framework), and `log.sh --script <Folder>` finds the
# messages by the folder name.
class Surface(ControlSurface):
    def __init__(self, c_instance):
        super().__init__(c_instance)
        # Elements and components get the services they need (MIDI out, registration) from the
        # control surface only inside component_guard; outside it they fail with a DependencyError.
        with self.component_guard():
            self._create_elements()
            self._create_session()
            self._create_mixer()
        self.log_message("ready")

    def _create_elements(self):
        self._grid = ButtonMatrixElement(
            name="Grid",
            rows=[[make_button(note, f"Grid_{row}_{col}") for col, note in enumerate(notes)]
                  for row, notes in enumerate(GRID_NOTES)])
        self._scene_buttons = ButtonMatrixElement(
            name="Scene_Buttons",
            rows=[[make_button(note, f"Scene_{row}") for row, note in enumerate(SCENE_NOTES)]])
        self._faders = [make_fader(cc, f"Fader_{i}") for i, cc in enumerate(FADER_CCS)]
        self._master_fader = make_fader(MASTER_FADER_CC, "Master_Fader")
        self._left, self._right = make_button(LEFT_NOTE, "Left"), make_button(RIGHT_NOTE, "Right")
        self._up, self._down = make_button(UP_NOTE, "Up"), make_button(DOWN_NOTE, "Down")

    def _create_session(self):
        self._session = SessionComponent(NUM_TRACKS, NUM_SCENES, name="Session")
        self._session.set_clip_launch_buttons(self._grid)
        self._session.set_scene_launch_buttons(self._scene_buttons)
        self._session.set_track_bank_buttons(self._right, self._left)
        self._session.set_scene_bank_buttons(self._down, self._up)
        for scene_index in range(NUM_SCENES):
            scene = self._session.scene(scene_index)
            for track_index in range(NUM_TRACKS):
                slot = scene.clip_slot(track_index)
                slot.set_stopped_value(LED_CLIP_STOPPED)
                slot.set_started_value(LED_CLIP_PLAYING)
                slot.set_triggered_to_play_value(LED_CLIP_TRIGGERED)
                slot.set_recording_value(LED_CLIP_RECORDING)
        self.set_highlighting_session_component(self._session)  # the box in Live's Session View

    def _create_mixer(self):
        self._mixer = MixerComponent(NUM_TRACKS, name="Mixer")
        self._session.set_mixer(self._mixer)  # the mixer follows the session box
        for index, fader in enumerate(self._faders):
            self._mixer.channel_strip(index).set_volume_control(fader)
        self._mixer.master_strip().set_volume_control(self._master_fader)

    def disconnect(self):
        # Turn off what the script lit, then let the framework release everything it built.
        self._grid.reset()
        self._scene_buttons.reset()
        super().disconnect()
