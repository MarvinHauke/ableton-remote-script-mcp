from .surface import Surface


def create_instance(c_instance):
    """Live calls this once when the script is chosen as a Control Surface."""
    return Surface(c_instance)
