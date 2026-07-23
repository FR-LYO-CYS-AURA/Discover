"""
API de simulation de crise DISCOVER (Phase 2).

Endpoints (préfixe /api/simulation) :
  POST /run                 lance une simulation (async) sur un scénario
  POST /run/status          statut d'une tâche de simulation
  GET  /<id>                détail d'une simulation
  GET  /<id>/status         statut/progression d'une simulation
  GET  /list[?scenario_id=] liste des simulations
  DELETE /<id>              suppression
"""

import traceback
import threading
from flask import request, jsonify

from . import simulation_bp
from ..config import Config
from ..services.expert_society import ExpertSociety
from ..services.domino_engine import DominoEngine
from ..services.trajectory_generator import TrajectoryGenerator
from ..models.scenario import ScenarioManager
from ..models.simulation import SimulationManager, SimulationStatus
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger

logger = get_logger('discover.api.simulation')


def _aggregate_domain_scores(expert_analyses):
    """Agrégat simple de criticité par domaine (échelle 1-5)."""
    scores = {}
    for a in expert_analyses:
        sev = a.get('severity', {})
        scores[a['domain']] = {
            "label": a.get('domain_label', a['domain']),
            "probability": sev.get('probability'),
            "gravity": sev.get('gravity'),
            "criticality": sev.get('criticality'),
            "affected_count": len(a.get('affected_node_ids', [])),
            "propagation_count": len(a.get('propagations', [])),
        }
    return scores


def _run_simulation(simulation_id: str, task_id: str):
    """Pipeline : experts -> domino -> narration. Exécuté en thread daemon."""
    tm = TaskManager()
    sim = SimulationManager.get_simulation(simulation_id)
    if not sim:
        tm.fail_task(task_id, "Simulation introuvable")
        return
    scenario = ScenarioManager.get_scenario(sim.scenario_id)
    if not scenario or not scenario.nodes:
        sim.status = SimulationStatus.FAILED
        sim.error = "Scénario ou graphe de crise indisponible"
        SimulationManager.save_simulation(sim)
        tm.fail_task(task_id, sim.error)
        return

    try:
        # 1) Société d'agents experts
        sim.status = SimulationStatus.ANALYZING
        SimulationManager.save_simulation(sim)
        tm.update_task(task_id, status=TaskStatus.PROCESSING, progress=10,
                       message="Analyse par les agents experts")
        society = ExpertSociety()
        active = society.select_domains(scenario.nodes)
        sim.active_domains = active
        analyses = society.analyze(scenario.description, scenario.nodes, scenario.edges, domains=active)
        sim.expert_analyses = analyses
        sim.domain_scores = _aggregate_domain_scores(analyses)
        SimulationManager.save_simulation(sim)

        # 2) Moteur d'effets domino (déterministe + narration)
        sim.status = SimulationStatus.PROPAGATING
        SimulationManager.save_simulation(sim)
        tm.update_task(task_id, progress=65, message="Propagation des effets domino")
        engine = DominoEngine()
        sim.status = SimulationStatus.NARRATING
        SimulationManager.save_simulation(sim)
        tm.update_task(task_id, progress=85, message="Qualification des chaînes de propagation")
        result = engine.propagate(scenario.nodes, scenario.edges, analyses, narrate=True)
        sim.propagated_graph = {"nodes": result["nodes"], "edges": result["edges"]}
        sim.propagation_chains = result["chains"]

        sim.status = SimulationStatus.COMPLETED
        SimulationManager.save_simulation(sim)
        tm.complete_task(task_id, result={"simulation_id": simulation_id})
        logger.info(f"Simulation {simulation_id} terminée : "
                    f"{len(analyses)} analyses, {len(result['chains'])} chaînes")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Simulation {simulation_id} échouée : {e}\n{traceback.format_exc()}")
        sim.status = SimulationStatus.FAILED
        sim.error = str(e)
        SimulationManager.save_simulation(sim)
        tm.fail_task(task_id, str(e))


@simulation_bp.route('/run', methods=['POST'])
def run_simulation():
    if not Config.llm_ready():
        return jsonify({"success": False, "error": "Backend LLM indisponible"}), 503
    data = request.get_json(silent=True) or {}
    scenario_id = (data.get('scenario_id') or '').strip()
    if not scenario_id:
        return jsonify({"success": False, "error": "Le champ 'scenario_id' est requis"}), 400
    scenario = ScenarioManager.get_scenario(scenario_id)
    if not scenario:
        return jsonify({"success": False, "error": f"Scénario introuvable: {scenario_id}"}), 404
    if not scenario.nodes:
        return jsonify({"success": False, "error": "Le graphe de crise n'est pas encore extrait"}), 400

    sim = SimulationManager.create_simulation(scenario_id)
    task_id = TaskManager().create_task(task_type="crisis_simulation",
                                        metadata={"simulation_id": sim.simulation_id})
    threading.Thread(target=_run_simulation, args=(sim.simulation_id, task_id),
                     daemon=True).start()
    return jsonify({"success": True, "data": {
        "simulation_id": sim.simulation_id, "task_id": task_id,
    }})


