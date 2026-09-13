"""
Teste automate pentru modulele de analiza si generare a raspunsurilor.
Rulare (din folderul aplicatie):  python -m unittest discover teste -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analiza import (agrega_tari, analizeaza_sentiment, analizeaza_stiri, calculeaza_legaturi, clasifica,
                     detecteaza_tari, stiri_centrale)
from colectare import citeste_data, curata_text, parseaza_rss
from rezumat import cu_de, genereaza_rezumat_offline, lista_ro, raspunde_offline


def stire(titlu, sursa="Bloomberg", limba="en", id_=None):
    return {"id": id_ or titlu[:12], "titlu": titlu, "descriere": "", "link": "", "data": "2026-09-13T10:00:00+00:00",
            "sursa": sursa, "sursa_id": sursa.lower(), "limba": limba}


class TestDetectareTari(unittest.TestCase):
    def test_tari_simple(self):
        self.assertEqual(detecteaza_tari("China and Japan agree on trade"), ["CHN", "JPN"])

    def test_cuvinte_asociate(self):
        self.assertIn("USA", detecteaza_tari("Fed holds rates steady as Trump criticizes Powell"))
        self.assertIn("RUS", detecteaza_tari("Kremlin rejects new proposal"))

    def test_majuscule_sensibile(self):
        self.assertIn("USA", detecteaza_tari("US inflation cools"))
        self.assertNotIn("USA", detecteaza_tari("Tell us what you think"))

    def test_excluderi(self):
        self.assertNotIn("USA", detecteaza_tari("Latin America stocks rally"))

    def test_romana_si_diacritice(self):
        self.assertIn("ROU", detecteaza_tari("Guvernul României adoptă noi taxe"))
        self.assertIn("FRA", detecteaza_tari("Ce se intampla in Franta?"))

    def test_uniunea_europeana(self):
        self.assertIn("EUU", detecteaza_tari("ECB keeps rates unchanged"))


class TestClasificare(unittest.TestCase):
    def test_categorii(self):
        self.assertEqual(clasifica("Oil prices jump as OPEC cuts output")[0], "Energie")
        self.assertIn("Cripto", clasifica("Bitcoin climbs above record"))
        self.assertIn("Politică", clasifica("Parlamentul votează noul guvern"))

    def test_fara_categorie(self):
        self.assertEqual(clasifica("Sunny weather this weekend"), [])


class TestSentiment(unittest.TestCase):
    def test_pozitiv(self):
        scor, cuvinte = analizeaza_sentiment("Stocks surge to record high")
        self.assertGreater(scor, 0.5)
        self.assertIn("record high", cuvinte)

    def test_negativ(self):
        self.assertLess(analizeaza_sentiment("Markets plunge as war fears grow")[0], -0.5)

    def test_negatie(self):
        self.assertGreater(analizeaza_sentiment("Company says there is no crisis")[0], 0)

    def test_romana(self):
        self.assertLess(analizeaza_sentiment("Criza energetică provoacă scumpiri")[0], 0)
        self.assertGreater(analizeaza_sentiment("Economia României înregistrează creștere")[0], 0)

    def test_neutru(self):
        self.assertEqual(analizeaza_sentiment("The meeting is on Tuesday")[0], 0)


class TestAgregare(unittest.TestCase):
    def setUp(self):
        self.stiri = analizeaza_stiri([
            stire("China stocks plunge as trade war with US escalates", id_="a"),
            stire("China factory output falls", id_="b"),
            stire("Japan exports surge to record high", id_="c"),
            stire("Bursa de la București crește", sursa="Profit.ro", limba="ro", id_="d"),
        ])

    def test_impact(self):
        tari = agrega_tari(self.stiri)
        self.assertLess(tari["CHN"]["impact"], 0)
        self.assertGreater(tari["JPN"]["impact"], 0)
        self.assertEqual(tari["CHN"]["nr_stiri"], 2)
        self.assertIn("ROU", tari)

    def test_legaturi(self):
        legaturi = calculeaza_legaturi(self.stiri)
        self.assertEqual({legaturi[0]["de"], legaturi[0]["la"]}, {"CHN", "USA"})

    def test_stiri_centrale_distincte(self):
        alese = stiri_centrale(self.stiri, 3)
        self.assertEqual(len({s["id"] for s in alese}), len(alese))


class TestColectare(unittest.TestCase):
    def test_parsare_rss(self):
        xml = b"""<rss><channel><item><title>Oil &amp; gas rally</title><link>https://ex.com/1</link>
                  <description>&lt;p&gt;Prices &lt;b&gt;up&lt;/b&gt;&lt;/p&gt;</description>
                  <pubDate>Sun, 13 Sep 2026 17:13:00 GMT</pubDate></item></channel></rss>"""
        rezultat = parseaza_rss(xml, {"id": "test", "nume": "Test", "limba": "en"})
        self.assertEqual(rezultat[0]["titlu"], "Oil & gas rally")
        self.assertEqual(rezultat[0]["descriere"], "Prices up")
        self.assertTrue(rezultat[0]["data"].startswith("2026-09-13T17:13"))

    def test_curatare_si_date(self):
        self.assertEqual(curata_text("  <b>A</b>   &amp; B "), "A & B")
        self.assertIsNone(citeste_data("nu este o dată"))


class TestRezumat(unittest.TestCase):
    def setUp(self):
        stiri = analizeaza_stiri([stire("China stocks plunge", id_="a"), stire("Germany economy grows", id_="b"),
                                  stire("Inflația scade în România", sursa="ZF", limba="ro", id_="c")])
        self.date = {"stiri": stiri, "tari": agrega_tari(stiri), "legaturi": [], "piete": [],
                     "categorii": [{"nume": "Piețe", "nr": 1, "sentiment": -0.5}], "sentiment_general": -0.1}
        self.date["briefing"] = genereaza_rezumat_offline(self.date)

    def test_titlu_pentru_citire(self):
        from rezumat import _fara_punct_final
        self.assertEqual(_fara_punct_final("ULTIMA ORĂ VIDEO Guvernul adoptă bugetul. Detalii în curând."),
                         "Guvernul adoptă bugetul")

    def test_formulari_romanesti(self):
        self.assertEqual(cu_de(5, "știri"), "5 știri")
        self.assertEqual(cu_de(25, "știri"), "25 de știri")
        self.assertEqual(cu_de(105, "știri"), "105 știri")
        self.assertEqual(lista_ro(["a", "b", "c"]), "a, b și c")

    def test_rezumat_generat(self):
        self.assertIn("3 știri", self.date["briefing"]["rezumat"])

    def test_intrebare_despre_tara(self):
        raspuns, tara, _ = raspunde_offline("Ce se întâmplă în China?", self.date)
        self.assertEqual(tara, "CHN")
        self.assertIn("China", raspuns)

    def test_intrebare_despre_piete_fara_date(self):
        raspuns, _, _ = raspunde_offline("Cum stau piețele azi?", self.date)
        self.assertIn("piață", raspuns)


if __name__ == "__main__":
    unittest.main()
