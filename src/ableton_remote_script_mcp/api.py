"""The stable Python API (plan 0001 step 11, Decision 49 Q4 and Q10).

Six functions, `lookup`, `search`, `outline`, `validate`, `check_names` and `list_builds`, plus
`diff`. They return the same answers as the CLI's `--json` and the MCP tools: plain dicts with
a `status` ("ok", "not_found", "folder_missing", "refused", "index_missing"), an `answer_version` and, when the answer was
larger than about `max_tokens`, a `cut` note saying what was left out and how to get it
(`answers.py`). `full=True` gives the whole answer.

    from ableton_remote_script_mcp import api
    api.lookup("SessionRingComponent", members=["set_offsets"])
    api.check_names(names=["Component.set_enabled", "song.tracks"], build="12.4.16")

`index_dir` defaults to the one `build-index` writes (`$ABLETON_REMOTE_SCRIPT_INDEX` or
`~/.local/share/ableton-remote-script-mcp/index`). A loaded build stays in memory while its
files don't change.
"""

from __future__ import annotations

from pathlib import Path

from . import query
from .answers import DEFAULT_MAX_TOKENS, FULL_HINT, bounded, cut_how, tokens
from .index_store import default_index_dir

__all__ = ["OUTLINE_SECTIONS", "check_names", "diff", "list_builds", "lookup", "outline", "search", "validate"]

OUTLINE_SECTIONS = ("modules", "create_instance", "classes", "specification", "component_map", "mappings",
                    "unknown_components", "elements", "components", "layers")

# What the cap may cut in each answer (plan 0001 Decision 62), with the key that names a list's
# records (its `cut` entry then lists the dropped names) or None. Nothing else is ever cut.
_MEMBERS = {"all_members": None, "members": None, "documented": None}
LOOKUP_CUTS = {"classes": "qualified_name", "documented": "qualified_name",
               **{f"classes[].{k}": v for k, v in _MEMBERS.items()}}
SEARCH_CUTS = {"results": "qualified_name"}
_SECTION_INNER_LIST = {"specification": "fields", "mappings": "mappings"}  # a record: cut the list inside it
OUTLINE_CUTS = {**dict.fromkeys(s for s in OUTLINE_SECTIONS if s not in _SECTION_INNER_LIST),
                **{f"{s}.{inner}": None for s, inner in _SECTION_INNER_LIST.items()}, "classes[].members": None}
VALIDATE_CUTS = {"findings": None, "not_checked": None}
CHECK_NAMES_CUTS = {"names": "name", "names[].classes": None, "unknown": None, "used_only": None,
                    "kwargs_unknown": None, "broken": None, "not_read": None}
LIST_BUILDS_CUTS = {"builds": "live_build", "installed_not_indexed": None}
_CHANGES = ("added", "removed", "changed")
DIFF_CUTS = {f"{what}.{change}": None for what in ("packages", "modules", "classes") for change in _CHANGES} | {
    f"{what}.changed[].members.{change}": None for what in ("modules", "classes") for change in _CHANGES}


def _dir(index_dir) -> Path:
    return Path(index_dir) if index_dir is not None else default_index_dir()


def _cap(full: bool, max_tokens: int | None) -> int | None:
    return None if full else max_tokens


def lookup(name: str, build: str | None = None, *, own: bool = False, members: list[str] | None = None,
           full: bool = False, max_tokens: int | None = DEFAULT_MAX_TOKENS, index_dir=None) -> dict:
    """A class by short, qualified or re-exported name, with its bases, MRO and members (own and
    inherited, each with its `origin`). `own` keeps only the class's own members in
    `all_members`; `members` only the named ones (and lists those it has not in `missing_members`)."""
    answer = query.get_class(name, _dir(index_dir), build)
    for c in answer.get("classes", []):
        if own:
            c["all_members"] = {n: m for n, m in c["all_members"].items() if m.get("origin") == c["qualified_name"]}
        if members is not None:
            wanted = list(dict.fromkeys(members))
            c["all_members"] = {n: c["all_members"][n] for n in wanted if n in c["all_members"]}
            c["members"] = {n: m for n, m in c["members"].items() if n in wanted}
            c["missing_members"] = [n for n in wanted if n not in c["all_members"]]
    return bounded(answer, _cap(full, max_tokens), collections=LOOKUP_CUTS,
                   how=f"{FULL_HINT}; members=[...] asks for named members only, own=true for the class's own")


def search(text: str, build: str | None = None, *, kind: str | None = None, limit: int = 20, offset: int = 0,
           full: bool = False, max_tokens: int | None = DEFAULT_MAX_TOKENS, index_dir=None) -> dict:
    """Classes, modules and members by name or words, best first; `next_offset` is the next page."""
    answer = bounded(query.search(text, _dir(index_dir), build, kind, limit, offset), _cap(full, max_tokens),
                     collections=SEARCH_CUTS)
    cut = answer.get("cut")
    if cut and any(f["field"] == "results" for f in cut["fields"]):
        kept = next(f["kept"] for f in cut["fields"] if f["field"] == "results")
        answer["next_offset"] = answer["offset"] + kept
        cut["how"] = cut_how(cut["fields"], f"offset={answer['next_offset']} gives the next results "
                             f"(CLI: --offset); {FULL_HINT}")
    return answer


