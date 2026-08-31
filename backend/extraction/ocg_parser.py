"""Parser for OCG Library EPUB DIKTA quizzes."""
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup

from .models import ExtractedQuestion

# OCG chapters mapped to domains
# Vol 1: ch01-17, Vol 2: ch18-31
VOL1_CHAPTERS = {
    "vol1_ch01": (1, "Network Fundamentals"),
    "vol1_ch02": (1, "Network Models"),
    "vol1_ch03": (2, "LANs"),
    "vol1_ch04": (2, "Cisco LAN Switching"),
    "vol1_ch05": (3, "IP Addressing"),
    "vol1_ch06": (3, "IP Subnetting"),
    "vol1_ch07": (3, "IPv4 Routing"),
    "vol1_ch08": (3, "IPv6"),
    "vol1_ch09": (4, "Transport Layer"),
    "vol1_ch10": (4, "Applications"),
    "vol1_ch11": (4, "Network Services"),
    "vol1_ch12": (5, "Security Fundamentals"),
    "vol1_ch13": (6, "Automation"),
    "vol1_ch14": (6, "Programmability"),
    "vol1_ch15": (6, "JSON and REST"),
    "vol1_ch16": (6, "YAML and Ansible"),
    "vol1_ch17": (6, "DNA Center"),
}

VOL2_CHAPTERS = {
    "vol2_ch18": (4, "IP Services"),
    "vol2_ch19": (4, "QoS"),
    "vol2_ch20": (4, "Network Management"),
    "vol2_ch21": (4, "Network Optimization"),
    "vol2_ch22": (5, "Security"),
    "vol2_ch23": (5, "AAA"),
    "vol2_ch24": (5, "Layer 2 Security"),
    "vol2_ch25": (5, "IPv4 ACLs"),
    "vol2_ch26": (5, "Wireless Security"),
    "vol2_ch27": (5, "Wireless Architecture"),
    "vol2_ch28": (6, "SDN and Controllers"),
    "vol2_ch29": (6, "Network Automation"),
    "vol2_ch30": (6, "Network Automation Tools"),
    "vol2_ch31": (6, "Programmability"),
}

OCG_CHAPTER_MAP = {**VOL1_CHAPTERS, **VOL2_CHAPTERS}


def _extract_epub(epub_path: str) -> Path:
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(epub_path, "r") as z:
        z.extractall(tmp)
    return tmp


def _find_dikta_section(soup: BeautifulSoup, anchor_id: str):
    """Find the DIKTA quiz section by anchor ID like 'ch01lev1sec1'."""
    section = soup.find(id=anchor_id)
    if section:
        return section
    # Fall back to looking for headers containing "DIKTA"
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if "dikta" in h.get_text(strip=True).lower():
            return h
    return None


def _parse_ocg_dikta_from_section(
    section,
    chapter_key: str,
    domain: int,
    chapter_name: str,
    images_dir: str,
) -> list[ExtractedQuestion]:
    """Parse DIKTA questions from a BeautifulSoup section."""
    questions = []
    question_num = 0

    # Walk through elements in the section
    for elem in section.find_all_next(["p", "div"], limit=500):
        text = elem.get_text(strip=True)

        # Stop at next major section (usually another h2/h3)
        if elem.name in ["h1", "h2", "h3"]:
            if elem.find_previous(["h1", "h2"]) and elem != section:
                break

        m = re.match(r"^(\d+)\.\s+(.*)", text, re.DOTALL)
        if not m:
            continue

        question_num = int(m.group(1))
        question_text = m.group(2).strip()

        block_text = elem.get_text(separator=" ", strip=True)

        opt_a = opt_b = opt_c = opt_d = ""
        a_m = re.search(r"[Aa]\.\s*([^\n]+?)(?=\s*[Bb]\.\s|\s*[Cc]\.\s|\s*[Dd]\.\s|$)", block_text)
        b_m = re.search(r"[Bb]\.\s*([^\n]+?)(?=\s*[Cc]\.\s|\s*[Dd]\.\s|$)", block_text)
        c_m = re.search(r"[Cc]\.\s*([^\n]+?)(?=\s*[Dd]\.\s|$)", block_text)
        d_m = re.search(r"[Dd]\.\s*([^\n]+)", block_text)

        if a_m:
            opt_a = a_m.group(1).strip()
        if b_m:
            opt_b = b_m.group(1).strip()
        if c_m:
            opt_c = c_m.group(1).strip()
        if d_m:
            opt_d = d_m.group(1).strip()

        if not (opt_a and opt_b and opt_c and opt_d):
            continue

        # Handle image
        img_tag = elem.find("img")
        img_filename = None
        if img_tag and img_tag.get("src"):
            src = img_tag["src"]
            img_filename = f"{chapter_key}_q{question_num}_{Path(src).name}"

        questions.append(ExtractedQuestion(
            source_book="ocg_dikta",
            source_chapter=chapter_key,
            book_title=f"OCG Library - {chapter_name}",
            domain=domain,
            sub_domain=None,
            sub_domain_name=chapter_name,
            question_text=question_text[:1000],
            question_image=img_filename,
            option_a=opt_a[:500],
            option_b=opt_b[:500],
            option_c=opt_c[:500],
            option_d=opt_d[:500],
            correct_option="A",  # OCG DIKTA answers need to be mapped from review section
            explanation="",
            ocg_chapter_ref=chapter_key,
            ocg_section_ref=None,
            difficulty=2,
        ))

    return questions


def parse_ocg_epub(epub_path: str, images_dir: str) -> list[ExtractedQuestion]:
    """Parse OCG Library EPUB DIKTA quizzes and return all questions."""
    tmp = _extract_epub(epub_path)

    all_questions = []

    for chapter_key, (domain, chapter_name) in OCG_CHAPTER_MAP.items():
        chapter_file = None
        for ext in ["xhtml", "html", "htm"]:
            candidate = tmp / f"{chapter_key}.{ext}"
            if candidate.exists():
                chapter_file = candidate
                break

        if not chapter_file:
            for f in tmp.rglob(f"*{chapter_key}*"):
                if f.suffix in (".xhtml", ".html", ".htm"):
                    chapter_file = f
                    break

        if not chapter_file:
            continue

        try:
            soup = BeautifulSoup(chapter_file.read_text(encoding="utf-8"), "lxml")

            # Try to find DIKTA section anchor
            anchor_id = chapter_key.replace("_", "") + "lev1sec1"
            section = _find_dikta_section(soup, anchor_id)

            if section:
                qs = _parse_ocg_dikta_from_section(
                    section, chapter_key, domain, chapter_name, images_dir
                )
                all_questions.extend(qs)
                print(f"  {chapter_key}: {len(qs)} questions")
        except Exception as e:
            print(f"  ERROR parsing {chapter_key}: {e}")

    return all_questions
