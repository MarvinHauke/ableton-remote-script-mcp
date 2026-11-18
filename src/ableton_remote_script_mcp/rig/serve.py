"""`rig serve`: keep the rig's virtual port open while the user restarts Live.

A script change needs a Live restart (the user, 2026-11-18), and the virtual port exists only
while a process holds it. `rig serve` holds it and lets `rig run` (and later the panel) use it
over a local socket: one JSON object per line, on 127.0.0.1 only.

    {"op": "hello"}                      -> {"ok": true, "port": name, "received": n, "last": s | null}
    {"op": "send", "messages": [[...]]}  -> {"ok": true}
    {"op": "drain"}                      -> {"ok": true, "messages": [[seconds, [bytes]], ...]}

Each connection has its own inbox: what Live sends goes to every client connected at that time.
The server sends only to its own virtual port (plan 0002 Decision 1).
"""

from __future__ import annotations

import json
import socket
import socketserver
import threading
import time

from .ports import Received, _Inbox

DEFAULT_PORT = 9878  # AbletonMCP uses 9877
VERSION = 1


class RigServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port, address=("127.0.0.1", DEFAULT_PORT), poll=0.002):
        self.midi = port
        self.inboxes: list[_Inbox] = []
        self.lock = threading.Lock()
        self.received = 0
        self.last: float | None = None
        self.started = time.monotonic()
        self._stop = threading.Event()
        super().__init__(address, _Handler)
        self._pump = threading.Thread(target=self._fan_out, args=(poll,), daemon=True)
        self._pump.start()

    def _fan_out(self, poll: float) -> None:
        while not self._stop.is_set():
            got = self.midi.drain()
            if got:
                with self.lock:
                    self.received += len(got)
                    self.last = time.monotonic()
                    for inbox in self.inboxes:
                        for r in got:
                            inbox.put(r.message)
            else:
                self._stop.wait(poll)

    def server_close(self) -> None:
        self._stop.set()
        super().server_close()


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        server: RigServer = self.server  # type: ignore[assignment]
        inbox = _Inbox()
        with server.lock:
            server.inboxes.append(inbox)
        try:
            for line in self.rfile:
                try:
                    answer = self._answer(server, inbox, json.loads(line))
                except (ValueError, KeyError, TypeError) as e:
                    answer = {"ok": False, "error": str(e)}
                self.wfile.write((json.dumps(answer) + "\n").encode())
        finally:
            with server.lock:
                server.inboxes.remove(inbox)

    @staticmethod
    def _answer(server: RigServer, inbox: _Inbox, request: dict) -> dict:
        op = request["op"]
        if op == "hello":
            last = None if server.last is None else round(time.monotonic() - server.last, 3)
            return {"ok": True, "version": VERSION, "port": server.midi.name, "received": server.received,
                    "last": last}
        if op == "send":
            for m in request["messages"]:
                if not (isinstance(m, list) and m and all(isinstance(b, int) and 0 <= b <= 255 for b in m)):
                    raise ValueError(f"not a MIDI message: {m!r}")
                server.midi.send(m)
            return {"ok": True}
        if op == "drain":
            return {"ok": True, "messages": [[r.time, r.message] for r in inbox.drain()]}
        raise ValueError(f"unknown op {op!r}")


class ServedPort:
    """A port held by `rig serve`, with the same interface as `VirtualPort`."""

    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 2.0):
        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._file = self._sock.makefile("rwb")
        hello = self._ask({"op": "hello"})
        if hello.get("version") != VERSION:
            self.close()
            raise ConnectionError(f"rig serve speaks version {hello.get('version')}, this rig {VERSION}")
        self.name = hello["port"]
        self.hello = hello

    def _ask(self, request: dict) -> dict:
        self._file.write((json.dumps(request) + "\n").encode())
        self._file.flush()
        line = self._file.readline()
        if not line:
            raise ConnectionError("rig serve closed the connection")
        answer = json.loads(line)
        if not answer.get("ok"):
            raise ConnectionError(f"rig serve: {answer.get('error')}")
        return answer

    def send(self, message: list[int]) -> None:
        self._ask({"op": "send", "messages": [list(message)]})

    def drain(self) -> list[Received]:
        return [Received(t, m) for t, m in self._ask({"op": "drain"})["messages"]]

    def close(self) -> None:
        try:
            self._file.close()
        finally:
            self._sock.close()


def connect(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> ServedPort | None:
    """The served port, or None when no `rig serve` listens there."""
    try:
        return ServedPort(host, port)
    except OSError:
        return None


def serve(name: str, address=("127.0.0.1", DEFAULT_PORT), log=print) -> None:  # pragma: no cover - needs MIDI
    from .ports import VirtualPort

    midi = VirtualPort(name)
    server = RigServer(midi, address)
    log(f"rig serve: holding the virtual port `{name}`; clients connect on {address[0]}:{address[1]}. "
        "Restart Live as often as needed; stop with Ctrl-C.")
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        midi.close()
