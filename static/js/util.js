/* =====================================================================
   util.js – functii ajutatoare folosite de toate modulele
   ===================================================================== */
"use strict";

const $ = (selector, parinte = document) => parinte.querySelector(selector);
const $$ = (selector, parinte = document) => [...parinte.querySelectorAll(selector)];

/** Protectie XSS: textul venit din surse externe nu este interpretat ca HTML. */
function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/** Acceptam doar legaturi http(s) – blocheaza adrese de tip "javascript:". */
function linkSigur(url) {
  return /^https?:\/\//i.test(url || "") ? url : "#";
}

const nrRo = (valoare, zecimale = 1) => Number(valoare || 0).toFixed(zecimale).replace(".", ",");
const cuSemn = (valoare, zecimale = 2) => (valoare > 0 ? "+" : "") + nrRo(valoare, zecimale);

/** Culoarea impactului: rosu (-1) -> gri (0) -> verde (+1). */
function rgbImpact(valoare) {
  const neutru = [100, 116, 139], rosu = [244, 63, 94], verde = [34, 197, 94];
  const v = Math.max(-1, Math.min(1, valoare || 0));
  const tinta = v < 0 ? rosu : verde;
  const k = Math.min(1, Math.abs(v) * 1.6);
  return neutru.map((n, i) => Math.round(n + (tinta[i] - n) * k)).join(",");
}
const culoareImpact = (valoare, alfa = 1) => `rgba(${rgbImpact(valoare)},${alfa})`;

function descriereImpact(v) {
  if (v <= -0.5) return "impact negativ puternic";
  if (v <= -0.2) return "impact negativ moderat";
  if (v < -0.05) return "impact ușor negativ";
  if (v <= 0.05) return "impact neutru";
  if (v < 0.2) return "impact ușor pozitiv";
  if (v < 0.5) return "impact pozitiv moderat";
  return "impact pozitiv puternic";
}

function descriereSentiment(v) {
  if (v <= -0.35) return "puternic negativ";
  if (v <= -0.12) return "negativ";
  if (v < -0.03) return "ușor negativ";
  if (v <= 0.03) return "neutru";
  if (v < 0.12) return "ușor pozitiv";
  if (v < 0.35) return "pozitiv";
  return "puternic pozitiv";
}

function timpRelativ(iso) {
  if (!iso) return "";
  const minute = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
  if (minute < 1) return "acum";
  if (minute < 60) return `acum ${minute} min`;
  if (minute < 1440) return `acum ${Math.round(minute / 60)} h`;
  return `acum ${Math.round(minute / 1440)} z`;
}

const CULORI_SURSE = {
  "Bloomberg": "#a78bfa",
  "TradingView": "#38bdf8",
  "Baha News": "#fb923c",
  "CNBC": "#60a5fa",
  "Profit.ro": "#4ade80",
  "Ziarul Financiar": "#f472b6",
  "Biziday": "#fbbf24",
};

const ICONITE_CATEGORII = {
  "Piețe": "📈", "Economie": "🏦", "Politică": "🏛️", "Geopolitică": "🌐", "Energie": "🛢️",
  "Tehnologie": "💻", "Companii": "🏢", "Cripto": "₿", "General": "📰",
};

/** Canvas clar si pe ecrane cu densitate mare de pixeli. */
function pregatesteCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const latime = canvas.clientWidth, inaltime = canvas.clientHeight;
  canvas.width = latime * dpr;
  canvas.height = inaltime * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, latime, inaltime };
}

/** Animatia unui numar de la valoarea curenta la valoarea tinta. */
function animaNumar(element, tinta, durata = 900) {
  const start = Number(element.dataset.valoare || 0);
  const t0 = performance.now();
  const pas = (acum) => {
    const p = Math.min(1, (acum - t0) / durata);
    const e = 1 - Math.pow(1 - p, 3);
    element.textContent = Math.round(start + (tinta - start) * e);
    if (p < 1) requestAnimationFrame(pas);
  };
  element.dataset.valoare = tinta;
  requestAnimationFrame(pas);
}
