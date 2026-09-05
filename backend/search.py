"""Finding a dream's symbols in the corpus. Pure code — no model involved.

This is the half of the system that decides *what the answer is allowed to be
about*. The model that runs afterwards can only discuss what this returns, so a
symbol that is missed here can never appear in an answer, and a symbol that is
invented here would poison one.

Matching is lexical on purpose. The books are glossaries keyed by symbol, so an
exact headword hit is both more accurate and more explainable than a similarity
score — you can show a user precisely why a symbol matched.

Measured: index loads in ~150 ms once at startup, a match costs ~1.5 ms.
"""

import functools
import json
import re
from pathlib import Path

from .aliases import ALIASES
from pipeline.arabic import normalize

INDEX = Path(__file__).resolve().parent.parent / "index"

# Arabic writes the article and some conjunctions joined to the word, so a
# headword must be allowed to carry them:
#   الحية (al-hayya = "the snake") · وحية (wa-hayya = "and a snake")
# The bare prepositions ب/ك/ل are deliberately excluded: allowing them let
# بير match inside كبيرة (kabira = "big") and report a "well" for a dream with
# no well in it. They cost more in false hits than they earn in recall.
_PREFIX = r"(?:وال|بال|كال|فال|لل|ال|و|ف)?"
# Possessives and sound plurals attach at the end:
#   بيتي (bayti = "my house") · أسنانه (asnanuhu = "his teeth")
_SUFFIX = r"(?:ها|هم|هن|كم|كن|نا|تين|ات|ين|ون|ان|ه|ي|ك)?"
_ARABIC = r"[؀-ۿ]"

MAX_SYMBOLS = 6
PSYCH_PER_SYMBOL = 2
CLASSICAL_PER_SYMBOL = 4
ADAB_MAX = 6

# Words suggesting the dream distressed the dreamer. Only a hint — the model
# decides — but it selects which etiquette passages are worth supplying.
DISTRESS_HINTS = (
    "خائف", "خفت", "خوف", "مرعب", "مفزع", "فزع", "كابوس", "مزعج",
    "أبكي", "بكيت", "حزين", "قلق", "دم", "موت", "أموت", "يطاردني",
    "هرب", "أهرب", "ثعبان", "حية", "نار", "جن", "شيطان", "قتل",
)


@functools.lru_cache(maxsize=16384)
def _pattern(key: str) -> re.Pattern:
    return re.compile(rf"(?<!{_ARABIC}){_PREFIX}{re.escape(key)}{_SUFFIX}(?!{_ARABIC})")


class Corpus:
    """The built index, loaded once and shared by every request."""

    def __init__(self) -> None:
        self.symbols: list[dict] = json.loads((INDEX / "symbols.json").read_text("utf-8"))
        self.passages: dict = json.loads((INDEX / "passages.json").read_text("utf-8"))
        self.adab: list[dict] = json.loads((INDEX / "adab.json").read_text("utf-8"))
        self.stats: dict = json.loads((INDEX / "stats.json").read_text("utf-8"))
        self._by_key = {e["key"]: e for e in self.symbols}

    # -- symbols ------------------------------------------------------------

    def match(self, dream: str, limit: int = MAX_SYMBOLS) -> list[dict]:
        """Symbols occurring in the dream, longest headword first."""
        text = normalize(dream)
        hits: list[dict] = []
        claimed: list[str] = []

        # Aliases run first so a dreamer's own wording reaches the classical
        # headword before the literal scan gets a chance to miss it.
        for alias, target in ALIASES.items():
            entry = self._by_key.get(target)
            if entry is not None and entry not in hits and _pattern(alias).search(text):
                hits.append(entry)
                claimed.append(entry["key"])

        for entry in self.symbols:            # pre-sorted longest key first
            if len(hits) >= limit:
                break
            key = entry["key"]
            if entry in hits or key not in text:   # cheap reject before regex
                continue
            if not _pattern(key).search(text):
                continue
            # A longer headword already covers this one.
            if any(key in longer for longer in claimed):
                continue
            claimed.append(key)
            hits.append(entry)

        return [self._with_passages(e) for e in hits[:limit]]

    def _with_passages(self, entry: dict) -> dict:
        """Attach supporting passages, keeping the lenses balanced.

        Without a per-kind cap the classical books (about 11,000 passages
        between them) would crowd out the psychological source entirely and that
        lens would silently vanish from every answer.
        """
        pool = self.passages.get(entry["key"]) or []
        classical = [p for p in pool if p.get("kind") != "psychological"][:CLASSICAL_PER_SYMBOL]
        psych = [p for p in pool if p.get("kind") == "psychological"][:PSYCH_PER_SYMBOL]
        return {**entry, "passages": classical + psych}

    # -- etiquette ----------------------------------------------------------

    def adab_for(self, dream: str, distressing: bool = False) -> list[dict]:
        """A short, relevant slice of the hadith on dream types and etiquette.

        Kept short deliberately: this is context for the model's classification,
        not the answer, and a long tail of hadith crowds out the interpretation.
        """
        if not self.adab:
            return []
        words = set(normalize(dream).split())
        scored = []
        for item in self.adab:
            chapter = item.get("chapter_ar") or ""
            score = 0.0
            if "أنواع الرؤيا" in chapter or "جزء من النبوة" in chapter:
                score += 2
            if distressing and ("يكرهه" in chapter or "يتفل" in chapter):
                score += 3
            score += min(len(set(normalize(item["text_ar"]).split()) & words), 3) * 0.2
            scored.append((score, item))
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:ADAB_MAX]]

    # -- browsing -----------------------------------------------------------

    def search_symbols(self, q: str, limit: int, offset: int) -> tuple[int, list[dict]]:
        if q.strip():
            needle = normalize(q)
            pool = [e for e in self.symbols if needle in e["key"]]
            pool.sort(key=lambda e: (len(e["key"]), e["key"]))
        else:
            pool = sorted(self.symbols, key=lambda e: e["key"])
        return len(pool), pool[offset:offset + limit]

    def symbol(self, key: str) -> dict | None:
        entry = self._by_key.get(normalize(key))
        return self._with_passages(entry) if entry else None


def looks_distressing(dream: str) -> bool:
    return any(w in dream for w in DISTRESS_HINTS)
