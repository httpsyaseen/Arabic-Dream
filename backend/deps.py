"""Shared singletons.

The index is ~13 MB of JSON and takes ~150 ms to parse, so it is loaded once at
import time and reused by every request. Loading it per request would make the
lookup the slowest part of the system instead of the fastest.
"""

from functools import lru_cache

from pipeline import sources

from .search import Corpus

CORPUS = Corpus()


@lru_cache(maxsize=1)
def source_names_ar() -> dict[str, str]:
    return {s.slug: s.name_ar for s in sources.SOURCES.values()}


def source_public(slug: str) -> dict:
    s = sources.SOURCES.get(slug)
    return sources.as_dict(s) if s else {"slug": slug}
