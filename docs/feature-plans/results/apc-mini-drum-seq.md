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
| The note editor gives its step buttons a translation channel, channel 2 (`DEFAULT_STEP_TRANSLATION_CHANNEL` = 1, 0-based); LED feedback still goes out on the element's own channel, channel 1 | observed (the channel), tested (feedback on channel 1) |
| New notes: one step long, velocity 100 (`DEFAULT_VELOCITY`), 127 with full velocity | documented |
| Skin names: `NoteEditor.StepFilled`, `StepEmpty`, `StepMuted`, `StepDisabled`, `NoClip`, `NoteEditor.Resolution.Selected`/`NotSelected`; `DrumGroup.PadSelected`, `PadFilled`, `PadEmpty`, `PadMuted`, `PadSoloed`, `PadAction` | documented |
| The drum group's matrix puts the lowest pad bottom left (matrix rows top first) | documented |
| `Device.can_have_drum_pads` (a Drum Rack), `Clip.name`, `Clip.looping` | observed (Push 3 helper's proxy model) |
| A clip is created only on a track with a Drum Rack directly on it; v3's instrument finder also finds one inside another rack, where the pads work but no clip is created (v1's limit) | observed (the script's own code) |
| The created clip fires at once (`q_no_q`), so the transport runs | tested |
| In this script on the mk1's port, Live's own playhead (`PlayheadComponent`, `c_instance.playhead`) sent nothing while the clip played: neither with v3's default notes 0-7 on channel 2 nor with the 32 step notes on channel 2 (`DEFAULT_STEP_TRANSLATION_CHANNEL`) at `playing_feedback_velocity` 5 (cause not found; Ableton's own v3 scripts use it) | tested (two runs: step 1, step 2's first run) |
| `Playhead.set_feedback_channels` takes a Python list: a tuple raises `Boost.Python.ArgumentError` when the script loads | tested |
| v3's `LoopSelectorComponent` gives each loop button one bar (`_on_matrix_pressed`, `_update_matrix` divide by `bar_length`); a subclass whose `bar_length` returns the paginator's `page_length` makes each button one page, the playhead's page uses the skin's `LoopSelector.Playhead` and the shown one `InsideLoopSelected` | observed, tested (the subclass) |
| A clip that starts playing on the target track becomes the sequencer's clip at its launch, and the loop selector moves the page back to the clip's loop start (`set_clip`); `fire_clip` is quantized, so a page press before the launch is undone | tested |
| v3's note editor shows the whole page of steps past the clip's loop end (no `StepDisabled` there); a note added there extends the loop (`_add_note_in_step` calls `extend_loop_for_region`) | observed, tested (no colour change without our code) |
| `NoteEditorComponent._get_alternate_color_for_step(index, visible_steps)` overrides a step's colour when it returns a skin name; its `_page_time`, `step_length`, `_clip`, `_clip_notes` and `TimeStep.filter_notes` give the step's time and notes | observed, tested |
| `Clip.playing_position` and `playing_status` listeners (`@listens`) fire while a session clip plays, often enough to light every 1/16 step at 120 BPM | tested |
| A skin name the note editor or the pad bank asks for through `LiveObjSkinEntry` has no fallback: a missing one raises `KeyError` (so the skin sets every name) | documented |
| `MixerComponent`, `SessionComponent`, `ViewControlComponent`, `SessionNavigationComponent` depend on the session ring | observed |
| A pad press plays its sound only on an armed track: silent unarmed, heard armed by hand and with the script's auto-arm | tested |
| v3's `AutoArmComponent`, built by the script in `setup()` and enabled, sets the target track's implicit arm without identification | tested |
| The framework builds its own auto-arm only with `include_auto_arming` and an identity reply | observed |
| The auto-arm steps back while a track is armed by hand: track 9's auto-arm went off while the user armed track 1 (12.4.16's `_can_auto_arm` differs from 12.0's `any_track_armed`, the behaviour is the same) | tested (by hand, step 4) |
| Live sends no LED feedback for a pad the drum group plays (`matrix_always_listenable=True`), armed or not, at `playing_feedback_velocity` 3; the script's own `DrumGroup.PadPressed` lights it | tested |
| v3's drum group hands any `scroll_*` control to its `DrumGroupScrollComponent` (`__getattr__`), so `scroll_up_button` and `scroll_down_button` map on `Drum_Group`; one press scrolls a row of 4, rows 0-28; a button that can't scroll is off (`DefaultButton.Disabled`) | observed (the forwarding, `position_count`, `page_length`), tested (the rows, the LEDs) |
| After the transport stops, the sequencer keeps the clip that played last on the track (not the selected scene's) and its page | tested |
| `ControlSurface.drum_group_changed(drum_group)` is called from `__init__` right after `setup()` and on each instrument change of the target track | observed (statement order) |
| v3's note editor reads a clip's notes only when its clip changes (`set_clip`) or its notes change; with no Drum Rack the script's `_has_clip` is false, so the script re-sets the clip in `drum_group_changed` (`refresh_clip`) for a rack added later | observed (statements); the re-set not checked on the rig |
| `ElementsBase.add_submatrix(matrix, name, columns=(start, stop), rows=…)` names a part of a matrix as another element (`resolution_buttons` = scene buttons 1-4); `StepSequenceComponent.set_resolution_buttons` hands it to the `GridResolutionComponent`'s radio buttons (`resolution_buttons`, `checked_index`), whose index picks from the script's four resolutions (step 4; replaced in step 5 by two buttons, finer and coarser, plan 0003 Decision 29) | observed (signatures, statements), tested |
| At 1/8 a step press writes a note one step long (`[40, 0.5, 0.5, 100]` on step 2); the active resolution's button is on (1), the others off | tested |
| The framework builds the session ring when a component depends on it (`session_ring` among the injected dependencies, `_create_session_ring`), disabled; it is enabled only on an identity reply, so the script's `FaderRingComponent` enables itself and Live draws the box | observed (`_create_session_ring`), documented (the lazy injection, 12.0), tested (the box) |
| `ControlSurfaceSpecification.link_session_ring_to_track_selection` (and `…_scene_selection`) default to `False`; only with one of them set does registering a `ViewControlComponent` link the ring to the selection (`SessionRingSelectionLinking`) | observed, tested (the faders stay on tracks 1-8) |
| `MixerComponent` with `volume_controls` and `master_track_volume_control` (keys it answers by `__getattr__`): faders 1-8 set tracks 1-8's volumes (absolute, CC/127), fader 9 the master | tested |
| `ViewControlComponent`'s `prev_track_button` and `next_track_button` select the previous and next of Live's visible tracks, then the returns and the master (`all_visible_tracks`); a button with no track to move to is off; the sequencer and the pads follow the selection | observed (names), documented (the track list, 12.0), tested (the moves and LEDs) |

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
11. **`get_class` and `outline_reference_script` answer from the newest index, the Live 13 beta,
   when no build is named** (step 2: a lookup of a v3 class came back with the beta's build). Beta facts must stay out of what
   is published (`CLAUDE.md`), so a script author on a release is easily served beta facts.
   Asked again with `build: 12.4.16`. Open: a STATUS item (the newest release as the default).
12. **`validate` can't see a wrong argument type into Live's C++ objects:** a tuple for
   `playhead_channels` passed, and the script failed to load (`ArgumentError`). Not a validator
   rule; for the skill (step 6): Live's objects take lists where they take a sequence.
13. **`check_names NoteEditorComponent.…` resolves the bare name to
   `bar_based_sequence.NoteEditorComponent` first**, and reports `_page_time`, `_clip`,
   `_clip_notes` as not members, though `__init__` sets them (finding 5 again). The statements of
   `__init__` showed them. Open: with finding 5's STATUS item.
14. **A method whose body is one `return` expression has no statements** (`_button_position`):
   whether v3's loop buttons count bars or pages came from `_update_matrix`'s statements.
   Open: a STATUS item (statements for a returned expression).
15. **`validate` can't check mapping keys a component answers by `__getattr__`** (`scroll_up_button`
   on v3's `DrumGroupComponent`): "not checked", correctly. The forwarding was found in the
   decompile, not by a tool, and `check_names DrumGroupComponent.set_scroll_up_button` answered
   with v2's `SlideComponent`. Open: a STATUS item (say where a `__getattr__` forwards to).

16. **`check_names` doesn't know an attribute `add_button_matrix` creates** (`self.scene_buttons`
   in `add_submatrix(self.scene_buttons, ...)`): "unknown attribute scene_buttons". The element
   attributes come from `_create_attribute_name` at run time; the validator's element reader
   knows them. Open: a STATUS item.
17. **The rig's controller model didn't read `add_submatrix`** ("built by add_submatrix, which
   the rig doesn't read"). Fixed in step 4: `Controller.submatrices` names the part of a matrix
   built before it; no new elements, the panel unchanged. A slice past the matrix stops at its
   edge; a matrix with rows of different lengths is unresolved (the reviewer).
18. **A nested `state` field couldn't be checked**: `get_session_info` gives the master's volume
   as `master_track: {name, volume, panning}`, compared whole and exactly. Fixed in step 4: a
   nested field matches the fields it names, numbers within the tolerance.
19. **`rig run` ran an old copy of the script and didn't say so**: Live loads the copy in the
   User Library, which `install --replace` writes; after a `rig restart-live` without it the
   first step-4 run tested step 3's code (20 passed, 10 failed: no reply from any new control).
   Open: a STATUS item (warn when the installed copy differs from the check file's `script:`).

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

**Step 2, 2026-11-19, Live 12.4.16** (a fresh default Set; track 9 "Yellow Kit" created and
loaded through AbletonMCP after `rig restart-live`, the user selected its scene 1 slot; 120 BPM).
Three attempts:
- Live's playhead on the 32 step notes, `playhead_channels` a tuple: the script didn't load
  (`Boost.Python.ArgumentError` in `Playhead.set_feedback_channels(Playhead, tuple)`).
- The same with a list, `playing_feedback_velocity` 5: 7 passed, 3 failed. Live's playhead sent
  nothing on any note or channel while the clip played (track button 1 blinked); no red past the
  loop end; the page check pressed before the quantized launch.
- The script's own playhead and loop end (Decision 25), the page check split in two: 11 passed,
  0 failed, 1 asked.
- The playhead: each step gets 5 (yellow) when it plays and its own colour after, about 16 LED
  messages a second at 120 BPM; the last lit step goes back when the transport stops.
- On a 1-bar clip, steps 17-32 are red (3); the playhead stays in steps 1-16.
- On a 4-bar clip, track button 2 shows steps 33-64 (the note on beat 8 lights step 1 green),
  button 2 blinks (the playhead's page), button 1 goes off; the clip keeps `length` 16, looping,
  loop 0-16.
- `log: clean` in every step.

**Step 3, 2026-11-19, Live 12.4.16** (a fresh default Set after `rig restart-live`, track 9
"Yellow Kit" through AbletonMCP, the user selected its scene 1 slot). Three attempts:
- With `playing_feedback_velocity` 3 and no auto-arm: 17 passed, 3 failed. A held pad showed
  only the script's values (5, 2), no red; the user heard nothing, also with the pad held 2 s
  alone; armed by hand, the pad sounded, still with no red from Live. Two check mistakes: the
  note went to clip 3 (the clip that played last), and the steps are redrawn dark (0) on a track
  without a Drum Rack.
- With the script's auto-arm and `PadPressed` (Decisions 26–27): 19 passed, 0 failed, 2 asked.
  The user heard the held pad and saw track 9's arm button lit in Live's auto-arm colour.
- Scrolling: up a row puts 40 bottom left (yellow); 18 more presses reach row 28 (scene 5 off),
  28 down reach row 0 (scene 6 off, 5 on); a pad of the scrolled bank sets the pitch (40).
- A new MIDI track (created through AbletonMCP, selected by Live): pads dark, a step press
  creates no clip. `log: clean` in every step.

**Step 4, 2026-11-19, Live 12.4.16** (a fresh default Set after `install --replace` and
`rig restart-live`, track 9 "Yellow Kit" through AbletonMCP, the user selected its scene 1 slot).
The first run used step 3's installed copy (finding 19). The second: 29 passed, 0 failed,
3 asked; all of steps 1-3 still pass. The third, after the review (the ring's link to the
selection set explicitly, a check for it): 30 passed, 0 failed, 3 asked.
- Resolution: scene button 3 sets 1/8 (on; button 2 off); step 2 then writes `[40, 0.5, 0.5,
  100]` in clip 3 (the clip that played last); scene button 2 sets 1/16 again.
- Track choice: from track 10 scene button 7 selects track 9 (the selected pad blinks green
  again), scene button 8 track 10 (pads dark); nine presses more reach track 1, where scene
  button 7 is off; scene button 8 lights it again.
- Faders: with track 10 selected, fader 1 at 90 gives track 1 0.709 (the ring stays on tracks
  1-8); fader 1 at 100 gives track 1 a volume of 0.787, fader 8 at 64 track 8 0.504, fader 9
  at 127 the master 1.0.
- The user saw the box around tracks 1-8, and, by hand, track 9's auto-arm go off while track 1
  was armed. `log: clean` in every step.

**Step 5, first task, 2026-11-19, Live 12.4.16** (the test Set after a restart with the fork's
AbletonMCP, track 9 "Yellow Kit" created and loaded through AbletonMCP at the user's request; the
rig selects the slot itself now, plan 0002 Decision 29): 31 passed, 0 failed, 2 asked.
- `select-track`: `select_clip_slot` selected track 9 and scene 1; `get_session_info` read back
  `selected_track: 9`, `selected_scene: 1`. The track-choice steps read the selected track as
  10, 9, 10, 1 and 2. The user saw Session View's selection jump at the start and at the end:
  `select_clip_slot` and the two fields are `tested` (12.4.16).
- The user heard the kit while the rig held the pad, and saw the box around tracks 1-8 and the
  master. Whether track 9's arm button was lit wasn't answered this time (step 4's run saw it).
- `create_clip` and `fire_clip` joined `TESTED` (the user saw the clips and heard them);
  `create_midi_track` and `stop_playback` are read back by the rig but not yet confirmed by the
  user. Confirmed later the same day: the user saw track 10 and the stopped transport; both
  joined `TESTED`.

**Step 5, Decisions 29-30, 2026-11-19, Live 12.4.16** (after `install --replace` and `rig
restart-live`, track 9 "Yellow Kit" again through AbletonMCP): with the scene buttons and the
resolution on two buttons, 35 passed, 0 failed, 2 asked; with the resolution pads, 37 passed,
0 failed, 2 asked. The user: the pad heard and track 9 armed (later track 2, the run's last
selection, armed instead: auto-arm follows the selection), the box around tracks 1-8, the
master at +6 dB (fader 9 at 127 is volume 1.0).

## The user's results

**The panel, 2026-11-19, Live 12.4.16** (`rig panel`, the test Set after the 37-passed run; plan
0003 Decision 14). The user went through nine points, limited to what was new or checked only
by the rig:
1. the resolution pads: the active one yellow, a press sets it: works;
2. scene buttons 1-2, finer and coarser, off at the ends: work;
3. a pattern at 1/16 closes up or spreads out at 1/8 and 1/32: works;
4. scene buttons 3-4 move the selected slot; with nothing playing the grid shows its clip: works;
5. on an empty slot the first step press creates the 2-bar "Drum Seq" clip: works;
6. a kick and snare pattern plays as set: works;
7. the playhead runs with the beat: "pretty sure", the delay makes it hard to tell; pressing
   feels immediate;
8. steps set or cleared while it plays are heard on the next pass: works;
9. pages on a clip longer than 2 bars, the playhead's page blinking: works.

What the user missed: the page doesn't follow the playhead when the clip is longer than the 32
steps show (as Push's sequencer does): plan 0003 Decision 31. Stopping a clip from the
controller was left out: the user stops it in Live.

Later on the panel (Decision 31): the steps follow the playhead, a picked page holds while the
clip plays.

**The APC mini, 2026-11-19, Live 12.4.16** (the slot on APC MINI; plan 0003 Decisions 12, 14).
First part, with the Yellow Kit: most points worked; two problems with one cause, fixed by
Decision 32 (the steps edit the selected slot, playing or not): a step press on an empty slot
while the transport ran wrote into the track's playing clip, and a Drum Rack added to a track
with a playing clip seemed to take no notes (Live counts a clip as playing after the transport
stops; tracks 1-8 of the test Set each had one). After the fix (`rig run`: 40 passed with the
Yellow Kit, 40 passed with the 808 Core Kit on track 9), the user: "its working right now. Also
switching the rack." No dropped press was reported: the old drops are explained by the plain
`ControlSurface`'s LED flood, not the unit (Decision 12).

**The user's test list, 2026-11-19, Live 12.4.16** (16 points, critical first):
- works: the steps edit the selected clip while another plays (Decision 32); an empty slot
  while playing creates a running clip; following comes back after a transport restart; the
  loop gesture on the APC; a picked page holds; the panel's Shift-click, Cmd-click, Esc and `?`;
  a return or master track selected; the last scene; no dropped press.
- a new clip starts at once, legato (v3's `create_sequencer_clip` fires it with
  `force_legato=True` and no quantization, 12.4.16 bytecode): it runs in phase with the playing
  clip, which the user heard as "quantized, with the next upbeat".
- not working: notes on a track with the Young Blood Kit, an Instrument Rack around a Drum Rack;
  fixed by Decision 33 (rig: 40 passed with the Yellow Kit, 5 passed on a Young Blood Kit track).
- no pad preview on the APC: the APC's input had Track off (the architect's advice, wrong); the
  rig's port has it on. With Track on, Live plays the pads on the armed track.
- in Arrangement View the steps edit the clicked clip, but the playhead and following don't run
  (they read the clip's playing position; not in this plan's scope).
- wishes for later: pad preview as an option; auto-duplicating the content the first time the
  loop gets longer (as Elektron does); a way back to following (Decision 34).
