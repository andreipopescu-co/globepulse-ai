/* =====================================================================
   app.js – logica interfetei: incarcarea datelor de la server, afisarea
   stirilor, a tarilor si a cotatiilor, legatura cu globul si cu vocea.
   ===================================================================== */
"use strict";

const stare = {
  date: null,
  tab: "stiri",
  filtruSursa: "Toate",
  filtruCategorie: null,
  taraDeschisa: null,
  sentimentAfisat: 0,
  stiriDupaId: new Map(),
  // true = versiunea online (GitHub Pages), fara server Python; marcata de build_static.py
  static: document.documentElement.dataset.mod === "static",
};

// ------------------------------------------------------------------
// Pornire
// ------------------------------------------------------------------
async function porneste() {
  Orb.porneste($("#orb"));
  configureazaEvenimente();
  configureazaSetariVoce();
  pornesteCeas();
  afiseazaInfoVoce();
  deseneazaIndicator(0);
  $("#text-asistent").innerHTML = `<div class="bula raspuns"><small>GlobePulse</small>Bună! Apasă <b>„Rezumatul zilei”</b> ca să-ți citesc cele mai importante știri, sau întreabă-mă ceva despre o țară, piețe ori politică.</div>`;

  try {
    await Glob.init($("#glob"), deschideTara);
  } catch (eroare) {
    $("#glob").innerHTML = `<div class="eroare-glob">Globul 3D nu poate fi afișat pe acest calculator (WebGL indisponibil).<br>${esc(eroare.message)}</div>`;
  }
  await incarcaDate(true);
  aplicaLegaturaDirecta();
  window.addEventListener("hashchange", aplicaLegaturaDirecta);
  setInterval(() => incarcaDate(), 60_000);
}

/** Legaturi directe: #tara=CHN, #tab=tari sau #intrebare=Cum stau pietele? */
function aplicaLegaturaDirecta() {
  if (!stare.date) return;
  const parametri = new URLSearchParams(location.hash.slice(1));
  const tab = parametri.get("tab");
  if (["stiri", "tari", "categorii", "puncte"].includes(tab)) { stare.tab = tab; randeazaTab(); }
  const tara = parametri.get("tara");
  if (tara && /^[A-Za-z]{3}$/.test(tara)) deschideTara(tara.toUpperCase());
  const intrebare = parametri.get("intrebare");
  if (intrebare) trimiteIntrebare(intrebare);
}

/** Local: datele vin de la serverul Python (api/date). Online (GitHub Pages): din fișierul date/date.json. */
async function preiaDate() {
  if (!stare.static) {
    try {
      const raspuns = await fetch("api/date", { cache: "no-store" });
      if (raspuns.ok) return await raspuns.json();
    } catch (eroare) { /* nu exista server Python: versiunea online */ }
  }
  const raspuns = await fetch(`date/date.json?t=${Date.now()}`, { cache: "no-store" });
  if (!raspuns.ok) throw new Error("date indisponibile");
  stare.static = true;
  return raspuns.json();
}

async function incarcaDate(fortat = false) {
  try {
    const date = await preiaDate();
    const neschimbat = stare.date && date.actualizat === stare.date.actualizat;
    if (neschimbat && !fortat) return;
    stare.date = date;
    stare.stiriDupaId = new Map(date.stiri.map((s) => [s.id, s]));
    randeazaTot();
  } catch (eroare) {
    $("#cip-actualizat").textContent = "⚠ Server indisponibil";
  }
}

function randeazaTot() {
  const d = stare.date;
  if (d.voce_neurala === false) Voce.seteazaNeuralDisponibil(false);
  if (d.static) {
    // online exista doar vocea Alina, pregenerata la fiecare actualizare
    Voce.seteazaAudioStatic(d.audio || {});
    const select = $("#select-voce");
    select.querySelector('option[value="emil"]').disabled = true;
    if (select.value === "emil") { select.value = "alina"; Voce.seteazaVoceNeurala("alina"); }
  }
  randeazaAntet();
  randeazaTicker();
  animaSentiment(d.sentiment_ai ?? d.sentiment_general);
  animaNumar($("#stat-stiri"), d.stiri.length);
  animaNumar($("#stat-tari"), Object.values(d.tari).filter((t) => t.nr_stiri > 0 && t.iso3 !== "EUU").length);
  animaNumar($("#stat-surse"), new Set(d.stiri.map((s) => s.sursa)).size);
  Glob.actualizeaza(d.tari, d.legaturi);
  pornesteUltimaOra();
  randeazaTab();
  if (stare.taraDeschisa) deschideTara(stare.taraDeschisa, false);
}

