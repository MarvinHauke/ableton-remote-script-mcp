"""Seam B: the validator over the hand-written index (tests/hand_index.py).

Every sample script is our own, written here: a clean v3 and a clean `_Framework` script with no
findings, and one bad sample per rule.
"""

import pytest
from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.query import validate_script

CLEAN_V3 = {
    "__init__.py": """\
from ableton.v3.control_surface import Component
from ableton.v3.control_surface.control_surface import ControlSurface
from ableton.v3.control_surface.control_surface_specification import ControlSurfaceSpecification
from .elements import Elements
from . import mappings


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    create_mappings_function = mappings.create_mappings


class MySurface(ControlSurface):
    pass


def create_instance(c_instance):
    return MySurface(specification=Specification, c_instance=c_instance)
""",
    "elements.py": """\
from ableton.v3.control_surface.elements_base import ElementsBase


class Elements(ElementsBase):
    pass
""",
    "mappings.py": """\
def create_mappings(control_surface):
    return {}
""",
}

CLEAN_FRAMEWORK = {
    "__init__.py": """\
from .surface import MySurface


def create_instance(c_instance):
    return MySurface(c_instance)
""",
    "surface.py": """\
from __future__ import absolute_import
import logging
import math
import sys
from functools import partial
from future.moves.itertools import zip_longest

import Live
import MidiRemoteScript
from Live.Song import Song
from _Framework.ButtonElement import ButtonElement
from _Framework.ControlSurface import ControlSurface
from _Framework.SessionComponent import SessionComponent

try:
    from numpy import array
except ImportError:
    array = None

logger = logging.getLogger(__name__)


class MySurface(ControlSurface):
    def __init__(self, c_instance):
        super().__init__(c_instance)
        with self.component_guard():
            self._session = SessionComponent()
""",
}


@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


def write(tmp_path, files, name="My_Script"):
    folder = tmp_path / "scripts" / name
    for rel, text in files.items():
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text)
    return folder


def validate(folder, index_dir):
    answer = validate_script(folder, index_dir, OLD)
    assert answer["status"] == "ok", answer
    assert answer["live_build"] == OLD and answer["confidence"] == "observed"
    return answer


def rules(answer):
    return [(f["rule"], f["file"], f["line"]) for f in answer["findings"]]


def test_clean_v3_script_has_no_findings(tmp_path, index_dir):
    answer = validate(write(tmp_path, CLEAN_V3), index_dir)
    assert answer["findings"] == []
    assert answer["files"] == 3 and answer["script"] == "My_Script"


def test_clean_framework_script_has_no_findings(tmp_path, index_dir):
    answer = validate(write(tmp_path, CLEAN_FRAMEWORK), index_dir)
    assert answer["findings"] == []
    reasons = {n["what"]: n["reason"] for n in answer["not_checked"] if n["rule"] == "unresolved-import"}
    live = ["import Live", "import MidiRemoteScript", "from Live.Song import Song"]
    assert [i for i in reasons if i != "import math"] == live  # `import sys` is built into Python: no entry
    assert "Live's own C++ code" in reasons["import Live"]
    # math is compiled into some Python builds and a C extension file in others
    assert "C module of Python's standard library" in reasons.get("import math", "C module of Python's standard library")


def test_standard_library_module_live_does_not_ship(tmp_path, index_dir):
    files = {**CLEAN_V3, "mappings.py": "import ctypes\n"}  # pure Python, but not in Live's lib
    answer = validate(write(tmp_path, files), index_dir)
    assert rules(answer) == [("unresolved-import", "mappings.py", 1)]
    assert answer["findings"][0]["message"].endswith(f"in Python's standard library, but Live {OLD} does not ship it")


def test_folder_name_with_spaces(tmp_path, index_dir):
    answer = validate(write(tmp_path, CLEAN_V3, name="My Script"), index_dir)
    assert rules(answer) == [("folder-name", ".", None)]
    assert "'My_Script'" in answer["findings"][0]["fix"]


