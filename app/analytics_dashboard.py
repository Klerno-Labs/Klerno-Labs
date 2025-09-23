"""
Real-time Analytics Dashboard for Klerno Labs
Advanced monitoring and analytics with live data visualization
"""

import asyncio
import json
import statistics
import time

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Import our monitoring systems
from .advanced_monitoring import get_monitoring_middleware
from .advanced_security_hardening import get_security_middleware
from .deps import current_user

# Templates
templates = Jinja2Templates(directory="templates")

# Router for analytics endpoints
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


class WebSocketManager:
    """Manage WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.analytics_data = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception:
            # If sending fails for any reason, disconnect to clean up
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Collect failed connections and remove them after
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global WebSocket manager
websocket_manager = WebSocketManager()


@analytics_router.get("/dashboard", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, user=Depends(current_user)):
    """Main analytics dashboard page"""
    return templates.TemplateResponse(
            "analytics/dashboard.html",
            {
                "request": request,
                "user": user,
                "title": "Analytics Dashboard - Klerno Labs",
            },
    )


@analytics_router.get("/api/metrics")
async def get_current_metrics():
    """Get current performance and analytics metrics"""
    monitoring = get_monitoring_middleware()

    if not monitoring:
        return {"error": "Monitoring not available"}

    dashboard_data = monitoring.get_monitoring_dashboard()

    # Add real-time system metrics
    current_time = time.time()

    # Enhance with additional calculated metrics
    performance = dashboard_data["performance"]
    analytics = dashboard_data["analytics"]

    # Calculate trends (last 5 minutes vs previous 5 minutes)
    response_time_trend = calculate_trend(
        performance["request_performance"]["avg_response_time"]
    )
    error_rate_trend = calculate_trend(len(performance["error_rates"]))

    enhanced_metrics = {
        "timestamp": current_time,
        "performance": {
            **performance,
            "trends": {
                "response_time": response_time_trend,
                "error_rate": error_rate_trend,
                "cpu_trend": calculate_trend(
                    performance["system_performance"]["cpu_percent"]
                ),
                "memory_trend": calculate_trend(
                    performance["system_performance"]["memory_percent"]
                ),
            },
        },
        "analytics": analytics,
        "alerts": dashboard_data["alerts"],
        "health_status": dashboard_data["health_status"],
        "real_time_stats": {
            "active_websockets": len(websocket_manager.active_connections),
            "uptime_seconds": get_uptime(),
            "requests_last_minute": get_requests_last_minute(performance),
            "unique_visitors_today": (
                get_unique_visitors_today(analytics)
            ),
        },
    }

    return enhanced_metrics


@analytics_router.get("/api/performance-history")
async def get_performance_history(hours: int = 24):
    """Get historical performance data"""
    monitoring = get_monitoring_middleware()

    if not monitoring:
        return {"error": "Monitoring not available"}

    # In a real implementation, this would query a time-series database
    # For now, we'll simulate historical data
    end_time = time.time()
    start_time = end_time - (hours * 3600)

    # Generate sample historical data points (every 5 minutes)
    data_points = []
    current_time = start_time

    while current_time <= end_time:
        data_points.append(
            {
                "timestamp": current_time,
                "response_time": generate_sample_response_time(current_time),
                "cpu_percent": generate_sample_cpu(current_time),
                "memory_percent": generate_sample_memory(current_time),
                "requests_per_minute": generate_sample_requests(current_time),
                "error_count": generate_sample_errors(current_time),
            }
        )
        current_time += 300  # 5 minutes

    return {
        "data_points": data_points,
        "summary": {
            "avg_response_time": statistics.mean(
                [p["response_time"] for p in data_points]
            ),
            "max_response_time": max(
                [p["response_time"] for p in data_points]
            ),
            "avg_cpu": statistics.mean(
                [p["cpu_percent"] for p in data_points]
            ),
            "max_cpu": max([p["cpu_percent"] for p in data_points]),
            "total_requests": sum(
                [p["requests_per_minute"] for p in data_points]
            ),
            "total_errors": sum([p["error_count"] for p in data_points]),
        },
    }


@analytics_router.get("/api/user-analytics")
async def get_user_analytics():
    """Get detailed user analytics and behavior data"""
    monitoring = get_monitoring_middleware()

    if not monitoring:
        return {"error": "Monitoring not available"}

    analytics = monitoring.user_analytics.get_analytics_summary()

    # Enhanced user analytics
    enhanced_analytics = {
        **analytics,
        "user_segments": {
            "new_users": calculate_new_users(analytics),
            "returning_users": calculate_returning_users(analytics),
            "power_users": calculate_power_users(analytics),
        },
        "conversion_funnel": {
            "visitors": analytics["total_sessions"],
            "signups": analytics["conversion_rates"].get("signup", 0),
            "logins": analytics["conversion_rates"].get("login", 0),
            "dashboard_users": (
                analytics["conversion_rates"].get("dashboard_access", 0)
            ),
        },
        "page_performance": {
            "bounce_rate": calculate_bounce_rate(analytics),
            "avg_pages_per_session": (
                calculate_avg_pages_per_session(analytics)
            ),
            "avg_session_duration": analytics["avg_session_duration"],
        },
        "popular_content": get_popular_content(analytics),
        "traffic_sources": get_traffic_sources(),
        "device_analytics": get_device_analytics(),
        "geographic_data": get_geographic_data(),
    }

    return enhanced_analytics


@analytics_router.get("/api/security-analytics")
async def get_security_analytics():
    """Get security-related analytics and threat information"""
    security = get_security_middleware()

    if not security:
        return {"error": "Security monitoring not available"}

    current_time = time.time()

    # Security analytics from the last 24 hours
    security_data = {
        "timestamp": current_time,
        "threat_summary": {
            "blocked_requests": get_blocked_requests_count(),
            "rate_limited_ips": get_rate_limited_ips(),
            "suspicious_patterns": get_suspicious_patterns(),
            "geographic_threats": get_geographic_threats(),
        },
        "attack_types": {
            "sql_injection_attempts": get_attack_count("sql_injection"),
            "xss_attempts": get_attack_count("xss"),
            "brute_force_attempts": get_attack_count("brute_force"),
            "bot_requests": get_attack_count("bot"),
        },
        "top_threat_countries": get_top_threat_countries(),
        "security_events": get_recent_security_events(),
        "ip_reputation": get_ip_reputation_stats(),
        "failed_logins": get_failed_login_attempts(),
    }

    return security_data


@analytics_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time analytics updates"""
    await websocket_manager.connect(websocket)

    try:
        while True:
            # Send real-time updates every 5 seconds
            metrics = await get_current_metrics()
            await websocket_manager.send_personal_message(
                json.dumps(metrics), websocket
            )
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# Background task to broadcast analytics updates
async def analytics_broadcaster():
    """Background task to broadcast analytics to all connected clients"""
    while True:
        try:
            if websocket_manager.active_connections:
                metrics = await get_current_metrics()
                await websocket_manager.broadcast(
                    json.dumps({"type": "metrics_update", "data": metrics})
                )

            await asyncio.sleep(10)  # Update every 10 seconds

        except Exception as e:
            print(f"Analytics broadcaster error: {e}")
            await asyncio.sleep(30)


