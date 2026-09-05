/* تأويل — Ta'weel front-end.
 *
 * A small hash-routed app over the API. No framework, no build step, so it can
 * be dropped on any static host — and it ports cleanly to Next.js later, where
 * each route below becomes a page and the lens pages become static routes.
 *
 * Routes
 *   #/                    home — write a dream, pick a lens
 *   #/result              the reading (rendered from the last response)
 *   #/interpreters        index of the lenses
 *   #/lens/<slug>         one interpreter: who they are, and a form scoped to them
 *   #/about               where the interpretations come from
 *   #/faq                 common questions
 *   #/journal             locally stored dreams
 *
 * The dream itself is always written in Arabic — the corpus is Arabic and the
 * lookup matches Arabic headwords. Only the interface switches language.
 */

const API_BASE = (() => {
  const q = new URLSearchParams(location.search).get("api");
  if (q) return q.replace(/\/$/, "");
  if (window.API_BASE) return window.API_BASE.replace(/\/$/, "");
  const dev = location.protocol === "file:" || (location.port && location.port !== "3000");
  return dev ? "http://localhost:3000" : "";
})();
const API = API_BASE + "/api/v1";

const $ = s => document.querySelector(s);
const esc = s => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let lang = localStorage.getItem("taweel_lang") || "ar";
let STATE = { stats: null, options: null, sources: [], nonSources: [], last: null };

