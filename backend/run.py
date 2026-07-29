"""
DISCOVER Backend - point d'entrée de démarrage
"""

import os
import sys

if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def main():
    errors = Config.validate()
    if errors:
        print("Error:")
        for err in errors:
            print(f"  - {err}")
        print("\nPlease check the configuration in the .env file")
        sys.exit(1)
    
    # Créer l'application
    app = create_app()

    # Filet de sécurité : garantit que le hook de trace (si activé) est posé
    # avant la création des threads workers du serveur (Flask threaded=True).
    try:
        from app.utils import exec_tracer
        exec_tracer.install()
    except Exception:  # noqa: BLE001
        pass
    
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG
    
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    main()

