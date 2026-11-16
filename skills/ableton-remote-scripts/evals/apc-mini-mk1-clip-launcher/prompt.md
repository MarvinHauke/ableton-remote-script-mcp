---
tags: [skill-creator, step-9a]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

I have an Akai APC mini, the original mk1. Write me a Remote Script for Live 12.4 that turns it into a clip launcher:

- the 8x8 grid launches the clips of an 8x8 session box, and its LEDs show the clips (a clip, playing, recording)
- the 8 scene buttons on the right launch the scenes of the box
- the 8 track buttons below the grid stop the clips of their track
- faders 1-8 set the volumes of the 8 tracks of the box, fader 9 the master volume
- while I hold Shift, the first four track buttons move the box up, down, left and right

From Akai's MIDI protocol for the APC mini: everything is on MIDI channel 1. The grid sends notes 0-63, note 0 is the bottom left pad and the rows of 8 go upwards. The track buttons send notes 64-71 (left to right), the scene buttons notes 82-89 (top to bottom), Shift note 98. The faders send CC 48-56, fader 9 (the master) is CC 56. Grid LEDs take velocity 0 off, 1 green, 2 green blinking, 3 red, 4 red blinking, 5 yellow, 6 yellow blinking. Track and scene button LEDs take 0 off, 1 on, 2 blinking.

Put the script in a folder in the current directory. Don't install it, I'll do that myself.
