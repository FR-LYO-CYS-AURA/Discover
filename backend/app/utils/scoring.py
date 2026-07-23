"""
Scoring des risques DISCOVER.

Conversion des niveaux qualitatifs (Faible/Moyenne/Élevée/Critique) en valeurs
numériques 1-5 et calcul de la criticité via une matrice de risque, alignée sur
le référentiel de risques.
"""

from typing import Dict

PROB_VALUE: Dict[str, int] = {"Faible": 2, "Moyenne": 3, "Élevée": 4, "Critique": 5}
GRAV_VALUE: Dict[str, int] = {"Faible": 2, "Moyenne": 3, "Élevée": 4, "Critique": 5}

# Ordre des niveaux pour comparaisons / affichage
LEVELS = ["Faible", "Moyenne", "Élevée", "Critique"]


def prob_to_value(label: str) -> int:
    return PROB_VALUE.get(label, 3)


def grav_to_value(label: str) -> int:
    return GRAV_VALUE.get(label, 4)


def criticite_label(prob: str, grav: str) -> str:
    """Matrice de risque (fidèle au référentiel, criticité plafonnée à Élevée
    pour les combinaisons présentes ; Critique réservé aux cas extrêmes)."""
    score = prob_to_value(prob) * grav_to_value(grav)
    if score <= 12:
        return "Moyenne"
    if score <= 20:
        return "Élevée"
    return "Critique"


def criticite_value(prob: str, grav: str) -> int:
    """Criticité numérique 1-5 (à partir du produit prob*grav, borné)."""
    score = prob_to_value(prob) * grav_to_value(grav)
    # 6..25 -> 1..5
    return max(1, min(5, round(score / 5)))


def compute_scoring(prob: str, grav: str) -> Dict[str, object]:
    """Retourne un scoring complet (labels + valeurs numériques)."""
    return {
        "probability": prob,
        "gravity": grav,
        "criticality": criticite_label(prob, grav),
        "probability_value": prob_to_value(prob),
        "gravity_value": grav_to_value(grav),
        "criticality_value": criticite_value(prob, grav),
    }