def _sections(answer: dict) -> dict:
    def count(v):
        return len(v) if isinstance(v, list | dict) else (0 if v is None else 1)
    return {s: count(answer.get(s)) for s in OUTLINE_SECTIONS if s in answer}


def outline(script: str, build: str | None = None, *, section: str | None = None, offset: int = 0,
            full: bool = False, max_tokens: int | None = DEFAULT_MAX_TOKENS, index_dir=None) -> dict:
    """The outline of one of Ableton's scripts, or of a script folder (a path), by section.

    `sections` counts the items of each section. An answer over the cap keeps the sections
    that fit, in order, and names the others in `cut`; `section` asks for one of them, and
    `offset` for its next items when it is a long list."""
    if section is not None and section not in OUTLINE_SECTIONS:
        return bounded({"status": "refused", "message": f"no outline section {section!r}; the sections are "
                        + ", ".join(OUTLINE_SECTIONS)}, None)
    answer = query.outline_script(script, _dir(index_dir), build)
    if answer["status"] != "ok":
        return bounded(answer, None)
    answer["sections"] = _sections(answer)
    limit = _cap(full, max_tokens)
    if section is not None:
        value = answer[section]
        if isinstance(value, list) and offset:
            value = value[offset:]
        head = {k: v for k, v in answer.items() if k not in OUTLINE_SECTIONS}
        out = bounded({**head, "section": section, "offset": offset, section: value}, limit, collections=OUTLINE_CUTS)
        cut = out.get("cut")
        if cut and any(f["field"] == section for f in cut["fields"]) and isinstance(value, list):
            kept = next(f["kept"] for f in cut["fields"] if f["field"] == section)
            out["next_offset"] = offset + kept
            cut["how"] = f"section={section!r} offset={out['next_offset']} gives the next items (CLI: --offset)"
        return out
    if limit is None or tokens(answer) <= limit:
        return bounded(answer, limit, collections=OUTLINE_CUTS)
    head = {k: v for k, v in answer.items() if k not in OUTLINE_SECTIONS}
    room = limit - tokens(head) - 60 * len(OUTLINE_SECTIONS)
    out, left_out = dict(head), []
    for s in OUTLINE_SECTIONS:
        if s not in answer:
            continue
        size = tokens({s: answer[s]})
        if size <= room:
            out[s] = answer[s]
            room -= size
        else:
            out[s] = [] if isinstance(answer[s], list) else None
            left_out.append({"field": s, "kept": 0, "total": answer["sections"][s]})
    out = bounded(out, limit, collections=OUTLINE_CUTS)
    cut = out.setdefault("cut", {"max_tokens": limit, "fields": []})
    cut["fields"] = left_out + cut["fields"]
    cut["how"] = (f"section=<name> gives one section, e.g. section={left_out[0]['field']!r} "
                  f"(CLI: --section); {FULL_HINT}") if left_out else cut.get("how", FULL_HINT)
    return out


def validate(folder: str | Path, build: str | None = None, *, full: bool = False,
             max_tokens: int | None = DEFAULT_MAX_TOKENS, index_dir=None) -> dict:
    """Static findings for a Remote Script folder: each with a file, a line, a rule, a severity,
    a message and a fix. `counts` holds the whole answer's numbers, also when it is cut."""
    answer = query.validate_script(Path(folder), _dir(index_dir), build)
    if answer["status"] == "ok":
        answer["counts"] = {"findings": len(answer["findings"]), "not_checked": len(answer["not_checked"]),
                            "errors": sum(f["severity"] == "error" for f in answer["findings"])}
    return bounded(answer, _cap(full, max_tokens), collections=VALIDATE_CUTS)


def check_names(folder: str | Path | None = None, names: list[str] | None = None, build: str | None = None, *,
                full: bool = False, max_tokens: int | None = DEFAULT_MAX_TOKENS, index_dir=None) -> dict:
    """Where each API name is known in one build, for a script folder or a list of names
    (`Class`, `Class.member`, a bare `name`): facts with their confidence, not errors."""
    answer = query.check_names(_dir(index_dir), build, Path(folder) if folder is not None else None, names)
    return bounded(answer, _cap(full, max_tokens), collections=CHECK_NAMES_CUTS)


def list_builds(*, full: bool = False, max_tokens: int | None = DEFAULT_MAX_TOKENS, index_dir=None,
                installs=None) -> dict:
    """The indexed Live builds, newest first, and the installed builds with no index; the
    default build is marked `default` (with `default_from`), each beta `beta`."""
    if installs is None:
        from .live_install import find_installs
        installs = find_installs()
    return bounded(query.list_builds(_dir(index_dir), installs), _cap(full, max_tokens), collections=LIST_BUILDS_CUTS)


def diff(from_build: str, to_build: str, *, under: str | None = None, full: bool = False,
         max_tokens: int | None = DEFAULT_MAX_TOKENS, index_dir=None) -> dict:
    """What changed between two builds: packages, modules, classes and members (`diff.py`)."""
    from .diff import diff_builds

    return bounded(diff_builds(from_build, to_build, _dir(index_dir), under), _cap(full, max_tokens),
                   how=f"under=<package or module> narrows the diff (CLI: --under); {FULL_HINT}",
                   collections=DIFF_CUTS)
