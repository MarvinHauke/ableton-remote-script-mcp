# A `_Framework` script

Read this when the script uses `_Framework`, the oldest of the three framework generations
(`_Framework`, `ableton.v2`, `ableton.v3`). It suits direct mappings: a clip grid, scene and
navigation buttons, faders on the mixer. The names below were observed in the Live 12.4.16 index;
look each one up in the build the user runs before relying on it (`scripts/lookup.sh class <Name>`).

## Contents

- The parts of a script
- Elements: the physical controls
- Components: the behaviour
- LED feedback
- Rules that keep a script loading
- Patterns worth looking up

## The parts of a script

```
My_Controller/          folder name = a Python name; Live imports the script by it
  __init__.py           create_instance(c_instance) returns the control surface
  my_controller.py      the ControlSurface subclass (any module name works)
```

`create_instance` is called once when the user picks the script as a Control Surface. It takes one
argument, `c_instance`, Live's handle for this control surface slot, and passes it to
`ControlSurface.__init__`.

The control surface class (`_Framework.ControlSurface.ControlSurface`) builds everything in its
`__init__`, inside `with self.component_guard():`, and releases it in `disconnect()`. Members a
script uses most:

| Member | Use |
|---|---|
| `component_guard()` | context manager; build every element and component inside it |
| `log_message(*message)` | writes a message to Live's `Log.txt`, starting with `(<ClassName>)` (`documented`: read in the decompiled 12.0 framework) |
| `show_message(message)` | text in Live's status bar |
| `song()` | the `Live.Song.Song` of the open Set |
| `set_highlighting_session_component(session)` | draws the session box in Session View |
| `schedule_message(delay_in_ticks, callback, parameter=None)` | run `callback` a number of display ticks later |
| `disconnect()` | override to turn off LEDs (`reset()` on each button matrix), then call `super().disconnect()` |

## Elements: the physical controls

An element wraps one device control and its MIDI identity. Message types come from
`_Framework.InputControlElement`: `MIDI_NOTE_TYPE`, `MIDI_CC_TYPE`. Channels count from 0.

| Class | Constructor | For |
|---|---|---|
| `_Framework.ButtonElement.ButtonElement` | `(is_momentary, msg_type, channel, identifier, …, name=…)` | buttons and pads; `is_momentary=True` when the button sends on press and on release |
| `_Framework.SliderElement.SliderElement` | `(msg_type, channel, identifier, …, name=…)` | faders and absolute knobs |
| `_Framework.EncoderElement.EncoderElement` | `(msg_type, channel, identifier, map_mode, …)` | endless encoders; `map_mode` is a `Live.MidiMap.MapMode` value (Live's C++ module: the index has only the Push 3 helper's proxy model of it, `live_model.Live.MidiMap.MapMode`) |
| `_Framework.ButtonMatrixElement.ButtonMatrixElement` | `(rows=[[button, …], …], name=…)` | a grid; also a single row of buttons, as one row |

