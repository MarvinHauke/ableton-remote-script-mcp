# Results: the APC mini mk1 drum sequencer (plan 0003)

The script is `examples/APC_mini_drum_seq/`, built step by step with the skill and the MCP server
(`ableton-remote-script`, Live 12.4.16). This page holds the facts it relies on, the tool
findings, the rig runs and the user's panel and hardware results (Decision 18).

## Facts the script relies on

Live 12.4.16. `observed`: in the index. `documented`: read in gluon's decompiled 12.0 framework
(local only), to be checked on the rig. `tested`: seen working on the rig or the device.

| Fact | Confidence |
|---|---|
| v3's default component map has no `Step_Sequence`; a script adds `StepSequenceComponent` itself (APC_mini_mk2's map has none, Move's adds its own) | observed |
| `StepSequenceComponent.__init__` depends on `grid_resolution`, its note editor on `sequencer_clip`, `target_track`, `full_velocity`; the framework injects only `target_track`, `full_velocity`, `session_ring`, `playhead` and a few more, the rest come from the control surface's `_get_additional_dependencies()` (Move: a `GridResolutionComponent` and a `SequencerClip`; Launchkey MK4: a `SequencerClip`) | observed |
| Each value `_get_additional_dependencies()` returns is a function the framework calls to get the dependency (`get_dependency_for` returns `accessor()`), so an object goes in as `const(obj)` (`ableton.v3.base.const`) | observed (statements) |
| v3's drum group sends its pads to Live as notes without the script seeing them unless built with `matrix_always_listenable=True` (`PlayableComponent.__init__`), and selects a pad on a press only while its select button is held (`_on_matrix_pressed`); the script's `PadBankComponent` listens and selects (`_pad_for_button`, `_do_select_pad`) | observed (signatures, statements) |
| The target clip is the clip playing on the selected track, else its clip in the selected scene; `prepare_new_clip_slot` may move the selected scene to an empty slot (Decision 22) | documented |
| The mappings can't hand a component to another: the pitch provider is set in `setup()` with `component_map["Step_Sequence"].set_pitch_provider(component_map["Drum_Group"])` (Launchkey MK4 does the same from code) | observed (statements) |
| `SequencerClip.create_clip(length)` creates the clip in the target track's slot (`prepare_new_clip_slot`), fires it at once and shows it in the detail view; the note editor calls it on the first step press of an empty slot | observed (statements) |
| `GridResolutionComponent(resolutions=, default_index=)`; `GRID_RESOLUTIONS` holds 1/32t … 1/4 with step lengths in beats; four without triplets give 1/32, 1/16, 1/8, 1/4 | observed (names), documented (values) |
| The note editor gives its step buttons a translation channel (channel 2) so Live's own playhead can light them; LED feedback still goes out on the element's own channel | documented |
| New notes: one step long, velocity 100 (`DEFAULT_VELOCITY`), 127 with full velocity | documented |
| Skin names: `NoteEditor.StepFilled`, `StepEmpty`, `StepMuted`, `StepDisabled`, `NoClip`, `NoteEditor.Resolution.Selected`/`NotSelected`; `DrumGroup.PadSelected`, `PadFilled`, `PadEmpty`, `PadMuted`, `PadSoloed`, `PadAction` | documented |
| The drum group's matrix puts the lowest pad bottom left (matrix rows top first) | documented |
| `Device.can_have_drum_pads` (a Drum Rack), `Clip.name`, `Clip.looping` | observed (Push 3 helper's proxy model) |
| A clip is created only on a track with a Drum Rack directly on it; v3's instrument finder also finds one inside another rack, where the pads work but no clip is created (v1's limit) | observed (the script's own code) |
| The created clip fires at once, so the transport runs and `PlayheadComponent` already drives Live's playhead (notes 0-7 on channel 2 by default, feedback velocity from `playing_feedback_velocity`, 127 by default): step 2's starting point | documented |
| A skin name the note editor or the pad bank asks for through `LiveObjSkinEntry` has no fallback: a missing one raises `KeyError` (so the skin sets every name) | documented |
| `MixerComponent`, `SessionComponent`, `ViewControlComponent`, `SessionNavigationComponent` depend on the session ring | observed |

## Tool findings

What was missing, wrong or awkward while writing the script, with what was asked and what came
back. Fixed in step 1 unless a STATUS item is named.

1. **`lookup class` crashed on a cut answer** (`KeyError: 'all_members'`, `cli.py`
   `_format_class`), e.g. `lookup class Live.Clip.Clip`: the cap had taken keys out of the class.
   Fixed: the text output prints the parts left and says which members were cut (test in
   `tests/test_mcp_server.py`).
2. **`validate` warned `session-ring` for a script without a session ring.** The sequencer maps
   no component that uses the ring, so the missing identity reply doesn't matter. Fixed: the rule
   warns only when a mapped component depends on the ring (`@depends(session_ring=…)` along its
   MRO) or the mappings can't be read (local-only tests).
3. **`element-name` gave up on `**NOTE` in `add_button_matrix(..., **NOTE)`** ("builds some names
   in a loop or by computation"), although the names were literal. Written out as
   `msg_type=MIDI_NOTE_TYPE`, the names are checked. Open: a STATUS item for the validator.
4. **The rig and the validator can't read MIDI numbers a script's own helper computes**
   (`grid_rows(4, 7)`: "can't be worked out without running the script"). Rows as `range(…)`
   lists are read. For the skill: write element numbers as literals or ranges (step 6's skill
   section).
5. **`check_names` calls `ControlSurface.component_map` not a member:** it is set in
   `ControlSurfaceMappingMixin.__init__` as an instance attribute. The skill already uses
   `self.component_map[...]` (tested on the UC4). Open: a STATUS item.
6. **`get_class` shows no `@depends` of a component** in a way that answers "what must I inject?":
   the decorators are on `__init__`, but which of them the framework provides needs the
   statements of `ControlSurface._create_extended_injector`, which no tool prints. Found by reading
   the statements file by hand. Open: a STATUS item (an `outline` or `get_class` note on
   injected dependencies).
7. **Nothing tells a script author that `_get_additional_dependencies()` takes functions**, and
   `validate` passes a script that returns objects, which fails when Live loads it. Caught by the
   reviewer from the statements of `get_dependency_for`. Open: a STATUS item (a validator rule, a
   line in the skill's v3 reference with step 6).
8. **`lookup class DrumGroupComponent` (the short name) prints only the cut note**: the name
   matches 16 classes, and the cap keeps none of them ("kept classes 0 of 16"). The full name
   works. Open: a STATUS item, with finding 10 (a list of the matching names when none fits).
9. **`outline_reference_script("Launchkey_MK4")` shows no specification, component map or
   mappings** (known since the spec): its Specification is built by a function. The mappings were
   found in the statements file by hand. Open: a STATUS item.
10. **`get_class("Clip")` returns skin and notification classes named `Clip`** and cuts
   `Live.Clip.Clip` (known since the spec). Open: a STATUS item.

## Rig runs

**Step 1, 2026-11-19, Live 12.4.16** (the test Set with track 9 "Yellow Kit", a Drum Rack; the
script on `ARS Test Rig`, AbletonMCP 1.7.1): 6 passed, 0 failed, 1 asked, twice (the second run
after the user deleted the clip; the result file stays local). The user confirmed the selection (track 9,
scene 1) and saw the note set.
- A pad press selects that pad: its LED turns green (1), the one selected before turns yellow
  (5), the pad with a sound. While held, the pressed pad first shows yellow, then green.
- On the empty slot, the first step press created "Drum Seq": 8 beats, looping, one note
  `[36, 0, 0.25, 100]` (C1, one 1/16 step, velocity 100); step 1's LED turned green. A second
  press cleared the note and the LED.
- After a press on the pad for 37, step 5 wrote `[37, 1.0, 0.25, 100]`.
- `log: clean` in every step.
- So these are now `tested` in 12.4.16: the `const` dependencies, the pad bank that selects,
  the clip preset, velocity 100, the step skin values, the lowest pad bottom left
  (`pads[12]` = 36).
- The user heard the kit during the second run. The rig's pad presses are 20 ms taps and the new
  clip plays its note too, so whether a pad press itself still sounds while the pad bank listens
  (`matrix_always_listenable=True`) is not told apart: the panel (a held pad) or the hardware
  decides it, at the latest in step 7.
- Live's own playhead sent nothing to the port, although the new clip played (the default
  playhead notes 0–7 on channel 2). Step 2's question (Decision 17).

## The user's results

Not yet (panel and hardware after step 7, Decision 14).
