"""Turn matched corpus entries into an interpretation.

The model's only job here is to explain: the symbols come from the index, and
the classical text comes from the corpus. It is told not to add symbols the
lookup did not find, so an interpretation cannot drift into material that is not
in the book.

Two rules come from the tradition rather than from product design:

  * dreams are classified first (ru'ya / hulm / adghath ahlam), because the
    tradition does not treat every dream as interpretable, and
  * a distressing dream gets the sunnah response — seek refuge, spit to the left,
    turn over, do not relate it — instead of an interpretation.

Both are the reason to trust this over a generic chatbot, so they are enforced in
the prompt rather than left to the model's judgement.
"""

import json
import os

from google import genai

SYSTEM = """\
أنت مساعد لعرض ما ورد في كتب تعبير الرؤيا الكلاسيكية. لست مفتياً ولا معبّراً،
ولا تدّعي علم الغيب.

قواعد ملزمة:

١- اعتمد حصراً على النصوص المرفقة من الكتاب. لا تضف رمزاً لم يرد فيها، ولا تستعن
   بمعلوماتك الخاصة عن ابن سيرين أو النابلسي أو غيرهما. إن لم تكفِ النصوص، قل ذلك
   صراحة.

٢- صنّف الرؤيا أولاً إلى واحد من ثلاثة، كما في الحديث:
   - رؤيا صالحة (بشرى من الله)
   - حلم من الشيطان (تخويف وتحزين)
   - أضغاث أحلام (حديث نفس ومما يشغل الذهن)
   واذكر أن التصنيف اجتهاد ظني لا قطع فيه.

٣- إن كانت الرؤيا مفزعة أو مكروهة، فلا تفسّرها. اذكر بدلاً من ذلك هدي السنة:
   الاستعاذة بالله من الشيطان الرجيم ومن شرها، والتفل عن اليسار ثلاثاً، وتحوّل
   الجنب الذي كان عليه، وألّا يحدّث بها أحداً، فإنها لا تضره.

٤- لكل رمز: اذكر ما ورد في النص، ثم اذكر الشروط والتفصيلات إن وجدت
   ("إن رآه كذا فكذا")، فإن التفصيل هو جوهر علم التعبير.
   وقد يرد للرمز الواحد نصوص من أكثر من كتاب؛ فانسب كل قول إلى كتابه،
   وإن اختلفت الكتب فاذكر الاختلاف ولا تُرجّح.

٥- اختم بتذكير موجز: أن التعبير ظنّي، وأنه يختلف باختلاف حال الرائي، وأن المرجع
   في ذلك أهل العلم.

الأسلوب: عربية فصيحة واضحة، موجزة، بلا مبالغة ولا جزم بالغيب.
"""


def build_prompt(dream: str, matches: list[dict]) -> str:
    if not matches:
        return (
            f"رؤيا السائل:\n{dream}\n\n"
            "لم يُعثر على أي رمز من رموز هذه الرؤيا في الكتاب المتاح. "
            "أخبر السائل بذلك بوضوح، وصنّف الرؤيا إن أمكن، ولا تفسّر شيئاً من عندك."
        )

    blocks = []
    for m in matches:
        src = m["source"]
        block = [
            f"الرمز: {m['symbol_ar']}",
            f"[{src['book_ar']} — {src['author']}، ص {src.get('printed_page')}]",
            m["body_ar"],
        ]
        # Supporting passages from the other two books, so the reading rests on
        # more than one lens where the corpus actually supports it.
        for p in m.get("passages") or []:
            block.append(
                f"\n[{p['book_ar']} — {p['author']}، ص {p.get('printed_page')}]\n"
                f"{p['text_ar']}"
            )
        blocks.append("\n".join(block))

    return (
        f"رؤيا السائل:\n{dream}\n\n"
        f"الرموز التي عُثر عليها في الكتاب ({len(matches)}):\n\n"
        + "\n\n---\n\n".join(blocks)
        + "\n\nاشرح للسائل معنى رؤياه اعتماداً على هذه النصوص وحدها."
    )


def client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=key)


def interpret(dream: str, matches: list[dict], model: str, cli=None) -> str:
    cli = cli or client()
    interaction = cli.interactions.create(
        model=model,
        input=build_prompt(dream, matches),
        system_instruction=SYSTEM,
        generation_config={"thinking_level": "low"},
        store=False,
    )
    return interaction.output_text or ""