// ------------------------------------------------------------------
// Antet, ceas, cotatii
// ------------------------------------------------------------------
function randeazaAntet() {
  const d = stare.date;
  const mod = $("#cip-mod");
  if (d.mod_ai === "claude") {
    mod.className = "cip ai";
    mod.textContent = `✦ AI: ${d.nume_model}`;
    mod.title = "Rezumatele și impactul pe țări sunt generate de modelul de limbaj Claude.";
  } else {
    mod.className = "cip offline";
    mod.textContent = "⚙ AI local";
    mod.title = `Rezumatele sunt generate de algoritmii locali (${d.motiv_offline}).`;
  }
  if (d.demo) mod.textContent += " · DEMO";

  const ok = d.surse.filter((s) => s.ok).length;
  const cipSurse = $("#cip-surse");
  cipSurse.textContent = `📡 ${ok}/${d.surse.length} fluxuri`;
  cipSurse.title = d.surse.map((s) => `${s.ok ? "✔" : "✖"} ${s.nume} (${s.id}): ${s.ok ? s.nr + " știri" : s.eroare}`).join("\n");
  const ora = new Date(d.actualizat).toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit" });
  $("#cip-actualizat").textContent = `🕒 actualizat ${ora}`;
  $("#cip-actualizat").title = d.static
    ? "Versiunea online se actualizează automat aproximativ la fiecare 30 de minute."
    : "Serverul local actualizează știrile la fiecare 10 minute.";
}

function pornesteCeas() {
  const tic = () => { $("#ceas").textContent = new Date().toLocaleTimeString("ro-RO"); };
  tic();
  setInterval(tic, 1000);
}

function sparkline(valori, culoare) {
  if (!valori || valori.length < 2) return "";
  const min = Math.min(...valori), max = Math.max(...valori), L = 54, H = 18;
  const puncte = valori.map((v, i) => {
    const x = (i / (valori.length - 1)) * L;
    const y = max === min ? H / 2 : H - 1 - ((v - min) / (max - min)) * (H - 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return `<svg viewBox="0 0 ${L} ${H}"><polyline fill="none" stroke="${culoare}" stroke-width="1.5" points="${puncte}"/></svg>`;
}

function formatPret(p) {
  const zecimale = p.pret >= 1000 ? 0 : p.pret >= 10 ? 2 : 4;
  return p.pret.toLocaleString("ro-RO", { minimumFractionDigits: zecimale, maximumFractionDigits: zecimale });
}

function randeazaTicker() {
  const piete = stare.date.piete || [];
  const pista = $("#ticker");
  if (!piete.length) {
    pista.style.animation = "none";
    pista.innerHTML = `<div class="cotatie"><span class="nume">Datele de piață nu sunt disponibile momentan</span></div>`;
    return;
  }
  const html = piete.map((p) => {
    const clasa = p.variatie > 0 ? "sus" : p.variatie < 0 ? "jos" : "";
    const sageata = p.variatie > 0 ? "▲" : p.variatie < 0 ? "▼" : "•";
    const culoare = p.variatie >= 0 ? "#22c55e" : "#f43f5e";
    return `<div class="cotatie"><span class="nume">${esc(p.nume)}</span><span class="pret">${formatPret(p)}</span>
      <span class="${clasa}">${sageata} ${nrRo(Math.abs(p.variatie), 2)}%</span>${sparkline(p.istoric, culoare)}</div>`;
  }).join("");
  pista.innerHTML = html + html; // continut dublat => derulare continua
  pista.style.animation = "";
  pista.style.animationDuration = `${piete.length * 5}s`;
}

// ------------------------------------------------------------------
// Indicatorul de sentiment (semicerc cu ac)
// ------------------------------------------------------------------
function deseneazaIndicator(valoare) {
  const { ctx, latime: L, inaltime: H } = pregatesteCanvas($("#indicator"));
  const cx = L / 2, cy = H - 10, r = Math.min(L / 2 - 14, H - 24);
  ctx.lineCap = "round";
  ctx.lineWidth = 12;
  ctx.strokeStyle = "rgba(51,65,85,.6)";
  ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, 2 * Math.PI); ctx.stroke();
  const gradient = ctx.createLinearGradient(cx - r, 0, cx + r, 0);
  gradient.addColorStop(0, "#f43f5e"); gradient.addColorStop(0.5, "#64748b"); gradient.addColorStop(1, "#22c55e");
  ctx.strokeStyle = gradient;
  ctx.globalAlpha = 0.9;
  ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, 2 * Math.PI); ctx.stroke();
  ctx.globalAlpha = 1;

  // scala afisata: [-0,5 ; +0,5] (sentimentul mediu al stirilor este de obicei mic)
  const pozitie = Math.max(-1, Math.min(1, valoare * 2));
  const unghi = Math.PI + ((pozitie + 1) / 2) * Math.PI;
  ctx.strokeStyle = "#e5edf7"; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(unghi) * (r - 16), cy + Math.sin(unghi) * (r - 16)); ctx.stroke();
  ctx.fillStyle = "#e5edf7";
  ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#8b9bb4"; ctx.font = "11px Segoe UI";
  ctx.textAlign = "left"; ctx.fillText("−", cx - r - 10, cy);
  ctx.textAlign = "right"; ctx.fillText("+", cx + r + 12, cy);
}

