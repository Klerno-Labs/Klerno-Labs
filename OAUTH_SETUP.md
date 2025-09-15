# OAuth Configuration Guide

To enable Google and Microsoft OAuth authentication, you need to set up the following environment variables:

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Go to Credentials > Create Credentials > OAuth 2.0 Client ID
5. Set authorized redirect URIs:
   - `http://localhost:8000/auth/oauth/google/callback` (for development)
   - `https://yourdomain.com/auth/oauth/google/callback` (for production)

Add to your `.env` file:
```
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
```

## Microsoft OAuth Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to Azure Active Directory > App registrations
3. Create a new registration
4. Set redirect URIs:
   - `http://localhost:8000/auth/oauth/microsoft/callback` (for development)
   - `https://yourdomain.com/auth/oauth/microsoft/callback` (for production)

Add to your `.env` file:
```
MICROSOFT_CLIENT_ID=your_microsoft_client_id_here
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret_here
```

## Features Added

### Enhanced Authentication
- **Google OAuth**: One-click sign up/login with Google accounts
- **Microsoft OAuth**: One-click sign up/login with Microsoft accounts
- **Traditional Email**: Enhanced forms with professional design
- **Wallet Integration**: Users can add wallet addresses during signup

### Wallet Management
- **Multi-Wallet Support**: Store multiple blockchain wallet addresses
- **Automatic Detection**: Detects Bitcoin, Ethereum, XRP, and BSC addresses
- **Address Labels**: Optional custom labels for wallet organization
- **CRUD Operations**: Add, edit, and remove wallet addresses
- **Professional UI**: Glass morphism design with animated interactions

### User Experience
- **Professional Design**: Enterprise-grade interface with gradients and animations
- **Mobile Responsive**: Optimized for all device sizes
- **Real-time Validation**: Instant feedback on wallet address formats
- **Copy to Clipboard**: Easy address copying functionality
- **Notifications**: Toast notifications for user actions

### Dashboard Integration
- **Wallet Dashboard**: Visual wallet management directly in the dashboard
- **Chain Detection**: Automatic blockchain type detection with icons
- **Address Preview**: Shortened address display with full address on hover
- **Quick Actions**: Copy, edit, and remove wallet addresses

## API Endpoints

### Wallet Management
- `GET /api/user/wallets` - Get user's wallet addresses
- `POST /api/user/wallets/add` - Add a new wallet address
- `POST /api/user/wallets/update` - Update wallet label
- `POST /api/user/wallets/remove` - Remove a wallet address

### OAuth Authentication
- `GET /auth/oauth/google` - Initiate Google OAuth
- `GET /auth/oauth/google/callback` - Google OAuth callback
- `GET /auth/oauth/microsoft` - Initiate Microsoft OAuth
- `GET /auth/oauth/microsoft/callback` - Microsoft OAuth callback

## Database Schema Extensions

The user table has been extended with:
- `oauth_provider` - OAuth provider (google, microsoft, null)
- `oauth_id` - Unique ID from OAuth provider
- `display_name` - User's display name from OAuth
- `avatar_url` - Profile picture URL from OAuth
- `wallet_addresses` - JSON array of wallet addresses with labels

## Security Notes

- All OAuth tokens are validated server-side
- User sessions use JWT with secure HTTP-only cookies
- Wallet addresses are stored securely in the database
- OAuth providers handle password management
- Users can unlink OAuth accounts (with password requirement)

## Getting Started

1. Set up OAuth credentials (optional - users can still use email/password)
2. Start the application
3. Users can now sign up with:
   - Google account (if configured)
   - Microsoft account (if configured)
   - Email and password (always available)
   - Add wallet addresses during signup or in dashboard

The application maintains backward compatibility - existing users continue to work, and OAuth is an additional convenience feature.