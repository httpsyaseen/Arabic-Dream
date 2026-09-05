"""Shamela scraper.

Walks a book page by page, caching each page to disk so reruns are free and an
interrupted run resumes where it stopped. Rate limited by SCRAPE_DELAY.

    python -m corpus.scrape nabulsi
    python -m corpus.scrape --all
    python -m corpus.scrape nabulsi --start 20 --limit 5   # sample a few pages

Page shape on Shamela: the body lives in `div.nass`, which carries
`data-page-id` (the id in the URL) and `data-page-num` (the printed page number
of the physical edition). The printed number is what a scholar needs in order to
check a citation against the paper book, so both are recorded.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from . import sources
from .arabic import strip_parens

load_dotenv()

BASE = "https://shamela.ws"
ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "context"
DELAY = float(os.getenv("SCRAPE_DELAY", "1.5"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en;q=0.8",
}

# Stop walking after this many consecutive pages come back missing or empty.
MISS_LIMIT = 5


def fetch(url: str, session: requests.Session, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"  ! {url} {type(e).__name__}", file=sys.stderr)
            time.sleep(DELAY * (attempt + 2))
            continue
        if r.status_code == 404:
            return None
        if r.status_code == 200:
            return r.text
        print(f"  ! {url} HTTP {r.status_code}", file=sys.stderr)
        time.sleep(DELAY * (attempt + 2))
    return None


def scrape_toc(book: sources.Source, session: requests.Session) -> list[dict]:
    """Chapter headings and the page id each one starts on."""
    html = fetch(f"{BASE}/book/{book.shamela_id}", session)
    if not html:
        raise SystemExit(f"could not load TOC for {book.slug}")
    soup = BeautifulSoup(html, "lxml")
    chapters, seen = [], set()
    for a in soup.select(f"a[href*='/book/{book.shamela_id}/']"):
        href = a.get("href", "")
        tail = href.rstrip("/").rsplit("/", 1)[-1]
        if not tail.isdigit():
            continue
        page_id = int(tail)
        title = a.get_text(" ", strip=True)
        if not title or page_id in seen:
            continue
        seen.add(page_id)
        chapters.append({"page_id": page_id, "title_ar": title})
    chapters.sort(key=lambda c: c["page_id"])
    return chapters


def chapter_for(page_id: int, chapters: list[dict]) -> str | None:
    """The last chapter heading that starts at or before this page."""
    current = None
    for c in chapters:
        if c["page_id"] <= page_id:
            current = c["title_ar"]
        else:
            break
    return current


def parse_page(html: str, book: sources.Source) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    nass = soup.select_one("div.nass")
    if nass is None:
        return None

    # Drop the per-paragraph copy-link buttons before reading any text.
    for junk in nass.select("a.btn_tag, span.fa"):
        junk.decompose()

    text = nass.get_text("\n", strip=True)
    if not text:
        return None

    paragraphs = []
    for p in nass.find_all("p"):
        body = p.get_text(" ", strip=True)
        if not body:
            continue
        # In dictionary books the headword sits in the first span.c2; in prose
        # books span.c2 marks a speaker or a "whoever sees" clause instead.
        marker = p.select_one("span.c2")
        paragraphs.append(
            {
                "marker": strip_parens(marker.get_text(strip=True)) if marker else None,
                "text": body,
            }
        )
    if not paragraphs:
        paragraphs = [{"marker": None, "text": text}]

    heading_el = soup.select_one("div.heading-title")
    heading = heading_el.get_text(" ", strip=True) if heading_el else None
    if heading:
        heading = heading.replace("مسار الصفحة الحالية:", "").strip()

    return {
        "book": book.slug,
        "shamela_id": book.shamela_id,
        "page_id": int(nass.get("data-page-id") or 0),
        "printed_page": nass.get("data-page-num"),
        "heading": heading,
        "text": text,
        "paragraphs": paragraphs,
    }


def scrape_book(book: sources.Source, start: int, limit: int | None, refetch: bool) -> None:
    session = requests.Session()
    out_dir = CONTEXT / book.slug / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    toc_path = CONTEXT / book.slug / "toc.json"
    if toc_path.exists() and not refetch:
        chapters = json.loads(toc_path.read_text(encoding="utf-8"))
    else:
        chapters = scrape_toc(book, session)
        toc_path.write_text(
            json.dumps(chapters, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        time.sleep(DELAY)
    print(f"[{book.slug}] {len(chapters)} chapters in TOC")

    page_id, misses, written, cached = start, 0, 0, 0
    while misses < MISS_LIMIT:
        if limit is not None and (written + cached) >= limit:
            break
        dest = out_dir / f"{page_id:05d}.json"
        if dest.exists() and not refetch:
            cached += 1
            misses = 0
            page_id += 1
            continue

        html = fetch(f"{BASE}/book/{book.shamela_id}/{page_id}", session)
        page = parse_page(html, book) if html else None
        if page is None:
            misses += 1
            page_id += 1
            time.sleep(DELAY)
            continue

        page["chapter"] = chapter_for(page_id, chapters)
        page["url"] = f"{BASE}/book/{book.shamela_id}/{page_id}"
        dest.write_text(
            json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        written += 1
        misses = 0
        if written % 25 == 0:
            print(f"[{book.slug}] page {page_id} ({written} fetched)")
        page_id += 1
        time.sleep(DELAY)

    print(f"[{book.slug}] done — {written} fetched, {cached} already cached")


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape classical dream texts from Shamela")
    ap.add_argument("book", nargs="?", help=f"one of: {', '.join(sources.SOURCES)}")
    ap.add_argument("--all", action="store_true", help="scrape every registered book")
    ap.add_argument("--start", type=int, default=1, help="first page id")
    ap.add_argument("--limit", type=int, help="stop after N pages (sampling)")
    ap.add_argument("--refetch", action="store_true", help="ignore the disk cache")
    args = ap.parse_args()

    if args.all:
        targets = sources.scraped()
    elif args.book:
        targets = [sources.get(args.book)]
    else:
        ap.error("pass a book slug or --all")

    for book in targets:
        if book.shamela_id is None:
            continue
        scrape_book(book, args.start, args.limit, args.refetch)


if __name__ == "__main__":
    main()
