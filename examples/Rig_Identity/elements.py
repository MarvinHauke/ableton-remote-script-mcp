"""Four faders on channel 16, CC 20-23: an arbitrary layout for the rig, no real device."""

from ableton.v3.control_surface import ElementsBase

CH16 = 15


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=CH16, **k)
        self.add_encoder_matrix([range(20, 24)], "Faders", is_feedback_enabled=True)
