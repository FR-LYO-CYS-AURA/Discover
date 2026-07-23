"""
Moteur de scoring DISCOVER (Phase 3).

Scoring déterministe des conséquences et des décisions à partir d'un graphe
propagé (moteur domino) et des analyses d'agents experts.

- Conséquences : criticité par domaine (1-5) + indice global (0-100) par trajectoire.
- Décisions : classement des mesures (prévention/mitigation) par effet estimé,
  pour aider à la priorisation en cellule de crise.
"""

from typing import Dict, Any, List

from .risk_repository import RiskRepository

# Poids par type de mesure (la mitigation agit pendant la crise, la prévention en amont)
_TYPE_WEIGHT = {"mitigation": 1.0, "prevention": 0.6}


def _to_1_5(x: float) -> int:
    """Convertit un impact 0-1 en niveau 1-5."""
    return max(1, min(5, round(1 + 4 * max(0.0, min(1.0, x)))))


def consequence_scores(propagated_nodes: List[Dict[str, Any]],
                       expert_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Score de conséquences : par domaine (1-5) + indice global (0-100)."""
    repo = RiskRepository()
    # domaines présents (via nœuds) + domaines analysés par les experts
    domains = {n.get('domain') for n in propagated_nodes if n.get('domain')}
    domains |= {a['domain'] for a in expert_analyses}

    domain_scores: Dict[str, Any] = {}
    total_mass = 0.0
    weighted_impact = 0.0

    for dom in domains:
        nodes = [n for n in propagated_nodes if n.get('domain') == dom]
        mass = sum((n.get('criticality', 3) or 3) for n in nodes)
        if mass > 0:
            impact = sum((n.get('impact_score', 0.0) or 0.0) * (n.get('criticality', 3) or 3)
                         for n in nodes) / mass
        else:
            # domaine sans nœud propre : reprendre la sévérité experte
            sev = next((a['severity']['criticality'] for a in expert_analyses
                        if a['domain'] == dom and a.get('severity')), 2)
            impact = (sev or 2) / 5.0
            mass = 1.0
        fam = repo.get_family(dom)
        domain_scores[dom] = {
            "label": fam['label'] if fam else dom,
            "impact": round(impact, 3),
            "criticality": _to_1_5(impact),
            "node_count": len(nodes),
        }
        total_mass += mass
        weighted_impact += impact * mass

    global_index = round(100 * (weighted_impact / total_mass), 1) if total_mass else 0.0
    return {"domain_scores": domain_scores, "global_index": global_index}


def decision_scores(expert_analyses: List[Dict[str, Any]],
                    domain_scores: Dict[str, Any], limit: int = 12) -> List[Dict[str, Any]]:
    """Classe les mesures par effet estimé (0-100)."""
    decisions: List[Dict[str, Any]] = []
    seen = set()
    for a in expert_analyses:
        dom = a['domain']
        dom_impact = domain_scores.get(dom, {}).get('impact', 0.4)
        label = a.get('domain_label', dom)
        measures = a.get('measures', {}) or {}
        for mtype in ("mitigation", "prevention"):
            for measure in (measures.get(mtype) or []):
                m = str(measure).strip()
                if not m:
                    continue
                key = (dom, m.lower())
                if key in seen:
                    continue
                seen.add(key)
                # effet = impact du domaine (potentiel de réduction) x poids du type
                effect = round(100 * dom_impact * _TYPE_WEIGHT.get(mtype, 0.6), 1)
                decisions.append({
                    "domain": dom,
                    "domain_label": label,
                    "type": mtype,
                    "measure": m,
                    "effect_score": effect,
                    "rationale": f"Agit sur le domaine « {label} » (impact {round(dom_impact * 100)}%).",
                })
    decisions.sort(key=lambda d: d['effect_score'], reverse=True)
    return decisions[:limit]


def score_trajectory(propagated_nodes: List[Dict[str, Any]],
                     expert_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Scoring complet d'une trajectoire : conséquences + décisions."""
    cons = consequence_scores(propagated_nodes, expert_analyses)
    decisions = decision_scores(expert_analyses, cons['domain_scores'])
    return {
        "domain_scores": cons['domain_scores'],
        "global_index": cons['global_index'],
        "decisions": decisions,
    }
