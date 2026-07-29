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
from typing import Optional
from flask import request, jsonify, Response

from . import simulation_bp
from ..config import Config
from ..services.expert_society import ExpertSociety
from ..services.domino_engine import DominoEngine
from ..services.trajectory_generator import TrajectoryGenerator
from ..services import report_builder
from ..models.scenario import ScenarioManager
from ..models.simulation import SimulationManager, SimulationStatus
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from ..utils import exec_tracer

logger = get_logger('discover.api.simulation')


def _run_in_scope(fn, label: str, *args):
    """Exécute une tâche de fond dans un scope de trace dédié (récap fichiers)."""
    with exec_tracer.traced_scope(label):
        fn(*args)


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


def _metrics_totals(steps):
    """Calcule les totaux à partir des étapes."""
    return {
        "llm_calls": sum(s.get('llm_calls', 0) for s in steps),
        "tokens_total": sum(s.get('tokens_total', 0) for s in steps),
        "tokens_input": sum(s.get('tokens_input', 0) for s in steps),
        "tokens_output": sum(s.get('tokens_output', 0) for s in steps),
        "cost": round(sum(s.get('cost', 0.0) for s in steps), 6),
    }


def _run_simulation(simulation_id: str, task_id: str):
    """Pipeline : experts -> domino -> narration. Exécuté en thread daemon."""
    import time
    from datetime import datetime as _dt
    from ..utils.usage import UsageTracker
    from ..utils.llm_client import LLMClient

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

    tracker = UsageTracker()
    client = LLMClient(usage_tracker=tracker)
    steps = []
    wall0 = time.perf_counter()

    def run_step(name, fn):
        t0 = time.perf_counter()
        snap0 = tracker.snapshot()
        out = fn()
        d = UsageTracker.delta(tracker.snapshot(), snap0)
        steps.append({"name": name, "duration_s": round(time.perf_counter() - t0, 3), **d})
        return out

    try:
        # 1) Société d'agents experts
        sim.status = SimulationStatus.ANALYZING
        SimulationManager.save_simulation(sim)
        tm.update_task(task_id, status=TaskStatus.PROCESSING, progress=10,
                       message="Analyse par les agents experts")
        society = ExpertSociety(llm_client=client)
        active = society.select_domains(scenario.nodes)
        sim.active_domains = active
        analyses = run_step("analyse_experts",
                            lambda: society.analyze(scenario.description, scenario.nodes,
                                                    scenario.edges, domains=active))
        sim.expert_analyses = analyses
        sim.domain_scores = _aggregate_domain_scores(analyses)
        SimulationManager.save_simulation(sim)

        # 2) Moteur d'effets domino (déterministe puis narration)
        engine = DominoEngine(llm_client=client)
        sim.status = SimulationStatus.PROPAGATING
        SimulationManager.save_simulation(sim)
        tm.update_task(task_id, progress=60, message="Propagation des effets domino")
        result = run_step("propagation",
                         lambda: engine.propagate(scenario.nodes, scenario.edges,
                                                  analyses, narrate=False))
        sim.status = SimulationStatus.NARRATING
        SimulationManager.save_simulation(sim)
        tm.update_task(task_id, progress=85, message="Qualification des chaînes de propagation")
        run_step("narration", lambda: engine._narrate(result['chains']))

        sim.propagated_graph = {"nodes": result["nodes"], "edges": result["edges"]}
        sim.propagation_chains = result["chains"]

        sim.metrics = {
            "started_at": _dt.fromtimestamp(time.time() - (time.perf_counter() - wall0)).isoformat(),
            "ended_at": _dt.now().isoformat(),
            "total_duration_s": round(time.perf_counter() - wall0, 3),
            "model": tracker.snapshot().get("model"),
            "steps": steps,
            "totals": _metrics_totals(steps),
        }
        sim.status = SimulationStatus.COMPLETED
        SimulationManager.save_simulation(sim)
        tm.complete_task(task_id, result={"simulation_id": simulation_id})
        logger.info(f"Simulation {simulation_id} terminée : {len(analyses)} analyses, "
                    f"{len(result['chains'])} chaînes, {sim.metrics['totals']['tokens_total']} tokens")
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
    # titre par défaut : titre du scénario + horodatage
    from datetime import datetime as _dt
    sim.title = f"{scenario.title} — {_dt.now().strftime('%d/%m %H:%M')}"
    SimulationManager.save_simulation(sim)
    task_id = TaskManager().create_task(task_type="crisis_simulation",
                                        metadata={"simulation_id": sim.simulation_id})
    threading.Thread(target=_run_in_scope,
                     args=(_run_simulation, f"simulation:{sim.simulation_id}",
                           sim.simulation_id, task_id),
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
    # cache des titres de scénario
    scn_titles = {}
    items = []
    for s in sims:
        if s.scenario_id not in scn_titles:
            scn = ScenarioManager.get_scenario(s.scenario_id)
            scn_titles[s.scenario_id] = scn.title if scn else s.scenario_id
        totals = (s.metrics or {}).get('totals', {})
        # indice global max des trajectoires (si présentes)
        max_index = None
        if s.trajectories:
            vals = [t.get('scores', {}).get('global_index') for t in s.trajectories]
            vals = [v for v in vals if v is not None]
            max_index = max(vals) if vals else None
        items.append({
            "simulation_id": s.simulation_id,
            "scenario_id": s.scenario_id,
            "scenario_title": scn_titles[s.scenario_id],
            "title": s.title or scn_titles[s.scenario_id],
            "status": s.status.value,
            "trajectories_status": s.trajectories_status,
            "created_at": s.created_at,
            "active_domains": s.active_domains,
            "chains_count": len(s.propagation_chains),
            "max_global_index": max_index,
            "duration_s": (s.metrics or {}).get('total_duration_s'),
            "tokens_total": totals.get('tokens_total'),
            "cost": totals.get('cost'),
            "model": (s.metrics or {}).get('model'),
        })
    return jsonify({"success": True, "data": items})


@simulation_bp.route('/<simulation_id>', methods=['PATCH'])
def rename_simulation(simulation_id: str):
    sim = SimulationManager.get_simulation(simulation_id)
    if not sim:
        return jsonify({"success": False, "error": f"Simulation introuvable: {simulation_id}"}), 404
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({"success": False, "error": "Le champ 'title' est requis"}), 400
    sim.title = title[:120]
    SimulationManager.save_simulation(sim)
    return jsonify({"success": True, "data": {"simulation_id": simulation_id, "title": sim.title}})


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
        import time
        from ..utils.usage import UsageTracker
        from ..utils.llm_client import LLMClient
        sim.trajectories_status = "generating"
        SimulationManager.save_simulation(sim)
        tm.update_task(task_id, status=TaskStatus.PROCESSING, progress=20,
                       message="Génération des trajectoires")
        tracker = UsageTracker()
        gen = TrajectoryGenerator(llm_client=LLMClient(usage_tracker=tracker))
        t0 = time.perf_counter()
        trajectories = gen.generate(scenario.description, scenario.nodes,
                                    scenario.edges, sim.expert_analyses)
        snap = tracker.snapshot()
        sim.trajectories = trajectories
        sim.trajectories_status = "completed"
        # ajoute l'étape trajectoires aux métriques
        metrics = sim.metrics or {}
        steps = metrics.get('steps', [])
        steps.append({
            "name": "trajectoires",
            "duration_s": round(time.perf_counter() - t0, 3),
            "llm_calls": snap["calls"],
            "tokens_total": snap["tokens_total"],
            "tokens_input": snap["tokens_input"],
            "tokens_output": snap["tokens_output"],
            "cost": snap["cost"],
        })
        metrics['steps'] = steps
        metrics['totals'] = _metrics_totals(steps)
        if snap.get("model"):
            metrics['model'] = snap.get("model")
        sim.metrics = metrics
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
    threading.Thread(target=_run_in_scope,
                     args=(_generate_trajectories, f"trajectories:{simulation_id}",
                           simulation_id, task_id),
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


# --------------------------------------------------------------------------- #
# Rapport de synthèse (Phase 4)
# --------------------------------------------------------------------------- #
def _build_report(simulation_id: str) -> Optional[str]:
    sim = SimulationManager.get_simulation(simulation_id)
    if not sim:
        return None
    scenario = ScenarioManager.get_scenario(sim.scenario_id)
    return report_builder.build_markdown(scenario, sim)


@simulation_bp.route('/<simulation_id>/report', methods=['GET'])
def get_report(simulation_id: str):
    md = _build_report(simulation_id)
    if md is None:
        return jsonify({"success": False, "error": f"Simulation introuvable: {simulation_id}"}), 404
    return jsonify({"success": True, "data": {"markdown": md}})


@simulation_bp.route('/<simulation_id>/report/download', methods=['GET'])
def download_report(simulation_id: str):
    md = _build_report(simulation_id)
    if md is None:
        return jsonify({"success": False, "error": f"Simulation introuvable: {simulation_id}"}), 404
    filename = f"rapport_crise_{simulation_id}.md"
    return Response(
        md, mimetype="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
