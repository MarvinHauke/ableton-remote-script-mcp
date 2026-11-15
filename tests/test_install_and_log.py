"""`install` and `log`, and the skill's scripts run as commands (the adapter smoke tests).

The Log.txt here is our own, written in the record format Live uses: one record per write, a
traceback split into fragments, an empty line after a fragment that ended a line.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from hand_index import OLD, write_hand_index
from test_validate import CLEAN_FRAMEWORK, write

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.live_log import find_log, read_log

SKILL = Path(__file__).parent.parent / "skills" / "ableton-remote-scripts"


def record(time, level, text):
    return f"2026-11-15T10:00:{time:09.6f}: {level}: {text}"


def traceback_records(time, script):
    """A traceback through `script`, written the way Live writes one: fragments, newlines as empty lines."""
    path = f"/Users/someone/Music/Ableton/User Library/Remote Scripts/{script}/__init__.py"
    parts = [("", False), ("Traceback (most recent call last):", True), ("", False),
             (f'  File "{path}", line 4, in create_instance', True), ("    ", False),
             ("return Surface(c_instance)", True), ("    ", False), (" ", False)]
    lines = []
    for i, (fragment, ends) in enumerate(parts):
        lines.append(record(time + i / 1000, "error", f"RemoteScriptError: {fragment}"))
        if ends:
            lines.append("")
    lines.append(record(time + 0.1, "error", "Last message repeated 2 time(s): RemoteScriptError:  "))
    lines.append(record(time + 0.1, "error", "RemoteScriptError: ^"))
    lines.append("")
    for fragment in ["NameError", ": ", "name 'Surface' is not defined"]:
        lines.append(record(time + 0.2, "error", f"RemoteScriptError: {fragment}"))
    lines.append("")
    return lines


LOG = [
    record(1, "info", "Started: Live 12.4.16 Build: 2026-01-01_0000000000"),
    *traceback_records(2, "My_Script"),
    record(3, "info", "RemoteScriptMessage: (My_Script) from the session before"),
    record(10, "info", "#######################################"),
    record(11, "info", "Started: Live 12.4.16 Build: 2026-01-01_0000000000"),
    record(12, "info", "AMidiIO: Midi Remote Scripts: "),
    '  MidiRemoteScript 1 [Control Surface="None" Input="None" Output="None"]',
    record(13, "info", "RemoteScriptMessage: (Other_Script) Initializing..."),
    record(14, "info", "RemoteScriptMessage: (My_Script) ready"),
    *traceback_records(20, "My_Script"),
    *traceback_records(30, "Other_Script"),
    record(40, "info", "Python: INFO:_Framework.ControlSurface:1 - LOG: (My_Script) ready"),
]

TRACEBACK = """\
Traceback (most recent call last):
  File "/Users/someone/Music/Ableton/User Library/Remote Scripts/My_Script/__init__.py", line 4, in create_instance
    return Surface(c_instance)
       ^
