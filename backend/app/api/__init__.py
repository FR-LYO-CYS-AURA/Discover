"""
API routes DISCOVER

- graph    : projets / ontologie / graphe Zep (socle réutilisé)
- scenario : scénarios de crise + extraction du graphe de crise (Phase 1)

Blueprints DISCOVER à venir (simulation d'agents experts, trajectoires,
scoring) : Phases 2-4.
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
scenario_bp = Blueprint('scenario', __name__)

from . import graph  # noqa: E402, F401
from . import scenario  # noqa: E402, F401
