"""`rig restart-live`: quit Live without saving and start it again, for the test rig only (plan
0002, Decision 23 once recorded).

1. Live must show only the test Set: its windows' names must be the expected title (default
   `Untitled`, the unsaved Set Live opens from the user's template). Otherwise nothing happens.
2. Live is asked to quit through AppleScript, without waiting for its answer. If it asks whether
   to save, the only button ever pressed is "Don't Save" (UI scripting, see `_press_dont_save`;
   needs the terminal's Accessibility permission). If that dialog can't be recognised, the
   restart stops and leaves Live as it is, dialog included.
3. Once Live has quit, the same app is opened again, and the restart waits until Live's
   `Log.txt` shows a new session (and, if given, a script's message).
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

PROCESS = "Live"


class RestartError(RuntimeError):
    pass


def _osa(script: str, timeout: float = 10.0) -> str:
    done = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout, check=False)
    if done.returncode != 0:
        raise RestartError(done.stderr.strip() or f"osascript exited {done.returncode}")
    return done.stdout.strip()


def running() -> bool:
    return _osa(f'tell application "System Events" to exists process "{PROCESS}"') == "true"


def window_names() -> list[str]:
    out = _osa(f'tell application "System Events" to tell process "{PROCESS}" to get name of every window')
    return [n.strip() for n in out.split(",") if n.strip()] if out else []


def _press_dont_save(title: str) -> bool:
    """Press "Don't Save" in Live's save dialog; True if pressed.

    Live draws the dialog itself: macOS sees an `AXDialog` window with a group holding the
    question as text and three unnamed buttons, Don't Save on the left, Cancel and Save on the
    right (Live 12.4.16, 2026-11-18). So the button is pressed only when the text is exactly
    `Save changes to "<title>" before closing?` and there are exactly three buttons; it is the
    leftmost one. Nothing else is ever pressed.
    """
    question = f'Save changes to "{title}" before closing?'.replace('"', '\\"')
    script = f'''
tell application "System Events" to tell process "{PROCESS}"
  repeat with w in windows
    if subrole of w is "AXDialog" then
      repeat with g in (groups of w)
        set texts to value of every static text of g
        set btns to every button of g
        if texts contains "{question}" and (count of btns) is 3 then
          set best to item 1 of btns
          set bestPos to position of best
          set bestX to item 1 of bestPos
          repeat with b in btns
            set bPos to position of b
            set bX to item 1 of bPos
            if bX < bestX then
              set best to b
              set bestX to bX
            end if
          end repeat
          perform action "AXPress" of best
          return "pressed"
        end if
      end repeat
    end if
  end repeat
  return "none"
end tell'''
    return _osa(script) == "pressed"


def _session_starts(log: Path) -> int:
    if not log.is_file():
        return 0
    return sum(1 for line in log.read_text(errors="replace").splitlines() if ": Started: Live " in line)


def restart_live(app: Path, log: Path, expect_title: str = "Untitled", wait_for: str | None = None,
                 quit_seconds: float = 60.0, start_seconds: float = 180.0, say=print) -> dict:
    if not running():
        raise RestartError("Live is not running; start it yourself")
    names = window_names()
    if not names or any(n != expect_title for n in names):
        raise RestartError(f"Live shows {names or 'no window'}, not only the test Set `{expect_title}`: "
                           "nothing was done")
    starts = _session_starts(log)
    say(f"quitting Live (the test Set `{expect_title}` is not saved)")
    # without waiting: Live answers a quit only after its save dialog is closed
    _osa(f'ignoring application responses\ntell application "{app}" to quit\nend ignoring', timeout=30)
    pressed = False
    end = time.monotonic() + quit_seconds
    while running():
        if time.monotonic() > end:
            raise RestartError("Live is still running: no \"Don't Save\" button was found, or Live didn't quit. "
                               "It is left as it is; please look at it")
        if not pressed and _press_dont_save(expect_title):
            pressed = True
            say("answered \"Don't Save\"")
        time.sleep(0.5)
    say(f"Live has quit; opening {app.name}")
    subprocess.run(["open", "-a", str(app)], check=True)
    end = time.monotonic() + start_seconds
    while _session_starts(log) <= starts:
        if time.monotonic() > end:
            raise RestartError(f"no new session in {log} after {start_seconds:.0f} s")
        time.sleep(1)
    say("Live has started (a new session in Log.txt)")
    if wait_for:
        from ..live_log import read_log

        while not any(wait_for in m["text"] for m in read_log(log)["messages"]):
            if time.monotonic() > end:
                raise RestartError(f"Live started, but no message `{wait_for}` in {start_seconds:.0f} s")
            time.sleep(1)
        say(f"the script logged `{wait_for}`")
    return {"pressed_dont_save": pressed, "app": str(app), "log": str(log)}
