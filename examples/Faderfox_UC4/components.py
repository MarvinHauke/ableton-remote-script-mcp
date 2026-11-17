"""Components of our own: the Monitor green buttons, the Global group's scene start button and
launch quantization, which no framework component has, and a session ring that is on without an
identity reply."""

from ableton.v3.base import clamp, depends, listens, listens_group, sign
from ableton.v3.control_surface import Component
from ableton.v3.control_surface.components import (
    SessionRingComponent as SessionRingComponentBase,
)
from ableton.v3.control_surface.controls import (
    ButtonControl,
    StepEncoderControl,
    control_list,
)
from ableton.v3.live import liveobj_valid

# Song.clip_trigger_quantization: 0 None, 1 8 Bars, ... 13 1/32 (documented: Structure Void's
# Live.Song.Quantization has 14 values; numbers, since the value names differ between sources)
LAST_QUANTIZATION = 13

# values of a track's current_monitoring_state (Live.Track.Track.monitoring_states)
MONITOR_IN = 0
MONITOR_AUTO = 1


class SessionRingComponent(SessionRingComponentBase):
    """The framework builds the session ring disabled and enables it only when the controller
    answers the identity request (Specification `identity_response_id_bytes`). The UC4 is not
    identified, so the ring enables itself; otherwise Live draws no box."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.set_enabled(True)


class MonitorComponent(Component):
    """Eight buttons for the eight tracks of the session ring: a press switches the track's
    monitoring between In and Auto; the LED is lit while it is In."""

    monitor_buttons = control_list(ButtonControl, control_count=8)

    @depends(session_ring=None)
    def __init__(self, name="Monitor", session_ring=None, *a, **k):
        super().__init__(*a, name=name, **k)
        self._session_ring = session_ring
        self.__on_tracks_changed.subject = session_ring
        self.__on_tracks_changed()

    @monitor_buttons.pressed
    def monitor_buttons(self, button):
        track = self._monitorable_track(button.index)
        if track is not None:
            is_in = track.current_monitoring_state == MONITOR_IN
            track.current_monitoring_state = MONITOR_AUTO if is_in else MONITOR_IN

    def _monitorable_track(self, index):
        """The ring's track at `index` if it has a monitoring switch (audio and MIDI tracks; not
        group, return or master tracks, which can't be armed either)."""
        tracks = self._session_ring.tracks
        if index < len(tracks) and liveobj_valid(tracks[index]) and tracks[index].can_be_armed:
            return tracks[index]
        return None

    @listens("tracks")
    def __on_tracks_changed(self):
        tracks = [self._monitorable_track(i) for i in range(len(self._session_ring.tracks))]
        self.__on_monitoring_changed.replace_subjects([t for t in tracks if t is not None])
        self._update_buttons()

    @listens_group("current_monitoring_state")
    def __on_monitoring_changed(self, _):
        self._update_buttons()

    def update(self):
        super().update()
        self._update_buttons()

    def _update_buttons(self):
        for button in self.monitor_buttons:
            track = self._monitorable_track(button.index)
            is_in = track is not None and track.current_monitoring_state == MONITOR_IN
            button.color = "Monitor.In" if is_in else "Monitor.Off"


class SceneLaunchComponent(Component):
    """One button that launches the scene selected in Live."""

    launch_button = ButtonControl()

    def __init__(self, name="Scene_Launch", *a, **k):
        super().__init__(*a, name=name, **k)

    @launch_button.pressed
    def launch_button(self, _):
        self.song.view.selected_scene.fire()


class QuantizationComponent(Component):
    """A relative encoder that steps Live's launch quantization (the control bar's Quant)."""

    quantization_encoder = StepEncoderControl(num_steps=64)

    def __init__(self, name="Quantization", *a, **k):
        super().__init__(*a, name=name, **k)
        song = self.song
        self.quantization_encoder.connect_property(
            song,
            "clip_trigger_quantization",
            # Live takes an int only; sign() gives a float (ArgumentError, tested in 12.4.16)
            transform=lambda x: int(clamp(song.clip_trigger_quantization + sign(x), 0, LAST_QUANTIZATION)),
        )
