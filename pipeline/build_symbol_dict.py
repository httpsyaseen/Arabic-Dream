"""Build the Arabic symbol dictionary from the English symbol list.

    python -m pipeline.build_symbol_dict

Reads   symbols.txt        English name, Arabic translation (449 pairs)
        symbols.json       English names with English interpretations (1,234)
        index/symbols.json the 2,317 Arabic headwords the site searches
Writes  index/arabic_symbol_dict.json

Keyed by the **Arabic** name, since that is what the corpus is indexed by and
what a lookup has to match. The English name rides along so the same file can
serve an English-language front end later.

Each entry records whether that Arabic word actually reaches a symbol in our
corpus, and how:

    exact   the Arabic word is itself a headword in the books
    alias   it reaches one through the alias table — ثعبان (thu'ban, "serpent")
            is not a headword, but resolves to حية (hayya, "snake")
    absent  nothing in the corpus for it

`absent` is the useful column: it is a list of symbols people expect us to know
and we do not, which is exactly what should drive the next round of work.
"""

import csv
import json
import re
from pathlib import Path

from backend.aliases import ALIASES
from .arabic import normalize

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index"

# Same affixes the live matcher allows, so "resolves" here means the same thing
# it will mean at request time.
_PREFIX = r"(?:وال|بال|كال|فال|لل|ال|و|ف)?"
_SUFFIX = r"(?:ها|هم|هن|كم|كن|نا|تين|ات|ين|ون|ان|ه|ي|ك|ا)?"


def resolve(arabic: str, corpus: dict[str, str]) -> tuple[str, str | None]:
    """(how it matched, the corpus headword) for one Arabic word."""
    key = normalize(arabic)
    if key in corpus:
        return "exact", corpus[key]
    if key in ALIASES and ALIASES[key] in corpus:
        return "alias", corpus[ALIASES[key]]

    # A multi-word name such as سقوط الأسنان ("falling of the teeth") will not be
    # a headword, but its parts are — the dictionaries file the noun, not the
    # phrase. Resolve on the first part that lands.
    for word in key.split():
        if word in corpus:
            return "partial", corpus[word]
        if word in ALIASES and ALIASES[word] in corpus:
            return "partial", corpus[ALIASES[word]]

    # Last try: the corpus headword may carry an affix relative to this word.
    for ckey, sym in corpus.items():
        if re.fullmatch(rf"{_PREFIX}{re.escape(ckey)}{_SUFFIX}", key):
            return "affix", sym
    return "absent", None


def build() -> dict:
    pairs: list[tuple[str, str]] = []
    with open(ROOT / "symbols.txt", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)                       # header
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                pairs.append((row[0].strip(), row[1].strip()))

    english_meanings: dict[str, list[dict]] = {}
    sj_path = ROOT / "symbols.json"
    if sj_path.exists():
        for entry in json.loads(sj_path.read_text(encoding="utf-8")):
            english_meanings[entry["symbol"].strip()] = entry.get("interpretations", [])

    corpus = {e["key"]: e["symbol_ar"]
              for e in json.loads((INDEX / "symbols.json").read_text(encoding="utf-8"))}

    out: dict[str, dict] = {}
    counts = {"exact": 0, "alias": 0, "partial": 0, "affix": 0, "absent": 0}
    for english, arabic in pairs:
        how, headword = resolve(arabic, corpus)
        counts[how] += 1
        # A later duplicate should not overwrite a resolved earlier one.
        if arabic in out and out[arabic]["match"] != "absent":
            continue
        out[arabic] = {
            "arabic": arabic,
            "english": english,
            "key": normalize(arabic),
            "match": how,
            "corpus_symbol": headword,
            "has_english_text": english in english_meanings,
        }

    # English names with an interpretation but no Arabic translation yet. Listed
    # rather than dropped: this is the gap to fill for an English version.
    untranslated = sorted(set(english_meanings) - {e for e, _ in pairs})

    payload = {
        "generated_from": ["symbols.txt", "symbols.json", "index/symbols.json"],
        "counts": {
            "entries": len(out),
            **counts,
            "english_without_arabic": len(untranslated),
        },
        "symbols": out,
        "english_without_arabic": untranslated,
    }
    (INDEX / "arabic_symbol_dict.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"entries            {len(out):>5}")
    for k in ("exact", "alias", "partial", "affix", "absent"):
        print(f"  {k:<16} {counts[k]:>5}")
    print(f"english w/o arabic {len(untranslated):>5}")
    print(f"-> {INDEX / 'arabic_symbol_dict.json'}")
    return payload


if __name__ == "__main__":
    build()
