# The Dream Project — A Complete Guide

Written for someone who does not read Arabic. Every Arabic term is given with a
transliteration and an English meaning the first time it appears, and the books
are described in English throughout.

This document explains what the project is, what the tradition behind it is, what
we built, why we built it that way, what works today, and what is still missing.

---

## Table of contents

1. [What this project is, in one page](#1-what-this-project-is-in-one-page)
2. [Background: what Islamic dream interpretation actually is](#2-background-what-islamic-dream-interpretation-actually-is)
3. [The six books, in English](#3-the-six-books-in-english)
4. [The competitor, and where the opening is](#4-the-competitor-and-where-the-opening-is)
5. [The core design decision](#5-the-core-design-decision)
6. [Stage 1 — Scraping the books](#6-stage-1--scraping-the-books)
7. [Stage 2 — Filtering out non-dream content](#7-stage-2--filtering-out-non-dream-content)
8. [Stage 3 — The extraction pipeline (built, then set aside)](#8-stage-3--the-extraction-pipeline-built-then-set-aside)
9. [Stage 4 — Building the index](#9-stage-4--building-the-index)
10. [Stage 5 — Matching a dream, and why Arabic makes it hard](#10-stage-5--matching-a-dream-and-why-arabic-makes-it-hard)
11. [Stage 6 — Composing the answer](#11-stage-6--composing-the-answer)
12. [Stage 7 — The website](#12-stage-7--the-website)
13. [What the user actually sees, translated](#13-what-the-user-actually-sees-translated)
14. [Every file in the repository](#14-every-file-in-the-repository)
15. [What works and what does not](#15-what-works-and-what-does-not)
16. [Costs, quota, and the API key](#16-costs-quota-and-the-api-key)
17. [What comes next](#17-what-comes-next)
18. [Glossary](#18-glossary)

---

## 1. What this project is, in one page

A website where a user types a dream in Arabic and receives an interpretation
drawn from classical Islamic dream-interpretation books, plus a psychological
reading, with every claim traceable to a specific page of a specific book.

The important word is **traceable**. Every competitor in this space is an AI
chatbot with a religious-sounding prompt. Ask one what a snake means and it will
tell you "Ibn Sirin says a snake represents an enemy" — and you have no way to
check whether Ibn Sirin says that, because there is no citation, no page, no
text. Often the model simply invented it.

This project inverts that. The symbols in a dream are found **by code**, by
looking them up in a dictionary built from the actual books. The AI is only
allowed to explain what the lookup already found. It cannot choose the symbols,
cannot supply the classical text, and cannot produce a page number.

The practical result:

```
User types:   "I dreamed I fell from a tall building and my teeth were falling out"

Code finds:   سقوط (suqut = falling) · بناء (bina' = building) · ضرس (dirs = molar tooth)

Code fetches: 9 classical passages + 5 psychological passages for those symbols

AI writes:    an explanation using only those 14 passages

Page shows:   the explanation, plus the original Arabic of all 14 passages,
              each with its book, author, printed page number, and a link to
              the scanned source
```

Current scale: **6 books · 2,317 dream symbols · 11,548 indexed passages · 44
hadith on dream etiquette.**

---

## 2. Background: what Islamic dream interpretation actually is

You need this section to understand why the software is shaped the way it is.
The design follows the tradition's own rules, not general chatbot conventions.

### Dreams are divided into three kinds

This division comes from a well-known hadith (a recorded saying of the Prophet
Muhammad ﷺ) and it is the foundation of the whole discipline:

| Arabic | Transliteration | Meaning |
|---|---|---|
| رؤيا | **ru'ya** | A true vision, described as coming from God. Good news. |
| حلم | **hulm** | A bad or frightening dream, attributed to Satan, intended to distress. |
| أضغاث أحلام | **adghath ahlam** | Literally "jumbled bundles of dreams" — mental noise, the day's worries replaying. |

**Only the first category is really interpreted.** This is the single most
important thing to understand about the tradition, and it is what most dream
websites ignore, because interpreting everything produces more engagement.

### The etiquette of a bad dream

If a dream falls in the second category, the tradition does not interpret it. It
prescribes actions instead:

1. Seek refuge in God from Satan
2. Spit lightly to the left three times
3. Turn over onto the other side
4. Get up and pray
5. **Do not tell anyone about it**

The last point matters: relating a bad dream is discouraged, so a site that
eagerly interprets nightmares is working directly against the tradition it claims
to represent.

The Arabic word for this body of etiquette is **آداب (adab)** — manners, proper
conduct. Our app has a whole layer for it.

### The discipline itself

| Arabic | Transliteration | Meaning |
|---|---|---|
| تعبير | **ta'bir** | Interpretation. Root sense: "crossing over" from the image to the meaning. |
| تأويل | **ta'wil** | Interpretation, tracing something back to its origin. |
| معبّر | **mu'abbir** | A dream interpreter. |
| رمز | **ramz** | A symbol. |

Two more properties of the tradition shaped our software directly:

**Interpretation is conditional, not fixed.** A classical entry never says "a
snake means an enemy" and stop. It says: *if it is in the house, then a household
enemy; if you kill it, then victory over an enemy; if you are not afraid of it,
then it is your own strength.* This branching structure **is** the discipline.
Any product that flattens it into one sentence has thrown away the substance.

**Interpretation depends on the dreamer.** The same symbol reads differently for a
man and a woman, a married and an unmarried person, the sick and the healthy.
This is why our site asks optional questions about the dreamer.

**Interpretation is ظنّي (zanni) — probabilistic, not certain.** No qualified
interpreter claims certainty. Our app says so on every response.

### The reasoning methods

Classical interpreters do not guess. They reason by identifiable principles, and
naming the principle is what separates the discipline from fortune-telling:

| Arabic | Transliteration | Meaning |
|---|---|---|
| أصل قرآني | asl qur'ani | Grounded in a Qur'anic verse |
| أصل من السنة | asl min al-sunna | Grounded in a hadith |
| اشتقاق اللفظ | ishtiqaq al-lafz | From the derivation/root of the word itself |
| التأويل بالمقابلة والضد | ta'wil bi-l-muqabala wa-l-didd | By opposite — crying means joy, laughter means sorrow |
| قياس على نظير | qiyas 'ala nazir | Analogy with a comparable case |
| العرف والعادة | al-'urf wa-l-'ada | Custom and convention |
| حال الرائي | hal al-ra'i | The dreamer's own circumstances |

Our app requires the AI to name which of these seven it used, for every symbol.

---

## 3. The six books, in English

Five are classical Arabic works, all public domain, taken from
**al-Maktaba al-Shamela** ("The Comprehensive Library", [shamela.ws](https://shamela.ws)) —
a large free Islamic digital library. One is a psychology source from the
Internet Archive.

> **Note on dates:** AH = *Anno Hegirae*, the Islamic calendar. CE conversions given.

### Book 1 — The symbol dictionary

**تعطير الأنام في تعبير المنام**
*Ta'tir al-Anam fi Ta'bir al-Manam* — "Perfuming Mankind in the Interpretation of Dreams"

- **Author:** Abd al-Ghani al-Nabulsi (d. 1143 AH / 1731 CE), a Damascene scholar
- **Source:** [shamela.ws/book/1217](https://shamela.ws/book/1217)
- **Size:** 378 pages scraped
- **Contribution:** all **2,317 headwords** — the entire symbol vocabulary

This is an **alphabetical dictionary**. Each entry is a headword in brackets
followed by its interpretation, e.g. `(حية)` — *hayya*, snake — then the ruling.

This structure is why the whole system works. Shamela marks each headword in the
page's HTML, so our scraper captured 6,198 headword-entry pairs **for free**, with
no AI involved. This book defines *what counts as a dream symbol*; the other books
are then searched for whatever it names.

### Book 2 — The famous one, with a caveat

**منتخب الكلام في تفسير الأحلام**
*Muntakhab al-Kalam fi Tafsir al-Ahlam* — "Selected Discourse on the Interpretation of Dreams"

- **Attributed to:** Muhammad Ibn Sirin (d. 110 AH / 728 CE)
- **Source:** [shamela.ws/book/21615](https://shamela.ws/book/21615)
- **Size:** 830 pages scraped → **6,129 passages**

Ibn Sirin is *the* famous name in Islamic dream interpretation — the equivalent of
Freud's name in the West. Nearly every dream app and book sells itself on it.

**But the attribution is false, and this is not controversial.** The book quotes
scholars who lived more than a century after Ibn Sirin died. Shamela's own editors
state plainly that ascribing it to him "is merely a commercial matter."

We carry the book — it genuinely is the received tradition that circulates under
his name — but **we say what it is.** That note is attached to every single
citation from it, in `corpus/books.py`.

This is a deliberate product decision. Competitors sell the name. Saying the
honest thing costs nothing and buys real credibility with exactly the audience
most likely to attack an AI religious product.

Structurally this book is **continuous prose organised by topic** — no headwords,
barely any punctuation. That is why it contributes passages rather than vocabulary.

### Book 3 — The systematic one

**الإشارات في علم العبارات**
*al-Isharat fi 'Ilm al-'Ibarat* — "The Indications in the Science of Interpretation"

- **Author:** Ghars al-Din Khalil ibn Shahin al-Zahiri (d. 873 AH / 1468 CE)
- **Source:** [shamela.ws/book/9968](https://shamela.ws/book/9968)
- **Size:** 273 pages scraped → **2,412 passages**

79 chapters. Its prose is punctuated by the recurring phrase **ومن رأى**
(*wa-man ra'a* = "and whoever sees…"), which introduces each individual ruling.
We use that phrase as a splitting marker when cutting the text into passages.

### Book 4 — The fourth lens

**تعبير الرؤيا**
*Ta'bir al-Ru'ya* — "The Interpretation of Visions"

- **Source:** [shamela.ws/book/10696](https://shamela.ws/book/10696)
- **Size:** 333 pages scraped → **1,201 passages**

Alphabetically arranged, but unlike Book 1 its headwords are written inline —
`البول في الرؤيا:` ("urine in a dream:") — rather than marked up in the HTML. So
it contributes passages, not vocabulary. Extracting its headwords properly is a
known future improvement.

### Book 5 — The foundation layer (not interpretation)

**الرؤيا**
*al-Ru'ya* — "The Vision"

- **Source:** [shamela.ws/book/20824](https://shamela.ws/book/20824)
- **Size:** 194 pages scraped → **44 hadith**

This is **not** a symbol dictionary. It is a collection of hadith about dreams,
organised by exactly the topics the app needs:

- ذكر أنواع الرؤيا — "mention of the types of vision"
- الرؤيا الصالحة جزء من النبوة — "the good vision is a part of prophethood"
- الأمر لمن رأى ما يكرهه أن يتفل عن يساره ثلاثاً — "the instruction to one who
  sees what he dislikes, to spit to his left three times"
- النهي عن الإخبار بالرؤيا المكروهة — "the prohibition on relating a disliked dream"

The interpretation books *assume* this material without stating it. This book is
what lets the app classify a dream and give the correct etiquette response — the
feature no competitor has.

### Book 6 — The psychological lens

**تفسير الأحلام** (*The Interpretation of Dreams*, Die Traumdeutung) and
**الحلم وتأويله** (*On Dreams*) — **Sigmund Freud**, Arabic translations

- **Source:** Internet Archive —
  [elshandawily6168](https://archive.org/details/elshandawily6168),
  [elshandawily6176](https://archive.org/details/elshandawily6176)
- **Size:** 1.34 MB of text → **1,806 passages**

Chosen for two reasons. First, the Arabic-language literature on dream psychology
largely rests on Freud, so his vocabulary is what an Arabic reader will recognise.
Second, he directly treats the dreams people actually ask about: falling, flying,
teeth falling out, nakedness, the death of a relative.

**Kept strictly separate from the classical books.** Tagged as `psych` at index
time, forbidden by the prompt from being blended with the interpretation books,
and shown in a different colour in the interface. A reader must always be able to
tell which tradition a statement comes from.

### Downloaded but not used

Muhammad al-Akili's **English** translation of the Ibn Sirin dictionary
([archive.org](https://archive.org/details/IbnSirinDictionaryOfDreams), 2.04M
characters). We parsed it into **2,129 English symbols with 2,317
cross-reference aliases** using nothing but a regular expression — no AI, no cost.

It contributes nothing to the Arabic site. It is held for a future English
version, where it would save the entire translation expense.

---

## 4. The competitor, and where the opening is

**royatok.com** is the reference competitor. What it offers:

- AI dream analysis, **Arabic only**
- Four "lenses": Ibn Sirin, al-Nabulsi, Ibn Shahin, modern psychology
- A dream journal with cloud sync
- Free tier: 1 interpretation per day. Paid: all lenses, follow-up chat

You tested it with a falling dream and it produced a fluent, well-structured
answer: a reading by Ibn Sirin's approach, a psychological reading, an "about the
methodology" note, sentiment percentages, and a closing piece of advice.

It was genuinely good. Here is what it could not do:

| | royatok | this project |
|---|---|---|
| Cites a book | ✗ | ✓ every claim |
| Cites a page number | ✗ | ✓ printed page |
| Shows the original Arabic text | ✗ | ✓ full passage |
| Links to the source scan | ✗ | ✓ Shamela link |
| Says when it has no source | ✗ | ✓ explicitly labelled |
| Refuses to interpret a bad dream | ✗ | ✓ gives the sunnah response |
| Psychology lens has a real corpus | ✗ | ✓ 1,806 Freud passages |
| Hadith / etiquette layer | ✗ | ✓ 44 hadith |
| Languages | Arabic only | Arabic (English planned) |

Its answer asserted "In Ibn Sirin's approach, falling may indicate moving from one
state to another." Maybe it does. There is no way to check. **That gap is the
product.**

---

## 5. The core design decision

Every AI dream app works like this:

```
dream ──────────────► AI ──────────────► answer
                (knows everything,
                 cites nothing,
                 invents freely)
```

Ours works like this:

```
dream ──► NORMALISE ──► LOOK UP ──► FETCH ──► AI ──► answer
          (code)        (code)      (code)   (writes prose
                                              over what code
                                              already found)
                           │
                           └──► citations returned separately,
                                independent of the AI
```

The consequence is structural, not a matter of prompting:

- The AI **cannot choose** which symbols are in the dream — code did that
- The AI **cannot supply** the classical text — code fetched it
- The AI **cannot invent** a page number — code stamps provenance
- If the AI fails completely, **the citations still display**

We enforce it with a prompt rule as well, but the architecture is what makes it
true. A prompt instruction can be ignored; a missing capability cannot.

---

## 6. Stage 1 — Scraping the books

**File:** `corpus/scrape.py` · **Run:** `python -m corpus.scrape --all`

Shamela serves each book one page at a time at `shamela.ws/book/<id>/<page>`.
The text sits in an HTML element with the class `nass` (نص = "text"), which
carries two useful attributes:

- `data-page-id` — the page number in the URL
- `data-page-num` — **the page number of the physical printed book**

That second one matters enormously. It is what lets a scholar verify a citation
against the paper edition. We record both.

For each page we save: the verbatim text, the paragraph breakdown, any headword
markers, the chapter title, the printed page number, and the URL.

Design points:

- **Cached per page.** A rerun costs nothing; nothing is re-fetched.
- **Resumable.** An interrupted scrape continues where it stopped.
- **Rate limited** (1.2s between requests) — this is a free community library and
  hammering it would be rude.
- **Stops after 5 consecutive misses**, since book lengths are not known upfront.

**Result: 2,008 pages across five books, roughly 25 minutes, no AI cost.**

---

## 7. Stage 2 — Filtering out non-dream content

**File:** `corpus/filters.py` · **Run:** `python -m corpus.filters --all`

The books are not purely dream interpretation. They open with prefaces, editorial
introductions and author biographies, and wander into chains of narration, poetry
and anecdotes. None of that belongs in a dream corpus.

The filter runs **before any AI call**, so junk costs nothing.

It looks for dream vocabulary — رؤيا (*ru'ya*, vision), منام (*manam*, sleep/dream),
تأويل (*ta'wil*, interpretation), رأى (*ra'a*, he saw) — and requires a minimum
density.

**I got this wrong twice, and both failures are instructive:**

**Failure 1 — it dropped all 492 pages.** Shamela puts the phrase فهرس الكتاب
("book index") in the breadcrumb of *every* page, and my "skip front matter" rule
matched it everywhere. Fixed by stripping that boilerplate.

**Failure 2 — it dropped Ibn Sirin's chapter on Qur'anic chapters in dreams.**
That chapter is pure symbol content — "whoever recites Surat al-Kahf in a dream
will attain his wishes" — but it is phrased with ومن قرأ (*wa-man qara'a*,
"whoever recites") and never uses the word "dream" at all. It scored zero.

The fix generalises: **if a page sits inside a chapter whose title contains dream
vocabulary, keep it regardless of the page's own wording.** Let the model return
nothing for a genuine digression. Losing real content is far more expensive than
one wasted call.

Final result: Nabulsi 376/378 kept, Ibn Sirin 723/830, Ibn Shahin 273/273. The
107 dropped Ibn Sirin pages are narration chains and editorial matter.

---

## 8. Stage 3 — The extraction pipeline (built, then set aside)

**Files:** `corpus/extract.py`, `corpus/validate.py`, `corpus/schema.py`,
`corpus/prompts.py`, `corpus/english.py`

**This is the part of the project the running website does not use.** I am
documenting it fully because it was real work, it is still in the repository, and
it is required for the English version.

### The original plan

Send each scraped page to Gemini and get back structured records:

```json
{
  "symbol_ar": "الميت كأنه حي",
  "symbol_en": "a dead person as if alive",
  "category": "death",
  "quote_ar": "فإن رأى ميتاً كأنه حي فإنّه يصلح أمره بعد الفساد",
  "quote_en": "If he sees a dead person as if alive, his affair will be set right after corruption",
  "conditions": [{ "if_en": "...", "then_en": "..." }],
  "valence": "good"
}
```

### The fabrication guard

The important piece. `corpus/validate.py` **discards any entry whose Arabic quote
is not literally present in the page it claims to quote.** No warning, no soft
pass, no override flag.

Comparison runs on a normalised form — vowel marks stripped, hamza and alef
folded — because the model reproduces wording faithfully but never diacritics
exactly. What gets stored and displayed stays verbatim.

Verified behaviour on a deliberately poisoned test set of 4 entries:

| Test entry | Result |
|---|---|
| Exact verbatim quote | ✓ passed |
| Same wording, different orthography | ✓ passed (correct) |
| Plausible but invented quote | ✗ rejected |
| Valid entry, one invented condition | ✗ whole entry rejected |

On real output: Nabulsi 19/20 (95%), Ibn Sirin 8/8 (100%).

**The model never writes a citation locator.** Book, chapter, printed page and URL
are all stamped by code from the scrape. A model that can write a page number will
eventually write a wrong one, and a wrong page number is worse than none — it
survives review because it looks checkable.

### Why it was set aside

Two reasons.

1. **Your free-tier API key ran out after 22 pages.** Full extraction is roughly
   1,370 pages, ~7.4M tokens, $14–51 depending on model.
2. **We discovered we did not need it.** Indexing the raw scrape directly — with
   no AI at all — produced a working product in 2.7 seconds.

That second point is the real finding. The extraction pipeline was solving a
problem the corpus structure had already solved.

### What it is still needed for

- **The English version.** Translation is the expensive part, and this is what
  does it.
- **A scholar review queue.** Every extracted entry carries
  `review: {status: "pending"}`. Scholars can only approve text that exists as
  discrete records.

`corpus/english.py` is the related win: al-Akili's English translation parses into
2,129 symbols with a plain regular expression, in about one second, for zero cost.
Its cross-references (`Charmer: (See Snake charmer)`) are a hand-built alias table
— exactly the thing I had been planning to pay a model to guess at.

---

## 9. Stage 4 — Building the index

**File:** `corpus/index.py` · **Run:** `python -m corpus.index --build` (~3 seconds)

This is what the live site actually uses. It builds three structures.

### 9.1 The symbol vocabulary — 2,317 entries

From al-Nabulsi's dictionary. Each headword becomes an entry:

```json
{
  "key": "حيه",
  "symbol_ar": "حية",
  "body_ar": "(حية) في المنام عدو أو دولة أو كنز أو امرأة أو ولد...",
  "source": { "book_ar": "...", "printed_page": "94", "url": "https://shamela.ws/..." }
}
```

`key` is the normalised form used for matching; `symbol_ar` is what gets shown.

Two junk filters: headwords must be 3–30 characters and at most 4 words. Shamela
occasionally wraps an entire sentence in a headword tag, and those are not symbols.

### 9.2 The passage index — 11,548 passages

The other four books have no headwords, so they are cut into passages and indexed
by which symbol each one mentions.

**Cutting**: classical Arabic prose is barely punctuated, so we split on the
phrases that actually begin a new ruling rather than on full stops:

| Arabic | Transliteration | Meaning |
|---|---|---|
| فإن رأى | fa-in ra'a | "and if he sees" |
| ومن رأى | wa-man ra'a | "and whoever sees" |
| وقال | wa-qala | "and he said" |
| وأما | wa-amma | "and as for" |

**Indexing**: for each passage, generate every word and phrase it contains
(stripped of prefixes and suffixes), and intersect that set with the 2,317 known
symbol keys.

That direction matters for speed. Running 2,317 regular expressions against every
one of ~11,000 passages would be 25 million operations. Generating candidates from
the text and doing a set intersection is near-instant — **the whole index builds
in under 3 seconds**.

Result: `{ "حيه": [passage, passage, ...], "ماء": [...], ... }`

### 9.3 The etiquette index — 44 hadith

From Book 5, selected by chapter title against a list of topics: types of vision,
the good vision, spitting to the left, not relating a bad dream, seeking refuge.

### Per-book contribution

| Book | Passages |
|---|---|
| Ibn Sirin | 6,129 |
| Ibn Shahin | 2,412 |
| Freud (psychological) | 1,806 |
| Ta'bir al-Ru'ya | 1,201 |
| **Total** | **11,548** |

---

## 10. Stage 5 — Matching a dream, and why Arabic makes it hard

This is the heart of the system and the part most worth understanding.

### Why not "AI semantic search"?

Because this is **dictionary lookup**. The classical books are literally
glossaries keyed by symbol. An exact headword hit is more accurate *and*
explainable than a similarity score. You can show a user *why* a symbol matched.

### Step 1 — Normalisation

**File:** `corpus/arabic.py`

Arabic writing has optional vowel marks and several letters with variant forms.
The same word appears many ways. Normalisation collapses them:

| Transformation | Example |
|---|---|
| Strip vowel marks | `حَيَّة` → `حية` |
| `أ إ آ` → `ا` | `أسنان` → `اسنان` |
| `ى` → `ي` | `شعرى` → `شعري` |
| `ة` → `ه` | `حية` → `حيه` |
| Remove punctuation, collapse spaces | |

Applied to **both** the dream and the index keys, so spelling variation stops
mattering.

**This form is only ever used for matching.** Displayed text stays verbatim —
normalisation is lossy and must never be written back into a citation.

### Step 2 — The alias table

Two things no rule can bridge. Both are handled by ~90 hand-written entries.

**Broken plurals.** English forms plurals by adding a suffix. Arabic often
restructures the word internally:

| Singular | Plural | Note |
|---|---|---|
| حية *hayya* (snake) | حيات *hayyat* | no suffix rule reaches this |
| ضرس *dirs* (molar) | أضراس *adras* | the stem itself changes |

**Conjugated verbs.** People describe dreams with verbs; dictionaries file
everything under the verbal noun (the *masdar*):

| What a user writes | Meaning | Dictionary entry |
|---|---|---|
| سقطت *saqattu* | "I fell" | سقوط *suqut* (falling) |
| وقعت *waqa'tu* | "I fell" | سقوط |
| أطير *atir* | "I fly" | طيران *tayaran* (flying) |

**This is the exact bug you found.** You wrote "I fell from a building" and got
nothing back, because `سقوط` was in the index but `وقعت` reached nothing. Adding
the verb forms fixed it.

The table also maps modern words to classical ones: بناية (*binaya*, modern
"building") → بناء (*bina'*, classical), أسنان (*asnan*, teeth) → ضرس (*dirs*,
molar — because al-Nabulsi files teeth under "molar", and nobody writing about
their dream types "molar").

### Step 3 — Affix-tolerant matching

Arabic attaches the definite article and some conjunctions to the front of a word,
and possessives to the back:

| Written | Parts | Meaning |
|---|---|---|
| الحية | ال + حية | "the snake" |
| وحية | و + حية | "and a snake" |
| بيتي | بيت + ي | "my house" |
| أسنانه | أسنان + ه | "his teeth" |

So we match with a pattern that permits those affixes but forbids any other
Arabic letter on either side:

```
(?<!arabic-letter) [prefix]? KEY [suffix]? (?!arabic-letter)
```

**One deliberate exclusion.** The single-letter prepositions ب/ك/ل are *not*
allowed as prefixes. Permitting them made `بير` match inside `كبيرة`
(*kabira*, "big") and return the symbol "well" for a dream containing no well.
They cost more in false matches than they earn in recall.

### Step 4 — Longest match wins

Entries are sorted longest key first. Once a longer headword matches, its
substrings are suppressed — otherwise a dream mentioning إلية الشاة ("sheep's
tail") would also report شاة ("sheep") as a separate symbol.

### Step 5 — Attaching passages, with a balance rule

For each matched symbol, pull its passages from the index — but **3 classical + 2
psychological**, enforced in code.

Without that cap, Ibn Sirin's 6,129 passages would bury Freud's 1,806 entirely and
the psychological lens would silently vanish.

### A real trace

```
INPUT     حلمت أني وقعت من بناية عالية وأسناني تسقط
          "I dreamed I fell from a tall building and my teeth were falling out"

NORMALISE حلمت اني وقعت من بنايه عاليه واسناني تسقط

ALIASES   اسنان → ضرس     وقعت → سقوط     تسقط → سقوط     بنايه → بناء

MATCHED   ضرس (molar) · سقوط (falling) · بناء (building)          in 1.53 ms

PASSAGES  ضرس  → 3 Ibn Sirin + 1 Freud
          سقوط → 3 Ibn Sirin + 2 Freud
          بناء → 3 Ibn Sirin + 2 Freud

ETIQUETTE 6 hadith, top one from the chapter
          "what one says who sees in his dream what he dislikes"

PROMPT    9,301 characters (~3,100 tokens)
```

**Total retrieval time: 1.53 milliseconds.** The AI call that follows takes 6–9
seconds. Retrieval is 0.02% of the request.

---

## 11. Stage 6 — Composing the answer

**File:** `corpus/answer.py`

Only now does AI enter. It is given the dream, the dreamer's stated circumstances,
the retrieved passages (each tagged classical or psychological), and the hadith.

The response is **structured JSON**, not free text, so the page can render proper
sections and so required fields cannot be skipped.

### What the schema forces

| Field | English | Why it is required |
|---|---|---|
| `tasnif` | classification | ru'ya / hulm / adghath, with a stated reason |
| `mukhifah` | "is it frightening?" | if true, no interpretation — etiquette instead |
| `rumuz[]` | symbols | one per matched symbol |
| `rumuz[].manhaj` | method | which of the 7 classical principles was used |
| `rumuz[].bayan_almanhaj` | explanation of method | *why* the symbol carries that meaning |
| `rumuz[].tafsil[]` | conditions | the if/then branches — the substance |
| `rumuz[].athar_hal_alraai` | effect of the dreamer's state | how their circumstances change it |
| `rumuz[].min_alkutub` | "from the books?" | **true/false — the honesty flag** |
| `rumuz[].masadir` | sources | which books |
| `qiraat[]` | readings | per-lens, including psychological |
| `muashirat` | indicators | optimism / hope / anxiety, 0–100, with reasoning |
| `adab[]` | etiquette | the sunnah response |
| `nasihah` | advice | closing counsel |
| `tanbih` | caution | that interpretation is probabilistic |
| `asas_aljawab` | basis of the answer | from books / from general knowledge / both |

`min_alkutub` is the field the whole product rests on. Every claim is stamped
true or false, and the interface shows it.

### The rules in the prompt

1. If passages are supplied, they are authoritative — do not contradict them
2. If they are silent, you **may** answer from what is settled among interpreters,
   but flag it `false` and never attribute it to a specific book or page.
   **Never leave the user with no answer** — this was your explicit requirement
3. Classify before interpreting
4. If the dream is distressing, do not interpret it — give the sunnah response
5. **Naming the method is mandatory**
6. Preserve the conditional structure
7. Tie the reading to the dreamer's stated circumstances, and invent nothing they
   did not say
8. **Never blend the two traditions** — no psychological meaning attributed to the
   interpretation books, and no classical meaning attributed to psychology

---

## 12. Stage 7 — The website

**Files:** `web/app.py` (API), `web/static/index.html` (interface)

A FastAPI server. The index loads **once at startup** (154 ms), not per request.

### Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | The page |
| `GET /api/health` | Corpus counts and configured models |
| `GET /api/symbols` | Browse the 2,317 symbols |
| `POST /api/interpret` | The main call |

### Model fallback

Google's free tier meters quota **per model**, not per key. So when one model is
exhausted the server retires it for that run and continues on the next. This is
what keeps the site answering.

**If every model is exhausted**, the API returns HTTP 503 — **with the citations
still attached**. The classical text is what users came for, and it survives an
AI outage entirely.

### The interface

Fully Arabic, right-to-left, adapts to light and dark, works on mobile.

- Optional questions about the dreamer
- Classification badge, colour-coded by dream type
- Symbols, each with its summary, conditions, method, and sources
- Indicator bars
- Per-lens readings
- Etiquette and advice
- **Collapsible original Arabic** for every passage — book, author, printed page,
  and a link to Shamela
- **A dream journal** in browser storage (`localStorage`), never sent to any
  server. Its real value is showing **which symbols recur across your dreams**
- Copy, print, and save buttons

---

## 13. What the user actually sees, translated

Real output for `رأيت أني أسقط من بناية عالية` ("I saw myself falling from a tall
building"), with context: male, unmarried, aged 20–30, anxious, recurring.

**Classification:** أضغاث أحلام — *adghath ahlam*, "jumbled dreams"
**Frightening:** yes → etiquette shown before interpretation
**Basis of answer:** mixed

**Indicators:** optimism 40% · hope 50% · anxiety 75%
*Stated reason: "the high anxiety figure derives from the recurrence of the falling
dream and the declared waking state of anxiety."*

**Symbol: falling** — tagged *from general knowledge* (not from the books)
> Falling from a height may indicate a change of state or a transition from one
> condition to another.

- **Method:** the dreamer's circumstances and the dream's attendant signs
- **According to your state:** being unmarried, in the 20–30 age group, and
  anxious makes falling an expression of anxieties about the future

**Symbol: tall building** — tagged **from the books**, sources: *Ta'tir al-Anam*,
*Muntakhab al-Kalam*
> A high or towering building indicates lofty ambitions and great goals the
> dreamer is striving toward.

- **Method:** derivation of the word and its sense — height denotes elevation,
  standing and advancement, so falling from it expresses fear of not attaining

**Readings:**
- *Psychological (Sigmund Freud)* — falling from a height reflects a bodily state
  or waking tension
- *The interpreters' approach (al-Nabulsi and Ibn Sirin)* — change of state, or
  fear of losing a position

**Advice:**
> Trust in God and be at ease, for frightening dreams are often jumbled ones
> arising from anxiety and daily pressures. Seek help in God, remember Him often,
> keep to the morning and evening remembrances, and trust that what is decreed
> for you is good.

Then the **original Arabic** of all 14 passages, each with its book, author,
printed page, and Shamela link.

**Look at the two symbol tags.** "Falling" is marked *not from the books* —
because the matched entries genuinely did not cover falling from a height, and
the system said so instead of inventing a citation. "Building" is marked *from
the books* with two named sources.

That distinction is the entire product.

---

## 14. Every file in the repository

### Runtime — what the website needs (~450 lines + 13 MB)

| File | Purpose |
|---|---|
| `corpus/data/index/*.json` | **The corpus artifact.** 13 MB |
| `corpus/index.py` | `match()` and `load()` — the matching engine |
| `corpus/arabic.py` | Arabic normalisation |
| `corpus/answer.py` | Prompt and response schema |
| `web/app.py` | API |
| `web/static/index.html` | The interface |

### Build-time — never deployed

| File | Purpose |
|---|---|
| `corpus/scrape.py` | Shamela scraper |
| `corpus/books.py` | Book registry + attribution notes |
| `corpus/filters.py` | Drops non-dream pages |
| `corpus/index.py` | `build()` — constructs the index |
| `corpus/models.py` | Lists models your API key can reach |

### Built but unused

| File | Purpose |
|---|---|
| `corpus/extract.py` | AI extraction into structured entries |
| `corpus/validate.py` | The fabrication guard |
| `corpus/schema.py` | Extraction output schema |
| `corpus/prompts.py` | Extraction prompts |
| `corpus/english.py` | Parses the English Ibn Sirin dictionary |
| `corpus/interpret.py` | **Dead code** — superseded by `answer.py` |

### Data

| Path | Size | Keep? |
|---|---|---|
| `corpus/data/raw/` | 21 MB | **Yes — the master source** |
| `corpus/data/index/` | 13 MB | Yes — the built artifact |
| `corpus/data/sources/` | 4.3 MB | Yes — Freud + English Ibn Sirin |

**Never delete `raw/`.** The index is derived from it. Every change to the alias
table or the matching rules requires rebuilding from raw — 3 seconds. Without it,
the matching rules are frozen forever and Shamela has to be re-scraped.

---

## 15. What works and what does not

### Working

- 6 books scraped and indexed, 2,317 symbols, 11,548 passages
- Retrieval in 1.5 ms; full response in 6–9 s
- Every classical claim carries book, author, printed page, source link
- Unsourced statements explicitly flagged
- Dream classification and the etiquette response
- Method named for every symbol
- Classical and psychological lenses kept separate
- Dreamer's circumstances change the reading
- Local dream journal with recurring-symbol detection
- Model fallback; citations survive total AI failure

### Not working, or missing

**The alias table is only ~90 entries.** If a user writes a verb or plural not on
the list, the symbol is missed entirely. This is the single biggest weakness. It
is exactly what produced your falling-dream failure.

**No logging of failed matches.** We have no data on what real users write that
finds nothing. This should be the next thing built — it makes every subsequent
improvement evidence-based rather than guesswork.

**Book 4's headwords are unextracted.** `تعبير الرؤيا` is alphabetical but its
headwords are inline, so it contributes passages instead of vocabulary. Extracting
them would add perhaps 1,000 more symbols.

**OCR noise in the Freud text**, since it comes from a scan.

**Free-tier quota.** Heavy use falls back to slower models and eventually fails.

**No accounts, no server-side history, no payments.** It is an MVP.

**English version not built**, though the corpus for it is parsed and waiting.

---

## 16. Costs, quota, and the API key

### What has been spent

Almost nothing. Scraping is free. Index building is free. Only interpretation
calls cost, and those are ~3,100 tokens in, ~2,000 out — fractions of a cent each.

The 22 extraction pages and roughly 15 API-shape probe calls are the only other
usage.

### Full extraction, if you ever run it

1,370 pages ≈ 2.0M input + 5.4M output tokens:

| Model | Cost |
|---|---|
| gemini-3.5-flash-lite | ~$14 |
| gemini-3.6-flash | ~$22 |
| gemini-3.5-flash | ~$51 |

One-time, not recurring. Roughly 40 minutes with 5-way parallelism on a paid tier;
2–3 weeks on free tier.

### Quota

Free-tier quota is **per model**, not per key. `gemini-3.6-flash` ran dry while
`gemini-3.5-flash` still answered — which is why the fallback chain exists.

Availability also varies by key: `gemini-2.5-flash` returns 404 for newly created
keys. Run `python -m corpus.models` to see what yours can reach.

### The API key

Lives in `.env`, permissions 0600, listed in `.gitignore`, **never committed**.
Verified against git's own index, not a filesystem search.

It is present in this conversation's history, so rotating it at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) is the clean move.

---

## 17. What comes next

### Immediately valuable

1. **Log every failed match.** Cheap, and it turns all guesswork into evidence.
2. **Expand the alias table offline.** One cheap AI call per symbol asking for
   plurals, synonyms, colloquial forms and verb derivations; bake the results into
   the table. ~$1–2 once, then **zero runtime cost forever**. This likely closes
   70–80% of the recall gap, because the misses are morphological rather than
   conceptual.
3. **Extract Book 4's headwords** — perhaps 1,000 more symbols, no AI needed.

### The Next.js port

Everything ports cleanly. The corpus is plain JSON and moves unchanged; only the
matching logic (~120 lines of regex and string work) needs rewriting. Measured:
retrieval is 1.5 ms against a 6–9 s AI call, so performance is not a
consideration.

Do it for the **static symbol pages**: 2,317 routes pre-rendered from the index
you already have, each with real Arabic text and citations. That is the free-search-traffic
engine, and a single-page FastAPI app cannot provide it.

One rule: load the index at module scope, not per request.

### Larger moves

- **The scholar layer.** A verified human interpreter answering within 48 hours.
  This is the strongest differentiator and the hardest to copy — recruiting is the
  long pole, so start early if you want it.
- **The English version.** The corpus is already parsed: 2,129 symbols with 2,317
  aliases, from al-Akili's translation, at zero cost.
- **Semantic search**, but only if the logs justify it. And even then: 2,317
  vectors is ~7 MB and brute-force cosine is sub-millisecond, so **no vector
  database is needed** at this scale.

---

## 18. Glossary

### The tradition

| Arabic | Transliteration | Meaning |
|---|---|---|
| رؤيا | ru'ya | True vision, from God |
| حلم | hulm | Bad dream, from Satan |
| أضغاث أحلام | adghath ahlam | Jumbled dreams, from the mind |
| تعبير | ta'bir | Interpretation ("crossing over") |
| تأويل | ta'wil | Interpretation ("tracing to origin") |
| معبّر | mu'abbir | Dream interpreter |
| رمز | ramz | Symbol |
| آداب | adab | Etiquette, proper conduct |
| ظنّي | zanni | Probabilistic, not certain |
| حديث | hadith | A recorded saying of the Prophet ﷺ |
| سنة | sunna | The Prophet's practice |
| دعاء | du'a | Supplication |
| استخارة | istikhara | Prayer seeking guidance |
| فتوى | fatwa | A formal religious ruling |

### Fields in our schema

| Arabic | Transliteration | Meaning |
|---|---|---|
| تصنيف | tasnif | Classification |
| مخيفة | mukhifah | Frightening |
| رموز | rumuz | Symbols (plural of *ramz*) |
| خلاصة | khulasah | Summary |
| تفصيل | tafsil | Detail, the conditions |
| منهج / مسلك | manhaj / maslak | Method, approach |
| مصادر | masadir | Sources |
| قراءات | qira'at | Readings |
| مؤشرات | mu'ashirat | Indicators |
| نصيحة | nasihah | Advice |
| تنبيه | tanbih | Caution |
| من الكتب | min al-kutub | "From the books" — the honesty flag |
| حال الرائي | hal al-ra'i | The dreamer's circumstances |

### Technical

| Term | Meaning |
|---|---|
| Corpus | The full body of indexed text |
| Index | The searchable structure built from the corpus |
| Headword | A dictionary entry's title word |
| Passage | A chunk of prose cut from a book |
| Normalisation | Reducing spelling variants to one form for matching |
| Alias | An alternative wording mapped to a headword |
| Lens | One interpretive perspective (a book, or psychology) |
| Provenance | The record of where text came from |
| Lexical matching | Matching by exact words |
| Semantic matching | Matching by meaning, via vectors |
| Masdar | Arabic verbal noun — the dictionary form |
| Broken plural | Arabic plural formed by restructuring the word |

---

*Sources for every book, with links and page ranges, are in `README.md` under
**References — المصادر**.*