@pytest.mark.parametrize("name, suggested", [("my-script", "my_script"), ("2nd_Script", "_2nd_Script")])
def test_folder_name_that_is_not_a_python_name(tmp_path, index_dir, name, suggested):
    answer = validate(write(tmp_path, CLEAN_V3, name=name), index_dir)
    assert rules(answer) == [("folder-name", ".", None)]
    assert "SyntaxError" in answer["findings"][0]["message"] and repr(suggested) in answer["findings"][0]["fix"]


def test_syntax_error_is_a_finding(tmp_path, index_dir):
    files = {**CLEAN_V3, "elements.py": "class Elements(\n    pass\n", "broken.py": b"x = 1\x00\n"}
    answer = validate(write(tmp_path, files), index_dir)
    assert [(r, f) for r, f, _ in rules(answer)] == [("syntax-error", "broken.py"), ("syntax-error", "elements.py")]
    assert answer["findings"][1]["line"] == 1
    assert all(f["severity"] == "error" and f["fix"] for f in answer["findings"])


def test_syntax_newer_than_live_python_is_a_finding(tmp_path, index_dir):
    files = {**CLEAN_V3, "mappings.py": "type Mapping = dict\n"}  # a type alias statement needs Python 3.12
    assert rules(validate(write(tmp_path, files), index_dir)) == [("syntax-error", "mappings.py", 1)]


@pytest.mark.parametrize("init, line", [
    ("from .elements import Elements\n", 1),
    ("def create_instance():\n    pass\n", 1),
    ("x = 1\n\ndef create_instance(c_instance, specification):\n    pass\n", 3),
])
def test_create_instance_missing_or_wrong(tmp_path, index_dir, init, line):
    answer = validate(write(tmp_path, {**CLEAN_V3, "__init__.py": init}), index_dir)
    assert rules(answer) == [("create-instance", "__init__.py", line)]
    assert "create_instance(c_instance)" in answer["findings"][0]["fix"]


@pytest.mark.parametrize("init", [
    "def create_instance(c_instance, *, debug=False):\n    pass\n",
    "def create_instance(*args):\n    pass\n",
    "from .elements import Elements as create_instance\n",
])
def test_create_instance_accepted_forms(tmp_path, index_dir, init):
    assert validate(write(tmp_path, {**CLEAN_V3, "__init__.py": init}), index_dir)["findings"] == []


def test_no_init_py(tmp_path, index_dir):
    files = {k: v for k, v in CLEAN_V3.items() if k != "__init__.py"}
    answer = validate(write(tmp_path, {**files, "__init__.pyc": b"compiled"}), index_dir)
    assert rules(answer) == [("create-instance", "__init__.py", None)]
    assert "only compiled .pyc" in answer["findings"][0]["message"]


def test_unresolved_imports(tmp_path, index_dir):
    surface = """\
from ableton.v3.control_surface import Componnet
from ableton.v3.control_surface.mixer import MixerComponent
from _Framework.ControlSurface import ControlSurface, Nope
import numpy
from .missing import Thing
from .elements import Elemnts
from elements import Elements
from ... import too_far
from ableton.v3.control_surface import BaseComponent
from ableton.v3.control_surface.components import Component
import ableton.v3.control_surface.component


def later():
    import _Framework.NoSuchModule
"""
    answer = validate(write(tmp_path, {**CLEAN_V3, "surface.py": surface}), index_dir)
    found = [(f["line"], f["message"]) for f in answer["findings"]]
    assert [line for line, _ in found] == [1, 2, 3, 4, 5, 6, 7, 8, 15]
    msg = dict(found)
    assert msg[1].endswith(f"Live {OLD}'s module ableton.v3.control_surface has no name Componnet")
    assert msg[2].endswith(f"no module ableton.v3.control_surface.mixer in Live {OLD}")
    assert msg[3].endswith("has no name Nope")
    assert "numpy is neither in" in msg[4]
    assert msg[5].endswith("the script has no module My_Script.missing")
    assert msg[6].endswith("the script's module My_Script.elements has no name Elemnts")
    assert "above the script's own package" in msg[8]
    fixes = {f["line"]: f["fix"] for f in answer["findings"]}
    assert "search Componnet" in fixes[1]
    assert "from .elements import" in fixes[7]
    assert {f["rule"] for f in answer["findings"]} == {"unresolved-import"}


