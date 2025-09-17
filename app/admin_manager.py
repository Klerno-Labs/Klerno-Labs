# app/admin_manager.py
"""
Comprehensive admin management system with role-based access control,
user blocking/restriction, logging, and notification features.
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging
from pathlib import Path

from .models import User, AdminAction, UserRole, AccountStatus, ActionType, BlockUserRequest
from .security_session import hash_pw as get_password_hash, verify_pw as verify_password

logger = logging.getLogger(__name__)

class AdminManager:
    """Comprehensive admin management system."""
    
    def __init__(self, db_path: str = "data/klerno.db"):
        self.db_path = db_path
        self.notification_email = "klerno@outlook.com"  # Configurable
        self.init_database()
        self.init_owner_account()
    
    def init_database(self):
        """Initialize database tables for enhanced user management."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Enhanced users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users_enhanced (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    blocked_until TIMESTAMP,
                    blocked_reason TEXT,
                    blocked_by TEXT,
                    is_premium BOOLEAN DEFAULT 0
                )
            """)
            
            # Admin actions log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_email TEXT NOT NULL,
                    target_email TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    additional_data TEXT
                )
            """)
            
            # System settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def init_owner_account(self):
        """Initialize the owner account with specified credentials."""
        owner_email = "klerno@outlook.com"
        owner_password = "Labs2025"
        
        try:
            # Check if owner already exists
            if self.get_user_by_email(owner_email):
                logger.info("Owner account already exists")
                return
            
            # Create owner account
            password_hash = get_password_hash(owner_password)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users_enhanced 
                    (email, password_hash, role, status, is_premium)
                    VALUES (?, ?, ?, ?, ?)
                """, (owner_email, password_hash, UserRole.OWNER, AccountStatus.ACTIVE, True))
                conn.commit()
            
            logger.info(f"Owner account created: {owner_email}")
            
        except Exception as e:
            logger.error(f"Failed to create owner account: {e}")
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, email, password_hash, role, status, created_at, 
                           last_login, blocked_until, blocked_reason, blocked_by, is_premium
                    FROM users_enhanced WHERE email = ?
                """, (email,))
                
                row = cursor.fetchone()
                if row:
                    return User(
                        id=row[0],
                        email=row[1],
                        password_hash=row[2],
                        role=UserRole(row[3]),
                        status=AccountStatus(row[4]),
                        created_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(timezone.utc),
                        last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                        blocked_until=datetime.fromisoformat(row[7]) if row[7] else None,
                        blocked_reason=row[8],
                        blocked_by=row[9],
                        is_premium=bool(row[10])
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def create_user(self, email: str, password: str, role: UserRole = UserRole.USER, 
                   admin_email: str = None, is_premium: bool = False) -> Dict[str, Any]:
        """Create a new user with role assignment."""
        try:
            # Check if user already exists
            if self.get_user_by_email(email):
                return {"success": False, "message": "User already exists"}
            
            # Hash password
            password_hash = get_password_hash(password)
            
            # Create user
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users_enhanced 
                    (email, password_hash, role, status, is_premium)
                    VALUES (?, ?, ?, ?, ?)
                """, (email, password_hash, role.value, AccountStatus.ACTIVE.value, is_premium))
                
                user_id = cursor.lastrowid
                conn.commit()
            
            # Log admin action if admin created the user
            if admin_email and role in [UserRole.ADMIN, UserRole.MANAGER]:
                self.log_admin_action(
                    admin_email=admin_email,
                    target_email=email,
                    action=ActionType.CREATE_ADMIN,
                    reason=f"Created {role.value} account"
                )
            
            return {
                "success": True, 
                "message": f"User created successfully with role: {role.value}",
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {"success": False, "message": f"Error creating user: {str(e)}"}
    
    def update_user_role(self, admin_email: str, target_email: str, 
                        new_role: UserRole) -> Dict[str, Any]:
        """Update user role with permission checking."""
        try:
            admin = self.get_user_by_email(admin_email)
            target = self.get_user_by_email(target_email)
            
            if not admin or not target:
                return {"success": False, "message": "User not found"}
            
            # Check permissions
            if not admin.can_edit_role(new_role):
                return {"success": False, "message": "Insufficient permissions"}
            
            # Update role
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users_enhanced SET role = ? WHERE email = ?
                """, (new_role.value, target_email))
                conn.commit()
            
            # Log action
            self.log_admin_action(
                admin_email=admin_email,
                target_email=target_email,
                action=ActionType.ROLE_CHANGE,
                reason=f"Role changed to {new_role.value}"
            )
            
            return {"success": True, "message": f"Role updated to {new_role.value}"}
            
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return {"success": False, "message": f"Error updating role: {str(e)}"}
    
    def block_user(self, admin_email: str, request: BlockUserRequest) -> Dict[str, Any]:
        """Block user with reason tracking and confirmation."""
        try:
            admin = self.get_user_by_email(admin_email)
            target = self.get_user_by_email(request.target_email)
            
            if not admin or not target:
                return {"success": False, "message": "User not found"}
            
            # Check permissions
            if not admin.can_block_users():
                return {"success": False, "message": "Insufficient permissions to block users"}
            
            # Check if trying to permanently block (only owner can do this)
            if request.duration_hours is None and not admin.can_permanent_block():
                return {"success": False, "message": "Only owners can permanently block users"}
            
            # Prevent blocking owner
            if target.is_owner():
                return {"success": False, "message": "Cannot block owner account"}
            
            # Determine block type and duration
            if request.duration_hours is None:
                # Permanent block
                status = AccountStatus.PERMANENTLY_BLOCKED
                blocked_until = None
                action_type = ActionType.BLOCK_PERMANENT
            else:
                # Temporary block
                status = AccountStatus.TEMPORARILY_BLOCKED
                blocked_until = datetime.now(timezone.utc) + timedelta(hours=request.duration_hours)
                action_type = ActionType.BLOCK_TEMPORARY
                
                # Admin can only do 24-hour blocks
                if admin.role == UserRole.ADMIN and request.duration_hours > 24:
                    return {"success": False, "message": "Admins can only block for maximum 24 hours"}
            
            # Update user status
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users_enhanced 
                    SET status = ?, blocked_until = ?, blocked_reason = ?, blocked_by = ?
                    WHERE email = ?
                """, (status.value, blocked_until.isoformat() if blocked_until else None, 
                     request.reason, admin_email, request.target_email))
                conn.commit()
            
            # Log action
            action_id = self.log_admin_action(
                admin_email=admin_email,
                target_email=request.target_email,
                action=action_type,
                reason=request.reason,
                additional_data=json.dumps({
                    "duration_hours": request.duration_hours,
                    "blocked_until": blocked_until.isoformat() if blocked_until else None
                })
            )
            
            # Send notification email
            self.send_block_notification(admin_email, request, action_type)
            
            block_type = "permanently" if request.duration_hours is None else f"for {request.duration_hours} hours"
            return {
                "success": True, 
                "message": f"User blocked {block_type}",
                "action_id": action_id
            }
            
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            return {"success": False, "message": f"Error blocking user: {str(e)}"}
    
    def unblock_user(self, admin_email: str, target_email: str, reason: str) -> Dict[str, Any]:
        """Unblock a user."""
        try:
            admin = self.get_user_by_email(admin_email)
            target = self.get_user_by_email(target_email)
            
            if not admin or not target:
                return {"success": False, "message": "User not found"}
            
            # Check permissions
            if not admin.can_block_users():
                return {"success": False, "message": "Insufficient permissions"}
            
            # Update user status
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users_enhanced 
                    SET status = ?, blocked_until = NULL, blocked_reason = NULL, blocked_by = NULL
                    WHERE email = ?
                """, (AccountStatus.ACTIVE.value, target_email))
                conn.commit()
            
            # Log action
            action_id = self.log_admin_action(
                admin_email=admin_email,
                target_email=target_email,
                action=ActionType.UNBLOCK,
                reason=reason
            )
            
            return {"success": True, "message": "User unblocked successfully", "action_id": action_id}
            
        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            return {"success": False, "message": f"Error unblocking user: {str(e)}"}
    
    def log_admin_action(self, admin_email: str, target_email: str, 
                        action: ActionType, reason: str, additional_data: str = None) -> int:
        """Log admin action to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO admin_actions 
                    (admin_email, target_email, action, reason, additional_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (admin_email, target_email, action.value, reason, additional_data))
                
                action_id = cursor.lastrowid
                conn.commit()
                return action_id
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
            return 0
    
    def get_admin_actions(self, start_date: datetime = None, 
                         end_date: datetime = None) -> List[AdminAction]:
        """Get admin actions within date range."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM admin_actions"
                params = []
                
                if start_date or end_date:
                    query += " WHERE"
                    conditions = []
                    
                    if start_date:
                        conditions.append(" timestamp >= ?")
                        params.append(start_date.isoformat())
                    
                    if end_date:
                        conditions.append(" timestamp <= ?")
                        params.append(end_date.isoformat())
                    
                    query += " AND".join(conditions)
                
                query += " ORDER BY timestamp DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                actions = []
                for row in rows:
                    actions.append(AdminAction(
                        id=row[0],
                        admin_email=row[1],
                        target_email=row[2],
                        action=ActionType(row[3]),
                        reason=row[4],
                        timestamp=datetime.fromisoformat(row[5]),
                        additional_data=row[6]
                    ))
                
                return actions
        except Exception as e:
            logger.error(f"Error getting admin actions: {e}")
            return []
    
    def send_block_notification(self, admin_email: str, request: BlockUserRequest, 
                               action_type: ActionType):
        """Send email notification for blocking actions."""
        try:
            # Create email content
            subject = f"User Account Action: {action_type.value}"
            
            body = f"""
            Admin Action Notification
            
            Admin: {admin_email}
            Target User: {request.target_email}
            Action: {action_type.value}
            Reason: {request.reason}
            Duration: {'Permanent' if request.duration_hours is None else f'{request.duration_hours} hours'}
            Timestamp: {datetime.now(timezone.utc).isoformat()}
            
            This is an automated notification from Klerno Labs Admin System.
            """
            
            # Note: Email sending would require SMTP configuration
            # For now, we'll log the notification
            logger.info(f"Email notification prepared for {self.notification_email}: {subject}")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def get_monthly_block_report(self, year: int, month: int) -> Dict[str, Any]:
        """Generate monthly report of blocking actions."""
        try:
            start_date = datetime(year, month, 1, tzinfo=timezone.utc)
            if month == 12:
                end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
            
            actions = self.get_admin_actions(start_date, end_date)
            
            # Filter blocking actions
            blocking_actions = [a for a in actions if a.action in [
                ActionType.BLOCK_TEMPORARY, ActionType.BLOCK_PERMANENT
            ]]
            
            # Generate statistics
            report = {
                "period": f"{year}-{month:02d}",
                "total_blocks": len(blocking_actions),
                "temporary_blocks": len([a for a in blocking_actions if a.action == ActionType.BLOCK_TEMPORARY]),
                "permanent_blocks": len([a for a in blocking_actions if a.action == ActionType.BLOCK_PERMANENT]),
                "actions": [
                    {
                        "admin": a.admin_email,
                        "target": a.target_email,
                        "action": a.action.value,
                        "reason": a.reason,
                        "timestamp": a.timestamp.isoformat()
                    }
                    for a in blocking_actions
                ]
            }
            
            return report
        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")
            return {"error": str(e)}
    
    def get_all_users(self, admin_email: str) -> List[Dict[str, Any]]:
        """Get all users for admin management."""
        try:
            admin = self.get_user_by_email(admin_email)
            if not admin or not admin.is_manager_or_higher():
                return []
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT email, role, status, created_at, last_login, 
                           blocked_until, blocked_reason, blocked_by, is_premium
                    FROM users_enhanced
                    ORDER BY created_at DESC
                """)
                
                rows = cursor.fetchall()
                users = []
                
                for row in rows:
                    users.append({
                        "email": row[0],
                        "role": row[1],
                        "status": row[2],
                        "created_at": row[3],
                        "last_login": row[4],
                        "blocked_until": row[5],
                        "blocked_reason": row[6],
                        "blocked_by": row[7],
                        "is_premium": bool(row[8])
                    })
                
                return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def update_notification_email(self, new_email: str, admin_email: str) -> Dict[str, Any]:
        """Update the notification email address."""
        try:
            admin = self.get_user_by_email(admin_email)
            if not admin or not admin.is_owner():
                return {"success": False, "message": "Only owner can update notification email"}
            
            self.notification_email = new_email
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value)
                    VALUES ('notification_email', ?)
                """, (new_email,))
                conn.commit()
            
            return {"success": True, "message": f"Notification email updated to {new_email}"}
        except Exception as e:
            logger.error(f"Error updating notification email: {e}")
            return {"success": False, "message": f"Error updating email: {str(e)}"}