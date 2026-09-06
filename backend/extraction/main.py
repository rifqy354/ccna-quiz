"""CLI for EPUB extraction pipeline."""
import argparse
import json
import sqlite3
import sys
import shutil
import tempfile
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extraction.models import ExtractedQuestion
from extraction.practice_tests import parse_practice_tests_epub
from extraction.ocg_parser import parse_ocg_epub


def create_tables(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_book TEXT NOT NULL,
            source_chapter TEXT NOT NULL,
            book_title TEXT NOT NULL,
            domain INTEGER,
            sub_domain TEXT,
            sub_domain_name TEXT,
            question_text TEXT NOT NULL,
            question_image TEXT,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            option_e TEXT,
            option_f TEXT,
            option_g TEXT,
            correct_option TEXT NOT NULL,
            explanation TEXT NOT NULL,
            ocg_chapter_ref TEXT,
            ocg_section_ref TEXT,
            difficulty INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # CREATE IF NOT EXISTS does not upgrade an existing question bank.
    conn.execute("BEGIN IMMEDIATE")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(questions)")}
    for column in ("option_e", "option_f", "option_g"):
        if column not in columns:
            conn.execute(f"ALTER TABLE questions ADD COLUMN {column} TEXT")
    conn.commit()
    return conn


def insert_questions(conn, questions: list[ExtractedQuestion]):
    for q in questions:
        conn.execute("""
            INSERT INTO questions
                (source_book, source_chapter, book_title, domain, sub_domain,
                 sub_domain_name, question_text, question_image, option_a, option_b,
                 option_c, option_d, option_e, option_f, option_g, correct_option,
                 explanation, ocg_chapter_ref, ocg_section_ref, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            q.source_book, q.source_chapter, q.book_title, q.domain, q.sub_domain,
            q.sub_domain_name, q.question_text, q.question_image, q.option_a,
            q.option_b, q.option_c, q.option_d, q.option_e, q.option_f, q.option_g,
            q.correct_option, q.explanation, q.ocg_chapter_ref, q.ocg_section_ref,
            q.difficulty,
        ))
    conn.commit()


def backfill_options(conn, questions: list[ExtractedQuestion]) -> int:
    """Fill E–G from a complete source reparse, preserving IDs and history.

    Reject ambiguous identities, incomplete parses, changed A–D content, and
    invalid answer keys before writing. The entire update is one transaction.
    """
    parsed = {}
    for q in questions:
        key = (q.source_book, q.ocg_chapter_ref, q.sub_domain)
        if not q.sub_domain or key in parsed:
            raise ValueError(f"Missing or duplicate source identity: {key}")
        if not q.correct_option or any(
            letter not in "ABCDEFG" or not getattr(q, f"option_{letter.lower()}").strip()
            for letter in q.correct_option
        ):
            raise ValueError(f"Answer key references a missing or unsupported option: {key}")
        parsed[key] = q
    if not parsed:
        raise ValueError("No questions parsed; refusing backfill")

    with conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute("SELECT * FROM questions")
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        keys = [(r["source_book"], r["ocg_chapter_ref"], r["sub_domain"]) for r in rows]
        if len(set(keys)) != len(keys) or set(keys) != set(parsed):
            raise ValueError("Database and parsed source identities do not match exactly")

        updates = []
        for key, row in zip(keys, rows):
            q = parsed[key]
            for field in ("question_text", "correct_option", "option_a", "option_b", "option_c", "option_d"):
                if row[field] != getattr(q, field):
                    raise ValueError(f"Existing {field} differs from source: {key}")
            values = tuple(getattr(q, f"option_{letter}") for letter in "efg")
            old = tuple(row[f"option_{letter}"] or "" for letter in "efg")
            if any(previous and previous != value for previous, value in zip(old, values)):
                raise ValueError(f"Existing E–G options differ from source: {key}")
            if old != values:
                updates.append((*values, row["id"]))
        conn.executemany(
            "UPDATE questions SET option_e = ?, option_f = ?, option_g = ? WHERE id = ?",
            updates,
        )
    return len(updates)


def _validated_questions(questions):
    parsed = {}
    for question in questions:
        key = (question.source_book, question.ocg_chapter_ref, question.sub_domain)
        if not question.source_book or not question.sub_domain or key in parsed:
            raise ValueError(f"Missing or duplicate source identity: {key}")
        if not question.correct_option or any(
            letter not in "ABCDEFG" or not (getattr(question, f"option_{letter.lower()}") or "").strip()
            for letter in question.correct_option
        ):
            raise ValueError(f"Answer key references a missing or unsupported option: {key}")
        parsed[key] = question
    if not parsed:
        raise ValueError("No questions parsed; refusing import")
    return parsed


def import_questions(conn, questions):
    """Replace source content in place without replacing IDs or learner history."""
    parsed = _validated_questions(questions)
    names = [field.name for field in fields(ExtractedQuestion)]
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = {}
        for row in conn.execute("SELECT id, source_book, ocg_chapter_ref, sub_domain FROM questions"):
            key = tuple(row[1:])
            if not key[0] or not key[2] or key in existing:
                raise ValueError(f"Missing or duplicate database source identity: {key}")
            existing[key] = row[0]
        for key, question in parsed.items():
            values = [getattr(question, name) for name in names]
            if key in existing:
                conn.execute(
                    "UPDATE questions SET " + ", ".join(f"{name} = ?" for name in names) + " WHERE id = ?",
                    values + [existing[key]],
                )
            else:
                conn.execute(
                    "INSERT INTO questions (" + ", ".join(names) + ") VALUES (" + ", ".join("?" for _ in names) + ")",
                    values,
                )


def main():
    parser = argparse.ArgumentParser(description="Extract CCNA quiz questions from EPUBs")
    parser.add_argument("practice_tests_epub", help="Path to Practice Tests EPUB")
    parser.add_argument("ocg_epub", help="Path to OCG Library EPUB")
    parser.add_argument("--output", default="./data", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate without writing output")
    args = parser.parse_args()
    report = {"practice_tests": 0, "ocg_dikta": 0, "errors": []}
    try:
        with tempfile.TemporaryDirectory(prefix="ccna-extraction-") as staging:
            images_dir = Path(staging) / "images"
            images_dir.mkdir()
            pt_questions = parse_practice_tests_epub(args.practice_tests_epub, str(images_dir))
            ocg_questions = parse_ocg_epub(args.ocg_epub, str(images_dir))
            report.update(practice_tests=len(pt_questions), ocg_dikta=len(ocg_questions))
            if not pt_questions or not ocg_questions:
                raise ValueError("Both EPUB sources must contain questions; refusing incomplete import")
            questions = pt_questions + ocg_questions
            _validated_questions(questions)
            if not args.dry_run:
                output_dir = Path(args.output)
                output_dir.mkdir(parents=True, exist_ok=True)
                conn = create_tables(str(output_dir / "ccna.db"))
                try:
                    import_questions(conn, questions)
                finally:
                    conn.close()
                shutil.copytree(images_dir, output_dir / "images", dirs_exist_ok=True)
                (output_dir / "report.json").write_text(json.dumps(report, indent=2))
    except Exception as exc:
        report["errors"].append(str(exc))
        print(f"ERROR extracting EPUBs: {exc}", file=sys.stderr)
        print(json.dumps(report, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
