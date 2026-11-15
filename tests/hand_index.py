"""Seam B fixture: a small API index written by hand (not extracted from Ableton's code).

Two builds. 12.4.90 holds:
- an inheritance chain across levels and framework generations, reached through re-exports:
  SessionRingComponent -> Component (v3) -> ControlManager (v2, re-exported twice) -> EventObject
- a star import (`Fake_Script.mixer`), a module-level alias (`ableton.v3.control_surface.BaseComponent`),
  a base named like the class itself (`Fake_Script.drums.DrumGroupComponent`), a nested class
  inherited from a base (`Fake_Script.display.Notifications.Device`), a diamond, an unresolved base,
  and a base from the C++ `Live` module with a proxy model in the Push 3 helper.
13.0b90 holds a smaller framework, where `Component.is_enabled` has changed and `NewThing` exists.

For the outline (step 5), 12.4.90 also holds two Remote Scripts with statement summaries:
- `Fake_V3` (v3): a Specification, Elements calling `self.add_*`, a mappings function, and the
  framework's ComponentMap with its defaults
- `Fake_Fw` (`_Framework`), built on the library `Fake_Lib`: a factory function, a `partial`
  alias, elements made in a comprehension, a component returned by a method, and layers
"""

from __future__ import annotations

from pathlib import Path

from ableton_remote_script_mcp.index_store import SCHEMA_VERSION, write_index

OLD, NEW = "12.4.90", "13.0b90"


def p(name, kind="positional_or_keyword", default=None):
    param = {"name": name, "kind": kind}
    if default is not None:
        param["default"] = default
    return param


SELF = p("self")
ARGS, KWARGS = p("a", "var_positional"), p("k", "var_keyword")


def method(line, *params, kind="method", decorators=(), docstring=None, statements=()):
    m = {"kind": kind, "line": line, "params": [SELF, *params] if kind == "method" else list(params),
         "decorators": list(decorators)}
    if docstring:
        m["docstring"] = docstring
    if statements:
        m["statements"] = list(statements)
    return m


def call(line, callee, *args, target=None, inside=None, under=(), **kwargs):
    st = {"line": line, "call": callee, "args": list(args), "kwargs": kwargs}
    if target:
        st["target"] = target
    if inside:
        st["inside"] = inside
    if under:
        st["under"] = list(under)
    return st


def store(line, target, value):
    return {"line": line, "store": target, "value": value}


def prop(line, setter=False):
    return {"kind": "property", "line": line, "params": [SELF], "decorators": ["property"], "setter": setter}


def attr(line, value):
    return {"kind": "attribute", "line": line, "value": value}


class Index:
    def __init__(self, build):
        self.build = build
        self.packages, self.modules, self.classes = {}, {}, {}

    def package(self, name, kind, framework=None, root="scripts", uses=()):
        key = name if root == "scripts" else f"{root}:{name}"
        self.packages[key] = {"name": name, "root": root, "kind": kind, "framework": framework,
                              "uses": list(uses), "source": f"MIDI Remote Scripts/{name}",
                              "live_build": self.build, "confidence": "observed"}

    def module(self, name, imports=None, star=(), members=None, root="scripts", package=False, docstring=None):
        key = name if root == "scripts" else f"{root}:{name}"
        src = "MIDI Remote Scripts" if root == "scripts" else "Helpers/Push3.app/Contents/Resources/python"
        self.modules[key] = {
            "name": name, "root": root, "package": package,
            "source": f"{src}/{name.replace('.', '/')}{'/__init__' if package else ''}.pyc",
            "imports": imports or {}, "star_imports": list(star), "members": members or {},
            "live_build": self.build, "confidence": "observed",
            **({"docstring": docstring} if docstring else {}),
        }
        return name

    def cls(self, module, qualname, bases=(), members=None, line=1, root="scripts", docstring=None, **extra):
        mkey = module if root == "scripts" else f"{root}:{module}"
        imports = self.modules[mkey]["imports"]
        resolved = []
        for b in bases:
            head = b.split(".")[0]
            resolved.append({"expr": b, "resolved": imports[head] + b[len(head):] if head in imports else None})
        key = f"{mkey}.{qualname}"
        self.classes[key] = {
            "name": qualname.rsplit(".", 1)[-1], "qualname": qualname, "module": module, "root": root,
            "line": line, "bases": resolved, "keywords": {}, "bases_parsed": True, "decorators": [],
            "members": members or {}, "source": self.modules[mkey]["source"],
            "live_build": self.build, "confidence": "observed",
            **({"docstring": docstring} if docstring else {}), **extra,
        }

    def write(self, index_dir: Path) -> None:
        index = {
            "schema": SCHEMA_VERSION, "live_build": self.build,
            "source": {"kind": "hand-written", "app": f"Ableton Live {self.build} (fixture)", "bundle_version": self.build},
            "created": "2026-11-15T00:00:00+00:00",
            "summary": {"packages": len(self.packages),
                        "scripts": sum(x["kind"] == "script" for x in self.packages.values()),
                        "modules": len(self.modules), "classes": len(self.classes), "errors": 0},
            "packages": self.packages, "modules": self.modules, "classes": self.classes, "errors": [],
        }
        write_index(index, index_dir)  # the statements go to their own file, as build-index writes them


