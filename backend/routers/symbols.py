"""Browsing the symbol vocabulary.

Useful on its own, and the seed for per-symbol pages later — 2,317 static routes
with real text and citations is the search-traffic engine a single-page app
cannot provide.
"""

from fastapi import APIRouter, HTTPException, Query

from ..deps import CORPUS, source_public
from ..schemas import SymbolsResponse

router = APIRouter(prefix="/symbols", tags=["symbols"])


@router.get("", response_model=SymbolsResponse)
def list_symbols(
    q: str = Query("", description="Arabic substring to filter by"),
    limit: int = Query(40, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    total, page = CORPUS.search_symbols(q, limit, offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "symbols": [
            {"symbol_ar": e["symbol_ar"], "key": e["key"],
             "excerpt": e["text_ar"][:200], "source": e["source"]}
            for e in page
        ],
    }


@router.get("/{key}")
def get_symbol(key: str) -> dict:
    entry = CORPUS.symbol(key)
    if entry is None:
        raise HTTPException(404, f"no symbol matching {key!r}")
    return {
        "symbol_ar": entry["symbol_ar"],
        "key": entry["key"],
        "text_ar": entry["text_ar"],
        "source": source_public(entry["source"]),
        "printed_page": entry.get("printed_page"),
        "url": entry.get("url"),
        "passages": [
            {"text_ar": p["text_ar"], "kind": p.get("kind"),
             "source": source_public(p["source"]),
             "printed_page": p.get("printed_page"), "url": p.get("url")}
            for p in entry.get("passages", [])
        ],
    }
