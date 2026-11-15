# ableton-remote-script-mcp

MCP server and agent skill for writing Ableton Live MIDI Remote Scripts. **Unofficial**, not
affiliated with Ableton. Work in progress: plan `docs/feature-plans/0001-architecture.md`.

## API index (works now)

Needs [uv](https://docs.astral.sh/uv/) and an installed Ableton Live (macOS). The index is built on
your machine from your Live install and never leaves it.

```sh
uv run ableton-remote-script-mcp build-index            # newest installed release, or --app <Live.app>
uv run ableton-remote-script-mcp list builds             # indexed builds, and installed ones with no index
uv run ableton-remote-script-mcp lookup class ControlSurfaceSpecification   # MRO, members with their origin, signatures
uv run ableton-remote-script-mcp lookup class ableton.v3.control_surface.Component  # re-exported names work too
uv run ableton-remote-script-mcp search session ring                          # by name or words; --kind, --build
uv run ableton-remote-script-mcp outline APC_mini_mk2   # a script's classes, Specification, component map, mappings, elements
```

`build-index` writes two files: the API index (names and signatures) and the statement summaries
of function bodies that only `outline` reads. `--no-statements` leaves the second one out.

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
