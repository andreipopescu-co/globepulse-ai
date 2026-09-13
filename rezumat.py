"""
Modul: rezumat.py
---------------------------------------------------------------
Generarea rezumatelor si a raspunsurilor in limba romana FARA model
AI extern ("modul local"). Textele sunt construite din rezultatele
analizei (sentiment, tari, categorii, piete) si din stirile centrale.
"""
from datetime import datetime

from analiza import CATEGORII, detecteaza_tari, fara_diacritice, stiri_centrale, termeni_cheie
from tari import TARI


# ------------------------------------------------------------------
# Formulari in limba romana
# ------------------------------------------------------------------
def numar_ro(valoare, zecimale=1):
    return f"{valoare:.{zecimale}f}".replace(".", ",")


def cu_de(n, plural, singular=None):
    """1 stire, 5 stiri, 20 de stiri, 101 stiri, 120 de stiri"""
    if n == 1 and singular:
        return f"1 {singular}"
    rest = n % 100
    return f"{n} de {plural}" if n >= 20 and (rest == 0 or rest >= 20) else f"{n} {plural}"


def lista_ro(elemente):
    elemente = [str(e) for e in elemente if e]
    if len(elemente) <= 1:
        return "".join(elemente)
    return ", ".join(elemente[:-1]) + " și " + elemente[-1]


def descriere_sentiment(v):
    if v <= -0.35: return "puternic negativ"
    if v <= -0.12: return "negativ"
    if v < -0.03: return "ușor negativ"
    if v <= 0.03: return "neutru"
    if v < 0.12: return "ușor pozitiv"
    if v < 0.35: return "pozitiv"
    return "puternic pozitiv"


def descriere_impact(v):
    if v <= -0.5: return "impact negativ puternic"
    if v <= -0.2: return "impact negativ moderat"
    if v < -0.05: return "impact ușor negativ"
    if v <= 0.05: return "impact neutru"
    if v < 0.2: return "impact ușor pozitiv"
    if v < 0.5: return "impact pozitiv moderat"
    return "impact pozitiv puternic"


NUME_ROSTITE = {
    "S&P 500": "indicele S&P 500", "Nasdaq": "indicele Nasdaq", "Dow Jones": "indicele Dow Jones",
    "DAX": "indicele DAX", "FTSE 100": "indicele FTSE 100", "Nikkei 225": "indicele Nikkei",
    "Petrol Brent": "petrolul Brent", "Aur": "aurul", "Bitcoin": "bitcoinul",
    "EUR/USD": "cursul euro-dolar", "EUR/RON": "cursul euro-leu", "VIX": "indicele de volatilitate VIX",
}


def descriere_variatie(instrument):
    v = instrument["variatie"]
    nume = NUME_ROSTITE.get(instrument["nume"], instrument["nume"])
    if abs(v) < 0.05:
        return f"{nume} este aproape neschimbat"
    verb = "crește" if v > 0 else "scade"
    return f"{nume} {verb} cu {numar_ro(abs(v), 1)} la sută"


_PREFIXE_PRESA = ("ULTIMA ORĂ", "BREAKING", "VIDEO", "FOTO", "LIVE", "UPDATE", "EXCLUSIV")


def _fara_punct_final(titlu, maxim=170):
    """Titlu potrivit pentru citire: fara etichete de tip "ULTIMA ORĂ", doar prima fraza, scurtat."""
    titlu = titlu.strip()
    schimbat = True
    while schimbat:
        schimbat = False
        for prefix in _PREFIXE_PRESA:
            if titlu.upper().startswith(prefix):
                titlu, schimbat = titlu[len(prefix):].lstrip(" :-–|"), True
    fraza = titlu.split(". ")[0]
    if len(fraza) > maxim:
        fraza = fraza[:maxim].rsplit(" ", 1)[0]
    return fraza.rstrip(" .!?;:,")


# ------------------------------------------------------------------
# Textele despre piete
# ------------------------------------------------------------------
PRINCIPALELE_PIETE = ["S&P 500", "DAX", "Petrol Brent", "Aur", "Bitcoin", "EUR/RON"]


def text_piete(piete, nume=None):
    alese = [p for p in piete if p["nume"] in (nume or PRINCIPALELE_PIETE)]
    if not alese:
        return ""
    fraze = [descriere_variatie(p) for p in alese]
    if len(fraze) == 1:
        return f"Pe piețe, {fraze[0]}."
    return "Pe piețe, " + ", ".join(fraze[:-1]) + ", iar " + fraze[-1] + "."


