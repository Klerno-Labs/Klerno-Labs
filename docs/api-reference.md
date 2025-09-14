# API Reference

## Authentication

All API requests require authentication using an API key sent in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" https://api.klerno.com/health
```

## Base URL

- **Production**: `https://api.klerno.com`
- **Staging**: `https://staging-api.klerno.com`

## Rate Limits

- **Standard Plan**: 1,000 requests per hour
- **Pro Plan**: 10,000 requests per hour  
- **Enterprise Plan**: Unlimited

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Total requests allowed per hour
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when rate limit resets

## Endpoints

### Health Check

Check API availability and your authentication status.

**Request:**
```http
GET /health
X-API-Key: your-api-key
```

**Response:**
```json
{
  "status": "ok",
  "time": "2025-01-27T10:00:00Z"
}
```

### Transaction Analysis

#### Analyze Single Transaction

Analyze a single transaction for risk and categorization.

**Request:**
```http
POST /analyze/tx
Content-Type: application/json
X-API-Key: your-api-key

{
  "tx_id": "abc123...",
  "timestamp": "2025-01-27T10:00:00Z",
  "chain": "XRPL",
  "from_addr": "rSender123...",
  "to_addr": "rReceiver456...",
  "amount": 1000.0,
  "symbol": "XRP",
  "direction": "out",
  "memo": "Payment description",
  "fee": 0.001
}
```

**Parameters:**
- `tx_id` (string, required): Unique transaction identifier
- `timestamp` (string, required): ISO 8601 timestamp
- `chain` (string, required): Blockchain name (e.g., "XRPL", "ETH")
- `from_addr` (string, required): Sender address
- `to_addr` (string, required): Recipient address
- `amount` (number, required): Transaction amount
- `symbol` (string, required): Currency symbol
- `direction` (string, required): "in" or "out" 
- `memo` (string, optional): Transaction memo/note
- `fee` (number, optional): Transaction fee

**Response:**
```json
{
  "tx_id": "abc123...",
  "timestamp": "2025-01-27T10:00:00Z",
  "chain": "XRPL",
  "from_addr": "rSender123...",
  "to_addr": "rReceiver456...",
  "amount": 1000.0,
  "symbol": "XRP",
  "direction": "out",
  "memo": "Payment description",
  "fee": 0.001,
  "score": 0.85,
  "flags": ["high_amount", "new_address"],
  "category": "transfer"
}
```

#### Analyze Batch Transactions

Analyze multiple transactions in a single request for better performance.

**Request:**
```http
POST /analyze/batch
Content-Type: application/json
X-API-Key: your-api-key

[
  {
    "tx_id": "abc123...",
    "timestamp": "2025-01-27T10:00:00Z",
    // ... other transaction fields
  },
  {
    "tx_id": "def456...",
    "timestamp": "2025-01-27T10:01:00Z",
    // ... other transaction fields
  }
]
```

**Response:**
```json
{
  "summary": {
    "total": 2,
    "high_risk": 1,
    "medium_risk": 0,
    "low_risk": 1,
    "avg_risk": 0.425
  },
  "items": [
    {
      "tx_id": "abc123...",
      "score": 0.85,
      "flags": ["high_amount"],
      "category": "transfer"
      // ... other fields
    },
    {
      "tx_id": "def456...", 
      "score": 0.0,
      "flags": [],
      "category": "transfer"
      // ... other fields
    }
  ]
}
```

### XRPL Integration

#### Parse XRPL Transaction Data

Convert raw XRPL transaction data into Klerno Labs format and analyze.

**Request:**
```http
POST /integrations/xrpl/parse
Content-Type: application/json
X-API-Key: your-api-key

{
  "account": "rAccount123...",
  "transactions": [
    {
      // Raw XRPL transaction data
      "Account": "rSender123...",
      "Destination": "rReceiver456...",
      "Amount": "1000000000",
      "Fee": "12",
      "TransactionType": "Payment"
      // ... other XRPL fields
    }
  ]
}
```

#### Fetch XRPL Account Transactions

Fetch and analyze transactions for an XRPL account.

**Request:**
```http
GET /integrations/xrpl/fetch?account=rAccount123...&limit=10
X-API-Key: your-api-key
```

