"""JWT and password utilities."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import get_settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain: str, hashed: str) -> bool:
    if len(plain.encode("utf-8")) > 72 or "\x00" in plain:
        return False
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    if len(password.encode("utf-8")) > 72 or "\x00" in password:
        raise HTTPException(status_code=422, detail="Password must be at most 72 UTF-8 bytes and contain no null characters")
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid4().hex})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def token_user_id(payload: dict) -> int:
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal() or len(subject) > 19:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = int(subject)
    if not 1 <= user_id <= 2**63 - 1:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = token_user_id(payload)

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, email, name, created_at FROM users WHERE id = ?", (int(user_id),)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        return dict(row)
