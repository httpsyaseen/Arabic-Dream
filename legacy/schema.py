"""Response schema for extraction, plus the enums the corpus is allowed to use.

Provenance (book, page, url, printed page number) is attached by code after the
model returns. The model is never asked to produce a citation locator, because a
model that can invent a page number will eventually invent one.
"""

CATEGORIES = [
    "animals", "body", "people", "nature", "plants", "food", "objects",
    "places", "actions", "religion", "death", "wealth", "relationships",
    "weather", "celestial", "other",
]

VALENCE = ["good", "warning", "neutral", "mixed"]

CONDITION = {
    "type": "object",
    "properties": {
        "if_en": {
            "type": "string",
            "description": "The qualifying circumstance, e.g. 'the snake is inside the house'.",
        },
        "then_en": {
            "type": "string",
            "description": "What the source says that circumstance indicates.",
        },
        "quote_ar": {
            "type": "string",
            "description": (
                "Verbatim Arabic span from the source covering this condition. "
                "Copy exactly; leave empty if no single span covers it."
            ),
        },
    },
    "required": ["if_en", "then_en"],
}

ENTRY = {
    "type": "object",
    "properties": {
        "symbol_ar": {
            "type": "string",
            "description": "The dream symbol in Arabic, as the source names it.",
        },
        "symbol_en": {
            "type": "string",
            "description": "Plain English name of the symbol, lowercase, e.g. 'snake'.",
        },
        "aliases_en": {
            "type": "array",
            "items": {"type": "string"},
            "description": "How an English speaker might describe this: synonyms, plurals, common phrasings.",
        },
        "aliases_ar": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Arabic synonyms and inflected forms.",
        },
        "category": {"type": "string", "enum": CATEGORIES},
        "quote_ar": {
            "type": "string",
            "description": (
                "VERBATIM contiguous Arabic text copied character-for-character from "
                "the source passage supplied to you. Do not paraphrase, reorder, "
                "summarise, correct spelling, or add or remove diacritics. This is "
                "checked automatically against the source and the entry is discarded "
                "if it does not match."
            ),
        },
        "quote_en": {
            "type": "string",
            "description": "Faithful English translation of quote_ar. Translate what is there, including anything unflattering or strange.",
        },
        "meaning_summary": {
            "type": "string",
            "description": "One or two sentences: what this symbol indicates according to THIS passage only.",
        },
        "conditions": {"type": "array", "items": CONDITION},
        "valence": {"type": "string", "enum": VALENCE},
        "notes": {
            "type": "string",
            "description": (
                "Flag anything a reviewing scholar must see: unclear wording, a "
                "corrupt passage, a claim that conflicts with mainstream teaching, "
                "or content that should not be shown to users."
            ),
        },
    },
    "required": [
        "symbol_ar", "symbol_en", "category", "quote_ar", "quote_en",
        "meaning_summary", "valence",
    ],
}

RESPONSE = {
    "type": "object",
    "properties": {"entries": {"type": "array", "items": ENTRY}},
    "required": ["entries"],
}
