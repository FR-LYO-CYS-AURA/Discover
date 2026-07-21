"""
Gestion de la configuration DISCOVER.
Charge la configuration depuis le fichier .env à la racine du projet.
"""

import os
from dotenv import load_dotenv

# Charge le .env à la racine du projet
# Chemin : DISCOVER/.env (relatif à backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # Sinon, on tente les variables d'environnement (production)
    load_dotenv(override=True)


class Config:
    """Configuration de l'application DISCOVER."""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'discover-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # JSON : ne pas échapper l'UTF-8 (accents affichés directement)
    JSON_AS_ASCII = False

    # LLM (format OpenAI unifié)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # LLM "boost" optionnel (2e fournisseur pour paralléliser certains traitements)
    LLM_BOOST_API_KEY = os.environ.get('LLM_BOOST_API_KEY')
    LLM_BOOST_BASE_URL = os.environ.get('LLM_BOOST_BASE_URL')
    LLM_BOOST_MODEL_NAME = os.environ.get('LLM_BOOST_MODEL_NAME')

    # Zep (graphe d'interdépendances / mémoire GraphRAG)
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    # Upload de fichiers (documents seed décrivant la crise / le contexte)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 Mo
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # Prétraitement de texte
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50

    # ---- Paramètres DISCOVER (Phases 2-4) ----
    # Domaines d'expertise activables (société d'agents experts)
    EXPERT_DOMAINS = [
        'cybersecurite', 'sante', 'rh', 'juridique',
        'finance', 'communication', 'operations', 'logistique',
    ]
    # Trajectoires générées par simulation
    TRAJECTORY_TYPES = ['optimiste', 'intermediaire', 'critique', 'rupture']
    # Répertoire de données des simulations DISCOVER
    SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    @classmethod
    def validate(cls) -> list[str]:
        """Valide la configuration requise."""
        errors: list[str] = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY non configurée")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY non configurée")
        return errors
