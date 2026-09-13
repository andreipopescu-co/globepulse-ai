"""
Modul: colectare.py
---------------------------------------------------------------
Descarca stirile din sursele configurate (fluxuri RSS/Atom si
serviciul JSON TradingView), le curata si le aduce la un format comun:

  {id, titlu, descriere, link, data, sursa, sursa_id, limba}

Sursele sunt interogate in paralel, stirile duplicate sunt eliminate,
iar cele mai vechi de VECHIME_MAXIMA_ORE sunt ignorate.
"""
import hashlib
import html
import json
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import config

jurnal = logging.getLogger("globepulse.colectare")

_ETICHETA_HTML = re.compile(r"<[^>]+>")
_SPATII = re.compile(r"\s+")
# titluri care nu sunt stiri propriu-zise (editii tiparite, liste de titluri)
_TITLURI_IGNORATE = re.compile(r"\bepaper\b|headlines you may have missed", re.IGNORECASE)


def descarca(url, timeout=config.TIMEOUT_CERERI):
    """Descarca continutul unei adrese web si il returneaza ca bytes."""
    cerere = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(cerere, timeout=timeout) as raspuns:
        return raspuns.read()


def curata_text(text):
    """Elimina etichetele HTML, entitatile (&amp; ...) si spatiile multiple."""
    if not text:
        return ""
    text = html.unescape(_ETICHETA_HTML.sub(" ", html.unescape(text)))
    return _SPATII.sub(" ", text).strip()


def citeste_data(text):
    """Transforma o data RSS (RFC 822) sau ISO 8601 intr-un obiect datetime UTC."""
    if not text:
        return None
    text = text.strip()
    try:
        data = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            data = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    return data.astimezone(timezone.utc)


def creeaza_stire(titlu, descriere, link, data, sursa):
    return {
        "id": hashlib.sha1((link or titlu).encode("utf-8")).hexdigest()[:12],
        "titlu": titlu,
        "descriere": descriere[:400],
        "link": link,
        "data": data.isoformat() if data else None,
        "sursa": sursa["nume"],
        "sursa_id": sursa["id"],
        "limba": sursa.get("limba", "en"),
    }


def _nume_local(eticheta):
    """'{http://www.w3.org/2005/Atom}entry' -> 'entry'"""
    return eticheta.rsplit("}", 1)[-1]


def parseaza_rss(continut, sursa):
    """Extrage stirile dintr-un flux RSS 2.0 sau Atom."""
    radacina = ET.fromstring(continut)
    stiri = []
    for element in radacina.iter():
        if _nume_local(element.tag) not in ("item", "entry"):
            continue
        campuri = {}
        for copil in element:
            cheie = _nume_local(copil.tag)
            if cheie == "link" and copil.get("href"):
                campuri.setdefault("link", copil.get("href"))
            elif copil.text and cheie not in campuri:
                campuri[cheie] = copil.text
        titlu = curata_text(campuri.get("title"))
        if not titlu:
            continue
        descriere = curata_text(campuri.get("description") or campuri.get("summary") or "")
        data = citeste_data(campuri.get("pubDate") or campuri.get("published")
                            or campuri.get("updated") or campuri.get("date"))
        stiri.append(creeaza_stire(titlu, descriere, (campuri.get("link") or "").strip(), data, sursa))
    return stiri


def parseaza_tradingview(continut, sursa):
    """Extrage stirile din raspunsul JSON al serviciului de stiri TradingView."""
    date = json.loads(continut)
    stiri = []
    for articol in date.get("items", [])[:config.MAX_STIRI_TRADINGVIEW]:
        titlu = curata_text(articol.get("title"))
        if not titlu:
            continue
        link = articol.get("link") or ""
        if not link and articol.get("storyPath"):
            link = "https://www.tradingview.com" + articol["storyPath"]
        data = datetime.fromtimestamp(articol["published"], tz=timezone.utc) if articol.get("published") else None
        stire = creeaza_stire(titlu, "", link, data, sursa)
        stire["sursa_originala"] = articol.get("source") or ""
        stire["urgenta"] = articol.get("urgency")
        stire["simboluri"] = [s["symbol"] for s in articol.get("relatedSymbols", [])[:5] if s.get("symbol")]
        stiri.append(stire)
    return stiri


PARSERE = {"rss": parseaza_rss, "tradingview": parseaza_tradingview}


def colecteaza_sursa(sursa):
    """Descarca si parseaza o singura sursa. Erorile nu opresc aplicatia."""
    stare = {"id": sursa["id"], "nume": sursa["nume"], "ok": False, "nr": 0, "eroare": None}
    try:
        stiri = PARSERE[sursa["tip"]](descarca(sursa["url"]), sursa)
        stare.update(ok=True, nr=len(stiri))
        return stiri, stare
    except Exception as eroare:  # retea, format invalid etc. - sursa este doar marcata ca indisponibila
        jurnal.warning("Sursa %s indisponibila: %s", sursa["id"], eroare)
        stare["eroare"] = str(eroare)[:150]
        return [], stare


def colecteaza_stiri(surse):
    """Colecteaza stirile din toate sursele, in paralel."""
    with ThreadPoolExecutor(max_workers=8) as executor:
        rezultate = list(executor.map(colecteaza_sursa, surse))

    toate, stari = [], []
    for stiri, stare in rezultate:
        toate.extend(stiri)
        stari.append(stare)

    limita = datetime.now(timezone.utc) - timedelta(hours=config.VECHIME_MAXIMA_ORE)
    vazute, unice = set(), []
    for stire in sorted(toate, key=lambda s: s["data"] or "", reverse=True):
        cheie = re.sub(r"[\W_]+", "", stire["titlu"].lower())[:80]
        if cheie in vazute or _TITLURI_IGNORATE.search(stire["titlu"]):
            continue
        if stire["data"] and datetime.fromisoformat(stire["data"]) < limita:
            continue
        vazute.add(cheie)
        unice.append(stire)
    return unice[:config.MAX_STIRI], stari
