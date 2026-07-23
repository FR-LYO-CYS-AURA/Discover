"""
Moteur d'effets domino DISCOVER (Phase 2).

Approche hybride :
  1. Propagation DÉTERMINISTE sur le graphe de crise : les effets se diffusent
     le long des arêtes, pondérés par le poids d'arête et la criticité des nœuds ;
     amorçage par les nœuds affectés des experts + nœuds vitaux ; la famille
     'resilience' amplifie les chaînes traversant plusieurs domaines.
  2. Qualification / NARRATION par LLM des chaînes de propagation significatives
     (nombre d'appels borné).

Sortie : graphe propagé (impact_score + ordre par nœud) + chaînes de propagation.
"""

from typing import Dict, Any, List, Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('discover.domino_engine')

# Paramètres de propagation
MAX_ROUNDS = 4
DECAY = 0.75              # atténuation par saut
ACTIVE_THRESHOLD = 0.15  # impact minimal pour considérer un nœud "touché"
EDGE_THRESHOLD = 0.12    # flux minimal pour qu'une arête soit "active"
RESILIENCE_AMP = 1.2     # amplification des chaînes multi-domaines
MAX_NARRATED_CHAINS = 8

_SEVERITY_LABELS = {1: "mineure", 2: "modérée", 3: "sérieuse", 4: "élevée", 5: "critique"}

NARRATION_SCHEMA = {
    "type": "object",
    "properties": {
        "chains": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "narrative": {"type": "string", "description": "récit court de la chaîne de propagation"},
                    "severity": {"type": "integer", "description": "sévérité 1-5 de la chaîne"},
                },
                "required": ["index", "narrative"],
            },
        }
    },
    "required": ["chains"],
}


