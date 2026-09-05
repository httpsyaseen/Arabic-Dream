"""Rewrite symbols.json with Arabic symbol names.

    python -m pipeline.translate_symbol_names            # use symbols.txt only
    python -m pipeline.translate_symbol_names --fill     # ask Gemini for the rest

Takes symbols.json exactly as it is and changes one thing: the `symbol` field
becomes Arabic. The interpretations are left untouched, so the output is the same
file in the same shape, readable by anything that reads the original.

Names come from symbols.txt (449 pairs) where it has them. That covers 453 of the
1,323 entries; `--fill` translates the remainder with one batched model call and
writes the new pairs back into symbols.txt, so the manual file keeps growing and
the same work is never paid for twice.

Writes symbols_ar.json.
"""

import argparse
import csv
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "symbols.json"
PAIRS = ROOT / "symbols.txt"
OUT = ROOT / "symbols_ar.json"

BATCH = 60          # names per model call; small enough to stay reliable

SYSTEM = """\
You translate dream-symbol names from English into Arabic.

Rules:
- Translate the WHOLE name, not just its head noun. "Prayer in the Mosque" is
  "الصلاة في المسجد", not "صلاة"; "Drinking Blood" is "شرب الدم", not "دم".
  Collapsing a phrase to its base noun makes distinct entries collide, which
  destroys the very distinction the entry exists to record.
- Write it as a dream dictionary would head the entry: no explanation, no
  transliteration, no English in brackets.
- Where the English already contains the Arabic word in brackets — "Pitcher
  (Kuz)", "Waterskin (Qirba)" — use that word, written in Arabic script.
- Prefer the word a classical Arabic dream dictionary would use over a modern
  loanword.
- Return exactly one Arabic name per input, in the same order, and nothing else.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "names": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["names"],
}


def load_pairs() -> dict[str, str]:
    pairs: dict[str, str] = {}
    if not PAIRS.exists():
        return pairs
    with open(PAIRS, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)                       # header
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                pairs[row[0].strip().lower()] = row[1].strip()
    return pairs


def save_pairs(pairs: dict[str, str], originals: dict[str, str]) -> None:
    """Rewrite symbols.txt with the new names folded in, original casing kept."""
    with open(PAIRS, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Symbol", "Arabic Translation"])
        for key in sorted(pairs, key=lambda k: originals.get(k, k).lower()):
            w.writerow([originals.get(key, key), pairs[key]])


def fill_missing(missing: list[str]) -> dict[str, str]:
    from google import genai
    from dotenv import load_dotenv
    load_dotenv()

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set")
    cli = genai.Client(api_key=key)

    models = [os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")] + [
        m.strip() for m in os.getenv(
            "GEMINI_FALLBACK_MODELS",
            "gemini-3.5-flash,gemini-3.1-flash-lite,gemini-3.6-flash").split(",")
        if m.strip()
    ]

    found: dict[str, str] = {}
    for start in range(0, len(missing), BATCH):
        chunk = missing[start:start + BATCH]
        payload = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(chunk))
        for model in models:
            try:
                out = cli.interactions.create(
                    model=model,
                    input=payload,
                    system_instruction=SYSTEM,
                    response_format={"type": "text", "mime_type": "application/json",
                                     "schema": SCHEMA},
                    generation_config={"thinking_level": "minimal"},
                    store=False,
                )
                names = json.loads(out.output_text)["names"]
            except Exception:
                continue
            if len(names) != len(chunk):
                continue           # a misaligned batch would mislabel every entry
            for english, arabic in zip(chunk, names):
                arabic = re.sub(r"^(ال)?", "", arabic.strip()) if arabic.strip().startswith("ال ") else arabic.strip()
                if arabic:
                    found[english.lower()] = arabic
            break
        print(f"  {min(start + BATCH, len(missing)):>4}/{len(missing)} translated")
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description="Rewrite symbols.json with Arabic names")
    ap.add_argument("--fill", action="store_true",
                    help="translate the names symbols.txt does not cover")
    ap.add_argument("--redo-collisions", action="store_true",
                    help="re-translate distinct English names that share one Arabic name")
    args = ap.parse_args()

    entries = json.loads(SRC.read_text(encoding="utf-8"))
    pairs = load_pairs()
    originals = {k: k for k in pairs}

    missing = sorted({e["symbol"].strip() for e in entries
                      if e["symbol"].strip().lower() not in pairs})
    print(f"entries {len(entries)} · named {len(entries) - len(missing)} · unnamed {len(missing)}")

    if args.redo_collisions:
        # Distinct English names sharing an Arabic name are usually a phrase that
        # was flattened to its head noun. Genuine duplicates in the source are
        # left alone — they were already the same entry twice.
        from collections import defaultdict
        groups = defaultdict(set)
        for e in entries:
            key = e["symbol"].strip().lower()
            if key in pairs:
                groups[pairs[key]].add(e["symbol"].strip())
        clashing = sorted({n for names in groups.values() if len(names) > 1
                           for n in names if len(n.split()) > 1})
        if clashing:
            print(f"re-translating {len(clashing)} flattened names…")
            redone = fill_missing(clashing)
            pairs.update(redone)
            originals.update({k.lower(): k for k in clashing})
            save_pairs(pairs, originals)
            print(f"  updated {len(redone)} pairs")

    if args.fill and missing:
        print(f"translating {len(missing)} names…")
        new = fill_missing(missing)
        pairs.update(new)
        originals.update({k.lower(): k for k in missing})
        save_pairs(pairs, originals)
        print(f"  added {len(new)} pairs to {PAIRS.name}")

    out, untranslated = [], []
    for e in entries:
        arabic = pairs.get(e["symbol"].strip().lower())
        if arabic:
            out.append({**e, "symbol": arabic})
        else:
            untranslated.append(e["symbol"])

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT.name}: {len(out)} entries with Arabic names "
          f"({OUT.stat().st_size // 1024} KB)")
    if untranslated:
        print(f"left out {len(untranslated)} with no Arabic name — run with --fill")
        print("  e.g.", ", ".join(untranslated[:6]))


if __name__ == "__main__":
    main()
