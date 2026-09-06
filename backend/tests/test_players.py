from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import get_settings
from app.database import get_db
from app.main import app


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as test_client:
        yield test_client


async def test_create_player_sets_secure_cookie_and_returns_public_profile(client):
    response = await client.post("/api/player", json={"name": "  Rifqy  "})

    assert response.status_code == 201
    assert response.json() == {"name": "Rifqy"}
    assert set(response.json()) == {"name"}
    cookie = response.headers["set-cookie"]
    assert "ccna_player=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=31536000" in cookie

    me = await client.get("/api/player/me")
    assert me.status_code == 200
    assert me.json() == {"name": "Rifqy"}


async def test_local_player_cookie_can_be_sent_over_http(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.players.get_settings",
        lambda: SimpleNamespace(
            PLAYER_COOKIE_NAME="ccna_player",
            PLAYER_COOKIE_MAX_AGE=31_536_000,
            PLAYER_COOKIE_DOMAIN=None,
            PLAYER_COOKIE_SECURE=False,
        ),
    )

    response = await client.post("/api/player", json={"name": "Local Player"})

    assert response.status_code == 201
    assert "Secure" not in response.headers["set-cookie"]


async def test_duplicate_display_names_create_distinct_players(client):
    first = await client.post("/api/player", json={"name": "Player"})
    first_cookie = first.cookies["ccna_player"]
    second = await client.post("/api/player", json={"name": "Player"})

    assert second.status_code == 201
    assert second.cookies["ccna_player"] != first_cookie
    async with get_db() as db:
        count = await (
            await db.execute(
                "SELECT COUNT(*) FROM guest_players WHERE display_name='Player'"
            )
        ).fetchone()
    assert count[0] == 2


@pytest.mark.parametrize(
    "name",
    ["", "A", "A" * 25, "A\nB", "A\x00B", " \t "],
)
async def test_create_player_rejects_invalid_names(client, name):
    response = await client.post("/api/player", json={"name": name})
    assert response.status_code == 422


async def test_me_requires_player_cookie(client):
    response = await client.get("/api/player/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Player identity required"


async def test_tampered_player_cookie_is_rejected(client):
    await client.post("/api/player", json={"name": "Player"})
    client.cookies.set("ccna_player", "not-a-signed-cookie")

    response = await client.get("/api/player/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid player identity"


async def test_expired_player_cookie_is_rejected(client):
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": "a" * 32,
            "type": "guest",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    client.cookies.set("ccna_player", expired)

    response = await client.get("/api/player/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid player identity"


async def test_unknown_player_identity_is_rejected(client):
    settings = get_settings()
    unknown = jwt.encode(
        {
            "sub": "a" * 32,
            "type": "guest",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    client.cookies.set("ccna_player", unknown)

    response = await client.get("/api/player/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Player identity not found"


async def test_player_creation_uses_inaccessible_internal_credentials(client):
    response = await client.post("/api/player", json={"name": "Guest Name"})
    assert response.status_code == 201

    async with get_db() as db:
        row = await (
            await db.execute(
                "SELECT u.email,u.password_hash,u.name,g.public_id,g.display_name "
                "FROM users u JOIN guest_players g ON g.user_id=u.id"
            )
        ).fetchone()
    assert row["email"].startswith("guest-")
    assert row["email"].endswith("@internal.invalid")
    assert row["password_hash"].startswith("$2")
    assert row["name"] == "Guest Name"
    assert row["display_name"] == "Guest Name"
    assert len(row["public_id"]) == 32
