# How it works

## From your Live to an answer

1. **The index is built.** Live ships its Remote Scripts as compiled Python 3.11 files
   (`.pyc`) inside the app. `build-index` reads them, without running them, and writes what it
   finds to one file per Live build.
2. **The query core answers.** `lookup`, `search`, `outline` and `validate` read that file. They follow
   imports and re-exports, so a class can be asked for by the short name a script imports it
   under, and they walk each class's bases to show every member it inherits.
3. **The command line prints the answer.** The skill's scripts call the same commands, and the
   MCP server will ask the same query core, so every way in gives the same answer.

## What the index holds

For each Live build:

- every module of the three framework generations (`_Framework`, `ableton.v2`,
  `ableton.v3`), every Remote Script and library package in the app, and the Push 3 helper's
  copies with its pure-Python model of the `Live` module
- each class with its bases, members, signatures with their default values where the compiled
  files keep them, class attributes and docstrings
- each module's imports, so names can be followed to where they are defined
- the names of the Python modules Live ships with (its standard library and a few extra
  packages), so an import can be checked against them

It holds names and signatures, not the code of function bodies.

## Statement summaries

`outline` needs more than names: to show which elements and components a script creates, it has
to know which calls a method makes. `build-index` therefore writes a second file next to the
index, the **statement summaries**: for each function, the calls it makes, where their results
are stored, and the conditions, loops and exception handlers each call sits under.

Nothing is run to get them, so a call under an `if` is only known to run, or not to run, when the
script's own class attributes settle the test. `outline` marks such entries.

`outline` also takes a path to a script folder of your own (`outline ./My_Script`). It reads the
folder the way `validate` does: it compiles the sources and lays them over the index. One gap:
a call that also passes `**k` loses its keyword arguments in the summary, so `outline` shows
them as `…`.

Only `outline` reads this file. If you don't want it, build with `--no-statements`; every other
command works the same, and `outline` tells you that the summaries are missing.

## Checking a script

`validate` reads your script's `.py` files with Python's own parser, never runs them, and checks
them against one build's index. Each finding has a severity: `error` (the index proves it wrong),
or `warning` (likely wrong, but the framework accepts it). The basic rules:

| Rule | Finds |
| --- | --- |
| `folder-name` | A folder name with spaces, which Live doesn't list, or one that isn't a Python name (`my-script`): Live imports the script by its folder name, and the import fails. |
| `syntax-error` | A file that doesn't parse as Python 3.11, the Python Live runs. A broken file is a finding, never a crash. |
| `create-instance` | An `__init__.py` without `create_instance`, or one that can't be called with the `c_instance` argument Live passes. |
| `unresolved-import` | An import that doesn't resolve in that build: not one of the script's own modules, not in Live's Remote Scripts folder, not in the Python Live ships. Also a name the imported module doesn't have. |

An import inside a `try` that handles `ImportError` is optional and isn't checked. A few imports
can't be decided from the index; they are listed as *not checked*, with the reason: the modules
Live provides from its own C++ code (`Live`, `MidiRemoteScript`), and the C modules of Python's
standard library, which are part of Live's program and not files the index can see.

### Framework checks

The framework checks look at how the script uses Live's framework. The validator compiles your
script with Python 3.11, the way Live does, and reads it with the same code that reads Live's own
scripts for the index. Then it looks at your Specification, component map, mappings, elements and
classes as `outline` would show them, without running anything.

| Rule | Severity | Finds |
| --- | --- | --- |
| `mapping-key` | error | A key in a v3 mappings section that the component's class has neither as a control nor as a `set_<key>` setter, looked up along the class's inheritance. In a modes section, its own keys are checked against the modes component, which also gets a `<mode>_button` for each mode. Each mode's keys are checked against the component the mode names. |
| `element-name` | error | A value in the mappings (`"pads"`, `"pads_raw[3]"`) that names no element your Elements class builds. Names are lower case with spaces as `_`; a matrix also gets `<name>_raw`; `add_modified_control` makes `<control>_with_<modifier>`. |
| `unknown-component` | warning | A mappings section that names nothing in the component map and has no modes, which is what a typo looks like. A mode whose `component=` names no component, or a mode without `component=`, is an error: the framework raises a `KeyError` while it sets up. |
| `specification-field` | warning | A field in your Specification that Live's `ControlSurfaceSpecification` doesn't have, so the framework never reads it. |
| `override-signature` | error | A method that overrides one of the framework's methods but can't take the arguments the framework's signature allows: too few or too many positional arguments, or keyword arguments that don't match. A renamed parameter is fine. `__init__` is yours to call and isn't checked. |
| `component-guard` | error | An element or component built in a control surface's `__init__` outside `with self.component_guard():`, also through a method `__init__` calls. v3's `setup()` and the Elements class are exempt: the framework runs them inside the guard. |
| `disconnect-base` | warning | A `disconnect` that doesn't call the `disconnect` it overrides, so the framework's clean-up doesn't run. |
| `session-ring` | warning | A v3 Specification with no identity reply and the framework's own session ring: the framework enables the ring only after the controller is identified, so Live draws no session box. |

