"""Faderfox UC4 Remote Script on `ableton.v3`, for the UC4's factory setup SE17 (Ableton, tracks
1-8), for Live 12.4 or later.

What each control does, by the groups printed on the panel (the device facts are in
`elements.py`):

- Faders 1-8: volume of the eight tracks of the session ring; fader 9: the crossfader.
- Encoder groups Send 1-4: sends A-D of the eight tracks; Pan: their pans; Rack: the eight
  parameters of the selected device's bank.
- Encoder group Track, for the selected track: 1 volume, 2 send A, 3 send B, 4 select a track,
  5 select a device, 6 pan.
- Encoder group Global: 1 tempo, 2 tempo fine, 3 cue volume, 4 select a scene, 6 master volume,
  8 master pan; push buttons 1-8: nudge down, nudge up, play, stop, stop all clips, start the
  selected scene, record, switch Session/Arrangement View.
- Green button groups: Launch (the selected scene's clips), Stop (each track's clips), Active
  (lit: the track plays), Solo, Record (arm), Monitor (In or Auto; lit: In), Track (bank left
  and right, previous and next track, scene, device), Select.

Which Global control is which printed function is not known (the UC4 Editor's device page);
the assignment above is this script's choice.
"""

import logging

from ableton.v3.control_surface import (
    ControlSurface,
    ControlSurfaceSpecification,
    create_skin,
)

from .components import MonitorComponent, SceneLaunchComponent, SessionRingComponent
from .elements import Elements
from .mappings import create_mappings
from .skin import Skin

logger = logging.getLogger(__name__)


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    control_surface_skin = create_skin(skin=Skin)
    num_tracks = 8
    num_scenes = 1
    link_session_ring_to_scene_selection = True  # Launch plays the selected scene's row
    session_ring_component_type = SessionRingComponent  # on without an identity reply
    create_mappings_function = create_mappings
    component_map = {"Monitor": MonitorComponent, "Scene_Launch": SceneLaunchComponent}


def create_instance(c_instance):
    """Live calls this once when the script is chosen as a Control Surface."""
    return Faderfox_UC4(specification=Specification, c_instance=c_instance)


class Faderfox_UC4(ControlSurface):
    def setup(self):
        super().setup()
        logger.info("Faderfox UC4 (SE17) ready")
