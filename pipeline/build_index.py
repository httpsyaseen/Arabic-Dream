"""Build the search index the API loads.

    python -m pipeline.build_index

Reads   context/*/chunks.json
Writes  index/symbols.json   the search vocabulary, from the dictionary source
        index/passages.json  symbol key -> supporting passages from every source
        index/adab.json      hadith on dream types and etiquette
        index/stats.json     counts, for /api/v1/health

Direction matters for speed. Running one regex per symbol against every passage
would be ~2,300 x ~16,000 = 37M operations. Instead every passage generates the
keys it *could* contain and those are intersected with the known vocabulary, so
the whole build is a couple of seconds.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from . import sources
from .arabic import normalize

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "context"
INDEX = ROOT / "index"

# Arabic attaches the article and some conjunctions to the front of a word and
# possessives to the back, so both are stripped when generating candidate keys.
_AFFIX = re.compile(r"^(?:وال|بال|كال|فال|لل|ال|و|ف)|(?:ها|هم|هن|كم|كن|نا|تين|ات|ين|ون|ان|ه|ي|ك)$")

# Per symbol, per source. Enough for the model to see agreement or disagreement
# between books without burying the prompt.
PER_SOURCE = 3


def load_chunks(slug: str) -> list[dict]:
    path = CONTEXT / slug / "chunks.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def candidates(text: str, max_words: int) -> set[str]:
    """Every n-gram the passage contains, with affixes stripped."""
    words = normalize(text).split()
    bare = [_AFFIX.sub("", w) for w in words]
    out: set[str] = set()
    for i in range(len(words)):
        for n in range(1, max_words + 1):
            if i + n > len(words):
                break
            out.add(" ".join(words[i:i + n]))
            out.add(" ".join(bare[i:i + n]))
    return out


def build() -> dict:
    # --- vocabulary: only sources whose role is "symbols" -------------------
    symbols: list[dict] = []
    for src in sources.SOURCES.values():
        if src.role != "symbols":
            continue
        for c in load_chunks(src.slug):
            symbols.append({
                "key": normalize(c["symbol_ar"]),
                "symbol_ar": c["symbol_ar"],
                "text_ar": c["text_ar"],
                "source": c["source"],
                "chapter_ar": c.get("chapter_ar"),
                "printed_page": c.get("printed_page"),
                "url": c.get("url", ""),
            })
    # Longest first, so a longer headword suppresses its own substrings at match
    # time — otherwise إلية الشاة would also report شاة as its own symbol.
    symbols.sort(key=lambda e: -len(e["key"]))
    keys = {e["key"] for e in symbols}
    max_words = max((len(k.split()) for k in keys), default=1)

    # --- passages: every source whose role is "passages" --------------------
    passages: dict[str, list[dict]] = defaultdict(list)
    per_source_counts: dict[str, int] = {}
    for src in sources.SOURCES.values():
        if src.role != "passages":
            continue
        n = 0
        for c in load_chunks(src.slug):
            hits = candidates(c["text_ar"], max_words) & keys
            for key in hits:
                bucket = passages[key]
                if sum(1 for p in bucket if p["source"] == src.slug) >= PER_SOURCE:
                    continue
                bucket.append({
                    "text_ar": c["text_ar"],
                    "source": src.slug,
                    "kind": src.kind,          # classical | psychological
                    "printed_page": c.get("printed_page"),
                    "url": c.get("url", ""),
                })
                n += 1
        per_source_counts[src.slug] = n

    # --- adab ---------------------------------------------------------------
    adab = []
    for src in sources.SOURCES.values():
        if src.role != "hadith":
            continue
        for c in load_chunks(src.slug):
            adab.append({
                "text_ar": c["text_ar"],
                "source": c["source"],
                "chapter_ar": c.get("chapter_ar"),
                "printed_page": c.get("printed_page"),
                "url": c.get("url", ""),
            })

    stats = {
        "symbols": len(symbols),
        "passages": sum(len(v) for v in passages.values()),
        "passages_by_source": per_source_counts,
        "adab": len(adab),
        "symbols_with_support": sum(1 for k in keys if passages.get(k)),
        "sources": len(sources.SOURCES),
    }

    INDEX.mkdir(exist_ok=True)
    (INDEX / "symbols.json").write_text(json.dumps(symbols, ensure_ascii=False), encoding="utf-8")
    (INDEX / "passages.json").write_text(json.dumps(passages, ensure_ascii=False), encoding="utf-8")
    (INDEX / "adab.json").write_text(json.dumps(adab, ensure_ascii=False, indent=1), encoding="utf-8")
    (INDEX / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"symbols            {stats['symbols']:>6}")
    print(f"passages           {stats['passages']:>6}")
    for slug, n in sorted(per_source_counts.items(), key=lambda x: -x[1]):
        print(f"  {slug:<16} {n:>6}")
    print(f"adab/hadith        {stats['adab']:>6}")
    print(f"symbols supported  {stats['symbols_with_support']:>6}")
    return stats


if __name__ == "__main__":
    build()
