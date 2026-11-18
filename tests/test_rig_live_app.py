"""`rig restart-live`'s guards (plan 0002 Decision 23), with AppleScript faked: nothing is done
unless Live shows only the test Set."""

import pytest

from ableton_remote_script_mcp.rig import live_app


def _fake(monkeypatch, windows, sent):
    def osa(script, timeout=10.0):
        sent.append(script)
        if "exists process" in script:
            return "true"
        if "name of every window" in script:
            return windows
        return ""
    monkeypatch.setattr(live_app, "_osa", osa)


@pytest.mark.parametrize("windows", ["", "My Song", "Untitled, My Song"])
def test_restart_does_nothing_unless_only_the_test_set_is_open(monkeypatch, tmp_path, windows):
    sent = []
    _fake(monkeypatch, windows, sent)
    with pytest.raises(live_app.RestartError, match="nothing was done"):
        live_app.restart_live(tmp_path / "Live.app", tmp_path / "Log.txt", say=lambda *_: None)
    assert not any("quit" in s for s in sent)


def test_the_dont_save_script_checks_the_question_and_three_buttons():
    sent = []
    live_app._osa, original = (lambda s, timeout=10.0: sent.append(s) or "none"), live_app._osa
    try:
        assert live_app._press_dont_save("Untitled") is False
    finally:
        live_app._osa = original
    script = sent[0]
    assert 'Save changes to \\"Untitled\\" before closing?' in script
    assert "(count of btns) is 3" in script and 'perform action "AXPress" of best' in script
    assert "Save\"" not in script.replace("Don't Save", "")  # never a button named Save
