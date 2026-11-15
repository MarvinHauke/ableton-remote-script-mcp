# Sources investigation — Remote Script MCP + skill

Date: 2026-11-14. Inputs: the ChatGPT conversation "MCP für Remote Skripts", midiremotescripts.structure-void.com, the gluon GitHub repos, and the local Live installs on this Mac.

## TL;DR

1. **Structure Void: the guides are conceptual, and the reference pages are a real API reference** (corrected 2026-11-15, see §1). It has 1741 Live 12 pages: module, class, bases and argument names for the framework, plus typed LOM signatures and docstrings. It was built from an unstated Live 12.x between 12.0 and 12.4.16; there are no defaults and no Live 13. It is CC BY-NC-SA 4.0: cite it and rephrase it, don't copy it in.
2. **The gluon repos are two old snapshots.** The Live 11 repo is **11.2.11** (decompyle3, June 2023). The "Live 12" repo's framework (`_Framework`, `ableton/v2`, `ableton/v3`) was decompiled with uncompyle6 from **Python 3.7 bytecode compiled March 9–11, 2024**. That matches the Live 12.0 release, not the "12.4" its README claims. (Corrected 2026-11-15: an earlier version of this note called it "Live 11-era"; comparing it against the Live 11 repo shows substantial v3 growth.) Only 10 controllers added in May 2026 come from Live 12.x Python 3.11 bytecode (pycdc), and their bodies are partial. Neither repo has a **licence**, and the code is Ableton's copyright. Read them locally; don't vendor them.
3. **The best data source is already on this Mac.** Live 12.4.16, 12.4.25b1 and 13.0b25 are installed, all with Python 3.11 `.pyc` files (magic `a70d0d0a`). We can build our own per-version API index (class tree, signatures, argument names, docstrings) the same way Structure Void does: code-object extraction plus a runtime probe inside Live. Keep the generated data git-ignored (Ableton copyright and the beta NDA). Publish the tools, not the data.
4. **The existing AbletonMCP (ahujasid, `uvx ableton-mcp`, already connected) controls Live at runtime.** It does not help write Remote Scripts. Our MCP fills that gap: a development-time API index, scaffolding and validation. They complement each other.

## 1. midiremotescripts.structure-void.com

- Author: Julien Bayle / Structure Void. Unofficial, not affiliated with Ableton. Built with MkDocs Material.
- Licence: **CC BY-NC-SA 4.0** for the docs and the generator. Code produced by the generator is CC0.
- Sections:
  - Guides: what-its-for, first-script, architecture, controlsurface-lifecycle, components-layers-modes, controls-and-elements, midi-message-flow, v2-vs-v3, lom-map, runtime-changes-11-to-12.
  - API reference for Live 9, 10, 11 and 12. URLs follow `reference/<liveN>/<module>/`.
  - A generator page.
- **How their reference is built** (the method worth copying):
  1. `extract_api.py`: reads `.py`/`.pyc` and writes JSON per module (classes, methods, argument names, attributes). It does not decompile function bodies.
  2. `dump_runtime_api.py`: runs inside Live and captures the C++ `Live` module with signatures and defaults. Docstrings exist only at runtime.
  3. `gen_docs.py`, `render_runtime.py` and `build_nav.py` turn the JSON into pages.
  4. `diff_runtime.py` produces the "What changed" page.
