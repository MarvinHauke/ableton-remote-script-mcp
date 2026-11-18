# 0002 — Virtual controller test rig

_Stage: draft (2026-11-18) — to be grilled before anything is built; after 0001's Milestone 1._
_Depends on: 0001 (outline, validator, `log`); input: the UC4 load test
([milestone-1/faderfox-uc4.md](milestone-1/faderfox-uc4.md))._

## Problem

Every behaviour check of a Remote Script needs the user, the hardware and a round of "press
this, what lights up?". The UC4 load test took two sessions, and three of its four bugs showed
only as wrong values or a traceback, which a machine can see. Some hardware can't be trusted for
the test at all: the APC mini mk1 loses presses under LED load, so a step sequencer can't be
load-tested on it reliably. The user wants a virtual controller that sends the script's MIDI
and shows what Live sends back, which the user can play with and Claude can drive itself.

## Design

A proposal; grilling decides.

- **A virtual port.** A MIDI port that Live sees like a controller: macOS's IAC Driver, or a
  port the rig creates itself. The user picks it once as the Remote Script's input and output.
- **A panel from the script's own facts.** `outline` already lists every element with its MIDI
  type, channel and number. The rig builds its controls from that list (faders, encoders,
  buttons, grids, with the device's own layout where we know it), so it works for any script,
  not just the UC4.
- **A web app for the user** (Web MIDI in Chrome): move a fader, press a button, and see what
  Live sends back (LED values, encoder values) on the panel.
- **A command-line driver for Claude:** a checklist written as data ("send CC 40 = 100 on
  channel 13; expect …"), run against the port, with Live's MIDI replies recorded and `Log.txt`
  read for tracebacks. Repeatable, so a fix can be checked again without the user.
- **Live's state through AbletonMCP, optional.** AbletonMCP (the user's own server and Remote
  Script, version 1.7.1, slot 4) reads the Set: tempo, a track's mute, solo, arm, volume, pan,
  its clips and devices, a device's parameters. That checks what MIDI replies can't (a fader
  moved the volume). See "Open questions" for what was found when its script was checked.

What it can catch: values that never come back, tracebacks (the Quant float error), wrong LED
values (the inverted Active LEDs), mappings that drive the wrong parameter. What it can't:
anything Live doesn't send back (the session box), and the hardware's own behaviour (the UC4's
pickup, its per-group LED memory, its displays, a controller that drops presses). It narrows the
hardware test; it doesn't replace it.

## Decisions

None yet.

## Open questions

Recommended answers, for the grilling.

1. **"Only the user operates Live" (CLAUDE.md).** Claude sending MIDI into Live, or changing a
   Set through AbletonMCP, is operating Live. Recommended boundary: the user picks the virtual
   port as a Control Surface and opens a test Set; after that Claude may send MIDI only to that
   virtual port, never to the user's hardware, and may change only that test Set. Selecting a
   control surface, restarting Live and connecting hardware stay the user's.
2. **AbletonMCP and Decision 10 of 0001** ("independent of AbletonMCP; the skill doesn't
   mention it"). Recommended: the rig is a local development aid. It may use AbletonMCP when it
   is there, and works without it from MIDI replies and the log. The skill and the MCP server
   keep not mentioning it.
3. **Which AbletonMCP tools.** Checked 2026-11-18 against 12.4.16:
   - The validator gives no findings. `eval_names.py` finds two real bugs: the
     `get_browser_categories` and `get_browser_items` commands call methods the file doesn't
     define, so they always fail. Everything else unknown is Python's socket, queue and thread
     methods, or guarded by `hasattr`.
   - It runs writes on Live's main thread (`schedule_message`), but reads
     (`get_session_info`, `get_track_info`, `get_device_parameters`, `get_session_snapshot`, …)
     straight from its socket thread. Live's API is not meant to be used outside its main thread
     (`documented`, community knowledge; not tested by us), so a read taken while a value
     changes may be stale.
   - Recommended: only `get_session_info`, `get_track_info` and `get_device_parameters` for
     reading, and only creating tracks and clips and setting the tempo for preparing a test Set.
     Each tool goes on a "tested" list only after reading back a state the user set by hand.
     Reads are repeated until two agree. MIDI replies and the log are the main evidence.
     Never call its rating, dataset-consent or browser tools, and leave its `user_prompt`
     telemetry argument empty.
4. **Web app and driver: one tool or two?** Recommended: one Python package in this repo (the
   driver, the port, the panel model from `outline`) with a small web page served locally for
   the user. The page uses Web MIDI, so it needs Chrome and a local server.
5. **Where the checklist lives.** Recommended: the milestone pages' checklists stay prose for
   the user; the rig gets a data file per script next to the example (`checks.yaml`) that names
   each step and the expected reply.
6. **Hardware layouts.** Recommended: a grid of the elements by name by default. Optional
   layout files for the devices we test (UC4, APC mini) come from their facts pages.
7. **Published or local?** Recommended: published with the repo (our own code, MIT), like the
   validator. AbletonMCP support stays optional and documented as a local aid.
8. **First use.** Recommended: the APC mini drum sequencer (the user's plan), so its LED-heavy
   checks don't depend on the mk1's dropped presses.

## Steps

Written after the grilling.

## Out of scope

- Replacing the user's load test on the hardware.
- Controlling Live for anything other than testing a Remote Script.
- Changing AbletonMCP (the user's project; the two bugs above are reported to the user).
