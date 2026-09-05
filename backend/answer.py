"""Compose the answer, using only what search.py already found.

Field names are Arabic because the answer is Arabic, but each one is glossed in
English here so the schema can be reviewed by someone who does not read Arabic.

    tasnif           = classification (which of the three kinds of dream)
    mukhifah         = "is it frightening?" — if true, no interpretation is given
    rumuz            = symbols (plural of ramz)
    khulasah         = summary
    tafsil           = the conditions, "if he sees X then Y"
    manhaj           = the interpretive method used
    bayan_almanhaj   = explanation of why that method yields that meaning
    athar_hal_alraai = how the dreamer's own circumstances change the reading
    masadir          = sources (which books)
    min_alkutub      = "from the books?" — the honesty flag, true or false
    qiraat           = readings, one per lens
    muashirat        = indicators (optimism / hope / anxiety)
    adab             = the etiquette response from the sunna
    dua              = a supplication
    nasihah          = closing advice
    tanbih           = the caution that interpretation is probabilistic
    asas_aljawab     = what the answer rests on: the books, general knowledge, or both

`min_alkutub` is the field the whole product rests on. Every claim is stamped
true or false and the interface shows which, so a reader always knows whether
they are looking at a cited ruling or at what is simply settled among
interpreters.
"""

import json
import os

from google import genai

# The seven reasoning principles of classical dream interpretation. Naming which
# one was used is what separates the discipline from fortune-telling, so it is a
# required field rather than an optional flourish.
MANHAJ = [
    "أصل قرآني",                  # grounded in a Qur'anic verse
    "أصل من السنة",               # grounded in a hadith
    "اشتقاق اللفظ ومعناه",         # from the derivation of the word itself
    "التأويل بالمقابلة والضد",     # by opposite: crying means joy
    "قياس على نظير",              # analogy with a comparable case
    "العرف والعادة",              # custom and convention
    "حال الرائي وقرائن الرؤيا",    # the dreamer's circumstances and the dream's signs
]

DREAM_KINDS = [
    "رؤيا صالحة",        # ru'ya saliha  = a true vision, from God
    "حلم من الشيطان",    # hulm          = a bad dream, from Satan
    "أضغاث أحلام",       # adghath ahlam = jumbled dreams, from the mind
    "غير محدد",          # undetermined
]

CONDITION = {
    "type": "object",
    "properties": {
        "halah": {"type": "string", "description": "القيد أو الحالة: إن رآه كذا"},
        "dalalah": {"type": "string", "description": "ما يدل عليه في تلك الحالة"},
    },
    "required": ["halah", "dalalah"],
}

SYMBOL = {
    "type": "object",
    "properties": {
        "ramz": {"type": "string", "description": "اسم الرمز بالعربية"},
        "khulasah": {"type": "string", "description": "خلاصة دلالته في سطر أو سطرين"},
        "tafsil": {"type": "array", "items": CONDITION,
                   "description": "الشروط والتفصيلات؛ وهي جوهر علم التعبير"},
        "manhaj": {"type": "string", "enum": MANHAJ,
                   "description": "المسلك الذي بُني عليه هذا التأويل"},
        "bayan_almanhaj": {"type": "string",
                           "description": "شرح موجز: لماذا دلّ هذا الرمز على ذلك المعنى بهذا المسلك"},
        "athar_hal_alraai": {"type": "string",
                             "description": "كيف يتغير المعنى بحسب ما ذكره السائل عن حاله؛ اتركه فارغاً إن لم يذكر شيئاً"},
        "masadir": {"type": "array", "items": {"type": "string"},
                    "description": "أسماء الكتب التي ورد فيها هذا القول"},
        "min_alkutub": {"type": "boolean",
                        "description": "true إن استند إلى النصوص المرفقة، false إن كان من المعروف المستقر"},
    },
    "required": ["ramz", "khulasah", "manhaj", "bayan_almanhaj", "min_alkutub"],
}