function animaSentiment(tinta) {
  const start = stare.sentimentAfisat, t0 = performance.now();
  const pas = (acum) => {
    const p = Math.min(1, (acum - t0) / 1200), e = 1 - Math.pow(1 - p, 3);
    const v = start + (tinta - start) * e;
    deseneazaIndicator(v);
    if (p < 1) requestAnimationFrame(pas);
  };
  stare.sentimentAfisat = tinta;
  requestAnimationFrame(pas);
  const el = $("#valoare-sentiment");
  el.textContent = `${descriereSentiment(tinta)} (${cuSemn(tinta)})`;
  el.style.color = culoareImpact(tinta * 2);
}

// ------------------------------------------------------------------
// Banda "Ultima ora"
// ------------------------------------------------------------------
let temporizatorUltimaOra = null;
function pornesteUltimaOra() {
  clearInterval(temporizatorUltimaOra);
  const stiri = stare.date.stiri.slice(0, 12);
  const el = $("#ultima-ora-text");
  if (!stiri.length) { el.textContent = "Nu există știri disponibile."; return; }
  let i = 0;
  const arata = () => {
    const s = stiri[i++ % stiri.length];
    el.classList.add("ascuns");
    setTimeout(() => {
      el.innerHTML = `<span class="sursa-mica">${esc(s.sursa)}</span>${esc(s.titlu)} <span style="color:#8b9bb4">· ${timpRelativ(s.data)}</span>`;
      el.classList.remove("ascuns");
    }, 450);
  };
  arata();
  temporizatorUltimaOra = setInterval(arata, 7000);
}

