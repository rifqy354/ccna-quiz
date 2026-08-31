# -*- coding: utf-8 -*-
"""Parser for CCNA 200-301 Official Cert Guide Library (Odom et al.) EPUB.

Each chapter contains a "Do I Know This Already?" (DIKTA) quiz section.
The section starts at anchor #chXXlev1sec1 and ends before
the Foundation Topics section (#chXXlev2sec1).

DIKTA questions use the pattern:
    <p class="quiz">
      <strong><a id="quessX_Y" href="...">N</a>.</strong> Question text?
      [<ol class="lower-alpha"> <li>A. ...</li> ... </ol>]
    </p>

Answers are in Appendix C (vol*_appc.xhtml):
    <p class="quiz">
      <strong><a id="quesX_Y" href="...">N</a>.</strong> Answer letter. Explanation.
    </p>

Domain mapping uses the official CCNA 200-301 topic structure:
  Vol1 ch 1-4  → Domain 1 (Network Fundamentals)
  Vol1 ch 5-10 → Domain 2 (Network Access)
  Vol1 ch 11-24 → Domain 3 (IP Connectivity)
  Vol1 ch 25-29 → Domain 4 (IP Services)
  Vol2 ch 1-4  → Domain 5 (Security Fundamentals)
  Vol2 ch 5-8  → Domain 4 (IP Services)
  Vol2 ch 9-12 → Domain 5 (Security Fundamentals)
  Vol2 ch 13-16 → Domain 4 (IP Services)
  Vol2 ch 17   → Domain 4 (IP Services)
  Vol2 ch 18-19 → Domain 2 (Network Access)
  Vol2 ch 20   → Domain 1 (Network Fundamentals)
  Vol2 ch 21-24 → Domain 6 (Automation and Programmability)
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from .models import ExtractedQuestion


# ── Volume / Chapter → Domain mapping ─────────────────────────────────────────
# Format: (volume, chapter) → (domain, domain_name)
_OCG_DOMAIN_MAP: dict[tuple[str, int], tuple[int, str]] = {
    # Volume 1
    ("vol1", 1):  (1, "Network Fundamentals"),
    ("vol1", 2):  (1, "Network Fundamentals"),
    ("vol1", 3):  (1, "Network Fundamentals"),
    ("vol1", 4):  (1, "Network Fundamentals"),
    ("vol1", 5):  (2, "Network Access"),
    ("vol1", 6):  (2, "Network Access"),
    ("vol1", 7):  (2, "Network Access"),
    ("vol1", 8):  (2, "Network Access"),
    ("vol1", 9):  (2, "Network Access"),
    ("vol1", 10): (2, "Network Access"),
    ("vol1", 11): (3, "IP Connectivity"),
    ("vol1", 12): (3, "IP Connectivity"),
    ("vol1", 13): (3, "IP Connectivity"),
    ("vol1", 14): (3, "IP Connectivity"),
    ("vol1", 15): (3, "IP Connectivity"),
    ("vol1", 16): (3, "IP Connectivity"),
    ("vol1", 17): (3, "IP Connectivity"),
    ("vol1", 18): (3, "IP Connectivity"),
    ("vol1", 19): (3, "IP Connectivity"),
    ("vol1", 20): (3, "IP Connectivity"),
    ("vol1", 21): (3, "IP Connectivity"),
    ("vol1", 22): (3, "IP Connectivity"),
    ("vol1", 23): (3, "IP Connectivity"),
    ("vol1", 24): (3, "IP Connectivity"),
    ("vol1", 25): (4, "IP Services"),
    ("vol1", 26): (4, "IP Services"),
    ("vol1", 27): (4, "IP Services"),
    ("vol1", 28): (4, "IP Services"),
    ("vol1", 29): (4, "IP Services"),
    # Volume 2
    ("vol2", 1):  (5, "Security Fundamentals"),
    ("vol2", 2):  (5, "Security Fundamentals"),
    ("vol2", 3):  (5, "Security Fundamentals"),
    ("vol2", 4):  (5, "Security Fundamentals"),
    ("vol2", 5):  (4, "IP Services"),
    ("vol2", 6):  (4, "IP Services"),
    ("vol2", 7):  (4, "IP Services"),
    ("vol2", 8):  (4, "IP Services"),
    ("vol2", 9):  (5, "Security Fundamentals"),
    ("vol2", 10): (5, "Security Fundamentals"),
    ("vol2", 11): (5, "Security Fundamentals"),
    ("vol2", 12): (5, "Security Fundamentals"),
    ("vol2", 13): (4, "IP Services"),
    ("vol2", 14): (4, "IP Services"),
    ("vol2", 15): (4, "IP Services"),
    ("vol2", 16): (4, "IP Services"),
    ("vol2", 17): (4, "IP Services"),
    ("vol2", 18): (2, "Network Access"),
    ("vol2", 19): (2, "Network Access"),
    ("vol2", 20): (1, "Network Fundamentals"),
    ("vol2", 21): (6, "Automation and Programmability"),
    ("vol2", 22): (6, "Automation and Programmability"),
    ("vol2", 23): (6, "Automation and Programmability"),
    ("vol2", 24): (6, "Automation and Programmability"),
}

_BOOK_TITLE = "CCNA 200-301 Official Cert Guide Library, 2nd Ed. (Odom et al.)"


# ── HTML helpers ──────────────────────────────────────────────────────────────
def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = (text
            .replace("\xa0", " ")
            .replace("'", "'").replace("'", "'")
            .replace(""", '"').replace(""", '"')
            .replace("–", "-").replace("—", "-")
            .replace("&#8211;", "–").replace("&#8212;", "—")
            .replace("&#8220;", '"').replace("&#8221;", '"')
            .replace("&#8216;", "'").replace("&#8217;", "'"))
    return text.strip()


def _read_xhtml(zf: zipfile.ZipFile, path: str) -> Optional[str]:
    try:
        return zf.read(path).decode("utf-8")
    except KeyError:
        return None


def _extract_chapter_title(soup: BeautifulSoup) -> str:
    # Try navpoint-style title (from TOC <a> text)
    # Fall back to heading in the file itself
    h1 = soup.find("h1")
    if h1:
        return _strip_html(str(h1))
    return "Unknown Chapter"


# ── DIKTA section extraction ───────────────────────────────────────────────────
def _extract_dikta_section(chapter_content: str, chapter_num: int) -> Optional[str]:
    """Return the raw HTML of the DIKTA quiz section for one chapter.

    The section starts at the "Do I Know This Already?" heading
    (anchor chXXlev1sec1) and ends before Foundation Topics
    (chXXlev2sec1 or the first section after lev1sec1).
    """
    chapter_str = f"ch{chapter_num:02d}"

    # Find the DIKTA section heading anchor
    dikta_start_pattern = re.compile(
        rf'id="{re.escape(chapter_str)}lev1sec1"'
    )
    m_start = dikta_start_pattern.search(chapter_content)
    if not m_start:
        return None

    start_idx = m_start.start()

    # End: the first Foundation Topics section (lev2sec1)
    dikta_end_pattern = re.compile(
        rf'id="{re.escape(chapter_str)}lev2sec1"'
    )
    m_end = dikta_end_pattern.search(chapter_content, pos=start_idx + 1)

    if m_end:
        end_idx = m_end.start()
    else:
        # Fallback: scan forward ~150 KB for the next <section> or Foundation
        search_range = chapter_content.find("Foundation Topics", start_idx)
        if search_range > start_idx:
            end_idx = search_range
        else:
            end_idx = start_idx + 150_000  # arbitrary safety limit

    return chapter_content[start_idx:end_idx]


# ── Question parsing ────────────────────────────────────────────────────────────
def _parse_dikta_questions(dikta_html: str, volume: str, chapter_num: int) -> list[dict]:
    """Parse individual DIKTA questions from the raw DIKTA section HTML.

    Returns a list of dicts with keys:
      q_num, question_text, options (list of (letter, text)), image_alt
    """
    soup = BeautifulSoup(dikta_html, "lxml")
    questions: list[dict] = []

    for pq in soup.find_all("p", class_="quiz"):
        # Extract question number from anchor
        anchor = pq.find("a")
        if not anchor:
            continue

        q_id = anchor.get("id", "")
        # e.g. "quess1_1" → q_num = "1"
        q_num_match = re.search(r"_(\d+)$", q_id)
        if not q_num_match:
            continue
        q_num = q_num_match.group(1)

        # Clone so we can mutate
        pq_clone = BeautifulSoup(str(pq), "lxml")
        anchor.decompose()  # remove the anchor from text

        # Text before the <ol> options
        raw_text = pq_clone.get_text(separator=" ", strip=True)
        # Remove leading "N. " that may appear after anchor removal
        raw_text = re.sub(r"^\d+\s*[\.\)]\s*", "", raw_text, count=1)

        # Extract options
        options: list[tuple[str, str]] = []
        ol = pq_clone.find("ol", class_="lower-alpha")
        if ol:
            for li_opt in ol.find_all("li"):
                letter_span = li_opt.find("span", class_="alpha")
                if letter_span:
                    letter = letter_span.get_text(strip=True)
                    text = letter_span.get_text(strip=True)
                    # letter is just the letter, text is the full option
                    options.append((letter[0] if letter else "?", text))
                else:
                    text = li_opt.get_text(strip=True)
                    if text:
                        options.append((text[0] if text else "?", text))

        # Extract image alt text (from any <figure><img alt="...">)
        img_alt = ""
        figure = pq_clone.find("figure")
        if figure:
            img = figure.find("img")
            if img:
                img_alt = img.get("alt", "")

        if not raw_text.strip():
            continue

        questions.append({
            "q_num": q_num,
            "question_text": _strip_html(raw_text),
            "options": options,
            "image_alt": img_alt,
        })

    return questions


# ── Answer lookup ──────────────────────────────────────────────────────────────
def _build_answer_index(zf: zipfile.ZipFile, volume: str) -> dict[str, tuple[str, str]]:
    """Parse vol*_appc.xhtml and return a dict keyed by 'volN_chXX_qN'.

    Each entry is (answer_letter, explanation).
    """
    index: dict[str, tuple[str, str]] = {}
    appc_path = f"OEBPS/xhtml/{volume}_appc.xhtml"
    raw = _read_xhtml(zf, appc_path)
    if not raw:
        return index

    soup = BeautifulSoup(raw, "lxml")
    for pq in soup.find_all("p", class_="quiz"):
        anchor = pq.find("a")
        if not anchor:
            continue

        q_id = anchor.get("id", "")  # e.g. "ques1_1"
        if not q_id.startswith("ques"):
            continue

        # Map to vol1_ch01_q1 format
        # ques1_1 → ch01_q1 (from vol1_appc)
        m = re.match(r"ques(\d+)_(\d+)", q_id)
        if not m:
            continue

        chapter_num_s, q_num = m.groups()
        chapter_num = int(chapter_num_s)

        # Extract the answer letter and explanation text
        # Format: "A." or "D and F." at start
        full_text = pq.get_text(separator=" ", strip=True)
        # Remove leading question number
        full_text = re.sub(r"^\d+\s*[\.\)]\s*", "", full_text, count=1)

        letter, explanation = _parse_answer_text(full_text)
        key = f"{volume}_ch{chapter_num:02d}_q{q_num}"
        index[key] = (letter, explanation)

    return index


def _parse_answer_text(text: str) -> tuple[str, str]:
    """Split 'A. Explanation...' or 'D and F. Explanation...' into (letter, explanation)."""
    m = re.match(r"^([A-Z](?:\s+(?:and|or)\s+[A-Z])*)\s*[\.\)]\s*(.*)", text.strip(), re.IGNORECASE)
    if m:
        letters_raw = m.group(1).upper()
        letters = re.findall(r"[A-Z]", letters_raw)
        return "".join(letters), _strip_html(m.group(2))
    # Fallback
    m2 = re.match(r"^([A-Z])", text.strip())
    first_letter = m2.group(1) if m2 else "A"
    return first_letter, _strip_html(text)


# ── Image extraction ───────────────────────────────────────────────────────────
def _extract_images_from_chapter(
    zf: zipfile.ZipFile,
    chapter_content: str,
    images_dir: Path,
    volume: str,
    chapter_num: int,
) -> dict[str, Optional[str]]:
    """Extract all images from a chapter's DIKTA section.

    Returns a dict mapping image source filename → saved filename.
    """
    saved: dict[str, Optional[str]] = {}
    soup = BeautifulSoup(chapter_content, "lxml")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        src = src.lstrip("./")
        filename = Path(src).name

        # Try to find in zip
        candidates = [
            src,
            f"OEBPS/xhtml/{src}",
            f"OEBPS/xhtml/images/{filename}",
            filename,
        ]
        for cand in candidates:
            if cand in zf.namelist():
                out_path = images_dir / filename
                if not out_path.exists():
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(zf.read(cand))
                saved[src] = filename
                break
        else:
            saved[src] = None  # not found in zip

    return saved


# ── Main parser ────────────────────────────────────────────────────────────────
def parse_ocg_epub(epub_path: str, images_dir: str) -> list[ExtractedQuestion]:
    """Extract all DIKTA questions from the OCG Library EPUB.

    Returns a list of ExtractedQuestion objects.
    """
    images_path = Path(images_dir)
    images_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(epub_path) as zf:
        questions: list[ExtractedQuestion] = []
        all_files = zf.namelist()

        # Build per-volume answer indexes
        answer_indexes: dict[str, dict[str, tuple[str, str]]] = {}
        for vol in ("vol1", "vol2"):
            answer_indexes[vol] = _build_answer_index(zf, vol)

        # Find all chapter files
        chapter_files: list[tuple[str, int]] = []
        for fname in all_files:
            m = re.match(r"OEBPS/xhtml/(vol\d+)_ch(\d+)\.xhtml$", fname)
            if m:
                chapter_files.append((m.group(1), int(m.group(2))))

        for volume, chapter_num in sorted(chapter_files, key=lambda x: (x[0], x[1])):
            chapter_key = f"{volume}_ch{chapter_num:02d}"
            chapter_path = f"OEBPS/xhtml/{volume}_ch{chapter_num:02d}.xhtml"
            raw = _read_xhtml(zf, chapter_path)
            if not raw:
                continue

            # Map to domain
            domain_info = _OCG_DOMAIN_MAP.get((volume, chapter_num))
            if not domain_info:
                continue
            domain_num, domain_name = domain_info

            # Extract DIKTA section
            dikta_html = _extract_dikta_section(raw, chapter_num)
            if not dikta_html:
                continue

            # Extract images from DIKTA section
            saved_images = _extract_images_from_chapter(
                zf, dikta_html, images_path, volume, chapter_num
            )

            # Parse questions
            dikta_questions = _parse_dikta_questions(dikta_html, volume, chapter_num)

            # Answer index for this volume/chapter
            vol_ans_index = answer_indexes.get(volume, {})

            for dq in dikta_questions:
                q_num = dq["q_num"]
                answer_key = f"{volume}_ch{chapter_num:02d}_q{q_num}"
                answer_data = vol_ans_index.get(answer_key)

                if answer_data:
                    correct_letter, explanation = answer_data
                else:
                    correct_letter, explanation = "A", "No explanation available."

                # Build options A/B/C/D (or more for choose-all)
                options = dq["options"]
                opt_a = opt_b = opt_c = opt_d = ""
                for i, (letter, text) in enumerate(options[:4]):
                    if letter == "A" or (text and text[0] == "A"):
                        opt_a = text
                    elif letter == "B" or (text and text[0] == "B"):
                        opt_b = text
                    elif letter == "C" or (text and text[0] == "C"):
                        opt_c = text
                    elif letter == "D" or (text and text[0] == "D"):
                        opt_d = text

                # Use first 4 options if letter-based assignment failed
                if not opt_a and len(options) > 0:
                    opt_a = options[0][1]
                if not opt_b and len(options) > 1:
                    opt_b = options[1][1]
                if not opt_c and len(options) > 2:
                    opt_c = options[2][1]
                if not opt_d and len(options) > 3:
                    opt_d = options[3][1]

                # Get chapter title
                soup_ch = BeautifulSoup(raw, "lxml")
                chapter_title = _extract_chapter_title(soup_ch)

                q = ExtractedQuestion(
                    source_book="ocg",
                    source_chapter=chapter_title,
                    book_title=_BOOK_TITLE,
                    domain=domain_num,
                    sub_domain=answer_key,
                    sub_domain_name=domain_name,
                    question_text=dq["question_text"],
                    question_image=None,  # images stored by alt text, not filename
                    option_a=opt_a,
                    option_b=opt_b,
                    option_c=opt_c,
                    option_d=opt_d,
                    correct_option=correct_letter,
                    explanation=explanation,
                    ocg_chapter_ref=f"{volume}_ch{chapter_num:02d}",
                    ocg_section_ref=f"ch{chapter_num:02d}lev1sec1",
                    difficulty=2,
                )
                questions.append(q)

    return questions
