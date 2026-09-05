"""Words a dreamer types, mapped to the headword the books file them under.

Two things no prefix/suffix rule can bridge, and this table exists for both.

**Broken plurals.** English pluralises with a suffix; Arabic often restructures
the word, so the stem itself changes:
    حية (hayya = snake)  ->  حيات (hayyat = snakes)
    ضرس (dirs = molar)   ->  أضراس (adras = molars)

**Conjugated verbs.** People describe dreams with verbs, while the dictionaries
file everything under the verbal noun (the masdar):
    "I fell"  سقطت (saqattu) / وقعت (waqa'tu)  ->  سقوط (suqut = falling)
    "I fly"   أطير (atir)                       ->  طيران (tayaran = flying)

Plus modern words for things the classical books name differently:
    بناية (binaya = building, modern)  ->  بناء (bina', classical)
    أسنان (asnan = teeth)              ->  ضرس (dirs = molar) — al-Nabulsi files
                                          teeth under "molar", and nobody
                                          describing a dream types "molar"

Keys are already normalised (see backend/arabic.py) — no hamza, no ta marbuta.
This table should grow from logs of dreams that matched nothing.
"""

ALIASES: dict[str, str] = {
    # --- teeth ---------------------------------------------------------------
    "اسنان": "ضرس",     # asnan = teeth
    "سن": "ضرس",        # sinn = tooth
    "ضروس": "ضرس",      # durus = molars
    "اضراس": "ضرس",     # adras = molars

    # --- snake ---------------------------------------------------------------
    "حيات": "حيه",      # hayyat = snakes
    "ثعبان": "حيه",     # thu'ban = serpent
    "ثعابين": "حيه",    # tha'abin = serpents
    "افعي": "حيه",      # af'a = viper

    # --- plurals of common nouns --------------------------------------------
    "مياه": "ماء",      # miyah = waters
    "بحار": "بحر",      # bihar = seas
    "بيوت": "بيت",      # buyut = houses
    "شعور": "شعر",      # shu'ur = hair (pl.)
    "اشعار": "شعر",
    "نيران": "نار",     # niran = fires
    "كلاب": "كلب",      # kilab = dogs
    "قطط": "قط",        # qitat = cats
    "اسماك": "سمك",     # asmak = fish (pl.)
    "طيور": "طير",      # tuyur = birds
    "خيول": "فرس",      # khuyul = horses
    "احصنه": "فرس",     # ahsina = horses
    "حصان": "فرس",      # hisan = horse
    "دماء": "دم",       # dima' = blood (pl.)
    "امطار": "مطر",     # amtar = rains
    "جبال": "جبل",      # jibal = mountains
    "ابواب": "باب",     # abwab = doors
    "اموات": "موت",     # amwat = the dead
    "موتي": "موت",
    "ميت": "موت",       # mayyit = a dead person
    "متوفي": "موت",     # mutawaffa = deceased
    "نقود": "دراهم",    # nuqud = money
    "فلوس": "دراهم",    # fulus = money (colloquial)
    "اطفال": "ولد",     # atfal = children
    "اولاد": "ولد",     # awlad = children
    "طفل": "ولد",       # tifl = child
    "زواج": "تزويج",    # zawaj = marriage
    "عرس": "عرس",       # 'urs = wedding
    "حامل": "حبل",      # hamil = pregnant

    # --- verbs: "I fell", "I flew", "I drowned" ------------------------------
    "سقطت": "سقوط", "اسقط": "سقوط", "يسقط": "سقوط", "تسقط": "سقوط",
    "سقط": "سقوط", "وقعت": "سقوط", "اقع": "سقوط", "يقع": "سقوط",
    "وقوع": "سقوط", "هويت": "سقوط", "انهار": "سقوط",
    "طرت": "طيران", "اطير": "طيران", "يطير": "طيران", "تطير": "طيران",
    "بكيت": "بكاء", "ابكي": "بكاء", "يبكي": "بكاء", "تبكي": "بكاء",
    "غرقت": "غرق", "اغرق": "غرق", "يغرق": "غرق",
    "هربت": "هرب", "اهرب": "هرب", "يطاردني": "هرب", "يلاحقني": "هرب",
    "مت": "موت", "اموت": "موت", "يموت": "موت", "توفي": "موت",
    "تزوجت": "تزويج", "اتزوج": "تزويج",
    "صليت": "صلاه", "اصلي": "صلاه",
    "اكلت": "اكل", "شربت": "شرب", "ضحكت": "ضحك", "صرخت": "صياح",
    "احترق": "حريق", "احترقت": "حريق", "اشتعل": "نار",
    "ولدت": "ولاده", "حلقت": "حلق", "ضاع": "ضياع", "ضعت": "ضياع",

    # --- modern words for classical entries ----------------------------------
    "بنايه": "بناء", "عماره": "بناء", "مبني": "بناء", "برج": "بناء",
    "سياره": "مركب",   # sayyara = car -> markab = vehicle/mount
    "طائره": "طيران",  # ta'ira = aeroplane
    "درج": "سلم", "سلالم": "سلم",
}
