"""Compose the answer shown to the user.

Four things distinguish this from a chatbot wrapper:

  * **The corpus decides the symbols.** Lookup happens in code, so the model can
    only speak about entries actually found in the books, and every ruling shown
    has a book, an author and a printed page behind it.
  * **A miss is answered, not swallowed.** When the books contain nothing, the
    answer is still given — from what is settled among the interpreters — but
    labelled, so the reader always knows which of the two they are reading.
  * **The tradition's own rules are enforced.** Dreams are classified before they
    are interpreted, and a distressing dream gets the sunnah response rather than
    an interpretation.
  * **The method is shown, not just the verdict.** Classical ta'bir reasons by
    identifiable principles — a Qur'anic or hadith echo, the derivation of the
    word, interpretation by opposite, the dreamer's own circumstance. Naming the
    principle is what separates this from a horoscope, so it is a required field.

The dreamer's circumstances matter because the books themselves make them matter:
the same symbol is read differently for a man and a woman, the married and the
unmarried, the sick and the healthy. Context is passed through when given.
"""

import json
import os

from google import genai

# ---------------------------------------------------------------- schema

MANHAJ = [
    "أصل قرآني", "أصل من السنة", "اشتقاق اللفظ ومعناه", "التأويل بالمقابلة والضد",
    "قياس على نظير", "العرف والعادة", "حال الرائي وقرائن الرؤيا",
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
                     "description": "اسم المسلك أو الكتاب: كمسلك ابن سيرين، أو النابلسي، أو ابن شاهين، أو القراءة النفسية"},
        "nass": {"type": "string", "description": "قراءة الرؤيا على هذا المسلك"},
        "min_alkutub": {"type": "boolean"},
    },
    "required": ["almanhaj", "nass", "min_alkutub"],
}

ANSWER = {
    "type": "object",
    "properties": {
        "tasnif": {
            "type": "object",
            "properties": {
                "naw": {"type": "string",
                        "enum": ["رؤيا صالحة", "حلم من الشيطان", "أضغاث أحلام", "غير محدد"]},
                "sabab": {"type": "string"},
            },
            "required": ["naw", "sabab"],
        },
        "mukhifah": {"type": "boolean",
                     "description": "هل الرؤيا مفزعة أو مكروهة؟ فلا تُفصَّل، ويُكتفى بهدي السنة"},
        "rumuz": {"type": "array", "items": SYMBOL},
        "qiraat": {"type": "array", "items": QIRAAH,
                   "description": "قراءات الرؤيا على مسالك مختلفة، ومنها قراءة نفسية إن ناسبت"},
        "khulasah_ammah": {"type": "string", "description": "قراءة عامة تجمع الرموز، بلا جزم"},
        "muashirat": {
            "type": "object",
            "properties": {
                "tafaul": {"type": "integer", "description": "دلالة التفاؤل ٠-١٠٠"},
                "raja": {"type": "integer", "description": "دلالة الرجاء ٠-١٠٠"},
                "qalaq": {"type": "integer", "description": "دلالة القلق ٠-١٠٠"},
                "bayan": {"type": "string", "description": "سبب هذه النسب في سطر"},
            },
            "required": ["tafaul", "raja", "qalaq"],
        },
        "adab": {"type": "array", "items": {"type": "string"},
                 "description": "ما ينبغي فعله من هدي السنة بحسب نوع الرؤيا"},
        "dua": {"type": "string", "description": "دعاء مأثور مناسب"},
        "nasihah": {"type": "string",
                    "description": "نصيحة ختامية للسائل: توكل، وأذكار، وصدقة، وحسن ظن بالله، بأسلوب رفيق"},
        "tanbih": {"type": "string", "description": "تنبيه على ظنية التعبير واختلافه بحال الرائي"},
        "asas_aljawab": {
            "type": "string",
            "enum": ["من الكتب المفهرسة", "من المعرفة العامة", "من الاثنين"],
        },
    },
    "required": ["tasnif", "mukhifah", "rumuz", "khulasah_ammah", "muashirat",
                 "adab", "nasihah", "tanbih", "asas_aljawab"],
}

# ---------------------------------------------------------------- prompts

