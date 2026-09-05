"""Regression tests for every bug documented in docs/CASE-STUDY.md.

    .venv/bin/python -m tests.test_regressions

Each of these shipped, was found, and was fixed. Every one of them failed
*silently* — returning a plausible answer instead of an error — which is exactly
the class of bug that comes back unnoticed during a refactor. This file exists so
that if one does, something says so.

No test framework: it runs with the interpreter alone so it works on a fresh
clone before anything is installed beyond the app's own dependencies.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.search import Corpus                    # noqa: E402
from pipeline.arabic import normalize                # noqa: E402
from pipeline.parse import is_dream_page             # noqa: E402

CORPUS = Corpus()
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"  — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def symbols_for(dream: str) -> list[str]:
    return [m["symbol_ar"] for m in CORPUS.match(dream)]


# --------------------------------------------------------------------------
# Bug 1 — the dream-content filter dropped every page, because the library puts
# the words "book index" in the breadcrumb of all of them.
# --------------------------------------------------------------------------
def bug1_filter_keeps_content_pages() -> None:
    print("\nBug 1 — filter must not reject every page")
    raw = Path("context/nabulsi/raw")
    pages = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(raw.glob("*.json"))]
    kept = sum(1 for p in pages if is_dream_page(p))
    check("keeps the great majority of a dictionary's pages",
          kept > len(pages) * 0.9, f"kept {kept}/{len(pages)}")


# --------------------------------------------------------------------------
# Bug 2 — the fixed filter then dropped Ibn Sirin's chapter on reciting Qur'an
# in dreams: pure symbol content that never uses the word "dream".
# --------------------------------------------------------------------------
def bug2_filter_keeps_chapters_without_dream_words() -> None:
    print("\nBug 2 — a page in a dream chapter is kept even with no dream words")
    page = {
        "text": "ومن قرأ سورة الكهف نال الأماني وطال عمره " * 6,
        "heading": "فهرس الكتاب (الباب الخامس) في تأويل سور القرآن العزيز",
        "chapter": "(الباب الخامس) في تأويل سور القرآن العزيز",
    }
    check("kept on the strength of its chapter title", is_dream_page(page))

    noise = {"text": "وقال ذو الرمة لقادح نار فقلت له ارفعها إليك وأحيها " * 5,
             "heading": "فهرس الكتاب", "chapter": "باب الشعر"}
    check("a poetry digression is still dropped", not is_dream_page(noise))


# --------------------------------------------------------------------------
# Bug 3 — people write verbs, the dictionaries store verbal nouns.
# --------------------------------------------------------------------------
def bug3_conjugated_verbs_reach_their_noun() -> None:
    print("\nBug 3 — conjugated verbs reach their dictionary form")
    for dream, expect in [
        ("رأيت أني أسقط من بناية", "سقوط"),      # "I fall"     -> falling
        ("حلمت أني وقعت من مكان عال", "سقوط"),   # "I fell"     -> falling
        ("رأيت أني أطير", "طيران"),               # "I fly"      -> flying
        ("حلمت أني أغرق", "غرق"),                 # "I drown"    -> drowning
    ]:
        check(f"{dream[:30]} -> {expect}", expect in symbols_for(dream),
              f"got {symbols_for(dream)}")


# --------------------------------------------------------------------------
# Bug 4 — the worst one. Arabic marks an indefinite noun in the object position
# with a trailing alif; it was missing from the allowed endings, so every direct
# object silently failed to match while still producing a fluent answer.
# --------------------------------------------------------------------------
def bug4_accusative_nouns_match() -> None:
    print("\nBug 4 — nouns carrying tanwin fath still match")
    for dream, expect in [
        ("رأيت طريقاً لا أعرفه", "طريق"),   # "a road"
        ("رأيت مطراً غزيراً", "مطر"),        # "rain"
        ("رأيت بيتاً كبيراً", "بيت"),        # "a house"
        ("رأيت كلباً أسود", "كلب"),          # "a dog"
    ]:
        check(f"{dream} -> {expect}", expect in symbols_for(dream),
              f"got {symbols_for(dream)}")


# --------------------------------------------------------------------------
# Bug 5 — with all sources selected, passages were taken in list order, so the
# last books in the list were never sent at all.
# --------------------------------------------------------------------------
def bug5_no_source_is_starved() -> None:
    print("\nBug 5 — every source with indexed passages gets a turn")
    dream = "رأيت حية في بيتي ثم رأيت ماءً صافياً ونوراً"
    matches = CORPUS.match(dream)
    sent = {p["source"] for m in matches for p in m["passages"]}
    available = {p["source"] for m in matches
                 for p in (CORPUS.passages.get(m["key"]) or [])}
    check("no source is indexed but never sent",
          not (available - sent), f"starved: {available - sent}")
    check("the psychological lens survives the classical ones",
          any(p.get("kind") == "psychological" for m in matches for p in m["passages"]))


# --------------------------------------------------------------------------
# Later fixes, found while building the Arabic symbol dictionary.
# --------------------------------------------------------------------------
def bug6_two_letter_symbols_exist() -> None:
    print("\nBug 6 — two-letter headwords are indexed, function words are not")
    keys = {e["key"] for e in CORPUS.symbols}
    for word in ["دم", "يد", "سن", "جن"]:      # blood, hand, tooth, jinn
        check(f"{word} is a symbol", normalize(word) in keys)
    for stop in ["من", "في", "ما"]:            # from, in, what
        check(f"{stop} is NOT a symbol", normalize(stop) not in keys)
    check("an ordinary sentence stays quiet",
          symbols_for("كان في المنام ما لا أذكره") == [],
          f"got {symbols_for('كان في المنام ما لا أذكره')}")


def bug7_ba_preposition_allowed() -> None:
    print("\nBug 7 — dreams described with ب (\"of\") still match")
    for dream, expect in [("حلمت بقطة بيضاء", "سنور"), ("حلمت بحية", "حية"),
                          ("حلمت بماء صاف", "ماء")]:
        check(f"{dream} -> {expect}", expect in symbols_for(dream),
              f"got {symbols_for(dream)}")
    # ك stays excluded: it is what let بير match inside كبيرة ("big").
    check("كبير does not produce a spurious symbol",
          "بئر" not in symbols_for("كنت أمشي في شارع كبير"),
          f"got {symbols_for('كنت أمشي في شارع كبير')}")


def bug8_modern_words_reach_classical_entries() -> None:
    print("\nBug 8 — modern words reach the older word the books use")
    for dream, expect in [("رأيت أسداً", "سبع"),        # lion -> beast of prey
                          ("رأيت ملابس جديدة", "ثوب"),  # clothes -> garment
                          ("حلمت أن أسناني تسقط", "ضرس")]:  # teeth -> molar
        check(f"{dream} -> {expect}", expect in symbols_for(dream),
              f"got {symbols_for(dream)}")


def bug9_short_symbols_do_not_match_common_words() -> None:
    print("\nBug 9 — short symbols are not read out of ordinary words")
    # فقط ("only") is ف + قط (cat); ذلك ("that") is ذل (humiliation) + ك.
    for sentence in ["كان ذلك مثال ذلك فقط",
                     "كنت أمشي وبعدها رأيت ذلك",
                     "وقفت بجانبه أثناء الحديث",
                     "رأيت شيئاً حولي مرة أخرى"]:
        got = symbols_for(sentence)
        check(f"quiet on: {sentence[:32]}", got == [], f"got {got}")
    # ...while the same words as real symbols still work.
    check("ذل as a genuine symbol still matches", "ذل" in symbols_for("حلمت بذل وهوان"))
    check("قط as a genuine symbol still matches", "قط" in symbols_for("حلمت بقطة"))


def bug10_inline_headwords_extracted() -> None:
    print("\nBug 10 — the inline-headword book contributes symbols, not just prose")
    keys = {e["key"] for e in CORPUS.symbols}
    from_tabir = [e for e in CORPUS.symbols if e["source"] == "tabir"]
    check("Ta'bir al-Ru'ya supplies headwords", len(from_tabir) > 100,
          f"only {len(from_tabir)}")
    check("no section heading became a symbol",
          not any("مقاله" in e["key"] or "قال" in e["key"] for e in from_tabir))
    for word in ["بستان", "بوم"]:            # garden, owl
        check(f"{word} is reachable", normalize(word) in keys)


# --------------------------------------------------------------------------

def main() -> int:
    print(f"corpus: {len(CORPUS.symbols)} symbols, "
          f"{sum(len(v) for v in CORPUS.passages.values())} passages")
    for fn in (bug1_filter_keeps_content_pages,
               bug2_filter_keeps_chapters_without_dream_words,
               bug3_conjugated_verbs_reach_their_noun,
               bug4_accusative_nouns_match,
               bug5_no_source_is_starved,
               bug6_two_letter_symbols_exist,
               bug7_ba_preposition_allowed,
               bug8_modern_words_reach_classical_entries,
               bug9_short_symbols_do_not_match_common_words,
               bug10_inline_headwords_extracted):
        fn()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
