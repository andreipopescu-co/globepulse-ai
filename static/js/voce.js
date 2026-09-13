/* =====================================================================
   voce.js – vorbirea asistentului si recunoasterea vocala.

   Doua "motoare" pentru citirea cu voce tare:
     * neural  – vocile romanesti Alina / Emil, generate de server
                 (/api/voce) si redate ca fisiere audio MP3;
     * browser – vocea sistemului (Web Speech API), folosita automat
                 daca vocea neurala nu este disponibila.
   Recunoasterea vorbirii (voce -> text) foloseste Web Speech API.
   ===================================================================== */
"use strict";

const Voce = (() => {
  const sinteza = window.speechSynthesis || null;
  const Recunoastere = window.SpeechRecognition || window.webkitSpeechRecognition || null;

  let motor = "neural";            // neural | browser
  let voceNeurala = "alina";       // alina | emil
  let viteza = 0;                  // procente: -30 ... +30
  let neuralDisponibil = true;
  let voceBrowser = null;
  let stare = "pregatit";          // pregatit | vorbeste | asculta | gandeste
  let sesiune = 0;                 // o citire noua le anuleaza pe cele vechi
  let recunoastereActiva = null;
  let anuleazaRedare = null;
  const ascultatori = [];

  const notifica = () => ascultatori.forEach((f) => f(stare));
  function seteazaStare(noua) { stare = noua; notifica(); }

  // ---------------- vocea browserului ----------------
  function alegeVoceBrowser() {
    if (!sinteza) return;
    const romanesti = sinteza.getVoices().filter((v) => v.lang.toLowerCase().startsWith("ro"));
    voceBrowser = romanesti.find((v) => /natural|online/i.test(v.name)) || romanesti[0] || null;
    notifica();
  }
  if (sinteza) {
    alegeVoceBrowser();
    sinteza.addEventListener?.("voiceschanged", alegeVoceBrowser);
  }

  /** Imparte textul in fraze: fiecare fraza este citita si evidentiata separat. */
  function imparte(text) {
    return (String(text).match(/[^.!?…]+[.!?…]*["”»]?/g) || []).map((f) => f.trim()).filter(Boolean);
  }

  function vorbesteBrowser(fraze, id, laFraza, laFinal, start = 0) {
    if (!sinteza) { seteazaStare("pregatit"); return false; }
    let i = start;
    const urmatoarea = () => {
      if (id !== sesiune) return;
      if (i >= fraze.length) { seteazaStare("pregatit"); laFinal(); return; }
      const rostire = new SpeechSynthesisUtterance(fraze[i]);
      rostire.lang = voceBrowser ? voceBrowser.lang : "ro-RO";
      if (voceBrowser) rostire.voice = voceBrowser;
      rostire.rate = 1 + viteza / 100;
      const index = i;
      rostire.onstart = () => id === sesiune && laFraza(index);
      rostire.onend = () => { i++; urmatoarea(); };
      rostire.onerror = (e) => { if (e.error !== "interrupted" && e.error !== "canceled") { i++; urmatoarea(); } };
      sinteza.speak(rostire);
    };
    setTimeout(urmatoarea, 80); // unele browsere ignora o rostire lansata imediat dupa cancel()
    return true;
  }

  // ---------------- vocea neurala (audio generat de server) ----------------
  const audio = new Audio();
  let contextAudio = null, analizor = null, esantioane = null;

  /** Analizorul audio masoara volumul real al vocii, pentru animatia orb-ului. */
  function pregatesteAnaliza() {
    if (contextAudio || !window.AudioContext) return;
    try {
      contextAudio = new AudioContext();
      const sursa = contextAudio.createMediaElementSource(audio);
      analizor = contextAudio.createAnalyser();
      analizor.fftSize = 512;
      esantioane = new Uint8Array(analizor.fftSize);
      sursa.connect(analizor);
      analizor.connect(contextAudio.destination);
    } catch (e) {
      contextAudio = null;
    }
  }

  function nivel() {
    if (!analizor || audio.paused) return null;
    analizor.getByteTimeDomainData(esantioane);
    let suma = 0;
    for (const v of esantioane) { const x = (v - 128) / 128; suma += x * x; }
    return Math.min(1, Math.sqrt(suma / esantioane.length) * 4);
  }

  let audioStatic = null;          // versiunea online: fraza -> fisier MP3 pregenerat
  const audioGenerat = new Map();  // cheie -> Promise<adresa obiectului audio>
  function audioPentru(text) {
    if (audioStatic) {
      if (audioStatic[text]) return Promise.resolve(audioStatic[text]);
      const eroare = new Error("fraza nu are audio pregenerat");
      eroare.lipsa = true;
      return Promise.reject(eroare);
    }
    const cheie = `${voceNeurala}|${viteza}|${text}`;
    if (!audioGenerat.has(cheie)) {
      const promisiune = fetch("api/voce", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voce: voceNeurala, viteza }),
      }).then((r) => {
        if (!r.ok) throw new Error("sinteza vocală indisponibilă");
        return r.blob();
      }).then((blob) => URL.createObjectURL(blob));
      promisiune.catch(() => audioGenerat.delete(cheie));
      audioGenerat.set(cheie, promisiune);
      if (audioGenerat.size > 150) {
        const [celMaiVechi, p] = audioGenerat.entries().next().value;
        audioGenerat.delete(celMaiVechi);
        p.then((adresa) => URL.revokeObjectURL(adresa)).catch(() => {});
      }
    }
    return audioGenerat.get(cheie);
  }

  async function vorbesteNeural(fraze, id, laFraza, laFinal, pozitie) {
    pregatesteAnaliza();
    if (contextAudio?.state === "suspended") contextAudio.resume();
    const pregateste = (f) => audioPentru(f).catch(() => {});
    fraze.slice(0, 3).forEach(pregateste); // pregatim in avans primele fraze
    for (let i = 0; i < fraze.length; i++) {
      pozitie.index = i;
      const adresa = await audioPentru(fraze[i]);
      fraze.slice(i + 1, i + 3).forEach(pregateste);
      if (id !== sesiune) return;
      audio.src = adresa;
      // online, viteza se regleaza la redare (fisierele sunt generate la viteza normala)
      audio.playbackRate = audioStatic ? 1 + viteza / 100 : 1;
      laFraza(i);
      await new Promise((rezolva, respinge) => {
        anuleazaRedare = rezolva;
        audio.onended = rezolva;
        audio.onerror = () => respinge(new Error("redare audio eșuată"));
        audio.play().catch(respinge);
      });
      if (id !== sesiune) return;
    }
    seteazaStare("pregatit");
    laFinal();
  }

  // ---------------- interfata publica ----------------
  function vorbeste(text, { laFraza = () => {}, laFinal = () => {} } = {}) {
    opreste();
    const id = ++sesiune;
    const fraze = imparte(text);
    if (!fraze.length) return false;
    seteazaStare("vorbeste");

    if (motor === "neural" && neuralDisponibil) {
      const pozitie = { index: 0 };
      vorbesteNeural(fraze, id, laFraza, laFinal, pozitie).catch((eroare) => {
        if (id !== sesiune) return;
        if (eroare.name === "NotAllowedError") { seteazaStare("pregatit"); return; } // redare blocata fara click
        if (eroare.lipsa) { vorbesteBrowser(fraze, id, laFraza, laFinal, pozitie.index); return; } // doar pentru acest text
        console.warn("Vocea neurală nu este disponibilă – se folosește vocea browserului.", eroare);
        neuralDisponibil = false;
        notifica();
        vorbesteBrowser(fraze, id, laFraza, laFinal, pozitie.index);
      });
      return true;
    }
    return vorbesteBrowser(fraze, id, laFraza, laFinal);
  }

  function opreste() {
    sesiune++;
    audio.pause();
    if (anuleazaRedare) { anuleazaRedare(); anuleazaRedare = null; }
    if (sinteza) sinteza.cancel();
    if (stare === "vorbeste") seteazaStare("pregatit");
  }

  function asculta({ laInterimar = () => {}, laFinal = () => {}, laEroare = () => {} } = {}) {
    if (!Recunoastere) return false;
    opreste();
    const r = new Recunoastere();
    r.lang = "ro-RO";
    r.interimResults = true;
    r.maxAlternatives = 1;
    let trimis = false;
    r.onresult = (e) => {
      let text = "", final = false;
      for (const rezultat of e.results) {
        text += rezultat[0].transcript;
        if (rezultat.isFinal) final = true;
      }
      laInterimar(text);
      if (final && !trimis) { trimis = true; laFinal(text); }
    };
    r.onerror = (e) => { seteazaStare("pregatit"); laEroare(e.error); };
    r.onend = () => { recunoastereActiva = null; if (stare === "asculta") seteazaStare("pregatit"); };
    recunoastereActiva = r;
    r.start();
    seteazaStare("asculta");
    return true;
  }

  return {
    vorbeste, opreste, asculta, imparte, seteazaStare, nivel,
    opresteAscultarea: () => recunoastereActiva?.stop(),
    stare: () => stare,
    laSchimbare: (f) => ascultatori.push(f),
    seteazaMotor: (m) => { motor = m; notifica(); },
    seteazaVoceNeurala: (v) => { voceNeurala = v; notifica(); },
    seteazaViteza: (v) => { viteza = Number(v) || 0; },
    seteazaNeuralDisponibil: (d) => { neuralDisponibil = d; notifica(); },
    seteazaAudioStatic: (index) => { audioStatic = index; },
    info: () => ({
      motor, voceNeurala, neuralDisponibil,
      sinteza: !!sinteza, recunoastere: !!Recunoastere, voceBrowser: voceBrowser ? voceBrowser.name : null,
    }),
  };
})();


