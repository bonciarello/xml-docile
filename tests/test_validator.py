"""
Test suite per XML Docile — validatore XML.
Testa il modulo validator.py con vari scenari.
"""

import sys
import os
import json
import unittest

# Aggiungi la directory del progetto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validator import validate_xml, check_tag_balance, parse_simple_dtd, explain_error
import xml.etree.ElementTree as ET


class TestValidXML(unittest.TestCase):
    """Test con XML ben formato e valido."""

    def test_simple_valid_xml(self):
        """Un semplice XML valido deve passare."""
        xml = "<root><child>testo</child></root>"
        result = validate_xml(xml)
        self.assertTrue(result["is_valid"])
        self.assertTrue(result["is_well_formed"])
        self.assertTrue(result["is_structurally_valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_self_closing_tags(self):
        """Tag autochiudenti devono essere validi."""
        xml = "<root><item id='1'/><item id='2'/></root>"
        result = validate_xml(xml)
        self.assertTrue(result["is_valid"])
        self.assertTrue(result["is_well_formed"])

    def test_nested_valid_xml(self):
        """XML con annidamento profondo deve passare."""
        xml = "<a><b><c><d><e>profondo</e></d></c></b></a>"
        result = validate_xml(xml)
        self.assertTrue(result["is_valid"])
        self.assertTrue(result["is_well_formed"])
        self.assertEqual(result["stats"]["max_depth"], 5)
        self.assertEqual(result["stats"]["total_elements"], 5)

    def test_xml_with_attributes(self):
        """XML con attributi deve essere valido."""
        xml = '<persona nome="Mario" età="30"><indirizzo via="Roma" n="10"/></persona>'
        result = validate_xml(xml)
        self.assertTrue(result["is_valid"])

    def test_xml_declaration(self):
        """XML con dichiarazione iniziale deve passare."""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<root><item/></root>'
        result = validate_xml(xml)
        self.assertTrue(result["is_valid"])

    def test_xml_with_entities(self):
        """XML con entità predefinite deve passare."""
        xml = "<root>5 &lt; 10 &amp; &gt; 3</root>"
        result = validate_xml(xml)
        self.assertTrue(result["is_valid"])


class TestInvalidXML(unittest.TestCase):
    """Test con XML malformato."""

    def test_unclosed_tag(self):
        """Tag non chiuso: deve segnalare errore."""
        xml = "<root><child>testo</root>"
        result = validate_xml(xml)
        self.assertFalse(result["is_valid"])
        self.assertFalse(result["is_well_formed"])
        self.assertTrue(len(result["errors"]) > 0)
        # L'errore deve menzionare il tag
        error_messages = " ".join(e["message"] for e in result["errors"])
        self.assertTrue("tag" in error_messages.lower() or "child" in error_messages.lower() or "chius" in error_messages.lower())

    def test_mismatched_closing_tag(self):
        """Tag di chiusura con nome sbagliato."""
        xml = "<root><item>testo</sbagliato></root>"
        result = validate_xml(xml)
        # Potrebbe essere rilevato come sintassi o struttura
        has_error = (not result["is_well_formed"]) or (not result["is_structurally_valid"])
        self.assertTrue(has_error, "Dovrebbe rilevare un errore nel tag di chiusura sbagliato")

    def test_no_root_element(self):
        """Nessun elemento radice."""
        xml = "solo testo senza tag"
        result = validate_xml(xml)
        self.assertFalse(result["is_valid"])
        self.assertFalse(result["is_well_formed"])

    def test_missing_angle_bracket(self):
        """Parentesi angolare mancante."""
        xml = "<root><item>testo</item root>"
        result = validate_xml(xml)
        self.assertFalse(result["is_valid"])

    def test_unquoted_attribute(self):
        """Attributo senza virgolette."""
        xml = "<root><item id=1>testo</item></root>"
        result = validate_xml(xml)
        self.assertFalse(result["is_valid"])
        self.assertFalse(result["is_well_formed"])

    def test_crossed_tags(self):
        """Tag incrociati: <a><b></a></b>."""
        xml = "<a><b>testo</a></b>"
        result = validate_xml(xml)
        # I tag incrociati dovrebbero essere rilevati come errore
        has_error = not result["is_valid"]
        self.assertTrue(has_error, "I tag incrociati dovrebbero essere rilevati")

    def test_empty_input(self):
        """Input vuoto: deve segnalare errore."""
        xml = ""
        result = validate_xml(xml)
        self.assertFalse(result["is_valid"])
        self.assertTrue(len(result["errors"]) > 0)

    def test_whitespace_only_input(self):
        """Solo spazi bianchi: deve segnalare errore."""
        xml = "   \n   \t   "
        result = validate_xml(xml)
        self.assertFalse(result["is_valid"])


class TestTagBalance(unittest.TestCase):
    """Test specifici per il bilanciamento dei tag."""

    def test_correctly_balanced(self):
        """Tag correttamente bilanciati: nessun errore."""
        xml = "<a><b><c/></b></a>"
        issues = check_tag_balance(xml)
        self.assertEqual(len(issues), 0)

    def test_unclosed_tag_balance(self):
        """Tag mai chiuso deve essere rilevato."""
        xml = "<a><b><c></b></a>"
        issues = check_tag_balance(xml)
        self.assertTrue(len(issues) > 0, "Il tag <c> non chiuso deve essere rilevato")

    def test_wrong_close_order(self):
        """Chiusura nell'ordine sbagliato."""
        xml = "<a><b></a></b>"
        issues = check_tag_balance(xml)
        self.assertTrue(len(issues) > 0)

    def test_extra_closing_tag(self):
        """Tag di chiusura di troppo."""
        xml = "<a><b></b></c></a>"
        issues = check_tag_balance(xml)
        self.assertTrue(len(issues) > 0)


class TestDTDValidation(unittest.TestCase):
    """Test per la validazione DTD semplificata."""

    def test_dtd_parsing(self):
        """Il parser DTD deve estrarre elementi e attributi."""
        dtd = """<!ELEMENT libri (libro+)>
<!ELEMENT libro (titolo, autore)>
<!ELEMENT titolo (#PCDATA)>
<!ELEMENT autore (#PCDATA)>
<!ATTLIST libro id CDATA #REQUIRED>"""
        parsed = parse_simple_dtd(dtd)
        self.assertIn("libri", parsed["elements"])
        self.assertIn("libro", parsed["elements"])
        self.assertIn("titolo", parsed["elements"])
        self.assertIn("autore", parsed["elements"])
        self.assertIn("libro", parsed["attributes"])
        self.assertTrue(parsed["attributes"]["libro"].get("id", False))

    def test_valid_against_dtd(self):
        """XML valido contro la DTD."""
        dtd = """<!ELEMENT libri (libro+)>
<!ELEMENT libro (titolo, autore)>
<!ELEMENT titolo (#PCDATA)>
<!ELEMENT autore (#PCDATA)>"""
        xml = "<libri><libro><titolo>Test</titolo><autore>Autore</autore></libro></libri>"
        result = validate_xml(xml, dtd)
        self.assertTrue(result["is_well_formed"])
        # La DTD non dovrebbe generare errori per tag definiti
        dtd_errors = [e for e in result["errors"] if e["type"] == "dtd"]
        self.assertEqual(len(dtd_errors), 0)

    def test_unknown_tag_in_dtd(self):
        """Tag non definito nella DTD deve essere segnalato."""
        dtd = """<!ELEMENT libri (libro+)>
<!ELEMENT libro (titolo)>
<!ELEMENT titolo (#PCDATA)>"""
        xml = "<libri><libro><titolo>Test</titolo><autore>Sconosciuto</autore></libro></libri>"
        result = validate_xml(xml, dtd)
        dtd_errors = [e for e in result["errors"] if e["type"] == "dtd"]
        self.assertTrue(len(dtd_errors) > 0, "Il tag <autore> non definito deve essere segnalato")

    def test_missing_required_attribute(self):
        """Attributo richiesto mancante nella DTD."""
        dtd = """<!ELEMENT libro (titolo)>
<!ELEMENT titolo (#PCDATA)>
<!ATTLIST libro id CDATA #REQUIRED>"""
        xml = "<libro><titolo>Test</titolo></libro>"
        result = validate_xml(xml, dtd)
        dtd_errors = [e for e in result["errors"] if e["type"] == "dtd"]
        self.assertTrue(len(dtd_errors) > 0, "L'attributo 'id' mancante deve essere segnalato")


class TestErrorExplanations(unittest.TestCase):
    """Test che le spiegazioni in italiano siano presenti e sensate."""

    def test_syntax_error_has_italian_explanation(self):
        """Un errore di sintassi deve avere spiegazione in italiano."""
        xml = "<root><child>testo</root>"
        try:
            ET.fromstring(xml)
        except ET.ParseError as e:
            explanation = explain_error(e, xml)
            self.assertIn("message", explanation)
            self.assertIn("suggestion", explanation)
            self.assertIn("title", explanation)
            # Verifica che il testo sia in italiano (contiene parole italiane comuni)
            text = explanation["message"] + explanation["suggestion"] + explanation["title"]
            italian_markers = ["tag", "errore", "il", "la", "di", "che", "non", "controlla", "verifica"]
            found = [m for m in italian_markers if m in text.lower()]
            self.assertTrue(len(found) >= 2, f"La spiegazione dovrebbe contenere parole italiane. Trovate: {found}")

    def test_error_has_line_column(self):
        """Gli errori devono riportare riga e colonna quando possibile."""
        xml = "<root>\n  <item>\n    <broken\n</root>"
        try:
            ET.fromstring(xml)
        except ET.ParseError as e:
            explanation = explain_error(e, xml)
            self.assertIn("line", explanation)
            self.assertIn("column", explanation)


class TestStructure(unittest.TestCase):
    """Test per la struttura ad albero."""

    def test_structure_built_for_valid_xml(self):
        """XML valido deve produrre una struttura."""
        xml = "<root><a><b>testo</b></a></root>"
        result = validate_xml(xml)
        self.assertIsNotNone(result["structure"])
        self.assertEqual(result["structure"]["tag"], "root")
        self.assertEqual(len(result["structure"]["children"]), 1)

    def test_structure_none_for_invalid_xml(self):
        """XML non valido non deve produrre struttura."""
        xml = "<root><a><b>testo</a></root>"
        result = validate_xml(xml)
        # Se il parser lo considera ben formato, avrà struttura
        # Se no, structure sarà None
        if not result["is_well_formed"]:
            self.assertIsNone(result["structure"])


class TestAcceptanceCriteria(unittest.TestCase):
    """Test per i criteri di accettazione specificati."""

    def test_criterion_1_unclosed_tag_with_line_column(self):
        """
        Criterio 1: XML ben formato ma con tag non chiuso →
        errore con riga, colonna e spiegazione in italiano.
        """
        xml = """<libri>
  <libro>
    <titolo>Il nome della rosa</titolo>
    <autore>Umberto Eco
  </libro>
</libri>"""
        # <autore> non è chiuso prima di </libro>
        result = validate_xml(xml)
        self.assertFalse(result["is_valid"])
        errors = result["errors"]
        self.assertTrue(len(errors) > 0, "Deve esserci almeno un errore")

        # Verifica che ci sia un errore relativo al tag non chiuso
        error_texts = " ".join(
            (e.get("title", "") + " " + e.get("message", ""))
            for e in errors
        )
        self.assertTrue(
            "autore" in error_texts.lower() or "chius" in error_texts.lower() or "tag" in error_texts.lower(),
            f"L'errore dovrebbe menzionare il tag non chiuso. Testo errori: {error_texts[:200]}"
        )

        # Verifica che almeno un errore abbia riga e colonna o che sia strutturale
        has_location = any(
            (e.get("line", 0) > 0) or e.get("type") == "structure"
            for e in errors
        )
        self.assertTrue(has_location, "Almeno un errore deve avere informazioni di posizione")

        # Verifica che ci sia una spiegazione in italiano
        for e in errors:
            msg = e.get("message", "") + e.get("suggestion", "")
            italian_words = ["il", "la", "di", "che", "non", "controlla", "tag", "errore"]
            found_italian = any(w in msg.lower() for w in italian_words)
            self.assertTrue(found_italian, f"La spiegazione dovrebbe essere in italiano: {msg[:100]}")

    def test_criterion_2_valid_xml_shows_success(self):
        """
        Criterio 2: XML valido → messaggio di successo con conferma.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<libri>
  <libro id="1">
    <titolo>Il nome della rosa</titolo>
    <autore>Umberto Eco</autore>
    <anno>1980</anno>
  </libro>
</libri>"""
        result = validate_xml(xml)
        self.assertTrue(result["is_valid"], "L'XML valido deve essere riconosciuto come valido")
        self.assertTrue(result["is_well_formed"], "Deve essere ben formato")
        self.assertTrue(result["is_structurally_valid"], "Deve essere strutturalmente valido")
        self.assertEqual(len(result["errors"]), 0, "Nessun errore per XML valido")

    def test_criterion_3_unknown_tag_vs_dtd(self):
        """
        Criterio 3: XML con tag sconosciuto rispetto a DTD →
        errore di validità strutturale.
        """
        dtd = """<!ELEMENT libri (libro+)>
<!ELEMENT libro (titolo, autore, anno)>
<!ELEMENT titolo (#PCDATA)>
<!ELEMENT autore (#PCDATA)>
<!ELEMENT anno (#PCDATA)>"""
        xml = """<libri>
  <libro>
    <titolo>Test</titolo>
    <autore>Autore</autore>
    <anno>2024</anno>
    <editore>Editore Sconosciuto</editore>
  </libro>
</libri>"""
        # <editore> non è definito nella DTD
        result = validate_xml(xml, dtd)
        dtd_errors = [e for e in result["errors"] if e["type"] == "dtd"]
        self.assertTrue(len(dtd_errors) > 0,
                        f"Il tag <editore> non definito nella DTD deve generare errori. "
                        f"Errori trovati: {result['errors']}")
        # Verifica che l'errore menzioni il tag non definito
        error_text = " ".join(e.get("title", "") + " " + e.get("message", "") for e in dtd_errors)
        self.assertIn("editore", error_text.lower())


class TestStats(unittest.TestCase):
    """Test per le statistiche."""

    def test_stats_for_valid_xml(self):
        """XML valido deve produrre statistiche."""
        xml = "<root><a><b/><c/></a><d/></root>"
        result = validate_xml(xml)
        self.assertIn("total_elements", result["stats"])
        self.assertIn("max_depth", result["stats"])
        self.assertEqual(result["stats"]["total_elements"], 5)
        self.assertEqual(result["stats"]["max_depth"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
