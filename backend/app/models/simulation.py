"""
Modèle de simulation DISCOVER (Phase 2).

Une Simulation applique la société d'agents experts + le moteur d'effets domino
à un scénario de crise (dont le graphe a été extrait en Phase 1) et stocke :
  - les analyses par domaine d'expert (ExpertAnalysis) ;
  - les chaînes de propagation (PropagationChain) ;
  - le graphe propagé (états de nœuds : impact_score, ordre).

Persistance JSON (un dossier par simulation), sur le modèle de ScenarioManager.
Plusieurs simulations peuvent être rattachées à un même scénario.
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from ..config import Config


class SimulationStatus(str, Enum):
    CREATED = "created"
    ANALYZING = "analyzing"        # société d'agents experts en cours
    PROPAGATING = "propagating"    # moteur domino (déterministe)
    NARRATING = "narrating"        # qualification/narration LLM des chaînes
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Simulation:
    """Résultat d'une simulation de crise."""
    simulation_id: str
    scenario_id: str
    status: SimulationStatus
    created_at: str
    updated_at: str

    title: str = ""

    active_domains: List[str] = field(default_factory=list)
    expert_analyses: List[Dict[str, Any]] = field(default_factory=list)   # ExpertAnalysis
    propagation_chains: List[Dict[str, Any]] = field(default_factory=list)  # PropagationChain
    propagated_graph: Dict[str, Any] = field(default_factory=dict)        # {nodes:[{id,impact_score,order,domain}], ...}
    domain_scores: Dict[str, Any] = field(default_factory=dict)          # agrégat criticité par domaine

    # Trajectoires (Phase 3)
    trajectories: List[Dict[str, Any]] = field(default_factory=list)     # 4 trajectoires + scores
    trajectories_status: str = "none"                                    # none|generating|completed|failed

    # Métriques (tokens, coût, durée par étape)
    metrics: Dict[str, Any] = field(default_factory=dict)

    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "scenario_id": self.scenario_id,
            "title": self.title,
            "status": self.status.value if isinstance(self.status, SimulationStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "active_domains": self.active_domains,
            "expert_analyses": self.expert_analyses,
            "propagation_chains": self.propagation_chains,
            "propagated_graph": self.propagated_graph,
            "domain_scores": self.domain_scores,
            "trajectories": self.trajectories,
            "trajectories_status": self.trajectories_status,
            "metrics": self.metrics,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Simulation":
        status = data.get('status', 'created')
        if isinstance(status, str):
            status = SimulationStatus(status)
        return cls(
            simulation_id=data['simulation_id'],
            scenario_id=data['scenario_id'],
            title=data.get('title', ''),
            status=status,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            active_domains=data.get('active_domains', []),
            expert_analyses=data.get('expert_analyses', []),
            propagation_chains=data.get('propagation_chains', []),
            propagated_graph=data.get('propagated_graph', {}),
            domain_scores=data.get('domain_scores', {}),
            trajectories=data.get('trajectories', []),
            trajectories_status=data.get('trajectories_status', 'none'),
            metrics=data.get('metrics', {}),
            error=data.get('error'),
        )


class SimulationManager:
    """Persistance des simulations (un dossier JSON par simulation)."""

    SIM_DIR = os.path.join(Config.UPLOAD_FOLDER, 'crisis_simulations')

    @classmethod
    def _ensure_dir(cls):
        os.makedirs(cls.SIM_DIR, exist_ok=True)

    @classmethod
    def _get_dir(cls, simulation_id: str) -> str:
        return os.path.join(cls.SIM_DIR, simulation_id)

    @classmethod
    def _get_meta_path(cls, simulation_id: str) -> str:
        return os.path.join(cls._get_dir(simulation_id), 'simulation.json')

    @classmethod
    def create_simulation(cls, scenario_id: str) -> Simulation:
        cls._ensure_dir()
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        sim = Simulation(
            simulation_id=simulation_id,
            scenario_id=scenario_id,
            status=SimulationStatus.CREATED,
            created_at=now,
            updated_at=now,
        )
        os.makedirs(cls._get_dir(simulation_id), exist_ok=True)
        cls.save_simulation(sim)
        return sim

    @classmethod
    def save_simulation(cls, sim: Simulation) -> None:
        sim.updated_at = datetime.now().isoformat()
        path = cls._get_meta_path(sim.simulation_id)
        # écriture atomique (évite les lectures partielles pendant le polling)
        tmp = f"{path}.tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(sim.to_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    @classmethod
    def get_simulation(cls, simulation_id: str) -> Optional[Simulation]:
        meta = cls._get_meta_path(simulation_id)
        if not os.path.exists(meta):
            return None
        try:
            with open(meta, 'r', encoding='utf-8') as f:
                return Simulation.from_dict(json.load(f))
        except (json.JSONDecodeError, ValueError):
            # lecture concurrente d'un fichier en cours d'écriture : nouvelle tentative
            import time as _t
            _t.sleep(0.05)
            with open(meta, 'r', encoding='utf-8') as f:
                return Simulation.from_dict(json.load(f))

    @classmethod
    def list_simulations(cls, scenario_id: Optional[str] = None, limit: int = 50) -> List[Simulation]:
        cls._ensure_dir()
        sims = []
        for sid in os.listdir(cls.SIM_DIR):
            sim = cls.get_simulation(sid)
            if sim and (scenario_id is None or sim.scenario_id == scenario_id):
                sims.append(sim)
        sims.sort(key=lambda s: s.created_at, reverse=True)
        return sims[:limit]

    @classmethod
    def delete_simulation(cls, simulation_id: str) -> bool:
        d = cls._get_dir(simulation_id)
        if not os.path.exists(d):
            return False
        shutil.rmtree(d)
        return True
