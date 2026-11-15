# Milestone 1, part 1: the APC mini mk1 script

Plan 0001 step 9. With the skill, Claude writes a `_Framework` script for the user's Akai APC mini
(mk1, Decision 19). This page holds the device facts it is written from, the behaviour checklist
(Decision 29) and the results.

## Device facts

Source: Akai's APC mini communication protocol (`documented`). The numbers match the MIDI numbers
of Ableton's `APC_mini` script in the 12.4.16 index (`observed`, local outline), so they are taken
as right for this unit; the load test confirms them.

- **MIDI channel:** 1 (0 in code) for every control.
- **Clip grid:** 8×8 pads, notes 0–63. The bottom row is 0–7, left to right; each row above adds
  8, so the top row is 56–63. Momentary: note on with velocity 127 when pressed, note off when
  released.
- **Grid LEDs:** set by sending a note on to the pad's note; the velocity picks the colour:
  0 off, 1 green, 2 green blinking, 3 red, 4 red blinking, 5 yellow, 6 yellow blinking.
- **Track buttons:** 8 buttons below the grid, notes 64–71, left to right; a red LED each:
  0 off, 1 on, 2 blinking.
- **Scene launch buttons:** 8 buttons right of the grid, notes 82–89, top to bottom; a green LED
  each: 0 off, 1 on, 2 blinking.
- **Shift:** note 98, momentary, no LED.
- **Faders:** 9 faders, CC 48–56, left to right; CC 56 is the rightmost (master) fader. Values
  0–127, absolute.
- **This unit:** its faders are defective and their values jump (Decision 29). A fader is checked
  only for reaching its target.

## Behaviour checklist

The script, named `APC_mini_mk1`, does this. The user checks each item in Live 12.4.16.

1. **Loads:** `log.sh --script APC_mini_mk1` shows its start-up message and no traceback.
2. **Session box:** an 8 tracks × 8 scenes box is drawn in Session View, starting at the first
   track and scene.
3. **Clip launch:** a grid pad launches the clip in its slot of the box (top row of pads = first
   scene of the box).
4. **Clip LEDs:** a slot with a stopped clip is yellow, a playing clip green, a clip about to start
   blinks green, a recording clip red; an empty slot is dark.
5. **Scene launch:** each scene launch button launches its scene of the box, top button = first
   scene; its LED is on for a scene that exists in the Set, blinks while the scene is triggered,
   and is off below the last scene.
6. **Track stop:** each track button stops the clips of its track in the box.
7. **Navigation:** with Shift held, track buttons 1–4 move the box up, down, left and right by one
   step per press; the grid LEDs follow the box. Each of the four is lit while its move is
   possible. Without Shift, they keep stopping clips.
8. **Faders:** faders 1–8 reach the volume of the 8 tracks in the box (they move along when the box
   moves); fader 9 reaches the master volume. Smoothness is not checked.
9. **Disconnect:** choosing None in the script's Control Surface slot turns the LEDs off.
10. **Stop LEDs:** a track button is lit while its track plays and blinks while a quantized stop
    waits. A group track's button is lit while any track in the group plays.
11. **Stop all:** Shift + the bottom scene button stops all clips; without Shift it launches its
    scene.
