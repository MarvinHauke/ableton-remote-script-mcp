# Answers, the API and the MCP server

The lookups answer in one shape, wherever you ask. The CLI's `--json`, the Python API and the
MCP tools return the same answer for the same question. The CLI's text output for people is
printed from that answer. Use the CLI with `--json` from code in any language, the Python
functions from Python, and the MCP tools from an MCP client.

## The answer

Each answer is a JSON object with:

- `status`:
  - `ok`;
  - `not_found`: no match (with a `message` that names the build);
  - `folder_missing`: no script folder, project folder or log file at that path;
  - `refused`: an input the tool won't use (an unknown section or kind, a folder it can't
    compile, a stubs folder with other files in it);
  - `index_missing` (with the command that builds the index).
- `answer_version`: the version of the answer's shape, now **3**.
- `live_build`: the build the facts come from. Without a build named, it is the default
  build: the one set with `default-build` (stored in the index folder, so never in a repo),
  else the newest indexed release, else, when only betas are indexed, the newest beta. A
  default that names a build with no index is refused (`index_missing`), never replaced.
- `beta`: `true` when that build is a beta (or, for `diff`, one of the two is). Release
  answers have no such field. Beta facts stay out of anything published. (`build-stubs` and
  `check-structure-void` print reports, not answers: their text says "(beta)", their JSON has
  no `beta`.)
- each fact's `confidence`:
  - `observed`: in that build's index;
  - `documented`: from Structure Void's pages, a secondary source.

### Size caps

An answer is capped at about 4,000 tokens, estimated as the compact JSON's length divided
by four. The cap removes nothing from the index. When an answer is larger, only the
collections the answer declares get cut: its classes and their member maps, its results, its
findings, its names, its outline sections, its diff lists. A record's own fields (a class's
`bases`, `mro`) are never cut. The largest collection keeps its first items, as many as fit; a
list keeps at least its first record, and the cut then goes inside it (that class's members).
A `cut` note says what was left out and how to get it:

```json
"cut": {"max_tokens": 4000,
        "fields": [{"field": "classes", "kept": 1, "total": 3,
                    "dropped": ["pkg.mod1.Thing", "pkg.mod2.Thing"]},
                   {"field": "classes[0].all_members", "kept": 40, "total": 300}],
        "how": "…; members=[...] asks for named members only, …; each name in `dropped` can be asked for on its own, by its qualified name"}
```

A list of named records (classes, search results, the names of `check_names`, builds) lists
the names it dropped in `dropped`, at most 50, and counts the rest in `more`. A cut member map
lists none: ask for the members you need.

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

### Exit codes

The CLI's exit code follows the answer's `status`: `ok` exits 0, or 1 when the answer has
something to act on (findings, unknown names, tracebacks); `not_found` exits 1; `folder_missing`
and `refused` exit 2; `index_missing` exits 3. A crash exits 5, never 1, so a script can tell a
bug from findings. The whole table is in the [CLI reference](reference/cli.md#exit-codes), and
the skill's scripts name the same codes.

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
| `own` | defined by the script, or built by its v3 Elements class |
| `index` | in the index |
| `used` | used in a call by Ableton's own scripts |
| `documented` | on Structure Void's pages |
| `python` | Python's own |
| `unknown` | none of these |

The names a v3 Elements class builds are read by compiling the script as Live's Python 3.11
does. When some can't be read (another Python, no source compiles, or names built from values
known only when the script runs), the answer's `not_read` says why, and an `unknown` name may
be one the Elements class builds. `outline` of a folder has a `not_read` of the same shape, a
list of reasons, for the files it couldn't read.

**For a list,** each name is one of these:

- a class;
- `Class.member`: own or inherited, with the class it comes from. The answer says
  `not_a_member` when the class lacks it.
- a bare name: in which classes it is defined.

A short class name stands for every class of that name, best first: a class at module level
before a nested one, then the framework's newest generation (a model of a `Live` class ranks
with it), then the class its package re-exports before another of that name. A member found
on a model of a `Live` class (the Push 3 helper's `live_model`) is marked `proxy_of`.

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
- **2** (2026-11-25, plan 0001 Decision 57): `check_names` of a folder counts the names its v3
  Elements class builds as `own`, and adds `not_read` (a list of reasons) when it couldn't
  read them.
- **3** (2026-11-26, plan 0001 Decision 61): two new statuses, `folder_missing` (no such
  folder; `not_found` now always means no match) and `refused`; one exit-code table for the
  CLI, and a crash exits 5. The cut (Decision 62) cuts only the collections an answer
  declares, keeps a list's first record, and names dropped records in `dropped` and `more`.
  The default build (Decision 63) is the setting or the newest release; `beta` marks a beta
  answer; `list_builds` marks `default` (with `default_from`) and each `beta`, and says in
  `default_problem` when the setting names a build with no index.
