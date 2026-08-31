# -*- coding: utf-8 -*-
"""Parser for CCNA Certification Practice Tests (Jon Buhagiar) EPUB.

Chapter structure:
  c01-c06  → CCNA domains 1-6
  c07      → Practice Exam 1  (domain 7)
  c08      → Practice Exam 2  (domain 7)

Answer key: b01.xhtml — single file with all 8 chapters' answers.
Answer ID pattern: bapp01-ex-NNNN matches question ID cXX-ex-NNNN directly
(both share the numeric suffix; gaps in question IDs → gaps in answer IDs).
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


# ── HTML cleaning ─────────────────────────────────────────────────────────────
def _strip_html(text: str) -> str:
    """Remove XHTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("\xa0", " ").replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("&#8211;", "–").replace("&#8212;", "—")
    text = text.replace("&#8220;", '"').replace("&#8221;", '"')
    return text.strip()


# ── Image extraction ──────────────────────────────────────────────────────────
def _extract_image(soup: BeautifulSoup, images_dir: Path, epub_zip, chapter_prefix: str) -> Optional[str]:
    """Extract the first <figure><img ...></figure> from a BeautifulSoup node.

    Saves the image to images_dir and returns the relative filename.
    """
    figure = soup.find("figure")
    if not figure:
        return None

    img = figure.find("img")
    if not img:
        return None

    src = img.get("src", "")
    if not src:
        return None

    # src is like "images/c01uf001.png" — locate in the EPUB zip
    # The zip stores images at the same path as the XHTML that references them.
    # Normalise: strip leading "../" if any.
    src = src.lstrip("./")
    filename = Path(src).name

    # Try to copy from zip
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
def _parse_answer_letter(text: str) -> str:
    """Pull the leading letter(s) from an answer text string.

    Handles single answers like "A." and multiple like "D and F."
    Returns a canonical letter like "A" or "AD" (uppercase, no spaces).
    Strips any leading HTML tags before matching.
    """
    # Remove leading HTML tags to get to the actual content
    cleaned = re.sub(r"^[^A-Za-z]+", "", text)
    letter_pattern = re.compile(r"^([A-Z](?:\s+(?:and|or)\s+[A-Z])*)\s*[\.\)]", re.IGNORECASE)
    m = letter_pattern.match(cleaned)
    if m:
        raw = m.group(1).upper()
        # normalize "A and B" → "AB"
        letters = re.findall(r"[A-Z]", raw)
        return "".join(letters)
    # Fallback: first letter of the cleaned text
    m2 = re.match(r"([A-Z])", cleaned)
    return m2.group(1) if m2 else "A"


def _parse_answer_from_html(html_str: str) -> tuple[str, str]:
    """Parse an answer <li> HTML string into (letter, explanation).

    Handles formats:
      <li>A. Explanation...</li>
      <li><b>A</b>. Explanation...</li>
    Returns (letter, explanation_text).
    """
    # Strip HTML tags and collapse whitespace to get clean text
    stripped = re.sub(r"<[^>]+>", " ", html_str)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    # Now stripped looks like "A. Explanation text..."
    # Find the first letter(s) followed by period
    m = re.match(r"^([A-Z](?:\s+(?:and|or)\s+[A-Z])*)\s*[\.\)]\s*(.*)", stripped, re.IGNORECASE)
    if m:
        raw_letters = m.group(1).upper()
        letters = re.findall(r"[A-Z]", raw_letters)
        letter = "".join(letters)
        explanation = _strip_html(m.group(2))
        return letter, explanation
    # Fallback
    m2 = re.match(r"^([A-Z])", stripped)
    letter = m2.group(1) if m2 else "A"
    return letter, _strip_html(stripped)


