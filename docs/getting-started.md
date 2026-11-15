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

Check what you have:

```sh
uv run ableton-remote-script-mcp list builds
```

It lists every indexed build and every installed Live that has no index yet. When you update
Live, run `build-index` again: each build gets its own index, and an old one is kept.

## Look things up

```sh
# a class: its bases, its order of inheritance, every member and where it comes from
uv run ableton-remote-script-mcp lookup class ControlSurfaceSpecification

# names by part of a name, or by words
uv run ableton-remote-script-mcp search session ring

# how one of Live's own scripts is built: classes, Specification, component map, elements
uv run ableton-remote-script-mcp outline APC_mini_mk2
```

Add `--build 12.4.16` to ask a particular build, and `--json` to get the answer as JSON. The
[CLI reference](reference/cli.md) lists every option.

## Where the index lives

By default in `~/.local/share/ableton-remote-script-mcp/index/` (or under `$XDG_DATA_HOME` when
you set it). Set `ABLETON_REMOTE_SCRIPT_INDEX`, or pass `--index-dir`, to use another folder.