**Parameters:**
- `account` (string, required): XRPL account address
- `limit` (integer, optional): Maximum transactions to fetch (default: 10, max: 100)

### Advanced Analytics

#### Comprehensive Analytics

Get detailed analytics and insights for a time period.

**Request:**
```http
GET /analytics/comprehensive?days=30
X-API-Key: your-api-key
```

**Parameters:**
- `days` (integer, optional): Analysis period in days (default: 30, max: 365)

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
        "max_risk": 0.95,
        "transaction_count": 45,
        "total_volume": 125000.0
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
        "transaction_count": 15,
        "total_volume": 250000.0,
        "avg_risk": 0.89,
        "max_risk": 0.99
      }
    ],
    "category_distribution": {
      "transfer": 800,
      "exchange": 250,
      "defi": 150,
      "unknown": 50
    },
    "network_analysis": {
      "total_connections": 1250,
      "unique_senders": 456,
      "hub_addresses": [
        {
          "address": "rHub123...",
          "connection_count": 45
        }
      ],
      "avg_connections_per_address": 2.74
    }
  },
  "insights": [
    {
      "type": "warning",
      "title": "High Average Risk Detected",
      "description": "Average risk score of 0.850 is significantly elevated. Immediate review recommended.",
      "action": "Review high-risk transactions and consider adjusting risk thresholds.",
      "priority": "high"
    }
  ]
}
```

#### AI-Powered Insights

Get AI-generated insights about transaction patterns and risks.

**Request:**
```http
GET /analytics/insights?days=7
X-API-Key: your-api-key
```

**Response:**
```json
{
  "insights": [
    {
      "type": "warning",
      "title": "Unusual Transaction Volume",
      "description": "Transaction volume has increased 300% compared to previous week",
      "priority": "high"
    },
    {
      "type": "info", 
      "title": "New High-Risk Address",
      "description": "Address rNew123... shows suspicious patterns",
      "priority": "medium"
    }
  ],
  "generated_at": "2025-01-27T10:00:00Z"
}
```

#### Network Analysis

Get detailed network analysis of transaction patterns.

**Request:**
```http
GET /analytics/network-analysis?days=30
X-API-Key: your-api-key
```

**Response:**
```json
{
  "network_analysis": {
    "total_connections": 1250,
    "unique_senders": 456,
    "hub_addresses": [
      {
        "address": "rHub123...",
        "connection_count": 45
      }
    ]
  },
  "top_risk_addresses": [
    {
      "address": "rRisky123...",
      "avg_risk": 0.89,
      "transaction_count": 25
    }
  ],
  "analysis_period": "30 days"
}
```

#### Risk Trends

Get risk trend analysis over time.

**Request:**
```http
GET /analytics/risk-trends?days=30
X-API-Key: your-api-key
```

### Alerts

#### Get Alerts

Retrieve high-risk transaction alerts.

**Request:**
```http
GET /alerts?limit=100
X-API-Key: your-api-key
```

**Parameters:**
- `limit` (integer, optional): Maximum alerts to return (default: 100, max: 1000)

**Response:**
```json
{
  "threshold": 0.75,
  "count": 25,
  "items": [
    {
      "tx_id": "alert123...",
      "timestamp": "2025-01-27T09:30:00Z",
      "risk_score": 0.95,
      "flags": ["suspicious_pattern", "high_amount"],
      "category": "transfer",
      "amount": 50000.0,
      "from_addr": "rSender123...",
      "to_addr": "rReceiver456..."
    }
  ]
}
```

### Reports

#### CSV Export

Export transaction data as CSV.

**Request:**
```http
GET /export/csv?wallet=rWallet123...&limit=1000
X-API-Key: your-api-key
```

**Parameters:**
- `wallet` (string, optional): Filter by wallet address
- `limit` (integer, optional): Maximum records (default: 1000, max: 10000)

**Response:**
```json
{
  "rows": 500,
  "csv": "timestamp,tx_id,from_addr,to_addr,amount,symbol,risk_score,category\n2025-01-27T10:00:00Z,abc123...,rSender...,rReceiver...,1000.0,XRP,0.85,transfer\n..."
}
```

#### CSV Download

Download CSV file directly.

**Request:**
```http
GET /export/csv/download?wallet=rWallet123...&limit=1000
X-API-Key: your-api-key
```

**Response:** CSV file download with `Content-Disposition: attachment` header.

### Memory/Storage

#### Save and Analyze Transaction

Analyze a transaction and save it to the database.

**Request:**
```http
POST /analyze_and_save/tx
Content-Type: application/json
X-API-Key: your-api-key

