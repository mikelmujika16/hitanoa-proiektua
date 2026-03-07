"""
Hitano Itzultzailea - Tokiko zerbitzaria
Abiarazteko: python server.py
Ondoren ireki: http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
import stanza
import os

# ---------------------------------------------------------------------------
# 'zu' izenordainaren mapaketa
# ---------------------------------------------------------------------------
MAPAKETA_ZU_HI = {
    "zu":         "hi",
    "zuk":        "hik",
    "zuri":       "hiri",
    "zure":       "hire",
    "zurekin":    "hirekin",
    "zuretzat":   "hiretzat",
    "zutaz":      "hitaz",
    "zuregan":    "hiregan",
    "zuregandik": "hiregandik",
    "zuregana":   "hiregana",
}

# Stanza-k inoiz PRON gisa sailkatzen ez dituen formak, baina anbiguoak ez direnak:
# zutaz (ADV gisa), zuregandik (ADV gisa), zuregana (PROPN gisa)
# Hauek POS-aren egiaztapena saltatu eta zuzenean ordezkatzen dira.
BETI_ORDEZKATU = {"zutaz", "zuregandik", "zuregana"}

# ---------------------------------------------------------------------------
# Flask aplikazioa
# ---------------------------------------------------------------------------
OINARRI_KARPETA = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=OINARRI_KARPETA, static_url_path='')

# Stanza pipeline-a behin kargatzen da abiaraztean
print("Stanza modeloa kargatzen...")
nlp = stanza.Pipeline('eu', processors='tokenize,pos,lemma', download_method=None)
print("Prest.")


@app.route('/')
def index():
    return send_from_directory(OINARRI_KARPETA, 'index.html')


@app.route('/api/izenordainak', methods=['POST'])
def itzuli_izenordainak():
    """
    Testua hartu, stanza-rekin analizatu, eta POS-ak PRON diren
    'zu'-ren formak 'hi'-rako itzulpenekin itzuli.

    Eskaera: { "testua": "..." }
    Erantzuna: { "ordezkapnak": { "zurekin": "hirekin", ... }, "tokenak": [{...}, ...] }
    """
    testua = (request.get_json(force=True) or {}).get('testua', '')
    if not testua:
        return jsonify({'ordezkapnak': {}, 'tokenak': []})

    dok = nlp(testua)
    ordezkapnak = {}
    tokenak = []

    for esaldia in dok.sentences:
        for hitza in esaldia.words:
            forma = hitza.text.lower()
            # Bide nagusia: stanza-k PRON+lemma=zu gisa sailkatutakoak
            if hitza.lemma == 'zu' and hitza.upos == 'PRON':
                if forma in MAPAKETA_ZU_HI:
                    ordezkapnak[forma] = MAPAKETA_ZU_HI[forma]
            # Bigarren bidea: stanza-k oker sailkatzen dituen forma anbiguogabeak
            elif forma in BETI_ORDEZKATU:
                ordezkapnak[forma] = MAPAKETA_ZU_HI[forma]

            tokenak.append({
                'forma': hitza.text,
                'lemma': hitza.lemma,
                'upos':  hitza.upos,
                'feats': hitza.feats or ''
            })

    return jsonify({'ordezkapnak': ordezkapnak, 'tokenak': tokenak})


if __name__ == '__main__':
    print("Zerbitzaria abiatzen: http://localhost:5000")
    app.run(debug=False, port=5000)
