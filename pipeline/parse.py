"""Turn each book's raw text into uniform chunks.

Four books, four physical layouts, one output shape. Everything downstream —
indexing, searching, citing — reads chunks and never needs to know which kind of
book a chunk came from.

    python -m pipeline.parse --all
    python -m pipeline.parse nabulsi

Reads   context/<slug>/raw/
Writes  context/<slug>/chunks.json
        context/<slug>/source.json   (metadata, for humans and for the API)

Every chunk:

    {
      "source": "nabulsi",
      "kind": "symbol" | "passage" | "hadith",
      "symbol_ar": "حية",          # only when kind == "symbol"
      "text_ar": "...",             # verbatim; never normalised
      "chapter_ar": "باب الحاء",
      "printed_page": "94",         # page of the physical printed edition
      "url": "https://shamela.ws/book/1217/91"
    }

`text_ar` is always verbatim. Normalisation happens only at match time and is
never written back into stored text, because stored text is what gets cited.

See docs/PARSING.md for why each layout is handled the way it is.
"""

import argparse
import json
import re
from pathlib import Path

from . import sources
from .arabic import normalize, strip_parens

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "context"

# --- shared limits -----------------------------------------------------------

PASSAGE_MIN = 80      # shorter than this is a fragment, not a ruling
PASSAGE_MAX = 700     # longer buries the relevant sentence in the prompt
HEADWORD_MIN = 3
HEADWORD_MAX = 30
HEADWORD_MAX_WORDS = 4
BODY_MIN = 30

# Classical prose is barely punctuated. These are the phrases that actually begin
# a new ruling, so they are the cut points rather than full stops.
RULING_START = re.compile(
    r"(?=(?:فإن رأى|وإن رأى|ومن رأى|من رأى|وإذا رأى|وقال|فمن رأى|وأما|ومن قرأ))"
)

# --- keeping only dream content ---------------------------------------------
# The books are not purely ta'bir. They open with prefaces, an editor's
# introduction and the author's biography, and drift into chains of narration
# and poetry. None of that belongs in a dream corpus: it adds no symbol
# coverage and dilutes retrieval.
#
# Vocabulary a page must carry to count as interpretation:
#   رؤيا (ru'ya = vision) · منام (manam = dream) · حلم (hulm = dream)
#   تأويل / تعبير (ta'wil / ta'bir = interpretation) · رأى (ra'a = he saw)
DREAM_WORDS = [normalize(w) for w in
               ("رؤيا", "منام", "حلم", "تأويل", "تعبير", "رأى", "يدل على", "دليل على")]

# Vocabulary in a CHAPTER TITLE that makes the whole chapter ta'bir. Pages
# inside such a chapter are kept even when the page itself never says "dream" —
# Ibn Sirin's chapter on Qur'anic suras runs page after page of
# "ومن قرأ سورة كذا" ("whoever recites sura X") with no dream vocabulary at all,
# and it is pure symbol content. Losing that costs far more than keeping a
# digression the chunker will simply never match.
CHAPTER_WORDS = [normalize(w) for w in ("تأويل", "رؤيا", "رؤية", "منام", "تعبير", "حلم")]

# Apparatus rather than content. Deliberately narrow: a chapter called
# مقدمة عن الرؤيا ("introduction on visions") IS dream material, so prefaces are
# judged on their vocabulary rather than their title.
APPARATUS = [normalize(w) for w in
             ("ترجمة المؤلف", "فهرس المحتويات", "الفهارس", "فهرس الموضوعات",
              "المصادر والمراجع")]
# Shamela prefixes every breadcrumb with this, so it carries no information.
_BOILERPLATE = normalize("فهرس الكتاب")

MIN_DREAM_HITS = 3
MIN_PAGE_CHARS = 200


