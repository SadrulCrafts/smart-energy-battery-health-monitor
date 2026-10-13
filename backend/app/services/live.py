"""
live.py
-------
Stage 3, Step 6: keep track of connected WebSocket clients (for example the
dashboard) and push new readings to all of them.
"""


class LiveConnections:
    def __init__(self):
        self._clients = set()

    @property
    def count(self):
        return len(self._clients)

    async def connect(self, websocket):
        await websocket.accept()
        self._clients.add(websocket)

    def disconnect(self, websocket):
        self._clients.discard(websocket)

    async def broadcast(self, message):
        """Send one JSON message to every client; drop clients that have gone away."""
        gone = []
        for websocket in list(self._clients):
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 - a closed/broken connection must not stop the others
                gone.append(websocket)
        for websocket in gone:
            self.disconnect(websocket)


# One shared instance used by the whole app
live_connections = LiveConnections()