"""Score the scripts that a `claude plugin eval` run of the skill evals wrote (plan 0001 step 9a).

    uv run python scripts/eval_score.py <result.json> [--out <dir>] [--build 12.4.16]

The eval command (run with `--keep-temp --json <result.json>`) keeps each run's sandbox and
seals the folder the run worked in. For every run this opens the sealed folder, finds each Remote
Script folder the run wrote (an `__init__.py` that defines `create_instance`, other than the
input files it was given), and scores it with the validator and `eval_names.py`. The judge's
verdicts on the other graders are copied from the result; the verdicts of the graders about the
validator and unknown names are overwritten with these scores, since the judge cannot run either.

Writes `scores.json` and `scores.md` to `--out` (default: next to the result). With
`--remove-kept` it then copies each run's trace into `<out>/traces/` and deletes the kept
sandboxes, which hold traces with output of Live's `.pyc` files outside any ignored folder.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

from eval_names import check as check_names

from ableton_remote_script_mcp.index_store import (
    attach_statements,
    default_index_dir,
    indexed_builds,
    load_index,
    load_statements,
)
from ableton_remote_script_mcp.validator import validate_folder

REPO = Path(__file__).resolve().parent.parent
SKILL_DIR = str(REPO / "skills" / "ableton-remote-scripts")
CLI_NAME = "ableton-remote-script-mcp"  # also in the index copy's name in ~/.local/bin
SCRIPT_GRADERS = ("validator-clean", "no-unknown-names")  # scored here, not by the judge
EVALS = REPO / "skills" / "ableton-remote-scripts" / "evals"


def _repo_spellings() -> list[str]:
    spellings = [str(REPO)]
    try:
        rel = REPO.relative_to(Path.home())
        spellings += [f"~/{rel}", f"$HOME/{rel}", f"${{HOME}}/{rel}"]
    except ValueError:
        pass
    return spellings


def repo_reads(trace: Path, arm: str = "with") -> list[str]:
    """Tool calls a clean run would not make: this repo outside the skill's own folder (the
    example script, the plans, also as `~/…` or `$HOME/…`), the skill's `evals/` (the graders,
    the answer key), and in the run without the skill anything of this tool (the CLI, the index
    copy), which that run is not meant to know about."""
    hits = []
    spellings = _repo_spellings()
    evals = f"{SKILL_DIR}/evals"
    try:
        lines = trace.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return hits
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        for part in message.get("content", []) if isinstance(message.get("content"), list) else []:
            if isinstance(part, dict) and part.get("type") == "tool_use":
                text = json.dumps(part.get("input"))
                outside = text.replace(SKILL_DIR + "/evals", "<evals>").replace(SKILL_DIR, "")
                if (any(s in outside for s in spellings) or "examples/APC_mini_mk1" in text
                        or evals in text
                        or (arm == "without" and CLI_NAME in text)):
                    hits.append(f"{part.get('name')}: {text[:160]}")
    return hits


def unseal(kept: Path) -> Path | None:
    """The folder the run worked in, made readable (the eval command seals it with mode 000)."""
    sealed = kept / "sealed"
    if not kept.is_dir() or kept.is_symlink():
        return None
    os.chmod(kept, 0o700)
    if not sealed.exists() or sealed.is_symlink():
        return None
    os.chmod(sealed, 0o700)
    for root, dirs, _ in os.walk(sealed):
        for d in dirs:
            if not (Path(root) / d).is_symlink():  # a link planted in the sandbox points outside it
                os.chmod(Path(root) / d, 0o700)
    cwd = sealed / "home" / "cwd"
    return cwd if cwd.is_dir() else sealed


def script_folders(cwd: Path, inputs: set[str]) -> list[Path]:
    found = []
    for init in cwd.rglob("__init__.py"):
        if any(part.startswith(".") or part == "__pycache__" for part in init.relative_to(cwd).parts):
            continue
        if init.parent.name in inputs:
            continue
        try:
            if "def create_instance" in init.read_text(encoding="utf-8", errors="replace"):
                found.append(init.parent)
        except OSError:
            continue
    return sorted(found)


def score_run(run: dict, case: str, arm: str, index: dict, statements: dict | None, keep_to: Path) -> dict:
    inputs = {p.name for p in (EVALS / case / "files").glob("*")} if (EVALS / case / "files").is_dir() else set()
    out = {"error": run.get("error"), "turns": run.get("turns"), "seconds": run.get("durationSeconds"),
           "judge": {g.get("name", g.get("id", "?")): g.get("passed") for g in run.get("graders", [])}}
    trace = run.get("tracePath")
    out["repo_reads"] = repo_reads(Path(trace), arm) if trace else []
    cwd = unseal(Path(trace).parent.parent) if trace else None
    if cwd is None:
        out["scripts"] = []
        return out
    out["scripts"] = []
    for folder in script_folders(cwd, inputs):
        validated = validate_folder(folder.resolve(), index)
        names = check_names(folder.resolve(), index, statements)
        copy = keep_to / folder.name
        shutil.copytree(folder, copy, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        out["scripts"].append({
            "folder": folder.name, "copy": str(copy),
            "validator_findings": [f"{f['file']}:{f['line']} [{f['rule']}] {f['message']}"
                                   for f in validated["findings"]],
            "unknown_names": [f"{u['file']}:{u['line']} {u['expr']}" for u in names["unknown"]]
                             + [f"{k['file']}:{k['line']} {k['class'].split('.')[-1]}({k['keyword']}=…)"
                                for k in names["kwargs_unknown"]],
            "attribute_counts": names["attribute_counts"]})
    _overwrite_script_graders(out)
    return out


def _overwrite_script_graders(out: dict) -> None:
    """The judge can run neither the validator nor the name check: put the computed verdict in."""
    if not out["scripts"]:
        return
    computed = {"validator-clean": not any(s["validator_findings"] for s in out["scripts"]),
                "no-unknown-names": not any(s["unknown_names"] for s in out["scripts"])}
    for name in out["judge"]:
        for grader, passed in computed.items():
            if grader in name:
                out["judge"][name] = passed


def kept_sandbox(trace: Path) -> Path | None:
    """The sandbox `--keep-temp` left for a run (`<tmp>/e-*/out/trace.jsonl`), or None when the
    trace is anywhere else: only such a folder may be deleted."""
    kept = trace.parent.parent
    tmp_roots = {Path(tempfile.gettempdir()).resolve(), Path("/tmp").resolve(), Path("/private/tmp")}
    if kept.name.startswith("e-") and kept.resolve().parent in tmp_roots and not kept.is_symlink():
        return kept
    return None


def remove_kept(result: dict, out_dir: Path) -> list[str]:
    """Copy each run's trace into `<out>/traces/` and delete its kept sandbox."""
    removed = []
    for case in result["cases"]:
        name = case.get("name") or case.get("id")
        for arm, runs in case["arms"].items():
            for i, run in enumerate(runs, 1):
                trace = Path(run["tracePath"]) if run.get("tracePath") else None
                kept = kept_sandbox(trace) if trace else None
                if kept is None or not kept.exists():
                    continue
                if trace.is_file():
                    dest = out_dir / "traces" / name / arm / f"run-{i}.jsonl"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(trace, dest)
                for root, dirs, files in os.walk(kept):
                    for entry in dirs + files:
                        path = Path(root) / entry
                        if not path.is_symlink():
                            os.chmod(path, 0o700)
                shutil.rmtree(kept)
                removed.append(str(kept))
    return removed


