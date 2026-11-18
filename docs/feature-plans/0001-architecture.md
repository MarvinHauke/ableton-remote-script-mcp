# 0001 — Architecture: API index, skill, MCP server

_Stage: in work — steps 1–3, 5, 5a, 7 and 9 built 2026-11-15, 9a (baseline round) and 8 2026-11-16. Frontier: Milestone 1 complete 2026-11-18 (step 10's 9a round run); next step 4 (order 4 → 6 → 11; the grilling session on the MCP design ideas comes before step 11)._
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
14. As a script author, I want the index to contain names and signatures only, never function bodies, so that it never holds Ableton's implementation code. _Amended 2026-11-15 (Decision 35): the statement summaries the outline needs are a separate file per build, which can be left out or deleted; the API index itself stays names and signatures._
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

34. **Names resolve at query time; index schema 3** (agent, 2026-11-15, step 3):
    - **The index stays a record of what each module says;** the query core resolves names to
      the class that defines them when it answers. Resolution follows imports (re-exports),
      module-level aliases (`Foo = Bar`), star imports (the last one wins, `_names` excluded)
      and, for `Class.Name`, the class body and then its MRO, as Python looks up a class
      attribute. It stays inside one root. Resolving at build time was rejected: Seam B tests
      could then not exercise it over a hand-written index, and the whole 12.4.16 index
      resolves in about 0.1 s anyway.
    - **Schema 3** adds each module's `star_imports`, in order; nothing else changes.
    - **Two rules from Live's own code:** a base named like the class it defines
      (`class DrumGroupComponent(…, DrumGroupComponent, …)` in `pushbase`) is the imported
      binding, since the class body runs before the name is rebound; a base in a nested class
      is looked up in the enclosing class body first (`Push2.skin_default.Colors`).
    - **MRO:** C3, with `builtins.object` for a class written with no bases. A class whose bases
      admit no C3 order falls back to depth-first and says so. Names outside the index
      (builtins, `typing`, `enum`, the C++ `Live` module) are `external`; a `Live` class names
      its proxy model when there is one. An unresolved or unparsed base along the MRO marks the
      class `complete: false`: inherited members may be missing.
    - **Search** ranks exact name, qualified-name suffix, name prefix, name substring, all words
      in the name, then all words in name, module and docstring; ties go to classes before
      modules before members, the framework (newest generation first) before libraries before
      Remote Scripts, and the Remote Scripts folder before the Push 3 helper.

35. **Statement summaries of function bodies; index schema 4** (agent, 2026-11-15, step 5):
    - **Why:** a script's elements (`Elements.__init__` calling `self.add_button(…)`), its v3
      mappings (`create_mappings`) and a `_Framework` script's components and layers are all
      made inside functions, which the index did not record. The outline needs them.
    - **What the extractor records:** each function's statement summary (GLOSSARY): its calls
      whose result is not used inside another expression, with where the result is stored (a
      name, `self.x`, `m['k']` or `return`), the calls made inside its comprehensions and
      nested functions (marked `inside`), and the values it stores into attributes and
      subscripts. Arguments are source-like text. It is a summary read from the bytecode, not a
      decompilation; the outline shows no function bodies. 12.4.16: 61967 statements; the
      build takes about 5 s instead of 3 s (once per Live build).
    - **A separate file, so the API index stays names and signatures** (user, 2026-11-15,
      amends user story 14): `build-index` writes the statement summaries to
      `live-<build>.statements.json` next to the API index (12.4.16: 12 MB index, 11 MB
      statements). Only `outline` reads them; `lookup class`, `search` and everything after
      never see them. `build-index --no-statements` leaves them out (a rebuild then deletes the
      old file), and deleting the file is enough to drop them: `outline` then answers "no
      statement summaries … rebuild", and every other command keeps working. The statements
      file names the index it belongs to (`index_created`), so a stale one is never used.
      Schema 4 for both files.
    - **Conditions** (user, 2026-11-15: keep the summary, but mark conditions before building on
      it): each statement lists what it runs under (`under`, outermost first): `if <test>` (an
      `else` is the negated test, `a or b` stays one test), `for … in <iterable>`, `on an
      exception` and `except <type>`, read from the bytecode's jumps and exception table.
      The outline decides a test of the form `if self.X` / `if not self.X` from a literal class
      attribute along the outlined class's MRO, including the call site's conditions for a
      method such as `self._transport = self._create_transport()`: `runs` is false ("not built
      for this script", with the attribute that decides it), true, or null when it can't tell
      ("only if …"). APC_mini: `APC_Key_25` builds its Play and Record buttons and its
      Transport only `if self.HAS_TRANSPORT:`, and APC_mini sets it to False. 12.4.16: 20064
      statements run under a condition; over all outlines, 7 entries are not built, 90 are
      decided as built, 210 stay conditional.
    - **Roles from the MRO:** a class is a control surface, Specification, elements, component,
      element or layer when that framework class (`ControlSurface`, `ControlSurfaceSpecification`,
      `ElementsBase`, `ControlSurfaceComponent` / `Component`, `ControlElement`, `Layer`) is on
      its MRO. Names in statements resolve where they are written, as bases do (Decision 34),
      plus module-level functions and `x = partial(f, …)` aliases.
    - **What the outline counts:** the code of the script's package and of every non-framework
      class along its classes' MROs, overridden methods included (an override usually calls
      `super()`); APC_mini's elements are built in `APC_Key_25`. An element is a call to an
      element class, a v3 `self.add_*` call in an Elements class (arguments named by the
      framework method's parameters), or a call to a factory (a function or method that returns
      an element, up to three levels deep). A factory's own `return ButtonElement(…)` is not
      listed. The v3 component map joins the framework's defaults (`ComponentMap`), the
      Specification's `component_map` and the names a control surface adds while it sets up
      (`self.component_map['Background'] = …`); names the mappings use that are in none of them
      are listed as unknown.
    - **Known limits:** scripts configured by constant tables (`_Generic`'s `GenericScript`,
      e.g. Axiom and the MPK family) or that send raw MIDI (RemoteSL, MackieControl) show no
      elements; a Specification built by a function (MiniLab_37's
      `create_minilab_specification`) is not found, so outline the library (`MiniLab_3`).
      12.4.16: 2324 elements, 1067 components and 1001 layers over all 151 non-framework
      packages, in 0.7 s; 60 Remote Scripts show no elements.

36. **A documentation site, written by a docs agent and checked by a reviewer** (user,
    2026-11-15, after the agent's assessment of cmdAbl's setup):
    - **Site:** MkDocs with the Material theme, published to GitHub Pages by a workflow on
      `main`, as cmdAbl does. Pages are split by audience: users (install, how the toolchain
      works, writing a Remote Script with the skill, the MCP setup), contributors (development,
      architecture, tests), and maintainer pages that stay in the repo, outside the site. The
      plans in `docs/feature-plans/` are not part of the site.
    - **Nothing from Ableton in published pages** (the rule of CLAUDE.md and Decision 15, which
      stands until the user has asked the people responsible at Ableton): naming API classes in
      our own words is fine; command output, outlines and examples come from our hand-written
      fixtures (`tests/hand_index.py`, the fake scripts), never from a real index; no Live 13
      beta facts; Structure Void is linked and credited, not copied.
    - **The CLI reference is generated** from the command's own argument parser by a script with
      a `--check` mode, so a stale page fails the docs check. A local `scripts/docs-check.sh`
      runs that check and `mkdocs build --strict`; CI runs the same.
    - **Two agent definitions, on demand:** `.claude/agents/docs.md` writes pages from a brief and
      from what the code and plans state, never invented behaviour; `.claude/agents/reviewer.md`
      reviews changes read-only (contracts, the Ableton-material rule, plans and STATUS in sync)
      and reports must-fix / consider. Docs pages are committed only after the reviewer passes
      them. They run as subagents or as on-demand peer sessions; cmdAbl's `scripts/agents.sh`
      team launcher is not adopted while one builder works the steps (Decision 31). These are
      development tools for this repo, not part of the plugin (Decision 24). The rest of
      `.claude/` stays untracked.
    - **When:** the skeleton now, as step 5a; the user guides with step 12, once the skill and
      the MCP server exist, so they don't churn.
    - **Changed 2026-11-15 (user): build with Zensical instead of MkDocs.** Material for MkDocs
      is in critical maintenance only (until 2027-05-05), MkDocs 2.0 is incompatible with it, and
      its team develops Zensical as the successor. Zensical reads `mkdocs.yml` and Material's
      settings; its gap is plugins, which this site does not use. Zensical is young (0.1.1,
      Beta, 2026-11-10), so it is pinned to an exact version as a uv dev dependency, and the
      `mkdocs.yml` stays plugin-free so `mkdocs-material` 9.7 builds it unchanged. If step 5a
      finds no Zensical equivalent of `mkdocs build --strict` (fail on broken links), the site
      builds with `mkdocs-material` 9.7 for now and switches later.
    - **Found 2026-11-15 (step 5a):** `zensical build --strict` fails on a missing page and on a
      missing anchor, so the site builds with Zensical; the fallback is not needed. The same
      `mkdocs.yml` builds with `mkdocs-material` 9.7.7 `--strict` too. The `--index-dir` default
      is resolved when the command runs, not in the parser, so `--help` and the generated
      reference show no home path.

37. **Imports are checked against the Python Live ships; index schema 5** (agent, 2026-11-15,
    step 7):
    - **Why:** Live 12.4.16 ships its own Python (`Contents/App-Resources/Python`): a standard
      library in `lib`, with some modules left out (`ctypes`), and extra packages under
      `site-packages/<distribution>/` (`future`, `past`, `decorator`, `raven`). Checking
      imports against the standard library of the Python the tool runs with would accept
      modules Live lacks and reject `future`, which older scripts import. A trial run over the
      decompiled 12.0-era scripts in `reference/` (local only) showed both.
    - **Schema 5** adds `python`: the top-level module names of Live's Python, each with the
      folder it is in (`observed`). Nothing else changes; older indexes answer "rebuild".
    - **An import resolves** to the script's own modules, the Remote Scripts folder, or Live's
      Python. Python's standard library modules with no file in Live are split by the Python the
      tool runs with: compiled into it (`sys`, `itertools`) is accepted; a C extension module
      (`math` in some builds) is listed as *not checked*; a pure-Python module (`ctypes`) is a
      finding, since Live would need its file. `Live` and `MidiRemoteScript` come from Live's
      C++ code and are listed as not checked. An import inside a `try` that handles `ImportError`
      is optional. Below a top-level module of Live's Python, names are not checked. An index of a
      bundle with no Python folder records `python.modules` as null; then the whole standard
      library is listed as not checked rather than reported.
    - **Findings** carry a `severity` (`error` for every basic check; step 8's warnings use
      `warning`). `validate` exits 0 with no findings, 1 with findings, 2 when the folder is
      missing and 3 when the index is.

38. **The skill `ableton-remote-scripts`; `install` and `log` are commands** (agent, 2026-11-15,
    step 9):
    - **Drafted with `/skill-creator`** (Decision 28), following its writing guide (description
      that triggers, progressive disclosure into references, bundled scripts); its eval loop is
      step 9a. The draft was then run once: a fresh agent wrote the APC mini script with only the
      skill, and its feedback went into the skill (sharing a button between a Shift combo and a
      plain binding, full dotted names for lookups, a help-text bug).
    - **Name:** `skills/ableton-remote-scripts/` (Decision 21's layout). The repo's name
      `ableton-remote-script-mcp` names the tools; the skill is named for what it writes.
    - **Contents of v1:** `SKILL.md` (trigger, fact confidence, a nine-step workflow, what done
      means), `references/framework-script.md` (a `_Framework` script: elements, components, LED
      feedback, the rules that keep it loading, every name looked up in 12.4.16),
      `references/loading-and-logs.md` (what to tell the user, how to read the log, common
      tracebacks), `assets/framework_template/` and four scripts. The v3 pages come with step 10.
    - **The scripts are thin:** `lookup.sh`, `validate.sh`, `install.sh` and `log.sh` call the
      `ableton-remote-script-mcp` command (or `$ABLETON_REMOTE_SCRIPT_MCP`) and say how to install
      it when it is missing. The work is in the command, so the MCP server (step 11) can reuse it
      and the tests run it at a seam.
    - **`install <folder>`** validates first and copies only on no findings (`--no-validate`
      skips it); it copies the source without `__pycache__`, `.pyc` and hidden files into
      `<User Library>/Remote Scripts/<folder>`, and replaces a copy only with `--replace` and only
      when that copy is a script folder (`__init__.py`) and not a symbolic link; the folder is
      resolved first (`install .`), its name must be a Python name, and the new copy is written
      beside the old one and swapped in. Exit 0 installed, 1 findings, 2 refused or missing,
      3 no index. Live stays the user's to operate.
    - **`log`** reads the `Log.txt` of a named build or the one written last, from the last
      `Started: Live` record. Live writes a traceback in fragments (`RemoteScriptError:` records,
      an empty line after a fragment that ended a line, `Last message repeated N time(s)`);
      `log` joins them, splits back-to-back tracebacks at their header (not inside one chained
      exception), and with `--script` keeps the tracebacks through that folder (or, for a bad
      folder name, Live's `import <folder>`) and the messages that script logged. Exit 0 no
      traceback, 1 tracebacks, 2 no log. Found in the user's
      own logs (12.2.1): a hyphenated folder (`import ableton-live-midi-remote-scripts`, a
      SyntaxError) and a `SessionComponent` built outside `component_guard`
      (`DependencyError … register_component`).
    - **The framework names a message by the control surface class** (`(%s)` of
      `self.__class__.__name__` in `_Framework`'s `log_message`, `documented` from the
      decompiled 12.0 scripts): so the skill names the class like the folder, and `log --script`
      matches the folder name.
    - **`folder-name` also rejects a folder that is not a Python name** (Live imports the script
      by it), with a suggested name; the user's log above shows the failure.
    - **Milestone 1 pages:** `docs/feature-plans/milestone-1/` holds each test device's facts,
      its behaviour checklist and the results; the scripts written in the demos live in
      `examples/` (our own code).

39. **A with/without benchmark comes last, as step 13** (user, 2026-11-15, step 9). Once every
    other step is built, the same Remote Script tasks run with the skill and the MCP server and
    without them. The scores, time and tokens go in a short README table that links to the full
    results. The load test in Live stays the user's step. Published results hold only our own
    tasks and scores, on 12.4 builds: no Ableton material, no Live 13 beta facts.
40. **The APC mini load test: what goes into the skill** (user and agent, 2026-11-15, step 9).
    The user ran the checklist in Live 12.4.16; three items were added during it (stop LEDs,
    Stop All, Shift + an unbuilt button does nothing). A finding goes into the skill only when it
    happens every time and the framework source or a traceback explains it (user). Intermittent
    faults that Ableton's `APC_mini` shows on the same controller too (late relights, doubled or
    lost Shift messages) are recorded in the milestone page as unconfirmed, because the controller or its
    Shift button may be worn (user). Plain `reset()` is kept in `disconnect`: a forced send was
    not needed once the test was run by choosing None (user's retest). Shift's fader and track
    modes are not part of step 9 (agent).
41. **Shift scripts build on `OptimizedControlSurface`; combos come from button lists; `log`
    shows framework-only tracebacks** (agent, 2026-11-16, step 9; the user ran the tests).
    Measured with ReceiveMIDI beside the log: on the plain `ControlSurface` each Shift press made
    the script resend most LEDs and the controller lost presses; on the optimized surface, as
    Ableton's `APC_mini`, every press got through. The scene combos had been built with
    `matrix.get_button()`, which returns `None` until a component holds the matrix, so Stop All
    and item 12 had passed by accident; the optimized surface turned that into a traceback with
    only `_Framework` frames, which `log --script` did not show. Now `log --script` lists such
    tracebacks as framework-only and exits 1 for them. This answers the open question of
    Decision 40: the second controller is no longer needed for it.
42. **The skill evals' baseline round; invented names in v3 mappings go to step 8** (agent
    proposed, user agreed, 2026-11-16, step 9a). The three cases ran three times with and without
    the skill in `claude plugin eval`'s sandbox, which hides this repo but not the installed Live.
    With the skill, all behaviour graders passed (without: 78%, 93% and 100%), and the
    `_Framework` case took less time and money. Both arms had no validator findings and no
    unknown names, so the check "fewer invented names" is not met. Without the skill, Claude
    reads Live's `.pyc` files itself. And the name check reads only attribute names and
    constructor keywords, which leaves most of a v3 script (names as text in the mappings)
    unchecked. So step 8's checks of the Specification and the component map also check the
    control names in a mappings function, and 9a is re-run after step 8 and after step 10. The
    trigger check waits until the usage limit allows it (the first round hit the user's 5-hour
    limit). Scores: [milestone-1/skill-evals.md](milestone-1/skill-evals.md).
43. **Step 8's rules, severities and real-world check** (agent proposed, user agreed,
    2026-11-16, step 8). Findings have three severities: `error` (the build's index proves it
    wrong), `warning` (likely wrong, but the framework accepts it) and `not_checked` (the rule
    can't decide, listed with the reason). The rules:
    - **Mapping keys** (`error`): each key of a component-map name must be a member `<key>`
      or a setter `set_<key>` of that component's class through its MRO, or `enable`. The
      class comes from the framework's default component map, the Specification's
      `component_map` and the script's own setup. Modes sections are checked the same way for
      each mode, and their own keys against `ModesComponent`. A component the rule can't
      resolve is `not_checked`.
    - **Element names** (`error`): a name on the right of a mapping must be one the Elements
      class builds (snake case of `name=` or `base_name=`, with `_raw` and `[i]`); names built
      in a loop or by computation are `not_checked`.
    - **Top-level names not in the component map** (`warning`) only when the section has no
      modes, because that's what a typo looks like.
    - **Specification fields** the base class doesn't have (`warning`).
    - **Overridden framework methods** that can't take the framework's arguments (`error`);
      renamed parameters and keyword style are not flagged.
    - **Elements or components built outside `component_guard`** in a ControlSurface
      subclass's `__init__`, following called methods one level deep (`error`); v3's `setup()`
      and an Elements class are exempt.
    - **`disconnect` not calling its base** (`warning`).
    
    `eval_names.py`'s name-only check doesn't become a validator rule; an attribute rule by
    class goes to STATUS. The clean v3 sample is hand-written in `tests/` over the hand-written
    index. In addition, a local-only check runs the rules over working v3 scripts in
    `reference/`: gluon's decompiled factory scripts and `hkdsun/MidiFighterV3` (Live 12; it has
    no licence and so stays local). Each `error` there is read: it is a false positive in our
    rules unless the script is older than the build. Most of gluon's scripts are decompiled from
    12.0-era bytecode, and only nine recent controllers from Live 12's Python 3.11 bytecode,
    some with partial bodies, so an error there may be a real change since 12.0 or a gap left
    by the decompiler. The glossary gains
    Eval case, Arm, Grader and Unknown name.
44. **How step 8's checks read a script, and what Decision 43 left open** (agent, 2026-11-16,
    step 8; for the user's review). The validator compiles the script's sources with Python 3.11,
    reads them with the extractor that reads Live's `.pyc` files, and lays the facts over a copy
    of the index in place of an indexed script of the same name. So the outline's reading of
    Specifications, component maps, mappings and elements works on the user's script unchanged.
    On another Python the framework checks are listed as `not_checked`; `eval_run.sh` therefore
    copies uv's Python 3.11 into the sandbox instead of using Homebrew's 3.12. Four points
    Decision 43 left open, decided from the reference run:
    - A modes component gets a `<mode>_button` control for each mode; such keys are known.
    - A class with its own `__getattr__` answers names by pattern. A key is `not_checked` when
      `set_<key>` starts with a prefix its `__getattr__` tests (`name.startswith(...)`), or when
      no prefix can be read. This leaves v3's `MixerComponent` keys unchecked.
    - A mode naming a component that is neither in the component map nor a modes section, or a
      mode without `component=`, is an `error` under `unknown-component`. The framework raises a
      KeyError while it sets up. Decision 43's `warning` stays for a section with no modes.
    - `disconnect-base` stays quiet when the overridden `disconnect` has no statements (a `pass`).
45. **Structure Void's runtime pages come into the index now, as `documented`** (user
    decided, 2026-11-16, after step 8; agent proposed how). Decision 23 already named them as the
    `documented` source for the `Live` module. Four outside scripts checked after step 8
    (cmdAbl, Prism, the APC40 mkII step sequencer, Beatstep_Q) showed how thin the Push 3
    helper's model is: no listener methods, no `is_foldable`, no beat time class. The user chose
    this over a 9a re-run first, to save tokens.
    - `import-structure-void` fetches the Live 12 runtime pages (43 pages) once. The pages and the
      document read from them (`structure-void-live12.json`) stay in the index folder, since
      the pages are CC BY-NC-SA 4.0.
    - `lookup class` adds the members the proxy model lacks, and `search` finds them; each fact is
      `documented` and names its page.
    - `eval_names.py` counts them in a `documented` bucket. It also counts names a script's
      `setattr` builds from a literal start as its own.
    - The validator doesn't use them: no rule checks attribute names by class yet (STATUS).
    - The pages come from one unstated Live 12.x build. A runtime probe stays out, as Decision 23
      says.
