# 0003 — A drum step sequencer for the APC mini mk1

_Stage: in work — spec and steps written 2026-11-19 (Decisions 17–20), steps approved by the user 2026-11-19 (Decision 21). Frontier: step 5; step 1 done 2026-11-19 on `feat/0003-step-1-tracer` (rig: 6 passed), step 2 done 2026-11-19 on `feat/0003-step-2-playhead` (rig: 11 passed, Decisions 24–25), step 3 done 2026-11-19 on `feat/0003-step-3-pad-bank` (rig: 19 passed, Decisions 26–27), step 4 done 2026-11-19 on `feat/0003-step-4-resolution-tracks-faders` (rig: 30 passed, Decision 28); step 5 on `feat/0003-step-5-hardware`: the panel run gave Decisions 29 (scene choice, resolution on two buttons), 30 (resolution pads) and 31 (the page follows the playhead); the APC run gave 32 (always the selected slot), the user's test list 33-35 (nested Drum Rack, follow again, own repo); Decision 36 (the repo `APC_mini_mk1_Plus`, the script `APC_mini_mk1_Plus`, a submodule) built 2026-11-19 on `feat/0003-own-repo`; next: step 6._
_Depends on: 0001 (the skill, the MCP server), 0002 (the test rig: its steps 6a and 6b before step 1; Decision 19)._

## Problem

The user wants to program drums on the APC mini mk1 from its grid, without the mouse. No script
does that for this controller. It is also the first job for our tools that works on Live's clips
and notes rather than only mapping controls onto components. That part of the API is where the
index is thinnest, and none of our eval cases covers it yet. The APC mini dropped presses under
the plain `ControlSurface`'s LED flood; since `OptimizedControlSurface` the user has seen none,
not yet confirmed (Decision 12). The test rig checks what the hardware can't show.

## Solution

A v3 Remote Script for the APC mini mk1, `examples/APC_mini_drum_seq/`, that turns the grid into
a **step sequencer** for a Drum Rack track (Decisions 3–16): the top four rows are 32 steps of
the selected drum pad, the bottom four rows a 4×4 **pad bank** that picks the pad and plays it.
It works on the selected track's selected clip slot and creates a clip from the **clip preset**
on an empty slot. It is written with the skill and the MCP server, the way a user would, and
every lookup that is missing or awkward becomes a finding for the skill or the server. It is
checked on the test rig, step by step, then played by the user on the panel and on the
hardware. What it teaches goes into the skill as `tested` facts (Decision 13).

What the 12.4.16 index offers (`observed`, looked up 2026-11-19 with the MCP server):
- `ableton.v3.control_surface.components.step_sequence.StepSequenceComponent`: `set_step_buttons`,
  `set_loop_buttons`, `set_resolution_buttons`, `set_prev_page_button`, `set_next_page_button`,
  `set_pitch_provider`, the property `note_editor` (Decision 29 adds our own finer and coarser
  resolution buttons, `StepResolutionComponent`). Its `__init__` takes `grid_resolution`
  (injected), `playhead_component_type`, `playhead_notes`, `playhead_triplet_notes`,
  `playhead_channels`. The draft said it has a `playhead` property: only
  `Launchkey_MK4.step_sequence.StepSequenceComponent` adds one; the base builds its playhead
  from `playhead_component_type`.
- `ableton.v3.control_surface.components.playhead.PlayheadComponent`: takes `playhead`,
  `sequencer_clip` and `grid_resolution` as dependencies, plus `paginator`, `notes`,
  `triplet_notes` and `channels`. It hands the clip, the start time and the step length to the injected `playhead`
  object; the LEDs are lit by Live, not by Python (read in gluon's 12.0 decompile, `documented`
  for 12.4.16). Whether that reaches the mk1's note LEDs is step 2's question (Decision 17).
- `SequencerClip.create_clip(length=None)` and the `clip` setter, in the same module.
- `ableton.v3.control_surface.components.drum_group.DrumGroupComponent`: `set_matrix`,
  `set_drum_group_device`, `select_drum_pad`, `assigned_drum_pads`; a `PitchProvider`.
- `ableton.v3.control_surface.components.drum_group_scroll.DrumGroupScrollComponent`:
  `set_scroll_up_button`, `set_scroll_down_button` (from `PageComponent`).
- `ableton.v3.control_surface.components.view_control.ViewControlComponent`:
  `set_prev_track_button`, `set_next_track_button` (Decision 15). Its `__init__` depends on a
  `session_ring`, so step 4 finds out where v1 gets one without a session mode (Decision 5).
