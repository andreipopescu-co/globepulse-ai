# GlobePulse AI – asistent vocal pentru știrile economice și politice mondiale

Lucrare pentru atestatul profesional la informatică (clasa a XII-a).

Aplicația colectează în timp real știrile din **Bloomberg, TradingView, Baha News, CNBC, Profit.ro,
Ziarul Financiar și Biziday**, plus cotațiile bursiere (Yahoo Finance). Știrile sunt analizate
(țări, categorii, sentiment, impact) și afișate pe un **glob 3D interactiv**. Un **asistent vocal**
citește rezumatul zilei cu o voce românească naturală (Alina / Emil) și răspunde la întrebări
scrise sau rostite.

## Instalare

```bash
pip install -r requirements.txt
```

## Pornire

```bash
python server.py            # știri în timp real
python server.py --demo     # date salvate, fără internet
```

Pe Windows: dublu-click pe `porneste.bat` (sau `porneste_demo.bat`).
Browserul se deschide la `http://127.0.0.1:8765` (recomandat: Google Chrome sau Microsoft Edge).

## Modul Claude (opțional)

Pune cheia API Anthropic în fișierul `cheie_api.txt` (lângă `server.py`) sau în variabila de mediu
`ANTHROPIC_API_KEY`. Fără cheie, aplicația folosește algoritmii locali.

## Structura

| Fișier | Rol |
|---|---|
| `server.py` | programul principal: server web, actualizare periodică, API |
| `config.py` | surse de știri și setări |
| `colectare.py` | descărcarea și parsarea fluxurilor RSS / JSON |
| `tari.py` | dicționarul țărilor |
| `analiza.py` | detectare țări, clasificare, sentiment, impact, știri centrale |
| `piete.py` | cotații bursiere |
| `rezumat.py` | rezumate și răspunsuri locale în română |
| `ai.py` | asistentul AI (Claude Opus 5 sau modul local) |
| `sinteza_vocala.py` | vocea românească Alina / Emil |
| `static/` | interfața web: `index.html`, `css/`, `js/` (glob, voce, aplicație) |
| `teste/` | teste automate: `python -m unittest discover teste -v` |
| `date/demo.json` | știri salvate pentru modul demo |
