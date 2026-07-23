"""
Extracteur de graphe de crise (DISCOVER).

À partir de la description d'une situation de crise en langage naturel,
un LLM extrait un graphe structuré :
  - noeuds = actifs / acteurs / services / processus impliqués, typés par domaine
  - arêtes = interdépendances pondérées (support des effets domino ultérieurs)

Adapté du service OntologyGenerator du socle MiroFish.
"""

import re
import json
from typing import Dict, Any, List, Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..config import Config

logger = get_logger('discover.crisis_graph_extractor')


# Vocabulaire contrôlé -------------------------------------------------------

# Domaines de noeud (alignés sur les domaines d'experts + catégories de crise)
ALLOWED_DOMAINS = set(Config.EXPERT_DOMAINS) | {
    'physique', 'geopolitique', 'reglementaire', 'reputation', 'autre'
}

# Types de noeud
ALLOWED_NODE_TYPES = {
    'actif',      # actif technique / SI / équipement
    'acteur',     # personne, équipe, organisation
    'service',    # service métier (soins, paie...)
    'processus',  # processus / activité
    'ressource',  # ressource (finances, stock, énergie...)
    'externe',    # entité externe (régulateur, média, fournisseur...)
}

# Types de relation (orientées cause -> conséquence potentielle)
ALLOWED_RELATIONS = {
    'depend_de',    # A dépend de B
    'impacte',      # A impacte B
    'fournit',      # A fournit / alimente B
    'regule',       # A régule / contrôle B
    'communique',   # A communique avec B
    'heberge',      # A héberge B
    'protege',      # A protège B
}


# JSON Schema de sortie (exploité par la sortie structurée native d'OpenCode)
CRISIS_GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "identifiant court snake_case"},
                    "label": {"type": "string", "description": "nom lisible du noeud"},
                    "domain": {"type": "string", "description": "domaine parmi la liste autorisée"},
                    "type": {"type": "string", "description": "type parmi la liste autorisée"},
                    "criticality": {"type": "integer", "description": "criticité de 1 (mineur) à 5 (vital)"},
                    "description": {"type": "string", "description": "rôle du noeud dans la crise"},
                },
                "required": ["id", "label", "domain", "type", "criticality"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "id du noeud source"},
                    "target": {"type": "string", "description": "id du noeud cible"},
                    "relation": {"type": "string", "description": "relation parmi la liste autorisée"},
                    "weight": {"type": "number", "description": "force de propagation de 0.0 à 1.0"},
                    "description": {"type": "string", "description": "nature de l'interdépendance"},
                },
                "required": ["source", "target", "relation", "weight"],
            },
        },
        "analysis_summary": {"type": "string", "description": "synthèse et chaînes de propagation"},
    },
    "required": ["nodes", "edges"],
}


SYSTEM_PROMPT = """Tu es un expert en gestion de crise et en analyse de risques systémiques.
À partir de la description d'une situation de crise, tu construis un GRAPHE DE CRISE
structuré, exploitable pour modéliser des effets domino entre domaines.

Tu dois répondre STRICTEMENT en JSON valide avec la structure suivante :
{
  "nodes": [
    {
      "id": "identifiant_court_snake_case",
      "label": "Nom lisible du noeud",
      "domain": "un domaine parmi la liste autorisée",
      "type": "un type parmi la liste autorisée",
      "criticality": 1-5,
      "description": "rôle du noeud dans la crise (1-2 phrases)"
    }
  ],
  "edges": [
    {
      "source": "id_noeud_source",
      "target": "id_noeud_cible",
      "relation": "une relation parmi la liste autorisée",
      "weight": 0.0-1.0,
      "description": "nature de l'interdépendance (courte)"
    }
  ],
  "analysis_summary": "synthèse de la situation et des principales chaînes de propagation (3-6 phrases)"
}

RÈGLES :
- domain ∈ {cybersecurite, sante, rh, juridique, finance, communication, operations, logistique, physique, geopolitique, reglementaire, reputation, autre}
- type ∈ {actif, acteur, service, processus, ressource, externe}
- relation ∈ {depend_de, impacte, fournit, regule, communique, heberge, protege}
- criticality : entier de 1 (mineur) à 5 (vital)
- weight : force de propagation de 0.0 (faible) à 1.0 (forte)
- Entre 8 et 25 noeuds ; couvre plusieurs domaines (pas seulement le domaine déclencheur).
- Les "id" des arêtes DOIVENT référencer des "id" de noeuds existants.
- Modélise explicitement les interdépendances qui permettront de tracer les effets domino
  (ex. SI -> service de soins -> RH -> réputation -> régulateur).
- Réponds uniquement avec le JSON, sans texte autour, sans balises Markdown."""


def _slugify(text: str, fallback: str) -> str:
    """Génère un id court snake_case à partir d'un libellé."""
    if not text:
        return fallback
    text = text.strip().lower()
    text = re.sub(r'[àáâä]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[^a-z0-9]+', '_', text)
    text = text.strip('_')
    return text[:40] or fallback


