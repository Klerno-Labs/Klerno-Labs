
# ===================================================================
# KLERNO LABS REAL-TIME FASTAPI INTEGRATION
# Add to your main FastAPI application
# ===================================================================

import asyncio
import json
import time
from datetime import datetime

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import the WebSocket manager
from realtime_websocket_server import manager, websocket_endpoint

app = FastAPI(title="Klerno Labs Enterprise Platform")

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Real-time WebSocket endpoints
@app.websocket("/ws")
async def websocket_main(websocket: WebSocket):
    """Main WebSocket endpoint"""
    await websocket_endpoint(websocket)

@app.websocket("/ws/{user_id}")
async def websocket_user(websocket: WebSocket, user_id: str):
    """User-specific WebSocket endpoint"""
    await websocket_endpoint(websocket, user_id)

# Real-time dashboard route
@app.get("/realtime", response_class=HTMLResponse)
async def realtime_dashboard(request: Request):
    """Serve the real-time dashboard"""
    return templates.TemplateResponse("realtime_dashboard.html", {"request": request})

# API endpoints for real-time features
@app.get("/api/realtime/users")
async def get_active_users():
    """Get list of active users"""
    return {"active_users": manager.get_active_users()}

@app.get("/api/realtime/rooms/{room_id}/members")
async def get_room_members(room_id: str):
    """Get members of a specific room"""
    return {"room_id": room_id, "members": manager.get_room_members(room_id)}

@app.post("/api/realtime/broadcast")
async def broadcast_message(message: dict):
    """Broadcast message to all connected users"""
    await manager.broadcast(message)
    return {"status": "Message broadcasted successfully"}

@app.post("/api/realtime/rooms/{room_id}/broadcast")
async def broadcast_to_room(room_id: str, message: dict):
    """Broadcast message to specific room"""
    await manager.broadcast_to_room(message, room_id)
    return {"status": f"Message broadcasted to room {room_id}"}

# Real-time data streaming endpoint
@app.post("/api/realtime/data/update")
async def update_realtime_data(data: dict):
    """Update real-time data and broadcast to clients"""
    await manager.broadcast({
        "type": "data_update",
        "data": data,
        "timestamp": datetime.now().isoformat(),
    })
    return {"status": "Data updated successfully"}

# Server-sent events endpoint for fallback
@app.get("/api/realtime/events")
async def realtime_events(request: Request):
    """Server-sent events endpoint for browsers that don't support WebSockets"""
    async def event_stream():
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                break

            # Send heartbeat
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"

            # Wait before next heartbeat
            await asyncio.sleep(30)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

# Add real-time middleware for tracking
@app.middleware("http")
async def realtime_middleware(request: Request, call_next):
    """Middleware to track user activity and real-time metrics"""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Broadcast performance metrics
    await manager.broadcast({
        "type": "performance_metric",
        "data": {
            "endpoint": str(request.url.path),
            "method": request.method,
            "process_time": process_time,
            "status_code": response.status_code,
        },
        "timestamp": datetime.now().isoformat(),
    })

    return response

# Real-time notification system
class NotificationManager:
    """Manages real-time notifications"""

    @staticmethod
    async def send_notification(user_id: str, notification: dict):
        """Send notification to specific user"""
        await manager.send_to_user({
            "type": "notification",
            "data": notification,
            "timestamp": datetime.now().isoformat(),
        }, user_id)

    @staticmethod
    async def broadcast_notification(notification: dict, exclude_user: str = None):
        """Broadcast notification to all users"""
        await manager.broadcast({
            "type": "notification",
            "data": notification,
            "timestamp": datetime.now().isoformat(),
        }, exclude_user=exclude_user)

# Example usage in your application:
# from realtime_integration import NotificationManager
# await NotificationManager.send_notification("user123", {"message": "Welcome!", "type": "info"})
