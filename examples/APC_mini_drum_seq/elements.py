"""The APC mini mk1's controls as v3 elements.

Device facts: Akai's APC mini communication protocol (`documented`), confirmed for this unit by
the APC_mini_mk1 load test (docs/feature-plans/milestone-1/apc-mini-mk1.md, "Device facts").
Every control is on MIDI channel 1 (0 here). The grid's notes count from the bottom left: the
bottom row is 0-7, each row above adds 8, the top row is 56-63. Grid pads, track buttons, scene
buttons and Shift are momentary notes; the nine faders are absolute CCs 48-56.
"""

from ableton.v3.control_surface import MIDI_NOTE_TYPE, ElementsBase

CHANNEL = 0  # channel 1 on the APC


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=CHANNEL, **k)
        # Rows are written out, top row first, so the validator and the test rig can read the
        # numbers without running the script.
        # The top four rows: 32 steps, read left to right and top to bottom (step 1 top left).
        self.add_button_matrix(
            [range(56, 64), range(48, 56), range(40, 48), range(32, 40)],
            "Steps",
            msg_type=MIDI_NOTE_TYPE,
        )
        # The bottom four rows' left half: a 4x4 bank of drum pads (the lowest pad bottom left,
        # as on Live's Drum Rack); the right half stays dark.
        self.add_button_matrix(
            [range(24, 28), range(16, 20), range(8, 12), range(0, 4)],
            "Pads",
            msg_type=MIDI_NOTE_TYPE,
        )
        # track buttons: red LEDs; scene buttons: green LEDs, top to bottom
        self.add_button_matrix([range(64, 72)], "Track_Buttons", msg_type=MIDI_NOTE_TYPE)
        self.add_button_matrix([range(82, 90)], "Scene_Buttons", msg_type=MIDI_NOTE_TYPE)
        # scene buttons 1-4: the steps' resolution (columns 0-3 of the one-row matrix)
        self.add_submatrix(self.scene_buttons, "Resolution_Buttons", columns=(0, 4))
        self.add_button(98, "Shift_Button", msg_type=MIDI_NOTE_TYPE)  # no LED
        self.add_encoder_matrix([range(48, 56)], "Faders")
        self.add_encoder(56, "Master_Fader")
