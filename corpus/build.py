"""Assemble the evaluation corpus from public legal sources.

Standard library only, so the corpus can be rebuilt on any machine with a
Python interpreter and no environment setup. Run from the repository root:

    python corpus/build.py          # everything
    python corpus/build.py irish    # Irish Acts only
    python corpus/build.py gdpr     # GDPR only

Source pages are downloaded into corpus/raw/ on first run and reused after
that, so repeated builds do not hit the source sites again. Delete that
directory to force a fresh download.

Provenance is recorded in corpus/README.md. Every document here is published
law. No client material is used at any point in this project.

Two things this file exists to get right, both of which fail silently:

Encoding. irishstatutebook.ie serves a single document in two encodings,
cp1252 navigation wrapped around a UTF-8 Act body, while declaring UTF-8 in
its meta tag. Decoding the page as either one corrupts the other half and
raises nothing. The Act container is sliced out of the raw bytes before
anything is decoded.

Line endings. The source pages are CRLF, Python translates newlines on write
unless told not to, and Git translates again on checkout. Character offsets
are computed against the output, so the same build must produce the same
bytes regardless of the platform it ran on.
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

ISB = "https://www.irishstatutebook.ie/eli"

# slug -> (title, source url). The print view carries the whole Act; the
# default view is only a table of contents.
IRISH_ACTS = {
    "data-protection-act-2018": (
        "Data Protection Act 2018",
        f"{ISB}/2018/act/7/enacted/en/print",
    ),
    "residential-tenancies-act-2004": (
        "Residential Tenancies Act 2004",
        f"{ISB}/2004/act/27/enacted/en/print",
    ),
    "employment-equality-act-1998": (
        "Employment Equality Act 1998",
        f"{ISB}/1998/act/21/enacted/en/print",
    ),
    "unfair-dismissals-act-1977": (
        "Unfair Dismissals Act 1977",
        f"{ISB}/1977/act/10/enacted/en/print",
    ),
}


def fetch_bytes(url: str) -> bytes:
    """Fetch without decoding.

    The caller decides the encoding, because these pages do not agree with
    their own meta tag.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def fetch(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", errors="replace")


def strip_html(fragment: str) -> str:
    """Reduce an HTML fragment to plain text, keeping line structure."""
    # The source pages use CRLF. Offsets are computed against the output, so
    # the line endings must not depend on the platform the build ran on.
    fragment = fragment.replace("\r\n", "\n").replace("\r", "\n")
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


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 with LF, on every platform."""
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"{path.name}: {len(text):,} chars")


def source_page(slug: str, url: str) -> bytes | None:
    """Return the raw page bytes, downloading once and caching in raw/."""
    cached = RAW / f"{slug}.html"
    if cached.exists():
        return cached.read_bytes()

    RAW.mkdir(exist_ok=True)
    print(f"downloading {slug}")
    try:
        data = fetch_bytes(url)
    except Exception as exc:
        print(f"  failed: {type(exc).__name__}: {exc}")
        return None
    cached.write_bytes(data)
    time.sleep(1)
    return data


def build_irish_acts() -> None:
    for slug, (title, url) in IRISH_ACTS.items():
        raw = source_page(slug, url)
        if raw is None:
            continue

        match = re.search(
            rb'(?is)<div[^>]*id="act"[^>]*>(.*?)<div[^>]*id="includedFooter"', raw
        )
        if not match:
            print(f"skip {slug}: Act container not found, the page layout may have changed")
            continue

        body = match.group(1).decode("utf-8", errors="replace")
        write_text(ROOT / f"{slug}.txt", f"{title}\n\n{strip_html(body)}")


def build_gdpr() -> None:
    """GDPR is published one Article per page on this mirror, so fetch each."""
    parts = ["Regulation (EU) 2016/679 (General Data Protection Regulation)", ""]
    got, missing = 0, []

    for n in range(1, 100):
        try:
            page = fetch(f"https://gdpr-info.eu/art-{n}-gdpr/")
        except Exception as exc:
            missing.append((n, type(exc).__name__))
            continue

        match = re.search(
            r'(?is)<div[^>]*class="entry-content"[^>]*>(.*?)(?:<footer|</article)', page
        )
        body = strip_html(match.group(1) if match else "")
        body = re.split(r"(?i)\n\s*Suitable Recitals\s*\n", body)[0].strip()
        if not body:
            missing.append((n, "empty"))
            continue

        parts += [f"===== Article {n} =====", body, ""]
        got += 1
        time.sleep(0.4)

    write_text(ROOT / "gdpr.txt", "\n".join(parts))
    print(f"  {got}/99 Articles")
    if missing:
        print("  missing:", missing[:10])


if __name__ == "__main__":
    import sys

    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "irish"):
        build_irish_acts()
    if which in ("all", "gdpr"):
        build_gdpr()