/* ---------------------------------------------------------------------
   Orb – animatia asistentului: forme ondulate care "respira" in asteptare
   si pulseaza dupa volumul real al vocii cand asistentul vorbeste.
   --------------------------------------------------------------------- */
const Orb = (() => {
  const CULORI = {
    pregatit: ["#22d3ee", "#7c3aed"],
    vorbeste: ["#a78bfa", "#22d3ee"],
    asculta: ["#f43f5e", "#fb923c"],
    gandeste: ["#fbbf24", "#22d3ee"],
  };
  let ctx, L, H, amplitudine = 0;

  function cadru(acum) {
    const t = acum / 1000;
    const stare = Voce.stare();
    const volum = Voce.nivel();
    const tinta = stare === "vorbeste"
      ? (volum !== null ? 0.25 + 0.75 * volum : 0.55 + 0.45 * Math.abs(Math.sin(t * 7.3) * Math.sin(t * 3.1)))
      : stare === "asculta" ? 0.45 + 0.2 * Math.sin(t * 9)
      : stare === "gandeste" ? 0.32 : 0.12;
    amplitudine += (tinta - amplitudine) * 0.15;

    const [c1, c2] = CULORI[stare] || CULORI.pregatit;
    const cx = L / 2, cy = H / 2, R = L * 0.27;
    ctx.clearRect(0, 0, L, H);

    const halo = ctx.createRadialGradient(cx, cy, R * 0.3, cx, cy, R * 1.85);
    halo.addColorStop(0, c1 + "55");
    halo.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = halo;
    ctx.fillRect(0, 0, L, H);

    for (let strat = 2; strat >= 0; strat--) {
      ctx.beginPath();
      for (let i = 0; i <= 72; i++) {
        const a = (i / 72) * Math.PI * 2;
        const r = R * (1 + strat * 0.07
          + amplitudine * 0.2 * Math.sin(a * (3 + strat) + t * (1.4 + strat * 0.6))
          + amplitudine * 0.1 * Math.sin(a * (5 + strat) - t * 2.2));
        const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.closePath();
      const gradient = ctx.createLinearGradient(cx - R, cy - R, cx + R, cy + R);
      gradient.addColorStop(0, c1);
      gradient.addColorStop(1, c2);
      ctx.globalAlpha = strat === 0 ? 0.95 : 0.28;
      ctx.fillStyle = gradient;
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    const luciu = ctx.createRadialGradient(cx - R * 0.35, cy - R * 0.4, 1, cx - R * 0.35, cy - R * 0.4, R * 0.7);
    luciu.addColorStop(0, "rgba(255,255,255,0.55)");
    luciu.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = luciu;
    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.95, 0, Math.PI * 2);
    ctx.fill();
    requestAnimationFrame(cadru);
  }

  function porneste(canvas) {
    ({ ctx, latime: L, inaltime: H } = pregatesteCanvas(canvas));
    requestAnimationFrame(cadru);
  }
  return { porneste };
})();
