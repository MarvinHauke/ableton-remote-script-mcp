from ..control_surface import component as comp
from .component import Component as Base
import ableton.v3


def _make():
    class HiddenInFunction(object):
        pass


class Meta(type):
    pass


class ControlSurfaceSpecification(metaclass=Meta):
    num_tracks = 8


class Deep(Base, comp.CompoundComponent, ableton.v3.Thing):
    pass


from typing import Generic, TypeVar

T = TypeVar("T")


class Typed(Base, Generic[T]):
    pass


mixins = (object,)


class Unpacked(*mixins):
    pass
