"""Turn scraped pages into structured symbol entries using the Gemini API.

    python -m corpus.extract nabulsi --limit 3
    python -m corpus.extract ibn_shaheen --pages 50,51,52
    python -m corpus.extract --all

Uses the Interactions API (`client.interactions.create`), which replaced
`models.generate_content` — the older endpoint now 404s for new API keys.
Differences that matter here: the prompt goes in `input`, the schema goes in
`response_format`, `output_text` holds the result, and there is no `temperature`
any more, so determinism comes from `seed` instead.

Only dream-interpretation pages are sent (see corpus/filters.py). Pages that the
filter rejects are still recorded, with the reason, so a skip can be audited
rather than silently disappearing.

One output file per source page: reruns skip finished work and a failed page can
be redone alone. Provenance is written by this module, never by the model.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from . import books, filters, prompts
from .schema import RESPONSE

load_dotenv()

DATA = Path(__file__).parent / "data"
RAW = DATA / "raw"
OUT = DATA / "extracted"

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# Free-tier quota is metered per model, not per key: gemini-3.6-flash can be
# exhausted while gemini-3.5-flash still answers. So a 429 retires that model for
# the rest of the run and work continues on the next one, instead of stalling.
# Every model here was checked against the fabrication guard before being listed.
FALLBACKS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite",
    ).split(",")
    if m.strip()
]
MODELS = [MODEL] + [m for m in FALLBACKS if m != MODEL]

MAX_RETRIES = 3
SEED = 7  # fixed so a rerun of the same page is reproducible

# Models that returned 429 during this run.
_exhausted: set[str] = set()


def client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set — copy .env.example to .env")
    return genai.Client(api_key=key)


def _status(exc: Exception) -> int | None:
    """HTTP status behind an SDK exception, when there is one."""
    for attr in ("status_code", "code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def call_model(cli: genai.Client, system: str, payload: str) -> tuple[list[dict], str]:
    """One page in, (entries, model that produced them) out.

    `response_mime_type` is deliberately not passed: setting it alongside
    `response_format` is rejected with "responseFormat must be set when
    responseMimeType is set". The mime type belongs inside `response_format`.
    """
    last_error = None

    for model in MODELS:
        if model in _exhausted:
            continue
        for attempt in range(MAX_RETRIES):
            try:
                interaction = cli.interactions.create(
                    model=model,
                    input=payload,
                    system_instruction=system,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": RESPONSE,
                    },
                    generation_config={"seed": SEED, "thinking_level": "low"},
                    store=False,
                )
                return json.loads(interaction.output_text)["entries"], model
            except Exception as e:
                last_error = e
                status = _status(e)
                if status == 429:
                    _exhausted.add(model)
                    remaining = [m for m in MODELS if m not in _exhausted]
                    print(
                        f"    {model} out of quota; "
                        f"{'switching to ' + remaining[0] if remaining else 'no models left'}",
                        file=sys.stderr,
                    )
                    break  # next model, no point retrying this one
                # Other 4xx means the request itself is wrong; resending it
                # unchanged only wastes time.
                if status is not None and 400 <= status < 500:
                    raise RuntimeError(f"HTTP {status}: {str(e)[:200]}") from e
                wait = 5 * 2**attempt
                print(
                    f"    {model} attempt {attempt + 1}/{MAX_RETRIES}: "
                    f"{type(e).__name__}: {str(e)[:120]} — retrying in {wait}s",
                    file=sys.stderr,
                )
                time.sleep(wait)

    raise RuntimeError(f"all models exhausted or failing: {str(last_error)[:200]}")


def extract_page(cli: genai.Client, book: books.Book, page: dict) -> dict:
    entries, model_used = call_model(
        cli, prompts.LAYOUT_PROMPTS[book.layout], prompts.build(book, page)
    )

    # Provenance is stamped here, from the scrape, not from the model.
    source = {
        "book_slug": book.slug,
        "lens": book.lens,
        "book_ar": book.title_ar,
        "book_en": book.title_en,
        "author": book.author_display,
        "attribution_note": book.attribution_note,
        "chapter_ar": page.get("chapter"),
        "printed_page": page.get("printed_page"),
        "page_id": page["page_id"],
        "url": page["url"],
    }
    for entry in entries:
        entry["source"] = source
        entry["review"] = {"status": "pending", "scholar_id": None, "date": None}

    return {
        "book": book.slug,
        "page_id": page["page_id"],
        "model": model_used,  # which model actually produced this, after fallback
        "source_text": page["text"],  # kept so validation needs no second read
        "entries": entries,
    }


def run_book(
    book: books.Book,
    limit: int | None,
    only: set[int] | None,
    redo: bool,
    use_filter: bool,
) -> None:
    src_dir = RAW / book.slug
    if not src_dir.exists():
        raise SystemExit(f"no scraped pages for {book.slug} — run corpus.scrape first")
    out_dir = OUT / book.slug
    out_dir.mkdir(parents=True, exist_ok=True)

    cli = client()
    done = failed = cached = filtered = total_entries = 0

    for path in sorted(src_dir.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        if only is not None and page["page_id"] not in only:
            continue
        dest = out_dir / path.name
        if dest.exists() and not redo:
            cached += 1
            continue

        if use_filter:
            keep, reason = filters.classify(page)
            if not keep:
                dest.write_text(
                    json.dumps(
                        {
                            "book": book.slug,
                            "page_id": page["page_id"],
                            "skipped": reason,
                            "source_text": page["text"],
                            "entries": [],
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                filtered += 1
                continue

        if limit is not None and done >= limit:
            break

        try:
            result = extract_page(cli, book, page)
        except RuntimeError as e:
            print(f"  x page {page["page_id"]} failed: {str(e)[:200]}",
                  file=sys.stderr)
            failed += 1
            continue

        dest.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        done += 1
        total_entries += len(result["entries"])
        print(
            f"[{book.slug}] p{page['page_id']:<5} -> {len(result['entries']):>2} entries"
            f"   (total {total_entries})"
        )

    print(
        f"[{book.slug}] {done} pages extracted, {total_entries} entries, "
        f"{filtered} filtered as non-dream, {cached} cached, {failed} failed"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract symbol entries with Gemini")
    ap.add_argument("book", nargs="?", help=f"one of: {', '.join(books.BOOKS)}")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, help="stop after N newly extracted pages")
    ap.add_argument("--pages", help="comma-separated page ids")
    ap.add_argument("--redo", action="store_true", help="re-extract finished pages")
    ap.add_argument(
        "--no-filter",
        action="store_true",
        help="send every page, including non-dream content (not recommended)",
    )
    args = ap.parse_args()

    only = {int(x) for x in args.pages.split(",")} if args.pages else None

    if args.all:
        targets = list(books.BOOKS.values())
    elif args.book:
        targets = [books.get(args.book)]
    else:
        ap.error("pass a book slug or --all")

    print(f"model: {MODEL}")
    for book in targets:
        run_book(book, args.limit, only, args.redo, not args.no_filter)


if __name__ == "__main__":
    main()
