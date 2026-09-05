"""Settings, all from the environment. See .env.example."""

import os

from dotenv import load_dotenv

load_dotenv()

API_PREFIX = "/api/v1"

# Free-tier quota is metered per model, not per key: one model can be exhausted
# while another still answers. So the server falls through this list rather than
# failing, and reports which model actually produced the answer.
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

# The frontend is a separate app, possibly on another origin. "*" is fine while
# the API is read-only and unauthenticated; narrow it once accounts exist.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

HAS_KEY = bool(os.getenv("GEMINI_API_KEY"))
