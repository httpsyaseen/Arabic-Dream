# Overview — what this project is and how it works

Written for a reader who does not know Arabic. Every Arabic term appears with a
transliteration and an English meaning.

Read this first. Then [PARSING.md](PARSING.md) for how the books become data, and
[SOURCES.md](SOURCES.md) for the books themselves.

---

## 1. The one-paragraph version

A website where someone types a dream in Arabic and gets an interpretation drawn
from classical Islamic dream-interpretation books, plus a psychological reading,
with **every claim traceable to a specific page of a specific book**.

Every competitor is an AI chatbot with a religious-sounding prompt. Ask one what
a snake means and it says "Ibn Sirin says a snake is an enemy" — and you cannot
check it. No citation, no page, no text. Often the model simply made it up.

This project inverts that. Symbols are found **by code**, by looking them up in a
dictionary built from the actual books. The model is only allowed to explain what
the lookup already found.

---

## 2. The tradition, briefly

You need this to understand why the software behaves as it does. It follows the
tradition's own rules rather than chatbot conventions.

### Dreams come in three kinds

From a well-known hadith (a recorded saying of the Prophet Muhammad ﷺ):

| Arabic | Transliteration | Meaning |
|---|---|---|
| رؤيا | **ru'ya** | A true vision, from God. Good news. |
| حلم | **hulm** | A bad dream, attributed to Satan, meant to distress. |
| أضغاث أحلام | **adghath ahlam** | "Jumbled bundles" — mental noise, the day's worries replaying. |

**Only the first is really interpreted.** Most dream sites ignore this, because
interpreting everything produces more engagement.

### A bad dream is not interpreted at all

The tradition prescribes actions instead: seek refuge in God, spit lightly to the
left three times, turn onto the other side, get up and pray, and **tell no one**.

That last point matters — a site that eagerly interprets nightmares is working
against the tradition it claims to represent. Our app classifies first and gives
the etiquette response (آداب, *adab* = proper conduct) when the dream is
distressing.

### Two properties that shaped the software

**Interpretation is conditional.** A classical entry never just says "a snake is
an enemy." It says: *if it is in the house, a household enemy; if you kill it,
victory over an enemy; if you are not afraid of it, your own strength.* That
branching **is** the discipline. Flattening it to one sentence throws away the
substance, so our schema has a required `tafsil` (تفصيل = detail/conditions)
field.

**Interpretation depends on the dreamer.** The same symbol reads differently for
a man and a woman, married and unmarried, sick and healthy. Hence the optional
questions on the form.

And it is **ظنّي** (*zanni*) — probabilistic, never certain. The app says so on
every response.

### Interpreters reason by named methods

Not guesswork. Seven identifiable principles, and naming which one was used is
what separates the discipline from fortune-telling:

| Arabic | English |
|---|---|
| أصل قرآني | grounded in a Qur'anic verse |
| أصل من السنة | grounded in a hadith |
| اشتقاق اللفظ | from the derivation of the word itself |
| التأويل بالمقابلة والضد | by opposite — crying means joy |
| قياس على نظير | analogy with a comparable case |
| العرف والعادة | custom and convention |
| حال الرائي | the dreamer's own circumstances |

Our schema **requires** the model to name one for every symbol.

---

## 3. The core design decision

Every AI dream app:

```
dream ─────────────────► AI ─────────────────► answer
                  (knows everything,
                   cites nothing,
                   invents freely)
```

This project:

```
dream ─► NORMALISE ─► LOOK UP ─► FETCH ─► AI ─► answer
          (code)       (code)    (code)  (writes prose over
                                          what code found)
                          │
                          └──► citations returned separately,
                               independent of the AI
```

The consequence is structural, not a matter of prompt wording:

- the AI **cannot choose** which symbols are in the dream — code did
- the AI **cannot supply** the classical text — code fetched it
- the AI **cannot invent** a page number — code stamps provenance
- if the AI fails entirely, **the citations still display**

A prompt instruction can be ignored. A missing capability cannot.

---

## 4. A request, end to end

Real trace for: `حلمت أني وقعت من بناية عالية وأسناني تسقط`
("I dreamed I fell from a tall building and my teeth were falling out")

```
① NORMALISE            حلمت اني وقعت من بنايه عاليه واسناني تسقط
   backend/arabic       strip vowel marks, fold letter variants
                        (used for matching only — displayed text stays verbatim)

② ALIASES              اسنان → ضرس    وقعت → سقوط
   backend/aliases      تسقط  → سقوط   بنايه → بناء
                        teeth→molar, "I fell"→falling, modern→classical

③ MATCH                ضرس (dirs = molar) · سقوط (suqut = falling) · بناء (bina' = building)
   backend/search       2,317 headwords, longest first, affix-tolerant
                        →  1.5 milliseconds

④ FETCH PASSAGES       ضرس  → 4 classical + 1 psychological
   from index/          سقوط → 4 classical + 2 psychological
                        بناء → 4 classical + 2 psychological
                        (the split is enforced in code, or the classical books
                         would bury the psychological source entirely)

⑤ FETCH ETIQUETTE      6 hadith, top one from the chapter
                        "what one says who sees what he dislikes in his dream"

⑥ BUILD PROMPT         ~9,300 characters: the dream, the dreamer's situation,
   backend/answer       and only the retrieved passages, each tagged
                        "interpretation books" or "psychological reading"

⑦ AI CALL              structured JSON back      →  6–9 seconds
                        (99.98% of the request time)

⑧ RESPOND              answer + citations + etiquette sources
                        citations come from ④, NOT from the AI
```