Every close name the index has is offered with the finding (`close: num_tracks`). What a rule
can't decide is listed as *not checked*, with the reason. Some examples:
- a component whose class answers names by pattern (v3's `MixerComponent` takes any `set_…`)
- element names your Elements class builds in a loop
- a component map that isn't a plain dict

The framework checks need Python 3.11; on another Python they are listed as not checked.

## Loading a script

Only you operate Live: the tools copy files and read the log, they never start, stop or control
Live.

- **`install`** runs `validate` first and stops at any finding (`--no-validate` skips the check).
  It copies the script's source into `Remote Scripts` in your User Library
  (`~/Music/Ableton/User Library`, or `--user-library`), leaving compiled files and hidden files
  behind. An existing copy is replaced only with `--replace`, and only if it is a script folder
  (it has an `__init__.py`) and not a symbolic link.
- **`log`** reads `Log.txt` in Live's preferences folder, of the Live build you name or the one
  that ran last, from the point where Live last started. Live writes a traceback in many small
  pieces; `log` puts each one back together. With `--script`, it shows the tracebacks that pass
  through that script's folder and the messages the script logged (a `_Framework` script's
  `log_message`, a v3 script's Python `logging`), and counts the others. It
  also shows tracebacks whose frames are all in Live's shared packages (`_Framework`, `ableton`,
  …) as "framework-only": a broken combo, for example, fails there without naming the script.

## Testing a script

The tools above never send anything to Live. The one exception is the
[test rig](test-rig.md), and only after you have picked its virtual port `ARS Test Rig` for a
Control Surface slot. It then sends MIDI to that port only, never to your hardware's ports. It
may change the open Set for a check, but never saves it. The rig works out each element's MIDI
message from the script's code the way `outline` does. It decides each step from Live's MIDI
replies and `Log.txt`, and also from Live's state when the AbletonMCP Remote Script runs.

## Fact confidence

Every answer names its Live build and a confidence:

| Confidence | Means |
| --- | --- |
| `observed` | Present in the index of that Live build. |
| `tested` | Used by a small script that loaded in that build. |
| `documented` | Found only in a secondary source, such as Structure Void, a forum or old decompiled code. |

Most answers are `observed`. A name that is `observed` in one build says nothing about
another build: ask that build.

### Live's own objects

Live's song, tracks, clips and devices come from Live's C++ code, not from files the index can
read. The index sees them through the model the Push 3 helper ships. That model lacks many
names: listener methods such as `add_notes_listener`, and properties such as `is_foldable`.

`import-structure-void` fills that gap from [Structure Void](https://midiremotescripts.structure-void.com)'s
"runtime" pages, which were read inside an unstated Live 12.x:

```sh
uv run ableton-remote-script-mcp import-structure-void
```

It fetches the pages once, keeps them and the facts read from them on your machine (the pages
are CC BY-NC-SA 4.0), and marks every fact from them `documented`, with its page. Then
`lookup class` shows those members next to the model's, and `search` finds them. A name that
both have is shown once, as `observed`. The `View` classes (`Song.View`, `Clip.View`) have no
members on those pages; the model has them.

### Checked against Structure Void's framework pages

Structure Void also has one page per module of Live's Remote Scripts: each class with its bases
and its members' argument names. `import-structure-void` reads those too, from the site's
search index (one download), and keeps them on your machine. They serve as a cross-check:

```sh
# the whole index against the pages, or one package
uv run ableton-remote-script-mcp check-structure-void --under ableton.v3
```

It lists the classes where the pages and the index disagree: members only one side has,
different argument names, different bases. `lookup class` shows the same for one class, with a
link to its page. The pages come from an older, unstated Live 12.x, so most differences are
changes between that build and yours (a renamed member, a new argument). A difference can also
point to a gap in the index. The check names what to look at; the index's own facts stay
`observed`.

## What stays local, and why

Live's code belongs to Ableton. The `.pyc` files, the index built from them and the statement
summaries stay on your machine, in a folder outside the repository. This project publishes its
own tools and its own writing, never anything extracted from Live.
