import pytest_asyncio
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db

pytest_plugins = ['pytest_asyncio']


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    from app import database
    monkeypatch.setattr(database, "_resolve_db_path", lambda: str(tmp_path / "auth.db"))
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    # Clean up any stale test user first
    await client.post("/api/auth/register", json={
        "email": "authtest@example.com", "password": "testpass1234", "name": "AuthTest"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "authtest@example.com", "password": "testpass1234"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register(client):
    uid = uuid.uuid4().hex[:12]
    email = f"newuser-{uid}@example.com"
    resp = await client.post("/api/auth/register", json={
        "email": email, "password": "securepass123", "name": "New User"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email
    assert data["name"] == "New User"
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/auth/register", json={
        "email": "dup@example.com", "password": "pass12345678", "name": "User1"
    })
    resp = await client.post("/api/auth/register", json={
        "email": "dup@example.com", "password": "pass12345678", "name": "User2"
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/auth/register", json={
        "email": "login@example.com", "password": "correctpass1", "name": "Login"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "login@example.com", "password": "correctpass1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={
        "email": "wrong@example.com", "password": "correctpass1", "name": "Wrong"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "wrong@example.com", "password": "wrongpass"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post("/api/auth/login", json={
        "email": "nobody@example.com", "password": "anypass123"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_with_auth(client, auth_headers):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "authtest@example.com"
    assert data["name"] == "AuthTest"


@pytest.mark.asyncio
async def test_refresh_token(client):
    await client.post("/api/auth/register", json={
        "email": "refresh@example.com", "password": "testpass1234", "name": "Refresh"
    })
    login = await client.post("/api/auth/login", json={
        "email": "refresh@example.com", "password": "testpass1234"
    })
    refresh = login.json()["refresh_token"]
    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
@pytest.mark.parametrize('password', ['a' * 73, 'é' * 37, 'abcdefgh\x00'])
async def test_register_rejects_unsupported_password(client, password):
    response = await client.post('/api/auth/register', json={
        'email': 'length@example.com', 'password': password, 'name': 'Length'
    })
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize('subject', [None, 'abc', '1.5', '999999999999999999999999'])
async def test_invalid_token_subject_is_unauthorized(client, subject):
    from app.auth import create_access_token, create_refresh_token
    response = await client.get('/api/auth/me', headers={
        'Authorization': 'Bearer ' + create_access_token({'sub': subject})
    })
    assert response.status_code == 401
    response = await client.post('/api/auth/refresh', json={
        'refresh_token': create_refresh_token({'sub': subject})
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotation_cannot_reuse_previous_token(client):
    await client.post('/api/auth/register', json={
        'email': 'rotation@example.com', 'password': 'password123', 'name': 'Rotation'
    })
    login = await client.post('/api/auth/login', json={
        'email': 'rotation@example.com', 'password': 'password123'
    })
    original = login.json()['refresh_token']
    rotated = await client.post('/api/auth/refresh', json={'refresh_token': original})
    assert rotated.status_code == 200
    assert rotated.json()['refresh_token'] != original
    replay = await client.post('/api/auth/refresh', json={'refresh_token': original})
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_concurrent_refresh_only_one_succeeds(client):
    import asyncio
    await client.post('/api/auth/register', json={
        'email': 'concurrent@example.com', 'password': 'password123', 'name': 'Concurrent'
    })
    login = await client.post('/api/auth/login', json={
        'email': 'concurrent@example.com', 'password': 'password123'
    })
    token = login.json()['refresh_token']
    responses = await asyncio.gather(*[
        client.post('/api/auth/refresh', json={'refresh_token': token}) for _ in range(2)
    ])
    assert sorted(response.status_code for response in responses) == [200, 401]


@pytest.mark.asyncio
async def test_concurrent_duplicate_registration(client):
    import asyncio
    responses = await asyncio.gather(*[
        client.post('/api/auth/register', json={
            'email': 'race@example.com', 'password': 'password123', 'name': 'Race'
        }) for _ in range(2)
    ])
    assert sorted(response.status_code for response in responses) == [201, 400]


@pytest.mark.asyncio
async def test_login_does_not_truncate_password(client):
    await client.post('/api/auth/register', json={
        'email': 'truncate@example.com', 'password': 'a' * 72, 'name': 'Truncate'
    })
    for password in ['a' * 73, 'abcdefgh\x00']:
        response = await client.post('/api/auth/login', json={
            'email': 'truncate@example.com', 'password': password
        })
        assert response.status_code == 401
