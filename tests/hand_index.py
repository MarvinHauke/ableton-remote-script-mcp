"""Seam B fixture: a small API index written by hand (not extracted from Ableton's code).

Two builds. 12.4.90 holds:
- an inheritance chain across levels and framework generations, reached through re-exports:
  SessionRingComponent -> Component (v3) -> ControlManager (v2, re-exported twice) -> EventObject
- a star import (`Fake_Script.mixer`), a module-level alias (`ableton.v3.control_surface.BaseComponent`),
  a base named like the class itself (`Fake_Script.drums.DrumGroupComponent`), a nested class
  inherited from a base (`Fake_Script.display.Notifications.Device`), a diamond, an unresolved base,
  and a base from the C++ `Live` module with a proxy model in the Push 3 helper.
13.0b90 holds a smaller framework, where `Component.is_enabled` has changed and `NewThing` exists.
"""

from __future__ import annotations

import json
from pathlib import Path

from ableton_remote_script_mcp.index_store import SCHEMA_VERSION

OLD, NEW = "12.4.90", "13.0b90"


def p(name, kind="positional_or_keyword", default=None):
    param = {"name": name, "kind": kind}
    if default is not None:
        param["default"] = default
    return param


SELF = p("self")
ARGS, KWARGS = p("a", "var_positional"), p("k", "var_keyword")


def method(line, *params, kind="method", decorators=(), docstring=None):
    m = {"kind": kind, "line": line, "params": [SELF, *params] if kind == "method" else list(params),
         "decorators": list(decorators)}
    if docstring:
        m["docstring"] = docstring
    return m


def prop(line, setter=False):
    return {"kind": "property", "line": line, "params": [SELF], "decorators": ["property"], "setter": setter}


def attr(line, value):
    return {"kind": "attribute", "line": line, "value": value}


class Index:
    def __init__(self, build):
        self.build = build
        self.packages, self.modules, self.classes = {}, {}, {}

    def package(self, name, kind, framework=None, root="scripts"):
        key = name if root == "scripts" else f"{root}:{name}"
        self.packages[key] = {"name": name, "root": root, "kind": kind, "framework": framework,
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
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / f"live-{self.build}.json").write_text(json.dumps(index, indent=1))


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

    ix.package("live_model", "library", root="push3-helper")
    ix.module("live_model.Live.Song", root="push3-helper")
    ix.cls("live_model.Live.Song", "Song", [], line=177, root="push3-helper", proxy_model=True,
           proxy_of="Live.Song.Song", members={"tempo": prop(180, setter=True)})
    return ix


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
