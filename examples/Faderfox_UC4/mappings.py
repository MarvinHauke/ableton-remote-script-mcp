"""Which element drives which component control. The keys are the components' control names
(a member or a `set_<key>` setter of the component's class, checked by the validator), the values
the elements' names in snake case."""


def create_mappings(control_surface):
    mappings = {}
    mappings["Mixer"] = {
        "volume_controls": "faders",
        "crossfader_control": "crossfader",
        # MixerComponent passes these on to its channel strips by name pattern
        "send_a_controls": "send_a_encoders",
        "send_b_controls": "send_b_encoders",
        "send_c_controls": "send_c_encoders",
        "send_d_controls": "send_d_encoders",
        "pan_controls": "pan_encoders",
        "mute_buttons": "active_buttons",
        "solo_buttons": "solo_buttons",
        "arm_buttons": "record_buttons",
        "track_select_buttons": "select_buttons",
        "prehear_volume_control": "cue_volume_encoder",
        "master_track_volume_control": "master_volume_encoder",
        "master_track_pan_control": "master_pan_encoder",
    }
    mappings["Target_Channel_Strip"] = {
        "volume_control": "track_volume_encoder",
        "pan_control": "track_pan_encoder",
        "send_a_control": "track_send_a_encoder",
        "send_b_control": "track_send_b_encoder",
    }
    mappings["Device"] = {"parameter_controls": "rack_encoders"}
    mappings["Session"] = {
        "clip_launch_buttons": "launch_buttons",
        "stop_track_clip_buttons": "stop_buttons",
        "stop_all_clips_button": "stop_all_clips_button",
    }
    mappings["Session_Navigation"] = {
        "page_left_button": "bank_left_button", "page_right_button": "bank_right_button"}
    mappings["View_Control"] = {
        "prev_track_button": "prev_track_button",
        "next_track_button": "next_track_button",
        "prev_scene_button": "prev_scene_button",
        "next_scene_button": "next_scene_button",
        "track_encoder": "track_select_encoder",
        "scene_encoder": "scene_select_encoder",
    }
    mappings["Device_Navigation"] = {
        "scroll_up_button": "prev_device_button",
        "scroll_down_button": "next_device_button",
        "scroll_encoder": "device_select_encoder",
    }
    mappings["Transport"] = {
        "tempo_coarse_encoder": "tempo_coarse_encoder",
        "tempo_fine_encoder": "tempo_fine_encoder",
        "nudge_down_button": "nudge_down_button",
        "nudge_up_button": "nudge_up_button",
        "play_button": "play_button",
        "stop_button": "stop_button",
    }
    mappings["View_Based_Recording"] = {"record_button": "record_button"}
    mappings["View_Toggle"] = {"main_view_toggle_button": "view_button"}
    mappings["Monitor"] = {"monitor_buttons": "monitor_buttons"}
    mappings["Quantization"] = {"quantization_encoder": "quantization_encoder"}
    mappings["Scene_Launch"] = {"launch_button": "scene_launch_button"}
    return mappings
