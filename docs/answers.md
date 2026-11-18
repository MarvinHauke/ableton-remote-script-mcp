# Answers, the API and the MCP server

The lookups answer in one shape, wherever you ask. The CLI's `--json`, the Python API and the
MCP tools return the same answer for the same question. The CLI's text output for people is
printed from that answer. Use the CLI with `--json` from code in any language, the Python
functions from Python, and the MCP tools from an MCP client.

## The answer

Each answer is a JSON object with:

- `status`:
  - `ok`;
  - `not_found` (with a `message` that names the build);
  - `index_missing` (with the command that builds the index).
- `answer_version`: the version of the answer's shape, now **1**.
- `live_build`: the build the facts come from.
- each fact's `confidence`:
  - `observed`: in that build's index;
  - `documented`: from Structure Void's pages, a secondary source.

### Size caps

An answer is capped at about 4,000 tokens, estimated as the compact JSON's length divided
by four. The cap removes nothing from the index. When an answer is larger, the longest lists
in it keep their first items, and a `cut` note says what was left out and how to get it:

```json
"cut": {"max_tokens": 4000,
        "fields": [{"field": "results", "kept": 63, "total": 200}],
        "how": "offset=63 gives the next results (CLI: --offset); full=true gives the whole answer (CLI: --full)"}
```

Ways to get the rest:

- `search`: a page at a time with `offset`; the answer's `next_offset` is the next page.
- `outline`: by section. `sections` counts the items of each one. A large outline keeps the
  sections that fit, in order; `section` asks for one of them, and `offset` for the next items
  of a long one.
- `lookup class`: `members` asks only for the members you need (the others it lacks go to
  `missing_members`), and `own` keeps only the class's own members.
- `diff`: `under` narrows it to one package or module.
- any of them: `full` (CLI `--full`) gives the whole answer.

The text output prints the same note as its last line.

## Checking names

`check-names` says where each API name is known in one build. It reports facts, not errors;
`validate` gives the errors.

```sh
uv run ableton-remote-script-mcp check-names my_script --build 12.4.16
uv run ableton-remote-script-mcp check-names --build 12.4.16 \
    --names SessionRingComponent.set_offsets Song.tracks ControlSurface.show_message
```

**For a folder,** it sorts every attribute name and every constructor keyword the code uses
into one of these:

| Name | Meaning |
|---|---|
| `own` | defined by the script |
| `index` | in the index |
| `used` | used in a call by Ableton's own scripts |
| `documented` | on Structure Void's pages |
| `python` | Python's own |
| `unknown` | none of these |

**For a list,** each name is one of these:

- a class;
- `Class.member`: own or inherited, with the class it comes from. The answer says
  `not_a_member` when the class lacks it.
- a bare name: in which classes it is defined.

A short class name stands for every class of that name; the framework's newest generation
comes first. A member found on a model of a `Live` class (the Push 3 helper's `live_model`) is
marked `proxy_of`.

The exit code is 1 when a name is unknown.

## The Python API

```python
from ableton_remote_script_mcp import api

api.lookup("SessionRingComponent", "12.4.16", members=["set_offsets"])
api.search("session ring", kind="class", offset=20)
api.outline("APC_mini_mk2", section="mappings")
api.validate("my_script")
api.check_names(names=["Song.tracks", "Component.set_enabled"])
api.list_builds()
api.diff("12.4.16", "12.5", under="ableton.v3")  # both builds indexed
```

Every function takes `index_dir` (default: the folder `build-index` writes to), `full` and
`max_tokens`. A build stays loaded while its index files don't change. Calling the functions
directly is about 0.05 s per lookup; a CLI call is 0.1–0.15 s, so give `check-names` many
names in one call.

## The MCP server

`ableton-remote-script-mcp mcp` runs the MCP server over stdio. It is written with the
official MCP SDK, and `uvx` starts it without an install. For Claude Code, from a clone of the
repository:

```sh
claude mcp add ableton-remote-script -- uvx --from /path/to/ableton-remote-script-mcp ableton-remote-script-mcp mcp
```

The server reads the same index as the CLI, so build it first (`build-index`). Every tool is
read-only:

| Tool | CLI command |
|---|---|
| `search_api` | `search` |
| `get_class` | `lookup class` |
| `check_names` | `check-names` |
| `outline_reference_script` | `outline` |
| `validate_script` | `validate` |
| `diff_builds` | `diff` |
| `list_builds` | `list builds` |

Each tool returns the answer as structured content, and as compact JSON in its text. Each tool's
description has one worked example.

## Changes to the answer

A change to an answer's shape raises `answer_version`, and gets a line here.

- **1** (2026-11-18): the first version. It adds `answer_version`, `cut`, and:
  - for `search`: `offset` and `next_offset`;
  - for `outline`: `sections`, and with a section, `section` and `offset`;
  - for `lookup`: `missing_members`;
  - for `validate`: `counts`.
