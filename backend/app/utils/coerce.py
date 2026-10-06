"""
Coercition défensive des sorties LLM.

Les modèles ne respectent pas toujours le schéma demandé : un champ déclaré
`array` peut revenir sous forme de chaîne (parfois un tableau JSON encodé en
chaîne), de dict, ou être absent. Sans garde, `for x in valeur` sur une chaîne
itère **caractère par caractère** et corrompt silencieusement les données
(bug observé : impacts == ['[', '"', 'B', 'l', ...]).

Ces helpers garantissent qu'on ne produit jamais une liste de caractères à
partir d'une chaîne, et que l'accès par clé ne lève pas d'AttributeError.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

__all__ = ["as_list", "as_dict", "as_str_list"]


def as_list(value: Any) -> List[Any]:
    """Coercition vers une liste, sans jamais exploser une chaîne en caractères.

    - list/tuple/set  -> list(value)
    - str             -> tente un décodage JSON ('["a","b"]' -> ['a','b']) ;
                         sinon la chaîne devient un élément unique.
                         Une chaîne vide (ou blanche) donne [].
    - dict            -> [] (un objet n'est pas une collection d'items ici)
    - None            -> []
    - scalaire        -> [value]
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        # Cas fréquent : le modèle encode le tableau en chaîne.
        if text[0] in '[{':
            try:
                decoded = json.loads(text)
            except (ValueError, TypeError):
                return [value]
            if isinstance(decoded, list):
                return decoded
            # Un objet JSON isolé reste un élément unique.
            return [decoded]
        return [value]
    if isinstance(value, dict):
        return []
    return [value]


def as_dict(value: Any) -> Dict[str, Any]:
    """Coercition vers un dict, pour sécuriser les accès `.get(...)`.

    - dict -> tel quel
    - str  -> tente un décodage JSON ; ne conserve que si c'est un objet
    - autre/None -> {}
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text[:1] == '{':
            try:
                decoded = json.loads(text)
            except (ValueError, TypeError):
                return {}
            if isinstance(decoded, dict):
                return decoded
    return {}


def as_str_list(value: Any, limit: Optional[int] = None) -> List[str]:
    """Liste de chaînes nettoyées (vides écartées), tronquée à `limit`.

    Remplace le motif `[str(x).strip() for x in (raw.get(k) or []) if ...][:n]`
    qui corrompt les données lorsque `raw[k]` est une chaîne.
    """
    out: List[str] = []
    for item in as_list(value):
        if item is None:
            continue
        # Un sous-objet est sérialisé plutôt que rendu en "{'a': 1}".
        if isinstance(item, (dict, list)):
            try:
                text = json.dumps(item, ensure_ascii=False)
            except (TypeError, ValueError):
                text = str(item)
        else:
            text = str(item)
        text = text.strip()
        if text:
            out.append(text)
    if limit is not None:
        return out[:limit]
    return out
