# 0002 — Virtual controller test rig

_Stage: in work — steps approved by the user 2026-11-18; step 1 built 2026-11-18. Frontier: step 2._
_Depends on: 0001 (outline, validator, `log`); input: the UC4 load test
([milestone-1/faderfox-uc4.md](milestone-1/faderfox-uc4.md))._

## Problem

Every behaviour check of a Remote Script needs the user, the hardware and a round of "press
this, what lights up?". The UC4 load test took two sessions, and three of its four bugs showed
only as wrong values or a traceback, which a machine can see. Some hardware can't be trusted for
the test at all: the APC mini mk1 loses presses under LED load, so a step sequencer can't be
load-tested on it reliably. The user wants a virtual controller that sends the script's MIDI
and shows what Live sends back, which the user can play with and Claude can drive itself.

## Solution

A **test rig** in this repo's package, started as `ableton-remote-script-mcp rig …`. Its driver
opens a named virtual MIDI port, plays a controller to a Remote Script the way a **check file**
says, records what Live sends back, reads `Log.txt` and, when AbletonMCP runs, the changes its
listeners saw. It reports each step as passed, failed or "ask the user". The controller's
elements come from `outline` of the script; a **device profile** adds layout and identity. A
web panel shows the same controller to the user and plays it through the driver. The rig works
in the **test Set** and never saves it. What it can't see (the session box, the hardware's own
behaviour) stays the user's load test. Decisions 1–21 below.

## User Stories

1. As a script author, I want to run a script's checks without the hardware, so that a fix is
   checked again in seconds and without the user.
2. As a script author, I want each check to say what was sent and what came back (MIDI, state
   changes, a traceback), so that a failure points at its cause.
3. As the user, I want the agent to send MIDI only to the rig's own port and change only the
   open test Set, so that my hardware and my projects are never touched.
4. As the user, I want a web panel of the controller that shows LED and display values, so that
   I can play a script without the hardware, while the driver stays in charge.
5. As a script author, I want the rig to answer an identity request like the device would, so
   that scripts that wait for one start.
6. As a script author, I want checks for the Live → controller direction (a parameter changed in
   Live lights an LED or updates a display), so that missing feedback is found before the
   hardware test.
7. As the user, I want checks no machine can see marked "ask the user", so that nothing is
   reported as passed that wasn't checked.
8. As a maintainer, I want the rig proven against the UC4's 14 known results, so that its
   verdicts can be trusted for new scripts.

## Implementation Decisions

- **Package layout:** `src/ableton_remote_script_mcp/rig/` with `ports.py` (rtmidi2, behind a
  small interface so tests use an in-memory port), `controller.py` (the controller model from
  `outline` plus a device profile), `checks.py` (load and run a check file), `abletonmcp.py`
  (socket client: version check, allow-list, repeated reads, `drain_passive_events`),
  `report.py`, `panel/` (web page and WebSocket server). `rtmidi2` becomes an optional
  dependency (`[rig]` extra), so the index, the validator and the MCP server don't need it.
- **Check file (`checks.yaml`):** `requires` (what the test Set must have), then `steps`, each
  with an id, a description, `send` (MIDI messages by element name, as `outline` names them, or
  raw), `expect` (replies by element name with value or "none", `log: clean`, `state` changes
  from AbletonMCP), `depends_on`, or `ask_user: <question>`. Live → controller steps use `do`
  (an allowed AbletonMCP command) instead of `send`.
- **Timing:** after each send the driver waits for replies until a quiet period (default
  150 ms, configurable per step), then reads the log and drains AbletonMCP's events.
- **Device profile (`device.yaml`):** beside the check file; identity reply bytes, panel layout,
  display hints (absolute, relative, bipolar).
- **Report:** printed summary plus `checks.result.json` beside the check file (git-ignored).
- **Panel:** a static page and a WebSocket served on localhost by `rig panel`; the page shows
  "parallel view: the driver is in charge". It renders the controller model and the last value
  sent and received per element.

## Testing Decisions

- **Seam C: the rig over fakes.** An in-memory MIDI port that plays a scripted Live (replies to
  given messages) and a fake AbletonMCP socket server. Assertions: the report's verdicts, what
  was sent, skipped dependents, the identity reply, the allow-list (a forbidden command is never
  sent), repeated reads until two agree, version mismatch → runs without AbletonMCP.
- **Controller model:** built from `outline` over the hand-written test index and from the UC4
  example against the real index (local-only).