def test_implicit_relative_import_gets_the_relative_form(tmp_path, index_dir):
    files = {**CLEAN_V3, "sub/__init__.py": "", "sub/strip.py": "from elements import Elements\nimport Live\n"}
    answer = validate(write(tmp_path, files), index_dir)
    assert rules(answer) == [("unresolved-import", "sub/strip.py", 1)]
    assert "`from ..elements import …`" in answer["findings"][0]["fix"]


def test_review_edge_cases(tmp_path, index_dir):
    files = {"mappings.py": "import elements\n", "elements.py": "",
             "opt.py": "try:\n    import numpy\nexcept* ImportError:\n    numpy = None\n"}
    answer = validate(write(tmp_path, {**files, "x.py": "from . import elements\n"}), index_dir)
    assert rules(answer) == [("create-instance", "__init__.py", None), ("unresolved-import", "mappings.py", 1)]
    assert "`from . import elements`" in answer["findings"][1]["fix"]


def test_index_without_a_record_of_lives_python(tmp_path, index_dir):
    import json
    path = index_dir / f"live-{OLD}.json"
    index = json.loads(path.read_text())
    index["python"]["modules"] = None
    path.write_text(json.dumps(index))
    answer = validate(write(tmp_path, {**CLEAN_V3, "mappings.py": "import ctypes\nimport json\n"}), index_dir)
    assert answer["findings"] == []
    assert [n["what"] for n in answer["not_checked"] if n["rule"] == "unresolved-import"] == ["import ctypes", "import json"]


def test_cli_output_as_in_getting_started(tmp_path, index_dir, capsys):
    files = {"__init__.py": "from .surface import MySurface\n\ndef create_instance(c_instance):\n"
                            "    return MySurface(c_instance)\n",
             "surface.py": "import numpy\nfrom _Framework.ControlSurface import ControlSurface\n\n\n"
                           "class MySurface(ControlSurface):\n    pass\n"}
    assert main(["--index-dir", str(index_dir), "validate", str(write(tmp_path, files)), "--build", OLD]) == 1
    assert capsys.readouterr().out.splitlines() == [
        f"My_Script  [Live {OLD}, observed]  1 finding in 2 files",
        (f"  surface.py:1: error [unresolved-import] `import numpy`: numpy is neither in Live {OLD}'s Remote "
         "Scripts folder nor in the Python that Live ships"),
        "      fix: use a module Live ships, or put the code inside the script's folder"]


def test_star_imports_are_followed(tmp_path, index_dir):
    # `Fake_Script.mixer` star-imports `_Framework.ControlSurfaceComponent`
    files = {**CLEAN_V3, "strip.py": "from Fake_Script.mixer import ControlSurfaceComponent, MixerStrip\n"}
    assert validate(write(tmp_path, files), index_dir)["findings"] == []


def test_folder_and_index_missing(tmp_path, index_dir):
    assert validate_script(tmp_path / "nope", index_dir, OLD)["status"] == "folder_missing"
    folder = write(tmp_path, CLEAN_V3)
    assert validate_script(folder, index_dir, "11.0.0")["status"] == "index_missing"


def test_cli_validate(tmp_path, index_dir, capsys):
    clean = write(tmp_path, CLEAN_V3)
    assert main(["--index-dir", str(index_dir), "validate", str(clean), "--build", OLD]) == 0
    assert f"My_Script  [Live {OLD}, observed]  0 findings in 3 files" in capsys.readouterr().out
    bad = write(tmp_path, {**CLEAN_V3, "__init__.py": "import numpy\n"}, name="Bad Script")
    assert main(["--index-dir", str(index_dir), "validate", str(bad), "--build", OLD]) == 1
    out = capsys.readouterr().out
    assert "3 findings in 3 files" in out
    assert "  __init__.py:1: error [unresolved-import] `import numpy`" in out
    assert "      fix: rename the folder to 'Bad_Script'" in out
    assert main(["--index-dir", str(index_dir), "validate", str(tmp_path / "nope")]) == 2
    assert main(["--index-dir", str(tmp_path / "empty"), "validate", str(clean)]) == 3
