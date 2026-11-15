# ableton-remote-script-mcp

Tools for writing **MIDI Remote Scripts** for Ableton Live: the Python packages Live loads to
drive a hardware controller (a *control surface*).

!!! note "Unofficial"
    This project is not made, endorsed or supported by Ableton. Ableton publishes no reference for
    its control-surface framework; the tool reads everything from the Live you have installed.

## What it is

The project has three parts. The first two work today:

- **API index.** One command reads the Remote Script framework from your installed Live and
  records its modules, classes, members and signatures, separately for each Live build. You look
  classes up, search them, outline how one of Live's own scripts is put together, and check your
  own script folder against a build before you load it in Live. Two more commands copy a script
  into your User Library and read Live's log for its errors.
- **Skill.** Guidance that walks a coding agent through writing a script from those facts:
  collect the controller's MIDI numbers, look up every framework name, check the script, install
  it, and read Live's log once you have loaded it. Its first version covers `_Framework`
  scripts; the `ableton.v3` guidance comes next.
- **MCP server.** The same lookups as tools an agent can call. Not built yet.

Every answer names the Live build it comes from and how sure it is (its *fact confidence*), so
you can tell a fact that is in your Live from one that is only written somewhere.

## Your Live stays on your machine

The index is built on your computer from your Live install and is never uploaded or published.
This site shows no output from a real index; examples use small scripts we wrote ourselves.

## Where to go next

- [Getting started](getting-started.md): install it and build your first index.
- [How it works](how-it-works.md): what the index holds and what each answer means.
- [CLI reference](reference/cli.md): every command and option.
- [Known limits](limits.md): what it can't tell you yet.

## Credits

Julien Bayle's [Structure Void](https://midiremotescripts.structure-void.com) documentation of
the MIDI Remote Scripts is the best public guide to the framework, and the words this project uses
for it follow his glossary.
