# 0001 — Architecture: API index, skill, MCP server

_Stage: in work — steps 1–2 built 2026-11-15. Frontier: step 3._
_Depends on: none. Input: [research/2026-11-14-sources-investigation.md](research/2026-11-14-sources-investigation.md)_

## Problem Statement

A musician who wants a Remote Script for their controller in Live 12.4 or 13 has no reliable API
to work from. Ableton publishes no reference for its control-surface framework (`_Framework`,
`ableton.v2`, `ableton.v3`). The best public reference (Structure Void) covers an unstated Live 12.x
build, without default values and without Live 13, and the public decompiled sources are a 12.0-era
snapshot with broken function bodies. When Claude is asked to write a script, it invents class
names, Specification fields and signatures. The script then fails to load, or misbehaves without
a clear reason, and the user has to debug Ableton's undocumented internals by hand.

## Solution

An unofficial, public **MCP server and agent skill** that make Claude (and other agents) write
Remote Scripts from facts instead of guesses:

- **API index.** The user builds it once per Live build from their own installed Live, with one
  command. It records every framework module, every controller script and the LOM as Live ships
  it, labelled with the Live build.
- **Skill.** It walks Claude through writing a script:
  1. collect the controller facts
  2. choose the framework generation
  3. design the elements, components, layers and modes
  4. look up every API name in the index
  5. write the files
  6. validate
  7. install
  8. read `Log.txt`

  Every API claim names its Live build and fact confidence.
- **MCP server.** The same lookups and the validator as tools, for faster and more reliable use.
- **Plugin.** One Claude Code plugin installs the skill and the MCP server together. Other agents
  install the skill with `npx skills add` and add the MCP server to their own configuration.

The user ends up with a script that loads without a traceback, does what their device controls are
meant to do, and uses only API names that exist in the Live build they target.

## User Stories

**Building the API index**

1. As a script author, I want to build the API index from my installed Live with one command, so that the facts match the Live I actually use.
2. As a script author, I want the index built separately for each Live build (12.4.16, 13.0b25), so that facts from one build never leak into another.
3. As a script author, I want the index command to find my installed Live apps by itself, so that I don't have to type bundle paths.
4. As a script author, I want to name a Live app explicitly when I have several, so that I control which build is indexed.
5. As a script author, I want the index command to bring its own Python 3.11 through uv, so that my system Python stays untouched.
6. As a script author, I want every framework module indexed (`_Framework`, `ableton.v2`, `ableton.v3`, the helper packages), so that no part of the framework is a blind spot.
7. As a script author, I want every controller script indexed, so that the skill can pick the reference scripts that fit my controller.
8. As a script author, I want the Push 3 helper's scripts and `live_model` indexed too, so that Push and the LOM are covered.
9. As a script author, I want each class recorded with its bases, so that inherited members can be resolved.
10. As a script author, I want methods recorded with argument names and, where Live's bytecode holds them, default values, so that generated calls use the right arguments.
11. As a script author, I want class attributes recorded (e.g. every `ControlSurfaceSpecification` field), so that generated Specifications use only fields that exist.
12. As a script author, I want docstrings recorded where they exist, so that the skill can explain what a member does.
13. As a script author, I want each fact to name its source (framework `.pyc`, `live_model`, Structure Void), so that I can judge how far to trust it.
14. As a script author, I want the index to contain names and signatures only, never function bodies, so that it never holds Ableton's implementation code.
15. As a script author, I want a clear message when a `.pyc` can't be read, naming the file, so that one broken file doesn't silently hide part of the framework.
16. As a script author, I want rebuilding a build's index to replace it completely, so that stale facts never remain.
17. As a script author, I want the index stored outside the repo or in a git-ignored folder, so that Ableton material never ends up in a commit.
18. As a script author, I want the Live 13 beta index kept local and out of anything published, so that I stay within the beta terms.
19. As a script author, I want to see which builds are indexed and when, so that I know what the lookups cover.

**Structure Void as a cross-check**

20. As a script author, I want Structure Void's reference (Live 9–12) loaded locally as a `documented` source, so that facts missing from my index can still be found, clearly labelled.
21. As a script author, I want lookups to show where Structure Void and my index disagree, so that I notice members that were renamed or removed.
22. As a script author, I want links to Structure Void's page for a module instead of copied text, so that his work is credited and his licence respected.

