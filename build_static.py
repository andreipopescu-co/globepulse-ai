"""
Script: build_static.py
---------------------------------------------------------------
Construieste versiunea ONLINE a aplicatiei, publicata pe GitHub Pages
de fluxul GitHub Actions (.github/workflows/actualizare.yml).

GitHub Pages gazduieste doar fisiere statice (fara server Python), asa
ca toata prelucrarea se face aici, la fiecare actualizare:
  1. colectarea si analiza stirilor (la fel ca serverul local);
  2. pregatirea raspunsurilor posibile (tari, piete, categorii);
  3. generarea fisierelor MP3 cu vocea Alina pentru fiecare fraza;
  4. scrierea site-ului complet in folderul _site/.

Rulare locala:  python build_static.py [--demo] [--fara-voce]
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

import config
from ai import AsistentAI
from analiza import fara_diacritice
from colectare import colecteaza_stiri
from piete import preia_piete
from rezumat import MESAJ_NECUNOSCUT, rezumat_tara_offline, text_categorie, text_piete, text_piete_detaliat
from server import proceseaza
from sinteza_vocala import VOCI, edge_tts, pregateste_text
from tari import TARI

jurnal = logging.getLogger("globepulse.build")

DIR_SITE = os.path.join(config.DIRECTOR, "_site")
VOCE_ONLINE = "alina"
# aceeasi impartire in fraze ca in static/js/voce.js (Voce.imparte)
TIPAR_FRAZA = re.compile(r'[^.!?…]+[.!?…]*["”»]?')


def imparte_fraze(text):
    return [f.strip() for f in TIPAR_FRAZA.findall(text) if f.strip()]


def pregateste_texte(date):
    """Toate textele pe care asistentul le poate rosti in versiunea online."""
    piete = date.get("piete") or []
    return {
        "rezumat": date["briefing"]["rezumat"],
        "tari": {iso: rezumat_tara_offline(iso, date) for iso, t in date["tari"].items() if t["nr_stiri"]},
        "piete": text_piete_detaliat(piete, ""),
        "instrumente": {p["nume"]: text_piete(piete, [p["nume"]]) for p in piete},
        "categorii": {c["nume"]: text_categorie(c["nume"], date) for c in date["categorii"] if c["nume"] != "General"},
        "necunoscut": MESAJ_NECUNOSCUT,
    }


def cuvinte_pentru_browser():
    """Cuvintele-cheie ale tarilor (fara diacritice), pentru intelegerea intrebarilor in browser."""
    return {iso: [fara_diacritice(nume).lower()] + [fara_diacritice(c).lower() for c in cuvinte if not c.startswith("=")]
            for iso, (nume, _, _, cuvinte) in TARI.items()}


async def genereaza_voce(fraze, director):
    """Genereaza cate un MP3 pentru fiecare fraza (maxim 6 cereri simultane, 3 incercari)."""
    os.makedirs(director, exist_ok=True)
    semafor = asyncio.Semaphore(6)
    index = {}

    async def una(fraza):
        nume = hashlib.sha1(fraza.encode("utf-8")).hexdigest()[:16] + ".mp3"
        async with semafor:
            for incercare in range(3):
                try:
                    audio = bytearray()
                    async for bucata in edge_tts.Communicate(pregateste_text(fraza), VOCI[VOCE_ONLINE]).stream():
                        if bucata["type"] == "audio":
                            audio.extend(bucata["data"])
                    if audio:
                        with open(os.path.join(director, nume), "wb") as fisier:
                            fisier.write(audio)
                        index[fraza] = "voce/" + nume
                        return
                except Exception as eroare:  # retea / limitare temporara: mai incercam
                    jurnal.warning("Voce: încercarea %d eșuată pentru „%s…”: %s", incercare + 1, fraza[:40], eroare)
                await asyncio.sleep(2 * (incercare + 1))

    await asyncio.gather(*(una(f) for f in fraze))
    return index


def main():
    parser = argparse.ArgumentParser(description="Construiește versiunea online (GitHub Pages)")
    parser.add_argument("--demo", action="store_true", help="folosește datele salvate")
    parser.add_argument("--fara-voce", action="store_true", help="nu genera fișierele audio")
    argumente = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    asistent = AsistentAI()
    demo = argumente.demo
    if not demo:
        stiri, surse = colecteaza_stiri(config.SURSE)
        piete = preia_piete()
        if not stiri:
            jurnal.error("Nicio știre colectată – se folosesc datele demo.")
            demo = True
    if demo:
        with open(config.CALE_DEMO, encoding="utf-8") as fisier:
            brut = json.load(fisier)
        stiri, surse, piete = brut["stiri"], brut["surse"], brut.get("piete", [])

    date, rezumat_ai = proceseaza(stiri, surse, piete, asistent, cere_ai=asistent.mod == "claude")
    acum = datetime.now(timezone.utc)
    date.update(
        static=True, demo=demo, voce_neurala=True, nume_model=config.NUME_MODEL_AI,
        mod_ai="claude" if rezumat_ai else "offline",
        motiv_offline="" if rezumat_ai else (asistent.motiv or "rezumatul AI nu a putut fi generat"),
        urmatoarea_actualizare=(acum + timedelta(minutes=30)).isoformat(timespec="seconds"),
    )
    date["texte"] = pregateste_texte(date)
    date["cuvinte_tari"] = cuvinte_pentru_browser()

    shutil.rmtree(DIR_SITE, ignore_errors=True)
    shutil.copytree(config.DIR_STATIC, os.path.join(DIR_SITE, "static"))
    with open(os.path.join(config.DIR_STATIC, "index.html"), encoding="utf-8") as fisier:
        pagina = fisier.read().replace('<html lang="ro">', '<html lang="ro" data-mod="static">', 1)
    with open(os.path.join(DIR_SITE, "index.html"), "w", encoding="utf-8") as fisier:
        fisier.write(pagina)  # data-mod="static": pagina nu mai cauta serverul Python

    texte = date["texte"]
    toate = [texte["rezumat"], texte["piete"], texte["necunoscut"], *texte["tari"].values(),
             *texte["instrumente"].values(), *texte["categorii"].values()]
    fraze = list(dict.fromkeys(f for text in toate for f in imparte_fraze(text)))
    date["audio"] = {}
    if not argumente.fara_voce and edge_tts is not None:
        jurnal.info("Se generează vocea pentru %d fraze...", len(fraze))
        date["audio"] = asyncio.run(genereaza_voce(fraze, os.path.join(DIR_SITE, "voce")))
        jurnal.info("Voce generată pentru %d din %d fraze.", len(date["audio"]), len(fraze))

    os.makedirs(os.path.join(DIR_SITE, "date"), exist_ok=True)
    with open(os.path.join(DIR_SITE, "date", "date.json"), "w", encoding="utf-8") as fisier:
        json.dump(date, fisier, ensure_ascii=False)
    open(os.path.join(DIR_SITE, ".nojekyll"), "w").close()  # GitHub Pages: fara procesare Jekyll
    if os.environ.get("DOMENIU_PERSONALIZAT"):
        with open(os.path.join(DIR_SITE, "CNAME"), "w") as fisier:
            fisier.write(os.environ["DOMENIU_PERSONALIZAT"].strip())

    jurnal.info("Site construit în %s: %d știri, %d țări, rezumat: %s",
                DIR_SITE, len(date["stiri"]), len(date["tari"]), date["briefing"]["generat_de"])


if __name__ == "__main__":
    main()
