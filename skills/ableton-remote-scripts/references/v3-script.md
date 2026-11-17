# An `ableton.v3` script

Read this when the script uses `ableton.v3`, the newest framework generation. It describes the
controller and its mappings as data instead of building components by hand, and it brings
modes, skins and a session ring along. Ableton's recent controller scripts use it (in 12.4.16:
`APC_mini_mk2`, `Launch_Control_XL_3`, `MiniLab_3`, `ATOM`, `FANTOM`, …). The names below were
observed in the Live 12.4.16 index unless marked otherwise. Look each one up in the build the
user runs (`scripts/lookup.sh class <Name>`), and outline one of those scripts for patterns
(`scripts/lookup.sh outline Launch_Control_XL_3`).

## Contents

- The parts of a script
- The Specification
- Elements
- Components and the component map
- Mappings and modes
- Skins and LED values
- A component of your own
- Rules that keep a script loading
- Logging

## The parts of a script

```
My_Controller/          folder name = a Python name; Live imports the script by it
  __init__.py           Specification, create_instance, the ControlSurface subclass
  elements.py           Elements: one element per device control, with its MIDI numbers
  mappings.py           create_mappings: which element drives which component control
  skin.py               LED values by name
  components.py         components of your own, if the framework has none for a job
```

Start from `assets/v3_template/`. `create_instance(c_instance)` returns
`MyController(specification=Specification, c_instance=c_instance)`, as
`Launch_Control_XL_3` does. The control surface class
`ableton.v3.control_surface.ControlSurface` (`__init__(self, specification=None, *a, **k)`)
builds everything from the Specification in its `setup()`. Override `setup()` and call
`super().setup()` first when the script needs to do something once everything is built.
Afterwards `self.component_map["Mixer"]` is the built component of that name.

## The Specification

A subclass of `ableton.v3.control_surface.ControlSurfaceSpecification` that sets class fields.
The fields a script sets most, with the framework default:

| Field | Default | Use |
|---|---|---|
| `elements_type` | `None` | your `Elements` class |
| `create_mappings_function` | a method | your `create_mappings` |
| `control_surface_skin` | `default_skin` | `create_skin(skin=Skin)`; `colors=` adds a colour class |
| `num_tracks`, `num_scenes` | `8`, `1` | the size of the session ring (the box Live draws) |
| `include_returns`, `include_master` | `False` | return tracks or the master in the ring |
| `link_session_ring_to_track_selection` | `False` | the ring follows the selected track |
| `link_session_ring_to_scene_selection` | `False` | the ring follows the selected scene |
| `component_map` | `{}` | your own components by name, or a framework one replaced |
| `identity_response_id_bytes` | `None` | bytes of the device's SysEx identity reply (see below) |
| `session_ring_component_type` | `SessionRingComponent` | a ring class of your own (see below) |
| `hello_messages`, `goodbye_messages` | `None` | MIDI sent on start and on exit |
| `feedback_channels`, `playing_feedback_velocity` | `None`, `127` | note feedback for drum pads and the like |

