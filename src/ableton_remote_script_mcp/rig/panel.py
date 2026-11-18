"""`rig panel`: a web page of the controller, for the user (plan 0002 step 5, Decisions 3, 9, 10).

The panel is a client: `rig serve` owns the virtual port, the panel talks to it like `rig run`
does, and the page talks to the panel over a WebSocket on 127.0.0.1 (no Web MIDI). The page says
that it is a parallel view and that the driver is in charge: what `rig run` plays shows up on the
page as it happens, and the user's moves on the page go to the same port.

    page -> panel   {"op": "play", "element": name, "value": n}     n: 0-127, or steps for a relative
                                                                    encoder, or "press"
                    {"op": "send", "message": [bytes]}              one raw MIDI message (a client that
                                                                    knows the device, not the script)
    panel -> page   {"type": "model", ...}                          once, on connecting, then the last
                                                                    "midi" event per element and dir
                                                                    with "replay": true
                    {"type": "midi", "dir": "in" | "out", "by": "panel" | "driver" | null,
                     "message": [...], "text": s, "elements": [names], "value": n | null}
                    {"type": "error", "text": s}                    `rig serve` lost, a bad move
                    {"type": "status", "text": s}                   `rig serve` back again

`dir` is seen from the controller: `in` is what Live sent to it (LEDs, values), `out` what was
played into Live. The WebSocket is a minimal RFC 6455 server (text frames, ping, close) so the
rig needs no further dependency. Only pages served from this machine may connect: a browser
sends the page's `Origin`, and one from another host (any website open in the browser) is
refused, so no website can play into Live. Clients outside a browser send no `Origin`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import urlsplit

from .checks import CheckFileError, _key, encode
from .controller import Controller
from .ports import describe

DEFAULT_PORT = 9879  # rig serve: 9878, AbletonMCP: 9877
PROTOCOL = 1  # the WebSocket protocol's version (docs/rig-panel-protocol.md): a client checks it
NOTICE = ("Parallel view: the test rig's driver is in charge. What `rig run` plays shows up here; "
          "what you play here goes to the same port. Live is never saved.")
ROW = 8  # elements per row in the plain layout
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def local_origin(origin: str | None) -> bool:
    """True for no `Origin` (not a browser) or a page served from this machine."""
    if origin is None:
        return True
    host = urlsplit(origin).hostname or ""
    return host in LOCAL_HOSTS or host.endswith(".localhost")


# --- the model the page draws --------------------------------------------------------------------

def _display(ctl: Controller, profile, name: str, group: str | None) -> str:
    hints = profile.display if profile else {}
    if name in hints:
        return hints[name]
    if group and group in hints:
        return hints[group]
    return "relative" if ctl.elements[name].relative else "absolute"


def panel_model(ctl: Controller, profile=None) -> dict:
    """Rows of groups of elements, as the page draws them. A profile's `layout` gives the rows
    (each name an element or a whole matrix); without one, a plain layout from `outline`: one
    row per matrix, then the single elements, buttons and encoders apart, `ROW` to a row
    (Decision 10). Elements a layout leaves out are added at the end, so none is hidden."""
    group_of = {item: m for m, items in ctl.matrices.items() for item in items}

    def group(name: str) -> dict:
        names = ctl.matrices.get(name, [name])
        return {"name": name, "elements": [
            {"name": n, "kind": ctl.elements[n].kind, "midi": ctl.elements[n].describe(),
             "display": _display(ctl, profile, n, group_of.get(n)),
             "feedback": ctl.elements[n].feedback} for n in names]}

    rows: list[list[str]] = [list(r) for r in profile.layout] if profile and profile.layout else []
    placed = {n for row in rows for x in row for n in ctl.matrices.get(x, [x])}
    if not rows:
        rows = [[m] for m in ctl.matrices]
        placed = set(group_of)
    rest = [n for n in ctl.elements if n not in placed and n not in group_of]
    rest_matrices = [m for m in ctl.matrices if not set(ctl.matrices[m]) & placed]
    rows += [[m] for m in rest_matrices]
    for kind in ("button", "encoder"):
        names = [n for n in rest if ctl.elements[n].kind == kind]
        rows += [names[i:i + ROW] for i in range(0, len(names), ROW)]
    return {"type": "model", "protocol": PROTOCOL, "script": ctl.script, "folder": ctl.folder,
            "profile": profile.name if profile else None, "notice": NOTICE,
            "rows": [[group(x) for x in row] for row in rows if row],
            "unresolved": ctl.unresolved}


def midi_event(ctl: Controller, message: list[int], direction: str, by: str | None) -> dict:
    """What the page shows for one message: the elements it belongs to and its value."""
    key = _key(message)
    names = [e.name for e in ctl.by_key(key[0])] if key else []
    return {"type": "midi", "dir": direction, "by": by, "message": list(message), "text": describe(message),
            "elements": names, "value": key[1] if key and names else None}


def play(ctl: Controller, name: str, value) -> list[list[int]]:
    """The messages a move on the page sends (a button sends 127 when pressed, 0 when let go)."""
    try:
        element = ctl.element(name)
    except KeyError as e:
        raise CheckFileError(str(e.args[0])) from e
    return encode(element, value)


# --- WebSocket (RFC 6455, the part a browser needs) ----------------------------------------------

def accept_key(key: str) -> str:
    return base64.b64encode(hashlib.sha1((key + _WS_GUID).encode()).digest()).decode()


def ws_frame(text: str, opcode: int = 0x1) -> bytes:
    data = text.encode()
    n = len(data)
    head = bytes([0x80 | opcode])
    if n < 126:
        head += bytes([n])
    elif n < 1 << 16:
        head += bytes([126]) + struct.pack(">H", n)
    else:
        head += bytes([127]) + struct.pack(">Q", n)
    return head + data


def ws_read(rfile) -> tuple[int, bytes] | None:
    """(opcode, payload) of the next frame, or None when the connection ended."""
    head = rfile.read(2)
    if len(head) < 2:
        return None
    opcode, n, masked = head[0] & 0x0F, head[1] & 0x7F, head[1] & 0x80
    if n == 126:
        n = struct.unpack(">H", rfile.read(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", rfile.read(8))[0]
    mask = rfile.read(4) if masked else b"\0\0\0\0"
    data = rfile.read(n)
    return opcode, bytes(b ^ mask[i % 4] for i, b in enumerate(data))


class _Client:
    def __init__(self, wfile):
        self.wfile = wfile
        self.lock = threading.Lock()

    def send(self, answer: dict, opcode: int = 0x1) -> bool:
        try:
            with self.lock:
                self.wfile.write(ws_frame(json.dumps(answer), opcode))
                self.wfile.flush()
            return True
        except OSError:
            return False


# --- the panel's server --------------------------------------------------------------------------

class PanelServer(ThreadingHTTPServer):
    """Serves the page and the WebSocket, and pumps `port` (a `ServedPort`, or any port with
    `send` and `drain`/`drain_both`) to every page. When `rig serve` goes away (it was restarted),
    `reconnect()` is tried every `retry` seconds until it returns a port again."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, ctl: Controller, port, profile=None, address=("127.0.0.1", DEFAULT_PORT), poll=0.01,
                 reconnect=None, retry: float = 1.0):
        self.ctl = ctl
        self.port = port
        self.reconnect = reconnect
        self.retry = retry
        self.model = panel_model(ctl, profile)
        self.clients: list[_Client] = []
        self.last: dict[tuple[str, str], dict] = {}  # (element, dir) -> its last event, for a page that connects later
        self.lock = threading.Lock()  # one request at a time on `port`'s socket
        self._stop = threading.Event()
        super().__init__(address, _PanelHandler)
        self._pump = threading.Thread(target=self._fan_out, args=(poll,), daemon=True)
        self._pump.start()

    def _drain(self):
        with self.lock:
            if hasattr(self.port, "drain_both"):
                return self.port.drain_both()
            return self.port.drain(), []

    def _fan_out(self, poll: float) -> None:
        while not self._stop.is_set():
            try:
                received, sent = self._drain()
            except (OSError, ConnectionError, ValueError) as e:
                self.broadcast({"type": "error", "text": f"lost `rig serve`: {e}"})
                if not self._reconnect():
                    return
                continue
            for r in sent:
                self.broadcast(midi_event(self.ctl, r.message, "out", "driver"))
            for r in received:
                self.broadcast(midi_event(self.ctl, r.message, "in", None))
            if not (received or sent):
                self._stop.wait(poll)

    def _reconnect(self) -> bool:
        if self.reconnect is None:
            return False
        while not self._stop.wait(self.retry):
            port = self.reconnect()
            if port is not None:
                with self.lock:
                    old, self.port = self.port, port
                try:
                    old.close()
                except OSError:
                    pass
                self.broadcast({"type": "status", "text": f"connected to `rig serve` again (`{port.name}`)"})
                return True
        return False

    def broadcast(self, event: dict) -> None:
        with self.lock:
            if event.get("type") == "midi" and event.get("value") is not None:
                for name in event["elements"]:
                    self.last[(name, event["dir"])] = event
            clients = list(self.clients)
        gone = [c for c in clients if not c.send(event)]
        if gone:
            with self.lock:
                self.clients = [c for c in self.clients if c not in gone]

    def play(self, name: str, value) -> list[list[int]]:
        return self.send([*play(self.ctl, name, value)])

    def send_raw(self, message) -> list[list[int]]:
        if not (isinstance(message, list) and message
                and all(isinstance(b, int) and not isinstance(b, bool) and 0 <= b <= 255 for b in message)):
            raise CheckFileError(f"not a MIDI message: {message!r}")
        return self.send([message])

    def send(self, messages: list[list[int]]) -> list[list[int]]:
        with self.lock:
            for m in messages:
                self.port.send(m)
        for m in messages:
            self.broadcast(midi_event(self.ctl, m, "out", "panel"))
        return messages

    def server_close(self) -> None:
        self._stop.set()
        super().server_close()


