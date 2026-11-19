"""Which element drives which component control. The keys are the components' control names
(a member or a `set_<key>` setter of the component's class, checked by the validator), the values
the elements' names in snake case.

Plan 0003 steps 1-3: the steps, the pad bank and its scrolling, the track buttons as loop
buttons. The pad bank is also the steps' pitch provider, which the mappings can't express;
`APC_mini_drum_seq.setup` sets it.
"""


def create_mappings(control_surface):
    mappings = {}
    mappings["Step_Sequence"] = {"step_buttons": "steps", "loop_buttons": "track_buttons"}
    # v3's drum group hands its scroll_* controls to its DrumGroupScrollComponent (a row each)
    mappings["Drum_Group"] = {
        "matrix": "pads",
        "scroll_up_button": "scene_buttons_raw[4]",
        "scroll_down_button": "scene_buttons_raw[5]",
    }
    return mappings
