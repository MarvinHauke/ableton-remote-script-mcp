# 0002 — Virtual controller test rig

_Stage: in work — steps approved by the user 2026-11-18; step 1 built 2026-11-18; steps 2-4 built and run in Live 2026-11-18; step 5 done 2026-11-18. step 6a built 2026-11-19 (the user's look at the colours waits for 0003 step 1); step 6b done 2026-11-19 (run in Live). Frontier: plan 0003 step 1 (0003's steps written 2026-11-19; step 6 split into 6a and 6b, 0003 Decision 19)._
_Depends on: 0001 (outline, validator, `log`); input: the UC4 load test
([milestone-1/faderfox-uc4.md](milestone-1/faderfox-uc4.md))._

## Problem

Every behaviour check of a Remote Script needs the user, the hardware and a round of "press
this, what lights up?". The UC4 load test took two sessions, and three of its four bugs showed
only as wrong values or a traceback, which a machine can see. Some hardware can't be trusted for
the test at all: the APC mini mk1 lost presses under LED load, so a step sequencer couldn't be
load-tested on it reliably (since `OptimizedControlSurface` none seen, not yet confirmed: 0003
Decision 12). The user wants a virtual controller that sends the script's MIDI
and shows what Live sends back, which the user can play with and Claude can drive itself.

## Solution

A **test rig** in this repo's package, started as `ableton-remote-script-mcp rig …`. Its driver
opens a named virtual MIDI port, plays a controller to a Remote Script the way a **check file**
says, records what Live sends back, reads `Log.txt` and, when AbletonMCP runs, the changes its
listeners saw. It reports each step as passed, failed or "ask the user". The controller's
elements come from `outline` of the script; a **device profile** adds layout and identity. A
web panel shows the same controller to the user and plays it through the driver. The rig works
in the **test Set** and never saves it. What it can't see (the session box, the hardware's own
behaviour) stays the user's load test. Decisions 1–24 below.

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
  display hints (absolute, relative, bipolar), LED colours (Decision 26).
- **Report:** printed summary plus `checks.result.json` beside the check file (git-ignored).
- **Panel:** a static page and a WebSocket served on localhost by `rig panel`; the page shows
  "parallel view: the driver is in charge". It renders the controller model and the last value
  sent and received per element, in the profile's LED colours where it gives them (Decision 26).

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
22. **The agent may capture Live's window to decide visual checks** (agent proposed, user agreed,
    2026-11-18, after step 4). For an `ask_user` step about what Live shows (the session box, the
    selection, a clip's state), the agent may capture Live's main window, and only that window,
    by its window id (`screencapture -l`). This works with Live behind other windows: on
    2026-11-18 it showed step 4's box around tracks 1-4. The images stay in the agent's scratchpad
    and are deleted after reading. What only the hardware shows (a display, LEDs it keeps per
    group) stays with the user. Restarting Live is Decision 23.
23. **The agent may restart Live for the test rig, never saving** (the user chose AppleScript,
    2026-11-18). The cmdAbl session has no way to restart Live; it leaves restarts to the user.
    `rig restart-live` does it:
    - It acts only while Live's windows show just the test Set (`Untitled`, the unsaved Set Live
      opens from the user's template); otherwise it does nothing.
    - It quits Live through AppleScript without waiting for an answer.
    - If Live asks to save, it presses the leftmost button, "Don't Save", and only if the
      dialog's text is exactly `Save changes to "Untitled" before closing?` with three buttons.
      Live draws that dialog itself: macOS sees three unnamed buttons, Don't Save left, Cancel
      and Save right (Live 12.4.16).
    - It opens the same Live app again and waits for a new session in `Log.txt`, and optionally
      for a script's message.
    - It needs the terminal's Accessibility permission, which the user grants.
    Tested 2026-11-18 in 12.4.16. Without changes, Live quit with no dialog. With a change, the
    rig answered the dialog itself. Either way, Live was back with `Rig_Identity` identified in
    about 9 s. Saving, closing other Sets and switching control surfaces stay the user's.

24. **The panel's WebSocket is a contract other programs may use** (the user asked whether the
    UC4 Editor could play through the rig instead of the panel's page, and agreed to the agent's
    plan, 2026-11-18). The protocol is versioned (`protocol` in the model event, version 1) and
    written down in `docs/rig-panel-protocol.md`. It sends raw bytes both ways and takes a raw
    `send`, so a client that knows the device needs no script element names. Only pages served
    from this machine may connect. The UC4 Editor's side (playing from its device view, Live's
    LEDs in it) belongs to that project: the agent sends its architect a brief for its plan 0008
    (live view) to grill, and builds nothing in that repo. The panel's own page stays, for
    scripts whose device has no editor.
