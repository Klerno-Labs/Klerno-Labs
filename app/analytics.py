"""
Advanced Analytics Module for Klerno Labs
Provides enhanced analytics, insights, and dashboard functionality
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

from . import store


@dataclass
class AnalyticsMetrics:
    """Enhanced analytics metrics structure"""
    total_transactions: int
    total_volume: float
    avg_risk_score: float
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    unique_addresses: int
    top_risk_addresses: List[Dict[str, Any]]
    risk_trend: List[Dict[str, Any]]
    category_distribution: Dict[str, int]
    hourly_activity: List[Dict[str, Any]]
    network_analysis: Dict[str, Any]
    anomaly_score: float


class AdvancedAnalytics:
    """Advanced analytics engine for transaction analysis"""
    
    def __init__(self):
        self.risk_thresholds = {
            'low': 0.33,
            'medium': 0.66,
            'high': 1.0
        }
    
    def generate_comprehensive_metrics(self, days: int = 30) -> AnalyticsMetrics:
        """Generate comprehensive analytics metrics for the dashboard"""
        # Get data from the last N days
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = store.list_all(limit=50000)
        
        if not rows:
            return self._empty_metrics()
        
        df = pd.DataFrame(rows)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['risk_score'] = df.apply(lambda row: self._get_risk_score(row), axis=1)
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        
        # Filter by date range
        recent_df = df[df['timestamp'] >= cutoff] if not df.empty else df
        
        if recent_df.empty:
            return self._empty_metrics()
        
        return AnalyticsMetrics(
            total_transactions=len(recent_df),
            total_volume=float(recent_df['amount'].sum()),
            avg_risk_score=float(recent_df['risk_score'].mean()),
            high_risk_count=int((recent_df['risk_score'] >= self.risk_thresholds['medium']).sum()),
            medium_risk_count=int(((recent_df['risk_score'] >= self.risk_thresholds['low']) & 
                                 (recent_df['risk_score'] < self.risk_thresholds['medium'])).sum()),
            low_risk_count=int((recent_df['risk_score'] < self.risk_thresholds['low']).sum()),
            unique_addresses=self._count_unique_addresses(recent_df),
            top_risk_addresses=self._get_top_risk_addresses(recent_df),
            risk_trend=self._calculate_risk_trend(recent_df),
            category_distribution=self._get_category_distribution(recent_df),
            hourly_activity=self._get_hourly_activity(recent_df),
            network_analysis=self._analyze_network_patterns(recent_df),
            anomaly_score=self._calculate_anomaly_score(recent_df)
        )
    
    def _get_risk_score(self, row: pd.Series) -> float:
        """Extract risk score from row with fallback"""
        try:
            score = row.get('risk_score', row.get('score', 0))
            if pd.isna(score):
                return 0.0
            return float(score)
        except (ValueError, TypeError):
            return 0.0
    
    def _count_unique_addresses(self, df: pd.DataFrame) -> int:
        """Count unique addresses in the dataset"""
        addresses = set()
        for _, row in df.iterrows():
            if row.get('from_addr'):
                addresses.add(row['from_addr'])
            if row.get('to_addr'):
                addresses.add(row['to_addr'])
        return len(addresses)
    
    def _get_top_risk_addresses(self, df: pd.DataFrame, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top risk addresses with their metrics"""
        address_metrics = {}
        
        for _, row in df.iterrows():
            for addr_field in ['from_addr', 'to_addr']:
                addr = row.get(addr_field)
                if not addr:
                    continue
                
                if addr not in address_metrics:
                    address_metrics[addr] = {
                        'address': addr,
                        'transaction_count': 0,
                        'total_volume': 0,
                        'avg_risk': 0,
                        'max_risk': 0,
                        'risk_scores': []
                    }
                
                metrics = address_metrics[addr]
                metrics['transaction_count'] += 1
                metrics['total_volume'] += float(row.get('amount', 0))
                risk_score = self._get_risk_score(row)
                metrics['risk_scores'].append(risk_score)
                metrics['max_risk'] = max(metrics['max_risk'], risk_score)
        
        # Calculate averages and sort by risk
        for addr, metrics in address_metrics.items():
            if metrics['risk_scores']:
                metrics['avg_risk'] = np.mean(metrics['risk_scores'])
            del metrics['risk_scores']  # Remove raw scores to save space
        
        # Sort by average risk score and return top addresses
        sorted_addresses = sorted(address_metrics.values(), 
                                key=lambda x: x['avg_risk'], reverse=True)
        
        return sorted_addresses[:limit]
    
    def _calculate_risk_trend(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Calculate risk trend over time"""
        if df.empty:
            return []
        
        # Group by day and calculate daily metrics
        df['date'] = df['timestamp'].dt.date
        daily_metrics = df.groupby('date').agg({
            'risk_score': ['mean', 'max', 'count'],
            'amount': 'sum'
        }).reset_index()
        
        daily_metrics.columns = ['date', 'avg_risk', 'max_risk', 'transaction_count', 'total_volume']
        
        trend = []
        for _, row in daily_metrics.iterrows():
            trend.append({
                'date': row['date'].isoformat(),
                'avg_risk': float(row['avg_risk']),
                'max_risk': float(row['max_risk']),
                'transaction_count': int(row['transaction_count']),
                'total_volume': float(row['total_volume'])
            })
        
        return sorted(trend, key=lambda x: x['date'])
    
    def _get_category_distribution(self, df: pd.DataFrame) -> Dict[str, int]:
        """Get distribution of transaction categories"""
        if 'category' not in df.columns:
            return {'unknown': len(df)}
        
        return df['category'].fillna('unknown').value_counts().to_dict()
    
    def _get_hourly_activity(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze transaction activity by hour of day"""
        if df.empty:
            return []
        
        df['hour'] = df['timestamp'].dt.hour
        hourly_stats = df.groupby('hour').agg({
            'risk_score': 'mean',
            'amount': 'sum'
        }).reset_index()
        
        activity = []
        for hour in range(24):
            hour_data = hourly_stats[hourly_stats['hour'] == hour]
            if not hour_data.empty:
                activity.append({
                    'hour': hour,
                    'avg_risk': float(hour_data['risk_score'].iloc[0]),
                    'total_volume': float(hour_data['amount'].iloc[0]),
                    'transaction_count': int(len(df[df['hour'] == hour]))
                })
            else:
                activity.append({
                    'hour': hour,
                    'avg_risk': 0.0,
                    'total_volume': 0.0,
                    'transaction_count': 0
                })
        
        return activity
    
    def _analyze_network_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze network patterns and connections"""
        if df.empty:
            return {'total_connections': 0, 'clusters': [], 'centrality_metrics': {}}
        
        # Create address interaction matrix
        connections = {}
        for _, row in df.iterrows():
            from_addr = row.get('from_addr')
            to_addr = row.get('to_addr')
            
            if from_addr and to_addr:
                if from_addr not in connections:
                    connections[from_addr] = set()
                connections[from_addr].add(to_addr)
        
        # Calculate basic network metrics
        total_connections = sum(len(targets) for targets in connections.values())
        
        # Find addresses with most connections (hubs)
        hub_addresses = sorted(connections.items(), 
                             key=lambda x: len(x[1]), reverse=True)[:5]
        
        return {
            'total_connections': total_connections,
            'unique_senders': len(connections),
            'hub_addresses': [{'address': addr, 'connection_count': len(targets)} 
                            for addr, targets in hub_addresses],
            'avg_connections_per_address': total_connections / len(connections) if connections else 0
        }
    
    def _calculate_anomaly_score(self, df: pd.DataFrame) -> float:
        """Calculate overall anomaly score for the dataset"""
        if df.empty or len(df) < 2:
            return 0.0
        
        # Calculate z-scores for amount anomalies
        amounts = df['amount'].values
        if len(amounts) > 1 and np.std(amounts) > 0:
            z_scores = np.abs((amounts - np.mean(amounts)) / np.std(amounts))
            anomaly_count = np.sum(z_scores > 2)  # More than 2 standard deviations
            return float(anomaly_count / len(amounts))
        
        return 0.0
    
    def _empty_metrics(self) -> AnalyticsMetrics:
        """Return empty metrics structure"""
        return AnalyticsMetrics(
            total_transactions=0,
            total_volume=0.0,
            avg_risk_score=0.0,
            high_risk_count=0,
            medium_risk_count=0,
            low_risk_count=0,
            unique_addresses=0,
            top_risk_addresses=[],
            risk_trend=[],
            category_distribution={},
            hourly_activity=[],
            network_analysis={},
            anomaly_score=0.0
        )


class InsightsEngine:
    """AI-powered insights generator"""
    
    def generate_insights(self, metrics: AnalyticsMetrics) -> List[Dict[str, Any]]:
        """Generate AI-powered insights from analytics data"""
        insights = []
        
        # Risk level insights
        if metrics.avg_risk_score > 0.7:
            insights.append({
                'type': 'warning',
                'title': 'High Average Risk Detected',
                'description': f'Average risk score of {metrics.avg_risk_score:.3f} is significantly elevated. Immediate review recommended.',
                'action': 'Review high-risk transactions and consider adjusting risk thresholds.',
                'priority': 'high'
            })
        elif metrics.avg_risk_score > 0.5:
            insights.append({
                'type': 'info',
                'title': 'Moderate Risk Environment',
                'description': f'Risk levels are moderate at {metrics.avg_risk_score:.3f}. Monitor for trends.',
                'action': 'Continue monitoring and prepare enhanced due diligence procedures.',
                'priority': 'medium'
            })
        
        # Volume insights
        if metrics.total_volume > 1000000:  # $1M threshold
            insights.append({
                'type': 'info',
                'title': 'High Transaction Volume',
                'description': f'Total transaction volume of ${metrics.total_volume:,.2f} detected.',
                'action': 'Consider volume-based risk adjustments and enhanced monitoring.',
                'priority': 'medium'
            })
        
        # Anomaly insights
        if metrics.anomaly_score > 0.1:
            insights.append({
                'type': 'warning',
                'title': 'Transaction Anomalies Detected',
                'description': f'{metrics.anomaly_score:.1%} of transactions show anomalous patterns.',
                'action': 'Investigate unusual transaction amounts and patterns.',
                'priority': 'high'
            })
        
        # Network insights
        if metrics.network_analysis.get('hub_addresses'):
            top_hub = metrics.network_analysis['hub_addresses'][0]
            if top_hub['connection_count'] > 10:
                insights.append({
                    'type': 'info',
                    'title': 'Network Hub Identified',
                    'description': f'Address {top_hub["address"][:10]}... has {top_hub["connection_count"]} connections.',
                    'action': 'Review hub address for potential money laundering patterns.',
                    'priority': 'medium'
                })
        
        return insights


# Global analytics instance
analytics_engine = AdvancedAnalytics()
insights_engine = InsightsEngine()