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

## Skill evals

The skill's eval cases are in `skills/ableton-remote-scripts/evals/`, one folder each in
`/skill-creator`'s format (plan 0001 step 9a). A round runs every case with and without the skill
in `claude plugin eval`'s sandbox, then scores the scripts the runs wrote:

```sh
scripts/eval_run.sh <out dir>                          # all cases, 3 runs per arm
scripts/eval_run.sh <out dir> --case uc4-mixer-v3 --runs 1 --ablation none   # one quick run
```

- **What it needs:** an index built with `build-index`, and Python 3.12 at
  `/opt/homebrew/bin/python3.12` (or `EVAL_PYTHON`). The sandbox can read neither this repo nor
  `~/.local/share`, so for the length of the round the script puts a self-contained build of the
  CLI and a copy of the index into `~/.local/bin`, and removes them afterwards.
- **The scores:** `scores.md` and `scores.json` in `<out dir>` hold each run's validator
  findings and its unknown names (`scripts/eval_names.py`) against Live 12.4.16 (`EVAL_BUILD`
  to change it), and flag runs that read the repo or the skill's `evals/`, or that use the CLI
  without the skill.
- **Python versions:** the CLI inside the sandbox runs on Python 3.12, so its `validate` checks
  imports against 3.12's standard library, while the scoring runs on the project's 3.11. A
  script that imports a module only one of them has can score differently in the two places.
- **What is left afterwards:** each run's trace goes to `<out dir>/traces/`, and the sandboxes
  the eval command kept in the temp folder are deleted (they hold traces with output from Live's
  `.pyc` files). The out dir must be outside the repo or git-ignored; the script refuses
  anything else.
- **Billing:** the runs use the claude.ai login (`ANTHROPIC_API_KEY` is unset for them) and count
  against its usage limit; a full round of 18 runs costs about $16 at API prices. The report
  stays local.
- **Where the results go:** keep them in `skills/ableton-remote-scripts-workspace/`, which is
  git-ignored: they contain the generated scripts and traces.

## Rules for anything published

- Nothing extracted from Live in the repository or on this site: no `.pyc` files, no decompiled
  code, no index data, no output from a real index. Examples come from the test fixtures.
- Structure Void's documentation is CC BY-NC-SA 4.0: link to it and write in your own words.