def framework(ix: Index, changed: bool) -> None:
    ix.package("ableton", "framework")
    ix.module("ableton.v2.base.event")
    ix.cls("ableton.v2.base.event", "EventObject", ["object"], line=10, members={
        "disconnect": method(12),
        "register_disconnectable": method(15, p("disconnectable")),
    })
    ix.module("ableton.v2.control_surface.control", package=True,
              imports={"ControlManager": "ableton.v2.control_surface.control.control.ControlManager"})
    ix.module("ableton.v2.control_surface.control.control", imports={"EventObject": "ableton.v2.base.event.EventObject"})
    ix.cls("ableton.v2.control_surface.control.control", "ControlManager", ["EventObject"], line=20, members={
        "__init__": method(22, ARGS, KWARGS),
        "control_notifications_enabled": method(30),
    })
    ix.module("ableton.v3.control_surface.controls",
              imports={"ControlManager": "ableton.v2.control_surface.control.ControlManager"})
    ix.module("ableton.v3.control_surface.component", imports={"ControlManager": "ableton.v3.control_surface.controls.ControlManager"})
    enabled = method(40, p("explicit", default="True" if changed else "False"))
    ix.cls("ableton.v3.control_surface.component", "Component", ["ControlManager"], line=16, members={
        "num_layers": attr(18, "0"),
        "__init__": method(20, p("name", default="''"), ARGS, KWARGS),
        "disconnect": method(35),
        "is_enabled": enabled,
        "layer": prop(45, setter=True),
    })
    ix.module("ableton.v3.control_surface", package=True,
              imports={"Component": "ableton.v3.control_surface.component.Component"},
              members={"BaseComponent": attr(3, "Component")})


