# Editor setup

If you write a Remote Script by hand in your own editor, this page gets you completion, signatures
and docstrings for the framework and the `Live` module, and a mark on a name your Live build
doesn't have. It works through type stubs (`.pyi` files), which your editor's Python language
server reads. Types are `Any` throughout, so the server checks names, not types.

## What you need

- A Mac with Ableton Live installed in `/Applications`; the stubs are built from your own Live.
- [uv](https://docs.astral.sh/uv/) and a clone of this repository, as in
  [Getting started](getting-started.md#install).
- An editor with a Python language server (below).

## Set it up

Run both commands in your clone of this repository; `uv run` finds the tool there.

1. Build the index of your Live build, once ([Getting started](getting-started.md#build-the-index)).
   The stubs are made from it:

    ```sh
    uv run ableton-remote-script-mcp build-index
    ```

2. Write the stubs into your script project. `--project` takes the project's folder:

    ```sh
    uv run ableton-remote-script-mcp build-stubs --build 12.4.16 --project path/to/My_Project
    ```

    Pass the build of the Live you use. Without `--build`, the newest indexed build is used, which
    may not be the one you run.

What `--project` does:

- The stubs go to `stubs/` in that folder. A folder of earlier stubs is replaced; a `stubs/`
  folder this tool didn't write is refused, so your own files are never deleted.
- When the folder has no pyright settings, it creates `pyrightconfig.json` with
  `"stubPath": "stubs"`, `"pythonVersion": "3.11"` and `"reportMissingModuleSource": false`
  (Live has the modules; the stubs stand in for them).
- When there are settings already (a `pyrightconfig.json`, or `[tool.pyright]` or
  `[tool.basedpyright]` in `pyproject.toml`), it leaves them alone. It prints the settings to use,
  or says the project is ready when its `stubPath` is already `"stubs"`.
- When the folder is in a git repo and nothing ignores `stubs/` yet, it adds `stubs/` to
  `.gitignore`.

`--project` and `--out` exclude each other. `--out` writes to a folder of your choice; without
either, the stubs go into the index folder.

The stubs belong to one project and to your machine. They are built from Ableton's code, so keep
them out of git and never commit or share them.

What the stubs hold: everything the index has (modules, classes with their bases, methods with
their parameters, properties, class attributes, and the attributes a class's methods set on
`self`), and the `Live` package, from the Push 3 helper's model of it. With
[Structure Void's pages](getting-started.md#build-the-index) imported, `Live` also gets the members
those pages list, marked `# documented`; `--observed-only` leaves them out.

## Your editor

### Neovim

Both forms below need the nvim-lspconfig plugin: it holds the servers' default commands and finds
the project root by its `pyrightconfig.json`, which basedpyright and pyright both read. In Neovim
0.11 or newer:

```lua
vim.lsp.config('basedpyright', {})
vim.lsp.enable('basedpyright')
```

In older versions:

```lua
require('lspconfig').basedpyright.setup {}
```

For pyright, use the name `pyright` in place of `basedpyright`. Open a file in the project, not
from another folder, so the root is found.

### VS Code

Pylance reads `pyrightconfig.json`, so the project needs nothing else. As an alternative, set
`python.analysis.stubPath` to `stubs` in the workspace settings.

### pylsp

pylsp with jedi is documented here, not tested. `build-stubs` prints the setting it needs, the
path of the stubs folder:

```text
pylsp.plugins.jedi.extra_paths = ["/path/to/your/project/stubs"]
```

## After a Live update

Build the index of the new build, then write the stubs again with the new build, in your clone as
before:

```sh
uv run ableton-remote-script-mcp build-index
uv run ableton-remote-script-mcp build-stubs --build <new build> --project path/to/My_Project
```

The `stubs/` folder is replaced. Your `pyrightconfig.json` stays as it is.

## The Python that pyright uses

Pyright also looks up imports in the Python it finds on your PATH. With a newer Python than Live's
(Homebrew's 3.15, say) it can report errors inside that Python's own standard library files.
`pythonVersion` alone doesn't stop this. Either make pyright use a Python 3.11 (activate a
3.11 environment before you start the editor, or name one with `venvPath` and `venv` in
`pyrightconfig.json`), or ignore those errors.

## What the remaining errors mean

The stubs cover the names of the framework and `Live`. The errors left in standard mode come from
pyright reading your own code, not from gaps in the stubs. Two are common.

An attribute that may be `None`: pyright wants you to check it before you use it.

The control idiom of `ableton.v3`: you declare a control, then its handler with the same name.
Pyright reports that the name "refers to itself":

```python
class MyComponent(Component):
    play = ButtonControl()

    @play.pressed
    def play(self, button):
        ...
```

Pyright special-cases only a property's `.setter` for this pattern, so no stub can fix it.
Silence it on the decorator's line; this works in pyright, basedpyright and Pylance, and nothing
changes when the script runs:

```python
class MyComponent(Component):
    play = ButtonControl()

    @play.pressed  # pyright: ignore[reportGeneralTypeIssues]
    def play(self, button):
        ...
```

Annotating the control as `Any` (`play: Any = ButtonControl()`) also clears it in pyright and
Pylance, but basedpyright then reports the name as redeclared.

Live's own scripts look the same to pyright.
