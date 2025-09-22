"""
Klerno Labs - Enterprise Configuration System
Controls enterprise features for TOP 0.1% application status
"""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class EnterpriseFeatures:
    """Enterprise feature configuration."""

    # Core Enterprise Features
    monitoring_enabled: bool = True
    security_hardening: bool = True
    analytics_enabled: bool = True
    financial_compliance: bool = True
    ai_processing: bool = True
    guardian_protection: bool = True

    # Performance Features
    advanced_caching: bool = True
    load_balancing: bool = True
    auto_scaling: bool = True

    # Security Features
    threat_intelligence: bool = True
    behavioral_analysis: bool = True
    automated_blocking: bool = True
    zero_day_protection: bool = True

    # Monitoring Features
    real_time_metrics: bool = True
    alerting_system: bool = True
    performance_dashboards: bool = True
    health_monitoring: bool = True

    # Analytics Features
    business_intelligence: bool = True
    predictive_analytics: bool = True
    real_time_reporting: bool = True
    custom_dashboards: bool = True


@dataclass
class EnterpriseConfig:
    """Main enterprise configuration."""

    # Mode Selection
    enterprise_mode: bool = True
    debug_mode: bool = False
    environment: str = "production"  # development, staging, production

    # Features
    features: EnterpriseFeatures | None = None

    # Database Configuration
    monitoring_db: str = "data/monitoring.db"
    analytics_db: str = "data/analytics.db"
    security_db: str = "data/security.db"

    # Performance Settings
    max_workers: int = 4
    cache_size: int = 1000
    rate_limit: int = 1000  # requests per minute

    # Security Settings
    encryption_key: str | None = None
    jwt_secret: str | None = None
    session_timeout: int = 3600  # seconds

    def __post_init__(self):
        """Initialize default features if not provided."""
        if self.features is None:
            self.features = EnterpriseFeatures()

    @classmethod
    def from_env(cls) -> 'EnterpriseConfig':
        """Create configuration from environment variables."""
        config = cls()

        # Load from environment
        config.enterprise_mode = os.getenv("ENTERPRISE_MODE", "true").lower() == "true"
        config.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        config.environment = os.getenv("ENVIRONMENT", "production")

        # Security
        config.encryption_key = os.getenv("ENCRYPTION_KEY")
        config.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-here")

        return config

    def get_feature_summary(self) -> dict[str, Any]:
        """Get summary of enabled enterprise features."""
        if self.features is None:
            self.features = EnterpriseFeatures()

        return {
            "enterprise_mode": self.enterprise_mode,
            "environment": self.environment,
            "total_features": sum([
                self.features.monitoring_enabled,
                self.features.security_hardening,
                self.features.analytics_enabled,
                self.features.financial_compliance,
                self.features.ai_processing,
                self.features.guardian_protection,
                self.features.advanced_caching,
                self.features.load_balancing,
                self.features.threat_intelligence,
                self.features.behavioral_analysis,
                self.features.real_time_metrics,
                self.features.business_intelligence,
            ]),
            "features": {
                "monitoring": self.features.monitoring_enabled,
                "security": self.features.security_hardening,
                "analytics": self.features.analytics_enabled,
                "compliance": self.features.financial_compliance,
                "ai_processing": self.features.ai_processing,
                "guardian": self.features.guardian_protection,
                "threat_intelligence": self.features.threat_intelligence,
                "behavioral_analysis": self.features.behavioral_analysis,
                "real_time_metrics": self.features.real_time_metrics,
                "business_intelligence": self.features.business_intelligence,
            }
        }

    def validate(self) -> list[str]:
        """Validate configuration and return any issues."""
        if self.features is None:
            self.features = EnterpriseFeatures()

        issues = []

        if self.enterprise_mode and not self.encryption_key:
            issues.append("Encryption key required for enterprise mode")

        if self.features.financial_compliance and self.environment == "production":
            if not self.monitoring_db:
                issues.append("Monitoring database required for financial compliance")

        if self.features.security_hardening and not self.jwt_secret:
            issues.append("JWT secret required for security hardening")

        return issues


# Global configuration instance
enterprise_config = EnterpriseConfig.from_env()


def get_config() -> EnterpriseConfig:
    """Get the global enterprise configuration."""
    return enterprise_config


def is_enterprise_enabled() -> bool:
    """Check if enterprise mode is enabled."""
    return enterprise_config.enterprise_mode


def get_enabled_features() -> list[str]:
    """Get list of enabled enterprise features."""
    features = []
    config = enterprise_config.features

    # Ensure features is initialized
    if config is None:
        config = EnterpriseFeatures()
        enterprise_config.features = config

    if config.monitoring_enabled:
        features.append("Enterprise Monitoring")
    if config.security_hardening:
        features.append("Advanced Security")
    if config.analytics_enabled:
        features.append("Business Analytics")
    if config.financial_compliance:
        features.append("ISO20022 Compliance")
    if config.ai_processing:
        features.append("AI Processing")
    if config.guardian_protection:
        features.append("Guardian Protection")
    if config.threat_intelligence:
        features.append("Threat Intelligence")
    if config.behavioral_analysis:
        features.append("Behavioral Analysis")
    if config.real_time_metrics:
        features.append("Real-time Metrics")
    if config.business_intelligence:
        features.append("Business Intelligence")

    return features
