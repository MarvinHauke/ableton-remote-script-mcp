# Framework basics from Hanz Petrov's blog, and decompiling

Date: 2026-11-16. Question (user): what do Hanz Petrov's four "Introduction to the Framework
Classes" posts (remotescripts.blogspot.com, 2010) teach that our APC mini mk1 script and the skill
should adopt; what do Structure Void's guides add for reliable scripts; which other sources are
worth pulling in; and should `morluto/rea` be used to decompile Live's `.pyc` files?

Everything below is in our own words. The blog posts are from 2010 (Live 7/8, Python 2); a tip
from them is `documented` at most and is checked against Live 12.4.16 before it goes into the
skill.

## The four posts

- Part 1 (2010-03): a first script, `create_instance`, elements, the session, mixer and transport
  components, `Log.txt`.
- Part 2 (2010-04): subclassing Ableton's own scripts (APC40/APC20) to change single methods.
- Part 3 (2010-05): an APC40 extension with a Shift-style mode and its own components.
- Part 4 (2010-09, not 2010-05 as first linked): one mapping file for several controllers, and
  linked sessions ("combination mode") that share one coloured box.

## What still holds, and where it stands for us

| Tip from the posts | Status for Live 12.4.16 | For us |
|---|---|---|
| Read `Log.txt` first; fix one error at a time, since one can hide the next | holds | in the skill (`log.sh`) |
| Name every component and element | holds; the framework and Max for Live use the names | our script does it |
| Keep the MIDI numbers in one place, apart from the logic | holds | our script's device-fact constants |
| Build each element once; one MIDI message must belong to one element only | `documented` (the posts); not checked in 12.4.16 | worth a validator rule (see below) |
| Wrap setup in `set_suppress_rebuild_requests(True/False)` | the method is gone in later Live versions (a reader on Live 10 reports it missing); `component_guard()` does this job now | already covered by `component_guard()` |
| Session first, then the mixer, then `session.set_mixer(mixer)` | holds | our order |
| Use a MIDI monitor to see what the hardware really sends before blaming the script | holds | in the skill since 2026-11-16 (ReceiveMIDI) |
| Reload by switching the slot to None and back | not for code changes in 12.4.16: Live keeps the imported modules, only a restart loads new code (tested 2026-11-15) | in the skill |
| Some controllers need `set_invert_mute_feedback` | holds (`set_invert_mute_feedback`, `observed` on `ChannelStripComponent` in 12.4.16) | in the skill's table |
| Set the session's triggered and stop LED values to match the device | holds | done (items 10, 11) |
| On a mode change, turn the old LEDs off and give the controls back | holds; with layers the framework does the handing back | our `Unassigned` holder |
| Subclass a factory script to change one method | works, but ties the script to Ableton's internals, which change between builds | only as a last resort; we override one private method and say so |
| Shift as a flag checked in every callback | works, but combos with layers do this without hand-kept state | we use combos |
| Several session boxes need several script instances, or linked sessions | `SessionComponent` still has linking (`_is_linked`, `_link`, `observed` in 12.4.16) | not needed for the APC mini |

Nothing from the posts changes the APC mini script. One idea is worth taking up: a validator
rule that warns when two elements are built for the same MIDI type, channel and number, which
the posts name as a cause of a script that does not load.

## Structure Void's guides

Not read again here: the site answers automated fetches with 403, and the Chrome extension was
not connected. The sitemap lists 18 guide pages, among them `debugging`, `cookbook`,
`midi-message-flow`, `controller-colours` and `idea-to-script`, which the 2026-11-14 note did not
cover. Next time Chrome is connected, read those five for reliability tips, in particular what
`midi-message-flow` says about forwarding and MIDI map rebuilds, given the LED-traffic finding of
0001 decision 41.

## Other sources

- **Ableton's own scripts for similar hardware, through `outline`**: the most reliable source,
  because they run in exactly the build in question. The `OptimizedControlSurface` finding came
  from comparing with `APC_mini`.
- **gluon's decompiled 12.0 framework** (local, `reference/`): how most `documented` facts were
  checked on 2026-11-15/16.
- **Forum threads** (Ableton forum, KVR): `documented` at most, case by case.

## `morluto/rea`

`rea` (MIT licence, TypeScript, an MCP server and command-line tool) is a general reverse
engineering kit for native binaries, JavaScript and Electron apps, .NET, Android and websites.
For a `.pyc` it has `inspect_python_pyc`, which reads the header and lists the nested code
objects with their bytecode. It does not decompile to Python source.

So it adds nothing to our extractor, which already reads the code objects of Live's `.pyc` files
directly (names, signatures, statement summaries). Recommendation: do not add it. A real
decompiler would be a separate question: Python 3.11 decompilers are incomplete (gluon's pycdc
files are partial), and whether we may decompile Live's code at all is part of the question to
Ableton already in STATUS. Any decompiled code would stay local, as `reference/` does.
