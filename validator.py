"""
XML Docile — Motore di validazione XML con spiegazioni in italiano.
Validazione sintattica (well-formedness) e strutturale (DTD semplificato).
"""

import xml.etree.ElementTree as ET
import re
from typing import Optional


# ── Dizionario errori comuni → spiegazione in italiano ──────────────────────

ERROR_PATTERNS_IT = [
    # (regex, titolo breve, spiegazione estesa, suggerimento)
    (
        r"mismatched tag",
        "Tag di chiusura non corrispondente",
        "Hai aperto un tag con un nome ma lo hai chiuso con un nome diverso. "
        "Ogni tag di chiusura deve avere esattamente lo stesso nome del tag di apertura.",
        "Controlla che il nome nel tag di chiusura (dopo </) sia identico a quello del tag di apertura. "
        "Attenzione a errori di battitura: 'nome' e 'nme' sono diversi!",
    ),
    (
        r"not well-formed\s*\(invalid token\)",
        "Carattere non valido nell'XML",
        "C'è un carattere che non è ammesso nella sintassi XML. Di solito si tratta "
        "di una & da sola (non seguita da un'entità) o di un carattere < in un punto sbagliato.",
        "Se devi scrivere il simbolo &, usa &amp;. Se devi scrivere <, usa &lt;. "
        "Controlla anche che non ci siano caratteri strani copiati da altri programmi.",
    ),
    (
        r"no element found",
        "Nessun elemento XML trovato",
        "Il testo inserito non contiene alcun elemento XML. Un documento XML deve "
        "avere almeno un elemento radice (root) che racchiude tutto il contenuto.",
        "Aggiungi un elemento radice. Esempio: <documento> ... </documento>",
    ),
    (
        r"unclosed token",
        "Tag o attributo non chiuso",
        "Hai dimenticato di chiudere un tag o un valore di attributo. "
        "Ogni tag aperto con < deve essere chiuso con >, e ogni attributo "
        'deve avere le virgolette: attributo="valore".',
        "Controlla che ogni < abbia il suo > corrispondente e che tutti "
        "gli attributi abbiano le virgolette intorno al valore.",
    ),
    (
        r"unbound prefix",
        "Prefisso namespace non definito",
        "Stai usando un prefisso (come <prefisso:nome>) ma non hai dichiarato "
        "a quale namespace appartiene con xmlns:prefisso='...'.",
        "Aggiungi la dichiarazione del namespace. Esempio: "
        '<root xmlns:prefisso="http://esempio.com">',
    ),
    (
        r"junk after document element",
        "Contenuto dopo l'elemento radice",
        "Dopo la chiusura dell'elemento radice (il tag principale) non può esserci "
        "altro contenuto. Hai probabilmente del testo o un altro tag dopo </root>.",
        "Sposta tutto il contenuto all'interno dell'elemento radice, "
        "oppure racchiudi tutto in un unico elemento contenitore.",
    ),
    (
        r"expected '>'",
        "Parentesi angolare '>' mancante",
        "Manca il carattere > per chiudere un tag. Ogni tag XML deve essere "
        "scritto tra < e >.",
        "Cerca il punto dove manca il > e aggiungilo. Controlla i tag "
        "nelle righe precedenti a quella segnalata.",
    ),
    (
        r"not well-formed",
        "XML malformato (errore di sintassi generico)",
        "Il documento non rispetta le regole base della sintassi XML. "
        "L'XML è molto preciso: ogni tag va aperto e chiuso correttamente, "
        "gli attributi vanno tra virgolette, e la struttura deve essere "
        "rigorosamente ad albero.",
        "Verifica riga per riga: ogni <tag> deve avere il suo </tag>, "
        "gli attributi devono essere attributo=\"valore\", e non ci possono "
        "essere tag incrociati (<a><b></a></b> è sbagliato!).",
    ),
    (
        r"undefined entity",
        "Entità non definita",
        "Hai usato un'entità (un codice che inizia con &) che non è tra quelle "
        "standard dell'XML. Le entità predefinite sono: &amp; (&), &lt; (<), "
        "&gt; (>), &apos; ('), &quot; (\").",
        "Usa solo le entità standard oppure dichiara le tue entità "
        "personalizzate nella DTD.",
    ),
    (
        r"duplicate attribute",
        "Attributo duplicato",
        "Un tag XML non può avere due attributi con lo stesso nome. "
        "Hai scritto lo stesso attributo due volte nello stesso tag.",
        "Rimuovi l'attributo duplicato. Ogni attributo può comparire "
        "una sola volta in ciascun tag.",
    ),
]