- **Local-only, against Live:** the step-1 spike (the user picks the port), then the UC4 check
  file reproducing the user's 14 results (Decision 16). These run only on request, since they
  need Live open with the test Set.
- **Prior art:** `tests/fixtures/fake_live_bundle`-style fakes and the `local_live` marker of
  plan 0001.

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

Written 2026-11-18 by the agent from the spec (the `/to-tickets` skill is not installed here),
for the user's approval. Order: 1 → 2 → 3 → 4 → 5 → 6.

1. **Spike: a virtual port Live sees** — blocked by: none.
   - **Delivers:** `rig ports` (list the MIDI ports) and `rig probe` (open the virtual port
     `ARS Test Rig`, send one message, print what comes back); `rtmidi2` as the `[rig]` extra.
   - **Checks:** the user picks `ARS Test Rig` as input and output of a free Control Surface slot
     with `Faderfox_UC4`; is the port listed without restarting Live? `rig probe` sends fader 1
     (CC 40, channel 13) and receives Live's value back (the feedback the load test fixed); with
     AbletonMCP, track 1's volume changed. If Live needs a restart or the port misbehaves, try
     `pylibremidi`, then the IAC Driver (Decision 7), and record which.
   - **Built** (2026-11-18): `rig ports`, `rig probe`, `rtmidi2` as the `[rig]` extra; seam C
     tests over `MemoryPort`. Run against Live 12.4.16 with `Faderfox_UC4` on `ARS Test Rig`:
     Live connected and sent the script's start-up state (every fader and encoder value, then
     every green LED); `CC 40 = 100, channel 13` came back as `CC 40 = 100`, and AbletonMCP read
     track 1's volume 0.787 (100/127; before: 0.693 = 88/127, the value Live had sent at start).
     For step 2: the start-up state comes in more than one burst (a full resend about a second
     later), so the driver waits for quiet before the first step and compares a control's last
     reply only. The port showed up in Live's lists without restarting Live (the user,
     2026-11-18): the rig can open its port at any time; no fallback needed.
2. **Driver and check files, MIDI and log only** — blocked by: 1.
   - **Delivers:** the controller model from `outline`, the check file format, `rig run` with
     send/expect by element name, quiet-period waiting, `log: clean`, `ask_user`, `depends_on`,
     the report and its JSON.
   - **Also** (the user, 2026-11-18): a script change needs a Live restart, and the port lives
     only while the rig runs. So a long-running `rig serve` keeps the port open across Live
     restarts; `rig run` (and later the panel) go through it instead of opening their own port.
   - **Checks:** seam C over the in-memory port; a first `examples/Faderfox_UC4/checks.yaml`
     with the steps MIDI and the log can decide, run against Live (local-only). In Live: with
     `rig serve` running, does a Live restart keep slot 1's `ARS Test Rig` and script? When Live
     starts before the rig, does the slot reconnect once the port appears? The answers go into
     the guide's "after a script change" steps.
3. **AbletonMCP** — blocked by: 2.
   - **Delivers:** the socket client (version, allow-list, repeated reads, events), `state`
     expectations, `do` steps (Live → controller), `requires` checked against the test Set and
     creating what is missing; the tested-command list procedure (Decision 6).
   - **Checks:** seam C over the fake socket; the user sets three states by hand for the
     tested list; the full UC4 check file reproduces the 14 results (Decision 16).
   - **Docs:** a guide page "Testing a script with the test rig"; How it works and Getting
     started mention the rig.
4. **Device profiles and identity** — blocked by: 2.
   - **Delivers:** `device.yaml` (identity reply, layout, display hints), the identity reply
     when Live asks; the UC4 profile.
   - **Checks:** seam C: a script that waits for identity starts only with the reply; local: a
     v3 sample script with `identity_response_id_bytes` starts with the rig's reply (`7D`).
5. **Web panel** — blocked by: 4.
   - **Delivers:** `rig panel <script>`: the page, the WebSocket, the "driver is in charge"
     notice, live values both ways.
   - **Checks:** the panel's WebSocket protocol over the fake port (tests); the user plays the
     UC4 script from the panel in Live.
6. **The APC mini drum sequencer's checks** — blocked by: 3, and the sequencer's own plan.
   - **Delivers:** its check file and device profile; the skill mentions the rig (Decision 20)
     once the sequencer's checks pass.

## Out of scope

- Replacing the user's load test on the hardware.
- Controlling Live for anything other than testing a Remote Script.
- Changing AbletonMCP (the user's project; the two bugs above are reported to the user).
