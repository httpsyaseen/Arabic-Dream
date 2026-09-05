"""Arabic text normalisation.

Two forms of every string are kept downstream:

  * the verbatim source text, which is what we cite and display, and
  * a normalised form, used only for matching.

The model's quotes will differ from the source in diacritics, hamza seating and
whitespace even when the wording is identical, so the substring guard in
corpus/validate.py compares normalised forms. Normalisation is deliberately
lossy and must never be written back into a citation.
"""

import re
import unicodedata

# Harakat, tanwin, shadda, sukun, superscript alef, and the Quranic annotation
# marks that appear in Shamela texts.
_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = re.compile(r"ـ+")
_NON_TEXT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")

_LETTER_MAP = str.maketrans(
    {
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
        "ى": "ي", "ئ": "ي",
        "ؤ": "و",
        "ة": "ه",
        "ـ": "",
    }
)


def strip_diacritics(text: str) -> str:
    """Remove vowel marks but keep the letters and punctuation intact."""
    text = unicodedata.normalize("NFC", text)
    text = _DIACRITICS.sub("", text)
    return _TATWEEL.sub("", text)


def normalize(text: str) -> str:
    """Aggressive fold used for matching and alias lookup only."""
    text = strip_diacritics(text)
    text = text.translate(_LETTER_MAP)
    text = _NON_TEXT.sub(" ", text)
    text = _WS.sub(" ", text)
    return text.strip().lower()


def contains(haystack: str, needle: str) -> bool:
    """True when `needle` appears in `haystack` ignoring diacritics/orthography."""
    if not needle.strip():
        return False
    return normalize(needle) in normalize(haystack)


def strip_parens(label: str) -> str:
    """`(أرز)` -> `أرز`. Shamela wraps dictionary headwords in brackets."""
    return label.strip().strip("()﴿﴾[]«»").strip()
