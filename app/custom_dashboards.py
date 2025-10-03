"""
Custom Dashboards Module for Klerno Labs.

Provides customizable dashboard functionality for Professional and Enterprise tiers.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .subscriptions import get_db_connection


class WidgetType(str, Enum):
    """Types of dashboard widgets."""

    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    ALERT_LIST = "alert_list"
    TRANSACTION_FLOW = "transaction_flow"
    RISK_HEATMAP = "risk_heatmap"
    COMPLIANCE_STATUS = "compliance_status"
    GEOGRAPHIC_MAP = "geographic_map"


class ChartType(str, Enum):
    """Chart visualization types."""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"


@dataclass
class DashboardWidget:
    """Dashboard widget configuration."""

    id: str
    type: WidgetType
    title: str
    config: dict[str, Any]
    position: dict[str, int]  # x, y, width, height
    data_source: str
    refresh_interval: int = 30  # seconds
    filters: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert widget to dictionary."""
        return asdict(self)


@dataclass
class Dashboard:
    """Dashboard configuration."""

    id: str
    user_id: str
    name: str
    description: str
    layout: dict[str, Any]
    widgets: list[DashboardWidget]
    is_public: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert dashboard to dictionary."""
        result = asdict(self)
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()
        return result


class DashboardManager:
    """Manages custom dashboards for users."""

    def __init__(self) -> None:
        self._init_dashboard_tables()

    def _init_dashboard_tables(self) -> None:
        """Initialize dashboard database tables."""
        conn = get_db_connection()
        cursor = conn.cursor()

        # Dashboards table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS dashboards (
            id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                layout TEXT NOT NULL,
                is_public INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
        )
        """
        )

        # Dashboard widgets table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS dashboard_widgets (
            id TEXT PRIMARY KEY,
                dashboard_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                config TEXT NOT NULL,
                position TEXT NOT NULL,
                data_source TEXT NOT NULL,
                refresh_interval INTEGER DEFAULT 30,
                filters TEXT,
                FOREIGN KEY (dashboard_id) REFERENCES dashboards (id) ON DELETE CASCADE
        )
        """
        )

        conn.commit()
        conn.close()

    def create_dashboard(
        self,
        user_id: str,
        name: str,
        description: str = "",
        layout: dict[str, Any] | None = None,
    ) -> Dashboard:
        """Create a new dashboard for user."""
        dashboard_id = str(uuid.uuid4())
        now = datetime.utcnow()

        if layout is None:
            layout = {"columns": 12, "rows": 8, "gap": 16, "responsive": True}

        dashboard = Dashboard(
            id=dashboard_id,
            user_id=user_id,
            name=name,
            description=description,
            layout=layout,
            widgets=[],
            created_at=now,
            updated_at=now,
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO dashboards (id, user_id, name, description, layout, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dashboard_id,
                user_id,
                name,
                description,
                json.dumps(layout),
                now.isoformat(),
                now.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return dashboard

    def get_user_dashboards(self, user_id: str) -> list[Dashboard]:
        """Get all dashboards for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, name, description, layout, is_public, created_at, updated_at
            FROM dashboards
            WHERE user_id=?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        )

        rows = cursor.fetchall()
        dashboards = []

        for row in rows:
            dashboard = Dashboard(
                id=row[0],
                user_id=row[1],
                name=row[2],
                description=row[3],
                layout=json.loads(row[4]),
                widgets=[],  # Load widgets separately
                is_public=bool(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                updated_at=datetime.fromisoformat(row[7]),
            )

            # Load widgets for this dashboard
            dashboard.widgets = self._get_dashboard_widgets(dashboard.id)
            dashboards.append(dashboard)

        conn.close()
        return dashboards

    def get_dashboard(
        self, dashboard_id: str, user_id: str | None = None
    ) -> Dashboard | None:
        """Get specific dashboard by ID."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT id, user_id, name, description, layout, is_public, created_at, updated_at
        FROM dashboards
        WHERE id=?
        """
        params = [dashboard_id]

        if user_id:
            query += " AND (user_id=? OR is_public=1)"
            params.append(user_id)

        cursor.execute(query, params)
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        dashboard = Dashboard(
            id=row[0],
            user_id=row[1],
            name=row[2],
            description=row[3],
            layout=json.loads(row[4]),
            widgets=self._get_dashboard_widgets(dashboard_id),
            is_public=bool(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
        )

        conn.close()
        return dashboard

    def add_widget(
        self,
        dashboard_id: str,
        widget_type: WidgetType,
        title: str,
        config: dict[str, Any],
        position: dict[str, int],
        data_source: str,
        refresh_interval: int = 30,
        filters: dict[str, Any] | None = None,
    ) -> DashboardWidget:
        """Add widget to dashboard."""
        widget_id = str(uuid.uuid4())

        widget = DashboardWidget(
            id=widget_id,
            type=widget_type,
            title=title,
            config=config,
            position=position,
            data_source=data_source,
            refresh_interval=refresh_interval,
            filters=filters or {},
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO dashboard_widgets
            (id, dashboard_id, type, title, config, position,
             data_source, refresh_interval, filters)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                widget_id,
                dashboard_id,
                widget_type.value,
                title,
                json.dumps(config),
                json.dumps(position),
                data_source,
                refresh_interval,
                json.dumps(filters or {}),
            ),
        )

        # Update dashboard timestamp
        cursor.execute(
            "UPDATE dashboards SET updated_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), dashboard_id),
        )

        conn.commit()
        conn.close()

        return widget

    def _get_dashboard_widgets(self, dashboard_id: str) -> list[DashboardWidget]:
        """Get all widgets for a dashboard."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, type, title, config, position, data_source, refresh_interval, filters
            FROM dashboard_widgets
            WHERE dashboard_id=?
            ORDER BY id
            """,
            (dashboard_id,),
        )

        rows = cursor.fetchall()
        widgets = []

        for row in rows:
            widget = DashboardWidget(
                id=row[0],
                type=WidgetType(row[1]),
                title=row[2],
                config=json.loads(row[3]),
                position=json.loads(row[4]),
                data_source=row[5],
                refresh_interval=row[6],
                filters=json.loads(row[7]) if row[7] else {},
            )
            widgets.append(widget)

        conn.close()
        return widgets

    def create_default_dashboard(self, user_id: str) -> Dashboard:
        """Create default dashboard with common widgets."""
        dashboard = self.create_dashboard(
            user_id=user_id,
            name="Default Dashboard",
            description="Your main analytics dashboard",
        )

        # Add default widgets

        # Risk Overview Chart
        self.add_widget(
            dashboard_id=dashboard.id,
            widget_type=WidgetType.CHART,
            title="Risk Score Trends",
            config={
                "chart_type": ChartType.LINE.value,
                "x_axis": "timestamp",
                "y_axis": "risk_score",
                "color_scheme": "risk",
            },
            position={"x": 0, "y": 0, "width": 6, "height": 3},
            data_source="risk_analytics",
        )

        # Transaction Volume
        self.add_widget(
            dashboard_id=dashboard.id,
            widget_type=WidgetType.METRIC,
            title="Daily Transaction Volume",
            config={
                "metric_type": "count",
                "format": "number",
                "comparison": "previous_day",
            },
            position={"x": 6, "y": 0, "width": 3, "height": 2},
            data_source="transaction_stats",
        )

        # Alert Summary
        self.add_widget(
            dashboard_id=dashboard.id,
            widget_type=WidgetType.ALERT_LIST,
            title="Recent Alerts",
            config={"limit": 10, "severity_filter": ["high", "critical"]},
            position={"x": 9, "y": 0, "width": 3, "height": 4},
            data_source="alerts",
        )

        # Geographic Risk Map
        self.add_widget(
            dashboard_id=dashboard.id,
            widget_type=WidgetType.GEOGRAPHIC_MAP,
            title="Geographic Risk Distribution",
            config={"map_type": "choropleth", "risk_metric": "average_risk_score"},
            position={"x": 0, "y": 3, "width": 6, "height": 4},
            data_source="geographic_analytics",
        )

        # Compliance Status
        self.add_widget(
            dashboard_id=dashboard.id,
            widget_type=WidgetType.COMPLIANCE_STATUS,
            title="Compliance Overview",
            config={"status_indicators": ["aml", "kyc", "sanctions"]},
            position={"x": 6, "y": 2, "width": 3, "height": 2},
            data_source="compliance_status",
        )

        return dashboard

    def get_widget_data(self, widget: DashboardWidget, user_id: str) -> dict[str, Any]:
        """Get data for a specific widget."""
        # This would integrate with your actual data sources
        # For now, return mock data based on widget type

        if widget.type == WidgetType.CHART:
            return self._get_chart_data(widget, user_id)
        elif widget.type == WidgetType.METRIC:
            return self._get_metric_data(widget, user_id)
        elif widget.type == WidgetType.ALERT_LIST:
            return self._get_alert_data(widget, user_id)
        elif widget.type == WidgetType.TABLE:
            return self._get_table_data(widget, user_id)
        else:
            return {"data": [], "timestamp": datetime.utcnow().isoformat()}

    def _get_chart_data(self, widget: DashboardWidget, user_id: str) -> dict[str, Any]:
        """Get chart data."""
        # Mock implementation - replace with real data queries
        import random
        from datetime import datetime, timedelta

        data = []
        now = datetime.utcnow()

        for i in range(30):  # Last 30 days
            date = now - timedelta(days=i)
            data.append(
                {
                    "timestamp": date.isoformat(),
                    "risk_score": random.uniform(0.1, 0.9),
                    # nosec: B311 - non-crypto randomness for demo/test data
                    "transaction_count": random.randint(10, 100),
                }
            )

        return {"data": data, "timestamp": now.isoformat(), "widget_id": widget.id}

    def _get_metric_data(self, widget: DashboardWidget, user_id: str) -> dict[str, Any]:
        """Get metric data."""
        import random

        return {
            "current_value": random.randint(100, 1000),
            "previous_value": random.randint(80, 950),
            "change_percentage": random.uniform(-10, 15),
            "timestamp": datetime.utcnow().isoformat(),
            "widget_id": widget.id,
        }

    def _get_alert_data(self, widget: DashboardWidget, user_id: str) -> dict[str, Any]:
        """Get alert data."""
        # Mock alerts data
        alerts = [
            {
                "id": "alert_1",
                "severity": "high",
                "title": "High Risk Transaction",
                "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            },
            {
                "id": "alert_2",
                "severity": "medium",
                "title": "Unusual Transaction Pattern",
                "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            },
        ]

        return {
            "alerts": alerts,
            "total_count": len(alerts),
            "timestamp": datetime.utcnow().isoformat(),
            "widget_id": widget.id,
        }

    def _get_table_data(self, widget: DashboardWidget, user_id: str) -> dict[str, Any]:
        """Get table data."""
        import random

        rows = []
        for i in range(10):
            rows.append(
                {
                    "transaction_id": f"tx_{i + 1}",
                    "amount": random.uniform(100, 10000),
                    "risk_score": random.uniform(0.1, 0.9),
                    "status": random.choice(["approved", "flagged", "pending"]),
                }
            )

        return {
            "rows": rows,
            "columns": ["transaction_id", "amount", "risk_score", "status"],
            "timestamp": datetime.utcnow().isoformat(),
            "widget_id": widget.id,
        }


# Global dashboard manager instance
dashboard_manager = DashboardManager()


def get_user_dashboards(user_id: str) -> list[Dashboard]:
    """Get all dashboards for a user."""
    return dashboard_manager.get_user_dashboards(user_id)


def create_dashboard(user_id: str, name: str, description: str = "") -> Dashboard:
    """Create new dashboard for user."""
    return dashboard_manager.create_dashboard(user_id, name, description)


def get_dashboard(dashboard_id: str, user_id: str | None = None) -> Dashboard | None:
    """Get specific dashboard."""
    return dashboard_manager.get_dashboard(dashboard_id, user_id)


def create_default_dashboard(user_id: str) -> Dashboard:
    """Create default dashboard for new user."""
    return dashboard_manager.create_default_dashboard(user_id)


def is_dashboard_feature_available(user_tier: str) -> bool:
    """Check if user has access to custom dashboards."""
    return user_tier.lower() in ["professional", "enterprise"]
