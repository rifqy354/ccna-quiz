# -*- coding: utf-8 -*-
"""Parser for CCNA Certification Practice Tests (Jon Buhagiar) EPUB.

Structure discovered by inspection (September 2026):

EPUB chapters:  c01–c08  (8 chapter files, one per CCNA domain/exam)
Answer key:     b01.xhtml  (single file with all 8 chapters' answers)

Chapter cXX structure:
  <ol>                              ← root quiz list (no class attribute)
    <li id="cXX-ex-NNN">            ← one question per <li>, ID is per-chapter numbering
      "Question text..."              ← first text node
      <figure>...<img.../>...</figure>  ← optional figure (discarded)
      <ol class="upper-alpha">       ← answer options
        <li>Option A text...</li>
        <li>Option B text...</li>
        <li>Option C text...</li>
        <li>Option D text...</li>     ← one c03 question has 5 options (A–E)
      </ol>
    </li>
    ... (more <li> elements)
  </ol>

Answer key (b01.xhtml) structure:
  8 root <ol> sections, one per chapter.
  Each <ol> contains <li> elements with id="bapp01-ex-NNNN".
  Entry format: "A. Explanation..."  (letter then period, then explanation)
  Answers are numbered SEQUENTIALLY in document order — the NNNN in bapp01-ex-NNNN
  does NOT match the per-chapter question IDs in the chapter files.
  The first <ol> of b01 contains 201 entries (IDs 0001–0203, gaps: 0003, 0007).
  Chapter c01 has 201 questions.  Sequential mapping: c01[q1] ↔ b01_ol0[entry0],
  c01[q2] ↔ b01_ol0[entry1], etc.

  Chapter answer ranges (answer key section → chapter):
    b01 ol[0]: 201 entries → c01  (201 questions)
    b01 ol[1]: 202 entries → c02  (202 questions)
    b01 ol[2]: 250 entries → c03  (250 questions)
    b01 ol[3]: 100 entries → c04  (100 questions)
    b01 ol[4]: 150 entries → c05  (150 questions)
    b01 ol[5]: 100 entries → c06  (100 questions)
    b01 ol[6]: 100 entries → c07  (100 questions)
    b01 ol[7]: 100 entries → c08  (100 questions)
    Total: 1203 answers, 1203 questions.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from .models import ExtractedQuestion


# ── Domain mapping ────────────────────────────────────────────────────────────
_DOMAIN_MAP: dict[str, tuple[int, str]] = {
    "c01": (1, "Network Fundamentals"),
    "c02": (2, "Network Access"),
    "c03": (3, "IP Connectivity"),
    "c04": (4, "IP Services"),
    "c05": (5, "Security Fundamentals"),
    "c06": (6, "Automation and Programmability"),
    "c07": (7, "Practice Exam 1"),
    "c08": (7, "Practice Exam 2"),
}

_BOOK_TITLE = "CCNA Certification Practice Tests, 2nd Edition (Buhagiar)"

# Letters for options A–G (upper-alpha lists in the EPUB)
_LETTER_MAP = dict(enumerate("ABCDEFG"))


# ── HTML cleaning ─────────────────────────────────────────────────────────────
def _strip_html(text: str) -> str:
    """Remove XHTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = (text.replace("\xa0", " ").replace("'", "'").replace("'", "'")
             .replace('"', '"').replace('"', '"')
             .replace("–", "–").replace("—", "—"))
    return text.strip()


# ── Image extraction ──────────────────────────────────────────────────────────
def _extract_image(li_el, images_dir: Path, epub_zip, chapter_key: str) -> Optional[str]:
    """Extract the first <figure><img ...></figure> from a question <li>.

    Saves the image to images_dir and returns the relative filename.
    """
    figure = li_el.find("figure")
    if not figure:
        return None
    img = figure.find("img")
    if not img:
        return None
    src = img.get("src", "")
    if not src:
        return None
    src = src.lstrip("./")
    filename = Path(src).name
    candidates = [
        src,
        f"OEBPS/{src}",
        f"OEBPS/images/{filename}",
        f"images/{filename}",
    ]
    for candidate in candidates:
        if candidate in epub_zip.namelist():
            out_path = images_dir / filename
            if not out_path.exists():
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(epub_zip.read(candidate))
            return filename
    return None