def explain_error(parse_error: ET.ParseError, xml_text: str) -> dict:
    """
    Data un'eccezione ParseError e il testo XML originale,
    restituisce un dizionario con spiegazione in italiano.
    """
    msg = str(parse_error)
    line = getattr(parse_error, 'position', (0, 0))[0] if hasattr(parse_error, 'position') else 0
    col = getattr(parse_error, 'position', (0, 0))[1] if hasattr(parse_error, 'position') else 0

    # Cerca corrispondenza tra i pattern noti
    for pattern, title, explanation, suggestion in ERROR_PATTERNS_IT:
        if re.search(pattern, msg, re.IGNORECASE):
            return {
                "type": "syntax",
                "line": line,
                "column": col,
                "title": title,
                "message": explanation,
                "suggestion": suggestion,
                "raw_error": msg,
            }

    # Fallback: nessun pattern specifico trovato
    return {
        "type": "syntax",
        "line": line,
        "column": col,
        "title": "Errore di sintassi XML",
        "message": f"Il parser XML ha rilevato un errore: {msg}. "
                   "Questo significa che il documento non rispetta le regole "
                   "di scrittura dell'XML (la cosiddetta 'buona forma' o well-formedness).",
        "suggestion": "Rileggi attentamente la riga segnalata e quelle vicine. "
                      "Controlla che ogni tag di apertura abbia il suo tag di chiusura, "
                      "che gli attributi siano tra virgolette, e che non ci siano "
                      "caratteri speciali non codificati.",
        "raw_error": msg,
    }


# ── Controlli strutturali aggiuntivi (oltre il parser) ──────────────────────

