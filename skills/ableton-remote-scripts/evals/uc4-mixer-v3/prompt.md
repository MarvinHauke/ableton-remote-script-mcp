---
tags: [skill-creator, step-9a]
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Write a Remote Script for my Faderfox UC4 on the ableton.v3 framework, for Live 12.4. It should be a mixer for 8 tracks:

- faders 1-8: volume of the 8 tracks
- encoders 1-8: pan of the 8 tracks
- green buttons 1-8: mute of the 8 tracks
- fader 9 (the horizontal one): the crossfader
- push buttons 1 and 2 (pressing encoders 1 and 2) move the 8 tracks left and right by one bank of 8

The UC4 is on setup 1 with factory settings, encoder group 1 and fader/button group 1. From my notes on the factory settings: everything is on MIDI channel 1. Encoders send CC 8-15, absolute 0-127. Encoder push buttons send notes 0-7. Faders 1-8 send CC 32-39, fader 9 sends CC 112. The green buttons send notes 64-71. I don't know whether the green LEDs react to notes sent to the UC4. The UC4's display shows the value of the encoder or fader I move, and the manual says it also shows values sent to it on the same CC. I don't know whether it answers a MIDI identity request.

Put the script in a folder in the current directory. Don't install it, I'll do that myself.
