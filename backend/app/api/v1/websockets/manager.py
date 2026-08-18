import json
import asyncio
from typing import Dict, List, Set, Optional
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        # restaurant_id -> {user_id: [websockets]}
        self.active_connections: Dict[UUID, Dict[UUID, List[WebSocket]]] = defaultdict(lambda: defaultdict(list))
        # restaurant_id -> {table_id: [websockets]} for public connections
        self.public_connections: Dict[UUID, Dict[UUID, List[WebSocket]]] = defaultdict(lambda: defaultdict(list))
    
    async def connect(self, websocket: WebSocket, restaurant_id: UUID, user_id: UUID):
        await websocket.accept()
        self.active_connections[restaurant_id][user_id].append(websocket)
    
    async def connect_public(self, websocket: WebSocket, restaurant_id: UUID, table_id: UUID):
        await websocket.accept()
        self.public_connections[restaurant_id][table_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, restaurant_id: UUID, user_id: UUID):
        if restaurant_id in self.active_connections:
            if user_id in self.active_connections[restaurant_id]:
                if websocket in self.active_connections[restaurant_id][user_id]:
                    self.active_connections[restaurant_id][user_id].remove(websocket)
                if not self.active_connections[restaurant_id][user_id]:
                    del self.active_connections[restaurant_id][user_id]
            if not self.active_connections[restaurant_id]:
                del self.active_connections[restaurant_id]
    
    def disconnect_public(self, websocket: WebSocket, restaurant_id: UUID, table_id: UUID):
        if restaurant_id in self.public_connections:
            if table_id in self.public_connections[restaurant_id]:
                if websocket in self.public_connections[restaurant_id][table_id]:
                    self.public_connections[restaurant_id][table_id].remove(websocket)
                if not self.public_connections[restaurant_id][table_id]:
                    del self.public_connections[restaurant_id][table_id]
            if not self.public_connections[restaurant_id]:
                del self.public_connections[restaurant_id]
    
    async def send_personal_message(self, message: dict, restaurant_id: UUID, user_id: UUID):
        if restaurant_id in self.active_connections:
            for ws in self.active_connections[restaurant_id].get(user_id, []):
                try:
                    await ws.send_json(message)
                except Exception:
                    pass
    
    async def broadcast_to_restaurant(self, message: dict, restaurant_id: UUID):
        # Send to all authenticated users in restaurant
        if restaurant_id in self.active_connections:
            for user_websockets in self.active_connections[restaurant_id].values():
                for ws in user_websockets:
                    try:
                        await ws.send_json(message)
                    except Exception:
                        pass
    
    async def broadcast_to_table(self, message: dict, restaurant_id: UUID, table_id: UUID):
        # Send to public connections (customer menu)
        if restaurant_id in self.public_connections:
            for ws in self.public_connections[restaurant_id].get(table_id, []):
                try:
                    await ws.send_json(message)
                except Exception:
                    pass
    
    async def broadcast_order_update(self, restaurant_id: UUID, order_data: dict):
        """Broadcast order update to all relevant connections"""
        message = {
            "type": "order_update",
            "payload": order_data
        }
        await self.broadcast_to_restaurant(message, restaurant_id)
        
        # Also send to table's public connection if exists
        if "table_id" in order_data:
            await self.broadcast_to_table(message, restaurant_id, UUID(order_data["table_id"]))
    
    async def broadcast_table_update(self, restaurant_id: UUID, table_data: dict):
        """Broadcast table status update"""
        message = {
            "type": "table_update",
            "payload": table_data
        }
        await self.broadcast_to_restaurant(message, restaurant_id)
        
        if "id" in table_data:
            await self.broadcast_to_table(message, restaurant_id, UUID(table_data["id"]))
    
    async def broadcast_service_call(self, restaurant_id: UUID, call_data: dict):
        """Broadcast new service call to waiters"""
        message = {
            "type": "service_call",
            "payload": call_data
        }
        await self.broadcast_to_restaurant(message, restaurant_id)
    
    async def broadcast_kitchen_update(self, restaurant_id: UUID, order_data: dict):
        """Broadcast to kitchen display"""
        message = {
            "type": "kitchen_update",
            "payload": order_data
        }
        await self.broadcast_to_restaurant(message, restaurant_id)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, restaurant_id: UUID, user_id: UUID):
    await manager.connect(websocket, restaurant_id, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            try:
                msg = json.loads(data)
                # Could handle ping/pong, subscriptions, etc.
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, restaurant_id, user_id)


async def public_websocket_endpoint(websocket: WebSocket, restaurant_id: UUID, table_id: UUID):
    await manager.connect_public(websocket, restaurant_id, table_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect_public(websocket, restaurant_id, table_id)