"""Authentication router — register, login, refresh, me."""
from sqlite3 import IntegrityError
from fastapi import APIRouter, HTTPException, Depends
from ..models import UserCreate, UserLogin, UserResponse, TokenResponse, RefreshRequest
from ..auth import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token, decode_token, get_current_user, token_user_id
)
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE email = ?", (data.email,)
        )
        if await cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = get_password_hash(data.password)
        try:
            cursor = await db.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                (data.email, hashed, data.name),
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Email already registered")
        user_id = cursor.lastrowid

        cursor = await db.execute(
            "SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (data.email,)
        )
        row = await cursor.fetchone()
        if not row or not verify_password(data.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id = row["id"]
        access = create_access_token({"sub": str(user_id)})
        refresh = create_refresh_token({"sub": str(user_id)})

        await db.execute(
            "UPDATE users SET refresh_token = ? WHERE id = ?", (refresh, user_id)
        )
        await db.commit()

        return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = token_user_id(payload)

    async with get_db() as db:
        access = create_access_token({"sub": str(user_id)})
        new_refresh = create_refresh_token({"sub": str(user_id)})
        # Compare and replace atomically so concurrent requests cannot reuse a token.
        cursor = await db.execute(
            "UPDATE users SET refresh_token = ? WHERE id = ? AND refresh_token = ?",
            (new_refresh, user_id, data.refresh_token),
        )
        if cursor.rowcount != 1:
            raise HTTPException(status_code=401, detail="Refresh token revoked")
        await db.commit()

        return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)