**Looking up the API**

23. As a script author, I want to search the API by name or words, so that I find classes and members without knowing the exact module.
24. As a script author, I want to see a class with all its members, including inherited ones and where each comes from, so that I know what a component or element really offers.
25. As a script author, I want every lookup result to show its Live build and fact confidence, so that I never mistake a `documented` fact for an `observed` one.
26. As a script author, I want to compare two builds (12.4.16 vs 13.0b25), so that I see what changed before porting a script.
27. As a script author, I want the outline of a reference script (its classes, the Specification fields it sets, its component map, its elements), so that I can learn from Ableton's own scripts without reading decompiled bodies.
28. As a script author, I want lookups to say "index missing, run …" when there is no index, so that Claude never answers from memory instead.
29. As a script author, I want lookups to say "not found in build X" clearly, so that a missing name is a signal, not a silent gap.
30. As a script author, I want to look up LOM classes (`Song`, `Track`, `Clip`, devices) with their enums and properties, so that the script's LOM calls are right too.

**Validating a script**

31. As a script author, I want to validate a script folder against a target Live build, so that problems are found before I load it in Live.
32. As a script author, I want the validator to check that `create_instance` exists, so that Live can load the script at all.
33. As a script author, I want every import checked against the target build's index, so that a wrong module or class name is caught.
34. As a script author, I want overridden framework methods checked against their signatures, so that a wrong argument list is caught.
35. As a script author, I want Specification fields and component-map keys checked against the build, so that a v3 script uses only real options.
36. As a script author, I want a warning when components are built outside `component_guard`, so that half-initialised objects are avoided.
37. As a script author, I want a warning when `disconnect` doesn't call its base, so that listeners and LEDs are cleaned up.
38. As a script author, I want a folder name with spaces flagged, so that the script shows up in Live's list.
39. As a script author, I want each finding with file, line, what is wrong and how to fix it, so that Claude can fix it directly.
40. As a script author, I want the validator never to crash on a broken script, so that a syntax error becomes a finding.

**Writing a script with the skill**

