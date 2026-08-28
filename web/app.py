"""موقع تعبير الرؤيا — واجهة الويب.

The split that matters: symbol lookup runs in code against the scraped books, so
the model is bounded by what the corpus actually contains. The API key is used
for one call per dream — composing the answer from entries that were already
found, plus, when the books are silent, what is settled among the interpreters,
labelled as such so the reader always knows which of the two they are reading.

    .venv/bin/uvicorn web.app:app --port 3000
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from corpus import answer as answer_mod
from corpus import index

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACKS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.5-flash,gemini-3.1-flash-lite,gemini-3.6-flash",
    ).split(",")
    if m.strip()
]
MODELS = [MODEL] + [m for m in FALLBACKS if m != MODEL]

STATIC = Path(__file__).parent / "static"

# Words suggesting the dream distressed the dreamer. Only a hint — the model
# makes the call — but it decides which adab passages are worth supplying.
DISTRESS_HINTS = [
    "خائف", "خفت", "خوف", "مرعب", "مفزع", "فزع", "كابوس", "مزعج",
    "أبكي", "بكيت", "حزين", "قلق", "دم", "موت", "أموت", "يطاردني",
    "هرب", "أهرب", "ثعبان", "حية", "نار", "جن", "شيطان", "قتل",
]

app = FastAPI(title="تعبير الرؤيا")
ENTRIES, PASSAGES, ADAB = index.load()


class DreamIn(BaseModel):
    dream: str = Field(min_length=3, max_length=4000)
    # All optional. The books themselves read a symbol differently for a man and
    # a woman, the married and the unmarried, the sick and the healthy — so when
    # the dreamer volunteers this, it genuinely changes the reading.
    jins: str | None = Field(default=None, max_length=20)
    hala: str | None = Field(default=None, max_length=30)
    umr: str | None = Field(default=None, max_length=30)
    shuur: str | None = Field(default=None, max_length=40)
    alam: str | None = Field(default=None, max_length=20)
    takrar: str | None = Field(default=None, max_length=20)
    waqt: str | None = Field(default=None, max_length=30)

    def context(self) -> dict:
        keys = ("jins", "hala", "umr", "shuur", "alam", "takrar", "waqt")
        return {k: v for k in keys if (v := getattr(self, k))}


def _citations(match: dict) -> list[dict]:
    src = match["source"]
    out = [
        {
            "text_ar": match["body_ar"],
            "book_ar": src["book_ar"],
            "author": src["author"],
            "printed_page": src.get("printed_page"),
            "url": src["url"],
            "lens": src.get("lens", "nabulsi"),
        }
    ]
    out += [
        {
            "text_ar": p["text_ar"],
            "book_ar": p["book_ar"],
            "author": p["author"],
            "printed_page": p.get("printed_page"),
            "url": p["url"],
            "lens": p.get("lens", ""),
        }
        for p in (match.get("passages") or [])
    ]
    return out


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "symbols": len(ENTRIES),
        "passages": sum(len(v) for v in PASSAGES.values()),
        "adab": len(ADAB),
        "books": 5,
        "models": MODELS,
    }


@app.get("/api/symbols")
def symbols(q: str = "", limit: int = 40) -> dict:
    """Browse the symbol vocabulary — useful on its own, and the seed for
    per-symbol pages later."""
    q = q.strip()
    pool = [e for e in ENTRIES if not q or q in e["symbol_ar"]]
    pool = sorted(pool, key=lambda e: len(e["symbol_ar"]))[:limit]
    return {
        "count": len(pool),
        "symbols": [
            {"symbol_ar": e["symbol_ar"], "excerpt": e["body_ar"][:160]} for e in pool
        ],
    }


@app.post("/api/interpret")
def api_interpret(payload: DreamIn) -> JSONResponse:
    dream = payload.dream.strip()
    matches = index.match(dream, ENTRIES, PASSAGES, limit=6)

    context = payload.context()
    distress = any(w in dream for w in DISTRESS_HINTS) or (
        payload.alam in ("نعم", "yes") or payload.shuur in ("قلق", "خوف", "حزن")
    )
    adab = index.adab_for(dream, ADAB, distressing_hint=distress)

    symbols_payload = [
        {"symbol_ar": m["symbol_ar"], "citations": _citations(m)} for m in matches
    ]
    adab_payload = [
        {
            "text_ar": a["text_ar"],
            "book_ar": a["book_ar"],
            "chapter_ar": a.get("chapter_ar"),
            "printed_page": a.get("printed_page"),
            "url": a["url"],
        }
        for a in adab
    ]

    last_error = None
    for model in MODELS:
        try:
            result = answer_mod.answer(dream, matches, adab, model, context)
            return JSONResponse(
                {
                    "answer": result,
                    "symbols": symbols_payload,
                    "adab_sources": adab_payload,
                    "matched": len(matches),
                    "context": context,
                    "model": model,
                }
            )
        except Exception as e:
            last_error = e
            continue

    # Even with every model out of quota the lookup succeeded, so the classical
    # text is still returned — that is the part users came for.
    return JSONResponse(
        status_code=503,
        content={
            "answer": None,
            "symbols": symbols_payload,
            "adab_sources": adab_payload,
            "matched": len(matches),
            "error": f"تعذّر توليد الشرح حالياً. النصوص من الكتب معروضة أدناه. ({str(last_error)[:120]})",
        },
    )


app.mount("/static", StaticFiles(directory=STATIC), name="static")