INSTRUMENTE_INTREBARI = {
    "bitcoin": "Bitcoin", "cripto": "Bitcoin", "aur": "Aur", "petrol": "Petrol Brent", "brent": "Petrol Brent",
    "dolar": "EUR/USD", "leu": "EUR/RON", "lei": "EUR/RON", "euro": "EUR/RON", "dax": "DAX",
    "nasdaq": "Nasdaq", "dow": "Dow Jones", "s&p": "S&P 500", "nikkei": "Nikkei 225", "ftse": "FTSE 100",
}


def text_piete_detaliat(piete, intrebare_normalizata):
    if not piete:
        return "Momentan nu am acces la datele de piață."
    cuvinte = intrebare_normalizata.replace("?", " ").replace(",", " ").split()
    # "bitcoinul", "aurul", "petrolului" -> se potrivesc dupa inceputul cuvantului
    ceruti = {nume for cheie, nume in INSTRUMENTE_INTREBARI.items()
              if any(c.startswith(cheie) and not c.startswith("europ") for c in cuvinte)}
    if ceruti:
        return text_piete(piete, ceruti)
    in_crestere = sum(1 for p in piete if p["variatie"] > 0)
    return (text_piete(piete, [p["nume"] for p in piete if p["tip"] != "valută"]) +
            f" În total, {in_crestere} din {len(piete)} instrumente urmărite sunt în creștere.")


# ------------------------------------------------------------------
# Rezumatul general
# ------------------------------------------------------------------
def genereaza_rezumat_offline(date):
    stiri = date["stiri"]
    if not stiri:
        return {"rezumat": "Momentan nu există știri disponibile. Verifică conexiunea la internet.",
                "puncte_cheie": [], "generat_de": "algoritm local"}

    tari = [t for t in date["tari"].values() if t["iso3"] != "EUU" and t["nr_stiri"] > 0]
    surse = sorted({s["sursa"] for s in stiri})
    fraze = [
        f"Bună! Sunt GlobePulse și îți prezint pulsul economic și politic al lumii, la ora {datetime.now():%H:%M}.",
        f"Am analizat {cu_de(len(stiri), 'știri', 'știre')} din {cu_de(len(surse), 'surse', 'sursă')}, "
        f"printre care {lista_ro(surse[:4])}.",
        f"Tonul general al știrilor este {descriere_sentiment(date['sentiment_general'])}.",
    ]

    categorii = [c["nume"].lower() for c in date["categorii"] if c["nume"] != "General"][:3]
    if categorii:
        fraze.append(f"Cele mai multe știri sunt despre {lista_ro(categorii)}.")

    if tari:
        cea_mai_prezenta = max(tari, key=lambda t: t["nr_stiri"])
        fraze.append(f"Cea mai prezentă țară în știri este {cea_mai_prezenta['nume']}, "
                     f"cu {cu_de(cea_mai_prezenta['nr_stiri'], 'mențiuni', 'mențiune')}.")
        negative = sorted((t for t in tari if t["impact"] <= -0.15 and t["nr_stiri"] >= 2), key=lambda t: t["impact"])[:2]
        pozitive = sorted((t for t in tari if t["impact"] >= 0.15 and t["nr_stiri"] >= 2), key=lambda t: -t["impact"])[:2]
        if negative:
            fraze.append(f"Cel mai tensionat context îl au {lista_ro(t['nume'] for t in negative)}.")
        if pozitive:
            fraze.append(f"La polul opus, știri mai degrabă pozitive vin din {lista_ro(t['nume'] for t in pozitive)}.")

    if date.get("legaturi"):
        legatura = date["legaturi"][0]
        fraze.append(f"Cea mai discutată relație internațională este cea dintre {TARI[legatura['de']][0]} "
                     f"și {TARI[legatura['la']][0]}.")

    piete = text_piete(date.get("piete") or [])
    if piete:
        fraze.append(piete)

    romanesti = stiri_centrale(stiri, 2, limba="ro")
    if romanesti:
        fraze.append("Din presa românească: " + ". ".join(_fara_punct_final(s["titlu"]) for s in romanesti) + ".")
    fraze.append("Pentru detalii, apasă pe o țară de pe glob sau pune-mi o întrebare.")

    return {
        "rezumat": " ".join(fraze),
        "puncte_cheie": [f"{_fara_punct_final(s['titlu'], 200)} ({s['sursa']})" for s in stiri_centrale(stiri, 6)],
        "generat_de": "algoritm local",
        "generat_la": datetime.now().isoformat(timespec="seconds"),
    }


