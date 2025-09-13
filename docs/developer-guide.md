# Klerno Labs Developer Documentation

Welcome to the Klerno Labs Developer Documentation. This comprehensive guide will help you integrate with our AML risk intelligence platform and extend its capabilities.

## Quick Start

### Authentication

All API requests require authentication using an API key:

```bash
# Get your API key from the Admin dashboard
export KLERNO_API_KEY="your-api-key-here"

# Use in requests
curl -H "X-API-Key: $KLERNO_API_KEY" https://api.klerno.com/health
```

### Your First API Call

```python
import requests

# Analyze a single transaction
transaction = {
    "tx_id": "example-123",
    "timestamp": "2025-01-27T10:00:00Z",
    "chain": "XRPL",
    "from_addr": "rSender123...",
    "to_addr": "rReceiver456...",
    "amount": 1000.0,
    "symbol": "XRP",
    "direction": "out",
    "memo": "Payment for services"
}

response = requests.post(
    "https://api.klerno.com/analyze/tx",
    json=transaction,
    headers={"X-API-Key": "your-api-key"}
)

result = response.json()
print(f"Risk Score: {result['score']}")
print(f"Category: {result['category']}")
print(f"Flags: {result['flags']}")
```

## Core Concepts

### Risk Scoring

Klerno Labs assigns risk scores from 0.0 (low risk) to 1.0 (high risk) based on:

- **Transaction patterns**: Unusual amounts, timing, or frequency
- **Address reputation**: Known associations with illicit activities  
- **Network analysis**: Position in transaction graphs
- **Behavioral analysis**: Deviation from normal patterns

### Transaction Categories

Transactions are automatically categorized:

- `transfer`: Standard peer-to-peer transfers
- `exchange`: Exchange-related transactions
- `defi`: Decentralized finance protocols
- `mixing`: Potential privacy coin usage
- `gambling`: Gaming/gambling platforms
- `unknown`: Unable to categorize

### Alert System

Alerts are triggered when:
- Risk score exceeds threshold (default: 0.75)
- Transaction amount exceeds limits
- Suspicious patterns detected
- Manual rules triggered

## API Reference

### Transaction Analysis

#### Single Transaction Analysis

```http
POST /analyze/tx
Content-Type: application/json
X-API-Key: your-api-key

{
  "tx_id": "string",
  "timestamp": "2025-01-27T10:00:00Z",
  "chain": "XRPL",
  "from_addr": "string",
  "to_addr": "string", 
  "amount": 1000.0,
  "symbol": "XRP",
  "direction": "out|in",
  "memo": "string",
  "fee": 0.001
}
```

**Response:**
```json
{
  "tx_id": "string",
  "timestamp": "2025-01-27T10:00:00Z",
  "score": 0.85,
  "flags": ["high_amount", "new_address"],
  "category": "transfer",
  "explanation": "High-value transfer to new address"
}
```

#### Batch Analysis

```http
POST /analyze/batch
Content-Type: application/json
X-API-Key: your-api-key

{
  "transactions": [
    // Array of transaction objects
  ]
}
```

### Advanced Analytics

#### Comprehensive Analytics

```http
GET /analytics/comprehensive?days=30
X-API-Key: your-api-key
```

**Response:**
```json
{
  "period_days": 30,
  "metrics": {
    "total_transactions": 1250,
    "total_volume": 5500000.0,
    "avg_risk_score": 0.23,
    "risk_distribution": {
      "high": 45,
      "medium": 180,
      "low": 1025
    },
    "unique_addresses": 892,
    "anomaly_score": 0.05
  },
  "trends": {
    "risk_trend": [
      {
        "date": "2025-01-01", 
        "avg_risk": 0.25,
        "transaction_count": 45
      }
    ],
    "hourly_activity": [
      {
        "hour": 0,
        "avg_risk": 0.15,
        "total_volume": 50000.0,
        "transaction_count": 12
      }
    ]
  },
  "analysis": {
    "top_risk_addresses": [
      {
        "address": "rHighRisk123...",
        "avg_risk": 0.89,
        "transaction_count": 15,
        "total_volume": 250000.0
      }
    ],
    "network_analysis": {
      "total_connections": 1250,
      "hub_addresses": [
        {
          "address": "rHub123...",
          "connection_count": 45
        }
      ]
    }
  },
  "insights": [
    {
      "type": "warning",
      "title": "High Average Risk Detected",
      "description": "Average risk score of 0.850 is significantly elevated.",
      "priority": "high"
    }
  ]
}
```

