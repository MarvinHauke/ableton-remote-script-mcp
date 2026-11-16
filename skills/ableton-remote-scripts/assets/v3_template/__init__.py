"""<Controller name> Remote Script on `ableton.v3`, for Live 12.4 or later.

What the controls do: <the behaviour list agreed with the user>.
Device facts: in `elements.py`, with their source.
"""

import logging

from ableton.v3.control_surface import (
    ControlSurface,
    ControlSurfaceSpecification,
    create_skin,
)
from ableton.v3.control_surface.components import (
    SessionRingComponent as SessionRingBase,
)

from .elements import Elements
from .mappings import create_mappings
from .skin import Skin

logger = logging.getLogger(__name__)  # Live writes it to Log.txt as `Python: INFO:<Folder>:…`


class SessionRingComponent(SessionRingBase):
    """The framework enables the ring only when the device answers the identity request; for a
    device without identity_response_id_bytes the ring enables itself, so Live draws the box."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.set_enabled(True)


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    control_surface_skin = create_skin(skin=Skin)
    num_tracks = 8  # the session ring: how many tracks and scenes the controller sees
    num_scenes = 1
    session_ring_component_type = SessionRingComponent  # remove if identity bytes are set
    create_mappings_function = create_mappings
    # component_map = {"My_Component": MyComponent}  # components of your own, by name


def create_instance(c_instance):
    """Live calls this once when the script is chosen as a Control Surface."""
    return Surface(specification=Specification, c_instance=c_instance)


class Surface(ControlSurface):  # rename like the folder: tracebacks and the log name it
    def setup(self):
        super().setup()  # builds the elements, the components and the mappings
        logger.info("ready")
