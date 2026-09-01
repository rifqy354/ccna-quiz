#!/usr/bin/env python3
"""Inline OCG DIKTA extractor — quick test."""
import re, sys, sqlite3, zipfile

try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup

def s(t):
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\s+", " ", t)
    return (t.replace(chr(0xa0), " ").replace(chr(0x2019), "'").strip())

conn = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "data/ccna.db")
conn.execute("DELETE FROM questions WHERE source_book = ?", ("ocg",))
conn.commit()

count = 0
skipped = 0
epub = sys.argv[2] if len(sys.argv) > 2 else "/home/ubuntu/Kuliah/CCNA Jeremy/Books/CCNA 200-301 Official Cert Guide Library -- Wendell Odom, David Hucaby, Jason Gooley -- ( WeLib.org )/ccna-200-301-official-library-2nd.epub"
if len(sys.argv) > 3:
    epub = sys.argv[3]

with zipfile.ZipFile(epub) as zf:
    for fname in zf.namelist():
        if not re.search(r"OEBPS/xhtml/vol\d+_ch\d+\.xhtml$", fname):
            continue
        raw = zf.read(fname).decode("utf-8", errors="replace")
        soup = BeautifulSoup(raw, features="html.parser")
        body = soup.find("body")
        if not body:
            skipped += 1
            continue
        all_p = list(body.find_all("p"))
        i = 0
        while i < len(all_p):
            el = all_p[i]
            if el.get("class") == ["quiz"]:
                text = el.get_text(separator=" ", strip=True)
                m = re.match(r"^\d+\.\s+(.*)", text)
                if m:
                    q_text = s(m.group(1))
                    opts = []
                    j = i + 1
                    while j < len(all_p):
                        nxt = all_p[j]
                        cls = nxt.get("class", [])
                        if cls == ["quiz"]:
                            break
                        if cls == ["alpha"]:
                            t = nxt.get_text(strip=True)
                            if t:
                                opts.append(t)
                        j += 1
                    if len(opts) >= 2:
                        a = s(opts[0]) if len(opts) > 0 else ""
                        b = s(opts[1]) if len(opts) > 1 else ""
                        c = s(opts[2]) if len(opts) > 2 else ""
                        d = s(opts[3]) if len(opts) > 3 else ""
                        conn.execute(
                            "INSERT INTO questions (source_book, source_chapter, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, domain) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            ("ocg", fname.split("/")[-1].replace(".xhtml",""), q_text, a, b, c, d, "A", "", 1)
                        count += 1
                    i = j
                else:
                    i += 1
            else:
                i += 1

conn.commit()
conn.close()
print(f"Extracted {count} OCG DIKTA questions")
print(f"Skipped {skipped} files without body")
