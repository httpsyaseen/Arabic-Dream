"""Health, sources, and form options — everything a frontend needs to render
itself without hardcoding Arabic or duplicating the source list."""

from fastapi import APIRouter

from pipeline import sources

from .. import config
from ..deps import CORPUS
from ..schemas import HealthResponse

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
        "examples": [
            "رأيت حية",
            "رأيت في المنام حية كبيرة دخلت بيتي وكنت خائفاً",
            "حلمت أن أسناني تسقط في يدي",
            "رأيت أبي المتوفى حياً يبتسم لي",
            "حلمت أني أسقط من بناية عالية",
            "رأيت الكعبة وأنا أصلي",
        ],
    }
