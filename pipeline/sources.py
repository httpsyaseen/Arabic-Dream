"""Registry of every source. One entry here is all it takes to add a book.

This replaces three structures that used to hold overlapping facts — a scraping
registry, two indexing dictionaries, and literal strings in the API — which meant
adding a book required editing all of them and keeping names in sync by hand.

Every source carries an Arabic **and** an English name. The API is consumed by
people who do not read Arabic, and a frontend should not have to ship its own
translation table.

`parser` selects how the raw text becomes chunks; see `pipeline/parse.py` and
`docs/PARSING.md`.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    slug: str                 # folder name under context/ and id in the API
    name_ar: str              # the book's full title
    name_en: str
    author_ar: str            # how the authorship is stated, with any caveat
    author_en: str
    # The name a reader actually recognises — "Ibn Sirin", not "Muntakhab
    # al-Kalam" and not "attributed to Ibn Sirin". This is what labels the
    # source picker and the cards; the full title stays as secondary detail.
    display_ar: str
    display_en: str

    # "classical" | "psychological" | "adab"
    kind: str
    # "symbols"  -> contributes headwords to the search vocabulary
    # "passages" -> contributes supporting text, found via those headwords
    # "both"     -> a dictionary whose prose is also worth searching
    # "hadith"   -> etiquette and classification material, not symbols
    role: str

    # How raw text is turned into chunks. See pipeline/parse.py.
    #   shamela_dictionary | shamela_prose | shamela_hadith | textfile
    parser: str

    shamela_id: int | None = None     # for scraped sources
    files: tuple[str, ...] = ()       # for plain-text sources under context/<slug>/raw/
    died: str = ""            # English form
    died_ar: str = ""         # Arabic form, for the Arabic interface
    source_url: str = ""
    color: str = "gold"               # display hint for the frontend

    # Shown verbatim wherever this source is cited. Attribution honesty is a
    # product feature — see docs/PARSING.md.
    note_ar: str = ""
    note_en: str = ""

    # Chapter-title keywords, used by the hadith parser to select relevant pages.
    topics: tuple[str, ...] = ()

    # True for scans whose ornamental borders OCR'd into noise; the text-file
    # parser then rescues lines by Arabic-letter ratio before chunking.
    needs_ocr_clean: bool = False


SOURCES: dict[str, Source] = {
    # ---------------------------------------------------------------- classical
    "nabulsi": Source(
        slug="nabulsi",
        display_ar="النابلسي",
        display_en="Al-Nabulsi",
        name_ar="تعطير الأنام في تعبير المنام",
        name_en="Ta'tir al-Anam — Perfuming Mankind in the Interpretation of Dreams",
        author_ar="عبد الغني النابلسي",
        author_en="Abd al-Ghani al-Nabulsi",
        kind="classical",
        role="symbols",
        parser="shamela_dictionary",
        shamela_id=1217,
        died="d. 1143 AH / 1731 CE",
        died_ar="ت ١١٤٣هـ / ١٧٣١م",
        source_url="https://shamela.ws/book/1217",
    ),
    "ibn_sirin": Source(
        slug="ibn_sirin",
        display_ar="ابن سيرين",
        display_en="Ibn Sirin",
        name_ar="تفسير الأحلام (منتخب الكلام)",
        name_en="Muntakhab al-Kalam — Selected Discourse on the Interpretation of Dreams",
        author_ar="منسوب إلى ابن سيرين",
        author_en="Attributed to Ibn Sirin",
        kind="classical",
        role="passages",
        parser="shamela_prose",
        shamela_id=21615,
        died="d. 110 AH / 728 CE",
        died_ar="ت ١١٠هـ / ٧٢٨م",
        source_url="https://shamela.ws/book/21615",
        note_ar=(
            "نسبة الكتاب إلى ابن سيرين غير صحيحة، وهو ما نصّ عليه المحققون، فالكتاب "
            "ينقل عن أعلام تأخّروا عنه بأكثر من قرن. ونعرضه بوصفه التراث المتداول "
            "باسمه لا بوصفه من تأليفه."
        ),
        note_en=(
            "The ascription to Ibn Sirin is rejected by scholars — the book quotes "
            "authorities who lived more than a century after his death. Carried as "
            "the tradition circulating under his name, not as his own writing."
        ),
    ),
    "ibn_shaheen": Source(
        slug="ibn_shaheen",
        display_ar="ابن شاهين",
        display_en="Ibn Shahin",
        name_ar="الإشارات في علم العبارات",
        name_en="al-Isharat — The Indications in the Science of Interpretation",
        author_ar="ابن شاهين الظاهري",
        author_en="Ibn Shahin al-Zahiri",
        kind="classical",
        role="passages",
        parser="shamela_prose",
        shamela_id=9968,
        died="d. 873 AH / 1468 CE",
        died_ar="ت ٨٧٣هـ / ١٤٦٨م",
        source_url="https://shamela.ws/book/9968",
    ),
    "tabir": Source(
        slug="tabir",
        display_ar="كتاب تعبير الرؤيا",
        display_en="Ta'bir al-Ru'ya",
        name_ar="تعبير الرؤيا",
        name_en="Ta'bir al-Ru'ya — The Interpretation of Visions",
        author_ar="كتاب تعبير الرؤيا",
        author_en="Ta'bir al-Ru'ya",
        kind="classical",
        role="both",
        parser="shamela_inline_dictionary",
        shamela_id=10696,
        source_url="https://shamela.ws/book/10696",
    ),

    # ------------------------------------------------------------- Shia tradition
    "sadiq": Source(
        slug="sadiq",
        display_ar="الإمام الصادق",
        display_en="Imam Al-Sadiq",
        name_ar="تفسير الأحلام الكبير برواية الإمام علي وأهل البيت",
        name_en="The Great Book of Dream Interpretation, narrated from Imam Ali and the Ahl al-Bayt",
        author_ar="منسوب إلى الإمام جعفر الصادق وأهل البيت",
        author_en="Attributed to Imam Ja'far al-Sadiq and the Ahl al-Bayt",
        kind="classical",
        role="passages",
        parser="textfile",
        files=("sadiq.txt",),
        needs_ocr_clean=True,
        died="al-Sadiq d. 148 AH / 765 CE",
        died_ar="الصادق ت ١٤٨هـ / ٧٦٥م",
        source_url="https://archive.org/details/0932890343",
        color="teal",
        note_ar=(
            "هذا الكتاب يمثّل تراث التعبير عند الشيعة، وهو مجموع متأخر. ونسبته إلى "
            "الإمام الصادق غير ثابتة؛ فقد نبّه الباحثون على أن بعض المتداول باسمه "
            "يذكر ما لم يكن موجوداً في عصره. ونعرضه بوصفه التراث المنسوب إليه لا "
            "بوصفه من كلامه. والنص مأخوذ من مسح ضوئي، وقد يبقى فيه شيء من خطأ القراءة."
        ),
        note_en=(
            "This represents the Shia strand of dream interpretation. It is a late "
            "compilation, and the attribution to Imam al-Sadiq is not established — "
            "researchers note that texts circulating under his name mention things "
            "that did not exist in his lifetime. Carried as the tradition ascribed "
            "to him, not as his own words. The text comes from a scan and some OCR "
            "errors remain."
        ),
    ),

    # ------------------------------------------------------------- psychological
    "freud": Source(
        slug="freud",
        display_ar="سيغموند فرويد",
        display_en="Sigmund Freud",
        name_ar="تفسير الأحلام / الحلم وتأويله",
        name_en="The Interpretation of Dreams / On Dreams",
        author_ar="سيغموند فرويد",
        author_en="Sigmund Freud",
        kind="psychological",
        role="passages",
        parser="textfile",
        files=("freud_tafsir.txt", "freud_hulm.txt"),
        source_url="https://archive.org/details/elshandawily6168",
        color="purple",
        note_ar="قراءة نفسية، ليست من كتب التعبير، وتُعرض مستقلة عنها.",
        note_en=(
            "A psychological reading. Not one of the interpretation books, and shown "
            "separately — the two traditions are never blended."
        ),
    ),

    # --------------------------------------------------------------------- adab
    "ruya": Source(
        slug="ruya",
        display_ar="أحاديث الرؤيا وآدابها",
        display_en="Hadith on dreams",
        name_ar="الرؤيا",
        name_en="al-Ru'ya — hadith on dreams and their etiquette",
        author_ar="كتاب الرؤيا",
        author_en="al-Ru'ya",
        kind="adab",
        role="hadith",
        parser="shamela_hadith",
        shamela_id=20824,
        source_url="https://shamela.ws/book/20824",
        color="green",
        note_ar="ليس كتاب رموز، بل أحاديث في أنواع الرؤيا وآدابها.",
        note_en=(
            "Not a symbol dictionary — hadith on the types of dream and the etiquette "
            "that follows one, which grounds classification and the sunnah response."
        ),
        topics=(
            "أنواع الرؤيا", "الرؤيا الصالحة", "بشرى", "جزء من النبوة",
            "يتفل عن يساره", "ما يكرهه", "يقوم فيصلي", "لا يحدث بها",
            "أضغاث", "حديث النفس", "تحزين من الشيطان", "الاستعاذة",
        ),
    ),
}


# Names that people search for but which have no book behind them. Kept here so
# the site can answer honestly instead of silently having nothing to say.
NON_SOURCES = {
    "ibn_kathir": {
        "name_ar": "ابن كثير",
        "name_en": "Ibn Kathir",
        "status": "no_such_work",
        "explanation_ar": (
            "لم يؤلف الحافظ ابن كثير (ت ٧٧٤هـ) كتاباً في تعبير الرؤيا. وهو مفسّر "
            "ومؤرخ، بل كان ممن أنكروا نسبة كتاب التعبير المتداول إلى ابن سيرين. "
            "وما يُنشر اليوم باسم «تفسير الأحلام لابن كثير» لا أصل له."
        ),
        "explanation_en": (
            "Ibn Kathir (d. 774 AH) wrote no work on dream interpretation. He was a "
            "Qur'an exegete and historian, and was in fact among those who rejected "
            "the ascription of the dream book to Ibn Sirin. Material published today "
            "as 'Ibn Kathir's dream interpretation' has no basis."
        ),
    },
    "idrisi": {
        "name_ar": "عبد الرحمن الإدريسي",
        "name_en": "Abdulrahman al-Idrisi",
        "status": "living_contemporary",
        "explanation_ar": (
            "معبّر معاصر حيّ، له موقع وقنوات على الإنترنت، وليس من مؤلفي كتب التعبير "
            "الكلاسيكية. فلا يوجد له متن قديم يُفهرس، ومادته مِلك له."
        ),
        "explanation_en": (
            "A living contemporary interpreter with his own website and channels, not "
            "a classical author. There is no historical text to index, and his "
            "material is his own work."
        ),
    },
}


def get(slug: str) -> Source:
    try:
        return SOURCES[slug]
    except KeyError:
        raise SystemExit(f"unknown source {slug!r}; known: {', '.join(SOURCES)}")


def scraped() -> list[Source]:
    return [s for s in SOURCES.values() if s.shamela_id is not None]


def as_dict(s: Source) -> dict:
    """Public shape returned by the API."""
    return {
        "slug": s.slug,
        "display": {"ar": s.display_ar, "en": s.display_en},
        "name": {"ar": s.name_ar, "en": s.name_en},
        "author": {"ar": s.author_ar, "en": s.author_en},
        "kind": s.kind,
        "role": s.role,
        "died": {"ar": s.died_ar or s.died, "en": s.died} if s.died else None,
        "source_url": s.source_url or None,
        "color": s.color,
        "note": {"ar": s.note_ar, "en": s.note_en} if s.note_en else None,
    }
