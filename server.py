"""
GlobePulse AI - serverul aplicatiei (programul principal)
---------------------------------------------------------------
Porneste un server web local care:
  * colecteaza periodic stirile si cotatiile bursiere;
  * le analizeaza si genereaza rezumatul (cu Claude sau local);
  * ofera o interfata API folosita de pagina web (glob 3D + asistent vocal).

Rulare:   python server.py            (date reale, necesita internet)
          python server.py --demo     (date salvate, fara internet)
"""
import argparse
import json
import logging
import mimetypes
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import config
from ai import AsistentAI
from analiza import agrega_categorii, agrega_tari, analizeaza_stiri, calculeaza_legaturi, sentiment_general
from colectare import colecteaza_stiri
from piete import preia_piete
from rezumat import genereaza_rezumat_offline
from sinteza_vocala import SintezaVocala
from tari import TARI

jurnal = logging.getLogger("globepulse")

for extensie, tip in ((".js", "application/javascript"), (".css", "text/css"), (".geojson", "application/json"),
                      (".json", "application/json"), (".svg", "image/svg+xml"), (".png", "image/png"),
                      (".jpg", "image/jpeg")):
    mimetypes.add_type(tip, extensie)


# ------------------------------------------------------------------
# Prelucrarea datelor
# ------------------------------------------------------------------
def aplica_rezumat_ai(date, rezumat_ai):
    """Inlocuieste rezumatul local si impactul pe tari cu evaluarile modelului AI."""
    date["briefing"] = {k: rezumat_ai[k] for k in ("rezumat", "puncte_cheie", "generat_de", "generat_la")}
    date["sentiment_ai"] = rezumat_ai["sentiment_general"]
    for iso, evaluare in rezumat_ai["tari"].items():
        if iso not in TARI:
            continue
        if iso not in date["tari"]:
            nume, lat, lng, _ = TARI[iso]
            date["tari"][iso] = {"iso3": iso, "nume": nume, "lat": lat, "lng": lng, "nr_stiri": 0,
                                 "stiri_regionale": 0, "impact": 0.0, "intensitate": 0.1, "categorii": [], "stiri": []}
        tara = date["tari"][iso]
        tara["impact_algoritm"] = tara["impact"]
        tara["impact"] = round(evaluare["impact"], 3)
        tara["explicatie"] = evaluare["explicatie"]


def proceseaza(stiri, surse, piete, asistent, rezumat_ai=None, cere_ai=False):
    stiri = analizeaza_stiri(stiri)
    date = {
        "actualizat": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "surse": surse,
        "stiri": stiri,
        "tari": agrega_tari(stiri),
        "legaturi": calculeaza_legaturi(stiri),
        "categorii": agrega_categorii(stiri),
        "sentiment_general": sentiment_general(stiri),
        "piete": piete,
    }
    if cere_ai:
        rezumat_ai = asistent.genereaza_rezumat(date)
    if rezumat_ai:
        aplica_rezumat_ai(date, rezumat_ai)
    else:
        date["briefing"] = genereaza_rezumat_offline(date)
    return date, rezumat_ai


class StareAplicatie:
    def __init__(self, demo=False):
        self.demo = demo
        self.asistent = AsistentAI()
        self.voce = SintezaVocala()
        self.date = None
        self.in_actualizare = False
        self.rezumat_ai = None
        self.moment_ai = 0.0
        self._blocare = threading.Lock()

    def _publica(self, date):
        date.update(mod_ai=self.asistent.mod, motiv_offline=self.asistent.motiv, demo=self.demo,
                    nume_model=config.NUME_MODEL_AI, voce_neurala=self.voce.disponibila)
        self.date = date

    def _citeste(self, cale):
        with open(cale, encoding="utf-8") as fisier:
            brut = json.load(fisier)
        return brut["stiri"], brut["surse"], brut.get("piete", [])

    def incarca_initial(self):
        """Afiseaza imediat datele salvate anterior, pana la prima colectare."""
        cai = [config.CALE_DEMO] if self.demo else [config.CALE_CACHE, config.CALE_DEMO]
        for cale in cai:
            if os.path.exists(cale):
                date, _ = proceseaza(*self._citeste(cale), self.asistent)
                self._publica(date)
                jurnal.info("Date inițiale încărcate din %s (%d știri)", os.path.basename(cale), len(date["stiri"]))
                return
        date, _ = proceseaza([], [], [], self.asistent)
        self._publica(date)

    def actualizeaza(self, fortat=False):
        if not self._blocare.acquire(blocking=False):
            return  # o actualizare este deja in curs
        self.in_actualizare = True
        try:
            if self.demo:
                stiri, surse, piete = self._citeste(config.CALE_DEMO)
            else:
                jurnal.info("Se colectează știrile...")
                stiri, surse = colecteaza_stiri(config.SURSE)
                piete = preia_piete() or (self.date or {}).get("piete", [])
                if not stiri:
                    jurnal.warning("Nicio știre colectată - se păstrează datele anterioare.")
                    if self.date:
                        self.date["surse"] = surse
                    return

            cere_ai = self.asistent.mod == "claude" and (fortat or time.time() - self.moment_ai > config.INTERVAL_AI)
            date, rezumat_ai = proceseaza(stiri, surse, piete, self.asistent, self.rezumat_ai, cere_ai)
            if cere_ai and rezumat_ai:
                self.rezumat_ai, self.moment_ai = rezumat_ai, time.time()
            self._publica(date)
            jurnal.info("Actualizare completă: %d știri, %d țări, rezumat: %s",
                        len(date["stiri"]), len(date["tari"]), date["briefing"]["generat_de"])

            if not self.demo:
                with open(config.CALE_CACHE, "w", encoding="utf-8") as fisier:
                    json.dump({"stiri": stiri, "surse": surse, "piete": piete, "actualizat": date["actualizat"]},
                              fisier, ensure_ascii=False)
        finally:
            self.in_actualizare = False
            self._blocare.release()


