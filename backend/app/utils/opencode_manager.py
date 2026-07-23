"""
Gestionnaire du serveur OpenCode managé par DISCOVER.

Lance `opencode serve` en sous-processus dans un répertoire de travail neutre
(pour que l'agent ne touche jamais aux fichiers du projet), attend que le
serveur soit sain, et l'arrête proprement à la sortie.

Ne fait rien si :
  - LLM_BACKEND != 'opencode', ou
  - OPENCODE_MANAGED = false, ou
  - un serveur est déjà joignable sur OPENCODE_SERVER_URL.
"""

import os
import time
import atexit
import signal
import tempfile
import subprocess
from urllib.parse import urlparse

import httpx

from ..config import Config
from .logger import get_logger

logger = get_logger('discover.opencode_manager')

_process = None
_started_by_us = False


def _health(url: str, timeout: float = 3.0) -> bool:
    try:
        r = httpx.get(f"{url.rstrip('/')}/global/health", timeout=timeout)
        return r.status_code == 200 and bool(r.json().get('healthy'))
    except Exception:  # noqa: BLE001
        return False


def start() -> bool:
    """
    Démarre le serveur OpenCode managé si nécessaire.
    Retourne True si un serveur est disponible (démarré ou déjà présent).
    """
    global _process, _started_by_us

    if Config.LLM_BACKEND != 'opencode':
        return True  # rien à gérer

    url = Config.OPENCODE_SERVER_URL

    # Déjà joignable (serveur externe ou instance précédente) ?
    if _health(url):
        logger.info(f"Serveur OpenCode déjà disponible sur {url}")
        return True

    if not Config.OPENCODE_MANAGED:
        logger.warning(f"OPENCODE_MANAGED=false et aucun serveur joignable sur {url}")
        return False

    parsed = urlparse(url)
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or 47600

    # Répertoire de travail neutre (isolé du repo DISCOVER)
    neutral_cwd = os.path.join(tempfile.gettempdir(), 'discover_opencode_workspace')
    os.makedirs(neutral_cwd, exist_ok=True)

    env = os.environ.copy()
    if Config.OPENCODE_SERVER_PASSWORD:
        env['OPENCODE_SERVER_PASSWORD'] = Config.OPENCODE_SERVER_PASSWORD
        if Config.OPENCODE_SERVER_USERNAME:
            env['OPENCODE_SERVER_USERNAME'] = Config.OPENCODE_SERVER_USERNAME

    cmd = [Config.OPENCODE_BIN, 'serve', '--hostname', host, '--port', str(port)]
    logger.info(f"Démarrage du serveur OpenCode managé : {' '.join(cmd)} (cwd={neutral_cwd})")

    try:
        _process = subprocess.Popen(
            cmd,
            cwd=neutral_cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # groupe de process pour un arrêt propre
        )
    except FileNotFoundError:
        logger.error(f"Binaire OpenCode introuvable : '{Config.OPENCODE_BIN}'. "
                     f"Installez OpenCode ou renseignez OPENCODE_BIN.")
        return False

    # Attente de disponibilité (max ~30s)
    for _ in range(60):
        if _health(url, timeout=2.0):
            _started_by_us = True
            atexit.register(stop)
            logger.info(f"Serveur OpenCode managé prêt sur {url}")
            return True
        if _process.poll() is not None:
            logger.error("Le process OpenCode s'est arrêté prématurément")
            return False
        time.sleep(0.5)

    logger.error("Le serveur OpenCode n'est pas devenu sain dans le délai imparti")
    return False


def stop() -> None:
    """Arrête le serveur OpenCode managé (uniquement si démarré par nous)."""
    global _process, _started_by_us
    if _process is None or not _started_by_us:
        return
    logger.info("Arrêt du serveur OpenCode managé")
    try:
        os.killpg(os.getpgid(_process.pid), signal.SIGTERM)
    except Exception:  # noqa: BLE001
        try:
            _process.terminate()
        except Exception:  # noqa: BLE001
            pass
    try:
        _process.wait(timeout=8)
    except Exception:  # noqa: BLE001
        try:
            os.killpg(os.getpgid(_process.pid), signal.SIGKILL)
        except Exception:  # noqa: BLE001
            pass
    _process = None
    _started_by_us = False