`name=` is a keyword of `ControlElement.__init__`; named elements make tracebacks and Live's own
control surface naming easier to read. A matrix's first row is the one the session gives its first
scene, so order the rows top to bottom even when the hardware numbers its pads from the bottom up
(`documented`, the pattern of Ableton's grid scripts; the load test checks it).

## Components: the behaviour

| Class | Constructor | Members a script sets |
|---|---|---|
| `_Framework.SessionComponent.SessionComponent` | `(num_tracks=0, num_scenes=0, auto_name=False, enable_skinning=False, …)`, plus `name=`, `is_enabled=` and `layer=` from `ControlSurfaceComponent` | `scene(index)` returns a scene; `set_clip_launch_buttons(matrix)`, `set_scene_launch_buttons(matrix)`, `set_track_bank_buttons(right_button, left_button)`, `set_scene_bank_buttons(down_button, up_button)`, `set_stop_track_clip_buttons(buttons)`, `set_stop_clip_value(value)`, `set_stop_clip_triggered_value(value)`, `set_stop_all_clips_button(button)`, `set_mixer(mixer)`, `set_offsets(track_offset, scene_offset)` |
| `_Framework.SceneComponent.SceneComponent` (from `session.scene(i)`) | | `clip_slot(index)`, `set_launch_button(button)`, `set_scene_value(value)`, `set_no_scene_value(value)`, `set_triggered_value(value)` |
| `_Framework.ClipSlotComponent.ClipSlotComponent` (from `scene.clip_slot(j)`) | | `set_launch_button(button)`, `set_stopped_value(value)`, `set_started_value(value)`, `set_triggered_to_play_value(value)`, `set_triggered_to_record_value(value)`, `set_recording_value(value)`, `set_record_button_value(value)` |
| `_Framework.MixerComponent.MixerComponent` | `(num_tracks=0, num_returns=0, auto_name=False, invert_mute_feedback=False, …)` | `channel_strip(index)`, `master_strip()`, `selected_strip()`, `return_strip(index)`, `set_volume_controls(controls)`, `set_arm_buttons(buttons)`, `set_solo_buttons(buttons)`, `set_mute_buttons(buttons)`, `set_track_select_buttons(buttons)` |
| `_Framework.ChannelStripComponent.ChannelStripComponent` (from `channel_strip(i)`) | | `set_volume_control(control)`, `set_pan_control(control)`, `set_send_controls(controls)`, `set_mute_button(button)`, `set_solo_button(button)`, `set_arm_button(button)`, `set_select_button(button)`, `set_invert_mute_feedback(invert_feedback)` |

`session.set_mixer(mixer)` makes the mixer follow the session box, so fader 1 is always the
leftmost track in the box. Passing `None` to a `set_…` method releases the element. (Both
`documented`: read in the decompiled 12.0 framework; the index shows the methods, not what they do.) For one button with two jobs, see "Patterns
worth looking up".

## LED feedback

`_Framework` lights a button by sending a value back to the same note or CC: a clip slot sends
its `set_started_value` value while its clip plays, its `set_stopped_value` value while the clip is
stopped, and so on for triggered and recording. Which value shows which colour or blink is up to the
controller (its manual lists the velocities its LEDs accept), so the values belong with the device
facts. What a slot sends when it was given no value is not in the index; set a value for every
state the checklist covers, and check the LEDs in the behaviour checklist.

- **Stop buttons:** `set_stop_clip_value` lights a track's stop button while the track plays,
  `set_stop_clip_triggered_value` while a quantized stop waits. Unset, the stop value starts as
  `None` (the button stays dark while its track plays) and the triggered value as 127
  (`documented`, decompiled 12.0 framework; setting both `tested` in Live 12.4.16).
- **Set LED values before the layer.** Assigning a layer hands the buttons over at once, and the
  component lights them with the values it has, so the first lighting uses the defaults otherwise
  (`documented`, decompiled 12.0 framework).
- **An override that sends LED values must handle `None`.** The framework treats an unset value
  as "turn off"; code of your own that passes it to `send_value` crashes with
  `TypeError: int() argument must be … not 'NoneType'`, and only once there is something to
  light, such as a playing clip when the Set opens (`tested` in Live 12.4.16).
- **Group tracks:** Live reports a playing clip only on the track that holds it, so a group
  track's stop button is never lit while the tracks in it play (`tested` in Live 12.4.16). The
  group's button blinks when the group itself is stopped. To light it, listen to
  `playing_slot_index` of every track and check `is_grouped` and `group_track` (`observed` in the
  Push 3 helper's proxy model of `Live.Track.Track`).
- **Turning LEDs off:** `reset()` on a button matrix turns its lit LEDs off; in `disconnect()` it
  is enough when the user chooses None as the Control Surface (`tested` in Live 12.4.16). When
  the user removes the output port instead, no script can reach the device and the LEDs stay lit.

## Rules that keep a script loading

- **Build inside `component_guard()`.** Elements and components get services (MIDI output,
  registration with the control surface) injected from the control surface. Outside the guard
  the injection is missing and Live logs
  `DependencyError: Required dependency register_component not provided` (seen in a Live 12.2.1
  log).
- **Call the base class.** `super().__init__(c_instance)` first in `__init__`, and
  `super().disconnect()` last in `disconnect()`. The base class's `disconnect` releases every
  component and element the script built (`documented`: read in the decompiled 12.0 framework); skipping it leaves them connected when the user
  switches scripts or closes the Set.
- **Use Live's Python only.** Live runs its own Python (3.11 in 12.4.16, observed) with its own standard library and a few
  extra packages; modules the tool's Python has may be missing (the validator says which).
  Third-party packages are not available unless the script ships them in its own folder.
- **Python 3, not Python 2.** Older scripts on the web import siblings without a dot
  (`from mixer import X`); in Python 3 that is `from .mixer import X`.

## Patterns worth looking up

These come up in `_Framework` scripts; look up the classes and outline a script that uses them
before writing one.

- **One button, two jobs (Shift):** `_Framework.ComboElement.ComboElement(control, modifiers=[shift])`
  is an element that acts only while its modifiers are held. Bind both the plain button and the
  combo through `Layer`s, not direct `set_…` calls: a layer grabs its elements as resources, and
  the combo (higher priority) takes the button away from the plain binding while Shift is held.
  A button that is the modifier of several combos needs
  `resource_type=_Framework.Resource.SharedResource` in its constructor, so they can all hold it.
  Ableton's `APC_mini` outline shows the pattern. Four things go with it (each `tested` in Live
  12.4.16, explained by the decompiled 12.0 framework):
  - **Give every Shift combination a job.** A button with no combo keeps its plain job while
    Shift is held, so Shift + an unbuilt button stops clips or launches a scene. Put combos for
    those buttons in a matrix and give it, through a layer, to a component that only holds them.
  - **Move one step per press with combos.** The session's bank buttons
    (`set_track_bank_buttons`, `set_scene_bank_buttons`) repeat while held and stop only on the
    button's release. When the user lets go of Shift first, the release goes to the plain
    binding, and the box keeps moving. A small component that calls `session.set_offsets` on
    each press has no such state.
  - **Light a combo's button in its setter.** When Shift is pressed, the combo takes its button
    and the layer calls the component's setter again. Send the LED there, only when
    `bool(combo)` is true (the combo holds its button).
  - **Write LEDs only to buttons the component holds.** Another component's LED updates still
    reach a button a combo holds (a session's stop LEDs, for example) unless it checks
    `matrix.owns_control_element(button)` first. And leave a borrowed button's LED as it is: a
    scene relights its button only when it is given a different one, so an LED darkened while
    Shift was held stays dark after it is let go.
  Open question: Ableton's combo scripts build on `_Framework.ControlSurface.OptimizedControlSurface`
  (`observed`), which hands each button to its final owner once per incoming MIDI message
  (`documented`). Whether a plain `ControlSurface` behaves worse with combos is not known yet.
- **Layers on components:** assign the layer after building the component,
  `session.layer = Layer(clip_launch_buttons=grid, …)`. A `layer=` passed to the constructor is
  grabbed only when the component's enabled state changes, so on a component that starts enabled
  it never takes effect: no button works and no LED lights, with no traceback (`tested` in Live
  12.4.16; Ableton's scripts pass `is_enabled=False` and enable the component later). Each layer
  key is the name after `set_` of one of the component's setters (`set_clip_launch_buttons`).
  This rule is `documented` (read in the decompiled 12.0 framework); the index shows only the
  setters, so look the setter up for each key.
- **Modes:** `_Framework.ModesComponent.ModesComponent` with `add_mode(name, mode_or_component)`
  and a `Layer` (`_Framework.Layer.Layer(priority=None, **controls)`) per mode. A layer binds a
  component's controls only while it is active, which avoids calling `set_…(None)` by hand.
- **Device control:** `_Framework.DeviceComponent.DeviceComponent` with
  `set_parameter_controls(controls)` and `self.set_device_component(device)` on the control
  surface.
- **Transport:** `_Framework.TransportComponent.TransportComponent` (`set_play_button`,
  `set_stop_button`, `set_record_button`).

For a full example of these together, outline one of Ableton's `_Framework` scripts for similar
hardware (`scripts/lookup.sh outline <Script>`). The outline lists each element with its MIDI
numbers, the components it builds, and which elements each layer binds.
