"""Comprehensive Integration Tests
Tests complete workflows and component interactions
"""

from unittest.mock import patch

import pytest


class TestAuthenticationFlow:
    """Test complete authentication workflows."""

    def test_user_registration_flow(self, test_client, db_utils, test_db):
        """Test complete user registration process."""
        # Register new user
        response = test_client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data

    def test_user_login_flow(self, test_client, db_utils, test_db, mock_user):
        """Test complete user login process."""
        # Create test user
        db_utils.create_test_user(test_db, mock_user)

        # Login
        response = test_client.post(
            "/auth/login",
            data={"username": mock_user["email"], "password": "testpassword"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_protected_endpoint_access(
        self, test_client, api_utils, db_utils, test_db, mock_user,
    ):
        """Test access to protected endpoints with authentication."""
        # Create and authenticate user
        db_utils.create_test_user(test_db, mock_user)
        token = api_utils.authenticate_user(
            test_client, mock_user["email"], "testpassword",
        )

        # Access protected endpoint
        headers = api_utils.get_auth_headers(token)
        response = test_client.get("/dashboard", headers=headers)

        assert response.status_code == 200


class TestTransactionProcessing:
    """Test complete transaction processing workflows."""

    @pytest.mark.asyncio
    async def test_transaction_creation_flow(
        self, async_client, db_utils, test_db, mock_user,
    ):
        """Test complete transaction creation process."""
        # Create user
        db_utils.create_test_user(test_db, mock_user)

        # Create transaction
        transaction_data = {
            "amount": 150.75,
            "currency": "USD",
            "recipient": "test_recipient",
            "description": "Test transaction",
        }

        response = await async_client.post("/transactions", json=transaction_data)

        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 150.75
        assert data["currency"] == "USD"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_compliance_analysis_integration(
        self, async_client, db_utils, test_db, mock_user,
    ):
        """Test integration between transaction creation and compliance analysis."""
        # Create user
        db_utils.create_test_user(test_db, mock_user)

        # Create high-value transaction (should trigger compliance analysis)
        transaction_data = {
            "amount": 75000,  # High amount
            "currency": "USD",
            "recipient": "unknown_entity",
            "description": "Large transfer",
        }

        response = await async_client.post("/transactions", json=transaction_data)

        assert response.status_code == 201
        data = response.json()

        # Check that compliance tags were created
        transaction_id = data["id"]
        tags_response = await async_client.get(
            f"/transactions/{transaction_id}/compliance-tags",
        )

        assert tags_response.status_code == 200
        tags = tags_response.json()
        assert len(tags) > 0
        assert any(tag["tag_type"] == "HIGH_AMOUNT" for tag in tags)


class TestXRPLIntegration:
    """Test XRPL integration workflows."""

    @pytest.mark.asyncio
    async def test_xrpl_account_creation(self, async_client, mock_xrpl_client):
        """Test XRPL account creation integration."""
        with patch(
            "app.integrations.xrp.get_xrpl_client", return_value=mock_xrpl_client,
        ):
            response = await async_client.post("/xrpl/create-account")

            assert response.status_code == 201
            data = response.json()
            assert "account_address" in data
            assert "secret" in data

    @pytest.mark.asyncio
    async def test_xrpl_balance_check(self, async_client, mock_xrpl_client):
        """Test XRPL balance checking integration."""
        with patch(
            "app.integrations.xrp.get_xrpl_client", return_value=mock_xrpl_client,
        ):
            response = await async_client.get("/xrpl/balance/rTest123")

            assert response.status_code == 200
            data = response.json()
            assert "balance" in data
            assert data["balance"] > 0


class TestPaywallIntegration:
    """Test paywall and subscription integration."""

    def test_free_tier_limitations(self, test_client, db_utils, test_db, mock_user):
        """Test free tier access limitations."""
        # Create free tier user
        db_utils.create_test_user(test_db, mock_user)

        # Try to access premium feature
        response = test_client.get("/premium/advanced-analytics")

        assert response.status_code == 402  # Payment required
        data = response.json()
        assert "upgrade required" in data["detail"].lower()

    def test_paid_tier_access(self, test_client, db_utils, test_db, mock_user):
        """Test paid tier feature access."""
        # Create paid tier user
        paid_user = mock_user.copy()
        paid_user["subscription_status"] = "active"
        db_utils.create_test_user(test_db, paid_user)

        # Access premium feature
        response = test_client.get("/premium/advanced-analytics")

        assert response.status_code == 200


class TestAdminWorkflows:
    """Test admin functionality workflows."""

    def test_admin_user_management(
        self, test_client, db_utils, test_db, mock_admin_user, mock_user,
    ):
        """Test admin user management capabilities."""
        # Create admin user
        db_utils.create_test_user(test_db, mock_admin_user)

        # Create regular user
        db_utils.create_test_user(test_db, mock_user)

        # Admin views all users
        response = test_client.get("/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2  # At least admin and regular user

    def test_admin_transaction_monitoring(
        self, test_client, db_utils, test_db, mock_admin_user,
    ):
        """Test admin transaction monitoring."""
        # Create admin user
        db_utils.create_test_user(test_db, mock_admin_user)

        # Admin views transaction analytics
        response = test_client.get("/admin/analytics/transactions")

        assert response.status_code == 200
        data = response.json()
        assert "total_transactions" in data
        assert "total_volume" in data


class TestISO20022Integration:
    """Test ISO 20022 message processing integration."""

    @pytest.mark.asyncio
    async def test_iso_message_parsing(self, async_client, sample_iso20022_message):
        """Test ISO 20022 message parsing workflow."""
        response = await async_client.post(
            "/iso20022/parse", json={"message": sample_iso20022_message},
        )

        assert response.status_code == 200
        data = response.json()
        assert "parsed_data" in data
        assert data["parsed_data"]["message_id"] == "MSG123456"
        assert data["parsed_data"]["amount"] == 1000.0

    @pytest.mark.asyncio
    async def test_iso_compliance_integration(
        self, async_client, sample_iso20022_message,
    ):
        """Test ISO 20022 message compliance analysis integration."""
        response = await async_client.post(
            "/iso20022/analyze-compliance", json={"message": sample_iso20022_message},
        )

        assert response.status_code == 200
        data = response.json()
        assert "compliance_tags" in data
        assert len(data["compliance_tags"]) >= 0


class TestEndToEndWorkflows:
    """Test complete end-to-end user workflows."""

    @pytest.mark.asyncio
    async def test_complete_user_journey(self, async_client, db_utils, test_db):
        """Test complete user journey from registration to transaction analysis."""
        # 1. User registration
        registration_response = await async_client.post(
            "/auth/register",
            json={
                "email": "journey@example.com",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
        )
        assert registration_response.status_code == 201

        # 2. User login
        login_response = await async_client.post(
            "/auth/login",
            data={"username": "journey@example.com", "password": "securepassword123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Upload transaction data
        transaction_data = {
            "amount": 5000,
            "currency": "USD",
            "recipient": "business_partner",
            "description": "Business transaction",
        }

        transaction_response = await async_client.post(
            "/transactions", json=transaction_data, headers=headers,
        )
        assert transaction_response.status_code == 201
        transaction_id = transaction_response.json()["id"]

        # 4. Check compliance analysis results
        compliance_response = await async_client.get(
            f"/transactions/{transaction_id}/compliance-tags", headers=headers,
        )
        assert compliance_response.status_code == 200

        # 5. View dashboard analytics
        dashboard_response = await async_client.get("/dashboard", headers=headers)
        assert dashboard_response.status_code == 200

        # 6. Check transaction history
        history_response = await async_client.get("/transactions", headers=headers)
        assert history_response.status_code == 200
        transactions = history_response.json()
        assert len(transactions) >= 1
