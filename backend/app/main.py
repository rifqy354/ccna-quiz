"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from .config import get_settings
from .database import init_db
from . import database
from .routers import (
    leaderboard_router,
    player_router,
    questions_router,
    sessions_router,
    stats_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="CCNA Quiz API",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
cors_origins = [
    origin.strip()
    for origin in settings.CORS_ALLOW_ORIGINS.split(",")
    if origin.strip()
]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(player_router)
app.include_router(leaderboard_router)
app.include_router(questions_router)
app.include_router(sessions_router)
app.include_router(stats_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/images/{filename}", include_in_schema=False)
async def question_image(filename: str):
    root = (Path(database._resolve_db_path()).parent / "images").resolve()
    path = (root / filename).resolve()
    if (not path.is_relative_to(root) or not path.is_file()
            or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)
