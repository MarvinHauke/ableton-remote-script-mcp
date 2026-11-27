"""Every collection an answer declares for the cut (plan 0001 Decision 62) is a list of records or
a map of members in the answers the API gives, never a record with fixed fields. The review of
Decision 62 found `specification`, `mappings` and a diff's `members` declared as collections: the
cut then dropped a record's own fields. This test walks each declared path over real answers of
the hand-written index, so a new declaration that lands on a record fails here first."""

import pytest
from hand_index import NEW, OLD, write_hand_index

from ableton_remote_script_mcp import api

MAPS = {"all_members", "members", "documented"}
"""The collections that are dicts: a class's members by name. Every other collection is a list."""

SCRIPT = """\
import numpy
from ableton.v3.control_surface import ControlSurface


class Box(ControlSurface):
    def setup(self):
        self.song.tracks
        self.component_map
"""


@pytest.fixture(scope="module")
def answers(tmp_path_factory):
    root = tmp_path_factory.mktemp("cut_paths")
    index_dir = write_hand_index(root / "index")
    folder = root / "Box"
    folder.mkdir()
    (folder / "__init__.py").write_text("from .box import Box\n\n\ndef create_instance(c_instance):\n"
                                        "    return Box(c_instance)\n")
    (folder / "box.py").write_text(SCRIPT)
    kw = {"full": True, "index_dir": index_dir}
    return {
        "lookup": [api.lookup(n, OLD, **kw) for n in ("NoteEditorComponent", "SessionRingComponent", "Component")],
        "search": [api.search("set", OLD, **kw), api.search("Component", OLD, **kw)],
        "outline": [api.outline(s, OLD, **kw) for s in ("Fake_V3", "Fake_Fw")],
        "validate": [api.validate(folder, OLD, **kw)],
        "check_names": [api.check_names(folder, build=OLD, **kw),
                        api.check_names(names=["SessionRingComponent.set_offsets", "NoteEditorComponent", "set_pitches", "Nope.nothing"], build=OLD, **kw)],
        "list_builds": [api.list_builds(installs=[], **kw)],
        "diff": [api.diff(OLD, NEW, **kw)],
    }


CUTS = {
    "lookup": api.LOOKUP_CUTS, "search": api.SEARCH_CUTS, "outline": api.OUTLINE_CUTS,
    "validate": api.VALIDATE_CUTS, "check_names": api.CHECK_NAMES_CUTS,
    "list_builds": api.LIST_BUILDS_CUTS, "diff": api.DIFF_CUTS,
}


def _targets(value, path: str):
    """(last key, value) for every place a declared path such as `classes[].members.added` reaches."""
    head, _, rest = path.partition(".")
    key, each = head.removesuffix("[]"), head.endswith("[]")
    if not isinstance(value, dict) or key not in value:
        return
    found = value[key]
    if each:
        for item in found if isinstance(found, list) else []:
            yield from _targets(item, rest) if rest else [(key, item)]
    elif rest:
        yield from _targets(found, rest)
    else:
        yield key, found


@pytest.mark.parametrize("name", sorted(CUTS))
def test_each_declared_collection_is_a_list_or_a_member_map(answers, name):
    assert all(a["status"] == "ok" for a in answers[name]), [a.get("message") for a in answers[name]]
    for path in CUTS[name]:
        for key, found in (t for a in answers[name] for t in _targets(a, path)):
            if isinstance(found, dict):
                assert key in MAPS, f"{name}: {path} is a record {sorted(found)}, not a collection"
            # a list is a collection; a number or string is never cut (`_containers` skips it)


def test_the_fixture_reaches_most_declared_paths(answers):
    """A path no fixture answer reaches is checked by nothing above: keep that list short."""
    unreached = sorted(f"{name}: {path}" for name, cuts in CUTS.items() for path in cuts
                       if not any(True for a in answers[name] for _ in _targets(a, path)))
    assert unreached == UNREACHED, unreached


UNREACHED = [
    "check_names: not_read",  # needs an Elements class the reader can't read
    "diff: modules.changed[].members.added",  # the hand index changes no module's own functions
    "diff: modules.changed[].members.changed",
    "diff: modules.changed[].members.removed",
    "lookup: classes[].documented",  # needs Structure Void's pages imported
    "lookup: documented",
]
"""Declared paths the hand index has no answer for: checked by review only."""
