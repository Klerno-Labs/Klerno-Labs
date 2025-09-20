"""
Enterprise Configuration & Settings

Comprehensive configuration for all enterprise - grade features including
ISO20022 compliance, advanced security, performance optimization,
    monitoring, testing, and resilience systems.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ISO20022Config:
    """ISO20022 compliance configuration."""

    enabled: bool = True
    supported_message_types: list[str] = field(
        default_factory=lambda: ["pain.001", "pain.002", "camt.053", "camt.054"]
    )
    validation_strict: bool = True
    xml_encoding: str = "UTF - 8"
    namespace_validation: bool = True
    iban_validation: bool = True
    bic_validation: bool = True
    real_time_processing: bool = True


@dataclass
class SecurityConfig:
    """Advanced security configuration."""

    enabled: bool = True
    behavioral_analysis: bool = True
    threat_intelligence: bool = True
    zero_day_protection: bool = True
    apt_detection: bool = True
    cryptographic_standards: str = "FIPS - 140 - 2"
    session_timeout: int = 3600  # seconds
    max_login_attempts: int = 3
    rate_limiting: bool = True
    requests_per_minute: int = 100
    advanced_firewall: bool = True


@dataclass
class PerformanceConfig:
    """Performance optimization configuration."""

    enabled: bool = True
    caching_enabled: bool = True
    cache_ttl: int = 3600  # seconds
    connection_pooling: bool = True
    max_connections: int = 100
    load_balancing: bool = True
    horizontal_scaling: bool = True
    performance_monitoring: bool = True
    target_response_time: int = 500  # milliseconds
    target_throughput: int = 1000  # requests per second


@dataclass
class MonitoringConfig:
    """Enterprise monitoring configuration."""

    enabled: bool = True
    real_time_metrics: bool = True
    alerting_enabled: bool = True
    dashboard_enabled: bool = True
    log_level: str = "INFO"
    metrics_retention: int = 30  # days
    health_check_interval: int = 60  # seconds
    quality_scoring: bool = True
    observability_enabled: bool = True


@dataclass
class ResilienceConfig:
    """Resilience system configuration."""

    enabled: bool = True
    circuit_breakers: bool = True
    retry_mechanisms: bool = True
    graceful_degradation: bool = True
    auto_failover: bool = True
    self_healing: bool = True
    disaster_recovery: bool = True
    backup_frequency: int = 24  # hours
    recovery_time_objective: int = 300  # seconds (5 minutes)


@dataclass
class TestingConfig:
    """Comprehensive testing configuration."""

    enabled: bool = True
    unit_tests: bool = True
    integration_tests: bool = True
    e2e_tests: bool = True
    performance_tests: bool = True
    security_tests: bool = True
    coverage_threshold: float = 99.9  # percentage
    continuous_testing: bool = True
    automated_quality_gates: bool = True


@dataclass
class QualityConfig:
    """Top 0.01% quality standards configuration."""

    enabled: bool = True
    target_overall_score: float = 99.0
    target_performance_score: float = 95.0
    target_security_score: float = 99.0
    target_reliability_score: float = 99.99
    target_compliance_score: float = 100.0
    target_test_coverage: float = 99.9
    target_code_quality: float = 90.0


@dataclass
class EnterpriseConfig:
    """Main enterprise configuration."""

    iso20022: ISO20022Config = field(default_factory=ISO20022Config)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)

    # Global settings
    enterprise_mode: bool = True
    debug_mode: bool = False
    environment: str = "production"

    @classmethod
    def from_env(cls) -> EnterpriseConfig:
        """Create configuration from environment variables."""
        config = cls()

        # Override from environment variables
        config.enterprise_mode = os.getenv("ENTERPRISE_MODE", "true").lower() == "true"
        config.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        config.environment = os.getenv("APP_ENV", "production")

        # ISO20022 settings
        if os.getenv("ISO20022_ENABLED"):
            config.iso20022.enabled = os.getenv("ISO20022_ENABLED").lower() == "true"

        # Security settings
        if os.getenv("SECURITY_BEHAVIORAL_ANALYSIS"):
            config.security.behavioral_analysis = (
                os.getenv("SECURITY_BEHAVIORAL_ANALYSIS").lower() == "true"
            )

        # Performance settings
        if os.getenv("PERFORMANCE_CACHING"):
            config.performance.caching_enabled = (
                os.getenv("PERFORMANCE_CACHING").lower() == "true"
            )

        return config

    def validate(self) -> list[str]:
        """Validate configuration and return any issues."""
        issues = []

        # Validate quality thresholds
        if self.quality.target_overall_score < 95.0:
            issues.append(
                "Overall quality score target is below enterprise standards (95%)"
            )

        if self.quality.target_security_score < 99.0:
            issues.append("Security score target is below enterprise standards (99%)")

        if self.quality.target_test_coverage < 95.0:
            issues.append("Test coverage target is below enterprise standards (95%)")

        # Validate performance targets
        if self.performance.target_response_time > 1000:
            issues.append("Response time target exceeds enterprise standards (1000ms)")

        # Validate security settings
        if not self.security.behavioral_analysis and self.security.enabled:
            issues.append(
                "Behavioral analysis should be enabled for enterprise security"
            )

        return issues

    def get_feature_summary(self) -> dict[str, Any]:
        """Get summary of enabled enterprise features."""
        return {
            "enterprise_mode": self.enterprise_mode,
            "environment": self.environment,
            "features": {
                "iso20022_compliance": self.iso20022.enabled,
                "advanced_security": self.security.enabled,
                "performance_optimization": self.performance.enabled,
                "enterprise_monitoring": self.monitoring.enabled,
                "resilience_system": self.resilience.enabled,
                "comprehensive_testing": self.testing.enabled,
                "quality_assurance": self.quality.enabled,
            },
            "quality_targets": {
                "overall_score": self.quality.target_overall_score,
                "security_score": self.quality.target_security_score,
                "performance_score": self.quality.target_performance_score,
                "reliability_score": self.quality.target_reliability_score,
                "test_coverage": self.quality.target_test_coverage,
            },
        }


# Global enterprise configuration instance
enterprise_config = EnterpriseConfig.from_env()

# Validation on import
config_issues = enterprise_config.validate()
if config_issues:
    import logging

    logger = logging.getLogger(__name__)
    logger.warning("Enterprise configuration issues found:")
    for issue in config_issues:
        logger.warning(f"  - {issue}")

# Export configuration
__all__ = [
    "EnterpriseConfig",
    "ISO20022Config",
    "SecurityConfig",
    "PerformanceConfig",
    "MonitoringConfig",
    "ResilienceConfig",
    "TestingConfig",
    "QualityConfig",
    "enterprise_config",
]
