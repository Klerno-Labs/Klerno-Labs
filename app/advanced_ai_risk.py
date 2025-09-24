"""
Advanced AI Risk Scoring Module for Klerno Labs.

Implements sophisticated AI - powered risk analysis for Professional tier features.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np

try:
    # Avoid importing sklearn at module-import time; import inside initializer
    IsolationForest = None
    RandomForestClassifier = None
    StandardScaler = None
except Exception:
    IsolationForest = None
    RandomForestClassifier = None
    StandardScaler = None

logger = logging.getLogger(__name__)


@dataclass
class RiskFactors:
    """Risk factors for advanced scoring."""

    transaction_frequency: float = 0.0
    amount_anomaly: float = 0.0
    time_pattern: float = 0.0
    address_reputation: float = 0.0
    geographical_risk: float = 0.0
    behavioral_pattern: float = 0.0
    network_analysis: float = 0.0


@dataclass
class AdvancedRiskScore:
    """Advanced risk scoring result."""

    overall_score: float
    confidence: float
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    factors: RiskFactors
    recommendations: list[str]
    ai_insights: list[str]
    timestamp: datetime


class AdvancedAIRiskEngine:
    """AI - powered advanced risk scoring engine."""

    def __init__(self):
        self.isolation_forest = None
        self.risk_classifier = None
        self.scaler = None
        self.is_trained = False
        self._initialize_models()

    def _initialize_models(self):
        """Initialize AI models with synthetic training data."""
        # Import sklearn here to avoid heavy import at module import-time
        try:
            from sklearn.ensemble import IsolationForest, RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
        except Exception as e:
            raise RuntimeError("sklearn is required to initialize AI models") from e
        # Generate synthetic training data for demonstration
        # In production, this would use real historical data
        X_train, y_train = self._generate_training_data()

        # Create and train models
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.risk_classifier = RandomForestClassifier(n_estimators=100, random_state=42)

        X_scaled = self.scaler.fit_transform(X_train)
        self.isolation_forest.fit(X_scaled)
        self.risk_classifier.fit(X_scaled, y_train)
        self.is_trained = True

        logger.info("Advanced AI risk models initialized and trained")

    def _generate_training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data."""
        np.random.seed(42)
        n_samples = 10000

        # Generate features: amount, frequency, time_hour, geo_risk, etc.
        features = []
        labels = []

        for _ in range(n_samples):
            # Transaction amount (log - scaled)
            amount = np.random.lognormal(mean=3, sigma=2)

            # Frequency (transactions per day)
            frequency = np.random.exponential(scale=5)

            # Time of day (0 - 23)
            hour = np.random.randint(0, 24)

            # Geographical risk (0 - 1)
            geo_risk = np.random.beta(2, 8)

            # Address age (days)
            addr_age = np.random.exponential(scale=180)

            # Network centrality (0 - 1)
            centrality = np.random.beta(3, 7)

            feature_vector = [amount, frequency, hour, geo_risk, addr_age, centrality]

            # Simple risk labeling logic
            risk_score = (
                (amount > 10000) * 0.3
                + (frequency > 20) * 0.2
                + (hour < 6 or hour > 22) * 0.1
                + geo_risk * 0.2
                + (addr_age < 7) * 0.15
                + centrality * 0.05
            )

            if risk_score > 0.7:
                label = 3  # HIGH
            elif risk_score > 0.4:
                label = 2  # MEDIUM
            else:
                label = 1  # LOW

            features.append(feature_vector)
            labels.append(label)

        return np.array(features), np.array(labels)

    def analyze_transaction(
        self,
        transaction_data: dict[str, Any],
        user_history: list[dict[str, Any]] | None = None,
    ) -> AdvancedRiskScore:
        """Perform advanced AI risk analysis on a transaction."""

        if (
            not self.is_trained
            or self.scaler is None
            or self.isolation_forest is None
            or self.risk_classifier is None
        ):
            raise RuntimeError("AI models not trained or not initialized")

        # Extract features from transaction
        features = self._extract_features(transaction_data, user_history or [])

        # Scale features
        if self.scaler is None:
            raise RuntimeError("Scaler not initialized")
        features_scaled = self.scaler.transform([features])

        # Get anomaly score
        if self.isolation_forest is None:
            raise RuntimeError("Isolation forest not initialized")
        anomaly_score = self.isolation_forest.decision_function(features_scaled)[0]
        is_anomaly = self.isolation_forest.predict(features_scaled)[0] == -1

        # Get risk classification
        if self.risk_classifier is None:
            raise RuntimeError("Risk classifier not initialized")
        risk_proba = self.risk_classifier.predict_proba(features_scaled)[0]
        self.risk_classifier.predict(features_scaled)[0]

        # Calculate overall risk score
        overall_score = self._calculate_overall_score(
            anomaly_score, risk_proba, features, transaction_data
        )

        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)

        # Extract detailed risk factors
        risk_factors = self._analyze_risk_factors(
            features, transaction_data, user_history or []
        )

        # Generate AI insights and recommendations
        insights = self._generate_ai_insights(
            transaction_data, risk_factors, anomaly_score, is_anomaly
        )
        recommendations = self._generate_recommendations(risk_level, risk_factors)

        return AdvancedRiskScore(
            overall_score=overall_score,
            confidence=max(risk_proba),
            risk_level=risk_level,
            factors=risk_factors,
            recommendations=recommendations,
            ai_insights=insights,
            timestamp=datetime.now(UTC),
        )

    def _extract_features(
        self, transaction: dict[str, Any], history: list[dict[str, Any]]
    ) -> list[float]:
        """Extract numerical features for AI analysis."""

        # Transaction amount (log - scaled for better distribution)
        amount = float(transaction.get("amount", 0))
        log_amount = np.log1p(amount)

        # Transaction frequency (transactions per day)
        frequency = len([h for h in history if self._is_recent(h, days=1)])

        # Time - based features
        tx_time = transaction.get("timestamp", datetime.now(UTC))
        if isinstance(tx_time, str):
            tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
        hour = tx_time.hour

        # Geographical risk (mock - based on addresses or known patterns)
        geo_risk = self._calculate_geo_risk(transaction)

        # Address age and reputation
        addr_age = self._calculate_address_age(transaction.get("from_address", ""))

        # Network centrality (mock calculation)
        centrality = self._calculate_network_centrality(transaction)

        return [log_amount, frequency, hour, geo_risk, addr_age, centrality]

    def _calculate_overall_score(
        self,
        anomaly_score: float,
        risk_proba: np.ndarray,
        features: list[float],
        transaction: dict[str, Any],
    ) -> float:
        """Calculate weighted overall risk score."""

        # Normalize anomaly score to 0 - 1 range
        normalized_anomaly = max(0, min(1, (1 - anomaly_score) / 2))

        # Get high - risk probability
        high_risk_proba = risk_proba[2] if len(risk_proba) > 2 else 0

        # Combine scores with weights
        overall = (
            normalized_anomaly * 0.4
            + high_risk_proba * 0.4
            + self._calculate_rule_based_score(features, transaction) * 0.2
        )

        return min(1.0, max(0.0, overall))

    def _calculate_rule_based_score(
        self, features: list[float], transaction: dict[str, Any]
    ) -> float:
        """Calculate rule - based risk component."""
        score = 0.0

        # Large amount penalty
        amount = np.exp(features[0]) - 1  # Reverse log transformation
        if amount > 10000:
            score += 0.3
        elif amount > 1000:
            score += 0.1

        # High frequency penalty
        if features[1] > 20:
            score += 0.2
        elif features[1] > 10:
            score += 0.1

        # Unusual time penalty
        hour = features[2]
        if hour < 6 or hour > 22:
            score += 0.1

        # Geographic risk
        score += features[3] * 0.2

        # New address penalty
        if features[4] < 7:  # Less than 7 days old
            score += 0.2

        return min(1.0, score)

    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from numerical score."""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.3:
            return "MEDIUM"
        else:
            return "LOW"

    def _analyze_risk_factors(
        self,
        features: list[float],
        transaction: dict[str, Any],
        history: list[dict[str, Any]] | None,
    ) -> RiskFactors:
        """Analyze individual risk factors."""
        history = history or []
        return RiskFactors(
            transaction_frequency=min(1.0, features[1] / 50),  # Normalize to 0 - 1
            amount_anomaly=min(1.0, (np.exp(features[0]) - 1) / 50000),  # Normalize
            time_pattern=1.0 if features[2] < 6 or features[2] > 22 else 0.0,
            address_reputation=features[3],  # Already 0 - 1
            geographical_risk=features[3],
            behavioral_pattern=self._analyze_behavioral_pattern(transaction, history),
            network_analysis=features[5],  # Network centrality
        )

    def _generate_ai_insights(
        self,
        transaction: dict[str, Any],
        factors: RiskFactors,
        anomaly_score: float,
        is_anomaly: bool,
    ) -> list[str]:
        """Generate AI - powered insights."""
        insights = []

        if is_anomaly:
            insights.append(
                "🤖 AI detected this transaction as anomalous compared to normal patterns"
            )

        if factors.transaction_frequency > 0.7:
            insights.append(
                "🔄 High transaction frequency detected - possible automated trading"
            )

        if factors.amount_anomaly > 0.8:
            insights.append(
                "💰 Unusually large transaction amount compared to typical patterns"
            )

        if factors.time_pattern > 0.5:
            insights.append(
                "⏰ Transaction occurred during unusual hours - potential suspicious activity"
            )

        if factors.geographical_risk > 0.6:
            insights.append(
                "🌍 Geographic risk factors detected - location - based risk assessment triggered"
            )

        if factors.behavioral_pattern > 0.7:
            insights.append(
                "🧠 Behavioral analysis indicates deviation from normal user patterns"
            )

        # Advanced ML insights
        if anomaly_score < -0.5:
            insights.append(
                "[ALERT] Machine learning models flag this as highly unusual transaction"
            )

        return insights

    def _generate_recommendations(
        self, risk_level: str, factors: RiskFactors
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if risk_level in ["HIGH", "CRITICAL"]:
            recommendations.append(
                "[ACTION] Consider requiring additional verification"
            )
            recommendations.append("👀 Manual review recommended")

        if factors.transaction_frequency > 0.6:
            recommendations.append("⏱️ Implement velocity checks")

        if factors.amount_anomaly > 0.7:
            recommendations.append("💡 Set up amount - based alerts")

        if factors.geographical_risk > 0.5:
            recommendations.append(
                "🔍 Enhanced due diligence for high - risk jurisdictions"
            )

        if risk_level == "CRITICAL":
            recommendations.append("🚨 Immediate investigation required")
            recommendations.append("❌ Consider blocking transaction pending review")

        return recommendations

    # Helper methods

    def _is_recent(self, transaction: dict[str, Any], days: int = 1) -> bool:
        """Check if transaction is within recent timeframe."""
        tx_time = transaction.get("timestamp", datetime.now(UTC))
        if isinstance(tx_time, str):
            tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))

        return (datetime.now(UTC) - tx_time).days <= days

    def _calculate_geo_risk(self, transaction: dict[str, Any]) -> float:
        """Calculate geographical risk score."""
        # Mock implementation - in production, use real geolocation data
        address = transaction.get("from_address", "")
        # Simple hash - based mock risk
        return (hash(address) % 100) / 100.0

    def _calculate_address_age(self, address: str) -> float:
        """Calculate address age in days."""
        # Mock implementation - in production, query blockchain for first transaction
        return max(1, (hash(address) % 365) + 1)

    def _calculate_network_centrality(self, transaction: dict[str, Any]) -> float:
        """Calculate network centrality score."""
        # Mock implementation - in production, analyze transaction graph
        address = transaction.get("from_address", "")
        return (hash(address + "centrality") % 100) / 100.0

    def _analyze_behavioral_pattern(
        self, transaction: dict[str, Any], history: list[dict[str, Any]]
    ) -> float:
        """Analyze behavioral patterns."""
        if len(history) < 5:
            return 0.5  # Insufficient data

        # Simple pattern analysis - in production, use more sophisticated methods
        current_amount = float(transaction.get("amount", 0))
        historical_amounts = [float(h.get("amount", 0)) for h in history[-10:]]

        if not historical_amounts:
            return 0.5

        avg_amount = sum(historical_amounts) / len(historical_amounts)
        deviation = abs(current_amount - avg_amount) / (avg_amount + 1)

        return min(1.0, deviation)


# Global instance
advanced_ai_engine = AdvancedAIRiskEngine()


def get_advanced_risk_score(
    transaction_data: dict[str, Any], user_history: list[dict[str, Any]] = None
) -> AdvancedRiskScore:
    """Get advanced AI risk score for a transaction."""
    return advanced_ai_engine.analyze_transaction(transaction_data, user_history)


def is_professional_feature_available(user_tier: str) -> bool:
    """Check if user has access to professional AI features."""
    return user_tier.lower() in ["professional", "enterprise"]
