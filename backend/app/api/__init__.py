"""
API routes DISCOVER

- graph       : projets / ontologie / graphe Zep (socle réutilisé)
- scenario    : scénarios de crise + extraction du graphe de crise (Phase 1)
- referentiel : référentiel de risques socle (Phase 2)

Blueprints DISCOVER à venir (simulation d'agents experts, trajectoires,
scoring) : Phases 2-4.
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
scenario_bp = Blueprint('scenario', __name__)
referentiel_bp = Blueprint('referentiel', __name__)
simulation_bp = Blueprint('simulation', __name__)

from . import graph  # noqa: E402, F401
from . import scenario  # noqa: E402, F401
from . import referentiel  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