/* ------------------------------------------------------------------ i18n */
const T = {
  ar: {
    dir: "rtl", brand: "تأويل",
    nav: { home: "الرئيسية", result: "آخر تفسير", interpreters: "المفسّرون", about: "مصادرنا", faq: "الأسئلة الشائعة", journal: "سجل أحلامي" },
    heroH1: "اكتب رؤياك، فيُبحث عن رموزها في كتب أهل التعبير",
    heroSub: "تفسير مبني على نصوص أصلية لا على تخمين — ويُعرض لك ما ورد فيها بنصّه ومصدره وصفحته.",
    symbols: "رمزًا", passages: "نصًا", hadith: "حديثًا في آداب الرؤيا",
    dreamLabel: "رؤياك",
    dreamHint: "اكتب رؤياك بالعربية — البحث يجري في كتب عربية.",
    placeholder: "رأيت في المنام…",
    ctxHead: "حالك (اختياري) — يُغيّر التأويل، فالكتب تفرّق بين الرجل والمرأة والمتزوج والأعزب",
    sourceLabel: "المرجعية",
    sourceAll: "كل المصادر مجتمعة",
    go: "فسّر الرؤيا", clear: "مسح", searching: "يُبحث في الكتب…",
    empty: "اكتب رؤياك أولاً.",
    yourDream: "رؤياك", changeDream: "تعديل الرؤيا",
    tasnif: "تصنيف الرؤيا", basis: "أساس الجواب",
    mukhifah: "رؤيا مكروهة — هدي السنة",
    mukhifahNote: "هذه الرؤيا فيها ما يُكره، ومن هدي النبي ﷺ ألّا تُفسَّر، وأن يفعل الرائي ما يلي.",
    rumuz: "الرموز ودلالاتها", qiraat: "الرؤيا على مسالك أهل التعبير",
    khulasah: "الخلاصة", adab: "آداب الرؤيا", nasihah: "نصيحة",
    nusus: "النصوص الأصلية من الكتب", ahadith: "من أحاديث الرؤيا وآدابها",
    fromBooks: "من الكتب", fromGeneral: "من المعروف المستقر",
    classical: "من كتب التعبير", psych: "قراءة نفسية",
    manhaj: "مسلك التأويل", byState: "بحسب حالك", masadir: "المصادر",
    tafaul: "التفاؤل", raja: "الرجاء", qalaq: "القلق",
    noCorpusNote: "لم يُعثر على نصٍّ لهذه الرؤيا في الكتب المفهرسة، فالجواب مبنيّ على ما استقرّ عند أهل التعبير لا على نصٍّ بعينه.",
    copy: "نسخ", print: "طباعة", save: "حفظ في سجلي", saved: "حُفظت ✓", copied: "نُسخ ✓",
    interpretersH1: "المفسّرون والمراجع",
    interpretersSub: "لكلٍّ مسلكه. اختر مرجعية لتقرأ عنها، أو لتُفسَّر رؤياك على مسلكها وحدها.",
    otherAuthorities: "مرجعيات أخرى",
    notSourceH: "توضيح", readMore: "اقرأ عنه ←",
    interpretWith: "فسّر رؤياك على مسلك", role: "الدور", contributes: "في الفهرس",
    aboutH1: "من أين تأتي تفسيراتنا؟",
    aboutSub: "كل قول تقرؤه هنا إمّا منقول من كتاب بعينه مع صفحته، أو موسوم بأنه من المعروف المستقر لا من نصّ. لا ثالث لهما.",
    faqH1: "أسئلة شائعة",
    journalH1: "سجل أحلامي", journalNote: "محفوظ في متصفحك وحده، لا يُرسل إلى أي خادم.",
    recurring: "رموز تتكرر في رؤاك:", jclear: "حذف السجل", noJournal: "لم تحفظ شيئاً بعد.",
    page: "ص", sourceLink: "المصدر", texts: "نص",
    footer: "هذا عرضٌ لما ورد في كتب التعبير، وليس فتوى ولا حكماً شرعياً ولا علماً بالغيب. التعبير ظنّي يختلف باختلاف حال الرائي، والمرجع في ذلك أهل العلم.",
    kinds: { classical: "من كتب التعبير", psychological: "قراءة نفسية", adab: "آداب وأحاديث" },
    roles: { symbols: "يمدّ الفهرس بالرموز", passages: "يمدّ الفهرس بالنصوص", hadith: "أحاديث الآداب والتصنيف" },
  },
  en: {
    dir: "ltr", brand: "Ta'weel",
    nav: { home: "Home", result: "Last reading", interpreters: "Interpreters", about: "Our sources", faq: "FAQ", journal: "My dreams" },
    heroH1: "Write your dream — its symbols are looked up in the classical books",
    heroSub: "Interpretation built on original texts, not guesswork. You are shown what they say, with the book, the author and the printed page.",
    symbols: "symbols", passages: "passages", hadith: "hadith on dream etiquette",
    dreamLabel: "Your dream",
    dreamHint: "Write your dream in Arabic — the search runs against Arabic books.",
    placeholder: "رأيت في المنام…",
    ctxHead: "About you (optional) — this changes the reading; the books themselves distinguish man from woman, married from unmarried",
    sourceLabel: "Authority",
    sourceAll: "All sources together",
    go: "Interpret", clear: "Clear", searching: "Searching the books…",
    empty: "Write your dream first.",
    yourDream: "Your dream", changeDream: "Edit dream",
    tasnif: "Classification", basis: "Basis of the answer",
    mukhifah: "A distressing dream — the sunna response",
    mukhifahNote: "This dream contains what is disliked. The Prophet ﷺ taught that such a dream is not interpreted; the dreamer does the following instead.",
    rumuz: "Symbols and their meanings", qiraat: "The dream across the interpretive schools",
    khulasah: "Summary", adab: "Etiquette of dreams", nasihah: "Advice",
    nusus: "Original texts from the books", ahadith: "From the hadith on dreams and their etiquette",
    fromBooks: "cited", fromGeneral: "general knowledge",
    classical: "interpretation books", psych: "psychological",
    manhaj: "Method", byState: "For your situation", masadir: "Sources",
    tafaul: "Optimism", raja: "Hope", qalaq: "Anxiety",
    noCorpusNote: "No text for this dream was found in the indexed books, so the answer rests on what is settled among interpreters rather than on a specific passage.",
    copy: "Copy", print: "Print", save: "Save", saved: "Saved ✓", copied: "Copied ✓",
    interpretersH1: "Interpreters and authorities",
    interpretersSub: "Each has its own method. Pick one to read about it, or to have your dream read on its approach alone.",
    otherAuthorities: "Other authorities",
    notSourceH: "Clarification", readMore: "Read more →",
    interpretWith: "Interpret your dream with", role: "Role", contributes: "In the index",
    aboutH1: "Where do our interpretations come from?",
    aboutSub: "Every statement here is either quoted from a named book with its page, or marked as settled interpreter knowledge rather than a text. There is no third category.",
    faqH1: "Frequently asked questions",
    journalH1: "My dreams", journalNote: "Stored in your browser only — never sent to any server.",
    recurring: "Symbols recurring in your dreams:", jclear: "Delete journal", noJournal: "Nothing saved yet.",
    page: "p.", sourceLink: "source", texts: "texts",
    footer: "This presents what the classical books say. It is not a fatwa, not a ruling, and not knowledge of the unseen. Interpretation is probabilistic and varies with the dreamer's situation; qualified scholars are the reference.",
    kinds: { classical: "interpretation books", psychological: "psychological", adab: "etiquette and hadith" },
    roles: { symbols: "supplies the symbol vocabulary", passages: "supplies supporting passages", hadith: "hadith for etiquette and classification" },
  },
};
const t = () => T[lang];

