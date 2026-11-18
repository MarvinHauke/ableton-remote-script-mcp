# 0002 — Virtual controller test rig

_Stage: grilled (2026-11-18, Decisions 1–25) — spec and steps next, when the user chooses._
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

All by the user, 2026-11-18, grilling round 1–5 (Q1–Q25), on the agent's recommendations.

1. **Who may send MIDI into Live** (Q1): the user starts Live, opens the test Set and picks the
   rig's virtual port as a Control Surface's input and output. After that the agent may send
   MIDI only to that virtual port, never to the user's hardware ports, and says so before each
   automated run; the user can stop it at any time. Restarting Live, choosing control surfaces
   and connecting hardware stay the user's. A dated exception to CLAUDE.md's "only the user
   operates Live", for the test rig only.
2. **AbletonMCP is an optional local aid** (Q2): the rig works from MIDI replies and `Log.txt`
   alone and uses AbletonMCP when it runs. 0001 Decision 10 stays for the skill and the MCP
   server: neither mentions it.
3. **Both a driver and a web panel** (Q3), in one Python package in this repo; the driver first.
   Both build on one model of the controller read from `outline`.
4. **Published** (Q4) with the repo (our own code, MIT); AbletonMCP support documented as an
   optional local aid.
5. **First use** (Q5): the UC4 script, whose 14 results are known, then the APC mini drum
   sequencer.
6. **AbletonMCP commands** (Q6, Q16): reading `get_session_info`, `get_track_info`,
   `get_device_parameters` and `drain_passive_events` (its listeners' buffered changes: the main
   state evidence, read after each step); preparing and the Live → controller direction
   `create_midi_track`, `create_audio_track`, `create_clip`, `set_tempo`,
   `set_device_parameter`, `fire_clip`, `stop_clip`, `start_playback`, `stop_playback`. A command
   is on the rig's "tested" list only after reading back a state the user set by hand. Reads
   run off Live's main thread in AbletonMCP 1.7.1 and are repeated until two agree (a first read
   after the user reopened Live failed with `Boost.Python.ArgumentError … None(Song)`, the next
   one worked; 2026-11-18). Never: its rating, dataset-consent or browser commands; its
   `user_prompt` telemetry argument stays empty. Mute, solo, arm and volume can't be set
   through it: those are checked controller → Live only.
7. **Port** (Q7, Q17): the rig creates its own named virtual ports with `rtmidi2` (1.5.0,
   2026-10, MIT, macOS arm64 wheels for Python 3.10–3.14), `pylibremidi` as the fallback library,
   the IAC Driver as the fallback port. Step 1 is a spike: does Live see a port that appears
   while it runs?
8. **Check file** (Q8): `checks.yaml` beside each example script; steps send MIDI and expect
   replies (or none), a clean log and, through AbletonMCP, state; steps no machine can see are
   "ask the user". The milestone pages' prose checklists stay for the user.
9. **The panel is a client** (Q9): the driver owns the ports; the panel is a local web page that
   talks to it over a WebSocket (no Web MIDI). The page says plainly that it is a parallel view
   for the user and that the driver is in charge.
10. **Layout** (Q10): a plain layout from `outline`'s elements by default; optional layout files
    in a device profile (UC4, APC mini), written from their facts pages.
11. **Identity** (Q11, Q18): no identity reply by default; a device profile may give the reply
    its script expects; an identity of the rig's own uses the non-commercial manufacturer ID
    `7D`, never a real manufacturer's.
12. **Commands** (Q12): `ableton-remote-script-mcp rig run <checks.yaml>` and
    `ableton-remote-script-mcp rig panel <script folder>`.
13. **Test Set** (Q13, Q19): the Set Live opens from the user's `devSetup.als` template (on
    2026-11-18: 8 tracks, 7 MIDI and 1 audio with one-shot samples, racks on every track, 2
    returns, 8 scenes, no group tracks). The rig may create what a check file needs in that open
    Set, never saves, and before a run checks the Set has what the checks need, stopping with a
    list otherwise.
14. **Saving test Sets** (Q20): the user saves (AbletonMCP has no save command), into
    `Ableton_Examples/` in this repo, git-ignored by default: an `.als` stores absolute sample
    paths, with the user's name. A Set with only MIDI clips and Live's built-in devices may be
    published after a path check.
15. **What the test Set can't give** (Q21): group tracks and a muted, soloed or armed starting
    state are "ask the user" steps; the rig may still mute or solo through the script under
    test.
16. **Testing the rig** (Q22): its tests use an in-memory fake port and a fake AbletonMCP socket;
    one local-only test runs the UC4's check file against real Live and passes only when it
    reproduces the user's 14 results.
17. **Glossary** (Q23): Test rig, Check file, Device profile, Test Set (added 2026-11-18).
18. **Reports** (Q24): per step passed, failed or ask the user, with what was sent and what came
    back (MIDI, AbletonMCP events, a traceback); a short printed report and the full result as
    JSON beside the check file. A failure doesn't stop the run; steps that depend on it are
    skipped. The agent still writes the milestone results, citing the run.
19. **Docs** (Q25): each step updates the `docs/` pages it touches; the rig gets its own guide
    once the driver works.
20. **The skill** (Q14) mentions the rig only after it is proven on the UC4 and the sequencer.
21. **Driver reaches AbletonMCP through its socket** (Q15), localhost:9877, version checked
    with `get_script_info` (1.7.1, protocol 1), commands from an allow-list only; with an
    unknown version or no socket the rig runs without it. The agent may use the matching MCP
    tools by hand.

## Open questions

None: grilling closed 2026-11-18 (user confirmed).

## Steps

Written after the grilling.

## Out of scope

- Replacing the user's load test on the hardware.
- Controlling Live for anything other than testing a Remote Script.
- Changing AbletonMCP (the user's project; the two bugs above are reported to the user).
