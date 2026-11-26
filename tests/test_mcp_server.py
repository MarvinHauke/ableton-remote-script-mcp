"""Plan 0001 step 11: the answer core (version, size caps), the stable API, `check-names`, and the
MCP server as an adapter over them (Decision 49). The MCP tools go through the SDK's in-memory
client; a tool and the matching skill script give the same answer."""

import json
import os
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from hand_index import OLD, write_hand_index
from mcp import Client

from ableton_remote_script_mcp import api
from ableton_remote_script_mcp.answers import ANSWER_VERSION, bounded, tokens
from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.mcp_server import make_server

SKILL = Path(__file__).resolve().parent.parent / "skills" / "ableton-remote-scripts"
RING = "ableton.v3.control_surface.components.session_ring.SessionRingComponent"
TOOLS = {"search_api", "get_class", "check_names", "outline_reference_script", "validate_script", "diff_builds",
         "list_builds"}


@pytest.fixture
def index_dir(tmp_path):
    return write_hand_index(tmp_path / "index")


def test_a_capped_answer_says_what_it_left_out():
    answer = {"status": "ok", "small": [1, 2], "big": [{"n": i, "text": "x" * 40} for i in range(200)]}
    whole = bounded(answer, None)
    assert whole["answer_version"] == ANSWER_VERSION and len(whole["big"]) == 200 and "cut" not in whole
    capped = bounded(answer, 500, how="ask for less", collections={"big": None})
    assert tokens(capped) <= 500 and capped["small"] == [1, 2]
    [cut] = capped["cut"]["fields"]
    assert cut["field"] == "big" and cut["total"] == 200 and cut["kept"] == len(capped["big"]) > 0
    assert capped["big"] == answer["big"][:cut["kept"]] and capped["cut"]["how"] == "ask for less"
    assert len(answer["big"]) == 200  # nothing is taken from the caller's answer


def test_search_pages_and_lookup_narrows(index_dir):
    first = api.search("set", OLD, limit=1, index_dir=index_dir)
    assert first["answer_version"] == ANSWER_VERSION and first["next_offset"] == 1 and first["total"] > 1
    second = api.search("set", OLD, limit=1, offset=1, index_dir=index_dir)
    assert second["results"][0] != first["results"][0] and second["offset"] == 1

    [ring] = api.lookup(RING, OLD, members=["set_offsets", "is_enabled", "nope"], index_dir=index_dir)["classes"]
    assert list(ring["all_members"]) == ["set_offsets", "is_enabled"] and ring["missing_members"] == ["nope"]
    assert ring["all_members"]["is_enabled"]["origin"] == "ableton.v3.control_surface.component.Component"
    [own] = api.lookup(RING, OLD, own=True, index_dir=index_dir)["classes"]
    assert {m["origin"] for m in own["all_members"].values()} == {RING}
    small = api.lookup(RING, OLD, max_tokens=300, index_dir=index_dir)
    assert small["cut"]["fields"] and "members=[...]" in small["cut"]["how"]
    assert "cut" not in api.lookup(RING, OLD, max_tokens=300, full=True, index_dir=index_dir)


def test_outline_by_section(index_dir):
    whole = api.outline("Fake_V3", OLD, full=True, index_dir=index_dir)
    assert whole["status"] == "ok" and whole["sections"]["elements"] == len(whole["elements"]) > 0
    part = api.outline("Fake_V3", OLD, section="elements", index_dir=index_dir)
    assert part["elements"] == whole["elements"] and "classes" not in part and part["sections"] == whole["sections"]
    tight = api.outline("Fake_V3", OLD, max_tokens=tokens(whole) - 50, index_dir=index_dir)
    left_out = [f for f in tight["cut"]["fields"] if f["kept"] == 0]
    assert left_out and "section=" in tight["cut"]["how"]
    page = api.outline("Fake_V3", OLD, section="elements", offset=1, index_dir=index_dir)
    assert page["elements"] == whole["elements"][1:]
    assert api.outline("Fake_V3", OLD, section="nope", index_dir=index_dir)["status"] == "refused"


def test_check_names_of_a_list(index_dir, capsys):
    answer = api.check_names(names=["SessionRingComponent", "SessionRingComponent.set_offsets",
                                    "SessionRingComponent.is_enabled", "SessionRingComponent.frobnicate",
                                    "Song.tempo", "set_pads", "frobnicate"], build=OLD, index_dir=index_dir)
    by = {r["name"]: r for r in answer["names"]}
    assert by["SessionRingComponent"]["kind"] == "class" and by["SessionRingComponent"]["confidence"] == "observed"
    assert by["SessionRingComponent.set_offsets"]["params"] == ["self", "track_offset", "scene_offset"]
    assert by["SessionRingComponent.is_enabled"]["origin"] == "ableton.v3.control_surface.component.Component"
    assert by["SessionRingComponent.frobnicate"]["known"] == "not_a_member"
    assert by["Song.tempo"]["proxy_of"] == "Live.Song.Song"
    assert by["set_pads"]["known"] == "index" and by["set_pads"]["in"][0].startswith("ableton.v3")
    assert by["frobnicate"]["known"] == "unknown"
    assert answer["unknown"] == ["SessionRingComponent.frobnicate", "frobnicate"]  # a list, as for a folder
    assert main(["--index-dir", str(index_dir), "check-names", "--build", OLD, "--names", "Song.tempo"]) == 0
    assert "the Push 3 helper's model of Live.Song.Song" in capsys.readouterr().out
    assert main(["--index-dir", str(index_dir), "check-names", "--build", OLD, "--names", "frobnicate"]) == 1
    assert main(["--index-dir", str(index_dir), "check-names", "--build", OLD]) == 2


