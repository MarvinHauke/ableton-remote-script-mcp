# Status and next steps

The working state: what is in work, what needs a check, small items. Decisions live in the plans;
finished work is in the git history.

_Last updated: 2026-11-26 (0001 Decision 64 built on `feat/answer-v3`: CI tests, a pre-commit hook, ruff as a gate, the cut paths tested; 0001 Decisions 61–63 grilled, Decisions 61–63 built on `feat/answer-v3`: one exit-code table, the cut of declared collections, the default build; the rig wish in Small items; 0001 Decisions 58–60 built, one class-name ranking, a rig session module and the Elements reader's smells, on `refactor/class-ranking`; 0001 Decision 57 built and merged, one Elements reader; where to continue: four choices; 0003 step 6 merged; 0003 step 6 built, Decision 37: the skill's step sequencer section, the rig and the type check in the skill; 0001 Decision 56 done, task 3 built, the Editor setup page; task 2 built, `build-stubs --project`; task 1 built, the stubs fix; 0003 Decision 36 built: the sequencer in its own repo and script `APC_mini_mk1_Plus`, a submodule here; 0003 step 6 next; 0003 Decisions 33-34 built, nested Drum Rack and follow again; 0003 Decision 32 built, the steps edit the selected slot; 0002 Decision 30 built, held buttons and help on the panel; 0003 Decision 31 built, the page follows the playhead; the user's panel run, 9 of 9; 0003 Decision 30 built, the resolution pads; 0003 Decision 29 built, scene choice and the resolution on two buttons; 0003 step 5's first task built, the rig's selection, 0002 Decision 29; 0003 step 4 done, 0003 Decision 28, 0002 Decision 28; 0003 step 3 done, Decisions 26–27; 0003 step 2 done, Decisions 24–25; 0003 step 1 built and loaded in Live, Decisions 22–23; 0003 steps approved, Decision 21; 0002 step 6b done and run in Live, a clip's notes in check files, Decision 27; 0002 step 6a built, the panel's LED colours; plan 0003 spec and steps, Decisions 17–20, 0002 step 6 split; plan 0003 grilled, Decisions 1–16; 0002 Decision 26; plan 0003 drafted, 0001 Decision 55; agent team, Decision 54; distribution stays last)._

## Now

- Research done: [research/2026-11-14-sources-investigation.md](research/2026-11-14-sources-investigation.md)
  (Structure Void, gluon repos, local Live installs, existing MCPs, review of ChatGPT's discovery toolkit).
- `reference/gluon-live11`, `reference/gluon-live12` and `reference/MidiFighterV3` cloned (shallow, git-ignored).
  `reference/PrismScript` added by the user (2026-11-16): the Prism MIDI Sequencer's Remote Script
  (V2.0, a `_Framework` `ControlSurface` that works through the Live object model, listeners and
  SysEx). Its page states no licence, so it stays local. Against 12.4.16 it validates with no
  findings; `eval_names.py` finds 2 unknown names, both a listener on `Song.View` for
  `appointed_device`, which the index has on `Song` (observed in the Push 3 helper's model only).
  The script catches the error, so the listener most likely never attaches in Live; not checked
  in Live.
- Planning structure in place (this folder, `CLAUDE.md`, `docs/agents/`, `docs/guides/`), committed on `docs/plan-0001`.
- 0001 grilled (Decisions 1–27). Python 3.11.12 installed via uv (0001 decision 5).
- 0001 decided: spec and steps (2026-11-15).
- 0001 step 1 built on `feat/0001-step-1-tracer` (2026-11-15): `ableton-remote-script-mcp build-index` and
  `lookup class`; 12.4.16 indexed (283 modules, 731 classes). `uv run pytest` green (9 tests, 2 local-only).
- 0001 step 2 built on `feat/0001-step-2-extraction` (2026-11-15): full extraction (members,
  defaults, attributes, docstrings), every Remote Script and the Push 3 helper with `live_model` as a
  proxy model, index schema 2 (0001 decision 33), `list builds`. 12.4.16: 139 Remote Scripts, 1797
  modules, 4055 classes. `uv run pytest` green (22 tests, 5 local-only).
- 0001 step 3 built on `feat/0001-step-3-inheritance` (2026-11-15): inherited members with their
  origin, `search`, names resolved through re-exports and star imports at query time (0001
  decision 34, index schema 3). 12.4.16: every base resolves. `uv run pytest` green (44 tests,
  8 local-only).
- 0001 step 5 built on `feat/0001-step-5-outline` (2026-11-15): `outline <script>` (classes and
  roles, Specification fields, component map, mappings, elements, components, layers); the
  extractor records a statement summary of each function (0001 decision 35, index schema 4;
  rebuild older indexes), with the conditions each statement runs under, kept in a separate
  `live-<build>.statements.json` so the API index stays names and signatures (user story 14
  amended). `uv run pytest` green (60 tests, 10 local-only).
- 0001 decision 36 (2026-11-15): a documentation site on GitHub Pages, built with Zensical
  (pinned; plugin-free `mkdocs.yml`, MkDocs-compatible), a docs agent and a reviewer agent;
  skeleton as the new step 5a, user guides with step 12.
- 0001 step 5a built on `feat/0001-step-5a-docs-site` (2026-11-15): Zensical site (`mkdocs.yml`,
  `docs/`: Home, Getting started, How it works, CLI reference, Known limits, Develop), the CLI
  reference generated by `scripts/gen_cli_reference.py` (`--check`), `scripts/docs-check.sh`, the
  `docs` GitHub Pages workflow, `.claude/agents/docs.md` and `reviewer.md`. `uv run pytest` green
  (64 tests, 10 local-only).
- 0001 step 7 built on `feat/0001-step-7-validator` (2026-11-15): `validate <folder>` with the
  rules `folder-name`, `syntax-error`, `create-instance` and `unresolved-import`; imports are
  checked against the Python Live ships, which the index now lists (0001 decision 37, index
  schema 5; rebuild older indexes). `uv run pytest` green (87 tests, 11 local-only).
- 0001 step 9 built on `feat/0001-step-9-skill-v1` (2026-11-15): the skill
  `skills/ableton-remote-scripts/` v1 (workflow, `_Framework` reference and template, loading and
  logs, four scripts), the commands `install` and `log`, and `folder-name` for names that are
  not Python names (0001 decision 38). `examples/APC_mini_mk1/` passed the load test and the
  12-item checklist in Live 12.4.16; results, fixes and the comparison with Ableton's `APC_mini`
  are in [milestone-1/apc-mini-mk1.md](milestone-1/apc-mini-mk1.md), and the skill took the
  repeatable findings (0001 decisions 40 and 41). `log --script` also shows framework-only
  tracebacks. `uv run pytest` green (103 tests, 13 local-only).
- 0001 step 9a built on `feat/0001-step-9a-skill-evals` (2026-11-16, baseline round): three eval
  cases in `skills/ableton-remote-scripts/evals/`, `scripts/eval_names.py` (unknown API names),
  `eval_score.py` and `eval_run.sh` (`claude plugin eval` in its sandbox). With the skill every
  behaviour grader passed; both arms had no unknown names, and the name check cannot see names
  in v3 mappings, so step 8 also checks them and 9a is re-run after step 8 (0001 decision 42;
  scores in [milestone-1/skill-evals.md](milestone-1/skill-evals.md)). After review: the name
  check's false negatives fixed and the 18 scripts checked again (still no unknown names), tests
  for the eval scripts, `eval_run.sh` pins 12.4.16, keeps the traces and deletes the sandboxes.
  `uv run pytest` green (116 tests, 13 local-only).
- 0001 decision 43 (2026-11-16): step 8's rules and severities decided. `reference/MidiFighterV3`
  cloned (no licence, local only) as a working community v3 script for the false-positive check.
- `reference/APC40_MkII_StepSequencer_v1.0`, `v1.1` and `v1.1.1` added by the user (2026-11-16):
  a Push-style step sequencer, grid keyboard and drum mode for the APC40 mkII, built on
  Ableton's `APC40_MkII` script (`_Framework`). No licence stated, so they stay local. v1.1.1 is
  the one to read: v1.1's main script differs from it only in the version string, and v1.0 is
  the older 1,700-line version. All give no findings against 12.4.16. `eval_names.py` finds 11
  or 13 unknown names: `Song.scale_intervals` and `add_…_listener`/`remove_…_listener` on clips
  and tracks. The Push 3 helper's model has no listener methods at all, which is the same gap
  in the `Live` module as below. A reference for the user's planned APC mini drum sequencer.
- `reference/beatstep` cloned (2026-11-16, user's link): raphaelquast's Beatstep_Q, a `_Framework`
  script for the Arturia BeatStep with a 16-step sequencer, browser and session control, written
  for Live 9–11 (last commit 2023-11-24), GPL-3.0. Against 12.4.16: 0 findings in 7 files.
  `eval_names.py` finds 107 unknown names, none shown to be wrong:
  - about 80 are `add_…_listener`, `remove_…_listener` and `…_has_listener` on songs, tracks
    and clips
  - `is_foldable` (6), `Live.Base.LimitationError`, `Live.Browser.Relation.equal`: the gap in
    the `Live` module below
  - about 40 are its own setters, which it makes with `setattr` in a loop (`set_B_mode`, …)
- 0001 step 8 built on `feat/0001-step-8-framework-checks` (2026-11-16): the validator's
  framework checks (`mapping-key`, `element-name`, `unknown-component`, `specification-field`,
  `override-signature`, `component-guard`, `disconnect-base`) with the severities `error` and
  `warning` and a `not_checked` list. The script is compiled with Python 3.11 and read by the
  extractor over a copy of the index (0001 decision 44). Local-only: gluon's Live 12 clone and
  MidiFighterV3 give no error against 12.4.16; the one error in the Live 11 clone is a real API
  change. `eval_run.sh` now copies uv's Python 3.11 into the sandbox. `uv run pytest` green
  (135 tests, 13 local-only).
- 0001 decision 45 built (2026-11-16): `import-structure-void` reads Structure Void's 43 Live 12
  runtime pages (121 classes, 2655 members, 33 functions) into a local `documented` document.
  `lookup class` and `search` show those facts, and `eval_names.py` counts them, plus names a
  script's `setattr` builds. Unknown names: Beatstep_Q 107 → 6, the APC40 mkII step sequencer
  13 → 0, Prism 2 → 0, cmdAbl 10 → 6 (the rest are Python's socket methods and setters built
  without a literal start). `uv run pytest` green (141 tests, 13 local-only).
- Step 10's UC4 setup (2026-11-16, the user: "use a dump from the UC4 Editor, note which one"):
  the factory **SE17** (Ableton, tracks 1–8). Layout from `node tools/uc4-config.ts factory 17`
  in `~/Development/web/UC4_Editor` (the editor's model of the factory `SndA`). The UC4
  architect confirmed (2026-11-16): the device's SE17 is factory, and
  `dumps/2026-11-13-Sndc-SE17.syx` matches it byte for byte. **To put it back: the user runs
  `rESc` on SE17** (setup mode, encoder 5 held until the bars run). Sending a dump to the UC4
  has never been tested, and nothing is sent to it without the user's go and a fresh `SndA`
  backup. Feedback on the same channel and number is in the manual (`Std` displays, `EXt` green
  LEDs), but the velocity rule (> 0 on, 0 off) and whether an encoder's value follows an
  incoming CC are untested: assumptions for the load test's checklist. Which Global control is
  which printed function is unknown: the script's choice, told to the user. Global encoders use
  the same channel and numbers (ch13, 56–63) as group 8's green buttons, as CC versus notes.
- `reference/clyphx-live11` cloned (2026-11-17, user's link): ldrolez's ClyphX 2.7+ for Live
  10–12 (last push 2026-11-02), LGPL-3.0: read it, don't copy its code into the MIT repos. A
  large `_Framework` script (37 files) that drives Live through the object model and other
  control surfaces. Against 12.4.16: 2 errors, both real (`InstantMappingMakeDoc.py` still has
  Python 2 syntax, `lambda (k, v)`, and is imported without a dot; the import sits inside one
  action, so the script loads and only that action fails) and 1 `disconnect-base` warning.
  `eval_names.py` lists Push internals (private attributes), `Song.View`'s
  `selected_parameter` listener (Structure Void has no members for the `View` classes) and
  `offset_has_listener` on `_Framework`'s `SessionComponent`, which is a false unknown (below).
- 0001 step 10 in work on `feat/0001-step-10-v3-uc4` (2026-11-17): the skill's
  `references/v3-script.md` and `assets/v3_template/`, and `examples/Faderfox_UC4/` for SE17
  (all encoder and green button groups mapped at once, two components of our own, the Global
  assignment the script's choice; 0001 decision 47). Both validate with no findings against
  12.4.16 (14 keys of the mixer's name patterns not checked, looked up by hand). `log --script`
  now also reads a v3 script's Python `logging`. Facts and the 14-item checklist:
  [milestone-1/faderfox-uc4.md](milestone-1/faderfox-uc4.md). `uv run pytest` green
  (144 tests then).
- UC4 load test passed (2026-11-18, the user, Live 12.4.16): all 14 items, four after fixes that
  went into the v3 reference and template as `tested` facts (session ring without identity
  reply, value feedback, exact property types, `Mixer.MuteOn` = muted); Quant added on Global
  encoder 5. Results in [milestone-1/faderfox-uc4.md](milestone-1/faderfox-uc4.md).
  
- Before the round (0001 decision 48, 2026-11-18): the `session-ring` validator warning, two new
  graders on `uc4-mixer-v3`, listener names from `__subject_events__`/`__events__` in
  `eval_names.py`, a reviewer pass on step 10 and its fixes. `uv run pytest` green (148 tests,
  16 local-only).
- Extractor fix (2026-11-18): a store of `a or b` / `a and b` kept only its last part, and a
  conditional expression one branch. The stack simulation now merges the paths that meet at a
  forward jump's target (`a or b` whole, other merges `…`). The 12.4.16, 12.4.25b1 and 13.0b25
  indexes are rebuilt; the step-8 reference check still gives no framework error (134 of gluon's
  Live 12 folders). Found while checking the mute LED fact, which now cites
  `track.mute or track.muted_via_solo`. `uv run pytest` green (152 tests, 16 local-only).
- Plan 0002 grilled (2026-11-18, Decisions 1–21), steps approved; step 1 built on
  `feat/0002-step-1-port-spike`: `rig ports`, `rig probe`; a fader message reached Live through
  `ARS Test Rig` and came back, and AbletonMCP saw the volume change. `uv run pytest` green
  (155 tests). Step 2 built on `feat/0002-step-2-rig-run`: `outline` of a script folder,
  `rig elements`, check files, `rig run`, `rig serve`, `examples/Faderfox_UC4/checks.yaml`
  (165 tests). In Live: 24 passed, 0 failed, 5 to ask; after a Live restart with `rig serve`
  running, and with Live started before the port, the slot reconnects by itself. Step 3 built
  on `feat/0002-step-3-abletonmcp`: the AbletonMCP client (allow-list, repeated reads, three
  reads tested by hand), `state`/`events`/`do`/`requires` in check files, `rig abletonmcp`, the
  guide page `docs/test-rig.md`. The UC4 check file in Live: 34 passed, 0 failed, 4 to ask
  (172 tests). Step 4 merged: device profiles (`device.yaml`), the rig's identity reply
  (`examples/Rig_Identity`, identified in Live, v3's session box drawn), window captures for
  visual checks (Decision 22) and `rig restart-live` (Decision 23) (183 tests). Step 5 built on
  `feat/0002-step-5-web-panel`: `rig panel <script folder>`, a page on 127.0.0.1:9879 that plays
  through `rig serve`; `rig serve` now passes each client's sends to the others, so the page
  shows what `rig run` plays. In Live with Rig_Identity: a fader dragged on the page reached
  Live and came back, `rig run`'s sends showed up on the page (191 tests). Left for step 5's
  check: the user plays the UC4 script from the panel. Played 2026-11-18: the controls reached
  Live. The panel's WebSocket became a contract (Decision 24, `docs/rig-panel-protocol.md`), and
  the UC4 Editor's architect got a brief for its plan 0008 (play through the rig). Step 5 done and merged
  (2026-11-18). Next for 0002: step 6 (its LED panel first; the checks once 0003's steps are written).
- The 0001 step 10 eval round ran (user confirmed Decision 46, 2026-11-18). With the skill:
  100% of the graders in all three cases, 0 findings. Without it: no v3 script got the session box
  or the UC4's value feedback. The login expired partway through, so the v3 cases ran a second
  time. **Milestone 1 is complete.** Next for 0001: step 4 (order 4 → 6 → 11); the grilling session
  on the MCP design ideas comes before step 11.
  Found: the statement summary drops a call's keywords next to `**k` (an `outline` gap).
  None of this blocks 0001's 9a round.
- The MCP design ideas are grilled (0001 Decision 49, 2026-11-18) and are part of step 11.
- 0001 step 4 built on `feat/0001-step-4-diff` (2026-11-18): `diff <from> <to>` between two
  builds' indexes (Decision 50), Seam B tests and a local-only check (199 tests). Step 6 built
  on the same branch: Structure Void's framework pages from its search index,
  `check-structure-void` and the comparison in `lookup class` (Decision 51). Against 12.4.16:
  2565 classes agree, 22 differ (changes since the pages' older 12.x), 34 not matched (205
  tests). Steps 4 and 6 merged into main (2026-11-18).
- 0001 step 11 built on `feat/0001-step-11-mcp` (2026-11-18, Decision 52):
  - the MCP server (`ableton-remote-script-mcp mcp`, 7 read-only tools, MCP SDK 2.3);
  - the stable Python API with one versioned answer core;
  - answers capped at about 4,000 tokens, with a `cut` note and pages or sections;
  - `check-names` in the package and the skill;
  - `eval_score.py` counts tool calls, tokens and cost.

  213 tests; started with `uvx` over stdio against 12.4.16. Next: `build-stubs` (Decision 49
  Q9, local only), then step 12.
  Merged into main (2026-11-19).
- 0001 `build-stubs` built on `feat/0001-build-stubs` (2026-11-19, Decision 53):
  - type stubs of a build for the user's language server (1436 files for 12.4.16, local only);
  - basedpyright flags invented names in a sample script and no stub gaps in the examples;
  - the README's "How to use it" section: clone, index, skill, MCP server, stubs.

  219 tests. The user decided (2026-11-19) that distribution (PyPI, the plugin, a release
  workflow) is one of the last steps: improve the tool first. Step 12 waits.
- Plan 0003 drafted on `docs/plan-0003-drum-sequencer` (2026-11-19): a drum step sequencer for
  the APC mini mk1, built with the skill and the MCP server and tested on the rig (0001 Decision
  55: short eval rounds of 2–3 runs along the way, the MCP round after the sequencer, one big
  round at the end as step 13). Question 7 decided
  (0003 Decision 2, 0002 Decision 25): `get_clip_notes`, `add_notes_to_clip` and
  `clear_notes_from_clip` are on the rig's allow-list, not yet tested. The skill has a section
  "With the MCP server" (each script's tool, `build=` always, absolute folders). 220 tests.
  Registered for this project (2026-11-19, the user's go, local only): the MCP server
  `ableton-remote-script` (`claude mcp add --scope local`, connected), the skill as a link
  `.claude/skills/ableton-remote-scripts`, and `ABLETON_REMOTE_SCRIPT_MCP` in the git-ignored
  `.claude/settings.local.json` for its scripts (no `uv tool install`: `eval_run.sh` refuses to
  run beside one). 0003 grilled (2026-11-19, Decisions 3–16): one pad at a time on v3's
  components, `examples/APC_mini_drum_seq/`, the APC a normal test device again until its hardware check shows otherwise (Decision 12),
  the panel draws LED colours (0002 Decision 26, an addition to protocol 1, in 0002 step 6), a
  fixed clip preset. A one-run `uc4-mixer-v3` check after the skill's MCP section: with 9/9,
  without 7/9 (Decision 7). Next, in a fresh session: 0003's spec and steps.
- 0003 spec and steps written on `docs/plan-0003-drum-sequencer` (2026-11-19, the architect;
  steps wait for the user's approval). The API facts were looked up with the MCP server
  (12.4.16, `observed`): the v3 base `StepSequenceComponent` has no `playhead` property, it
  builds a `PlayheadComponent` that hands the lighting to Live's own playhead (Decision 17:
  v3's first, our own if it doesn't reach the mk1). 0002 step 6 split into 6a (panel LED
  colours) and 6b (a clip's notes in check files); order 0002 6a → 6b → 0003 1–7, the LED
  colours before the first rig checks as Decision 14 says (Decision 19). Three tool findings for 0003 step 1's list: `get_class("Clip")` cuts
  `Live.Clip.Clip` behind skin and notification classes named `Clip`; `Launchkey_MK4`'s outline
  shows no mappings; `lookup class` crashes (`KeyError: 'all_members'`, `cli.py`
  `_format_class`) on a cut answer, e.g. `Live.Clip.Clip`. The steps still wait for the
  user's approval.
- 0002 step 6a built on `feat/0002-step-6a-led-colours` (2026-11-19, solo): `leds` in
  `device.yaml` (value → colour, ` blink`), the optional `leds` field per element in the panel's
  `model` message (still protocol 1), the rule that clients ignore unknown fields in
  `docs/rig-panel-protocol.md`, the page drawing them; `docs/test-rig.md` says how. 223 tests.
  Open: the user's look at the colours (with the sequencer, 0003 step 1); the one-line note to
  the UC4 Editor's architect, handed to the user.
- 0002 step 6b built on `feat/0002-step-6b-clip-notes` (2026-11-19, solo): a `state` target
  `track N clip M` (`has_clip`, `name`, `length`, `notes`, `looping`, `loop_start`,
  `loop_end`), `add_notes_to_clip` taking `[pitch, start, length, velocity]` lists, and
  `requires` `drum_racks` and `empty_slots` (named, never created). 0002 Decision 27 (user):
  `get_session_snapshot` joins the reads, only for a clip's looping. `docs/test-rig.md` says
  how. 229 tests. Run in Live the same day (track 7, scene 8 of the test Set): two notes the
  user drew read back, an add and a clear seen by the user; `get_clip_notes`,
  `get_session_snapshot`, `add_notes_to_clip` and `clear_notes_from_clip` joined `TESTED`.
  Plan 0002's steps are done except 6a's look at the colours (with 0003 step 1).
- 0003 steps approved by the user (2026-11-19, Decision 21); 0003's spec and 0002 6a and 6b
  merged into main.
- 0003 step 1 built on `feat/0003-step-1-tracer` (2026-11-19, solo): `examples/APC_mini_drum_seq/`
  (v3 `StepSequenceComponent` on the top four rows, a pad bank of our own that selects the pad it
  plays, the clip preset, `grid_resolution` and `sequencer_clip` injected as `const`),
  `device.yaml` with the LED colours, a first `checks.yaml`, the results page
  [results/apc-mini-drum-seq.md](results/apc-mini-drum-seq.md) with 10 tool findings. Two package
  fixes (Decision 23): `lookup class` on a cut answer, `session-ring` only for components that use
  the ring. The clip is v3's: the playing one first (Decision 22, user). 235 tests. Loaded in Live
  12.4.16 on `ARS Test Rig`, no traceback; `rig run` 6 passed, 0 failed, twice; the user confirmed
  the selection. **Step 1 done.** Open: whether a pad press still sounds (heard, not told apart
  from the clip's note: a held pad on the panel or the hardware). Next: 0003 step 2 (playhead,
  loop end, pages), in a fresh session; Live's own playhead sent nothing to the port in step 1.
- 0003 step 2 built on `feat/0003-step-2-playhead` (2026-11-19, solo, branched from step 1's
  branch): the playhead and the loop end drawn by the script's own note editor (Decision 25: Live's
  playhead sent nothing, tested), track buttons as one page each (Decision 24, user), the skin's
  `LoopSelector` names, `checks.yaml` with four more steps. `rig run` 11 passed, 0 failed, after
  `rig restart-live` and track 9 rebuilt through AbletonMCP (the test Set is unsaved, so a restart
  loses it). **Step 2 done.** Next: 0003 step 3 (the pad bank); it also takes the reviewer's
  code points: the playhead redrawn with the page, a no-op `PlayheadComponent`, `step_count`,
  a note on triplets.
- 0003 step 3 built on `feat/0003-step-3-pad-bank` (2026-11-19, solo, branched from step 2's):
  pad colours (selected green blinking, a sound yellow, held red from the script's skin,
  Decision 27), scene 5–6 scroll the bank, the script's own auto-arm (Decision 26, user: pads
  sound only on an armed track), steps dark and inert on a track without a Drum Rack, Live's
  playhead off, and the reviewer's step-2 code points. `rig run` 19 passed, 0 failed; the user
  heard the held pad and saw the auto-arm. Step 1's open point is answered: a pad press plays
  its sound (on an armed track). **Step 3 done.** Next: 0003 step 4 (resolution, track choice,
  faders), in a fresh session. Step 4 also takes the reviewer's step-3 code points:
  - a Drum Rack added to the selected track leaves the steps empty, and a step press on a
    track without one drops the editor's clip (`_has_clip` side effects in
    `__on_clip_notes_changed` and `_on_pad_pressed`): re-set the clip on `drum_group_changed`;
  - the held-pad set: clear it in `set_matrix`, no red on a track without a Drum Rack, try
    `pressed_color`;
  - `super().update()` in `NoPlayheadComponent`;
  - a check that the auto-arm steps back while another track is armed by hand.
- 0003 step 4 built on `feat/0003-step-4-resolution-tracks-faders` (2026-11-19, solo, branched
  from step 3's): scene 1–4 the resolution (a submatrix of the scene buttons), scene 7–8 the
  previous and next track (`View_Control`), faders 1–8 tracks 1–8 and fader 9 the master
  (`Mixer`), the session ring enabled for the faders' box (0003 Decision 28), and the reviewer's
  step-3 code points. Two rig additions: a nested `state` field, `add_submatrix` in the
  controller model (0002 Decision 28). `rig run` 30 passed, 0 failed (after a first run on the
  stale installed copy, finding 19); the user saw the box and, by hand, the auto-arm give way to
  a track armed by hand. **Step 4 done.** Next: 0003 step 5 (the full check file, then the
  user's pattern on the panel and on the APC), in a fresh session. Before a rig run: `install
  examples/APC_mini_drum_seq --replace`, then `rig restart-live`. First task of step 5 (user,
  2026-11-19, 0002 Decision 29): the rig selects track and slot itself. In the user's AbletonMCP
  fork (`~/Development/python/ableton-mcp`, the user's repo: commit there only as the user says)
  a write command that sets the selected track and scene, and `get_session_info` reporting both;
  in the rig, the command on the allow-list (`do: {select_clip_slot: {track: 9, scene: 1}}` or
  similar), `song: {selected_track: …, selected_scene: …}` in `state`, and `checks.yaml` without
  the `select-track` question (the track-choice checks can then read the selection too).
  Also (user, 2026-11-19): AbletonMCP as a reference (a local clone under `reference/` or its
  path for `outline_reference_script`); its facts `documented`, double-checked before the skill
  uses them.
- 0003 step 5, first task built on `feat/0003-step-5-rig-selection` (2026-11-19, solo; 0002
  Decision 29): the rig sets and reads Live's selection (`select_clip_slot`, `song:
  {selected_track, selected_scene}`), `checks.yaml`'s `select-track` is a `do` with its state
  read back, and the track-choice steps read the selected track. The fork's half is committed on
  its own branch `feat/select-clip-slot` (from `cmdabl-testing`; the user merges and pushes).
  242 tests here, 59 in the fork. The fork's script is installed in the User Library. `rig run` 2026-11-19: 31 passed, 0 failed, 2 asked
  (answered yes); the user saw the selection move, so `select_clip_slot`, `create_clip` and
  `fire_clip` joined `TESTED` (results page). Open: the user's glance for `create_midi_track` and
  `stop_playback`. **First task done.** Next: step 5's main part, the user's pattern on the panel
  (`rig panel`), then on the APC (Decisions 12, 14), in a fresh session. Before a run: delete
  track 9's three clips and track 10 (or restart Live without saving); keep track 9.
- 0003 step 5, main part on `feat/0003-step-5-hardware` (2026-11-19, solo; from `main` after
  the merge `948e3f5`). In the panel run the user could move the track but not the clip slot:
  **0003 Decision 29** (user): scene buttons 1–2 the resolution finer and coarser (lit while they
  can move, `StepResolutionComponent`), 3–4 previous and next scene (`View_Control`), 5–8 and
  Shift unchanged. `checks.yaml`'s resolution steps rewritten, `scene-next` and `scene-prev`
  added; that the steps follow the scene is a check by hand (clip 3 still counts as playing in
  the run). Validator and `check-names` clean on 12.4.16, 242 tests, reviewed. `rig run`
  2026-11-19 after `install --replace` and `rig restart-live`: 35 passed, 0 failed, 2 asked
  (the user: pad heard, track 9 armed, the box on 1-8); `create_midi_track` and `stop_playback`
  joined `TESTED` (the user saw track 10 and the stopped transport).
  - **0003 Decision 30** (user, during the panel run): the resolution's own pads, notes 28–31
    (the right half's top row), v3's `resolution_buttons`, the active one yellow; two
    `resolution-pad` checks. `rig run` after install and restart: 37 passed, 0 failed, 2 asked.
  - **The user's panel run** (results page): 9 of 9 points work (the playhead "pretty sure",
    the delay makes it hard to tell).
  - **0003 Decision 31** (user, from the panel run): the page follows the playhead while the
    clip plays, a page pick pauses it until the transport starts or the clip changes
    (`PageLoopSelectorComponent`); `page-follows` and `page-one-pick` added, `page-two` picks page 2 by hand and it stays. Next:
    review, install, restart, track 9, `rig run`; the user tries the follow on the panel, then
    the APC run (Decisions 12, 14), with the results page. `rig run` 2026-11-19: 39 passed,
    0 failed, 2 asked (the three page checks pass).
  - The user's panel checks of Decision 31: the steps follow, a picked page holds while the
    clip plays.
  - **0002 Decision 30** (user, from the panel run): the panel holds buttons, Shift-click once
    (until the next plain click is released), Cmd-click until clicked again, Esc releases all;
    a `?` cheat sheet. The page still sends only 127 and 0, no protocol change; the latch logic
    is tested in node (`tests/test_rig_panel.py`, skipped without node).
  - **The APC run, first part** (user, 2026-11-19): with the Yellow Kit most points work; two
    problems, one cause: a step press on an empty slot while playing wrote into the track's
    playing clip, and a Drum Rack on a track with a playing clip seemed to take no notes.
    **0003 Decision 32** (user): the steps always edit the selected slot
    (`SelectedSlotTargetTrackComponent`); the checks select each clip's scene,
    `edit-other-slot` added. The local disassembly of 12.4.16's `ableton/v3` and `v2` is in
    `reference/live-12.4.16-dis/` (made now, it found the cause). Next: review, install,
    restart, `rig run`, then the rest of the APC run.
  - After Decision 32: `rig run` 40 passed (Yellow Kit), 40 passed (808 Core Kit on track 9).
    The user on the APC: working, also with another rack. **Step 5 done** (results page).
    Merged into `main` 2026-11-19 (`440f4c9`).
- 0003 after step 5 on `feat/0003-nested-drum-rack` (2026-11-19, solo): the user's test list
  (results page). **Decision 33**: a Drum Rack inside an Instrument Rack counts (v3's
  `find_drum_group_device`). **Decision 34**: the playhead's page turns following on again.
  `rig run` 40 passed (Yellow Kit), an ad-hoc check 5 passed on a Young Blood Kit track (before
  the review's delete/copy guard in `_on_matrix_pressed`, not yet run in Live).
  **Decision 35** (user): the sequencer in its own repo `../APC_mini_drum_seq`, a submodule here
  at `examples/APC_mini_drum_seq`: the next task, then 0003 step 6. For that task (reviewer):
  `.gitmodules` with a relative or remote URL, never a home path; a fresh clone needs `git
  submodule update --init` (tests that read the example: skip or a clear error); CLAUDE.md names
  the new repo and its owner; its README under the same Ableton-material rules; nothing pushed
  or published until the user says so.
  Merged into `main` 2026-11-19 (`c91d0ab`).
- 0003 Decision 36 on `feat/0003-own-repo` (2026-11-19, solo): the name (user: one repo per
  controller, created on GitHub as `MarvinHauke/APC_mini_mk1_Plus`) and the layout. The repo `../APC_mini_mk1_Plus` (10 commits
  of history, plus README, LICENSE, `pyrightconfig.json`) with the script in
  `APC_mini_mk1_Plus/`; here the submodule `examples/APC_mini_mk1_Plus`. Validates with 0
  findings against 12.4.16; `uv run pytest` 246 passed (5 skip without the submodule). The user
  pushed it to GitHub (2026-11-19, `98161a8`, the submodule's pointer), so `main` can be pushed
  after the merge (Decision 36's hold is lifted). Merged into `main` 2026-11-19 (`7c2d80d`). Then (user):
  the submodule is the only working copy, with GitHub as its `origin` and on `main`. The clone
  beside this repo is deleted, and the stubs are in `examples/APC_mini_mk1_Plus/stubs`. Two guards (Decision 36): `branch = main` in
  `.gitmodules`, `push.recurseSubmodules = check` in the local config. **For the user in Live:** `install`
  of `examples/APC_mini_mk1_Plus/APC_mini_mk1_Plus`, restart, choose `APC_mini_mk1_Plus` as
  the Control Surface, delete the old `APC_mini_drum_seq` from the User Library's Remote Scripts.
  Next: 0003 step 6.
  - **After step 5, before step 6** (user, 2026-11-19): a local disassembly (Python's `dis`) of
    12.4.16's `ableton/v3`, and the `v2` modules v3 inherits from, into `reference/`
    (git-ignored, never published). The 12.0-era decompiled reference was wrong or empty on
    three facts this step needed (the loop selector's slot order, `_update_matrix`, the note
    editor's `set_clip`), and step 6's facts are to be checked against 12.4.16.
- 0003 step 6 on `feat/0003-step-6-skill` (2026-11-20, solo; Decision 37), in both repos. The
  facts checked against 12.4.16's bytecode first (results page). The skill's v3 reference has
  "A step sequencer" (its snippets as one script: `validate` 0 findings, `check-names` 0
  unknown, `typecheck.sh` 0 errors, 12.4.16) and two general rules in Elements and Skins;
  `references/test-rig.md` and `scripts/rig.sh` put the rig in the skill (0002 Decision 20);
  `scripts/typecheck.sh` and SKILL.md's step 7 add the type check, with the eval case
  `fix-typecheck-errors`. `APC_mini_mk1_Plus`: the ignore comment on its two control
  decorators, type check clean. `uv run pytest` 263 passed. Tool findings: all filed (finding
  20 new, with finding 5's item); 4 and 12 are in the skill now. Next: 0003 step 7 (the
  sequencer eval case and the MCP round; the user's go for its cost).
  Merged into `main` in both repos 2026-11-25 (user); `APC_mini_mk1_Plus` at `44f2b40`.

- **Where to continue** (architect, 2026-11-25; the user chooses in the next session):
  1. 0003 step 7: the sequencer eval case and the MCP round (costs the user's usage: their go).
  2. ~~The architecture review's top pick: **one Elements reader**~~ (report in the OS temp
     folder, not kept). Built 2026-11-25 as 0001 Decision 57 on `refactor/elements-reader`
     (`elements.py`; the validator, the rig and `check_names` read from it; findings 3 and 16
     fixed; `check_names` says in `not_read` when it can't read the Elements class,
     `answer_version` 2; 277 tests). Merged into `main` 2026-11-25 (user). The other candidates,
     weaker:
     - ~~the cut cuts only declared collections~~ (findings 1, 8): built 2026-11-26 as 0001
       Decision 62 on `feat/answer-v3` (dropped records named; 296 tests), not merged yet;
     - ~~one class-name ranking~~ (findings 10, 13): built 2026-11-25 as 0001 Decision 58 on
       `refactor/class-ranking` (`query.class_rank`; 278 tests), not merged yet;
     - ~~one exit-code table~~: built 2026-11-26 as 0001 Decision 61 on `feat/answer-v3`
       (`cli.EXIT_CODES`, `folder_missing`, `refused`, a crash exits 5; `answer_version` 3;
       292 tests), not merged yet;
     - ~~a rig session module~~: built 2026-11-25 as 0001 Decision 59 on
       `refactor/class-ranking` (`rig/session.py`; 283 tests), not merged yet;
     - ~~the code review's eight smells in the Elements reader~~: fixed 2026-11-25 as 0001
       Decision 60 on `refactor/class-ranking`, not merged yet;
     - ~~the default build~~ (finding 11): built 2026-11-26 as 0001 Decision 63 on
       `feat/answer-v3` (the newest release or `default-build`'s setting, beta answers marked;
       304 tests), not merged yet.
     After these: a code review of `refactor/class-ranking` and `feat/answer-v3` (user,
     2026-11-25), then point 3. Before the review, the retro's guardrail (user, 2026-11-26):
     built as 0001 Decision 64 on `feat/answer-v3` (312 tests). Next: the mattpocock
     `code-review` of `main..feat/answer-v3`, its fixes, then `retro` (`skills-workflow.md`
     step 6). For that review: in `check_names` the field `unknown` is a list for a folder and
     a count for `names=[…]` (found by `test_cut_paths.py`; the cut skips the count).
  3. Reopen plan 0001 Decision 23, the runtime probe of the `Live` module (user's ChatGPT
     chat, 2026-11-25, on Structure Void's `dump_runtime_api.py`). Decision 23's condition
     ("when Claude gets LOM calls wrong") has shown twice: a float into an int property and a
     tuple into `set_feedback_channels` (`Boost.Python.ArgumentError`), types only Live's own
     docstrings show. Our own probe script, not Structure Void's code; the dump stays local;
     an index schema change (user). Later on it: paths through the LOM (`Song` → `DrumPad`).
  4. A plan for hardware discovery (the same chat): the user presses each control, the tool
     records the messages into a device profile. Reads the user's controller port, which no
     rule allows yet: a plan and a decision of its own. Step locks (below) are the other 0004
     candidate.
  From the chat, already built: version diffs (`diff_builds`), device profiles, verified
  examples, observed/documented/tested. Wrong in it: the `Live` module does have `.pyc` (the
  Push 3 helper's model); `self.song()` is `_Framework`, v3 has `self.song`.

## After grilling

- Since 2026-11-19 (0001 Decision 54, `CLAUDE.md` "Agent team", `scripts/agents.sh`): solo mode
  by default, one task per fresh architect session that plans and builds, with the reviewer and
  docs as subagents; peer builders (core, skill, rig, docs, reviewer) only for parallel work. Before that: one session with a `/compact`
  between steps (Decision 31).
- Order: 1 → 2 → 3 → 5 → 5a → 7 → 9 → 9a → 8 → 10 → 4 → 6 → 11 → 12 → 13 (13, the
  with/without benchmark for the README, was added last by the user, 0001 decision 39).

## Small items

- [idea, rig] (user, 2026-11-25, grilling round 1): more rigs, e.g. one for the UC4 editor's
  layout. The default rig stays as it is: an 8x8 matrix, a few encoders, pots and extra buttons
  for testing. Later, its layout could follow where a controller's buttons usually are; for
  simple tests it is fine now.

- **Done (0001 Decision 56), merged 2026-11-20:** stubs for writing scripts by hand, three tasks in order, branch
  `feat/0001-stubs-hand-dev` (from `chore/submodule-guards`, both unmerged): (1) the stubs'
  property and control-decorator fix, **built 2026-11-20** (`APC_mini_mk1_Plus` 13 → 2 errors,
  both the control idiom, which no stub can fix; accepted by the user 2026-11-20, task 3's page
  explains it and the `b: Any = …` workaround); (2) `build-stubs --project`, **built 2026-11-20**;
  (3) the docs page "Editor setup", **built 2026-11-20** (the control idiom's workaround is now
  `# pyright: ignore[reportGeneralTypeIssues]`, as `b: Any` fails under basedpyright); the
  created config sets `"typeCheckingMode": "standard"` (user, 2026-11-20). Decision 56
  done; merged into `main` in both repos 2026-11-20 (user).
- [needs-triage] 0001 (index): the index keeps only the last `def` of a name (architect,
  2026-11-20, from task 1). `lookup class GridResolutionComponent` shows `index` as a method
  `(self, index)` with `index.setter`, not a property; controls and `@listens` slots show as
  methods; a `NamedTuple`'s fields (annotations) are missing. The stubs work around all three;
  the index fix changes its content (a rebuild): grill.
- **Done (0003 step 6, Decision 37):** (user, 2026-11-20, "if it helps do that", on the architect's proposal): the
  skill's validate step also runs basedpyright (or pyright) with the project's stubs
  (`build-stubs --project`) when one is installed, as an extra check of the script's own code
  (a misspelled `self._attribute`, a wrong argument count, an undefined name), which
  `check-names` doesn't cover. It reports those and leaves out the known false errors: the v3
  control idiom ("refers to itself") and an attribute that may be `None`. Optional: no checker
  installed means the step is skipped with a note, never a failure. A task for arsm-skill, with
  an eval case. Settled (user, 2026-11-20, "it should ask you to write them but keeps reasons to
  do so. If there are errors it should handle them"):
  - **Stubs:** the skill doesn't write them; it asks the user to run `build-stubs --project`, and
    says why (the check, completion in their editor), so the user can decide.
  - **Errors:** the skill handles every error the checker reports, by fixing the script: a
    real mistake is corrected, an attribute that may be `None` gets its check, and the v3
    control idiom gets `# pyright: ignore[reportGeneralTypeIssues]` on the decorator's line
    (Decision 56). Nothing is filtered out of the result unseen. Standard mode
    (`typeCheckingMode`), whatever the project's config says (architect, 2026-11-20).
- [idea, validate/install] (user's run, 2026-11-19): `install examples/APC_mini_mk1_Plus` (the
  repo root) gave `create-instance` "no __init__.py". When the folder has none but exactly one
  subfolder that has one, say "did you mean `<folder>/<sub>`?". Also: without `--build` the
  newest indexed build (13.0b25) was used, while Live 12.4.16 is the one in use (fixed
  2026-11-26, 0001 Decision 63).
- [finding, build-stubs] (architect, 2026-11-19, on `APC_mini_mk1_Plus` with the 12.4.16
  stubs): the imports resolve, but pyright and basedpyright report 13 false errors.
  - A property with a setter (`listenable_property`, e.g. `StepResolutionComponent.index`) comes
    out as a plain method `def index(self, index)`.
  - A control's decorator (`@finer_button.pressed` over `def finer_button`) reads as a
    self-reference, and `MethodType` attribute writes fail (`subject`, `name`, `looping`).
  - Fix in the stubs (emit a property, give controls a `pressed` decorator type) before the user
    relies on them. Done 2026-11-20, except the control idiom (above).
- **Done** (`APC_mini_mk1_Plus` `9f2fee7`): the LICENSE holder is `Marvin Hauke` (the todo of
  2026-11-19 said `MarvinHauke`; the commit wrote the name with a space).
- [idea, later] From the user's test list (0003 results page): pad preview as an option; the
  first loop extension duplicates the content (Elektron); playhead and following in Arrangement
  View; a new clip's launch quantization (v3 starts it at once, legato).

- [idea, later] Step locks for the drum sequencer (user, 2026-11-19, after 0003 step 5; out of
  0003's scope): hold a step, faders 1-8 set macros 1-8 of the track's rack as clip automation
  for that step's time. A plan of its own (0004?), drafted and grilled after 0003 steps 6-7.
  Facts so far: `Envelope.insert_step` (documented, Structure Void); Push's and Move's
  `_insert_step` (12.4.16, observed) as local references. Grill: the faders' jump (0001
  Decision 29), how a locked step shows, several held steps, clearing a lock, which rack.

- [needs-triage] 0002 panel: the pads (`role=button`) have no `tabindex`, so the keyboard can't
  reach them (reviewer, 2026-11-19, Decision 30's review; older than it).

- [needs-triage] 0001 (index, MCP): the order of what a method does (which slots `__init__`
  registers, which method calls which) is not in the index; 0003 step 5 needed it twice and read
  the `.pyc` bytecode by hand. A statements feature for the MCP? Touches the index schema: grill.

- [needs-triage] Tool findings from 0003 step 6 (results page, finding 20): `check_names` doesn't
  list `ControlSurface._auto_arm`, set in v3's `ControlSurface.__init__`: finding 5's gap
  (instance attributes a base's `__init__` sets).
- [open, user] (reviewer, 2026-11-20, 0003 Decision 37): may a value read from a build's own
  bytecode (the local disassembly in `reference/`) count as `observed`? Today `observed` means
  "in the index", so such values are `documented`. A yes changes CLAUDE.md and the glossary.
- [needs-triage] Tool findings from 0003 step 1 (results page, findings 5–10; finding 3, `**dict`
  in `add_…` calls, fixed by 0001 Decision 57): `check_names` counts instance attributes of a mixin's
  `__init__` (`component_map`) as not members; no tool says which dependencies the framework
  injects and that `_get_additional_dependencies()` takes functions (a validator rule?);
  `lookup class <short name>` with many matches prints nothing but the cut note; `outline` of
  `Launchkey_MK4` shows no Specification or mappings; `get_class("Clip")` buries `Live.Clip.Clip`.
- [needs-triage] Tool findings from 0003 steps 2–3 (results page, 11, 13–15): ~~`get_class` and
  `outline` default to the newest index, the Live 13 beta~~ (0001 Decision 63);
  `check_names` resolves bare `NoteEditorComponent` to `bar_based_sequence` first; a one-`return`
  method has no statements; nothing says where a `__getattr__` forwards control names to.
- [needs-triage] Tool findings from 0003 step 4 (results page, 19; 16, an attribute
  `add_button_matrix` creates, fixed by 0001 Decision 57): `rig run` doesn't notice
  that the installed copy in the User Library is older than the check file's `script:` folder.
- The rig can't select a track or slot (AbletonMCP 1.7.1 has no command for it), so `ask_user`
  stays for the selection. A track created through AbletonMCP is selected by Live (the user,
  2026-11-19): a check can reach a new track that way.

- [grilled] **MCP server design ideas for step 11, from the user's sources (2026-11-17):**
  Zhang, Kraska, Khattab, *Recursive Language Models* (arxiv.org/abs/2512.24601), Zhang's blog
  post *The Mismanaged Geniuses Hypothesis* (alexzhang13.github.io/blog/2026/mgh/), and a video
  on Claude Code's "code mode" (youtube.com/watch?v=DRNbxPk9Ab8, only its title read). Their
  point for us: keep big reference data out of the agent's context and give it small
  primitives it can combine, from code too, with bounded answers. The index already stays out
  of context and answers are structured. Ideas:
  1. a batch tool `check_names`: every class, member and keyword of a draft in one call, each
     observed, documented or unknown (what `eval_names.py` does)
  2. the query core documented as a small Python API, so an agent in code mode can loop over
     lookups instead of one tool call each
  3. size limits with "more available" on `outline` and `search` (a section, a next page)
  4. a worked example in each tool description and a batch-check example in the skill
  
  Measure them in the 9a round and the step 13 benchmark (tool calls, tokens, invented names).
  Grilled 2026-11-18, round 1 (Q1–Q8): 0001 Decision 49. Round 2 (2026-11-18): Q9 type stubs for the
  user's language server; Q10 one versioned answer core, MCP extras allowed. Grilling closed;
  the comparison run goes into step 13.


- [needs-triage] Validator rule for attribute names by class (for example a made-up
  `self.song().some_method()` outside the mappings); step 8 checks only v3 mappings by class
  (0001 decision 43).

- [needs-triage] `mapping-key` for v3's `MixerComponent`: its `__getattr__` passes `set_…` on to
  its channel strips, so its keys are not checked (0001 decision 44). A rule could look the key
  up on the channel strip class.

- [needs-triage] remotify.io (Control Surface Studio, a paid Remote Script generator, with
  tutorials): a possible `documented` source and, if its terms allow, generated scripts for the
  false-positive check (user's suggestion, 2026-11-16). Not looked at yet.

- [needs-triage] A validator rule for attribute names by class on Live's objects
  (`song.view.add_appointed_device_listener` is on `Song`, not `Song.View`: Prism has this bug,
  and the name-only check can't see it). It could use the proxy model and Structure Void's
  `documented` classes (0001 decision 45).

- [ready-for-agent] Run the skill's trigger check: 20 queries in
  `skills/ableton-remote-scripts/evals/trigger-eval.json`, one round of `/skill-creator`'s
  `run_loop.py` (60 short `claude -p` calls), with `ANTHROPIC_API_KEY` unset so the claude.ai
  login is used. Wait until the usage limit allows it (0001 decision 42).

- [needs-triage] Validator rule: warn when two elements are built for the same MIDI type, channel
  and number (a load failure the 2010 blog posts name; check it in 12.4.16 first). From
  [research/2026-11-16-framework-basics-and-decompiling.md](research/2026-11-16-framework-basics-and-decompiling.md).

- [needs-triage] `APC_mini_mk1`: Shift's fader modes (volume, pan, send, device) and track
  modes (stop, solo, arm, mute, select), as on Ableton's script. Not in a step yet.
- [ready-for-human] The user plans to get a second grid controller (2026-11-15). On it, check
  how much LED traffic it takes before it loses presses; the APC mini's limit is in
  [milestone-1/apc-mini-mk1.md](milestone-1/apc-mini-mk1.md) (0001 decision 41).

- Done 2026-11-18 (the user's go): the Live 13 beta findings are out of the research doc
  (section 3's differences, the beta's `.pyc` counts, the Push2 move, the User Library listing)
  and out of plan step 4's check. The 60 unpushed commits were rewritten (`git filter-branch`),
  so no commit on `main` carries them.
- [ready-for-human] Push `main` (the step branches are merged and deleted, 2026-11-18), so the
  `docs` workflow publishes the site. GitHub Pages is set to deploy from GitHub Actions (the user, checked 2026-11-15).
- [ready-for-human] Ask the people responsible at Ableton whether extracted API facts and Live 13
  beta findings may be published (0001 decisions 15 and 36); until then they stay local.
- [ready-for-human] Set the GitHub repo description and topics (0001 decision 27).
- [ready-for-human] Archive `ableton-remote-script-skill` on GitHub; its README already points here (commit 3100c40 by the skill-repo session, 2026-11-15) (0001 decision 21).

## Backlog

- (empty)