---

## 5. What the user sees

For that dream, with context "male, unmarried, anxious, recurring":

**Classification:** أضغاث أحلام (*adghath ahlam* = jumbled dreams)
**Distressing:** yes → etiquette shown before any interpretation
**Indicators:** optimism 40% · hope 50% · anxiety 75%, *with a stated reason*

**Symbol: falling** — tagged **general knowledge**, no sources
> may indicate a change of state or a transition from one condition to another

**Symbol: tall building** — tagged **from the books**, sources: *Ta'tir al-Anam*,
*Muntakhab al-Kalam*
> a high building indicates lofty ambitions the dreamer is striving toward
> *Method: derivation of the word — height denotes elevation and advancement, so
> falling from it expresses fear of not attaining*

Then the original Arabic of every passage, with book, author, printed page and a
link to the scan.

**Look at those two tags.** "Falling" is marked *not from the books*, because the
matched entries genuinely did not cover falling from a height — and it says so
instead of inventing a citation. "Building" is marked *from the books* with two
named sources.

That distinction is the entire product.

---

## 6. The pieces

```
backend/          the API — FastAPI, pure JSON, serves no HTML
  main.py         app, CORS, routes
  search.py       the matching engine          ← the heart of it
  answer.py       prompt + response schema
  aliases.py      ~90 hand-written word mappings
  routers/        health · sources · symbols · interpret

pipeline/         build-time only, never deployed
  sources.py      the registry — one entry adds a book
  scrape.py       downloads from the digital library
  parse.py        raw text → uniform chunks     ← the four parsers
  build_index.py  chunks → searchable index

context/          one folder per book: raw/ · chunks.json · source.json
index/            the built artifact (13 MB) the API loads at startup
frontend/         standalone client, calls the API over HTTP
```

**Runtime is about 450 lines plus a 13 MB JSON file.** Everything else is
build-time tooling that runs on your machine and never reaches the server.

---

## 7. The API

Base: `/api/v1` · interactive reference at `/docs`

| Endpoint | Purpose |
|---|---|
| `GET /health` | corpus counts, configured models |
| `GET /sources` | every book with both names, plus **non-sources** — names people search for that have no book behind them |
| `GET /options` | the form fields, labelled in both languages, so the frontend ships no translation table |
| `GET /symbols` | browse the 2,317 symbols |
| `GET /symbols/{key}` | one symbol with all its citations |
| `POST /interpret` | the main call |

CORS is open, so the frontend can live anywhere.

If every model hits its quota, `/interpret` returns **503 with the citations
still attached** — the classical text survives an AI outage.

---

## 8. Current scale

| | |
|---|---|
| Sources | **7** (5 classical Arabic, 1 psychological, 1 hadith) |
| Symbols | **2,317** |
| Indexed passages | **12,738** |
| Etiquette hadith | **44** |
| Raw pages | 2,008 |
| Match time | **1.5 ms** |
| Full response | 6–9 s |
| Full corpus rebuild | ~6 s |

---

## 9. Known weaknesses

**The alias table is only ~90 entries.** If someone writes a verb or plural not
on the list, the symbol is missed entirely. This is the single biggest weakness —
it is what made "I fell from a building" return nothing until verb forms were
added.

**No logging of failed matches.** We have no data on what real users write that
finds nothing. This should be built next; it makes every later improvement
evidence-based instead of guesswork.

**One book's headwords are unextracted.** *Ta'bir al-Ru'ya* is alphabetical but
writes its headwords inline rather than marking them up, so it contributes
passages instead of vocabulary. Extracting them would add perhaps 1,000 symbols.

**OCR noise** in the two scanned sources (Freud, and the Shia volume).

**Free-tier quota.** Heavy use falls back to slower models and eventually fails.

**No accounts, no server-side history, no payments.** It is an MVP.

**No English version yet**, though a full English Ibn Sirin dictionary is already
parsed and waiting (2,129 symbols, 2,317 aliases, obtained at zero cost).

---

## 10. Glossary

| Arabic | Transliteration | Meaning |
|---|---|---|
| رؤيا | ru'ya | true vision, from God |
| حلم | hulm | bad dream, from Satan |
| أضغاث أحلام | adghath ahlam | jumbled dreams, from the mind |
| تعبير | ta'bir | interpretation ("crossing over") |
| تأويل | ta'wil | interpretation ("tracing to origin") |
| معبّر | mu'abbir | dream interpreter |
| رمز / رموز | ramz / rumuz | symbol / symbols |
| آداب | adab | etiquette |
| ظنّي | zanni | probabilistic, not certain |
| حديث | hadith | a recorded saying of the Prophet ﷺ |
| سنة | sunna | the Prophet's practice |
| دعاء | du'a | supplication |
| تصنيف | tasnif | classification |
| تفصيل | tafsil | the conditions, "if X then Y" |
| منهج | manhaj | method |
| مصادر | masadir | sources |
| نصيحة | nasihah | advice |
| من الكتب | min al-kutub | "from the books" — the honesty flag |

| Term | Meaning |
|---|---|
| Corpus | the full body of indexed text |
| Index | the searchable structure built from it |
| Headword | a dictionary entry's title word |
| Passage | a chunk of prose cut from a book |
| Normalisation | reducing spelling variants to one form, for matching |
| Alias | an alternative wording mapped to a headword |
| Lens | one interpretive perspective (a book, or psychology) |
| Provenance | the record of where text came from |
| Masdar | Arabic verbal noun — the dictionary form of a verb |
| Broken plural | Arabic plural formed by restructuring the word |
