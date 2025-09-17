# Klerno Labs - XRPL Integration Guide

## Overview

This guide explains how to use the XRPL payment and subscription system implemented in the Klerno Labs application. The system allows users to subscribe using XRP payments on the XRP Ledger.

## Key Features

- **XRPL Payment Processing**: Generate payment requests and verify payments on the XRP Ledger
- **Subscription Management**: Manage user subscriptions with different tiers and durations
- **Admin Controls**: Admins can view and manage all subscriptions
- **Production Ready**: Configured for deployment on Render with health checks and secure settings

## Setup Instructions

1. **Environment Setup**:
   - Create a `.env` file based on the provided example
   - Configure XRPL settings, including network and destination wallet

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

## XRPL Configuration

The application supports three XRPL networks:
- `mainnet`: Production XRP Ledger
- `testnet`: XRP Ledger Test Net
- `devnet`: XRP Ledger Dev Net (for development)

Configure the network in your `.env` file:
```
XRPL_NET=testnet
DESTINATION_WALLET=your_xrp_wallet_address
SUB_PRICE_XRP=10.0
SUB_DURATION_DAYS=30
```

## Subscription Tiers

The system supports three subscription tiers:
- **Starter**: Core XRPL analytics and transaction monitoring
- **Professional**: Advanced analytics and real-time alerts
- **Enterprise**: Enterprise-grade XRPL intelligence with API access

Tiers can be customized by modifying the `DEFAULT_TIERS` dictionary in `app/subscriptions.py`.

## Payment Flow

1. User selects a subscription tier
2. System generates a payment request with a unique code
3. User sends XRP to the destination wallet
4. User submits the transaction hash (optional)
5. System verifies the payment and activates the subscription

## API Endpoints

### XRPL Payment Endpoints

- `GET /xrpl/network-info`: Get information about the XRPL network configuration
- `POST /xrpl/payment-request`: Create a payment request
- `POST /xrpl/verify-payment`: Verify a payment and activate subscription

### Subscription Endpoints

- `GET /subscriptions/tiers`: List all available subscription tiers
- `GET /subscriptions/my-subscription`: Get current user's subscription status

## Deployment on Render

The application is configured for deployment on Render using the `render.yaml` file. This provides:

- Automatic builds and deployments
- Health check endpoint (`/healthz`)
- Environment variable configuration
- Proper Python version specification

## Security Considerations

- XRPL transaction verification uses cryptographic validation
- Payment requests include unique codes to prevent replay attacks
- Subscription data is stored securely in the database
- All endpoints that modify data are protected with CSRF tokens

## Development Notes

- For local development, use the testnet or devnet
- Test payments can be made using the XRPL Testnet Faucet
- The `xrpl-py` library handles all XRPL interactions

## Troubleshooting

- **Payment Verification Issues**: Ensure the transaction hash is correct and the payment was sent to the correct destination
- **Network Connectivity**: Check that the application can connect to the XRPL network
- **Database Errors**: Verify that the database path is correct and writable

## Further Documentation

- [XRPL Developer Documentation](https://xrpl.org/docs.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Render Deployment Guide](https://render.com/docs/deploy-python)