#### AI-Powered Insights

```http
GET /analytics/insights?days=7
X-API-Key: your-api-key
```

### Real-time Monitoring

#### WebSocket Alerts

Connect to real-time transaction alerts:

```javascript
const ws = new WebSocket('wss://api.klerno.com/ws/alerts');

// Watch specific addresses
ws.send(JSON.stringify({
  watch: ["rAddress1...", "rAddress2..."]
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'tx') {
    console.log('New transaction:', data.item);
    if (data.item.risk_score > 0.75) {
      alert('High-risk transaction detected!');
    }
  }
};
```

### Plugin System

#### List Available Plugins

```http
GET /plugins
X-API-Key: your-api-key
```

#### Execute Plugin Hooks

```http
POST /plugins/hooks/transaction_analyzed/execute
Content-Type: application/json
X-API-Key: your-api-key

{
  "transaction_data": {
    "tx_id": "example-123",
    "risk_score": 0.85
  }
}
```

## Integration Examples

### Python Integration

```python
import requests
from typing import List, Dict, Any

class KlernoClient:
    def __init__(self, api_key: str, base_url: str = "https://api.klerno.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def analyze_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single transaction"""
        response = requests.post(
            f"{self.base_url}/analyze/tx",
            json=transaction,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive analytics"""
        response = requests.get(
            f"{self.base_url}/analytics/comprehensive",
            params={"days": days},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        response = requests.get(
            f"{self.base_url}/alerts",
            params={"limit": limit},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["items"]

# Usage
client = KlernoClient("your-api-key")

# Analyze transaction
result = client.analyze_transaction({
    "tx_id": "example-123",
    "timestamp": "2025-01-27T10:00:00Z",
    "chain": "XRPL",
    "from_addr": "rSender123...",
    "to_addr": "rReceiver456...",
    "amount": 1000.0,
    "symbol": "XRP",
    "direction": "out"
})

print(f"Risk Score: {result['score']}")

# Get analytics
analytics = client.get_analytics(days=7)
print(f"Total Transactions: {analytics['metrics']['total_transactions']}")
```

### Node.js Integration

```javascript
const axios = require('axios');

class KlernoClient {
    constructor(apiKey, baseUrl = 'https://api.klerno.com') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = { 'X-API-Key': apiKey };
    }

    async analyzeTransaction(transaction) {
        const response = await axios.post(
            `${this.baseUrl}/analyze/tx`,
            transaction,
            { headers: this.headers }
        );
        return response.data;
    }

    async getAnalytics(days = 30) {
        const response = await axios.get(
            `${this.baseUrl}/analytics/comprehensive`,
            { 
                params: { days },
                headers: this.headers 
            }
        );
        return response.data;
    }
}

// Usage
const client = new KlernoClient('your-api-key');

client.analyzeTransaction({
    tx_id: 'example-123',
    timestamp: '2025-01-27T10:00:00Z',
    chain: 'XRPL',
    from_addr: 'rSender123...',
    to_addr: 'rReceiver456...',
    amount: 1000.0,
    symbol: 'XRP',
    direction: 'out'
}).then(result => {
    console.log(`Risk Score: ${result.score}`);
}).catch(console.error);
```

## Plugin Development

### Creating a Custom Plugin

