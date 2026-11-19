"""The rig's AbletonMCP client (plan 0002 Decisions 2, 6, 21, 25): Live's state, read through the
AbletonMCP Remote Script's socket on localhost:9877, as optional evidence beside the MIDI replies.

Protocol (AbletonMCP 1.7.1, read from its `__init__.py`): the client writes one JSON object
`{"type": <command>, "params": {...}}` with no delimiter; the script answers with one JSON object
`{"status": "success", "result": ...}` or `{"status": "error", "message": ...}` on the same
connection. Reads run off Live's main thread; writes are scheduled on it.

Only the commands in `ALLOWED` are ever sent (Decisions 6, 25, 27, 29); never its rating, dataset-consent,
browser or clip-deleting commands. A read is repeated until two answers agree, because a first read after the user
reopened Live failed once (`Boost.Python.ArgumentError … None(Song)`, 2026-11-18). With another
script version, or no socket, the rig runs without AbletonMCP.
"""

from __future__ import annotations

import json
import socket

HOST, PORT = "127.0.0.1", 9877
SCRIPT_VERSION, PROTOCOL_VERSION = "1.7.1", 1
READS = {"get_script_info", "get_session_info", "get_track_info", "get_device_parameters",
         "drain_passive_events", "get_clip_notes",
         "get_session_snapshot"}  # only for a clip's looping, loop_start, loop_end: Decision 27
WRITES = {"create_midi_track", "create_audio_track", "create_clip", "set_tempo", "set_device_parameter",
          "fire_clip", "stop_clip", "start_playback", "stop_playback",
          "add_notes_to_clip", "clear_notes_from_clip",  # the notes three: Decision 25
          "select_clip_slot"}  # the user's fork only: Decision 29
ALLOWED = READS | WRITES
# Commands the upstream 1.7.1 script lacks: sent only when `get_script_info` lists them among its
# `capabilities` (the user's fork, MarvinHauke/ableton-mcp, keeps the version 1.7.1).
NEEDS_CAPABILITY = {"select_clip_slot"}

# Commands whose answer was checked against a state the user set by hand in Live (Decision 6),
# with the evidence. A command not listed here is used, but its result is labelled untested.
TESTED = {
    "get_track_info": "2026-11-18, Live 12.4.16: track 1's volume read 0.787 after the rig sent CC 40 = 100 (step 1); "
                      "track 3 read `mute` after the user muted it by hand",
    "get_session_info": "2026-11-18, Live 12.4.16: tempo read 123 after the user set 123 BPM by hand",
    "get_device_parameters": "2026-11-18, Live 12.4.16: Macro 2 of track 2's Instrument Rack read 64.0 after the "
                             "user set it to 64 by hand",
    # plan 0002 step 6b, the user's clip on track 7, scene 8 of the test Set
    "get_clip_notes": "2026-11-19, Live 12.4.16: read C#3 on 1.2 and C3 on 1.4, the two notes the user drew by hand",
    "get_session_snapshot": "2026-11-19, Live 12.4.16: read the same clip looping over its whole bar (0-4), "
                            "as the user's screenshot showed (a new clip's default loop; a loop changed by hand "
                            "is still to be read, in 0003's checks)",
    "add_notes_to_clip": "2026-11-19, Live 12.4.16: a D3 on 1.1 read back and seen by the user, the two notes kept",
    "clear_notes_from_clip": "2026-11-19, Live 12.4.16: the three notes gone, read back and seen by the user",
}


class Forbidden(ValueError):
    """A command outside the rig's allow-list (plan 0002 Decision 6)."""


class AbletonMCPError(RuntimeError):
    pass


class AbletonMCP:
    def __init__(self, host: str = HOST, port: int = PORT, timeout: float = 5.0, sock=None):
        self._sock = sock or socket.create_connection((host, port), timeout=timeout)
        self._sock.settimeout(timeout)
        self.info = self.read("get_script_info")

    def close(self) -> None:
        self._sock.close()

    def call(self, command: str, **params):
        """One command; its `result`. Raises Forbidden before sending anything not allowed."""
        if command not in ALLOWED:
            raise Forbidden(f"the rig never sends AbletonMCP's `{command}` (plan 0002 Decision 6)")
        if command in NEEDS_CAPABILITY and command not in (getattr(self, "info", None) or {}).get("capabilities", []):
            raise AbletonMCPError(f"this AbletonMCP doesn't list `{command}` in its capabilities "
                                  "(MarvinHauke/ableton-mcp has it)")
        self._sock.sendall(json.dumps({"type": command, "params": params}).encode("utf-8"))
        buffer = b""
        decoder = json.JSONDecoder()
        while True:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise AbletonMCPError("AbletonMCP closed the connection")
            buffer += chunk
            try:
                answer, _ = decoder.raw_decode(buffer.decode("utf-8"))
                break
            except (ValueError, UnicodeDecodeError):
                continue
        if answer.get("status") != "success":
            raise AbletonMCPError(f"`{command}`: {answer.get('message', answer)}")
        return answer.get("result")

    def read(self, command: str, tries: int = 4, project=None, **params):
        """A read repeated until two answers in a row agree (or an error the last time). With
        `project`, only `project(answer)` must agree, and it is what comes back: a snapshot holds
        the song time, so two whole ones never agree while Live plays."""
        if command not in READS - {"drain_passive_events"}:
            raise Forbidden(f"`{command}` is not a repeatable read")
        last, error = None, None
        for _ in range(tries):
            try:
                answer = self.call(command, **params)
                if project is not None:
                    answer = project(answer)
            except AbletonMCPError as e:
                error, last = e, None
                continue
            if last is not None and answer == last:
                return answer
            last = answer
        if last is not None:
            return last
        raise error or AbletonMCPError(f"`{command}` gave no answer")

    def events(self) -> list[dict]:
        """AbletonMCP's buffered listener events since the last drain (it keeps at most 500)."""
        return (self.call("drain_passive_events") or {}).get("events", [])


def connect(host: str = HOST, port: int = PORT) -> tuple[AbletonMCP | None, str]:
    """(a client, "") or (None, why the rig runs without AbletonMCP)."""
    try:
        client = AbletonMCP(host, port)
    except OSError:
        return None, f"no AbletonMCP on {host}:{port} (is it picked as a Control Surface?)"
    except AbletonMCPError as e:
        return None, f"AbletonMCP didn't answer get_script_info: {e}"
    info = client.info or {}
    if info.get("script_version") != SCRIPT_VERSION or info.get("protocol_version") != PROTOCOL_VERSION:
        client.close()
        return None, (f"AbletonMCP {info.get('script_version')} (protocol {info.get('protocol_version')}); the rig "
                      f"knows {SCRIPT_VERSION} (protocol {PROTOCOL_VERSION}) only")
    return client, ""
