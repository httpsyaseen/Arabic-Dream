# تعبير الرؤيا — Arabic dream interpretation

An Arabic dream-interpretation site grounded in five source texts. A dream is
typed in Arabic, its symbols are looked up **in code** against a corpus built
from those texts, and the model's only job is to explain what the lookup found.

The rule the whole design exists to enforce: **the reader always knows where a
statement came from.** Every classical claim carries a book, an author, a printed
page and a link to the source scan. Anything not backed by the corpus is labelled
as such rather than dressed up as a citation.

## The five lenses

| Lens | Source | In the index |
|---|---|---|
| النابلسي | تعطير الأنام في تعبير المنام | 2,317 headwords — the symbol vocabulary |
| ابن سيرين | منتخب الكلام في تفسير الأحلام | 6,129 passages |
| ابن شاهين | الإشارات في علم العبارات | 2,412 passages |
| تعبير الرؤيا | كتاب تعبير الرؤيا | 1,201 passages |
| نفسية | تفسير الأحلام / الحلم وتأويله — فرويد | 1,806 passages |
| آداب | كتاب الرؤيا | 44 hadith on dream types and etiquette |

**11,548 passages.** Classical and psychological passages are tagged at index
time and never blended: the prompt forbids attributing a psychological meaning to
the interpretation books or the reverse, and the UI colours them differently.

The Ibn Sirin dictionary is popularly attributed to him but the attribution is
rejected by scholars — including Shamela's own editors. That note ships with
every citation from it. See `corpus/books.py`.

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY
.venv/bin/python -m corpus.index --build      # ~3s, writes corpus/data/index/
.venv/bin/uvicorn web.app:app --host 0.0.0.0 --port 3000
```

`.venv/bin/python -m corpus.models` lists the models your key can reach. Model
availability varies per key, so set `GEMINI_MODEL` from that list rather than
trusting the default. `GEMINI_FALLBACK_MODELS` is used when one runs out of
quota — on the free tier quota is metered **per model**, so rotation keeps the
site answering.

## What ships and what doesn't

Runtime needs roughly 450 lines and the built index:

```
corpus/data/index/*.json    13 MB   the corpus artifact
corpus/index.py             match() and load() only
corpus/arabic.py            Arabic normalisation
corpus/answer.py            prompt + response schema
web/                        API and page
```

Build-time only, never deployed — `scrape.py`, `filters.py`, `extract.py`,
`validate.py`, `english.py`, `books.py`, `prompts.py`, `schema.py`.

**Do not delete `corpus/data/raw/`.** The index is derived from it, and every
change to the alias table, chunking rules or key-length limits means rebuilding
from raw. Without it the matching rules are frozen and Shamela has to be
re-scraped.

## How matching works

Lexical, not semantic — this is glossary lookup, and an exact headword hit is
both more accurate and more explainable than a nearest-neighbour score.

Arabic joins the article and conjunctions to the word (`الحية`, `وحية`) and
attaches possessives at the end (`بيتي`), so headwords are matched with an
affix-tolerant pattern. Bare prepositions `ب/ك/ل` are deliberately excluded from
the prefix set — allowing them made `بير` match inside `كبيرة`.

Two things no affix rule can bridge, both handled by an explicit alias table in
`corpus/index.py`:

* **Broken plurals.** `حيات` never reaches `حية` by any rule; the stem changes.
* **Conjugated verbs.** People write "I fell" (`سقطت`, `وقعت`, `أقع`) while the
  dictionaries file everything under the verbal noun (`سقوط`).

The table is ~90 hand-written entries and should grow from real query logs.

## Rebuilding from scratch

```bash
.venv/bin/python -m corpus.scrape --all     # ~1,800 pages from Shamela, rate limited
.venv/bin/python -m corpus.filters --all    # report non-dream pages
.venv/bin/python -m corpus.index --build
```

The scrape is cached per page and resumable. `corpus/filters.py` drops prefaces,
biographies, narration chains and poetry — a page inside a titled ta'bir chapter
is kept regardless of its own vocabulary, because chapters like Ibn Sirin's on
Qur'anic suras are pure symbol content that never uses the word "dream".

## The extraction pipeline (currently unused)

`extract.py`, `validate.py` and `english.py` convert the Arabic prose into
structured, translated, citation-checked entries via Gemini. The running site
does not use any of it — indexing the raw scrape directly turned out to work
without extraction.

It is kept because the English version and a scholar review queue both need it.
`validate.py` is the fabrication guard: it discards any entry whose Arabic quote
is not literally present in the page it claims to quote, comparing normalised
forms since the model reproduces wording faithfully but not diacritics. There is
no override flag.

## Porting to Next.js

The corpus is plain JSON and moves unchanged. Only `index.py`'s matching logic
needs rewriting (~120 lines of regex and string work, no Python-specific
dependencies). Measured: index loads in 154 ms once at startup, matching costs
**1.5 ms per dream**, and the Gemini call is 6–9 s — so matching is a rounding
error either way.

Load the index at module scope, not per request.

## Sources

All texts are from [al-Maktaba al-Shamela](https://shamela.ws) except the
psychological corpus, which is from the Internet Archive.
