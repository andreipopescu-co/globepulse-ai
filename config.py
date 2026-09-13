"""
Modul: config.py
---------------------------------------------------------------
Setarile generale ale aplicatiei GlobePulse AI: caile catre fisiere,
intervalele de actualizare, modelul AI si lista surselor de stiri.
"""
import os

DIRECTOR = os.path.dirname(os.path.abspath(__file__))
DIR_STATIC = os.path.join(DIRECTOR, "static")
DIR_DATE = os.path.join(DIRECTOR, "date")
CALE_CACHE = os.path.join(DIR_DATE, "cache.json")
CALE_DEMO = os.path.join(DIR_DATE, "demo.json")
CALE_CHEIE_API = os.path.join(DIRECTOR, "cheie_api.txt")

PORT = 8765
INTERVAL_ACTUALIZARE = 10 * 60   # secunde intre doua colectari de stiri
INTERVAL_AI = 30 * 60            # secunde intre doua rezumate generate cu Claude
TIMEOUT_CERERI = 12              # secunde de asteptare pentru o sursa
MAX_STIRI = 300                  # numarul maxim de stiri pastrate
MAX_STIRI_TRADINGVIEW = 60
VECHIME_MAXIMA_ORE = 72          # stirile mai vechi sunt ignorate
MAX_STIRI_AI = 120               # cate stiri primeste modelul AI

MODEL_AI = "claude-opus-5"
NUME_MODEL_AI = "Claude Opus 5"

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# tip = "rss" (flux RSS/Atom) sau "tradingview" (JSON)
SURSE = [
    {"id": "bloomberg-piete", "nume": "Bloomberg", "tip": "rss", "limba": "en",
     "url": "https://feeds.bloomberg.com/markets/news.rss"},
    {"id": "bloomberg-economie", "nume": "Bloomberg", "tip": "rss", "limba": "en",
     "url": "https://feeds.bloomberg.com/economics/news.rss"},
    {"id": "bloomberg-politica", "nume": "Bloomberg", "tip": "rss", "limba": "en",
     "url": "https://feeds.bloomberg.com/politics/news.rss"},
    {"id": "bloomberg-tehnologie", "nume": "Bloomberg", "tip": "rss", "limba": "en",
     "url": "https://feeds.bloomberg.com/technology/news.rss"},
    {"id": "tradingview", "nume": "TradingView", "tip": "tradingview", "limba": "en",
     "url": "https://news-headlines.tradingview.com/v2/headlines?client=web&lang=en&streaming=false"},
    {"id": "baha", "nume": "Baha News", "tip": "rss", "limba": "en",
     "url": "https://breakingthenews.net/news-feed.xml"},
    {"id": "cnbc-economie", "nume": "CNBC", "tip": "rss", "limba": "en",
     "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html"},
    {"id": "cnbc-lume", "nume": "CNBC", "tip": "rss", "limba": "en",
     "url": "https://www.cnbc.com/id/100727362/device/rss/rss.html"},
    {"id": "profit", "nume": "Profit.ro", "tip": "rss", "limba": "ro",
     "url": "https://www.profit.ro/rss"},
    {"id": "zf", "nume": "Ziarul Financiar", "tip": "rss", "limba": "ro",
     "url": "https://www.zf.ro/rss"},
    {"id": "biziday", "nume": "Biziday", "tip": "rss", "limba": "ro",
     "url": "https://www.biziday.ro/feed/"},
]