// ------------------------------------------------------------------
// Taburi: stiri, tari, categorii, puncte cheie
// ------------------------------------------------------------------
function cardStire(s, index = 0) {
  const culoare = CULORI_SURSE[s.sursa] || "#94a3b8";
  const sursa = s.sursa_originala ? `${s.sursa} · ${s.sursa_originala}` : s.sursa;
  const tari = s.tari.map((iso) => `<button class="eticheta-tara" data-iso="${esc(iso)}">${esc(Glob.numeTara(iso))}</button>`).join("");
  const categorii = s.categorii.map((c) => `<span class="eticheta-cat">${ICONITE_CATEGORII[c] || ""} ${esc(c)}</span>`).join("");
  const explicatie = `Sentiment ${cuSemn(s.sentiment)}${s.cuvinte_sentiment.length ? " – cuvinte: " + s.cuvinte_sentiment.join(", ") : ""}`;
  return `<article class="stire" style="animation-delay:${Math.min(index, 15) * 35}ms">
    <div class="stire-cap">
      <span class="sursa" style="color:${culoare};background:${culoare}22">${esc(sursa)}</span>
      <span>${timpRelativ(s.data)}</span>
      <span class="punct" style="background:${culoareImpact(s.sentiment * 1.5)}" title="${esc(explicatie)}"></span>
    </div>
    <a href="${esc(linkSigur(s.link))}" target="_blank" rel="noopener noreferrer">${esc(s.titlu)}</a>
    <div class="etichete">${tari}${categorii}</div>
  </article>`;
}

function baraImpact(v, mare = false) {
  const latime = Math.min(50, Math.abs(v) * 50);
  const pozitie = v >= 0 ? "left:50%" : "right:50%";
  return `<div class="bara-impact${mare ? " mare" : ""}"><i style="${pozitie};width:${latime}%;background:${culoareImpact(v)}"></i></div>`;
}

function randeazaFiltre() {
  const filtre = $("#filtre");
  if (stare.tab !== "stiri") { filtre.innerHTML = ""; return; }
  const surse = ["Toate", ...new Set(stare.date.stiri.map((s) => s.sursa))];
  let html = surse.map((s) => `<button class="filtru${s === stare.filtruSursa ? " activ" : ""}" data-sursa="${esc(s)}">${esc(s)}</button>`).join("");
  if (stare.filtruCategorie) {
    html += `<button class="filtru activ" data-sterge-categorie="1">${ICONITE_CATEGORII[stare.filtruCategorie] || ""} ${esc(stare.filtruCategorie)} ✕</button>`;
  }
  filtre.innerHTML = html;
}

function randeazaTab() {
  const d = stare.date, lista = $("#lista");
  randeazaFiltre();
  $$(".taburi nav button").forEach((b) => b.classList.toggle("activ", b.dataset.tab === stare.tab));

  if (stare.tab === "stiri") {
    let stiri = d.stiri;
    if (stare.filtruSursa !== "Toate") stiri = stiri.filter((s) => s.sursa === stare.filtruSursa);
    if (stare.filtruCategorie) stiri = stiri.filter((s) => s.categorii.includes(stare.filtruCategorie));
    lista.innerHTML = stiri.slice(0, 150).map(cardStire).join("") || `<p class="gol">Nicio știre pentru filtrul ales.</p>`;
  } else if (stare.tab === "tari") {
    const tari = Object.values(d.tari).filter((t) => t.nr_stiri > 0).sort((a, b) => b.nr_stiri - a.nr_stiri);
    lista.innerHTML = tari.map((t, i) => `
      <div class="rand" data-iso="${t.iso3}" style="animation-delay:${Math.min(i, 20) * 25}ms">
        <div><b>${esc(t.nume)}</b><small>${esc(descriereImpact(t.impact))} (${cuSemn(t.impact)})</small></div>
        ${baraImpact(t.impact)}
        <span class="nr">${t.nr_stiri}</span>
      </div>`).join("") || `<p class="gol">Nu există date.</p>`;
  } else if (stare.tab === "categorii") {
    const maxim = Math.max(1, ...d.categorii.map((c) => c.nr));
    lista.innerHTML = d.categorii.map((c, i) => `
      <div class="rand" data-categorie="${esc(c.nume)}" style="animation-delay:${i * 30}ms">
        <div><b>${ICONITE_CATEGORII[c.nume] || ""} ${esc(c.nume)}</b><small>ton ${esc(descriereSentiment(c.sentiment))}</small></div>
        <div class="bara-simpla"><i style="width:${(c.nr / maxim) * 100}%"></i></div>
        <span class="nr">${c.nr}</span>
      </div>`).join("");
  } else {
    const b = d.briefing;
    const ora = b.generat_la ? new Date(b.generat_la).toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit" }) : "";
    lista.innerHTML = `<ol class="puncte-cheie">${b.puncte_cheie.map((p, i) => `<li style="animation-delay:${i * 60}ms">${esc(p)}</li>`).join("")}</ol>
      <p class="nota">Generat de: <b>${esc(b.generat_de)}</b>${ora ? " la ora " + ora : ""}.</p>`;
  }
}

