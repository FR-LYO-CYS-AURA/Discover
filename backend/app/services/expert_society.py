"""
Société d'agents experts DISCOVER (Phase 2).

Active un agent par domaine d'impact pertinent (parmi les 9 familles de risque)
et produit, pour chaque domaine, une analyse spécialisée au scénario réel :
impacts, sévérité, nœuds affectés, propagations inter-domaines et mesures.

- Sélection des domaines pertinents = domaines présents dans le graphe de crise
  ∩ EXPERT_DOMAINS, plus 'resilience' (qui pilote les effets domino).
- Exécution parallèle (ThreadPoolExecutor) via le client LLM (harness OpenCode).
- Spécialisation LLM des impacts/prévention/mitigation génériques du référentiel.
"""

import concurrent.futures
from typing import Dict, Any, List, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .risk_repository import RiskRepository

logger = get_logger('discover.expert_society')


# Schéma de sortie d'un agent expert (sortie structurée OpenCode)
EXPERT_SCHEMA = {
    "type": "object",
    "properties": {
        "impacts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "impacts concrets dans ce domaine, spécialisés au scénario",
        },
        "severity": {
            "type": "object",
            "properties": {
                "probability": {"type": "integer", "description": "probabilité 1 (faible) à 5 (quasi certaine)"},
                "gravity": {"type": "integer", "description": "gravité 1 (mineure) à 5 (critique)"},
            },
            "required": ["probability", "gravity"],
        },
        "affected_node_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "ids de nœuds du graphe affectés dans ce domaine",
        },
        "propagations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "to_domain": {"type": "string", "description": "domaine impacté par effet domino"},
                    "to_node_id": {"type": "string", "description": "id de nœud cible (optionnel)"},
                    "weight": {"type": "number", "description": "force de propagation 0.0-1.0"},
                    "rationale": {"type": "string", "description": "mécanisme de propagation (court)"},
                },
                "required": ["to_domain", "weight", "rationale"],
            },
        },
        "measures": {
            "type": "object",
            "properties": {
                "prevention": {"type": "array", "items": {"type": "string"}},
                "mitigation": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "required": ["impacts", "severity", "affected_node_ids", "propagations"],
}


def _clamp_int(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(round(float(v)))))
    except (TypeError, ValueError):
        return default