41. As a script author, I want the skill to trigger when I ask to write, change, port or debug a Remote Script, so that I don't have to call it by name.
42. As a script author, I want the skill to first collect my controller's facts (device controls, MIDI types, channels, numbers, value ranges, LED feedback), so that the script matches the hardware.
43. As a script author, I want the skill to use existing device facts when I have them (e.g. the UC4's documented controls), so that I don't repeat myself.
44. As a script author, I want the skill to recommend v3 for Live 12.4/13 and `_Framework` for the simplest scripts, and to say why, so that the choice is explicit.
45. As a script author, I want the skill to design the elements, components, layers and modes before writing code, so that the structure is reviewed first.
46. As a script author, I want every API name the skill writes to be `observed` in the target build, or marked unverified, so that nothing is invented.
47. As a script author, I want the skill to point to the Ableton reference script closest to my controller (e.g. `APC_mini` for a grid controller), so that it follows proven patterns.
48. As a script author, I want minimal v3 and `_Framework` starting points, so that every script starts from a known-good skeleton.
49. As a script author, I want the skill's references (lifecycle, v3 Specification and elements, components/layers/modes, skins and colours, MIDI mapping and feedback, pitfalls) written in plain words, so that Claude understands the framework, not just its names.
50. As a script author, I want the skill to validate the script before handing it over, so that the first load in Live has the best chance.
51. As a script author, I want the skill to link the script into my User Library with one step, so that installing is easy and edits take effect after a reload.
52. As a script author, I want the skill to tell me exactly what to do in Live (restart or reselect the control surface, which slot, input/output ports), so that I know my part.
53. As a script author, I want the skill to read `Log.txt` for my Live build after I load the script, and to explain any traceback, so that load errors are fixed quickly.
54. As a script author, I want a short behaviour checklist for my device (press this, expect that), so that I can confirm the script works.
55. As a script author, I want the skill to work without the MCP server, through its own lookup and validate scripts, so that it works in any agent.

**MCP server**

56. As a script author, I want the lookups and the validator as MCP tools, so that Claude calls them directly with structured results.
57. As a script author, I want the MCP server to start with `uvx` and no further setup, so that installing it is one line.
58. As a script author, I want the MCP tools and the skill's scripts to give the same answers, so that it doesn't matter which one Claude uses.
59. As a script author, I want the MCP server to load the index once and answer quickly, so that lookups don't slow the conversation.

**Packaging and publishing**

60. As a Claude Code user, I want one plugin that installs the skill and the MCP server, so that setup is a single step.
61. As a user of another agent (Codex, Cursor, Gemini CLI), I want to install the skill with `npx skills add` and add the MCP server to my config, so that I'm not tied to Claude Code.
62. As a visitor, I want the README to say plainly that this is unofficial and not affiliated with Ableton, and to credit Julien Bayle / Structure Void, so that I know where it stands.
63. As a visitor, I want to find the repo by searching "ableton mcp", "remote script" or "agent skill", so that it is discoverable.
64. As a maintainer, I want everything published to be our own code and text under MIT, so that it can be shared freely.
65. As a maintainer, I want indexing a new Live build to be one command, so that new releases are covered quickly.

**Milestone 1**

66. As a UC4 owner, I want a v3 Remote Script for my Faderfox UC4 written with the skill, so that I can use it with Live 12.4.
67. As an APC mini mk1 owner, I want a `_Framework` Remote Script written with the skill and compared with Ableton's `APC_mini`, so that the fallback path is proven.

## Implementation Decisions

- **Three parts in one repo, built in order: API index → skill → MCP server** (Decisions 4, 21).
  The plugin manifest wraps the skill and the MCP server (Decision 24).
- **Modules:**
  - **Extractor.** Reads the `.pyc` files of one installed Live build: the framework packages,
    every controller script, and the Push 3 helper's packages including `live_model`. Code
    objects are loaded with Python 3.11 (`marshal`), never decompiled. It collects modules,
    classes with bases, methods with argument names and recoverable literal defaults, class
    attributes and docstrings, and it records unreadable files as errors.
  - **Structure Void importer.** Reads a locally downloaded copy of the site's search index into
    `documented` facts for Live 9–12, with the page URL for each module.
  - **Index store.** One JSON document per Live build, plus one for the Structure Void import.
    A versioned schema; each fact carries its Live build, source and confidence. Stored outside
    git; JSON is the source of truth (Decision 22).
  - **Query core.** The single interface the skill scripts and the MCP tools both use:
    - search
    - get a class with its members, inherited ones resolved along the bases
    - outline a reference script
    - diff two builds
    - list the indexed builds

    It also answers "index missing" and "not found in build X" explicitly.
  - **Validator.** A static check of a script folder against one build's index, using Python's
    own parser. Checks: `create_instance` exists; imports resolve; overridden methods match their
    signatures; Specification fields and component-map keys exist; components are built inside
    `component_guard`; `disconnect` calls its base; the folder name has no spaces. Each finding
    has a file, a line, a rule, a message and a fix.
  - **Skill** (open Agent Skills format):
    - an entry file with the trigger and the workflow
    - reference pages in our own words, each read only when needed
    - small lookup, validate, install and log scripts that call the query core and validator
    - minimal v3 and `_Framework` templates
  - **MCP server.** Python, official MCP SDK (FastMCP), run with `uvx` over stdio
    (Decision 17). Version 1 tools: `search_api`, `get_class`, `outline_reference_script`,
    `diff_builds`, `validate_script`, `list_builds`; all are thin adapters over the query core and
    the validator.
  - **CLI.** `build-index` (Decision 26) and the lookup and validate commands the skill scripts
    use. Builds the index only when the user runs it.
- **Fact confidence** (Decision 6): the extractor writes `observed`; the Structure Void importer
  writes `documented`; `tested` is set when a script using the fact loaded in that build
  (recorded by hand at first).
- **LOM** (Decision 23): from `live_model/Live` (`observed`, marked as a proxy model) and
  Structure Void's runtime pages (`documented`); no runtime probe in this phase.
- **Builds:** 12.4.16 and 13.0b25 now; new ones as they are installed (Decision 14). The 13.0b25
  index stays local (Decision 15).
- **Generated scripts:** v3 first, `_Framework` as the fallback; target Live 12.4 and 13
  (Decisions 7, 16).
- **Vocabulary:** the Remote Script framework's words; Element = physical, Control = logical slot;
  a hardware name is a device control (Decision 11, GLOSSARY).
- **Licence:** MIT for code and skill text; nothing from CC BY-NC-SA material in published files;
  the README credits Structure Void and states that the project is unofficial (Decisions 3, 20).
- **Repo:** `ableton-remote-script-mcp`, with the description and topics from Decision 27.

## Testing Decisions

- **Good tests check behaviour at a seam,** with the inputs a user would give and the outputs they
  would see, never internal helpers. A refactor that keeps behaviour must keep the tests green.
- **Seam A: `build-index`** (installed Live → JSON index, confirmed by the user 2026-11-15).
  - **Fixture:** a small fake framework that we write ourselves and compile to `.pyc` with
    Python 3.11, laid out like a Live bundle. It contains classes with bases, methods with
    defaults, class attributes, a docstring, a fake `live_model` and one corrupt file.
  - **Assertions:** the JSON's modules, classes, bases, members, argument names, defaults, build
    label, source and the error for the corrupt file. Ableton's real files never go into the repo.
  - **Local-only check against the installed 12.4.16,** skipped when the app is absent. It asserts
    known facts, e.g. `ControlSurfaceSpecification` has `session_ring_selection_linking_type`, and
    `APC_mini` is a `_Framework` script.
- **Seam B: the query core and the validator over an index** (confirmed by the user 2026-11-15).
  - **Fixture:** a small hand-written JSON index (two builds, inheritance across three levels, one
    member that differs between the builds, a Structure Void entry).
  - **Assertions:** search ranking basics, inherited members with their origin, the diff,
    "index missing", "not found in build X", and the confidence labels.
  - **Validator:** good and bad sample scripts that we write ourselves, one per rule, plus a clean
    v3 and a clean `_Framework` sample with no findings.
- **Adapters:** one or two smoke tests each. The MCP tools go through the MCP SDK's in-memory
  client; the skill scripts are run as commands. They show that the adapter calls seam B and passes
  its answer through.
- **The skill text** is tested by Milestone 1 (Decision 25): the UC4 v3 script and the APC mini mk1
  `_Framework` script. Each loads in 12.4.16 with no traceback in `Log.txt` (the user loads it, the
  agent reads the log), passes its behaviour checklist, and uses only names `observed` in the
  12.4.16 index.
- **Prior art:** none in this repo yet (no code). pytest, with uv as the runner. The UC4 Editor's
  fixture-pair rule is the model for the local-only checks: a fact is asserted only when it was seen
  in a named build.

## Decisions

1. Plans and STATUS live in this repo, `docs/feature-plans/`, following the UC4 Editor's layout
   (user, 2026-11-15).
2. Grilling happens in this session; a fresh session in the repo named by Q2 then builds the first
   step (user, 2026-11-15).
3. **A public, unofficial tool.** Personal use first, for a short time only. It credits Julien
   Bayle / Structure Void and states that it is unofficial and not affiliated with Ableton
   (user, 2026-11-15, grilling Q1).
4. **Order: API index → skill → MCP server** (user, 2026-11-15, grilling Q3). The Structure Void
   reference pages are a source alongside our own index (see Q17).
5. **The API index is extracted from the installed Live builds.** The bundles hold only `.pyc`, so
   the extractor reads their code objects with Python 3.11 (CPython 3.11.12 via `uv`, installed
   2026-11-15; proven on 12.4.16). The gluon clones are used only for reading function bodies
   (user, 2026-11-15, grilling Q4).
6. **Fact confidence `observed` / `tested` / `documented`**, as in `CLAUDE.md`. The skill names
   the Live build and confidence of each API claim it relies on (user, 2026-11-15, grilling Q8).
7. **Generated scripts use v3 first**, with `_Framework` as the fallback for the simplest scripts
   (user, 2026-11-15, grilling Q9).
8. **First test controller: the Faderfox UC4.** Its facts come from Faderfox's manual, not from
   Ableton. Second test device: the user's Akai APC mini (8×8 grid, faders, buttons; one
   potentiometer is defective and makes the volume jump), which has an Ableton reference script
   (user, 2026-11-15, grilling Q11; model in Q19).