// ------------------------------------------------------------------
// Panoul unei tari
// ------------------------------------------------------------------
function deschideTara(iso, zboara = true) {
  const d = stare.date, t = d?.tari[iso], panou = $("#panou-tara");
  stare.taraDeschisa = iso;
  Glob.selecteaza(iso);
  if (zboara) Glob.zboaraLa(iso);
  panou.hidden = false;

  const cap = (nume) => `<div class="tara-cap"><div><div class="eticheta">Profil de impact</div><h3>${esc(nume)}</h3></div>
    <button class="inchide" id="inchide-tara" title="Închide">✕</button></div>`;

  if (!t || !t.nr_stiri) {
    panou.innerHTML = cap(Glob.numeTara(iso)) + `<p class="gol">Nu există știri recente despre această țară.</p>`;
    return;
  }
  const stiri = t.stiri.map((id) => stare.stiriDupaId.get(id)).filter(Boolean);
  const evaluare = t.explicatie
    ? `<p class="tara-descriere">${esc(t.explicatie)}</p><p class="tara-sursa-evaluare">Evaluare generată de ${esc(d.nume_model)}</p>`
    : `<p class="tara-descriere">Evaluare algoritmică: ${esc(descriereImpact(t.impact))}, pe baza a ${t.nr_stiri} știri${t.stiri_regionale ? ` și a ${t.stiri_regionale} știri despre Uniunea Europeană` : ""}.</p>`;

  panou.innerHTML = cap(t.nume) + `
    <div class="tara-metrici">
      <div class="metrica"><strong style="color:${culoareImpact(t.impact)}">${cuSemn(t.impact)}</strong><span>impact</span></div>
      <div class="metrica"><strong>${t.nr_stiri}</strong><span>știri</span></div>
      <div class="metrica"><strong>${Math.round(t.intensitate * 100)}%</strong><span>intensitate</span></div>
    </div>
    ${baraImpact(t.impact, true)}
    ${evaluare}
    <div class="etichete">${t.categorii.map((c) => `<span class="eticheta-cat">${ICONITE_CATEGORII[c] || ""} ${esc(c)}</span>`).join("")}</div>
    <button class="btn principal" id="asculta-tara">🔊 Ascultă analiza</button>
    <div class="lista">${stiri.map(cardStire).join("")}</div>`;
}

function inchideTara() {
  stare.taraDeschisa = null;
  $("#panou-tara").hidden = true;
  Glob.selecteaza(null);
}

async function ascultaTara(iso) {
  const text = stare.static
    ? stare.date.texte.tari[iso] || `Momentan nu am găsit știri despre ${Glob.numeTara(iso)}.`
    : (await fetch(`api/tara?iso=${encodeURIComponent(iso)}`).then((x) => x.json())).text;
  citeste(text,`<div class="bula raspuns"><small>Analiza țării · ${esc(Glob.numeTara(iso))}</small>`);
}

// ------------------------------------------------------------------
// Asistentul: citire cu voce, intrebari
// ------------------------------------------------------------------
function afiseazaInfoVoce() {
  const info = Voce.info();
  const el = $("#info-voce");
  if (info.motor === "neural" && info.neuralDisponibil) {
    el.textContent = `Voce neurală în limba română: ${info.voceNeurala === "emil" ? "Emil" : "Alina"}`;
  } else if (info.voceBrowser) {
    el.textContent = `Voce browser: ${info.voceBrowser}`;
  } else if (info.motor === "neural") {
    el.textContent = "Vocea neurală cere internet, iar browserul nu are voce română.";
  } else {
    el.textContent = "Browserul nu are voce română instalată – alege Alina sau Emil.";
  }
}