def old_build() -> Index:
    ix = Index(OLD)
    framework(ix, changed=False)
    ix.module("ableton.v3.control_surface.components.session_ring",
              imports={"Component": "ableton.v3.control_surface.Component"})
    ix.cls("ableton.v3.control_surface.components.session_ring", "SessionRingComponent", ["Component"], line=65,
           docstring="Moves a red box over the clip grid of the Session View.", members={
               "__init__": method(67, p("num_tracks", default="0"), p("num_scenes", default="0"), ARGS, KWARGS),
               "set_offsets": method(80, p("track_offset"), p("scene_offset")),
               "tracks_to_use": prop(90),
           })
    ix.module("ableton.v3.control_surface.components.drum_group", imports={"Component": "ableton.v3.control_surface.Component"})
    ix.cls("ableton.v3.control_surface.components.drum_group", "DrumGroupComponent", ["Component"], line=12,
           members={"set_pads": method(14, p("pads"))})
    ix.module("ableton.v3.control_surface.display.notifications")
    ix.cls("ableton.v3.control_surface.display.notifications", "Notifications", ["object"], line=5)
    ix.cls("ableton.v3.control_surface.display.notifications", "Notifications.Device", ["object"], line=6,
           members={"bank": attr(7, "'Bank'")})
    ix.cls("ableton.v3.control_surface.display.notifications", "DefaultNotifications", ["Notifications"], line=20)

    ix.package("_Framework", "framework")
    ix.module("_Framework.ControlSurfaceComponent")
    ix.cls("_Framework.ControlSurfaceComponent", "ControlSurfaceComponent", ["object"], line=8,
           members={"set_enabled": method(10, p("enable"))})

    ix.package("Fake_Script", "script", framework="ableton.v3")
    ix.module("Fake_Script", package=True, members={"create_instance": method(3, p("c_instance"), kind="function")})
    ix.module("Fake_Script.mixer", star=["_Framework.ControlSurfaceComponent"])
    ix.cls("Fake_Script.mixer", "MixerStrip", ["ControlSurfaceComponent"], line=4)
    ix.module("Fake_Script.drums", imports={"DrumGroupComponent": "ableton.v3.control_surface.components.drum_group.DrumGroupComponent"})
    ix.cls("Fake_Script.drums", "DrumGroupComponent", ["DrumGroupComponent"], line=6,
           members={"set_pads": method(8, p("pads"))})
    ix.module("Fake_Script.display",
              imports={"DefaultNotifications": "ableton.v3.control_surface.display.notifications.DefaultNotifications"})
    ix.cls("Fake_Script.display", "Notifications", ["DefaultNotifications"], line=4)
    ix.cls("Fake_Script.display", "Notifications.Device", ["DefaultNotifications.Device"], line=5)
    ix.module("Fake_Script.diamond", imports={"BaseComponent": "ableton.v3.control_surface.BaseComponent"})
    ix.cls("Fake_Script.diamond", "Top", ["BaseComponent"], line=1, members={"hello": method(2)})
    ix.cls("Fake_Script.diamond", "Left", ["Top"], line=4, members={"hello": method(5)})
    ix.cls("Fake_Script.diamond", "Right", ["Top"], line=7, members={"hello": method(8), "right_only": method(9)})
    ix.cls("Fake_Script.diamond", "Bottom", ["Left", "Right"], line=11)
    ix.module("Fake_Script.broken")
    ix.cls("Fake_Script.broken", "Orphan", ["Mystery"], line=3, members={"orphaned": method(4)})
    ix.module("Fake_Script.listener", imports={"Live": "Live"})
    ix.cls("Fake_Script.listener", "SongProxy", ["Live.Song.Song"], line=3)

    outline_scripts(ix)

    ix.package("live_model", "library", root="push3-helper")
    ix.module("live_model.Live.Song", root="push3-helper")
    ix.cls("live_model.Live.Song", "Song", [], line=177, root="push3-helper", proxy_model=True,
           proxy_of="Live.Song.Song", members={"tempo": prop(180, setter=True)})
    return ix


