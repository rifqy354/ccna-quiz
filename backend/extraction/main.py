"""CLI for EPUB extraction pipeline."""
import argparse
import json
import os
import sqlite3
import sys
import zipfile
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
            correct_option TEXT NOT NULL,
            explanation TEXT NOT NULL,
            ocg_chapter_ref TEXT,
            ocg_section_ref TEXT,
            difficulty INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    return conn


def insert_questions(conn, questions: list[ExtractedQuestion]):
    for q in questions:
        conn.execute("""
            INSERT INTO questions
                (source_book, source_chapter, book_title, domain, sub_domain,
                 sub_domain_name, question_text, question_image, option_a, option_b,
                 option_c, option_d, correct_option, explanation, ocg_chapter_ref,
                 ocg_section_ref, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            q.source_book, q.source_chapter, q.book_title, q.domain, q.sub_domain,
            q.sub_domain_name, q.question_text, q.question_image, q.option_a,
            q.option_b, q.option_c, q.option_d, q.correct_option, q.explanation,
            q.ocg_chapter_ref, q.ocg_section_ref, q.difficulty,
        ))
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Extract CCNA quiz questions from EPUBs")
    parser.add_argument("practice_tests_epub", help="Path to Practice Tests EPUB")
    parser.add_argument("ocg_epub", help="Path to OCG Library EPUB")
    parser.add_argument("--output", default="./data", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Parse but don't write DB")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    db_path = output_dir / "ccna.db"
    conn = create_tables(str(db_path))

    report = {"practice_tests": 0, "ocg_dikta": 0, "errors": []}

    try:
        pt_questions = parse_practice_tests_epub(
            args.practice_tests_epub, str(images_dir)
        )
        if not args.dry_run:
            insert_questions(conn, pt_questions)
        report["practice_tests"] = len(pt_questions)
        print(f"Practice Tests: extracted {len(pt_questions)} questions")
    except Exception as e:
        report["errors"].append(f"Practice Tests: {str(e)}")
        print(f"ERROR parsing Practice Tests: {e}", file=sys.stderr)

    try:
        ocg_questions = parse_ocg_epub(args.ocg_epub, str(images_dir))
        if not args.dry_run:
            insert_questions(conn, ocg_questions)
        report["ocg_dikta"] = len(ocg_questions)
        print(f"OCG Library DIKTA: extracted {len(ocg_questions)} questions")
    except Exception as e:
        report["errors"].append(f"OCG Library: {str(e)}")
        print(f"ERROR parsing OCG Library: {e}", file=sys.stderr)

    cursor = conn.execute("""
        SELECT domain, COUNT(*) FROM questions GROUP BY domain ORDER BY domain
    """)
    print("\nQuestions per domain:")
    for row in cursor.fetchall():
        print(f"  Domain {row[0]}: {row[1]} questions")

    if not args.dry_run:
        conn.close()

    report_path = output_dir / "report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