@simulation_bp.route('/run/status', methods=['POST'])
def run_status():
    data = request.get_json(silent=True) or {}
    task_id = (data.get('task_id') or '').strip()
    task = TaskManager().get_task(task_id)
    if not task:
        return jsonify({"success": False, "error": "Tâche introuvable"}), 404
    return jsonify({"success": True, "data": task.to_dict()})


@simulation_bp.route('/<simulation_id>', methods=['GET'])
def get_simulation(simulation_id: str):
    sim = SimulationManager.get_simulation(simulation_id)
    if not sim:
        return jsonify({"success": False, "error": f"Simulation introuvable: {simulation_id}"}), 404
    return jsonify({"success": True, "data": sim.to_dict()})


@simulation_bp.route('/<simulation_id>/status', methods=['GET'])
def simulation_status(simulation_id: str):
    sim = SimulationManager.get_simulation(simulation_id)
    if not sim:
        return jsonify({"success": False, "error": f"Simulation introuvable: {simulation_id}"}), 404
    return jsonify({"success": True, "data": {
        "simulation_id": sim.simulation_id,
        "status": sim.status.value,
        "active_domains": sim.active_domains,
        "analyses_count": len(sim.expert_analyses),
        "chains_count": len(sim.propagation_chains),
        "error": sim.error,
    }})


@simulation_bp.route('/list', methods=['GET'])
def list_simulations():
    scenario_id = request.args.get('scenario_id')
    limit = request.args.get('limit', 50, type=int)
    sims = SimulationManager.list_simulations(scenario_id=scenario_id, limit=limit)
    items = [{
        "simulation_id": s.simulation_id,
        "scenario_id": s.scenario_id,
        "status": s.status.value,
        "created_at": s.created_at,
        "active_domains": s.active_domains,
        "chains_count": len(s.propagation_chains),
    } for s in sims]
    return jsonify({"success": True, "data": items})


@simulation_bp.route('/<simulation_id>', methods=['DELETE'])
def delete_simulation(simulation_id: str):
    ok = SimulationManager.delete_simulation(simulation_id)
    if not ok:
        return jsonify({"success": False, "error": f"Simulation introuvable: {simulation_id}"}), 404
    return jsonify({"success": True, "data": {"deleted": simulation_id}})


# --------------------------------------------------------------------------- #
# Trajectoires (Phase 3)
# --------------------------------------------------------------------------- #
def _generate_trajectories(simulation_id: str, task_id: str):
    tm = TaskManager()
    sim = SimulationManager.get_simulation(simulation_id)
    if not sim:
        tm.fail_task(task_id, "Simulation introuvable")
        return
    scenario = ScenarioManager.get_scenario(sim.scenario_id)
    if not scenario:
        sim.trajectories_status = "failed"
        SimulationManager.save_simulation(sim)
        tm.fail_task(task_id, "Scénario introuvable")
        return
    try:
        sim.trajectories_status = "generating"
        SimulationManager.save_simulation(sim)
        tm.update_task(task_id, status=TaskStatus.PROCESSING, progress=20,
                       message="Génération des trajectoires")
        gen = TrajectoryGenerator()
        trajectories = gen.generate(scenario.description, scenario.nodes,
                                    scenario.edges, sim.expert_analyses)
        sim.trajectories = trajectories
        sim.trajectories_status = "completed"
        SimulationManager.save_simulation(sim)
        tm.complete_task(task_id, result={"simulation_id": simulation_id,
                                           "count": len(trajectories)})
        logger.info(f"Trajectoires {simulation_id} : {len(trajectories)} générées")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Trajectoires {simulation_id} échouées : {e}\n{traceback.format_exc()}")
        sim.trajectories_status = "failed"
        sim.error = str(e)
        SimulationManager.save_simulation(sim)
        tm.fail_task(task_id, str(e))


@simulation_bp.route('/<simulation_id>/trajectories', methods=['POST'])
def generate_trajectories(simulation_id: str):
    if not Config.llm_ready():
        return jsonify({"success": False, "error": "Backend LLM indisponible"}), 503
    sim = SimulationManager.get_simulation(simulation_id)
    if not sim:
        return jsonify({"success": False, "error": f"Simulation introuvable: {simulation_id}"}), 404
    if sim.status != SimulationStatus.COMPLETED:
        return jsonify({"success": False, "error": "La simulation n'est pas terminée"}), 400
    task_id = TaskManager().create_task(task_type="crisis_trajectories",
                                        metadata={"simulation_id": simulation_id})
    threading.Thread(target=_generate_trajectories, args=(simulation_id, task_id),
                     daemon=True).start()
    return jsonify({"success": True, "data": {"simulation_id": simulation_id, "task_id": task_id}})


@simulation_bp.route('/<simulation_id>/trajectories', methods=['GET'])
def get_trajectories(simulation_id: str):
    sim = SimulationManager.get_simulation(simulation_id)
    if not sim:
        return jsonify({"success": False, "error": f"Simulation introuvable: {simulation_id}"}), 404
    return jsonify({"success": True, "data": {
        "simulation_id": simulation_id,
        "trajectories_status": sim.trajectories_status,
        "trajectories": sim.trajectories,
    }})
