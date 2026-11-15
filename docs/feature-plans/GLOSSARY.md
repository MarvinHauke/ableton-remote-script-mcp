# Remote Script assistant

The shared language for the plans, the code, the skill and the MCP tools. Framework words follow
Ableton's own class names and Structure Void's glossary
(`midiremotescripts.structure-void.com/guides/glossary/`).

## Language

### Live and its scripts

**Remote Script**:
A Python package in a `Remote Scripts` folder that Live loads as a control surface; its
`__init__.py` defines `create_instance(c_instance)`.
_Avoid_: MIDI script, controller script, plugin

**Control surface**:
One Remote Script selected in a slot under Settings → Link, Tempo & MIDI; at runtime one
`ControlSurface` instance.

**Live build**:
One exact Live version an API fact belongs to, e.g. `12.4.16`, `13.0b25`.
_Avoid_: Live version (when the exact build matters)

**LOM** (Live Object Model):
The object tree of the open Set exposed by the C++ `Live` module (`Song`, `Track`, `Clip`, `Device`, …).

**Library package**:
A shared package in the Remote Scripts folder that is neither a Remote Script nor the framework,
used by several scripts (`_Generic`, `pushbase`, `novation`).

**Re-export**:
A name a module binds by importing it from where it is defined, so scripts can import it from a
shorter path (`ableton.v3.control_surface.Component` for `….component.Component`).

**Push 3 helper**:
The Python inside Live's bundle that Push 3 standalone runs (`Helpers/Push3.app`): its own copies of
`ableton`, `Push2` and `_Generic`, plus `live_model`.

**Proxy model**:
`live_model`, the Push 3 helper's pure-Python model of the `Live` module. Its classes mirror the LOM
(`live_model.Live.Song.Song` for `Live.Song.Song`) but are not Live itself.

**User Library**:
`~/Music/Ableton/User Library/Remote Scripts/`, where user scripts are installed.

### The framework

**Framework generation**:
One of `_Framework`, `ableton.v2`, `ableton.v3`: the three generations of Ableton's
control-surface framework.

**Element**:
A wrapped physical knob, fader, button or pad and its MIDI identity: type, channel, number
(`ButtonElement`, `EncoderElement`, `ButtonMatrixElement`).
_Avoid_: control (for the physical thing)

**Control**:
A named, logical slot on a component (`play_button`, `ButtonControl`, `EncoderControl`) that a layer
binds to an element.
_Avoid_: element, button (for the slot)

**Device control**:
A physical knob, fader, button or pad as the hardware's own manual names it (e.g. the UC4's `Enc1`),
before it is wrapped as an element.

**Component**:
A unit of behaviour (`SessionComponent`, `MixerComponent`, …) that talks to the LOM.

**Layer**:
The mapping from elements to a component's controls.

**Mode**:
A named arrangement of layers and components, switched by `ModesComponent`.

**Specification**:
A `ControlSurfaceSpecification` subclass: the declarative description of a v3 script.

**Component map**:
In a v3 script, the names (`Session`, `Mixer`, …) under which the framework builds components.
The framework brings default names; a Specification and the script's own setup can add or replace
names.

**Mappings**:
In a v3 script, what the Specification's mappings function returns: for each component-map name,
which element goes to which of the component's controls, or which modes a modes component has.

**Reference script**:
One of Ableton's own Remote Scripts (e.g. `Launchkey_MK4`), read for its structure.

**Outline**:
A reference script's structure without its function bodies: its classes and their roles, the
Specification fields it sets, its component map and mappings, and the elements, components and
layers it creates, including those it inherits from other Remote Scripts and libraries.

### This project

**API index**:
The per-Live-build record of modules, classes, members, signatures and docstrings, extracted from
the installed bundle and a runtime dump.

**Fact confidence**:
`observed` (in the API index of a Live build), `tested` (used by a script that loaded in that
build) or `documented` (secondary source only).

**Statement summary**:
What the API index records of a function body: the calls it makes, where each result is stored,
and the values it stores into attributes and subscripts, each with the conditions, loops and
exception handlers it runs under. It does not execute anything, so whether a conditional call runs
is decided only where a script's own class attributes settle it.

**Origin**:
For a member a class has, the class along its MRO that defines it: the class itself or the base
it inherits the member from. A member that hides one of the same name further along the MRO
overrides it.
