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
        "email": "qtest@example.com", "password": "testpass1234", "name": "QTest"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "qtest@example.com", "password": "testpass1234"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_domains_requires_auth(client):
    resp = await client.get("/api/domains")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_domains_returns_6_domains(client, auth_headers):
    resp = await client.get("/api/domains", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6
    assert all("domain" in d and "name" in d and "total_questions" in d for d in data)


@pytest.mark.asyncio
async def test_domains_includes_mastery_fields(client, auth_headers):
    resp = await client.get("/api/domains", headers=auth_headers)
    data = resp.json()
    assert all("mastered" in d and "attempted" in d for d in data)


@pytest.mark.asyncio
async def test_random_question_empty_db(client, auth_headers):
    resp = await client.get("/api/questions/random", headers=auth_headers)
    # 404 when DB has no questions is acceptable
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_domain_invalid_id(client, auth_headers):
    resp = await client.get("/api/domains/99", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_random_question_with_domain_filter(client, auth_headers):
    resp = await client.get("/api/questions/random?domain=1", headers=auth_headers)
    assert resp.status_code in (200, 404)
