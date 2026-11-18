# ableton-remote-script-mcp

MCP server and agent skill for writing Ableton Live MIDI Remote Scripts. **Unofficial**, not
affiliated with Ableton. Work in progress: plan `docs/feature-plans/0001-architecture.md`.

## API index and skill (work now)

Needs [uv](https://docs.astral.sh/uv/) and an installed Ableton Live (macOS). The index is built on
your machine from your Live install and never leaves it.

```sh
uv run ableton-remote-script-mcp build-index            # newest installed release, or --app <Live.app>
uv run ableton-remote-script-mcp list builds             # indexed builds, and installed ones with no index
uv run ableton-remote-script-mcp lookup class ControlSurfaceSpecification   # MRO, members with their origin, signatures
uv run ableton-remote-script-mcp lookup class ableton.v3.control_surface.Component  # re-exported names work too
uv run ableton-remote-script-mcp search session ring                          # by name or words; --kind, --build
uv run ableton-remote-script-mcp outline APC_mini_mk2   # a script's classes, Specification, component map, mappings, elements
uv run ableton-remote-script-mcp validate path/to/My_Script --build 12.4.16   # findings: file, line, rule, message, fix
uv run ableton-remote-script-mcp install path/to/My_Script   # validate, then copy into the User Library (--replace)
uv run ableton-remote-script-mcp log --script My_Script      # its tracebacks and messages in Live's Log.txt
```

`build-index` writes two files: the API index (names and signatures) and the statement summaries
of function bodies that only `outline` reads. `--no-statements` leaves the second one out.
`validate` checks a script folder's syntax, `create_instance` and imports against that build,
including the Python modules Live ships.

The skill, `skills/ableton-remote-scripts/` (open Agent Skills format), walks a coding agent
through writing a script with these commands: device facts, lookups, the `_Framework` and `ableton.v3`
templates and reference pages, validate, install, and reading the log after you loaded the script in Live.

Every answer names the Live build and the fact's confidence (`observed` = present in that build's
index).

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
