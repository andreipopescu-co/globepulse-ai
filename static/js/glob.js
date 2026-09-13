/* =====================================================================
   glob.js – globul 3D interactiv (biblioteca globe.gl, bazata pe three.js)
   Tarile sunt colorate dupa impactul stirilor, iar cele mai mediatizate
   sunt marcate cu unde animate, etichete si arce de legatura.
   ===================================================================== */
"use strict";

const Glob = (() => {
  let globe = null, element = null;
  let tari = {}, legaturi = [];
  let selectat = null, survolat = null;
  let arataLegaturi = true, rotireActiva = true, temporizator = null;
  let laClick = () => {};
  const dupaIso = new Map();
  const numeRegiuni = window.Intl?.DisplayNames ? new Intl.DisplayNames(["ro"], { type: "region" }) : null;

  // ADM0_A3 din fisierul GeoJSON corespunde codului ISO3 (cu mici exceptii)
  const isoDin = (f) => ({ SDS: "SSD", KOS: "XKX" }[f.properties.ADM0_A3] || f.properties.ADM0_A3);

  function numeDin(f) {
    const iso = isoDin(f);
    if (tari[iso]) return tari[iso].nume;
    const a2 = f.properties.ISO_A2;
    try { if (numeRegiuni && a2 && a2 !== "-99") return numeRegiuni.of(a2); } catch (e) { /* cod necunoscut */ }
    return f.properties.NAME;
  }

  function culoareCapac(f) {
    const iso = isoDin(f), t = tari[iso];
    const evidentiat = f === survolat || iso === selectat;
    if (!t) return evidentiat ? "rgba(56,189,248,0.35)" : "rgba(100,116,139,0.10)";
    const alfa = evidentiat ? 0.95 : 0.4 + 0.5 * Math.min(1, t.intensitate + (t.nr_stiri > 0 ? 0.15 : 0));
    return culoareImpact(t.impact, alfa);
  }

  function altitudine(f) {
    const iso = isoDin(f), t = tari[iso];
    let a = t ? 0.01 + 0.07 * Math.min(1, t.intensitate * 0.7 + Math.abs(t.impact) * 0.5) : 0.004;
    if (f === survolat || iso === selectat) a += 0.03;
    return a;
  }

  function eticheta(f) {
    const iso = isoDin(f), t = tari[iso], nume = esc(numeDin(f));
    if (!t) return `<div class="tooltip-glob"><b>${nume}</b><br><span style="color:#8b9bb4">Fără știri recente</span></div>`;
    const regionale = t.stiri_regionale ? ` · ${t.stiri_regionale} despre UE` : "";
    return `<div class="tooltip-glob"><b>${nume}</b><br>
      Impact: <b style="color:${culoareImpact(t.impact)}">${cuSemn(t.impact)}</b> · ${esc(descriereImpact(t.impact))}<br>
      ${t.nr_stiri} știri${regionale}<br><span style="color:#22d3ee">Click pentru detalii</span></div>`;
  }

  function reimprospateaza() {
    if (!globe) return;
    // functii noi => globe.gl recalculeaza culorile si altitudinile
    globe.polygonCapColor((f) => culoareCapac(f)).polygonAltitude((f) => altitudine(f));
  }

  function pauzaRotire() {
    if (!globe) return;
    globe.controls().autoRotate = false;
    clearTimeout(temporizator);
    temporizator = setTimeout(() => {
      if (rotireActiva && !selectat) globe.controls().autoRotate = true;
    }, 15000);
  }

  async function init(el, onClick) {
    element = el;
    laClick = onClick;
    if (typeof Globe === "undefined") throw new Error("Biblioteca globe.gl nu a putut fi încărcată.");

    const geo = await fetch("static/date/tari.geojson").then((r) => r.json());
    const caracteristici = geo.features.filter((f) => f.properties.ADM0_A3 !== "ATA");
    caracteristici.forEach((f) => dupaIso.set(isoDin(f), f));

    globe = Globe({ animateIn: true })(el)
      .width(el.clientWidth).height(el.clientHeight)
      .backgroundImageUrl("static/vendor/night-sky.png")
      .globeImageUrl("static/vendor/earth-night.jpg")
      .bumpImageUrl("static/vendor/earth-topology.png")
      .showAtmosphere(true).atmosphereColor("#38bdf8").atmosphereAltitude(0.22)
      // tarile
      .polygonsData(caracteristici)
      .polygonCapColor(culoareCapac).polygonAltitude(altitudine)
      .polygonSideColor(() => "rgba(8,15,30,0.55)").polygonStrokeColor(() => "rgba(148,163,184,0.28)")
      .polygonLabel(eticheta).polygonsTransitionDuration(500)
      .onPolygonHover((f) => { survolat = f; el.style.cursor = f ? "pointer" : "grab"; reimprospateaza(); })
      .onPolygonClick((f) => laClick(isoDin(f)))
      // undele animate din tarile cele mai mediatizate
      .ringColor((d) => (t) => `rgba(${d.rgb},${Math.max(0, 1 - t)})`)
      .ringAltitude(0.085)  // deasupra tarilor ridicate, altfel undele ar fi ascunse
      .ringMaxRadius("raza").ringPropagationSpeed("viteza").ringRepeatPeriod("perioada")
      // arcele dintre tarile mentionate impreuna
      .arcColor("culori").arcStroke("grosime").arcAltitudeAutoScale(0.45)
      .arcDashLength(0.4).arcDashGap(0.2).arcDashInitialGap(() => Math.random()).arcDashAnimateTime(() => 2200 + Math.random() * 1500)
      // etichetele
      .labelLat("lat").labelLng("lng").labelText("nume").labelAltitude(0.09).labelResolution(2)
      .labelSize((d) => 0.9 + d.pondere * 0.9).labelDotRadius((d) => 0.35 + d.pondere * 0.45)
      .labelColor(() => "rgba(229,237,247,0.92)")
      .onLabelClick((d) => laClick(d.iso3));

    globe.pointOfView({ lat: 35, lng: 15, altitude: 2.2 });
    const controale = globe.controls();
    controale.autoRotate = true;
    controale.autoRotateSpeed = 0.35;
    controale.addEventListener("start", pauzaRotire);
    new ResizeObserver(() => globe.width(el.clientWidth).height(el.clientHeight)).observe(el);
  }

  function aplicaLegaturi() {
    if (!globe) return;
    const maxim = Math.max(1, ...legaturi.map((l) => l.nr));
    globe.arcsData(arataLegaturi ? legaturi.map((l) => {
      const neutru = Math.abs(l.sentiment) < 0.05;
      return {
        startLat: l.lat1, startLng: l.lng1, endLat: l.lat2, endLng: l.lng2,
        culori: neutru ? ["rgba(34,211,238,0.12)", "rgba(34,211,238,0.9)"] : [culoareImpact(l.sentiment, 0.15), culoareImpact(l.sentiment, 0.95)],
        grosime: 0.25 + 0.9 * (l.nr / maxim),
      };
    }) : []);
  }

  function actualizeaza(dateTari, dateLegaturi) {
    tari = dateTari || {};
    legaturi = dateLegaturi || [];
    if (!globe) return;
    reimprospateaza();
    const lista = Object.values(tari).filter((t) => t.nr_stiri > 0 && t.iso3 !== "EUU");
    const maxim = Math.max(1, ...lista.map((t) => t.nr_stiri));
    const top = [...lista].sort((a, b) => b.nr_stiri - a.nr_stiri).slice(0, 12);
    globe.ringsData(top.slice(0, 8).map((t) => ({
      // culoare mai deschisa decat a tarii, ca undele sa se vada peste ea
      lat: t.lat, lng: t.lng, rgb: rgbImpact(t.impact).split(",").map((c) => Math.round((Number(c) + 255) / 2)).join(","),
      raza: 3 + 6 * (t.nr_stiri / maxim),
      viteza: 1.5 + Math.abs(t.impact) * 2,
      perioada: 1400 - 600 * Math.abs(t.impact),
    })));
    globe.labelsData(top.map((t) => ({ ...t, pondere: t.nr_stiri / maxim })));
    aplicaLegaturi();
  }

  function centru(f) {
    let minX = 180, maxX = -180, minY = 90, maxY = -90;
    const parcurge = (c) => {
      if (typeof c[0] === "number") {
        minX = Math.min(minX, c[0]); maxX = Math.max(maxX, c[0]);
        minY = Math.min(minY, c[1]); maxY = Math.max(maxY, c[1]);
      } else c.forEach(parcurge);
    };
    parcurge(f.geometry.coordinates);
    return { lat: (minY + maxY) / 2, lng: (minX + maxX) / 2 };
  }

  function zboaraLa(iso) {
    if (!globe) return;
    const pozitie = tari[iso] || (dupaIso.has(iso) ? centru(dupaIso.get(iso)) : null);
    if (!pozitie) return;
    globe.controls().autoRotate = false;
    globe.pointOfView({ lat: pozitie.lat, lng: pozitie.lng, altitude: 1.55 }, 1400);
  }

  function selecteaza(iso) {
    selectat = iso;
    reimprospateaza();
    if (!iso) pauzaRotire();
  }

  function rotire(activa) {
    rotireActiva = activa;
    if (globe) globe.controls().autoRotate = activa && !selectat;
  }

  function legaturiVizibile(vizibile) {
    arataLegaturi = vizibile;
    aplicaLegaturi();
  }

  function numeTara(iso) {
    if (tari[iso]) return tari[iso].nume;
    return dupaIso.has(iso) ? numeDin(dupaIso.get(iso)) : iso;
  }

  return { init, actualizeaza, zboaraLa, selecteaza, rotire, legaturiVizibile, numeTara };
})();