QIRAAH = {
    "type": "object",
    "properties": {
        "almanhaj": {"type": "string",
                     "description": "اسم المسلك أو الكتاب الذي بُنيت عليه هذه القراءة"},
        "nass": {"type": "string", "description": "قراءة الرؤيا على هذا المسلك"},
        "min_alkutub": {"type": "boolean"},
    },
    "required": ["almanhaj", "nass", "min_alkutub"],
}

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "tasnif": {
            "type": "object",
            "properties": {
                "naw": {"type": "string", "enum": DREAM_KINDS},
                "sabab": {"type": "string"},
            },
            "required": ["naw", "sabab"],
        },
        # The headline a reader sees first. A bare classification label
        # ("jumbled dreams") tells them nothing; this is the same judgement said
        # as a sentence, which is what someone came to the page for.
        "unwan": {
            "type": "string",
            "description": (
                "حكم مُجمل في جملة واحدة بلغة السائل، لا مصطلحاً مجرداً. "
                "مثال: «رؤيا طيّبة تبشّر بانتقالك إلى حالٍ أفضل، بإذن الله». "
                "ولا تجزم بالغيب، واستعمل مثل «بإذن الله» و«والله أعلم»."
            ),
        },
        "tamhid": {
            "type": "string",
            "description": (
                "سطران أو ثلاثة تحت العنوان: ما الذي اجتمع في هذه الرؤيا من "
                "المعاني، بإيجاز، قبل التفصيل."
            ),
        },
        "mukhifah": {"type": "boolean"},
        "rumuz": {"type": "array", "items": SYMBOL},
        "qiraat": {"type": "array", "items": QIRAAH},
        "khulasah_ammah": {"type": "string"},
        "muashirat": {
            "type": "object",
            "properties": {
                "tafaul": {"type": "integer", "description": "دلالة التفاؤل ٠-١٠٠"},
                "raja": {"type": "integer", "description": "دلالة الرجاء ٠-١٠٠"},
                "qalaq": {"type": "integer", "description": "دلالة القلق ٠-١٠٠"},
                "bayan": {"type": "string"},
            },
            "required": ["tafaul", "raja", "qalaq"],
        },
        "adab": {"type": "array", "items": {"type": "string"}},
        "dua": {"type": "string"},
        "nasihah": {"type": "string"},
        "tanbih": {"type": "string"},
        "asas_aljawab": {
            "type": "string",
            "enum": ["من الكتب المفهرسة", "من المعرفة العامة", "من الاثنين"],
        },
    },
    "required": ["tasnif", "unwan", "tamhid", "mukhifah", "rumuz",
                 "khulasah_ammah", "muashirat", "adab", "nasihah", "tanbih",
                 "asas_aljawab"],
}

