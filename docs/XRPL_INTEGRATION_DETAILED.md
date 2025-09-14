# XRPL Integration for Payments and Subscriptions

## Overview

This document provides detailed information about the XRPL (XRP Ledger) integration in Klerno Labs for handling payments and subscription management. The integration allows users to make payments using XRP and manages subscription tiers with automatic verification.

## Table of Contents

- [Architecture](#architecture)
- [Setup and Configuration](#setup-and-configuration)
- [Payment Flow](#payment-flow)
- [Subscription Tiers](#subscription-tiers)
- [API Reference](#api-reference)
- [Testing and Development](#testing-and-development)
- [Troubleshooting](#troubleshooting)

## Architecture

The XRPL integration consists of several key components:

1. **XRP Client (`app/integrations/xrp.py`)**: Core connection to the XRPL network
2. **Payment Processing (`app/xrpl_payments.py`)**: Handles payment creation and verification
3. **Subscription Management (`app/subscriptions.py`)**: Manages subscription tiers and user access
4. **Configuration (`app/config.py`)**: Environment-specific XRPL settings

### Component Relationships

```
                         ┌─────────────────┐
                         │   API Routes    │
                         └────────┬────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               │                  │                  │
     ┌─────────▼──────────┐      │        ┌─────────▼──────────┐
     │  XRPL Payments     │◄─────┘        │  Subscriptions     │
     └─────────┬──────────┘               └─────────┬──────────┘
               │                                    │
               │                                    │
     ┌─────────▼──────────┐               ┌─────────▼──────────┐
     │  XRP Integration   │               │  Database Models   │
     └─────────┬──────────┘               └────────────────────┘
               │
     ┌─────────▼──────────┐
     │   XRPL Network     │
     └────────────────────┘
```

## Setup and Configuration

### Environment Variables

Configure XRPL integration by setting the following environment variables in your `.env` file:

```
# XRPL Network (testnet, devnet, or mainnet)
XRPL_NET=testnet

# Destination wallet to receive payments
DESTINATION_WALLET=rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe

# Subscription price in XRP
SUB_PRICE_XRP=10

# Subscription duration in days
SUB_DURATION_DAYS=30
```

### Network Selection

The system supports three XRPL networks:

- **Testnet**: Recommended for development and testing
- **Devnet**: For early integration testing
- **Mainnet**: For production use

### Wallet Setup

1. Create an XRP wallet for your application using [XUMM](https://xumm.app/) or [XRP Toolkit](https://www.xrptoolkit.com/)
2. Set the wallet address as `DESTINATION_WALLET` in your `.env` file
3. For testing, you can fund a testnet wallet using the [XRPL Faucet](https://faucet.altnet.rippletest.net/)

## Payment Flow

### Payment Creation

1. User selects a subscription tier
2. System generates a payment request with:
   - Destination address
   - XRP amount
   - User-specific memo
   - Expiration time

2. User receives payment instructions with:
   - QR code (for mobile wallets)
   - Destination address
   - Exact XRP amount
   - Memo to include

3. User makes the payment from their XRP wallet

### Payment Verification

1. System monitors for incoming transactions to the destination wallet
2. When a transaction is detected, the system:
   - Verifies the transaction hash
   - Confirms the payment amount matches the subscription tier
   - Validates the memo matches the user's request
   - Checks that the payment was received within the validity window

3. Upon successful verification:
   - The subscription is activated
   - User access is updated
   - A receipt is generated

### Code Example: Creating a Payment

```python
from app.xrpl_payments import create_payment_request

# Create a payment request for a user
payment_info = create_payment_request(
    user_id=user.id,
    tier="premium",
    custom_amount=None  # Use the default amount for the tier
)

# The payment_info object contains:
# - destination_address: The wallet to send XRP to
# - amount_xrp: The amount of XRP to send
# - memo: The unique memo to include in the transaction
# - qr_code_url: URL for QR code to scan with mobile wallet
# - expires_at: Timestamp when the payment request expires
```

### Code Example: Verifying a Payment

```python
from app.xrpl_payments import verify_payment

# Verify a payment using the transaction hash
verification_result = verify_payment(transaction_hash)

if verification_result.verified:
    # Payment is verified, activate subscription
    activate_subscription(
        user_id=verification_result.user_id,
        tier=verification_result.tier,
        amount=verification_result.amount,
        transaction_hash=transaction_hash
    )
else:
    # Handle verification failure
    handle_failed_payment(
        reason=verification_result.reason,
        transaction_hash=transaction_hash
    )
```

## Subscription Tiers

The system supports multiple subscription tiers with different pricing and features.

### Tier Structure

Subscription tiers are defined in `app/subscriptions.py`:

```python
class SubscriptionTier(str, Enum):
    """Available subscription tiers."""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class TierDetails:
    """Details for a subscription tier."""
    def __init__(
        self, 
        name: str, 
        price_xrp: float, 
        duration_days: int,
        features: List[str],
        description: str
    ):
        self.name = name
        self.price_xrp = price_xrp
        self.duration_days = duration_days
        self.features = features
        self.description = description
```

### Default Tiers

| Tier | Price (XRP) | Duration | Features |
|------|-------------|----------|----------|
| Basic | 10 XRP | 30 days | Basic analytics, Standard reports |
| Premium | 25 XRP | 30 days | Advanced analytics, Custom reports, API access |
| Enterprise | 100 XRP | 30 days | Full access, Dedicated support, Custom integrations |

### Customizing Tiers

Tiers can be customized in the admin interface or by modifying the tier configuration in `app/subscriptions.py`.

## API Reference

### Endpoints

The XRPL integration exposes the following API endpoints:

#### Create Payment Request

```
POST /api/xrpl/payment-request
```

**Request:**
```json
{
  "user_id": "user123",
  "tier": "premium",
  "custom_amount": null
}
```

**Response:**
```json
{
  "payment_id": "pay_12345",
  "destination_address": "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe",
  "amount_xrp": "25.0",
  "memo": "KL-U123-P-20250914",
  "qr_code_url": "https://api.klernolabs.com/qr/pay_12345",
  "expires_at": "2025-09-14T12:34:56Z"
}
```

#### Verify Payment

```
GET /api/xrpl/verify-payment/{transaction_hash}
```

**Response:**
```json
{
  "verified": true,
  "user_id": "user123",
  "tier": "premium",
  "amount": "25.0",
  "transaction_time": "2025-09-14T10:12:34Z",
  "subscription_id": "sub_12345",
  "expiration_date": "2025-10-14T10:12:34Z"
}
```

#### Get Subscription Status

```
GET /api/subscriptions/status
```

**Response:**
```json
{
  "has_active_subscription": true,
  "tier": "premium",
  "started_at": "2025-09-14T10:12:34Z",
  "expires_at": "2025-10-14T10:12:34Z",
  "features": [
    "Advanced analytics", 
    "Custom reports", 
    "API access"
  ]
}
```

## Testing and Development

### Test Wallets

For development and testing, you can use the following resources:

1. **XRPL Testnet Faucet**: https://faucet.altnet.rippletest.net/
2. **XUMM Dev App**: Create a developer account at https://apps.xumm.dev/

### Testing Payments

1. Set up your environment to use the XRPL Testnet:
   ```
   XRPL_NET=testnet
   ```

2. Generate a test payment request:
   ```python
   from app.xrpl_payments import create_payment_request
   
   # Create a test payment
   payment = create_payment_request(user_id="test123", tier="basic")
   print(f"Send {payment.amount_xrp} XRP to {payment.destination_address}")
   print(f"Include memo: {payment.memo}")
   ```

3. Make the payment using a testnet wallet

4. Verify the payment:
   ```python
   from app.xrpl_payments import verify_payment
   
   # Get the transaction hash from the wallet after payment
   tx_hash = "your_transaction_hash"
   result = verify_payment(tx_hash)
   print(f"Verified: {result.verified}")
   ```

### Mocking XRPL in Tests

For unit testing, you can use the mock XRPL client in `tests/mocks/xrpl_client.py`:

```python
from tests.mocks.xrpl_client import MockXRPLClient

# Replace the real client with a mock for testing
from unittest.mock import patch

with patch('app.integrations.xrp.XRPLClient', MockXRPLClient):
    # Test code here
    payment = create_payment_request(user_id="test123", tier="basic")
    # The mock client will simulate XRPL interactions
```

## Troubleshooting

### Common Issues

#### Transaction Not Verified

**Problem**: Payment was sent but not verified by the system.

**Solutions**:
1. Check that the exact amount was sent
2. Verify the memo was included correctly
3. Confirm the transaction was sent to the correct destination address
4. Check if the payment request has expired

#### Network Connection Issues

**Problem**: Cannot connect to XRPL network.

**Solutions**:
1. Check internet connectivity
2. Verify XRPL_NET is set correctly in .env
3. Check XRPL network status at https://livenet.xrpl.org/ or https://testnet.xrpl.org/

#### Subscription Not Activated

**Problem**: Payment verified but subscription not activated.

**Solutions**:
1. Check database connectivity
2. Verify user exists in the system
3. Check for errors in the subscription activation logic

### Logs and Debugging

Enable detailed logging by setting:

```
LOG_LEVEL=debug
```

XRPL-specific logs will be prefixed with `[XRPL]` for easy filtering.

### Support Resources

- [XRPL Developer Documentation](https://xrpl.org/docs.html)
- [XRPL-py Library Documentation](https://xrpl-py.readthedocs.io/)
- [Klerno Labs Support](mailto:support@klernolabs.com)

---

Last Updated: September 14, 2025