def _clamp_float(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


class ExpertSociety:
    """Orchestre les agents experts sur un graphe de crise."""

    ALWAYS_ON = ["resilience"]  # domaine toujours actif (pilote le domino)

    def __init__(self, llm_client: Optional[LLMClient] = None, parallel: int = 5):
        self.llm = llm_client or LLMClient()
        self.parallel = parallel
        self.repo = RiskRepository()

    # -- Sélection des domaines pertinents --
    def select_domains(self, nodes: List[Dict[str, Any]]) -> List[str]:
        expert_domains = set(Config.EXPERT_DOMAINS)
        present = {n.get('domain') for n in nodes if n.get('domain') in expert_domains}
        for d in self.ALWAYS_ON:
            present.add(d)
        if not present:
            # fallback minimal si le graphe ne référence aucun domaine d'expert
            present = {'operationnel', 'resilience'}
        # ordonner selon EXPERT_DOMAINS
        return [d for d in Config.EXPERT_DOMAINS if d in present]

    # -- Contexte sous-graphe pour un domaine --
    @staticmethod
    def _subgraph_context(domain: str, nodes: List[Dict[str, Any]],
                          edges: List[Dict[str, Any]]) -> str:
        own = [n for n in nodes if n.get('domain') == domain]
        own_ids = {n['id'] for n in own}
        related_ids = set()
        for e in edges:
            if e['source'] in own_ids:
                related_ids.add(e['target'])
            if e['target'] in own_ids:
                related_ids.add(e['source'])
        lines = ["Nœuds de votre domaine :"]
        for n in own:
            lines.append(f"  - [{n['id']}] {n['label']} (criticité {n.get('criticality', 3)}/5) : {n.get('description', '')}")
        if not own:
            lines.append("  (aucun nœud directement rattaché à votre domaine)")
        rel_nodes = [n for n in nodes if n['id'] in related_ids]
        if rel_nodes:
            lines.append("Nœuds voisins (autres domaines) :")
            for n in rel_nodes:
                lines.append(f"  - [{n['id']}] {n['label']} ({n.get('domain')})")
        rel_edges = [e for e in edges if e['source'] in own_ids or e['target'] in own_ids]
        if rel_edges:
            lines.append("Interdépendances :")
            for e in rel_edges:
                lines.append(f"  - {e['source']} --[{e['relation']}, w={e.get('weight')}]--> {e['target']}")
        return "\n".join(lines)

    def _system_prompt(self, family: Dict[str, Any]) -> str:
        return (
            f"Tu es l'agent expert du domaine « {family['label']} » d'une cellule de crise.\n"
            f"Cadre de référence pour ton domaine :\n"
            f"  - Impacts types : {family['impacts']}\n"
            f"  - Prévention type : {family['prevention']}\n"
            f"  - Mitigation type : {family['mitigation']}\n"
            "Analyse la crise décrite SPÉCIFIQUEMENT pour ton domaine (ne recopie pas le générique, "
            "spécialise-le au scénario et au graphe). Identifie les nœuds affectés, estime la sévérité, "
            "et surtout les PROPAGATIONS par effet domino vers d'autres domaines. "
            "Réponds uniquement en JSON conforme au schéma."
        )

    def _run_agent(self, domain: str, description: str,
                   nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        family = self.repo.get_family(domain) or {"label": domain, "impacts": "", "prevention": "", "mitigation": ""}
        system = self._system_prompt(family)
        user = (
            f"Description de la crise :\n{description}\n\n"
            f"Contexte du graphe de crise pour le domaine « {family['label']} » :\n"
            f"{self._subgraph_context(domain, nodes, edges)}\n\n"
            f"Domaines d'experts activés (cibles possibles de propagation) : "
            f"{', '.join(Config.EXPERT_DOMAINS)}."
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            raw = self.llm.chat_json(messages, temperature=0.3, max_tokens=2048, schema=EXPERT_SCHEMA)
            return self._normalize(domain, family, raw, nodes)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Agent expert '{domain}' en échec, fallback règles : {e}")
            return self._fallback(domain, family, nodes)

    def _normalize(self, domain: str, family: Dict[str, Any],
                   raw: Dict[str, Any], nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        valid_ids = {n['id'] for n in nodes}
        expert_domains = set(Config.EXPERT_DOMAINS)
        sev = raw.get('severity') or {}
        prob = _clamp_int(sev.get('probability'), 1, 5, 3)
        grav = _clamp_int(sev.get('gravity'), 1, 5, 4)
        crit = max(1, min(5, round((prob * grav) / 5)))

        propagations = []
        for p in (raw.get('propagations') or []):
            if not isinstance(p, dict):
                continue
            to_dom = str(p.get('to_domain', '')).strip().lower()
            if to_dom not in expert_domains or to_dom == domain:
                continue
            to_node = p.get('to_node_id')
            to_node = to_node if to_node in valid_ids else None
            propagations.append({
                "to_domain": to_dom,
                "to_node_id": to_node,
                "weight": round(_clamp_float(p.get('weight', 0.5), 0.0, 1.0, 0.5), 2),
                "rationale": str(p.get('rationale', '')).strip(),
            })

        affected = [nid for nid in (raw.get('affected_node_ids') or []) if nid in valid_ids]
        measures = raw.get('measures') or {}
        return {
            "domain": domain,
            "domain_label": family['label'],
            "impacts": [str(x).strip() for x in (raw.get('impacts') or []) if str(x).strip()][:8],
            "severity": {"probability": prob, "gravity": grav, "criticality": crit},
            "affected_node_ids": affected,
            "propagations": propagations,
            "measures": {
                "prevention": [str(x).strip() for x in (measures.get('prevention') or []) if str(x).strip()][:6],
                "mitigation": [str(x).strip() for x in (measures.get('mitigation') or []) if str(x).strip()][:6],
            },
        }

    def _fallback(self, domain: str, family: Dict[str, Any],
                  nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        affected = [n['id'] for n in nodes if n.get('domain') == domain]
        return {
            "domain": domain,
            "domain_label": family['label'],
            "impacts": [family.get('impacts', '')],
            "severity": {"probability": 3, "gravity": 4, "criticality": 2},
            "affected_node_ids": affected,
            "propagations": [],
            "measures": {
                "prevention": [family.get('prevention', '')],
                "mitigation": [family.get('mitigation', '')],
            },
            "fallback": True,
        }

    # -- Orchestration --
    def analyze(self, description: str, nodes: List[Dict[str, Any]],
                edges: List[Dict[str, Any]], domains: Optional[List[str]] = None
                ) -> List[Dict[str, Any]]:
        active = domains or self.select_domains(nodes)
        logger.info(f"Société d'agents experts : {len(active)} domaines actifs {active}")
        results: List[Dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.parallel) as ex:
            futures = {ex.submit(self._run_agent, d, description, nodes, edges): d for d in active}
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())
        # ordonner selon EXPERT_DOMAINS
        order = {d: i for i, d in enumerate(Config.EXPERT_DOMAINS)}
        results.sort(key=lambda a: order.get(a['domain'], 99))
        return results
