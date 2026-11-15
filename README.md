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
```

Every answer names the Live build and the fact's confidence (`observed` = present in that build's
index).

## Development

```sh
uv run pytest            # tests that need an installed Live 12.4.16 skip themselves when it is absent
```

## Credits

Julien Bayle's [Structure Void](https://midiremotescripts.structure-void.com) MIDI Remote Scripts documentation.
