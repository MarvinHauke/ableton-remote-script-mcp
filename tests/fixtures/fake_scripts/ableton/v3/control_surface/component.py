"""Fake v3 components, written for the tests."""

DEFAULT_LAYER = None


def listens(event_name, *a):
    def decorate(f):
        return f

    return decorate


class Component(object):
    """A unit of behaviour.

    Second paragraph.
    """

    __events__ = ("enabled",)
    num_layers = 0
    canonical_parent = None
    layer_type = DEFAULT_LAYER
    sizes = [1, 2, 3]

    def __init__(self, name="", parent=None, layer=DEFAULT_LAYER, *a, is_enabled=True, **k):
        """Make a component."""
        self.name = name

    def disconnect(self):
        pass

    @property
    def is_enabled(self):
        return True

    @is_enabled.setter
    def is_enabled(self, value):
        pass

    @property
    def song(self):
        return None

    @staticmethod
    def make(x, /, y=(1, "a")):
        pass

    @classmethod
    def create(cls, *, size=8):
        pass

    @listens("value")
    def _on_value(self, value):
        pass

    on_selected = lambda self: None


class CompoundComponent(Component):
    class State:
        pass
