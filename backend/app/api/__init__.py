"""
API routes DISCOVER

- scenario    : scénarios de crise + extraction du graphe de crise (Phase 1)
- referentiel : référentiel de risques socle (Phase 2)
- simulation  : société d'agents experts, effets domino, trajectoires & scoring
"""

from flask import Blueprint

scenario_bp = Blueprint('scenario', __name__)
referentiel_bp = Blueprint('referentiel', __name__)
simulation_bp = Blueprint('simulation', __name__)

from . import scenario  # noqa: E402, F401
from . import referentiel  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
