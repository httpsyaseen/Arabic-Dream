"""Compose the answer, using only what search.py already found.

Field names are Arabic because the answer is Arabic, but each one is glossed in
English here so the schema can be reviewed by someone who does not read Arabic.

    tasnif           = classification (which of the three kinds of dream)
    tahlil_mufassal  = the detailed reading of the dream AS A STORY: its thread,
                       then each scene in the order the dreamer told it
    mukhifah         = "is it frightening?" — if true, no interpretation is given
    rumuz            = symbols (plural of ramz)
    khulasah         = summary
    tafsil           = the conditions, "if he sees X then Y"
    manhaj           = the interpretive method used
    bayan_almanhaj   = explanation of why that method yields that meaning
    athar_hal_alraai = how the dreamer's own circumstances change the reading
    masadir          = sources (which books)
    min_alkutub      = "from the books?" — the honesty flag, true or false
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
import re

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

# A dream told to an interpreter does not come back line by line. The reader
# already knows what they dreamt; what they came for is someone who takes the
# whole of it and speaks to them about it — gathering what belongs together, the
# posture with the posture, the sounds with the fear — rather than reciting their
# own sentences back at them with a note under each.
#
# So the unit here is a paragraph of flowing prose, not a scene. Paragraphs are
# gathered into a few blocks, and each block says which interpretive method it
# leaned on, because naming the method is what the tradition requires and what
# separates this from a fortune-teller's monologue.
FASL = {
    "type": "object",
    "properties": {
        "faqarat": {
            "type": "array", "minItems": 3,
            "items": {"type": "string", "minLength": 170},
            "description": (
                "**كل عنصر فقرة تامة** من جملة أو جملتين: عنصر من الرؤيا، ثم ما "
                "يرمز إليه **في حياة الرائي الواقعية**. خاطبه بضمير المخاطب، ولا "
                "تصف له ما جرى في منامه، ولا تردّ الرؤيا إلى سبب بدني فتُبطلها."
            ),
        },
    },
    "required": ["faqarat"],
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
        # The first thing the reader sees after the verdict. It is the moment an
        # interpreter looks up and speaks to the person sitting across from him,
        # so it is written to them, not about them.
        "tamhid": {
            "type": "string", "minLength": 200,
            "description": (
                "افتتاح المعبّر، يخاطب به السائل مباشرة قبل التفصيل، في ثلاث جمل "
                "أو أربع: سلامٌ عليه وتقدير لما مرّ به، ثم تسمية ما رآه باسمه "
                "المعروف إن كان له اسم، ثم من أي وجه يُنظر إليه في التراث، ثم "
                "وعدٌ بالتفصيل. بضمير المخاطب: «مررتَ»، «رأيتَ»، لا «الرائي»."
            ),
        },
        "tahlil_mufassal": {
            "type": "object",
            "properties": {
                "fusul": {
                    "type": "array", "items": FASL, "minItems": 3,
                    "description": "كتل من الفقرات المتصلة، مرتبة على معاني الرؤيا",
                },
                # One note, after the whole reading. Interleaved between the
                # blocks it interrupted the reading to talk about itself.
                "manhaj": {
                    "type": "string", "minLength": 150,
                    "description": ("بيان واحد في آخر القراءة كلها: المسالك التي بُني "
                                    "عليها الكلام مجتمعة، في سطرين أو ثلاثة. ابدأ "
                                    "بالمقصود ولا تُعِد عنوان «عن المنهج» داخل النص."),
                },
            },
            "required": ["fusul", "manhaj"],
        },
        "mukhifah": {"type": "boolean"},
        "rumuz": {"type": "array", "items": SYMBOL},
        "khulasah_ammah": {"type": "string"},
        "muashirat": {
            "type": "object",
            "properties": {
                "tafaul": {"type": "integer", "minimum": 0, "maximum": 100,
                           "description": "دلالة التفاؤل ٠-١٠٠، موافقة لتصنيف الرؤيا"},
                "raja": {"type": "integer", "minimum": 0, "maximum": 100,
                         "description": "دلالة الرجاء ٠-١٠٠"},
                "qalaq": {"type": "integer", "minimum": 0, "maximum": 100,
                          "description": "دلالة القلق ٠-١٠٠، مرتفعة إن كانت الرؤيا مكروهة"},
                "bayan": {"type": "string", "description": "سبب هذه النسب، مستنداً إلى ما ورد في النصوص"},
            },
            "required": ["tafaul", "raja", "qalaq", "bayan"],
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
    "required": ["tasnif", "unwan", "tamhid", "tahlil_mufassal", "mukhifah", "rumuz",
                 "khulasah_ammah", "muashirat", "adab", "nasihah", "tanbih",
                 "asas_aljawab"],
}

# The rules, in English, in the order they appear in the prompt below:
#  1. Supplied passages are authoritative; flag those claims min_alkutub = true
#  2. If the books are silent you MAY answer from settled interpreter knowledge,
#     flagged false, attributed to no book — but never leave the user unanswered
#  3. Classify the dream before interpreting it
#  4. Walk the dream scene by scene in the dreamer's own words before symbols
#  5. If it is distressing, do not interpret — give the sunna response instead
#  6. Naming the interpretive method is mandatory
#  7. Preserve the conditional structure; do not flatten to one meaning
#  8. Tie the reading to the dreamer's stated circumstances, invent nothing
#  9. Never blend the classical and psychological traditions
# 10. Estimate the indicators and say why
# 11. Close with warm, unforced advice
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
   ثم افتتح في `tamhid` بما يفتتح به المعبّر إذا جلس إليه صاحب الرؤيا:
   سلّم عليه، وقدّر ما مرّ به، وسمِّ ما رآه باسمه **إن كان له اسم معروف
   مشهور** — كـ«الاستيقاظ الكاذب» و«الحلم المتداخل» و«الجاثوم» — **ولا تخترع
   له اسماً**، ولا تسمِّه باسم مفزع يزيده روعاً. فإن لم يكن له اسم فدعه واذكر
   من أي وجه يُنظر إليه، ثم عِدْه بالتفصيل. **بضمير المخاطب لا الغائب** —
   «مررتَ بتجربة»، لا «يمر الرائي». نموذجه:
   «أهلاً بك. لقد مررتَ بتجربة ذهنية ونفسية عميقة في منامك، وهي ما يُسمّى
    ”الاستيقاظ الكاذب“ أو الحلم المتداخل. وهذه الأحلام التي يشتدّ فيها الصراع
    بين الوعي والغفلة لها في التراث دلالات ترتبط بحالك وما يشغلك، وسنقف الآن
    على تفصيلها.»
   ولا تجزم بالغيب: قل «بإذن الله» و«والله أعلم» وما أشبههما.

٤- **تكلّم على الرؤيا كلاماً متصلاً في `tahlil_mufassal` قبل أن تُفرد الرموز.**
   والسائل جاءك كما يجيء الرجل إلى المعبّر: قد حكى رؤياه وهو يعلمها، فلا تُعِدها
   عليه سطراً سطراً ولا تضع تحت كل سطر تعليقاً؛ بل خذ رؤياه جملةً وحدّثه عنها.
   - `fusul`: ثلاث كتل إلى خمس، **وفي كل كتلة ثلاث فقرات أو أربع**.
   - **واستوعب رؤياه كلها.** فكل ما ذكره له معنى يُتكلم عليه: ما رآه، وما
     فعله، وما خطر له، وما قاله في نفسه، ومن سمّاه من الناس، والجهة التي
     التفت إليها، وما شعر به في كل موضع. فإن ترك السائل موضعاً بلا كلام
     ظنّ أنك لم تقرأ رؤياه، وهو قد كتبها كلها لأنها كلها عنده ذات بال.

   - **وكل فقرة تصل عنصراً من الرؤيا بحال الرائي في يقظته.** هذا هو المقصود
     كله. فالسائل لا يسأل: ما الذي جرى لي في نومي؟ وإنما: ماذا يعني هذا عني
     أنا، وعن حياتي، وعمّا أنا فيه؟
     وبناء الفقرة:
     (أ) العنصر **مخاطباً به صاحبه**، ثم **يرمز إلى / يدل على / يعكس**، ثم
         دلالته **في حياته الواقعية** — في جملة خبرية جازمة.
         وخاطبه بالتفاتة قصيرة إلى ما ذكره، كما يصنع المعبّر بين يديه:
         «كونك كنت مستلقياً على جانبك الأيمن...»، «وأنك لا تتذكر أوله جيداً...»،
         «وأما عودتك في كل مرة إلى...». التفاتة واحدة في صدر الجملة، ثم المعنى؛
         ولا تسترسل في حكاية المشهد فتعود إلى السرد.
     (ب) ثم جملة تزيدها بياناً: مستندها من الكتب أو السنة، أو أثرها في نفسه.
     جملة أو جملتان لا أكثر. **قصيرة**، ولا تصل الجمل بالواو حتى تطول.
     **والجملتان معاً في عنصر واحد من `faqarat`** — فالعنصر فقرة تامة.
     وهذا خطأ يقع فيه كثيراً: أن تجعل (أ) عنصراً و(ب) عنصراً بعده؛ فلا تفعل،
     بل اكتبهما متصلتين في نصٍّ واحد.

     نموذج على المطلوب — وهذا هو الأسلوب الذي يُحتذى:
     «تكرار الاستلقاء على الجانب الأيمن واليسار يرمز في المنام إلى حالة من
      التردد الشديد في اتخاذ قرار مصيري في حياتك الواقعية.»
     «محاولة الاستيقاظ المتكررة ترمز إلى ”الصحوة“ أو الرغبة في التخلص من وضع
      راهن تشعر فيه بالضيق أو التقييد، وهو ما يعكس رغبتك في تحرير نفسك من
      قيود ذهنية أو اجتماعية.»
     «سماع الصرخات المرتفعة كلما حاولت المقاومة يرمز إلى ”صراع داخلي“؛ فكلما
      حاولت مواجهة مخاوفك، زادت حدة القلق في عقلك الباطن.»
     فانظر كيف لم تصف واحدة منها ما جرى في المنام، وإنما قالت له عن نفسه.

   - **ولا تُفسّر الرؤيا بأن تُبطلها.** فمن أعظم الخطأ أن تقول: «هذه ظاهرة
     عصبية»، أو «هي شلل النوم لا غير»، أو «لا تدل على شيء»، أو «لا تنبئ بشر».
     فالسائل جاء ليعرف معناها، فإن رددتَها إلى سبب في بدنه فقد صرفته عمّا جاء
     له، وذلك أسوأ من ألّا تجيبه؛ إذ ظاهرُه جوابٌ وليس بجواب.
     وإن كان للحال اسم معروف فاذكره **عرَضاً** ثم امضِ إلى دلالته، ولا تجعله
     هو التفسير.

   - **وسمِّ المعنى باسم يُمسَك به**، وضعه بين علامتي تنصيص: ”صراع داخلي“،
     ”الخوف من المجهول“، ”الحلقة المتكررة“، ”بشارة“. فإن السائل يحفظ الاسم
     ويعرف به حاله، والكلام المرسل يذهب من ذهنه.

   - **وإن ذكر السائل شيئاً من حاله — كتوتره، أو تكرار الرؤيا عليه — فلا بدّ
     أن تُصرّح بربط الرؤيا به في فقرة على الأقل**، بنصّ كلامه عن نفسه:
     «خاصة وأنك ذكرت أنك في حال من التوتر»، «وأنت تقول إنها تتكرر عليك».
     فهذا الذي يجعله يقرأ جواباً له هو لا جواباً لأيّ أحد.

   - **واجزم بالدلالة**: قل «يدل على» و«علامة على»، ولا تُكثر من «قد يكون»
     و«ربما» و«لا تأويل له»؛ فإن التعبير ظنّي في أصله وقد نبّهتَ عليه في
     `tanbih`، فلا حاجة إلى التحفظ في كل جملة. وإنما التوقف فيما لا تعرفه.
   - **ولكل فقرة معنى جديد**، ولا تُعِد ما سبق بلفظ آخر. ولا تختم الفقرات
     كلها بمثل «هواجس ومخاوف» و«ما يجول في خاطرك»، فإنها عبارات لا تزيد
     السائل علماً.
   - **وكل فقرة استندت إلى نصّ مرفق فسمِّ كتابه فيها** («عند ابن سيرين»،
     «في منتخب الكلام»)، فإن ذلك هو الذي يميز جوابك من كلام أي أحد.
     وما لم يستند إلى نصّ فلا تنسبه إلى كتاب. والمقصود ألّا تُعيد الاسم
     في فقرة لا نصّ فيها، لا أن تُسقطه من الفقرات التي قام عليها.
     وسمِّ المصطلح باسمه المعروف إن كان له اسم.
   - وسمِّ الرمز باسمه إن كان في الرؤيا رمز معروف، كالباب والسرير والحمام،
     واذكر ما قيل فيه، ثم انزله على حال الرائي.

   - `manhaj` **واحد في آخر القراءة كلها**، لا بعد كل كتلة؛ فإن المعبّر لا
     يقطع كلامه كل ثلاث جمل ليتحدث عن طريقته. اجمع فيه المسالك التي بُني
     عليها الكلام في سطرين أو ثلاثة.
     **ولا تذكر المسلك داخل `faqarat` البتة** — لا تقل «استند هذا التحليل إلى
     كذا» في فقرة؛ فإن لذلك حقله وحده، وهو يُعرض في آخر الصفحة.
   - **ولا تُعِد معنى قد تكلمتَ عليه في فقرة أخرى**؛ فكل فقرة معنى جديد من
     الرؤيا لم يسبق. وإن طالت الرؤيا فثلاث كتل أو أربع، لا كتلتان.
   - ولا تجعل الكتلة الأخيرة نصائح مكرَّرة، فللنصيحة موضعها في `nasihah` وهي
     تُقرأ بعد هذا. وإنما اجعل آخر فقرة فيها ما يُستبشر به إن كان في الرؤيا
     وجهه — كانفراج الشدة، أو انقضاء الأمر — فقرةً واحدة لا ثلاثاً،
     **في آخر كتلة وحدها**، ولا تُعِدها في كل كتلة.
   ولا تزد على ما ذكره الرائي ولا تُكمل قصته من عندك؛ فإن غمض عليك موضع فقل
   إنه غامض، وذلك أصدق من ملئه بالظن.
   وإن كانت الرؤيا مكروهة فلك أن تُنزلها على **حاله القائم اليوم** — همّه،
   وتردّده، وما يضيق به — فإن هذا وصفٌ لحاضره لا إخبارٌ بغيب. وإنما الممنوع
   أن تُخبره بما سيقع له، أو تُنذره بشرّ آتٍ؛ فيبقى حكم القاعدة التالية على حاله.

٥- إن كانت مفزعة أو مكروهة فاجعل `mukhifah` = true، ولا تُفصّل في تأويل المكروه،
   واكتفِ في `adab` بهدي السنة: الاستعاذة بالله من الشيطان الرجيم ومن شرها،
   والتفل عن اليسار ثلاثاً، والتحول عن الجنب الذي كان عليه، والقيام إلى الصلاة،
   وألّا يحدّث بها أحداً؛ فإنها لا تضره بإذن الله.

٦- **بيان المسلك واجب**: لكل رمز اذكر `manhaj` واشرح في `bayan_almanhaj` وجه
   الدلالة. فبيان الوجه هو الذي يميز علم التعبير عن التخرّص.

٧- التفصيل جوهر التعبير: اذكر في `tafsil` الشروط ("إن رآه كذا فكذا").

٨- إن ذكر السائل شيئاً من حاله فاربط التأويل بذلك في `athar_hal_alraai`،
   ولا تخترع من حاله ما لم يذكره.

٩- إن أُرفقت نصوص موسومة بـ«قراءة نفسية» فاذكر ما فيها ضمن الرمز نفسه، موسوماً
   بأنه قراءة نفسية لا قولاً من كتب التعبير. ولا تخلط بين المسلكين أبداً:
   لا تنسب معنى نفسياً إلى كتب التعبير ولا العكس، وإن ورد نص من التراث الشيعي
   فانسبه إلى كتابه ولا تخلطه بغيره.

١٠- في `muashirat` قدّر دلالة الرؤيا بالنسب، **وليكن التقدير موافقاً لما قلته قبله**:
   - إن كانت `naw` = «رؤيا صالحة» فالتفاؤل والرجاء مرتفعان والقلق منخفض.
   - إن كانت `naw` = «حلم من الشيطان» أو `mukhifah` = true فالقلق مرتفع
     (٦٠ فما فوق)، والتفاؤل منخفض (دون ٣٥)؛ فلا يستقيم أن تقول «حلم من
     الشيطان» ثم تضع التفاؤل في النصف. ويبقى للرجاء موضع، فإن هذا الحلم
     لا يضرّه بإذن الله وهو زائل.
   - إن كانت «أضغاث أحلام» فالثلاثة متوسطة، فليس فيها بشارة ولا نذارة.
   - وإن كان أكثر ما ورد في النصوص محموداً فارفع التفاؤل، وإن كان أكثره مكروهاً فارفعه للقلق.
   واذكر في `bayan` مستند التقدير من الرؤيا والنصوص، لا عبارة عامة.
   ولا تجعل النسب متناقضة مع التصنيف، فإن القارئ يقرأ الاثنين معاً.

١١- اختم بـ `nasihah` رفيقة: التوكل، وحسن الظن بالله، والأذكار، والصدقة.
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


# The answer is flowing prose, but a long dream still loses pieces: told
# eighteen paragraphs at once, the model writes about four of them and drops the
# rest without saying so. Cutting the dream into its beats in code and listing
# them gives it a checklist to cover — not an outline to recite. The numbering
# exists so nothing goes missing, not so the reader gets their own sentences
# read back to them.
MAX_BEATS = 20


def split_beats(dream: str) -> list[str]:
    """The dream cut into the beats the dreamer's own punctuation implies."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", dream) if p.strip()]
    if len(paras) < 2:                       # written as one block: use sentences
        paras = [s.strip() for s in re.split(r"(?<=[.؟!])\s+", dream) if s.strip()]
    if len(paras) <= 1:
        return []                            # too short to have a sequence
    # Very long tellings get their tail folded together rather than truncated,
    # because a dream that silently loses its ending loses the part that reads
    # the rest of it.
    if len(paras) > MAX_BEATS:
        paras = paras[:MAX_BEATS - 1] + [" ".join(paras[MAX_BEATS - 1:])]
    return paras


