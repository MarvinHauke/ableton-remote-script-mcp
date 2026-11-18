---
name: ableton-remote-scripts
description: Write, fix and load Ableton Live MIDI Remote Scripts (control surface scripts in Python) against an API index of the installed Live build, so every framework name is checked instead of guessed. Use this whenever the user wants a Remote Script or control surface script for a MIDI controller, asks to map a controller's pads, buttons, faders or knobs to Live's session, mixer or devices, works with `create_instance`, `ControlSurface`, `_Framework` or `ableton.v3`, or has a Remote Script that does not show up or throws in Live's Log.txt — even if they only say "make my controller work with Ableton".
license: MIT
compatibility: macOS with Ableton Live 12.4 or later installed, and the ableton-remote-script-mcp command (Python 3.11 through uv) with an index built by `ableton-remote-script-mcp build-index`.
---

# Writing Ableton Live Remote Scripts

A Remote Script is a Python package in a `Remote Scripts` folder whose `__init__.py` defines
`create_instance(c_instance)`. Live runs it inside its own Python (3.11 in Live 12.4.16, observed) and gives it no API
documentation; Ableton's framework ships only as compiled `.pyc`. Names that look right but don't
exist (`set_clip_buttons`, `SessionComponent(width=8)`) fail only when Live loads the script, so
**look every name up before you write it.** The index of the user's own Live build is the
authority, not memory, blog posts or other scripts.

This skill is unofficial and not affiliated with Ableton.

## Facts carry a build and a confidence

Every API name you rely on comes from one Live build, with one of three confidences:

- `observed`: present in that build's index (a lookup found it).
- `tested`: used by a script that loaded in that build with no traceback.
- `documented`: from a secondary source only (Structure Void's reference, a forum, a decompiled
  script). Say so when you use one, and look it up before building on it.

