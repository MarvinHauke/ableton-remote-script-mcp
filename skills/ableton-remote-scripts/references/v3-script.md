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
- A step sequencer
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

and set `session_ring_component_type = SessionRingComponent` in the Specification. The validator
warns when a Specification has neither and a mapped component depends on the ring
(`session-ring`).
`link_session_ring_to_scene_selection` moves the box only for selections made through the
script's `View_Control` (`scene_encoder`, `prev_scene_button`, …), not for clicks in Live
(`observed` in 12.4.16's `SessionRingSelectionLinking`, `tested` on the UC4).
`…_track_selection` is built the same way (`observed`; not tested).

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

**Write the numbers so a reader can see them.** The validator and the test rig read `Elements`
without running it: literal numbers, `range(…)` rows and `create_matrix_identifiers` are read; a
helper of your own that computes the rows (`grid_rows(4, 7)`) is not, and its elements go
unchecked. Pass keywords by name (`msg_type=MIDI_NOTE_TYPE`), not from a dict (`**NOTE`): the
validator can't read element names behind a `**`.

**Names.** The mappings name an element by its `name` in lower case with spaces as underscores:
`"Play_Button"` is `play_button`. A matrix also gives `<name>_raw`, the flat list of its
elements, so a mapping can name one of them (`"scene_launch_buttons_raw[7]"`). A modified
control is `<control>_with_<modifier without _button>` (`play_button_with_shift`). The validator
checks every name in the mappings against what `Elements` builds (`element-name`).

**Relative encoders.** `MapMode` (`ableton.v3.control_surface.MapMode`) names the
`Live.MidiMap.MapMode` values: `Absolute`, `LinearTwoCompliment` (1 up, 127 down, smooth),
`AccelTwoCompliment`, `LinearBinaryOffset` (65 up, 63 down), `LinearSignedBit`, and more.
What "smooth" and the binary-offset values mean is `documented` (Ableton's custom MIDI mapping
help); `LinearTwoCompliment` with 1 and 127 is `tested` on the Faderfox UC4. Which
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

Modes keep the dict's order, and the first one is selected at start (`documented`, decompiled
12.0 framework). Ableton's `APC_mini_mk2`
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
  names (`observed` in 12.4.16's `Skin.__getitem__` and default skin), with 127 and 0
  (`documented`: read from 12.4.16's bytecode, not in the index). So a
  one-colour controller that takes 127 and 0 needs only the names it wants otherwise. A
  controller that takes colours as velocities (0 off, 1 green, …) sets every name its
  components use: 127 is no colour there.
- **No fallback for a track's colour.** A name a component asks for through `LiveObjSkinEntry`
  (the note editor and the drum group do) is looked up directly: a name the skin and the default
  skin both lack raises `KeyError` (`observed` in 12.4.16's `Skin.__getitem__`). Put every name
  of your own into the skin.
- **Names the framework uses.** Ableton's v3 skins in 12.4.16 set `Session.ClipStopped`,
  `ClipPlaying`, `ClipTriggeredPlay`, `ClipRecording`, `ClipTriggeredRecord`, `Slot`,
  `StopClip`, `StopClipTriggered`, `StopClipDisabled`, `Navigation`, `NavigationPressed`;
  `Mixer.ArmOn`/`Off`, `MuteOn`/`Off`, `SoloOn`/`Off`, `Selected`, `NotSelected`;
  `Transport.PlayOn`/`Off`, `StopOn`/`Off`, `LoopOn`/`Off`, `MetronomeOn`/`Off`;
  `Recording.ArrangementRecordOn`/`Off`, `SessionRecordOn`/`Off`/`Transition`;
  `ViewControl.Track`/`TrackPressed`; `Device.Navigation`/`NavigationPressed`.
- **`Mixer.MuteOn`: the mute LED is "on" for a muted track.** It is also "on" for a track that
  another track's solo silences, although that track is not muted (its Track Activator stays
  on in Live). Both `tested` in 12.4.16 with the framework's own `ChannelStripComponent`, through
  the Faderfox UC4 script, which changes only the skin's values; the class sets the LED from
  `track.mute or track.muted_via_solo` (`observed` in the 12.4.16 index). A script that keeps
  that class gets the same LED logic in that build; one with a channel strip of its own may not. In the
  decompiled 12.0 framework the button was mapped to the track activator, where "on" meant
  playing: the behaviour changed between 12.0 and 12.4.16, so trust the build's. For a button
  labelled "Active" or "Track On", swap the values (`MuteOn = OFF`, `MuteOff = ON`); it then
  also goes dark for tracks a solo silences, unlike Live's Track Activator.
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
  `index` is its place (`tested` with the UC4's Monitor buttons in 12.4.16). Set `button.color = "My.SkinName"` to light it.
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

## A step sequencer

A drum step sequencer on a grid: one row of buttons per bar of steps, pads that pick the drum
sound the steps write, the clip's notes edited in place. v3 has the parts. Everything here is
from building one for the APC mini mk1 in Live 12.4.16: `tested` there unless marked. The
methods starting with `_` are the framework's private ones: `observed` in 12.4.16's index, and
they can change in another build. Look each one up in the user's build before you rely on it.

**The parts.** `StepSequenceComponent` (in `ableton.v3.control_surface.components`) holds a note
editor (the step buttons), a loop selector (one button per page of steps), Live's playhead and a
grid resolution. `DrumGroupComponent` is the pad bank and gives the steps their pitch.
`Step_Sequence` is not in the default component map (`observed`; Ableton's `APC_mini_mk2` has
none), so add it to the Specification's `component_map`, with the pad bank of your own (below)
in place of the default `Drum_Group`, and map them:

```python
component_map = {"Step_Sequence": StepSequenceComponent, "Drum_Group": PadBankComponent}

mappings["Step_Sequence"] = dict(step_buttons="steps", loop_buttons="page_buttons",
                                 resolution_buttons="resolution_buttons")
mappings["Drum_Group"] = dict(matrix="pads", scroll_up_button="up_button",
                              scroll_down_button="down_button")
```

- `scroll_up_button` and `scroll_down_button` reach the drum group's own scroll component through
  `__getattr__`: the validator lists them as not checked. One press moves the bank by a row of 4;
  a button that can't move further is off (`DefaultButton.Disabled`).
- The drum group's matrix puts the lowest pad bottom left: give the matrix its rows top first.

**Two dependencies the framework doesn't build.** The sequencer's `__init__` asks for a
`grid_resolution`, its note editor for a `sequencer_clip` (`observed`: `@depends`). The framework
injects `target_track`, `session_ring`, `full_velocity` and a few more, not these; the control
surface hands them in from `_get_additional_dependencies()`. Each value there is a function the
framework calls to get the dependency (`observed` in the statements of `get_dependency_for`), so
an object goes in wrapped in `const` (`ableton.v3.base`); the framework would call an object
passed bare (`observed`, not tried). The validator doesn't check this.

```python
from ableton.v3.base import const
from ableton.v3.control_surface import ControlSurface
from ableton.v3.control_surface.components import (
    AutoArmComponent, GridResolutionComponent, SequencerClip)
from ableton.v3.control_surface.components.grid_resolution import GRID_RESOLUTIONS

class My_Sequencer(ControlSurface):
    def _get_additional_dependencies(self):
        dependencies = super()._get_additional_dependencies() or {}
        resolutions = tuple(r for r in GRID_RESOLUTIONS if not r.is_triplet)
        dependencies["grid_resolution"] = const(
            GridResolutionComponent(resolutions=resolutions, default_index=1))
        dependencies["sequencer_clip"] = const(
            self.register_disconnectable(SequencerClip(target_track=self._target_track)))
        return dependencies

    def setup(self):
        super().setup()
        # the mappings can't hand one component to another: the pads give the steps their pitch
        self.component_map["Step_Sequence"].set_pitch_provider(self.component_map["Drum_Group"])
        # pads play only on an armed track (below)
        self._drum_auto_arm = AutoArmComponent(is_enabled=True)
```

- **Resolutions.** `GRID_RESOLUTIONS` (`observed`) holds eight, 1/32t to 1/4, each with its
  step length in beats: 1/16 is 0.25 and 1/8 0.5 (`tested`), 1/32 0.125 (`documented`). Without
  the triplets four remain: 1/32, 1/16, 1/8, 1/4. `resolution_buttons` are radio buttons, one per resolution; the active one gets
  `NoteEditor.Resolution.Selected`. A new note is one step long at the active resolution.
- **Notes.** A step press writes a note of the selected pad's pitch, one step long, velocity 100
  (`DEFAULT_VELOCITY`: the name `observed`, the value `tested`), 127 with Live's full velocity
  on (`documented`). A second press clears it.
- **The step buttons' channel.** The note editor moves its step buttons to MIDI channel 2
  (`DEFAULT_STEP_TRANSLATION_CHANNEL` = 1, `observed`); the LEDs still go out on the element's
  own channel (`tested`).

**The clip.** `SequencerClip` is the clip the steps edit. On an empty slot the note editor calls
its `create_clip(length)` on the first step press; it creates the clip in the target track's slot,
fires it at once with no quantization and legato, in phase with what plays (`observed` in the
statements, `tested`), and shows it in Live's detail view. Subclass it for a clip preset:

```python
from ableton.v3.live import get_bar_length, liveobj_valid

class PresetClip(SequencerClip):
    def create_clip(self, length=None):
        super().create_clip(length=2 * get_bar_length())   # 2 bars, whatever v3 asked for
        clip = self.clip
        if liveobj_valid(clip):
            clip.name = "Steps"
            clip.looping = True
        return clip
```

Which clip it edits comes from the target track: v3 takes the track's playing clip first, then
its clip in the selected scene (`observed`). Live still counts a clip as playing after the
transport stops, so the steps often edit another clip than the selected slot's. For "always the
selected slot", subclass `TargetTrackComponent`, override `_target_clip_from_session()` to return
the selected scene's clip on the target track, and set `target_track_component_type` in the
Specification. `ViewControlComponent`'s `prev_scene_button` and `next_scene_button` then move the
slot the steps edit.

**The pads.** Two things v3's drum group doesn't do on its own:
- **Select by pressing.** It selects a pad only while its select button is held, and its pads go
  to Live as notes without the script seeing them (`observed`). Build it with
  `matrix_always_listenable=True` and select in `_on_matrix_pressed`:

  ```python
  class PadBankComponent(DrumGroupComponent):
      def __init__(self, *a, **k):
          super().__init__(*a, matrix_always_listenable=True, **k)

      def _on_matrix_pressed(self, button):
          pad = self._pad_for_button(button)
          if liveobj_valid(pad):
              self._do_select_pad(pad, str(pad.name))
          super()._on_matrix_pressed(button)
  ```
- **Sound.** A pad press plays its sound only on an armed track. The framework builds its own
  auto-arm only with `include_auto_arming` and an identity reply (`observed`); without one,
  build `AutoArmComponent(is_enabled=True)` in `setup()`: the selected MIDI track gets Live's
  implicit arm, and steps back while the user arms a track by hand. Don't call it `_auto_arm`:
  the control surface's `__init__` sets an attribute of that name (`observed` in the statements;
  `check_names` doesn't list it).
- **Feedback.** Live sent no LED value for a pad the drum group played: light a held pad from the
  script (set its `button.color` in `_update_button_color`).
- **Which tracks.** The drum group finds a Drum Rack on the track or inside an Instrument Rack
  (`find_drum_group_device`, `ableton.v3.control_surface.instrument_finder`). On a track without
  one the pads stay dark; v3's note editor still tries to create a clip on a step press, so guard
  the note editor's `_on_pad_pressed` with the same finder if the steps should do nothing there.

**Pages and the loop.** The loop selector gives each of its buttons one bar of the clip
(`_update_matrix` and `_on_matrix_pressed` divide by its `bar_length`, `observed`). A subclass
whose `bar_length` property returns `self._paginator.page_length` makes each button one page of
steps; holding two buttons sets the clip's loop in pages. It has no "follow the playhead": a
subclass that sets `self._paginator.page_time` to the playhead's page from `_update_matrix` adds
it. Steps past the clip's loop end are shown like the others (no `StepDisabled`), and a note set
there extends the loop (`_add_note_in_step` calls `extend_loop_for_region`, `observed`).

**The playhead.** `StepSequenceComponent` builds a `PlayheadComponent` around
`c_instance.playhead`, Live's own playhead, which sends the playing step as note feedback. On the
APC mini mk1's port it sent nothing while the clip played: neither on v3's default notes 0-7 nor
on the 32 step notes on channel 2 (`tested` twice; cause not found, and Ableton's v3 scripts use
it). Try it first on the user's controller; if no step lights, draw the playhead in the note
editor:
- give the sequencer `note_editor_component_type=` a `NoteEditorComponent` subclass that listens
  to its clip's `playing_position` and `playing_status` (`@listens`; they fire often enough to
  light every 1/16 step at 120 BPM);
- return a skin name of your own from `_get_alternate_color_for_step(index, visible_steps)` for
  the playing step (the step's time is `self._page_time + index * self.step_length`); and
- give the sequencer `playhead_component_type=` a `PlayheadComponent` subclass that keeps Live's
  playhead off (its `update()` sets `self._playhead.clip = None`), so a later build doesn't draw
  a second one.

`Playhead.set_feedback_channels` takes a list: a tuple raises `Boost.Python.ArgumentError` when
the script loads. The same holds for Live's objects in general: where one takes a sequence, pass
a list. The validator doesn't see argument types.

**The skin.** The names the parts ask for are in 12.4.16's default skin (`observed`), with 127
and 0 (`documented`):
- `NoteEditor`: `StepFilled`, `StepEmpty`, `StepMuted`, `StepDisabled`, `NoClip`, and
  `NoteEditor.Resolution.Selected`, `NotSelected`;
- `LoopSelector`: `InsideLoopSelected`, `InsideLoop`, `OutsideLoopSelected`, `OutsideLoop`,
  `Playhead`, `PlayheadRecord`, `Navigation`, `NavigationPressed`;
- `DrumGroup`: `PadEmpty`, `PadFilled`, `PadSelected`, `PadMuted`, `PadMutedSelected`,
  `PadSoloed`, `PadSoloedSelected`, `PadAction`, `Scroll`, `ScrollPressed`.

The note editor and the drum group ask through `LiveObjSkinEntry`, so a name of your own
(`NoteEditor.Playhead`) that the skin lacks raises `KeyError` (Skins and LED values, above).

**The faders beside it.** `MixerComponent` reads its tracks from the session ring, so on a
controller with no identity reply the ring needs to enable itself (The Specification, above);
`volume_controls` and `master_track_volume_control` then set tracks 1-8 and the master.

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
`Python: INFO:<logger>:<ms> - <text>`; the number is the milliseconds of the record's time.
With `getLogger(__name__)` the logger's name starts with the folder name, so `scripts/log.sh
--script <Folder>` shows these messages (`tested` with the Faderfox UC4 script in 12.4.16).
`logger.exception(…)` keeps its traceback lines in the message. The template logs `ready` from `setup()`: when that line is
there, the whole Specification was built.