{
  "tx_id": "save123...",
  "timestamp": "2025-01-27T10:00:00Z",
  // ... other transaction fields
}
```

**Response:**
```json
{
  "saved": true,
  "item": {
    "tx_id": "save123...",
    "risk_score": 0.85,
    "risk_bucket": "high",
    // ... analyzed transaction data
  },
  "email": {
    "sent": true,
    "to": "alerts@example.com"
  }
}
```

#### Get Transactions for Wallet

Retrieve stored transactions for a specific wallet.

**Request:**
```http
GET /transactions/rWallet123...?limit=100
X-API-Key: your-api-key
```

**Response:**
```json
{
  "wallet": "rWallet123...",
  "count": 50,
  "items": [
    {
      "tx_id": "stored123...",
      "timestamp": "2025-01-27T10:00:00Z",
      "risk_score": 0.65,
      // ... other fields
    }
  ]
}
```

### AI/LLM Features

#### Explain Transaction

Get AI explanation for a transaction's risk score.

**Request:**
```http
POST /explain/tx
Content-Type: application/json
X-API-Key: your-api-key

{
  "tx_id": "explain123...",
  "timestamp": "2025-01-27T10:00:00Z",
  "amount": 50000.0,
  "risk_score": 0.95,
  "flags": ["high_amount", "suspicious_pattern"]
}
```

**Response:**
```json
{
  "explanation": "This transaction received a high risk score of 0.95 due to several factors: the unusually large amount of $50,000 significantly exceeds the typical transaction size for this address, and the transaction exhibits patterns consistent with potential money laundering schemes. The recipient address has been flagged in previous suspicious activity reports."
}
```

#### Explain Batch

Get explanations for multiple transactions.

**Request:**
```http
POST /explain/batch
Content-Type: application/json
X-API-Key: your-api-key

{
  "items": [
    {
      "tx_id": "batch1...",
      "risk_score": 0.85
      // ... other fields
    },
    {
      "tx_id": "batch2...",
      "risk_score": 0.15
      // ... other fields  
    }
  ]
}
```

#### Natural Language Query

Ask questions about your transaction data in natural language.

**Request:**
```http
POST /ask
Content-Type: application/json
X-API-Key: your-api-key

{
  "question": "Show me all high-risk transactions from the last week involving amounts over $10,000"
}
```

**Response:**
```json
{
  "filters": {
    "min_amount": 10000,
    "date_from": "2025-01-20T00:00:00Z",
    "risk_bucket": "high"
  },
  "count": 5,
  "preview": [
    {
      "tx_id": "query1...",
      "amount": 25000.0,
      "risk_score": 0.89
    }
  ],
  "answer": "I found 5 high-risk transactions from the last week with amounts over $10,000. The largest was $25,000 with a risk score of 0.89, flagged for suspicious patterns and new address usage."
}
```

#### Summary Report

Get AI-generated summary of transaction activity.

**Request:**
```http
GET /explain/summary?days=7&wallet=rWallet123...
X-API-Key: your-api-key
```

**Response:**
```json
{
  "summary": "Over the past 7 days, this wallet processed 45 transactions totaling $125,000. Risk levels were generally low (average 0.23) with 3 transactions flagged for review. Notable patterns include increased activity on weekends and larger amounts during business hours.",
  "period": "7 days",
  "transaction_count": 45,
  "total_volume": 125000.0,
  "key_insights": [
    "Weekend activity spike suggests automated processing",
    "Business hour concentration indicates legitimate operations",
    "3 transactions require manual review"
  ]
}
```

### Plugin System

#### List Plugins

Get list of available plugins.

**Request:**
```http
GET /plugins
X-API-Key: your-api-key
```

**Response:**
```json
{
  "plugins": [
    {
      "name": "SampleAnalytics",
      "metadata": {
        "name": "SampleAnalytics",
        "version": "1.0.0",
        "description": "Sample analytics plugin",
        "author": "Klerno Labs",
        "tags": ["analytics", "demo"]
      },
      "status": "active"
    }
  ]
}
```

#### Get Plugin Info

Get detailed information about a specific plugin.

**Request:**
```http
GET /plugins/SampleAnalytics
X-API-Key: your-api-key
```

#### Execute Plugin Hook

Manually execute a plugin hook.

**Request:**
```http
POST /plugins/hooks/transaction_analyzed/execute
Content-Type: application/json
X-API-Key: your-api-key