class DominoEngine:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self._llm = llm_client
        self._llm_provided = llm_client is not None

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    # ------------------------------------------------------------------ #
    def propagate(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]],
                  expert_analyses: List[Dict[str, Any]], narrate: bool = True,
                  severity_mult: float = 1.0, decay: Optional[float] = None,
                  resilience_amp: Optional[float] = None, mitigation_factor: float = 0.0,
                  mitigated_node_ids: Optional[List[str]] = None
                  ) -> Dict[str, Any]:
        decay = DECAY if decay is None else decay
        resilience_amp = RESILIENCE_AMP if resilience_amp is None else resilience_amp
        mitigated = set(mitigated_node_ids or [])
        node_by_id = {n['id']: n for n in nodes}
        crit = {n['id']: (n.get('criticality', 3) or 3) / 5.0 for n in nodes}

        # 1) Amorçage : nœuds affectés par les experts (pondérés par sévérité + trajectoire)
        impact: Dict[str, float] = {n['id']: 0.0 for n in nodes}
        order: Dict[str, int] = {}
        for a in expert_analyses:
            sev = (a.get('severity') or {}).get('criticality', 2) / 5.0
            seed = min(1.0, (0.5 + 0.5 * sev) * severity_mult)
            for nid in a.get('affected_node_ids', []):
                if nid in impact:
                    val = seed * (1.0 - mitigation_factor) if nid in mitigated else seed
                    impact[nid] = max(impact[nid], val)
                    order.setdefault(nid, 0)
        # nœuds vitaux non touchés reçoivent une amorce faible
        for n in nodes:
            if crit[n['id']] >= 0.8 and impact[n['id']] == 0.0:
                impact[n['id']] = min(1.0, 0.2 * severity_mult)

        # arêtes experts (propagations inter-domaines) ajoutées comme liens virtuels
        virtual_edges = self._virtual_edges(expert_analyses, node_by_id)
        all_edges = edges + virtual_edges

        # 2) Propagation itérative
        active_flow: Dict[str, float] = {}  # edge_id -> flux max observé
        for rnd in range(1, MAX_ROUNDS + 1):
            delta: Dict[str, float] = {n['id']: 0.0 for n in nodes}
            for e in all_edges:
                s, t = e['source'], e['target']
                if s not in impact or t not in impact:
                    continue
                w = float(e.get('weight', 0.5) or 0.5)
                flow = impact[s] * w * (0.5 + 0.5 * crit.get(t, 0.6)) * (decay ** (rnd - 1))
                if t in mitigated:
                    flow *= (1.0 - mitigation_factor)
                if flow > delta[t]:
                    delta[t] = flow
                eid = e.get('id') or f"{s}->{t}"
                if flow > active_flow.get(eid, 0.0):
                    active_flow[eid] = flow
            changed = False
            for nid, add in delta.items():
                if add > impact[nid] + 1e-6:
                    impact[nid] = min(1.0, add)
                    order[nid] = order.get(nid, rnd)
                    changed = True
            if not changed:
                break

        # 3) Construction des chaînes de propagation
        chains = self._build_chains(all_edges, impact, active_flow, node_by_id)
        chains = self._amplify_resilience(chains, resilience_amp)

        # 4) Narration LLM (bornée)
        if narrate and chains:
            self._narrate(chains)

        propagated_nodes = []
        for n in nodes:
            propagated_nodes.append({
                "id": n['id'],
                "label": n['label'],
                "domain": n.get('domain'),
                "criticality": n.get('criticality', 3),
                "impact_score": round(impact[n['id']], 3),
                "order": order.get(n['id']),
            })
        propagated_edges = []
        for e in edges:
            eid = e.get('id') or f"{e['source']}->{e['target']}"
            propagated_edges.append({**e, "flow": round(active_flow.get(eid, 0.0), 3),
                                     "active": active_flow.get(eid, 0.0) >= EDGE_THRESHOLD})

        return {
            "nodes": propagated_nodes,
            "edges": propagated_edges,
            "chains": chains,
        }

    # ------------------------------------------------------------------ #
    @staticmethod
    def _virtual_edges(expert_analyses: List[Dict[str, Any]],
                       node_by_id: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transforme les propagations inter-domaines des experts en arêtes."""
        virtual = []
        # index : un nœud "représentant" par domaine (le plus critique)
        rep: Dict[str, str] = {}
        for nid, n in node_by_id.items():
            d = n.get('domain')
            if d and (d not in rep or (n.get('criticality', 0) > node_by_id[rep[d]].get('criticality', 0))):
                rep[d] = nid
        for a in expert_analyses:
            src_dom = a.get('domain')
            for p in a.get('propagations', []):
                tgt = p.get('to_node_id') or rep.get(p.get('to_domain'))
                src = rep.get(src_dom)
                if src and tgt and src != tgt:
                    virtual.append({
                        "id": f"exp_{src_dom}_{p.get('to_domain')}",
                        "source": src, "target": tgt,
                        "relation": "propage_vers", "weight": p.get('weight', 0.5),
                        "description": p.get('rationale', ''), "virtual": True,
                    })
        return virtual

    def _build_chains(self, edges: List[Dict[str, Any]], impact: Dict[str, float],
                      active_flow: Dict[str, float], node_by_id: Dict[str, Any]
                      ) -> List[Dict[str, Any]]:
        # arêtes actives ordonnées par flux
        active = []
        for e in edges:
            eid = e.get('id') or f"{e['source']}->{e['target']}"
            f = active_flow.get(eid, 0.0)
            if f >= EDGE_THRESHOLD and e['source'] in node_by_id and e['target'] in node_by_id:
                active.append((f, e))
        active.sort(key=lambda x: x[0], reverse=True)

        # adjacence sur arêtes actives
        adj: Dict[str, List[Dict[str, Any]]] = {}
        for _, e in active:
            adj.setdefault(e['source'], []).append(e)

        # nœuds de départ = affectés en premier (order 0) ou fort impact sans prédécesseur actif
        targets = {e['target'] for _, e in active}
        seeds = [nid for nid, sc in impact.items()
                 if sc >= ACTIVE_THRESHOLD and nid not in targets]
        seeds.sort(key=lambda nid: impact[nid], reverse=True)

        chains = []
        seen_paths = set()
        for seed in seeds[:12]:
            path = self._greedy_path(seed, adj, impact)
            if len(path) < 2:
                continue
            key = tuple(path)
            if key in seen_paths:
                continue
            seen_paths.add(key)
            chains.append(self._chain_record(path, node_by_id, active_flow))
        # trie par poids décroissant
        chains.sort(key=lambda c: c['weight'], reverse=True)
        for i, c in enumerate(chains):
            c['id'] = f"chain_{i+1}"
        return chains

    @staticmethod
    def _greedy_path(seed: str, adj: Dict[str, List[Dict[str, Any]]],
                     impact: Dict[str, float], max_len: int = 6) -> List[str]:
        path = [seed]
        visited = {seed}
        cur = seed
        while len(path) < max_len and cur in adj:
            # choisir l'arête sortante vers le nœud le plus impacté non visité
            candidates = [e for e in adj[cur] if e['target'] not in visited]
            if not candidates:
                break
            best = max(candidates, key=lambda e: impact.get(e['target'], 0) * float(e.get('weight', 0.5)))
            cur = best['target']
            path.append(cur)
            visited.add(cur)
        return path

    @staticmethod
    def _chain_record(path: List[str], node_by_id: Dict[str, Any],
                      active_flow: Dict[str, float]) -> Dict[str, Any]:
        labels = [node_by_id[nid]['label'] for nid in path]
        domains = []
        for nid in path:
            d = node_by_id[nid].get('domain')
            if d and d not in domains:
                domains.append(d)
        # poids de chaîne = min des flux le long du chemin
        flows = []
        for i in range(len(path) - 1):
            eid_guess = None
            # cherche le flux d'une arête reliant path[i]->path[i+1]
            for eid, f in active_flow.items():
                if eid.endswith(path[i + 1]) and path[i] in eid:
                    eid_guess = f
                    break
            flows.append(eid_guess if eid_guess is not None else 0.3)
        weight = round(min(flows) if flows else 0.0, 3)
        return {
            "id": "",
            "path": path,
            "labels": labels,
            "domains": domains,
            "weight": weight,
            "severity": None,
            "narrative": "",
        }

    @staticmethod
    def _amplify_resilience(chains: List[Dict[str, Any]], amp: float = RESILIENCE_AMP) -> List[Dict[str, Any]]:
        for c in chains:
            if len(c['domains']) >= 2:
                c['weight'] = round(min(1.0, c['weight'] * amp), 3)
                c['multi_domain'] = True
            else:
                c['multi_domain'] = False
        chains.sort(key=lambda c: c['weight'], reverse=True)
        return chains

    def _narrate(self, chains: List[Dict[str, Any]]) -> None:
        top = chains[:MAX_NARRATED_CHAINS]
        listing = []
        for i, c in enumerate(top):
            arrow = " → ".join(c['labels'])
            listing.append(f"{i}. [{', '.join(c['domains'])}] {arrow}")
        system = (
            "Tu es analyste de crise. Pour chaque chaîne de propagation (effet domino) fournie, "
            "rédige un récit court (1-2 phrases) expliquant le mécanisme et estime sa sévérité 1-5. "
            "Réponds uniquement en JSON conforme au schéma."
        )
        user = "Chaînes de propagation :\n" + "\n".join(listing)
        try:
            raw = self.llm.chat_json(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.4, max_tokens=1500, schema=NARRATION_SCHEMA,
            )
            by_idx = {int(c.get('index', -1)): c for c in raw.get('chains', []) if isinstance(c, dict)}
            for i, c in enumerate(top):
                info = by_idx.get(i, {})
                c['narrative'] = str(info.get('narrative', '')).strip()
                sev = info.get('severity')
                try:
                    sev = max(1, min(5, int(sev)))
                except (TypeError, ValueError):
                    sev = max(1, min(5, round(c['weight'] * 5)))
                c['severity'] = sev
                c['severity_label'] = _SEVERITY_LABELS.get(sev, "")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Narration LLM des chaînes échouée : {e}")
            for c in top:
                c['severity'] = max(1, min(5, round(c['weight'] * 5)))
                c['severity_label'] = _SEVERITY_LABELS.get(c['severity'], "")