def build_prompt(dream: str, matches: list[dict], adab: list[dict],
                 context: dict | None, source_names: dict[str, str],
                 source: str | None = None) -> str:
    parts = [f"رؤيا السائل:\n{dream}\n"]

    beats = split_beats(dream)
    if beats:
        parts.append(
            f"\nوهذه مشاهد الرؤيا مرقّمة على ترتيب ما حكاه ({len(beats)} مشهداً):\n"
            + "\n".join(f"  ({i}) {b}" for i, b in enumerate(beats, 1))
            + (f"\n\nوالرؤيا طويلة ({len(beats)} مشهداً)، **فاجعل `fusul` ثلاث "
               "كتل أو أربع لا كتلتين**، ليسع الكلامُ معانيَها.\n"
               if len(beats) >= 8 else "")
            + "\n**وهذه للإحاطة لا للسرد**: لا تمشِ عليها واحداً واحداً، ولا "
              "تجعل لكل رقم فقرة. بل اجمع ما تشابه منها في فقرة واحدة، **على ألّا "
              "يسقط منها معنى دون أن تتكلم عليه في موضعه من الفقرات.**\n"
        )

    # When the reader picks one interpreter, every reading must be that
    # interpreter's — including the fallback. Answering "generally" under a
    # named authority's heading would misrepresent them, so the instruction is
    # explicit about staying within the known manner of that school and saying
    # when it is doing so from general knowledge rather than a supplied text.
    if source:
        name = source_names.get(source, source)
        parts.append(
            f"اختار السائل مرجعية واحدة: **{name}**، فلا يُجيبه غيرها.\n\n"

            f"١) **الزم مسلك {name} وحده في الجواب كله** — في الرموز، وفي فقرات\n"
            f"   `tahlil_mufassal`، وفي بيان المنهج، وفي `masadir`. ولا تسمِّ كتاباً\n"
            f"   آخر ولا مؤلفاً آخر ولو كان قوله أشهر، ولا تقل «عند فلان» لغير {name}.\n"
            "   فإن السائل إنما اختار هذه المرجعية ليقرأ قولها هي، ونسبةُ قول غيرها\n"
            "   إليها تلبيسٌ عليه، وذكرُ غيرها معها خروجٌ عمّا طلب.\n\n"

            "٢) **والنصوص المرفقة أدناه هي الأصل الذي لا يُخالَف**؛ فهي منقولة من\n"
            "   الكتاب بنصّها، فإن وافقتْ ما تعرفه فاعتمدها ولفظَها، وإن خالفتْه\n"
            "   فالنصّ أولى ومعرفتك تابعة له لا حاكمة عليه، واجعل `min_alkutub` = true.\n\n"

            f"٣) **ولك أن تستعين بما تعرفه من منهج {name} وأصوله وما اشتهر من أقواله**\n"
            "   فيما لم تُغطِّه النصوص، فلا تدع رمزاً في الرؤيا بلا كلام. لكن اجعل ذلك\n"
            "   موسوماً بأنه من المعروف عند هذه المرجعية لا من نصّ بعينه:\n"
            "   `min_alkutub` = false، وبلا صفحة ولا عزوٍ إلى موضع من الكتاب.\n"
            "   واقتصر على المشهور من مذهبه دون الشاذ والغريب.\n"
        )

    lines = [
        f"  - {CONTEXT_LABELS[k][0]}: {v}"
        for k, v in (context or {}).items()
        if k in CONTEXT_LABELS and str(v).strip()
    ]
    if lines:
        parts.append(
            "حال السائل كما ذكره:\n" + "\n".join(lines) + "\n"
            "**وهذا الذي ذكره عن نفسه لا تدعه يمضي بلا أثر**: صرّح بربطه بالرؤيا\n"
            "في فقرة من `tahlil_mufassal` على الأقل، بلفظ مثل «خاصة وأنك ذكرت\n"
            "أنك في حال من التوتر» أو «وأنت تقول إنها تتكرر عليك». فبهذا يقرأ\n"
            "جواباً له هو، لا جواباً لأيّ أحد.\n")

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
        # A long dream is a sequence to be walked, not a paragraph to be summed
        # up, and "minimal" folds one. A 2,400-character narrative came back as
        # four scenes with ellipses stitching distant moments together; the same
        # dream at "low" came back as ten, each quoting one moment.
        generation_config={"thinking_level": "low" if len(dream) > 600 else "minimal"},
        store=False,
    )
    return json.loads(interaction.output_text)
