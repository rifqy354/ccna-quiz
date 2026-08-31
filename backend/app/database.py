"""Async SQLite connection management and database initialization.

Tables created by init_db():
  1. users
  2. questions
  3. user_progress
  4. study_sessions
  5. user_responses
"""

import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from .config import get_settings

_db_path: str | None = None


def _resolve_db_path() -> str:
    """Return the absolute path to the SQLite database file."""
    settings = get_settings()
    url = settings.DATABASE_URL  # e.g. sqlite+aiosqlite:///data/ccna.db

    # Strip the aiosqlite driver prefix for aiosqlite.connect()
    if url.startswith("sqlite+aiosqlite:///"):
        path = url.removeprefix("sqlite+aiosqlite:///").lstrip("/")
    elif url.startswith("sqlite:///"):
        path = url.removeprefix("sqlite:///").lstrip("/")
    else:
        path = url

    # Make relative paths absolute relative to the project root
    if not path.startswith("/"):
        root = Path(__file__).parent.parent.parent  # backend/ -> ccna-quiz/
        path = str(root / path)

    return path


async def init_db() -> None:
    """Create all five tables if they do not already exist."""

    db_path = _resolve_db_path()
    # Ensure the parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        # Enable foreign-key enforcement
        await db.execute("PRAGMA foreign_keys = ON;")

        # ── users ──────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name          TEXT NOT NULL,
                refresh_token TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ── questions ──────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                source_book     TEXT NOT NULL,
                source_chapter  TEXT NOT NULL,
                book_title      TEXT NOT NULL,
                domain          INTEGER NOT NULL,
                sub_domain      TEXT,
                sub_domain_name TEXT,
                question_text   TEXT NOT NULL,
                question_image  TEXT,
                option_a        TEXT NOT NULL,
                option_b        TEXT NOT NULL,
                option_c        TEXT NOT NULL,
                option_d        TEXT NOT NULL,
                correct_option  TEXT NOT NULL,
                explanation     TEXT NOT NULL,
                ocg_chapter_ref TEXT,
                ocg_section_ref TEXT,
                difficulty      INTEGER DEFAULT 2,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ── user_progress (SR state) ────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER NOT NULL,
                question_id         INTEGER NOT NULL,
                attempts            INTEGER DEFAULT 0,
                correct_count       INTEGER DEFAULT 0,
                consecutive_correct INTEGER DEFAULT 0,
                ease_factor         REAL DEFAULT 2.5,
                interval_days       INTEGER DEFAULT 1,
                next_review_date    DATE,
                mastered            INTEGER DEFAULT 0,
                mastered_at         TIMESTAMP,
                last_attempt_at     TIMESTAMP,
                UNIQUE(user_id, question_id),
                FOREIGN KEY (user_id)     REFERENCES users(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );
        """)

        # ── study_sessions ─────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                domain          INTEGER,
                session_type    TEXT NOT NULL,
                questions_shown INTEGER DEFAULT 0,
                correct_count   INTEGER DEFAULT 0,
                started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at    TIMESTAMP
            );
        """)

        # ── user_responses ─────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_responses (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                question_id     INTEGER NOT NULL REFERENCES questions(id),
                session_id      INTEGER REFERENCES study_sessions(id),
                selected_option TEXT NOT NULL,
                is_correct      INTEGER NOT NULL,
                confidence      TEXT NOT NULL,
                response_time_ms INTEGER,
                answered_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.commit()


@asynccontextmanager
async def get_db():
    """Async context manager that yields a connection with row-dict factory.

    Usage:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (1,))
            row = await cursor.fetchone()
            print(dict(row))
    """
    db_path = _resolve_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db
