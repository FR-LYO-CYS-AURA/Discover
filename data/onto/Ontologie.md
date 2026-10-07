---
type: "Index"
label: "Ontologie DISCOVER"
---

# Ontologie du référentiel de risques

Représentation en **graphe de connaissance** du référentiel de risques socle de DISCOVER (`data/referentiel_risques.csv`).

## Classes

| Classe | Nombre | Dossier | Porte |
|---|---|---|---|
| Catégorie d’aléa | 8 | `Catégories/` | — |
| Type d’aléa | 64 | `Aléas/` | description, tags, **probabilité** |
| Famille de risque | 9 | `Familles/` | impacts, prévention, mitigation, **gravité** |
| Risque | 18 | `Risques/` | — |
| Valeur de scoring | 6 | `Scoring/` | poids |

## Relations

```
Catégorie d’aléa  ──comprend──▶  Type d’aléa
Famille de risque ──comprend──▶  Risque

Type d’aléa       ──probabilité──▶  ┐
                                    ├──▶  Criticité
Famille de risque ──gravité─────▶  ┘
```

Les deux taxonomies (aléas / risques) sont reliées par le **scoring** : voir [[Matrice de criticité]]. Le croisement exhaustif aléa × famille est décrit dans [[Matrice aléa × famille]].

## Comment explorer

1. **Vue graphe** (`Ctrl/Cmd + G`) — les couleurs par dossier sont préconfigurées.
2. **Afficher les étiquettes** dans les options de la vue graphe pour faire apparaître les tags transversaux entre aléas.
3. **Canvas** `Ontologie — schéma.canvas` — disposition fixe, pour présenter.

## Points d’entrée

### Catégories d’aléa

- [[Accident]]
- [[Aléa naturel]]
- [[Invasion]]
- [[Médico-sanitaire]]
- [[Mouvement social]]
- [[Pénurie]]
- [[Socio-culturel – politique – écologique]]
- [[Terrorisme ou malveillance]]

### Familles de risque

- [[Opérationnel]]
- [[Industriel – technique]]
- [[Ressources humaines]]
- [[Juridique – conformité]]
- [[Financier]]
- [[Image – réputation]]
- [[Géopolitique – institutionnel]]
- [[Informatique – numérique]]
- [[Défaillance – résilience]]

---

_Vault généré par `backend/scripts/build_ontology_vault.py` — ne pas éditer à la main._
