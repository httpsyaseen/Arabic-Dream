"""Source book registry.

Every book we ingest is public-domain classical Arabic. English renderings are
produced by us (see corpus/extract.py) so the resulting corpus carries no
third-party translation rights.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Book:
    slug: str
    shamela_id: int
    title_ar: str
    title_en: str
    # How the page body is laid out, which decides the extraction prompt.
    #   "dictionary" -> one <p> per symbol, symbol name inside span.c2
    #   "prose"      -> topical chapters, symbols must be identified by the model
    layout: str
    # The lens key surfaced to end users.
    lens: str
    author_display: str
    # Shown verbatim in the UI wherever this book is cited. Attribution honesty
    # is a product feature, not a footnote — see README.
    attribution_note: str = ""
    # Pages that are front matter / indexes rather than interpretation content.
    skip_page_ids: frozenset = field(default_factory=frozenset)


BOOKS = {
    "nabulsi": Book(
        slug="nabulsi",
        shamela_id=1217,
        title_ar="تعطير الأنام في تعبير المنام",
        title_en="Ta'tir al-Anam fi Ta'bir al-Manam",
        layout="dictionary",
        lens="nabulsi",
        author_display="Abd al-Ghani al-Nabulsi (d. 1143 AH)",
        attribution_note=(
            "Authored by Abd al-Ghani al-Nabulsi. Attribution is undisputed."
        ),
    ),
    "ibn_sirin": Book(
        slug="ibn_sirin",
        shamela_id=21615,
        title_ar="تفسير الأحلام = منتخب الكلام في تفسير الأحلام",
        title_en="Muntakhab al-Kalam fi Tafsir al-Ahlam",
        layout="prose",
        lens="ibn_sirin",
        author_display="Attributed to Muhammad ibn Sirin (d. 110 AH)",
        attribution_note=(
            "This dictionary is popularly attributed to Ibn Sirin, but the "
            "attribution is rejected by scholars — including the editors of the "
            "Shamela edition itself. It quotes authorities who lived more than a "
            "century after Ibn Sirin died. We present it as the received "
            "tradition circulating under his name, not as his own writing."
        ),
    ),
    "ibn_shaheen": Book(
        slug="ibn_shaheen",
        shamela_id=9968,
        title_ar="الإشارات في علم العبارات",
        title_en="al-Isharat fi Ilm al-Ibarat",
        layout="prose",
        lens="ibn_shaheen",
        author_display="Ghars al-Din Khalil ibn Shahin al-Zahiri (d. 873 AH)",
        attribution_note="Authored by Ibn Shahin al-Zahiri. Attribution is undisputed.",
    ),
    # Fourth interpretation lens. Alphabetical like Nabulsi, so it contributes
    # headwords to the symbol vocabulary rather than only supporting passages.
    "tabir": Book(
        slug="tabir",
        shamela_id=10696,
        title_ar="تعبير الرؤيا",
        title_en="Ta'bir al-Ru'ya",
        layout="dictionary",
        lens="tabir",
        author_display="كتاب تعبير الرؤيا",
        attribution_note="",
    ),
    # Not an interpretation dictionary: this is the hadith and adab of dreams —
    # the types of dream, what to do after a distressing one, the etiquette of
    # relating a dream. It grounds the classification and adab layer that the
    # interpretation books assume but do not state.
    "ruya": Book(
        slug="ruya",
        shamela_id=20824,
        title_ar="الرؤيا",
        title_en="al-Ru'ya",
        layout="prose",
        lens="adab",
        author_display="كتاب الرؤيا",
        attribution_note="",
    ),
}


def get(slug: str) -> Book:
    try:
        return BOOKS[slug]
    except KeyError:
        raise SystemExit(f"unknown book {slug!r}; known: {', '.join(BOOKS)}")
