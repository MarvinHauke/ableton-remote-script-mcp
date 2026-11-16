# Loading a script and reading the log

Read this at step 8 of the workflow, and whenever a script does not appear in Live, does nothing,
or throws.

## Only the user operates Live

Choosing a control surface, restarting Live and connecting hardware are the user's actions. Tell
them what to do in a short numbered list, wait until they say it is done, then read the log
yourself with `scripts/log.sh`. Never ask the user to paste the log.

## What to tell the user

After `scripts/install.sh <folder>` succeeded:

1. Quit and restart Live. Live keeps a script's modules once it has imported them: reopening a
   Set or choosing the script again runs the old code (`tested` in Live 12.4.16). Only a restart
   runs the new copy.
2. Settings → Link, Tempo & MIDI: in a free Control Surface slot choose `<Folder>`, and set its
   Input and Output to the controller's ports. For LED feedback the Output must be set.
3. Say when it is done (and press a few pads or buttons if the checklist needs it).

For a new version of a script already selected, steps 1 and 3 are enough: Live selects it again
when it starts.

## Reading the log

`scripts/log.sh --script <Folder>` reads `Log.txt` of the most recently run Live build
(`--build <build>` for another one) and shows, since Live last started:

- each traceback that passes through the script's folder, put back together (Live writes it in
  fragments)
- the script's own messages (`log_message`). The framework starts each with the control surface's
  class name (`documented`, decompiled 12.0 framework), so they are found only when the
  `ControlSurface` subclass carries the folder's name
- tracebacks whose frames are all in Live's shared packages (`_Framework`, `ableton`, …), under
  "framework-only": no frame names a script, so they may be this script's (a broken combo, a
  listener it set up) or another loaded script's. Read them when the script misbehaves
- how many tracebacks from other scripts or Live itself it left out

It exits 0 with no traceback, 1 with tracebacks of the script or framework-only ones, and 2 when
it finds no log.

Read it as follows:

| What the log shows | What it means |
|---|---|
| the script's start-up message, no traceback | it loaded; go on to the checklist |
| no message and no traceback | Live has not loaded it: the user has not selected it yet, the folder is not in the User Library's `Remote Scripts`, or Live was not restarted |
| a traceback in `create_instance` or `__init__` | it failed to load; Live shows no error to the user |
| a traceback later, after a button or pad was pressed | a listener or callback failed; the rest may still work |
| a traceback that names only Live's own scripts | not this script's problem unless its frames are in it |

## Tracebacks seen often

| Traceback | Cause and fix |
|---|---|
| `SyntaxError` at `import <folder-name>` | the folder name is not a Python name (a hyphen or a space); rename it (the validator's `folder-name` rule). `log.sh --script <folder-name>` finds it by the `import` line |
| `DependencyError: Required dependency register_component not provided` | an element or component was built outside `with self.component_guard():` |
| `AttributeError: '…Component' object has no attribute 'set_…'` | an invented method; look the class up and use a member it has |
| `TypeError: __init__() got an unexpected keyword argument` | an argument the constructor does not take; the lookup shows its signature |
| `AttributeError: 'NoneType' object has no attribute 'resource'` in `ComboElement`, with only `_Framework` frames | a combo wraps `None`, usually built from `matrix.get_button()`; build it from the button itself |
| `TypeError: int() argument must be … not 'NoneType'` in `send_value` | the script's own code sent an unset (`None`) LED value; turn the LED off for `None`, as the framework does |
| `ModuleNotFoundError` / `ImportError` | a module Live's Python does not have, or a sibling import without the dot; the validator catches these before loading |

## When nothing happens and there is no traceback

The script loaded but a mapping does not react. Check, in this order:

1. The ports: the controller's Input (and Output, for LEDs) in the script's Control Surface slot.
2. The device facts: the MIDI type, channel (counted from 0 in code) and number of the device control;
   a MIDI monitor shows what the controller really sends.
3. The session box: clip launch buttons act on the tracks and scenes inside the box drawn in
   Session View; an empty slot launches nothing.
4. An element used twice: the second `set_…` call takes the element away from the first component.
5. A different component holds the button: a combo with Shift, or a layer with a higher priority.

## When it works only sometimes

An exception in one listener can stop the listeners after it that the same message would have
reached: the framework calls them in turn without catching errors (`documented`, decompiled 12.0
framework), and while a combo threw on every Shift message, the script's other Shift listener
never saw a release (`tested` in Live 12.4.16). So read the framework-only tracebacks first, even when the symptom
looks unrelated.

1. **Log what the script sees.** Add `self.log_message(...)` to the handlers in question (each
   press, Shift's value, the box position before and after), let the user repeat it, and read the
   records with `log.sh`. Take them out once the cause is found.
2. **Record what the controller sends,** beside the log, when presses seem lost or doubled.
   ReceiveMIDI (a command-line tool; `receivemidi dev "<port>" ts`) reads the controller
   directly while Live runs. When the controller already sends fewer presses than the user made,
   the device loses them; when it sends them all and the script logs fewer, look inside Live.
3. **Count what the script sends.** A controller can lose button presses while it is flooded with
   LED messages. Override `_do_send_midi(self, midi_event_bytes)` for a moment to count messages
   a second and how many repeat the value a button already has, and log the count from
   `update_display()`. Many unchanged values mean the script resends LEDs it does not need to.
4. **Compare with Ableton's script for the same controller** on the same hardware, if Live has
   one. When it shows the same fault, suspect the controller and write that down as unconfirmed
   instead of working around it; when it does not, the difference is in the script.
