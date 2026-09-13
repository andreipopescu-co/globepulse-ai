"""
Modul: analiza.py
---------------------------------------------------------------
Analiza automata a stirilor (procesarea limbajului natural), fara
servicii externe:

  1. detectarea tarilor mentionate (dictionar de cuvinte-cheie);
  2. clasificarea pe categorii (Piete, Economie, Politica ...);
  3. analiza sentimentului pe baza unui lexicon financiar ponderat;
  4. estimarea importantei unei stiri;
  5. agregarea pe tari -> scorul de impact afisat pe glob;
  6. alegerea stirilor "centrale" (subiectele cele mai mediatizate),
     cu un algoritm inspirat de TextRank.
"""
import math
import re
import unicodedata
from collections import Counter, defaultdict

from tari import TARI, MEMBRI_UE, EXCLUDERI


# ------------------------------------------------------------------
# Utilitare pentru text
# ------------------------------------------------------------------
def normalizeaza(text):
    """Uniformizeaza diacriticele romanesti (ş -> ș) si apostrofurile."""
    return ((text or "").replace("ş", "ș").replace("ţ", "ț").replace("Ş", "Ș").replace("Ţ", "Ț")
            .replace("’", "'").replace("‘", "'"))


def fara_diacritice(text):
    """'Franța' -> 'Franta' (descompunere Unicode NFD si eliminarea accentelor)."""
    return "".join(c for c in unicodedata.normalize("NFD", normalizeaza(text))
                   if unicodedata.category(c) != "Mn")


def compileaza_cuvinte(cuvinte):
    """
    Transforma o lista de cuvinte-cheie (vezi conventiile din tari.py) in doua
    expresii regulate: una sensibila la majuscule si una nesensibila.
    """
    sensibile, nesensibile = [], []
    for cuvant in cuvinte:
        cuvant = fara_diacritice(cuvant)
        destinatie = nesensibile
        if cuvant.startswith("="):
            cuvant, destinatie = cuvant[1:], sensibile
        prefix = cuvant.endswith("*")
        if prefix:
            cuvant = cuvant[:-1]
        # (?<!\w) si (?!\w) = limitele cuvantului, functioneaza si pentru "U.S."
        destinatie.append(r"(?<!\w)" + re.escape(cuvant) + ("" if prefix else r"(?!\w)"))
    return (re.compile("|".join(sensibile)) if sensibile else None,
            re.compile("|".join(nesensibile), re.IGNORECASE) if nesensibile else None)


def _prima_pozitie(tipare, text):
    pozitii = [m.start() for tipar in tipare if tipar for m in [tipar.search(text)] if m]
    return min(pozitii) if pozitii else None


def _numar_potriviri(tipare, text):
    return sum(len(tipar.findall(text)) for tipar in tipare if tipar)


# ------------------------------------------------------------------
# 1. Detectarea tarilor
# ------------------------------------------------------------------
_TIPARE_TARI = {iso: compileaza_cuvinte(date[3]) for iso, date in TARI.items()}
_TIPAR_EXCLUDERI = re.compile("|".join(re.escape(fara_diacritice(e)) for e in EXCLUDERI), re.IGNORECASE)


def detecteaza_tari(text):
    """Returneaza codurile ISO3 ale tarilor mentionate, in ordinea aparitiei."""
    text = _TIPAR_EXCLUDERI.sub(" ", fara_diacritice(text))
    gasite = []
    for iso, tipare in _TIPARE_TARI.items():
        pozitie = _prima_pozitie(tipare, text)
        if pozitie is not None:
            gasite.append((pozitie, iso))
    return [iso for _, iso in sorted(gasite)]


