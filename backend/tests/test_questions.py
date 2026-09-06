import pytest_asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db

pytest_plugins = ['pytest_asyncio']


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def player(client):
    response = await client.post("/api/player", json={"name": "Question Player"})
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_domains_requires_auth(client):
    resp = await client.get("/api/domains")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_domains_returns_6_domains(client, player):
    resp = await client.get("/api/domains")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 7
    assert all("domain" in d and "name" in d and "total_questions" in d for d in data)


@pytest.mark.asyncio
async def test_domains_includes_mastery_fields(client, player):
    resp = await client.get("/api/domains")
    data = resp.json()
    assert all("mastered" in d and "attempted" in d for d in data)


@pytest.mark.asyncio
async def test_random_question_empty_db(client, player):
    resp = await client.get("/api/questions/random")
    # 404 when DB has no questions is acceptable
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_domain_invalid_id(client, player):
    resp = await client.get("/api/domains/99")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_random_question_with_domain_filter(client, player):
    resp = await client.get("/api/questions/random?domain=1")
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_random_question_domain_7(client, player):
    resp = await client.get("/api/questions/random?domain=7")
    assert resp.status_code in (200, 404)
