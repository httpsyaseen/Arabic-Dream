"""Request and response shapes.

Kept explicit rather than returning raw dicts, so the generated OpenAPI docs at
/docs are usable as the contract by whoever builds the frontend.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Bilingual(BaseModel):
    ar: str
    en: str


class DreamRequest(BaseModel):
    dream: str = Field(min_length=3, max_length=4000,
                       description="The dream, in Arabic")

    # All optional. The books themselves read a symbol differently for a man and
    # a woman, the married and the unmarried, the sick and the healthy, so when
    # the dreamer volunteers this it genuinely changes the reading.
    jins: str | None = Field(None, max_length=20, description="gender — ذكر / أنثى")
    hala: str | None = Field(None, max_length=30, description="marital status")
    umr: str | None = Field(None, max_length=30, description="age range")
    shuur: str | None = Field(None, max_length=40, description="waking emotional state")
    alam: str | None = Field(None, max_length=20, description="pain in the dream — نعم / لا")
    takrar: str | None = Field(None, max_length=20, description="does it recur — نعم / لا")
    waqt: str | None = Field(None, max_length=30, description="time of the dream")

    # Which interpreter to answer as. Omit for all sources together. When set,
    # only that source's text is shown and the fallback answers in its manner.
    source: str | None = Field(None, max_length=40,
                               description="lens slug, e.g. ibn_sirin — see GET /sources")

    def context(self) -> dict[str, str]:
        keys = ("jins", "hala", "umr", "shuur", "alam", "takrar", "waqt")
        return {k: v for k in keys if (v := getattr(self, k))}


class Citation(BaseModel):
    text_ar: str
    source: str
    source_name: Bilingual
    author: Bilingual
    kind: Literal["classical", "psychological", "adab"]
    printed_page: str | None = None
    url: str | None = None


class SymbolHit(BaseModel):
    symbol_ar: str
    key: str
    citations: list[Citation]


class AdabSource(BaseModel):
    text_ar: str
    source: str
    chapter_ar: str | None = None
    printed_page: str | None = None
    url: str | None = None


class InterpretMeta(BaseModel):
    source: str | None = None          # the lens asked for, if any
    used_corpus: bool = True           # False when the answer fell back to general knowledge
    model: str | None = None
    elapsed_ms: int
    matched: int
    answer_available: bool
    # Set when every model was exhausted. The citations are still returned —
    # the classical text is what users came for and it survives an AI outage.
    error: str | None = None


class InterpretResponse(BaseModel):
    answer: dict[str, Any] | None
    symbols: list[SymbolHit]
    adab_sources: list[AdabSource]
    context: dict[str, str]
    meta: InterpretMeta


class SymbolSummary(BaseModel):
    symbol_ar: str
    key: str
    excerpt: str
    source: str


class SymbolsResponse(BaseModel):
    total: int
    limit: int
    offset: int
    symbols: list[SymbolSummary]


class HealthResponse(BaseModel):
    status: str
    api_key_configured: bool
    models: list[str]
    counts: dict[str, Any]