# ── Answer parsing ─────────────────────────────────────────────────────────────
def _parse_answer_from_html(html_str: str) -> tuple[str, str]:
    """Parse an answer <li> HTML string into (letter, explanation).

    Handles: "<li>A. Explanation...</li>"
             "<li><b>D</b>.vlan.datis the database...</li>"
             "<li>D .vlan.datis..."  (space before period, from tag removal)
    Returns (letter, explanation_text).
    """
    # Collapse tags to spaces, then clean
    stripped = re.sub(r"<[^>]+>", " ", html_str)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    # Format: "A. Explanation..."  or  "A . Explanation..."  (space before period)
    m = re.match(r"^([A-Z])\s*\.\s*(.*)", stripped, re.IGNORECASE)
    if m:
        return m.group(1).upper(), _strip_html(m.group(2))
    # Fallback: first capital letter
    m2 = re.match(r"^([A-Z])", stripped)
    letter = m2.group(1).upper() if m2 else "?"
    return letter, _strip_html(stripped)


# ── Option extraction ─────────────────────────────────────────────────────────
def _extract_options(li_el) -> dict[str, str]:
    """Extract answer options from a question <li> element.

    Options live in <ol class="upper-alpha"><li>...</li></ol>.
    The option LETTER is determined by the <li>'s POSITION in the list
    (A=0th, B=1st, C=2nd, D=3rd, E=4th, F=5th) — NOT by the first
    character of the option text.

    Many PT options start with words like "Spanning Tree Protocol" or
    "One broadcast domain", not "A.", "B.", etc., so we must NOT infer
    the letter from the text content.
    """
    options: dict[str, str] = {}
    ol = li_el.find("ol", class_="upper-alpha")
    if not ol:
        return options
    # Only direct <li> children count (not nested lists)
    for idx, li_opt in enumerate(ol.find_all("li", recursive=False)):
        if idx > 6:  # Safety: cap at 7 options (A–G)
            break
        text = li_opt.get_text(strip=True)
        if not text:
            continue
        letter = _LETTER_MAP.get(idx)
        if letter:
            options[letter] = text
    return options


# ── Question text extraction ──────────────────────────────────────────────────
def _get_question_text(li_el) -> str:
    """Return the question text from a question <li>, stripping options."""
    clone = BeautifulSoup(str(li_el), "xml")
    # Remove the options <ol> and any figures
    for ol in clone.find_all("ol"):
        ol.decompose()
    for fig in clone.find_all("figure"):
        fig.decompose()
    # Remove pagebreak spans
    for pb in clone.find_all("span", attrs={"epub:type": "pagebreak"}):
        pb.decompose()
    return clone.get_text(separator=" ", strip=True)


# ── Chapter title extraction ────────────────────────────────────────────────────
def _extract_chapter_title(soup: BeautifulSoup) -> str:
    span = soup.find("span", class_="chapterTitle")
    if span:
        return span.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        return _strip_html(str(h1))
    return "Unknown Chapter"


