"""LED values. A grid pad's colour is the velocity Live sends on its note: 0 off, 1 green,
2 green blinking, 3 red, 4 red blinking, 5 yellow, 6 yellow blinking. The track buttons (red) and
scene buttons (green) take 0 off, 1 on, 2 blinking (device facts in `elements.py`).

The framework's default skin lights a missing name ending in On, Pressed, Selected or Enabled with
127, which the APC doesn't show as a colour, so every name the components use here is set.
"""

from ableton.v3.control_surface.elements import SimpleColor

OFF = SimpleColor(0)
GREEN = SimpleColor(1)
GREEN_BLINK = SimpleColor(2)
RED = SimpleColor(3)
RED_BLINK = SimpleColor(4)
YELLOW = SimpleColor(5)
YELLOW_BLINK = SimpleColor(6)

ON = SimpleColor(1)  # a track or scene button's LED
BLINK = SimpleColor(2)


class Skin:
    class NoteEditor:  # the 32 step buttons
        StepFilled = GREEN
        StepEmpty = OFF
        StepMuted = OFF
        StepDisabled = OFF
        Playhead = YELLOW  # our note editor's names (components.py)
        StepOutsideLoop = RED  # an empty step outside the clip's loop
        NoClip = OFF

        class Resolution:
            Selected = ON
            NotSelected = OFF

    class LoopSelector:  # the track buttons: one page each
        InsideLoopSelected = ON  # the page the steps show
        OutsideLoopSelected = ON
        InsideLoop = OFF
        OutsideLoop = OFF
        Playhead = BLINK  # the page the playhead is on
        PlayheadRecord = BLINK
        Navigation = OFF
        NavigationPressed = ON

    class ViewControl:  # scene buttons 7-8: off when there is no track to move to
        Track = ON
        TrackPressed = ON

    class DrumGroup:  # the 4x4 pad bank
        PadPressed = RED  # our pad bank's name (components.py): a held pad
        PadSelected = GREEN_BLINK
        PadMutedSelected = GREEN_BLINK
        PadSoloedSelected = GREEN_BLINK
        PadFilled = YELLOW
        PadEmpty = OFF
        PadMuted = OFF
        PadSoloed = YELLOW
        PadAction = YELLOW
        Scroll = ON  # scene buttons 5-6, off when they can't scroll (DefaultButton.Disabled)
        ScrollPressed = ON
