"""Arabic symbol index across all three scraped books.

Two structures, both built from the scrape with no model involved:

  * a **symbol vocabulary** from Nabulsi, which is an alphabetical dictionary and
    so already tells us what counts as a dream symbol and what its headword is, and
  * a **passage index** over Ibn Sirin and Ibn Shaheen, which are topical prose
    with no headwords. Those two are searched for passages mentioning a symbol the
    vocabulary already identified.

So Nabulsi decides *what the symbols are* and all three books supply *evidence*.
That gives three lenses without needing any of the prose extracted first.

    python -m corpus.index --build
    python -m corpus.index --match "رأيت حية في بيتي"

Matching is lexical on purpose. This is glossary lookup, and an exact headword hit
is both more accurate and more explainable than a nearest-neighbour score.
"""

import argparse
import functools
import json
import re
from collections import defaultdict
from pathlib import Path

from .arabic import normalize

DATA = Path(__file__).parent / "data"
RAW = DATA / "raw"
OUT = DATA / "index"

# Arabic joins the article and some conjunctions to the word, so a headword must
# be allowed to carry them: الحية, وحية. The bare prepositions ب/ك/ل are excluded
# — allowing them lets بير match inside كبيرة, which costs more than it gains.
_PREFIX = r"(?:وال|بال|كال|فال|لل|ال|و|ف)?"
# Possessives and sound plurals attach at the end: بيتي, أسنانه.
_SUFFIX = r"(?:ها|هم|هن|كم|كن|نا|تين|ات|ين|ون|ان|ه|ي|ك)?"
_ARABIC = r"[؀-ۿ]"

# Modern or colloquial words a dreamer would actually type, mapped to the
# headword the classical dictionary files them under. Nabulsi has no أسنان entry
# — teeth live under ضرس — and nobody writes ضرس when describing their dream.
# Broken plurals are the same problem: حيات never matches حية by any prefix or
# suffix rule, because the stem itself changes.
ALIASES = {
    "اسنان": "ضرس", "سن": "ضرس", "ضروس": "ضرس", "اضراس": "ضرس",
    "حيات": "حيه", "ثعبان": "حيه", "افعي": "حيه", "ثعابين": "حيه",
    "مياه": "ماء", "بحار": "بحر", "بيوت": "بيت",
    "شعور": "شعر", "اشعار": "شعر",
    "موتي": "موت", "ميت": "موت", "متوفي": "موت", "اموات": "موت",
    "نيران": "نار", "كلاب": "كلب", "قطط": "قط", "اسماك": "سمك",
    "طيور": "طير", "خيول": "فرس", "احصنه": "فرس", "حصان": "فرس",
    "دماء": "دم", "امطار": "مطر", "جبال": "جبل", "ابواب": "باب",
    "نقود": "دراهم", "فلوس": "دراهم",
    "زواج": "تزويج", "عرس": "عرس", "حامل": "حبل",
    "طفل": "ولد", "اطفال": "ولد", "اولاد": "ولد",

    # People describe dreams with conjugated verbs — "I fell", "I was flying" —
    # while the dictionaries file everything under the verbal noun (سقوط, طيران).
    # No prefix or suffix rule bridges that, so the forms are listed explicitly.
    "سقطت": "سقوط", "اسقط": "سقوط", "يسقط": "سقوط", "تسقط": "سقوط",
    "وقعت": "سقوط", "اقع": "سقوط", "يقع": "سقوط", "وقوع": "سقوط",
    "هويت": "سقوط", "انهار": "سقوط", "سقط": "سقوط",
    "طرت": "طيران", "اطير": "طيران", "يطير": "طيران", "تطير": "طيران",
    "بكيت": "بكاء", "ابكي": "بكاء", "يبكي": "بكاء", "تبكي": "بكاء",
    "غرقت": "غرق", "اغرق": "غرق", "يغرق": "غرق",
    "هربت": "هرب", "اهرب": "هرب", "يطاردني": "هرب", "يلاحقني": "هرب",
    "مت": "موت", "اموت": "موت", "يموت": "موت", "توفي": "موت",
    "تزوجت": "تزويج", "اتزوج": "تزويج",
    "صليت": "صلاه", "اصلي": "صلاه",
    "اكلت": "اكل", "شربت": "شرب", "ضحكت": "ضحك", "صرخت": "صياح",
    "احترق": "حريق", "احترقت": "حريق", "اشتعل": "نار",
    "ولدت": "ولاده", "حلقت": "حلق", "ضاع": "ضياع", "ضعت": "ضياع",

    # Places people name that the books file differently.
    "بنايه": "بناء", "عماره": "بناء", "مبني": "بناء", "برج": "بناء",
    "سياره": "مركب", "طائره": "طيران", "درج": "سلم", "سلالم": "سلم",
    "مكان عال": "مكان مرتفع", "من عال": "سقوط",
}

