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
from .. import misses
from ..deps import CORPUS, source_names_ar, source_public
from ..schemas import DreamRequest, InterpretResponse
from ..search import looks_distressing

router = APIRouter(tags=["interpret"])


# The model sets the indicator percentages, and left alone it sometimes
# contradicts its own classification — a dream it called distressing coming back
# with low anxiety. The two sit side by side on the page, so an incoherent pair
# is worse than an approximate one. These bounds are the floor and ceiling each
# classification implies; anything inside them is left exactly as the model set
# it, and only a genuine contradiction is corrected.
_BOUNDS = {
    #                     tafaul      raja       qalaq
    "رؤيا صالحة":       ((55, 100), (55, 100), (0, 45)),
    "حلم من الشيطان":   ((0, 45),   (0, 55),   (55, 100)),
    "أضغاث أحلام":      ((20, 70),  (20, 75),  (25, 80)),
}


def _coherent(answer: dict) -> dict:
    """Keep the indicators consistent with the classification they sit beside."""
    ind = answer.get("muashirat")
    if not isinstance(ind, dict):
        return answer

    bounds = _BOUNDS.get((answer.get("tasnif") or {}).get("naw"))
    adjusted = []
    for field, span in zip(("tafaul", "raja", "qalaq"), bounds or ()):
        try:
            value = int(ind.get(field, 0))
        except (TypeError, ValueError):
            value = 0
        clamped = max(span[0], min(span[1], value))
        if clamped != value:
            adjusted.append(field)
        ind[field] = clamped

    # A dream the model itself called distressing cannot read as calm.
    if answer.get("mukhifah") and ind.get("qalaq", 0) < 55:
        ind["qalaq"] = 55
        adjusted.append("qalaq")

    if adjusted:
        ind["adjusted"] = sorted(set(adjusted))
    return answer


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


@router.post("/match")
def match_only(payload: DreamRequest) -> dict:
    """Symbols and citations, with no model call. Costs ~2 ms.

    The page uses this first so a reader sees their symbols and the classical
    text almost immediately, then fills in the interpretation when the model
    returns six to nine seconds later. Waiting on the model to show text that
    was already on disk is a self-inflicted delay.
    """
    started = time.time()
    dream = payload.dream.strip()
    matches = CORPUS.match(dream, source=payload.source)
    misses.record(dream, matches)
    distressing = looks_distressing(dream) or payload.alam == "نعم" or \
        payload.shuur in ("قلق", "خوف", "حزن")
    return {
        "symbols": [
            {"symbol_ar": m["symbol_ar"], "key": m["key"], "citations": _citations(m)}
            for m in matches
        ],
        "matched": len(matches),
        "distressing": distressing,
        "source": payload.source,
        "elapsed_ms": int((time.time() - started) * 1000),
    }


@router.post("/interpret", response_model=InterpretResponse)
def interpret(payload: DreamRequest):
    started = time.time()
    dream = payload.dream.strip()
    context = payload.context()

    matches = CORPUS.match(dream, source=payload.source)
    # Note the words that reached nothing. Words only — never the dream itself.
    misses.record(dream, matches)
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
            result = _coherent(answer_mod.generate(
                dream, matches, adab, model, context, source_names_ar(),
                payload.source,
            ))
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