/** Setarile vocii sunt memorate in browser (localStorage). */
function configureazaSetariVoce() {
  const select = $("#select-voce"), viteza = $("#viteza-voce");
  try {
    select.value = localStorage.getItem("globepulse-voce") || "alina";
    viteza.value = localStorage.getItem("globepulse-viteza") || "0";
  } catch (e) { /* stocare indisponibila */ }
  const aplica = () => {
    if (select.value === "browser") Voce.seteazaMotor("browser");
    else { Voce.seteazaMotor("neural"); Voce.seteazaVoceNeurala(select.value); Voce.seteazaNeuralDisponibil(stare.date?.voce_neurala !== false); }
    Voce.seteazaViteza(viteza.value);
    try {
      localStorage.setItem("globepulse-voce", select.value);
      localStorage.setItem("globepulse-viteza", viteza.value);
    } catch (e) { /* stocare indisponibila */ }
    afiseazaInfoVoce();
  };
  select.addEventListener("change", aplica);
  viteza.addEventListener("change", aplica);
  aplica();
}

/** Afiseaza textul fraza cu fraza si il citeste, evidentiind fraza curenta. */
function citeste(text, inceputBula) {
  const fraze = Voce.imparte(text);
  const container = $("#text-asistent");
  const bulaNoua = `${inceputBula}${fraze.map((f, i) => `<span class="fraza" data-i="${i}">${esc(f)} </span>`).join("")}</div>`;
  const utilizator = container.querySelector(".bula.utilizator.curenta");
  container.innerHTML = (utilizator ? utilizator.outerHTML : "") + bulaNoua;
  container.scrollTop = 0;

  const pornit = Voce.vorbeste(text, {
    laFraza: (i) => {
      $$(".fraza", container).forEach((el) => el.classList.toggle("curenta", Number(el.dataset.i) === i));
      $(`.fraza[data-i="${i}"]`, container)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    },
    laFinal: () => $$(".fraza.curenta", container).forEach((el) => el.classList.remove("curenta")),
  });
  if (!pornit) afiseazaInfoVoce();
}

async function trimiteIntrebare(text) {
  text = text.trim();
  if (!text) return;
  if (/^(stop|opre[sș]te|taci|gata)\b/i.test(text)) { Voce.opreste(); return; }

  const container = $("#text-asistent");
  container.innerHTML = `<div class="bula utilizator curenta"><small>Tu</small>${esc(text)}</div>
    <div class="bula raspuns"><small>GlobePulse</small><span class="se-gandeste">Analizez știrile</span></div>`;
  Voce.opreste();
  Voce.seteazaStare("gandeste");
  try {
    const r = stare.static ? raspundeStatic(text) : await fetch("api/intrebare", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }),
    }).then((x) => x.json());
    Voce.seteazaStare("pregatit");
    if (r.eroare) throw new Error(r.eroare);
    if (r.tara) deschideTara(r.tara);
    if (r.categorie) { stare.tab = "stiri"; stare.filtruCategorie = r.categorie; randeazaTab(); }
    citeste(r.raspuns, `<div class="bula raspuns"><small>GlobePulse · ${esc(r.generat_de)}</small>`);
  } catch (eroare) {
    Voce.seteazaStare("pregatit");
    container.innerHTML += `<div class="bula raspuns">A apărut o eroare: ${esc(eroare.message)}</div>`;
  }
}

// ------------------------------------------------------------------
// Versiunea online: intelegerea intrebarilor direct in browser
// (aceeasi logica precum rezumat.py -> raspunde_offline)
// ------------------------------------------------------------------
const faraDiacritice = (text) => text.normalize("NFD").replace(/\p{M}/gu, "");
const CUVINTE_PIETE = ["piat", "piet", "bursa", "burse", "indic", "actiun", "bitcoin", "cripto", "aur", "petrol",
  "brent", "dolar", "euro", "curs", "leu", "lei", "cotat"];
const INSTRUMENTE_INTREBARI = { bitcoin: "Bitcoin", cripto: "Bitcoin", aur: "Aur", petrol: "Petrol Brent", brent: "Petrol Brent",
  dolar: "EUR/USD", leu: "EUR/RON", lei: "EUR/RON", euro: "EUR/RON", dax: "DAX", nasdaq: "Nasdaq", dow: "Dow Jones",
  "s&p": "S&P 500", nikkei: "Nikkei 225", ftse: "FTSE 100" };
