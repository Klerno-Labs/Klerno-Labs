"""
Enterprise Features Module for Klerno Labs.

Provides enterprise - grade features including white - label solution, SLA guarantees,
    on - premise deployment capabilities, custom AI models, and dedicated support.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from .subscriptions import get_db_connection


class WhiteLabelConfig(str, Enum):
    """White - label configuration options."""

    BASIC = "basic"  # Logo and colors only
    ADVANCED = "advanced"  # Full branding customization
    COMPLETE = "complete"  # Complete custom domain and branding


class SLATier(str, Enum):
    """SLA tier levels."""

    STANDARD = "standard"  # 99.5% uptime
    PREMIUM = "premium"  # 99.9% uptime
    ENTERPRISE = "enterprise"  # 99.95% uptime


class DeploymentType(str, Enum):
    """Deployment types."""

    CLOUD = "cloud"  # Cloud - hosted
    ON_PREMISE = "on_premise"  # On - premise deployment
    HYBRID = "hybrid"  # Hybrid deployment


@dataclass
class WhiteLabelSettings:
    """White - label branding settings."""

    company_name: str
    logo_url: str | None = None
    primary_color: str = "  #1f2937"
    secondary_color: str = "  #3b82f6"
    accent_color: str = "  #10b981"
    custom_domain: str | None = None
    favicon_url: str | None = None
    footer_text: str | None = None
    support_email: str = "support@company.com"
    support_phone: str | None = None
    terms_url: str | None = None
    privacy_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SLAMetrics:
    """SLA performance metrics."""

    uptime_percentage: float
    response_time_ms: float
    availability_hours: float
    planned_downtime_hours: float
    unplanned_downtime_hours: float
    incident_count: int
    mttr_minutes: float  # Mean Time To Resolution
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class CustomAIModel:
    """Custom AI model configuration."""

    id: str
    name: str
    description: str
    model_type: str  # "risk_scoring", "fraud_detection", "compliance"
    training_data_path: str
    model_file_path: str
    accuracy: float
    last_trained: datetime
    version: str
    is_active: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["last_trained"] = self.last_trained.isoformat()
        return result


@dataclass
class SupportTicket:
    """Dedicated support ticket."""

    id: str
    user_id: str
    priority: str  # "low", "medium", "high", "critical"
    category: str
    subject: str
    description: str
    status: str = "open"  # "open", "in_progress", "resolved", "closed"
    assigned_to: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
        if self.resolved_at:
            result["resolved_at"] = self.resolved_at.isoformat()
        return result


class EnterpriseManager:
    """Manages enterprise - grade features and services."""

    def __init__(self):
        self._init_enterprise_tables()

    def _init_enterprise_tables(self):
        """Initialize enterprise feature tables."""
        conn = get_db_connection()
        cursor = conn.cursor()

        # White - label configurations
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS white_label_configs (
            user_id TEXT PRIMARY KEY,
                config_level TEXT NOT NULL,
                company_name TEXT NOT NULL,
                logo_url TEXT,
                primary_color TEXT DEFAULT '  #1f2937',
                secondary_color TEXT DEFAULT '  #3b82f6',
                accent_color TEXT DEFAULT '  #10b981',
                custom_domain TEXT,
                favicon_url TEXT,
                footer_text TEXT,
                support_email TEXT,
                support_phone TEXT,
                terms_url TEXT,
                privacy_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
        )
        """
        )

        # SLA agreements and metrics
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS sla_agreements (
            user_id TEXT PRIMARY KEY,
                tier TEXT NOT NULL,
                uptime_guarantee REAL NOT NULL,
                response_time_guarantee INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                created_at TEXT NOT NULL
        )
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS sla_metrics (
            id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                uptime_percentage REAL NOT NULL,
                response_time_ms REAL NOT NULL,
                availability_hours REAL NOT NULL,
                planned_downtime_hours REAL DEFAULT 0,
                unplanned_downtime_hours REAL DEFAULT 0,
                incident_count INTEGER DEFAULT 0,
                mttr_minutes REAL DEFAULT 0,
                created_at TEXT NOT NULL
        )
        """
        )

        # Custom AI models
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS custom_ai_models (
            id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                model_type TEXT NOT NULL,
                training_data_path TEXT NOT NULL,
                model_file_path TEXT NOT NULL,
                accuracy REAL NOT NULL,
                last_trained TEXT NOT NULL,
                version TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
        )
        """
        )

        # Support tickets
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                priority TEXT NOT NULL,
                category TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                assigned_to TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT
        )
        """
        )

        conn.commit()
        conn.close()

    def setup_white_label(
        self, user_id: str, config_level: WhiteLabelConfig, settings: WhiteLabelSettings
    ) -> bool:
        """Set up white - label configuration for enterprise client."""

        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now(UTC)

        cursor.execute(
            """
            INSERT OR REPLACE INTO white_label_configs
            (user_id, config_level, company_name, logo_url, primary_color,
             secondary_color, accent_color, custom_domain, favicon_url,
                 footer_text, support_email, support_phone, terms_url,
                 privacy_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                config_level.value,
                settings.company_name,
                settings.logo_url,
                settings.primary_color,
                settings.secondary_color,
                settings.accent_color,
                settings.custom_domain,
                settings.favicon_url,
                settings.footer_text,
                settings.support_email,
                settings.support_phone,
                settings.terms_url,
                settings.privacy_url,
                now.isoformat(),
                now.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return True

    def get_white_label_config(self, user_id: str) -> WhiteLabelSettings | None:
        """Get white - label configuration for user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT company_name, logo_url, primary_color, secondary_color,
                   accent_color, custom_domain, favicon_url, footer_text,
                       support_email, support_phone, terms_url, privacy_url
            FROM white_label_configs
            WHERE user_id=?
            """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return WhiteLabelSettings(
            company_name=row[0],
            logo_url=row[1],
            primary_color=row[2],
            secondary_color=row[3],
            accent_color=row[4],
            custom_domain=row[5],
            favicon_url=row[6],
            footer_text=row[7],
            support_email=row[8],
            support_phone=row[9],
            terms_url=row[10],
            privacy_url=row[11],
        )

    def create_sla_agreement(
        self, user_id: str, tier: SLATier, duration_months: int = 12
    ) -> bool:
        """Create SLA agreement for enterprise client."""

        # SLA guarantees by tier
        guarantees = {
            SLATier.STANDARD: {"uptime": 99.5, "response_time": 1000},
            SLATier.PREMIUM: {"uptime": 99.9, "response_time": 500},
            SLATier.ENTERPRISE: {"uptime": 99.95, "response_time": 250},
        }

        guarantee = guarantees[tier]

        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now(UTC)
        end_date = now + timedelta(days=duration_months * 30)

        cursor.execute(
            """
            INSERT OR REPLACE INTO sla_agreements
            (user_id, tier, uptime_guarantee, response_time_guarantee,
             start_date, end_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                tier.value,
                guarantee["uptime"],
                guarantee["response_time"],
                now.isoformat(),
                end_date.isoformat(),
                now.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return True

    def record_sla_metrics(
        self,
        user_id: str,
        period_start: datetime,
        period_end: datetime,
        metrics: SLAMetrics,
    ) -> bool:
        """Record SLA performance metrics."""

        conn = get_db_connection()
        cursor = conn.cursor()

        metric_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO sla_metrics
            (id, user_id, period_start, period_end, uptime_percentage,
             response_time_ms, availability_hours, planned_downtime_hours,
                 unplanned_downtime_hours, incident_count, mttr_minutes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric_id,
                user_id,
                period_start.isoformat(),
                period_end.isoformat(),
                metrics.uptime_percentage,
                metrics.response_time_ms,
                metrics.availability_hours,
                metrics.planned_downtime_hours,
                metrics.unplanned_downtime_hours,
                metrics.incident_count,
                metrics.mttr_minutes,
                datetime.now(UTC).isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return True

    def get_sla_metrics(self, user_id: str, days: int = 30) -> list[SLAMetrics]:
        """Get SLA metrics for user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        cursor.execute(
            """
            SELECT uptime_percentage, response_time_ms, availability_hours,
                   planned_downtime_hours, unplanned_downtime_hours,
                       incident_count, mttr_minutes, created_at
            FROM sla_metrics
            WHERE user_id=? AND created_at >= ?
            ORDER BY created_at DESC
            """,
            (user_id, cutoff_date.isoformat()),
        )

        rows = cursor.fetchall()
        metrics: list[SLAMetrics] = []

        for row in rows:
            metric = SLAMetrics(
                uptime_percentage=row[0],
                response_time_ms=row[1],
                availability_hours=row[2],
                planned_downtime_hours=row[3],
                unplanned_downtime_hours=row[4],
                incident_count=row[5],
                mttr_minutes=row[6],
                timestamp=datetime.fromisoformat(row[7]),
            )
            metrics.append(metric)

        conn.close()
        return metrics

    def deploy_custom_ai_model(
        self,
        user_id: str,
        name: str,
        description: str,
        model_type: str,
        training_data: bytes,
        model_data: bytes,
    ) -> CustomAIModel:
        """Deploy custom AI model for enterprise client."""

        model_id = str(uuid.uuid4())

        # Save training data and model files
        models_dir = f"data / custom_models/{user_id}"
        os.makedirs(models_dir, exist_ok=True)

        training_data_path = os.path.join(models_dir, f"{model_id}_training.pkl")
        model_file_path = os.path.join(models_dir, f"{model_id}_model.pkl")

        with open(training_data_path, "wb") as f:
            f.write(training_data)

        with open(model_file_path, "wb") as f:
            f.write(model_data)

        # Create model record
        now = datetime.now(UTC)
        model = CustomAIModel(
            id=model_id,
            name=name,
            description=description,
            model_type=model_type,
            training_data_path=training_data_path,
            model_file_path=model_file_path,
            accuracy=0.95,  # Mock accuracy - would be calculated during training
            last_trained=now,
            version="1.0.0",
            is_active=False,
        )

        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO custom_ai_models
            (id, user_id, name, description, model_type, training_data_path,
             model_file_path, accuracy, last_trained, version, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model_id,
                user_id,
                name,
                description,
                model_type,
                training_data_path,
                model_file_path,
                model.accuracy,
                now.isoformat(),
                model.version,
                0,
                now.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return model

    def get_custom_ai_models(self, user_id: str) -> list[CustomAIModel]:
        """Get custom AI models for user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, description, model_type, training_data_path,
                   model_file_path, accuracy, last_trained, version, is_active
            FROM custom_ai_models
            WHERE user_id=?
            ORDER BY last_trained DESC
            """,
            (user_id,),
        )

        rows = cursor.fetchall()
        models: list[CustomAIModel] = []

        for row in rows:
            model = CustomAIModel(
                id=row[0],
                name=row[1],
                description=row[2],
                model_type=row[3],
                training_data_path=row[4],
                model_file_path=row[5],
                accuracy=row[6],
                last_trained=datetime.fromisoformat(row[7]),
                version=row[8],
                is_active=bool(row[9]),
            )
            models.append(model)

        conn.close()
        return models

    def create_support_ticket(
        self, user_id: str, priority: str, category: str, subject: str, description: str
    ) -> SupportTicket:
        """Create dedicated support ticket."""

        ticket_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        ticket = SupportTicket(
            id=ticket_id,
            user_id=user_id,
            priority=priority,
            category=category,
            subject=subject,
            description=description,
            created_at=now,
            updated_at=now,
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO support_tickets
            (id, user_id, priority, category, subject, description,
             status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                user_id,
                priority,
                category,
                subject,
                description,
                "open",
                now.isoformat(),
                now.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return ticket

    def get_support_tickets(
        self, user_id: str, status: str | None = None
    ) -> list[SupportTicket]:
        """Get support tickets for user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT id, user_id, priority, category, subject, description,
               status, assigned_to, created_at, updated_at, resolved_at
        FROM support_tickets
        WHERE user_id=?
        """
        params = [user_id]

        if status:
            query += " AND status=?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        tickets: list[SupportTicket] = []

        for row in rows:
            ticket = SupportTicket(
                id=row[0],
                user_id=row[1],
                priority=row[2],
                category=row[3],
                subject=row[4],
                description=row[5],
                status=row[6],
                assigned_to=row[7],
                created_at=datetime.fromisoformat(row[8]),
                updated_at=datetime.fromisoformat(row[9]),
                resolved_at=datetime.fromisoformat(row[10]) if row[10] else None,
            )
            tickets.append(ticket)

        conn.close()
        return tickets

    def generate_on_premise_deployment_package(self, user_id: str) -> dict[str, Any]:
        """Generate on - premise deployment package."""

        # Generate deployment configuration
        config: dict[str, Any] = {
            "version": "1.0.0",
            "deployment_type": "on_premise",
            "user_id": user_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "components": {
                "api_server": {
                    "docker_image": "klerno / api:latest",
                    "ports": ["8000:8000"],
                    "environment": {
                        "DATABASE_URL": "postgresql://user:pass@localhost / klerno",
                        "REDIS_URL": "redis://localhost:6379",
                        "JWT_SECRET": "REPLACE_WITH_SECURE_SECRET",
                        "ADMIN_EMAIL": "admin@company.com",
                    },
                },
                "database": {
                    "docker_image": "postgres:14",
                    "volumes": ["./data / postgres:/var / lib / postgresql / data"],
                    "environment": {
                        "POSTGRES_DB": "klerno",
                        "POSTGRES_USER": "klerno_user",
                        "POSTGRES_PASSWORD": "REPLACE_WITH_SECURE_PASSWORD",
                    },
                },
                "redis": {
                    "docker_image": "redis:7",
                    "volumes": ["./data / redis:/data"],
                },
                "nginx": {
                    "docker_image": "nginx:alpine",
                    "ports": ["80:80", "443:443"],
                    "volumes": ["./nginx.conf:/etc / nginx / nginx.conf"],
                },
            },
            "requirements": {
                "minimum_ram": "8GB",
                "minimum_storage": "100GB",
                "minimum_cpu_cores": 4,
                "operating_system": "Linux (Ubuntu 20.04+ recommended)",
                "docker_version": "20.10+",
                "docker_compose_version": "2.0+",
            },
            "installation_steps": [
                "1. Ensure Docker and Docker Compose are installed",
                "2. Create directory: mkdir klerno - enterprise && cd klerno - enterprise",
                "3. Save deployment files to this directory",
                "4. Update environment variables in .env file",
                "5. Run: docker - compose up -d",
                "6. Access application at http://localhost",
                "7. Configure SSL certificates for production use",
            ],
        }

        return config


# Global enterprise manager
enterprise_manager = EnterpriseManager()


def setup_white_label(
    user_id: str, config_level: WhiteLabelConfig, settings: WhiteLabelSettings
) -> bool:
    """Set up white - label configuration."""
    return enterprise_manager.setup_white_label(user_id, config_level, settings)


def get_white_label_config(user_id: str) -> WhiteLabelSettings | None:
    """Get white - label configuration."""
    return enterprise_manager.get_white_label_config(user_id)


def create_sla_agreement(
    user_id: str, tier: SLATier, duration_months: int = 12
) -> bool:
    """Create SLA agreement."""
    return enterprise_manager.create_sla_agreement(user_id, tier, duration_months)


def get_sla_metrics(user_id: str, days: int = 30) -> list[SLAMetrics]:
    """Get SLA metrics."""
    return enterprise_manager.get_sla_metrics(user_id, days)


def deploy_custom_ai_model(
    user_id: str,
    name: str,
    description: str,
    model_type: str,
    training_data: bytes,
    model_data: bytes,
) -> CustomAIModel:
    """Deploy custom AI model."""
    return enterprise_manager.deploy_custom_ai_model(
        user_id, name, description, model_type, training_data, model_data
    )


def create_support_ticket(
    user_id: str, priority: str, category: str, subject: str, description: str
) -> SupportTicket:
    """Create support ticket."""
    return enterprise_manager.create_support_ticket(
        user_id, priority, category, subject, description
    )


def get_support_tickets(user_id: str, status: str | None = None) -> list[SupportTicket]:
    """Get support tickets."""
    return enterprise_manager.get_support_tickets(user_id, status)


def generate_on_premise_deployment_package(user_id: str) -> dict[str, Any]:
    """Generate on - premise deployment package."""
    return enterprise_manager.generate_on_premise_deployment_package(user_id)


def is_enterprise_feature_available(user_tier: str) -> bool:
    """Check if user has access to enterprise features."""
    return user_tier.lower() == "enterprise"