# ── Main parser ───────────────────────────────────────────────────────────────
def parse_practice_tests_epub(epub_path: str, images_dir: str) -> list[ExtractedQuestion]:
    """Extract all questions from the Practice Tests EPUB.

    Returns a list of ExtractedQuestion objects.
    """
    images_path = Path(images_dir)
    images_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(epub_path) as zf:
        questions: list[ExtractedQuestion] = []

        # ── 1. Build per-chapter answer index from b01.xhtml ────────────────
        # b01 has 8 root <ol> elements, one per chapter.
        # We build a flat list of (chapter_index, letter, explanation) per answer entry.
        # chapter_index: 0=c01, 1=c02, ..., 7=c08

        b01_content = _read_xhtml(zf, "OEBPS/b01.xhtml")
        if not b01_content:
            return []

        soup_b01 = BeautifulSoup(b01_content, "xml")
        root_ols_b01 = [ol for ol in soup_b01.find_all("ol") if not ol.get("class")]
        # answer_entries[chapter_idx] = [(letter, explanation), ...]
        answer_entries: list[list[tuple[str, str]]] = []
        for ol in root_ols_b01:
            chapter_answers: list[tuple[str, str]] = []
            for li in ol.find_all("li", recursive=False):
                html_str = str(li)
                letter, explanation = _parse_answer_from_html(html_str)
                chapter_answers.append((letter, explanation))
            answer_entries.append(chapter_answers)

        # ── 2. Parse each chapter c01–c08 ───────────────────────────────────
        for chapter_idx in range(8):
            chapter_key = f"c{chapter_idx + 1:02d}"
            chapter_file = f"OEBPS/{chapter_key}.xhtml"
            raw = _read_xhtml(zf, chapter_file)
            if not raw:
                continue

            soup = BeautifulSoup(raw, "xml")
            domain_num, domain_name = _DOMAIN_MAP.get(chapter_key, (0, "Unknown"))
            chapter_title = _extract_chapter_title(soup)

            # Find root quiz <ol> (no class attribute)
            root_ol = None
            for ol in soup.find_all("ol"):
                if not ol.get("class"):
                    root_ol = ol
                    break

            if not root_ol:
                continue

            # All direct <li> children are questions
            question_lis = root_ol.find_all("li", recursive=False)

            # Get the corresponding answer list for this chapter
            chapter_answers = answer_entries[chapter_idx] if chapter_idx < len(answer_entries) else []

            for q_pos, li in enumerate(question_lis):
                lid = li.get("id", "")

                question_text = _get_question_text(li)
                if not question_text.strip():
                    continue  # Skip empty questions

                question_text = _strip_html(question_text)

                # Extract image (if any)
                image_filename = _extract_image(li, images_path, zf, chapter_key)

                # Extract options by list position
                options = _extract_options(li)

                # Look up answer by sequential position
                answer_letter: str = "?"
                explanation: str = ""
                if q_pos < len(chapter_answers):
                    answer_letter, explanation = chapter_answers[q_pos]
                # If q_pos >= len(chapter_answers), the question has no answer entry

                # Record sub_domain as the chapter question ID (e.g. "c01-ex-0001")
                q_num_str = lid.removeprefix(f"{chapter_key}-ex-") if lid.startswith(f"{chapter_key}-ex-") else str(q_pos + 1)
                sub_domain = f"{chapter_key}-ex-{q_num_str}"

                q = ExtractedQuestion(
                    source_book="practice_tests",
                    source_chapter=chapter_title,
                    book_title=_BOOK_TITLE,
                    domain=domain_num,
                    sub_domain=sub_domain,
                    sub_domain_name=domain_name,
                    question_text=question_text,
                    question_image=image_filename,
                    option_a=options.get("A", ""),
                    option_b=options.get("B", ""),
                    option_c=options.get("C", ""),
                    option_d=options.get("D", ""),
                    option_e=options.get("E", ""),
                    option_f=options.get("F", ""),
                    option_g=options.get("G", ""),
                    correct_option=answer_letter,
                    explanation=explanation,
                    ocg_chapter_ref=None,
                    ocg_section_ref=None,
                    difficulty=2,
                )
                questions.append(q)

    return questions


# ── Helpers ───────────────────────────────────────────────────────────────────
def _read_xhtml(zf: zipfile.ZipFile, path: str) -> Optional[str]:
    try:
        return zf.read(path).decode("utf-8")
    except KeyError:
        return None
