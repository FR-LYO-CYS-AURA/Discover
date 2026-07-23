"""
API du référentiel de risques DISCOVER.

Endpoints (préfixe /api/referentiel) :
  GET /meta                     métadonnées du référentiel
  GET /categories               liste des 8 catégories d'aléa
  GET /scenarios[?category=id]  liste des scénarios (64), filtrable par catégorie
  GET /scenario/<id>            détail d'un scénario (avec scoring de base)
  GET /families                 liste des 9 familles de risque (domaines d'impact)
"""

from flask import request, jsonify

from . import referentiel_bp
from ..services.risk_repository import RiskRepository

_repo = RiskRepository()


@referentiel_bp.route('/meta', methods=['GET'])
def get_meta():
    return jsonify({"success": True, "data": _repo.meta()})


@referentiel_bp.route('/categories', methods=['GET'])
def get_categories():
    return jsonify({"success": True, "data": _repo.get_categories()})


@referentiel_bp.route('/scenarios', methods=['GET'])
def get_scenarios():
    category_id = request.args.get('category')
    return jsonify({"success": True, "data": _repo.get_scenarios(category_id)})


@referentiel_bp.route('/scenario/<scenario_id>', methods=['GET'])
def get_scenario(scenario_id: str):
    scn = _repo.get_scenario(scenario_id)
    if not scn:
        return jsonify({"success": False, "error": f"Scénario introuvable: {scenario_id}"}), 404
    return jsonify({"success": True, "data": scn})


@referentiel_bp.route('/families', methods=['GET'])
def get_families():
    return jsonify({"success": True, "data": _repo.get_families()})
