"""
Compliance Reporting Module for Klerno Labs.

Provides comprehensive compliance reporting for Professional and Enterprise tiers.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import io
import csv

from .subscriptions import get_db_connection


class ReportType(str, Enum):
    """Types of compliance reports."""
    AML_SUMMARY="aml_summary"
    KYC_STATUS="kyc_status"
    SANCTIONS_SCREENING="sanctions_screening"
    TRANSACTION_MONITORING="transaction_monitoring"
    RISK_ASSESSMENT="risk_assessment"
    SUSPICIOUS_ACTIVITY="suspicious_activity"
    REGULATORY_FILING="regulatory_filing"


class ReportFormat(str, Enum):
    """Report output formats."""
    PDF="pdf"
    CSV="csv"
    JSON="json"
    EXCEL="excel"


class ComplianceStatus(str, Enum):
    """Compliance status levels."""
    COMPLIANT="compliant"
    NON_COMPLIANT="non_compliant"
    UNDER_REVIEW="under_review"
    REQUIRES_ACTION="requires_action"

@dataclass


class ComplianceReport:
    """Compliance report structure."""
    id: str
    user_id: str
    report_type: ReportType
    title: str
    description: str
    date_range: Dict[str, str]  # start_date, end_date
    parameters: Dict[str, Any]
    status: str="pending"
    file_path: Optional[str] = None
    created_at: datetime=None
    completed_at: Optional[datetime] = None


    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        result=asdict(self)
        if self.created_at:
            result['created_at'] = self.created_at.isoformat()
        if self.completed_at:
            result['completed_at'] = self.completed_at.isoformat()
        return result

@dataclass


class ComplianceMetrics:
    """Compliance metrics summary."""
    total_transactions: int
    flagged_transactions: int
    high_risk_transactions: int
    compliance_rate: float
    aml_alerts: int
    kyc_pending: int
    sanctions_hits: int
    risk_distribution: Dict[str, int]
    timestamp: datetime


class ComplianceReportingEngine:
    """Generates compliance reports for regulatory requirements."""


    def __init__(self):
        self._init_compliance_tables()


    def _init_compliance_tables(self):
        """Initialize compliance reporting tables."""
        conn=get_db_connection()
        cursor=conn.cursor()

        # Compliance reports table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS compliance_reports (
            id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                report_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                date_range TEXT NOT NULL,
                parameters TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                file_path TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
        )
        ''')

        # Compliance events table for tracking
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS compliance_events (
            id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                transaction_id TEXT,
                details TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                resolved_at TEXT
        )
        ''')

        conn.commit()
        conn.close()


    def generate_aml_report(
        self,
            user_id: str,
            start_date: datetime,
            end_date: datetime,
            output_format: ReportFormat=ReportFormat.PDF
    ) -> ComplianceReport:
        """Generate AML (Anti - Money Laundering) compliance report."""

        report_id=str(uuid.uuid4())

        report=ComplianceReport(
            id=report_id,
                user_id=user_id,
                report_type=ReportType.AML_SUMMARY,
                title=f"AML Compliance Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                description="Anti - Money Laundering compliance summary and risk assessment",
                date_range={
                "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
            },
                parameters={
                "output_format": output_format.value,
                    "include_transactions": True,
                    "include_risk_scores": True,
                    "include_alerts": True
            },
                created_at=datetime.now(timezone.utc)
        )

        # Save report to database
        self._save_report(report)

        # Generate report content
        report_data=self._generate_aml_data(user_id, start_date, end_date)

        # Create report file
        file_path=self._create_report_file(report, report_data, output_format)

        # Update report with file path and completion
        report.file_path=file_path
        report.status="completed"
        report.completed_at=datetime.now(timezone.utc)

        self._update_report(report)

        return report


    def generate_transaction_monitoring_report(
        self,
            user_id: str,
            start_date: datetime,
            end_date: datetime,
            risk_threshold: float=0.5
    ) -> ComplianceReport:
        """Generate transaction monitoring report."""

        report_id=str(uuid.uuid4())

        report=ComplianceReport(
            id=report_id,
                user_id=user_id,
                report_type=ReportType.TRANSACTION_MONITORING,
                title=f"Transaction Monitoring Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                description="Comprehensive transaction monitoring and risk analysis",
                date_range={
                "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
            },
                parameters={
                "risk_threshold": risk_threshold,
                    "include_low_risk": False,
                    "group_by_type": True
            },
                created_at=datetime.now(timezone.utc)
        )

        self._save_report(report)

        # Generate monitoring data
        monitoring_data=self._generate_monitoring_data(user_id, start_date, end_date, risk_threshold)

        # Create CSV report
        file_path=self._create_monitoring_csv(report, monitoring_data)

        report.file_path=file_path
        report.status="completed"
        report.completed_at=datetime.now(timezone.utc)

        self._update_report(report)

        return report


    def generate_suspicious_activity_report(
        self,
            user_id: str,
            start_date: datetime,
            end_date: datetime
    ) -> ComplianceReport:
        """Generate Suspicious Activity Report (SAR)."""

        report_id=str(uuid.uuid4())

        report=ComplianceReport(
            id=report_id,
                user_id=user_id,
                report_type=ReportType.SUSPICIOUS_ACTIVITY,
                title=f"Suspicious Activity Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                description="Detailed analysis of suspicious transactions and patterns",
                date_range={
                "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
            },
                parameters={
                "min_risk_score": 0.7,
                    "include_patterns": True,
                    "include_recommendations": True
            },
                created_at=datetime.now(timezone.utc)
        )

        self._save_report(report)

        # Generate SAR data
        sar_data=self._generate_sar_data(user_id, start_date, end_date)

        # Create comprehensive report
        file_path=self._create_sar_report(report, sar_data)

        report.file_path=file_path
        report.status="completed"
        report.completed_at=datetime.now(timezone.utc)

        self._update_report(report)

        return report


    def get_compliance_metrics(
        self,
            user_id: str,
            start_date: datetime,
            end_date: datetime
    ) -> ComplianceMetrics:
        """Get compliance metrics for a date range."""

        # Mock implementation - replace with real data queries
        import random

        total_transactions=random.randint(1000, 10000)
        flagged_transactions=random.randint(10, 100)
        high_risk_transactions=random.randint(5, 50)

        return ComplianceMetrics(
            total_transactions=total_transactions,
                flagged_transactions=flagged_transactions,
                high_risk_transactions=high_risk_transactions,
                compliance_rate=((total_transactions - flagged_transactions) / total_transactions) * 100,
                aml_alerts=random.randint(0, 20),
                kyc_pending=random.randint(0, 10),
                sanctions_hits=random.randint(0, 5),
                risk_distribution={
                "low": random.randint(800, 900),
                    "medium": random.randint(80, 150),
                    "high": random.randint(10, 50),
                    "critical": random.randint(0, 10)
            },
                timestamp=datetime.now(timezone.utc)
        )


    def get_user_reports(self, user_id: str, limit: int = 50) -> List[ComplianceReport]:
        """Get compliance reports for a user."""
        conn=get_db_connection()
        cursor=conn.cursor()

        cursor.execute(
            '''
            SELECT id, user_id, report_type, title, description, date_range,
                   parameters, status, file_path, created_at, completed_at
            FROM compliance_reports
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ?
            ''',
                (user_id, limit)
        )

        rows=cursor.fetchall()
        reports=[]

        for row in rows:
            report=ComplianceReport(
                id=row[0],
                    user_id=row[1],
                    report_type=ReportType(row[2]),
                    title=row[3],
                    description=row[4],
                    date_range=json.loads(row[5]),
                    parameters=json.loads(row[6]),
                    status=row[7],
                    file_path=row[8],
                    created_at=datetime.fromisoformat(row[9]),
                    completed_at=datetime.fromisoformat(row[10]) if row[10] else None
            )
            reports.append(report)

        conn.close()
        return reports


    def _save_report(self, report: ComplianceReport):
        """Save report to database."""
        conn=get_db_connection()
        cursor=conn.cursor()

        cursor.execute(
            '''
            INSERT INTO compliance_reports
            (id, user_id, report_type, title, description, date_range, parameters, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
                (
                report.id,
                    report.user_id,
                    report.report_type.value,
                    report.title,
                    report.description,
                    json.dumps(report.date_range),
                    json.dumps(report.parameters),
                    report.status,
                    report.created_at.isoformat()
            )
        )

        conn.commit()
        conn.close()


    def _update_report(self, report: ComplianceReport):
        """Update report in database."""
        conn=get_db_connection()
        cursor=conn.cursor()

        cursor.execute(
            '''
            UPDATE compliance_reports
            SET status=?, file_path=?, completed_at=?
            WHERE id=?
            ''',
                (
                report.status,
                    report.file_path,
                    report.completed_at.isoformat() if report.completed_at else None,
                    report.id
            )
        )

        conn.commit()
        conn.close()


    def _generate_aml_data(
        self,
            user_id: str,
            start_date: datetime,
            end_date: datetime
    ) -> Dict[str, Any]:
        """Generate AML report data."""

        # Mock AML data - replace with real queries
        import random

        transactions=[]
        for i in range(100):
            tx_date=start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            transactions.append({
                "transaction_id": f"tx_{i + 1}",
                    "date": tx_date.isoformat(),
                    "amount": random.uniform(100, 50000),
                    "risk_score": random.uniform(0.1, 0.9),
                    "from_address": f"addr_{random.randint(1000, 9999)}",
                    "to_address": f"addr_{random.randint(1000, 9999)}",
                    "flags": random.choice([[], ["high_amount"], ["unusual_pattern"], ["high_amount", "unusual_pattern"]])
            })

        return {
            "summary": {
                "total_transactions": len(transactions),
                    "total_amount": sum(tx["amount"] for tx in transactions),
                    "high_risk_count": len([tx for tx in transactions if tx["risk_score"] > 0.7]),
                    "flagged_count": len([tx for tx in transactions if tx["flags"]])
            },
                "transactions": transactions,
                "risk_analysis": {
                "avg_risk_score": sum(tx["risk_score"] for tx in transactions) / len(transactions),
                    "risk_distribution": {
                    "low": len([tx for tx in transactions if tx["risk_score"] < 0.3]),
                        "medium": len([tx for tx in transactions if 0.3 <= tx["risk_score"] < 0.7]),
                        "high": len([tx for tx in transactions if tx["risk_score"] >= 0.7])
                }
            }
        }


    def _generate_monitoring_data(
        self,
            user_id: str,
            start_date: datetime,
            end_date: datetime,
            risk_threshold: float
    ) -> List[Dict[str, Any]]:
        """Generate transaction monitoring data."""

        # Mock monitoring data
        import random

        data=[]
        for i in range(50):
            risk_score=random.uniform(risk_threshold, 1.0)
            data.append({
                "transaction_id": f"mon_tx_{i + 1}",
                    "timestamp": (start_date + timedelta(days=random.randint(0, (end_date - start_date).days))).isoformat(),
                    "amount": random.uniform(1000, 100000),
                    "risk_score": risk_score,
                    "risk_level": "HIGH" if risk_score > 0.7 else "MEDIUM",
                    "alert_type": random.choice(["velocity", "amount", "pattern", "geographic"]),
                    "status": random.choice(["pending", "reviewed", "cleared", "flagged"])
            })

        return data


    def _generate_sar_data(
        self,
            user_id: str,
            start_date: datetime,
            end_date: datetime
    ) -> Dict[str, Any]:
        """Generate Suspicious Activity Report data."""

        # Mock SAR data
        import random

        suspicious_transactions=[]
        for i in range(10):
            suspicious_transactions.append({
                "transaction_id": f"sar_tx_{i + 1}",
                    "date": (start_date + timedelta(days=random.randint(0, (end_date - start_date).days))).isoformat(),
                    "amount": random.uniform(10000, 500000),
                    "risk_score": random.uniform(0.8, 1.0),
                    "suspicious_indicators": random.choice([
                    ["structuring", "unusual_amount"],
                        ["rapid_movement", "high_risk_jurisdiction"],
                        ["smurfing", "round_amounts"],
                        ["velocity", "pattern_matching"]
                ]),
                    "recommendation": random.choice([
                    "File SAR",
                        "Enhanced monitoring",
                        "Account restriction",
                        "Investigation required"
                ])
            })

        return {
            "period": {
                "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
            },
                "summary": {
                "total_suspicious": len(suspicious_transactions),
                    "avg_risk_score": 0.85,
                    "recommendations_summary": {
                    "file_sar": 3,
                        "enhanced_monitoring": 4,
                        "investigation": 2,
                        "restriction": 1
                }
            },
                "transactions": suspicious_transactions
        }


    def _create_report_file(
        self,
            report: ComplianceReport,
            data: Dict[str, Any],
            output_format: ReportFormat
    ) -> str:
        """Create report file in specified format."""

        import os

        # Create reports directory if it doesn't exist
        reports_dir="data / compliance_reports"
        os.makedirs(reports_dir, exist_ok=True)

        filename=f"{report.id}_{report.report_type.value}.{output_format.value}"
        file_path=os.path.join(reports_dir, filename)

        if output_format == ReportFormat.JSON:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        elif output_format == ReportFormat.CSV:
            # Convert to CSV format
            with open(file_path, 'w', newline='') as f:
                if "transactions" in data:
                    writer=csv.DictWriter(f, fieldnames=data["transactions"][0].keys())
                    writer.writeheader()
                    writer.writerows(data["transactions"])

        # For PDF and Excel, you would implement proper generation
        # For now, create a placeholder JSON file
        else:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        return file_path


    def _create_monitoring_csv(self, report: ComplianceReport, data: List[Dict[str, Any]]) -> str:
        """Create CSV file for monitoring report."""
        import os

        reports_dir="data / compliance_reports"
        os.makedirs(reports_dir, exist_ok=True)

        filename=f"{report.id}_monitoring.csv"
        file_path=os.path.join(reports_dir, filename)

        with open(file_path, 'w', newline='') as f:
            if data:
                writer=csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        return file_path


    def _create_sar_report(self, report: ComplianceReport, data: Dict[str, Any]) -> str:
        """Create SAR report file."""
        import os

        reports_dir="data / compliance_reports"
        os.makedirs(reports_dir, exist_ok=True)

        filename=f"{report.id}_sar.json"
        file_path=os.path.join(reports_dir, filename)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return file_path

# Global compliance reporting engine
compliance_engine=ComplianceReportingEngine()


def generate_aml_report(user_id: str, start_date: datetime, end_date: datetime) -> ComplianceReport:
    """Generate AML compliance report."""
    return compliance_engine.generate_aml_report(user_id, start_date, end_date)


def generate_transaction_monitoring_report(user_id: str, start_date: datetime, end_date: datetime) -> ComplianceReport:
    """Generate transaction monitoring report."""
    return compliance_engine.generate_transaction_monitoring_report(user_id, start_date, end_date)


def get_compliance_metrics(user_id: str, start_date: datetime, end_date: datetime) -> ComplianceMetrics:
    """Get compliance metrics."""
    return compliance_engine.get_compliance_metrics(user_id, start_date, end_date)


def get_user_reports(user_id: str) -> List[ComplianceReport]:
    """Get user's compliance reports."""
    return compliance_engine.get_user_reports(user_id)


def is_compliance_feature_available(user_tier: str) -> bool:
    """Check if user has access to compliance reporting."""
    return user_tier.lower() in ['professional', 'enterprise']
