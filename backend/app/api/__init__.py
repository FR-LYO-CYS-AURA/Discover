"""
API routes DISCOVER

Phase 0 : seul le blueprint `graph` (projets / ontologie / graphe) est actif.
Les blueprints DISCOVER (scenario, simulation d'agents experts, trajectoires,
scoring) seront ajoutés aux Phases 1-4.
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)

from . import graph  # noqa: E402, F401
