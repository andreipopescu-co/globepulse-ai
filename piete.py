"""
Modul: piete.py
---------------------------------------------------------------
Preia cotatiile principalilor indici bursieri, marfuri, criptomonede
si valute (serviciul public de grafice Yahoo Finance): pretul curent,
variatia fata de inchiderea anterioara si istoricul ultimei luni.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from colectare import descarca

jurnal = logging.getLogger("globepulse.piete")

INSTRUMENTE = [
    ("^GSPC", "S&P 500", "indice"),
    ("^IXIC", "Nasdaq", "indice"),
    ("^DJI", "Dow Jones", "indice"),
    ("^GDAXI", "DAX", "indice"),
    ("^FTSE", "FTSE 100", "indice"),
    ("^N225", "Nikkei 225", "indice"),
    ("BZ=F", "Petrol Brent", "marfă"),
    ("GC=F", "Aur", "marfă"),
    ("BTC-USD", "Bitcoin", "cripto"),
    ("EURUSD=X", "EUR/USD", "valută"),
    ("EURRON=X", "EUR/RON", "valută"),
    ("^VIX", "VIX", "indice"),
]


def _ziua(marcaj):
    return datetime.fromtimestamp(marcaj, tz=timezone.utc).date()


def preia_instrument(instrument):
    simbol, nume, tip = instrument
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(simbol)}?range=1mo&interval=1d"
        rezultat = json.loads(descarca(url))["chart"]["result"][0]
        meta = rezultat["meta"]
        inchideri = rezultat["indicators"]["quote"][0]["close"]
        puncte = [(t, c) for t, c in zip(rezultat.get("timestamp") or [], inchideri) if c is not None]
        if not puncte:
            return None
        pret = meta.get("regularMarketPrice") or puncte[-1][1]
        # daca ultima lumanare este chiar ziua curenta, comparam cu ziua precedenta
        if len(puncte) >= 2 and meta.get("regularMarketTime") and _ziua(puncte[-1][0]) == _ziua(meta["regularMarketTime"]):
            anterior = puncte[-2][1]
        else:
            anterior = puncte[-1][1]
        return {
            "simbol": simbol, "nume": nume, "tip": tip,
            "pret": round(pret, 4),
            "variatie": round((pret / anterior - 1) * 100, 2) if anterior else 0.0,
            "istoric": [round(c, 4) for _, c in puncte[-22:]],
            "moneda": meta.get("currency", ""),
            "sursa": "Yahoo Finance",
        }
    except Exception as eroare:  # un instrument indisponibil nu trebuie sa opreasca restul
        jurnal.warning("Cotatia %s indisponibila: %s", simbol, eroare)
        return None


# ------------------------------------------------------------------
# Surse de rezerva: API-uri publice oficiale, gratuite, fara cheie
# ------------------------------------------------------------------
def cursuri_frankfurter():
    """Cursurile de referinta ale Bancii Centrale Europene (api.frankfurter.dev)."""
    inceput = (datetime.now(timezone.utc) - timedelta(days=40)).date().isoformat()
    date = json.loads(descarca(f"https://api.frankfurter.dev/v1/{inceput}..?base=EUR&symbols=USD,RON"))
    zile = sorted(date["rates"].items())
    rezultat = []
    for moneda, nume in (("USD", "EUR/USD"), ("RON", "EUR/RON")):
        istoric = [valori[moneda] for _, valori in zile if moneda in valori]
        if len(istoric) >= 2:
            rezultat.append({"simbol": f"EUR{moneda}", "nume": nume, "tip": "valută", "pret": istoric[-1],
                             "variatie": round((istoric[-1] / istoric[-2] - 1) * 100, 2),
                             "istoric": istoric[-22:], "moneda": moneda, "sursa": "Frankfurter (BCE)"})
    return rezultat


def bitcoin_coingecko():
    """Pretul bitcoinului si istoricul pe 30 de zile (api.coingecko.com)."""
    istoric = json.loads(descarca(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=30&interval=daily"))["prices"]
    pret = json.loads(descarca(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"))["bitcoin"]
    return [{"simbol": "BTC", "nume": "Bitcoin", "tip": "cripto", "pret": pret["usd"],
             "variatie": round(pret["usd_24h_change"], 2), "istoric": [round(p, 2) for _, p in istoric[-22:]],
             "moneda": "USD", "sursa": "CoinGecko"}]


SURSE_REZERVA = [(cursuri_frankfurter, {"EUR/USD", "EUR/RON"}), (bitcoin_coingecko, {"Bitcoin"})]


def preia_piete():
    with ThreadPoolExecutor(max_workers=6) as executor:
        rezultate = [r for r in executor.map(preia_instrument, INSTRUMENTE) if r]
    gasite = {r["nume"] for r in rezultate}
    for functie, acoperite in SURSE_REZERVA:
        if acoperite - gasite:  # Yahoo nu a raspuns pentru aceste instrumente
            try:
                rezultate += [r for r in functie() if r["nume"] not in gasite]
            except Exception as eroare:
                jurnal.warning("Sursa de rezervă %s indisponibilă: %s", functie.__name__, eroare)
    ordine = {nume: i for i, (_, nume, _) in enumerate(INSTRUMENTE)}
    return sorted(rezultate, key=lambda r: ordine.get(r["nume"], len(ordine)))