# ── Main parser ────────────────────────────────────────────────────────────────
def parse_practice_tests_epub(epub_path: str, images_dir: str) -> list[ExtractedQuestion]:
    """Extract all questions from the Practice Tests EPUB.

    Returns a list of ExtractedQuestion objects.
    """
    images_path = Path(images_dir)
    images_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(epub_path) as zf:
        questions: list[ExtractedQuestion] = []

        # ── 1. Build answer index from b01.xhtml ─────────────────────────────
        answer_index: dict[str, tuple[str, str]] = {}  # id_suffix → (letter, explanation)

        b01_content = _read_xhtml(zf, "OEBPS/b01.xhtml")
        if b01_content:
            soup_b01 = BeautifulSoup(b01_content, "lxml")
            for li in soup_b01.find_all("li"):
                lid = li.get("id", "")
                if lid.startswith("bapp01-ex-"):
                    suffix = lid.removeprefix("bapp01-ex-")
                    # Full text of the answer list item
                    answer_html = str(li)
                    letter, explanation = _parse_answer_from_html(answer_html)
                    answer_index[suffix] = (letter, explanation)

        # ── 2. Parse each chapter c01-c08 ───────────────────────────────────
        for chapter_key in [f"c{i:02d}" for i in range(1, 9)]:
            chapter_file = f"OEBPS/{chapter_key}.xhtml"
            raw = _read_xhtml(zf, chapter_file)
            if not raw:
                continue

            soup = BeautifulSoup(raw, "lxml")
            domain_num, domain_name = _DOMAIN_MAP.get(chapter_key, (0, "Unknown"))
            chapter_title = _extract_chapter_title(soup)

            # Find all question <li> elements
            for li in soup.find_all("li"):
                lid = li.get("id", "")
                if not lid.startswith(f"{chapter_key}-ex-"):
                    continue

                q_num = lid.removeprefix(f"{chapter_key}-ex-")
                question_text_raw = _get_question_text(li)
                if not question_text_raw.strip():
                    continue

                question_text = _strip_html(question_text_raw)

                # Extract image (if any)
                image_filename = _extract_image(li, images_path, zf, chapter_key)

                # Extract options A/B/C/D
                options = _extract_options(li)
                if len(options) < 2:
                    # Skip malformed questions
                    continue

                # Look up answer
                answer_data = answer_index.get(q_num)
                if answer_data is None:
                    # Missing answer — skip to avoid bad data
                    continue

                correct_letter, explanation = answer_data

                q = ExtractedQuestion(
                    source_book="practice_tests",
                    source_chapter=chapter_title,
                    book_title=_BOOK_TITLE,
                    domain=domain_num,
                    sub_domain=f"{chapter_key}-ex-{q_num}",
                    sub_domain_name=domain_name,
                    question_text=question_text,
                    question_image=image_filename,
                    option_a=options.get("A", ""),
                    option_b=options.get("B", ""),
                    option_c=options.get("C", ""),
                    option_d=options.get("D", ""),
                    correct_option=correct_letter,
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


def _extract_chapter_title(soup: BeautifulSoup) -> str:
    span = soup.find("span", class_="chapterTitle")
    if span:
        return span.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        return _strip_html(str(h1))
    return "Unknown Chapter"


def _get_question_text(li) -> str:
    """Return the question text without the options <ol>."""
    # Clone so we don't mutate the soup
    clone = BeautifulSoup(str(li), "lxml")
    # Remove the options <ol>
    for ol in clone.find_all("ol"):
        ol.decompose()
    # Remove pagebreak spans
    for pb in clone.find_all("span", attrs={"epub:type": "pagebreak"}):
        pb.decompose()
    return clone.get_text(separator=" ", strip=True)


def _extract_options(li) -> dict[str, str]:
    """Extract A/B/C/D options from a question <li> element.

    Options are in <ol class="upper-alpha"><li>...</li></ol>.
    Returns {"A": "...", "B": "...", "C": "...", "D": "..."}.
    """
    options: dict[str, str] = {}
    ol = li.find("ol", class_="upper-alpha")
    if not ol:
        return options
    for li_opt in ol.find_all("li"):
        text = li_opt.get_text(strip=True)
        if not text:
            continue
        first_char = text[0].upper()
        if first_char in ("A", "B", "C", "D"):
            options[first_char] = text
    return options