# ------------------------------------------------------------------
# Serverul HTTP
# ------------------------------------------------------------------
class CereriHTTP(BaseHTTPRequestHandler):
    stare: StareAplicatie = None

    def log_message(self, format, *args):
        pass  # fara mesaje pentru fiecare cerere

    def _trimite(self, cod, continut, tip, cache="no-store"):
        self.send_response(cod)
        self.send_header("Content-Type", tip)
        self.send_header("Content-Length", str(len(continut)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(continut)

    def _json(self, obiect, cod=200):
        self._trimite(cod, json.dumps(obiect, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _fisier_static(self, cale_relativa):
        radacina = os.path.realpath(config.DIR_STATIC)
        cale = os.path.realpath(os.path.join(radacina, cale_relativa))
        # protectie: nu permitem accesul in afara folderului static ("../")
        if not cale.startswith(radacina + os.sep) or not os.path.isfile(cale):
            return self._json({"eroare": "Fișierul nu există"}, 404)
        tip = mimetypes.guess_type(cale)[0] or "application/octet-stream"
        if tip.startswith("text/") or tip in ("application/javascript", "application/json"):
            tip += "; charset=utf-8"
        with open(cale, "rb") as fisier:
            continut = fisier.read()
        self._trimite(200, continut, tip, "public, max-age=86400" if "vendor" in cale_relativa else "no-cache")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._fisier_static("index.html")
        if url.path.startswith("/static/"):
            return self._fisier_static(unquote(url.path[len("/static/"):]))
        if url.path == "/api/date":
            return self._json(self.stare.date)
        if url.path == "/api/stare":
            return self._json({"in_actualizare": self.stare.in_actualizare, "actualizat": self.stare.date["actualizat"],
                               "mod_ai": self.stare.asistent.mod})
        if url.path == "/api/tara":
            iso = parse_qs(url.query).get("iso", [""])[0].upper()[:3]
            return self._json({"iso": iso, "text": self.stare.asistent.rezumat_tara(iso, self.stare.date)})
        return self._json({"eroare": "Adresă necunoscută"}, 404)

    def do_POST(self):
        url = urlparse(self.path)
        lungime = min(int(self.headers.get("Content-Length") or 0), 10_000)
        corp = self.rfile.read(lungime) if lungime else b""
        if url.path == "/api/actualizeaza":
            threading.Thread(target=self.stare.actualizeaza, kwargs={"fortat": True}, daemon=True).start()
            return self._json({"ok": True})
        if url.path == "/api/intrebare":
            try:
                text = str(json.loads(corp or b"{}").get("text", "")).strip()[:500]
            except ValueError:
                text = ""
            if not text:
                return self._json({"eroare": "Întrebarea este goală"}, 400)
            return self._json(self.stare.asistent.raspunde(text, self.stare.date))
        if url.path == "/api/voce":
            try:
                cerere = json.loads(corp or b"{}")
                text = str(cerere.get("text", "")).strip()
            except ValueError:
                cerere, text = {}, ""
            if not text:
                return self._json({"eroare": "Textul este gol"}, 400)
            try:
                audio = self.stare.voce.genereaza(text, cerere.get("voce", "alina"), cerere.get("viteza", 0))
            except Exception as eroare:  # fara internet sau fara edge-tts: browserul foloseste vocea proprie
                jurnal.warning("Sinteza vocală indisponibilă: %s", eroare)
                return self._json({"eroare": "Sinteza vocală nu este disponibilă"}, 503)
            return self._trimite(200, audio, "audio/mpeg", "private, max-age=3600")
        return self._json({"eroare": "Adresă necunoscută"}, 404)


def main():
    parser = argparse.ArgumentParser(description="GlobePulse AI - știri economice și politice cu glob 3D și asistent vocal")
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--demo", action="store_true", help="folosește datele salvate, fără internet")
    parser.add_argument("--fara-browser", action="store_true", help="nu deschide automat browserul")
    argumente = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    stare = StareAplicatie(demo=argumente.demo)
    stare.incarca_initial()
    CereriHTTP.stare = stare
    server = ThreadingHTTPServer(("127.0.0.1", argumente.port), CereriHTTP)

    def actualizare_periodica():
        while True:
            stare.actualizeaza()
            time.sleep(config.INTERVAL_ACTUALIZARE)

    threading.Thread(target=actualizare_periodica, daemon=True).start()

    adresa = f"http://127.0.0.1:{argumente.port}"
    print("=" * 60)
    print("  GlobePulse AI a pornit:", adresa)
    print("  Mod AI:", config.NUME_MODEL_AI if stare.asistent.mod == "claude" else f"local ({stare.asistent.motiv})")
    print("  Date:", "DEMO (salvate)" if argumente.demo else "în timp real")
    print("  Oprire: Ctrl + C")
    print("=" * 60)
    if not argumente.fara_browser:
        threading.Timer(1.0, lambda: webbrowser.open(adresa)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServerul a fost oprit.")


if __name__ == "__main__":
    main()
