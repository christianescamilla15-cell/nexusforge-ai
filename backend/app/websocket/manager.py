import json
import logging

from fastapi import WebSocket

from app.db.client import get_redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        logger.info("WebSocket connected: room=%s (total=%d)", room_id, len(self.active_connections[room_id]))

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
            logger.info("WebSocket disconnected: room=%s", room_id)

    async def broadcast(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            data = json.dumps(message)
            disconnected = []
            for ws in self.active_connections[room_id]:
                try:
                    await ws.send_text(data)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self.disconnect(room_id, ws)

    async def listen_redis(self, room_id: str):
        """Subscribe to Redis pub/sub channel and broadcast to WebSocket clients."""
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"run:{room_id}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await self.broadcast(room_id, data)


manager = ConnectionManager()