# The rules, in English, in the order they appear in the prompt below:
#  1. Supplied passages are authoritative; flag those claims min_alkutub = true
#  2. If the books are silent you MAY answer from settled interpreter knowledge,
#     flagged false, attributed to no book — but never leave the user unanswered
#  3. Classify the dream before interpreting it
#  4. If it is distressing, do not interpret — give the sunna response instead
#  5. Naming the interpretive method is mandatory
#  6. Preserve the conditional structure; do not flatten to one meaning
#  7. Tie the reading to the dreamer's stated circumstances, invent nothing
#  8. Never blend the classical and psychological traditions
#  9. Estimate the indicators and say why
# 10. Close with warm, unforced advice
SYSTEM = """\
أنت عارض لما ورد في كتب تعبير الرؤيا. لست مفتياً ولا معبّراً معتمداً،
ولا تدّعي علم الغيب، ولا تجزم بشيء من المستقبل.

قواعد ملزمة:

١- إن أُرفقت لك نصوص من الكتب فاجعلها الأصل ولا تخالفها، واجعل `min_alkutub` = true،
   واذكر في `masadir` أسماء الكتب التي ورد فيها القول.

٢- إن لم تُرفق نصوص، أو لم تُغطِّ النصوص رمزاً ظاهراً في الرؤيا، فاذكر ما استقرّ عند
   أهل التعبير، بشرط: `min_alkutub` = false، وألّا تخترع نصاً ولا تنسب قولاً إلى
   كتاب أو صفحة بعينها. **ولا تترك السائل بلا جواب أبداً.**

٣- صنّف الرؤيا أولاً: رؤيا صالحة / حلم من الشيطان / أضغاث أحلام. والتصنيف ظنّي.
   ثم اكتب في `unwan` حكماً مُجملاً **في جملة واحدة بلغة السائل**، لا مصطلحاً
   مجرداً؛ فإن السائل جاء ليعرف ماذا تعني رؤياه لا ليقرأ تصنيفاً.
   واكتب في `tamhid` سطرين أو ثلاثة يجمعان ما اجتمع فيها من المعاني.
   ولا تجزم بالغيب: قل «بإذن الله» و«والله أعلم» وما أشبههما.

٤- إن كانت مفزعة أو مكروهة فاجعل `mukhifah` = true، ولا تُفصّل في تأويل المكروه،
   واكتفِ في `adab` بهدي السنة: الاستعاذة بالله من الشيطان الرجيم ومن شرها،
   والتفل عن اليسار ثلاثاً، والتحول عن الجنب الذي كان عليه، والقيام إلى الصلاة،
   وألّا يحدّث بها أحداً؛ فإنها لا تضره بإذن الله.

٥- **بيان المسلك واجب**: لكل رمز اذكر `manhaj` واشرح في `bayan_almanhaj` وجه
   الدلالة. فبيان الوجه هو الذي يميز علم التعبير عن التخرّص.

٦- التفصيل جوهر التعبير: اذكر في `tafsil` الشروط ("إن رآه كذا فكذا").

٧- إن ذكر السائل شيئاً من حاله فاربط التأويل بذلك في `athar_hal_alraai`،
   ولا تخترع من حاله ما لم يذكره.

٨- في `qiraat` اعرض الرؤيا على المسالك التي وردت في النصوص، كلٌّ باسم كتابه.
   وأفرد قراءة نفسية مستقلة. وإن أُرفقت نصوص موسومة بـ«قراءة نفسية» فاعتمدها
   واجعل `min_alkutub` = true لها، وإلا فاجعلها false.
   ولا تخلط بين المسلكين أبداً: لا تنسب معنى نفسياً إلى كتب التعبير ولا العكس.
   وإن ورد نص من التراث الشيعي فانسبه إلى كتابه ولا تخلطه بغيره.

٩- في `muashirat` قدّر دلالة الرؤيا بالنسب مع بيان موجز للسبب.

١٠- اختم بـ `nasihah` رفيقة: التوكل، وحسن الظن بالله، والأذكار، والصدقة.
   بأسلوب أخوي دافئ بلا تهويل.

الأسلوب: عربية فصيحة سهلة، موجزة، بلا سجع ولا مبالغة.
"""

# Labels for the optional questions about the dreamer. The books themselves read
# a symbol differently for a man and a woman, the married and the unmarried, the
# sick and the healthy — so this genuinely changes the reading.
CONTEXT_LABELS = {
    "jins":   ("الجنس", "gender"),
    "hala":   ("الحالة الاجتماعية", "marital status"),
    "umr":    ("الفئة العمرية", "age range"),
    "shuur":  ("الحال النفسية في اليقظة", "waking emotional state"),
    "alam":   ("هل كان في الرؤيا ألم أو أذى", "pain or harm in the dream"),
    "takrar": ("هل تتكرر الرؤيا", "does the dream recur"),
    "waqt":   ("وقت الرؤيا", "time of the dream"),
}


