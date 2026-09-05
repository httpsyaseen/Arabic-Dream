# How the books become structured data

Written for a reader who does not know Arabic. Every Arabic term appears with a
transliteration and an English meaning.

Seven books, four physical layouts, one output format. This document explains
each step and — more usefully — **why** each decision was made, including the
mistakes that forced them.

---

## The four stages

```
  ①  DOWNLOAD          ②  PARSE              ③  INDEX            ④  SEARCH
  the raw book    →    uniform chunks   →   searchable      →   symbols for
                                            structure           one dream

  context/<book>/      context/<book>/       index/*.json        (at request
      raw/                chunks.json                             time)

  pipeline/scrape.py   pipeline/parse.py   pipeline/          backend/
                                           build_index.py     search.py

   no AI                 no AI                no AI              no AI
```

**No AI is involved in any of it.** That is the point. The model runs only after
all four stages are done, and can only discuss what stage ④ returned.

---

## Stage ① — Download

Two kinds of source.

**Scraped from Shamela** (5 books). [al-Maktaba al-Shamela](https://shamela.ws)
("The Comprehensive Library") serves one page at a time. The text sits in an HTML
element with class `nass` (نص = "text"), which carries two attributes:

| Attribute | Meaning |
|---|---|
| `data-page-id` | the page number in the URL |
| `data-page-num` | **the page number in the physical printed book** |

The second is what lets a scholar check a citation against the paper edition, so
both are stored. Requests are rate-limited to 1.2 s and cached per page, so a
rerun is free and an interruption resumes.

**Plain text files** (2 sources: Freud, and the Shia volume). Downloaded from the
Internet Archive as OCR text and dropped into the folder directly.

Result: `context/<book>/raw/`

---

## Stage ② — Parse

### First: is this page even about dreams?

The books are not purely interpretation. They open with prefaces, an editor's
introduction and the author's biography, and drift into chains of narration and
poetry. None of that belongs in a dream corpus.

`is_dream_page()` in `pipeline/parse.py` drops those before anything is chunked.
It cost me two bugs to get right:

**Bug 1 — it dropped all 492 pages.** Shamela puts فهرس الكتاب (*fihris
al-kitab* = "book index") in the breadcrumb of *every* page, so a "skip front
matter" rule matched everywhere. Fixed by stripping that boilerplate first.

**Bug 2 — it dropped Ibn Sirin's chapter on Qur'anic suras.** That chapter is
pure symbol content — "whoever recites Surat al-Kahf in a dream will attain his
wishes" — but it is phrased with ومن قرأ (*wa-man qara'a* = "whoever recites")
and never uses the word "dream" at all. It scored zero.

The fix generalises: **if a page sits inside a chapter whose title contains dream
vocabulary, keep it regardless of the page's own wording.** Losing real content
costs far more than keeping a digression the chunker will never match anyway.

Currently drops 214 non-dream passages across the scraped books.

### Then: one chunk format

Every book, whatever its layout, becomes the same chunk:

```json
{
  "source": "nabulsi",
  "kind": "symbol",
  "symbol_ar": "حية",
  "text_ar": "(حية) في المنام عدو أو دولة أو كنز أو امرأة أو ولد...",
  "chapter_ar": "باب الحاء",
  "printed_page": "94",
  "url": "https://shamela.ws/book/1217/91"
}
```

`text_ar` is **always verbatim**. Nothing is normalised, cleaned or rewritten,
because this is the text that will be quoted to a user and shown next to a page
number. Normalisation happens only at match time, and is never written back.

`kind` is one of three:

| kind | meaning | which books |
|---|---|---|
| `symbol` | a dictionary entry with a headword | al-Nabulsi only |
| `passage` | a chunk of interpretive prose | Ibn Sirin, Ibn Shahin, Ta'bir, al-Sadiq, Freud |
| `hadith` | a saying about dream etiquette | al-Ru'ya only |

### Parser A — `shamela_dictionary` (al-Nabulsi)

The book is an alphabetical dictionary. Shamela marks each headword in its own
HTML element, so the scraper already captured them — **for free, with no AI**.

```
- (أرز) في المنام مال فيه نصب وشغب...
   ↑ headword: aruzz = rice        ↑ its interpretation
```

**This is the only parser that produces symbols, so this one book defines the
entire vocabulary the whole system searches by.** The other six are then searched
for whatever it names.

Two filters:
- Headwords must be **3–30 characters and at most 4 words**. Shamela occasionally
  wraps a whole sentence in a headword element ("وقد ضمن الحسن بن الحسين الخلال…"
  = "and al-Hasan ibn al-Husayn al-Khallal included…"), and those are not symbols.
- When a headword appears on several pages, the **longest treatment wins**.

Result: **2,317 symbols.**

### Parser B — `shamela_prose` (Ibn Sirin, Ibn Shahin, Ta'bir al-Ru'ya)

These are topical prose with no headwords and almost no punctuation. You cannot
split on full stops because there aren't any.

But classical prose has its own structural markers — fixed phrases that begin a
new ruling:

| Arabic | Transliteration | English |
|---|---|---|
| فإن رأى | fa-in ra'a | "and if he sees" |
| ومن رأى | wa-man ra'a | "and whoever sees" |
| وإن رأى | wa-in ra'a | "and if he sees" |
| وقال | wa-qala | "and he said" |
| وأما | wa-amma | "and as for" |
| ومن قرأ | wa-man qara'a | "and whoever recites" |

So the text is cut at those phrases. Each piece is one ruling, which is exactly
the unit you want to retrieve and quote.

Chunks under 80 characters are dropped as fragments; anything over 700 is split,
because a long chunk buries the relevant sentence when it reaches the model.

### Parser C — `shamela_hadith` (al-Ru'ya)

Not a dictionary at all — hadith about dreams. Selected **by chapter title**,
because this book's chapters are precisely the topics needed:

| Chapter | English |
|---|---|
| ذكر أنواع الرؤيا | mention of the types of vision |
| الرؤيا الصالحة جزء من النبوة | the good vision is part of prophethood |
| الأمر لمن رأى ما يكرهه أن يتفل عن يساره ثلاثاً | the instruction to spit to the left three times |
| النهي عن الإخبار بالرؤيا المكروهة | the prohibition on relating a disliked dream |

The same hadith recurs verbatim across chapters, so the first 80 characters of
its normalised form act as a fingerprint for de-duplication.

Result: **44 hadith** — the classification and etiquette layer.

### Parser D — `textfile` (Freud, al-Sadiq)

Plain text with no page structure, so it is cut on paragraphs and accumulated to
~420 characters before emitting a chunk.

**Why accumulate?** I got this wrong the first time. The initial version flushed
a chunk as soon as it passed the 80-character minimum, so the Shia volume came
out as 5,038 chunks averaging 133 characters — each too short to carry any
context. Accumulating to a target fixed it: **1,490 chunks averaging 453
characters.**

#### The OCR rescue

The Shia volume is a scan of a decorated edition. Every page has ornamental
borders, and OCR turned them into runs of garbage:

```
E O ATTN iv gO Sa o RTT SARO
OF a OOF FO. OF a FO OF fS O a O O ao O r a O e
```

Roughly 38% of the file is this. Filtering on the **ratio of Arabic letters** —
keep a line only if ≥90% of its letters are Arabic, it is ≥25 characters, has ≥5
words, and averages ≥2.5 characters per word — separates text from ornament
cleanly, recovering **679 KB (62%)** of readable Arabic.

The last condition matters: ornament fragments survive as runs of one- and
two-letter tokens that pass every other test.

This runs only for sources flagged `needs_ocr_clean` in the registry, since
applying it to clean text would discard legitimate short lines.

---

## Stage ③ — Index

`pipeline/build_index.py` turns chunks into three files.

**`symbols.json`** — the vocabulary. Each entry gets a `key`: its headword
normalised for matching (see below). Sorted **longest key first**, so at match
time a longer headword suppresses its own substrings — otherwise a dream
mentioning إلية الشاة (*alyat al-sha* = "the sheep's tail") would also report
شاة (*sha* = "sheep") as a separate symbol.

**`passages.json`** — an inverted index, `symbol key → passages that mention it`.

The direction here is a deliberate performance decision. Running one regular
expression per symbol against every passage would be 2,317 × ~16,000 ≈ **37
million operations**. Instead, each passage generates the keys it *could*
contain — every word and phrase, with prefixes and suffixes stripped — and those
are intersected with the known vocabulary. **The whole index builds in ~4.7
seconds.**

Capped at 3 passages per symbol **per source**, so no single book dominates.

**`adab.json`** — the 44 hadith.

### Current totals

| Source | Role | Contribution |
|---|---|---|
| al-Nabulsi | vocabulary | 2,317 symbols |
| Ibn Sirin | passages | 2,934 |
| Ibn Shahin | passages | 2,918 |
| al-Sadiq (Shia) | passages | 2,702 |
| Ta'bir al-Ru'ya | passages | 2,537 |
| Freud | passages | 1,861 |
| al-Ru'ya | hadith | 44 |

**12,952 passages · 2,317 symbols · 1,685 symbols with supporting text.**

---

## Stage ④ — Search

At request time, in `backend/search.py`. Measured: **~1.5 ms per dream.**

### Normalisation

Arabic has optional vowel marks and several letters with variant forms, so the
same word appears many ways. Both the dream and the index keys are folded:

| Rule | Example |
|---|---|
| strip vowel marks | حَيَّة → حية |
| أ إ آ → ا | أسنان → اسنان |
| ى → ي | شعرى → شعري |
| ة → ه | حية → حيه |
| remove punctuation, collapse spaces | |

**Used for matching only.** Stored and displayed text stays verbatim.

### The alias table

Two things no rule can bridge, both handled by ~90 hand-written entries in
`backend/aliases.py`:

**Broken plurals.** English adds a suffix; Arabic restructures the word:

| Singular | Plural |
|---|---|
| حية (*hayya* = snake) | حيات (*hayyat*) |
| ضرس (*dirs* = molar) | أضراس (*adras*) |

**Conjugated verbs.** People write verbs; dictionaries file the verbal noun:

| Typed | Meaning | Dictionary entry |
|---|---|---|
| سقطت (*saqattu*) | "I fell" | سقوط (*suqut* = falling) |
| وقعت (*waqa'tu*) | "I fell" | سقوط |
| أطير (*atir*) | "I fly" | طيران (*tayaran* = flying) |

**This was a real bug.** A dream saying "I fell from a building" returned nothing,
because سقوط was indexed but وقعت reached it by no rule. Adding verb forms fixed
it.

Also maps modern words: بناية (*binaya*, modern "building") → بناء (*bina'*,
classical), and أسنان (*asnan* = teeth) → ضرس (*dirs* = molar), because
al-Nabulsi files teeth under "molar" and nobody describing a dream types "molar".

### Affix-tolerant matching

Arabic joins the article and some conjunctions to the front, and possessives to
the back:

| Written | Parts | English |
|---|---|---|
| الحية | ال + حية | "the snake" |
| وحية | و + حية | "and a snake" |
| بيتي | بيت + ي | "my house" |
| أسنانه | أسنان + ه | "his teeth" |

So the pattern permits those affixes but forbids any other Arabic letter on
either side:

```
(?<!arabic) [prefix]? KEY [suffix]? (?!arabic)
```

**One deliberate exclusion.** The single-letter prepositions ب / ك / ل are *not*
allowed as prefixes. Permitting them made بير match inside كبيرة (*kabira* =
"big") and return the symbol "well" for a dream containing no well. They cost
more in false matches than they earn in recall.

### Lens balance

Per symbol: **4 classical + 2 psychological**, enforced in code.

Without the cap, the ~11,000 classical passages would bury Freud's 1,861
entirely, and the psychological lens would silently disappear from every answer.

---

## Adding a book

One entry in `pipeline/sources.py`:

```python
"newbook": Source(
    slug="newbook",
    name_ar="...", name_en="...",
    author_ar="...", author_en="...",
    kind="classical",        # classical | psychological | adab
    role="passages",         # symbols | passages | hadith
    parser="shamela_prose",  # which of the four parsers
    shamela_id=12345,        # or files=("book.txt",)
),
```

Then:

```bash
python -m pipeline.scrape newbook     # or drop the .txt into context/newbook/raw/
python -m pipeline.parse newbook
python -m pipeline.build_index
```

That is the whole procedure. The registry is the single source of truth —
previously these facts lived in three separate structures and adding a book meant
editing all of them and keeping the names in sync by hand.

---

## Two things deliberately not done

**No AI in the pipeline.** An extraction pipeline once existed (removed; see git history) that used
Gemini to turn prose into structured translated entries, with a guard that
discarded any entry whose Arabic quote was not literally present in its source
page. It works — 95–100% pass rates — but the site does not use it, because
indexing the raw scrape directly turned out to produce a working product without
it. It is kept for the English version, where translation is unavoidable.

**No semantic search.** This is glossary lookup: the books are literally
dictionaries keyed by symbol. An exact headword hit is more accurate *and*
explainable — you can show a user why a symbol matched. Embeddings would mainly
paper over gaps in the alias table, and that table is cheaper to grow than a
vector pipeline is to run. If it is ever added, note that 2,317 vectors is ~7 MB
and brute-force cosine is sub-millisecond, so **no vector database is required**
at this scale.
