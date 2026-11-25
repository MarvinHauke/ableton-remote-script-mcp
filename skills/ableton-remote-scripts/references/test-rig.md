# Checking a script with the test rig

Read this at step 8 of the workflow when the script has more behaviour than a few presses show:
LEDs that follow Live, pages, modes, a sequencer. The test rig plays the controller to the
script over a virtual MIDI port and records what Live sends back, so each check runs in seconds
after every change, without the hardware. It is optional: without it, the user walks the
checklist on the controller.

It was used this way for a Faderfox UC4 mixer script and an APC mini mk1 drum sequencer in Live
12.4.16. It reads the script's elements from its own code, so it knows the controller only as
the script describes it: what the real hardware does (a display, a dropped press, LEDs it keeps
per group) stays the user's check.

## What the rig may do

- It sends MIDI only to its own port, `ARS Test Rig`, never to the controller's ports.
- It may change the open Set (a volume, a mute, an empty clip) but never saves it. Ask the user
  for a Set they use only for testing.
- Choosing the script in Live and restarting Live stay the user's steps (references/loading-and-logs.md).
  `scripts/rig.sh restart-live` quits Live with "Don't Save" and starts it again, and only does
  so while Live shows nothing but an unsaved Set named `Untitled`. Use it only when the user has
  said you may, in this conversation. It assumes Live 12 Suite in `/Applications` and build
  12.4.16: for another edition or build pass `--app` and `--build`. Never pass a `--title`
  other than the test Set's: the title is what keeps it away from a Set with the user's work.

## Set it up

1. The rig needs the tool's `rig` extra. If `scripts/rig.sh serve --help` fails, tell the user
   to install the tool with it: `uv tool install '<path to the clone>[rig]'`, or in the clone
   `uv sync --extra rig`.
2. Start `scripts/rig.sh serve` in the background and leave it running. It opens the port
   and keeps it open across Live restarts.
3. The user's step: in Live, Settings → Link, Tempo & MIDI, choose the script in a free Control
   Surface slot with `ARS Test Rig` as its Input and Output. No restart is needed for the port;
   a new version of the script still needs one.
4. Wait until the user says it is done. Only then send anything.

## A check file

`scripts/rig.sh elements <folder>` lists every element as the rig sees it
(`faders[0]  encoder  CC 48, channel 1`); a matrix's elements are `<matrix>[i]`, row by row from
0. An element it can't read (numbers computed by a helper) is listed as not read. Put
`checks.yaml` beside the script's files, one step per checklist item:

```yaml
script: .            # the script folder, relative to this file
build: 12.4.16       # the user's Live build
steps:
  - id: fader-1
    description: fader 1 sets track 1's volume and Live sends the value back
    send:
      - faders[0]: 99
      - faders[0]: 100
    expect:
      faders[0]: 100
    log: clean
  - id: step-1
    send:
      steps[0]: press
    expect:
      steps[0]: 1
  - id: session-box
    ask_user: Is there a box around tracks 1-8 in Session View?
```

- `send`: an element and a value; `press` is 127, then 0. `expect`: the last value Live sent to
  the element in the step (a value, a list, `any`, or `none`). `log: clean`: no new traceback of
  the script in `Log.txt`. `ask_user`: a question for what MIDI can't show; ask the user and
  note the answer. `depends_on` skips a step when an earlier one failed.
- **Live answers only a change, and late.** The same value twice gets no second reply, so send
  another value first (as `fader-1` does). Each step waits at least half a second for replies;
  `wait`, `quiet` and `timeout` change that per step or for the file.
- Every option and the Live state checks (with the AbletonMCP Remote Script in another slot:
  `state`, `do`, `requires`, `events`) are in `scripts/rig.sh run --help` and the tool's test
  rig page.

## Run it

`scripts/rig.sh run <folder>/checks.yaml`. Each step is passed, failed, skipped or asks the
user; a failure doesn't stop the run, and the report shows what was sent and what came back.
The full result goes to `checks.result.json` beside the check file.

- **A new version of the script:** install it with `--replace`, then Live must restart before the
  rig sees it. Without the restart the rig tests the old copy, and new controls get no reply.
- A step that fails on the rig may be the check, not the script: read what came back before you
  change code. Report each run in the report's checklist: passed, failed, asked, and what only
  the hardware can show.