def is_dream_page(page: dict) -> bool:
    """Whether a scraped page is dream-interpretation content."""
    text = page.get("text", "")
    if len(text) < MIN_PAGE_CHARS:
        return False

    heading = normalize(f"{page.get('heading') or ''} {page.get('chapter') or ''}")
    heading = heading.replace(_BOILERPLATE, " ")
    if any(a in heading for a in APPARATUS):
        return False
    if any(w in heading for w in CHAPTER_WORDS):
        return True

    norm = normalize(text)
    return sum(norm.count(w) for w in DREAM_WORDS) >= MIN_DREAM_HITS

# OCR of scanned books leaves ornamental borders as stray Latin and broken glyphs.
_ARABIC_CHAR = re.compile(r"[؀-ۿ]")
_OCR_NOISE = re.compile(r"[ـ]|\(\s*[0-9A-Za-z/:.\s]{1,12}\s*\)|[«»]")


def _split_long(text: str) -> list[str]:
    out = []
    while len(text) > PASSAGE_MAX:
        out.append(text[:PASSAGE_MAX])
        text = text[PASSAGE_MAX:]
    if len(text) >= PASSAGE_MIN:
        out.append(text)
    return out


# --- parsers -----------------------------------------------------------------


def parse_shamela_dictionary(src: sources.Source, pages: list[dict]) -> list[dict]:
    """Alphabetical dictionary: Shamela marks each headword in its own span.

    This is the only layout that yields *symbols*, and so it alone defines the
    vocabulary the whole search is built on. A headword can recur across pages;
    the fullest treatment wins.
    """
    best: dict[str, dict] = {}
    for page in pages:
        if not is_dream_page(page):
            continue
        for para in page["paragraphs"]:
            head = (para.get("marker") or "").strip()
            body = para["text"].strip()
            if not head or len(body) < BODY_MIN:
                continue

            key = normalize(strip_parens(head))
            if not (HEADWORD_MIN <= len(key) <= HEADWORD_MAX):
                continue
            # Shamela sometimes wraps a whole sentence in a headword span
            # ("وقد ضمن الحسن بن الحسين الخلال…"). Those are not symbols.
            if len(key.split()) > HEADWORD_MAX_WORDS:
                continue

            prev = best.get(key)
            if prev and len(prev["text_ar"]) >= len(body):
                continue
            best[key] = {
                "source": src.slug,
                "kind": "symbol",
                "symbol_ar": strip_parens(head),
                "text_ar": body,
                "chapter_ar": page.get("chapter"),
                "printed_page": page.get("printed_page"),
                "url": page.get("url", ""),
            }
    return list(best.values())


def parse_shamela_prose(src: sources.Source, pages: list[dict]) -> list[dict]:
    """Topical prose with no headwords: cut at the phrases that start a ruling."""
    out = []
    for page in pages:
        if not is_dream_page(page):
            continue
        for part in RULING_START.split(page["text"]):
            part = " ".join(part.split())
            if len(part) < PASSAGE_MIN:
                continue
            for chunk in _split_long(part):
                out.append({
                    "source": src.slug,
                    "kind": "passage",
                    "text_ar": chunk,
                    "chapter_ar": page.get("chapter"),
                    "printed_page": page.get("printed_page"),
                    "url": page.get("url", ""),
                })
    return out


def parse_shamela_hadith(src: sources.Source, pages: list[dict]) -> list[dict]:
    """Hadith on dream etiquette, selected by chapter title.

    The chapters of this book are exactly the topics the classification and adab
    layer needs, so the chapter title is a better selector than the body text.
    """
    out, seen = [], set()
    for page in pages:
        chapter = page.get("chapter") or ""
        if not any(topic in chapter for topic in src.topics):
            continue
        for para in page["paragraphs"]:
            text = " ".join(para["text"].split())
            if not (60 <= len(text) <= 600):
                continue
            fingerprint = normalize(text)[:80]   # the same hadith recurs verbatim
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            out.append({
                "source": src.slug,
                "kind": "hadith",
                "text_ar": text,
                "chapter_ar": chapter,
                "printed_page": page.get("printed_page"),
                "url": page.get("url", ""),
            })
    return out


