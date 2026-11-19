"""Which element drives which component control. The keys are the components' control names
(a member or a `set_<key>` setter of the component's class, checked by the validator), the values
the elements' names in snake case.

Step 1 of plan 0003: the steps and the pad bank. The pad bank is also the steps' pitch provider,
which the mappings can't express; `APC_mini_drum_seq.setup` sets it.
"""


def create_mappings(control_surface):
    mappings = {}
    mappings["Step_Sequence"] = {"step_buttons": "steps"}
    mappings["Drum_Group"] = {"matrix": "pads"}
    return mappings
