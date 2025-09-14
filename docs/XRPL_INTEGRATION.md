# XRPL Integration for Klerno Labs

This document outlines the XRPL (XRP Ledger) integration for Klerno Labs subscription payments.

## Overview

Klerno Labs now supports subscription payments via the XRP Ledger. Users can purchase subscriptions using XRP, providing a crypto-native payment option that is fast, secure, and has low transaction fees.

## Features

- **Tiered Subscription Model**: Basic, Premium, and Enterprise tiers with different pricing and features
- **XRP Payment Processing**: Generate payment requests with destination tags for tracking
- **Payment Verification**: Verify transactions on the XRP Ledger
- **Subscription Management**: Admin panel for managing user subscriptions

## Integration Components

### 1. Configuration (`app/config.py`)

The configuration module manages environment settings including:

- XRPL network selection (Mainnet/Testnet)
- Destination wallet address
- Subscription pricing
- API endpoints

### 2. XRPL Payments (`app/xrpl_payments.py`)

This module handles XRPL payment operations:

- `create_payment_request()`: Generates payment details (address, amount, destination tag)
- `verify_payment()`: Validates that a payment has been received on the XRP Ledger
- `get_network_info()`: Retrieves current network status and configuration

### 3. Subscription Management (`app/subscriptions.py`)

Manages the subscription lifecycle:

- `SubscriptionTier`: Enum defining subscription tiers (Basic, Premium, Enterprise)
- `create_subscription()`: Creates/updates a user's subscription
- `get_user_subscription()`: Retrieves a user's current subscription
- `require_active_subscription()`: Dependency for routes requiring an active subscription

### 4. Payment Flow

1. User selects a subscription tier on the paywall page
2. User requests payment details via API
3. User sends XRP to the specified address with the required destination tag
4. User submits the transaction hash for verification
5. System verifies the transaction and activates the subscription
6. User is granted access to premium features

## API Endpoints

### Payment Processing

- `POST /xrpl/payment-request`: Create a new payment request
- `POST /xrpl/verify-payment`: Verify a submitted payment
- `GET /xrpl/network-info`: Get current network information

### Subscription Management

- `GET /api/subscription/tiers`: List available subscription tiers
- `GET /api/subscription/my`: Get current user's subscription details
- `POST /api/subscription/upgrade`: Request upgrade to a specific tier

### Admin Endpoints

- `GET /api/subscription/list`: List all subscriptions (admin only)
- `POST /api/subscription/create`: Create a subscription for a user (admin only)

## Management Script

The `scripts/manage_subscriptions.py` utility provides command-line tools for subscription management:

```
# Create a subscription
python scripts/manage_subscriptions.py create USER_ID --tier 1 --days 30

# View a user's subscription
python scripts/manage_subscriptions.py get USER_ID

# List all subscriptions
python scripts/manage_subscriptions.py list
```

## Deployment Notes

- Ensure XRPL wallet secrets are properly secured and not exposed in code
- Set proper environment variables for production deployment
- Configure webhook notifications for payment events (recommended)
- Regular database backups for subscription data

## Testing

For testing purposes, you can use the XRPL Testnet:

1. Set `XRPL_NETWORK` to `testnet` in your environment
2. Use the [XRPL Testnet Faucet](https://faucet.altnet.rippletest.net/) to get test XRP
3. Test the full payment flow in a non-production environment

## Security Considerations

- Always verify payments on-chain before granting subscription access
- Implement rate limiting on payment endpoints to prevent abuse
- Keep private keys secure and never expose them in client-side code
- Monitor for suspicious payment patterns or attempts to bypass verification