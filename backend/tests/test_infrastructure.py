"""Runtime paths and diagram serving must work outside the repository checkout."""
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app import config, database
from app.main import app


@pytest.mark.parametrize("prefix", ["sqlite:///", "sqlite+aiosqlite:///"])
def test_absolute_sqlite_url_preserves_absolute_path(prefix, tmp_path, monkeypatch):
    target = tmp_path / "external.db"
    monkeypatch.setattr(config, "_settings", config.Settings(_env_file=None, DATABASE_URL=prefix + str(target)))
    assert database._resolve_db_path() == str(target)


async def test_diagram_is_served_from_bank_image_directory(tmp_path):
    images = Path(database._resolve_db_path()).parent / "images"
    images.mkdir()
    content = b"\x89PNG\r\n\x1a\nexample"
    (images / "diagram.png").write_bytes(content)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/images/diagram.png")
        assert response.status_code == 200
        assert response.content == content
        assert response.headers["content-type"] == "image/png"


async def test_diagrams_cannot_serve_database_or_external_symlink(tmp_path):
    images = Path(database._resolve_db_path()).parent / "images"
    images.mkdir()
    (images / "escape.png").symlink_to(Path(database._resolve_db_path()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ["escape.png", "missing.png", "..%2Fapplication.db"]:
            assert (await client.get("/api/images/" + path)).status_code == 404