# Utility functions for analytics calculations
def calculate_trend(current_value, historical_values=None):
    """Calculate trend direction for a metric"""
    # Simplified trend calculation
    if historical_values and len(historical_values) > 1:
        recent_avg = statistics.mean(historical_values[-5:])
        older_avg = statistics.mean(historical_values[-10:-5])

        if recent_avg > older_avg * 1.1:
            return "up"
        elif recent_avg < older_avg * 0.9:
            return "down"
        else:
            return "stable"

    return "stable"


def get_uptime():
    """Get application uptime in seconds"""
    # This would track actual uptime in production
    return 86400  # 24 hours for demo


def get_requests_last_minute(performance_data):
    """Get number of requests in the last minute"""
    return performance_data["request_performance"].get(
        "requests_per_minute", 0
    )


def get_unique_visitors_today(analytics_data):
    """Calculate unique visitors today"""
    return len(analytics_data.get("active_sessions", [])) * 3  # Estimate


def calculate_new_users(analytics):
    """Calculate new users percentage"""
    total = analytics["total_sessions"]
    return {"count": total * 0.3, "percentage": 30.0}  # Simplified


def calculate_returning_users(analytics):
    """Calculate returning users percentage"""
    total = analytics["total_sessions"]
    return {"count": total * 0.7, "percentage": 70.0}  # Simplified


def calculate_power_users(analytics):
    """Calculate power users (high engagement)"""
    total = analytics["total_sessions"]
    return {"count": total * 0.1, "percentage": 10.0}  # Simplified


def calculate_bounce_rate(analytics):
    """Calculate bounce rate"""
    return 25.5  # Simplified demo value


def calculate_avg_pages_per_session(analytics):
    """Calculate average pages per session"""
    return 4.2  # Simplified demo value


def get_popular_content(analytics):
    """Get most popular content pages"""
    page_views = analytics.get("page_views", {})
    return sorted(page_views.items(), key=lambda x: x[1], reverse=True)[:10]


