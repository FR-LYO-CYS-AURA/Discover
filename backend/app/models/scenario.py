"""
Modèle de scénario de crise DISCOVER.

Un Scenario porte la description en langage naturel fournie par le décideur,
et le graphe de crise extrait (actifs/acteurs + interdépendances pondérées).
Persistance JSON sur disque (un dossier par scénario), sur le modèle de
ProjectManager du socle MiroFish.
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


class ScenarioStatus(str, Enum):
    """État d'un scénario."""
    CREATED = "created"          # créé, description saisie
    EXTRACTING = "extracting"    # extraction du graphe de crise en cours
    GRAPH_READY = "graph_ready"  # graphe de crise disponible
    FAILED = "failed"            # échec


@dataclass
class Scenario:
    """Scénario de crise."""
    scenario_id: str
    title: str
    description: str
    status: ScenarioStatus
    created_at: str
    updated_at: str

    # Contexte additionnel optionnel (contraintes, périmètre, secteur...)
    context: Optional[str] = None

    # Graphe de crise extrait
    nodes: List[Dict[str, Any]] = field(default_factory=list)  # CrisisNode
    edges: List[Dict[str, Any]] = field(default_factory=list)  # CrisisEdge
    analysis_summary: Optional[str] = None

    # Erreur éventuelle
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, ScenarioStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context": self.context,
            "nodes": self.nodes,
            "edges": self.edges,
            "analysis_summary": self.analysis_summary,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scenario':
        status = data.get('status', 'created')
        if isinstance(status, str):
            status = ScenarioStatus(status)
        return cls(
            scenario_id=data['scenario_id'],
            title=data.get('title', 'Scénario sans titre'),
            description=data.get('description', ''),
            status=status,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            context=data.get('context'),
            nodes=data.get('nodes', []),
            edges=data.get('edges', []),
            analysis_summary=data.get('analysis_summary'),
            error=data.get('error'),
        )


class ScenarioManager:
    """Gestionnaire de persistance des scénarios (un dossier JSON par scénario)."""

    SCENARIOS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'scenarios')

    @classmethod
    def _ensure_dir(cls):
        os.makedirs(cls.SCENARIOS_DIR, exist_ok=True)

    @classmethod
    def _get_dir(cls, scenario_id: str) -> str:
        return os.path.join(cls.SCENARIOS_DIR, scenario_id)

    @classmethod
    def _get_meta_path(cls, scenario_id: str) -> str:
        return os.path.join(cls._get_dir(scenario_id), 'scenario.json')

    @classmethod
    def create_scenario(cls, title: str, description: str,
                        context: Optional[str] = None) -> Scenario:
        cls._ensure_dir()
        scenario_id = f"scn_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        scenario = Scenario(
            scenario_id=scenario_id,
            title=title or 'Scénario sans titre',
            description=description,
            status=ScenarioStatus.CREATED,
            created_at=now,
            updated_at=now,
            context=context,
        )
        os.makedirs(cls._get_dir(scenario_id), exist_ok=True)
        cls.save_scenario(scenario)
        return scenario

    @classmethod
    def save_scenario(cls, scenario: Scenario) -> None:
        scenario.updated_at = datetime.now().isoformat()
        with open(cls._get_meta_path(scenario.scenario_id), 'w', encoding='utf-8') as f:
            json.dump(scenario.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def get_scenario(cls, scenario_id: str) -> Optional[Scenario]:
        meta_path = cls._get_meta_path(scenario_id)
        if not os.path.exists(meta_path):
            return None
        with open(meta_path, 'r', encoding='utf-8') as f:
            return Scenario.from_dict(json.load(f))

    @classmethod
    def list_scenarios(cls, limit: int = 50) -> List[Scenario]:
        cls._ensure_dir()
        scenarios = []
        for scenario_id in os.listdir(cls.SCENARIOS_DIR):
            scenario = cls.get_scenario(scenario_id)
            if scenario:
                scenarios.append(scenario)
        scenarios.sort(key=lambda s: s.created_at, reverse=True)
        return scenarios[:limit]

    @classmethod
    def delete_scenario(cls, scenario_id: str) -> bool:
        scenario_dir = cls._get_dir(scenario_id)
        if not os.path.exists(scenario_dir):
            return False
        shutil.rmtree(scenario_dir)
        return True

    @classmethod
    def set_graph(cls, scenario: Scenario, nodes: List[Dict[str, Any]],
                  edges: List[Dict[str, Any]],
                  analysis_summary: Optional[str] = None) -> None:
        scenario.nodes = nodes
        scenario.edges = edges
        scenario.analysis_summary = analysis_summary
        scenario.status = ScenarioStatus.GRAPH_READY
        scenario.error = None
        cls.save_scenario(scenario)
