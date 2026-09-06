"""Exercise real EPUB parsers and their SQLite storage boundary."""
import sqlite3
import zipfile
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from backend.extraction.main import create_tables, insert_questions
from backend.extraction.ocg_parser import parse_ocg_epub
from backend.extraction.practice_tests import parse_practice_tests_epub


def write_epub(path, files):
    with zipfile.ZipFile(path, "w") as archive:
        for name, body in files.items():
            archive.writestr(name, f"<html><body>{body}</body></html>")
    return str(path)


@pytest.fixture
def ocg_epub(tmp_path):
    options = "".join(f'<p class="alpha">Choice {letter}</p>' for letter in "ABCDEFG")
    return write_epub(tmp_path / "ocg.epub", {
        "OEBPS/xhtml/vol1_ch01.xhtml": '<p class="quiz"><b>1</b>. First?</p>' + options,
        "OEBPS/xhtml/vol1_ch02.xhtml": '<p class="quiz"><b>1</b>. Second?</p>' + options,
        "OEBPS/xhtml/vol1_appc.xhtml": (
            '<p class="quiz"><a id="ques1_1">1</a>. D and F. First explanation.</p>'
            '<p class="quiz"><a id="ques2_1">1</a>. B, E, and G. Second explanation.</p>'
        ),
    })


@pytest.fixture
def pt_epub(tmp_path):
    options = '<ol class="upper-alpha">' + "".join(
        f"<li>Choice {letter}</li>" for letter in "ABCDEFG"
    ) + "</ol>"
    return write_epub(tmp_path / "pt.epub", {
        "OEBPS/c01.xhtml": '<h1>Network Fundamentals</h1><ol>'
        '<li id="c01-ex-0001">First?' + options + '</li>'
        '<li id="c01-ex-0003">Second?' + options + '</li></ol>',
        "OEBPS/b01.xhtml": '<ol><li><b>E</b>. First explanation.</li>'
        '<li><b>G</b>. Second explanation.</li></ol>',
    })


@pytest.mark.parametrize("source", ["ocg", "pt"])
def test_epub_options_and_answer_alignment_survive_storage(source, request, tmp_path):
    epub = request.getfixturevalue(source + "_epub")
    parser = parse_ocg_epub if source == "ocg" else parse_practice_tests_epub
    questions = parser(epub, str(tmp_path / "images"))
    assert len(questions) == 2
    assert [q.correct_option for q in questions] == (["DF", "BEG"] if source == "ocg" else ["E", "G"])
    with create_tables(str(tmp_path / "quiz.db")) as conn:
        insert_questions(conn, questions)
        rows = conn.execute("SELECT option_e, option_f, option_g FROM questions ORDER BY id").fetchall()
        assert rows == [("Choice E", "Choice F", "Choice G")] * 2


def test_extraction_upgrades_legacy_schema_without_losing_rows(tmp_path):
    path = str(tmp_path / "legacy.db")
    conn = create_tables(path)
    for letter in "efg":
        conn.execute(f"ALTER TABLE questions DROP COLUMN option_{letter}")
    conn.execute("INSERT INTO questions (id, source_book, source_chapter, book_title, question_text, "
                 "option_a, option_b, option_c, option_d, correct_option, explanation) "
                 "VALUES (42, 'test', 'ch1', 'Book', 'Question?', 'a', 'b', 'c', 'd', 'A', 'Why')")
    conn.commit()
    conn.close()
    for _ in range(2):
        conn = create_tables(path)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(questions)")}
        assert {"option_e", "option_f", "option_g"} <= columns
        assert conn.execute("SELECT id, question_text FROM questions").fetchall() == [(42, "Question?")]
        conn.close()


