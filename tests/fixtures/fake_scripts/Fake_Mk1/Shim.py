# Fake Remote Script module written for the tests; not Ableton code. A base from a star import.
from _Framework.ControlSurface import *


class ShimmedSurface(ControlSurface):
    def disconnect(self):
        ControlSurface.disconnect(self)
