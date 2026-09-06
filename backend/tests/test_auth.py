import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


pytestmark = pytest.mark.asyncio


async def test_legacy_auth_routes_are_not_mounted():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as client:
        responses = [
            await client.post("/api/auth/register", json={}),
            await client.post("/api/auth/login", json={}),
            await client.post("/api/auth/refresh", json={}),
            await client.get("/api/auth/me"),
        ]
        assert [response.status_code for response in responses] == [404, 404, 404, 404]