46. **One 9a round after step 10, not one after step 8 as well** (agent proposed 2026-11-16; the
    user went ahead with step 10 without objecting, 2026-11-17; explicit confirmation asked
    2026-11-18; the user confirmed and asked to start the round, 2026-11-18). Decision 42 planned a re-run
    after step 8 and another after step 10. A round costs much of the user's usage limit, and the
    v3 cases (the UC4 mixer, the port to v3) need the v3 references of step 10 to show a
    difference. So one round runs after step 10, with step 8's checks and the v3 pages in place.
    Run 2026-11-18 (results in [milestone-1/skill-evals.md](milestone-1/skill-evals.md)). With the
    skill: 100% of the behaviour graders in all three cases, no validator findings, and faster and
    cheaper runs. Without it: no v3 script got the session box or the UC4's value feedback.
47. **How step 10's UC4 script is built** (agent, 2026-11-17, step 10).
    - **Target:** the UC4's factory setup SE17 (the user: "use a dump from the UC4 Editor, note
      which one"). The device facts come from the UC4 Editor's model of SE17 and its device
      page; the UC4 architect confirmed SE17 on the device is factory. To restore it, the user
      runs `rESc`; nothing is sent to the device.
    - **Every group at once:** the UC4 switches its encoder and green button groups itself, and
      each group sends other numbers, so the script maps all of them and needs no modes. Two
      controls sending the same message (the Track group's push buttons 3–4 and the Track green
      buttons 1–2) are one element.
    - **Framework components first,** two of our own where none fits: Monitor (In/Auto per
      track) and the selected scene's start button. The printed `Quant` and the Track group's
      encoders 7–8 are left out.
    - **The Global group's assignment is the script's choice:** which encoder or push button is
      which printed function is not known. It is listed in the milestone page and on the
      checklist.
    - **`log --script` also reads Python's `logging`.** v3 has no `log_message`; Ableton's v3
      scripts log with `logging.getLogger(__name__)`, which Live writes as
      `Python: <LEVEL>:<logger>:<ms> - <text>`. `_Framework`'s copy of a `log_message` is skipped.
    - **The v3 pages** are one reference, `references/v3-script.md`, and `assets/v3_template/`,
      both written from the 12.4.16 index and outlines of Ableton's v3 scripts. The facts the
      index can't show (what a skin does with a missing name, what `Mixer.MuteOn` means) are
      marked `documented`, read in the decompiled 12.0 framework.
    - **Changed by the load test** (the user, 2026-11-18): Quant is built, on Global encoder 5,
      at the user's request. `Mixer.MuteOn` means "muted", `tested` in 12.4.16, replacing the
      12.0 reading; the script's skin swaps it for the panel's "Active". `log`'s format line
      reads `<logger>:<ms>`, not `<module>:<line>` (the reviewer, from the 12.4.16 log).
