"""Tests that verify all five database tables are created correctly."""

import pytest
import pytest_asyncio
import aiosqlite
import os
import tempfile
from pathlib import Path


@pytest.fixture
def isolated_db_env(tmp_path: Path, monkeypatch):
    """Patch _resolve_db_path to return a temp file, isolated per test."""
    db_file = str(tmp_path / "test_ccna.db")

    # Patch _resolve_db_path so init_db and get_db both use the temp path
    import app.database as db_module

    monkeypatch.setattr(db_module, "_resolve_db_path", lambda: db_file)

    return db_file


@pytest_asyncio.fixture
async def fresh_db(isolated_db_env: str):
    """Provide a fresh SQLite database file for each test."""
    import app.database as db_module

    db_module._db_path = None  # reset any cached state
    await db_module.init_db()

    yield isolated_db_env


async def table_exists(db_path: str, table: str) -> bool:
    """Return True if the named table exists in the database."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table,),
        )
        row = await cursor.fetchone()
        return row is not None


async def table_columns(db_path: str, table: str) -> list[str]:
    """Return the column names for a table."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(f"PRAGMA table_info({table});")
        rows = await cursor.fetchall()
        return [row["name"] for row in rows]


async def table_index_count(db_path: str, table: str) -> int:
    """Return the number of indexes on a table (excluding auto PK index)."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name = ?",
            (table,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ─── Table existence tests ──────────────────────────────────────────────────────

pytestmark = pytest.mark.asyncio


async def test_users_table_created(fresh_db):
    assert await table_exists(fresh_db, "users")


async def test_questions_table_created(fresh_db):
    assert await table_exists(fresh_db, "questions")


async def test_user_progress_table_created(fresh_db):
    assert await table_exists(fresh_db, "user_progress")


async def test_study_sessions_table_created(fresh_db):
    assert await table_exists(fresh_db, "study_sessions")


async def test_user_responses_table_created(fresh_db):
    assert await table_exists(fresh_db, "user_responses")


# ─── Column schema tests ────────────────────────────────────────────────────────

async def test_users_columns(fresh_db):
    cols = await table_columns(fresh_db, "users")
    expected = {"id", "email", "password_hash", "name", "refresh_token", "created_at"}
    assert set(cols) == expected


async def test_questions_columns(fresh_db):
    cols = await table_columns(fresh_db, "questions")
    expected = {
        "id", "source_book", "source_chapter", "book_title", "domain",
        "sub_domain", "sub_domain_name", "question_text", "question_image",
        "option_a", "option_b", "option_c", "option_d", "correct_option",
        "explanation", "ocg_chapter_ref", "ocg_section_ref", "difficulty",
        "created_at",
    }
    assert set(cols) == expected


async def test_user_progress_columns(fresh_db):
    cols = await table_columns(fresh_db, "user_progress")
    expected = {
        "id", "user_id", "question_id", "attempts", "correct_count",
        "consecutive_correct", "ease_factor", "interval_days",
        "next_review_date", "mastered", "mastered_at", "last_attempt_at",
    }
    assert set(cols) == expected


async def test_study_sessions_columns(fresh_db):
    cols = await table_columns(fresh_db, "study_sessions")
    expected = {
        "id", "user_id", "domain", "session_type", "questions_shown",
        "correct_count", "started_at", "completed_at",
    }
    assert set(cols) == expected


async def test_user_responses_columns(fresh_db):
    cols = await table_columns(fresh_db, "user_responses")
    expected = {
        "id", "user_id", "question_id", "session_id", "selected_option",
        "is_correct", "confidence", "response_time_ms", "answered_at",
    }
    assert set(cols) == expected


# ─── Constraints ──────────────────────────────────────────────────────────────

async def test_users_email_unique(fresh_db):
    """Verify UNIQUE constraint on users.email via a second insert failure."""
    async with aiosqlite.connect(fresh_db) as db:
        await db.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            ("dup@test.com", "hash1", "User One"),
        )
        await db.commit()

        with pytest.raises(Exception):  # integrity error
            await db.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                ("dup@test.com", "hash2", "User Two"),
            )


async def test_user_progress_unique_constraint(fresh_db):
    """Verify UNIQUE(user_id, question_id) via a second insert failure."""
    async with aiosqlite.connect(fresh_db) as db:
        # Insert a question first
        await db.execute(
            "INSERT INTO questions (source_book, source_chapter, book_title, domain, "
            "question_text, option_a, option_b, option_c, option_d, correct_option, "
            "explanation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("test", "ch01", "Test", 1, "Q1", "A", "B", "C", "D", "A", "Expl"),
        )
        # Insert user
        await db.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            ("u@test.com", "h", "U"),
        )
        await db.commit()

        await db.execute(
            "INSERT INTO user_progress (user_id, question_id) VALUES (?, ?)",
            (1, 1),
        )
        await db.commit()

        with pytest.raises(Exception):  # UNIQUE constraint violation
            await db.execute(
                "INSERT INTO user_progress (user_id, question_id) VALUES (?, ?)",
                (1, 1),
            )


async def test_init_db_idempotent(fresh_db):
    """init_db() can be called multiple times without error (CREATE IF NOT EXISTS)."""
    import app.database as db_module

    await db_module.init_db()  # call again — should not raise
    assert await table_exists(fresh_db, "users")