**A controller with no identity reply gets no session box.** The framework builds the session
ring disabled and enables it only when the controller answers the SysEx identity request
(`observed` in 12.4.16's `ControlSurface`). Without `identity_response_id_bytes` it stays
disabled: the mappings work, but Live draws no box. Give such a script a ring that enables
itself (`tested` on the Faderfox UC4 in 12.4.16):

```python
from ableton.v3.control_surface.components import SessionRingComponent as SessionRingBase

class SessionRingComponent(SessionRingBase):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.set_enabled(True)   # no identity reply will enable it
```

and set `session_ring_component_type = SessionRingComponent` in the Specification.
`link_session_ring_to_scene_selection` (and `…_track_selection`) moves the box only for
selections made through the script's `View_Control` (`scene_encoder`, `prev_scene_button`, …),
not for clicks in Live (`observed`, `tested`).

The validator reports a field the base class doesn't have (`specification-field`). A typo
otherwise only makes a new class attribute that nothing reads.

## Elements

`Elements(ElementsBase)` builds each element in `__init__` with the `add_…` methods of
`ableton.v3.control_surface.ElementsBase`. Pass `global_channel=` to `super().__init__` for the
channel most controls use (channels count from 0), and `channel=` to an `add_…` call for the
others.

| Method | Builds |
|---|---|
| `add_button(identifier, name, **k)` | a button; `msg_type=MIDI_NOTE_TYPE` for notes (the default is CC), `is_momentary=False` for a button that sends only on press |
| `add_encoder(identifier, name, **k)` | a fader, knob or encoder; `map_mode=` for a relative encoder |
| `add_button_matrix(identifiers, base_name, channels=None, …)` | a grid or a row of buttons; `identifiers` is a list of rows |
| `add_encoder_matrix(identifiers, base_name, channels=None, …)` | a row or grid of faders or knobs |
| `add_modifier_button(identifier, name, …)` | a button other elements can be combined with (Shift) |
| `add_modified_control(control=, modifier=)` | the combination, named `<control>_with_<modifier>` |
| `add_submatrix(matrix, name, columns=, rows=)` | part of a matrix under a name of its own |

`create_matrix_identifiers(start, stop, width=, flip_rows=)` makes the rows for a block of
consecutive numbers; `flip_rows=True` puts the top row first when the hardware numbers its pads
from the bottom up.

**Names.** The mappings name an element by its `name` in lower case with spaces as underscores:
`"Play_Button"` is `play_button`. A matrix also gives `<name>_raw`, the flat list of its
elements, so a mapping can name one of them (`"scene_launch_buttons_raw[7]"`). A modified
control is `<control>_with_<modifier without _button>` (`play_button_with_shift`). The validator
checks every name in the mappings against what `Elements` builds (`element-name`).

**Relative encoders.** `MapMode` (`ableton.v3.control_surface.MapMode`) names the
`Live.MidiMap.MapMode` values: `Absolute`, `LinearTwoCompliment` (1 up, 127 down, smooth),
`AccelTwoCompliment`, `LinearBinaryOffset` (65 up, 63 down), `LinearSignedBit`, and more. Which
one the device sends is a device fact.

**Values back to the controller.** An encoder element sends a mapped parameter's value back
only when it's built with `is_feedback_enabled=True`; the default is `False` (observed in
12.4.16; FANTOM and Komplete Kontrol S mk3 pass `True`). Set it for every fader and absolute
knob of a controller that shows values or picks them up (a value display, LED rings, soft
pickup on the device): without it the device never learns Live's value, and its own pickup
jumps (`tested` on the Faderfox UC4 in 12.4.16).

**One element per MIDI message.** Two controls that send the same type, channel and number
(the same note on two pages of a controller) are one element; build it once and map it once.

## Components and the component map

The framework builds the components the mappings name, from a component map of names to
classes. Its default names (outline any v3 script with `--all-components` to see the classes):
`Mixer`, `Session`, `Session_Navigation`, `Session_Overview`, `Transport`, `Recording`,
`View_Based_Recording`, `View_Control`, `View_Toggle`, `Device`, `Device_Navigation`,
`Target_Channel_Strip`, `Clip_Actions`, `Undo_Redo`, `Drum_Group`, `Sliced_Simpler`, `Accent`,
`Active_Parameter`, `Modifier_Background`, `Translating_Background`, and the ring
(`Session_Ring`) and target track the others depend on.

Controls a script maps most, by component (each `observed` as a member or `set_` setter in
12.4.16, except where noted):

