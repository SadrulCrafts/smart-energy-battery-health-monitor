"""
live_api.py
-----------
Stage 3, Step 6: WebSocket endpoint for live updates.

    WS /ws   - stay connected; every new reading is pushed as
               {"type": "reading", "data": {...same fields as GET /status...}}
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .services.live import live_connections

router = APIRouter(tags=["live"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await live_connections.connect(websocket)
    await websocket.send_json({
        "type": "hello",
        "message": "Connected. New readings will be pushed here.",
        "clients": live_connections.count,
    })
    try:
        while True:
            # We do not expect messages from the client; waiting here keeps the
            # connection open and tells us when the client disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        live_connections.disconnect(websocket)