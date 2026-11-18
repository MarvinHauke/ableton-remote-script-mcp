"""Four faders (CC 20-23) and four launch buttons (notes 0-3), channel 16: an arbitrary layout
for the rig, no real device."""

from ableton.v3.control_surface import MIDI_NOTE_TYPE, ElementsBase

CH16 = 15


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=CH16, **k)
        self.add_encoder_matrix([range(20, 24)], "Faders", is_feedback_enabled=True)
        self.add_button_matrix([range(0, 4)], "Launch_Buttons", msg_type=MIDI_NOTE_TYPE)
