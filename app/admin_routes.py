# app / admin_routes.py
"""
Comprehensive admin API routes with role - based access control,
    user management, blocking system, and monitoring dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import json

from .models import User, UserRole, AccountStatus, BlockUserRequest, UserCreateRequest, UserUpdateRequest
from .admin_manager import AdminManager
from .system_monitor import SystemMonitor
from .auth_enhanced import get_current_user
from .security_session import verify_pw as verify_password, hash_pw as get_password_hash

router=APIRouter(prefix="/admin", tags=["admin"])
templates=Jinja2Templates(directory="app / templates")

# Initialize managers
admin_manager=AdminManager()
system_monitor=SystemMonitor()

# Dependency to check admin access


async def require_admin_access(current_user: Optional[User] = Depends(get_current_user)):
    if not current_user or not current_user.is_manager_or_higher():
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_admin_edit_access(current_user: Optional[User] = Depends(get_current_user)):
    if not current_user or not current_user.is_admin_or_higher():
        raise HTTPException(status_code=403, detail="Admin edit access required")
    return current_user


async def require_owner_access(current_user: Optional[User] = Depends(get_current_user)):
    if not current_user or not current_user.is_owner():
        raise HTTPException(status_code=403, detail="Owner access required")
    return current_user

@router.get("/dashboard", response_class=HTMLResponse)


async def admin_dashboard(request: Request, current_user: User = Depends(require_admin_access)):
    """Main admin dashboard with system monitoring and user management."""
    # Ensure templates have access to url_path_for
    templates.env.globals["url_path_for"] = request.app.url_path_for

    # Get dashboard data
    dashboard_data=system_monitor.get_dashboard_data(24)
    users=admin_manager.get_all_users(current_user.email)
    recent_actions=admin_manager.get_admin_actions(
        start_date=datetime.now(timezone.utc) - timedelta(days=7)
    )

    context={
        "request": request,
            "user": current_user,
            "dashboard_data": dashboard_data,
            "users": users,
            "recent_actions": recent_actions[:10],  # Last 10 actions
        "user_roles": [role.value for role in UserRole],
            "account_statuses": [status.value for status in AccountStatus]
    }

    return templates.TemplateResponse("admin_dashboard.html", context)

@router.get("/api / dashboard - data")


async def get_dashboard_data(
    hours: int=24,
        current_user: User=Depends(require_admin_access)
):
    """Get real - time dashboard data for AJAX updates."""
    return system_monitor.get_dashboard_data(hours)

@router.get("/api / users")


async def get_all_users(current_user: User = Depends(require_admin_access)):
    """Get all users for management interface."""
    users=admin_manager.get_all_users(current_user.email)
    return {"users": users}

@router.post("/api / users")


async def create_user(
    user_data: UserCreateRequest,
        current_user: User=Depends(require_admin_edit_access)
):
    """Create new user with role assignment."""

    # Check if current user can assign this role
    if not current_user.can_edit_role(user_data.role):
        raise HTTPException(
            status_code=403,
                detail=f"Insufficient permissions to create {user_data.role.value} role"
        )

    result=admin_manager.create_user(
        email=user_data.email,
            password=user_data.password,
            role=user_data.role,
            admin_email=current_user.email,
            is_premium=user_data.is_premium
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result

@router.put("/api / users/{target_email}/role")


async def update_user_role(
    target_email: str,
        new_role: UserRole,
        current_user: User=Depends(require_admin_edit_access)
):
    """Update user role with permission checking."""

    result=admin_manager.update_user_role(
        admin_email=current_user.email,
            target_email=target_email,
            new_role=new_role
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result

@router.post("/api / users / block")


async def block_user(
    block_request: BlockUserRequest,
        current_user: User=Depends(require_admin_edit_access)
):
    """Block user with confirmation and reason tracking."""

    result=admin_manager.block_user(
        admin_email=current_user.email,
            request=block_request
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result

@router.post("/api / users/{target_email}/unblock")


async def unblock_user(
    target_email: str,
        reason: str=Form(...),
        current_user: User=Depends(require_admin_edit_access)
):
    """Unblock user account."""

    result=admin_manager.unblock_user(
        admin_email=current_user.email,
            target_email=target_email,
            reason=reason
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result

@router.put("/api / users/{target_email}/password")


async def change_user_password(
    target_email: str,
        new_password: str=Form(...),
        current_user: User=Depends(require_admin_edit_access)
):
    """Change user password (admin function)."""

    try:
        target_user=admin_manager.get_user_by_email(target_email)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check permissions - owners can change anyone's password,
            # admins can change manager / user passwords
        if not current_user.is_owner() and target_user.is_admin_or_higher():
            raise HTTPException(
                status_code=403,
                    detail="Insufficient permissions to change this user's password"
            )

        # Update password
        new_hash=get_password_hash(new_password)

        import sqlite3
        with sqlite3.connect(admin_manager.db_path) as conn:
            cursor=conn.cursor()
            cursor.execute("""
                UPDATE users_enhanced SET password_hash=? WHERE email=?
            """, (new_hash, target_email))
            conn.commit()

        # Log action
        admin_manager.log_admin_action(
            admin_email=current_user.email,
                target_email=target_email,
                action="password_change",
                reason="Password changed by admin"
        )

        return {"success": True, "message": "Password changed successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error changing password: {str(e)}")

@router.get("/api / actions")


async def get_admin_actions(
    days: int=30,
        current_user: User=Depends(require_admin_access)
):
    """Get admin action history."""

    start_date=datetime.now(timezone.utc) - timedelta(days=days)
    actions=admin_manager.get_admin_actions(start_date=start_date)

    return {
        "actions": [
            {
                "id": action.id,
                    "admin_email": action.admin_email,
                    "target_email": action.target_email,
                    "action": action.action.value,
                    "reason": action.reason,
                    "timestamp": action.timestamp.isoformat(),
                    "additional_data": action.additional_data
            }
            for action in actions
        ]
    }

@router.get("/api / reports / monthly - blocks")


async def get_monthly_block_report(
    year: int,
        month: int,
        current_user: User=Depends(require_admin_access)
):
    """Get monthly blocking report with professional charts."""

    report=admin_manager.get_monthly_block_report(year, month)
    return report

@router.put("/api / settings / notification - email")


async def update_notification_email(
    new_email: str=Form(...),
        current_user: User=Depends(require_owner_access)
):
    """Update notification email (owner only)."""

    result=admin_manager.update_notification_email(new_email, current_user.email)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result

@router.get("/api / system / health")


async def get_system_health(current_user: User = Depends(require_admin_access)):
    """Get comprehensive system health status."""

    system_metrics=system_monitor.get_system_metrics()
    app_metrics=system_monitor.get_application_metrics()
    security_metrics=system_monitor.get_security_metrics()

    # Determine overall health status
    health_status="healthy"
    warnings=[]

    if system_metrics:
        if system_metrics.cpu_percent > 80:
            health_status="warning"
            warnings.append(f"High CPU usage: {system_metrics.cpu_percent}%")

        if system_metrics.memory_percent > 85:
            health_status="warning"
            warnings.append(f"High memory usage: {system_metrics.memory_percent}%")

        if system_metrics.disk_usage_percent > 90:
            health_status="critical"
            warnings.append(f"High disk usage: {system_metrics.disk_usage_percent}%")

    if security_metrics and security_metrics.threat_level in ["MEDIUM", "HIGH"]:
        health_status="warning" if security_metrics.threat_level == "MEDIUM" else "critical"
        warnings.append(f"Security threat level: {security_metrics.threat_level}")

    return {
        "status": health_status,
            "warnings": warnings,
            "metrics": {
            "system": system_metrics.__dict__ if system_metrics else None,
                "application": app_metrics.__dict__ if app_metrics else None,
                "security": security_metrics.__dict__ if security_metrics else None
        },
            "uptime": {
            "seconds": int(system_monitor.start_time),
                "formatted": f"{(datetime.now().timestamp() - system_monitor.start_time) / 3600:.1f} hours"
        }
    }

@router.get("/api / charts / system - performance")


async def get_system_performance_chart(
    hours: int=24,
        current_user: User=Depends(require_admin_access)
):
    """Get system performance data formatted for charts."""

    dashboard_data=system_monitor.get_dashboard_data(hours)

    if "historical_data" not in dashboard_data:
        return {"error": "No data available"}

    system_data=dashboard_data["historical_data"]["system"]

    # Format data for chart.js
    timestamps=[item["timestamp"] for item in system_data]

    chart_data={
        "labels": timestamps,
            "datasets": [
            {
                "label": "CPU Usage (%)",
                    "data": [item["cpu_percent"] for item in system_data],
                    "borderColor": "rgb(255, 99, 132)",
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "tension": 0.1
            },
                {
                "label": "Memory Usage (%)",
                    "data": [item["memory_percent"] for item in system_data],
                    "borderColor": "rgb(54, 162, 235)",
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "tension": 0.1
            },
                {
                "label": "Disk Usage (%)",
                    "data": [item["disk_usage_percent"] for item in system_data],
                    "borderColor": "rgb(255, 205, 86)",
                    "backgroundColor": "rgba(255, 205, 86, 0.2)",
                    "tension": 0.1
            }
        ]
    }

    return chart_data

@router.get("/api / charts / user - activity")


async def get_user_activity_chart(
    hours: int=24,
        current_user: User=Depends(require_admin_access)
):
    """Get user activity data formatted for charts."""

    dashboard_data=system_monitor.get_dashboard_data(hours)

    if "historical_data" not in dashboard_data:
        return {"error": "No data available"}

    app_data=dashboard_data["historical_data"]["application"]

    chart_data={
        "labels": [item["timestamp"] for item in app_data],
            "datasets": [
            {
                "label": "Active Sessions",
                    "data": [item["active_sessions"] for item in app_data],
                    "borderColor": "rgb(75, 192, 192)",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "tension": 0.1
            },
                {
                "label": "Requests / Minute",
                    "data": [item["requests_per_minute"] for item in app_data],
                    "borderColor": "rgb(153, 102, 255)",
                    "backgroundColor": "rgba(153, 102, 255, 0.2)",
                    "tension": 0.1
            }
        ]
    }

    return chart_data

@router.post("/api / test - block - confirmation")


async def test_block_confirmation(current_user: User = Depends(require_admin_edit_access)):
    """Test endpoint for block confirmation dialog."""
    return {
        "confirmation_required": True,
            "message": "Are you sure you want to block this user?",
            "admin": current_user.email,
            "permissions": {
            "can_temp_block": current_user.can_block_users(),
                "can_perm_block": current_user.can_permanent_block()
        }
    }

# WebSocket endpoint for real - time updates (if needed)
@router.get("/api / live - status")


async def get_live_status(current_user: User = Depends(require_admin_access)):
    """Get live system status for real - time updates."""

    current_metrics={
        "system": system_monitor.get_system_metrics(),
            "application": system_monitor.get_application_metrics(),
            "security": system_monitor.get_security_metrics()
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
            "server_online": True,
            "database_connected": True,
            "metrics": {
            k: v.__dict__ if v else None
            for k, v in current_metrics.items()
        }
    }