- **Live 11→12 diff page:** 1427 members added, 84 removed, 1573 with changed signatures. These are introspected public members. Some entries are noise: stdlib names leaking in, int-enum members such as `bit_count`, and a docstring captured as a name. Notable additions include `Track.take_lanes`/`create_take_lane`/`create_midi_clip`/`insert_device`, `Chain.insert_device`, `RackDevice.insert_chain`, `SimplerDevice.replace_sample`, `Clip.automation_envelopes`, `DeviceParameter.display_value`, `Song.tuning_system`/`scale_mode`, Compare A/B on many devices, and the new device classes Looper, Meld, Roar, DrumCell and CcControl. The page is about 470 KB and only the first 100 KB was read.
- **The guides are conceptual and shallow.** Useful facts for the skill:
  - Lifecycle: `create_instance(c_instance)` → `__init__` builds everything inside `with self.component_guard():` in the order controls → components → modes. Then `update()`/`refresh_state()` (full feedback resend), `request_rebuild_midi_map()` → `build_midi_map()` (batched), `update_display()` (about every 100 ms), `suspend`/`resume`, and `disconnect()`. `disconnect()` must remove hand-added listeners, blank the LEDs, then call super.
  - MIDI map: "direct mapping" goes straight to a LOM parameter without Python and has lower latency. "Forwarding" sends the message to the script.
  - Gotchas:
    - Building objects outside `component_guard` leaves them half initialised.
    - Orphaned listeners cause crashes and leaks.
    - The MIDI map goes stale after a mode change unless a rebuild is requested.
    - There is no hot reload: set the slot to None and back, and restart Live for new folders or imports.
    - Folder names must not contain spaces.
  - Paths on macOS:
    - User Library scripts: `~/Music/Ableton/User Library/Remote Scripts/`
    - Log: `~/Library/Preferences/Ableton/Live <N>/Log.txt`
  - v3 is declarative: a `ControlSurfaceSpecification` plus an `ElementsBase` subclass plus a thin `ControlSurface` with `setup()`. Live 12 factory scripts use v3.
- **Generator:** runs in the browser using WebMIDI and outputs **classic `_Framework`** scripts for Live 11/12. It supports track volume/pan/mute/solo/arm, master volume, transport, and the selected device's parameters (bank of 8). Mappings are momentary or toggle. It writes a `.zip` and a `.mmproj.json` project file. It has **no v3 support**, which is where our project can go further, as ChatGPT also pointed out.

### Correction 2026-11-15: the API reference pages (I had only read the guides)

- `sitemap.xml` counts **1741 reference pages for live12**, 364 for live11, 30 for live10 and 25 for live9. The Live 12 sidebar (`Devices & Framework (static surface)`) lists every controller plus the `_Framework`, `ableton.*`, `pushbase` … module trees, e.g.
  - `reference/live12/ableton.v2.base.abl_signal/`
  - `reference/live12/_Framework.ControlSurface/`
- **Static framework pages** give, per module: constants, classes with **bases**, and methods as **signatures with argument names only**. There are no defaults, docstrings or types. Example: `ControlSurface(Subject, SlotManager)`, `__init__(self, c_instance, *a, **k)`, `build_midi_map(self, midi_map_handle)`.
- **Runtime pages** exist for Live 12 too, e.g. `reference/live12/Live.Song.runtime/` (the sidebar hides them; `Live.runtime` is 404). They give Boost.Python signatures with argument types and return type, defaults where Live exposes them, one-line docstrings, and the listener triplets. Example: `create_midi_track( (Song)arg1 [, (object)Index=None]) -> Track`.
- **Which build?** None is stated anywhere. Pages exist for modules that are in 12.4.16 but not in the gluon 12.0-era repo (`ableton.v3.control_surface.components.zoom`, `device_provider`, `ableton.v3.live.detail_view_controller`). There are none for `MPK_mini_Plus_II` or `NKS_Connect`, which 12.4.16 has. So it is **a later Live 12.x than gluon's repo, earlier than 12.4.16**, and not a mirror of the repo. There is no Live 13.
- **Machine-readable:** MkDocs publishes `search/search_index.json` (about 34 MB, the text of every page). It could be ingested locally (licence: CC BY-NC-SA).
- **Glossary page** (`guides/glossary/`): "Element (a.k.a. control)" wraps one physical control. Inside a component, "controls" are the named logical roles (`play_button`) that a Layer wires to elements. Also defines Skin/SkinColor, MIDI map, Forwarding, c_instance and create_instance.
- **Verdict:** a real, structured API reference for an unspecified Live 12.x: names, bases and argument lists for the framework, typed signatures and docstrings for the LOM. It is a strong `documented` source and a cross-check for our extractor. Our own index still adds the exact build, 12.4.16 and 13.0b25, default values and framework docstrings.

### Contributing (2026-11-15)

The home page's "About the guides" section asks for contributions: "corrections and pull requests are very welcome". No repository is linked. gluon's public repos (github.com/gluon) contain no docs-site source; the two `…_MIDIRemoteScripts` repos hold only the decompiled scripts. So where PRs go is unknown; ask him (it goes in the planned mail, 0001 decision 15).

