# -*- coding: utf-8 -*-
"""
Python REST API for Meteo Base. Handles two tasks:
1. Computing duration-curves for the neerslagduurlijnen project
2. Forewarding Hydromedah forcing-files for the SIPS project
"""

__author__ = "Daniel Tollenaar"
__credits__ = ["Daniel Tollenaar", "Siebe Bosch"]
__maintainer__ = "Daniel Tollenaar"
__email__ = "daniel@d2hydro.nl"
__status__ = "Development"

STATUS_FILE = 'status.txt'
wiwb_dir = 'wiwb_raw'
work_dir = 'work_dir'
client_dir = 'to_client'

from flask import Flask, request, send_file
from waitress import serve
from flask_cors import CORS
from . import stats_app
from . import sips_app

app = Flask(__name__, static_url_path='/static')
CORS(app, supports_credentials=True)

app.register_blueprint(stats_app.bp)
app.register_blueprint(sips_app.bp)

@app.route('/hello')
def hello():
    """return 'Hello, World!', just an example to test the api functioning"""
    return 'Hello, World!'

serve(app, port=5000)