MIN_KEY_CHARS = 3
# Shamela occasionally wraps a whole sentence in span.c2 rather than a headword
# ("وقد ضمن الحسن بن الحسين الخلال..."). Those are not symbols.
MAX_KEY_CHARS = 30
MAX_KEY_WORDS = 4

# Classical prose is barely punctuated, so passages are cut at the phrases that
# actually start a new ruling rather than at full stops.
_SPLIT = re.compile(
    r"(?=(?:فإن رأى|وإن رأى|ومن رأى|من رأى|وإذا رأى|وقال|فمن رأى|وأما))"
)
PASSAGE_MIN = 80
PASSAGE_MAX = 700
PASSAGES_PER_SYMBOL = 3

PROSE_BOOKS = {
    "ibn_sirin": ("تفسير الأحلام (منتخب الكلام)", "منسوب إلى ابن سيرين"),
    "ibn_shaheen": ("الإشارات في علم العبارات", "ابن شاهين الظاهري"),
    # Alphabetical, but its headwords are inline ("البول في الرؤيا:") rather than
    # marked up, so it contributes passages instead of vocabulary.
    "tabir": ("تعبير الرؤيا", "كتاب تعبير الرؤيا"),
}

# The psychological lens. Not a classical source and never presented as one — it
# is indexed and cited separately so a reader can always tell which tradition a
# reading comes from. Freud is used because he is what the Arabic literature on
# dream psychology actually rests on, and because he treats precisely the dreams
# people ask about: falling, flying, teeth, nakedness, the death of a relative.
TEXT_BOOKS = {
    "freud": {
        "files": ["freud_tafsir.txt", "freud_hulm.txt"],
        "book_ar": "تفسير الأحلام",
        "author": "سيغموند فرويد",
        "lens": "psych",
    },
}

# OCR of these scans leaves footnote markers and stray Latin page references
# mid-sentence; they add nothing and confuse the model.
_OCR_NOISE = re.compile(r"[ـ]|\(\s*[0-9A-Za-z/:.\s]{1,12}\s*\)|[«»]")

# Hadith and etiquette of dreams rather than symbol interpretation. Selected by
# chapter title, because the chapters in this book are exactly the topics the
# classification and adab layer needs.
ADAB_BOOK = ("ruya", "الرؤيا")
ADAB_TOPICS = [
    "أنواع الرؤيا", "الرؤيا الصالحة", "بشرى", "جزء من النبوة",
    "يتفل عن يساره", "ما يكرهه", "يقوم فيصلي", "لا يحدث بها",
    "أضغاث", "حديث النفس", "تحزين من الشيطان", "الاستعاذة",
]
ADAB_MAX = 6


@functools.lru_cache(maxsize=16384)
def _pattern(key: str) -> re.Pattern:
    return re.compile(
        rf"(?<!{_ARABIC}){_PREFIX}{re.escape(key)}{_SUFFIX}(?!{_ARABIC})"
    )


def _chunks(text: str) -> list[str]:
    out = []
    for part in _SPLIT.split(text):
        part = part.strip()
        if len(part) < PASSAGE_MIN:
            continue
        while len(part) > PASSAGE_MAX:
            out.append(part[:PASSAGE_MAX])
            part = part[PASSAGE_MAX:]
        if len(part) >= PASSAGE_MIN:
            out.append(part)
    return out


def _candidates(chunk_norm: str, max_words: int) -> set[str]:
    """Every n-gram in the chunk, with prefixes/suffixes stripped.

    Cheaper than running 2,300 regexes over every passage: build the possible
    keys from the text once, then intersect with the vocabulary.
    """
    words = chunk_norm.split()
    strip = re.compile(rf"^{_PREFIX}|{_SUFFIX}$")
    bare = [strip.sub("", w) for w in words]
    out: set[str] = set()
    for i in range(len(words)):
        for n in range(1, max_words + 1):
            if i + n > len(words):
                break
            out.add(" ".join(words[i : i + n]))
            out.add(" ".join(bare[i : i + n]))
    return out


