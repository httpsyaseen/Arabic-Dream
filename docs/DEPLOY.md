# Deploying

Two pieces: a FastAPI process and a folder of static files.

```
nginx ──┬── /            →  frontend/   (static)
        └── /api/        →  127.0.0.1:3000  (uvicorn)
```

## The API

```bash
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 3000
```

Bind to localhost, not `0.0.0.0` — nginx is the only thing that should reach it.
Run it under whatever supervises services on the box so it survives a reboot.

The index is committed, so there is no build step. It loads once at startup
(~150 ms) and is shared by every request.

## The frontend

`frontend/` is plain files. Point nginx at it.

### Caching — the rule that matters

**Never let the browser cache `index.html` or an unversioned script.**

This bit us during development: `python -m http.server` answers conditional
requests with 304 and sends no `Cache-Control`, so a browser kept running a
version of `app.js` from an hour earlier. The visible symptom was a new dream
showing the *previous* dream's answer — the page was executing old code. It
looked like a state bug and was not one.

```nginx
location / {
    root /srv/taweel/frontend;
    try_files $uri $uri/ /index.html;

    # HTML and unhashed assets: always revalidate.
    location ~* \.(html|js|css)$ {
        add_header Cache-Control "no-cache";
    }
}

location /api/ {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # An interpretation can take twenty seconds when the free tier falls
    # through its model list. The default 60s is enough, but do not lower it.
    proxy_read_timeout 120s;
}
```

`no-cache` means "revalidate before using", not "do not store" — the browser
still gets a cheap 304 when nothing changed. Once there is a build step that
puts a hash in the filename, those files can be `immutable` instead and only the
HTML stays `no-cache`.

For local development use `python frontend/serve.py`, which sends `no-store` and
never answers 304, so a reload always runs what is on disk.

## Environment

`.env` beside the repo root, `chmod 600`, never committed:

```
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.1-flash-lite,gemini-3.6-flash
CORS_ORIGINS=https://yourdomain.com
```

Narrow `CORS_ORIGINS` once the frontend has a real domain — `*` is only
reasonable while the API is read-only and unauthenticated.

Free-tier quota is metered **per model**, which is why the fallback list exists.
`python -m pipeline.models` lists what your key can actually reach; availability
differs between keys.

## Checks after deploying

```bash
curl -s https://yourdomain.com/api/v1/health
curl -s -X POST https://yourdomain.com/api/v1/match \
  -H 'Content-Type: application/json' \
  -d '{"dream":"رأيت حية في بيتي"}'
```

`/match` needs no API key and should answer in milliseconds — if it is slow, the
index is being reloaded per request rather than held in memory.

Then open the site, submit a dream, and confirm the citations appear almost
immediately while the reading fills in after. If you instead watch a blank
skeleton for the whole wait, the browser has an old `app.js` and the cache
headers above are not in effect.

## Rebuilding the corpus

Only when sources or matching rules change:

```bash
.venv/bin/python -m pipeline.parse --all      # raw -> chunks
.venv/bin/python -m pipeline.build_index      # chunks -> index
.venv/bin/python -m tests.test_regressions    # 10 known bugs stay fixed
```

Restart the API afterwards; the index is read at startup.
