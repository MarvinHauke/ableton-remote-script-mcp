# The panel's protocol

`rig panel` speaks a small WebSocket protocol. Its own page uses it, and so can another
program, such as an editor that already draws your controller. This page is the contract:
protocol version **1**.

## Connecting

- Start `rig serve`, then `rig panel <script folder>`.
- Connect to `ws://127.0.0.1:9879/ws`. `--http` changes the port.
- Only pages served from your machine may connect. A browser sends the page's `Origin`, and the
  panel accepts only `localhost`, `127.0.0.1`, `::1` and names ending in `.localhost`, on any
  port. Everything else gets HTTP 403. A program outside a browser sends no `Origin` and is
  accepted.
- Messages are JSON text frames, one object per frame.

## What the panel sends

The first message is the **model**. Then the panel sends the last value it has seen for each
element and direction, marked `"replay": true`, and after that every message as it happens.

```json
{"type": "model", "protocol": 1, "script": "Faderfox_UC4", "folder": "…",
 "profile": "Faderfox UC4, setup SE17", "notice": "Parallel view: …",
 "rows": [[{"name": "faders", "elements": [
   {"name": "faders[0]", "kind": "encoder", "midi": "CC 40, channel 13",
    "display": "absolute", "feedback": true}]}]],
 "unresolved": []}
```

Check `protocol` first. A client built for version 1 should stop with a message if the number
is different.

**MIDI**, in either direction:

```json
{"type": "midi", "dir": "in", "by": null, "message": [188, 40, 81],
 "text": "CC 40 = 81, channel 13", "elements": ["faders[0]"], "value": 81}
```

- `dir` is seen from the controller. `in` is what Live sent to it (an LED, a value), `out` is
  what was played into Live.
- `by` says who played an `out` message: `panel` (a page or client of this panel) or `driver`
  (`rig run`, or another client of `rig serve`). It is `null` for `in`.
- `message` holds the raw bytes. A client that knows its device matches on these, not on the
  script's element names.
- `elements` lists the script's elements on that message, which may be none. `value` is the
  message's value (a note off counts as 0), or `null` when no element matches.

Live often answers a button press with a quick pair of values and then the settled one, about
40 ms later (seen in Live 12.4.16). Show the last value you get.

**Status:**

```json
{"type": "error", "text": "lost `rig serve`: …"}
{"type": "status", "text": "connected to `rig serve` again (`ARS Test Rig`)"}
```

An `error` also answers a request the panel couldn't carry out. The connection stays open.

## What a client sends

```json
{"op": "send", "message": [188, 40, 81]}
{"op": "play", "element": "faders[0]", "value": 81}
```

- `send` plays one raw MIDI message into Live. Each byte is 0–255. This is the op for a client
  that knows the device.
- `play` uses the script's element names:
  - a number 0–127;
  - steps for a relative encoder (−63 to 63, not 0);
  - `"press"`, which sends 127 and then 0.

A button is held for as long as you like: send its pressed message, then its released one.

Everything goes to the rig's virtual port and nowhere else. Nothing reaches a hardware
controller.