def _ocr_clean(raw: str) -> list[str]:
    """Recover readable Arabic lines from a scanned book.

    Scans of decorated editions turn their ornamental borders into runs of stray
    Latin characters and broken glyphs. Filtering on the ratio of Arabic letters
    keeps the text and drops the ornament; on the Shia volume this recovers about
    62% of the file, and what it drops really is noise.
    """
    kept = []
    for line in raw.split("\n"):
        line = " ".join(_OCR_NOISE.sub(" ", line).split())
        if len(line) < 25:
            continue
        letters = [c for c in line if c.isalpha()]
        if not letters:
            continue
        if sum(1 for c in letters if _ARABIC_CHAR.match(c)) / len(letters) < 0.90:
            continue
        words = line.split()
        if len(words) < 5:
            continue
        # Ornament fragments survive as runs of one- and two-letter tokens.
        if sum(len(w) for w in words) / len(words) < 2.5:
            continue
        kept.append(line)
    return kept


# Blocks are glued together up to this length before a chunk is emitted. Without
# a target, OCR-rescued lines (which are one printed line each) would each become
# their own chunk and carry no context.
PASSAGE_TARGET = 420


def parse_textfile(src: sources.Source, _pages) -> list[dict]:
    """Plain-text sources: no page structure, so accumulate text into passages."""
    out = []
    raw_dir = CONTEXT / src.slug / "raw"

    def emit(text: str) -> None:
        for chunk in _split_long(text):
            out.append({
                "source": src.slug,
                "kind": "passage",
                "text_ar": chunk,
                "chapter_ar": None,
                "printed_page": None,
                "url": src.source_url,
            })

    for name in src.files:
        path = raw_dir / name
        if not path.exists():
            print(f"    ! missing {path}")
            continue

        text = path.read_text(encoding="utf-8")
        if src.needs_ocr_clean:
            # A scan of a decorated edition: rescue lines before anything else,
            # since its "paragraphs" are ornament as often as text.
            blocks = _ocr_clean(text)
        else:
            blocks = re.split(r"\n\s*\n", _OCR_NOISE.sub(" ", text))

        buffer = ""
        for block in blocks:
            block = " ".join(block.split())
            if not block:
                continue
            buffer = f"{buffer} {block}".strip()
            if len(buffer) >= PASSAGE_TARGET:
                emit(buffer)
                buffer = ""
        if len(buffer) >= PASSAGE_MIN:
            emit(buffer)
    return out


PARSERS = {
    "shamela_dictionary": parse_shamela_dictionary,
    "shamela_prose": parse_shamela_prose,
    "shamela_hadith": parse_shamela_hadith,
    "textfile": parse_textfile,
}


# --- driver ------------------------------------------------------------------


def load_pages(slug: str) -> list[dict]:
    raw = CONTEXT / slug / "raw"
    if not raw.exists():
        return []
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(raw.glob("*.json"))
    ]


def parse_source(src: sources.Source) -> list[dict]:
    pages = load_pages(src.slug)
    chunks = PARSERS[src.parser](src, pages)

    out_dir = CONTEXT / src.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    meta = sources.as_dict(src) | {
        "parser": src.parser,
        "raw_pages": len(pages),
        "chunks": len(chunks),
    }
    (out_dir / "source.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    kinds = {}
    for c in chunks:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    print(f"[{src.slug:<12}] {len(pages):>4} pages -> {len(chunks):>5} chunks  {kinds}")
    return chunks


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse raw sources into uniform chunks")
    ap.add_argument("source", nargs="?", help=f"one of: {', '.join(sources.SOURCES)}")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    targets = (
        list(sources.SOURCES.values()) if args.all
        else [sources.get(args.source)] if args.source
        else ap.error("pass a source slug or --all")
    )
    total = sum(len(parse_source(s)) for s in targets)
    print(f"total chunks: {total}")


if __name__ == "__main__":
    main()
