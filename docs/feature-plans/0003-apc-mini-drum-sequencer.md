# 0003 — A drum step sequencer for the APC mini mk1

_Stage: draft (2026-11-19). Next: grilling with the user._
_Depends on: 0001 (the skill, the MCP server), 0002 (the test rig; its step 6 waits for this plan)._

## Problem

The user wants to program drums on the APC mini mk1 from its grid, without the mouse. No script
does that for this controller. It is also the first job for our tools that works on Live's clips
and notes rather than only mapping controls onto components. That part of the API is where the
index is thinnest, and none of our eval cases covers it yet. The APC mini drops presses under
LED load, so the hardware can't test a sequencer reliably; the test rig can.

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

## Open questions

Each with a recommended answer.

1. **What it sequences.** One drum lane at a time (Push-like), or several lanes at once?
   _Recommended:_ the top four rows are 32 steps of the selected drum pad; the bottom four rows
   are a 4×4 drum pad bank that picks the lane and plays the sound. That is how v3's
   `StepSequenceComponent` works (one pitch from a pitch provider). Rejected: 8 lanes × 8 steps,
   which v3 doesn't offer and would be all our own code.
2. **Framework.** v3's sequencer components, or our own code on Live's clip API?
   _Recommended:_ v3's components, with our own code only where they don't fit the mk1 (its
   three colours and blinking). The trade-off: fewer direct calls into the `Live` objects, so
   less of the index gap is exercised. The skill learns the components either way.
3. **Clip.** Which clip does it write into, and what happens on an empty slot?
   _Recommended:_ the selected track's selected clip slot; on an empty slot the first step press
   creates a clip (length from the loop, 2 bars by default). To check in the build how v3's
   note editor handles that.
4. **The other buttons.** _Recommended:_
   - scene buttons 1–4: resolution (1/32, 1/16, 1/8, 1/4); 5 and 6: previous and next page;
   - Shift + a scene button: mode switch to a session grid (later, see question 9);
   - track buttons: free in v1;
   - faders: track volumes as on the mk1 example; fader 9 the velocity of new steps.
5. **LEDs on three colours.** _Recommended:_ a step with a note green, an empty step off, the
   playhead yellow, steps outside the loop dark; the selected drum pad red, a pad with a sound
   yellow, an empty pad off.
6. **Velocity and note length.** _Recommended:_ fixed length of one step; velocity from fader 9
   (default 100). No per-step editing in v1.
7. _Decided: Decision 2._
8. **What stays for the hardware check.** The rig can't see the hardware's own behaviour.
   _Recommended:_ the user plays a short pattern and watches the playhead; dropped presses are
   recorded with ReceiveMIDI beside the script's log and stay on this plan's results page, never
   in the skill (the APC mini drops presses under LED load).
9. **Scope of v1.** _Recommended:_ the sequencer only. A session mode (the mk1 example's clip
   launcher) comes later, as its own step.
10. **Where it lives and what it is called.** _Recommended:_ `examples/APC_mini_drum_seq/` (our
    own code, MIT), with `checks.yaml` and `device.yaml` beside it, like the UC4 example.
11. **What goes into the skill.** _Recommended:_ the sequencer components as a `tested` section
    of the v3 reference once the rig checks and the user's hardware check pass, and the rig in
    the skill (0002 Decision 20). Then the eval case and its 2–3 runs.
12. **Before the build.** _Recommended:_ the skill's section on using the MCP tools, and the
    MCP server registered in Claude Code, so the build uses them.

## Steps

Written after grilling.

## Out of scope

- Per-step velocity, length, probability or automation editing.
- Melodic (non-drum) sequencing.
- Other controllers; the APC mini mk2 has its own script from Ableton.
