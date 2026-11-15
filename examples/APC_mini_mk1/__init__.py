from .apc_mini_mk1 import APC_mini_mk1


def create_instance(c_instance):
    """Live calls this once when the script is chosen as a Control Surface."""
    return APC_mini_mk1(c_instance)
