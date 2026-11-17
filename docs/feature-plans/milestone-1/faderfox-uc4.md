# Milestone 1, part 2: the Faderfox UC4 script

Plan 0001 step 10. With the skill and its v3 references, Claude writes an `ableton.v3` script for
the user's Faderfox UC4, for the UC4's factory setup SE17 (Ableton, tracks 1–8). This page holds
the device facts, the behaviour checklist (Decision 29) and the results. The script is
[`examples/Faderfox_UC4/`](../../../examples/Faderfox_UC4/).

## Device facts

Source: the UC4 Editor (the user's own project, `~/Development/web/UC4_Editor`): its model of the
factory SE17 (`node tools/uc4-config.ts factory 17`) and its device page
(`docs/reference/uc4-device.md`, from Faderfox's manual, the factory `SndA` dump and the user's
panel photo). The UC4 architect (the UC4 Editor's agent) confirmed on 2026-11-16 that the
device's SE17 is factory: `dumps/2026-11-13-Sndc-SE17.syx` matches it byte for byte. **To put
SE17 back:** in setup mode (Shift + Edit twice), turn encoder 1 to SE17 and hold encoder 5's
push button until the bars run (`rESc`). Nothing is sent to the UC4 for this test.

Channels as the UC4 shows them (Ch13 = 12 in code). Every control sends 0–127; the green buttons
and push buttons are momentary (`btn`): the upper value on press, the lower on release.

| Group (printed name) | Controls | Messages |
|---|---|---|
| Faders 1–8 | fader per track | CC 40–47, Ch13, `SnAP` (sends after catching up with its last value) |
| Fader 9 (horizontal) | crossfader | CC 48, Ch14, `JMP` |
| Encoders: Send 1–4 | 8 encoders each | CC 0–7, 8–15, 16–23, 24–31, Ch13, absolute |
| Encoders: Track | 8 encoders | CC 56–63, Ch14; 4–5 relative (`CCr1`: 1 up, 127 down), 6–7 bipolar display |
| Encoders: Rack | 8 encoders | CC 48–55, Ch13, absolute |
| Encoders: Pan | 8 encoders | CC 32–39, Ch13, absolute, bipolar display |
| Encoders: Global | 8 encoders | CC 56–63, Ch13; 1, 2, 4, 5 relative (`CCr1`) |
| Push buttons: Track 3, 4 | 2 buttons | notes 122, 123, Ch14 (the same notes as green buttons Track 2 and 1) |
| Push buttons: Global 1–8 | 8 buttons | notes 120–127, Ch13 |
| Push buttons, other groups | — | `OFF`: send nothing |
| Green buttons: Launch, Stop, Active, Solo | 8 each | notes 64–71, 72–79, 104–111, 96–103, Ch13 |
| Green buttons: Record, Monitor, Select | 8 each | notes 80–87, 88–95, 56–63, Ch13 |
| Green buttons: Track | 8 | notes 123 122 127 126 124 125 120 121 (left to right), Ch14 |

- **Groups are switched on the UC4:** Shift + encoder n selects encoder group n (its name on the
  display), Shift + green button n selects green button group n (shown by the green LEDs). The
  script maps every group at once; only the selected group's controls send.
- **Feedback:** the encoders' displays (`Std`, `bPoL`) and the green LEDs (`EXt`) follow
  messages Live sends on the same channel and number (the manual). Untested, so on the
  checklist: that a note with velocity above 0 lights a green LED and 0 turns it off, and that an
  encoder's own value follows an incoming CC.
- **The same numbers, other types:** Global encoders (CC 56–63, Ch13) and the Select buttons
  (notes 56–63, Ch13) share channel and numbers; a CC and a note are different messages.
- **Which Global control is which printed function** (`coarse Tempo fine`, `nudge`,
  `play – global – stop`, `Track Cue`, `Quant Scene`, `stop – scene – start`,
  `record – global – view`, `Pan Master`) is not known. The script's choice is below.
- **Routing:** factory `Rou6`; the UC4 shows up as the port `Faderfox UC4`.

## What the script does

- Faders 1–8: volume of the 8 tracks of the session ring; fader 9: crossfader.
- Send 1–4: sends A–D of the 8 tracks. Pan: their pans. Rack: the 8 parameters of the selected
  device's current bank.
- Track (the selected track): 1 volume, 2 send A, 3 send B, 4 select the previous or next track,
  5 select the previous or next device, 6 pan; 7 and 8 do nothing.
- Global encoders: 1 tempo (coarse), 2 tempo (fine), 3 cue volume, 4 select the previous or next
  scene, 5 launch quantization (the printed `Quant`, added during the test), 6 master volume,
  8 master pan; 7 does nothing.
- Global push buttons 1–8: nudge down, nudge up, play, stop, stop all clips, start the selected
  scene, record, switch between Session and Arrangement View.
- Green buttons: Launch the clips of the ring's tracks in the selected scene; Stop each track's
  clips; Active (lit while the track plays, not muted); Solo; Record (arm); Monitor (switch In or
  Auto, lit while In); Track (bank left and right by 8 tracks, previous and next track, previous
  and next scene, previous and next device); Select (select the track).

## Behaviour checklist

The script, named `Faderfox_UC4`, does this. The user checks each item in Live 12.4.16, with
the UC4 on SE17 and its port as the Control Surface's input and output.

1. **Loads:** `log.sh --script Faderfox_UC4` shows `Faderfox UC4 (SE17) ready` and no
   traceback.
2. **Session ring:** a box of 8 tracks × 1 scene is drawn in Session View; selecting another
   scene with the UC4 (Global encoder 4, Track buttons 5–6) moves it. A mouse click doesn't:
   the framework follows only selections made through the script (corrected during the test).
3. **Faders:** faders 1–8 set the volume of the 8 tracks in the box; each picks the value up
   before it moves it (`SnAP`). Fader 9 moves the crossfader.
4. **Send and pan groups:** in Send 1–4 the encoders set sends A–D of the 8 tracks; in Pan their
   pans. The display shows Live's value when the group is selected and after a change in Live.
5. **Rack:** the 8 encoders set the selected device's 8 parameters; selecting another device
   moves them along.
6. **Track group:** encoder 1 sets the selected track's volume, 2 and 3 its sends A and B, 6 its
   pan; 4 selects the previous or next track (turn left or right), 5 the previous or next device.
7. **Global encoders:** 1 and 2 change the tempo coarsely and finely; 3 the cue volume; 4 selects
   the previous or next scene; 6 the master volume; 8 the master pan.
8. **Global push buttons:** 1 and 2 nudge while held; 3 plays, 4 stops; 5 stops all clips; 6
   starts the selected scene; 7 records (Session or Arrangement, by the view shown); 8 switches
   between Session and Arrangement View.
9. **Launch and Stop:** a Launch button starts its track's clip in the selected scene; its LED is
   lit while that clip plays or is about to start, and dark for a stopped clip or an empty slot.
   A Stop button stops its track's clips and is lit while the track plays.
10. **Active, Solo, Record, Select:** each button toggles mute, solo and arm, or selects its
    track; Active is lit while the track is not muted, Solo and Record while on, Select for the
    selected track. A change made in Live shows on the LEDs.
11. **Monitor:** a button switches its track's monitoring between In and Auto, and is lit while it
    is In; a group or return track's button does nothing.
12. **Track buttons:** 1 and 2 move the box 8 tracks left and right; 3 and 4 select the previous
    and next track; 5 and 6 the previous and next scene; 7 and 8 the previous and next device.
    Each is lit while held.
13. **LEDs per group:** after switching to another green button group and back, the LEDs show
    that group's state.
14. **Disconnect:** choosing None in the script's Control Surface slot leaves no green LED lit.

## Results

Load test in Live 12.4.16, 2026-11-17, by the user (in progress).

| Item | Result |
|---|---|
| 1 Loads | passed: `Faderfox UC4 (SE17) ready`, no traceback (also confirms how Live logs a v3 script) |
| 2 Session ring | passed after fix 1; the box follows Global encoder 4 |
| 3 Faders | passed after fix 2: volumes, pickup (`SnAP`), crossfader |
| 4 Send and pan groups | passed; the displays show Live's values |
| 5 Rack | passed: follows the selected device (racks, EQ Eight) |
| 6 Track group | passed: volume, sends A–B, pan, track and device selection |
| 7 Global encoders | passed: tempo coarse and fine, cue volume, scene selection, master volume and pan; encoder 5 added during the test (fix 3) |
| 8 Global push buttons | passed: nudge, play, stop, stop all clips, scene start, record, view |

Fixes found by the test:

1. **No box drawn.** v3 builds the session ring disabled and enables it only when the
   controller answers the identity request (`observed` in 12.4.16's `ControlSurface`
   statements). The UC4 doesn't, so the script's ring enables itself
   (`session_ring_component_type`). The box the user first saw was the APC mini's.
2. **No values sent to the UC4,** so its pickup compared against its own last value and the
   volume jumped. A v3 `EncoderElement` sends a mapped parameter's value back only with
   `is_feedback_enabled=True` (default `False`, `observed`); FANTOM and Komplete Kontrol S mk3
   pass it. Now set on every fader and absolute encoder; the UC4 displays Live's values and
   picks up.
3. **Quant on Global encoder 5** (the user's request): a component of our own steps
   `Song.clip_trigger_quantization` with `StepEncoderControl.connect_property`, as the
   framework's `TransportComponent` does for tempo. The first version passed a float, and every
   turn raised `Boost.Python.ArgumentError … None(TPyHandle<ASong>, int)`; Live's properties take
   the exact type. Also fixed: `log` dropped a record's lines without a timestamp, which held
   that error's signature.
