"""
Hitano Bihurtzaile Automatikoa - Tokiko zerbitzaria
Abiarazteko: python server.py
Ondoren ireki: http://localhost:5000
"""

from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for
import os
from functools import wraps
from typing import Any, List, Optional, Set, Tuple

from translator import HitanoTranslator

try:
    import stanza
except Exception:
    stanza = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def load_local_env(env_path: str) -> None:
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, 'r', encoding='utf-8') as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        # .env fitxategia aukerakoa da; huts eginez gero, inguruneak jarraitzen du.
        pass

OINARRI_KARPETA = os.path.dirname(os.path.abspath(__file__))
load_local_env(os.path.join(OINARRI_KARPETA, '.env'))
app = Flask(__name__, static_folder=OINARRI_KARPETA, static_url_path='')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Ez zaude autentifikatuta'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


_nlp_eu = None
_nlp_error = None
_translator = None
_latxa_client = None
_latxa_model = None
_latxa_error = None


def get_translator() -> HitanoTranslator:
    global _translator
    if _translator is None:
        _translator = HitanoTranslator(project_root=OINARRI_KARPETA)
    return _translator


def get_eu_pipeline():
    global _nlp_eu, _nlp_error
    if _nlp_eu is not None:
        return _nlp_eu
    if _nlp_error is not None:
        raise RuntimeError(_nlp_error)
    if stanza is None:
        _nlp_error = "stanza ez dago instalatuta"
        raise RuntimeError(_nlp_error)

    try:
        # Lehen aldian, eredua deskargatu eta cachean gordetzen da.
        stanza.download("eu", processors="tokenize,pos,lemma", verbose=False)
        _nlp_eu = stanza.Pipeline(
            lang="eu",
            processors="tokenize,pos,lemma",
            tokenize_no_ssplit=True,
            verbose=False,
        )
        return _nlp_eu
    except Exception as exc:
        _nlp_error = str(exc)
        raise RuntimeError(_nlp_error)


def _extract_tokens_and_zuri_positions(text: str) -> Tuple[List[dict], Set[int], Optional[str]]:
    tokens: List[dict] = []
    zuri_positions: Set[int] = set()
    analysis_error: Optional[str] = None

    try:
        nlp = get_eu_pipeline()
        doc = nlp(text)
        for sent in doc.sentences:
            for word in sent.words:
                upos = (word.upos or '').upper()
                xpos = (word.xpos or '').upper()
                is_noun = upos in {'NOUN', 'PROPN'} or xpos in {'IZE', 'IZEN'}
                tokens.append({
                    'word': word.text,
                    'lemma': word.lemma or '',
                    'upos': upos,
                    'xpos': xpos,
                    'is_noun': is_noun,
                })
        zuri_positions = _build_zuri_color_positions(tokens)
    except Exception as exc:
        analysis_error = str(exc)

    return tokens, zuri_positions, analysis_error


def get_latxa_client_and_model():
    global _latxa_client, _latxa_model, _latxa_error

    if _latxa_client is not None and _latxa_model:
        return _latxa_client, _latxa_model

    if _latxa_error is not None:
        raise RuntimeError(_latxa_error)

    if OpenAI is None:
        _latxa_error = 'openai paketea ez dago instalatuta'
        raise RuntimeError(_latxa_error)

    api_key = os.getenv('LATXA_API_KEY', '').strip()
    api_url = os.getenv('LATXA_API_URL', '').strip()
    model = os.getenv('LATXA_MODEL', '').strip()

    missing = []
    if not api_key:
        missing.append('LATXA_API_KEY')
    if not api_url:
        missing.append('LATXA_API_URL')
    if not model:
        missing.append('LATXA_MODEL')

    if missing:
        _latxa_error = f'Latxa konfigurazio falta: {", ".join(missing)}'
        raise RuntimeError(_latxa_error)

    try:
        _latxa_client = OpenAI(api_key=api_key, base_url=api_url.rstrip('/'))
        _latxa_model = model
    except Exception as exc:
        _latxa_error = str(exc)
        raise RuntimeError(_latxa_error)

    return _latxa_client, _latxa_model