NameError: name 'Surface' is not defined"""


@pytest.fixture
def log(tmp_path):
    path = tmp_path / "prefs" / "Live 12.4.16" / "Log.txt"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(LOG) + "\n")
    return path


def test_log_reads_the_last_session(log):
    answer = read_log(log)
    assert answer["status"] == "ok" and answer["live_build"] == "12.4.16"
    second_start = LOG.index(record(11, "info", "Started: Live 12.4.16 Build: 2026-01-01_0000000000"))
    assert answer["session_line"] == second_start + 1
    assert [t["scripts"] for t in answer["tracebacks"]] == [["My_Script"], ["Other_Script"]]
    assert answer["tracebacks"][0]["text"] == TRACEBACK
    assert [(m["script"], m["text"]) for m in answer["messages"]] == [
        ("Other_Script", "Initializing..."), ("My_Script", "ready")]


def test_log_for_one_script(log):
    answer = read_log(log, "My_Script")
    assert len(answer["tracebacks"]) == 1 and answer["others"] == 1
    assert [m["text"] for m in answer["messages"]] == ["ready"]
    assert read_log(log, "Quiet_Script")["tracebacks"] == []


def test_find_log(log, tmp_path):
    prefs = log.parent.parent
    older = prefs / "Live 12.4.15" / "Log.txt"
    older.parent.mkdir()
    older.write_text("")
    os.utime(older, (1, 1))
    assert find_log(prefs=prefs) == log
    assert find_log("12.4.15", prefs) == older
    assert find_log("11.0", prefs) is None
    assert find_log(prefs=tmp_path / "none") is None


def test_cli_log(log, capsys, monkeypatch):
    monkeypatch.setenv("ABLETON_PREFERENCES", str(log.parent.parent))
    assert main(["log", "--script", "My_Script"]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[1:4] == ["tracebacks (1):", f"  line {read_log(log)['tracebacks'][0]['line']}:",
                        "    Traceback (most recent call last):"]
    assert "(1 traceback from other scripts or Live not shown; run without --script to see them)" in out
    assert out[-1].endswith("(My_Script) ready")
    assert main(["log", "--script", "Quiet_Script"]) == 0
    out = capsys.readouterr().out
    assert "no tracebacks" in out and "no messages from Quiet_Script" in out
    assert main(["log", "--build", "11.0"]) == 2


@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


@pytest.fixture
def library(tmp_path):
    (tmp_path / "User Library").mkdir()
    return tmp_path / "User Library"


def install(index_dir, library, *args):
    return main(["--index-dir", str(index_dir), "install", *map(str, args), "--build", OLD,
                 "--user-library", str(library)])


def test_install_copies_the_source(tmp_path, index_dir, library, capsys):
    folder = write(tmp_path, {**CLEAN_FRAMEWORK, "__pycache__/surface.cpython-311.pyc": b"x",
                              "old.pyc": b"x", ".DS_Store": b"x", "notes.txt": "keep"})
    assert install(index_dir, library, folder) == 0
    dest = library / "Remote Scripts" / "My_Script"
    assert sorted(p.name for p in dest.rglob("*")) == ["__init__.py", "notes.txt", "surface.py"]
    out = capsys.readouterr().out
    assert f"installed {dest} (3 files)" in out and "restart Live" in out
    assert install(index_dir, library, folder) == 2
    assert "pass --replace" in capsys.readouterr().out
    (dest / "stale.py").write_text("")
    assert install(index_dir, library, folder, "--replace") == 0
    assert not (dest / "stale.py").exists()


def test_install_refuses_findings_and_strangers(tmp_path, index_dir, library, capsys):
    bad = write(tmp_path, {**CLEAN_FRAMEWORK, "surface.py": "import numpy\n"}, name="Bad_Script")
    assert install(index_dir, library, bad) == 1
    assert "not installed: fix the findings first" in capsys.readouterr().out
    assert not (library / "Remote Scripts" / "Bad_Script").exists()
    assert install(index_dir, library, bad, "--no-validate") == 0
    folder = write(tmp_path, CLEAN_FRAMEWORK, name="Taken")
    stranger = library / "Remote Scripts" / "Taken"
    stranger.mkdir()
    (stranger / "mine.txt").write_text("")
    assert install(index_dir, library, folder, "--replace") == 2
    assert "not a Remote Script folder" in capsys.readouterr().out and (stranger / "mine.txt").exists()
    assert install(index_dir, tmp_path / "no library", folder) == 2
    assert install(index_dir, library, tmp_path / "nope") == 2
    assert main(["--index-dir", str(tmp_path / "empty"), "install", str(folder),
                 "--user-library", str(library)]) == 3


def run_skill_script(name, *args, env):
    cli = f"{sys.executable} -m ableton_remote_script_mcp.cli"
    return subprocess.run([str(SKILL / "scripts" / name), *map(str, args)], capture_output=True, text=True, check=False,
                          env={**os.environ, "ABLETON_REMOTE_SCRIPT_MCP": cli, **env})


def test_skill_scripts_call_the_command(tmp_path, index_dir, library, log):
    env = {"ABLETON_REMOTE_SCRIPT_INDEX": str(index_dir), "ABLETON_USER_LIBRARY": str(library),
           "ABLETON_PREFERENCES": str(log.parent.parent)}
    folder = write(tmp_path, CLEAN_FRAMEWORK)
    r = run_skill_script("validate.sh", folder, "--build", OLD, env=env)
    assert r.returncode == 0 and "0 findings in 2 files" in r.stdout
    r = run_skill_script("lookup.sh", "class", "ControlSurface", "--build", OLD, env=env)
    assert r.returncode == 0 and f"[Live {OLD}, observed]" in r.stdout
    r = run_skill_script("lookup.sh", "builds", env=env)
    assert r.returncode == 0 and f"Live {OLD}" in r.stdout
    assert run_skill_script("lookup.sh", env=env).returncode == 2
    r = run_skill_script("install.sh", folder, "--build", OLD, env=env)
    assert r.returncode == 0 and (library / "Remote Scripts" / "My_Script" / "__init__.py").is_file()
    r = run_skill_script("log.sh", "--script", "My_Script", env=env)
    assert r.returncode == 1 and "NameError" in r.stdout


def test_skill_scripts_say_when_the_command_is_missing(tmp_path):
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    r = subprocess.run([str(SKILL / "scripts" / "validate.sh"), str(tmp_path)], capture_output=True, text=True, check=False,
                       env=env)
    assert r.returncode == 127 and "uv tool install" in r.stderr


def fragments(time, text):
    """`text` written the way Live writes it: one record per line, an empty line after each."""
    lines = []
    for line in text.splitlines():
        lines += [record(time, "error", f"RemoteScriptError: {line}"), ""]
    return lines


def test_log_keeps_a_chained_exception_together(tmp_path):
    chained = (f"{TRACEBACK}\n\nDuring handling of the above exception, another exception occurred:\n\n"
               + TRACEBACK.replace("NameError", "KeyError"))
    path = tmp_path / "Log.txt"
    path.write_text("\n".join([record(1, "info", "Started: Live 12.4.16 Build: x"),
                               *fragments(2, chained)]) + "\n")
    answer = read_log(path, "My_Script")
    assert len(answer["tracebacks"]) == 1 and answer["others"] == 0
    assert answer["tracebacks"][0]["text"].replace("\n\n", "\n") == chained.replace("\n\n", "\n")


def test_log_names_the_script_of_a_bad_folder_name(tmp_path):
    error = '  File "<string>", line 1\n    import my-script\n             ^\nSyntaxError: invalid syntax'
    path = tmp_path / "Log.txt"
    path.write_text("\n".join([record(1, "info", "Started: Live 12.4.16 Build: x"), *fragments(2, error)]) + "\n")
    assert read_log(path)["tracebacks"][0]["scripts"] == ["my-script"]
    assert len(read_log(path, "my-script")["tracebacks"]) == 1


def test_install_resolves_the_folder_and_leaves_links_alone(tmp_path, index_dir, library, capsys, monkeypatch):
    folder = write(tmp_path, CLEAN_FRAMEWORK)
    monkeypatch.chdir(folder)
    assert install(index_dir, library, ".") == 0
    assert (library / "Remote Scripts" / "My_Script" / "__init__.py").is_file()
    assert "pick 'My_Script'" in capsys.readouterr().out
    other = write(tmp_path / "elsewhere", CLEAN_FRAMEWORK)
    link = library / "Remote Scripts" / "Linked"
    link.symlink_to(other)
    renamed = write(tmp_path / "again", CLEAN_FRAMEWORK, name="Linked")
    assert install(index_dir, library, renamed, "--replace") == 2
    assert "is a symbolic link; left as it is" in capsys.readouterr().out and link.is_symlink()
    shutil.rmtree(library / "Remote Scripts" / "My_Script")
    (library / "Remote Scripts" / "My_Script").symlink_to(folder)
    assert install(index_dir, library, folder) == 0
    assert "already in the User Library" in capsys.readouterr().out
    bad = write(tmp_path, CLEAN_FRAMEWORK, name="my-script")
    assert install(index_dir, library, bad, "--no-validate") == 2
    assert list((library / "Remote Scripts").glob(".*")) == []  # no staging folder left behind