48. **Before the 9a round: a review, two graders, a validator warning, listener names** (user
    agreed, 2026-11-18, step 10, after the UC4 load test). So that the round measures what the load
    test taught:
    - The reviewer agent reviews step 10.
    - The `uc4-mixer-v3` case gets two graders, the session box without an identity reply and
      values sent back for the UC4's display, and its prompt the two device facts they rest on
      (the display shows values sent to it; whether the UC4 answers an identity request is not
      known). Their scores can't be compared with the baseline round; the two arms of the new
      round can.
    - The validator gets `session-ring` (warning): a v3 Specification without
      `identity_response_id_bytes` or `custom_identity_response` and without a ring class of its
      own. It runs only when the build's Specification has the identity field. Gluon's v3
      scripts give no such warning against 12.4.16.
    - `eval_names.py` derives `add_<e>_listener`, `remove_<e>_listener`, `<e>_has_listener` and
      `notify_<e>` from a class's `__subject_events__` or `__events__` (`documented`, decompiled
      12.0 framework), found with ClyphX's `offset_has_listener`.
    - Not a rule: Live's property types (an int, not a float); the index has them only for some
      members.
    - **The extractor's stack simulation merges paths at jump targets** (user, 2026-11-18): a
      store of `a or b` had kept only `b`, and the v3 page's mute LED claim had rested on that.
      Now `a or b` and `a and b` keep both sides, other merges (a conditional expression) give
      `…`; indexes are rebuilt (no schema change).
