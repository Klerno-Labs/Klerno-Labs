
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from app.main import app

@pytest.mark.asyncio


async def test_error_handling():
    transport=ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response=await ac.get("/render - test / error")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Test error for Render deployment"