const CATEGORII_INTREBARI = { politic: "Politică", alegeri: "Politică", guvern: "Politică", econom: "Economie",
  inflati: "Economie", dobanz: "Economie", energ: "Energie", gaze: "Energie", tehnolog: "Tehnologie",
  "inteligenta artificiala": "Tehnologie", razboi: "Geopolitică", geopolit: "Geopolitică", conflict: "Geopolitică",
  sanctiun: "Geopolitică", compan: "Companii", firme: "Companii", afaceri: "Companii" };
const CUVINTE_REZUMAT = ["rezumat", "ce se intampla", "noutati", "pe scurt", "briefing", "ce s-a intamplat",
  "ultimele stiri", "stirile zilei"];
const CUVINTE_DE_LEGATURA = new Set(("care este sunt pentru despre cum cele mai din prin doar fost acest aceasta acum " +
  "lui sau dar ale unei unui sub asupra are vor fie insa foarte inca spre pana intre fata catre peste azi stau spune " +
  "spui vreau ceva lumea zici stii ati").split(" "));

function detecteazaTaraStatic(intrebare) {
  const q = faraDiacritice(intrebare.toLowerCase());
  let gasita = null, pozitie = Infinity;
  for (const [iso, cuvinte] of Object.entries(stare.date.cuvinte_tari || {})) {
    for (const cuvant of cuvinte) {
      const prefix = cuvant.endsWith("*");
      const radacina = (prefix ? cuvant.slice(0, -1) : cuvant).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const potrivire = new RegExp(`(?<![a-z0-9])${radacina}${prefix ? "" : "(?![a-z0-9])"}`).exec(q);
      if (potrivire && potrivire.index < pozitie) { pozitie = potrivire.index; gasita = iso; }
    }
  }
  return gasita;
}

function raspundeStatic(intrebare) {
  const d = stare.date, texte = d.texte, q = faraDiacritice(intrebare.toLowerCase());
  const raspuns = (text, extra = {}) => ({ raspuns: text, generat_de: "algoritm local", ...extra });

  const tara = detecteazaTaraStatic(intrebare);
  if (tara) return raspuns(texte.tari[tara] || `Momentan nu am găsit știri despre ${Glob.numeTara(tara)}.`, { tara });

  if (CUVINTE_PIETE.some((c) => q.includes(c))) {
    const cuvinte = q.split(/[^a-z0-9&]+/);
    const ceruti = [...new Set(Object.entries(INSTRUMENTE_INTREBARI)
      .filter(([cheie]) => cuvinte.some((w) => w.startsWith(cheie) && !w.startsWith("europ")))
      .map(([, nume]) => nume))];
    return raspuns(ceruti.length === 1 && texte.instrumente[ceruti[0]] ? texte.instrumente[ceruti[0]] : texte.piete);
  }

  for (const [cheie, categorie] of Object.entries(CATEGORII_INTREBARI)) {
    if (q.includes(cheie) && texte.categorii[categorie]) return raspuns(texte.categorii[categorie], { categorie });
  }

  if (CUVINTE_REZUMAT.some((c) => q.includes(c)) || q.includes("stiri")) return raspuns(texte.rezumat);

  const termeni = (text) => new Set((faraDiacritice(text.toLowerCase()).match(/[a-z]{3,}/g) || [])
    .filter((c) => !CUVINTE_DE_LEGATURA.has(c)).map((c) => c.slice(0, 6)));
  const dinIntrebare = termeni(intrebare);
  const gasite = d.stiri
    .map((s) => [[...termeni(s.titlu)].filter((t) => dinIntrebare.has(t)).length, s])
    .filter(([scor]) => scor > 0).sort((a, b) => b[0] - a[0]).slice(0, 3);
  if (gasite.length) {
    return raspuns("Am găsit câteva știri legate de întrebarea ta: " +
      gasite.map(([, s]) => s.titlu.replace(/[ .!?;:]+$/, "")).join(". ") + ".");
  }
  return raspuns(texte.necunoscut);
}