### Push 3 helper and `live_model` (2026-11-15)

- Every Live install ships `Contents/Helpers/Push3.app/Contents/Resources/python/` (12.4.16: 1272 `.pyc`), with `ableton/`, `_Generic`, `Push2/` and **`live_model/`**. Buying a Push 3 therefore gives no extra code: its scripts are already on disk. Its value would be as a test device for Ableton's most complex v3 script.
- **`live_model/Live/*.pyc` (64 files)** is a Python model of the `Live` module: `Song` (with the enums `Quantization`, `CaptureMode`, `CaptureDestination`, …, `Song.View`), `Track`, `Clip`, `Chain`, `MixerDevice` and the device classes (Roar, DrumCell, Transmute, …). Its methods take a `flip_object`, so it is a proxy model, not the C++ API itself. It is a `.pyc` source for LOM class, enum and property names per Live build, readable by our extractor; how far it matches the real `Live` module needs checking.

### Python 3.11 feasibility (2026-11-15)

`uv python install 3.11` installed CPython 3.11.12 (python-build-standalone). `marshal.load` reads Live 12.4.16 `.pyc` files after the 16-byte header. A class body's `co_names` shows the 12.4.16 `ControlSurfaceSpecification` attributes, including **`session_ring_selection_linking_type`**, which the gluon 12.0-era source lacks.

### remotescripts.blogspot.com (Hanz Petrov, 2010)

"Introduction to the Framework Classes" (March 2010) plus part 2 (April 2010) and posts in May and September 2010. It covers `_Framework` for Live 7/8 (Python 2), learned from decompiled 7.0.13 scripts: ControlSurface → components → elements, `ButtonElement(is_momentary, msg_type, channel, identifier)`, `Log.txt`/`log_message`, reloading by switching the slot to None and back, and the APC40/APC64-40 step sequencer mods. It is historical; the concepts still hold, but the code needs updating (a 2019 comment reports breakage on Live 10). Cite it as history, not as an API source.

## 2. gluon GitHub repos

- https://github.com/gluon/AbletonLive12_MIDIRemoteScripts (README says "Live 12.4", updated 2026-05-25/27)
- https://github.com/gluon/AbletonLive11_MIDIRemoteScripts
- Neither repo has a licence file. The code is decompiled from Ableton.
- Live 11 repo: "Uncompyled 11.2.11 MIDI Remote Scripts" (commit of 2023-06-08), decompyle3 3.8.0, py3.7 bytecode. 1183 files.
- Live 11 → Live 12 repo comparison (git tree SHAs): 1289 files in the Live 12 repo; 148 paths only in 12, 42 only in 11. **Every shared `_Framework`, `ableton/v2` and `ableton/v3` file differs.** Part of that is the different decompiler headers, but the code changes are real. For example, `ControlSurfaceSpecification` gained `display_specification=DisplaySpecification()`, `snap_track_offset`, `recording_method_type`, `send_goodbye_messages_last`, `create_mappings_function`, `component_map`, `parameter_bank_definitions/size` and the parameter sensitivities. Added in v3:
  - the `mode/` package (behaviour, mode, modes, selector)
  - `display/` (event_signal, notifications, state, text, view)
  - components: active_parameter, clipboard, grid_resolution, loop_selector, note_editor, paginator, playhead, recording, step_sequence
  - elements: button_matrix, discrete_values, lockable_button, lockable_combo, touch
  - `component_map.py`, `control_surface_mapping.py`, `layer.py`, `instrument_finder.py`, `ableton/v3/live/`
  - `ableton/v2/.../drift_decoration.py`, `roar_decoration.py`

  `ableton/v3/base` exists only in 11 (merged elsewhere later). The new controllers in the 12 repo include APC64, Push2, Move, Launch_Control_XL_3, Komplete_Kontrol_S_Mk3, KeyLab_Essential_mk3, Launchkey_MK4 and Keystage.
