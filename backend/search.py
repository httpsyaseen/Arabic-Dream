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
# ب is allowed because dreams are constantly described with it — حلمت بقطة
# ("I dreamed of a cat") — and excluding it silently lost those. ك and ل stay
# out: ك is what let بير match inside كبيرة (kabira = "big") and report a well
# for a dream containing none.
_PREFIX = r"(?:وال|بال|كال|فال|لل|ال|وب|فب|و|ف|ب)?"
# Possessives and sound plurals attach at the end:
#   بيتي (bayti = "my house") · أسنانه (asnanuhu = "his teeth")
# The bare ا matters more than it looks: Arabic marks an indefinite noun in the
# accusative with tanwin fath, written as an extra alif — طريقاً (tariqan = "a
# road"), مطراً (mataran = "rain"). Normalisation strips the tanwin mark but
# leaves that alif, so without it here every direct object in a dream sentence
# silently failed to match its own headword.
_SUFFIX = r"(?:ها|هم|هن|كم|كن|نا|تين|ات|ين|ون|ان|ه|ي|ك|ا)?"
_ARABIC = r"[؀-ۿ]"

# Very common Arabic words that a short symbol plus a permitted affix can be
# read out of. فقط ("only") is ف + قط (qitt = cat); ذلك ("that") is ذل
# (dhull = humiliation) + ك. Both produced confident, entirely wrong symbols.
# Masking the whole word before matching is more reliable than trying to forbid
# the affix, which is legitimate elsewhere — دماً (blood) needs that same alif.
# Stems, not surface forms: the same word arrives as بعد, وبعدها, فبعد, so the
# token has its affixes stripped before this set is consulted.
COMMON_WORDS = {
    "فقط", "ذلك", "كذلك", "لذلك", "هكذا", "هذلك",
    "كانت", "كنت", "كانوا", "بينما", "عندما", "حينما", "ايضا", "ربما",
    "جدا", "قليلا", "كثيرا", "دايما", "احيانا", "فجاه", "مباشره",
    "بعد", "قبل", "لكن", "لان", "حول", "امام", "خلف", "بجانب", "نحو",
    "اثناء", "خلال", "وسط", "جانب", "طرف", "جهه", "مره", "مرات",
}

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

    # Stripping affixes with one greedy pass picks the wrong split when the stem
    # itself begins with a prefix letter: وبعدها is و + بعدها, but a pattern that
    # prefers the longer "وب" reads it as وب + عدها. So every plausible split is
    # tried and the word is masked if any of them is a common word.
    _PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال", "وب", "فب", "و", "ف", "ب", "")
    _SUFFIXES = ("ها", "هم", "هن", "كم", "كن", "نا", "ات", "ين", "ون", "ان",
                 "ه", "ي", "ك", "ا", "")

    @classmethod
    def _stems(cls, word: str):
        for pre in cls._PREFIXES:
            if pre and not word.startswith(pre):
                continue
            body = word[len(pre):]
            for suf in cls._SUFFIXES:
                if suf and not body.endswith(suf):
                    continue
                stem = body[: len(body) - len(suf)] if suf else body
                if stem:
                    yield stem

    @classmethod
    def _mask_common(cls, text: str) -> str:
        """Blank out words a short symbol could be misread out of."""
        return " ".join(
            "\u0000" if any(s in COMMON_WORDS for s in cls._stems(word)) else word
            for word in text.split()
        )

    def match(self, dream: str, limit: int = MAX_SYMBOLS,
              source: str | None = None) -> list[dict]:
        """Symbols occurring in the dream, longest headword first.

        `source` restricts which book's passages are attached. The vocabulary
        itself always comes from the dictionary source — that is the plumbing
        that finds symbols at all — but when a reader has chosen one interpreter,
        only that interpreter's text is shown to them and to the model.
        """
        text = self._mask_common(normalize(dream))
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

        return [self._with_passages(e, source) for e in hits[:limit]]

    @staticmethod
    def _round_robin(passages: list[dict], cap: int) -> list[dict]:
        """Take up to `cap` passages, one per source in turn.

        Taking the first `cap` of the list instead lets whichever book is
        indexed first swallow every slot: with four classical sources and a cap
        of four, Ibn Sirin's three passages plus one of Ibn Shahin's filled the
        quota and Ta'bir al-Ru'ya and the Shia volume were never sent at all,
        despite being indexed. Two of five lenses were silently dead.
        """
        by_source: dict[str, list[dict]] = {}
        for p in passages:
            by_source.setdefault(p["source"], []).append(p)

        picked, depth = [], 0
        while len(picked) < cap and any(len(v) > depth for v in by_source.values()):
            for group in by_source.values():
                if len(picked) >= cap:
                    break
                if len(group) > depth:
                    picked.append(group[depth])
            depth += 1
        return picked

    def _with_passages(self, entry: dict, source: str | None = None) -> dict:
        """Attach supporting passages, keeping the lenses balanced.

        Two separate balances. Classical and psychological are capped
        independently, or the ~11,000 classical passages would crowd the
        psychological source out of every answer. And within the classical
        share, sources are taken round-robin so every book gets a voice.

        When one source is selected neither applies — the reader asked for that
        book, so they get more of it and nothing else. The headword definition is
        included only when it belongs to the chosen source; otherwise picking
        "Ibn Sirin" would still show al-Nabulsi's definition of the symbol.
        """
        pool = self.passages.get(entry["key"]) or []

        if source:
            picked = [p for p in pool if p["source"] == source][:CLASSICAL_PER_SYMBOL + PSYCH_PER_SYMBOL]
            return {**entry, "passages": picked,
                    "own_text_applies": entry["source"] == source}

        classical = self._round_robin(
            [p for p in pool if p.get("kind") != "psychological"], CLASSICAL_PER_SYMBOL)
        psych = self._round_robin(
            [p for p in pool if p.get("kind") == "psychological"], PSYCH_PER_SYMBOL)
        return {**entry, "passages": classical + psych, "own_text_applies": True}

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

    def symbol(self, key: str, source: str | None = None) -> dict | None:
        entry = self._by_key.get(normalize(key))
        return self._with_passages(entry, source) if entry else None


def looks_distressing(dream: str) -> bool:
    return any(w in dream for w in DISTRESS_HINTS)