def outline_scripts(ix: Index) -> None:
    """The framework classes an outline needs, and two Remote Scripts built on them."""
    V3 = "ableton.v3.control_surface"
    ix.module(f"{V3}.elements_base")
    ix.cls(f"{V3}.elements_base", "ElementsBase", [], line=10, members={
        "__init__": method(12, p("global_channel", default="0"), ARGS, KWARGS),
        "add_button": method(20, p("identifier"), p("name"), KWARGS),
        "add_button_matrix": method(30, p("identifiers"), p("base_name"), p("channels", default="None"), ARGS, KWARGS),
    })
    ix.module(f"{V3}.control_surface", imports={"EventObject": "ableton.v2.base.event.EventObject"})
    ix.cls(f"{V3}.control_surface", "ControlSurface", ["EventObject"], line=5, members={"setup": method(9, statements=[
        store(10, "self.component_map['Background']", "self._background"),
    ])})
    ix.module(f"{V3}.control_surface_specification")
    ix.cls(f"{V3}.control_surface_specification", "ControlSurfaceSpecification", [], line=3, members={
        "elements_type": attr(4, "None"),
        "num_tracks": attr(5, "1"),
        "component_map": attr(6, "{}"),
        "create_mappings_function": method(7, kind="function"),
    })
    ix.module(f"{V3}.components", imports={"Component": f"{V3}.Component"})
    for line, name in ((10, "MixerComponent"), (20, "SessionComponent"), (30, "TransportComponent")):
        ix.cls(f"{V3}.components", name, ["Component"], line=line)
    ix.module(f"{V3}.component_map", imports={
        "partial": "functools.partial",
        **{n: f"{V3}.components.{n}" for n in ("MixerComponent", "SessionComponent", "TransportComponent")},
    })
    ix.cls(f"{V3}.component_map", "ComponentMap", ["dict"], line=8, members={
        "_create_component_map": method(20, p("specification"), statements=[
            store(21, "self['Mixer']", "MixerComponent"),
            call(22, "partial", "SessionComponent", target="self['Session']", snap="specification.snap"),
            store(23, "self['Transport']", "TransportComponent"),
            call(24, "self.update", "specification.component_map"),
        ]),
    })

    ix.package("Fake_V3", "script", framework="ableton.v3")
    ix.module("Fake_V3", package=True, imports={
        "ControlSurface": f"{V3}.control_surface.ControlSurface",
        "ControlSurfaceSpecification": f"{V3}.control_surface_specification.ControlSurfaceSpecification",
        "Elements": "Fake_V3.elements.Elements",
        "create_mappings": "Fake_V3.mappings.create_mappings",
        "SessionComponent": f"{V3}.components.SessionComponent",
        "TransportComponent": f"{V3}.components.TransportComponent",
    }, members={"create_instance": method(30, p("c_instance"), kind="function", statements=[
        call(31, "FakeV3", specification="Specification", c_instance="c_instance", target="return"),
    ])})
    ix.cls("Fake_V3", "Specification", ["ControlSurfaceSpecification"], line=10, members={
        "elements_type": attr(11, "Elements"),
        "num_tracks": attr(12, "8"),
        "component_map": attr(13, "{'Session': SessionComponent, 'Looper': LooperThing}"),
        "create_mappings_function": attr(14, "create_mappings"),
        "led_brightness": attr(15, "3"),
    })
    ix.cls("Fake_V3", "FakeV3", ["ControlSurface"], line=20, members={"setup": method(21, statements=[
        call(22, "super().setup"),
        call(23, "TransportComponent", target="self.component_map['Clock']", is_enabled="False"),
    ])})
    ix.module("Fake_V3.elements", imports={"ElementsBase": f"{V3}.elements_base.ElementsBase"})
    ix.cls("Fake_V3.elements", "Elements", ["ElementsBase"], line=5, members={
        "__init__": method(6, ARGS, KWARGS, statements=[
            call(7, "super().__init__", "*a", **{"**": "k"}),
            call(8, "self.add_button", "98", "'Shift_Button'", msg_type="MIDI_NOTE_TYPE"),
            call(9, "self.add_button_matrix", "[range(36, 44)]", "'Pads'", channels="9"),
            call(10, "self.not_a_framework_method", "1"),
        ]),
    })
    ix.module("Fake_V3.mappings", members={"create_mappings": method(3, p("control_surface"), kind="function", statements=[
        call(5, "dict", target="mappings['Session']", clip_launch_buttons="'pads'"),
        call(6, "dict", target="mappings['Pad_Modes']", mode_selection_control="'shift_button'",
             session="dict(component='Session', clip_launch_buttons='pads')",
             drum="dict(component='Drum_Group', matrix='pads')", note="None",
             priority="HIGH_PRIORITY"),
    ])})

    ix.module("_Framework.ControlElement")
    ix.cls("_Framework.ControlElement", "ControlElement", ["object"], line=4)
    ix.module("_Framework.ButtonElement", imports={"ControlElement": "_Framework.ControlElement.ControlElement"})
    ix.cls("_Framework.ButtonElement", "ButtonElement", ["ControlElement"], line=6)
    ix.module("_Framework.ButtonMatrixElement", imports={"ControlElement": "_Framework.ControlElement.ControlElement"})
    ix.cls("_Framework.ButtonMatrixElement", "ButtonMatrixElement", ["ControlElement"], line=6)
    ix.module("_Framework.SessionComponent", imports={
        "ControlSurfaceComponent": "_Framework.ControlSurfaceComponent.ControlSurfaceComponent"})
    ix.cls("_Framework.SessionComponent", "SessionComponent", ["ControlSurfaceComponent"], line=9)
    ix.module("_Framework.TransportComponent", imports={
        "ControlSurfaceComponent": "_Framework.ControlSurfaceComponent.ControlSurfaceComponent"})
    ix.cls("_Framework.TransportComponent", "TransportComponent", ["ControlSurfaceComponent"], line=7)
    ix.module("_Framework.Layer")
    ix.cls("_Framework.Layer", "Layer", ["object"], line=3)
    ix.module("_Framework.ControlSurface")
    ix.cls("_Framework.ControlSurface", "ControlSurface", ["object"], line=5, members={"disconnect": method(9)})

    ix.package("Fake_Lib", "library", framework="_Framework")
    ix.module("Fake_Lib", package=True)
    ix.module("Fake_Lib.utils", imports={"ButtonElement": "_Framework.ButtonElement.ButtonElement"},
              members={"make_button": method(3, p("channel"), p("identifier"), KWARGS, kind="function", statements=[
                  call(4, "ButtonElement", "True", "MIDI_NOTE_TYPE", "channel", "identifier", **{"**": "k"},
                       target="return"),
              ])})
    ix.module("Fake_Lib.base", imports={
        "ControlSurface": "_Framework.ControlSurface.ControlSurface",
        "ButtonMatrixElement": "_Framework.ButtonMatrixElement.ButtonMatrixElement",
        "SessionComponent": "_Framework.SessionComponent.SessionComponent",
        "TransportComponent": "_Framework.TransportComponent.TransportComponent",
        "Layer": "_Framework.Layer.Layer",
        "make_button": "Fake_Lib.utils.make_button",
        "partial": "functools.partial",
    })
    ix.cls("Fake_Lib.base", "LibSurface", ["ControlSurface"], line=12, members={
        "HAS_TRANSPORT": attr(13, "True"),
        "__init__": method(14, p("c_instance"), statements=[
            call(15, "self.component_guard"),
            call(16, "self._create_controls"),
            call(17, "self._create_session", target="self._session"),
            call(18, "self._create_transport", target="self._transport", under=["if self.HAS_TRANSPORT"]),
        ]),
        "_create_transport": method(26, statements=[
            call(27, "TransportComponent", target="return", name="'Transport'",
                 layer="Layer(play_button=self._play_button)"),
        ]),
        "_create_controls": method(20, statements=[
            call(21, "partial", "make_button", target="make_pad", skin="self._skin"),
            call(22, "make_button", "0", "98", target="self._shift_button", name="'Shift_Button'"),
            call(23, "make_pad", "0", "36 + i", inside="<listcomp>", name="'Pad_%d' % i"),
            store(23, "self._pads", "[… for … in range(8)]"),
            call(24, "ButtonMatrixElement", target="self._matrix", name="'Matrix'", rows="[self._pads]"),
            call(25, "make_button", "0", "91", target="self._play_button", name="'Play_Button'",
                 under=["if self.HAS_TRANSPORT"]),
            call(25, "make_button", "0", "92", target="self._mode_button", name="'Mode_Button'",
                 under=["for … in range(2)", "if self.has_modes()"]),
        ]),
        "_create_session": method(30, statements=[
            call(31, "SessionComponent", "8", "1", target="return", name="'Session'",
                 layer="Layer(clip_launch_buttons=self._matrix)"),
        ]),
    })
    ix.package("Fake_Fw", "script", framework="_Framework", uses=["Fake_Lib"])
    ix.module("Fake_Fw", package=True, imports={"FwSurface": "Fake_Fw.surface.FwSurface"},
              members={"create_instance": method(3, p("c_instance"), kind="function", statements=[
                  call(4, "FwSurface", "c_instance", target="return")])})
    ix.module("Fake_Fw.surface", imports={
        "LibSurface": "Fake_Lib.base.LibSurface", "make_button": "Fake_Lib.utils.make_button", "Layer": "_Framework.Layer.Layer"})
    ix.cls("Fake_Fw.surface", "FwSurface", ["LibSurface"], line=6, members={
        "HAS_TRANSPORT": attr(7, "False"),
        "_create_controls": method(8, statements=[
            call(9, "super()._create_controls"),
            call(10, "make_button", "0", "64", target="self._stop_button", name="'Stop_Button'"),
        ]),
        "_create_session": method(14, statements=[
            call(15, "super()._create_session", target="session"),
            call(16, "Layer", target="session.layer", stop_all_clips_button="self._stop_button", priority="1"),
            {"line": 17, "call": "session", "args": [], "kwargs": {}, "target": "return"},
        ]),
    })


def new_build() -> Index:
    ix = Index(NEW)
    framework(ix, changed=True)
    ix.module("ableton.v3.control_surface.new_thing", imports={"Component": "ableton.v3.control_surface.Component"})
    ix.cls("ableton.v3.control_surface.new_thing", "NewThing", ["Component"], line=3)
    return ix


def write_hand_index(index_dir: Path) -> Path:
    old_build().write(index_dir)
    new_build().write(index_dir)
    return index_dir