- What's actually in the "Live 12" repo, from the file headers:
  - `_Framework/*`, `ableton/v2/*`, `ableton/v3/*`: `uncompyle6 3.9.1`, "bytecode version base 3.7.0", compiled 2024-03-09/11. That is a **Live 12.0-era** snapshot (presumably 12.0 still shipped py3.7; every install on this Mac, 12.4.x and 13.0b, is 3.11). It is about 2.5 years older than the installed 12.4.16.
  - `Launchkey_MK4`, `Launch_Control_XL_3`, `Launch_Control_3`, `Launchkey_Mini_MK4`, `Osmose(_CE)`, `KeyLab_mk3`, `MPK_mini_IV`, `MPK_mini_Plus`, `Move`: "Decompiled with pycdc from Ableton Live 12 (Python 3.11). Some functions may be partial."
- **Local clones (2026-11-15):** `reference/gluon-live11` and `reference/gluon-live12`, shallow clones, git-ignored via `/reference/`.
  - gluon-live11: 1150 `.py` files; 4 contain decompiler failure markers.
  - gluon-live12: 1271 `.py` files, 47 of them from pycdc; 78 contain failure markers. Most are in the new pycdc controllers (Launch_Control_XL_3 10, Move 8, Launchkey_MK4 4, MPK_mini_IV 3, KeyLab_mk3 3); the rest are pushbase 6, ableton/v2 5, ableton/v3 5 and _Framework 4.
  - For v3 bodies, prefer the uncompyle6 framework files. Treat the pycdc controller scripts as structure only.
- Still useful: the v3 `ControlSurfaceSpecification` attributes are readable. Defaults from the 2024 version:
  `elements_type, control_surface_skin, display_specification, num_tracks=8, num_scenes=1, include_returns, include_master, right_align_non_player_tracks, snap_track_offset, include_auto_arming, link_session_ring_to_track_selection, link_session_ring_to_scene_selection, session_ring_component_type, target_track_component_type, auto_arm_component_type, device_provider_type, recording_method_type, feedback_channels, playing_feedback_velocity, recording_feedback_velocity, background_priority, identity_response_id_bytes, custom_identity_response, identity_request, identity_request_delay, hello_messages, goodbye_messages, send_goodbye_messages_last, create_mappings_function, component_map, parameter_bank_definitions, parameter_bank_size, continuous/quantized_parameter_sensitivity`.
  Verify these against 12.4/13 before relying on them.
- v3 module list, `ableton/v3/control_surface/`: banking_util, capabilities, colors, component, component_map, components/, consts, control_surface, control_surface_mapping, control_surface_specification, controls/, default_bank_definitions, default_skin, device_decorators, display/, elements/, elements_base, identification, instrument_finder, layer, legacy_bank_definitions, midi, mode/, parameter_info, parameter_mapping_sensitivities, session_ring_selection_linking, skin.

## 3. Local installs (metadata only: file names and sizes, nothing decoded)

| App | Version | `.pyc` in MIDI Remote Scripts | Python |
|---|---|---|---|
| Ableton Live 12 Suite | 12.4.16 (2026-10-30) | 1376 | 3.11 (`a70d0d0a`) |
| Ableton Live 12 Beta | 12.4.25b1 (2026-10-28) | 1376 | 3.11 |
| Ableton Live 13 Beta | 13.0b25 (2026-11-03) | (beta: kept local) | 3.11 |

Remote Script differences between 12.4.16 and 13.0b25: kept local while Live 13 is in beta (0001 Decision 15).

