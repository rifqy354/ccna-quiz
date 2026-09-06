"""Every backend test uses a disposable bank, never the user's data file."""
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def isolated_application(tmp_path, monkeypatch):
    from app import config, database
    from app.routers import sessions

    monkeypatch.setattr(config, "_settings", config.Settings(
        _env_file=None, DATABASE_URL=str(tmp_path / "application.db"),
        JWT_SECRET_KEY="test-only-secret",
    ))
    monkeypatch.setattr(sessions, "_session_cache", {})
    await database.init_db()
    async with database.get_db() as db:
        await db.executemany(
            "INSERT INTO questions(source_book,source_chapter,book_title,domain,sub_domain,"
            "sub_domain_name,question_text,option_a,option_b,option_c,option_d,option_e,option_f,"
            "correct_option,explanation) VALUES('test','ch1','Test bank',?,?,'Topic',"
            "'Choose an answer','a','b','c','d','e','f',?,'Test explanation')",
            [(domain, f"topic-{domain}", "AF" if domain == 1 else "B") for domain in range(1, 8)],
        )
        await db.commit()
