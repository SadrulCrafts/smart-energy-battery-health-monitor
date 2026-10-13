"""
ws_listen.py
------------
Stage 3, Step 6: a tiny test client that connects to  WS /ws  and prints every
reading the backend pushes. The dashboard will do the same thing later.

Run from the project root (backend must be running):
    python backend/ws_listen.py
Stop with Ctrl+C.

Note: recv() waits at most 1 second at a time. On Windows, Ctrl+C is not
noticed while a program waits without a time limit, so the short timeout lets
Ctrl+C work even when no readings are arriving.
"""

import json
import sys

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

URL = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8000/ws"
WAIT_S = 1.0


def show(message):
    """Print one message from the server in a readable line."""
    if message.get("type") == "hello":
        print(f"[hello] {message['message']} (clients: {message['clients']})")
    elif message.get("type") == "reading":
        r = message["data"]
        alert = f"  <- {r['alert_message']}" if r["alert_message"] else ""
        print(f"[live] id={r['id']:<6} {r['source']:<9} {r['status']:<8} "
              f"V={r['voltage_v']:.3f}  I={r['current_a']:+.3f}  "
              f"T={r['temperature_c']}{alert}")
    else:
        print("[other]", message)


def main():
    print(f"Connecting to {URL} ...  (press Ctrl+C to stop)")
    try:
        with connect(URL) as websocket:
            while True:
                try:
                    raw = websocket.recv(timeout=WAIT_S)
                except TimeoutError:
                    continue  # nothing new yet; loop again (this is where Ctrl+C is noticed)
                show(json.loads(raw))
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except ConnectionClosed:
        print("Connection closed by the server.")
    except OSError:
        print("Could not connect. Is uvicorn running?")


if __name__ == "__main__":
    main()