/* ------------------------------------------------------------------ boot */
async function boot() {
  try {
    const [h, o, s] = await Promise.all([
      fetch(API + "/health").then(r => r.json()),
      fetch(API + "/options").then(r => r.json()),
      fetch(API + "/sources").then(r => r.json()),
    ]);
    STATE.stats = h.counts;
    STATE.options = o;
    STATE.sources = s.sources;
    STATE.nonSources = s.not_sources;
  } catch (e) {
    document.body.innerHTML = `<div class="wrap"><div class="card err">API unreachable at ${esc(API)} — ${esc(e.message)}</div></div>`;
    return;
  }
  window.addEventListener("hashchange", route);
  route();
}

function setLang(l) {
  lang = l;
  localStorage.setItem("taweel_lang", l);
  route();
}

/* ---------------------------------------------------------------- layout */
function chrome(inner) {
  const L = t();
  const here = location.hash || "#/";
  const link = (href, key) =>
    `<a href="${href}" class="${here === href || (href !== "#/" && here.startsWith(href)) ? "active" : ""}">${L.nav[key]}</a>`;

  document.documentElement.lang = L.dir === "rtl" ? "ar" : "en";
  document.documentElement.dir = L.dir;

  document.body.innerHTML = `
    <div class="topbar"><div class="topbar-inner">
      <a class="brand" href="#/">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M12 3c-4 3-6 6-6 10a6 6 0 0 0 12 0c0-4-2-7-6-10Z"/></svg>
        <span>${L.brand}</span>
      </a>
      <nav class="nav-links">
        ${link("#/", "home")}${link("#/result", "result")}${link("#/interpreters", "interpreters")}
        ${link("#/about", "about")}${link("#/faq", "faq")}${link("#/journal", "journal")}
        <span class="lang-switch">
          <button class="${lang === "ar" ? "active" : ""}" onclick="setLang('ar')">AR</button>
          <button class="${lang === "en" ? "active" : ""}" onclick="setLang('en')">EN</button>
        </span>
      </nav>
    </div></div>
    ${inner}
    <footer class="site-foot"><div class="wrap">${L.footer}</div></footer>`;
}

/* ---------------------------------------------------------------- router */
function route() {
  const h = location.hash || "#/";
  if (h.startsWith("#/lens/")) return viewLens(decodeURIComponent(h.slice(7)));
  if (h.startsWith("#/note/")) return viewNonSource(decodeURIComponent(h.slice(7)));
  ({
    "#/": viewHome, "#/result": viewResult, "#/interpreters": viewInterpreters,
    "#/about": viewAbout, "#/faq": viewFaq, "#/journal": viewJournal,
  }[h] || viewHome)();
  window.scrollTo(0, 0);
}

