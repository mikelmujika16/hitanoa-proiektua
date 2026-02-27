import pdfplumber
import json
import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# Euskaltzaindiaren 14. araua (Adizki alokutiboak, hikako moldea) PDF-tik
# aditz-forma guztiak JSON formatuan ateratzeko scripta.
#
# PDFak ez du benetako taula-egiturarik; testua 3 zutabetan dago (zuka,
# toka, noka). Hitz bakoitzaren x-koordenatua erabiltzen da zutabeak
# zuzen identifikatzeko. Zutabe-mugak:
#   Zuka:  x0 ≈  63   (col 1)
#   Toka:  x0 ≈ 183   (col 2)
#   Noka:  x0 ≈ 351   (col 3)
# ---------------------------------------------------------------------------

# Zutabe-mugak (x-koordenatuak). Hitz bat bigarren zutabetik aurrera dago
# x0 >= COL2_THRESHOLD denean, eta hirugarrenetik aurrera x0 >= COL3_THRESHOLD.
COL2_THRESHOLD = 130  # zuka eta toka arteko muga
COL3_THRESHOLD = 270  # toka eta noka arteko muga

# Goiburuen eta orrialdeen lerroek duten y-muga bereizteko
HEADER_KEYWORDS = {'ORAINALDIA', 'IRAGANALDIA', 'ALEGIAZKOA', 'ALEGIAZKO'}
SECTION_PATTERN = re.compile(r'^[\(\*]?NOR')
FOOTER_PATTERN = re.compile(r'–\d+–')

# Ezagutzen ditugun aditz-izenak
KNOWN_VERBS = {
    'izan',
    '*edin aditz laguntzailea',
    '*edun',
    '*-i- aditz laguntzailea',
    '*ezan aditz laguntzailea',
    '*iro-',
    'Egon', 'Etorri', 'Ibili', 'Joan', 'Atxeki',
    'Jarraiki (Jarraitu)', 'Ekin', 'Jari(n), Jario, Jariatu',
    'Etzan', 'Eduki', 'Ekarri', 'Eraman', 'Erabili', 'Ezagutu',
    'Egin', 'Ikusi', 'Jakin', 'Entzun', 'Erakutsi', 'Eroan',
    'Ihardun', 'Iharduki', 'Erauntsi', 'Eutsi', 'Iraun', 'Irudi',
    'Iritzi', '*Io', 'Erran',
}

# Oharretan ager daitezkeen aditz-izenen hitz solteak
VERB_NAME_WORDS = set()
for v in KNOWN_VERBS:
    for w in re.split(r'[\s,]+', v):
        cleaned = w.strip('()')
        if cleaned:
            VERB_NAME_WORDS.add(cleaned)


def strip_footnotes(text):
    """Amaierako oin-ohar zenbakiak kendu."""
    return re.sub(r'\d+$', '', text).strip()


def group_words_by_row(words, y_tolerance=3.0):
    """Hitzak lerrotan multzokatu y-koordenatuaren arabera."""
    if not words:
        return []

    rows = []
    current_row = [words[0]]
    current_top = words[0]['top']

    for w in words[1:]:
        if abs(w['top'] - current_top) <= y_tolerance:
            current_row.append(w)
        else:
            rows.append(current_row)
            current_row = [w]
            current_top = w['top']

    if current_row:
        rows.append(current_row)

    return rows


def row_to_text(row_words):
    """Lerro bateko hitz guztiak testu batean bildu."""
    return ' '.join(w['text'] for w in sorted(row_words, key=lambda w: w['x0']))


# Aditz-formako hitza den egiaztatzeko: minuskulak, komak, parentesiak,
# eta marratxoak soilik. Ez du digiaturik, punturik, bi punturik, etab.
VERB_FORM_PATTERN = re.compile(r'^[a-z(),\-]+$')


def _is_verb_form_word(text):
    """Hitz bat aditz-formako hitza den begiratu."""
    return bool(VERB_FORM_PATTERN.match(text))


