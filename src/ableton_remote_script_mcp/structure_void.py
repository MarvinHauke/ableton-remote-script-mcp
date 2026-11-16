"""Structure Void's runtime pages of the `Live` module, as a `documented` source (plan 0001
Decisions 23 and 45).

midiremotescripts.structure-void.com publishes one "runtime" page per `Live` module (for Live
12: `reference/live12/Live.Clip.runtime/` …), introspected inside an unstated Live 12.x. Each
page lists the module's classes with their bases, properties, methods (Boost.Python signatures
with argument types, including the `add_…_listener` methods) and enum values, and the module's
functions. This reads those pages into a local JSON document next to the index:
`structure-void-live<N>.json`. The pages are CC BY-NC-SA 4.0: the fetched pages and the
document stay on this machine, like the index, and every fact names its page.

The `View` classes (`Song.View`, `Clip.View`) appear only by name; their members are not on
the pages. The Push 3 helper's model has them.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

SITE = "https://midiremotescripts.structure-void.com"
LICENCE = "CC BY-NC-SA 4.0"
USER_AGENT = "ableton-remote-script-mcp (local API index builder)"
_RUNTIME_URL = re.compile(r"/reference/live(\d+)/(Live\.[A-Za-z0-9_]+)\.runtime/$")
_HEADING = re.compile(r"<h([2-5])\b[^>]*>(.*?)</h\1>", re.DOTALL)
_ITEM = re.compile(r"<li>(.*?)</li>", re.DOTALL)
_CLASS = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)")
_NAME = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)")


def document_path(index_dir: Path, live: str) -> Path:
    return Path(index_dir) / f"structure-void-live{live}.json"


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("¶", "").strip()


def _first_sentence(text: str) -> str | None:
    text = " ".join(text.split())
    if not text:
        return None
    end = text.find(". ")
    return text if end < 0 else text[: end + 1]


def parse_page(page: str, module: str, url: str) -> dict:
    """{"classes": {key: class}, "functions": {name: function}} of one runtime page."""
    start, end = page.find("<article"), page.find("</article>")
    article = page[start:end] if start >= 0 else page
    classes: dict[str, dict] = {}
    functions: dict[str, dict] = {}
    section = None  # "classes" | "functions"
    cls = None
    part = None  # "properties" | "methods" | "attributes"
    heads = list(_HEADING.finditer(article))
    for i, h in enumerate(heads):
        level, title = int(h[1]), _text(h[2])
        body = article[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(article)]
        if level == 2:
            section, cls, part = title.lower(), None, None
        elif level == 3 and section == "classes":
            match = _CLASS.match(title)
            if not match:
                cls = None
                continue
            name, base = match[1], match[2].strip()
            kind = {"enum": "enum", "instance": "value class"}.get(base, "class")
            cls = classes[f"{module}.{name}"] = {
                "name": name, "module": module, "bases": [] if base in ("enum", "instance") else [base],
                "kind": kind, "url": url, "members": {}}
            doc = _first_sentence(_text(body.split("<h", 1)[0]))
            if doc:
                cls["doc"] = doc
            part = None
        elif level == 3 and section == "functions":
            match = _NAME.match(title)
            if match:
                functions[match[1]] = {"kind": "function", **_signature(body, match[1])}
        elif level == 4 and cls is not None:
            part = title.lower()
            if part in ("properties", "attributes"):
                for item in _ITEM.findall(body):
                    _member(cls, part, _text(item))
        elif level == 5 and cls is not None and part == "methods":
            match = _NAME.match(title)
            if not match or match[1].startswith("__") or cls["kind"] == "enum":
                continue
            name = match[1]
            info = _signature(body, name)
            kind = "class" if name[0].isupper() and "signature" not in info else "method"
            cls["members"][name] = {"kind": kind, **info}
    return {"classes": classes, "functions": functions}


def _member(cls: dict, part: str, text: str) -> None:
    match = _NAME.match(text)
    if not match or match[1].startswith("_"):
        return
    name, rest = match[1], text[len(match[1]):].strip()
    if part == "attributes":
        # an enum's values read `q_bar = Song.Quantization.q_bar`; the rest is int's own
        value = rest[1:].split(" - ", 1)[0].strip() if rest.startswith("=") else ""
        if cls["kind"] == "enum" and value.endswith(f".{cls['name']}.{name}"):
            cls["members"][name] = {"kind": "enum value"}
        elif cls["kind"] != "enum":
            cls["members"][name] = {"kind": "attribute"}
        return
    entry = {"kind": "property"}
    doc = _first_sentence(rest[1:].strip()) if rest.startswith("-") else None
    if doc:
        entry["doc"] = doc
    cls["members"][name] = entry


def _signature(body: str, name: str) -> dict:
    """The Boost.Python signature line of a method or function (`name( (Clip)arg1, …) -> T`)
    and the first sentence of its description."""
    paragraph = re.search(r"<p>(.*?)</p>", body, re.DOTALL)
    text = _text(paragraph[1]) if paragraph else ""
    out: dict = {}
    if text.startswith(name + "("):
        head, _, doc = text.partition(" :")
        out["signature"] = " ".join(head.split())
        text = doc
    doc = _first_sentence(text)
    if doc:
        out["doc"] = doc
    return out


def runtime_urls(sitemap: str, live: str) -> list[tuple[str, str]]:
    """(module, url) of every runtime page of one Live version in the site's sitemap."""
    out = []
    for url in re.findall(r"<loc>([^<]+)</loc>", sitemap):
        match = _RUNTIME_URL.search(url)
        if match and match[1] == live:
            out.append((match[2], url))
    return sorted(out)


def _get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def import_pages(index_dir: Path, live: str = "12", refresh: bool = False, fetch=_get,
                 delay: float = 0.5, log=print) -> dict:
    """Fetch (or reuse) the runtime pages of one Live version and write the document."""
    cache = Path(index_dir) / "structure-void" / f"live{live}"
    cache.mkdir(parents=True, exist_ok=True)
    pages = runtime_urls(fetch(f"{SITE}/sitemap.xml"), live)
    if not pages:
        raise ValueError(f"the sitemap of {SITE} lists no runtime pages for Live {live}")
    classes: dict[str, dict] = {}
    functions: dict[str, dict] = {}
    for module, url in pages:
        path = cache / f"{module}.html"
        if refresh or not path.is_file():
            path.write_text(fetch(url), encoding="utf-8")
            time.sleep(delay)
        parsed = parse_page(path.read_text(encoding="utf-8"), module, url)
        classes.update(parsed["classes"])
        for name, f in parsed["functions"].items():
            functions[f"{module}.{name}"] = {**f, "url": url}
    doc = {
        "source": "Structure Void, Live Object Model & framework reference (runtime pages)",
        "site": SITE, "licence": LICENCE, "live": live,
        "covers": f"an unstated Live {live}.x build", "confidence": "documented",
        "fetched": datetime.now(UTC).isoformat(timespec="seconds"),
        "pages": len(pages), "classes": dict(sorted(classes.items())), "functions": dict(sorted(functions.items())),
    }
    out = document_path(index_dir, live)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"wrote {out}: {len(classes)} classes, {sum(len(c['members']) for c in classes.values())} members, "
        f"{len(functions)} functions from {len(pages)} pages")
    return doc


def load_document(index_dir: Path, live: str) -> dict | None:
    try:
        return json.loads(document_path(index_dir, live).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def live_major(live_build: str) -> str:
    return re.match(r"\d+", live_build)[0]
