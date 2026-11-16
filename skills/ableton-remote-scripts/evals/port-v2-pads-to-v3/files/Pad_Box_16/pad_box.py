"""A Remote Script on ableton.v2 for a small pad controller (written for the skill evals).

The controller: a 4x4 pad grid (notes 36-51 on channel 1, bottom-left pad first, rows of four),
four faders (CC 20-23), and four buttons below the faders (notes 60-63): the two left ones move
the session box left and right, the two right ones up and down. The pads light with velocity
0 (off), 1 (green), 2 (green blinking) and 3 (red); this script leaves the LED values at the
framework's defaults.
"""

from ableton.v2.control_surface import ControlSurface, Layer, MIDI_CC_TYPE, MIDI_NOTE_TYPE
from ableton.v2.control_surface.components import (MixerComponent, SessionComponent,
                                                   SessionNavigationComponent, SessionRingComponent)
from ableton.v2.control_surface.elements import ButtonElement, ButtonMatrixElement, SliderElement

CHANNEL = 0
NUM_TRACKS = NUM_SCENES = 4


class PadBox(ControlSurface):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        with self.component_guard():
            pads = ButtonMatrixElement(rows=[
                [ButtonElement(True, MIDI_NOTE_TYPE, CHANNEL, 36 + row * 4 + col, name=f"Pad_{row}_{col}")
                 for col in range(4)]
                for row in reversed(range(4))], name="Pads")
            faders = ButtonMatrixElement(rows=[[SliderElement(MIDI_CC_TYPE, CHANNEL, 20 + i, name=f"Fader_{i}")
                                                for i in range(4)]], name="Faders")
            left, right, up, down = (ButtonElement(True, MIDI_NOTE_TYPE, CHANNEL, 60 + i, name=n)
                                     for i, n in enumerate(("Left", "Right", "Up", "Down")))

            self._ring = SessionRingComponent(num_tracks=NUM_TRACKS, num_scenes=NUM_SCENES, name="Session_Ring")
            self._session = SessionComponent(session_ring=self._ring, name="Session")
            self._session.layer = Layer(clip_launch_buttons=pads)
            self._navigation = SessionNavigationComponent(session_ring=self._ring, name="Navigation")
            self._navigation.layer = Layer(left_button=left, right_button=right, up_button=up, down_button=down)
            self._mixer = MixerComponent(tracks_provider=self._ring, name="Mixer")
            self._mixer.layer = Layer(volume_controls=faders)
        self.show_message("Pad_Box_16 loaded")
