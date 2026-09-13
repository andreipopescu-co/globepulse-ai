"""
Modul: sinteza_vocala.py
---------------------------------------------------------------
Transforma textul in vorbire in limba romana folosind vocile neuronale
Microsoft "Alina" (feminina) si "Emil" (masculina), prin biblioteca
edge-tts (aceleasi voci ca functia "Citire cu voce tare" din Microsoft Edge).

Rezultatul este un fisier audio MP3, trimis browserului. Fisierele deja
generate sunt pastrate in memorie (cache), ca o fraza repetata sa nu
mai fie sintetizata din nou.

Necesita internet si biblioteca edge-tts (pip install edge-tts). Daca
nu sunt disponibile, browserul foloseste vocea proprie.
"""
import asyncio
import hashlib
import re
import threading
from collections import OrderedDict

try:
    import edge_tts
except ImportError:  # biblioteca este optionala
    edge_tts = None

VOCI = {"alina": "ro-RO-AlinaNeural", "emil": "ro-RO-EmilNeural"}

# Pronuntie mai clara pentru abrevieri si simboluri frecvente in stirile economice
INLOCUIRI = [
    (re.compile(r"S&P\s*500"), "S and P 500"),
    (re.compile(r"EUR/RON"), "euro-leu"),
    (re.compile(r"EUR/USD"), "euro-dolar"),
    (re.compile(r"(\d)\s*%"), r"\1 la sută"),
    (re.compile(r"\bSUA\b"), "S.U.A."),
    (re.compile(r"\bBNR\b"), "B.N.R."),
    (re.compile(r"\bUE\b"), "U.E."),
    (re.compile(r"\bPIB\b"), "P.I.B."),
    (re.compile(r"\bFMI\b"), "F.M.I."),
    (re.compile(r"\bBCE\b"), "B.C.E."),
]


def pregateste_text(text):
    text = " ".join(text.split())[:1500]
    for tipar, inlocuire in INLOCUIRI:
        text = tipar.sub(inlocuire, text)
    return text


class SintezaVocala:
    def __init__(self, maxim_cache=300):
        self.disponibila = edge_tts is not None
        self._cache = OrderedDict()
        self._maxim = maxim_cache
        self._blocare = threading.Lock()

    def genereaza(self, text, voce="alina", viteza=0):
        """Returneaza continutul MP3 (bytes) pentru textul dat."""
        if not self.disponibila:
            raise RuntimeError("biblioteca edge-tts nu este instalată")
        text = pregateste_text(text)
        nume_voce = VOCI.get(voce, VOCI["alina"])
        viteza = f"{max(-50, min(50, int(viteza))):+d}%"
        cheie = hashlib.sha1(f"{nume_voce}|{viteza}|{text}".encode("utf-8")).hexdigest()

        with self._blocare:
            if cheie in self._cache:
                self._cache.move_to_end(cheie)
                return self._cache[cheie]

        audio = asyncio.run(self._sintetizeaza(text, nume_voce, viteza))
        if not audio:
            raise RuntimeError("serviciul de sinteză nu a returnat audio")

        with self._blocare:
            self._cache[cheie] = audio
            if len(self._cache) > self._maxim:
                self._cache.popitem(last=False)
        return audio

    @staticmethod
    async def _sintetizeaza(text, nume_voce, viteza):
        comunicare = edge_tts.Communicate(text, nume_voce, rate=viteza)
        audio = bytearray()
        async for bucata in comunicare.stream():
            if bucata["type"] == "audio":
                audio.extend(bucata["data"])
        return bytes(audio)