def build_symbols() -> list[dict]:
    entries: dict[str, dict] = {}
    for path in sorted((RAW / "nabulsi").glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        for para in page["paragraphs"]:
            head = (para.get("marker") or "").strip()
            body = para["text"].strip()
            if not head or len(body) < 30:
                continue
            key = normalize(head)
            if not (MIN_KEY_CHARS <= len(key) <= MAX_KEY_CHARS):
                continue
            if len(key.split()) > MAX_KEY_WORDS:
                continue
            existing = entries.get(key)
            if existing and len(existing["body_ar"]) >= len(body):
                continue
            entries[key] = {
                "key": key,
                "symbol_ar": head,
                "body_ar": body,
                "source": {
                    "book_ar": "تعطير الأنام في تعبير المنام",
                    "author": "عبد الغني النابلسي",
                    "lens": "nabulsi",
                    "printed_page": page.get("printed_page"),
                    "url": page["url"],
                },
            }
    return sorted(entries.values(), key=lambda e: -len(e["key"]))


def _text_book_chunks(spec: dict) -> list[str]:
    """Plain-text sources have no page structure, so they are cut on paragraphs."""
    out = []
    for name in spec["files"]:
        path = DATA / "sources" / name
        if not path.exists():
            continue
        raw = _OCR_NOISE.sub(" ", path.read_text(encoding="utf-8"))
        for para in re.split(r"\n\s*\n", raw):
            para = " ".join(para.split())
            if len(para) < PASSAGE_MIN:
                continue
            while len(para) > PASSAGE_MAX:
                out.append(para[:PASSAGE_MAX])
                para = para[PASSAGE_MAX:]
            if len(para) >= PASSAGE_MIN:
                out.append(para)
    return out


def build_passages(keys: set[str]) -> dict[str, list[dict]]:
    max_words = max(len(k.split()) for k in keys)
    inverted: dict[str, list[dict]] = defaultdict(list)

    for slug, spec in TEXT_BOOKS.items():
        for chunk in _text_book_chunks(spec):
            hits = _candidates(normalize(chunk), max_words) & keys
            for key in hits:
                bucket = inverted[key]
                if sum(1 for p in bucket if p["lens"] == spec["lens"]) >= PASSAGES_PER_SYMBOL:
                    continue
                bucket.append(
                    {
                        "text_ar": chunk,
                        "book_ar": spec["book_ar"],
                        "author": spec["author"],
                        "lens": spec["lens"],
                        "printed_page": None,
                        "url": "",
                    }
                )

    for slug, (book_ar, author) in PROSE_BOOKS.items():
        for path in sorted((RAW / slug).glob("*.json")):
            page = json.loads(path.read_text(encoding="utf-8"))
            for chunk in _chunks(page["text"]):
                hits = _candidates(normalize(chunk), max_words) & keys
                for key in hits:
                    if len(inverted[key]) >= PASSAGES_PER_SYMBOL * 4:
                        continue
                    inverted[key].append(
                        {
                            "text_ar": chunk,
                            "book_ar": book_ar,
                            "author": author,
                            "lens": slug,
                            "printed_page": page.get("printed_page"),
                            "url": page["url"],
                        }
                    )
    return inverted


def build_adab() -> list[dict]:
    """Hadith on the types of dream and what to do after a distressing one."""
    slug, book_ar = ADAB_BOOK
    src = RAW / slug
    if not src.exists():
        return []

    out, seen = [], set()
    for path in sorted(src.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        chapter = page.get("chapter") or ""
        if not any(topic in chapter for topic in ADAB_TOPICS):
            continue
        for para in page["paragraphs"]:
            text = para["text"].strip()
            if not (60 <= len(text) <= 600):
                continue
            fingerprint = normalize(text)[:80]
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            out.append(
                {
                    "text_ar": text,
                    "book_ar": book_ar,
                    "chapter_ar": chapter,
                    "printed_page": page.get("printed_page"),
                    "url": page["url"],
                }
            )
    return out


def build() -> tuple[list[dict], dict, list[dict]]:
    symbols = build_symbols()
    keys = {e["key"] for e in symbols}
    passages = build_passages(keys)
    adab = build_adab()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "nabulsi_ar.json").write_text(
        json.dumps(symbols, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "passages_ar.json").write_text(
        json.dumps(passages, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "adab_ar.json").write_text(
        json.dumps(adab, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    covered = sum(1 for k in keys if passages.get(k))
    print(
        f"indexed {len(symbols)} symbols; "
        f"{sum(len(v) for v in passages.values())} passages from "
        f"{len(PROSE_BOOKS)} prose books; {covered} symbols have prose support; "
        f"{len(adab)} adab/hadith passages"
    )
    return symbols, passages, adab


def load() -> tuple[list[dict], dict, list[dict]]:
    sym = OUT / "nabulsi_ar.json"
    if not sym.exists():
        raise SystemExit("index missing — run: python -m corpus.index --build")

    def _read(name, default):
        path = OUT / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    return (
        json.loads(sym.read_text(encoding="utf-8")),
        _read("passages_ar.json", {}),
        _read("adab_ar.json", []),
    )


def adab_for(dream: str, adab: list[dict], distressing_hint: bool = False) -> list[dict]:
    """A small, relevant slice of the adab corpus to ground classification.

    Kept short deliberately: this material is context for the model's judgement,
    not the answer itself, and a long tail of hadith crowds out the actual
    interpretation.
    """
    if not adab:
        return []
    scored = []
    text = normalize(dream)
    for item in adab:
        score = 0
        chapter = item.get("chapter_ar") or ""
        if "أنواع الرؤيا" in chapter or "جزء من النبوة" in chapter:
            score += 2
        if distressing_hint and ("يكرهه" in chapter or "يتفل" in chapter):
            score += 3
        # Slight preference for passages sharing vocabulary with the dream.
        shared = len(set(normalize(item["text_ar"]).split()) & set(text.split()))
        score += min(shared, 3) * 0.2
        scored.append((score, item))
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:ADAB_MAX]]


def match(
    dream: str, entries: list[dict], passages: dict | None = None, limit: int = 6
) -> list[dict]:
    """Symbols occurring in the dream text, longest headword first.

    `entries` is pre-sorted by descending key length, so once a longer headword
    matches, its shorter substrings are suppressed — otherwise every dream
    mentioning إلية الشاة would also report شاة as its own symbol.
    """
    text = normalize(dream)
    by_key = {e["key"]: e for e in entries}

    # Aliases run first so a dreamer's wording reaches the classical headword.
    forced: list[dict] = []
    for alias, target in ALIASES.items():
        if _pattern(alias).search(text) and target in by_key:
            entry = by_key[target]
            if entry not in forced:
                forced.append(entry)

    hits: list[dict] = list(forced)
    claimed = [e["key"] for e in forced]
    for entry in entries:
        if len(hits) >= limit:
            break
        key = entry["key"]
        if entry in hits or key not in text:
            continue
        if not _pattern(key).search(text):
            continue
        if any(key in longer for longer in claimed):
            continue
        claimed.append(key)
        hits.append(entry)

    if passages:
        for entry in hits:
            pool = passages.get(entry["key"]) or []
            # Keep the lenses balanced. Taking the first N would let whichever
            # book happens to be indexed first crowd the others out, and the
            # psychological reading would disappear behind the classical ones.
            classical = [p for p in pool if p.get("lens") != "psych"][:PASSAGES_PER_SYMBOL]
            psych = [p for p in pool if p.get("lens") == "psych"][:2]
            entry["passages"] = classical + psych

    return hits[:limit]


def main() -> None:
    ap = argparse.ArgumentParser(description="Arabic symbol index")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--match", help="test matching against a dream in Arabic")
    args = ap.parse_args()

    built = build() if args.build else None
    if args.match:
        entries, passages, _adab = built or load()
        found = match(args.match, entries, passages)
        print(f"{len(found)} symbols matched:")
        for e in found:
            extra = len(e.get("passages") or [])
            print(f"  {e['symbol_ar']:<14} (+{extra} prose passages)")
    if not args.build and not args.match:
        ap.error("pass --build or --match")


if __name__ == "__main__":
    main()
