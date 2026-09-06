# -*- coding: utf-8 -*-
"""Parser for CCNA 200-301 Official Cert Guide Library (Odom et al.) EPUB."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from .models import ExtractedQuestion

_OCG_DOMAIN_MAP = {
    ("vol1", 1): (1, "Network Fundamentals"), ("vol1", 2): (1, "Network Fundamentals"),
    ("vol1", 3): (1, "Network Fundamentals"), ("vol1", 4): (1, "Network Fundamentals"),
    ("vol1", 5): (2, "Network Access"), ("vol1", 6): (2, "Network Access"),
    ("vol1", 7): (2, "Network Access"), ("vol1", 8): (2, "Network Access"),
    ("vol1", 9): (2, "Network Access"), ("vol1", 10): (2, "Network Access"),
    ("vol1", 11): (3, "IP Connectivity"), ("vol1", 12): (3, "IP Connectivity"),
    ("vol1", 13): (3, "IP Connectivity"), ("vol1", 14): (3, "IP Connectivity"),
    ("vol1", 15): (3, "IP Connectivity"), ("vol1", 16): (3, "IP Connectivity"),
    ("vol1", 17): (3, "IP Connectivity"), ("vol1", 18): (3, "IP Connectivity"),
    ("vol1", 19): (3, "IP Connectivity"), ("vol1", 20): (3, "IP Connectivity"),
    ("vol1", 21): (3, "IP Connectivity"), ("vol1", 22): (3, "IP Connectivity"),
    ("vol1", 23): (3, "IP Connectivity"), ("vol1", 24): (3, "IP Connectivity"),
    ("vol1", 25): (4, "IP Services"), ("vol1", 26): (4, "IP Services"),
    ("vol1", 27): (4, "IP Services"), ("vol1", 28): (4, "IP Services"),
    ("vol1", 29): (4, "IP Services"),
    ("vol2", 1): (5, "Security Fundamentals"), ("vol2", 2): (5, "Security Fundamentals"),
    ("vol2", 3): (5, "Security Fundamentals"), ("vol2", 4): (5, "Security Fundamentals"),
    ("vol2", 5): (4, "IP Services"), ("vol2", 6): (4, "IP Services"),
    ("vol2", 7): (4, "IP Services"), ("vol2", 8): (4, "IP Services"),
    ("vol2", 9): (5, "Security Fundamentals"), ("vol2", 10): (5, "Security Fundamentals"),
    ("vol2", 11): (5, "Security Fundamentals"), ("vol2", 12): (5, "Security Fundamentals"),
    ("vol2", 13): (4, "IP Services"), ("vol2", 14): (4, "IP Services"),
    ("vol2", 15): (4, "IP Services"), ("vol2", 16): (4, "IP Services"),
    ("vol2", 17): (4, "IP Services"),
    ("vol2", 18): (2, "Network Access"), ("vol2", 19): (2, "Network Access"),
    ("vol2", 20): (1, "Network Fundamentals"),
    ("vol2", 21): (6, "Automation and Programmability"),
    ("vol2", 22): (6, "Automation and Programmability"),
    ("vol2", 23): (6, "Automation and Programmability"),
    ("vol2", 24): (6, "Automation and Programmability"),
}

_BOOK_TITLE = "CCNA 200-301 Official Cert Guide Library, 2nd Ed. (Odom et al.)"


def _s(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return (text.replace("\xa0", " ")
            .replace("’", "'").replace("‘", "'")
            .replace("“", '"').replace("”", '"')
            .replace("–", "-").replace("—", "-")).strip()


def _read(path: str, zf: zipfile.ZipFile) -> Optional[str]:
    try:
        return zf.read(path).decode("utf-8", errors="replace")
    except KeyError:
        return None


def _letters(raw: str) -> str:
    """Parse 'D and F' or 'B, D, and E' -> 'DF' or 'BDE'."""
    # Split by comma first, then handle 'and'/'or' per segment
    parts = raw.strip().rstrip(".").split(",")
    out = []
    for p in parts:
        subparts = re.split(r"\s+and\s+|\s+or\s+", p, flags=re.IGNORECASE)
        for sp in subparts:
            m = re.match(r"^([A-Z])", sp.strip().upper())
            if m:
                out.append(m.group(1))
    return "".join(out) if out else "A"


def _answer_list(zf: zipfile.ZipFile, vol: str) -> list[tuple[str, str]]:
    """Parse vol*_appc.xhtml -> [(letters, explanation], in DIKTA order."""
    raw = _read(f"OEBPS/xhtml/{vol}_appc.xhtml", zf)
    if not raw:
        return []
    soup = BeautifulSoup(raw, "lxml")
    body = soup.find("body")
    out: list[tuple[str, str]] = []
    for el in (body.find_all("p") if body else []):
        if el.get("class") != ["quiz"]:
            continue
        text = el.get_text(separator=" ", strip=True)
        # "1 . D and F. Explanation..."
        m = re.match(r"^\d+\s*\.\s*([A-Za-z][^.]*?)\s*[.?!]\s+(.*)", text)
        if not m:
            continue
        raw_ans = m.group(1)
        letters = _letters(raw_ans)
        expl = _s(m.group(2))
        out.append((letters, expl))
    return out


def _parse_body(
    vol: str, body, chapter_num: int,
    answers: list[tuple[str, str]],
    chapter_answer_offset: int = 0,
) -> list[ExtractedQuestion]:
    domain_info = _OCG_DOMAIN_MAP.get((vol, chapter_num))
    if not domain_info:
        return []
    domain_num, domain_name = domain_info
    all_p = list(body.find_all("p"))
    questions: list[ExtractedQuestion] = []
    q_idx = 0
    i = 0
    while i < len(all_p):
        el = all_p[i]
        if el.get("class") != ["quiz"]:
            i += 1
            continue
        text = el.get_text(separator=" ", strip=True)
        m = re.match(r"^(\d+)\s+\.\s+(.*)", text)
        if not m:
            i += 1
            continue
        q_num = int(m.group(1))          # question number from text (1-indexed)
        q_text = _s(m.group(2))
        opts: list[str] = []
        j = i + 1
        while j < len(all_p):
            opt_el = all_p[j]
            cls = opt_el.get("class", [])
            if cls == ["quiz"]:
                break
            if cls == ["alpha"]:
                t = opt_el.get_text(strip=True)
                if t:
                    opts.append(t)
            j += 1
        if len(opts) < 2:
            i = j
            continue
        ans_idx = chapter_answer_offset + q_idx
        ans_let = answers[ans_idx][0] if 0 <= ans_idx < len(answers) else "A"
        expl = answers[ans_idx][1] if 0 <= ans_idx < len(answers) else "No explanation."
        q_idx += 1
        pos_list = [ord(c) - ord("A") + 1
                    for c in ans_let.upper() if c.isalpha()]
        if len(pos_list) == 1:
            correct = chr(ord("A") + pos_list[0] - 1)
        elif len(pos_list) > 1:
            correct = "".join(chr(ord("A") + p - 1) for p in pos_list)
            pos_chr = ", ".join(chr(ord("A") + p - 1) for p in pos_list)
            expl = f"[Multi: {pos_chr}] {expl}"
        else:
            correct = "A"
        a = _s(opts[0]) if len(opts) > 0 else ""
        b = _s(opts[1]) if len(opts) > 1 else ""
        c = _s(opts[2]) if len(opts) > 2 else ""
        d = _s(opts[3]) if len(opts) > 3 else ""
        questions.append(ExtractedQuestion(
            source_book="ocg", source_chapter=f"Ch{chapter_num:02d} DIKTA",
            book_title=_BOOK_TITLE,
            domain=domain_num, sub_domain=f"ch{chapter_num:02d}_q{q_num}",
            sub_domain_name=domain_name,
            question_text=q_text, question_image=None,
            option_a=a, option_b=b, option_c=c, option_d=d,
            option_e=_s(opts[4]) if len(opts) > 4 else "",
            option_f=_s(opts[5]) if len(opts) > 5 else "",
            option_g=_s(opts[6]) if len(opts) > 6 else "",
            correct_option=correct, explanation=_s(expl),
            ocg_chapter_ref=f"{vol}_ch{chapter_num:02d}",
            ocg_section_ref=f"ch{chapter_num:02d}lev1sec1",
            difficulty=2,
        ))
        i = j
    return questions


def parse_ocg_epub(epub_path: str, images_dir: str) -> list[ExtractedQuestion]:
    images_path = Path(images_dir)
    images_path.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path) as zf:
        vol_answers: dict[str, list[tuple[str, str]]] = {
            vol: _answer_list(zf, vol) for vol in ("vol1", "vol2")
        }
        chapters: list[tuple[str, int, str]] = []
        for fname in zf.namelist():
            m = re.match(r"OEBPS/xhtml/(vol\d+)_ch(\d+)\.xhtml$", fname)
            if m:
                chapters.append((m.group(1), int(m.group(2)), fname))
        all_q: list[ExtractedQuestion] = []
        # Build per-volume chapter offset map: vol → {chapter_num → answer_start_index}
        vol_ch_offsets: dict[str, dict[int, int]] = {}
        for vol in ("vol1", "vol2"):
            offsets: dict[int, int] = {}
            running = 0
            # vol_answers[vol] is ordered as quesN_M (chapter N, question M)
            for ans_letters, ans_expl in vol_answers.get(vol, []):
                # Extract chapter number from the answer entry's anchor if available
                pass  # compute below
            # Instead: scan the answer list HTML and extract chapter numbers from anchor IDs
            app_raw = _read(f"OEBPS/xhtml/{vol}_appc.xhtml", zf)
            if app_raw:
                soup_app = BeautifulSoup(app_raw, "lxml")
                app_body = soup_app.find("body")
                chapter_counts: dict[int, int] = {}
                current_ch = None
                current_count = 0
                for el in (app_body.find_all("p") if app_body else []):
                    if el.get("class") == ["quiz"]:
                        text = el.get_text(separator=" ", strip=True)
                        m = re.match(r"^\d+\s*\.\s*([A-Za-z][^.]*?)\s*[.?!]\s+(.*)", text)
                        if not m:
                            continue
                        anchor = el.find("a", recursive=True)
                        anchor_id = anchor.get("id", "") if anchor else ""
                        mc = re.match(r"ques(\d+)_", anchor_id)
                        if mc:
                            ch = int(mc.group(1))
                            if ch not in chapter_counts:
                                chapter_counts[ch] = 0
                            chapter_counts[ch] += 1
                running = 0
                for ch in sorted(chapter_counts):
                    offsets[ch] = running
                    running += chapter_counts[ch]
            vol_ch_offsets[vol] = offsets
        for vol, chapter_num, fname in sorted(chapters, key=lambda x: (x[0], x[1])):
            raw = _read(fname, zf)
            if not raw:
                continue
            soup = BeautifulSoup(raw, "lxml")
            body = soup.find("body")
            if body:
                offset = vol_ch_offsets.get(vol, {}).get(chapter_num, 0)
                all_q.extend(_parse_body(vol, body, chapter_num,
                                         vol_answers.get(vol, []), offset))
    return all_q