def build_prompt(dream: str, matches: list[dict], adab: list[dict],
                 context: dict | None, source_names: dict[str, str],
                 source: str | None = None) -> str:
    parts = [f"رؤيا السائل:\n{dream}\n"]

    # When the reader picks one interpreter, every reading must be that
    # interpreter's — including the fallback. Answering "generally" under a
    # named authority's heading would misrepresent them, so the instruction is
    # explicit about staying within the known manner of that school and saying
    # when it is doing so from general knowledge rather than a supplied text.
    if source:
        parts.append(
            f"اختار السائل مرجعية واحدة: **{source_names.get(source, source)}**.\n"
            "فاقصر الجواب على مسلك هذه المرجعية وحدها، ولا تخلط معها غيرها،\n"
            "واجعل اسمها في `qiraat[].almanhaj`.\n"
        )

    lines = [
        f"  - {CONTEXT_LABELS[k][0]}: {v}"
        for k, v in (context or {}).items()
        if k in CONTEXT_LABELS and str(v).strip()
    ]
    if lines:
        parts.append("حال السائل كما ذكره:\n" + "\n".join(lines) + "\n")

    if matches:
        parts.append(f"\nالنصوص الموجودة في الكتب المفهرسة ({len(matches)} رمزاً):\n")
        for m in matches:
            block = [f"■ الرمز: {m['symbol_ar']}"]
            if m.get("own_text_applies", True):
                block += [
                    f"  [{source_names.get(m['source'], m['source'])}"
                    + (f"، ص {m['printed_page']}]" if m.get("printed_page") else "]"),
                    f"  {m['text_ar']}",
                ]
            for p in m.get("passages") or []:
                kind = "قراءة نفسية" if p.get("kind") == "psychological" else "من كتب التعبير"
                page = f"، ص {p['printed_page']}" if p.get("printed_page") else ""
                name = source_names.get(p["source"], p["source"])
                block.append(f"  [{kind} — {name}{page}]\n  {p['text_ar']}")
            parts.append("\n".join(block))
    else:
        who = f"على مسلك {source_names.get(source, source)}" if source else "عند أهل التعبير"
        parts.append(
            "\nلم يُعثر على نصّ لهذه الرؤيا في الكتب المفهرسة.\n"
            f"فأجب السائل بما هو معروف مستقر {who}، معتمداً على ما تعرفه من "
            "منهج هذه المرجعية وأصولها، بشرط:\n"
            "  - `asas_aljawab` = «من المعرفة العامة»\n"
            "  - `min_alkutub` = false في كل رمز\n"
            "  - ألّا تخترع نصاً ولا تنسب قولاً إلى كتاب أو صفحة بعينها\n"
            "  - أن تقتصر على المشهور دون الشاذ\n"
            "**ولا تدع السائل بغير جواب.**"
        )

    if adab:
        parts.append("\nنصوص في آداب الرؤيا وأنواعها (للاستئناس في التصنيف والآداب):\n")
        for a in adab:
            parts.append(f"  [{a['text_ar']}]")

    parts.append("\nأجب السائل عن رؤياه إجابة كاملة نافعة، مع بيان مسلك التأويل في كل رمز.")
    return "\n".join(p for p in parts if p)


def client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=key)


def generate(dream: str, matches: list[dict], adab: list[dict], model: str,
             context: dict | None, source_names: dict[str, str],
             source: str | None = None, cli=None) -> dict:
    """One call. `response_mime_type` is deliberately not passed — setting it
    alongside `response_format` is rejected; the mime type belongs inside it."""
    cli = cli or client()
    interaction = cli.interactions.create(
        model=model,
        input=build_prompt(dream, matches, adab, context, source_names, source),
        system_instruction=SYSTEM,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ANSWER_SCHEMA,
        },
        generation_config={"thinking_level": "minimal"},
        store=False,
    )
    return json.loads(interaction.output_text)
