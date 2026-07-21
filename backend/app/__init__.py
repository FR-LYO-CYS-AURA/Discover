"""
DISCOVER Backend - Flask application factory
Fork du socle DISCOVER (AGPL-3.0), adapté à la simulation de crises.
"""

import os
import warnings

# Supprime les avertissements resource_tracker de certaines libs tierces.
# Doit être défini avant tout autre import.
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger

APP_NAME = "discover"


def create_app(config_class=Config):
    """Fabrique d'application Flask DISCOVER."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Encodage JSON : afficher l'UTF-8 directement (accents, etc.)
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False

    logger = setup_logger(APP_NAME)

    # N'afficher les logs de démarrage qu'une fois (évite le double affichage en mode debug).
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("DISCOVER Backend - démarrage...")
        logger.info("=" * 50)

    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Middlewares de journalisation
    @app.before_request
    def log_request():
        rlogger = get_logger(f'{APP_NAME}.request')
        rlogger.debug(f"Requête: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            rlogger.debug(f"Corps: {request.get_json(silent=True)}")

    @app.after_request
    def log_response(response):
        rlogger = get_logger(f'{APP_NAME}.request')
        rlogger.debug(f"Réponse: {response.status_code}")
        return response

    # Blueprints (Phase 0 : graphe uniquement ; simulation/trajectoires ajoutés Phases 1-4)
    from .api import graph_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')

    # Santé
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'DISCOVER Backend'}

    if should_log_startup:
        logger.info("DISCOVER Backend - prêt")

    return app