SYSTEM = """\
أنت عارض لما ورد في كتب تعبير الرؤيا عند المسلمين. لست مفتياً ولا معبّراً معتمداً،
ولا تدّعي علم الغيب، ولا تجزم بشيء من المستقبل.

قواعد ملزمة:

١- إن أُرفقت لك نصوص من الكتب فاجعلها الأصل ولا تخالفها، واجعل `min_alkutub` = true،
   واذكر في `masadir` أسماء الكتب التي ورد فيها القول.

٢- إن لم تُرفق نصوص، أو لم تُغطِّ النصوص رمزاً ظاهراً في الرؤيا، فاذكر ما استقرّ عند
   أهل التعبير، بشرط: `min_alkutub` = false، وألّا تخترع نصاً ولا تنسب قولاً إلى
   كتاب أو صفحة بعينها، وأن تقتصر على المشهور دون الشاذ.
   **ولا تترك السائل بلا جواب أبداً.** تركه بلا شيء أسوأ من جواب مُبيَّن أساسه.

٣- صنّف الرؤيا أولاً كما في الحديث: رؤيا صالحة / حلم من الشيطان / أضغاث أحلام.
   والتصنيف اجتهاد ظني لا قطع فيه.

٤- إن كانت مفزعة أو مكروهة فاجعل `mukhifah` = true، ولا تُفصّل في تأويل المكروه،
   واكتفِ في `adab` بهدي السنة: الاستعاذة بالله من الشيطان الرجيم ومن شرها،
   والتفل عن اليسار ثلاثاً، والتحول عن الجنب الذي كان عليه، والقيام إلى الصلاة،
   وألّا يحدّث بها أحداً؛ فإنها لا تضره بإذن الله.

٥- **بيان المسلك واجب**: لكل رمز اذكر في `manhaj` المسلك الذي بُني عليه التأويل،
   واشرح في `bayan_almanhaj` وجه الدلالة؛ كأن يكون التأويل مأخوذاً من آية أو حديث،
   أو من اشتقاق اللفظ، أو بالمقابلة والضد، أو قياساً على نظير، أو من العرف.
   فبيان الوجه هو الذي يميز علم التعبير عن التخرّص.

٦- التفصيل جوهر التعبير: اذكر في `tafsil` الشروط ("إن رآه كذا فكذا") ولا تكتفِ بمعنى عام.

٧- إن ذكر السائل شيئاً من حاله (ذكر أو أنثى، متزوج أو أعزب، سنّه، حاله النفسية،
   وجود ألم في الرؤيا، تكرارها) فاربط التأويل بذلك في `athar_hal_alraai`، فإن
   الكتب نفسها تفرّق بين الرجل والمرأة والمتزوج والأعزب والمريض والصحيح.
   ولا تخترع من حاله ما لم يذكره.

٨- في `qiraat` اعرض الرؤيا على أكثر من مسلك: مسلك ابن سيرين، والنابلسي،
   وابن شاهين، وكتاب تعبير الرؤيا — كلٌّ بما ورد عنه في النصوص.
   وأفرد قراءة نفسية مستقلة.
   وإن أُرفقت نصوص موسومة بـ«قراءة نفسية» فاعتمدها في القراءة النفسية،
   واذكر كتابها وصاحبها في `almanhaj`، واجعل `min_alkutub` = true لها.
   ولا تخلط بين المسلكين أبداً: لا تنسب معنى نفسياً إلى كتب التعبير،
   ولا تنسب معنى من كتب التعبير إلى علم النفس.
   وإن لم تُرفق نصوص نفسية فاجعل `min_alkutub` = false للقراءة النفسية.

٩- في `muashirat` قدّر دلالة الرؤيا بالنسب، مع بيان موجز لسبب التقدير.

١٠- اختم بـ `nasihah` رفيقة: التوكل على الله، وحسن الظن به، وأذكار الصباح والمساء،
   والصدقة، وأن ما قدّره الله خير. بأسلوب أخوي دافئ بلا تهويل ولا وعظ ثقيل.

الأسلوب: عربية فصيحة سهلة، موجزة، بلا سجع ولا مبالغة.
"""

CONTEXT_LABELS = {
    "jins": "الجنس",
    "hala": "الحالة الاجتماعية",
    "umr": "الفئة العمرية",
    "shuur": "الحال النفسية في اليقظة",
    "alam": "هل كان في الرؤيا ألم أو أذى",
    "takrar": "هل تتكرر الرؤيا",
    "waqt": "وقت الرؤيا",
}


def _context_block(context: dict | None) -> str:
    if not context:
        return ""
    lines = [
        f"  - {CONTEXT_LABELS[k]}: {v}"
        for k, v in (context or {}).items()
        if k in CONTEXT_LABELS and str(v).strip()
    ]
    if not lines:
        return ""
    return "\nحال السائل كما ذكره:\n" + "\n".join(lines) + "\n"


def build_prompt(dream: str, matches: list[dict], adab: list[dict],
                 context: dict | None = None) -> str:
    parts = [f"رؤيا السائل:\n{dream}\n", _context_block(context)]

    if matches:
        parts.append(f"\nالنصوص الموجودة في الكتب المفهرسة ({len(matches)} رمزاً):\n")
        for m in matches:
            src = m["source"]
            block = [
                f"■ الرمز: {m['symbol_ar']}",
                f"  [{src['book_ar']} — {src['author']}، ص {src.get('printed_page')}]",
                f"  {m['body_ar']}",
            ]
            for p in m.get("passages") or []:
                kind = "قراءة نفسية" if p.get("lens") == "psych" else "من كتب التعبير"
                page = f"، ص {p['printed_page']}" if p.get("printed_page") else ""
                block.append(
                    f"  [{kind} — {p['book_ar']} — {p['author']}{page}]\n"
                    f"  {p['text_ar']}"
                )
            parts.append("\n".join(block))
    else:
        parts.append(
            "\nلم يُعثر على أي رمز من رموز هذه الرؤيا في الكتب المفهرسة.\n"
            "فأجب السائل مما استقرّ عند أهل التعبير، واجعل `asas_aljawab` = "
            "«من المعرفة العامة» و`min_alkutub` = false في كل رمز، ولا تنسب شيئاً "
            "إلى كتاب بعينه، ولا تدع السائل بغير جواب."
        )

    if adab:
        parts.append("\nنصوص في آداب الرؤيا وأنواعها (للاستئناس في التصنيف والآداب):\n")
        for a in adab:
            parts.append(f"  [{a['book_ar']}] {a['text_ar']}")

    parts.append(
        "\nأجب السائل عن رؤياه إجابة كاملة نافعة، مع بيان مسلك التأويل في كل رمز، "
        "وربط ذلك بحاله إن ذكره."
    )
    return "\n".join(p for p in parts if p)


# ---------------------------------------------------------------- call


def client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=key)


def answer(dream: str, matches: list[dict], adab: list[dict], model: str,
           context: dict | None = None, cli=None) -> dict:
    cli = cli or client()
    interaction = cli.interactions.create(
        model=model,
        input=build_prompt(dream, matches, adab, context),
        system_instruction=SYSTEM,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ANSWER,
        },
        generation_config={"thinking_level": "minimal"},
        store=False,
    )
    return json.loads(interaction.output_text)