25. **AbletonMCP's note commands join the allow-list** (user, 2026-11-19, "allow the note
    check", for plan 0003's drum sequencer; adds to Decision 6). The read `get_clip_notes` and
    the test-Set changes `add_notes_to_clip` and `clear_notes_from_clip`. Like every command,
    each joins the "tested" list only after it read back, or set, a state the user made or
    checked by hand in Live. Still never sent: deleting clips, the browser, rating and
    dataset consent. How check files state a clip's notes is part of step 6.
26. **The panel draws LED colours from the device profile** (user, 2026-11-19, plan 0003
    Decision 14, "yes to a-d"). `device.yaml` may give a `leds` map, value → colour and
    blinking, per element or matrix; the panel draws them, so it can stand in for a grid
    controller. The colours reach the page as a new optional field per element in the `model`
    message: an addition, still protocol 1, and `docs/rig-panel-protocol.md` gains the rule that
    clients ignore fields they don't know. The UC4 Editor's architect gets a one-line note.
    Changes Decision 24's contract by that field and the rule on unknown fields only.
27. **The rig may read AbletonMCP's `get_session_snapshot`** (user, 2026-11-19, step 6b, asked by
    the architect; adds to Decisions 6 and 25). Only for a clip's `looping`, `loop_start` and
    `loop_end`, which no other allowed command reports, and only with `include_notes` and
    `include_params` off. A read, so it joins `READS`; like every command it is labelled
    untested until it read back a state the user set by hand.