/* ------------------------------------------------------------ components */
function dreamForm(fixedSource) {
  const L = t(), o = STATE.options;
  const sourceRow = fixedSource ? "" : `
    <label class="field field-source">
      <span>${L.sourceLabel}</span>
      <select id="f-source">
        <option value="">${L.sourceAll}</option>
        ${STATE.sources.filter(s => s.role !== "hadith")
          .map(s => `<option value="${s.slug}">${esc(s.name[lang])}</option>`).join("")}
      </select>
    </label>`;

  return `
    <div class="card form-card">
      <label class="field">
        <span>${L.dreamLabel}</span>
        <textarea id="dream" dir="rtl" lang="ar" placeholder="${L.placeholder}"></textarea>
        <small>${L.dreamHint}</small>
      </label>
      ${sourceRow}
      <details class="ctx" ${fixedSource ? "" : "open"}>
        <summary>${L.ctxHead}</summary>
        <div class="ctx-grid">
          ${o.fields.map(f => `
            <label><span>${esc(f.label[lang])}</span>
              <select id="f-${f.key}"><option value="">—</option>
                ${f.values.map(v => `<option value="${esc(v.ar)}">${esc(v[lang])}</option>`).join("")}
              </select></label>`).join("")}
        </div>
      </details>
      <div class="row">
        <button class="btn btn-gold" onclick="submitDream('${fixedSource || ""}')">${L.go}</button>
        <button class="btn ghost" onclick="document.getElementById('dream').value=''">${L.clear}</button>
      </div>
      <div class="examples">
        ${o.examples.map(e => `<span class="ex" onclick="document.getElementById('dream').value=this.textContent">${esc(e)}</span>`).join("")}
      </div>
    </div>`;
}

function sourceCard(s) {
  const L = t();
  return `
    <a class="hub-card" href="#/lens/${s.slug}">
      <div class="hub-head">
        <span class="dot dot-${s.color}"></span>
        <h3>${esc(s.name[lang])}</h3>
      </div>
      <div class="hub-author">${esc(s.author[lang])}${s.died ? ` · ${esc(s.died)}` : ""}</div>
      <div class="hub-role">${L.kinds[s.kind] || s.kind} · ${L.roles[s.role] || s.role}</div>
      <span class="arrow">${L.readMore}</span>
    </a>`;
}

/* ------------------------------------------------------------------ views */
function viewHome() {
  const L = t(), c = STATE.stats;
  const n = x => x.toLocaleString(lang === "ar" ? "ar-EG" : "en-US");
  chrome(`
    <div class="hero"><div class="hero-inner">
      <h1>${L.heroH1}</h1>
      <p class="sub">${L.heroSub}</p>
      <div class="trust-line">
        <span><b>${n(c.symbols)}</b> ${L.symbols}</span>·
        <span><b>${n(c.passages)}</b> ${L.passages}</span>·
        <span><b>${n(c.adab)}</b> ${L.hadith}</span>
      </div>
    </div></div>
    <div class="wrap">
      ${dreamForm(null)}
      <div id="pending"></div>
      <h2 class="section-label">${L.interpretersH1}</h2>
      <div class="hub-grid">${STATE.sources.filter(s => s.role !== "hadith").map(sourceCard).join("")}</div>
    </div>`);
}

function viewInterpreters() {
  const L = t();
  chrome(`
    <div class="wrap page">
      <h1>${L.interpretersH1}</h1>
      <p class="sub">${L.interpretersSub}</p>
      <div class="hub-grid">${STATE.sources.map(sourceCard).join("")}</div>

      <h2 class="section-label">${L.otherAuthorities}</h2>
      <div class="hub-grid">
        ${STATE.nonSources.map(nsCard).join("")}
      </div>
    </div>`);
}

function nsCard(ns) {
  const L = t();
  return `<a class="hub-card muted" href="#/note/${ns.slug}">
      <div class="hub-head"><span class="dot dot-grey"></span><h3>${esc(ns.name_ar)} — ${esc(ns.name_en)}</h3></div>
      <div class="hub-role">${L.notSourceH}</div>
      <span class="arrow">${L.readMore}</span></a>`;
}

