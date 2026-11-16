"""LED values. The UC4's green LEDs have one colour: on or off. The framework's default skin
already lights most "on" states with 127 and turns the rest off with 0; this skin changes only
what this controller wants otherwise."""

from ableton.v3.control_surface import BasicColors

ON = BasicColors.ON  # velocity 127
OFF = BasicColors.OFF  # velocity 0


class Skin:
    class Session:
        StopClip = ON  # a Stop button is lit while its track plays
        StopClipTriggered = ON
        Navigation = OFF  # navigation buttons light only while held
        NavigationPressed = ON

    class ViewControl:
        Track = OFF
        TrackPressed = ON
        Scene = OFF
        ScenePressed = ON

    class Monitor:  # our own component's names (components.py)
        In = ON
        Off = OFF