```python
from app.plugin_system import BasePlugin, PluginMetadata
from fastapi import FastAPI

class CustomAnalyticsPlugin(BasePlugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="CustomAnalytics",
            version="1.0.0",
            description="Custom analytics for specific use case",
            author="Your Company",
            tags=["analytics", "custom"]
        )
    
    def initialize(self, app: FastAPI, plugin_manager):
        # Register hooks
        plugin_manager.hooks['transaction_analyzed'].register(
            self.on_transaction_analyzed
        )
        
        # Add custom endpoints
        self.add_api_route(
            app,
            "/custom-analysis",
            self.custom_analysis,
            methods=["GET"]
        )
    
    def on_transaction_analyzed(self, transaction_data):
        # Custom analysis logic
        risk_adjustment = 0.1 if transaction_data.get('amount', 0) > 10000 else 0
        
        return {
            "plugin": "CustomAnalytics",
            "risk_adjustment": risk_adjustment,
            "custom_flag": "large_amount" if risk_adjustment > 0 else None
        }
    
    async def custom_analysis(self):
        return {
            "plugin": "CustomAnalytics",
            "analysis": "Custom analysis results"
        }
```

### Plugin Installation

1. Save your plugin file in the `app/plugins/` directory
2. Restart the Klerno Labs application
3. Verify installation: `GET /plugins`

## Webhooks

### Setting Up Webhooks

Configure webhooks to receive real-time notifications:

```python
# Configure webhook URL in settings
webhook_config = {
    "url": "https://your-app.com/klerno-webhook",
    "events": ["high_risk_transaction", "alert_generated"],
    "secret": "your-webhook-secret"
}

# Webhook payload example
{
    "event": "high_risk_transaction",
    "timestamp": "2025-01-27T10:00:00Z",
    "data": {
        "transaction": {
            "tx_id": "example-123",
            "risk_score": 0.95,
            "flags": ["suspicious_pattern", "high_amount"]
        }
    },
    "signature": "sha256=..." // HMAC signature for verification
}
```

## Best Practices

### Performance Optimization

1. **Batch Processing**: Use `/analyze/batch` for multiple transactions
2. **Caching**: Cache results for repeated queries
3. **Rate Limiting**: Respect API rate limits (1000 requests/hour)
4. **Pagination**: Use pagination for large datasets

### Security

1. **API Key Security**: Never expose API keys in client-side code
2. **HTTPS Only**: Always use HTTPS for API calls
3. **Webhook Verification**: Verify webhook signatures
4. **Input Validation**: Validate all transaction data

### Error Handling

```python
import requests
from requests.exceptions import RequestException

def safe_api_call(client, transaction):
    try:
        result = client.analyze_transaction(transaction)
        return result
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Rate limited - wait and retry
            time.sleep(60)
            return safe_api_call(client, transaction)
        elif e.response.status_code == 400:
            # Bad request - check transaction data
            print(f"Invalid transaction data: {e.response.text}")
        else:
            print(f"API error: {e.response.status_code}")
    except RequestException as e:
        print(f"Network error: {e}")
    
    return None
```

## Support

### Community

- **GitHub**: [github.com/Klerno-Labs/Klerno-Labs](https://github.com/Klerno-Labs/Klerno-Labs)
- **Discord**: [Join our developer community](https://discord.gg/klerno-labs)
- **Documentation**: [docs.klerno.com](https://docs.klerno.com)

### Enterprise Support

For enterprise customers:
- **Email**: enterprise@klerno.com
- **Slack Connect**: Available for enterprise plans
- **Phone Support**: 24/7 for critical issues

### Status Page

Monitor API status and incidents:
- **Status Page**: [status.klerno.com](https://status.klerno.com)
- **API Health**: `GET /health`

## Changelog

### v1.5.0 (Latest)
- ✨ Added advanced analytics API
- ✨ Plugin system for extensibility
- ✨ Enhanced onboarding experience
- ✨ Real-time WebSocket alerts
- 🐛 Fixed Bootstrap loading issues
- 📚 Comprehensive developer documentation

### v1.4.0
- ✨ AI-powered insights
- ✨ Network analysis features
- 🐛 Improved risk scoring accuracy

### v1.3.0
- ✨ Batch transaction analysis
- ✨ Export functionality
- 🐛 Performance improvements

---

*This documentation is continuously updated. For the latest information, visit [docs.klerno.com](https://docs.klerno.com).*