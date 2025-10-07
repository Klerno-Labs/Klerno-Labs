#!/usr/bin/env python3
"""Database validation and optimization analysis."""

import json
import sqlite3
from pathlib import Path
from typing import Any


def analyze_database_structure() -> dict[str, Any]:
    """Analyze database structure and identify issues."""
    db_path = "./data/klerno.db"
    report: dict[str, Any] = {
        "database_path": db_path,
        "issues": [],
        "tables": {},
        "indexes": {},
        "recommendations": [],
    }

    if not Path(db_path).exists():
        report["issues"].append("Database file does not exist")
        return report

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        report["tables"]["list"] = tables

        # Analyze each table
        for table in tables:
            if table.startswith("sqlite_"):
                continue

            # Get table schema
            cursor.execute(f"PRAGMA table_info({table})")
            schema = cursor.fetchall()
            report["tables"][table] = {"columns": len(schema), "schema": schema}

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            report["tables"][table]["row_count"] = row_count

            # Check for indexes
            cursor.execute(f"PRAGMA index_list({table})")
            indexes = cursor.fetchall()
            report["indexes"][table] = indexes

        # Identify specific issues

        # 1. Table naming inconsistency
        if "txs" in tables and "transactions" not in tables:
            report["issues"].append(
                "Table naming inconsistency: 'txs' exists but Alembic expects 'transactions'",
            )
            report["recommendations"].append(
                "Consider renaming 'txs' to 'transactions' or updating Alembic migrations",
            )

        # 2. Missing indexes for performance
        if "txs" in report["indexes"] and len(report["indexes"]["txs"]) < 2:
            report["issues"].append("txs table lacks performance indexes")
            report["recommendations"].append(
                "Add indexes on txs(timestamp), txs(chain), txs(from_addr), txs(to_addr)",
            )

        # 3. Check for users table completeness
        if "users" in tables:
            users_schema = report["tables"]["users"]["schema"]
            required_columns = ["email", "password_hash", "role", "subscription_active"]
            existing_columns = [col[1] for col in users_schema]

            missing = [col for col in required_columns if col not in existing_columns]
            if missing:
                report["issues"].append(
                    f"Users table missing required columns: {missing}",
                )

        # 4. Check for orphaned or unused tables
        expected_tables = ["users", "txs", "user_settings"]
        unexpected = [
            t
            for t in tables
            if t not in expected_tables and not t.startswith("sqlite_")
        ]
        if unexpected:
            report["issues"].append(f"Unexpected tables found: {unexpected}")
            report["recommendations"].append(
                "Review if these tables are needed or can be removed",
            )

        # 5. Database size and optimization
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        db_size_mb = (page_size * page_count) / (1024 * 1024)

        report["database_size_mb"] = round(db_size_mb, 2)
        if db_size_mb > 100:
            report["recommendations"].append(
                "Database is large - consider archiving old data or implementing data retention policies",
            )

        # 6. Check for proper foreign key constraints
        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()
        if fk_violations:
            report["issues"].append(
                f"Foreign key violations found: {len(fk_violations)} issues",
            )
            report["recommendations"].append("Fix foreign key constraint violations")

        conn.close()

    except Exception as e:
        report["issues"].append(f"Database analysis error: {e!s}")

    return report


def generate_optimization_queries() -> list[str]:
    """Generate SQL queries for database optimization."""
    return [
        # Add missing indexes for performance
        "CREATE INDEX IF NOT EXISTS idx_txs_timestamp ON txs(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_txs_chain ON txs(chain);",
        "CREATE INDEX IF NOT EXISTS idx_txs_from_addr ON txs(from_addr);",
        "CREATE INDEX IF NOT EXISTS idx_txs_to_addr ON txs(to_addr);",
        "CREATE INDEX IF NOT EXISTS idx_txs_category ON txs(category);",
        "CREATE INDEX IF NOT EXISTS idx_txs_risk_score ON txs(risk_score);",
        # User table indexes
        "CREATE INDEX IF NOT EXISTS idx_users_oauth_provider ON users(oauth_provider);",
        "CREATE INDEX IF NOT EXISTS idx_users_oauth_id ON users(oauth_id);",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);",
        # User settings table index
        "CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);",
        # Database maintenance
        "VACUUM;",
        "ANALYZE;",
    ]


def check_migration_consistency() -> dict[str, Any]:
    """Check Alembic migration consistency."""
    report: dict[str, Any] = {
        "alembic_status": "unknown",
        "migration_issues": [],
        "recommendations": [],
    }

    try:
        # Check if alembic_version table exists
        conn = sqlite3.connect("./data/klerno.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'",
        )
        alembic_table = cursor.fetchone()

        if not alembic_table:
            report["alembic_status"] = "not_initialized"
            report["migration_issues"].append("Alembic version table does not exist")
            report["recommendations"].append(
                "Run 'alembic stamp head' to initialize migration tracking",
            )
        else:
            cursor.execute("SELECT version_num FROM alembic_version")
            current_version = cursor.fetchone()
            if current_version:
                report["alembic_status"] = f"current_version_{current_version[0]}"
            else:
                report["alembic_status"] = "no_version_recorded"

        conn.close()

    except Exception as e:
        report["migration_issues"].append(f"Migration check error: {e!s}")

    return report


def main():
    """Run complete database validation."""
    structure_report = analyze_database_structure()

    migration_report = check_migration_consistency()

    optimization_queries = generate_optimization_queries()

    # Combine reports
    full_report = {
        "analysis_timestamp": "2025-10-04T21:00:00Z",
        "structure_analysis": structure_report,
        "migration_analysis": migration_report,
        "optimization_queries": optimization_queries,
        "summary": {
            "total_issues": len(structure_report["issues"])
            + len(migration_report["migration_issues"]),
            "total_recommendations": len(structure_report["recommendations"])
            + len(migration_report["recommendations"]),
            "database_health": (
                "needs_attention"
                if structure_report["issues"] or migration_report["migration_issues"]
                else "good"
            ),
        },
    }

    # Save report
    with Path("database_validation_report.json").open("w") as f:
        json.dump(full_report, f, indent=2)

    # Print summary

    if structure_report["issues"]:
        for _i, _issue in enumerate(structure_report["issues"], 1):
            pass

    if migration_report["migration_issues"]:
        for _i, _issue in enumerate(migration_report["migration_issues"], 1):
            pass

    if full_report["summary"]["total_recommendations"] > 0:
        pass

    return full_report


if __name__ == "__main__":
    main()
