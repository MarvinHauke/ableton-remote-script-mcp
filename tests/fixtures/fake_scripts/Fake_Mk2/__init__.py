from ableton.v3.control_surface import Component, ControlSurfaceSpecification


class Specification(ControlSurfaceSpecification):
    num_tracks = 4
    component_map = {"Mixer": Component}


def create_instance(c_instance):
    return None
