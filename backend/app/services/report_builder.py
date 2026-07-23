"""
Constructeur de rapport de synthèse DISCOVER (Phase 4).

Assemble un rapport Markdown à partir d'un scénario et de sa simulation
(analyses experts, chaînes domino, trajectoires, scores, décisions).
"""

from datetime import datetime
from typing import Dict, Any, List, Optional


def consolidated_decisions(trajectories: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """Union des décisions des trajectoires, classées par effet max."""
    agg: Dict[tuple, Dict[str, Any]] = {}
    for t in trajectories:
        for d in t.get('decisions', []):
            key = (d.get('domain'), d.get('measure', '').lower())
            cur = agg.get(key)
            if cur is None:
                agg[key] = {
                    "domain_label": d.get('domain_label', d.get('domain')),
                    "type": d.get('type'),
                    "measure": d.get('measure'),
                    "max_effect": d.get('effect_score', 0),
                    "trajectories": [t['type']],
                }
            else:
                cur["max_effect"] = max(cur["max_effect"], d.get('effect_score', 0))
                if t['type'] not in cur["trajectories"]:
                    cur["trajectories"].append(t['type'])
    items = sorted(agg.values(), key=lambda x: x["max_effect"], reverse=True)
    return items[:limit]


def build_markdown(scenario: Any, simulation: Any) -> str:
    L: List[str] = []
    title = getattr(scenario, 'title', None) or 'Scénario de crise'
    L.append(f"# Rapport de crise — {title}")
    L.append(f"*Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')} — DISCOVER*")
    L.append("")

    # Contexte
    L.append("## 1. Contexte")
    L.append(getattr(scenario, 'description', '') or "—")
    if getattr(scenario, 'analysis_summary', None):
        L.append("")
        L.append(f"> {scenario.analysis_summary}")
    L.append("")

    # Graphe de crise
    nodes = getattr(scenario, 'nodes', []) or []
    edges = getattr(scenario, 'edges', []) or []
    L.append("## 2. Graphe de crise")
    L.append(f"- **{len(nodes)}** nœuds (actifs/acteurs) · **{len(edges)}** interdépendances")
    top = sorted(nodes, key=lambda n: n.get('criticality', 0), reverse=True)[:5]
    if top:
        L.append("- Nœuds les plus critiques :")
        for n in top:
            L.append(f"  - **{n.get('label')}** ({n.get('domain')}, criticité {n.get('criticality')}/5)")
    L.append("")

    # Analyses par domaine
    analyses = getattr(simulation, 'expert_analyses', []) or []
    if analyses:
        L.append("## 3. Analyses par domaine d'expert")
        for a in analyses:
            sev = a.get('severity', {})
            L.append(f"### {a.get('domain_label', a.get('domain'))}")
            L.append(f"*Sévérité : probabilité {sev.get('probability')}/5 · gravité "
                     f"{sev.get('gravity')}/5 · criticité {sev.get('criticality')}/5*")
            for imp in a.get('impacts', [])[:4]:
                L.append(f"- {imp}")
            measures = a.get('measures', {}) or {}
            if measures.get('mitigation'):
                L.append(f"- **Mitigation** : {', '.join(measures['mitigation'][:4])}")
            if measures.get('prevention'):
                L.append(f"- **Prévention** : {', '.join(measures['prevention'][:4])}")
            L.append("")

    # Chaînes de propagation
    chains = getattr(simulation, 'propagation_chains', []) or []
    if chains:
        L.append("## 4. Chaînes de propagation (effets domino)")
        for c in chains[:8]:
            path = " → ".join(c.get('labels', []))
            sev = c.get('severity')
            L.append(f"- **{path}**" + (f" *(sévérité {sev}/5)*" if sev else ""))
            if c.get('narrative'):
                L.append(f"  {c['narrative']}")
        L.append("")

    # Trajectoires
    trajectories = getattr(simulation, 'trajectories', []) or []
    if trajectories:
        L.append("## 5. Trajectoires")
        L.append("| Trajectoire | Indice global /100 |")
        L.append("|---|---|")
        for t in trajectories:
            L.append(f"| {t.get('label', t['type'])} | {t.get('scores', {}).get('global_index', '—')} |")
        L.append("")
        for t in trajectories:
            L.append(f"### {t.get('label', t['type'])} "
                     f"(indice {t.get('scores', {}).get('global_index', '—')}/100)")
            if t.get('narrative'):
                L.append(t['narrative'])
            if t.get('key_bifurcations'):
                L.append("")
                L.append("Bascules clés :")
                for b in t['key_bifurcations']:
                    L.append(f"- {b}")
            L.append("")

        # Décisions consolidées
        decisions = consolidated_decisions(trajectories)
        if decisions:
            L.append("## 6. Décisions prioritaires (consolidées)")
            L.append("| Effet | Type | Mesure | Domaine | Trajectoires |")
            L.append("|---|---|---|---|---|")
            for d in decisions:
                typ = "Mitigation" if d['type'] == 'mitigation' else "Prévention"
                L.append(f"| {d['max_effect']} | {typ} | {d['measure']} | "
                         f"{d['domain_label']} | {', '.join(d['trajectories'])} |")
            L.append("")

    L.append("---")
    L.append("*DISCOVER — Simulation de risques, crises et exercices. "
             "Ce rapport est un support d'aide à la décision / d'exercice.*")
    return "\n".join(L)
