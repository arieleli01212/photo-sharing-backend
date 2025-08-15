from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from typing import List

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.guest_count = 0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.guest_count = len(self.active_connections)
        await self.broadcast_guest_count()
        print("➕ connected", self.guest_count)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.guest_count = len(self.active_connections)
        print("➖ disconnected", self.guest_count)

    async def broadcast_guest_count(self) -> None:
        stale = []
        for ws in list(self.active_connections):
            if ws.client_state != WebSocketState.CONNECTED:
                stale.append(ws)
                continue

            try:
                await ws.send_json({"guestCount": self.guest_count})
            except Exception as e:
                # Any send error means the connection is bad
                print(f"Failed to send to client: {e}")
                stale.append(ws)

        # Remove stale connections
        for ws in stale:
            if ws in self.active_connections:
                self.active_connections.remove(ws)
        
        # Update guest count after cleanup
        self.guest_count = len(self.active_connections)

    async def handle_websocket(self, websocket: WebSocket):
        await self.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass  # Handle disconnect gracefully
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            # Clean up connection
            self.disconnect(websocket)
            await self.broadcast_guest_count()

# Global instance
websocket_manager = WebSocketManager()