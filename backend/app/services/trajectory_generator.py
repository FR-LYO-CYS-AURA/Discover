"""
Générateur de trajectoires DISCOVER (Phase 3).

À partir d'une simulation complétée (graphe de crise + analyses experts), génère
4 trajectoires plausibles (optimiste / intermédiaire / critique / rupture) via une
approche HYBRIDE :
  - variation déterministe de paramètres (sévérité, mitigation, propagation) puis
    ré-exécution du moteur domino et scoring par branche ;
  - un unique appel LLM produisant les 4 narratifs + bascules clés.
"""

from typing import Dict, Any, List, Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .domino_engine import DominoEngine
from . import scoring_engine

logger = get_logger('discover.trajectory_generator')

# Paramètres par trajectoire (severity_mult, mitigation_factor, decay, resilience_amp)
TRAJECTORY_PARAMS = {
    "optimiste": {
        "label": "Optimiste",
        "severity_mult": 0.6, "mitigation_factor": 0.7, "decay": 0.6, "resilience_amp": 1.05,
        "hypothesis": "Détection rapide, mesures de mitigation efficaces, propagation contenue.",
    },
    "intermediaire": {
        "label": "Intermédiaire",
        "severity_mult": 1.0, "mitigation_factor": 0.4, "decay": 0.75, "resilience_amp": 1.2,
        "hypothesis": "Réponse partielle, propagation modérée, quelques domaines débordés.",
    },
    "critique": {
        "label": "Critique",
        "severity_mult": 1.3, "mitigation_factor": 0.2, "decay": 0.85, "resilience_amp": 1.35,
        "hypothesis": "Réponse tardive, mitigation faible, propagation forte multi-domaines.",
    },
    "rupture": {
        "label": "Rupture",
        "severity_mult": 1.6, "mitigation_factor": 0.05, "decay": 0.92, "resilience_amp": 1.6,
        "hypothesis": "Défaillances en cascade, résilience saturée, effondrement systémique.",
    },
}

TRAJECTORY_ORDER = ["optimiste", "intermediaire", "critique", "rupture"]

NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "trajectories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "narrative": {"type": "string", "description": "récit de la trajectoire (2-4 phrases)"},
                    "key_bifurcations": {
                        "type": "array", "items": {"type": "string"},
                        "description": "bascules décisives qui mènent à cette trajectoire",
                    },
                },
                "required": ["type", "narrative"],
            },
        }
    },
    "required": ["trajectories"],
}


class TrajectoryGenerator:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self._llm = llm_client
        self.engine = DominoEngine(llm_client=llm_client)

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def generate(self, description: str, nodes: List[Dict[str, Any]],
                 edges: List[Dict[str, Any]], expert_analyses: List[Dict[str, Any]]
                 ) -> List[Dict[str, Any]]:
        # nœuds couverts par une mesure de mitigation (cible de réduction d'impact)
        mitigated = set()
        for a in expert_analyses:
            if (a.get('measures') or {}).get('mitigation'):
                mitigated.update(a.get('affected_node_ids', []))
        mitigated = list(mitigated)

        trajectories: List[Dict[str, Any]] = []
        for ttype in TRAJECTORY_ORDER:
            p = TRAJECTORY_PARAMS[ttype]
            result = self.engine.propagate(
                nodes, edges, expert_analyses, narrate=False,
                severity_mult=p["severity_mult"], decay=p["decay"],
                resilience_amp=p["resilience_amp"], mitigation_factor=p["mitigation_factor"],
                mitigated_node_ids=mitigated,
            )
            scores = scoring_engine.score_trajectory(result["nodes"], expert_analyses)
            trajectories.append({
                "type": ttype,
                "label": p["label"],
                "hypothesis": p["hypothesis"],
                "params": {k: p[k] for k in ("severity_mult", "mitigation_factor", "decay", "resilience_amp")},
                "propagated_graph": {"nodes": result["nodes"], "edges": result["edges"]},
                "chains": result["chains"],
                "scores": {"domain_scores": scores["domain_scores"], "global_index": scores["global_index"]},
                "decisions": scores["decisions"],
                "narrative": "",
                "key_bifurcations": [],
            })

        # Narratifs LLM (un seul appel pour les 4)
        self._narrate(description, trajectories)
        return trajectories

    def _narrate(self, description: str, trajectories: List[Dict[str, Any]]) -> None:
        listing = []
        for t in trajectories:
            top = sorted(t["scores"]["domain_scores"].items(),
                         key=lambda kv: kv[1]["impact"], reverse=True)[:3]
            doms = ", ".join(f"{v['label']} ({v['criticality']}/5)" for _, v in top)
            listing.append(
                f"- {t['type']} (indice global {t['scores']['global_index']}/100) : "
                f"{t['hypothesis']} Domaines les plus touchés : {doms}."
            )
        system = (
            "Tu es analyste de crise. Pour chaque trajectoire fournie, rédige un récit court "
            "(2-4 phrases) cohérent avec son indice global et ses domaines touchés, et liste les "
            "bascules décisives (key_bifurcations) qui y mènent. Réponds uniquement en JSON."
        )
        user = f"Crise :\n{description}\n\nTrajectoires :\n" + "\n".join(listing)
        try:
            raw = self.llm.chat_json(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.5, max_tokens=1800, schema=NARRATIVE_SCHEMA,
            )
            by_type = {str(x.get('type', '')).strip().lower(): x
                       for x in raw.get('trajectories', []) if isinstance(x, dict)}
            for t in trajectories:
                info = by_type.get(t['type'], {})
                t['narrative'] = str(info.get('narrative', '')).strip()
                kb = info.get('key_bifurcations') or []
                t['key_bifurcations'] = [str(x).strip() for x in kb if str(x).strip()][:5]
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Narration LLM des trajectoires échouée : {e}")
            for t in trajectories:
                t['narrative'] = t['hypothesis']