def check_tag_balance(xml_text: str) -> list[dict]:
    """
    Controlla manualmente il bilanciamento dei tag (tag aperti ma non chiusi, ecc.)
    Restituisce una lista di problemi strutturali trovati.
    """
    issues = []

    # Trova tutti i tag di apertura (non autochiudenti) e di chiusura
    # [^>]*? non-greedy per non consumare il / dei tag autochiudenti
    tag_pattern = re.compile(r'<(\/?)\s*([a-zA-Z_][\w:.-]*)(?:\s[^>]*?)?(\/)?\s*>')

    stack = []  # (tag_name, line_number)
    line_num = 1

    for match in tag_pattern.finditer(xml_text):
        # Calcola il numero di riga
        line_num = xml_text[:match.start()].count('\n') + 1

        is_closing = match.group(1) == '/'
        tag_name = match.group(2)
        is_self_closing = match.group(3) == '/'

        if is_closing:
            # Tag di chiusura </nome>
            if not stack:
                issues.append({
                    "type": "structure",
                    "line": line_num,
                    "column": match.start() - xml_text.rfind('\n', 0, match.start()) if '\n' in xml_text[:match.start()] else match.start() + 1,
                    "title": "Tag di chiusura senza apertura",
                    "message": f"Il tag di chiusura </{tag_name}> non ha un corrispondente "
                               "tag di apertura. Forse hai chiuso un tag di troppo, "
                               "oppure il tag di apertura ha un nome diverso.",
                    "suggestion": f"Verifica che esista un tag di apertura <{tag_name}> "
                                  "prima di questo punto, e che non ci siano errori di battitura nel nome.",
                })
            else:
                expected = stack[-1][0]
                if expected != tag_name:
                    # Cerchiamo se il tag è aperto da qualche parte nello stack
                    found_at = None
                    for i, (tname, tline) in enumerate(stack):
                        if tname == tag_name:
                            found_at = i
                            break
                    if found_at is not None:
                        # Il tag è aperto più sopra, ma ci sono tag non chiusi in mezzo
                        unclosed = [t[0] for t in stack[found_at + 1:]]
                        issues.append({
                            "type": "structure",
                            "line": line_num,
                            "column": match.start() - xml_text.rfind('\n', 0, match.start()) if '\n' in xml_text[:match.start()] else match.start() + 1,
                            "title": "Tag chiusi nell'ordine sbagliato",
                            "message": f"Stai chiudendo </{tag_name}> ma prima devi chiudere "
                                       f"i tag ancora aperti: {', '.join(unclosed)}. "
                                       "In XML i tag vanno chiusi nell'ordine inverso "
                                       "rispetto all'apertura (LIFO: Last In, First Out).",
                            "suggestion": f"Chiudi prima i tag più interni. "
                                          f"L'ordine corretto è: apri <a>, apri <b>, "
                                          f"chiudi </b>, chiudi </a>. Non puoi fare: "
                                          f"<a><b></a></b>.",
                        })
                    else:
                        issues.append({
                            "type": "structure",
                            "line": line_num,
                            "column": match.start() - xml_text.rfind('\n', 0, match.start()) if '\n' in xml_text[:match.start()] else match.start() + 1,
                            "title": f"Tag di chiusura </{tag_name}> non corrisponde",
                            "message": f"Il tag di chiusura </{tag_name}> non corrisponde "
                                       f"al tag di apertura attualmente aperto (<{expected}>). "
                                       "I tag XML devono essere annidati correttamente.",
                            "suggestion": f"Controlla l'ordine dei tag. "
                                          f"Forse hai dimenticato di chiudere <{expected}> "
                                          f"prima di chiudere </{tag_name}>.",
                        })
                else:
                    stack.pop()  # Corretto: chiude il tag aspettato
        elif not is_self_closing:
            # Tag di apertura <nome> (non autochiudente)
            stack.append((tag_name, line_num))

    # Tag rimasti aperti
    for tag_name, tag_line in stack:
        issues.append({
            "type": "structure",
            "line": tag_line,
            "column": 1,
            "title": f"Tag <{tag_name}> mai chiuso",
            "message": f"Il tag <{tag_name}> aperto alla riga {tag_line} non è mai stato chiuso. "
                       "In XML ogni tag di apertura (che non sia autochiudente) "
                       "deve avere il corrispondente tag di chiusura.",
            "suggestion": f"Aggiungi </{tag_name}> nel punto appropriato del documento. "
                          "Ricorda: se un tag non ha contenuto, puoi usare la forma "
                          f"abbreviata <{tag_name}/> (tag autochiudente).",
        })

    return issues


# ── Validazione DTD semplificata ────────────────────────────────────────────

def parse_simple_dtd(dtd_text: str) -> dict:
    """
    Parser DTD semplificato. Estrae:
    - elements: {tag_name: [child_element_names]}
    - attributes: {tag_name: {attr_name: required_or_optional}}
    """
    elements = {}
    attributes = {}

    # Pattern per <!ELEMENT nome (figlio1, figlio2, ...)>
    element_pattern = re.compile(
        r'<!ELEMENT\s+([a-zA-Z_][\w:.-]*)\s+\(([^)]*)\)\s*>',
        re.IGNORECASE
    )
    for match in element_pattern.finditer(dtd_text):
        tag_name = match.group(1)
        content = match.group(2)
        # Estrai i nomi dei figli dal modello di contenuto
        children = re.findall(r'([a-zA-Z_][\w:.-]*)', content)
        # Filtra parole chiave DTD come #PCDATA, EMPTY, ANY
        children = [c for c in children if c not in ('#PCDATA', 'EMPTY', 'ANY')]
        elements[tag_name] = children

    # Pattern per <!ATTLIST nome_elemento nome_attributo CDATA #REQUIRED>
    attr_pattern = re.compile(
        r'<!ATTLIST\s+([a-zA-Z_][\w:.-]*)\s+([a-zA-Z_][\w:.-]*)\s+CDATA\s+(#REQUIRED|#IMPLIED)\s*>',
        re.IGNORECASE
    )
    for match in attr_pattern.finditer(dtd_text):
        tag_name = match.group(1)
        attr_name = match.group(2)
        required = match.group(3).upper() == '#REQUIRED'
        if tag_name not in attributes:
            attributes[tag_name] = {}
        attributes[tag_name][attr_name] = required

    return {"elements": elements, "attributes": attributes}


