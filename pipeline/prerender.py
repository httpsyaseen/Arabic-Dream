"""Generate the readings for a topic page once, so visitors never pay for them.

    python -m pipeline.prerender teeth
    python -m pipeline.prerender teeth --force        # regenerate all
    python -m pipeline.prerender teeth --only 3,7     # just those clusters

The topic pages carry the highest traffic and the least variation: the same
sixteen dreams, asked over and over. Answering each one live spends a model call
per visitor for a reading that does not change between them. Generated once and
served from disk, ten thousand visits to a page cost what one visit costs.

Calls the running API rather than the model directly, so a stored reading is
byte-for-byte what a live one would have been — same retrieval, same prompt, same
coherence pass. Nothing here is a second code path that could drift.

Writes index/pages/<slug>/<query-slug>.json, one per query.
"""

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "index" / "pages"
API = os.getenv("TAWEEL_API", "http://127.0.0.1:3000") + "/api/v1"

PAUSE = 2.0        # between calls, so a free-tier key is not hammered


def slugify(text: str) -> str:
    """A short, stable, URL-safe id from the English title."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)[:48] or "query"


def interpret(dream: str, timeout: int = 240) -> dict | None:
    req = urllib.request.Request(
        f"{API}/interpret",
        data=json.dumps({"dream": dream}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        body = json.load(e)
        # 503 means every model was out of quota. The citations are still there,
        # but a page without a reading is not worth storing as if it were one.
        print(f"    HTTP {e.code}: {body.get('meta', {}).get('error', '')[:90]}")
        return None
    except Exception as e:
        print(f"    {type(e).__name__}: {str(e)[:90]}")
        return None


def build(slug: str, force: bool, only: set[int] | None) -> None:
    source = PAGES / f"{slug}.json"
    if not source.exists():
        raise SystemExit(f"no topic page {slug!r} — run pipeline.cluster_queries first")

    page = json.loads(source.read_text(encoding="utf-8"))
    clusters = page["clusters"]
    out_dir = PAGES / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    index = []
    done = skipped = failed = 0

    for i, c in enumerate(clusters, 1):
        qslug = slugify(c["title"]["en"])
        dest = out_dir / f"{qslug}.json"
        entry = {
            "slug": qslug,
            "title": c["title"],
            "dream": c["dream_ar"],
        }

        if only and i not in only:
            if dest.exists():
                index.append(entry)
            continue

        if dest.exists() and not force:
            print(f"  {i:>2}/{len(clusters)}  {qslug:<40} cached")
            index.append(entry)
            skipped += 1
            continue

        print(f"  {i:>2}/{len(clusters)}  {qslug:<40} generating…", flush=True)
        result = interpret(c["dream_ar"])
        if not result or not result.get("answer"):
            failed += 1
            continue

        dest.write_text(json.dumps({
            **entry,
            "generated_at": int(time.time()),
            "answer": result["answer"],
            "symbols": result.get("symbols", []),
            "adab_sources": result.get("adab_sources", []),
            "meta": result.get("meta", {}),
        }, ensure_ascii=False, indent=1), encoding="utf-8")

        naw = result["answer"].get("tasnif", {}).get("naw", "?")
        cites = sum(len(s["citations"]) for s in result.get("symbols", []))
        print(f"      {naw} · {cites} citations · {result['meta']['elapsed_ms']} ms")
        index.append(entry)
        done += 1
        time.sleep(PAUSE)

    (out_dir / "index.json").write_text(
        json.dumps({"slug": slug, "queries": index}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    print(f"\ngenerated {done} · cached {skipped} · failed {failed}")
    print(f"-> {out_dir}")
    if failed:
        print("rerun to pick the failures up; existing pages are left alone.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pre-generate a topic page's readings")
    ap.add_argument("slug")
    ap.add_argument("--force", action="store_true", help="regenerate even if cached")
    ap.add_argument("--only", help="comma-separated cluster numbers")
    a = ap.parse_args()
    build(a.slug, a.force, {int(x) for x in a.only.split(",")} if a.only else None)