# ------------------------------------------------------------------
# 2. Clasificarea pe categorii
# ------------------------------------------------------------------
CATEGORII = {
    "Piețe": ["stock*", "shares", "equit*", "index", "indices", "S&P", "Nasdaq", "=Dow", "bond", "bonds",
              "yield*", "rally", "rallies", "selloff", "sell-off", "investor*", "trader*", "Wall Street",
              "market*", "futures", "=ETF*", "bursa", "bursă", "burse", "acțiuni", "acțiunile", "investitori",
              "indicele", "randament*", "obligațiuni", "cotați*"],
    "Economie": ["inflation", "=GDP", "econom*", "central bank", "=Fed", "Federal Reserve", "=ECB",
                 "interest rate*", "rate cut*", "rate hike*", "jobs", "unemployment", "payroll*", "wage*",
                 "recession", "consumer*", "retail sales", "deficit", "debt", "budget", "tax", "taxes",
                 "trade", "export*", "import*", "tariff*", "inflați*", "=PIB", "dobând*", "șomaj", "salari*",
                 "buget*", "deficit*", "taxe", "impozit*", "=BNR", "=TVA", "economi*", "pensii"],
    "Politică": ["election*", "president", "prime minister", "minister*", "parliament", "government",
                 "vote", "votes", "voter*", "Congress", "senate", "lawmaker*", "opposition", "campaign",
                 "White House", "Kremlin", "alegeri", "președint*", "premier*", "guvern*", "parlament*",
                 "partid*", "coaliți*", "ministr*", "senat*", "politic*"],
    "Geopolitică": ["war", "military", "army", "troops", "missile*", "drone*", "attack*", "ceasefire",
                    "conflict*", "invasion", "sanction*", "=NATO", "nuclear", "defense", "defence", "terror*",
                    "Hormuz", "vessel struck", "război*", "armat*", "atac*", "sancțiun*", "rachet*",
                    "încetarea focului", "geopolitic*"],
    "Energie": ["oil", "crude", "Brent", "=WTI", "=OPEC*", "natural gas", "=LNG", "gas prices", "energy",
                "power grid", "electricity", "fuel", "gasoline", "petrol*", "gaze", "energi*", "carburan*",
                "benzin*", "motorin*", "electricitate"],
    "Tehnologie": ["=AI", "artificial intelligence", "chip*", "semiconductor*", "Nvidia", "Apple", "Microsoft",
                   "Google", "Alphabet", "=Meta", "Amazon", "OpenAI", "Anthropic", "Tesla", "tech",
                   "software", "cyber*", "data center*", "inteligență artificială", "tehnologi*", "=IT"],
    "Companii": ["earnings", "profit*", "revenue*", "=IPO", "merger*", "acquisition*", "acquire*", "deal",
                 "=CEO", "layoff*", "bankrupt*", "quarter*", "dividend*", "compani*", "firma", "firme",
                 "afaceri", "cifra de afaceri", "fuziune", "achiziți*", "listare", "concedier*",
                 "faliment*", "insolvenț*"],
    "Cripto": ["bitcoin", "crypto*", "ethereum", "blockchain", "stablecoin*", "=BTC", "criptomonede*", "cripto*"],
}
_TIPARE_CATEGORII = {nume: compileaza_cuvinte(cuvinte) for nume, cuvinte in CATEGORII.items()}


def clasifica(text):
    """Returneaza categoriile stirii, ordonate dupa numarul de cuvinte-cheie gasite."""
    text = fara_diacritice(text)
    scoruri = [(_numar_potriviri(tipare, text), nume) for nume, tipare in _TIPARE_CATEGORII.items()]
    return [nume for scor, nume in sorted(scoruri, key=lambda x: -x[0]) if scor > 0]