Tooling: Homebrew `python3` is 3.15 and `uv` is installed. **There is no Python 3.11.** Loading 3.11 `.pyc` code objects with `marshal` needs exactly 3.11 (`uv python install 3.11`, not done yet: it's a download, so it waits for your OK).

## 4. Landscape: existing Ableton MCPs

All of these control Live at runtime over a socket, and none of them helps write Remote Scripts:
- ahujasid/ableton-mcp (installed and connected here, port 9877): https://glama.ai/mcp/servers/ahujasid/ableton-mcp
- alaarab/livemcp: https://github.com/alaarab/livemcp
- opendining/ableton-mcp-server (exec-based, port 16619): https://glama.ai/mcp/servers/opendining/ableton-mcp-server
- jpoindexter/ableton-mcp: https://glama.ai/mcp/servers/jpoindexter/ableton-mcp

Real v3 examples are rare on GitHub. Most community scripts (ElectraOne, protocol0, MackieC4_P3, Beatstep) are `_Framework`/v2. The best v3 reference material is Ableton's own scripts (Launchkey_MK4, Launch_Control_XL_3, APC64, Move).

## 5. Review of ChatGPT's discovery toolkit (turn 2)

The design is sound. Fix these before using it:
1. `live_version = str(self.application)` records the object's repr. Use `Live.Application.get_application()` → `get_major_version()`, `get_minor_version()`, `get_bugfix_version()`, plus `get_build_id()`/`get_variant()` (new in Live 12).
2. `compare_runtime_api.flatten()` builds a set of member **dicts**. Dicts aren't hashable, so it raises `TypeError` on the first run. It also compares names only, so signature and kind changes are missed. Key members by name and compare signature and kind.
3. `inspect_live_bundle.py` finds 0 `.py` files, because the bundles ship only `.pyc`. As written it collects only hashes. Use 3.11 code-object extraction instead (names, argument names, defaults, docstrings from `co_consts`; no bodies), run with a 3.11 interpreter.
4. The probe only records modules that are already loaded. It should import each framework module from the file list explicitly, one at a time and wrapped in try/except, logging failures.
5. The probe's base-class order prefers v2. Use `_Framework.ControlSurface` (simplest, works 9–13) or v3.
6. Write output under the label/version so runs don't overwrite each other, e.g. `~/Documents/AbletonRemoteScriptDiscovery/<major.minor.bugfix-build>.json`.
7. Push2 needs a separate inventory pass under `Helpers/Push3.app`.

## 6. Proposed architecture

**Data pipeline** (this repo, `tools/`). The tools are public; the output is git-ignored.
- `extract_bundle.py` (Python 3.11 via uv): for each Live app, walk `MIDI Remote Scripts/**.pyc` and use `marshal.load` to read the code objects. From them collect classes, bases (from the class-body code where determinable), method names, argument names, defaults (from `co_consts` where possible), and docstrings. Do not decompile.
- `probe/` Remote Script: a runtime dump of the `Live` module plus imported framework modules, with real `inspect.signature`, MRO and docstrings.
- `build_index.py`: merges both sources into SQLite with tables `module`, `class`, `base`, `member(kind, signature, doc)` and `version`, plus FTS5 for search.
- `diff.py`: version diffs (12.4.16 vs 13.0b25, 12.4.16 vs 12.4.25b1).

**MCP server** (Python, FastMCP, stdio). Proposed tools, refined from ChatGPT's list:
- `search_api(query, version?, scope?)`, `get_class(name, version)` (with MRO and inherited members), `get_member(qualname, version)`
- `diff_versions(a, b, filter?)`
- `list_reference_scripts(framework=v3)`, `outline_reference_script(name, version)`: the structure of Ableton's own scripts (classes, the Specification attributes they set, component_map keys), not their bodies.
- `validate_script(path, target_version)`: static checks. `create_instance` is present; imports resolve in the target version's index; overridden methods match signatures; `disconnect` calls super; no work happens outside `component_guard`; the folder name has no spaces.
- `scaffold_script(spec)`: v3 or `_Framework` templates from a controller description (CC/notes, encoders, faders, pads, LED colours).
- Dev loop: `install_script(path)` (symlink into the User Library), `tail_log(version)`, and reload instructions.

**Skill** (`ableton-remote-script-skill`):
- `SKILL.md` covering the workflow: identify the controller → collect MIDI mappings → choose the framework (v3 for new work on Live 12+; `_Framework` for maximum compatibility) → scaffold → validate → install → read the log.
- References: lifecycle, v3 Specification and Elements, components/layers/modes, skins, gotchas, debugging. Written in our own words, citing Structure Void.
- Keep the third-party `ableton-lom` skill (mikecfisher) for LOM detail rather than duplicating it.

## 7. Open questions for you

1. Install Python 3.11 via `uv python install 3.11` so the bundle extractor can read the `.pyc` files?
2. Should the generated API index for 13.0b25 stay strictly local (beta NDA)? That's my assumption.
3. Target framework for scaffolding: v3 first, `_Framework` first, or both?
4. Do you have a specific controller to use as the first end-to-end test? `Faderfox_Universal_2` is already in your User Library.
5. Should the two repos stay separate (skill vs MCP), or should the skill live inside the MCP repo?
