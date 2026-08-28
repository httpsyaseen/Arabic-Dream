"""Extraction prompts, one per book layout."""

COMMON_RULES = """\
You are preparing a scholarly reference corpus of classical Islamic dream
interpretation (ta'bir al-ru'ya). A qualified scholar will review everything you
produce before it reaches any user, so accuracy and traceability matter far more
than fluency or completeness.

Hard rules:

1. `quote_ar` must be copied VERBATIM from the passage given to you: the same
   characters, in the same order, contiguous, with the diacritics exactly as they
   appear. Do not fix spelling, modernise orthography, join fragments, or trim
   words from the middle. An automated check compares your quote against the
   source and silently discards any entry that does not match, so a paraphrase
   means the entry is simply lost.
2. Extract only what the passage actually says. Never supplement from your own
   knowledge of Ibn Sirin, al-Nabulsi, hadith, or any other source. If the passage
   is unclear, say so in `notes` rather than smoothing it over.
3. Translate faithfully, including material that reads as harsh, superstitious or
   unfamiliar. You are not editing the tradition, you are recording it. Put any
   concern in `notes` and let the reviewing scholar decide.
4. Classical interpretation is overwhelmingly conditional — "if he sees X then A,
   but if Y then B". Preserve that structure in `conditions` instead of flattening
   it into one general meaning. This structure is the point of the exercise.
5. Skip passages that are not symbol interpretation: chains of narration,
   biographical anecdotes, prefaces, poetry, indexes. Returning an empty list is a
   correct answer for such a page.
6. Do not invent page numbers, book titles or citations. Provenance is attached
   separately.
"""

DICTIONARY = COMMON_RULES + """\

This passage comes from an alphabetically arranged dream dictionary. Each
paragraph begins with a headword in brackets, e.g. `(أرز)`, followed by that
symbol's interpretation. Produce exactly one entry per headword paragraph, using
the bracketed headword as `symbol_ar`.

Where one paragraph covers several distinct dream situations, keep it as a single
entry and split the situations across `conditions`.
"""

PROSE = COMMON_RULES + """\

This passage comes from a topically arranged chapter of continuous prose rather
than a dictionary. Read it and identify each distinct dream symbol it interprets.
A single page may yield several entries, one entry, or none.

Phrases such as `ومن رأى` ("and whoever sees"), `من رأى أن` and `وقال فلان`
introduce individual rulings and opinions — these usually mark where one
condition ends and the next begins. Attribute nothing to a named authority unless
the passage names them.

The chapter heading is given for context only. Do not treat it as a symbol and do
not let it pull you toward symbols the passage does not actually discuss.
"""

LAYOUT_PROMPTS = {"dictionary": DICTIONARY, "prose": PROSE}


def build(book, page: dict) -> str:
    """Assemble the user-turn payload for one page."""
    header = [
        f"Book: {book.title_ar} ({book.title_en})",
        f"Author: {book.author_display}",
    ]
    if page.get("chapter"):
        header.append(f"Chapter: {page['chapter']}")
    if page.get("printed_page"):
        header.append(f"Printed page: {page['printed_page']}")
    return (
        "\n".join(header)
        + "\n\nPASSAGE (extract from this text and nothing else):\n"
        + "-" * 60
        + "\n"
        + page["text"]
        + "\n"
        + "-" * 60
    )