function viewLens(slug) {
  const L = t();
  const s = STATE.sources.find(x => x.slug === slug);
  if (!s) return viewInterpreters();
  const isHadith = s.role === "hadith";
  chrome(`
    <div class="wrap page">
      <a class="home-link" href="#/interpreters">← ${L.nav.interpreters}</a>
      <h1>${esc(s.name[lang])}</h1>
      <p class="sub">${esc(s.author[lang])}${s.died ? ` · ${esc(s.died)}` : ""}</p>

      <div class="card meta-card">
        <div class="meta-row"><span>${L.role}</span><b>${L.kinds[s.kind] || s.kind} · ${L.roles[s.role] || s.role}</b></div>
        ${s.source_url ? `<div class="meta-row"><span>${L.sourceLink}</span>
          <a href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.source_url)}</a></div>` : ""}
      </div>

      ${s.note ? `<div class="note caution"><b>${L.notSourceH}:</b> ${esc(s.note[lang])}</div>` : ""}

      ${isHadith ? "" : `
        <h2 class="section-label">${L.interpretWith} ${esc(s.name[lang])}</h2>
        ${dreamForm(s.slug)}`}
      <div id="pending"></div>
    </div>`);
}

function viewNonSource(slug) {
  const L = t();
  const ns = STATE.nonSources.find(x => x.slug === slug);
  if (!ns) return viewInterpreters();
  chrome(`
    <div class="wrap page">
      <a class="home-link" href="#/interpreters">← ${L.nav.interpreters}</a>
      <h1>${esc(ns.name_ar)} — ${esc(ns.name_en)}</h1>
      <div class="card">
        <p dir="rtl" lang="ar" class="serif">${esc(ns.explanation_ar)}</p>
        <hr>
        <p dir="ltr" lang="en">${esc(ns.explanation_en)}</p>
      </div>
      <a class="btn btn-gold" href="#/">${L.nav.home}</a>
    </div>`);
}

function viewAbout() {
  const L = t();
  chrome(`
    <div class="wrap page">
      <h1>${L.aboutH1}</h1>
      <p class="sub">${L.aboutSub}</p>
      <div class="hub-grid">${STATE.sources.map(sourceCard).join("")}</div>
      <div class="card">
        <h2>${L.basis}</h2>
        <p><span class="badge book">${L.fromBooks}</span> — ${lang === "ar"
          ? "منقول من كتاب بعينه، ويُعرض نصّه العربي مع اسم الكتاب وصفحته المطبوعة ورابط المصدر."
          : "Quoted from a named book. Its Arabic text is shown with the book, the printed page and a link to the scan."}</p>
        <p><span class="badge">${L.fromGeneral}</span> — ${lang === "ar"
          ? "ليس في الكتب المفهرسة نصٌّ له، فيُذكر ما استقرّ عند أهل التعبير، ولا يُنسب إلى كتاب ولا صفحة."
          : "The indexed books contain nothing for it, so what is settled among interpreters is given — attributed to no book and no page."}</p>
      </div>
    </div>`);
}

function viewFaq() {
  const L = t();
  const qs = lang === "ar" ? [
    ["هل هذا فتوى؟", "لا. هذا عرضٌ لما ورد في كتب التعبير، والتعبير ظنّي يختلف بحال الرائي، والمرجع فيه أهل العلم."],
    ["لماذا لا تُفسَّر بعض الرؤى؟", "لأن الرؤيا المكروهة لا تُعبَّر في هدي السنة، بل يُستعاذ بالله من شرها، ويتفل الرائي عن يساره ثلاثاً، ويتحوّل عن جنبه، ولا يحدّث بها أحداً."],
    ["ماذا يعني وسم «من الكتب» و«من المعروف المستقر»؟", "الأول: نصّ منقول من كتاب بعينه مع صفحته. والثاني: لا نصّ له في كتبنا المفهرسة، فذُكر المشهور عند أهل التعبير دون نسبة إلى كتاب."],
    ["هل يتغيّر التفسير بحسب حال الرائي؟", "نعم، والكتب نفسها تفرّق بين الرجل والمرأة، والمتزوج والأعزب، والمريض والصحيح. ولذلك تُسأل عن حالك اختياريًا."],
    ["لماذا أكتب الرؤيا بالعربية؟", "لأن البحث يجري على رموز عربية مستخرجة من الكتب، فالمطابقة تكون على ألفاظها."],
  ] : [
    ["Is this a fatwa?", "No. It presents what the classical books say. Interpretation is probabilistic, varies with the dreamer's situation, and qualified scholars are the reference."],
    ["Why are some dreams not interpreted?", "Because a distressing dream is not interpreted in the sunna. The dreamer seeks refuge in God from its harm, spits lightly to the left three times, turns onto the other side, and tells no one."],
    ["What do the 'cited' and 'general knowledge' tags mean?", "The first: quoted from a named book with its page. The second: the indexed books contain nothing for it, so what is settled among interpreters is given, attributed to no book."],
    ["Does the reading change with my situation?", "Yes. The books themselves distinguish man from woman, married from unmarried, sick from healthy. That is why you are optionally asked."],
    ["Why must I write the dream in Arabic?", "The search runs against Arabic headwords extracted from the books, so matching happens on their own wording."],
  ];
  chrome(`
    <div class="wrap page">
      <h1>${L.faqH1}</h1>
      ${qs.map(([q, a]) => `<details class="acc-item"><summary class="acc-head">${esc(q)}</summary>
        <div class="acc-body">${esc(a)}</div></details>`).join("")}
    </div>`);
}

