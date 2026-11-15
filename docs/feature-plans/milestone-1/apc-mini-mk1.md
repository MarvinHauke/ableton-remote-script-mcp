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
7. **Navigation:** with Shift held, track buttons 1–4 move the box up, down, left and right by one;
   the grid LEDs follow the box. Without Shift, they keep stopping clips.
8. **Faders:** faders 1–8 reach the volume of the 8 tracks in the box (they move along when the box
   moves); fader 9 reaches the master volume. Smoothness is not checked.
9. **Disconnect:** choosing None in the script's Control Surface slot turns the LEDs off.

## Results

Not run yet.