9. **Testing:** static checks by the validator first; then a load test the user runs while the
   agent reads `Log.txt`; then a short behaviour checklist. Mocks of `Live` only if static checks
   miss real bugs (user, 2026-11-15, grilling Q12).
10. **Independent of AbletonMCP**, and the skill doesn't mention it. Possible later use: automatic
    testing (user, 2026-11-15, grilling Q14).
11. **Vocabulary follows the Remote Script framework and Structure Void's glossary:** Element =
    physical, Control = a component's logical slot (user, 2026-11-15, grilling Q15).
12. **One planning session plus a fresh builder per step;** a reviewer session once there is code;
    an agent team only for parallel steps (user, 2026-11-15, grilling Q16).
13. **Goal and priority: better results from Claude when writing Remote Scripts,** using the
    content that already exists (installed Live, Structure Void, the gluon clones). It started as a
    side project to the user's real script builds. Improving or contributing to Julien Bayle's work
    comes later (user, 2026-11-15, grilling round 2).
14. **API index builds: 12.4.16 and 13.0b25;** new builds as they are installed (user, 2026-11-15,
    grilling Q5). **Coverage:** every framework module and every controller script of those builds,
    since the skill picks the relevant reference scripts. The Structure Void reference is used for
    all its versions (Live 9, 10, 11, 12) (user, 2026-11-15, grilling round 2).