When you tell the user what a script relies on, name the build and confidence ("`SessionComponent`
(Live 12.4.16, observed)"). Build code on `observed` or `tested` names only.

## The tools

The scripts in `scripts/` call the `ableton-remote-script-mcp` command; each prints `--help`.
If a script says the command or the index is missing, tell the user the command it prints
(installing the tool, or `ableton-remote-script-mcp build-index`); don't work around it.

| Script | What it answers |
|---|---|
| `scripts/lookup.sh builds` | the indexed Live builds, and installed builds with no index |
| `scripts/lookup.sh class <Name>` | a class with its bases, MRO and every member with its signature and origin (`--own` for its own members, `--member <m>` for only the ones you need); give the full dotted name (`_Framework.SessionComponent.SessionComponent`), since a short name matches the class in every framework generation |
| `scripts/lookup.sh search <words>` | classes, modules and members by name or words (`--kind class`) |
| `scripts/lookup.sh outline <Script>` | one of Ableton's own scripts: its classes, elements with their MIDI numbers, components and layers (`--section <name>` for one part of a large one) |
| `scripts/lookup.sh names <folder>` | every attribute and constructor keyword the script uses: known in the index (observed), on Structure Void's pages (documented), or unknown; `--names A.b C.d` checks a list |
| `scripts/validate.sh <folder>` | findings (file, line, rule, fix) for a script folder against a build |
| `scripts/install.sh <folder>` | validates, then copies the script into the User Library (`--replace` for a new version) |
| `scripts/log.sh --script <Folder>` | the tracebacks and messages of that script in Live's `Log.txt` since Live last started |

Live's own objects (`lookup.sh class Live.Clip.Clip`) are partly known to the index. If the user
ran `ableton-remote-script-mcp import-structure-void`, the lookup also shows members from
Structure Void's pages, marked `documented`: say so when you use one.

`lookup.sh class|search|outline`, `validate.sh` and `install.sh` take `--build <build>`, the index
to ask (default: the newest indexed build); `log.sh --build` picks which Live build's log to read.
Each script's header lists its options and exit codes. Answers are capped at about 4,000 tokens;
a line at the end says what was cut and how to get it (`--section`, `--offset`, `--full`).

## Workflow

1. **Find the build.** Run `scripts/lookup.sh builds` and ask which Live build the user runs if
   more than one is indexed. Write for Live 12.4 or later.

2. **Collect the device facts.** For each physical knob, fader, button or pad (a *device control*),
   write down: its name in the manual, MIDI message type (note or CC), channel, number, whether a
   button is momentary or toggles, and what its LED accepts (values or colours, and how to turn it
   off). Take them from the manufacturer's manual or MIDI implementation chart, or ask the user to
   read them off the controller's editor or a MIDI monitor. Name the source in the script's
   docstring. Never guess a MIDI number: a wrong one fails silently, with no traceback.

3. **Agree what the script does.** A short list of behaviours in the user's words ("the grid
   launches clips of the 8×8 box", "fader 1–8 set track volume"). This list becomes the behaviour
   checklist in step 8.

4. **Choose the framework generation.**
   - `ableton.v3` (Specification, elements, mappings) for new scripts that need modes, skins or
     several layers.
   - `_Framework` for a simple, direct mapping: a grid, a few buttons, faders on the mixer. It is
     the oldest generation and still ships in Live 12.
   Look up whichever you choose; never mix generations in one script. For `_Framework`, read
   [references/framework-script.md](references/framework-script.md) and start from
   `assets/framework_template/`. For v3, read [references/v3-script.md](references/v3-script.md)
   (Specification, elements, mappings and modes, skins, components of your own) and start from
   `assets/v3_template/`.

5. **Read a reference script.** Find one of Ableton's scripts for similar hardware
   (`scripts/lookup.sh search <controller name> --kind module`) and outline it. The outline shows
   which elements, components and layers that script builds and with which MIDI numbers. Use it to
   learn the framework's patterns, then write your own code: describe and adapt, don't copy.

6. **Write the script.** Copy the template, fill in the device facts, and build only what the
   behaviour list asks for. Before using a class, method or argument, look it up; the lookup
   shows inherited members and exact signatures. Check many names in one call rather than one
   lookup each:
   `scripts/lookup.sh names --names SessionRingComponent.set_offsets Song.tracks ControlSurface.show_message`. Keep the folder name a plain Python name
   (`My_Controller`): Live imports the script by its folder name. Name the `ControlSurface`
   subclass like the folder too: a `_Framework` script's log messages start with the class
   name, a v3 script's with its module, and the log script finds both by the folder name.

7. **Validate, check the names, then install.** Run `scripts/validate.sh <folder>` and fix every finding; the
   validator parses the code as Live's Python does and checks against the build:
   - imports and `create_instance`
   - v3 mapping keys and element names, and the component map
   - Specification fields
   - overridden framework methods' signatures
   - components built outside `component_guard`
   - `disconnect` overrides
   - a v3 session ring that Live never enables (no identity reply)

   An `error` is proven wrong by the index; a `warning` is likely wrong. Read the "not checked"
   list too: those names (keys of a component that answers names by pattern, such as v3's
   `MixerComponent`) are yours to look up. Names used on objects outside the mappings
   (`self._session.set_foo(...)`) are not checked either: run `scripts/lookup.sh names <folder>` on
   each draft and look at every `unknown` name; a `documented` one is labelled as such in the report. The index has names and signatures, not behaviour: when the
   code relies on what a method does (which LED value it sends, whether it releases a button),
   say so in the report and put it on the checklist. Then `scripts/install.sh <folder>` (add `--replace` after
   the first time).

8. **Load it in Live: the user's step.** Only the user operates Live. Tell them exactly what to do,
   then read the log yourself — see [references/loading-and-logs.md](references/loading-and-logs.md):
   restart Live, choose the script as a Control Surface under Settings → Link, Tempo & MIDI with
   the controller's input and output ports, then `scripts/log.sh --script <Folder>`. A
   traceback means the script did not load (or broke later); fix it, validate, reinstall with
   `--replace`, and ask for another restart. With no traceback, walk the user through the
   behaviour checklist one item at a time and note what passed.

9. **Report.** The files written, the build, every framework name used with its confidence (they
   become `tested` once the script loaded with no traceback), the validator result, the log
   result, and the checklist result. Say what was not tested.

## Done means

- `scripts/validate.sh` reports 0 findings for the build the user runs.
- After the user loaded it, `scripts/log.sh --script <Folder>` shows no traceback and shows the
  script's own start-up message.
- The user confirmed each checklist item, or you listed the ones that failed or were not tried.
