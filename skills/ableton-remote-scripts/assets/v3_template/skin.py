"""LED values by skin name (`Mixer.MuteOn`, `Session.ClipPlaying`, …). `create_skin` lays this
over the framework's default skin, which sends 127 for most "on" names and 0 for the rest; list
here only what the controller wants otherwise. Values come from the device facts."""

from ableton.v3.control_surface import BasicColors


class Skin:
    class Mixer:
        MuteOn = BasicColors.ON  # see the v3 reference page: "on" is the track activator
        MuteOff = BasicColors.OFF