15. **Live 13 beta data stays private** while Live 13 is in beta. When there are results, the user
    mails Julien Bayle, who is probably working on Live 13 too, and asks where PRs should go
    (user, 2026-11-15, grilling Q7).
16. **Generated scripts target Live 12.4 and 13;** older builds are out of the user's interest
    (user, 2026-11-15, grilling Q10).
17. **MCP stack: Python with the official MCP SDK** (FastMCP), `uv`, stdio (user, 2026-11-15,
    grilling Q13).
18. **Structure Void reference:** its `search_index.json` is ingested locally as a `documented`
    cross-check and never redistributed; the public tool links to his pages; the user contacts him
    (user, 2026-11-15, grilling Q17).
19. **The APC mini is an mk1**, so its answer key is Ableton's `_Framework` script `APC_mini`. That
    tests the fallback path; an mk2 (v3) may come later (user, 2026-11-15, grilling Q19).
20. **MIT licence** for our code and the skill text. The README says "unofficial, not affiliated
    with Ableton" and credits Structure Void (and Hanz Petrov's 2010 blog as history). Published
    files contain nothing derived from CC BY-NC-SA material (user, 2026-11-15, grilling Q20).

21. **One repo, usable by every agent:** the skill in the open Agent Skills format
    (`skills/<name>/SKILL.md`), the MCP server, and a thin Claude Code plugin manifest on top.
    `ableton-remote-script-skill` is retired (user, 2026-11-15, grilling Q2).
22. **Index format:** JSON per Live build, queried by `jq` and a small Python lookup script; the
    MCP server loads it into memory. SQLite + FTS5 only if ranked search turns out to be needed
    (user, 2026-11-15, grilling Q6).
23. **No runtime probe in the skill phase.** The LOM comes from `live_model/Live/*.pyc`
    (`observed`, proxy model), Structure Void's runtime pages (`documented`) and the `ableton-lom`
    skill. The probe comes back for Live 13 LOM work, or when Claude gets LOM calls wrong (user,
    2026-11-15, grilling Q18).
24. **Plugin version 1 holds only the skill and the MCP server** (user, 2026-11-15, grilling Q21).
25. **Milestone 1 = "working":** with the skill, Claude writes a v3 script for the UC4 and a
    `_Framework` script for the APC mini mk1. Each loads in 12.4.16 with no traceback in
    `Log.txt`, passes its behaviour checklist, and uses only API names `observed` in the 12.4.16
    index (user, 2026-11-15, grilling Q22).

26. **Each user builds the API index on their own machine** with an explicit command
    (`… build-index`, Python 3.11 through uv). When the index is missing, the tools answer "index
    missing, run …" instead of guessing (user, 2026-11-15, grilling Q24).

