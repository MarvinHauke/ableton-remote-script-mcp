"""The CLI reference generator: `--check` passes on a current page and fails on a stale one."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "gen_cli_reference.py"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT, check=False)


def test_check_passes_on_a_freshly_written_page(tmp_path):
    page = tmp_path / "cli.md"
    assert run("--page", str(page)).returncode == 0
    assert "## `outline`" in page.read_text()
    assert run("--check", "--page", str(page)).returncode == 0


def test_check_fails_on_a_stale_page_and_leaves_it_alone(tmp_path):
    page = tmp_path / "cli.md"
    run("--page", str(page))
    stale = page.read_text().replace("Print the query core's answer as JSON.", "Print JSON.")
    page.write_text(stale)
    result = run("--check", "--page", str(page))
    assert result.returncode == 1
    assert "is stale" in result.stderr
    assert page.read_text() == stale


def test_committed_page_is_current():
    assert run("--check").returncode == 0


def test_page_shows_no_home_path(tmp_path):
    page = tmp_path / "cli.md"
    run("--page", str(page))
    assert str(Path.home()) not in page.read_text()
