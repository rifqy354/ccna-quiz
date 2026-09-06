"""Run the real extraction command on synthetic EPUB archives only."""
import json
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

CLI = Path(__file__).resolve().parents[1] / 'extraction' / 'main.py'


def write_epub(path, files):
    with zipfile.ZipFile(path, 'w') as archive:
        for name, body in files.items():
            archive.writestr(name, f'<html><body>{body}</body></html>')
    return path


@pytest.fixture
def sources(tmp_path):
    pt = write_epub(tmp_path / 'pt.epub', {
        'OEBPS/c01.xhtml': '<h1>Network Fundamentals</h1><ol><li id="c01-ex-0001">First?'
        '<ol class="upper-alpha"><li>A choice</li><li>B choice</li><li>C choice</li><li>D choice</li></ol></li></ol>',
        'OEBPS/b01.xhtml': '<ol><li><b>A</b>. Explanation.</li></ol>',
    })
    ocg = write_epub(tmp_path / 'ocg.epub', {
        'OEBPS/xhtml/vol1_ch01.xhtml': '<p class="quiz"><b>1</b>. Second?</p>' + ''.join(
            f'<p class="alpha">Choice {letter}</p>' for letter in 'ABCD'),
        'OEBPS/xhtml/vol1_appc.xhtml': '<p class="quiz"><a id="ques1_1">1</a>. A. Explanation.</p>',
    })
    return pt, ocg


def run_cli(sources, output, *args):
    return subprocess.run([sys.executable, str(CLI), *map(str, sources), '--output', str(output), *args],
                          text=True, capture_output=True)


def test_dry_run_creates_no_output(sources, tmp_path):
    output = tmp_path / 'output'
    result = run_cli(sources, output, '--dry-run')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['practice_tests'] == 1
    assert not output.exists()


def test_rerun_updates_in_place_preserving_history(sources, tmp_path):
    output = tmp_path / 'output'
    assert run_cli(sources, output).returncode == 0
    with sqlite3.connect(output / 'ccna.db') as conn:
        original = conn.execute('SELECT id FROM questions ORDER BY id').fetchall()
        conn.execute('CREATE TABLE history(question_id INTEGER REFERENCES questions(id), attempts INTEGER)')
        conn.execute('INSERT INTO history VALUES (?, 7)', original[0])
        conn.execute("UPDATE questions SET question_text = 'old content'")
    result = run_cli(sources, output)
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(output / 'ccna.db') as conn:
        assert conn.execute('SELECT id FROM questions ORDER BY id').fetchall() == original
        assert conn.execute('SELECT * FROM history').fetchall() == [(original[0][0], 7)]
        assert conn.execute("SELECT COUNT(*) FROM questions WHERE question_text = 'old content'").fetchone()[0] == 0


def test_failed_second_parse_does_not_create_output(sources, tmp_path):
    output = tmp_path / 'output'
    sources[1].write_text('broken epub')
    result = run_cli(sources, output)
    assert result.returncode != 0
    assert not output.exists()


def test_missing_answer_option_rejected_before_write(sources, tmp_path):
    write_epub(sources[1], {
        'OEBPS/xhtml/vol1_ch01.xhtml': '<p class="quiz"><b>1</b>. Second?</p><p class="alpha">Only A</p>',
        'OEBPS/xhtml/vol1_appc.xhtml': '<p class="quiz"><a id="ques1_1">1</a>. G. Explanation.</p>',
    })
    output = tmp_path / 'output'
    result = run_cli(sources, output)
    assert result.returncode != 0
    assert not output.exists()


def test_duplicate_existing_identity_rejected_without_updates(sources, tmp_path):
    output = tmp_path / 'output'
    assert run_cli(sources, output).returncode == 0
    with sqlite3.connect(output / 'ccna.db') as conn:
        conn.execute("UPDATE questions SET source_book = 'practice_tests', ocg_chapter_ref = NULL, sub_domain = 'c01-ex-0001', question_text = 'keep'")
    result = run_cli(sources, output)
    assert result.returncode != 0
    with sqlite3.connect(output / 'ccna.db') as conn:
        assert conn.execute('SELECT question_text FROM questions').fetchall() == [('keep',), ('keep',)]


def test_database_error_rolls_back_both_sources(sources, tmp_path):
    output = tmp_path / 'output'
    assert run_cli(sources, output).returncode == 0
    with sqlite3.connect(output / 'ccna.db') as conn:
        conn.execute("UPDATE questions SET question_text = 'keep'")
        conn.execute("CREATE TRIGGER block_second BEFORE UPDATE ON questions WHEN OLD.source_book != 'practice_tests' BEGIN SELECT RAISE(ABORT, 'blocked'); END")
    result = run_cli(sources, output)
    assert result.returncode != 0
    with sqlite3.connect(output / 'ccna.db') as conn:
        assert conn.execute('SELECT question_text FROM questions').fetchall() == [('keep',), ('keep',)]
