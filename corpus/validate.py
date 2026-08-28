"""Fabrication guard.

Every entry claims to quote a classical book. This checks that claim against the
scraped source text before the entry is allowed anywhere near a scholar's review
queue, let alone a user. An entry whose `quote_ar` is not actually present in its
source page is discarded — no warning, no soft pass, no manual override.

Comparison is done on the normalised form (see corpus/arabic.py) because the
model reliably differs from Shamela in diacritics and hamza seating while
reproducing the wording exactly. What we store and display stays verbatim.

    python -m corpus.validate nabulsi
    python -m corpus.validate --all --report
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from . import books
from .arabic import contains
from .schema import CATEGORIES, VALENCE

DATA = Path(__file__).parent / "data"
EXTRACTED = DATA / "extracted"
VALIDATED = DATA / "validated"
REJECTED = DATA / "rejected"

REQUIRED = ["symbol_ar", "symbol_en", "category", "quote_ar", "quote_en",
            "meaning_summary", "valence"]

MIN_QUOTE_CHARS = 15  # anything shorter is not a citation


def check(entry: dict, source_text: str, layout: str) -> list[str]:
    """Return a list of reasons this entry must be rejected; empty means it passes."""
    problems = []

    for field in REQUIRED:
        if not str(entry.get(field, "")).strip():
            problems.append(f"missing:{field}")

    quote = entry.get("quote_ar", "")
    if len(quote.strip()) < MIN_QUOTE_CHARS:
        problems.append("quote_too_short")
    elif not contains(source_text, quote):
        problems.append("quote_not_in_source")

    # In a dictionary book the headword is printed on the page, so it must be
    # found there. In a prose book there is no headword — the symbol name is an
    # editorial label the model coins to describe the passage ("circling the
    # graves"), and requiring it verbatim would reject correct entries. The
    # quote above is the citation either way; the label is not.
    symbol_ar = entry.get("symbol_ar", "")
    if layout == "dictionary" and symbol_ar and not contains(source_text, symbol_ar):
        problems.append("symbol_not_in_source")

    if entry.get("category") not in CATEGORIES:
        problems.append("bad_category")
    if entry.get("valence") not in VALENCE:
        problems.append("bad_valence")

    for i, cond in enumerate(entry.get("conditions") or []):
        cq = (cond.get("quote_ar") or "").strip()
        if cq and not contains(source_text, cq):
            problems.append(f"condition_quote_not_in_source:{i}")
        if not (cond.get("if_en") or "").strip() or not (cond.get("then_en") or "").strip():
            problems.append(f"condition_incomplete:{i}")

    return problems


def validate_book(book: books.Book, verbose: bool) -> dict:
    src_dir = EXTRACTED / book.slug
    if not src_dir.exists():
        raise SystemExit(f"nothing extracted for {book.slug}")

    passed, rejected = [], []
    reasons = Counter()

    for path in sorted(src_dir.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        source_text = page["source_text"]
        for entry in page["entries"]:
            problems = check(entry, source_text, book.layout)
            if problems:
                reasons.update(problems)
                rejected.append({"page_id": page["page_id"], "problems": problems,
                                 "entry": entry})
                if verbose:
                    print(f"  reject p{page['page_id']} "
                          f"{entry.get('symbol_en', '?')}: {', '.join(problems)}")
            else:
                passed.append(entry)

    VALIDATED.mkdir(parents=True, exist_ok=True)
    REJECTED.mkdir(parents=True, exist_ok=True)
    (VALIDATED / f"{book.slug}.json").write_text(
        json.dumps(passed, ensure_ascii=False, indent=2), encoding="utf-8")
    (REJECTED / f"{book.slug}.json").write_text(
        json.dumps(rejected, ensure_ascii=False, indent=2), encoding="utf-8")

    total = len(passed) + len(rejected)
    rate = (len(passed) / total * 100) if total else 0.0
    print(f"[{book.slug}] {len(passed)}/{total} passed ({rate:.1f}%)")
    if reasons:
        for reason, n in reasons.most_common():
            print(f"    {reason}: {n}")

    return {"book": book.slug, "passed": len(passed), "rejected": len(rejected),
            "pass_rate": round(rate, 1), "reasons": dict(reasons)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify every quote against its source")
    ap.add_argument("book", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="print each rejection")
    ap.add_argument("--report", action="store_true", help="write data/validation_report.json")
    args = ap.parse_args()

    if args.all:
        targets = list(books.BOOKS.values())
    elif args.book:
        targets = [books.get(args.book)]
    else:
        ap.error("pass a book slug or --all")

    summaries = []
    for book in targets:
        try:
            summaries.append(validate_book(book, args.verbose))
        except SystemExit as e:
            print(e)

    if args.report:
        (DATA / "validation_report.json").write_text(
            json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print("wrote corpus/data/validation_report.json")


if __name__ == "__main__":
    main()
