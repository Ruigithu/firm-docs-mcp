"""Assemble the evaluation corpus from public legal sources.

Standard library only, so the corpus can be rebuilt on any machine with a
Python interpreter and no environment setup. Run from the repository root:

    python corpus/build.py          # everything
    python corpus/build.py irish    # Irish Acts only
    python corpus/build.py gdpr     # GDPR only

Provenance is recorded in corpus/README.md. Every document here is published
law. No client material is used at any point in this project.

Note on encoding: irishstatutebook.ie serves a single document in two
encodings, cp1252 navigation around a UTF-8 act body. Decoding the page as
either one corrupts the other half with no error raised. The act container is
therefore sliced out of the raw bytes before anything is decoded.
"""

import html
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

IRISH_ACTS = {
    "dpa_print": ("data-protection-act-2018", "Data Protection Act 2018"),
    "employment_equality_1998": ("employment-equality-act-1998", "Employment Equality Act 1998"),
    "residential_tenancies_2004": ("residential-tenancies-act-2004", "Residential Tenancies Act 2004"),
    "unfair_dismissals_1977": ("unfair-dismissals-act-1977", "Unfair Dismissals Act 1977"),
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def strip_html(fragment: str) -> str:
    """Reduce an HTML fragment to plain text, keeping line structure."""
    fragment = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", fragment)
    # The Irish Statute Book renders both languages; keep the English.
    fragment = re.sub(r'(?is)<[^>]*class="irish_language"[^>]*>.*?</[a-z]+>', " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h[1-6]>", "\n", fragment)
    fragment = re.sub(r"(?s)<[^>]+>", " ", fragment)
    fragment = html.unescape(fragment)
    fragment = fragment.replace(" ", " ")
    # Soft hyphens are invisible but break substring matching, and this
    # corpus is searched by substring. Remove them at ingest.
    fragment = fragment.replace("­", "")
    fragment = re.sub(r"[ \t]+", " ", fragment)
    fragment = re.sub(r"\n[ \t]+", "\n", fragment)
    fragment = re.sub(r"\n{3,}", "\n\n", fragment)
    return fragment.strip()


def build_irish_acts() -> None:
    for stem, (slug, title) in IRISH_ACTS.items():
        src = RAW / f"{stem}.html"
        if not src.exists():
            print(f"skip {slug}: {src.name} not downloaded")
            continue
        # The page is mixed encoding: cp1252 site chrome wrapped around a
        # UTF-8 act body. Slice the container out of the raw bytes first, then
        # decode that fragment as what it actually is. Decoding the whole page
        # as either encoding corrupts the other half, and does so silently.
        raw = src.read_bytes()
        m = re.search(
            rb'(?is)<div[^>]*id="act"[^>]*>(.*?)<div[^>]*id="includedFooter"', raw
        )
        if not m:
            print(f"skip {slug}: act container not found")
            continue
        body = m.group(1).decode("utf-8", errors="replace")
        text = f"{title}\n\n{strip_html(body)}"
        out = ROOT / f"{slug}.txt"
        out.write_text(text, encoding="utf-8")
        parts = len(re.findall(r"(?m)^\s*\d+\.", text))
        print(f"{out.name}: {out.stat().st_size:,} bytes, ~{parts} numbered provisions")


def build_gdpr() -> None:
    """GDPR is published one article per page on this mirror, so fetch each."""
    out = ROOT / "gdpr.txt"
    parts = ["Regulation (EU) 2016/679 (General Data Protection Regulation)", ""]
    got, missing = 0, []
    for n in range(1, 100):
        try:
            page = fetch(f"https://gdpr-info.eu/art-{n}-gdpr/")
        except Exception as exc:
            missing.append((n, type(exc).__name__))
            continue
        m = re.search(
            r'(?is)<div[^>]*class="entry-content"[^>]*>(.*?)(?:<footer|</article)', page
        )
        body = strip_html(m.group(1) if m else "")
        body = re.split(r"(?i)\n\s*Suitable Recitals\s*\n", body)[0].strip()
        if not body:
            missing.append((n, "empty"))
            continue
        parts += [f"===== Article {n} =====", body, ""]
        got += 1
        time.sleep(0.4)
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"gdpr.txt: {out.stat().st_size:,} bytes, {got}/99 articles")
    if missing:
        print("  missing:", missing[:10])


if __name__ == "__main__":
    import sys

    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "irish"):
        build_irish_acts()
    if which in ("all", "gdpr"):
        build_gdpr()
