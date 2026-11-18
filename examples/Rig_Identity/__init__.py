"""A minimal v3 script that waits for the test rig's identity reply (plan 0002 step 4).

It sets the rig's own identity bytes (manufacturer 7D, MIDI's non-commercial ID) as its
`identity_response_id_bytes` and uses the framework's own session ring, so Live draws the box only
once the rig has answered. It logs when it is identified. Pick it with `ARS Test Rig` as Input
and Output while `rig serve --profile examples/Rig_Identity/device.yaml` runs.
"""

import logging

from ableton.v3.control_surface import ControlSurface, ControlSurfaceSpecification

from .elements import Elements
from .mappings import create_mappings

logger = logging.getLogger(__name__)

RIG_IDENTITY_BYTES = (0x7D, 0x00, 0x01, 0x00, 0x01)  # rig/profile.py RIG_IDENTITY_BYTES


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    num_tracks = 4
    num_scenes = 1
    identity_response_id_bytes = RIG_IDENTITY_BYTES
    create_mappings_function = create_mappings


def create_instance(c_instance):
    return Rig_Identity(specification=Specification, c_instance=c_instance)


class Rig_Identity(ControlSurface):
    def setup(self):
        super().setup()
        logger.info("ready, waiting for the identity reply")

    def on_identified(self, response_bytes):
        super().on_identified(response_bytes)
        logger.info("identified: %s", " ".join(f"{b:02X}" for b in response_bytes))
