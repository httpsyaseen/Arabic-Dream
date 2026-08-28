"""Parse the English Ibn Sirin dictionary (al-Akili edition) into symbol entries.

This edition is already what the Arabic extraction pipeline was trying to
produce: an A-Z dictionary, one headword per symbol, with the conditional
structure of classical ta'bir preserved in the prose ("If one sees X ... it
means Y"). Because it is structured, splitting it needs a regex rather than a
model — the whole dictionary parses in about a second for nothing.

    python -m corpus.english --parse           # writes data/english/ibn_sirin_en.json
    python -m corpus.english --lookup snake

What still wants a model afterwards is enrichment: category, valence, and
pulling the conditions out of the prose into structured `if/then` pairs. That is
incremental and can run symbol by symbol, unlike translation which was
all-or-nothing.

The source is OCR, so text is de-hyphenated and unwrapped before parsing, and
headwords carry OCR variants (Ka'ba / Kaaba) that the alias table absorbs.
"""

import argparse
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"
SRC = DATA / "sources" / "ibnsirin_en.txt"
OUT = DATA / "english"

SOURCE = {
    "book_en": "Ibn Seerin's Dictionary of Dreams",
    "edition": "trans. Muhammad M. Al-Akili, Pearl Publishing House",
    "lens": "ibn_sirin",
    "language": "en",
}

# "Headword: body text" — the only structural marker the edition uses.
ENTRY = re.compile(
    r"(?:^|\s{2,}|\n)([A-Z][A-Za-z'\- ]{1,34}):\s+(.+?)"
    r"(?=(?:\s{2,}|\n)[A-Z][A-Za-z'\- ]{1,34}:\s|\Z)",
    re.S,
)

# "(See Snake charmer)" / "(Also see Alms tax; Endowment)"
XREF = re.compile(r"\((?:Also see|See)\s+([^)]+)\)", re.I)

# The A-Z body starts here; everything before it is preface and biography whose
# "Ibn Seer'in replied:" quotations otherwise parse as bogus headwords.
BODY_STARTS = "abandoned infant"

MIN_BODY_CHARS = 60


def normalise_text(raw: str) -> str:
    raw = re.sub(r"-\n", "", raw)        # join words split across lines
    return re.sub(r"\n(?!\n)", " ", raw)  # unwrap lines, keep paragraph breaks


def parse(raw: str) -> list[dict]:
    text = normalise_text(raw)
    matches = [
        (m.group(1).strip(), " ".join(m.group(2).split()))
        for m in ENTRY.finditer(text)
    ]

    start = next(
        (i for i, (h, _) in enumerate(matches) if h.lower() == BODY_STARTS), 0
    )
    body = matches[start:]

    entries: dict[str, dict] = {}
    aliases: list[tuple[str, str]] = []  # (alias, target)

    for head, text_body in body:
        key = head.lower()
        xref_only = text_body.startswith("(See")
        if xref_only:
            targets = XREF.findall(text_body)
            if targets:
                for target in re.split(r"[;,]", targets[0]):
                    target = target.strip().lower()
                    if target:
                        aliases.append((key, target))
            continue

        if len(text_body) < MIN_BODY_CHARS:
            continue

        related = []
        for group in XREF.findall(text_body):
            related += [r.strip() for r in re.split(r"[;,]", group) if r.strip()]

        entries[key] = {
            "symbol_en": head,
            "symbol_key": key,
            "body_en": text_body,
            "related": sorted({r.lower() for r in related}),
            "aliases": [],
            "source": SOURCE,
            "review": {"status": "pending", "scholar_id": None, "date": None},
        }

    # Attach cross-references as aliases of the entry they point at. A pointer to
    # a headword we did not keep is dropped rather than left dangling.
    orphans = 0
    for alias, target in aliases:
        entry = entries.get(target)
        if entry is None:
            orphans += 1
            continue
        entry["aliases"].append(alias)

    for entry in entries.values():
        entry["aliases"] = sorted(set(entry["aliases"]))

    print(
        f"parsed {len(entries)} symbols, "
        f"{sum(len(e['aliases']) for e in entries.values())} aliases attached, "
        f"{orphans} cross-refs orphaned"
    )
    return sorted(entries.values(), key=lambda e: e["symbol_key"])


def load() -> list[dict]:
    path = OUT / "ibn_sirin_en.json"
    if not path.exists():
        raise SystemExit("not parsed yet — run: python -m corpus.english --parse")
    return json.loads(path.read_text(encoding="utf-8"))


def lookup(query: str, entries: list[dict], limit: int = 8) -> list[dict]:
    """Exact key first, then alias, then substring. Cheap and deterministic."""
    q = query.lower().strip()
    exact = [e for e in entries if e["symbol_key"] == q]
    alias = [e for e in entries if q in e["aliases"] and e not in exact]
    partial = [
        e
        for e in entries
        if q in e["symbol_key"] and e not in exact and e not in alias
    ]
    return (exact + alias + partial)[:limit]


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse/query the English Ibn Sirin dictionary")
    ap.add_argument("--parse", action="store_true", help="parse the source text")
    ap.add_argument("--lookup", help="look a symbol up in the parsed dictionary")
    args = ap.parse_args()

    if args.parse:
        if not SRC.exists():
            raise SystemExit(f"source text not found at {SRC}")
        entries = parse(SRC.read_text(encoding="utf-8"))
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "ibn_sirin_en.json").write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote {OUT / 'ibn_sirin_en.json'}")

    if args.lookup:
        for e in lookup(args.lookup, load()):
            print(f"\n[{e['symbol_en']}]  aliases={e['aliases'][:5]}")
            print(f"  {e['body_en'][:280]}...")

    if not args.parse and not args.lookup:
        ap.error("pass --parse or --lookup")


if __name__ == "__main__":
    main()
