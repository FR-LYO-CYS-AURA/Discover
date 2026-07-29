"""
Traceur d'exécution DISCOVER.

Objectif : comprendre **quels fichiers et fonctions du package `app/`** sont
exécutés, dans l'ordre chronologique, pour chaque action/requête.

Mécanisme : hook `sys.setprofile` + `threading.setprofile`, filtré sur le
répertoire du package `app/`. Purement additif : n'altère aucune logique métier.

Activation : variable d'environnement `TRACE_EXECUTION=true` (désactivé par
défaut → aucun surcoût en fonctionnement normal). La trace est écrite dans un
fichier dédié `backend/logs/trace-AAAA-MM-JJ.log`, séparé des logs applicatifs.

Points d'attention :
- Le serveur Flask tourne en `threaded=True` : chaque requête s'exécute dans un
  thread worker. `threading.setprofile` est donc indispensable pour que le hook
  soit hérité par ces threads.
- Anti-récursion : ce module et le logger applicatif sont exclus du filtrage.
- Robustesse : le hook n'échoue jamais au détriment de l'application (try/except).
"""

import os
import sys
import time
import atexit
import logging
import threading
from datetime import datetime
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler


# Répertoire racine du package `app/` (backend/app) — sert de filtre.
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Répertoire des logs (backend/logs).
_LOG_DIR = os.path.join(os.path.dirname(_APP_DIR), 'logs')

# Fichiers exclus du filtrage (anti-récursion / bruit d'infrastructure).
_EXCLUDED_FILES = {
    os.path.abspath(__file__),
    os.path.join(_APP_DIR, 'utils', 'logger.py'),
}

# État interne du traceur.
_installed = False
_logger: logging.Logger | None = None
_include_returns = False
_max_depth = 0  # 0 = illimité
_summary = False          # écrire les blocs de récapitulatif
_summary_min_files = 1    # seuil anti-bruit pour les récaps de scope

# Contexte par thread : profondeur d'appel courante + libellé de requête +
# compteurs de fichiers utilisés (dédupliqués) par thread.
_local = threading.local()

# Agrégation globale : références vers les dicts de compteurs de chaque thread.
# Chaque dict est enregistré UNE seule fois par thread (verrou pris à cet instant
# uniquement, pas à chaque appel → surcoût négligeable).
_global_lock = threading.Lock()
_thread_stats: list[dict[str, int]] = []


def _cfg_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def _cfg_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def is_enabled() -> bool:
    """Indique si la trace d'exécution est activée via l'environnement."""
    return _cfg_bool('TRACE_EXECUTION', False)


def _build_logger() -> logging.Logger:
    """Crée le logger dédié à la trace (fichier séparé, non propagé)."""
    os.makedirs(_LOG_DIR, exist_ok=True)
    lg = logging.getLogger('discover.exec_trace')
    lg.setLevel(logging.DEBUG)
    lg.propagate = False  # ne pollue pas les logs applicatifs / la console
    if not lg.handlers:
        filename = 'trace-' + datetime.now().strftime('%Y-%m-%d') + '.log'
        handler = RotatingFileHandler(
            os.path.join(_LOG_DIR, filename),
            maxBytes=20 * 1024 * 1024,  # 20 Mo
            backupCount=5,
            encoding='utf-8',
        )
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(message)s', datefmt='%H:%M:%S'
        ))
        lg.addHandler(handler)
    return lg


def _rel(filename: str) -> str | None:
    """Chemin relatif à `app/` si le fichier appartient au package, sinon None."""
    try:
        abspath = os.path.abspath(filename)
    except (TypeError, ValueError):
        return None
    if not abspath.startswith(_APP_DIR + os.sep):
        return None
    if abspath in _EXCLUDED_FILES:
        return None
    return os.path.relpath(abspath, _APP_DIR)


def _thread_files() -> dict[str, int]:
    """Retourne (en le créant/enregistrant au 1er appel) le dict de compteurs du thread."""
    files = getattr(_local, 'files', None)
    if files is None:
        files = {}
        _local.files = files
        # Enregistrement unique du dict du thread pour l'agrégation globale.
        with _global_lock:
            _thread_stats.append(files)
    return files


def _record_file(rel: str) -> None:
    """Incrémente le compteur d'appels du fichier pour le thread courant."""
    files = _thread_files()
    files[rel] = files.get(rel, 0) + 1


def _write_scope_summary(label: str, counts: dict[str, int]) -> None:
    """Écrit le bloc de récapitulatif des fichiers utilisés pour un scope."""
    if not _summary or _logger is None or not counts:
        return
    if len(counts) < _summary_min_files:
        return
    total_calls = sum(counts.values())
    _logger.debug(
        f'--- Fichiers utilisés — {label} '
        f'({len(counts)} fichiers, {total_calls} appels) ---'
    )
    for rel, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        _logger.debug(f'    {rel:<48} ({n} appels)')