class _PanelHandler(BaseHTTPRequestHandler):
    server: PanelServer  # type: ignore[assignment]

    def log_message(self, *_):  # quiet
        pass

    def do_GET(self) -> None:
        if self.path == "/ws" and self.headers.get("Upgrade", "").lower() == "websocket":
            self._websocket()
            return
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        page = resources.files(__package__).joinpath("panel.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(page)

    def _websocket(self) -> None:
        if not local_origin(self.headers.get("Origin")):
            self.send_error(403, "only pages served from this machine may connect")
            return
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept_key(self.headers["Sec-WebSocket-Key"]))
        self.end_headers()
        self.close_connection = True
        client = _Client(self.wfile)
        with self.server.lock:  # the model, then the values seen so far, then what comes
            client.send(self.server.model)
            for event in {id(e): e for e in self.server.last.values()}.values():
                client.send({**event, "replay": True})
            self.server.clients.append(client)
        try:
            while (frame := ws_read(self.rfile)) is not None:
                opcode, data = frame
                if opcode == 0x8:
                    with client.lock:
                        self.wfile.write(b"\x88\x00")
                    break
                if opcode == 0x9:
                    with client.lock:
                        self.wfile.write(bytes([0x8A, len(data)]) + data)
                    continue
                if opcode != 0x1:
                    continue
                try:
                    request = json.loads(data)
                    if request.get("op") == "play":
                        self.server.play(str(request["element"]), request["value"])
                    elif request.get("op") == "send":
                        self.server.send_raw(request["message"])
                    else:
                        raise CheckFileError(f"unknown op {request.get('op')!r}")
                except (ValueError, KeyError, TypeError, CheckFileError) as e:
                    client.send({"type": "error", "text": str(e)})
                except (OSError, ConnectionError) as e:
                    client.send({"type": "error", "text": f"`rig serve` didn't take it: {e}"})
        except (TimeoutError, OSError):
            pass
        finally:
            with self.server.lock:
                if client in self.server.clients:
                    self.server.clients.remove(client)