def _extract_chat_text(response: Any) -> str:
    choices = getattr(response, 'choices', None) or []
    if not choices:
        return ''

    message = getattr(choices[0], 'message', None)
    content = getattr(message, 'content', '')

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text' and item.get('text'):
                    parts.append(str(item.get('text')))
                continue
            item_type = getattr(item, 'type', None)
            item_text = getattr(item, 'text', None)
            if item_type == 'text' and item_text:
                parts.append(str(item_text))
        return ''.join(parts).strip()

    return str(content).strip()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('authenticated'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        app_password = os.getenv('APP_PASSWORD', '')
        if app_password and password == app_password:
            session['authenticated'] = True
            return redirect(url_for('index'))
        return redirect(url_for('login', error=1))
    return send_from_directory(OINARRI_KARPETA, 'login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return send_from_directory(OINARRI_KARPETA, 'index.html')


@app.route('/latxa')
@login_required
def latxa_page():
    return send_from_directory(OINARRI_KARPETA, 'latxa.html')


@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_text():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get('text', '')).strip()
    if not text:
        return jsonify({'tokens': []})

    tokens, _zuri_positions, analysis_error = _extract_tokens_and_zuri_positions(text)
    if analysis_error:
        return jsonify({'error': analysis_error}), 503

    return jsonify({'tokens': tokens})


def _build_zuri_color_positions(tokens: List[dict]) -> Set[int]:
    positions: Set[int] = set()
    for i, token in enumerate(tokens):
        word = str(token.get('word', '')).strip().lower()
        if word != 'zuri' or i == 0:
            continue

        prev = tokens[i - 1]
        prev_word = str(prev.get('word', '')).strip().lower()
        prev_lemma = str(prev.get('lemma', '')).strip().lower()
        prev_is_noun = bool(prev.get('is_noun', False))

        if prev_is_noun and prev_word and prev_word == prev_lemma:
            positions.add(i)

    return positions


@app.route('/api/translate', methods=['POST'])
@login_required
def translate_text():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get('text', ''))

    if not text.strip():
        return jsonify({
            'toka': {'plain': '', 'html': '', 'count': 0},
            'noka': {'plain': '', 'html': '', 'count': 0},
            'tokens': [],
            'analysis_error': None,
            'total_forms': len(get_translator().lookup_toka),
        })

    tokens, zuri_positions, analysis_error = _extract_tokens_and_zuri_positions(text)

    translator = get_translator()
    result = translator.translate_both_detailed(text, zuri_positions)

    return jsonify({
        'toka': result['toka'],
        'noka': result['noka'],
        'tokens': tokens,
        'analysis_error': analysis_error,
        'total_forms': len(translator.lookup_toka),
    })


@app.route('/api/explain', methods=['POST'])
@login_required
def explain_translation():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get('text', '')).strip()
    if not text:
        return jsonify({'steps': []})

    _tokens, zuri_positions, _analysis_error = _extract_tokens_and_zuri_positions(text)
    translator = get_translator()
    steps = translator.explain(text, zuri_positions)
    return jsonify({'steps': steps})


@app.route('/api/latxa', methods=['POST'])
@login_required
def latxa_chat():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get('question', '')).strip()
    if not question:
        return jsonify({'error': 'Galdera hutsik dago.'}), 400

    try:
        client, model = get_latxa_client_and_model()
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 503

    messages = [
        {
            'role': 'system',
            'content': (
                'Erantzun beti euskaraz. Erabili zuka forma naturala eta ez erabili hika zuzenean. '
                'Izan argia, lagungarria eta laburra.'
            ),
        },
        {'role': 'user', 'content': question},
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
        latxa_text = _extract_chat_text(response)
    except Exception as exc:
        return jsonify({'error': f'Latxa deian errorea: {exc}'}), 502

    if not latxa_text:
        return jsonify({'error': 'Latxak ez du erantzunik itzuli.'}), 502

    tokens, zuri_positions, analysis_error = _extract_tokens_and_zuri_positions(latxa_text)
    result = get_translator().translate_both_detailed(latxa_text, zuri_positions)

    return jsonify({
        'model': model,
        'latxa_response': latxa_text,
        'toka': result['toka'],
        'noka': result['noka'],
        'tokens': tokens,
        'analysis_error': analysis_error,
    })


if __name__ == '__main__':
    print("Stanza modeloa kargatzen...")
    try:
        get_eu_pipeline()
        print("Prest.")
    except RuntimeError as exc:
        print(f"Abisua: ezin izan da Stanza kargatu ({exc})")
    port = int(os.getenv('PORT', 5000))
    print(f"Zerbitzaria abiatzen: http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
