"""FastAPI app.

    .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 3000

Pure JSON API — it serves no HTML. The frontend in frontend/ is a separate
static page that calls this over HTTP, so either side can be replaced without
touching the other. Interactive docs at /docs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import interpret, meta, symbols

app = FastAPI(
    title="Ta'weel API — تأويل",
    description=(
        "Arabic dream interpretation grounded in classical sources. Symbol lookup "
        "runs in code against an indexed corpus; the model only explains what the "
        "lookup found, and every claim is marked as either cited or not."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

for r in (meta.router, symbols.router, interpret.router):
    app.include_router(r, prefix=config.API_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": "Ta'weel API",
        "docs": "/docs",
        "endpoints": [
            f"{config.API_PREFIX}/health",
            f"{config.API_PREFIX}/sources",
            f"{config.API_PREFIX}/options",
            f"{config.API_PREFIX}/symbols",
            f"{config.API_PREFIX}/symbols/{{key}}",
            f"{config.API_PREFIX}/interpret",
        ],
    }
