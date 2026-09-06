"""Back up an existing bank and fill E–G without replacing question records."""
import argparse
import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .main import backfill_options, create_tables
from .ocg_parser import parse_ocg_epub
from .practice_tests import parse_practice_tests_epub


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("practice_tests_epub")
    parser.add_argument("ocg_epub")
    args = parser.parse_args()
    database = args.database.resolve(strict=True)

    # Parsing images into a temporary directory keeps existing image paths intact.
    with tempfile.TemporaryDirectory() as images:
        questions = parse_practice_tests_epub(args.practice_tests_epub, images)
        questions += parse_ocg_epub(args.ocg_epub, images)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = database.with_name(f"{database.name}.pre-option-backfill-{timestamp}.bak")
    with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)) as source:
        with closing(sqlite3.connect(backup)) as destination:
            source.backup(destination)

    with closing(create_tables(str(database))) as conn:
        updated = backfill_options(conn, questions)
        counts = dict(conn.execute("SELECT source_book, COUNT(*) FROM questions GROUP BY source_book"))
        options = {
            letter.upper(): conn.execute(
                f"SELECT COUNT(*) FROM questions WHERE TRIM(COALESCE(option_{letter}, '')) != ''"
            ).fetchone()[0]
            for letter in "efg"
        }
    print(json.dumps({"backup": str(backup), "updated_questions": updated,
                      "questions_by_source": counts, "populated_options": options}, indent=2))


if __name__ == "__main__":
    main()
