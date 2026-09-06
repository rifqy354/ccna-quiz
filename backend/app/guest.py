"""Signed-cookie identity for browser-specific guest players."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from jose import JWTError, jwt

from .config import get_settings
from .database import get_db


def create_player_cookie(public_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": public_id,
        "type": "guest",
        "exp": datetime.now(timezone.utc)
        + timedelta(seconds=settings.PLAYER_COOKIE_MAX_AGE),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def _decode_public_id(cookie: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(
            cookie,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid player identity")

    public_id = payload.get("sub")
    if (
        payload.get("type") != "guest"
        or not isinstance(public_id, str)
        or len(public_id) != 32
        or any(char not in "0123456789abcdef" for char in public_id)
    ):
        raise HTTPException(status_code=401, detail="Invalid player identity")
    return public_id


async def get_current_player(request: Request) -> dict:
    settings = get_settings()
    cookie = request.cookies.get(settings.PLAYER_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=401, detail="Player identity required")

    public_id = _decode_public_id(cookie)
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT u.id, g.public_id, g.display_name AS name
            FROM guest_players g
            JOIN users u ON u.id = g.user_id
            WHERE g.public_id = ?
            """,
            (public_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Player identity not found")
        await db.execute(
            "UPDATE guest_players SET last_seen_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (row["id"],),
        )
        await db.commit()
        return dict(row)
