# How it works

## From your Live to an answer

1. **The index is built.** Live ships its Remote Scripts as compiled Python 3.11 files
   (`.pyc`) inside the app. `build-index` reads them, without running them, and writes what it
   finds to one file per Live build.
2. **The query core answers.** `lookup`, `search`, `outline` and `validate` read that file. They follow
   imports and re-exports, so a class can be asked for by the short name a script imports it
   under, and they walk each class's bases to show every member it inherits.
3. **The command line prints the answer.** Later, the skill and the MCP server will ask the same
   query core, so every way in gives the same answer.

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

Only `outline` reads this file. If you don't want it, build with `--no-statements`; every other
command works the same, and `outline` tells you that the summaries are missing.

## Checking a script

`validate` reads your script's `.py` files with Python's own parser, never runs them, and checks
them against one build's index:

| Rule | Finds |
| --- | --- |
| `folder-name` | A folder name with spaces: Live doesn't list the script. |
| `syntax-error` | A file that doesn't parse as Python 3.11, the Python Live runs. A broken file is a finding, never a crash. |
| `create-instance` | An `__init__.py` without `create_instance`, or one that can't be called with the `c_instance` argument Live passes. |
| `unresolved-import` | An import that doesn't resolve in that build: not one of the script's own modules, not in Live's Remote Scripts folder, not in the Python Live ships. Also a name the imported module doesn't have. |

An import inside a `try` that handles `ImportError` is optional and isn't checked. A few imports
can't be decided from the index; they are listed as *not checked*, with the reason: the modules
Live provides from its own C++ code (`Live`, `MidiRemoteScript`), and the C modules of Python's
standard library, which are part of Live's program and not files the index can see.

Checks of how the script uses the framework (signatures of overridden methods, Specification
fields) are not built yet.

## Fact confidence

Every answer names its Live build and a confidence:

| Confidence | Means |
| --- | --- |
| `observed` | Present in the index of that Live build. |
| `tested` | Used by a small script that loaded in that build. |
| `documented` | Found only in a secondary source, such as Structure Void, a forum or old decompiled code. |

Today every answer is `observed`. A name that is `observed` in one build says nothing about
another build: ask that build.

## What stays local, and why

Live's code belongs to Ableton. The `.pyc` files, the index built from them and the statement
summaries stay on your machine, in a folder outside the repository. This project publishes its
own tools and its own writing, never anything extracted from Live.