def _clamp(value, lo, hi, default):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


class CrisisGraphExtractor:
    """Extrait un graphe de crise structuré depuis une description en langage naturel."""

    MAX_TEXT_LENGTH = 20000  # tronque les descriptions trop longues avant l'appel LLM

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def extract(self, description: str, context: Optional[str] = None,
                max_retries: int = 2) -> Dict[str, Any]:
        """
        Extrait le graphe de crise.

        Returns: {"nodes": [...], "edges": [...], "analysis_summary": str}
        """
        if not description or not description.strip():
            raise ValueError("La description du scénario est vide.")

        user_content = f"Description de la crise :\n{description.strip()[:self.MAX_TEXT_LENGTH]}"
        if context and context.strip():
            user_content += f"\n\nContexte additionnel :\n{context.strip()[:self.MAX_TEXT_LENGTH]}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        last_error: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Extraction du graphe de crise (tentative {attempt}/{max_retries})")
                raw = self.llm.chat_json(messages, temperature=0.3, max_tokens=4096,
                                         schema=CRISIS_GRAPH_SCHEMA)
                return self._validate_and_normalize(raw)
            except Exception as e:  # noqa: BLE001
                last_error = e
                logger.warning(f"Échec extraction (tentative {attempt}): {e}")

        raise RuntimeError(f"Extraction du graphe de crise échouée : {last_error}")

    # -- Validation / normalisation -----------------------------------------

    def _validate_and_normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("Réponse LLM invalide (objet attendu).")

        raw_nodes = raw.get('nodes') or []
        raw_edges = raw.get('edges') or []
        summary = raw.get('analysis_summary') or ''

        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise ValueError("Aucun noeud extrait.")

        # --- Noeuds ---
        nodes: List[Dict[str, Any]] = []
        seen_ids = set()
        for i, n in enumerate(raw_nodes):
            if not isinstance(n, dict):
                continue
            label = str(n.get('label') or n.get('id') or f"noeud_{i+1}").strip()
            node_id = str(n.get('id') or '').strip()
            if not node_id:
                node_id = _slugify(label, f"n{i+1}")
            else:
                node_id = _slugify(node_id, f"n{i+1}")
            # unicité des id
            base_id = node_id
            k = 2
            while node_id in seen_ids:
                node_id = f"{base_id}_{k}"
                k += 1
            seen_ids.add(node_id)

            domain = str(n.get('domain') or 'autre').strip().lower()
            if domain not in ALLOWED_DOMAINS:
                domain = 'autre'
            node_type = str(n.get('type') or 'actif').strip().lower()
            if node_type not in ALLOWED_NODE_TYPES:
                node_type = 'actif'
            criticality = int(_clamp(n.get('criticality', 3), 1, 5, 3))

            nodes.append({
                "id": node_id,
                "label": label,
                "domain": domain,
                "type": node_type,
                "criticality": criticality,
                "description": str(n.get('description') or '').strip(),
            })

        valid_ids = {n['id'] for n in nodes}
        # Table de correspondance libellé -> id (pour rattraper des arêtes référencées par label)
        label_to_id = {n['label'].strip().lower(): n['id'] for n in nodes}

        # --- Arêtes ---
        edges: List[Dict[str, Any]] = []
        seen_edges = set()
        for j, e in enumerate(raw_edges):
            if not isinstance(e, dict):
                continue
            src = str(e.get('source') or '').strip()
            dst = str(e.get('target') or '').strip()
            # résolution par id direct, puis id slugifié, puis label
            src_id = self._resolve_ref(src, valid_ids, label_to_id)
            dst_id = self._resolve_ref(dst, valid_ids, label_to_id)
            if not src_id or not dst_id or src_id == dst_id:
                continue

            relation = str(e.get('relation') or 'impacte').strip().lower()
            if relation not in ALLOWED_RELATIONS:
                relation = 'impacte'
            weight = round(_clamp(e.get('weight', 0.5), 0.0, 1.0, 0.5), 2)

            dedup_key = (src_id, dst_id, relation)
            if dedup_key in seen_edges:
                continue
            seen_edges.add(dedup_key)

            edges.append({
                "id": f"e{j+1}",
                "source": src_id,
                "target": dst_id,
                "relation": relation,
                "weight": weight,
                "description": str(e.get('description') or '').strip(),
            })

        logger.info(f"Graphe de crise : {len(nodes)} noeuds, {len(edges)} arêtes")
        return {
            "nodes": nodes,
            "edges": edges,
            "analysis_summary": str(summary).strip(),
        }

    @staticmethod
    def _resolve_ref(ref: str, valid_ids: set, label_to_id: Dict[str, str]) -> Optional[str]:
        if not ref:
            return None
        if ref in valid_ids:
            return ref
        slug = _slugify(ref, '')
        if slug in valid_ids:
            return slug
        return label_to_id.get(ref.strip().lower())
