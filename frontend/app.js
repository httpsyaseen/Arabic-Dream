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

/* Bumped on every commit. `window.TAWEEL` in the console tells you at a glance
 * whether the browser is running current code or something it cached earlier —
 * a question that cost real time to answer the hard way. */
const BUILD = "5dd90b9-1788624242";

const API_BASE = (() => {
  const q = new URLSearchParams(location.search).get("api");
  if (q) return q.replace(/\/$/, "");
  if (window.API_BASE) return window.API_BASE.replace(/\/$/, "");
  // Served from somewhere other than the API's own port (a static dev server,
  // or opened as a file). Use the same hostname so it still works when the page
  // is opened from another device on the network, not just this machine.
  const dev = location.protocol === "file:" || (location.port && location.port !== "3000");
  if (!dev) return "";
  const host = location.hostname || "localhost";
  return `http://${host}:3000`;
})();
const API = API_BASE + "/api/v1";

const $ = s => document.querySelector(s);

/* ------------------------------------------------------------- numerals
 * Arabic writes its own digits, and Latin ones inside Arabic text read as a
 * foreign object — worse in RTL, where the browser has to flip direction for
 * them mid-sentence.
 *
 * Counting is also not a matter of appending a plural. Arabic agreement runs:
 *   1  singular            نصّ واحد
 *   2  dual                نصّان
 *   3-10 plural            ٣ نصوص
 *   11+ singular again     ٢٠ نصًّا
 * so "20 نصوص" is simply wrong. `count()` puts the right form with the number.
 */
const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";
const num = n => lang === "ar"
  ? String(n).replace(/\d/g, d => AR_DIGITS[+d])
  : Number(n).toLocaleString("en-US");

function count(n, forms) {
  // forms: [singular, dual, plural, accusative-singular] for ar; [one, many] for en
  if (lang !== "ar") return `${num(n)} ${n === 1 ? forms.one : forms.many}`;
  const [one, two, few, many] = forms.ar;
  if (n === 1) return one;
  if (n === 2) return two;
  if (n >= 3 && n <= 10) return `${num(n)} ${few}`;
  return `${num(n)} ${many}`;
}
const TEXTS  = { ar: ["نصٌّ واحد", "نصّان", "نصوص", "نصًّا"], one: "text", many: "texts" };
const SYMS   = { ar: ["رمزٌ واحد", "رمزان", "رموز", "رمزًا"], one: "symbol", many: "symbols" };
const HADITH = { ar: ["حديثٌ واحد", "حديثان", "أحاديث", "حديثًا"], one: "hadith", many: "hadith" };
const DREAMS = { ar: ["رؤيا واحدة", "رؤيان", "رؤى", "رؤيا"], one: "dream", many: "dreams" };
const esc = s => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let lang = localStorage.getItem("taweel_lang") || "ar";
let STATE = { stats: null, options: null, sources: [], nonSources: [], last: null, pages: {} };

