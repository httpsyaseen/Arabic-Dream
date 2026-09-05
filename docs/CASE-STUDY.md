# Case study: building an AI product that cannot make things up

A worked example, in plain English, for readers with no Arabic and no prior
knowledge of the subject.

Every number, quote and trace below is real output from the running system, not
an illustration.

---

## Contents

1. [The problem](#1-the-problem)
2. [Why the obvious solution fails](#2-why-the-obvious-solution-fails)
3. [The key idea](#3-the-key-idea)
4. [What we are working with](#4-what-we-are-working-with)
5. [Stage 1 — Getting the books](#5-stage-1--getting-the-books)
6. [Stage 2 — Cutting books into pieces](#6-stage-2--cutting-books-into-pieces)
7. [Stage 3 — Building the index](#7-stage-3--building-the-index)
8. [Stage 4 — Answering one dream, start to finish](#8-stage-4--answering-one-dream-start-to-finish)
9. [What the user sees](#9-what-the-user-sees)
10. [Five bugs and what each taught](#10-five-bugs-and-what-each-taught)
11. [Design decisions worth stealing](#11-design-decisions-worth-stealing)
12. [Exercises](#12-exercises)

---

## 1. The problem

People want to know what their dreams mean. In Muslim cultures there is a
1,300-year-old scholarly tradition for this, with real books by named authors.

Dozens of websites offer AI dream interpretation. They all work the same way:
send the dream to a language model with a prompt like *"You are an expert in
Islamic dream interpretation"*, and print whatever comes back.

Try one. Ask what a snake means. You will get something like:

> **"According to Ibn Sirin, a snake in a dream represents a hidden enemy."**

Confident. Plausible. Well written.

**Now try to check it.** Which book? Which page? Did Ibn Sirin write that, or did
the model produce a sentence that merely sounds like something he might have
written?

You cannot check it, because there is nothing to check. And this is a topic where
people make real decisions — about marriages, business, health — based on the
answer.

**That gap is the product.**

---

## 2. Why the obvious solution fails

The obvious fix is a better prompt:

> "Only use authentic sources. Always cite the book and page. Never invent."

**This does not work, and it is important to understand why.**

A language model does not have a list of quotations it looks things up in. It
generates text that is statistically likely given what came before. When you ask
for a citation, "Ibn Sirin, page 142" is an extremely likely-looking thing to
appear after a claim about dream interpretation — so the model produces it,
whether or not page 142 says anything of the sort.

Asking a model not to invent citations is like asking someone to describe a
painting they have never seen but not to guess. The instruction does not give
them the missing information.

**A prompt is a request. It can be ignored, misread, or overridden. It is not a
guarantee.**

---

## 3. The key idea

> **Do not ask the model to remember. Give it the text, and let it only explain
> what it was given.**

Most AI dream apps:

```
   dream  ───────────────────────►  MODEL  ───────────────────►  answer
                            (recalls, cites nothing,
                             invents when unsure)
```

This project:

```
   dream ──► clean up ──► LOOK UP ──► fetch text ──► MODEL ──► answer
              (code)       (code)        (code)      (explains
                                                      what it got)
                              │
                              └──────► citations sent to the page
                                       separately, not via the model
```

The difference is not that we asked nicely. It is that **the model no longer has
the ability to invent**, because:

- it does not choose which symbols are in the dream — code did that
- it does not supply the classical text — code fetched it from files
- it does not write the page numbers — code stamps them from the source data
- if the model fails completely, **the quotations still appear on the page**

> **The lesson:** when correctness matters, remove the capability to be wrong.
> Do not merely discourage it.

This pattern has a name in industry — *retrieval-augmented generation*, or RAG —
but the name matters less than the discipline: **retrieval is code, generation is
commentary.**

---

## 4. What we are working with

### The subject, in sixty seconds

You need this much to follow the design.

Islamic tradition divides dreams into **three kinds**, based on a saying of the
Prophet Muhammad:

| Arabic | Said as | Meaning |
|---|---|---|
| رؤيا | *ru'ya* | A true vision. Good news. |
| حلم | *hulm* | A bad dream meant to distress. |
| أضغاث أحلام | *adghath ahlam* | "Jumbled dreams" — mental noise, yesterday's worries. |

**Only the first is really interpreted.**

If a dream is frightening, the tradition does not interpret it at all. It
prescribes actions: seek refuge in God, spit lightly to the left three times,
turn onto the other side, get up and pray, and **tell nobody**.

Notice that a site which eagerly interprets nightmares is working *against* the
tradition it claims to represent — while getting more engagement for doing so.
Our software classifies the dream first and refuses to interpret frightening
ones. That is a product decision that costs engagement and buys trust.

Two more properties that shaped the code:

**Meanings are conditional.** A real entry never says "a snake is an enemy" and
stops. It says: *if it is in the house, a household enemy; if you kill it,
victory over an enemy; if you are not afraid of it, your own strength.* That
branching **is** the scholarship. Flattening it to one sentence throws away the
thing you came for.

**Meanings depend on the dreamer.** The same symbol reads differently for a man
and a woman, married and unmarried, sick and healthy.

### The books

Six sources, all in Arabic. Five are public-domain classical texts from
[shamela.ws](https://shamela.ws), a free Islamic digital library. One is Freud,
in Arabic translation, from the Internet Archive.

| Source | Who | What it contributes |
|---|---|---|
| **Al-Nabulsi** (d. 1731) | Damascus scholar | 2,317 **symbols** — an A–Z dictionary |
| **Ibn Sirin** (d. 728) | *attributed* — see below | 2,792 passages |
| **Ibn Shahin** (d. 1468) | Egyptian scholar | 2,918 passages |
| **Ta'bir al-Ru'ya** | anonymous | 2,465 passages |
| **Imam al-Sadiq** (d. 765) | *attributed* — Shia tradition | 2,702 passages |
| **Freud** | Sigmund Freud, in Arabic | 1,861 passages |
| **Hadith on dreams** | a collection | 44 sayings on the etiquette |

**Total: 2,317 symbols and 12,738 passages.**

### An honesty problem, handled honestly

The most famous of these books is sold everywhere as "Ibn Sirin". **He did not
write it.** It quotes scholars who lived more than a century after he died. The
library's own editors say the attribution is "merely a commercial matter".

The same is true of the al-Sadiq text — researchers note that versions
circulating under his name mention **trains and pineapples**, which did not exist
in the 8th century.

Every competitor sells the famous name. We carry both books — they genuinely are
the traditions that circulate under those names — but **the caveat is attached to
every single citation from them.**

> **The lesson:** honesty about your own weaknesses is cheap to implement and
> very hard for a competitor to copy, because copying it means admitting the same
> thing.

---

## 5. Stage 1 — Getting the books

The library serves one page at a time at `shamela.ws/book/1217/91`. A script
walks each book page by page and saves the text.

One detail matters more than it looks. Each page carries **two** page numbers:

| | |
|---|---|
| the page number in the web address | useless to a reader |
| **the page number in the physical printed book** | what a scholar checks |

We store both. The printed number is what makes a citation verifiable by someone
holding the paper edition. **A citation nobody can check is decoration.**

The scraper is polite (waits 1.2 seconds between requests — this is a free
community library), caches every page, and resumes if interrupted.

**Result: 2,008 pages. Cost: nothing. No AI involved.**

---

## 6. Stage 2 — Cutting books into pieces

The books have four different physical layouts, so there are four parsers. They
all produce the same output shape, so nothing downstream has to care which kind
of book a piece came from.

### First: is this page even about dreams?

Books contain prefaces, editor's introductions, author biographies, poetry, and
chains of narration. None of that belongs in a dream corpus.

A filter drops them before anything else happens. **It cost two bugs to get
right** — see §10.

### Parser A — the dictionary (al-Nabulsi)

This book is alphabetical, and the library's HTML marks each headword. So the
scraper already captured them, **for free, with no AI**:

```
(ضرس)  يحصل في الأسنان في المنام خيانة ممن دلت الأسنان عليه كالأهل والأولاد...
  ↑                    ↑
headword:            its meaning
"molar tooth"        "Something happening to the teeth in a dream means
                      betrayal by whoever the teeth stand for — family,
                      children, spouses, partners…"
```

**This one book defines every symbol the whole system knows.** The other five are
then searched for whatever it names.

### Parser B — the prose books (Ibn Sirin, Ibn Shahin, Ta'bir)

These are continuous prose organised by topic, with **almost no punctuation**.
You cannot split on full stops because there aren't any.

But the prose has its own structure — fixed phrases that begin each new ruling:

| Arabic | Means |
|---|---|
| فإن رأى | "and if he sees" |
| ومن رأى | "and whoever sees" |
| وقال | "and he said" |
| ومن قرأ | "and whoever recites" |

So we cut the text at those phrases. Each piece is one ruling — exactly the unit
you want to quote.

### Parser C — the hadith book

Not a dictionary. Selected by **chapter title**, because this book's chapters are
precisely the topics needed: *"the types of vision"*, *"the instruction to spit
to the left three times"*, *"the prohibition on relating a disliked dream"*.

### Parser D — the scanned books (Freud, al-Sadiq)

These came as scans run through text recognition. The al-Sadiq volume is a
decorated edition, and the ornamental page borders became garbage:

```
E O ATTN iv gO Sa o RTT SARO
OF a OOF FO. OF a FO OF fS O a O O ao O r a O e
```

About 38% of the file looked like that. The rescue is a simple rule: **keep a
line only if at least 90% of its letters are Arabic**, it is 25+ characters, has
5+ words, and averages 2.5+ characters per word.

That last condition matters — border fragments survive as runs of one- and
two-letter tokens and pass every other test.

**Result: 679 KB of clean text recovered, 62% of the file.**

---

## 7. Stage 3 — Building the index

Now we build the thing the website actually searches.

**The symbol list** — 2,317 entries, each with a `key`: the headword stripped
down for matching (explained next).

**The passage index** — a lookup table: *symbol → passages mentioning it*.

Here is a performance decision worth understanding. The naive approach is: for
each of 2,317 symbols, search all ~15,000 passages. That is **35 million
searches**.

Instead we invert it. For each passage, generate every word and phrase it
*could* be, then check which of those are known symbols. Set lookup is instant.

**Whole index builds in under 5 seconds.**

> **The lesson:** when a loop is too slow, check whether you can turn it inside
> out before reaching for a database.

---

## 8. Stage 4 — Answering one dream, start to finish

Real trace. The dream:

> **حلمت أني وقعت من بناية عالية وأسناني تسقط**
> *"I dreamed I fell from a tall building and my teeth were falling out."*

### Step 1 — Normalise

Arabic has optional vowel marks and letters with variant forms, so the same word
can be spelled several ways. We fold them all to one form:

```
before:  حلمت أني وقعت من بناية عالية وأسناني تسقط
after:   حلمت اني وقعت من بنايه عاليه واسناني تسقط
```

Applied to **both** the dream and the stored symbols, so spelling stops
mattering.

**Important:** this stripped-down form is used *only* for matching. What we
display and quote stays exactly as printed. If you normalise your stored text you
have corrupted your own evidence.

### Step 2 — Aliases

Four fire here:

```
اسنان  →  ضرس     "teeth"       → the dictionary files them under "molar"
وقعت   →  سقوط    "I fell"      → the dictionary uses the noun "falling"
تسقط   →  سقوط    "falling"     → same
بنايه  →  بناء    "building"    → modern word → classical word
```

Why is a table needed at all? Two reasons no rule can handle:

**Arabic plurals often restructure the word instead of adding an ending.**
*hayya* (snake) → *hayyat* (snakes). English adds "-s"; Arabic changes the middle
of the word.

**People write verbs; dictionaries store nouns.** Someone types "I fell"
(*waqa'tu*). The book files everything under "falling" (*suqut*). No spelling
rule connects them.

### Step 3 — Match

```
matched in 1.01 milliseconds:
   ضرس   (molar tooth)
   سقوط  (falling)
   بناء  (building)
```

Symbols are checked longest-first, so a longer phrase suppresses its own parts —
otherwise a dream mentioning "the sheep's tail" would also report "sheep" as a
separate symbol.

### Step 4 — Fetch the text

For the first symbol, the dictionary's own definition, **verbatim**:

> **(ضرس)** يحصل في الأسنان في المنام خيانة ممن دلت الأسنان عليه كالأهل والأولاد
> والأزواج أو الشركاء…
>
> *"Something happening to the teeth in a dream means betrayal by whoever the
> teeth stand for — family, children, spouses, or partners…"*
>
> — *Ta'tir al-Anam*, al-Nabulsi, **printed page 224** ·
> [source](https://shamela.ws/book/1217/221)

Then supporting passages from the other books:

```
ضرس  → ibn_sirin 2 · tabir 1 · sadiq 1 · freud 1
سقوط → ibn_sirin 1 · ibn_shaheen 1 · tabir 1 · sadiq 1 · freud 2
بناء → ibn_sirin 1 · ibn_shaheen 1 · tabir 1 · sadiq 1 · freud 2
```

Note the deliberate balance. Two rules:

1. **Classical and psychological are capped separately.** The classical books
   have ~11,000 passages, Freud has 1,861. First-come-first-served would bury the
   psychological reading in every single answer.
2. **Within the classical share, sources take turns.** This one was a bug — see
   §10.

### Step 5 — Fetch the etiquette

The dream sounds distressing, so hadith about frightening dreams are selected:

> عن إبراهيم النخعي: «إذا رأى أحدكم رؤيا يكرهها فليقل أعوذ بما عاذت به ملائكة
> الله ورسله من شر رؤياي…»
>
> *"If one of you sees a dream he dislikes, let him say: I seek refuge in what
> God's angels and messengers sought refuge in, from the evil of my dream…"*
>
> — chapter: *"What one says who sees in his dream what he dislikes"*

### Step 6 — Build the prompt

The dream, the dreamer's stated situation, and **only the fetched passages** —
each labelled as classical or psychological.

**12,049 characters ≈ 4,000 tokens.**

### Step 7 — Call the model

The model must return **structured data**, not free text — so required fields
cannot be skipped. Including:

| Field | Why it is required |
|---|---|
| classification | which of the three kinds |
| **is it frightening?** | if yes, no interpretation — etiquette instead |
| verdict sentence | the judgement in plain language, not a label |
| conditions | the "if X then Y" branches |
| **method** | which of seven reasoning principles was used |
| **from the books?** | **true/false — the honesty flag** |

That last field is the whole product. Every claim is stamped as either *quoted
from a book* or *general knowledge*, and the page shows which.

### The whole thing, timed

| Step | Time |
|---|---|
| Steps 1–5 (all the code) | **1.5 ms** |
| Step 7 (the AI call) | **6,000 ms** |

**Retrieval is 0.02% of the request.** Worth remembering when someone tells you
the lookup needs a specialised database.

---

## 9. What the user sees

A verdict first, in plain language:

> ┌─ *A true vision · built on 14 original texts* ─┐
>
> ### A blessed vision, pointing to a new stage in your life and to relief, God willing

Then each symbol, with a critical distinction:

**Symbol: tall building** — tagged **cited**
> A high building indicates lofty ambitions the dreamer strives toward.
> *Method: derivation of the word — height denotes elevation and advancement, so
> falling from it expresses fear of not attaining.*
> — *Ta'tir al-Anam*, al-Nabulsi (p. 233) · [source]

**Symbol: falling** — tagged **general knowledge**, no sources
> May indicate a change of state or a transition from one condition to another.

Look at those two tags. The books genuinely did not cover *falling from a height*
in the matched entries — **so the system says so, rather than inventing a
citation.** The other symbol has two named books behind it.

Then the original Arabic of every passage, each with book, author, printed page
and a link to the scan.

**That distinction — cited versus not — is the entire product.**

---

## 10. Five bugs and what each taught

Real bugs from this build. The lessons generalise well beyond this project.

### Bug 1 — The filter deleted everything

The dream-content filter dropped **all 492 pages**.

Cause: the library puts the words *"book index"* in the navigation strip of
**every** page. The "skip index pages" rule matched everywhere.

> **Lesson:** boilerplate that appears on every page is invisible until it
> matches a rule. Strip the constant before testing the variable.

### Bug 2 — The filter deleted the good stuff

Fixed version dropped Ibn Sirin's chapter on reciting Qur'an in dreams. That
chapter is pure symbol content — *"whoever recites Surat al-Kahf in a dream will
attain his wishes"* — but it is phrased with "whoever recites" and **never uses
the word "dream" at all.** It scored zero.

Fix: if a page sits inside a chapter whose *title* is about dreams, keep it
regardless of the page's own wording.

> **Lesson:** a heuristic tuned on typical documents fails on the atypical ones,
> which are often the valuable ones. Test your filter on what it *removes*, not
> on what it keeps.

### Bug 3 — "I fell from a building" matched nothing

The word *falling* was in the dictionary. The user typed *"I fell"*. No rule
connects a conjugated verb to its noun form.

> **Lesson:** your users' vocabulary is not your data's vocabulary. Log what
> finds nothing — that log is your roadmap.

### Bug 4 — Every direct object silently failed

Worse version of the same class, and my favourite bug here.

Arabic marks an indefinite noun in the object position with an extra letter:
*road* → *a road*, *rain* → *heavy rain*. Normalisation removed the vowel mark
but left that extra letter, which was not in the list of allowed endings.

So **"I saw a road and rain" matched nothing at all** — while "I saw road"
matched both. Since almost every dream is written as "I saw a ___", this was
silently breaking a large share of real input.

The fix was **one character** added to a pattern. That dream went from 0 to 14
citations.

> **Lesson:** the worst bugs return a plausible answer instead of an error. This
> one produced a fluent interpretation every time — just not one based on the
> books. Test with realistic sentences, not with keywords.

### Bug 5 — Two of six sources were never used

The user asked a simple question: *"with all sources selected, do we send them
all?"*

Measurement said no. Passages were taken in list order, so the first book's three
passages plus one of the second's filled the quota of four. **Ta'bir al-Ru'ya and
the al-Sadiq text were never sent on any request**, despite being fully indexed.

Fix: take one passage per source in turn.

> **Lesson:** a cap plus an ordered list is a silent starvation bug. It never
> errors, it just quietly excludes. And note how it was found — someone asked a
> question and we *measured* instead of reasoning about the code.

---

## 11. Design decisions worth stealing

**Remove the capability, not just the permission.** The model cannot invent
citations because it never handles them.

**Make the honesty flag structural.** Every claim carries true/false for
"is this from a source?". It is a required field, so it cannot be quietly
omitted.

**Never return nothing.** When the books have no entry, the system still answers —
from general knowledge — but says so plainly. An empty result is a bad user
experience; an unlabelled guess is a bad product. The third option is a labelled
guess.

**Degrade without collapsing.** If every AI model is unavailable, the endpoint
returns an error *with the quotations still attached*. The most valuable part of
the page survives the outage.

**Choose boring retrieval when it fits.** No embeddings, no vector database. The
books are dictionaries keyed by symbol, so exact lookup is both more accurate and
**explainable** — you can show a user *why* a symbol matched. And it runs in 1.5
milliseconds.

**Let honesty be a feature.** Saying "this book is not really by Ibn Sirin" costs
nothing and is hard to copy.

**Separate build-time from run-time.** Scraping and parsing happen on a developer
machine and produce a file. The server just reads the file. Roughly 450 lines and
one 13 MB file run in production; everything else is tooling.

---

## 12. Exercises

1. **Explain the difference** between telling a model "always cite your sources"
   and giving it the sources. Why does only one of them work?

2. **Bug 4** (the missing letter) produced fluent, confident, *wrong* answers
   rather than errors. Name two ways you could have caught it automatically.

3. The system caps passages at 4 classical + 2 psychological per symbol. What
   breaks if you remove the cap? What breaks if you set it to 1?

4. Al-Nabulsi's dictionary alone defines every symbol the system knows. Name one
   strength and one weakness of that design.

5. The dream is always written in Arabic, even when the interface is English.
   Why? What would it take to accept English dreams, and what would you lose?

6. **Design question.** Users are typing dreams that match no symbols. You can
   (a) hand-write more aliases, (b) have an AI generate aliases offline, or
   (c) add semantic search with embeddings. What would you measure before
   choosing, and which would you try first?

---

## Further reading in this repository

| Document | Contents |
|---|---|
| [OVERVIEW.md](OVERVIEW.md) | The tradition and architecture in more depth |
| [PARSING.md](PARSING.md) | Each parser and matching rule in full |
| [SOURCES.md](SOURCES.md) | Every book with links and page ranges |
| `/docs` on the running API | Interactive endpoint reference |
