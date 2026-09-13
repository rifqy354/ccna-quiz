"""Create and resolve browser-specific guest players."""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Response, status

from ..auth import get_password_hash
from ..config import get_settings
from ..database import get_db
from ..guest import create_player_cookie, get_current_player
from ..models import PlayerCreate, PlayerResponse


router = APIRouter(prefix="/api/player", tags=["player"])


@router.post("", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
async def create_player(data: PlayerCreate, response: Response):
    settings = get_settings()
    public_id = uuid4().hex
    password_hash = get_password_hash(secrets.token_urlsafe(32))

    async with get_db() as db:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "INSERT INTO users(email,password_hash,name) VALUES(?,?,?)",
            (f"guest-{public_id}@internal.invalid", password_hash, data.name),
        )
        user_id = cursor.lastrowid
        await db.execute(
            "INSERT INTO guest_players(user_id,public_id,display_name) VALUES(?,?,?)",
            (user_id, public_id, data.name),
        )
        await db.commit()

    response.set_cookie(
        key=settings.PLAYER_COOKIE_NAME,
        value=create_player_cookie(public_id),
        max_age=settings.PLAYER_COOKIE_MAX_AGE,
        expires=datetime.now(timezone.utc)
        + timedelta(seconds=settings.PLAYER_COOKIE_MAX_AGE),
        secure=settings.PLAYER_COOKIE_SECURE,
        httponly=True,
        samesite=settings.PLAYER_COOKIE_SAMESITE,
        domain=settings.PLAYER_COOKIE_DOMAIN,
        path="/",
    )
    return PlayerResponse(name=data.name)


@router.get("/me", response_model=PlayerResponse)
async def current_player(player: dict = Depends(get_current_player)):
    return PlayerResponse(name=player["name"])
