"""The main endpoint.

The split that defines this project: symbol lookup runs in code, so the model can
only speak about what the corpus actually contains. It cannot choose the symbols,
cannot supply the classical text, and cannot produce a page number — those are
stamped from the index.

Citations are assembled before the model is called and returned regardless of
what it does, so an AI outage degrades the answer without destroying the page.
"""

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import answer as answer_mod
from .. import config
from ..deps import CORPUS, source_names_ar, source_public
from ..schemas import DreamRequest, InterpretResponse
from ..search import looks_distressing

router = APIRouter(tags=["interpret"])


def _citations(match: dict) -> list[dict]:
    """The headword entry first, then its supporting passages."""
    def cite(text, slug, kind, page, url):
        pub = source_public(slug)
        return {
            "text_ar": text,
            "source": slug,
            "source_name": pub.get("name", {"ar": slug, "en": slug}),
            "author": pub.get("author", {"ar": "", "en": ""}),
            "kind": kind,
            "printed_page": page,
            "url": url or None,
        }

    out = []
    if match.get("own_text_applies", True):
        out.append(cite(match["text_ar"], match["source"], "classical",
                        match.get("printed_page"), match.get("url")))
    out += [
        cite(p["text_ar"], p["source"], p.get("kind", "classical"),
             p.get("printed_page"), p.get("url"))
        for p in match.get("passages", [])
    ]
    return out


@router.post("/interpret", response_model=InterpretResponse)
def interpret(payload: DreamRequest):
    started = time.time()
    dream = payload.dream.strip()
    context = payload.context()

    matches = CORPUS.match(dream, source=payload.source)
    distressing = looks_distressing(dream) or payload.alam == "نعم" or \
        payload.shuur in ("قلق", "خوف", "حزن")
    adab = CORPUS.adab_for(dream, distressing)

    symbols = [
        {"symbol_ar": m["symbol_ar"], "key": m["key"], "citations": _citations(m)}
        for m in matches
    ]
    # A symbol with no citations left after filtering to one source is not
    # corpus-backed for this reader, even though the lookup found it.
    cited = sum(len(s["citations"]) for s in symbols)
    adab_sources = [
        {"text_ar": a["text_ar"], "source": a["source"],
         "chapter_ar": a.get("chapter_ar"), "printed_page": a.get("printed_page"),
         "url": a.get("url") or None}
        for a in adab
    ]

    last_error = None
    for model in config.MODELS:
        try:
            result = answer_mod.generate(
                dream, matches, adab, model, context, source_names_ar(),
                payload.source,
            )
        except Exception as e:            # quota, transport, malformed JSON
            last_error = e
            continue
        return {
            "answer": result,
            "symbols": symbols,
            "adab_sources": adab_sources,
            "context": context,
            "meta": {
                "source": payload.source,
                "used_corpus": cited > 0,
                "model": model,
                "elapsed_ms": int((time.time() - started) * 1000),
                "matched": len(matches),
                "answer_available": True,
            },
        }

    # Every model exhausted. The lookup still succeeded, so the classical text is
    # returned anyway — 503 tells the client the explanation is missing, not the
    # citations.
    return JSONResponse(
        status_code=503,
        content={
            "answer": None,
            "symbols": symbols,
            "adab_sources": adab_sources,
            "context": context,
            "meta": {
                "source": payload.source,
                "used_corpus": cited > 0,
                "model": None,
                "elapsed_ms": int((time.time() - started) * 1000),
                "matched": len(matches),
                "answer_available": False,
                "error": f"all models unavailable: {str(last_error)[:160]}",
            },
        },
    )
