# Testing a script with the test rig

The **test rig** plays your controller to a Remote Script over a virtual MIDI port and records
what Live sends back. It checks a script in seconds, without the hardware, after every change. A
**check file** lists the steps: what to send, by the element names your script uses, and what
Live should answer.

The rig sends MIDI only to its own virtual port, never to your hardware's ports. It may change
the open Set (a volume, a mute, a new empty clip) but never saves it, so run it in a Set you use
for testing.

## Set it up

Install the rig's extra once:

```sh
uv sync --extra rig
```

Start the port holder in a terminal of its own and leave it running:

```sh
uv run ableton-remote-script-mcp rig serve
```

It opens a virtual MIDI port named `ARS Test Rig`. In Live, under **Settings → Tempo & MIDI**,
pick your script in a free Control Surface slot, with `ARS Test Rig` as its Input and Output.
Live lists the port as soon as it exists; you don't need to restart Live.

## After a script change

Live loads a script's code only when it starts, so a script change needs a Live restart. Keep
`rig serve` running while you restart Live. The slot keeps `ARS Test Rig` and the script, and
reconnects by itself. If Live starts before `rig serve`, the slot shows `ARS Test Rig` greyed out
and reconnects within a few seconds of `rig serve` starting. (Both seen in Live 12.4.16.)

`rig restart-live` does the restart for you:

```sh
uv run ableton-remote-script-mcp rig restart-live --wait-for "ready"
```

It works only while Live shows nothing but an unsaved Set named `Untitled`, the one Live opens
from a template, and otherwise does nothing. If Live asks whether to save, it answers "Don't
Save", never "Save". It then starts Live again and waits until Live's log shows the new session
(and, with `--wait-for`, a message from your script). It needs the Accessibility permission for
your terminal (System Settings → Privacy & Security → Accessibility).

## See your controller as the rig sees it

```sh
uv run ableton-remote-script-mcp rig elements path/to/My_Script
```

This lists every element of the script with its MIDI message: `faders[0]  encoder  CC 40,
channel 13`. The rig reads the elements from the script's own code (a v3 Elements class), without
running it. A matrix's elements are `<matrix>[i]`, counted row by row from 0. An element whose
numbers can't be worked out without running the script is listed as not read.

## Write a check file

Put `checks.yaml` next to the script's files:

```yaml
script: .            # the script folder, relative to this file
build: 12.4.16       # the Live build whose index reads the script
steps:
  - id: fader-1
    description: fader 1 sets track 1's volume and Live sends the value back
    send:
      - faders[0]: 99
      - faders[0]: 100
    expect:
      faders[0]: 100
    log: clean
  - id: mute-1
    send:
      active_buttons[0]: press
    expect:
      active_buttons[0]: 0
  - id: session-box
    ask_user: Is there a box around tracks 1-8 in Session View?
```

- **`send`:** an element and a value. `press` sends 127, then 0, to a button. On a relative
  encoder a number is steps: `1` up, `-1` down. A raw message also works: `cc 13 40 100`.
- **`expect`:** the last value Live sent to an element during the step. Write a value, a list of
  values, `any`, or `none` for no reply at all.
- **`log: clean`:** no new traceback of the script in Live's `Log.txt` during the step.
- **`ask_user`:** a question for you, for what MIDI can't show, such as the session box.
- **`depends_on`:** skip this step if an earlier one failed.
- **Timing:** `wait` (at least 0.5 s by default), `quiet` and `timeout`, per step or for the
  whole file.

Two things Live does shape how a check is written:

- **It sends a value back only when the value changes.** Sending the same value twice gets no
  second reply, so send a different value first, as `fader-1` does above.
- **It sends a value back late,** after more than 150 ms. That's why every step listens for at
  least `wait` seconds.

## Run it

```sh
uv run ableton-remote-script-mcp rig run path/to/My_Script/checks.yaml
```

Each step is **passed**, **failed**, **skipped** (a step it depends on failed) or **ask the
user**. A failure doesn't stop the run. The report shows what was sent and what came back for
each failure. The full result, with every message, goes to `checks.result.json` next to the
check file. The exit code is 0 when no step failed and 1 when one did.

## With AbletonMCP: Live's state too

If the AbletonMCP Remote Script runs in another slot,
the rig also reads Live's state through its socket. It's an optional local aid: without it, the
rig works from MIDI and the log alone. The rig only talks to AbletonMCP 1.7.1, and only sends a
fixed list of read commands and simple Set changes. It never sends AbletonMCP's rating,
dataset-consent or browser commands.

```sh
uv run ableton-remote-script-mcp rig abletonmcp
```

This prints what the rig reads: the tempo and every track's volume, pan, mute, solo, arm, devices
and clips. Compare it with what Live shows.

Check files then take four more keys. Tracks, scenes, devices and parameters count from 1, as
Live shows them:

```yaml
requires:
  tracks: 8
  devices: [1]                    # track 1 has a device
  clips: [{track: 1, scene: 1}]   # created as an empty MIDI clip if missing
steps:
  - id: mute-1
    send:
      active_buttons[0]: press
    state:
      track 1: {mute: true}
    events:
      - {type: mute_changed, track: 1}
  - id: macro-to-encoder
    do:
      - set_device_parameter: {track: 1, device: 1, parameter: 2, value: 64}
    expect:
      rack_encoders[0]: 64
```

- **`requires`:** checked before the first step. The run stops with a list of what the Set lacks.
  It creates a missing clip on a MIDI track.
- **`state`:** `song`, `track N` or `track N device M` with the fields to compare. Numbers match
  within 0.005.
- **`events`:** a change AbletonMCP's listeners saw during the step.
- **`do`:** a change made in Live first, for the Live → controller direction: does the script
  show a change made in Live?

Without AbletonMCP, `do` steps are skipped, and their state and events are listed as not checked.

## Play it from a web page

`rig panel` shows the script's controller as a web page, so you can play the script without the
hardware:

```sh
uv run ableton-remote-script-mcp rig panel path/to/My_Script --open
```

It needs `rig serve` running and plays through its port. The page is at
`http://127.0.0.1:9879/`, on your machine only. Only pages served from your machine can connect
to it. A website open in your browser can't play into Live.

- **Buttons** are pads. They send 127 while you hold them and 0 when you let go, and light up
  with the value Live sends back.
- **Encoders** are sliders. A bipolar one shows its value from the centre. A relative one has −
  and + buttons; hold Shift for steps of 10.
- **Each control** shows the last value played into Live (↑) and the last value Live sent
  back (↓).
- **The log** at the bottom lists every message on the port, with the element it belongs to.

The page is a parallel view, and the rig's driver is in charge. While `rig run` plays a check
file, its messages show up on the page, marked "driver". A `device.yaml` in the script's folder
sets the rows (`layout`) and how values show (`display`). Without one, the page shows one row
per matrix, then the single elements. If you restart `rig serve`, the panel connects again by
itself.

## What the rig can't see

The rig sees MIDI, the log and, with AbletonMCP, Live's state. It can't see Live's screen (the
session box, the selection) or the hardware's own behaviour (its display, LEDs it keeps per
group, pickup). Those stay `ask_user` steps, or a load test on the hardware.
