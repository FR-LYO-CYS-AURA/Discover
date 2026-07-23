"""
Référentiel de risques DISCOVER (socle).

Charge le référentiel normalisé (risk_referentiel.json) et expose des accès
en lecture : catégories, scénarios (64), familles de risque (9), scoring de base.

Le référentiel sert de socle à DISCOVER :
  - intake assisté (sélection catégorie -> scénario) ;
  - contexte pour l'extraction du graphe de crise ;
  - amorçage du scoring par domaine (société d'agents experts).
"""

import os
import json
import threading
from typing import Dict, Any, List, Optional

from ..utils.scoring import compute_scoring
from ..utils.logger import get_logger

logger = get_logger('discover.risk_repository')

_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'risk_referentiel.json')


class RiskRepository:
    """Accès en lecture au référentiel de risques (singleton chargé à la demande)."""

    _instance: Optional["RiskRepository"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._loaded = False
        return cls._instance

    def _ensure_loaded(self):
        if getattr(self, '_loaded', False):
            return
        with self._lock:
            if self._loaded:
                return
            with open(os.path.abspath(_DATA_PATH), 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            self._categories = self._data.get('categories', [])
            self._scenarios = self._data.get('scenarios', [])
            self._families = self._data.get('families', [])
            self._scenario_index = {s['id']: s for s in self._scenarios}
            self._family_index = {fam['domain']: fam for fam in self._families}
            self._loaded = True
            logger.info(
                f"Référentiel chargé : {len(self._categories)} catégories, "
                f"{len(self._scenarios)} scénarios, {len(self._families)} familles"
            )

    # -- Métadonnées --
    def meta(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return self._data.get('meta', {})

    # -- Catégories --
    def get_categories(self) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        return list(self._categories)

    # -- Scénarios --
    def get_scenarios(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        if category_id:
            return [s for s in self._scenarios if s['category_id'] == category_id]
        return list(self._scenarios)

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_loaded()
        scn = self._scenario_index.get(scenario_id)
        if not scn:
            return None
        # enrichit avec le scoring de base
        enriched = dict(scn)
        enriched['scoring'] = compute_scoring(scn['base_probability'], "Élevée")
        return enriched

    # -- Familles (domaines d'impact) --
    def get_families(self) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        return list(self._families)

    def get_family(self, domain: str) -> Optional[Dict[str, Any]]:
        self._ensure_loaded()
        return self._family_index.get(domain)

    def domains(self) -> List[str]:
        self._ensure_loaded()
        return [fam['domain'] for fam in self._families]

    # -- Contexte pour l'extracteur de graphe --
    def scenario_context(self, scenario_id: str) -> Optional[str]:
        """Texte de contexte (description + tags + familles) pour enrichir
        l'extraction du graphe de crise à partir d'un scénario du référentiel."""
        self._ensure_loaded()
        scn = self._scenario_index.get(scenario_id)
        if not scn:
            return None
        families = ", ".join(f['label'] for f in self._families)
        return (
            f"Scénario de référence : « {scn['type']} » (catégorie {scn['category_label']}).\n"
            f"Description de l'aléa : {scn['description']}.\n"
            f"Points sensibles : {', '.join(scn['tags'])}.\n"
            f"Domaines d'impact à considérer : {families}."
        )
