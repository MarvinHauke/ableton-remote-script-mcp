# Develop

How to work on the project itself.

## Setup

```sh
uv sync                 # Python 3.11 and the dev tools
uv run pytest           # the tests
```

Tests that need an installed Live (marked `local_live`) skip themselves when it is absent. All
other tests run on small Remote Scripts and a hand-written index that live in `tests/`, so they
need no Live and contain nothing of Ableton's.

## Docs

The site is built with [Zensical](https://zensical.org) from `mkdocs.yml` and `docs/`:

```sh
scripts/docs-check.sh          # what CI runs: the CLI reference is current, the site builds strictly
uv run zensical serve          # preview at http://localhost:8000
```

The [CLI reference](reference/cli.md) is generated from the command's argument parser. Change a
help text in the code, then run `uv run python scripts/gen_cli_reference.py`; never edit the page
by hand.

## Rules for anything published

- Nothing extracted from Live in the repository or on this site: no `.pyc` files, no decompiled
  code, no index data, no output from a real index. Examples come from the test fixtures.
- Structure Void's documentation is CC BY-NC-SA 4.0: link to it and write in your own words.
