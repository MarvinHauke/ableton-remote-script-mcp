from functools import partial

from _Framework.ControlSurface import ControlSurface


class FakeMk1(ControlSurface):
    def _create_controls(self, *a, **k):
        make_color_button = partial(make_button, skin=self._skin)
        self._shift_button = make_button(0, 98, name="Shift_Button")
        self._pads = [make_color_button(0, 36 + i, name="Pad_%d" % (i + 1)) for i in range(8)]
        mappings = {}
        mappings["Mixer"] = dict(volume_controls="faders")
        with self.component_guard():
            self._session = SessionComponent(8, 1, layer=Layer(clip_launch_buttons=self._pads))
        if self._shift_button:
            self._mode = None
        self.mixer().layer = Layer(volume_controls=self._faders)
        super().__init__(*a, **k)
        return ButtonMatrixElement(rows=[self._pads])

    def _create_transport(self):
        if self.HAS_TRANSPORT:
            self._play = make_button(0, 91)
        else:
            self._play = None
        if self.A or self.B:
            ping()
        for i in range(2):
            tick(i)
        try:
            risky()
        except KeyError:
            recover()
        done()