27. **Repo name stays `ableton-remote-script-mcp`.** On GitHub, Ableton tooling is found under
    "mcp" (248 repos vs 50 for "skill", 2026-11-15), and `remote-script` sets it apart from the
    runtime-control Ableton MCPs. The description and topics carry the skill: "MCP server and agent
    skill for writing Ableton Live MIDI Remote Scripts (unofficial)"; topics `ableton`,
    `ableton-live`, `midi-remote-scripts`, `control-surface`, `mcp`, `mcp-server`, `agent-skills`,
    `claude-skills`, `claude-code-plugin` (user, 2026-11-15, grilling Q23).

28. **The skill is drafted and refined with `/skill-creator`, and measured with evals** (step
    9a): with and without the skill, scored by invented API names and validator findings, plus a
    trigger check. Milestone 1 also requires fewer invented names with the skill than without
    (adds to Decision 25) (user, 2026-11-15, /to-tickets).
29. **The APC mini mk1 has defective faders** (values jump). Its checklist tests the button matrix
    and buttons. A fader is checked only for reaching its mapped target, never for smooth values,
    and jumps count as a hardware fault, not a script bug (user, 2026-11-15, /to-tickets).
30. **Breakdown approved:** 12 steps plus 9a, APC mini before the UC4, MCP server after the skill
    so its tools build on what the skill's lookups showed (user, 2026-11-15, /to-tickets).

31. **Changes Decision 12:** the building also happens in this session, with a `/compact` between
    steps instead of a fresh builder session; the plan, STATUS and the glossary are what is kept
    (user, 2026-11-15).

32. **One name everywhere: `ableton-remote-script-mcp`** for the repo, the distribution and the
    command; Python package `ableton_remote_script_mcp`. Subcommands carry the meaning
    (`build-index`, `lookup class`, later `validate`); with no subcommand it will start the MCP
    server over stdio (step 11), so an MCP config is just `uvx ableton-remote-script-mcp`. The
    agent's first choice, `ableton-remote-script`, read as if the tool were a Remote Script
    (user, 2026-11-15, step 1). Index location (agent, 2026-11-15, step 1): the index defaults to `~/.local/share/ableton-remote-script-mcp/index/`
    (`$XDG_DATA_HOME` honoured, `ABLETON_REMOTE_SCRIPT_INDEX` or `--index-dir` override), outside
    any repo; `/index/` is git-ignored as well. `build-index` without `--app` takes the newest
    installed release build. The project requires Python 3.11 exactly (`marshal` needs it).

33. **Index schema 2** (agent, 2026-11-15, step 2):
    - **Two roots:** the Remote Scripts folder and the Push 3 helper's Python. The helper ships
      its own, different copies of `ableton`, `Push2` and `_Generic`, so its facts are keyed
      `push3-helper:<name>` and never overwrite the Remote Scripts' facts.
    - **Package kinds:** `framework` (`_Framework`, `ableton`), a Remote Script (its `__init__`
      defines `create_instance`), or a library (`_Generic`, `pushbase`, `novation`, …).
    - **A package's framework generation** is the one its own module-level imports bind most
      often (newest wins a tie); with none, it is the generation of the libraries it imports.
      The counts are kept, so mixed packages stay visible (MackieControl imports `ableton.v2`
      twice and `ableton.v3` once). Taking the newest generation anywhere in the dependencies was
      rejected: it made `APC_mini` an `ableton.v2` script through one import inside a function of
      `_APC`.
    - **Members** are recorded for modules as well as classes, so `create_instance` and module
      constants are queryable. Values and defaults are source-like text with a `literal` flag;
      `…` marks an expression the extractor does not model.
    - **Proxy model:** everything under the helper's `live_model` carries `proxy_model: true`;
      classes under `live_model.Live` name the `Live` class they model (`proxy_of`).
    - An index with another schema answers "index missing … rebuild"; it is never read half-way.

## Open questions

None: grilling closed 2026-11-15 (user confirmed).

## Steps

Written by `/to-tickets` (2026-11-15, approved by the user). Each step is a vertical slice that works
on its own and fits one fresh builder session. One builder at a time works the frontier in this order:
1 → 2 → 3 → 5 → 7 → 9 → 9a → 8 → 10 → 4 → 6 → 11 → 12. Milestone 1 is complete after step 10.
Every step's checks include `uv run pytest` passing.

