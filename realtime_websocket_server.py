
# ===================================================================
# KLERNO LABS REAL-TIME WEBSOCKET SERVER
# Elite Real-Time Features for FastAPI
# ===================================================================

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import uuid
import asyncio
from datetime import datetime
import logging

class ConnectionManager:
    """Manages WebSocket connections and real-time communication"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Dict] = {}
        self.room_connections: Dict[str, Set[str]] = {}
        self.user_presence: Dict[str, Dict] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str = None):
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        
        if not user_id:
            user_id = f"user_{connection_id[:8]}"
            
        self.user_sessions[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "status": "online"
        }
        
        # Update user presence
        self.user_presence[user_id] = {
            "status": "online",
            "last_seen": datetime.now().isoformat(),
            "connections": self.user_presence.get(user_id, {}).get("connections", []) + [connection_id]
        }
        
        # Notify others about user joining
        await self.broadcast_user_presence(user_id, "joined")
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""
        if connection_id in self.active_connections:
            session = self.user_sessions.get(connection_id, {})
            user_id = session.get("user_id")
            
            # Remove connection
            del self.active_connections[connection_id]
            
            if connection_id in self.user_sessions:
                del self.user_sessions[connection_id]
            
            # Update user presence
            if user_id and user_id in self.user_presence:
                connections = self.user_presence[user_id].get("connections", [])
                if connection_id in connections:
                    connections.remove(connection_id)
                
                if not connections:
                    self.user_presence[user_id]["status"] = "offline"
                    self.user_presence[user_id]["last_seen"] = datetime.now().isoformat()
                    await self.broadcast_user_presence(user_id, "left")
                
                self.user_presence[user_id]["connections"] = connections
    
    async def send_personal_message(self, message: str, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message)
            except:
                await self.disconnect(connection_id)
    
    async def send_to_user(self, message: Dict, user_id: str):
        """Send message to all connections of a specific user"""
        if user_id in self.user_presence:
            connections = self.user_presence[user_id].get("connections", [])
            for connection_id in connections[:]:  # Copy to avoid modification during iteration
                await self.send_personal_message(json.dumps(message), connection_id)
    
    async def broadcast(self, message: Dict, exclude_user: str = None):
        """Broadcast message to all connected users"""
        message_json = json.dumps(message)
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            session = self.user_sessions.get(connection_id, {})
            if exclude_user and session.get("user_id") == exclude_user:
                continue
                
            try:
                await websocket.send_text(message_json)
            except:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
    
    async def broadcast_to_room(self, message: Dict, room_id: str, exclude_user: str = None):
        """Broadcast message to all users in a specific room"""
        if room_id in self.room_connections:
            for connection_id in list(self.room_connections[room_id]):
                session = self.user_sessions.get(connection_id, {})
                if exclude_user and session.get("user_id") == exclude_user:
                    continue
                await self.send_personal_message(json.dumps(message), connection_id)
    
    async def join_room(self, connection_id: str, room_id: str):
        """Add user to a room"""
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        self.room_connections[room_id].add(connection_id)
        
        session = self.user_sessions.get(connection_id, {})
        user_id = session.get("user_id")
        
        # Notify room about new member
        await self.broadcast_to_room({
            "type": "room_member_joined",
            "room_id": room_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }, room_id, exclude_user=user_id)
    
    async def leave_room(self, connection_id: str, room_id: str):
        """Remove user from a room"""
        if room_id in self.room_connections:
            self.room_connections[room_id].discard(connection_id)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]
                
        session = self.user_sessions.get(connection_id, {})
        user_id = session.get("user_id")
        
        # Notify room about member leaving
        await self.broadcast_to_room({
            "type": "room_member_left",
            "room_id": room_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }, room_id, exclude_user=user_id)
    
    async def broadcast_user_presence(self, user_id: str, action: str):
        """Broadcast user presence changes"""
        presence_data = self.user_presence.get(user_id, {})
        await self.broadcast({
            "type": "user_presence",
            "action": action,
            "user_id": user_id,
            "status": presence_data.get("status", "offline"),
            "timestamp": datetime.now().isoformat()
        }, exclude_user=user_id)
    
    def get_active_users(self) -> List[Dict]:
        """Get list of active users"""
        active_users = []
        for user_id, presence in self.user_presence.items():
            if presence.get("status") == "online":
                active_users.append({
                    "user_id": user_id,
                    "status": presence.get("status"),
                    "last_seen": presence.get("last_seen"),
                    "connection_count": len(presence.get("connections", []))
                })
        return active_users
    
    def get_room_members(self, room_id: str) -> List[str]:
        """Get list of users in a room"""
        if room_id not in self.room_connections:
            return []
        
        members = []
        for connection_id in self.room_connections[room_id]:
            session = self.user_sessions.get(connection_id, {})
            user_id = session.get("user_id")
            if user_id:
                members.append(user_id)
        return list(set(members))  # Remove duplicates

# Global connection manager
manager = ConnectionManager()

# WebSocket endpoint for FastAPI
async def websocket_endpoint(websocket: WebSocket, user_id: str = None):
    """Main WebSocket endpoint"""
    connection_id = await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            await handle_websocket_message(connection_id, message_data)
            
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await manager.disconnect(connection_id)

async def handle_websocket_message(connection_id: str, message: Dict):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    session = manager.user_sessions.get(connection_id, {})
    user_id = session.get("user_id")
    
    if message_type == "ping":
        await manager.send_personal_message(json.dumps({"type": "pong"}), connection_id)
        
    elif message_type == "join_room":
        room_id = message.get("room_id")
        if room_id:
            await manager.join_room(connection_id, room_id)
            
    elif message_type == "leave_room":
        room_id = message.get("room_id")
        if room_id:
            await manager.leave_room(connection_id, room_id)
            
    elif message_type == "chat_message":
        room_id = message.get("room_id")
        content = message.get("content")
        
        if room_id and content:
            await manager.broadcast_to_room({
                "type": "chat_message",
                "room_id": room_id,
                "user_id": user_id,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "message_id": str(uuid.uuid4())
            }, room_id)
            
    elif message_type == "user_activity":
        activity_data = message.get("data", {})
        await manager.broadcast({
            "type": "user_activity",
            "user_id": user_id,
            "activity": activity_data,
            "timestamp": datetime.now().isoformat()
        }, exclude_user=user_id)
        
    elif message_type == "data_update":
        # Handle real-time data updates
        update_data = message.get("data", {})
        await manager.broadcast({
            "type": "data_update",
            "data": update_data,
            "updated_by": user_id,
            "timestamp": datetime.now().isoformat()
        }, exclude_user=user_id)

# Add this to your FastAPI routes
# app.websocket("/ws/{user_id}")(websocket_endpoint)
# app.websocket("/ws")(lambda websocket: websocket_endpoint(websocket))
