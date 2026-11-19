# 0003 — A drum step sequencer for the APC mini mk1

_Stage: grilled (2026-11-19, Decisions 1–16). Next: spec and steps._
_Depends on: 0001 (the skill, the MCP server), 0002 (the test rig; its step 6 waits for this plan's steps, and this plan's rig checks need step 6's LED panel, Decision 14)._

## Problem

The user wants to program drums on the APC mini mk1 from its grid, without the mouse. No script
does that for this controller. It is also the first job for our tools that works on Live's clips
and notes rather than only mapping controls onto components. That part of the API is where the
index is thinnest, and none of our eval cases covers it yet. The APC mini dropped presses under
the plain `ControlSurface`'s LED flood; since `OptimizedControlSurface` the user has seen none,
not yet confirmed (Decision 12). The test rig checks what the hardware can't show.

## Design

A Remote Script for the APC mini mk1 that turns the grid into a step sequencer for a Drum Rack
track. Written with the skill and the MCP server, the way a user would: every lookup that is
missing or awkward, and every fact the skill lacks, becomes a fix in the skill or the server.
Checked on the test rig (plan 0002 step 6: a check file and a device profile), then on the
hardware by the user for what the rig can't see.

What the 12.4.16 index already offers (`observed`):
- `ableton.v3.control_surface.components.step_sequence.StepSequenceComponent`, with
  `set_step_buttons`, `set_loop_buttons`, `set_resolution_buttons`, `set_prev_page_button`,
  `set_next_page_button`, `set_pitch_provider` and the properties `note_editor` and `playhead`.
- v3 modules `note_editor`, `playhead` and `bar_based_sequence` beside it.
- `Launchkey_MK4.step_sequence.StepSequenceComponent` subclasses it: a reference script to read
  with `outline`.

Device facts: [milestone-1/apc-mini-mk1.md](milestone-1/apc-mini-mk1.md), "Device facts"
(`documented` from Akai's protocol, confirmed for this unit by the step 9 load test).

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
   - track buttons 1–8: v3's loop buttons, one page of 32 steps each (replaces previous/next page);
   - scene buttons 1–4: resolution 1/32, 1/16, 1/8, 1/4; 5–6: scroll the pad bank up and down by
     a row (`DrumGroupScrollComponent`);
   - scene buttons 7–8 and Shift: free in v1, Shift kept for the later session mode (7–8 amended
     by Decision 15: previous and next track);
   - faders 1–8: track volumes; fader 9: master volume, as on the mk1 example.
10. **LEDs** (user, 2026-11-19, Q5):
    - steps: a note green, empty off, the playhead yellow, beyond the loop end red (the mk1 has
      no dim colour);
    - pads: the selected one green blinking, one with a sound yellow, empty off, red while held;
    - track buttons (red): the current page on, the playhead's page blinking;
    - scene buttons (green): the active resolution on, the scroll buttons on when they can scroll,
      7–8 on when there is a track to move to (Decision 15).
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

## Open questions

None: questions 1–12 are Decisions 2–13 (each names its question), the panel question from
round 2 is Decision 14, the track choice Decision 15, the clip preset Decision 16. Grilling closed 2026-11-19 (rounds 1–4, user confirmed).

## Steps

Written after grilling.

## Out of scope

- Per-step velocity, length, probability or automation editing.
- Melodic (non-drum) sequencing.
- Other controllers; the APC mini mk2 has its own script from Ableton.
