"""Which element drives which component control.

A section named like a component of the component map binds that component's controls: each key
is a member or a `set_<key>` setter of its class, each value an element's name. Any other
section is a modes component: its dict values are modes, its string values its own controls.
"""


def create_mappings(control_surface):
    mappings = {}
    mappings["Mixer"] = {"volume_controls": "faders"}
    mappings["Transport"] = {"play_button": "play_button", "stop_button": "stop_button"}
    # one set of buttons, several jobs: a modes component cycled by a button of its own
    mappings["Track_Button_Modes"] = {
        "cycle_mode_button": "mode_button",
        "mute": {"component": "Mixer", "mute_buttons": "track_buttons"},
        "solo": {"component": "Mixer", "solo_buttons": "track_buttons"},
    }
    return mappings
