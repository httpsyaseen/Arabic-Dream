"""Group a keyword sheet into semantic clusters for a topic page.

    python -m pipeline.cluster_queries sheets/teeth.csv --slug teeth

The obvious approach is to bucket on substrings — everything containing
"للعزباء" into one group, everything with "بدون ألم" into another. That falls
apart immediately, because the same idea is written many ways: سقوط, وقوع,
تساقط and خلع all describe teeth coming out, and a keyword can belong to two
buckets at once ("teeth falling for a married woman without pain").

So the grouping is done by meaning. The model is shown every keyword and asked
to organise them the way someone looking for their own dream would expect, then
to write, for each cluster, the sentence a person would actually type into the
site — because a search phrase is not a dream. Nobody says "interpretation of
dream of teeth falling for single woman"; they say "I dreamed my teeth fell out
and I am unmarried". The site takes dreams, so what the page offers must be a
dream.

Writes index/pages/<slug>.json, which the API serves and the page renders.
"""

import argparse
import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "index" / "pages"

BATCH = 140       # keywords per call; the model has to see enough to group well

SYSTEM = """\
تنظّم قائمة عبارات بحث عربية عن رؤيا واحدة، لتُعرض في صفحة واحدة على موقع
لتعبير الرؤيا.

اجمع العبارات في مجموعات بحسب **المعنى**، لا بحسب تشابه الألفاظ. فـ«سقوط» و«وقوع»
و«تساقط» و«خلع» كلها تعني خروج السنّ، ويجب أن تكون في مجموعة واحدة إن اتحد المعنى.
واجعل التقسيم على ما يفرّق به الرائي نفسه: حال الرائي (عزباء، متزوجة، حامل، رجل)،
وموضع السنّ (علوي، سفلي، أمامي، ضرس)، وما رافق الرؤيا (ألم، دم، في اليد، أمام
الناس)، وما وقع للسنّ (سقط، خُلع، انكسر، تسوّس، ابيضّ).

لكل مجموعة:
- `title_ar`: عنوان قصير بالعربية.
- `title_en`: ترجمته بالإنجليزية.
- `dream_ar`: **الجملة التي يكتبها صاحب الرؤيا**، لا عبارة البحث. الموقع يستقبل
  رؤى لا كلمات مفتاحية؛ فاكتب ما يقوله الإنسان عن منامه، مثل:
  «حلمت أن أسناني تسقط في يدي ولم أشعر بألم»
  لا «تفسير حلم سقوط الأسنان في اليد بدون ألم».
  اجعلها بصيغة المتكلم، طبيعية، وبين ست وعشرين كلمة.
- `keywords`: أرقام العبارات الداخلة في المجموعة، من القائمة المعطاة.

قواعد:
- كل عبارة تدخل في مجموعة واحدة فقط، وأنسبِها إلى أقرب معنى.
- لا تترك عبارة بلا مجموعة.
- اجعل المجموعات بين ثمانٍ وستّ عشرة، ولا تُنشئ مجموعة لعبارة واحدة إلا إذا تفرّدت
  حقاً بمعناها.
- رتّب المجموعات من الأعمّ إلى الأخصّ.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "clusters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title_ar": {"type": "string"},
                    "title_en": {"type": "string"},
                    "dream_ar": {"type": "string",
                                 "description": "ما يكتبه الرائي عن منامه، لا عبارة بحث"},
                    "keywords": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["title_ar", "title_en", "dream_ar", "keywords"],
            },
        },
    },
    "required": ["clusters"],
}


def read_sheet(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            kw = (r.get("Keyword (Arabic)") or "").strip()
            if not kw:
                continue
            try:
                vol = int(r.get("Volume") or 0)
            except ValueError:
                vol = 0
            rows.append({"keyword": kw, "volume": vol,
                         "english": (r.get("Translation (English) - as provided") or "").strip()})
    rows.sort(key=lambda r: -r["volume"])
    return rows


def client():
    from dotenv import load_dotenv
    from google import genai
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set")
    return genai.Client(api_key=key)


def models() -> list[str]:
    first = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    rest = [m.strip() for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.5-flash,gemini-3.1-flash-lite,gemini-3.6-flash").split(",") if m.strip()]
    return [first] + [m for m in rest if m != first]


def cluster(rows: list[dict]) -> list[dict]:
    cli = client()
    clusters: list[dict] = []

    for start in range(0, len(rows), BATCH):
        chunk = rows[start:start + BATCH]
        listing = "\n".join(
            f"{start + i + 1}. {r['keyword']}  [{r['volume']}]"
            for i, r in enumerate(chunk))
        note = ("" if not clusters else
                "\n\nمجموعات أُنشئت سابقاً — استعمل العنوان نفسه إن كان المعنى واحداً:\n"
                + "\n".join(f"- {c['title_ar']}" for c in clusters))

        for model in models():
            try:
                out = cli.interactions.create(
                    model=model,
                    input=listing + note,
                    system_instruction=SYSTEM,
                    response_format={"type": "text", "mime_type": "application/json",
                                     "schema": SCHEMA},
                    generation_config={"thinking_level": "low"},
                    store=False,
                )
                new = json.loads(out.output_text)["clusters"]
            except Exception:
                continue
            # Merge into an existing cluster when the model reused its title.
            by_title = {c["title_ar"]: c for c in clusters}
            for c in new:
                target = by_title.get(c["title_ar"])
                if target:
                    target["keywords"] += c["keywords"]
                else:
                    clusters.append(c)
                    by_title[c["title_ar"]] = c
            break
        print(f"  {min(start + BATCH, len(rows)):>4}/{len(rows)} keywords grouped "
              f"({len(clusters)} clusters)")
    return clusters


def build(sheet: Path, slug: str) -> dict:
    rows = read_sheet(sheet)
    print(f"{len(rows)} keywords, {sum(r['volume'] for r in rows):,} total volume")
    clusters = cluster(rows)

    out, seen = [], set()
    for c in clusters:
        members = []
        for n in c["keywords"]:
            if 1 <= n <= len(rows) and n not in seen:
                seen.add(n)
                members.append(rows[n - 1])
        if not members:
            continue
        members.sort(key=lambda r: -r["volume"])
        out.append({
            "title": {"ar": c["title_ar"], "en": c["title_en"]},
            "dream_ar": c["dream_ar"],
            "volume": sum(m["volume"] for m in members),
            "queries": [{"ar": m["keyword"], "en": m["english"], "volume": m["volume"]}
                        for m in members],
        })
    out.sort(key=lambda c: -c["volume"])

    ungrouped = [rows[i] for i in range(len(rows)) if i + 1 not in seen]
    payload = {
        "slug": slug,
        "clusters": out,
        "totals": {
            "keywords": len(rows),
            "grouped": len(seen),
            "clusters": len(out),
            "volume": sum(r["volume"] for r in rows),
        },
        # Listed rather than dropped: a keyword nothing covers is a gap, and a
        # silent one is worse than a visible one.
        "ungrouped": [r["keyword"] for r in ungrouped],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{slug}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nclusters {len(out)} · grouped {len(seen)}/{len(rows)} · ungrouped {len(ungrouped)}")
    for c in out:
        print(f"  {c['volume']:>6}  {c['title']['ar']:<34} {len(c['queries']):>3} queries")
        print(f"          → {c['dream_ar']}")
    print(f"\n-> {path}")
    return payload


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Cluster a keyword sheet by meaning")
    ap.add_argument("sheet")
    ap.add_argument("--slug", required=True)
    a = ap.parse_args()
    build(Path(a.sheet), a.slug)
