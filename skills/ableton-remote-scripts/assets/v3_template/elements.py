"""The controller's controls as elements.

Device facts: <where the MIDI numbers come from: the manual's MIDI chart, page …, or the
controller's editor>. Every number below comes from there.
"""

from ableton.v3.control_surface import MIDI_NOTE_TYPE, ElementsBase

CHANNEL = 0  # MIDI channel 1; channels count from 0

# Device facts. Replace each None with the controller's numbers; never guess one.
FADER_CCS = None  # one CC per track fader, left to right: [range(…)]
TRACK_BUTTON_NOTES = None  # one note per track button: [range(…)]
PLAY_NOTE = STOP_NOTE = None
MODE_NOTE = None  # the button that switches the track buttons between mute and solo


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=CHANNEL, **k)
        # the name in snake case is the element's name in the mappings: "faders", "play_button"
        self.add_encoder_matrix([FADER_CCS], "Faders")
        self.add_button_matrix([TRACK_BUTTON_NOTES], "Track_Buttons", msg_type=MIDI_NOTE_TYPE)
        self.add_button(PLAY_NOTE, "Play_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(STOP_NOTE, "Stop_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(MODE_NOTE, "Mode_Button", msg_type=MIDI_NOTE_TYPE)