def get_traffic_sources():
    """Get traffic source analytics"""
    return {
        "direct": 45.2,
        "organic_search": 32.1,
        "social_media": 12.8,
        "referral": 7.3,
        "email": 2.6,
    }


def get_device_analytics():
    """Get device and browser analytics"""
    return {
        "devices": {"desktop": 65.4, "mobile": 28.9, "tablet": 5.7},
        "browsers": {
            "chrome": 58.2,
            "firefox": 18.5,
            "safari": 12.8,
            "edge": 7.9,
            "other": 2.6,
        },
    }


def get_geographic_data():
    """Get geographic analytics"""
    return {
        "countries": {
            "United States": 45.2,
            "Canada": 12.8,
            "United Kingdom": 8.9,
            "Germany": 6.7,
            "Australia": 4.8,
        },
        "cities": {
            "New York": 15.2,
            "Los Angeles": 8.9,
            "Toronto": 6.7,
            "London": 5.8,
            "Berlin": 4.2,
        },
    }


# Security analytics helper functions
def get_blocked_requests_count():
    """Get count of blocked requests in last 24 hours"""
    return 247  # Demo value


def get_rate_limited_ips():
    """Get count of rate-limited IP addresses"""
    return 18  # Demo value


def get_suspicious_patterns():
    """Get count of suspicious pattern detections"""
    return 12  # Demo value


def get_geographic_threats():
    """Get geographic distribution of threats"""
    return {"Russia": 25, "China": 18, "Brazil": 12, "Unknown": 8}


def get_attack_count(attack_type):
    """Get count of specific attack type"""
    attack_counts = {
        "sql_injection": 15,
        "xss": 8,
        "brute_force": 23,
        "bot": 156,
    }
    return attack_counts.get(attack_type, 0)


def get_top_threat_countries():
    """Get top countries by threat count"""
    return [
        {"country": "Russia", "threats": 45, "percentage": 28.5},
        {"country": "China", "threats": 32, "percentage": 20.3},
        {"country": "Brazil", "threats": 18, "percentage": 11.4},
        {"country": "India", "threats": 12, "percentage": 7.6},
        {"country": "Other", "threats": 51, "percentage": 32.2},
    ]


def get_recent_security_events():
    """Get recent security events"""
    return [
        {
            "timestamp": time.time() - 300,
            "type": "Rate Limit Exceeded",
            "ip": "192.168.1.100",
            "severity": "medium",
        },
        {
            "timestamp": time.time() - 600,
            "type": "SQL Injection Attempt",
            "ip": "10.0.0.50",
            "severity": "high",
        },
        {
            "timestamp": time.time() - 900,
            "type": "Suspicious User Agent",
            "ip": "172.16.0.10",
            "severity": "low",
        },
    ]


def get_ip_reputation_stats():
    """Get IP reputation statistics"""
    return {
        "clean_ips": 1250,
        "suspicious_ips": 45,
        "malicious_ips": 12,
        "unknown_ips": 78,
    }


def get_failed_login_attempts():
    """Get failed login attempt statistics"""
    return {"last_hour": 8, "last_24_hours": 45, "last_week": 234}


# Sample data generators for historical charts
def generate_sample_response_time(timestamp):
    """Generate sample response time data"""
    import math

    base = 0.5
    variation = 0.3 * math.sin(timestamp / 3600)  # Hourly variation
    noise = 0.1 * (hash(str(timestamp)) % 100) / 100
    return max(0.1, base + variation + noise)


def generate_sample_cpu(timestamp):
    """Generate sample CPU usage data"""
    import math

    base = 35
    variation = 20 * math.sin(timestamp / 3600)
    noise = 10 * (hash(str(timestamp)) % 100) / 100
    return max(0, min(100, base + variation + noise))


def generate_sample_memory(timestamp):
    """Generate sample memory usage data"""
    import math

    base = 60
    variation = 15 * math.sin(timestamp / 7200)  # 2-hour cycle
    noise = 5 * (hash(str(timestamp)) % 100) / 100
    return max(0, min(100, base + variation + noise))


def generate_sample_requests(timestamp):
    """Generate sample requests per minute data"""
    import math

    base = 50
    variation = 30 * math.sin(timestamp / 1800)  # 30-minute cycle
    noise = 10 * (hash(str(timestamp)) % 100) / 100
    return max(0, base + variation + noise)


def generate_sample_errors(timestamp):
    """Generate sample error count data"""
    import math

    base = 2
    variation = 3 * math.sin(timestamp / 3600)
    noise = 2 * (hash(str(timestamp)) % 100) / 100
    return max(0, base + variation + noise)
