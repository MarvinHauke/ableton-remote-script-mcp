"""The MCP server (plan 0001 step 11, Decisions 17 and 49): the API index's lookups as tools, over
stdio, with the official MCP SDK.

    uvx --from <this repo or its git URL> ableton-remote-script-mcp mcp

Every tool is a thin adapter over `api.py`: it returns the same answer as the matching CLI
command's `--json` and the Python function, as structured content, with the same answer
compact as the text. The index stays loaded between calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent, ToolAnnotations

from . import api
from .query import SEARCH_KINDS

INSTRUCTIONS = """\
Facts about the API of Ableton Live's MIDI Remote Script framework (ableton.v3, ableton.v2,
_Framework) and the Live module, from an index of an installed Live build. Every fact names its
Live build and a confidence: observed (in that build's index) or documented (Structure Void's
pages, a secondary source). Build code on observed facts. Answers are capped at about 4,000
tokens; a `cut` note says what was left out and how to get it (full=true, a page, a section).
If an answer says index_missing, tell the user to run `ableton-remote-script-mcp build-index`.
"""

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def _result(answer: dict) -> CallToolResult:
    text = json.dumps(answer, separators=(",", ":"), ensure_ascii=False, default=str)
    return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=answer)


def make_server(index_dir: Path | None = None) -> MCPServer:
    server = MCPServer("ableton-remote-script-mcp", instructions=INSTRUCTIONS)
    where = {"index_dir": index_dir}

    @server.tool(annotations=READ_ONLY)
    def search_api(query: str, build: str | None = None, kind: str | None = None, limit: int = 20,
                   offset: int = 0, full: bool = False) -> dict[str, Any]:
        """Find classes, modules and members by name or words, best first.

        `kind` narrows to one of: class, module, member, method, property, classmethod,
        staticmethod, function, attribute. `next_offset` in the answer is the next page.

        Example: search_api(query="session ring", kind="class") gives
        ableton.v3.control_surface.components.session_ring.SessionRingComponent first.
        """
        if kind is not None and kind not in SEARCH_KINDS:
            return _result({"status": "not_found", "message": f"kind must be one of {', '.join(SEARCH_KINDS)}"})
        return _result(api.search(query, build, kind=kind, limit=limit, offset=offset, full=full, **where))

    @server.tool(annotations=READ_ONLY)
    def get_class(name: str, build: str | None = None, members: list[str] | None = None, own: bool = False,
                  full: bool = False) -> dict[str, Any]:
        """A class by short, qualified or re-exported name: bases, MRO, and every member, own and
        inherited (each with the class it comes from, `origin`).

        `members` asks only whether the class has these (the rest go to `missing_members`);
        `own` keeps only its own members.

        Example: get_class(name="SessionRingComponent", members=["set_offsets", "track_offset"])
        """
        return _result(api.lookup(name, build, own=own, members=members, full=full, **where))

    @server.tool(annotations=READ_ONLY)
    def check_names(names: list[str] | None = None, folder: str | None = None, build: str | None = None,
                    full: bool = False) -> dict[str, Any]:
        """Where API names are known in one Live build: give a list of names, or a script folder
        (then every attribute and constructor keyword its code uses).

        A name is `Class`, `Class.member` or a bare `name`. Each comes back as observed in the
        index, documented, or unknown (not_a_member: the class lacks it). A folder answer's
        `not_read` says what couldn't be read, so an unknown there may still be the script's own
        (an element its Elements class builds). Facts, not errors: check a whole draft in one
        call.

        Example: check_names(names=["ControlSurface.schedule_message", "Song.tracks",
        "SessionRingComponent.set_offsets"], build="12.4.16")
        """
        if (names is None) == (folder is None):
            return _result({"status": "not_found", "message": "give either names or folder"})
        return _result(api.check_names(folder, names, build, full=full, **where))

    @server.tool(annotations=READ_ONLY)
    def outline_reference_script(script: str, build: str | None = None, section: str | None = None,
                                 offset: int = 0, full: bool = False) -> dict[str, Any]:
        """The outline of one of Ableton's Remote Scripts (by folder name), or of a script folder
        (a path): its classes, Specification, component map, mappings, elements, components and
        layers, without function bodies.

        `sections` counts each section's items. A large outline keeps the sections that fit;
        `section` asks for one (modules, create_instance, classes, specification, component_map,
        mappings, unknown_components, elements, components, layers), `offset` for its next items.

        Example: outline_reference_script(script="APC_mini_mk2", section="mappings")
        """
        return _result(api.outline(script, build, section=section, offset=offset, full=full, **where))

    @server.tool(annotations=READ_ONLY)
    def validate_script(folder: str, build: str | None = None, full: bool = False) -> dict[str, Any]:
        """Check a Remote Script folder against a Live build's index, without running it: each
        finding has a file, a line, a rule, a severity, a message and a fix. `counts` holds the
        totals.

        Example: validate_script(folder="/Users/me/Music/Ableton/User Library/Remote Scripts/My_UC4")
        """
        return _result(api.validate(folder, build, full=full, **where))

    @server.tool(annotations=READ_ONLY)
    def diff_builds(from_build: str, to_build: str, under: str | None = None, full: bool = False) -> dict[str, Any]:
        """What changed between two indexed Live builds: packages, modules, classes and members
        added, removed or changed (bases, parameters, defaults). `by_package` counts per package;
        `under` narrows to one package or module.

        Example: diff_builds(from_build="12.4.16", to_build="12.5", under="ableton.v3"), once both are indexed
        """
        return _result(api.diff(from_build, to_build, under=under, full=full, **where))

    @server.tool(annotations=READ_ONLY)
    def list_builds() -> dict[str, Any]:
        """The indexed Live builds, newest first, with their counts, and installed Live builds
        that have no index yet. Other tools take `build`; without it they use the newest.

        Example: list_builds()
        """
        return _result(api.list_builds(**where))

    return server