12. **Shift + an unbuilt button:** with Shift held, track buttons 5–8 and scene buttons 1–7 do
    nothing (their jobs on Ableton's script, fader and track modes, are not built yet).

Items 10–12 were added during the load test, on the user's request and from what it found.

## Results

Run by the user in Live 12.4.16 on 2026-11-15, with the agent reading `Log.txt`; the user ran
Ableton's `APC_mini` on the same controller for comparison.

| Item | Result |
|---|---|
| 1. Loads | passes: start-up message, no traceback (after the fixes below) |
| 2. Session box | passes |
| 3. Clip launch | passes |
| 4. Clip LEDs | passes: green blinking follows the global launch quantization |
| 5. Scene launch | passes; the LED below the last scene was not checked |
| 6. Track stop | passes |
| 7. Navigation | passes: one step per press, stops at the edges, LEDs show the possible moves (the log of about 450 presses shows every press moving one step) |
| 8. Faders | passes: every fader reaches its target |
| 9. Disconnect | passes with `reset()` on the matrices |
| 10. Stop LEDs | passes, group tracks included |
| 11. Stop all | passes |
| 12. Shift + an unbuilt button | passes |

Every name the script uses is `observed` in the 12.4.16 index, with two notes. The track members
`is_grouped` and `group_track` are `observed` only in the Push 3 helper's proxy model of
`Live.Track.Track`, and `tested` in 12.4.16 by item 10. And three instance attributes
of `SessionComponent` it reads (`_stop_track_clip_buttons`, `_stop_clip_value`,
`_stop_clip_triggered_value`), set in its constructor and so not in the index: `documented` from
the decompiled 12.0 framework. The group-track LEDs override a private method
(`_update_stop_clips_led`, `observed`), so they may break in a later build.

### Found and fixed during the load test

Each of these happened every time and is explained by the framework source or a traceback.

- **No pad worked, no LED lit, no traceback:** the session's layer was passed to its constructor.
  A component that starts enabled never grabs that layer; assigning `session.layer` after
  construction fixed it.
- **The box ran away to the left or right:** the session's own bank buttons repeat while held and
  stop on the button's release. When Shift was let go first, the release went to the stop button
  and the repeat never stopped. Replaced by one step per press.
- **A crash on opening a Set with a group track playing** (`TypeError … 'NoneType'`): the
  script's own group-track code sent the stop value while it was still unset (`None`), because
  the layer was assigned before the values were set. That code now turns the LED off for `None`,
  as the framework does, and the values are set before the layer.
- **Group tracks' stop buttons stayed dark while their tracks played:** Live reports a playing
  clip only on the track that holds it. The script lights a group's button itself.
- **The movement LEDs were overwritten** when a clip started or stopped while Shift was held: the
  session wrote stop LEDs to buttons a combo held. It now skips buttons it does not hold.
- **Shift + an unbuilt button stopped clips or launched a scene:** those buttons now go to a
  component that holds them and does nothing.
- **Scene LEDs stayed dark after Shift** when the unbuilt buttons were darkened while Shift was
  held: a scene relights its button only when it is given a different one. The script now leaves
  those LEDs as they are.

### Seen, not confirmed

The test controller may be slow or worn, its Shift button in particular; these were seen with
Ableton's `APC_mini` too, so they are not taken as the script's behaviour and are not in the skill:

- LEDs relight late after Shift is let go or after the box moves.
- Shift is sometimes reported pressed twice without a release, and a button release sometimes
  arrives without its press.

### Not covered

- Removing the controller's ports while the script runs leaves the LEDs lit: the script can no
  longer reach the device. Only choosing None in the Control Surface slot turns them off.
- Reopening a Set does not load a new version of the script; only restarting Live does.

## Comparison with Ableton's `APC_mini`

Ableton's script for this controller is a small subclass of its APC Key 25 script. In our own
words; the structure and the MIDI numbers are `observed` in the 12.4.16 index (outline), how the
parts behave is `documented` from the decompiled 12.0 reference:

- **Same device facts:** the same notes and CCs as this page (`observed`).
- **Shift works the same way:** combos with Shift as a shared modifier, and a holder for the
  buttons with no job while Shift is held.
- **It does more with Shift:** track buttons 5–8 switch what the faders control (volume, pan,
  send, device), and scene buttons 1–5 switch what the track buttons do (stop, solo, arm, mute,
  select). Ours does neither yet.
- **It navigates with the session's own bank buttons**, which repeat while held. Ours moves one
  step per press, after the runaway above.
- **It builds its components disabled,** with the layer in the constructor, and enables them
  later; ours assigns the layer after construction. Both make the layer take effect.
- **Its surface is an `OptimizedControlSurface`** (`observed`), which hands each button to its
  final owner once per incoming MIDI message instead of on every ownership change
  (`documented`, decompiled 12.0 framework). Ours is a plain `ControlSurface`. Whether that matters for scripts with combos is open: on this
  controller it could not be told apart from the delays above.
- **It uses skins** (named colour values) for its LEDs; ours passes the velocities directly.
