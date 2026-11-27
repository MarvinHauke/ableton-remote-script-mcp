"""The answer core's version and its size caps (plan 0001 step 11, Decision 49 Q5 and Q10).

The CLI's `--json`, the Python API (`api.py`) and the MCP tools return the same answers. Each
answer carries `answer_version`; a change to the shape of an answer raises it and gets a line
in `docs/answers.md`.

An answer is capped at about `DEFAULT_MAX_TOKENS` tokens (estimated as compact JSON / 4). The
cap removes nothing from the index: it keeps the first items of the collections the answer
declares (plan 0001 Decision 62), never a record's own fields, and says in `cut` what it left
out and how to get the rest (`full`, or a narrower question such as a page, a section or named
members). `max_tokens=None` gives the whole answer.
"""

from __future__ import annotations

import copy
import json
import re

from .live_install import is_beta

ANSWER_VERSION = 4
DEFAULT_MAX_TOKENS = 4000
CHARS_PER_TOKEN = 4
_NOTE_TOKENS = 40  # room left for each `cut` entry
FULL_HINT = "full=true gives the whole answer (CLI: --full)"
DROPPED_LISTED = 50  # names of dropped records a `cut` entry lists; `more` counts the rest
DROPPED_HINT = "each name in `dropped` can be asked for on its own, by its qualified name"


def tokens(value) -> int:
    """An estimate: the compact JSON's length / 4."""
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)) // CHARS_PER_TOKEN + 1


def _containers(value, path: str = ""):
    """(path, list or dict) for every list and dict with two or more items below the answer."""
    if isinstance(value, dict):
        for k, v in value.items():
            p = f"{path}.{k}" if path else str(k)
            if isinstance(v, list | dict):
                if len(v) > 1:
                    yield p, v
                yield from _containers(v, p)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            if isinstance(v, list | dict):
                p = f"{path}[{i}]"
                if len(v) > 1:
                    yield p, v
                yield from _containers(v, p)


def _replace(answer: dict, path: str, new) -> None:
    parts: list = []
    for chunk in path.split("."):
        name, _, rest = chunk.partition("[")
        parts.append(name)
        parts += [int(i) for i in rest.rstrip("]").split("][")] if rest else []
    target = answer
    for p in parts[:-1]:
        target = target[p]
    target[parts[-1]] = new


def _first(container, k: int):
    if isinstance(container, dict):
        return dict(list(container.items())[:k])
    return container[:k]


def stamp(answer: dict) -> dict:
    """The answer with its version, and `beta: true` when its facts come from a beta build
    (plan 0001 Decision 63): worked out from the build's name, so a release answer has no such
    field and nothing stored ever needs it removed."""
    builds = [answer.get(k) for k in ("live_build", "from", "to")]
    beta = {"beta": True} if any(isinstance(b, str) and is_beta(b) for b in builds) else {}
    return {"answer_version": ANSWER_VERSION, **answer, **beta}


def _pattern(path: str) -> str:
    """`classes[0].all_members` -> `classes[].all_members`, the form a collection is declared in."""
    return re.sub(r"\[\d+\]", "[]", path)


def bounded(answer: dict, max_tokens: int | None = DEFAULT_MAX_TOKENS, how: str | None = None,
            collections: dict[str, str | None] | None = None) -> dict:
    """The answer, stamped with its version and cut to about `max_tokens`.

    Only the `collections` are cut: paths like `results` or `classes[].all_members`, each with
    the key that names its records (`qualified_name`) or None. Repeatedly the largest of them
    keeps its first items, as many as fit; a list keeps at least its first record, so the next
    cut may go inside it. `cut` lists each one with `kept` and `total`, a named list the names
    it dropped (`dropped`, at most `DROPPED_LISTED`, and `more`; a record without a name is
    only counted in `total`), and `how` says how to get the
    rest. Nothing else in the answer is ever cut, so it may stay over the cap.
    """
    answer = stamp(answer)
    if max_tokens is None or not collections or tokens(answer) <= max_tokens:
        return answer
    answer = copy.deepcopy(answer)  # the cut replaces lists inside records: never the caller's
    cut: list[dict] = []
    for _ in range(50):
        size = tokens(answer)  # with the note so far: its dropped names count
        if size <= max_tokens:
            break
        candidates = [(tokens(c), p, c) for p, c in _containers(answer) if _pattern(p) in collections]
        if not candidates:
            break
        own, path, container = max(candidates, key=lambda t: t[0])
        is_map = isinstance(container, dict)
        items = list(container.items()) if is_map else list(container)
        name_key = collections[_pattern(path)]
        names = [i.get(name_key) if isinstance(i, dict) else None for i in items] if name_key else []
        room = tokens(names[1:1 + DROPPED_LISTED]) if name_key else 0  # at most this many names get listed
        budget = max_tokens - (size - own) - _NOTE_TOKENS - room
        kept, used = 0, 2
        for item in items:
            used += tokens(dict([item]) if is_map else item)
            if used > budget:
                break
            kept += 1
        kept = min(kept, len(items) - 1) if is_map else max(1, min(kept, len(items) - 1))
        _replace(answer, path, _first(container, kept))
        earlier = next((c for c in cut if c["field"] == path), None)
        if earlier:  # cut again: the total stays the answer's
            earlier["kept"] = kept
            if name_key:
                earlier["names"] = names[kept:] + earlier["names"]
        else:
            cut.append({"field": path, "kept": kept, "total": len(items), **({"names": names[kept:]} if name_key else {})})
        answer["cut"] = _note(cut, max_tokens, how)
    return answer


def _note(cut: list[dict], max_tokens: int, how: str | None) -> dict:
    """The `cut` note: each cut collection, with at most `DROPPED_LISTED` of its dropped names."""
    fields = []
    for c in cut:
        entry = {k: v for k, v in c.items() if k != "names"}
        names = [n for n in c.get("names", []) if isinstance(n, str)]
        if names:
            entry["dropped"] = names[:DROPPED_LISTED]
            if len(names) > DROPPED_LISTED:
                entry["more"] = len(names) - DROPPED_LISTED
        fields.append(entry)
    return {"max_tokens": max_tokens, "fields": fields, "how": cut_how(fields, how)}


def cut_how(fields: list[dict], how: str | None = None) -> str:
    """The `cut` note's `how`: `how` (default: ask for the whole answer), and when a field names
    dropped records, that each can be asked for on its own."""
    hint = how or FULL_HINT
    return f"{hint}; {DROPPED_HINT}" if any("dropped" in f for f in fields) else hint
