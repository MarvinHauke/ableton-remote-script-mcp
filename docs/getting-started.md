# Getting started

## What you need

- A Mac with Ableton Live installed in `/Applications`.
- [uv](https://docs.astral.sh/uv/), the Python package manager. It brings the Python 3.11 that
  Live's scripts need, so your own Python stays untouched.
- `git`, to get the code.

## Install

There is no release yet; you run it from a clone of the repository:

```sh
git clone https://github.com/MarvinHauke/ableton-remote-script-mcp.git
cd ableton-remote-script-mcp
uv sync
```

## Build the index

```sh
uv run ableton-remote-script-mcp build-index
```

This finds the newest Live release in `/Applications` and indexes it. To index another build,
such as a beta, name its app:

```sh
uv run ableton-remote-script-mcp build-index --app "/Applications/Ableton Live 12 Beta.app"
```

Optionally, add Structure Void's pages on Live's own objects (song, tracks, clips, devices),
which the index knows only partly ([How it works](how-it-works.md#lives-own-objects)), and its
framework pages, to check the index against
([How it works](how-it-works.md#checked-against-structure-voids-framework-pages)):

```sh
uv run ableton-remote-script-mcp import-structure-void
```

Check what you have:

```sh
uv run ableton-remote-script-mcp list builds
```

It lists every indexed build and every installed Live that has no index yet. When you update
Live, run `build-index` again: each build gets its own index, and an old one is kept. When a new
version of this tool changes what the index holds, it asks you to rebuild.

## Look things up

```sh
# a class: its bases, its order of inheritance, every member and where it comes from
uv run ableton-remote-script-mcp lookup class ControlSurfaceSpecification

# names by part of a name, or by words
uv run ableton-remote-script-mcp search session ring

# how one of Live's own scripts is built: classes, Specification, component map, elements
uv run ableton-remote-script-mcp outline APC_mini_mk2
```

When you update Live, compare the old build's index with the new one's to see what a script
written for the old build may find added, removed or changed:

```sh
# counts per package
uv run ableton-remote-script-mcp diff 12.4.16 12.4.25b1

# the classes, members and signatures, for one package or module
uv run ableton-remote-script-mcp diff 12.4.16 12.4.25b1 --under ableton.v3
```

The diff compares names, bases and signatures (parameters, defaults, constant values), not line
numbers or docstrings. Both builds need an index.

Add `--build 12.4.16` to ask a particular build, and `--json` to get the answer as JSON. The
[CLI reference](reference/cli.md) lists every option.

## Check your script

Before you load a script in Live, check its folder against the build you target:

```sh
uv run ableton-remote-script-mcp validate ~/"Music/Ableton/User Library/Remote Scripts/My_Script" --build 12.4.16
```

Each finding names the file and line, the rule, what is wrong and how to fix it. For a script
whose `surface.py` imports `numpy`:

```text
My_Script  [Live 12.4.16, observed]  1 finding in 2 files
  surface.py:1: error [unresolved-import] `import numpy`: numpy is neither in Live 12.4.16's Remote Scripts folder nor in the Python that Live ships
      fix: use a module Live ships, or put the code inside the script's folder
```

The command exits with 0 when there are no findings and 1 when there are. [How it
works](how-it-works.md#checking-a-script) lists the rules.

`check-names` then lists every attribute and keyword the script uses that the build doesn't
know. It also takes a list of names, so you can check a draft's names in one call:

```sh
uv run ableton-remote-script-mcp check-names --build 12.4.16 --names SessionRingComponent.set_offsets Song.tracks
```

[Answers, API and MCP server](answers.md) explains its answer, and how the same lookups work
from Python and as MCP tools.

## Install it and read the log

`install` checks the folder first and copies it into your User Library only when there are no
findings:

```sh
uv run ableton-remote-script-mcp install path/to/My_Script --build 12.4.16   # --replace for a new version
```

Then, in Live: restart it, and choose `My_Script` as a Control Surface under Settings → Link,
Tempo & MIDI, with your controller's input and output ports. Live shows no error when a script
fails to load; it writes it to its log. `log` finds that script's errors and messages since Live
last started:

```sh
uv run ableton-remote-script-mcp log --script My_Script
```

It exits with 0 when there is no traceback and 1 when there is one. [How it
works](how-it-works.md#loading-a-script) says how it reads the log.

## Test it without the hardware

The test rig plays your controller to the script over a virtual MIDI port and checks what Live
sends back, step by step, as a check file says. [Testing with the rig](test-rig.md) shows how.

## Where the index lives

By default in `~/.local/share/ableton-remote-script-mcp/index/` (or under `$XDG_DATA_HOME` when
you set it). Set `ABLETON_REMOTE_SCRIPT_INDEX`, or pass `--index-dir`, to use another folder.