/* ------------------------------------------------------------------ i18n */
const T = {
  ar: {
    dir: "rtl", brand: "تأويل",
    nav: { home: "الرئيسية", teeth: "سقوط الأسنان", result: "آخر تفسير", interpreters: "المفسّرون", about: "مصادرنا", faq: "الأسئلة الشائعة", journal: "سجل أحلامي" },
    teethH1: "تفسير حلم سقوط الأسنان",
    teethSub: "من أكثر ما يُسأل عنه من الرؤى. اختر ما يشبه رؤياك، أو اكتبها بنفسك — والجواب مبنيّ على ما ورد في كتب أهل التعبير بنصّه ومصدره.",
    teethPick: "اختر ما يشبه رؤياك",
    teethAsked: "ما يبحث عنه الناس في هذا الباب",
    teethOwn: "أو اكتب رؤياك بنفسك",
    interpretThis: "فسّر هذه الرؤيا",
    searchesLabel: "عبارة بحث",
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
    stageSearch: "يُبحث عن رموز رؤياك في الكتب…",
    stageFound: (s, c) => `وُجد ${s} في ${c}. يُحرَّر الشرح الآن…`,
    stageNone: "لم يُعثر على رمزٍ في الكتب المفهرسة. يُحرَّر الجواب الآن…",
    stageWait: "قد يستغرق هذا بضع ثوانٍ.",
    foundSymbols: "الرموز التي عُثر عليها",
    empty: "اكتب رؤياك أولاً.",
    yourDream: "رؤياك", changeDream: "تعديل الرؤيا",
    verdictPill: (kind, n) => `${kind} · مبنيّ على ${count(n, TEXTS)} من الكتب`,
    verdictPillNoText: kind => `${kind} · لا نصّ له في كتبنا`,
    basedOn: "اعتماداً على",
    plusPsych: "مع قراءة نفسية مضافة",
    lensOnly: name => `أنت تطالع تفسيراً مقصوراً على مسلك ${name} وحده. والرمز الذي لا نصّ له عند هذا المفسّر في فهرسنا يُوسَم بذلك، ولا يُؤخذ من مصدر آخر.`,
    givenSituation: "بحسب حالك",
    addedPsych: "قراءة نفسية مضافة",
    fromSource: "من",
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
    skip: "تخطَّ إلى المحتوى",
    page: "ص", sourceLink: "المصدر", texts: "نص",
    footer: "هذا عرضٌ لما ورد في كتب التعبير، وليس فتوى ولا حكماً شرعياً ولا علماً بالغيب. التعبير ظنّي يختلف باختلاف حال الرائي، والمرجع في ذلك أهل العلم.",
    kinds: { classical: "من كتب التعبير", psychological: "قراءة نفسية", adab: "آداب وأحاديث" },
    roles: { symbols: "يمدّ الفهرس بالرموز", passages: "يمدّ الفهرس بالنصوص",
             both: "يمدّ الفهرس بالرموز والنصوص", hadith: "أحاديث الآداب والتصنيف" },
  },
  en: {
    dir: "ltr", brand: "Ta'weel",
    nav: { home: "Home", teeth: "Falling teeth", result: "Last reading", interpreters: "Interpreters", about: "Our sources", faq: "FAQ", journal: "My dreams" },
    teethH1: "Dreams of teeth falling out",
    teethSub: "One of the most asked-about dreams there is. Pick whichever is closest to yours, or write your own — the answer rests on what the classical books say, with the text and its source shown.",
    teethPick: "Pick the one closest to your dream",
    teethAsked: "What people search for here",
    teethOwn: "Or write your own dream",
    interpretThis: "Interpret this dream",
    searchesLabel: "searches",
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
    stageSearch: "Looking up your dream's symbols in the books…",
    stageFound: (s, c) => `Found ${s} across ${c}. Composing the reading…`,
    stageNone: "No symbol found in the indexed books. Composing an answer…",
    stageWait: "This takes a few seconds.",
    foundSymbols: "Symbols found",
    empty: "Write your dream first.",
    yourDream: "Your dream", changeDream: "Edit dream",
    verdictPill: (kind, n) => `${kind} · built on ${n} original ${n === 1 ? "text" : "texts"}`,
    verdictPillNoText: kind => `${kind} · no text for it in our books`,
    basedOn: "Based on",
    plusPsych: "plus an added psychological reading",
    lensOnly: name => `You are viewing a reading restricted to ${name}'s method only. Symbols with no direct text from this interpreter in our database are flagged as such, instead of pulling from another source.`,
    givenSituation: "Given your situation",
    addedPsych: "Added psychological reading",
    fromSource: "From",
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
    skip: "Skip to content",
    page: "p.", sourceLink: "source", texts: "texts",
    footer: "This presents what the classical books say. It is not a fatwa, not a ruling, and not knowledge of the unseen. Interpretation is probabilistic and varies with the dreamer's situation; qualified scholars are the reference.",
    kinds: { classical: "interpretation books", psychological: "psychological", adab: "etiquette and hadith" },
    roles: { symbols: "supplies the symbol vocabulary", passages: "supplies supporting passages",
             both: "supplies both symbols and passages", hadith: "hadith for etiquette and classification" },
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
  shellBuilt = false;          // its labels are in the other language now
  route();
}

/* ---------------------------------------------------------------- layout
 * The shell is built once. Rewriting the whole body on every render tore down
 * the topbar and footer each time — and since one submit renders three times
 * (skeleton, then citations, then the reading), the chrome flashed three times
 * and the page read as though it had reloaded.
 *
 * Only #main is replaced now; the nav has its active state updated in place.
 */
let shellBuilt = false;

function buildShell() {
  const L = t();
  document.body.innerHTML = `
    <a class="skip" href="#main">${L.skip}</a>
    <div class="topbar"><div class="topbar-inner">
      <a class="brand" href="#/">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M12 3c-4 3-6 6-6 10a6 6 0 0 0 12 0c0-4-2-7-6-10Z"/></svg>
        <span>${L.brand}</span>
      </a>
      <nav class="nav-links">
        <a href="#/" data-route="#/">${L.nav.home}</a>
        <a href="#/teeth" data-route="#/teeth">${L.nav.teeth}</a>
        <a href="#/result" data-route="#/result">${L.nav.result}</a>
        <a href="#/interpreters" data-route="#/interpreters">${L.nav.interpreters}</a>
        <a href="#/about" data-route="#/about">${L.nav.about}</a>
        <a href="#/faq" data-route="#/faq">${L.nav.faq}</a>
        <a href="#/journal" data-route="#/journal">${L.nav.journal}</a>
        <span class="lang-switch">
          <button data-lang="ar" onclick="setLang('ar')">AR</button>
          <button data-lang="en" onclick="setLang('en')">EN</button>
        </span>
      </nav>
    </div></div>
    <main id="main"></main>
    <footer class="site-foot"><div class="wrap">${L.footer}
      <div class="build">build ${BUILD}</div></div></footer>`;
  shellBuilt = true;
}

function chrome(inner) {
  const L = t();
  document.documentElement.lang = L.dir === "rtl" ? "ar" : "en";
  document.documentElement.dir = L.dir;

  if (!shellBuilt) buildShell();

  const here = location.hash || "#/";
  document.querySelectorAll(".nav-links a[data-route]").forEach(a => {
    const r = a.dataset.route;
    a.classList.toggle("active", here === r || (r !== "#/" && here.startsWith(r)));
  });
  document.querySelectorAll(".lang-switch button").forEach(bt =>
    bt.classList.toggle("active", bt.dataset.lang === lang));

  document.getElementById("main").innerHTML = inner;
}

/* ---------------------------------------------------------------- router */
let lastRoute = null;

function route() {
  const h = location.hash || "#/";
  const moved = h !== lastRoute;
  if (h.startsWith("#/lens/") || h.startsWith("#/note/")) {
    (h.startsWith("#/lens/") ? viewLens : viewNonSource)(decodeURIComponent(h.slice(7)));
    if (moved) { window.scrollTo(0, 0); lastRoute = h; }
    return;
  }
  ({
    "#/": viewHome, "#/teeth": viewTeeth, "#/result": viewResult,
    "#/interpreters": viewInterpreters,
    "#/about": viewAbout, "#/faq": viewFaq, "#/journal": viewJournal,
  }[h] || viewHome)();

  // Jumping to the top on every render would yank the reader back up each time
  // the pending view refreshes with new content. Only a real move does that.
  if (h !== lastRoute) {
    window.scrollTo(0, 0);
    lastRoute = h;
  }
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
          .map(s => `<option value="${s.slug}">${esc(s.display[lang])}</option>`).join("")}
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
        <h3>${esc(s.display[lang])}</h3>
      </div>
      <div class="hub-author">«${esc(s.name[lang])}»</div>
      <div class="hub-role">${esc(s.author[lang])}${s.died ? ` · ${esc(s.died[lang])}` : ""}</div>
      <div class="hub-role">${L.kinds[s.kind] || s.kind} · ${L.roles[s.role] || s.role}</div>
      <span class="arrow">${L.readMore}</span>
    </a>`;
}

/* ------------------------------------------------------------------ views */
function viewHome() {
  const L = t(), c = STATE.stats;
  chrome(`
    <div class="hero"><div class="hero-inner">
      <h1>${L.heroH1}</h1>
      <p class="sub">${L.heroSub}</p>
      <div class="trust-line">
        <span>${count(c.symbols, SYMS)}</span>·
        <span>${count(c.passages, TEXTS)}</span>·
        <span>${count(c.adab, HADITH)}</span>
      </div>
    </div></div>
    <div class="wrap">
      ${dreamForm(null)}
      <div id="pending"></div>
      <h2 class="section-label">${L.interpretersH1}</h2>
      <div class="hub-grid">${STATE.sources.filter(s => s.role !== "hadith").map(sourceCard).join("")}</div>
    </div>`);
}

/* A topic page built from a keyword sheet: the dreams people are actually
 * asking about, grouped by meaning, each one runnable. */
async function viewTeeth() {
  const L = t();
  if (!STATE.pages.teeth) {
    chrome(`<div class="wrap page"><h1>${L.teethH1}</h1>
      <div class="card"><div class="skel" style="width:45%"></div>
        <div class="skel"></div><div class="skel" style="width:75%"></div></div></div>`);
    try {
      STATE.pages.teeth = await fetch(API + "/pages/teeth").then(r => r.json());
    } catch (e) {
      return chrome(`<div class="wrap page"><div class="card err">${esc(e.message)}</div></div>`);
    }
    if (!location.hash.startsWith("#/teeth")) return;   // moved on while loading
  }

  const page = STATE.pages.teeth;
  const cards = page.clusters.map((c, i) => `
    <div class="card topic-card">
      <div class="topic-head">
        <h3>${esc(c.title[lang])}</h3>
        ${c.volume ? `<span class="badge">${num(c.volume)} ${L.searchesLabel}</span>` : ""}
      </div>
      <p class="topic-dream serif" dir="rtl" lang="ar">${esc(c.dream_ar)}</p>
      <div class="row">
        <button class="btn btn-gold" onclick="runDream(${i})">${L.interpretThis}</button>
      </div>
      <details class="topic-queries">
        <summary>${L.teethAsked} <span class="badge">${num(c.queries.length)}</span></summary>
        <div class="qlist">${c.queries.slice(0, 24).map(q =>
          `<span class="q" dir="rtl" lang="ar">${esc(q.ar)}${q.volume
            ? `<span class="q-n">${num(q.volume)}</span>` : ""}</span>`).join("")}</div>
      </details>
    </div>`).join("");

  chrome(`<div class="wrap page">
    <h1>${L.teethH1}</h1>
    <p class="sub">${L.teethSub}</p>
    <h2 class="section-label">${L.teethPick}</h2>
    ${cards}
    <h2 class="section-label">${L.teethOwn}</h2>
    ${dreamForm(null)}
    <div id="pending"></div>
  </div>`);
}

/* Send one of the page's dreams through the normal flow — same endpoint, same
   citations, so nothing here is a special case. */
function runDream(i) {
  const c = STATE.pages.teeth?.clusters[i];
  if (!c) return;
  const el = document.getElementById("dream");
  if (el) el.value = c.dream_ar;
  else {
    // The form is further down the page; stage the text and submit directly.
    STATE.stagedDream = c.dream_ar;
  }
  submitDream("", c.dream_ar);
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
      <h1>${esc(s.display[lang])}</h1>
      <p class="sub">«${esc(s.name[lang])}» · ${esc(s.author[lang])}${s.died ? ` · ${esc(s.died[lang])}` : ""}</p>

      <div class="card meta-card">
        <div class="meta-row"><span>${L.role}</span><b>${L.kinds[s.kind] || s.kind} · ${L.roles[s.role] || s.role}</b></div>
        ${s.source_url ? `<div class="meta-row"><span>${L.sourceLink}</span>
          <a href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.source_url)}</a></div>` : ""}
      </div>

      ${s.note ? `<div class="note caution"><b>${L.notSourceH}:</b> ${esc(s.note[lang])}</div>` : ""}

      ${isHadith ? "" : `
        <h2 class="section-label">${L.interpretWith} ${esc(s.display[lang])}</h2>
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
async function submitDream(fixedSource, explicitDream) {
  const L = t();
  const dream = (explicitDream ?? $("#dream")?.value ?? "").trim();
  if (dream.length < 3) {
    const box = $("#pending");
    if (box) box.innerHTML = `<div class="card err">${L.empty}</div>`;
    return;
  }

  const body = { dream };
  const src = fixedSource || ($("#f-source") ? $("#f-source").value : "");
  if (src) body.source = src;
  (STATE.options.fields || []).forEach(f => {
    const el = $("#f-" + f.key);
    if (el && el.value) body[f.key] = el.value;
  });

  // A skeleton of the shape that is coming reads as progress; a bare spinner
  // reads as a stall, and this call takes six seconds or more.
  // Two phases. The lookup costs about 2 ms and the model six to nine seconds,
  // so the citations are shown as soon as they exist rather than being held
  // hostage to the slow half. A reader gets real content in well under a second.
  // Drop the previous reading before anything else. Without this, any path that
  // renders before the new one arrives — a stale cached script, a hashchange
  // firing out of order — can put the last dream's answer back on screen.
  STATE.last = null;
  sessionStorage.removeItem("taweel_last");
  STATE.pending = { dream, body, phase: "matching", match: null };
  location.hash = "#/result";
  route();

  try {
    const m = await fetch(API + "/match", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(r => r.json());
    if (STATE.pending?.dream !== dream) return;      // a newer dream took over
    STATE.pending.match = m;
    STATE.pending.phase = "interpreting";
    if (location.hash === "#/result") route();
  } catch { /* fall through to the full call */ }

  try {
    const r = await fetch(API + "/interpret", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (STATE.pending?.dream !== dream) return;
    STATE.last = await r.json();
    STATE.last.dream = dream;
    STATE.pending = null;
    sessionStorage.setItem("taweel_last", JSON.stringify(STATE.last));
    if (location.hash === "#/result") route(); else location.hash = "#/result";
  } catch (e) {
    STATE.pending = { ...STATE.pending, phase: "error", error: e.message };
    if (location.hash === "#/result") route();
  }
}

/* The dream echoed back, shown in every phase so the page never looks empty. */
function dreamEcho(dream, srcName) {
  const L = t();
  return `<div class="card dream-echo">
      <div class="echo-label">${L.yourDream}${srcName ? ` · ${esc(srcName)}` : ""}</div>
      <p dir="rtl" lang="ar" class="serif">${esc(dream || "")}</p>
      <a class="btn ghost" href="#/">${L.changeDream}</a>
    </div>`;
}

/* What is on screen while the model is still working. */
function viewPending() {
  const L = t(), pend = STATE.pending;
  const m = pend.match;
  const srcName = pend.body.source
    ? (STATE.sources.find(s => s.slug === pend.body.source) || {}).display?.[lang]
    : null;

  let stage, sub;
  if (pend.phase === "matching") {
    stage = L.stageSearch; sub = "";
  } else if (m && m.matched) {
    stage = L.stageFound(count(m.matched, SYMS),
                         count(m.symbols.reduce((n, s) => n + s.citations.length, 0), TEXTS));
    sub = L.stageWait;
  } else {
    stage = L.stageNone; sub = L.stageWait;
  }

  let h = `<div class="wrap page">${dreamEcho(pend.dream, srcName)}`;

  if (pend.phase === "error") {
    h += `<div class="card err">${esc(pend.error)}</div></div>`;
    return chrome(h);
  }

  // A skeleton in the shape of the verdict that is coming, so the layout does
  // not jump when it arrives.
  h += `<div class="verdict verdict-loading" aria-live="polite" aria-busy="true">
      <span class="verdict-pill"><span class="spin"></span> ${esc(stage)}</span>
      <div class="skel skel-lg" style="width:78%;margin-inline:auto"></div>
      <div class="skel skel-lg" style="width:56%;margin-inline:auto"></div>
      <div class="skel" style="width:64%;margin-inline:auto;margin-top:1.4rem"></div>
      <div class="skel" style="width:48%;margin-inline:auto"></div>
      ${sub ? `<p class="verdict-foot">${esc(sub)}</p>` : ""}
    </div>`;

  // The citations already exist — show them rather than another placeholder.
  if (m?.symbols?.length) {
    h += `<h2 class="section-label">${L.foundSymbols}</h2>
      <div class="chips">${m.symbols.map((s, i) =>
        `<span class="chip"><b>${num(i + 1)}</b> ${esc(s.symbol_ar)}
          <span class="chip-n">${count(s.citations.length, TEXTS)}</span></span>`).join("")}</div>`;
    h += citationsBlock(m.symbols);
  }
  return chrome(h + `</div>`);
}

function viewResult() {
  const L = t();
  if (STATE.pending) return viewPending();
  if (!STATE.last) {
    try { STATE.last = JSON.parse(sessionStorage.getItem("taweel_last")); } catch { /* none */ }
  }
  const d = STATE.last;
  if (!d) return viewHome();

  const a = d.answer, meta = d.meta || {};
  const srcName = meta.source
    ? (STATE.sources.find(s => s.slug === meta.source) || {}).display?.[lang]
    : null;

  let h = `<div class="wrap page">${dreamEcho(d.dream, srcName)}`;

  if (!a) {
    h += `<div class="card err">${esc(meta.error || "no answer")}</div>`;
  } else {
    // Which books actually backed this reading, for the line under the verdict.
    const citedSlugs = [...new Set((d.symbols || []).flatMap(s => s.citations.map(c => c.source)))];
    const citedCount = (d.symbols || []).reduce((n, s) => n + s.citations.length, 0);
    const classicalNames = citedSlugs
      .filter(sl => (STATE.sources.find(x => x.slug === sl) || {}).kind !== "psychological")
      .map(sl => (STATE.sources.find(x => x.slug === sl) || {}).display?.[lang])
      .filter(Boolean);
    const hasPsych = citedSlugs.some(sl => (STATE.sources.find(x => x.slug === sl) || {}).kind === "psychological");

    const tone = a.tasnif.naw === "رؤيا صالحة" ? "good"
               : a.tasnif.naw === "حلم من الشيطان" ? "warn" : "neutral";

    h += `<div class="verdict verdict-${tone}">
      <span class="verdict-pill">${citedCount
        ? L.verdictPill(esc(a.tasnif.naw), citedCount)
        : L.verdictPillNoText(esc(a.tasnif.naw))}</span>
      <h2 class="verdict-title serif">${esc(a.unwan || a.tasnif.naw)}</h2>
      ${a.tamhid ? `<p class="verdict-sub">${esc(a.tamhid)}</p>` : ""}
      ${classicalNames.length ? `<p class="verdict-foot">${L.basedOn} ${classicalNames.map(esc).join("، ")}${hasPsych ? ` — ${L.plusPsych}` : ""}</p>` : ""}
    </div>`;

    if (meta.source && srcName) {
      h += `<div class="lens-banner">${L.lensOnly(esc(srcName))}</div>`;
    }

    if (a.mukhifah) h += `<div class="card">
      <h2>${L.mukhifah}</h2><div class="alert">${L.mukhifahNote}</div>
      <ul>${(a.adab || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
      ${a.dua ? `<div class="dua">${esc(a.dua)}</div>` : ""}</div>`;

    if (a.rumuz?.length) {
      h += `<h2 class="section-label">${L.rumuz}</h2>`;
      h += a.rumuz.map((r, i) => {
        // Pair each symbol with the citations the lookup found for it, so the
        // quote box can name the exact book and page under the meaning.
        const hit = (d.symbols || []).find(s => s.symbol_ar === r.ramz) || {};
        const cites = hit.citations || [];
        const classical = cites.filter(c => c.kind !== "psychological");
        const psych = cites.filter(c => c.kind === "psychological");
        // Book, then author, then page — the reader needs the name of whose
        // opinion this is, not only which volume it sits in.
        const srcLine = c => {
          const author = c.author && (c.author[lang] || c.author.ar);
          return `«${esc(c.source_name[lang] || c.source_name.ar)}»`
            + (author ? ` — ${esc(author)}` : "")
            + (c.printed_page ? ` (${L.page} ${esc(c.printed_page)})` : "")
            + (c.url ? ` · <a href="${esc(c.url)}" target="_blank" rel="noopener">${L.sourceLink}</a>` : "");
        };

        return `<div class="card symbol-card">
          <div class="symbol-head">
            <div class="symbol-icon">${num(i + 1)}</div>
            <h3 class="symbol-name">${esc(r.ramz)}
              <span class="badge ${r.min_alkutub ? "book" : ""}">${r.min_alkutub ? L.fromBooks : L.fromGeneral}</span></h3>
          </div>

          <div class="quote-box">
            <p>${esc(r.khulasah)}</p>
            ${(r.tafsil || []).map(c => `<p class="cond-line"><b>${esc(c.halah)}</b> — ${esc(c.dalalah)}</p>`).join("")}
            ${classical.length ? `<div class="quote-src">${L.fromSource}: ${srcLine(classical[0])}</div>` : ""}
          </div>

          ${r.athar_hal_alraai ? `<div class="hal"><b>${L.givenSituation}:</b> ${esc(r.athar_hal_alraai)}</div>` : ""}
          ${r.manhaj ? `<div class="method-note"><b>${L.manhaj}:</b> ${esc(r.manhaj)}${r.bayan_almanhaj ? ` — ${esc(r.bayan_almanhaj)}` : ""}</div>` : ""}
          ${psych.length ? `<div class="psych-block"><span class="badge psych">${L.addedPsych}</span>
            <p class="serif">${esc(psych[0].text_ar.slice(0, 320))}${psych[0].text_ar.length > 320 ? "…" : ""}</p>
            <div class="quote-src">${srcLine(psych[0])}</div></div>` : ""}
          ${r.masadir?.length ? `<div class="srcs">${L.masadir}: ${r.masadir.map(esc).join(" · ")}</div>` : ""}
        </div>`;
      }).join("");
    }

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

  if (d.symbols?.length) h += citationsBlock(d.symbols);
  h += adabBlock(d);

  h += `<div class="actions">
    <button class="btn ghost" id="copyBtn">${L.copy}</button>
    <button class="btn ghost" onclick="window.print()">${L.print}</button>
    <button class="btn ghost" id="saveBtn">${L.save}</button></div></div>`;

  chrome(h);
  $("#copyBtn").onclick = copyResult;
  $("#saveBtn").onclick = () => { saveToJournal(); $("#saveBtn").textContent = L.saved; };
}

function citationsBlock(symbols) {
  const L = t();
  return `<div class="card"><h2>${L.nusus}</h2>` + symbols.map(s => `
    <details><summary>${esc(s.symbol_ar)} <span class="badge">${count(s.citations.length, TEXTS)}</span></summary>
      ${s.citations.map(c => `<div class="cite">
        <div class="txt serif">${esc(c.text_ar)}</div>
        <div class="meta"><span class="badge ${c.kind === "psychological" ? "psych" : "book"}">${c.kind === "psychological" ? L.psych : L.classical}</span>
          «${esc(c.source_name[lang] || c.source_name.ar)}»${c.author && (c.author[lang] || c.author.ar) ? ` — ${esc(c.author[lang] || c.author.ar)}` : ""}${c.printed_page ? ` (${L.page} ${num(c.printed_page)})` : ""}
          ${c.url ? `· <a href="${esc(c.url)}" target="_blank" rel="noopener">${L.sourceLink}</a>` : ""}</div>
      </div>`).join("")}</details>`).join("") + `</div>`;
}

function adabBlock(d) {
  const L = t();
  let h = "";
  if (d.adab_sources?.length) h += `<div class="card"><details class="fold"><summary><h2>${L.ahadith}</h2>
      <span class="badge">${count(Math.min(d.adab_sources.length, 4), HADITH)}</span></summary>` +
    d.adab_sources.slice(0, 4).map(x => `<div class="cite">
      <div class="txt serif">${esc(x.text_ar)}</div>
      <div class="meta">${esc(x.chapter_ar || "")}${x.printed_page ? ` (${L.page} ${num(x.printed_page)})` : ""}
        ${x.url ? `· <a href="${esc(x.url)}" target="_blank" rel="noopener">${L.sourceLink}</a>` : ""}</div>
    </div>`).join("") + `</details></div>`;
  return h;
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
      <div class="recur">${rec.map(([r, n]) => `<span class="r">${esc(r)} · ${num(n)}</span>`).join("")}</div></div>` : ""}
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

// Diagnostics. Type `TAWEEL` in the console.
window.TAWEEL = {
  build: BUILD,
  api: API,
  get state() {
    return { hash: location.hash, pending: STATE.pending?.phase ?? null,
             hasLast: !!STATE.last, lang, shellBuilt };
  },
  async ping() {
    const t0 = performance.now();
    const r = await fetch(API + "/health").then(r => r.json());
    return { ok: true, ms: Math.round(performance.now() - t0), symbols: r.counts.symbols };
  },
};
console.info(`%cتأويل build ${BUILD}%c  API: ${API}`,
  "background:#122B2A;color:#A9782E;padding:2px 6px;border-radius:3px", "");

window.setLang = setLang;
window.submitDream = submitDream;
window.runDream = runDream;
window.jdel = jdel;
window.jclear = jclear;
boot();
