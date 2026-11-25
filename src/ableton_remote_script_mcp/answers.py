"""The answer core's version and its size caps (plan 0001 step 11, Decision 49 Q5 and Q10).

The CLI's `--json`, the Python API (`api.py`) and the MCP tools return the same answers. Each
answer carries `answer_version`; a change to the shape of an answer raises it and gets a line
in `docs/answers.md`.

An answer is capped at about `DEFAULT_MAX_TOKENS` tokens (estimated as compact JSON / 4). The
cap removes nothing from the index: it keeps the first items of the largest lists and maps of
the answer, and says in `cut` what it left out and how to get the rest (`full`, or a narrower
question such as a page, a section or named members). `max_tokens=None` gives the whole answer.
"""

from __future__ import annotations

import json

ANSWER_VERSION = 2
DEFAULT_MAX_TOKENS = 4000
CHARS_PER_TOKEN = 4
_NOTE_TOKENS = 40  # room left for each `cut` entry
FULL_HINT = "full=true gives the whole answer (CLI: --full)"


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
    return {"answer_version": ANSWER_VERSION, **answer}


def bounded(answer: dict, max_tokens: int | None = DEFAULT_MAX_TOKENS, how: str | None = None,
            protect: tuple[str, ...] = ()) -> dict:
    """The answer, stamped with its version and cut to about `max_tokens`.

    Repeatedly the largest list or map (by size, two or more items, not under a `protect`ed
    key) keeps its first items, as many as fit. `cut` lists each one with `kept` and `total`,
    and `how` says how to get the rest.
    """
    answer = stamp(answer)
    if max_tokens is None or tokens(answer) <= max_tokens:
        return answer
    cut: list[dict] = []
    for _ in range(50):
        size = tokens(answer)
        if size <= max_tokens:
            break
        candidates = [(tokens(c), p, c) for p, c in _containers(answer)
                      if p != "cut" and not any(p == k or p.startswith((k + ".", k + "["))
                                                for k in protect)]
        if not candidates:
            break
        own, path, container = max(candidates, key=lambda t: t[0])
        budget = max_tokens - (size - own) - _NOTE_TOKENS * (len(cut) + 1)
        items = list(container.items()) if isinstance(container, dict) else list(container)
        kept, used = 0, 2
        for item in items:
            used += tokens(dict([item]) if isinstance(container, dict) else item)
            if used > budget:
                break
            kept += 1
        if kept >= len(items):
            kept = len(items) - 1
        _replace(answer, path, _first(container, kept))
        earlier = next((c for c in cut if c["field"] == path), None)
        if earlier:  # cut again: the total stays the answer's
            earlier["kept"] = kept
        else:
            cut.append({"field": path, "kept": kept, "total": len(items)})
    answer["cut"] = {"max_tokens": max_tokens, "fields": cut, "how": how or FULL_HINT}
    return answer
