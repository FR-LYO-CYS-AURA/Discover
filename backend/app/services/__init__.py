"""
Services métier DISCOVER (pipeline de simulation de crise).

  - CrisisGraphExtractor : extraction du graphe de crise (Phase 1)
  - RiskRepository       : référentiel de risques socle (Phase 2)
  - ExpertSociety        : société d'agents experts par domaine (Phase 2)
  - DominoEngine         : propagation des effets domino (Phase 2)
  - TrajectoryGenerator  : génération des 4 trajectoires + scoring (Phase 3)
  - report_builder       : rapport de synthèse Markdown (Phase 4)
"""

from .crisis_graph_extractor import CrisisGraphExtractor
from .risk_repository import RiskRepository
from .expert_society import ExpertSociety
from .domino_engine import DominoEngine
from .trajectory_generator import TrajectoryGenerator

__all__ = [
    'CrisisGraphExtractor',
    'RiskRepository',
    'ExpertSociety',
    'DominoEngine',
    'TrajectoryGenerator',
]
