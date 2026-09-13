"""
Modul: tari.py
---------------------------------------------------------------
Dictionarul tarilor pe care aplicatia le poate recunoaste in stiri.
Pentru fiecare tara (cod ISO 3166-1 alpha-3) se retin: numele in
romana, coordonatele aproximative ale capitalei si cuvintele-cheie.

Conventii pentru cuvintele-cheie:
  "cuvant"   - potrivire exacta, fara a tine cont de majuscule
  "=CUVANT"  - potrivire exacta, tinand cont de majuscule (ex: "=US")
  "prefix*"  - orice cuvant care incepe cu prefixul (ex: "German*")
Diacriticele sunt ignorate la comparare ("Franța" = "Franta").
"""

TARI = {
    # ---------------- America de Nord si de Sud
    "USA": ("Statele Unite", 38.90, -77.04, [
        "United States", "U.S.", "=US", "=USA", "America", "American", "Americans", "Washington",
        "White House", "Trump", "Federal Reserve", "=Fed", "Wall Street", "Congress", "Pentagon",
        "S&P 500", "Nasdaq", "Dow Jones", "New York", "California", "Texas", "SUA", "Statele Unite",
        "american*", "Casa Albă", "Rezerva Federală"]),
    "CAN": ("Canada", 45.42, -75.70, ["Canada", "Canadian*", "Ottawa", "Toronto", "Carney", "Canadei", "canadian*"]),
    "MEX": ("Mexic", 19.43, -99.13, ["Mexic*", "Sheinbaum"]),
    "BRA": ("Brazilia", -15.79, -47.88, ["Brazil*", "Brasilia", "Lula", "Sao Paulo", "Brazili*"]),
    "ARG": ("Argentina", -34.60, -58.38, ["Argentin*", "Buenos Aires", "Milei"]),
    "VEN": ("Venezuela", 10.48, -66.90, ["Venezuel*", "Caracas", "Maduro"]),
    "COL": ("Columbia", 4.71, -74.07, ["Colombia*", "Bogota", "Columbia"]),
    "CHL": ("Chile", -33.45, -70.67, ["Chile", "Chilean*", "Santiago de Chile"]),
    # ---------------- Europa
    "EUU": ("Uniunea Europeană", 50.85, 4.35, [
        "European Union", "=EU", "Eurozone", "euro zone", "euro area", "=ECB", "European Central Bank",
        "Lagarde", "Brussels", "European Commission", "von der Leyen", "Uniunea Europeană", "=UE",
        "zona euro", "=BCE", "Bruxelles", "Comisia Europeană"]),
    "GBR": ("Marea Britanie", 51.51, -0.13, [
        "Britain", "British", "=UK", "United Kingdom", "London", "Starmer", "Bank of England", "=BOE",
        "FTSE", "England", "Marea Britanie", "britanic*", "Londra", "Regatul Unit"]),
    "DEU": ("Germania", 52.52, 13.40, ["German*", "Berlin", "Merz", "Bundesbank", "=DAX"]),
    "FRA": ("Franța", 48.86, 2.35, ["France", "French", "Paris", "Macron", "Le Pen", "CAC 40", "Franța", "Franței", "francez*"]),
    "ITA": ("Italia", 41.90, 12.50, ["Ital*", "Rome", "Meloni", "Milan", "Roma"]),
    "ESP": ("Spania", 40.42, -3.70, ["Spain", "Spanish", "Madrid", "Spania", "Spaniei", "spaniol*"]),
    "PRT": ("Portugalia", 38.72, -9.14, ["Portug*", "Lisbon", "Lisabona"]),
    "NLD": ("Țările de Jos", 52.37, 4.90, ["Netherlands", "Dutch", "Amsterdam", "The Hague", "Olanda", "olandez*", "Țările de Jos"]),
    "BEL": ("Belgia", 50.85, 4.35, ["Belgi*"]),
    "LUX": ("Luxemburg", 49.61, 6.13, ["Luxembourg", "Luxemburg"]),
    "IRL": ("Irlanda", 53.35, -6.26, ["Ireland", "Irish", "Dublin", "Irlanda"]),
    "CHE": ("Elveția", 46.95, 7.45, ["Switzerland", "Swiss", "Zurich", "Geneva", "=SNB", "Elveția", "elvețian*"]),
    "AUT": ("Austria", 48.21, 16.37, ["Austria*", "Vienna", "Viena"]),
    "DNK": ("Danemarca", 55.68, 12.57, ["Denmark", "Danish", "Copenhagen", "Novo Nordisk", "Danemarca"]),
    "GRL": ("Groenlanda", 64.18, -51.72, ["Greenland", "Groenlanda"]),
    "SWE": ("Suedia", 59.33, 18.07, ["Swed*", "Stockholm", "Suedia", "suedez*"]),
    "NOR": ("Norvegia", 59.91, 10.75, ["Norw*", "Oslo", "Norvegi*"]),
    "FIN": ("Finlanda", 60.17, 24.94, ["Finland", "Finnish", "Helsinki", "Finlanda"]),
    "EST": ("Estonia", 59.44, 24.75, ["Estonia*", "Tallinn"]),
    "LVA": ("Letonia", 56.95, 24.11, ["Latvia*", "Riga", "Letonia"]),
    "LTU": ("Lituania", 54.69, 25.28, ["Lithuania*", "Vilnius", "Lituania"]),
    "POL": ("Polonia", 52.23, 21.01, ["Poland", "=Polish", "Warsaw", "Tusk", "Nawrocki", "Polonia", "Poloniei", "polonez*", "Varșovia"]),
    "CZE": ("Cehia", 50.08, 14.44, ["Czech*", "Prague", "Cehia", "Praga"]),
    "SVK": ("Slovacia", 48.15, 17.11, ["Slovakia", "Slovak", "Bratislava", "Slovacia", "Fico"]),
    "HUN": ("Ungaria", 47.50, 19.04, ["Hungar*", "Budapest", "Orbán", "Orban", "Ungari*", "unguresc*", "maghiar*"]),
    "SVN": ("Slovenia", 46.06, 14.51, ["Slovenia*", "Ljubljana"]),
    "HRV": ("Croația", 45.81, 15.98, ["Croatia*", "Zagreb", "Croația", "Croației"]),
    "ROU": ("România", 44.43, 26.10, [
        "Romania*", "Bucharest", "România", "României", "român*", "Bucureșt*", "=BNR", "=BET",
        "Bolojan", "Nicușor Dan", "=ANAF"]),
    "MDA": ("Republica Moldova", 47.01, 28.86, ["Moldova", "Moldovan", "Chișinău", "Chisinau", "Maia Sandu"]),
    "BGR": ("Bulgaria", 42.70, 23.32, ["Bulgaria*", "Sofia"]),
    "GRC": ("Grecia", 37.98, 23.73, ["Greece", "Greek", "Athens", "Grecia", "Greciei", "grecesc*"]),
    "CYP": ("Cipru", 35.19, 33.38, ["Cyprus", "Cypriot", "Nicosia", "Cipru"]),
    "MLT": ("Malta", 35.90, 14.51, ["Malta", "Maltese"]),
    "SRB": ("Serbia", 44.79, 20.45, ["Serbia*", "Belgrade", "Vucic", "Vučić", "Belgrad"]),
    "UKR": ("Ucraina", 50.45, 30.52, ["Ukrain*", "Kyiv", "Kiev", "Zelensky*", "Ucrain*"]),
    "RUS": ("Rusia", 55.76, 37.62, ["Russia", "Russian*", "Moscow", "Kremlin*", "Putin", "Rusia", "Rusiei", "rusă", "ruși", "rușii", "ruse", "rusesc*", "Moscova"]),
    "TUR": ("Turcia", 39.93, 32.85, ["Turkey", "Turkish", "Türkiye", "Turkiye", "Ankara", "Istanbul", "Erdogan", "Erdoğan", "Turcia", "Turciei"]),
    # ---------------- Orientul Mijlociu si Africa
    "ISR": ("Israel", 31.77, 35.21, ["Israel*", "Tel Aviv", "Jerusalem", "Netanyahu", "Ierusalim", "Gaza"]),
    "IRN": ("Iran", 35.69, 51.39, ["Iran*", "Tehran", "Teheran", "Khamenei", "Pezeshkian", "Hormuz"]),
    "IRQ": ("Irak", 33.31, 44.36, ["Iraq*", "Baghdad", "Irak*"]),
    "SYR": ("Siria", 33.51, 36.29, ["Syria*", "Damascus", "Siria", "Siriei", "sirian*"]),
    "LBN": ("Liban", 33.89, 35.50, ["Leban*", "Beirut", "Hezbollah", "Liban*"]),
    "SAU": ("Arabia Saudită", 24.71, 46.68, ["Saudi*", "Riyadh", "Aramco", "Arabia Saudit*", "Riad"]),
    "ARE": ("Emiratele Arabe Unite", 24.45, 54.38, ["=UAE", "United Arab Emirates", "Dubai", "Abu Dhabi", "Emiratele Arabe"]),
    "QAT": ("Qatar", 25.29, 51.53, ["Qatar*", "Doha"]),
    "YEM": ("Yemen", 15.37, 44.19, ["Yemen*", "Houthi*", "Sanaa"]),
    "EGY": ("Egipt", 30.04, 31.24, ["Egypt*", "Cairo", "Egipt*", "Suez"]),
    "ZAF": ("Africa de Sud", -25.75, 28.19, ["South Africa*", "Johannesburg", "Pretoria", "Africa de Sud"]),
    "NGA": ("Nigeria", 9.08, 7.40, ["Nigeria*", "Lagos", "Abuja"]),
    # ---------------- Asia si Oceania
    "CHN": ("China", 39.90, 116.40, [
        "China", "Chinese", "Beijing", "Xi Jinping", "=Xi", "Shanghai", "Shenzhen", "=PBOC",
        "People's Bank of China", "Yuan", "Hong Kong", "Chinei", "chinez*", "Phenian"]),
    "TWN": ("Taiwan", 25.03, 121.57, ["Taiwan*", "Taipei", "=TSMC"]),
    "JPN": ("Japonia", 35.68, 139.69, ["Japan*", "Tokyo", "Nikkei", "=BOJ", "Bank of Japan", "=Yen", "Takaichi", "Japoni*", "japonez*"]),
    "KOR": ("Coreea de Sud", 37.57, 126.98, ["South Korea*", "Seoul", "=KOSPI", "Samsung", "Hyundai", "=SK Hynix", "Coreea de Sud", "sud-coreean*"]),
    "PRK": ("Coreea de Nord", 39.04, 125.76, ["North Korea*", "Pyongyang", "Kim Jong Un", "Coreea de Nord", "nord-coreean*"]),
    "IND": ("India", 28.61, 77.21, ["India", "Indian", "Indians", "New Delhi", "Delhi", "Modi", "Mumbai", "Rupee", "Sensex", "Nifty", "Indiei", "indiană", "indieni"]),
    "PAK": ("Pakistan", 33.68, 73.05, ["Pakistan*", "Islamabad"]),
    "IDN": ("Indonezia", -6.21, 106.85, ["Indonesia*", "Jakarta", "Prabowo", "Indonezi*"]),
    "VNM": ("Vietnam", 21.03, 105.85, ["Vietnam*", "Hanoi"]),
    "AUS": ("Australia", -35.28, 149.13, ["Australia*", "Sydney", "Canberra", "=RBA", "Reserve Bank of Australia"]),
}

# Corectie: "Phenian" (Pyongyang in romana) apartine Coreei de Nord
TARI["CHN"][3].remove("Phenian")
TARI["PRK"][3].append("Phenian")

MEMBRI_UE = ["AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL",
             "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE"]

# Expresii eliminate inainte de detectare, pentru a evita confuziile
# (de exemplu "Latin America" nu se refera la Statele Unite).
EXCLUDERI = ["Latin America", "South America", "Central America", "North America", "Americas",
             "America Latină", "America de Sud", "America Centrală", "America de Nord", "Moldova Nouă"]