{
  "transaction_data": {
    "tx_id": "hook123...",
    "risk_score": 0.75
  }
}
```

**Response:**
```json
{
  "hook": "transaction_analyzed",
  "results": [
    {
      "plugin": "SampleAnalytics",
      "custom_risk_score": 0.123,
      "analysis_note": "Custom analytics applied"
    }
  ]
}
```

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error description",
  "error_code": "INVALID_REQUEST",
  "timestamp": "2025-01-27T10:00:00Z"
}
```

### Common Error Codes

- `UNAUTHORIZED` (401): Invalid or missing API key
- `FORBIDDEN` (403): API key doesn't have required permissions
- `NOT_FOUND` (404): Resource not found
- `RATE_LIMITED` (429): Rate limit exceeded
- `INVALID_REQUEST` (400): Invalid request parameters
- `INTERNAL_ERROR` (500): Server error

### Rate Limiting

When rate limited, response includes:

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 3600
}
```

## WebSocket API

### Real-time Alerts

Connect to receive real-time transaction alerts.

**Connection:**
```javascript
const ws = new WebSocket('wss://api.klerno.com/ws/alerts');
```

**Authentication:**
Include API key in connection headers or send after connection:
```javascript
ws.send(JSON.stringify({
  "auth": "your-api-key"
}));
```

**Watch Addresses:**
```javascript
ws.send(JSON.stringify({
  "watch": ["rAddress1...", "rAddress2..."]
}));
```

**Message Types:**

Alert message:
```json
{
  "type": "tx",
  "item": {
    "tx_id": "alert123...",
    "risk_score": 0.95,
    "timestamp": "2025-01-27T10:00:00Z"
  }
}
```

Acknowledgment:
```json
{
  "type": "ack",
  "watch": ["rAddress1...", "rAddress2..."]
}
```

Health check:
```json
{
  "type": "pong"
}
```

## Webhooks

Configure webhooks to receive notifications at your endpoint.

### Setup

Configure webhook URL and events in your account settings.

### Events

- `transaction_analyzed`: New transaction analyzed
- `alert_generated`: High-risk alert created
- `risk_threshold_exceeded`: Transaction exceeds risk threshold

### Payload

```json
{
  "event": "alert_generated",
  "timestamp": "2025-01-27T10:00:00Z",
  "data": {
    "alert_id": "alert_123",
    "transaction": {
      "tx_id": "webhook123...",
      "risk_score": 0.95,
      "amount": 50000.0
    }
  },
  "signature": "sha256=..."
}
```

### Verification

Verify webhook authenticity using HMAC-SHA256 signature:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    computed = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={computed}" == signature
```

## SDK Examples

### Python SDK

```python
pip install klerno-python
```

```python
from klerno import KlernoClient

client = KlernoClient(api_key="your-api-key")

# Analyze transaction
result = client.analyze_transaction({
    "tx_id": "example",
    "amount": 1000.0,
    # ... other fields
})

# Get analytics
analytics = client.get_analytics(days=30)

# Real-time alerts
def on_alert(alert):
    print(f"Alert: {alert['risk_score']}")

client.subscribe_alerts(callback=on_alert)
```

### JavaScript SDK

```bash
npm install klerno-js
```

```javascript
import Klerno from 'klerno-js';

const client = new Klerno({ apiKey: 'your-api-key' });

// Analyze transaction
const result = await client.analyzeTransaction({
    txId: 'example',
    amount: 1000.0
    // ... other fields
});

// Real-time alerts
client.onAlert((alert) => {
    console.log(`Alert: ${alert.riskScore}`);
});
```