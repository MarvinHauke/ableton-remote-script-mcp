"""`rig probe` (plan 0002 step 1): does Live see the rig's virtual port, and does a message sent
there reach a Remote Script and come back?

1. Open the port and wait until Live sends anything on it: a script picked on that port sends
   its LED and value state when it starts, which shows that Live connected the port.
2. Send one message (default: the UC4's fader 1, CC 40 = 100 on channel 13) and collect the
   replies until Live has been quiet for a moment.
"""

from __future__ import annotations

import time

from .ports import describe

DEFAULT_SEND = [0xBC, 40, 100]  # Faderfox UC4, SE17: fader 1 = track 1's volume


def probe(port, connect_seconds: float, send: list[int], reply_seconds: float = 2.0,
          quiet: float = 0.3, wait=None, log=print) -> dict:
    """The probe's result: whether Live connected, what it sent first, the replies to `send`."""
    from .ports import wait_for

    wait = wait or wait_for
    log(f"opened the virtual port `{port.name}`; in Live, pick it as a Control Surface's Input "
        f"and Output (waiting up to {connect_seconds:.0f} s for Live to send anything)")
    first = wait(port, connect_seconds, until_any=True)
    if not first:
        return {"connected": False, "port": port.name, "first": [], "sent": None, "replies": []}
    first += wait(port, 1.0, quiet=quiet)  # the rest of the script's start-up state
    log(f"Live sent {len(first)} message(s) on `{port.name}`: it sees the port")
    port.send(send)
    log(f"sent {describe(send)}")
    replies = wait(port, reply_seconds, quiet=quiet)
    same = [r for r in replies if r.message[:2] == send[:2]]
    return {
        "connected": True,
        "port": port.name,
        "first": [describe(r.message) for r in first],
        "sent": describe(send),
        "replies": [describe(r.message) for r in replies],
        "echo": [describe(r.message) for r in same],
    }


def run_probe(name: str, connect_seconds: float, send: list[int], log=print) -> dict:
    from .ports import VirtualPort

    port = VirtualPort(name)
    try:
        time.sleep(0.2)
        return probe(port, connect_seconds, send, log=log)
    finally:
        port.close()
