# تأويل — Ta'weel

Arabic dream interpretation grounded in six source texts. A dream is typed in
Arabic, its symbols are looked up **in code** against an indexed corpus, and the
model only explains what the lookup found.

The rule the whole design enforces: **the reader always knows where a statement
came from.** Every classical claim carries a book, an author, a printed page and
a link to the source scan. Anything not backed by the corpus is labelled as such
rather than dressed up as a citation.

## Read these, in order

| Document | What it covers |
|---|---|
| **[docs/CASE-STUDY.md](docs/CASE-STUDY.md)** | Plain-English walkthrough for someone new to the project: the problem, why the obvious solution fails, one dream traced end to end with real output, and the five bugs worth learning from. English only, no Arabic assumed. |
| **[docs/OVERVIEW.md](docs/OVERVIEW.md)** | Start here. What the project is, the tradition behind it, and how a request flows end to end. Written for a reader who does not know Arabic. |
| **[docs/PARSING.md](docs/PARSING.md)** | How the books become structured data — the four parsers, the OCR rescue, and the matching rules. |
| **[docs/SOURCES.md](docs/SOURCES.md)** | Every book, with links, page ranges and what it contributes. |
| **[docs/DEPLOY.md](docs/DEPLOY.md)** | Running it in production, and the cache headers that stop a browser serving stale code. |
| `/docs` on the running API | Interactive OpenAPI reference. |

## Layout

```
backend/     FastAPI. Pure JSON API — serves no HTML
pipeline/    build-time tools: scrape → parse → build_index
context/     one folder per source: raw pages, parsed chunks, metadata
index/       the built artifact the API loads (13 MB)
frontend/    standalone client, talks to the API over HTTP
docs/        documentation + the design prototype
```

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 3000   # API
.venv/bin/python frontend/serve.py 5173                        # frontend
```

Use `frontend/serve.py` rather than `python -m http.server`: it sends `no-store`,
so a reload always runs the code on disk. The stock server answers 304 and a
browser will happily keep executing a script from an hour ago.

The index is committed, so no build step is needed. Open `frontend/index.html`
directly, or serve it from anywhere — it finds the API via `?api=`, a global, or
same-origin.

`.venv/bin/python -m pipeline.models` lists the models your key can reach.
Availability differs per key, and free-tier quota is metered **per model**, so
the server falls through `GEMINI_FALLBACK_MODELS` when one runs dry.

## Rebuild the corpus

```bash
.venv/bin/python -m pipeline.scrape --all    # ~1,800 pages, rate limited
.venv/bin/python -m pipeline.parse --all     # raw -> chunks
.venv/bin/python -m pipeline.build_index     # chunks -> index
```

Parse and index together take about 6 seconds. **Do not delete `context/*/raw/`**
— the index is derived from it, and every change to the alias table or the
matching rules means rebuilding from it.

## Adding a book

One entry in `pipeline/sources.py`, then scrape, parse, build. See
[docs/PARSING.md](docs/PARSING.md#adding-a-book).