def summarize(scores: dict) -> str:
    lines = [f"# Skill evals against Live {scores['live_build']}", "",
             "| case | arm | runs | scripts | validator findings (mean) | unknown names (mean) | judge pass rate |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for case, arms in scores["cases"].items():
        for arm, runs in arms.items():
            v = [sum(len(s["validator_findings"]) for s in r["scripts"]) for r in runs if r["scripts"]]
            u = [sum(len(s["unknown_names"]) for s in r["scripts"]) for r in runs if r["scripts"]]
            judged = [p for r in runs for name, p in r["judge"].items()
                      if p is not None and not any(g in name for g in SCRIPT_GRADERS)]
            rate = f"{sum(judged) / len(judged):.0%}" if judged else "–"
            lines.append(f"| {case} | {arm} | {len(runs)} | {sum(len(r['scripts']) for r in runs)} | "
                         f"{statistics.mean(v) if v else '–'} | {statistics.mean(u) if u else '–'} | {rate} |")
    lines += ["", "Runs that wrote no script count in `runs` but not in the means. Unknown names are",
              "candidates: read each one (`scores.json`) before calling it invented.", ""]
    for case, arms in scores["cases"].items():
        for arm, runs in arms.items():
            for i, r in enumerate(runs, 1):
                head = f"- {case} / {arm} / run {i}"
                if r["error"]:
                    lines.append(f"{head}: error {r['error']}")
                    continue
                if not r["scripts"]:
                    lines.append(f"{head}: no script folder")
                if r.get("repo_reads"):
                    lines.append(f"{head}: read the repo outside the skill ({len(r['repo_reads'])} calls), not clean")
                for s in r["scripts"]:
                    lines.append(f"{head}: `{s['folder']}`, {len(s['validator_findings'])} findings, "
                                 f"unknown: {', '.join(s['unknown_names']) or 'none'}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("result", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--build", default="12.4.16", help="Live build (default: 12.4.16, plan step 9a)")
    parser.add_argument("--remove-kept", action="store_true",
                        help="after scoring, keep the traces in <out>/traces and delete the kept sandboxes")
    parser.add_argument("--index-dir", type=Path, default=default_index_dir())
    args = parser.parse_args(argv)
    result = json.loads(args.result.read_text())
    out_dir = args.out or args.result.parent
    builds = indexed_builds(args.index_dir)
    build = args.build
    if build not in builds:
        print(f"no index for Live {build} in {args.index_dir}", file=sys.stderr)
        return 2
    index = load_index(args.index_dir, build)
    statements = load_statements(args.index_dir, index)
    if statements:
        attach_statements(index, statements)
    scores = {"live_build": build, "result": str(args.result), "cases": {}}
    for case in result["cases"]:
        name = case.get("name") or case.get("id")
        for arm, runs in case["arms"].items():
            scores["cases"].setdefault(name, {})[arm] = [
                score_run(run, name, arm, index, statements, out_dir / "scripts" / name / arm / f"run-{i}")
                for i, run in enumerate(runs, 1)]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scores.json").write_text(json.dumps(scores, indent=2))
    (out_dir / "scores.md").write_text(summarize(scores))
    print(summarize(scores))
    if args.remove_kept:
        removed = remove_kept(result, out_dir)
        print(f"removed {len(removed)} kept sandboxes; traces in {out_dir / 'traces'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
