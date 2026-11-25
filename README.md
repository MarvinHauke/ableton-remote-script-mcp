# ableton-remote-script-mcp

MCP server and agent skill for writing Ableton Live MIDI Remote Scripts. **Unofficial**, not
affiliated with Ableton. Work in progress: plan `docs/feature-plans/0001-architecture.md`.

## How to use it

There is no release yet: you run it from a clone. You need a Mac with Ableton Live in
`/Applications`, [uv](https://docs.astral.sh/uv/) (it brings the Python 3.11 that Live's
scripts need) and `git`.

**1. Clone it and build the index.** The index is built on your machine from your Live install and
never leaves it.

```sh
git clone https://github.com/MarvinHauke/ableton-remote-script-mcp.git
cd ableton-remote-script-mcp
uv sync
uv run ableton-remote-script-mcp build-index             # newest installed release, or --app <Live.app>
uv run ableton-remote-script-mcp import-structure-void   # optional: Structure Void's pages, as a documented cross-check
```

**2. Give your coding agent the skill.** `skills/ableton-remote-scripts/` (open Agent Skills
format) walks the agent through a script:
- the device facts and a reference script;
- the `_Framework` or `ableton.v3` template;
- lookups and a name check of each draft;
- validate, an optional type check of the script's own code (basedpyright or pyright with the
  stubs of [Editor setup](docs/editor-setup.md)), and install;
- reading Live's log after you loaded the script, and optionally checking it with the
  [test rig](docs/test-rig.md).

Its scripts call the `ableton-remote-script-mcp` command, so put the command on your PATH and
link the skill where your agent finds skills (for Claude Code, `~/.claude/skills`):

```sh
uv tool install --editable .     # the command, from this clone
ln -s "$PWD/skills/ableton-remote-scripts" ~/.claude/skills/ableton-remote-scripts
```

Then ask: "Write a Remote Script for my controller". The agent asks you for the device facts. Only
you operate Live: the agent tells you when to restart it and pick the script, then reads the log.

**3. Or add the MCP server.** The same lookups, as tools for any MCP client (Claude Code,
Claude Desktop, Cursor). It reads the index from step 1:

```sh
claude mcp add ableton-remote-script -- uv run --project "$PWD" ableton-remote-script-mcp mcp
```

For another client, the command is `uv run --project /path/to/clone ableton-remote-script-mcp mcp`.

**4. Completion in your editor.** `build-stubs` writes type stubs of a build into your script
project, for basedpyright, pyright or pylsp. Run it in the clone, after `build-index`:

```sh
uv run ableton-remote-script-mcp build-stubs --build 12.4.16 --project path/to/My_Project
```

[Editor setup](https://marvinhauke.github.io/ableton-remote-script-mcp/editor-setup/) has the
editor configuration.

**The commands** behind all of these:

```sh
uv run ableton-remote-script-mcp list builds             # indexed builds, and installed ones with no index
uv run ableton-remote-script-mcp lookup class ControlSurfaceSpecification   # MRO, members with their origin, signatures
uv run ableton-remote-script-mcp search session ring     # by name or words; --kind, --build, --offset
uv run ableton-remote-script-mcp outline APC_mini_mk2    # a script's classes, Specification, mappings, elements; --section
uv run ableton-remote-script-mcp check-names path/to/My_Script   # each API name it uses: observed, documented or unknown
uv run ableton-remote-script-mcp validate path/to/My_Script --build 12.4.16   # findings: file, line, rule, message, fix
uv run ableton-remote-script-mcp install path/to/My_Script   # validate, then copy into the User Library (--replace)
uv run ableton-remote-script-mcp log --script My_Script      # its tracebacks and messages in Live's Log.txt
uv run ableton-remote-script-mcp diff 12.4.16 <newer build> --under ableton.v3   # what changed between two builds
```

Every answer names the Live build and the fact's confidence (`observed` = present in that build's
index, `documented` = from Structure Void's pages). Answers are capped at about 4,000 tokens
and say what they left out; `--json` gives the same answer as the MCP tools and the Python API.
`rig` plays a controller to your script over a virtual MIDI port, to test it without the
hardware.

## Documentation

[marvinhauke.github.io/ableton-remote-script-mcp](https://marvinhauke.github.io/ableton-remote-script-mcp/),
built from `docs/` with [Zensical](https://zensical.org).

## Development

```sh
uv run pytest            # tests that need an installed Live 12.4.16 skip themselves when it is absent
scripts/docs-check.sh    # the CLI reference is current and the docs site builds (--strict)
uv run python scripts/gen_cli_reference.py   # regenerate docs/reference/cli.md after changing a help text
```

## Credits

Julien Bayle's [Structure Void](https://midiremotescripts.structure-void.com) MIDI Remote Scripts documentation.
