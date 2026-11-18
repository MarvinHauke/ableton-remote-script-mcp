"""Faders 1-4: the volumes of the four tracks in the session box; buttons 1-4 launch their clips.
The Session mapping matters for the identity check: v3 enables the session ring on identification
only when the script has a SessionComponent (12.4.16, `ControlSurface._can_enable_session_ring`)."""


def create_mappings(control_surface):
    return {
        "Mixer": {"volume_controls": "faders"},
        "Session": {"clip_launch_buttons": "launch_buttons"},
    }