def _hook(frame, event, arg):
    """Hook de profilage : trace les appels/retours de fonctions du package app/."""
    if event not in ('call', 'return'):
        return
    try:
        code = frame.f_code
        rel = _rel(code.co_filename)
        if rel is None:
            return

        depth = getattr(_local, 'depth', 0)

        if event == 'call':
            _record_file(rel)
            if _max_depth and depth >= _max_depth:
                _local.depth = depth + 1
                return
            indent = '  ' * depth
            ctx = getattr(_local, 'ctx', None)
            prefix = f'{{{ctx}}} ' if ctx else ''
            _logger.debug(
                f'{prefix}{indent}\u2192 {rel}:{code.co_name}:{frame.f_lineno}'
            )
            _local.depth = depth + 1
            if _include_returns:
                # mémorise l'instant d'entrée pour calculer la durée au retour
                stack = getattr(_local, 'tstack', None)
                if stack is None:
                    stack = []
                    _local.tstack = stack
                stack.append(time.perf_counter())

        else:  # return
            new_depth = max(depth - 1, 0)
            _local.depth = new_depth
            if _include_returns:
                stack = getattr(_local, 'tstack', None)
                started = stack.pop() if stack else None
                if new_depth < (_max_depth or new_depth + 1):
                    indent = '  ' * new_depth
                    dur = ''
                    if started is not None:
                        dur = f' ({(time.perf_counter() - started) * 1000:.1f}ms)'
                    ctx = getattr(_local, 'ctx', None)
                    prefix = f'{{{ctx}}} ' if ctx else ''
                    _logger.debug(
                        f'{prefix}{indent}\u2190 {rel}:{code.co_name}{dur}'
                    )
    except Exception:  # noqa: BLE001 — une trace ne doit jamais casser l'appli
        pass


def begin_scope(label: str | None) -> None:
    """
    Ouvre un scope de trace (requête HTTP ou tâche asynchrone).

    Mémorise la baseline des compteurs de fichiers pour pouvoir, à la fermeture,
    calculer les fichiers réellement utilisés dans ce scope.
    """
    if not _installed:
        return
    _local.ctx = label
    _local.depth = 0
    # Baseline = snapshot des compteurs du thread à l'entrée du scope.
    _local.scope_base = dict(_thread_files())
    _local.scope_label = label
    if label and _logger is not None:
        _logger.debug('=' * 60)
        _logger.debug(f'===== {label} =====')


def end_scope() -> None:
    """Ferme le scope courant et écrit le récapitulatif des fichiers utilisés."""
    if not _installed:
        return
    label = getattr(_local, 'scope_label', None)
    base = getattr(_local, 'scope_base', None)
    if label is not None and base is not None:
        current = _thread_files()
        diff = {
            rel: n - base.get(rel, 0)
            for rel, n in current.items()
            if n - base.get(rel, 0) > 0
        }
        _write_scope_summary(label, diff)
    _local.ctx = None
    _local.depth = 0
    _local.scope_label = None
    _local.scope_base = None


# Alias de compatibilité (utilisés par les middlewares Flask).
def set_request_context(label: str | None) -> None:
    begin_scope(label)


def clear_request_context() -> None:
    end_scope()


@contextmanager
def traced_scope(label: str):
    """
    Gestionnaire de contexte délimitant un scope de trace.

    Utilisé pour les tâches asynchrones (threads de fond) qui échappent au cycle
    before/after_request des middlewares Flask.
    """
    begin_scope(label)
    try:
        yield
    finally:
        end_scope()


def dump_summary(reason: str = 'manuel') -> dict:
    """
    Agrège les compteurs de tous les threads et écrit le récapitulatif GLOBAL.

    Best-effort : lecture concurrente possible pendant qu'un thread écrit encore,
    ce qui n'affecte pas la validité de l'inventaire des fichiers.

    Returns:
        Structure {'fichiers': [...], 'totaux': {...}} exploitable par l'API.
    """
    merged: dict[str, int] = {}
    with _global_lock:
        stats_snapshot = list(_thread_stats)
    for files in stats_snapshot:
        for rel, n in list(files.items()):
            merged[rel] = merged.get(rel, 0) + n

    ordered = sorted(merged.items(), key=lambda kv: (-kv[1], kv[0]))
    total_calls = sum(merged.values())

    if _summary and _logger is not None:
        _logger.debug('#' * 60)
        _logger.debug(
            f'##### RÉCAPITULATIF GLOBAL ({reason}) — '
            f'{len(merged)} fichiers distincts, {total_calls} appels #####'
        )
        for rel, n in ordered:
            _logger.debug(f'    {rel:<48} ({n} appels)')

    return {
        'fichiers': [{'fichier': rel, 'appels': n} for rel, n in ordered],
        'totaux': {'fichiers_distincts': len(merged), 'appels_total': total_calls},
    }


def install() -> bool:
    """
    Installe le hook de trace si `TRACE_EXECUTION` est actif.

    Idempotent : peut être appelé plusieurs fois (create_app + run.py) sans
    double installation. Pose le hook sur le thread courant (`sys.setprofile`)
    et sur tous les threads futurs (`threading.setprofile`).

    Returns:
        True si la trace est active, False sinon.
    """
    global _installed, _logger, _include_returns, _max_depth
    global _summary, _summary_min_files

    if not is_enabled():
        return False
    if _installed:
        return True

    _include_returns = _cfg_bool('TRACE_INCLUDE_RETURNS', False)
    _max_depth = _cfg_int('TRACE_MAX_DEPTH', 0)
    _summary = _cfg_bool('TRACE_SUMMARY', True)
    _summary_min_files = _cfg_int('TRACE_SUMMARY_MIN_FILES', 1)
    _logger = _build_logger()

    # Thread courant + tous les threads workers créés ensuite (Flask threaded=True).
    threading.setprofile(_hook)
    sys.setprofile(_hook)

    # Récapitulatif global écrit à l'arrêt du processus.
    atexit.register(dump_summary, 'atexit')

    _installed = True
    _logger.debug(
        f'#### Trace d\u2019exécution activée (returns={_include_returns}, '
        f'max_depth={_max_depth or "illimité"}, summary={_summary}, '
        f'min_files={_summary_min_files}) ####'
    )
    return True
