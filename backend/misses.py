"""Record the words that found nothing, so the alias table can be grown from
evidence instead of guesswork.

Every recall bug so far was found by accident — someone tried a dream, noticed a
thin answer, and dug in. That does not scale, and it means the gaps nobody
happens to try stay invisible forever.

**Dreams are not logged.** Only the individual words that matched no symbol, and
how often each occurred. A dream is a private thing, the app tells readers their
journal never leaves their browser, and logging the text would quietly make that
untrue. Single words carry the signal needed to write an alias and carry almost
none of the content of the dream they came from.

    python -m backend.misses           # report what is missing most often

Writes `data/misses.json`, an ordinary counter file. If the directory is not
writable — a read-only container, say — recording is skipped silently rather
than failing a request over telemetry.
"""

import json
import re
from collections import Counter
from pathlib import Path

from pipeline.arabic import normalize

STORE = Path(__file__).resolve().parent.parent / "data" / "misses.json"

# Function words, pronouns and the verbs of seeing carry no symbol information —
# every dream contains them, and logging them would bury the real signal.
IGNORE = {
    normalize(w) for w in (
        "في", "من", "على", "الى", "عن", "مع", "ثم", "او", "ان", "انا", "انه",
        "كان", "كانت", "قد", "لا", "ما", "لم", "لن", "هو", "هي", "هم", "هذا",
        "هذه", "ذلك", "التي", "الذي", "كل", "بعد", "قبل", "عند", "حتى", "لكن",
        "رايت", "راى", "حلمت", "حلم", "منام", "المنام", "رويا", "الرويا",
        "اني", "انني", "نفسي", "وانا", "ثم", "بينما", "عندما", "جدا", "جدااا",
        "شي", "شيء", "شيئا", "كثير", "كثيرا", "كبير", "كبيرا", "صغير",
    )
}

MIN_WORD = 3          # shorter than this is almost always a particle
MAX_PER_DREAM = 12    # a long dream should not dominate the counts

# The same word arrives wearing different affixes — مصعد, بالمصعد, والمصعد — and
# counting those separately splits the very signal the log exists to produce.
# Same affix set the matcher allows, so what is counted is what actually failed.
_AFFIX = re.compile(
    r"^(?:وال|بال|كال|فال|لل|ال|وب|فب|و|ف|ب)|(?:ها|هم|هن|كم|كن|نا|تين|ات|ين|ون|ان|ه|ي|ك|ا)$"
)


def _stem(word: str) -> str:
    """Strip one leading and one trailing affix, if the result is still a word."""
    for _ in range(2):
        stripped = _AFFIX.sub("", word, count=1)
        if len(stripped) < MIN_WORD:
            break
        word = stripped
    return word


def _load() -> dict:
    if STORE.exists():
        try:
            return json.loads(STORE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"words": {}, "dreams_seen": 0, "dreams_with_no_match": 0}


def record(dream: str, matched: list[dict]) -> None:
    """Note which words in this dream reached no symbol."""
    matched_keys = {m["key"] for m in matched}
    words = []
    for raw in re.split(r"\s+", normalize(dream)):
        word = raw.strip()
        if len(word) < MIN_WORD or word in IGNORE:
            continue
        # Skip anything the lookup already accounted for.
        if any(key in word or word in key for key in matched_keys):
            continue
        words.append(_stem(word))

    data = _load()
    data["dreams_seen"] += 1
    if not matched:
        data["dreams_with_no_match"] += 1
    for word in words[:MAX_PER_DREAM]:
        data["words"][word] = data["words"].get(word, 0) + 1

    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass          # telemetry must never break a request


def report(top: int = 40) -> dict:
    data = _load()
    counts = Counter(data["words"])
    seen = data["dreams_seen"]
    blank = data["dreams_with_no_match"]
    print(f"dreams seen            {seen}")
    print(f"  of which matched nothing {blank}"
          + (f"  ({blank / seen * 100:.0f}%)" if seen else ""))
    print(f"distinct unmatched words {len(counts)}\n")
    print("most frequent words that reach no symbol:")
    for word, n in counts.most_common(top):
        print(f"  {n:>4}  {word}")
    print("\nEach of these is a candidate for backend/aliases.py, or a symbol")
    print("the corpus genuinely lacks.")
    return {"dreams_seen": seen, "no_match": blank, "top": counts.most_common(top)}


if __name__ == "__main__":
    report()
