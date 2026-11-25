"""The skill's `typecheck.sh`: basedpyright (or pyright) over a script with its project's stubs,
in standard mode whatever the project's own settings say (plan 0003 step 6; STATUS, the skill's
basedpyright check). The checkers here are fakes that print the config they were given."""

import json
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills" / "ableton-remote-scripts" / "scripts" / "typecheck.sh"

# a fake checker: prints its name and the config given with -p, exits with $FAKE_EXIT
FAKE = """#!/bin/sh
while [ $# -gt 0 ]; do [ "$1" = "-p" ] && config="$2"; shift; done
echo "checker: $(basename "$0")"
cat "$config"
exit "${FAKE_EXIT:-0}"
"""


def project(tmp_path, stubs=True):
    root = tmp_path / "My_Project"
    script = root / "My_Script"
    script.mkdir(parents=True)
    (script / "__init__.py").write_text("def create_instance(c_instance):\n    pass\n")
    (root / "pyrightconfig.json").write_text('{"typeCheckingMode": "strict"}')
    if stubs:
        (root / "stubs" / "ableton").mkdir(parents=True)
    return script


def checkers(tmp_path, *names):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name in names:
        (bin_dir / name).write_text(FAKE)
        (bin_dir / name).chmod(0o755)
    return bin_dir


def run(*args, bin_dir, exit_code=0):
    env = {**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin", "FAKE_EXIT": str(exit_code)}
    return subprocess.run([str(SCRIPT), *map(str, args)], capture_output=True, text=True, check=False, env=env)


def config_of(stdout):
    return json.loads(stdout[stdout.index("{"):])


def test_runs_basedpyright_in_standard_mode_with_the_projects_stubs(tmp_path):
    script = project(tmp_path)
    r = run(script, bin_dir=checkers(tmp_path, "basedpyright", "pyright"))
    assert r.returncode == 0, r.stderr
    assert "checker: basedpyright" in r.stdout
    config = config_of(r.stdout)
    assert config["typeCheckingMode"] == "standard"  # not the project's "strict"
    assert config["stubPath"] == str(script.parent / "stubs")
    assert config["include"] == [str(script)]
    assert config["pythonVersion"] == "3.11" and config["reportMissingModuleSource"] is False


def test_falls_back_to_pyright_and_passes_its_errors_on(tmp_path):
    r = run(project(tmp_path), bin_dir=checkers(tmp_path, "pyright"), exit_code=1)
    assert r.returncode == 1 and "checker: pyright" in r.stdout


def test_stubs_named_by_hand(tmp_path):
    script = project(tmp_path, stubs=False)
    elsewhere = tmp_path / "other_stubs"
    elsewhere.mkdir()
    r = run(script, "--stubs", elsewhere, bin_dir=checkers(tmp_path, "basedpyright"))
    assert r.returncode == 0 and config_of(r.stdout)["stubPath"] == str(elsewhere)


def test_without_stubs_it_says_what_to_ask_the_user(tmp_path):
    r = run(project(tmp_path, stubs=False), bin_dir=checkers(tmp_path, "basedpyright"))
    assert r.returncode == 3
    assert "build-stubs --build <build> --project" in r.stderr and "My_Project" in r.stderr


def test_without_a_checker_it_is_skipped(tmp_path):
    r = run(project(tmp_path), bin_dir=checkers(tmp_path))
    assert r.returncode == 4 and "skipped" in r.stderr


def test_a_missing_folder(tmp_path):
    assert run(tmp_path / "nope", bin_dir=checkers(tmp_path, "basedpyright")).returncode == 2


def test_stubs_without_a_value_stops(tmp_path):
    r = run(project(tmp_path), "--stubs", bin_dir=checkers(tmp_path, "basedpyright"))
    assert r.returncode == 2 and "--stubs needs a folder" in r.stderr


def test_the_checkers_own_failure_is_not_the_scripts(tmp_path):
    r = run(project(tmp_path), bin_dir=checkers(tmp_path, "basedpyright"), exit_code=3)
    assert r.returncode == 5 and "not an error in the script" in r.stderr


def test_a_path_with_a_space_and_a_quote(tmp_path):
    script = project(tmp_path / 'my "odd" folder')
    r = run(script, bin_dir=checkers(tmp_path, "basedpyright"))
    assert r.returncode == 0, r.stderr
    assert config_of(r.stdout)["include"] == [str(script)]
    r = run(project(tmp_path / "no stubs here", stubs=False), bin_dir=checkers(tmp_path, "basedpyright"))
    assert r.returncode == 3 and "--project '" in r.stderr
