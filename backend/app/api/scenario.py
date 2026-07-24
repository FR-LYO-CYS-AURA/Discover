"""
API des scénarios de crise DISCOVER.

Endpoints (préfixe /api/scenario) :
  POST   /create           crée un scénario et extrait le graphe de crise (synchrone)
  POST   /<id>/extract     (re)lance l'extraction du graphe de crise
  GET    /<id>             détail d'un scénario (avec graphe)
  GET    /<id>/graph       graphe de crise seul (nodes/edges)
  GET    /list             liste des scénarios
  DELETE /<id>             suppression
"""

import traceback
from flask import request, jsonify

from . import scenario_bp
from ..config import Config
from ..services.crisis_graph_extractor import CrisisGraphExtractor
from ..services.risk_repository import RiskRepository
from ..models.scenario import ScenarioManager, ScenarioStatus
from ..utils.logger import get_logger

logger = get_logger('discover.api.scenario')


def _run_extraction(scenario):
    """Exécute l'extraction du graphe de crise et met à jour le scénario."""
    scenario.status = ScenarioStatus.EXTRACTING
    ScenarioManager.save_scenario(scenario)
    try:
        import time
        from ..utils.usage import UsageTracker
        from ..utils.llm_client import LLMClient
        tracker = UsageTracker()
        extractor = CrisisGraphExtractor(llm_client=LLMClient(usage_tracker=tracker))
        t0 = time.perf_counter()
        result = extractor.extract(scenario.description, context=scenario.context)
        duration = round(time.perf_counter() - t0, 3)
        snap = tracker.snapshot()
        scenario.metrics = {
            "extraction": {
                "duration_s": duration,
                "llm_calls": snap["calls"],
                "tokens_total": snap["tokens_total"],
                "tokens_input": snap["tokens_input"],
                "tokens_output": snap["tokens_output"],
                "cost": snap["cost"],
                "model": snap.get("model"),
            }
        }
        ScenarioManager.set_graph(
            scenario,
            nodes=result['nodes'],
            edges=result['edges'],
            analysis_summary=result.get('analysis_summary'),
        )
        return True, None
    except Exception as e:  # noqa: BLE001
        logger.error(f"Extraction échouée: {e}\n{traceback.format_exc()}")
        scenario.status = ScenarioStatus.FAILED
        scenario.error = str(e)
        ScenarioManager.save_scenario(scenario)
        return False, str(e)


@scenario_bp.route('/create', methods=['POST'])
def create_scenario():
    """Crée un scénario puis extrait le graphe de crise (synchrone)."""
    if not Config.llm_ready():
        return jsonify({"success": False, "error": "Backend LLM indisponible (voir OpenCode / LLM_BACKEND)"}), 503

    data = request.get_json(silent=True) or {}
    description = (data.get('description') or '').strip()
    title = (data.get('title') or '').strip() or 'Scénario sans titre'
    context = (data.get('context') or '').strip() or None

    # Si un scénario du référentiel est fourni, on enrichit le contexte d'extraction
    ref_id = (data.get('referentiel_scenario_id') or '').strip()
    if ref_id:
        ref_context = RiskRepository().scenario_context(ref_id)
        if ref_context:
            context = f"{context}\n\n{ref_context}" if context else ref_context

    if not description:
        return jsonify({"success": False, "error": "Le champ 'description' est requis"}), 400

    scenario = ScenarioManager.create_scenario(title=title, description=description, context=context)
    ok, err = _run_extraction(scenario)
    if not ok:
        return jsonify({
            "success": False,
            "error": err,
            "data": scenario.to_dict(),
        }), 500

    return jsonify({"success": True, "data": scenario.to_dict()})


@scenario_bp.route('/<scenario_id>/extract', methods=['POST'])
def extract_scenario(scenario_id: str):
    """(Re)lance l'extraction du graphe de crise pour un scénario existant."""
    if not Config.llm_ready():
        return jsonify({"success": False, "error": "Backend LLM indisponible (voir OpenCode / LLM_BACKEND)"}), 503

    scenario = ScenarioManager.get_scenario(scenario_id)
    if not scenario:
        return jsonify({"success": False, "error": f"Scénario introuvable: {scenario_id}"}), 404

    ok, err = _run_extraction(scenario)
    if not ok:
        return jsonify({"success": False, "error": err, "data": scenario.to_dict()}), 500
    return jsonify({"success": True, "data": scenario.to_dict()})


@scenario_bp.route('/<scenario_id>', methods=['GET'])
def get_scenario(scenario_id: str):
    scenario = ScenarioManager.get_scenario(scenario_id)
    if not scenario:
        return jsonify({"success": False, "error": f"Scénario introuvable: {scenario_id}"}), 404
    return jsonify({"success": True, "data": scenario.to_dict()})


@scenario_bp.route('/<scenario_id>/graph', methods=['GET'])
def get_scenario_graph(scenario_id: str):
    scenario = ScenarioManager.get_scenario(scenario_id)
    if not scenario:
        return jsonify({"success": False, "error": f"Scénario introuvable: {scenario_id}"}), 404
    return jsonify({
        "success": True,
        "data": {
            "nodes": scenario.nodes,
            "edges": scenario.edges,
            "analysis_summary": scenario.analysis_summary,
            "status": scenario.status.value,
        },
    })


@scenario_bp.route('/list', methods=['GET'])
def list_scenarios():
    limit = request.args.get('limit', 50, type=int)
    scenarios = ScenarioManager.list_scenarios(limit=limit)
    # Vue allégée pour la liste (sans les graphes complets)
    items = []
    for s in scenarios:
        items.append({
            "scenario_id": s.scenario_id,
            "title": s.title,
            "status": s.status.value,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "node_count": len(s.nodes),
            "edge_count": len(s.edges),
        })
    return jsonify({"success": True, "data": items})


@scenario_bp.route('/<scenario_id>', methods=['DELETE'])
def delete_scenario(scenario_id: str):
    ok = ScenarioManager.delete_scenario(scenario_id)
    if not ok:
        return jsonify({"success": False, "error": f"Scénario introuvable: {scenario_id}"}), 404
    return jsonify({"success": True, "data": {"deleted": scenario_id}})