28. **Two additions for plan 0003 step 4** (architect, 2026-11-19, 0003 Decision 28; no contract
    changes: the panel's model and protocol stay as they are). A nested `state` field matches the
    fields it names, numbers within the tolerance (`song: {master_track: {volume: 1.0}}`, from
    `get_session_info`). The controller model reads `add_submatrix` as another name for a part of
    a matrix built before it (`Controller.submatrices`; no new elements, so the panel and the
    check names are unchanged).
29. **The rig selects the track and clip slot itself** (user, 2026-11-19, after 0003 step 4:
    "the chosen selected clip slot is essential for automated testing"; adds to Decisions 6 and
    25). The user's AbletonMCP fork (`MarvinHauke/ableton-mcp`, MIT) gets a write command that
    sets Live's selected track and scene (`Song.View.selected_track`, `selected_scene`), and its
    session info reports both, so a check can set the selection in `do` and read it back in
    `state`. The command joins the allow-list, labelled untested until it read back a selection
    the user saw in Live (Decision 25). It lives in the test tool, never in a script the skill
    writes. Replaces the `ask_user` selection steps (0003's `select-track`). Rejected: creating
    and deleting a clip in the slot to move the selection (not known to move it, and it changes
    the Set for nothing). AbletonMCP's code is MIT: it may also serve as a cited, `documented`
    source of `Live` API usage and as a reference script for `outline_reference_script`.
    Confirmed (user, 2026-11-19): AbletonMCP is a reference as well as a test tool. Its facts
    stay `documented` until the index or the rig checks them, and are double-checked for a
    better way before the skill builds on them.

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
   - **Built** (2026-11-18, agent; branch `feat/0002-step-2-rig-run`), not yet run against Live:
     - `outline` takes a script folder (`outline examples/Faderfox_UC4`), read like the
       validator reads it (sources compiled, then the index overlay).
     - The controller model (`rig/controller.py`, `rig elements <folder>`): `outline` finds the
       calls that build elements; the arguments come from those calls in the script's source,
       because the statement summary drops the keywords of a call that also passes `**k`
       (`channel=CH14` next to `**SHOWS_VALUE`). Defaults observed in the 12.4.16 index:
       the channel comes from the keywords, else `global_channel`; `ButtonElement` and
       `EncoderElement` default to `msg_type=MIDI_CC_TYPE`. A matrix element is `<matrix>[i]`,
       counted row by row. For the UC4 it gives 142 elements, matching `elements.py`. Elements
       it can't work out are listed as not read, never guessed.
     - Check files (`rig/checks.py`): `send` takes an element and a value (a number, `press`, or
       steps on a relative encoder), or a raw message. `expect` checks the last reply per
       element: a value, a list of values, `any` or `none`. Also `log: clean`, `ask_user`,
       `depends_on`, and `quiet`/`timeout` per step. Before the first step the run waits for
       `settle` seconds of quiet. Relative steps are encoded only as two's complement, the
       only mode tested so far (the UC4's CCr1).
     - `rig run <checks.yaml>` goes through `rig serve` when one is running; otherwise it opens
       its own port and waits for Live. It prints a report and writes `checks.result.json`
       beside the check file (git-ignored). Exit codes: 0 no step failed, 1 a step failed,
       2 Live never connected, 3 no rig extra, 4 the check file can't be read.
     - `rig serve` (`rig/serve.py`) holds the port and talks JSON lines on 127.0.0.1:9878
       (AbletonMCP uses 9877). Each client gets its own inbox.
     - The first check file is `examples/Faderfox_UC4/checks.yaml`: 22 steps from MIDI and the
       log, 6 `ask_user` steps. Items 1 and 14 stay with the start of the run and the user.
     - PyYAML joins the `rig` extra. 165 tests pass (seam C over `MemoryPort`, including a
       served port; 3 new local-only tests: the folder outline, the UC4 model and its check
       file's names).
   - **Run in Live** (12.4.16, the test Set, over `rig serve`; 2026-11-18): 24 passed, 0 failed,
     5 to ask the user, which agrees with the user's 14 results. Three runs to get there:
     - Live sends a value back later than 150 ms after it arrives: each echo turned up in the next
       step. A step now listens at least `wait` (default 0.5 s).
     - Live sends a value back only when it changes: the same values a second time got no reply.
       Each value step in the check file first sends one below its value.
     - The test Set has 2 returns, so send D has nothing to set: the step uses send B.
     - When `rig serve` opened the port while Live was running, the slot (picked in step 1)
       reconnected and the script sent its start-up state (228 messages) without a restart.
   - **Live restart with `rig serve` running** (the user, 2026-11-18): the slot kept
     `ARS Test Rig` and `Faderfox_UC4`; the script logged `ready`, the port stayed open, and the
     check file passed again (24 passed). So after a script change: keep `rig serve` running,
     restart Live, run the checks.
   - **Live started while no `rig serve` held the port** (the user, 2026-11-18): slot 1 kept
     `ARS Test Rig` as its input and output, greyed and not offered in the list. Once `rig serve`
     started, the slot reconnected by itself: the script sent its start-up state within 3 s, and
     the check file passed (24 passed). So the order doesn't matter: the port can come before or
     after Live.
   - **Step 2 done** (2026-11-18). The 5 `ask_user` steps were answered in the user's load test;
     the group LED step needs the UC4 itself.
   - **Found on the way:** the extractor's statement summary loses the keywords of a call that
     also passes `**k`. That is an `outline` gap for every script, recorded for 0001.
3. **AbletonMCP** — blocked by: 2.
   - **Delivers:** the socket client (version, allow-list, repeated reads, events), `state`
     expectations, `do` steps (Live → controller), `requires` checked against the test Set and
     creating what is missing; the tested-command list procedure (Decision 6).
   - **Checks:** seam C over the fake socket; the user sets three states by hand for the
     tested list; the full UC4 check file reproduces the 14 results (Decision 16).
   - **Built** (2026-11-18, agent; branch `feat/0002-step-3-abletonmcp`):
     - `rig/abletonmcp.py`: the client. AbletonMCP's protocol, read from its 1.7.1 script: one
       JSON object per request and per answer, with no delimiter. The client checks the version
       with `get_script_info` and refuses commands outside the allow-list before sending
       anything. Reads repeat until two answers agree. `TESTED` holds the commands checked
       against a state the user set by hand; a result from any other command is labelled.
     - `rig/state.py`: check files gain `do` (allowed AbletonMCP writes), `state` (`song`,
       `track N`, `track N device M`, fields compared within 0.005), `events` (AbletonMCP's
       listener events during the step) and `requires` (the run stops with a list of what's
       missing; a missing clip on a MIDI track is created). Everything counts from 1, as Live
       shows it. Without AbletonMCP, `do` steps are skipped and state is listed as not checked.
     - `rig abletonmcp` prints what the rig reads, so the user can compare it with Live.
     - Run in Live (12.4.16, the test Set): 29 passed, including state for volume, pan, mute,
       solo (a track silenced by a solo reads `mute: false`), arm and transport. In the Live →
       controller direction, a macro set through AbletonMCP shows on Rack encoder 1.
     - Learned: Tempo Coarse +1 and −1 sent at once fire no `tempo_changed` (one at a time
       does). Clips start and stop on the next bar (2 s at 120 BPM), so those steps listen at
       least 2.5 s. Pressing Launch 2 also resends the controller's whole state. The two clip
       LED steps failed at first: track 2's clips have follow actions (the user), so after a fire
       the track moved on to its scene 2 clip. The clip steps now use track 1, scene 1, where
       `requires` creates a plain 4-beat clip.
     - Tested-command list (Decision 6; the user set three states by hand, 2026-11-18): the
       rig read track 3 muted (`get_track_info`), tempo 123 (`get_session_info`) and Macro 2
       = 64 (`get_device_parameters`). All three are in `TESTED`.
     - The full UC4 check file in Live: 34 passed, 0 failed, 4 to ask the user (session box,
       navigation, device follow, group LEDs). This reproduces the load test's results for
       items 3-12.
     - Docs: the site page `docs/test-rig.md` ("Testing a script with the test rig"), linked
       from Getting started and How it works. It gives AbletonMCP no link, because the copy
       used here may be a fork.
   - **Done** (2026-11-18). 172 tests pass.
   - **Docs:** a guide page "Testing a script with the test rig"; How it works and Getting
     started mention the rig.
4. **Device profiles and identity** — blocked by: 2.
   - **Delivers:** `device.yaml` (identity reply, layout, display hints), the identity reply
     when Live asks; the UC4 profile.
   - **Checks:** seam C: a script that waits for identity starts only with the reply; local: a
     v3 sample script with `identity_response_id_bytes` starts with the rig's reply (`7D`).
   - **Built** (2026-11-18, agent; branch `feat/0002-step-4-device-profiles`):
     - `rig/profile.py`: `device.yaml` with the identity request and reply, the layout and the
       display hints. The reply is `none` by default, `rig` for the rig's own identity
       (manufacturer `7D`), or the device's message in hex.
     - `rig serve --profile` answers the request with no client connected. `rig run` uses the
       `device.yaml` beside the check file, checks its names, and warns when `rig serve` runs
       without the reply.
     - `examples/Rig_Identity` (a v3 script with the rig's identity bytes and the framework's
       own session ring) and `examples/Faderfox_UC4/device.yaml` (no reply, a layout row per
       group, display hints only from the device facts). 179 tests pass.
   - **In Live** (12.4.16, the user, 2026-11-18):
     - With `rig serve` running without a reply, the script logged
       `ready, waiting for the identity reply` and nothing more.
     - When `rig serve` restarted with `--profile`, Live asked again as soon as the port
       reappeared. The rig answered once, and the script logged
       `identified: 7F 06 02 7D 00 01 00 01 00 01 00 00`, then sent its start-up state.
     - So the bytes a v3 script gets lack `F0 7E` and `F7`. That's why the framework finds
       `06 02` at positions 1–2 and the id bytes from position 3 (tested).
     - Its check file: fader 1 passed. No box was drawn (the user). The reason, observed in
       the 12.4.16 index: `ControlSurface.__init__` sets `_can_enable_session_ring` only when the
       script is identifiable and has a `SessionComponent`, and the sample mapped only the
       Mixer. The sample gained four launch buttons mapped to `Session`. After a Live restart
       the box around tracks 1-4 was drawn (the user, 2026-11-18), so the identity reply enables
       v3's own ring (tested). Without a reply it stays off, which was the UC4's first bug.
   - **Done** (2026-11-18).
5. **Web panel** — blocked by: 4.
   - **Delivers:** `rig panel <script>`: the page, the WebSocket, the "driver is in charge"
     notice, live values both ways.
   - **Checks:** the panel's WebSocket protocol over the fake port (tests); the user plays the
     UC4 script from the panel in Live.
   - **Built** (2026-11-18, `feat/0002-step-5-web-panel`):
     - `rig/panel.py` and `rig/panel.html`: `rig panel <script folder>` serves one page and a
       WebSocket on 127.0.0.1:9879 (a minimal RFC 6455 server in the standard library, so no
       new dependency). The panel is a client of `rig serve` (Decision 9) and refuses to start
       without it. When `rig serve` is restarted, it connects again by itself.
     - The page draws the `device.yaml` layout, or one row per matrix and then the single
       elements, eight to a row (Decision 10). An element the layout leaves out is added at the
       end, so none is hidden. Buttons are pads (127 pressed, 0 let go) with an LED lit by
       Live's value. Absolute encoders are sliders, bipolar ones show the value from the
       centre, relative ones step −/+ (Shift: 10). Each cell shows the last value played (↑)
       and the last value Live sent (↓). A log lists every message with its element.
     - `rig serve` passes each client's sends to the other clients (`drain` gains `sent`), so
       the page shows what `rig run` plays, marked "driver" (the notice: the driver is in
       charge). A page that connects later gets the last values seen.
     - In Live 12.4.16 with `Rig_Identity` on `ARS Test Rig`: a fader dragged on the page went
       to Live, and Live's echo came back to the page. During `rig run`, the page showed the
       driver's sends and Live's reply. The page was checked in Chrome. 191 tests.
     - Only pages served from this machine may open the WebSocket: the browser's `Origin` must
       be localhost, 127.0.0.1, ::1 or a `.localhost` name, so no website open in the browser
       can play into Live. Besides `play` by element name, the WebSocket takes `send` with one
       raw MIDI message, for a client that knows the device rather than the script.
     - The user played the UC4 script from the panel (2026-11-18): the controls tried reached
       Live. The mute buttons seemed to need two clicks. Checked: each press toggled track 1's
       mute (AbletonMCP read True, False, True), and the page ended on Live's value. Live
       answers a press with a quick 0/127 pair and then the settled value about 40 ms later.
       The user then saw it working after the servers were restarted.
   - **Done** (2026-11-18, the user).
6. **The APC mini drum sequencer's checks** — split in two around plan 0003's steps (0003
   Decision 19, architect, 2026-11-19). The sequencer's check file and device profile grow in
   0003's steps 1–5 (0003 Decision 20), no longer here.
   - **6a. LED colours in the panel** — blocked by: 5. Before 0003 step 1 (0003 Decision 14).
     - **Delivers:** Decision 26: `leds` in `device.yaml` (value → colour and blinking, per
       element or matrix), the new optional field per element in the `model` message, the rule
       in `docs/rig-panel-protocol.md` that clients ignore unknown fields, the page drawing them;
       the one-line note to the UC4 Editor's architect.
     - **Checks:** seam C (a profile's `leds` reaches the `model` message; a profile without
       them gives the message as before); the protocol page's check; the user sees a profile's
       colours on the page with `Rig_Identity` or the sequencer.
     - **Built** (2026-11-19, the architect in solo mode, branch `feat/0002-step-6a-led-colours`):
       `leds` names an element or a matrix, each value a colour (`off`, a name from
       `rig/profile.py` `COLOURS`, or a quoted `'#rrggbb'`) with ` blink` after it; an element's
       own map wins over its matrix's; a value the map leaves out lights the LED by the value as
       before. YAML 1.1 reads a bare `off` (and `no`, `false`) as false, taken as off; `on` is
       refused. A map on a control that isn't a button is refused like an unknown name (exit 4).
       The model's field: `"leds": {"<value>": {"colour": "#rrggbb" | null, "blink": bool}}`,
       absent without a map. 223 tests. Open: the user's look at the colours, with the
       sequencer's `device.yaml` in 0003 step 1 (`Rig_Identity`'s values from Live's default skin
       aren't known, so no map is guessed for it); the UC4 Editor note, handed to the user.
   - **6b. A clip's notes in check files** — blocked by: 3. Before 0003 step 1.
     - **Delivers:** Decision 25: a `state` target `track N clip M` (`notes` as pitch, start,
       length, velocity; `length`, `looping`, `name`) read with `get_clip_notes` and the clip
       info; `do` with `add_notes_to_clip` and `clear_notes_from_clip`; `requires` names a Drum
       Rack track and an empty slot when they are missing (never creates the Drum Rack).
     - **Checks:** seam C over the fake socket; the user sets two notes by hand in a test-Set
       clip, the rig reads them back, and `get_clip_notes` joins `TESTED`; an add and a clear
       read back and checked by the user join it too.
     - **Built** (2026-11-19, the architect in solo mode, branch `feat/0002-step-6b-clip-notes`):
       `track N clip M` takes `has_clip`, `name` and `length` (read with `get_track_info`, which is
       tested), `notes` (`get_clip_notes`) and `looping`, `loop_start` and `loop_end`
       (`get_session_snapshot`, Decision 27, repeated until the three loop fields agree, since a
       whole snapshot holds the song time). Each read is made only when a field needs it. An
       empty slot reads as `has_clip: false`, and its other fields as "(no clip)". A note is
       `[pitch, start, length]` or `[pitch, start, length, velocity]`. Notes match in any order,
       and a muted note matches none. `add_notes_to_clip` takes the same lists, with velocity
       100 when it is left out. `requires` takes `drum_racks` (AbletonMCP's device type
       `drum_machine`) and `empty_slots`, both only named when missing. 229 tests.
     - **Run in Live** (2026-11-19, Live 12.4.16, the user's clip on track 7, scene 8): the rig
       read the two notes the user drew (C#3 on 1.2, C3 on 1.4) and the clip looping over its
       bar, which the user confirmed with a screenshot; an added D3 on 1.1 and then a clear were
       read back and seen by the user. `get_clip_notes`, `get_session_snapshot`,
       `add_notes_to_clip` and `clear_notes_from_clip` joined `TESTED`. Step 6b is done.
   - The skill mentions the rig (Decision 20) in 0003 step 6.

## Out of scope

- Replacing the user's load test on the hardware.
- Controlling Live for anything other than testing a Remote Script.
- Changing AbletonMCP (the user's project; the two bugs above are reported to the user).