# ------------------------------------------------------------------
# 3. Analiza sentimentului
# ------------------------------------------------------------------
# Lexicon ponderat (engleza + romana). "*" = prefix, spatiu = expresie.
LEXICON = {
    # pozitive
    "surge*": 2, "soar*": 2, "rally": 1.5, "rallies": 1.5, "jump*": 1.5, "gain": 1, "gains": 1, "rise": 1,
    "rises": 1, "rising": 1, "climb*": 1, "record high": 2, "all-time high": 2, "beat": 1, "beats": 1,
    "boost*": 1, "strong": 1, "stronger": 1, "recover*": 1.5, "rebound*": 1.5, "optimis*": 1.5,
    "upgrade*": 1.5, "growth": 0.5, "expand*": 1, "approv*": 1, "agreement": 1, "deal": 0.5,
    "ceasefire": 1.5, "peace": 1.5, "eases": 1, "easing": 1, "cools": 0.5, "profit": 0.5, "profits": 0.5,
    "wins": 1, "success*": 1, "stabiliz*": 1, "outperform*": 1.5, "bullish": 1.5, "hope*": 1,
    "breakthrough": 2, "record": 1,
    "crește": 1, "creștere*": 1, "cresc": 1, "urcă": 1, "câștig*": 1, "acord*": 1, "investiți*": 0.5,
    "ieftin*": 1, "redresare": 1.5, "succes*": 1, "avans*": 1, "majorare salarială": 1,
    # negative
    "fall": -1, "falls": -1, "falling": -1, "fell": -1, "drop*": -1, "slump*": -2, "plunge*": -2,
    "plummet*": -2, "tumbl*": -2, "sink*": -1.5, "slide*": -1, "declin*": -1, "loss": -1, "losses": -1,
    "crash*": -2.5, "collaps*": -2.5, "crisis": -2, "recession*": -2, "inflation": -0.5, "war": -2,
    "wars": -2, "attack*": -2, "struck": -1.5, "missile*": -1.5, "sanction*": -1.5, "tariff*": -1,
    "default*": -2, "downgrad*": -1.5, "layoff*": -1.5, "job cuts": -1.5, "bankrupt*": -2.5, "fear*": -1.5,
    "concern*": -1, "worr*": -1.5, "risk": -0.5, "risks": -0.5, "tension*": -1.5, "conflict*": -1.5,
    "protest*": -1, "slow*": -1, "weak*": -1.5, "deficit*": -0.5, "probe": -1, "lawsuit*": -1,
    "ban": -1, "bans": -1, "banned": -1, "shutdown*": -1.5, "turmoil": -2, "selloff": -2, "sell-off": -2,
    "warn*": -1.5, "threat*": -1.5, "squeez*": -1, "misses": -1, "missed": -1, "halt*": -1,
    "suspend*": -1, "volatil*": -1, "uncertain*": -1, "bearish": -1.5, "dispute*": -1, "escalat*": -1.5,
    "invasion": -2, "killed": -2, "crackdown": -1.5, "hack*": -1.5, "scandal*": -1.5, "fraud*": -2,
    "investigat*": -1, "penalt*": -1, "record low": -2, "delay*": -0.5, "elusive": -0.5,
    "scade": -1, "scad": -1, "scădere*": -1, "pierder*": -1.5, "criz*": -2, "război*": -2, "atac*": -2,
    "sancțiun*": -1.5, "recesiun*": -2, "faliment*": -2.5, "insolvenț*": -2, "inflați*": -0.5,
    "scump*": -1, "concedier*": -1.5, "tensiun*": -1.5, "amenin*": -1.5, "prăbuș*": -2.5,
    "datori*": -0.5, "taxe": -0.5, "impozit*": -0.5, "avertiz*": -1.5, "îngrijor*": -1.5, "anchet*": -1,
    "amend*": -1, "blocaj*": -1.5, "grevă": -1.5, "greve": -1.5, "deficitul": -1,
}
NEGATII = {"not", "no", "never", "without", "nu", "fara", "nici"}


def _pregateste_lexicon(lexicon):
    exacte, prefixe, expresii = {}, [], []
    for cheie, pondere in lexicon.items():
        cheie = fara_diacritice(cheie).lower()
        if " " in cheie:
            expresii.append((re.compile(r"(?<!\w)" + re.escape(cheie) + r"(?!\w)"), pondere, cheie))
        elif cheie.endswith("*"):
            prefixe.append((cheie[:-1], pondere))
        else:
            exacte[cheie] = pondere
    prefixe.sort(key=lambda p: -len(p[0]))  # prefixele lungi au prioritate
    return exacte, prefixe, expresii


_EXACTE, _PREFIXE, _EXPRESII = _pregateste_lexicon(LEXICON)


def _pondere_cuvant(cuvant):
    if cuvant in _EXACTE:
        return _EXACTE[cuvant]
    for prefix, pondere in _PREFIXE:
        if cuvant.startswith(prefix):
            return pondere
    return 0.0


def analizeaza_sentiment(text):
    """
    Returneaza (scor, cuvinte_gasite). Scorul este in intervalul [-1, 1]:
    se aduna ponderile cuvintelor din lexicon (cu semn inversat daca sunt
    precedate de o negatie), apoi suma este "comprimata" cu tangenta hiperbolica.
    """
    text = fara_diacritice(text).lower()
    total, gasite = 0.0, []
    for tipar, pondere, forma in _EXPRESII:
        if tipar.search(text):
            total += pondere
            gasite.append(forma)
            text = tipar.sub(" ", text)
    cuvinte = re.findall(r"[a-z0-9][a-z0-9'-]*", text)
    for i, cuvant in enumerate(cuvinte):
        pondere = _pondere_cuvant(cuvant)
        if not pondere:
            continue
        if any(anterior in NEGATII for anterior in cuvinte[max(0, i - 2):i]):
            pondere = -pondere * 0.6
        total += pondere
        gasite.append(cuvant)
    return math.tanh(total / 2.0), gasite