def test_check_names_of_a_folder(index_dir, tmp_path):
    folder = tmp_path / "My_Box"
    folder.mkdir()
    (folder / "__init__.py").write_text("from ableton.v3.control_surface.components.session_ring import "
                                        "SessionRingComponent\n\n"
                                        "def create_instance(c_instance):\n"
                                        "    ring = SessionRingComponent(num_tracks=8)\n"
                                        "    ring.set_offsets(0, 0)\n    ring.frobnicate()\n")
    answer = api.check_names(folder, build=OLD, index_dir=index_dir)
    assert answer["status"] == "ok" and [u["name"] for u in answer["unknown"]] == ["frobnicate"]
    assert answer["attribute_counts"]["index"] == 1  # set_offsets; keywords: tests/test_eval_scripts.py
    assert api.check_names(tmp_path / "nope", build=OLD, index_dir=index_dir)["status"] == "folder_missing"


def _call(index_dir, tool, arguments):
    async def run():
        async with Client(make_server(index_dir)) as client:
            listed = await client.list_tools()
            result = await client.call_tool(tool, arguments)
            return listed.tools, result
    return anyio.run(run)


def test_the_tools_pass_the_api_answers_through(index_dir):
    tools, result = _call(index_dir, "get_class", {"name": RING, "build": OLD, "members": ["set_offsets"]})
    assert {t.name for t in tools} == TOOLS
    assert all("Example:" in t.description for t in tools)  # one worked example each (Decision 49 Q6)
    assert all(t.annotations.read_only_hint for t in tools)
    expected = api.lookup(RING, OLD, members=["set_offsets"], index_dir=index_dir)
    assert result.structured_content == expected
    assert json.loads(result.content[0].text) == expected

    _, names = _call(index_dir, "check_names", {"names": ["Song.tempo", "frobnicate"], "build": OLD})
    assert names.structured_content["counts"] == {"index": 1, "unknown": 1}
    _, missing = _call(index_dir, "search_api", {"query": "ring", "build": "9.9.9"})
    assert missing.structured_content["status"] == "index_missing" and "build-index" in missing.structured_content["message"]
    _, diff = _call(index_dir, "diff_builds", {"from_build": OLD, "to_build": "12.4.99", "under": "ableton.v3"})
    assert diff.structured_content["status"] in ("ok", "index_missing")


def test_a_tool_and_the_skill_script_give_the_same_answer(index_dir):
    cli = f"{sys.executable} -m ableton_remote_script_mcp.cli"
    env = {**os.environ, "ABLETON_REMOTE_SCRIPT_MCP": cli, "ABLETON_REMOTE_SCRIPT_INDEX": str(index_dir)}
    for script_args, tool, arguments in [
        (["class", RING, "--build", OLD], "get_class", {"name": RING, "build": OLD}),
        (["search", "session", "ring", "--build", OLD], "search_api", {"query": "session ring", "build": OLD}),
        (["names", "--names", "Song.tempo", "SessionRingComponent.set_offsets", "--build", OLD], "check_names",
         {"names": ["Song.tempo", "SessionRingComponent.set_offsets"], "build": OLD}),
        (["outline", "Fake_V3", "--build", OLD], "outline_reference_script", {"script": "Fake_V3", "build": OLD}),
    ]:
        run = subprocess.run([str(SKILL / "scripts" / "lookup.sh"), *script_args, "--json"], capture_output=True,
                             text=True, check=False, env=env)
        _, result = _call(index_dir, tool, arguments)
        assert json.loads(run.stdout) == result.structured_content, script_args


def test_the_cli_prints_a_class_whose_answer_was_cut(index_dir):
    # 0003 step 1: `lookup class Live.Clip.Clip` raised KeyError 'all_members' when the cap took
    # the member lists out of the class
    from ableton_remote_script_mcp.cli import _format_class

    for max_tokens in (150, 300, 600):
        answer = api.lookup(RING, OLD, max_tokens=max_tokens, index_dir=index_dir)
        assert answer["cut"]["fields"]
        for c in answer["classes"]:
            text = _format_class(c, own_only=False)
            assert c["qualified_name"] in text
