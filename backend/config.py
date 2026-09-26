"""Settings, all from the environment. See .env.example."""

import os

from dotenv import load_dotenv

load_dotenv()

API_PREFIX = "/api/v1"

# Free-tier quota is metered per model, not per key: one model can be exhausted
# while another still answers. So the server falls through this list rather than
# failing, and reports which model actually produced the answer.
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACKS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.7-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite",
    ).split(",")
    if m.strip()
]
MODELS = [MODEL] + [m for m in FALLBACKS if m != MODEL]

# The frontend is a separate app, possibly on another origin. "*" is fine while
# the API is read-only and unauthenticated; narrow it once accounts exist.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

HAS_KEY = bool(os.getenv("GEMINI_API_KEY"))

# How long one model attempt may run before it is abandoned and the next model
# in the chain is tried. Without a ceiling a single call holds the connection
# for as long as the endpoint feels like — 473 and 530 second calls were
# measured against a congested free tier — and the proxy in front gives up
# first, answering the browser with an HTML error page it cannot parse.
MODEL_TIMEOUT_SECONDS = int(os.getenv("MODEL_TIMEOUT_SECONDS", "45"))

# The budget for the whole request across every model in the chain. When it is
# spent the citations are returned without an interpretation, which is a real
# answer, rather than leaving the caller waiting for one that will not arrive.
# Keep this BELOW nginx's proxy_read_timeout so the backend always wins the
# race and the reader gets JSON instead of the proxy's error page.
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "100"))