- Reference scripts to read with `outline`: `Launchkey_MK4` and `Move` (v3 step sequencers),
  `APC_mini_mk2` (v3, `Drum_Group`, `View_Control`, the mk1's sibling with other MIDI numbers).
  `Launchkey_MK4`'s outline shows no mappings section: a finding for the server (step 1).

Device facts: [milestone-1/apc-mini-mk1.md](milestone-1/apc-mini-mk1.md), "Device facts"
(`documented` from Akai's protocol, confirmed for this unit by the step 9 load test).

## User Stories

1. As a drummer, I want to set and clear steps of a drum pad from the APC's grid, so that I can
   program a beat without the mouse.
2. As a drummer, I want to pick the drum pad from the grid and hear it, so that I know which
   sound I am programming.
3. As a drummer, I want to see the notes, the playhead and the loop end on the grid, so that I
   know where I am in the pattern.
4. As a drummer, I want a new clip made for me on an empty slot, so that I can start with one
   press.
5. As a drummer, I want to page through a longer clip, change the step resolution and move
   between tracks from the APC, so that I rarely need the mouse.
6. As a drummer, I want the faders to set track volumes, so that I can mix while I program.
7. As a maintainer, I want each part of the sequencer checked on the test rig before the user
   plays it, so that the hardware test only covers what the rig can't see.
8. As a maintainer, I want every gap the skill and the MCP server showed while writing it
   written down and fixed or filed, so that the next script with clips and notes goes better.
9. As a script author using the skill, I want the sequencer components as a `tested` section of
   the v3 reference, so that I can build a step sequencer for my own controller.

## Implementation Decisions

- **Framework:** `ableton.v3` (`ControlSurface`, `ControlSurfaceSpecification`, elements, a
  component map, mappings), like `examples/Faderfox_UC4/`. Our own code only where v3 doesn't
  fit the mk1 (Decision 4): the skin (three colours and blinking, Decision 10), the clip preset
  (Decision 16), and the playhead if v3's doesn't reach the mk1 (Decision 17).
- **Files:** `examples/APC_mini_drum_seq/` with `__init__.py` (`create_instance`, the
  Specification), `elements.py`, `skin.py`, `mappings.py`, `components.py` (our own), and
  beside them `checks.yaml` and `device.yaml` (Decision 6). MIT, our own code; nothing copied
  from the decompiled references.
- **Elements** (device facts, channel 1): `steps` = grid rows 5–8 (notes 32–63) as a 8×4
  matrix in the order v3's note editor expects; `pads` = the bottom four rows' left half as 4×4
  (Decision 3; which half is the builder's choice, told to the user); `track_buttons` 64–71;
  `scene_buttons` 82–89; `shift_button` 98 (unmapped in v1); `faders` CC 48–55 and
  `master_fader` CC 56; `resolution_pads` = notes 28–31, the right half's top row, 1×4
  (Decision 30). The right half's three lower rows stay dark in v1.
- **Mappings:** `Step_Sequence` (step buttons, loop buttons = track buttons, finer and coarser
  resolution = scene 1–2, pitch provider = `Drum_Group`), `Drum_Group` (pads), `Drum_Group_Scroll`
  (scene 5–6), `View_Control` (scene 3–4 prev/next scene, 7–8 prev/next track), `Mixer` (faders,
  master). Scene 1–4 were the four resolutions until Decision 29; the resolution pads (notes
  28–31) are `resolution_buttons` since Decision 30. Each name and
  key is looked up with the MCP server and passed by `validate` and `check_names`.
- **Target:** the selected track (v3's `Target_Track`) and its clip slot in the selected scene
  (Decision 8, 15); no Drum Rack → pads dark, steps inert.
- **Clip preset** (Decision 16): 2 bars (8 beats in 4/4), looping over the whole clip, named
  "Drum Seq"; new notes one step long, velocity 100 (Decision 11). Constants in one place in
  `components.py`.
- **Results page:** `docs/feature-plans/results/apc-mini-drum-seq.md` (Decision 18): facts
  with build and confidence, the tool findings, the rig runs, the user's panel and hardware
  results.

## Testing Decisions

- **No new package code is planned** (two fixes found in step 1: Decision 23; two rig
  additions in step 4: Decision 28). The script is an example, so its seams are the existing
  ones: `validate` and `check-names` (no errors, no unknown names), `outline` of the folder,
  and the rig.
- **Local-only tests** (`local_live`, like the UC4 example's): the example validates clean
  against 12.4.16, its controller model has the elements above, its check file and device
  profile name only its elements.
- **The rig, step by step** (Decision 20): each step adds its checks to `checks.yaml` and runs
  them against Live (the test Set, a Drum Rack track). Steps on notes use `state` of a clip
  (0002 step 6b); LED steps use the replies Live sends (Decision 2). Every check passed in a
  step stays passed in the next.
- **The user:** loading the script (a slot with `ARS Test Rig`), then at the end the panel and
  the hardware (Decisions 12, 14). Anything seen only on this unit stays on the results page.
- **Prior art:** `examples/Faderfox_UC4/checks.yaml`, `tests/test_local_live.py`.

## Decisions

1. **The sequencer comes before the 9a round with the MCP tools** (user, 2026-11-19, asked which
   open work brings new information). It is built with the skill and the MCP server and tested
   on the rig. A short eval round follows, with a sequencer case and 2–3 runs; the big
   round comes at the end (0001 Decision 55). Rejected: a full eval round now, which costs
   much and would most likely repeat 100% graders and 0 unknown names.
2. **The rig may read and set a clip's notes** (user, 2026-11-19, open question 7, "allow the
   note check"): AbletonMCP's `get_clip_notes`, `add_notes_to_clip` and
   `clear_notes_from_clip` are on the rig's allow-list (0002 Decision 25), untested until read
   back against a state set by hand. The rig also records the LED messages, so the playhead and
   the step LEDs are checked from what Live sends.
3. **One drum pad at a time** (user, 2026-11-19, Q1 "a"): the top four rows are 32 steps of the
   selected drum pad, the bottom four rows a 4×4 drum pad bank that picks the pad and plays its
   sound. v3's model: one pitch from a pitch provider. Rejected: 8 lanes × 8 steps (all our own
   code), 64 steps with the pad picked elsewhere.
4. **v3's components** (user, 2026-11-19, Q2): `StepSequenceComponent`, `DrumGroupComponent` and
   `DrumGroupScrollComponent` (all `observed` in 12.4.16), our own code only where they don't fit
   the mk1, mainly its skin (three colours and blinking). Direct calls into the `Live` clip API
   can follow in a later step where v3 falls short.
5. **v1 is the sequencer only** (user, 2026-11-19, Q9); a session mode comes later as its own step.
6. **`examples/APC_mini_drum_seq/`, shipped with the repo** (user, 2026-11-19, Q10): our own code,
   MIT, with `checks.yaml` and `device.yaml` beside it, like the UC4 example.
7. **Ready to build with the MCP tools** (architect, 2026-11-19, Q12; the user's answer was about
   shipping, recorded in Decision 6): the skill's "With the MCP
   server" section and the server's registration for this project are in (STATUS). A one-run
   check of `uc4-mixer-v3` after the section went in: with the skill 9/9 graders, 0 findings;
   without 7/9. The eval sandbox has no MCP server, so the run used the CLI; the MCP tools are
   measured in the later MCP round (0001 Decision 55).
8. **The clip** (user, 2026-11-19, Q3): the selected track's selected clip slot. On an empty slot
   the first step press creates a 2-bar clip (`SequencerClip.create_clip(length)`, `observed`).
   A track without a Drum Rack leaves the pad bank dark and the steps inert.
9. **The other controls** (user, 2026-11-19, Q4):
   - track buttons 1–8: v3's loop buttons, one page of 32 steps each (replaces previous/next page;
     amended by Decision 31: the page also follows the playhead, a pick pauses it);
   - scene buttons 1–4: resolution 1/32, 1/16, 1/8, 1/4; 5–6: scroll the pad bank up and down by
     a row (`DrumGroupScrollComponent`) (1–4 amended by Decision 29: 1–2 finer and coarser,
     3–4 previous and next scene);
   - scene buttons 7–8 and Shift: free in v1, Shift kept for the later session mode (7–8 amended
     by Decision 15: previous and next track);
   - faders 1–8: track volumes; fader 9: master volume, as on the mk1 example.
10. **LEDs** (user, 2026-11-19, Q5):
    - steps: a note green, empty off, the playhead yellow, beyond the loop end red (the mk1 has
      no dim colour);
    - pads: the selected one green blinking, one with a sound yellow, empty off, red while held;
    - track buttons (red): the current page on, the playhead's page blinking;
    - scene buttons (green): the active resolution on, the scroll buttons on when they can scroll,
      7–8 on when there is a track to move to (Decision 15). Amended by Decision 29: 1–2 on
      while there is a finer or coarser resolution, 3–4 while there is a scene to move to.
    - Amended by Decision 30: the resolution pads, the active one yellow, the others off.
11. **Fixed note length and velocity** (user, 2026-11-19, Q6): one step long, velocity 100, no
    fader for velocity in v1 (this unit's faders jump, 0001 Decision 29). Replaces the draft's
    fader 9 for velocity.
12. **The hardware is a normal test device again, until shown otherwise** (user, 2026-11-19, Q8):
    with the current mk1 script every message the user sent came through, even with many LEDs
    running, but the user isn't sure the drops are gone; the sequencer's hardware check decides.
    The drops were seen with the plain `ControlSurface`'s 80–320 LED messages a second; `OptimizedControlSurface` cut that to
    about 50 ([milestone-1/apc-mini-mk1.md](milestone-1/apc-mini-mk1.md)). So:
    - the user plays a short pattern and watches the playhead and LEDs; ReceiveMIDI runs only when
      a press seems missing;
    - something seen only on this unit stays on the results page, never in the skill;
    - the moving playhead is steady LED traffic: if no press drops, the results page says the old
      finding is explained by the LED flood, not the unit.
13. **What goes into the skill** (user, 2026-11-19, Q11): once the rig checks and the hardware
    check pass, the sequencer components as a `tested` section of the v3 reference and the rig
    (0002 Decision 20); then a sequencer eval case and its 2–3 runs.
14. **The web panel as a test stage** (user, 2026-11-19, a question in round 2, then "yes to
    a-d"):
    - `device.yaml` gets an optional `leds` map (value → colour and blinking), so `rig panel`
      draws the APC's grid in its colours (`documented`, Akai's protocol, confirmed for this unit
      by the step 9 load test, [milestone-1/apc-mini-mk1.md](milestone-1/apc-mini-mk1.md); grid: 0 off, 1 green, 2 green blinking, 3 red, 4 red
      blinking, 5 yellow, 6 yellow blinking; track buttons red, scene buttons green, 0 off,
      1 on, 2 blinking), laid out by the profile's `layout`;
    - test order: the rig's checks, then the user plays a pattern on the panel, then the same
      short pattern on the hardware (Decision 12);
    - the colours reach the page as a new optional field in the panel's `model` message, an
      addition to protocol 1 (0002 Decision 26), with the rule that clients ignore unknown fields;
    - built by the rig builder as part of 0002 step 6, before the sequencer's rig checks.
15. **Track choice without the mouse** (user, 2026-11-19, round 4, "as recommended"): scene
    buttons 7 and 8 select the previous and next track, lit when there is one to move to (the API,
    for example v3's `ViewControlComponent`, named with its build and confidence in the steps); the
    clip slot follows Live's selected scene (Live's arrow keys). The mouse stays a fine way in
    v1. Rejected for v1: Shift + scene 7/8 for scenes (Shift stays for the session mode).
    Amends Decision 9 (scene buttons 7–8 were free).
    Confirmed for the hardware script (user, 2026-11-19): the panel only mirrors the APC.
16. **A clip preset** (user, 2026-11-19, "a", then "yes"): a clip the sequencer creates on an
    empty slot is 2 bars, looping, loop = the whole clip, named "Drum Seq"; new notes as in
    Decision 11. Fixed in code for v1; editable presets (a file, or chosen on the device) later.
    Rejected for v1: loading a Drum Rack onto a track that has none (browser API, out of scope).

17. **The playhead: v3's first, our own if it doesn't reach the mk1** (architect, 2026-11-19,
    spec; no contract changes). v3's `PlayheadComponent` leaves the lighting to Live's own
    playhead object, on the notes and channels the script gives it. Step 2 tries it with the
    mk1's step notes on channel 1 and the yellow value (5) and records what Live sends. If the
    rig sees no playhead LEDs, or ones the mk1 can't show, the script draws the playhead itself
    from the clip's playing position (`Clip.playing_position`: in 12.4.16 `observed` in the
    Push 3 helper's proxy model and `documented` by Structure Void; its listener is checked in
    step 2) through a `playhead_component_type` of our own. Either way
    the result is a `tested` fact for the skill.
18. **The results page is `docs/feature-plans/results/apc-mini-drum-seq.md`** (architect,
    2026-11-19, spec): milestone 1 is complete, so this plan's page doesn't go into its folder.
    A new folder `results/` holds result pages from here on; milestone 1's pages stay where
    they are.
19. **Plan 0002's step 6 is split around this plan's steps** (architect, 2026-11-19, steps):
    6a, the panel's LED colours (0002 Decision 26), and 6b, a clip's notes in check files plus
    the note commands on the tested list (0002 Decision 25). The sequencer's check file and
    device profile, which 0002 step 6 named, grow in this plan's steps (Decision 20). Order:
    0002 6a → 0002 6b → 0003 1 → 2 → 3 → 4 → 5 → 6 → 7, so the LED colours come before the
    sequencer's first rig checks, as Decision 14 says.
20. **The checks grow with the script** (architect, 2026-11-19, steps): each step adds its
    checks to `checks.yaml` and passes them against Live before it is done; `device.yaml` comes
    in step 1 with the layout and the `leds` map (0002 6a is in by then). A step that needs the
    user in Live says so in its checks, and the user is asked once per step.
21. **The steps are approved as written** (user, 2026-11-19): order and content as in Steps;
    step 1 is built on `feat/0003-step-1-tracer`, branched from 0002 step 6b's branch.
22. **The clip: the track's playing clip first, as v3 does** (replaced by Decision 32) (user, 2026-11-19, step 1 review;
    amends Decision 8). v3's target track takes the clip that plays on the selected track and
    the selected scene's slot only when none plays (`documented`, 12.0 decompile; checked on the
    rig). The script keeps v3's behaviour, which Ableton's own sequencers have. Rejected: a target
    track class of our own that always takes the selected slot.
23. **Two package fixes in step 1** (architect, 2026-11-19, step 1; amends Testing Decisions'
    "no new package code"): `lookup class` prints a class whose answer was cut instead of raising
    `KeyError`, and the validator's `session-ring` warning fires only when a mapped component
    depends on the session ring (`@depends(session_ring=…)` along its MRO) or the mappings can't
    be read. Neither changes a contract: the answer core, the MCP tools and the exit codes are
    as before. Narrows plan 0001 step 10's rule (0001 Decision 48).
24. **Track buttons: one page each** (user, 2026-11-19, step 2; amends Decision 9's "v3's loop
    buttons"). In 12.4.16 v3's `LoopSelectorComponent` gives each button one bar (`observed`:
    `_on_matrix_pressed`, `_update_matrix` divide by `bar_length`), so at 1/16 button 2 would show
    steps 17–48. The script's `PageLoopSelectorComponent` returns the paginator's `page_length` as
    its `bar_length`: button N shows page N at every resolution, and holding two buttons or
    double-clicking one sets the loop in pages. Rejected: v3 as is (overlapping pages); pages
    without the loop setting. Side effects (reviewer, 12.4.16): every caller of `bar_length`
    sees pages, so a loop that starts mid-page rounds the page time to a page, and delete and
    copy on a loop button (not mapped in v1) act on a whole page.
25. **The script draws the playhead and the loop end in its note editor** (architect,
    2026-11-19, step 2; carries out Decision 17's fallback). Live's own playhead sent nothing to
    the port in two runs, with v3's default notes and with the 32 step notes on the translation
    channel at velocity 5 (`tested`, 12.4.16). So `DrumNoteEditorComponent` lights the playing
    step from `Clip.playing_position` through v3's `_get_alternate_color_for_step` hook and
    updates only the two steps that change (two LED messages a step, about 16 a second at
    120 BPM, Decision 12). The same hook paints an empty step outside the clip's loop red: v3
    shows the whole page past the loop end, and a press there extends the loop
    (`extend_loop_for_region`, `observed`). Done in the note editor instead of a
    `playhead_component_type`, because the note editor owns the step colours (amends Decision 17's
    "through a `playhead_component_type`"); no contract changes. v3's `PlayheadComponent` is
    still built; step 3 replaces it with one that does nothing, so a later build where it works
    can't draw a second playhead.
26. **The script arms the selected track for the pads** (user, 2026-11-19, step 3). A pad press
    reaches the Drum Rack only on an armed track (tested: silent unarmed, heard armed by hand).
    v3 builds its `AutoArmComponent` only for a controller that answers Live's identity request
    (`include_auto_arming`, `observed`), which the mk1 script doesn't ask for; so `setup()` builds
    one itself, enabled. It sets the selected MIDI track's implicit arm (Live's auto-arm, not
    the record arm; tested). Whether it steps back while another track is armed by hand is
    `documented` only (12.0; 12.4.16's `_can_auto_arm` differs), a check for step 4.
    Rejected: arming by hand; deciding later.
    Checked in step 4 (2026-11-19, the user, by hand): track 9's auto-arm went off while track 1
    was armed by hand (`tested`).
27. **A held pad is red from the script's own skin name** (architect, 2026-11-19, step 3;
    carries out Decision 10). Live sent no feedback for a played pad, armed or not, with
    `playing_feedback_velocity` 3 (tested), so `PadBankComponent` keeps the held pads and gives
    them `DrumGroup.PadPressed`. The selected pad blinks green (`PadSelected` 2).

28. **Step 4's parts** (architect, 2026-11-19, step 4; carries out Decisions 9 and 15):
    - scene buttons 1–4 are `resolution_buttons`, a submatrix of the scene buttons
      (`ElementsBase.add_submatrix`, `observed`), mapped on `Step_Sequence` (amended by
      Decision 29: two buttons, finer and coarser; the submatrix is gone);
    - `View_Control` takes `prev_track_button` and `next_track_button` (scene buttons 7–8), with
      the framework's session ring; `Mixer` takes `volume_controls` (faders 1–8, tracks 1–8)
      and `master_track_volume_control` (fader 9);
    - the session ring enables itself (`FaderRingComponent`, as in the UC4 example): the
      framework enables it only on an identity reply, and the box shows which tracks the faders
      reach. It never moves: no session navigation in v1, and `link_session_ring_to_track_selection`
      stays `False` (the default, `observed`; set in the Specification so it reads as meant, and
      checked: fader 1 sets track 1 while track 10 is selected). Rejected: the ring disabled, which
      works but leaves the faders' tracks unmarked and the validator's `session-ring` warning;
    - two rig additions the checks needed, no contract changed (the check file's format grows,
      the panel's model and protocol stay as they are): a nested `state` field matches the
      fields it names (the master's volume, `song: {master_track: {volume: 1.0}}`), and the
      controller model reads `add_submatrix` (`Controller.submatrices`, no new elements);
    - the reviewer's step-3 code points: the clip is re-set on `drum_group_changed`, a step press
      without a Drum Rack is inert (`_on_pad_pressed`), the held pads clear in `set_matrix` and
      are red only with a Drum Rack, `NoPlayheadComponent.update` calls `super().update()`. The
      skin's `pressed_color` was not tried: the script's own red works (Decision 27).
    - the auto-arm check (Decision 26) is a test by hand: `ask_user` doesn't wait during a run.

29. **The scene from the controller; the resolution on two buttons** (user, 2026-11-19, step 5's
    panel run; amends Decisions 9 and 10). Playing on the panel, the user could move the track
    but not the clip slot: the slot the steps edit (Decision 8) was chosen only in Live. Asked
    for a pair of buttons, the user chose to fold the resolution into two buttons instead of
    using Shift:
    - scene button 1 one resolution finer, 2 one coarser (1/32, 1/16, 1/8, 1/4), each lit while
      it can move; no button shows which resolution is on (amended by Decision 30), the notes' spacing does (user, "lit
      if it can go further", over a blink at the default). v3's `GridResolutionComponent` has
      only one button per resolution (12.4.16, `observed`); `StepResolutionComponent` adds a
      finer and a coarser `ButtonControl` that set its `index`, and the step sequencer forwards
      `set_finer_resolution_button` and `set_coarser_resolution_button` to it;
    - scene buttons 3–4: `View_Control`'s `prev_scene_button` and `next_scene_button` (12.4.16,
      `observed`), skin names `ViewControl.Scene` and `ScenePressed`; 5–8 unchanged;
    - Shift stays free for the later session mode (Decision 9);
    - the checks: the resolution's LEDs at both ends and the 1/8 note, scene 2 and back with
      `song: {selected_scene: N}` (0002 Decision 29). That the steps then edit the new scene's
      slot is a check by hand in the panel run: in the run clip 3 still counts as the track's
      playing clip after the stop (resolution-note writes to it), and the playing clip comes
      first (Decision 22). (Amended by Decision 32: scene-next and scene-prev check the steps.)

30. **The resolution on its own pads** (user, 2026-11-19, step 5's panel run, "bottom-right pad
    row"; amends Decision 29's "no button shows which resolution is on"). The user couldn't tell
    whether a note was missing or the resolution was wrong. The top row of the bottom four rows'
    right half (notes 28–31, dark until now) is v3's own `resolution_buttons` radio group, one
    pad per resolution, 1/32, 1/16, 1/8, 1/4: the active one yellow, the others off, a press sets
    it. Scene buttons 1–2 stay as finer and coarser. The three rows below stay dark. The panel's
    profile puts the pads in the pad bank's row (the panel draws each group as one line of
    cells, no matrix shape); no rig or protocol change.

31. **The page follows the playhead** (user, 2026-11-19, step 5's panel run, "follow; a pick
    pauses it"; amends Decision 9, where pages change only by hand). On a clip longer than one
    page the user missed Push's follow. v3's `LoopSelectorComponent` has none (12.4.16,
    `observed`: no `is_following` or follow button), so `PageLoopSelectorComponent` does it:
    - while the transport and the clip play, the page shown is the playhead's page;
    - a track button press that changes the page pauses following, so that page can be edited
      while the clip plays (pressing the page already shown changes nothing, and following
      goes on);
    - following starts again when the transport starts or the sequencer's clip changes
      (amended by Decision 34: or a press on the playhead's page);
    - the pause is set in `_on_matrix_pressed` (12.4.16, `observed`) before v3 sets the page:
      v3's own redraw on the page change runs before any slot of ours, and would follow back;
    - the checks: `page-follows` (page 2 shows on its own while it plays), `page-one-pick`
      (page 1 shown while page 2 plays), `page-two` (page 2 picked, it stays while page 1
      plays; after the stop `scroll-pitch` picks page 2 with track button 2). Rejected: always follow (no editing of another page while it plays), Shift to
      toggle (Shift stays for the session mode).

32. **The clip: always the selected slot** (user, 2026-11-19, the APC run; replaces Decision 22,
    back to Decision 8's wording). On the hardware a step press on an empty slot while the
    transport ran wrote into the track's playing clip, and a Drum Rack added to a track with a
    playing clip seemed not to take notes: they went into that clip. Live counts a clip as
    playing after the transport stops too (tracks 1–8 of the test Set all had one), so the
    selected slot was often not the one edited. `SelectedSlotTargetTrackComponent` overrides
    `TargetTrackComponent._target_clip_from_session` (12.4.16, `observed`; its playing-slot
    rule read in the 12.4.16 bytecode, local disassembly) to take the selected scene's slot,
    playing or not, keeping the base's listener on the slot (in Session view; in Arrangement
    v3's detail clip, unchanged). A press on an empty slot creates
    the clip there: v3's `create_sequencer_clip` uses the selected slot when it is empty and
    starts it at once, legato, in place of the track's playing clip (12.4.16 bytecode). The
    checks select each clip's scene (`select_clip_slot`) and `edit-other-slot` shows clip 2
    while clip 3 plays. Rejected (user): a created clip that doesn't start; the playing clip
    first.

33. **A Drum Rack inside an Instrument Rack counts** (architect, 2026-11-19, the user's test list;
    fixes Decision 8's "a track without a Drum Rack"). The user's Young Blood Kit is an
    Instrument Rack with the Drum Rack inside: v3's pad bank found it, but the script's own check
    looked only at the track's devices, so the steps stayed inert ("it seems to be hardcoded to
    Yellow Kit"). `has_drum_rack` now uses v3's `find_drum_group_device` (12.4.16, `observed`),
    as the pad bank does. Checked on the rig with a Young Blood Kit track (an ad-hoc check file;
    the check file can't load a kit: the rig never sends browser commands, 0002 Decision 6).
34. **The playhead's page turns following on again** (user, 2026-11-19, "how come I back to follow
    mode?"; adds to Decision 31): a track button press on the page the playhead plays shows it and
    follows again; a press on another page pauses, as before. The check file's `page-two` became
    `page-follows-again` (page 2 pressed while it plays, page 1 comes up by itself).
35. **The sequencer gets its own repo** (user, 2026-11-19): `APC_mini_drum_seq` next to this repo
    (`../APC_mini_drum_seq`), MIT, with the script, `checks.yaml`, `device.yaml`, its own README
    and a `pyrightconfig.json` for the stubs, its history carried over; released on its own, later
    (distribution comes last). This repo keeps it at `examples/APC_mini_drum_seq` as a git
    submodule at a pinned commit (user: "isn't a submodule better for pulling continuously?"; the
    path stays, so the tests and the skill's reference don't change). It becomes a real-world test
    field for the MCP. Built as its own task after this one.
36. **Its name and layout** (2026-11-19; the name: user, "lets use your recommendation pick",
    from the architect's suggestions; one repo per controller: user; the layout: architect).
    This changes Decision 35's name and path. One repo per controller, so this one is for the
    APC mini mk1 only, with more modes to come.
    - Repo `APC_mini_mk1_Plus` (user, 2026-11-19: created on GitHub as
      `MarvinHauke/APC_mini_mk1_Plus`, in place of the architect's `apc-mini-mk1-toolkit`), cloned
      at `../APC_mini_mk1_Plus`. The script folder, Live's Control Surface name and the class are
      `APC_mini_mk1_Plus` too.
    - In the repo: `APC_mini_mk1_Plus/` holds the script, `checks.yaml` and `device.yaml` (the rig
      finds them beside the script, `script: .` unchanged). README, LICENSE (MIT),
      `pyrightconfig.json` (stubs in a git-ignored `stubs/`) and `.gitignore` sit at the root, so
      they don't land in the User Library.
    - Here: a submodule at `examples/APC_mini_mk1_Plus`, the script at
      `examples/APC_mini_mk1_Plus/APC_mini_mk1_Plus`. `.gitmodules` has the relative URL
      `../APC_mini_mk1_Plus.git` (it resolves against `origin` to
      `git@github.com:MarvinHauke/APC_mini_mk1_Plus.git`; until that repo is pushed, only this
      checkout, whose local config points at the sibling, can update it). Tests that read the script skip with `git submodule update --init` as the reason.
    - Its history (10 commits) was carried over with `git subtree split`. In Live the user picks
      `APC_mini_mk1_Plus` once, after `install` of the new folder; the old installed
      `APC_mini_drum_seq` can be deleted from the User Library.
    - Pushing (architect, 2026-11-19): the script's repo is pushed only when the user says so. Until
      its GitHub repo has the commits, the architect holds the push of
      `main` after merging this branch and asks the user first: a pushed `main` would point at a
      submodule nobody can fetch. CI is not affected either way: the tests skip and `docs.yml`
      doesn't check out submodules.
      The user pushed the repo themselves (2026-11-19, `98161a8`), so the hold is lifted.

## Open questions

None: questions 1–12 are Decisions 2–13 (each names its question), the panel question from
round 2 is Decision 14, the track choice Decision 15, the clip preset Decision 16. Grilling closed 2026-11-19 (rounds 1–4, user confirmed).

## Steps

Written 2026-11-19 by the architect from the spec (the `/to-tickets` skill is not installed
here), for the user's approval. Order (Decision 19): 0002 6a → 0002 6b → 1 → 2 → 3 → 4 → 5 →
6 → 7. Every step is written with the skill and the MCP server; each lookup that was missing,
wrong or awkward goes onto the results page's tool findings with what was asked and what came
back, and the step's overview says which became a fix and which a STATUS item.

- **Before step 1, plan 0002's steps 6a (the panel's LED colours, 0002 Decision 26) and 6b:
  a clip's notes in check files.** Written out in 0002; 6b's summary here.
   - **Delivers:** a `state` target for a clip (`track N clip M`: `notes` as pitch, start,
     length, velocity; `length`, `looping`, `name`) read with `get_clip_notes` and AbletonMCP's
     clip info; `do` with `add_notes_to_clip` and `clear_notes_from_clip`; `requires` can ask
     for a Drum Rack track and an empty slot (named, never created: loading devices is out of
     scope, Decision 16).
   - **Checks:** seam C over the fake socket; then the user sets two notes by hand in a test-Set
     clip and the rig reads them back: `get_clip_notes` joins `TESTED`; an add and a clear are
     read back and checked by the user, and join it too (0002 Decision 25).
1. **Tracer: steps of one pad, on the rig** — blocked by: 0002 6a, 6b.
   - **Delivers:** `examples/APC_mini_drum_seq/` (Implementation Decisions): elements, the
     Specification, `Step_Sequence` on the 32 step buttons with `Drum_Group` as pitch provider
     on the 4×4 pads (selection only, plain colours), the clip preset on an empty slot
     (Decisions 8, 16), the skin for steps (note green, empty off); `device.yaml` with the
     layout (grid, track row, scene column, faders); a first `checks.yaml`; the results page
     (Decision 18) with the tool findings so far. Already found while writing the spec:
     `get_class("Clip")` returns skin and notification classes named `Clip` and cuts
     `Live.Clip.Clip`; `Launchkey_MK4`'s outline has no mappings; `lookup class` crashes with
     `KeyError: 'all_members'` (`cli.py`, `_format_class`) when the answer is cut, for example
     for `Live.Clip.Clip` and v3's `DrumGroupComponent` (a fix for the core builder).
   - **Checks:** `validate` no findings, `check-names` no unknown names (12.4.16); the
     `local_live` tests for the example; the user loads it on a slot with `ARS Test Rig` (the
     test Set gets a Drum Rack track, which the user adds); `rig run`: on an empty slot a step
     press creates "Drum Seq" (2 bars, looping), the step's note is in the clip (pitch of the
     selected pad, one step long, velocity 100), its LED turns green, a second press clears
     both; a pad press changes the pitch the steps write; `log: clean`.
2. **Playhead, loop end and pages** — blocked by: 1.
   - **Delivers:** the playhead in yellow (Decision 17: v3's `PlayheadComponent` first, our own
     otherwise), steps beyond the loop end red, track buttons 1–8 as loop buttons (a page of
     32 steps each; current page on, the playhead's page blinking) (Decisions 9, 10).
   - **Checks:** `rig run` with transport playing: the playhead's LEDs move along the steps
     (Live's replies, Decision 2); a clip shortened by `do` shows red beyond its end (AbletonMCP
     can't shorten a clip: a 1-bar clip created by `do` instead); track
     button 2 on a 4-bar clip shows steps 33–64, and a loop button press leaves the clip's
     `length` and `looping` as they were (v3's loop selector may set the loop). The results page records which playhead
     worked, as a `tested` fact.
3. **The pad bank** — blocked by: 1.
   - **Delivers:** pad colours (selected green blinking, with a sound yellow, empty off, red
     while held), pads play their sound, scene 5–6 scroll the bank by a row
     (`DrumGroupScrollComponent`, lit when they can scroll), a track without a Drum Rack leaves
     the pads dark and the steps inert (Decisions 3, 8, 9, 10).
   - **Checks:** `rig run`: pad LEDs against a Drum Rack with known filled pads, a scroll moves
     the bank and the pitch, the scroll LEDs at the ends; on a MIDI track without a Drum Rack:
     no pad LEDs, a step press creates no clip. Whether a pad plays its sound: `ask_user`.
4. **Resolution, track choice, faders** — blocked by: 1.
   - **Delivers** (as built in step 4; Decision 29 changed scene 1–4 in step 5): scene 1–4 the
     resolution (1/32, 1/16, 1/8, 1/4, the active one on), scene
     7–8 previous and next track (`ViewControlComponent`, lit when there is one, Decision 15),
     the clip slot following Live's selected scene, faders 1–8 track volumes and fader 9 the
     master (Decision 9).
   - **Checks:** `rig run`: a resolution press changes the step length of new notes and the
     LED; scene 8 moves to the next track and the sequencer follows it (AbletonMCP reads the
     selected track if it can; else `ask_user`); faders reach their target volume only
     (0001 Decision 29). All checks of steps 1–3 still pass.
5. **Panel and hardware** — blocked by: 4.
   - **Delivers:** the full check file
     passing, then the user's two runs (Decisions 12, 14): a short pattern on the panel, then
     the same on the APC; the results page gets both, and whether a press dropped.
   - **Checks:** `rig run` all passed; the panel shows the grid in the APC's colours; the user's
     list (playhead, pads, pages, track and scene choice, no dropped presses while the playhead
     runs). Decisions 29 (the scene buttons, the resolution on two), 30 (the resolution pads)
     and 31 (the page follows the playhead) came out of the panel run.
     ReceiveMIDI only if a press seems missing. Unit-only findings stay on the results page.
6. **Into the skill** — blocked by: 5.
   - **Delivers:** a `tested` section "A step sequencer" in the v3 reference (the components,
     their dependencies, the clip preset, the playhead finding, the mk1 skin), the rig in the
     skill (0002 Decision 20); the tool findings fixed or filed in STATUS.
   - **Checks:** the reviewer against the results page (every fact with build and
     confidence); `validate` and `check-names` on the reference's snippets.
7. **A sequencer eval case and the MCP round** — blocked by: 6.
   - **Delivers:** an eval case for a step sequencer on a grid controller (not the APC mini mk1,
     so the case can't copy the example), its graders, and the round with the MCP tools: 2–3
     runs per arm (0001 Decision 55), tool calls, tokens and cost counted.
   - **Checks:** the scores and unknown names on the results page, compared with
     [milestone-1/skill-evals.md](milestone-1/skill-evals.md); the user reads the numbers before
     the big round (0001 step 13).

## Out of scope

- Per-step velocity, length, probability or automation editing.
- Melodic (non-drum) sequencing.
- Other controllers; the APC mini mk2 has its own script from Ableton.
