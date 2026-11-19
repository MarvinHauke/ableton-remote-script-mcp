"""Which element drives which component control. The keys are the components' control names
(a member or a `set_<key>` setter of the component's class, checked by the validator), the values
the elements' names in snake case.

Plan 0003 steps 1-4: the steps, the pad bank and its scrolling, the track buttons as loop
buttons, the resolution, the track choice and the faders; step 5 (Decisions 29-30): the
resolution one step finer or coarser or on its own pad, and the scene choice. The pad bank is
also the steps' pitch provider, which the mappings can't express; `APC_mini_drum_seq.setup`
sets it.
"""


def create_mappings(control_surface):
    mappings = {}
    mappings["Step_Sequence"] = {
        "step_buttons": "steps",
        "loop_buttons": "track_buttons",
        "finer_resolution_button": "scene_buttons_raw[0]",  # Decision 29
        "coarser_resolution_button": "scene_buttons_raw[1]",
        "resolution_buttons": "resolution_pads",  # Decision 30: one pad per resolution
    }
    # v3's drum group hands its scroll_* controls to its DrumGroupScrollComponent (a row each)
    mappings["Drum_Group"] = {
        "matrix": "pads",
        "scroll_up_button": "scene_buttons_raw[4]",
        "scroll_down_button": "scene_buttons_raw[5]",
    }
    # the previous and next scene (the clip slot the steps edit, Decision 29), and the previous
    # and next track among Live's visible, return and master tracks
    mappings["View_Control"] = {
        "prev_scene_button": "scene_buttons_raw[2]",
        "next_scene_button": "scene_buttons_raw[3]",
        "prev_track_button": "scene_buttons_raw[6]",
        "next_track_button": "scene_buttons_raw[7]",
    }
    # faders 1-8: tracks 1-8 (the framework's session ring, which never moves here); fader 9: master
    mappings["Mixer"] = {"volume_controls": "faders", "master_track_volume_control": "master_fader"}
    return mappings