def test_backfill_cli_migrates_and_backs_up_legacy_bank(pt_epub, ocg_epub, tmp_path):
    questions = parse_practice_tests_epub(pt_epub, str(tmp_path / "images"))
    questions += parse_ocg_epub(ocg_epub, str(tmp_path / "images"))
    database = tmp_path / "legacy.db"
    conn = create_tables(str(database))
    insert_questions(conn, questions)
    for letter in "efg":
        conn.execute(f"ALTER TABLE questions DROP COLUMN option_{letter}")
    conn.commit()
    before = conn.execute("SELECT * FROM questions ORDER BY id").fetchall()
    conn.close()
    result = subprocess.run(
        [sys.executable, "-m", "backend.extraction.backfill", str(database), pt_epub, ocg_epub],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True,
    )
    report = json.loads(result.stdout)
    assert report["updated_questions"] == 4
    assert report["populated_options"] == {"E": 4, "F": 4, "G": 4}
    with sqlite3.connect(report["backup"]) as backup:
        assert backup.execute("SELECT * FROM questions ORDER BY id").fetchall() == before
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT id, option_g FROM questions ORDER BY id").fetchall() == [
            (1, "Choice G"), (2, "Choice G"), (3, "Choice G"), (4, "Choice G"),
        ]


def test_source_epubs_have_complete_answer_options(tmp_path):
    """Opt-in real-book integration; EPUBs are not redistributed in the repo."""
    pt = os.environ.get("CCNA_PT_EPUB")
    ocg = os.environ.get("CCNA_OCG_EPUB")
    if not pt or not ocg:
        pytest.skip("Set CCNA_PT_EPUB and CCNA_OCG_EPUB to run the real-book audit")
    questions = parse_practice_tests_epub(pt, str(tmp_path / "images"))
    assert len(questions) == 1203
    ocg_questions = parse_ocg_epub(ocg, str(tmp_path / "images"))
    assert len(ocg_questions) == 343
    questions += ocg_questions
    assert [sum(bool(getattr(q, "option_" + letter)) for q in questions) for letter in "efg"] == [88, 31, 17]
    for q in questions:
        assert q.correct_option
        assert all(letter in "ABCDEFG" and getattr(q, "option_" + letter.lower()).strip()
                   for letter in q.correct_option), (q.source_book, q.sub_domain, q.correct_option)


def test_backfill_preserves_ids_history_and_is_repeatable(ocg_epub, tmp_path):
    from backend.extraction.main import backfill_options

    questions = parse_ocg_epub(ocg_epub, str(tmp_path / "images"))
    conn = create_tables(str(tmp_path / "backfill.db"))
    conn.execute("PRAGMA foreign_keys = ON")
    insert_questions(conn, [replace(q, option_e="", option_f="", option_g="") for q in questions])
    conn.execute("CREATE TABLE history (question_id INTEGER REFERENCES questions(id), selection TEXT)")
    conn.execute("INSERT INTO history VALUES (1, 'DF')")
    conn.commit()
    assert backfill_options(conn, questions) == 2
    assert backfill_options(conn, questions) == 0
    assert conn.execute("SELECT id, option_g FROM questions ORDER BY id").fetchall() == [(1, "Choice G"), (2, "Choice G")]
    assert conn.execute("SELECT * FROM history").fetchall() == [(1, "DF")]
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


@pytest.mark.parametrize("problem", ["missing_option", "missing_question", "duplicate_key", "changed_text"])
def test_backfill_rejects_invalid_or_unmatched_data_atomically(problem, ocg_epub, tmp_path):
    from backend.extraction.main import backfill_options

    questions = parse_ocg_epub(ocg_epub, str(tmp_path / "images"))
    conn = create_tables(str(tmp_path / "backfill.db"))
    insert_questions(conn, [replace(q, option_e="", option_f="", option_g="") for q in questions])
    before = conn.execute("SELECT * FROM questions ORDER BY id").fetchall()
    if problem == "missing_option":
        questions[1] = replace(questions[1], option_g="")
    elif problem == "missing_question":
        questions.pop()
    elif problem == "duplicate_key":
        questions.append(questions[0])
    else:
        questions[1] = replace(questions[1], question_text="Different question")
    with pytest.raises(ValueError):
        backfill_options(conn, questions)
    assert conn.execute("SELECT * FROM questions ORDER BY id").fetchall() == before
    conn.close()