def validate_against_dtd(xml_text: str, dtd_text: str) -> list[dict]:
    """
    Valida il testo XML contro una DTD semplificata.
    Restituisce una lista di problemi strutturali.
    """
    issues = []
    dtd = parse_simple_dtd(dtd_text)

    if not dtd["elements"] and not dtd["attributes"]:
        # DTD vuota o non riconosciuta
        return issues

    # Parsing dell'XML per estrarre la struttura
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []  # Se l'XML non è ben formato, gli errori sintattici sono già segnalati

    all_elements_defined = set(dtd["elements"].keys())
    all_elements_used = set()

    def check_element(element, parent_tag=None, depth=0):
        tag = element.tag
        # Rimuovi eventuale namespace dal tag (parte dopo })
        if '}' in tag:
            tag = tag.split('}', 1)[1]

        all_elements_used.add(tag)

        # Controlla che il tag sia definito nella DTD
        if tag not in all_elements_defined and all_elements_defined:
            # Calcola approssimativamente la riga
            line_info = find_element_line(xml_text, element)
            issues.append({
                "type": "dtd",
                "line": line_info,
                "column": 1,
                "title": f"Tag <{tag}> non definito nella DTD",
                "message": f"Il tag <{tag}> non è dichiarato nella DTD fornita. "
                           "La DTD specifica quali tag sono ammessi nel documento. "
                           "Solo i tag dichiarati con <!ELEMENT ...> possono essere usati.",
                "suggestion": f"Aggiungi una dichiarazione <!ELEMENT {tag} (...) > "
                              "nella DTD, oppure correggi il nome del tag nel documento XML. "
                              "Verifica anche eventuali errori di battitura.",
            })

        # Controlla gli attributi richiesti
        if tag in dtd["attributes"]:
            for attr_name, required in dtd["attributes"][tag].items():
                if required and attr_name not in element.attrib:
                    line_info = find_element_line(xml_text, element)
                    issues.append({
                        "type": "dtd",
                        "line": line_info,
                        "column": 1,
                        "title": f"Attributo '{attr_name}' mancante in <{tag}>",
                        "message": f"Il tag <{tag}> richiede l'attributo '{attr_name}' "
                                   "(dichiarato come #REQUIRED nella DTD), ma non è presente.",
                        "suggestion": f"Aggiungi l'attributo: <{tag} {attr_name}='valore'>",
                    })

        # Controlla i figli
        for child in element:
            check_element(child, tag, depth + 1)

    check_element(root)

    # Controlla tag definiti nella DTD ma non usati (solo avviso)
    unused = all_elements_defined - all_elements_used
    if unused and all_elements_defined:
        # Non è un errore, ma lo segnaliamo come nota
        pass

    return issues


def find_element_line(xml_text: str, element) -> int:
    """Cerca approssimativamente la riga di un elemento nel testo XML."""
    tag = element.tag
    if '}' in tag:
        tag = tag.split('}', 1)[1]

    # Cerca <tag o <prefix:tag nel testo
    pattern = re.compile(rf'<\s*{re.escape(tag)}(?:\s|>|/)')
    match = pattern.search(xml_text)
    if match:
        return xml_text[:match.start()].count('\n') + 1
    return 1


# ── Costruzione struttura ad albero per visualizzazione ─────────────────────