# ------------------------------------------------------------------
# 4. Importanta unei stiri
# ------------------------------------------------------------------
_TIPARE_IMPORTANTA = compileaza_cuvinte([
    "war", "invasion", "sanction*", "tariff*", "recession", "default", "crisis", "crash*", "rate cut*",
    "rate hike*", "interest rate*", "central bank", "=Fed", "=ECB", "election*", "coup", "nuclear",
    "attack*", "ceasefire", "record", "emergency", "bankrupt*", "=OPEC", "=GDP", "inflation",
    "război*", "criz*", "sancțiun*", "alegeri", "dobând*", "=BNR", "recesiun*", "faliment*", "inflați*"])


def calculeaza_importanta(text, stire):
    """1 + 0,35 pentru fiecare termen important (maxim +1,5) + 0,5 pentru stirile urgente."""
    potriviri = _numar_potriviri(_TIPARE_IMPORTANTA, fara_diacritice(text))
    urgenta = 0.5 if stire.get("urgenta") == 1 else 0.0
    return 1.0 + min(1.5, 0.35 * potriviri) + urgenta


# ------------------------------------------------------------------
# Analiza completa a listei de stiri
# ------------------------------------------------------------------
def analizeaza_stiri(stiri):
    for stire in stiri:
        text = f"{stire['titlu']}. {stire.get('descriere') or ''}"
        tari = detecteaza_tari(text)
        if not tari and stire.get("limba") == "ro":
            tari = ["ROU"]  # presa romaneasca scrie in principal despre Romania
        sentiment, cuvinte = analizeaza_sentiment(stire["titlu"] + ". " + (stire.get("descriere") or "")[:300])
        stire["tari"] = tari[:5]
        stire["categorii"] = clasifica(text)[:3] or ["General"]
        stire["sentiment"] = round(sentiment, 3)
        stire["cuvinte_sentiment"] = cuvinte[:8]
        stire["importanta"] = round(calculeaza_importanta(text, stire), 2)
        stire["scor"] = round(sentiment * stire["importanta"], 3)
    return stiri


# ------------------------------------------------------------------
# 5. Agregarea pe tari, legaturi si categorii
# ------------------------------------------------------------------
def agrega_tari(stiri):
    """
    Pentru fiecare tara se calculeaza media sentimentului stirilor, ponderata cu
    importanta lor (prima tara mentionata intr-o stire are pondere 1, urmatoarele
    0,7). Stirile despre Uniunea Europeana se transmit si statelor membre (0,3).

        impact = tanh(2 * medie) * incredere,   incredere = 1 - 0,5 * e^(-n/3)

    Factorul de incredere reduce impactul tarilor cu foarte putine stiri.
    """
    acumulator = defaultdict(lambda: {"suma": 0.0, "greutate": 0.0, "nr": 0, "regional": 0,
                                      "categorii": Counter(), "stiri": []})
    for stire in stiri:
        for pozitie, iso in enumerate(stire["tari"]):
            pondere = 1.0 if pozitie == 0 else 0.7
            a = acumulator[iso]
            a["suma"] += stire["scor"] * pondere
            a["greutate"] += stire["importanta"] * pondere
            a["nr"] += 1
            a["categorii"].update(stire["categorii"][:1])
            a["stiri"].append((stire["importanta"] * pondere, stire["data"] or "", stire["id"]))
            if iso == "EUU":
                for membru in MEMBRI_UE:
                    b = acumulator[membru]
                    b["suma"] += stire["scor"] * 0.3
                    b["greutate"] += stire["importanta"] * 0.3
                    b["regional"] += 1

    rezultat = {}
    for iso, a in acumulator.items():
        nume, lat, lng, _ = TARI[iso]
        medie = a["suma"] / a["greutate"] if a["greutate"] else 0.0
        incredere = 1 - 0.5 * math.exp(-(a["nr"] + 0.3 * a["regional"]) / 3)
        rezultat[iso] = {
            "iso3": iso, "nume": nume, "lat": lat, "lng": lng,
            "nr_stiri": a["nr"], "stiri_regionale": a["regional"],
            "impact": round(math.tanh(2 * medie) * incredere, 3),
            "intensitate": round(min(1.0, a["greutate"] / 8), 3),
            "categorii": [c for c, _ in a["categorii"].most_common(3)],
            "stiri": [id_ for _, _, id_ in sorted(a["stiri"], reverse=True)[:15]],
            "explicatie": None,
        }
    return rezultat