1. **Tracer bullet: index one build, look up one class**
   - **Blocked by:** none
   - **Delivers:**
     - **Repo setup:** a Python project run with uv, pytest, and a git-ignored index location.
     - **`build-index`:** finds the installed Live 12.4.16 and records its framework modules and
       classes with bases as a JSON index, with the Live build and source on every fact.
     - **`lookup class <name>`:** answers with the Live build and `observed`, or with "index
       missing, run …".
   - **Checks:**
     - **Seam A test:** a fake framework compiled to `.pyc` with Python 3.11, laid out like a Live
       bundle.
     - **Local-only check:** in the real 12.4.16, `ControlSurfaceSpecification` exists and is
       found by `lookup`.
   - **Demo:** `build-index`, then `lookup class ControlSurfaceSpecification`.
   - **Built 2026-11-15.** 12.4.16: 283 framework modules (`_Framework`, `ableton`), 731 classes,
     0 unreadable files, all bases resolved through each module's imports. Classes are found by
     simulating the bytecode from `LOAD_BUILD_CLASS` to its `CALL`, including `Generic[T]` bases
     and `metaclass=` keywords. A base expression that isn't modelled keeps the class, flagged
     `bases_parsed: false`. A resolved base is the name as imported, which can be a re-export
     (`ableton.v3.control_surface.NotifyingControlElement`); following re-exports to the defining
     module is step 3. Classes defined inside functions are not recorded.
2. **Full extraction**
   - **Blocked by:** 1
   - **Delivers:**
     - methods with argument names and recoverable defaults, class attributes, and docstrings
     - every controller script and the Push 3 helper's packages, with `live_model` marked as a
       proxy model
     - unreadable files recorded as errors, and `list builds`
   - **Checks:**
     - **Seam A:** the fake framework gains defaults, attributes, a docstring, `live_model` and
       one corrupt file.
     - **Local-only:** `ControlSurfaceSpecification` has `session_ring_selection_linking_type`;
       `APC_mini` is found as a `_Framework` script and `APC_mini_mk2` as a v3 script.
   - **Built 2026-11-15.** 12.4.16: 154 packages, 139 Remote Scripts (in the Remote Scripts
     folder 75 `_Framework`, 38 `ableton.v2`, 25 `ableton.v3`; plus the helper's `Push2`), 1797 modules (1376 Remote Scripts
     + 421 Push 3 helper), 4055 classes, 0 unreadable files; members: 18244 methods, 1704
     properties, 179 static and class methods, 10169 attributes; 3435 defaults, none
     unmodelled. About 12 MB, built in about 3 s. Module and class bodies are read by one symbolic
     stack simulation (Decision 33). Docstrings: Live's `.pyc` files carry almost none (11 class
     docstrings in 12.4.16), so the index has what exists. Known limits:
     - 34 attribute values are `…` (comprehensions and similar), and 5 classes have unparsed bases
       (e.g. `Push2.push2_model.Root`).
     - 31 classes have a base that can't be resolved, mostly names that come from a star import
       (`MackieControlComponent`). Following star imports and re-exports is step 3's job.
3. **Inherited members and search**
   - **Blocked by:** 2
   - **Delivers:**
     - a class with all its members, resolved along the bases, each showing the class it comes
       from
     - search by name or words, and "not found in build X"
   - **Checks:** Seam B tests against a hand-written index with three levels of inheritance.
4. **Second build and diff**
   - **Blocked by:** 2
   - **Delivers:** the 13.0b25 index (local only, Decision 15) and `diff` between two builds:
     added, removed and changed members.
   - **Checks:** Seam B test with a member that differs between two builds; local-only: the diff
     12.4.16 → 13.0b25 lists the added and removed modules.
5. **Reference script outline**
   - **Blocked by:** 2
   - **Delivers:** for one of Ableton's own scripts: its classes, the Specification fields it sets,
     its component map and its elements, without function bodies.
   - **Checks:** Seam B tests; local-only: outlines of `APC_mini` (`_Framework`) and `APC_mini_mk2`
     (v3).
6. **Structure Void as a cross-check**
   - **Blocked by:** 3
   - **Delivers:** imports a locally downloaded copy of the site's search index for Live 9–12 as
     `documented` facts with page links; lookups show where it disagrees with our index.
   - **Checks:** Seam B tests with a small extract we write ourselves (not his text);
     nothing from the import is committed.