def build_structure(xml_text: str) -> Optional[dict]:
    """
    Costruisce una rappresentazione ad albero dell'XML per la visualizzazione.
    Restituisce un dizionario annidato o None se l'XML non è valido.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    def node_to_dict(element, depth=0):
        tag = element.tag
        if '}' in tag:
            tag = tag.split('}', 1)[1]

        children = [node_to_dict(child, depth + 1) for child in element]

        result = {
            "tag": tag,
            "depth": depth,
            "attributes": dict(element.attrib),
            "children": children,
            "text": (element.text or "").strip()[:100] if element.text else "",
        }
        return result

    return node_to_dict(root)


# ── Funzione principale ──────────────────────────────────────────────────────

def validate_xml(xml_text: str, dtd_text: Optional[str] = None) -> dict:
    """
    Valida un testo XML e restituisce un report completo.

    Args:
        xml_text: Il testo XML da validare
        dtd_text: Testo DTD opzionale per la validazione strutturale

    Returns:
        dict con:
        - is_valid: bool
        - is_well_formed: bool
        - is_structurally_valid: bool
        - is_dtd_valid: bool or None (None se nessuna DTD fornita)
        - errors: list[dict] — tutti gli errori trovati
        - warnings: list[dict] — avvisi non bloccanti
        - structure: dict | None — struttura ad albero
        - stats: dict — statistiche (numero tag, profondità, ecc.)
    """
    result = {
        "is_valid": False,
        "is_well_formed": False,
        "is_structurally_valid": False,
        "is_dtd_valid": None,
        "errors": [],
        "warnings": [],
        "structure": None,
        "stats": {},
        "tag_count": 0,
        "max_depth": 0,
    }

    if not xml_text or not xml_text.strip():
        result["errors"].append({
            "type": "input",
            "line": 0,
            "column": 0,
            "title": "Nessun testo XML inserito",
            "message": "Non hai ancora inserito alcun testo XML da validare. "
                       "Incolla il tuo XML nell'area di testo o trascina un file.",
            "suggestion": "Copia e incolla il tuo documento XML nell'area 'Inserisci XML' "
                          "oppure trascina un file .xml nella zona di caricamento.",
        })
        return result

    # Step 1: Validazione sintattica (well-formedness)
    try:
        ET.fromstring(xml_text)
        result["is_well_formed"] = True
    except ET.ParseError as e:
        result["errors"].append(explain_error(e, xml_text))

    # Step 2: Controlli strutturali aggiuntivi (bilanciamento tag)
    balance_issues = check_tag_balance(xml_text)
    result["errors"].extend(balance_issues)

    result["is_structurally_valid"] = len([e for e in result["errors"] if e["type"] == "structure"]) == 0

    # Step 3: Validazione DTD (opzionale)
    if dtd_text and dtd_text.strip():
        dtd_issues = validate_against_dtd(xml_text, dtd_text)
        if dtd_issues:
            result["errors"].extend(dtd_issues)
            result["is_dtd_valid"] = False
        else:
            result["is_dtd_valid"] = True

    # Step 4: Costruzione struttura
    if result["is_well_formed"]:
        result["structure"] = build_structure(xml_text)

    # Step 5: Statistiche
    if result["is_well_formed"]:
        try:
            root = ET.fromstring(xml_text)

            def count_all(element):
                count = 1
                max_d = 0
                for child in element:
                    c, d = count_all(child)
                    count += c
                    max_d = max(max_d, d)
                return count, max_d + 1

            total, depth = count_all(root)
            result["stats"] = {
                "total_elements": total,
                "max_depth": depth,
            }
        except ET.ParseError:
            pass

    # Determina validità complessiva
    all_errors = result["errors"]
    has_blocking = any(
        e["type"] in ("syntax", "structure") or e["type"] == "input"
        for e in all_errors
    )
    has_dtd_errors = result["is_dtd_valid"] is False

    result["is_valid"] = not has_blocking and not has_dtd_errors

    # Separa warnings da errors (DTD non bloccante va in warnings)
    # (per ora tutto rimane in errors, ma potremmo spostare cose)

    return result
