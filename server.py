"""
XML Docile — Server Flask
Validatore XML con spiegazioni in italiano per principianti.
"""

import os
import sys
from flask import Flask, request, jsonify, render_template, send_from_directory

# Aggiungi la directory corrente al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validator import validate_xml

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB max


@app.route("/")
def index():
    """Pagina principale."""
    return render_template("index.html")


@app.route("/api/validate", methods=["POST"])
def api_validate():
    """
    Endpoint di validazione XML.
    Accetta JSON: {"xml": "...", "dtd": "..." (opzionale)}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Richiesta non valida: invia un JSON con il campo 'xml'"}), 400

    xml_text = data.get("xml", "")
    dtd_text = data.get("dtd", None)

    if not xml_text or not xml_text.strip():
        return jsonify({
            "is_valid": False,
            "is_well_formed": False,
            "is_structurally_valid": False,
            "is_dtd_valid": None,
            "errors": [{
                "type": "input",
                "line": 0,
                "column": 0,
                "title": "Nessun testo XML inserito",
                "message": "Non hai ancora inserito alcun testo XML da validare.",
                "suggestion": "Incolla il tuo XML nell'area di testo oppure trascina un file .xml.",
            }],
            "warnings": [],
            "structure": None,
            "stats": {},
        })

    result = validate_xml(xml_text, dtd_text)
    return jsonify(result)


@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(".", "robots.txt")


@app.route("/sitemap.xml")
def sitemap_xml():
    return send_from_directory(".", "sitemap.xml")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4601))
    app.run(host="0.0.0.0", port=port, debug=False)
