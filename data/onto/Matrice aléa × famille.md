---
type: "Règle"
label: "Matrice aléa × famille"
lignes_csv_équivalentes: "1152"
---

# Matrice aléa × famille

Le référentiel est **exhaustif par construction** : chacun des **64 types d'aléa** se décline dans chacune des **9 familles de risque**, à raison de 2 intitulés par famille.

> 64 aléas × 9 familles × 2 intitulés = **1152 lignes** dans `data/referentiel_risques.csv`

> [!warning] Pourquoi ces 1152 combinaisons ne sont pas des notes
> Le croisement étant **complet**, il ne porte aucune information distinctive : tout aléa est associé à tous les risques. Les matérialiser donnerait 1152 notes et ~2300 liens strictement équivalents, noyant l'ontologie réelle. La règle est donc énoncée ici une fois pour toutes.

## Les 8 catégories d’aléa

- [[Accident]] (8 aléas)
- [[Aléa naturel]] (8 aléas)
- [[Invasion]] (8 aléas)
- [[Médico-sanitaire]] (8 aléas)
- [[Mouvement social]] (8 aléas)
- [[Pénurie]] (8 aléas)
- [[Socio-culturel – politique – écologique]] (8 aléas)
- [[Terrorisme ou malveillance]] (8 aléas)

## Les 9 familles de risque

- [[Opérationnel]] — `operationnel`
- [[Industriel – technique]] — `technique`
- [[Ressources humaines]] — `rh`
- [[Juridique – conformité]] — `juridique`
- [[Financier]] — `finance`
- [[Image – réputation]] — `communication`
- [[Géopolitique – institutionnel]] — `geopolitique`
- [[Informatique – numérique]] — `cybersecurite`
- [[Défaillance – résilience]] — `resilience`

---

La **criticité** de chaque combinaison se calcule via [[Matrice de criticité]].
