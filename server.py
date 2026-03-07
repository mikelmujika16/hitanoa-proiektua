"""
Hitano Itzultzailea - Tokiko zerbitzaria
Abiarazteko: python server.py
Ondoren ireki: http://localhost:5000
"""

from flask import Flask, send_from_directory
import os

OINARRI_KARPETA = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=OINARRI_KARPETA, static_url_path='')


@app.route('/')
def index():
    return send_from_directory(OINARRI_KARPETA, 'index.html')


if __name__ == '__main__':
    print("Zerbitzaria abiatzen: http://localhost:5000")
    app.run(debug=False, port=5000)
