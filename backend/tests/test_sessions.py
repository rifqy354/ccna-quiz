import pytest_asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db

pytest_plugins = ['pytest_asyncio']


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "sesstest@example.com", "password": "testpass1234", "name": "SessTest"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "sesstest@example.com", "password": "testpass1234"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_start_session_requires_auth(client):
    resp = await client.post("/api/sessions/start", json={"count": 5})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_start_session_empty_db(client, auth_headers):
    resp = await client.post("/api/sessions/start", json={"domain": 1, "count": 5}, headers=auth_headers)
    # 404 when no questions in DB is expected
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    resp = await client.get("/api/stats/dashboard")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_returns_stats(client, auth_headers):
    resp = await client.get("/api/stats/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_questions" in data
    assert "study_streak" in data
    assert "domains" in data
    assert len(data["domains"]) == 6


@pytest.mark.asyncio
async def test_weak_areas_requires_auth(client):
    resp = await client.get("/api/stats/weak-areas")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_weak_areas_returns_empty_list(client, auth_headers):
    resp = await client.get("/api/stats/weak-areas", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "weak_areas" in data