def calculeaza_legaturi(stiri, maxim=25):
    """Perechile de tari mentionate impreuna in aceleasi stiri (arcele de pe glob)."""
    perechi = defaultdict(lambda: [0, 0.0])
    for stire in stiri:
        reale = [iso for iso in stire["tari"] if iso != "EUU"][:3]
        for i in range(len(reale)):
            for j in range(i + 1, len(reale)):
                cheie = tuple(sorted((reale[i], reale[j])))
                perechi[cheie][0] += 1
                perechi[cheie][1] += stire["scor"]
    cele_mai_dese = sorted(perechi.items(), key=lambda kv: -kv[1][0])[:maxim]
    return [{"de": a, "la": b, "lat1": TARI[a][1], "lng1": TARI[a][2], "lat2": TARI[b][1], "lng2": TARI[b][2],
             "nr": nr, "sentiment": round(math.tanh(scor / 2), 3)}
            for (a, b), (nr, scor) in cele_mai_dese]


def agrega_categorii(stiri):
    nr, suma = Counter(), defaultdict(float)
    for stire in stiri:
        for categorie in stire["categorii"]:
            nr[categorie] += 1
            suma[categorie] += stire["sentiment"]
    return [{"nume": c, "nr": n, "sentiment": round(suma[c] / n, 3)} for c, n in nr.most_common()]


def sentiment_general(stiri):
    """Media sentimentelor, ponderata cu importanta stirilor."""
    greutate = sum(s["importanta"] for s in stiri)
    return round(sum(s["sentiment"] * s["importanta"] for s in stiri) / greutate, 3) if greutate else 0.0


# ------------------------------------------------------------------
# 6. Stirile centrale (algoritm inspirat de TextRank)
# ------------------------------------------------------------------
CUVINTE_DE_LEGATURA = set("""
the and for with from that this what will have has had are was were been into over after amid about than
more most says said say its their they them you your our not but can may could would should while when where
which who how why new now out off two one all his her she him just also first year years week weeks today
live update updates latest ahead report reports news billion million percent per via set sets make makes
care este sunt pentru dupa despre cele cel mai din prin doar fost acest aceasta acum lui sau dar ale unei unui
sub cum asupra avea are vor fie insa foarte inca spre pana intre fata catre peste noi nou noua
""".split())


def termeni_cheie(text):
    """Cuvintele semnificative ale unui titlu, reduse la primele 6 litere (radacina aproximativa)."""
    cuvinte = re.findall(r"[a-z]{3,}", fara_diacritice(text).lower())
    return {c[:6] for c in cuvinte if c not in CUVINTE_DE_LEGATURA}


def stiri_centrale(stiri, k=6, limba=None):
    """
    O stire este "centrala" daca impartaseste multi termeni rari (IDF mare) cu
    celelalte stiri, adica subiectul ei apare in mai multe surse. Se aleg cele mai
    centrale k stiri, evitand subiectele aproape identice (similaritate Jaccard).
    """
    candidati = [s for s in stiri if limba is None or s.get("limba") == limba]
    if not candidati:
        return []
    termeni = [termeni_cheie(s["titlu"]) for s in candidati]
    n = len(candidati)
    frecventa = Counter(t for ts in termeni for t in ts)
    idf = {t: math.log((n + 1) / (f + 0.5)) for t, f in frecventa.items()}

    scoruri = []
    for i, ti in enumerate(termeni):
        similaritate = 0.0
        for j, tj in enumerate(termeni):
            if i != j:
                comune = ti & tj
                if comune:
                    similaritate += sum(idf[t] for t in comune) / (1 + math.log(1 + len(ti) + len(tj)))
        scoruri.append(similaritate * (0.6 + 0.4 * candidati[i]["importanta"]) + 0.01 * candidati[i]["importanta"])

    alese = []
    for i in sorted(range(n), key=lambda i: -scoruri[i]):
        if all(len(termeni[i] & termeni[j]) / max(1, len(termeni[i] | termeni[j])) < 0.3 for j in alese):
            alese.append(i)
        if len(alese) == k:
            break
    return [candidati[i] for i in alese]
