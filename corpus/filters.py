"""Keep only dream-interpretation content.

The source books are not purely ta'bir. They open with prefaces, the editor's
introduction and the author's biography, and in places drift into narration
chains, poetry and anecdotes. None of that belongs in the corpus: it adds no
symbol coverage, it dilutes retrieval, and it costs extraction spend to process.

Filtering happens twice. This module is the cheap pass — pure string matching, no
API call — and it runs before a page is ever sent to the model. The prompt then
carries the expensive pass, telling the model to return no entries for a passage
that is not symbol interpretation.

    python -m corpus.filters --all          # report what would be dropped
    python -m corpus.filters nabulsi -v     # list the dropped pages
"""

import argparse
import json
from pathlib import Path

from . import books
from .arabic import normalize

DATA = Path(__file__).parent / "data"
RAW = DATA / "raw"

# Vocabulary that ta'bir prose is saturated with and other content is not.
# Stored normalised, because that is how page text is compared.
_DREAM_WORDS = [
    "رؤيا",      # vision
    "منام",      # dream / sleep
    "حلم",       # dream
    "تأويل",     # interpretation
    "تعبير",     # interpretation
    "رأى",       # "saw" — covers من رأى / فإن رأى / ومن رأى
    "يدل على",   # "indicates"
    "دليل على",  # "is a sign of"
]
DREAM_WORDS = [normalize(w) for w in _DREAM_WORDS]

# Vocabulary in a CHAPTER TITLE that marks the whole chapter as ta'bir. Pages
# inside such a chapter are kept even when the page itself never says "dream" —
# Ibn Sirin's sura chapter, for instance, runs page after page of
# "ومن قرأ سورة كذا" with no dream vocabulary at all, and it is pure symbol
# content. Losing that costs far more than a wasted extraction call on a page
# the model will correctly return no entries for.
_CHAPTER_WORDS = ["تأويل", "رؤيا", "رؤية", "منام", "تعبير", "حلم"]
CHAPTER_WORDS = [normalize(w) for w in _CHAPTER_WORDS]

# Shamela prefixes every breadcrumb with this, so it carries no information and
# must be stripped before the heading is inspected.
_BOILERPLATE = normalize("فهرس الكتاب")

# Headings that mark apparatus rather than content. Deliberately narrow: a
# chapter called مقدمة عن الرؤيا ("introduction on visions") is dream material and
# must survive, so prefaces are judged on their vocabulary instead of their title.
_SKIP_HEADINGS = [
    "ترجمة المؤلف",   # author biography
    "فهرس المحتويات", # table of contents
    "الفهارس",        # back-matter indexes
    "فهرس الموضوعات", # subject index
    "المصادر والمراجع",  # bibliography
]
SKIP_HEADINGS = [normalize(h) for h in _SKIP_HEADINGS]

# A page must hit dream vocabulary at least this many times to be kept.
MIN_HITS = 3
# ...and be at least this long. Shorter pages are running heads or stubs.
MIN_CHARS = 200


def score(page: dict) -> tuple[int, int]:
    """(total dream-word occurrences, distinct dream words present)."""
    text = normalize(page.get("text", ""))
    total = distinct = 0
    for word in DREAM_WORDS:
        n = text.count(word)
        if n:
            total += n
            distinct += 1
    return total, distinct


def classify(page: dict) -> tuple[bool, str]:
    """Decide whether this page is dream-interpretation content.

    Returns (keep, reason). The reason is recorded for dropped pages so the
    threshold can be audited rather than trusted.
    """
    text = page.get("text", "")
    if len(text) < MIN_CHARS:
        return False, "too_short"

    heading = normalize(page.get("heading") or "") + " " + normalize(page.get("chapter") or "")
    heading = heading.replace(_BOILERPLATE, " ")
    for skip in SKIP_HEADINGS:
        if skip and skip in heading:
            return False, f"apparatus:{skip}"

    total, distinct = score(page)

    # Inside an explicitly named ta'bir chapter, keep the page and let the model
    # judge the passage. Outside one, the page must carry the vocabulary itself.
    if any(word in heading for word in CHAPTER_WORDS):
        return True, f"dream_chapter:{total}/{distinct}"

    if total < MIN_HITS:
        return False, f"low_dream_vocab:{total}"

    return True, f"ok:{total}/{distinct}"


def report(book: books.Book, verbose: bool) -> dict:
    src = RAW / book.slug
    if not src.exists():
        print(f"[{book.slug}] not scraped yet")
        return {}

    kept, dropped, reasons = 0, [], {}
    for path in sorted(src.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        keep, reason = classify(page)
        if keep:
            kept += 1
        else:
            dropped.append((page["page_id"], reason, (page.get("heading") or "")[:50]))
            key = reason.split(":")[0]
            reasons[key] = reasons.get(key, 0) + 1

    total = kept + len(dropped)
    print(f"[{book.slug}] keep {kept}/{total} pages, drop {len(dropped)}")
    for reason, n in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {n}")
    if verbose:
        for page_id, reason, heading in dropped:
            print(f"    p{page_id:<5} {reason:<28} {heading}")

    return {"book": book.slug, "kept": kept, "dropped": len(dropped), "reasons": reasons}


def main() -> None:
    ap = argparse.ArgumentParser(description="Report which scraped pages are dream content")
    ap.add_argument("book", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true", help="list every dropped page")
    args = ap.parse_args()

    if args.all:
        targets = list(books.BOOKS.values())
    elif args.book:
        targets = [books.get(args.book)]
    else:
        ap.error("pass a book slug or --all")

    for book in targets:
        report(book, args.verbose)


if __name__ == "__main__":
    main()
