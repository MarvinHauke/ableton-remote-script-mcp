"""Structure Void's runtime pages as a `documented` source (plan 0001 Decision 45).

The page below is written here in the layout of the site's runtime pages (headings, lists,
Boost.Python signature lines); its names and texts are our own, not copied from the site.
Nothing is fetched: `import_pages` gets a fake `fetch`.
"""

import sys
from pathlib import Path

from hand_index import OLD, write_hand_index

from ableton_remote_script_mcp.cli import main
from ableton_remote_script_mcp.query import get_class, search
from ableton_remote_script_mcp.structure_void import (
    import_pages,
    load_document,
    parse_page,
    runtime_urls,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import eval_names

SITE = "https://midiremotescripts.structure-void.com"
PAGE = """<html><body><nav>not read</nav><article>
<h1 id="livesong-runtime"><code>Live.Song</code> (runtime)</h1>
<h2 id="functions">Functions</h2>
<h3 id="list_things"><code>list_things(...)</code></h3>
<p>list_things() -&gt; tuple :
    Lists the things. More words.</p>
<h2 id="classes">Classes</h2>
<h3 id="class-songlomobject">class <code>Song(LomObject)</code>&para;</h3>
<p>The song. It has tracks.</p>
<h4 id="properties">Properties</h4>
<ul>
<li><code>_live_ptr</code></li>
<li><code>tempo</code> - Get/set the tempo. In BPM.</li>
<li><code>is_wobbly</code></li>
</ul>
<h4 id="methods">Methods</h4>
<h5 id="view"><code>View(...)</code></h5>
<p>The view of the song.</p>
<h5 id="__init__"><code>__init__(...)</code></h5>
<p>Raises an exception</p>
<h5 id="add_tempo_listener"><code>add_tempo_listener(...)</code></h5>
<p>add_tempo_listener( (Song)arg1, (object)arg2) -&gt; None :
    Add a listener for "tempo".</p>
<div class="highlight"><pre><code>C++ signature :
    void add_tempo_listener(TPyHandle&lt;ASong&gt;,boost::python::api::object)</code></pre></div>
<h3 id="class-quantizationenum">class <code>Quantization(enum)</code></h3>
<h4 id="methods_1">Methods</h4>
<h5 id="bit_length"><code>bit_length(self, /)</code></h5>
<p>Number of bits.</p>
<h4 id="attributes">Attributes</h4>
<ul>
<li><code>imag</code> = <code>&lt;attribute 'imag' of 'int' objects&gt;</code> - the imaginary part</li>
<li><code>q_bar</code> = <code>Song.Quantization.q_bar</code></li>
<li><code>q_all</code> = <code>Song.Quantization.q_all</code> - Every step.</li>
</ul>
<h3 id="class-beattimeinstance">class <code>BeatTime(instance)</code></h3>
<h4 id="properties_1">Properties</h4>
<ul><li><code>ticks</code></li></ul>
</article></body></html>"""

SITEMAP = f"""<urlset>
<url><loc>{SITE}/reference/live12/Live.Song.runtime/</loc></url>
<url><loc>{SITE}/reference/live12/_Framework.ControlSurface/</loc></url>
<url><loc>{SITE}/reference/live11/Live.Song.runtime/</loc></url>
<url><loc>{SITE}/guides/runtime-changes-11-to-12/</loc></url>
</urlset>"""


def test_parse_page():
    parsed = parse_page(PAGE, "Live.Song", "u")
    assert sorted(parsed["classes"]) == ["Live.Song.BeatTime", "Live.Song.Quantization", "Live.Song.Song"]
    song = parsed["classes"]["Live.Song.Song"]
    assert song["bases"] == ["LomObject"] and song["kind"] == "class" and song["doc"] == "The song."
    assert song["members"] == {
        "tempo": {"kind": "property", "doc": "Get/set the tempo."},
        "is_wobbly": {"kind": "property"},
        "View": {"kind": "class", "doc": "The view of the song."},
        "add_tempo_listener": {"kind": "method", "signature": "add_tempo_listener( (Song)arg1, (object)arg2) -> None",
                               "doc": 'Add a listener for "tempo".'},
    }
    quantization = parsed["classes"]["Live.Song.Quantization"]
    assert quantization["kind"] == "enum" and quantization["members"] == {
        "q_bar": {"kind": "enum value"}, "q_all": {"kind": "enum value"}}
    assert parsed["classes"]["Live.Song.BeatTime"]["kind"] == "value class"
    assert parsed["functions"] == {"list_things": {"kind": "function", "signature": "list_things() -> tuple",
                                                   "doc": "Lists the things."}}


def test_runtime_urls_of_one_version():
    assert runtime_urls(SITEMAP, "12") == [("Live.Song", f"{SITE}/reference/live12/Live.Song.runtime/")]


def documented_index(tmp_path):
    index_dir = write_hand_index(tmp_path / "index")
    fetched = []

    def fetch(url):
        fetched.append(url)
        return SITEMAP if url.endswith("sitemap.xml") else PAGE

    import_pages(index_dir, "12", fetch=fetch, delay=0, log=lambda *_: None)
    import_pages(index_dir, "12", fetch=fetch, delay=0, log=lambda *_: None)  # the page is reused
    assert fetched.count(f"{SITE}/reference/live12/Live.Song.runtime/") == 1
    return index_dir


def test_import_writes_a_documented_document(tmp_path):
    index_dir = documented_index(tmp_path)
    doc = load_document(index_dir, "12")
    assert doc["confidence"] == "documented" and doc["licence"] == "CC BY-NC-SA 4.0"
    assert doc["functions"]["Live.Song.list_things"]["url"].endswith("/live12/Live.Song.runtime/")


def test_lookup_adds_documented_members_to_the_proxy_model(tmp_path):
    index_dir = documented_index(tmp_path)
    answer = get_class("Live.Song.Song", index_dir, OLD)  # the hand index has its proxy model
    assert [c["qualified_name"] for c in answer["classes"]] == ["push3-helper:live_model.Live.Song.Song"]
    documented = answer["classes"][0]["documented"]
    assert documented["confidence"] == "documented"
    assert "tempo" not in documented["members"]  # the proxy model has it: observed wins
    assert "add_tempo_listener" in documented["members"]
    only = get_class("BeatTime", index_dir, OLD)
    assert only["classes"] == [] and only["documented"][0]["qualified_name"] == "Live.Song.BeatTime"


def test_search_marks_documented_hits(tmp_path, capsys):
    index_dir = documented_index(tmp_path)
    hits = search("add_tempo_listener", index_dir, OLD)["results"]
    assert hits[0]["qualified_name"] == "Live.Song.Song.add_tempo_listener"
    assert hits[0]["confidence"] == "documented"
    assert main(["--index-dir", str(index_dir), "search", "is_wobbly", "--build", OLD]) == 0
    assert "Live.Song.Song.is_wobbly  (name, documented;" in capsys.readouterr().out


def test_eval_names_counts_documented_and_setattr_prefix_names(tmp_path):
    index_dir = documented_index(tmp_path)
    from ableton_remote_script_mcp.index_store import (
        attach_statements,
        load_index,
        load_statements,
    )
    index = load_index(index_dir, OLD)
    statements = load_statements(index_dir, index)
    attach_statements(index, statements)
    folder = tmp_path / "Probe"
    folder.mkdir()
    (folder / "__init__.py").write_text(
        "def f(song, ui):\n"
        "    for key in ('mode', 'channel'):\n"
        "        setattr(ui, 'set_B_' + key, None)\n"
        "    song.add_tempo_listener(f)\n"
        "    ui.set_B_mode(1)\n"
        "    return song.is_wobblee\n")
    result = eval_names.check(folder, index, statements, load_document(index_dir, "12"))
    assert [u["name"] for u in result["unknown"]] == ["is_wobblee"]
    assert result["attribute_counts"]["documented"] == 1
