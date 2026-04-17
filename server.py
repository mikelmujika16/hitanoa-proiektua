"""
Hitano Bihurtzaile Automatikoa - Tokiko zerbitzaria
Abiarazteko: python server.py
Ondoren ireki: http://localhost:5000
"""

from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for
import os
from functools import wraps
from typing import Any, List, Set

from translator import HitanoTranslator

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


_translator = None
_latxa_client = None
_latxa_model = None
_latxa_error = None


def get_translator() -> HitanoTranslator:
    global _translator
    if _translator is None:
        _translator = HitanoTranslator(project_root=OINARRI_KARPETA)
    return _translator



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



@app.route('/api/translate', methods=['POST'])
@login_required
def translate_text():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get('text', ''))

    zuri_positions: Set[int] = set()

    if not text.strip():
        return jsonify({
            'toka': {'plain': '', 'html': '', 'count': 0},
            'noka': {'plain': '', 'html': '', 'count': 0},
            'tokens': [],
            'analysis_error': None,
            'total_forms': len(get_translator().lookup_toka),
        })

    translator = get_translator()
    result = translator.translate_both_detailed(text, zuri_positions)

    return jsonify({
        'toka': result['toka'],
        'noka': result['noka'],
        'tokens': [],
        'analysis_error': None,
        'total_forms': len(translator.lookup_toka),
    })


@app.route('/api/explain', methods=['POST'])
@login_required
def explain_translation():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get('text', '')).strip()
    if not text:
        return jsonify({'steps': []})

    translator = get_translator()
    steps = translator.explain(text, set())
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

    result = get_translator().translate_both_detailed(latxa_text, set())

    return jsonify({
        'model': model,
        'latxa_response': latxa_text,
        'toka': result['toka'],
        'noka': result['noka'],
        'tokens': [],
        'analysis_error': None,
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"Zerbitzaria abiatzen: http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
