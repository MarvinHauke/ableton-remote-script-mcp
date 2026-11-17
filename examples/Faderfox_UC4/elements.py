"""The UC4's controls in its factory setup SE17, as v3 elements.

Device facts: the UC4 Editor's model of the factory setup SE17 (`node tools/uc4-config.ts
factory 17` in the UC4 Editor repo), which matches the device's own SE17 dump
(`dumps/2026-11-13-Sndc-SE17.syx`) byte for byte, and the editor's `docs/reference/uc4-device.md`
(the panel's printed Ableton names). The UC4 counts channels from 1 (Ch13, Ch14); the framework
counts from 0.

The UC4 switches its own groups (Shift + encoder n, Shift + green button n): each group sends
other numbers, so every group is an element of its own here and all of them are mapped at once.
Two controls that send the same message are built once: the Track group's push buttons 3 and 4
send the notes of the Track green buttons 2 and 1.
"""

from ableton.v3.control_surface import MIDI_NOTE_TYPE, ElementsBase, MapMode

CH13 = 12  # setup SE17's main channel, Ch13 on the UC4
CH14 = 13  # Ch14: the Track encoder group, fader 9 and the Track green buttons

# Track and Global encoders 1, 2, 4, 5 send CCr1: 1 for up and 127 for down, Ableton's
# "Relative (2's Comp.)"
RELATIVE = MapMode.LinearTwoCompliment

# Live sends a mapped parameter's value back only to elements built with is_feedback_enabled=True
# (v3's default is False). The UC4 shows it on its display and its pickup (SnAP) waits for it.
SHOWS_VALUE = {"is_feedback_enabled": True}


class Elements(ElementsBase):
    def __init__(self, *a, **k):
        super().__init__(*a, global_channel=CH13, **k)
        # faders 1-8 (CC 40-47, SnAP: the UC4 sends only after catching the value) and fader 9
        self.add_encoder_matrix([range(40, 48)], "Faders", **SHOWS_VALUE)
        self.add_encoder(48, "Crossfader", channel=CH14, **SHOWS_VALUE)

        # encoder groups 1-4 (Send 1-4), 7 (Pan) and 6 (Rack): eight absolute CCs each
        self.add_encoder_matrix([range(8)], "Send_A_Encoders", **SHOWS_VALUE)
        self.add_encoder_matrix([range(8, 16)], "Send_B_Encoders", **SHOWS_VALUE)
        self.add_encoder_matrix([range(16, 24)], "Send_C_Encoders", **SHOWS_VALUE)
        self.add_encoder_matrix([range(24, 32)], "Send_D_Encoders", **SHOWS_VALUE)
        self.add_encoder_matrix([range(32, 40)], "Pan_Encoders", **SHOWS_VALUE)
        self.add_encoder_matrix([range(48, 56)], "Rack_Encoders", **SHOWS_VALUE)

        # encoder group 5 (Track), Ch14 CC 56-63; encoders 7 and 8 are left free
        self.add_encoder(56, "Track_Volume_Encoder", channel=CH14, **SHOWS_VALUE)
        self.add_encoder(57, "Track_Send_A_Encoder", channel=CH14, **SHOWS_VALUE)
        self.add_encoder(58, "Track_Send_B_Encoder", channel=CH14, **SHOWS_VALUE)
        self.add_encoder(59, "Track_Select_Encoder", channel=CH14, map_mode=RELATIVE)
        self.add_encoder(60, "Device_Select_Encoder", channel=CH14, map_mode=RELATIVE)
        self.add_encoder(61, "Track_Pan_Encoder", channel=CH14, **SHOWS_VALUE)

        # encoder group 8 (Global), CC 56-63; encoder 7 is left free
        self.add_encoder(56, "Tempo_Coarse_Encoder", map_mode=RELATIVE)
        self.add_encoder(57, "Tempo_Fine_Encoder", map_mode=RELATIVE)
        self.add_encoder(58, "Cue_Volume_Encoder", **SHOWS_VALUE)
        self.add_encoder(59, "Scene_Select_Encoder", map_mode=RELATIVE)
        self.add_encoder(60, "Quantization_Encoder", map_mode=RELATIVE)
        self.add_encoder(61, "Master_Volume_Encoder", **SHOWS_VALUE)
        self.add_encoder(63, "Master_Pan_Encoder", **SHOWS_VALUE)

        # the Global group's push buttons, notes 120-127
        self.add_button(120, "Nudge_Down_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(121, "Nudge_Up_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(122, "Play_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(123, "Stop_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(124, "Stop_All_Clips_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(125, "Scene_Launch_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(126, "Record_Button", msg_type=MIDI_NOTE_TYPE)
        self.add_button(127, "View_Button", msg_type=MIDI_NOTE_TYPE)

        # the green buttons' eight groups (the panel's names above them), notes; their LEDs are
        # set to EXt: lit only by what the script sends back on the same note
        self.add_button_matrix([range(64, 72)], "Launch_Buttons", msg_type=MIDI_NOTE_TYPE)
        self.add_button_matrix([range(72, 80)], "Stop_Buttons", msg_type=MIDI_NOTE_TYPE)
        self.add_button_matrix([range(104, 112)], "Active_Buttons", msg_type=MIDI_NOTE_TYPE)
        self.add_button_matrix([range(96, 104)], "Solo_Buttons", msg_type=MIDI_NOTE_TYPE)
        self.add_button_matrix([range(80, 88)], "Record_Buttons", msg_type=MIDI_NOTE_TYPE)
        self.add_button_matrix([range(88, 96)], "Monitor_Buttons", msg_type=MIDI_NOTE_TYPE)
        self.add_button_matrix([range(56, 64)], "Select_Buttons", msg_type=MIDI_NOTE_TYPE)
        # group 7 (Track), Ch14, numbered 123 122 127 126 124 125 120 121 from left to right
        self.add_button(123, "Bank_Left_Button", channel=CH14, msg_type=MIDI_NOTE_TYPE)
        self.add_button(122, "Bank_Right_Button", channel=CH14, msg_type=MIDI_NOTE_TYPE)
        self.add_button(127, "Prev_Track_Button", channel=CH14, msg_type=MIDI_NOTE_TYPE)
        self.add_button(126, "Next_Track_Button", channel=CH14, msg_type=MIDI_NOTE_TYPE)
        self.add_button(124, "Prev_Scene_Button", channel=CH14, msg_type=MIDI_NOTE_TYPE)
        self.add_button(125, "Next_Scene_Button", channel=CH14, msg_type=MIDI_NOTE_TYPE)
        self.add_button(120, "Prev_Device_Button", channel=CH14, msg_type=MIDI_NOTE_TYPE)
        self.add_button(121, "Next_Device_Button", channel=CH14, msg_type=MIDI_NOTE_TYPE)
