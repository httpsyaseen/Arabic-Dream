"""Health, sources, and form options — everything a frontend needs to render
itself without hardcoding Arabic or duplicating the source list."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from pipeline import sources

from .. import config
from ..deps import CORPUS
from ..schemas import HealthResponse
from .. import misses

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {
        "status": "ok",
        "api_key_configured": config.HAS_KEY,
        "models": config.MODELS,
        "counts": CORPUS.stats,
    }


@router.get("/sources")
def list_sources() -> dict:
    """Every indexed source, with both names, its role, and its attribution note.

    Also returns names people search for that have no book behind them, so the
    site can answer honestly instead of silently having nothing to say.
    """
    return {
        "sources": [sources.as_dict(s) for s in sources.SOURCES.values()],
        "not_sources": [
            {"slug": k, **v} for k, v in sources.NON_SOURCES.items()
        ],
    }


@router.get("/options")
def options() -> dict:
    """Choices for the optional questions about the dreamer, labelled in both
    languages so the frontend ships no translation table of its own."""
    return {
        "fields": [
            {"key": "jins", "label": {"ar": "الجنس", "en": "Gender"},
             "values": [{"ar": "ذكر", "en": "Male"}, {"ar": "أنثى", "en": "Female"}]},
            {"key": "hala", "label": {"ar": "الحالة الاجتماعية", "en": "Marital status"},
             "values": [{"ar": "أعزب", "en": "Single"}, {"ar": "متزوج", "en": "Married"},
                        {"ar": "مطلق", "en": "Divorced"}, {"ar": "أرمل", "en": "Widowed"}]},
            {"key": "umr", "label": {"ar": "الفئة العمرية", "en": "Age range"},
             "values": [{"ar": "أقل من ٢٠", "en": "Under 20"}, {"ar": "٢٠-٣٠", "en": "20-30"},
                        {"ar": "٣٠-٤٠", "en": "30-40"}, {"ar": "٤٠-٦٠", "en": "40-60"},
                        {"ar": "أكثر من ٦٠", "en": "Over 60"}]},
            {"key": "shuur", "label": {"ar": "الحال النفسية", "en": "Waking state"},
             "values": [{"ar": "مطمئن", "en": "At ease"}, {"ar": "قلق", "en": "Anxious"},
                        {"ar": "حزن", "en": "Sad"}, {"ar": "خوف", "en": "Fearful"},
                        {"ar": "فرح", "en": "Joyful"}]},
            {"key": "alam", "label": {"ar": "ألم في الرؤيا", "en": "Pain in the dream"},
             "values": [{"ar": "نعم", "en": "Yes"}, {"ar": "لا", "en": "No"}]},
            {"key": "takrar", "label": {"ar": "تتكرر الرؤيا", "en": "Recurring"},
             "values": [{"ar": "نعم", "en": "Yes"}, {"ar": "لا", "en": "No"}]},
        ],
        # Paired, because the dream itself is always written in Arabic: the
        # English label is what an English reader reads, `ar` is what gets typed
        # into the box.
        "examples": [
            {"ar": "رأيت أفعى تطاردني",
             "en": "I dreamed a snake was chasing me"},
            {"ar": "رأيت أسناني تتساقط",
             "en": "I dreamed my teeth were falling out"},
            {"ar": "رأيت أبي المتوفى يبتسم لي",
             "en": "I dreamed my late father smiled at me"},
        ],
    }


@router.get("/misses")
def unmatched(top: int = 60) -> dict:
    """Words that reached no symbol, most frequent first.

    The list of aliases still worth writing. Dreams are never stored — only the
    individual words, which is enough to act on and carries almost none of the
    content of the dream they came from.
    """
    data = misses._load()
    ranked = sorted(data["words"].items(), key=lambda kv: -kv[1])[:top]
    return {
        "dreams_seen": data["dreams_seen"],
        "dreams_with_no_match": data["dreams_with_no_match"],
        "distinct_unmatched_words": len(data["words"]),
        "words": [{"word": w, "count": n} for w, n in ranked],
    }


PAGES = Path(__file__).resolve().parent.parent.parent / "index" / "pages"


@router.get("/pages")
def list_pages() -> dict:
    """Topic pages built from a keyword sheet."""
    if not PAGES.exists():
        return {"pages": []}
    out = []
    for f in sorted(PAGES.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        cached = PAGES / d["slug"]
        out.append({
            "slug": d["slug"],
            "totals": d.get("totals", {}),
            "prerendered": len(list(cached.glob("*.json"))) - 1 if cached.exists() else 0,
        })
    return {"pages": out}


@router.get("/pages/{slug}")
def get_page(slug: str) -> dict:
    """One topic page: its clusters, each with the dream a reader would type.

    The searches people run are not dreams — nobody types "interpretation of
    dream of teeth falling for single woman". Each cluster therefore carries the
    sentence a person would actually write, which is what the site can act on.
    """
    path = PAGES / f"{slug}.json"
    if not path.exists() or "/" in slug or ".." in slug:
        raise HTTPException(404, f"no page {slug!r}")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/pages/{slug}/{query}")
def get_prerendered(slug: str, query: str) -> dict:
    """A reading generated ahead of time, served from disk.

    The topic pages carry the most traffic and the least variation — the same
    sixteen dreams asked over and over — so answering each one live would spend
    a model call per visitor for a reading identical to the last. These were
    produced by the same endpoint, so what is stored is what a live call would
    have returned.
    """
    if any(bad in part for part in (slug, query) for bad in ("/", "..")):
        raise HTTPException(404, "not found")
    path = PAGES / slug / f"{query}.json"
    if not path.exists():
        raise HTTPException(404, f"no cached reading {slug}/{query}")
    return json.loads(path.read_text(encoding="utf-8"))