// ------------------------------------------------------------------
// Evenimente
// ------------------------------------------------------------------
function configureazaEvenimente() {
  Voce.laSchimbare((s) => {
    const texte = { pregatit: "Pregătit", vorbeste: "Vorbește…", asculta: "Te ascult…", gandeste: "Mă gândesc…" };
    $("#stare-voce").textContent = texte[s] || s;
    $("#btn-microfon").classList.toggle("ascultare", s === "asculta");
    $("#btn-microfon").textContent = s === "asculta" ? "● Ascult" : "🎤 Întreabă";
    afiseazaInfoVoce();
  });

  $("#btn-rezumat").addEventListener("click", () => {
    const b = stare.date?.briefing;
    if (b) citeste(b.rezumat, `<div class="bula raspuns"><small>Rezumatul zilei · ${esc(b.generat_de)}</small>`);
  });
  $("#btn-stop").addEventListener("click", () => { Voce.opreste(); Voce.opresteAscultarea(); });

  $("#btn-microfon").addEventListener("click", () => {
    if (Voce.stare() === "asculta") { Voce.opresteAscultarea(); return; }
    const input = $("#input-intrebare");
    const pornit = Voce.asculta({
      laInterimar: (t) => { input.value = t; },
      laFinal: (t) => { input.value = ""; trimiteIntrebare(t); },
      laEroare: (e) => {
        $("#info-voce").textContent = e === "not-allowed" ? "Permite accesul la microfon din setările browserului." : `Eroare microfon: ${e}`;
      },
    });
    if (!pornit) $("#info-voce").textContent = "Recunoașterea vocală necesită Google Chrome sau Microsoft Edge. Poți scrie întrebarea.";
  });

  $("#form-intrebare").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("#input-intrebare");
    trimiteIntrebare(input.value);
    input.value = "";
  });

  $(".taburi nav").addEventListener("click", (e) => {
    const buton = e.target.closest("button[data-tab]");
    if (!buton || !stare.date) return;
    stare.tab = buton.dataset.tab;
    randeazaTab();
  });

  $("#filtre").addEventListener("click", (e) => {
    const buton = e.target.closest("button");
    if (!buton) return;
    if (buton.dataset.stergeCategorie) stare.filtruCategorie = null;
    else stare.filtruSursa = buton.dataset.sursa;
    randeazaTab();
  });

  // click pe eticheta unei tari, pe un rand din clasament sau pe o categorie
  document.addEventListener("click", (e) => {
    const tara = e.target.closest("[data-iso]");
    if (tara) { deschideTara(tara.dataset.iso); return; }
    const categorie = e.target.closest("[data-categorie]");
    if (categorie) { stare.tab = "stiri"; stare.filtruCategorie = categorie.dataset.categorie; randeazaTab(); return; }
    if (e.target.closest("#inchide-tara")) { inchideTara(); return; }
    if (e.target.closest("#asculta-tara") && stare.taraDeschisa) ascultaTara(stare.taraDeschisa);
  });

  $("#btn-rotire").addEventListener("click", (e) => {
    const activ = !e.currentTarget.classList.contains("activ");
    e.currentTarget.classList.toggle("activ", activ);
    Glob.rotire(activ);
  });
  $("#btn-legaturi").addEventListener("click", (e) => {
    const activ = !e.currentTarget.classList.contains("activ");
    e.currentTarget.classList.toggle("activ", activ);
    Glob.legaturiVizibile(activ);
  });

  $("#btn-actualizeaza").addEventListener("click", async (e) => {
    const buton = e.currentTarget;
    if (buton.classList.contains("roteste")) return;
    buton.classList.add("roteste");
    if (!stare.static) {
      await fetch("api/actualizeaza", { method: "POST" });
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const s = await fetch("api/stare").then((x) => x.json()).catch(() => null);
        if (s && !s.in_actualizare) break;
      }
    }
    await incarcaDate(true);
    buton.classList.remove("roteste");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { inchideTara(); Voce.opreste(); }
  });
}

porneste();