def _is_valid_verb_column(col_text):
    """Zutabe baten edukia aditz-forma baliozkoa den egiaztatu.

    Aditz-formako zutabe batean, koma bidez bereizitako elementu bakoitza
    hitz bakarra izan behar da (ez prosa). Adibidez:
      'zaridak, zeridak' -> OK (2 hitz, koma bidez)
      'bezalako adizkerei dagokien' -> EZ (espazio bidez bereizitako hitzak)
    """
    if not col_text:
        return False
    # Koma bidez banatu (koma + optional espazioa)
    parts = re.split(r',\s*', col_text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Elementu bakoitza hitz bakarra izan behar da (espazioak ez)
        if ' ' in part:
            return False
        if not VERB_FORM_PATTERN.match(part):
            return False
    return True


def classify_row(row_words):
    """Lerro bat klasifikatu: 'verb', 'section', 'tense', 'footer', 'data', 'other'."""
    text = row_to_text(row_words)
    text_clean = strip_footnotes(text)

    if FOOTER_PATTERN.search(text):
        return 'footer', text_clean

    if text_clean in KNOWN_VERBS:
        return 'verb', text_clean

    # Hitz gutxi batzuk eta guztiak aditz-izen baten parte badira
    words_only = [w for w in re.split(r'[\s,()]+', text_clean) if w]
    if len(words_only) <= 4 and all(w in VERB_NAME_WORDS or w.startswith('*') for w in words_only):
        candidate = text_clean
        if candidate in KNOWN_VERBS:
            return 'verb', candidate

    if SECTION_PATTERN.match(text_clean):
        return 'section', text_clean

    for kw in HEADER_KEYWORDS:
        if text_clean.startswith(kw):
            return 'tense', text_clean

    # "Adizkera trinko" bezalako goiburua
    if text_clean.startswith('Adizkera trinko') or text_clean.startswith('Adizki alokutiboak'):
        return 'other', text_clean

    # Datu-lerroa: 3 zutabeetan hitzak egon behar dira, eta guztiak
    # aditz-formak izan behar dira (minuskulak, komak, parentesiak soilik).
    col1_words = [w for w in row_words if w['x0'] < COL2_THRESHOLD]
    col2_words = [w for w in row_words if COL2_THRESHOLD <= w['x0'] < COL3_THRESHOLD]
    col3_words = [w for w in row_words if w['x0'] >= COL3_THRESHOLD]

    if col1_words and col2_words and col3_words:
        # 3 zutabeetan hitzak daude; egiaztatu aditz-formak direla
        all_words_texts = [w['text'] for w in row_words]
        if all(_is_verb_form_word(t) for t in all_words_texts):
            # Zutabe bakoitzaren edukia egiaztatu: ez prosa, aditz-formak baizik
            col1_text = ' '.join(w['text'] for w in sorted(col1_words, key=lambda w: w['x0']))
            col2_text = ' '.join(w['text'] for w in sorted(col2_words, key=lambda w: w['x0']))
            col3_text = ' '.join(w['text'] for w in sorted(col3_words, key=lambda w: w['x0']))
            if (_is_valid_verb_column(col1_text) and
                    _is_valid_verb_column(col2_text) and
                    _is_valid_verb_column(col3_text)):
                return 'data', text_clean

    return 'other', text_clean


def extract_columns(row_words):
    """Lerro bateko hitzak 3 zutabetan banatu x-koordenatuaren arabera."""
    col1, col2, col3 = [], [], []

    for w in sorted(row_words, key=lambda w: w['x0']):
        x = w['x0']
        if x < COL2_THRESHOLD:
            col1.append(w['text'])
        elif x < COL3_THRESHOLD:
            col2.append(w['text'])
        else:
            col3.append(w['text'])

    return ' '.join(col1), ' '.join(col2), ' '.join(col3)


def extract_verbs(pdf_path, json_path):
    all_entries = []
    current_verb = None
    current_section = None
    current_tense = None

    with pdfplumber.open(pdf_path) as pdf:
        print(f"{len(pdf.pages)} orrialde prozesatzen...")

        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words()
            if not words:
                continue

            # Hitzak y-koordenatuaren arabera ordenatu
            words_sorted = sorted(words, key=lambda w: (w['top'], w['x0']))
            rows = group_words_by_row(words_sorted)

            for row in rows:
                row_type, text = classify_row(row)

                if row_type == 'verb':
                    current_verb = text
                elif row_type == 'section':
                    current_section = text
                elif row_type == 'tense':
                    current_tense = text
                elif row_type == 'data':
                    zuka, toka, noka = extract_columns(row)

                    # Soilik 3 zutabe bete dituzten lerroak gorde
                    if zuka and toka and noka:
                        entry = {
                            "aditza": current_verb,
                            "saila": current_section,
                            "aldia": current_tense,
                            "zuka": zuka,
                            "hika_toka": toka,
                            "hika_noka": noka,
                            "orrialdea": page_num + 1,
                        }
                        all_entries.append(entry)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=4)

    print(f"Prozesua amaituta! {len(all_entries)} aditz-forma atera dira.")
    print(f"Fitxategia hemen gordeta: {json_path}")


# --- Exekuzioa ---
import os

# Proiektuaren erroa (src/ karpetaren gurasoa)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

archivo_pdf = os.path.join(PROJECT_ROOT, "docs", "Araua_0014.pdf")
archivo_json = os.path.join(PROJECT_ROOT, "json", "aditzak_hika.json")

extract_verbs(archivo_pdf, archivo_json)