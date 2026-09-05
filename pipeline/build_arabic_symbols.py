"""Build arabic_symbols.json — the Arabic counterpart of symbols.json.

    python -m pipeline.build_arabic_symbols

Same shape as the English symbols.json so the two can be used interchangeably:

    [
      {
        "symbol": "ماء",
        "interpretations": [
          { "source": "...", "text": "..." },
          ...
        ]
      },
      ...
    ]

The difference is where the text comes from. The English file's interpretations
were generated, so they carry no page numbers and the same book appears under
two different titles. These are lifted verbatim from the scanned books, so each
one keeps its printed page and a link to the scan — fields added alongside the
required two rather than in place of them, so anything reading the English shape
still works.

Ordered by how much support a symbol has, so the entries a reader is most likely
to want come first.
"""

import json
import re
from pathlib import Path

from . import sources
from .arabic import normalize

# Scanned sources carry OCR damage — runs of one- and two-letter fragments where
# an ornamental border or a footnote used to be. A passage that is mostly that is
# worse than no passage, so it is left out rather than shown under a symbol.
_ARABIC = re.compile(r"[؀-ۿ]")


def readable(text: str) -> bool:
    words = text.split()
    if len(words) < 6:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(1 for c in letters if _ARABIC.match(c)) / len(letters) < 0.92:
        return False
    # Real Arabic prose averages well over three letters a word; OCR wreckage
    # does not.
    return sum(len(w) for w in words) / len(words) >= 3.0


def relevance(text: str, key: str) -> tuple:
    """Rank: how often the symbol occurs, and how early it appears.

    A passage that merely brushes past the word is worth less than one that
    keeps returning to it, and one that opens with it is usually the entry for
    that symbol rather than a mention in passing.
    """
    norm = normalize(text)
    hits = norm.count(key)
    first = norm.find(key)
    return (-hits, first if first >= 0 else 10**6)

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index"

MAX_PER_SYMBOL = 6      # matches what a reader is shown for one dream


def source_label(slug: str) -> str:
    """«Book title» — Author, the way it is credited on the page."""
    s = sources.SOURCES.get(slug)
    if not s:
        return slug
    return f"«{s.name_ar}» — {s.author_ar}" if s.author_ar else f"«{s.name_ar}»"


def build() -> list[dict]:
    symbols = json.loads((INDEX / "symbols.json").read_text(encoding="utf-8"))
    passages = json.loads((INDEX / "passages.json").read_text(encoding="utf-8"))

    # English names, where the translated list happens to cover the symbol.
    english: dict[str, str] = {}
    dict_path = INDEX / "arabic_symbol_dict.json"
    if dict_path.exists():
        for entry in json.loads(dict_path.read_text(encoding="utf-8"))["symbols"].values():
            if entry.get("corpus_symbol"):
                english.setdefault(entry["corpus_symbol"], entry["english"])

    out = []
    for sym in symbols:
        interpretations = [{
            "source": source_label(sym["source"]),
            "text": sym["text_ar"],
            "printed_page": sym.get("printed_page"),
            "url": sym.get("url") or None,
        }]

        # Supporting passages, one book at a time so a single source cannot fill
        # the entry on its own.
        pool = passages.get(sym["key"]) or []
        by_source: dict[str, list[dict]] = {}
        for p in pool:
            by_source.setdefault(p["source"], []).append(p)

        # Drop the unreadable, then put the most relevant of each book first.
        for slug in list(by_source):
            kept = [p for p in by_source[slug] if readable(p["text_ar"])]
            kept.sort(key=lambda p: relevance(p["text_ar"], sym["key"]))
            if kept:
                by_source[slug] = kept
            else:
                del by_source[slug]

        depth = 0
        while len(interpretations) < MAX_PER_SYMBOL and any(
                len(v) > depth for v in by_source.values()):
            for slug, group in by_source.items():
                if len(interpretations) >= MAX_PER_SYMBOL:
                    break
                if len(group) > depth:
                    p = group[depth]
                    interpretations.append({
                        "source": source_label(slug),
                        "text": p["text_ar"],
                        "printed_page": p.get("printed_page"),
                        "url": p.get("url") or None,
                        "kind": p.get("kind"),      # classical | psychological
                    })
            depth += 1

        entry = {"symbol": sym["symbol_ar"], "interpretations": interpretations}
        if english.get(sym["symbol_ar"]):
            entry["english"] = english[sym["symbol_ar"]]
        out.append(entry)

    out.sort(key=lambda e: (-len(e["interpretations"]), e["symbol"]))

    path = ROOT / "arabic_symbols.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(len(e["interpretations"]) for e in out)
    with_en = sum(1 for e in out if "english" in e)
    multi = sum(1 for e in out if len(e["interpretations"]) > 1)
    print(f"symbols                {len(out):>6}")
    print(f"interpretations        {total:>6}")
    print(f"  average per symbol   {total / len(out):>6.1f}")
    print(f"  with more than one   {multi:>6}")
    print(f"with an English name   {with_en:>6}")
    print(f"-> {path}  ({path.stat().st_size // 1024} KB)")
    return out


if __name__ == "__main__":
    build()