# ------------------------------------------------------------------
# Rezumatul unei tari
# ------------------------------------------------------------------
def rezumat_tara_offline(iso, date):
    nume = TARI[iso][0] if iso in TARI else iso
    tara = date["tari"].get(iso)
    if not tara or not tara["nr_stiri"]:
        return f"Momentan nu am găsit știri despre {nume}."

    fraze = [f"{nume}: {cu_de(tara['nr_stiri'], 'știri analizate', 'știre analizată')}, "
             f"cu un {descriere_impact(tara['impact'])}."]
    if tara.get("explicatie"):
        fraze.append(tara["explicatie"])
    teme = [c.lower() for c in tara["categorii"] if c != "General"]
    if teme:
        fraze.append(f"{'Temele principale sunt' if len(teme) > 1 else 'Tema principală este'} {lista_ro(teme)}.")

    dupa_id = {s["id"]: s for s in date["stiri"]}
    stiri_tara = [dupa_id[i] for i in tara["stiri"] if i in dupa_id]
    romanesti = [s for s in stiri_tara if s["limba"] == "ro"][:2]
    if romanesti:
        fraze.append("Din presa românească: " + ". ".join(_fara_punct_final(s["titlu"]) for s in romanesti) + ".")
    internationale = len([s for s in stiri_tara if s["limba"] != "ro"])
    if internationale:
        fraze.append(f"Alte {cu_de(internationale, 'titluri internaționale', 'titlu internațional')} "
                     f"sunt afișate în panoul țării.")
    return " ".join(fraze)


# ------------------------------------------------------------------
# Raspunsuri la intrebari (intelegerea intentiei prin cuvinte-cheie)
# ------------------------------------------------------------------
CUVINTE_PIETE = ["piat", "piet", "bursa", "burse", "indic", "actiun", "bitcoin", "cripto", "aur",
                 "petrol", "brent", "dolar", "euro", "curs", "leu", "lei", "cotat"]
CATEGORII_INTREBARI = {
    "politic": "Politică", "alegeri": "Politică", "guvern": "Politică", "econom": "Economie",
    "inflati": "Economie", "dobanz": "Economie", "energ": "Energie", "gaze": "Energie",
    "tehnolog": "Tehnologie", "inteligenta artificiala": "Tehnologie", "razboi": "Geopolitică",
    "geopolit": "Geopolitică", "conflict": "Geopolitică", "sanctiun": "Geopolitică",
    "compan": "Companii", "firme": "Companii", "afaceri": "Companii",
}
CUVINTE_REZUMAT = ["rezumat", "ce se intampla", "noutati", "pe scurt", "briefing", "ce s-a intamplat",
                   "ultimele stiri", "stirile zilei"]


def text_categorie(categorie, date):
    stiri = [s for s in date["stiri"] if categorie in s["categorii"]]
    if not stiri:
        return f"Nu am găsit știri din categoria {categorie.lower()}."
    sentiment = sum(s["sentiment"] for s in stiri) / len(stiri)
    centrale = stiri_centrale(stiri, 2)
    text = (f"Am găsit {cu_de(len(stiri), 'știri', 'știre')} din categoria {categorie.lower()}, "
            f"cu un ton {descriere_sentiment(sentiment)}.")
    romanesti = [s for s in centrale if s["limba"] == "ro"]
    if romanesti:
        text += " Din presa românească: " + ". ".join(_fara_punct_final(s["titlu"]) for s in romanesti) + "."
    return text + " Titlurile sunt afișate în lista de știri."


def raspunde_offline(intrebare, date):
    """Returneaza (raspuns, cod_tara_sau_None, categorie_sau_None)."""
    q = fara_diacritice(intrebare).lower()

    tari = detecteaza_tari(intrebare)
    if tari:
        return rezumat_tara_offline(tari[0], date), tari[0], None

    if any(c in q for c in CUVINTE_PIETE):
        return text_piete_detaliat(date.get("piete") or [], q), None, None

    for cheie, categorie in CATEGORII_INTREBARI.items():
        if cheie in q and categorie in CATEGORII:
            return text_categorie(categorie, date), None, categorie

    if any(c in q for c in CUVINTE_REZUMAT) or "stiri" in q:
        return date["briefing"]["rezumat"], None, None

    termeni = termeni_cheie(intrebare)
    potrivite = sorted(((len(termeni & termeni_cheie(s["titlu"])), s) for s in date["stiri"]),
                       key=lambda x: -x[0])
    relevante = [s for scor, s in potrivite if scor > 0][:3]
    if relevante:
        return ("Am găsit câteva știri legate de întrebarea ta: " +
                ". ".join(_fara_punct_final(s["titlu"]) for s in relevante) + "."), None, None

    return MESAJ_NECUNOSCUT, None, None


MESAJ_NECUNOSCUT = ("Nu am găsit informații despre asta în știrile curente. Mă poți întreba, de exemplu: "
                    "„Ce se întâmplă în China?”, „Cum stau piețele?” sau „Care sunt știrile politice?”")
