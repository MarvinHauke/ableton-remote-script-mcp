"""Two small components of our own, for panel functions no framework component has: the Monitor
green buttons and the Global group's scene start button."""

from ableton.v3.base import depends, listens, listens_group
from ableton.v3.control_surface import Component
from ableton.v3.control_surface.controls import ButtonControl, control_list
from ableton.v3.live import liveobj_valid

# values of a track's current_monitoring_state (Live.Track.Track.monitoring_states)
MONITOR_IN = 0
MONITOR_AUTO = 1


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