/* ------------------------------------------------------------ interpret */
async function submitDream(fixedSource) {
  const L = t(), dream = $("#dream").value.trim();
  if (dream.length < 3) { $("#pending").innerHTML = `<div class="card err">${L.empty}</div>`; return; }

  const body = { dream };
  const src = fixedSource || ($("#f-source") ? $("#f-source").value : "");
  if (src) body.source = src;
  (STATE.options.fields || []).forEach(f => {
    const el = $("#f-" + f.key);
    if (el && el.value) body[f.key] = el.value;
  });

  $("#pending").innerHTML = `<div class="card"><span class="spin"></span> ${L.searching}</div>`;
  try {
    const r = await fetch(API + "/interpret", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    STATE.last = await r.json();
    STATE.last.dream = dream;
    sessionStorage.setItem("taweel_last", JSON.stringify(STATE.last));
    location.hash = "#/result";
    if ((location.hash || "") === "#/result") route();
  } catch (e) {
    $("#pending").innerHTML = `<div class="card err">${esc(e.message)}</div>`;
  }
}

function viewResult() {
  const L = t();
  if (!STATE.last) {
    try { STATE.last = JSON.parse(sessionStorage.getItem("taweel_last")); } catch { /* none */ }
  }
  const d = STATE.last;
  if (!d) return viewHome();

  const a = d.answer, meta = d.meta || {};
  const srcName = meta.source
    ? (STATE.sources.find(s => s.slug === meta.source) || {}).name?.[lang]
    : null;

  let h = `<div class="wrap page">
    <div class="card dream-echo">
      <div class="echo-label">${L.yourDream}${srcName ? ` · ${esc(srcName)}` : ""}</div>
      <p dir="rtl" lang="ar" class="serif">${esc(d.dream || "")}</p>
      <a class="btn ghost" href="#/">${L.changeDream}</a>
    </div>`;

  if (!a) {
    h += `<div class="card err">${esc(meta.error || "no answer")}</div>`;
  } else {
    h += `<div class="card">
      <h2>${L.tasnif}</h2>
      <span class="badge ${a.tasnif.naw === "رؤيا صالحة" ? "good" : a.tasnif.naw === "حلم من الشيطان" ? "warn" : ""}">${esc(a.tasnif.naw)}</span>
      <div class="why">${esc(a.tasnif.sabab)}</div>
      <div class="srcs"><span class="badge ${a.asas_aljawab === "من الكتب المفهرسة" ? "book" : ""}">${L.basis}: ${esc(a.asas_aljawab)}</span></div>
    </div>`;

    if (a.mukhifah) h += `<div class="card">
      <h2>${L.mukhifah}</h2><div class="alert">${L.mukhifahNote}</div>
      <ul>${(a.adab || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
      ${a.dua ? `<div class="dua">${esc(a.dua)}</div>` : ""}</div>`;

    if (a.rumuz?.length) h += `<div class="card"><h2>${L.rumuz}</h2>` + a.rumuz.map(r => `
      <div class="symbol-card">
        <h3 class="symbol-name">${esc(r.ramz)}
          <span class="badge ${r.min_alkutub ? "book" : ""}">${r.min_alkutub ? L.fromBooks : L.fromGeneral}</span></h3>
        <div>${esc(r.khulasah)}</div>
        ${(r.tafsil || []).map(c => `<div class="cond"><b>${esc(c.halah)}</b> — ${esc(c.dalalah)}</div>`).join("")}
        ${r.athar_hal_alraai ? `<div class="hal">${L.byState}: ${esc(r.athar_hal_alraai)}</div>` : ""}
        ${r.manhaj ? `<div class="method-note"><b>${L.manhaj}:</b> ${esc(r.manhaj)}${r.bayan_almanhaj ? ` — ${esc(r.bayan_almanhaj)}` : ""}</div>` : ""}
        ${r.masadir?.length ? `<div class="srcs">${L.masadir}: ${r.masadir.map(esc).join(" · ")}</div>` : ""}
      </div>`).join("") + `</div>`;

    if (a.qiraat?.length) h += `<div class="card"><h2>${L.qiraat}</h2>` + a.qiraat.map(q => `
      <div class="qira"><h4>${esc(q.almanhaj)}
        <span class="badge ${q.min_alkutub ? "book" : ""}">${q.min_alkutub ? L.fromBooks : L.fromGeneral}</span></h4>
        <div>${esc(q.nass)}</div></div>`).join("") + `</div>`;

    if (a.khulasah_ammah) {
      h += `<div class="card"><h2>${L.khulasah}</h2><div>${esc(a.khulasah_ammah)}</div>`;
      const m = a.muashirat;
      if (m) {
        const bar = (lbl, v, col) => `<div class="meter"><div class="lbl"><span>${lbl}</span><span>${v}%</span></div>
          <div class="bar"><i style="width:${Math.max(0, Math.min(100, v))}%;background:${col}"></i></div></div>`;
        h += `<div class="meters">${bar(L.tafaul, m.tafaul, "var(--teal)")}${bar(L.raja, m.raja, "var(--gold)")}${bar(L.qalaq, m.qalaq, "var(--caution)")}</div>`;
        if (m.bayan) h += `<div class="why">${esc(m.bayan)}</div>`;
      }
      h += `${a.tanbih ? `<div class="tanbih">${esc(a.tanbih)}</div>` : ""}</div>`;
    }

    if (!a.mukhifah && a.adab?.length) h += `<div class="card"><h2>${L.adab}</h2>
      <ul>${a.adab.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
      ${a.dua ? `<div class="dua">${esc(a.dua)}</div>` : ""}</div>`;

    if (a.nasihah) h += `<div class="card"><h2>${L.nasihah}</h2><div class="personal-note">${esc(a.nasihah)}</div></div>`;
    if (meta.used_corpus === false) h += `<div class="note">${L.noCorpusNote}</div>`;
  }

  if (d.symbols?.length) h += `<div class="card"><h2>${L.nusus}</h2>` + d.symbols.map(s => `
    <details><summary>${esc(s.symbol_ar)} <span class="badge">${s.citations.length} ${L.texts}</span></summary>
      ${s.citations.map(c => `<div class="cite">
        <div class="txt serif">${esc(c.text_ar)}</div>
        <div class="meta"><span class="badge ${c.kind === "psychological" ? "psych" : "book"}">${c.kind === "psychological" ? L.psych : L.classical}</span>
          ${esc(c.source_name[lang] || c.source_name.ar)}${c.printed_page ? ` (${L.page} ${esc(c.printed_page)})` : ""}
          ${c.url ? `· <a href="${esc(c.url)}" target="_blank" rel="noopener">${L.sourceLink}</a>` : ""}</div>
      </div>`).join("")}</details>`).join("") + `</div>`;

  if (d.adab_sources?.length) h += `<div class="card"><h2>${L.ahadith}</h2>` +
    d.adab_sources.slice(0, 4).map(x => `<div class="cite">
      <div class="txt serif">${esc(x.text_ar)}</div>
      <div class="meta">${esc(x.chapter_ar || "")}${x.printed_page ? ` (${L.page} ${esc(x.printed_page)})` : ""}
        ${x.url ? `· <a href="${esc(x.url)}" target="_blank" rel="noopener">${L.sourceLink}</a>` : ""}</div>
    </div>`).join("") + `</div>`;

  h += `<div class="actions">
    <button class="btn ghost" id="copyBtn">${L.copy}</button>
    <button class="btn ghost" onclick="window.print()">${L.print}</button>
    <button class="btn ghost" id="saveBtn">${L.save}</button></div></div>`;

  chrome(h);
  $("#copyBtn").onclick = copyResult;
  $("#saveBtn").onclick = () => { saveToJournal(); $("#saveBtn").textContent = L.saved; };
}

/* ------------------------------------------------------------- journal */
const JKEY = "taweel_journal_v1";
const jload = () => { try { return JSON.parse(localStorage.getItem(JKEY) || "[]"); } catch { return []; } };
const jsave = a => localStorage.setItem(JKEY, JSON.stringify(a.slice(0, 60)));

function saveToJournal() {
  const d = STATE.last; if (!d) return;
  const a = jload();
  a.unshift({ t: Date.now(), dream: d.dream, naw: d.answer?.tasnif?.naw || "",
              source: d.meta?.source || null, rumuz: (d.symbols || []).map(s => s.symbol_ar) });
  jsave(a);
}

function viewJournal() {
  const L = t(), a = jload();
  const counts = {};
  a.forEach(x => (x.rumuz || []).forEach(r => counts[r] = (counts[r] || 0) + 1));
  const rec = Object.entries(counts).filter(([, n]) => n > 1).sort((x, y) => y[1] - x[1]).slice(0, 12);

  chrome(`<div class="wrap page">
    <h1>${L.journalH1}</h1>
    <p class="sub">${L.journalNote}</p>
    ${rec.length ? `<div class="card"><div class="why">${L.recurring}</div>
      <div class="recur">${rec.map(([r, n]) => `<span class="r">${esc(r)} · ${n}</span>`).join("")}</div></div>` : ""}
    ${a.length ? `<div class="card">${a.map((x, i) => `
      <div class="jrow"><div><b dir="rtl" lang="ar">${esc(x.dream.slice(0, 130))}</b>
        ${x.rumuz?.length ? `<div class="why">${x.rumuz.map(esc).join(" · ")}</div>` : ""}</div>
        <div class="jmeta">${new Date(x.t).toLocaleDateString(lang === "ar" ? "ar-EG" : "en-GB")}
          <button onclick="jdel(${i})">✕</button></div></div>`).join("")}
      </div><button class="btn ghost" onclick="jclear()">${L.jclear}</button>`
      : `<div class="card">${L.noJournal}</div>`}
  </div>`);
}

function jdel(i) { const a = jload(); a.splice(i, 1); jsave(a); route(); }
function jclear() { localStorage.removeItem(JKEY); route(); }

function copyResult() {
  const d = STATE.last, a = d?.answer, L = t(); if (!a) return;
  const out = [`${L.yourDream}: ${d.dream}`, `${L.tasnif}: ${a.tasnif.naw} — ${a.tasnif.sabab}`];
  (a.rumuz || []).forEach(r => {
    out.push(`\n• ${r.ramz} [${r.min_alkutub ? L.fromBooks : L.fromGeneral}]`, `  ${r.khulasah}`);
    (r.tafsil || []).forEach(c => out.push(`  - ${c.halah} => ${c.dalalah}`));
    if (r.masadir?.length) out.push(`  ${L.masadir}: ${r.masadir.join(" · ")}`);
  });
  if (a.khulasah_ammah) out.push(`\n${L.khulasah}: ${a.khulasah_ammah}`);
  if (a.nasihah) out.push(`\n${L.nasihah}: ${a.nasihah}`);
  out.push(`\n${a.tanbih}`);
  navigator.clipboard.writeText(out.join("\n")).then(() => {
    $("#copyBtn").textContent = L.copied;
    setTimeout(() => $("#copyBtn").textContent = L.copy, 1600);
  });
}

window.setLang = setLang;
window.submitDream = submitDream;
window.jdel = jdel;
window.jclear = jclear;
boot();
