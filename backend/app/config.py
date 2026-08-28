"""
Gestion de la configuration DISCOVER.
Charge la configuration depuis le fichier .env à la racine du projet.
"""

import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Charge le .env à la racine du projet
# Chemin : DISCOVER/.env (relatif à backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # Sinon, on tente les variables d'environnement (production)
    load_dotenv(override=True)


def trust_env_for(url: str) -> bool:
    """
    Indique si httpx doit lire les variables d'environnement (proxy) pour cette URL.

    Retourne False quand la cible est locale (loopback) : cela évite qu'un proxy
    d'entreprise (HTTP_PROXY/HTTPS_PROXY défini sans NO_PROXY) n'intercepte le
    trafic vers le serveur OpenCode local, ce qui provoque des timeouts.
    Une cible distante (OPENCODE_SERVER_URL externe) continue d'utiliser le proxy.
    """
    host = (urlparse(url).hostname or '').lower()
    return host not in ('127.0.0.1', 'localhost', '::1', '0.0.0.0')



class Config:
    """Configuration de l'application DISCOVER."""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'discover-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # JSON : ne pas échapper l'UTF-8 (accents affichés directement)
    JSON_AS_ASCII = False

    # Backend LLM : 'opencode' (défaut, via le harness OpenCode) ou 'openai' (direct)
    LLM_BACKEND = os.environ.get('LLM_BACKEND', 'opencode').lower()

    # --- Backend OpenCode (harness) ---
    # Auth et choix du modèle gérés par OpenCode ; aucune LLM_API_KEY requise.
    OPENCODE_SERVER_URL = os.environ.get('OPENCODE_SERVER_URL', 'http://127.0.0.1:47600')
    OPENCODE_SERVER_USERNAME = os.environ.get('OPENCODE_SERVER_USERNAME')
    OPENCODE_SERVER_PASSWORD = os.environ.get('OPENCODE_SERVER_PASSWORD')
    # Modèle optionnel au format 'providerID/modelID' (ex. github-copilot/claude-sonnet-4.6).
    # Si vide, le modèle par défaut configuré dans OpenCode est utilisé.
    OPENCODE_MODEL = os.environ.get('OPENCODE_MODEL') or None
    OPENCODE_AGENT = os.environ.get('OPENCODE_AGENT') or None
    # Serveur OpenCode managé par DISCOVER (sous-processus). Si OPENCODE_SERVER_URL
    # pointe vers un serveur externe déjà lancé, mettre à 'false'.
    OPENCODE_MANAGED = os.environ.get('OPENCODE_MANAGED', 'true').lower() == 'true'
    OPENCODE_BIN = os.environ.get('OPENCODE_BIN', 'opencode')

    # --- Backend OpenAI (rétro-compatibilité) ---
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # LLM "boost" optionnel (2e fournisseur pour paralléliser certains traitements)
    LLM_BOOST_API_KEY = os.environ.get('LLM_BOOST_API_KEY')
    LLM_BOOST_BASE_URL = os.environ.get('LLM_BOOST_BASE_URL')
    LLM_BOOST_MODEL_NAME = os.environ.get('LLM_BOOST_MODEL_NAME')

    # Répertoire racine de persistance (scénarios, simulations)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')

    # ---- Paramètres DISCOVER (Phases 2-4) ----
    # Domaines d'experts (société d'agents), alignés sur les 9 familles de risque
    # du référentiel. 'resilience' pilote le moteur d'effets domino.
    EXPERT_DOMAINS = [
        'operationnel', 'technique', 'rh', 'juridique', 'finance',
        'communication', 'geopolitique', 'cybersecurite', 'resilience',
    ]
    # Domaines "secteur" additionnels utilisables pour typer les noeuds du graphe
    # de crise (contextes, pas des domaines d'impact d'experts).
    SECTOR_DOMAINS = ['sante', 'logistique', 'physique', 'reglementaire', 'reputation', 'autre']
    # Trajectoires générées par simulation
    TRAJECTORY_TYPES = ['optimiste', 'intermediaire', 'critique', 'rupture']
    # Répertoire de données des simulations DISCOVER
    SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    # ---- Trace d'exécution (debug/pédagogie) ----
    # Active la trace des fichiers/fonctions du package app/ réellement exécutés,
    # dans un fichier dédié backend/logs/trace-AAAA-MM-JJ.log. Désactivée par
    # défaut (aucun surcoût). Voir app/utils/exec_tracer.py.
    TRACE_EXECUTION = os.environ.get('TRACE_EXECUTION', 'false').lower() == 'true'
    # Inclure aussi les événements de retour (←) avec durée par fonction.
    TRACE_INCLUDE_RETURNS = os.environ.get('TRACE_INCLUDE_RETURNS', 'false').lower() == 'true'
    # Profondeur maximale d'appels tracée (0 = illimité).
    TRACE_MAX_DEPTH = int(os.environ.get('TRACE_MAX_DEPTH', '0') or 0)
    # Écrire les blocs de récapitulatif dédupliqué des fichiers utilisés
    # (par scope + global via GET /api/trace/summary et à l'arrêt).
    TRACE_SUMMARY = os.environ.get('TRACE_SUMMARY', 'true').lower() == 'true'
    # Seuil anti-bruit : n'émet un récap de scope que si ≥ N fichiers distincts.
    TRACE_SUMMARY_MIN_FILES = int(os.environ.get('TRACE_SUMMARY_MIN_FILES', '1') or 1)

    @classmethod
    def validate(cls) -> list[str]:
        """Valide la configuration requise selon le backend LLM."""
        errors: list[str] = []
        if cls.LLM_BACKEND == 'openai':
            if not cls.LLM_API_KEY:
                errors.append("LLM_API_KEY non configurée (LLM_BACKEND=openai)")
        # En mode 'opencode', pas de clé requise : la disponibilité du serveur
        # est vérifiée au démarrage (voir opencode_manager) et via llm_ready().
        return errors

    @classmethod
    def llm_ready(cls) -> bool:
        """Indique si le backend LLM est prêt à être utilisé."""
        if cls.LLM_BACKEND == 'openai':
            return bool(cls.LLM_API_KEY)
        # opencode : vérifie la santé du serveur
        try:
            import httpx
            url = cls.OPENCODE_SERVER_URL.rstrip('/')
            r = httpx.get(f"{url}/global/health", timeout=5,
                          trust_env=trust_env_for(url))
            return r.status_code == 200 and bool(r.json().get('healthy'))
        except Exception:  # noqa: BLE001
            return False
