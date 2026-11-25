from ableton.v3.control_surface import Component
from ableton.v3.control_surface.controls import ButtonControl


class SceneJumpComponent(Component):
    """Moves the selected scene down by `step` and fires it."""

    jump_button = ButtonControl()

    def __init__(self, name="Scene_Jump", step=1, *a, **k):
        super().__init__(*a, name=name, **k)
        self._step = step

    @jump_button.pressed
    def jump_button(self, _):
        scenes = list(self.song.scenes)
        index = scenes.index(self.song.view.selected_scene)
        target = self._next_index(index, len(scenes))
        self.song.view.selected_scene = scenes[target]
        scenes[target].fire()

    def _next_index(self, index, count, wrap):
        new_index = index + self._stpe
        return new_index % count if wrap else min(new_index, count - 1)