49. **The MCP design ideas go into step 11** (user, 2026-11-18, grilling round 1 of the MCP
    ideas, Q1–Q8, on the agent's recommendations). Sources: Zhang, Kraska, Khattab, *Recursive
    Language Models* (arxiv.org/abs/2512.24601); Zhang, *The Mismanaged Geniuses Hypothesis*
    (alexzhang13.github.io/blog/2026/mgh/); Claude Code's Code Mode page
    (code.claude.com/docs/de/code-mode) and MindStudio's explainer of it. Their shared point:
    keep big reference data out of the agent's context, and give it small building blocks it can
    combine, also from code, with answers of bounded size.
    - **Q1:** they are additions to step 11, not a plan of their own.
    - **Q2:** every building block is in the query core, so the CLI, the skill's scripts and
      the MCP tools all have it. The user asked what MCP adds then:
      - typed tool parameters the client shows the model;
      - clients without a shell (Claude Desktop, other MCP clients);
      - starting with `uvx`, no install;
      - an index kept loaded between calls.
      Its cost: the tool descriptions take context in every session.
    - **Q3:** `check_names` (from `scripts/eval_names.py`) moves into the package as a CLI
      command and MCP tool. For a script folder or a list of names, it gives each class, member
      and keyword with its confidence. It stays separate from `validate`, since it reports facts,
      not errors. The skill runs it on each draft. The user asked about editor completion; that
      is the open Q9.
    - **Q4:** a small stable API of six functions (`lookup`, `search`, `outline`, `validate`,
      `check_names`, `list_builds`), returning the same answers as the tools. More can join
      later. Claude Code's Code Mode (experimental, off by default) runs **JavaScript** that calls
      tools and shell commands, so for code the CLI's `--json` answers are the interface any
      language reaches; the Python functions serve Python callers (Q10).
    - **Q5:** every answer has a default size cap (about 4,000 tokens). `outline` is answered by
      section (classes, Specification, mappings, elements). `search` and `outline` say what was
      left out and how to get the next page. The user's condition: it must be undoable and
      harmless. So `--full` or a larger limit gives the whole answer, nothing is removed from
      the index, and the note always says what was cut.
    - **Q6:** one short worked example in each tool's description; one batch-check example in
      the skill.
    - **Q7:** `eval_score.py` counts tool calls and tokens per run from the kept traces, so later
      rounds and the step 13 benchmark show what these save.
    - **Q8:** no tool that calls a model itself for now. The user wants it compared later with
      plain tool calls (cost and correctness), as an experiment in the step 13 benchmark.
    - **Q9 (round 2):** editor completion comes from **type stubs**. `build-stubs <build>` writes
      `.pyi` files for a Live build, which the user's existing Python language server
      (basedpyright or pylsp in Neovim) reads; there is no language server of our own. Like the
      index, the stubs are built from Ableton's code, so they are generated locally and never
      published; maybe in a separate repo later (the user). A small step after step 11.
    - **Q10 (round 2), proposed, the user asked about the drawbacks:** one answer shape for the
      CLI's `--json`, the Python functions and the MCP tools, with the CLI documented as the way
      in for code in any language. Nothing is lost: the CLI's text output, the Python functions
      and the MCP tools stay as they are. The costs:
      - the shape is a contract, so answers carry a version number and changes are noted;
      - a CLI call takes 0.11–0.15 s against about 0.05 s from Python (measured 2026-11-18),
        so `lookup` and `check_names` take many names in one call.
      Awaiting the user's yes.

## Open questions

None: grilling closed 2026-11-15 (user confirmed).

## Steps

Written by `/to-tickets` (2026-11-15, approved by the user). Each step is a vertical slice that works
on its own and fits one fresh builder session. One builder at a time works the frontier in this order:
1 → 2 → 3 → 5 → 5a → 7 → 9 → 9a → 8 → 10 → 4 → 6 → 11 → 12 → 13. Milestone 1 is complete after step 10.
Step 5a was added on 2026-11-15 (Decision 36), step 13 on 2026-11-15 (Decision 39).
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
   - **Built 2026-11-15.** `lookup class` shows a class's MRO and every member with its origin
     and what it overrides (`--own` for own members only) and finds re-exported names;
     `search` takes a name or words (`--kind`, `--limit`, `--build`). Names resolve at query
     time (Decision 34; index schema 3 records star imports). 12.4.16: every base of all 4055
     classes resolves (step 2 left 31 classes with an unresolved base), all MROs are C3, and
     6 classes are incomplete because of the 5 unparsed base expressions. Seam B: a
     hand-written index in two builds (`tests/hand_index.py`) with a diamond, a star import,
     an alias, a self-named base, an inherited nested class, an unresolved base and a `Live`
     base with its proxy model.
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
   - **Built 2026-11-15.** `outline <script>` (`--all-components`, `--build`, `--json`) shows a
     script's classes with their roles, own members and what they override, its Specification
     fields with the framework's defaults, its component map, mappings and modes (v3), and its
     elements, components and layers with where each is made. The extractor now records a
     statement summary of each function, in a separate file per build (Decision 35, index
     schema 4; `build-index --no-statements` leaves it out). Seam A: a fixture method
     with each kind of statement and each kind of condition. Seam B: a hand-written v3 script and a `_Framework` script on
     a library, with a factory, a `partial` alias, a comprehension, an override that calls
     `super()`, a component returned by a method and runtime component-map names. Local-only:
     APC_mini_mk2 (8 elements, 6 mappings, `Drum_Group` from the framework's map) and APC_mini
     (its shift button and session from `APC_Key_25`, its master volume from its own
     `_create_controls`, its transport not built because `HAS_TRANSPORT = False`).
5a. **Documentation site skeleton** (Decision 36)
   - **Blocked by:** 5
   - **Delivers:**
     - a plugin-free `mkdocs.yml` built with Zensical (pinned) and the first pages: Home (what it is, unofficial, credits),
       Getting started (install with uv, `build-index`), How it works (index → query core →
       CLI, skill and MCP server; fact confidence; what stays local and why; the statement
       summaries and `--no-statements`), the generated CLI reference, Known limits
     - a script that generates the CLI reference from the argument parser, with `--check`
     - `scripts/docs-check.sh` and a GitHub Pages workflow (the user enables Pages in the repo
       settings)
     - `.claude/agents/docs.md` and `.claude/agents/reviewer.md`, adapted from cmdAbl
   - **Checks:** `scripts/docs-check.sh` passes (the Zensical build fails on broken links, the
     reference is current); the same `mkdocs.yml` also builds with `mkdocs-material` 9.7; a test that the reference generator's `--check` fails on a stale page; the
     reviewer agent passes the pages, including the rule that no example comes from a real
     index.
   - **Built 2026-11-15.** Pages Home, Getting started, How it works, CLI reference (generated by
     `scripts/gen_cli_reference.py`, `--check` tested on a stale page), Known limits and Develop;
     `scripts/docs-check.sh`; the `docs` Pages workflow; the docs and reviewer agents. `zensical
     build --strict` fails on missing pages and anchors, and `mkdocs-material` 9.7.7 builds the
     same `mkdocs.yml` with `--strict` (see the 2026-11-15 finding under Decision 36). The
     `--index-dir` default is resolved at run time, so no home path reaches the reference. The
     reviewer agent's findings were fixed.
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
   - **Built 2026-11-15.** `validate <folder>` (`--build`, `--json`), with the rules
     `folder-name`, `syntax-error` (parsed as Python 3.11), `create-instance` (exists and takes
     `c_instance`) and `unresolved-import` (also names missing from the imported module, and the
     relative form for a Python 2 implicit relative import), plus a `not_checked` list
     (Decision 37, index schema 5). Seam B: clean v3 and `_Framework` samples and a bad sample
     per rule over the hand-written index; Seam A: the fake bundle's Python. Local-only: a clean
     sample against 12.4.16 has no findings. Docs: How it works, Getting started and Known
     limits describe it.
8. **Validator: framework checks**
   - **Blocked by:** 7
   - **Delivers:** checks for:
     - signatures of overridden framework methods
     - Specification fields and component-map keys, and the control names in a mappings
       function (Decision 42)
     - components built outside `component_guard`
     - `disconnect` not calling its base
     - with the severities `error`, `warning` and `not_checked` (Decision 43)
   - **Checks:** a bad sample for each rule; a clean hand-written v3 sample gives no findings.
     Local-only: the v3 scripts in `reference/` (gluon's factory scripts, MidiFighterV3) give
     no `error` against 12.4.16 that is ours (Decision 43 says how each one is read).
   - **Built** (2026-11-16): `framework_checks.py` with the seven rules of Decision 43, read as
     Decision 44 says; `tests/test_framework_checks.py` (a clean v3 sample, a bad sample per
     rule). Local-only against 12.4.16:
     - gluon's Live 12 clone (147 script folders) and MidiFighterV3 give no `error`. The one
       `warning` is MidiFighterV3's `disconnect`, which skips its base: a real finding.
     - The Live 11.2.11 clone gives one `error`, an `override-signature` in `pushbase`. The
       Live 12 clone's `pushbase` matches 12.4.16, so it is an API change since 11, not a false
       positive.
     - A copy of `APC_mini_mk2` with seven mistakes planted gives each one as a finding.
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
   - **Built** (2026-11-15): the load test and the 12-item checklist pass in Live 12.4.16, the
     comparison and the findings are in [milestone-1/apc-mini-mk1.md](milestone-1/apc-mini-mk1.md),
     and the skill took the repeatable findings (Decisions 40 and 41). Every API name is `observed`,
     except `is_grouped` and `group_track` (observed only in the Push 3 helper's proxy model,
     `tested` by the checklist) and three `SessionComponent` instance attributes (`documented`).
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
   - **Built** (2026-11-16, baseline round): the three cases, `scripts/eval_names.py`,
     `eval_score.py` and `eval_run.sh`, and the scores in
     [milestone-1/skill-evals.md](milestone-1/skill-evals.md). With the skill every behaviour
     grader passed. "Fewer invented names" is not met yet: both arms had none, and the name check
     cannot see names in v3 mappings (Decision 42). One more round after step 10 (Decision 46);
     the trigger check is still to run.
10. **v3 references and the UC4 script (Milestone 1, part 2)**
    - **Blocked by:** 8, 9a
    - **Delivers:** the v3 template and references (Specification and elements,
      components/layers/modes, skins and colours), refined with `/skill-creator`.
    - **Demo:** Claude writes a v3 script for the UC4 from the UC4 Editor's device facts.
    - **Checks:** the same as step 9 on the UC4; the 9a evals re-run and show the v3 references
      help. Milestone 1 is complete (Decision 28).
    - **In work** (2026-11-17): `references/v3-script.md`, `assets/v3_template/` and
      `examples/Faderfox_UC4/` (Decision 47) validate with no findings against 12.4.16; the
      device facts, what the script does and the 14-item checklist are in
      [milestone-1/faderfox-uc4.md](milestone-1/faderfox-uc4.md).
    - **Load test passed** (2026-11-18, the user, Live 12.4.16): all 14 items. Four fixes came
      from it and went into the skill as `tested` facts: a session ring that enables itself
      without an identity reply, `is_feedback_enabled=True` for controls that show values, exact
      types for Live's properties (an int, not a float), and `Mixer.MuteOn` meaning "muted" (the
      12.0 reading had it the other way round). Quant was added on Global encoder 5 at the
      user's request. `log` also reads v3 logging and a record's lines without a timestamp.
      The 9a round ran 2026-11-18 (Decision 46): with the skill, every behaviour grader passed and
      no script had a validator finding. **Step 10 is done, and with it Milestone 1.**
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
      - the user guides on the documentation site (Decision 36): writing a Remote Script with
        the skill, the MCP server setup, and the install for Claude Code and other agents
    - **Checks:**
      - installs in Claude Code
      - `npx skills add` installs the skill
      - no Ableton material or Live 13 data in the published files
      - the user sets the GitHub description and topics (Decision 27)

13. **Benchmark: with and without the skill and the MCP server** (Decision 39)
    - **Blocked by:** 12
    - **Delivers:**
      - a set of Remote Script tasks (write a script for a controller, add a feature, fix a
        script that does not load), run with the skill and the MCP server and without them
      - scores checked by a script: the result validates clean against the build's index, every
        API name it uses is in that build, the known traps are avoided; time and tokens per run
      - a short README table, linked to the full results on the documentation site
    - **Checks:**
      - the user loads the best and the worst script of each side in Live; the agent reads `Log.txt`
      - no Ableton material or Live 13 data in the published results

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