7. **Validator: basic checks**
   - **Blocked by:** 2
   - **Delivers:** `validate <folder> --build <build>` with findings (file, line, rule, message,
     fix) for:
     - a missing `create_instance`
     - imports that don't resolve in the build
     - folder names with spaces
     - syntax errors (as findings, never a crash)
   - **Checks:** our own good and bad sample scripts, one per rule; a clean `_Framework` sample
     gives no findings.
8. **Validator: framework checks**
   - **Blocked by:** 7
   - **Delivers:** checks for:
     - signatures of overridden framework methods
     - Specification fields and component-map keys
     - components built outside `component_guard`
     - `disconnect` not calling its base
   - **Checks:** a bad sample for each rule; a clean v3 sample gives no findings.
9. **Skill v1 and the APC mini mk1 script (Milestone 1, part 1)**
   - **Blocked by:** 3, 5, 7
   - **Delivers:** the skill, drafted with `/skill-creator`, in the open Agent Skills format:
     - the workflow, the `_Framework` template and the references this script needs
     - the lookup, validate, install and log scripts
   - **Demo:** Claude writes an APC mini mk1 script with the skill.
   - **Checks:**
     - it validates clean against 12.4.16
     - the user loads it in Live and `Log.txt` shows no traceback
     - the behaviour checklist passes, covering the button matrix and buttons (Decision 29)
     - every API name it uses is `observed`
     - it is compared with Ableton's `APC_mini`
9a. **Skill evals**
   - **Blocked by:** 9
   - **Delivers:** with `/skill-creator`'s eval workflow:
     - a small set of tasks (APC mini mk1 grid, a UC4 mixer, porting a v2 script to v3), each run
       with and without the skill, several times
     - scored automatically: invented API names (names not in the 12.4.16 index) and validator
       findings per script
     - a trigger check: the skill fires for Remote Script prompts and stays quiet for unrelated
       ones; the description is tuned until it does
   - **Checks:** a report with and without the skill; fewer invented names with the skill.
     Re-run after step 10.
10. **v3 references and the UC4 script (Milestone 1, part 2)**
    - **Blocked by:** 8, 9a
    - **Delivers:** the v3 template and references (Specification and elements,
      components/layers/modes, skins and colours), refined with `/skill-creator`.
    - **Demo:** Claude writes a v3 script for the UC4 from the UC4 Editor's device facts.
    - **Checks:** the same as step 9 on the UC4; the 9a evals re-run and show the v3 references
      help. Milestone 1 is complete (Decision 28).
11. **MCP server v1**
    - **Blocked by:** 4, 6, 10
    - **Delivers:** the tools `search_api`, `get_class`, `outline_reference_script`, `diff_builds`,
      `validate_script` and `list_builds` over the same core, shaped by what the skill's lookups
      showed in steps 9–10, and startable with `uvx`.
    - **Checks:** in-memory MCP client smoke tests; a tool and the matching skill script give the
      same answer.
12. **Plugin and publishing**
    - **Blocked by:** 11
    - **Delivers:**
      - a Claude Code plugin manifest (skill and MCP server), the MIT licence, and a README that
        says unofficial and not affiliated with Ableton and credits Structure Void
      - install instructions for other agents
    - **Checks:**
      - installs in Claude Code
      - `npx skills add` installs the skill
      - no Ableton material or Live 13 data in the published files
      - the user sets the GitHub description and topics (Decision 27)

## Out of scope

- Controlling Live at runtime (AbletonMCP and similar servers do that).
- Max for Live devices and the Extensions SDK (other skills cover them).
- Publishing Ableton's code, decompiled bodies, extracted API data or Live 13 beta facts.
- A runtime probe of the `Live` module (later: Live 13 LOM work or observed LOM errors, Decision 23).
- SQLite or other search engines (only if ranked search proves necessary, Decision 22).
- Plugin commands, subagents and hooks (Decision 24).
- Script generation from a form or wizard (`scaffold_script`), Live builds before 12.4, Windows paths.

## Further Notes

- Sources and numbers: [research/2026-11-14-sources-investigation.md](research/2026-11-14-sources-investigation.md).
- The user plans to mail Julien Bayle once there are results, and to ask where PRs should go
  (Decision 15).
- Possible later test devices: an APC mini mk2 (v3 answer key), a Push 3 (Ableton's most complex
  v3 script; its scripts already ship with Live).