| Component | Keys |
|---|---|
| `Mixer` (`MixerComponent`) | `volume_controls`, `pan_controls`, `send_controls`, `send_a_controls`… (one send each), `mute_buttons`, `solo_buttons`, `arm_buttons`, `track_select_buttons`, `crossfader_control`, `prehear_volume_control`, `master_track_volume_control`, `master_track_pan_control`, `target_track_volume_control`, `prev_send_index_button`, `next_send_index_button` |
| `Target_Channel_Strip` | the selected track: `volume_control`, `pan_control`, `send_a_control`…, `mute_button`, `solo_button`, `arm_button` |
| `Session` | `clip_launch_buttons`, `scene_launch_buttons`, `stop_track_clip_buttons`, `stop_all_clips_button`, `clip_slot_select_button` |
| `Session_Navigation` | `up_button`, `down_button`, `left_button`, `right_button`, `page_…_button`, `vertical_encoder`, `horizontal_encoder` |
| `View_Control` | `prev_track_button`, `next_track_button`, `prev_scene_button`, `next_scene_button`, `track_encoder`, `scene_encoder` |
| `Transport` | `play_button`, `play_toggle_button`, `stop_button`, `loop_button`, `metronome_button`, `tap_tempo_button`, `nudge_down_button`, `nudge_up_button`, `tempo_coarse_encoder`, `tempo_fine_encoder`, `capture_midi_button` |
| `View_Based_Recording` | `record_button` (session or arrangement recording, by the view shown) |
| `View_Toggle` | `main_view_toggle_button`, `detail_view_toggle_button`, `clip_view_toggle_button`, `browser_view_toggle_button` |
| `Device` | `parameter_controls` (the selected device's bank of 8) |
| `Device_Navigation` | `scroll_up_button`, `scroll_down_button` (previous and next device), `scroll_encoder` |

`MixerComponent` and `TargetChannelStripComponent` answer many of their keys by name pattern
(`__getattr__`): `mute_buttons` sets each channel strip's `mute_button`,
`send_b_controls` the second send of each strip, `master_track_…` the master strip's control.
The validator lists these keys as not checked. Look the strip's member up
(`ableton.v3.control_surface.components.channel_strip.ChannelStripComponent`) and check that one
of Ableton's scripts uses the key (outline it); the pattern code itself is in the index's
statements, which `outline` doesn't print.

## Mappings and modes

`create_mappings(control_surface)` returns a dict of sections. The rules, read in
`ControlSurfaceMappingMixin.setup` (12.4.16):

- **A section named like a component** binds that component's controls: each key is a member
  or `set_<key>` setter of its class (`mapping-key`), each value an element name.
  `enable=False` builds the component disabled.
- **Any other section is a modes component** (`ModesComponent`). A value that is a dict is a
  mode, `None` an empty mode; a string value is a control of the modes component itself:
  `cycle_mode_button`, `<mode>_button` (one per mode, made for you), `prev_mode_button`,
  `next_mode_button`, `mode_selection_control`. Options it reads: `modes_component_type`,
  `default_behaviour`, `support_momentary_mode_cycling`, `is_private`, `enable`.
- **A mode** names its `component=` and binds that component's keys while the mode is
  selected. `modes=[dict(component=…, …), …]` binds several components in one mode.
  `behaviour=` changes what the mode button does: `MomentaryBehaviour()` (selected while held,
  the usual Shift), `ToggleBehaviour()`, `ImmediateBehaviour()`, `LatchingBehaviour()`, and
  `make_reenter_behaviour(…, on_reenter=…)` (all in `ableton.v3.control_surface.mode`).
- A mode's `component=` must be in the component map or be another modes section, or setup
  raises a KeyError (the validator's `unknown-component`).

```python
mappings["Fader_Modes"] = dict(
    cycle_mode_button="fader_mode_button",
    volume=dict(component="Mixer", volume_controls="faders"),
    device=dict(component="Device", parameter_controls="faders"),
)
```

Modes keep the dict's order, and the first one is selected at start (`documented`). Ableton's `APC_mini_mk2`
and `Launch_Control_XL_3` outlines show Shift as a `MomentaryBehaviour` mode with several
parts.

## Skins and LED values

A component never sends a number itself: it asks for a colour by skin name
(`Mixer.MuteOn`, `Session.ClipPlaying`, `Transport.PlayOff`), and the skin gives the value the
element sends. `create_skin(skin=Skin, colors=…)` lays your classes over the framework's
default skin; nested classes make the dotted names:

```python
from ableton.v3.control_surface import BasicColors   # ON = SimpleColor(127), OFF = SimpleColor(0)

class Skin:
    class Session:
        StopClip = BasicColors.ON       # light a track's stop button while it plays
```

- **Missing names.** A name the skin doesn't have is sent as `BasicColors.ON` when it ends in
  `On`, `Pressed`, `Selected` or `Enabled`, else `OFF`; the default skin covers the framework's
  names with 127 and 0 (`documented`, decompiled 12.0 framework). So a one-colour controller
  that takes 127 and 0 needs only the names it wants otherwise.
- **Names the framework uses.** Ableton's v3 skins in 12.4.16 set `Session.ClipStopped`,
  `ClipPlaying`, `ClipTriggeredPlay`, `ClipRecording`, `ClipTriggeredRecord`, `Slot`,
  `StopClip`, `StopClipTriggered`, `StopClipDisabled`, `Navigation`, `NavigationPressed`;
  `Mixer.ArmOn`/`Off`, `MuteOn`/`Off`, `SoloOn`/`Off`, `Selected`, `NotSelected`;
  `Transport.PlayOn`/`Off`, `StopOn`/`Off`, `LoopOn`/`Off`, `MetronomeOn`/`Off`;
  `Recording.ArrangementRecordOn`/`Off`, `SessionRecordOn`/`Off`/`Transition`;
  `ViewControl.Track`/`TrackPressed`; `Device.Navigation`/`NavigationPressed`.
- **`Mixer.MuteOn` means the track plays.** The mute button is mapped to the track activator,
  so "on" is the activator on, the track not muted (`documented`, decompiled 12.0 framework).
  Put it on the checklist.
- **RGB pads.** A colour class of `SimpleColor(value)` per colour (`colors=Rgb`), or
  `RgbColor`/`create_rgb_color` from `ableton.v3.control_surface.elements`; `Launch_Control_XL_3`
  and `APC_mini_mk2` outlines show both. An entry such as `make_color_for_liveobj` (in
  `Launch_Control_XL_3`'s skin) takes the track's or clip's colour.

## A component of your own

When no framework component does the job, write one and add it to `component_map`:

```python
from ableton.v3.base import depends, listens
from ableton.v3.control_surface import Component
from ableton.v3.control_surface.controls import ButtonControl, control_list

class SceneLaunchComponent(Component):
    launch_button = ButtonControl()

    def __init__(self, name="Scene_Launch", *a, **k):
        super().__init__(*a, name=name, **k)

    @launch_button.pressed
    def launch_button(self, _):
        self.song.view.selected_scene.fire()
```

- **Controls** are class attributes (`ableton.v3.control_surface.controls`): `ButtonControl`,
  `ToggleButtonControl(color=, on_color=)`, `MappedControl` (mapped to a Live parameter),
  `StepEncoderControl(num_steps=)`, `control_list(ButtonControl, control_count=8)` for a row. A
  mapping key is the control's name. The decorator `@<control>.pressed` (also `released`,
  `value`, `double_clicked`) names the handler; in a list the handler gets the button, whose
  `index` is its place (`documented`). Set `button.color = "My.SkinName"` to light it.
- **Dependencies.** `@depends(session_ring=None)` on `__init__` gets the session ring (its
  `tracks`, `track_offset`), `@depends(target_track=None)` the target track; the framework
  passes them in (`observed` in `MixerComponent` and `ViewControlComponent`).
- **Listeners.** `@listens("tracks")` on a method and `self.__on_x.subject = obj` listens to one
  object; `@listens_group("arm")` with `replace_subjects(tracks)` to several (both from
  `ableton.v3.base`). They are released with the component.
- **Live's properties take the exact type.** Setting an int property to a float raises
  `Boost.Python.ArgumentError … did not match C++ signature: None(TPyHandle<ASong>, int)` on
  every use, and nothing changes in Live. `sign()` and division give floats: wrap them in
  `int(…)` (`tested` with `Song.clip_trigger_quantization` in 12.4.16). Read the signature in
  the error, or a `documented` member's signature in `lookup class`.
- **Live's objects.** `self.song` is the `Live.Song.Song`; `liveobj_valid(obj)` from
  `ableton.v3.live` tells whether a Live object still exists. Live's own classes are only partly
  in the index; a member from Structure Void's pages is `documented`: say so.

## Rules that keep a script loading

- **Build nothing in `__init__`.** `setup()` builds the elements and components inside the
  component guard; code of your own that builds elements or components goes in `setup()` after
  `super().setup()` (the validator's `component-guard` exempts `setup`).
- **Every mapping name must exist.** A key the component doesn't have, an element name
  `Elements` doesn't build, or a mode's unknown component stops the script with a traceback when
  it loads. The validator checks all three; read its not-checked list for the pattern keys.
- **Overrides keep the framework's arguments** (`override-signature`), and an overridden
  `disconnect` calls `super().disconnect()` (`disconnect-base`).
- **Don't mix generations.** Import from `ableton.v3` (and `ableton.v2.base` only through
  `ableton.v3.base`); never from `_Framework`.

## Logging

v3 has no `log_message`. Ableton's v3 scripts use Python's `logging`:
`logger = logging.getLogger(__name__)` and `logger.info(…)`. Live writes it to `Log.txt` as
`Python: INFO:<module>:<line> - <text>` (the format is `observed` for `_Framework`'s own logger
in 12.4.16 logs). The module name starts with the folder name, so `scripts/log.sh --script
<Folder>` shows these messages. The template logs `ready` from `setup()`: when that line is
there, the whole Specification was built.
