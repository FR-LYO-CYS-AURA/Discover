# DISCOVER

**FR — Simulation de risques, crises et exercices de gestion de crise par société d'agents IA.**
**EN — Simulation of risks, crises and crisis-management exercises powered by a society of AI agents.**

> **FR —** Décrivez une situation de crise en langage naturel. DISCOVER active une société
> d'agents experts, modélise les effets domino entre domaines, génère plusieurs
> trajectoires plausibles et vous aide à décider grâce à un scoring en temps réel.
>
> **EN —** Describe a crisis situation in natural language. DISCOVER activates a society of
> expert agents, models domino effects across domains, generates several plausible
> trajectories and supports your decisions with real-time scoring.

DISCOVER est à la fois un **outil d'aide à la décision en temps réel** et un
**générateur d'exercices de gestion de crise**. Son approche prédictive et
adaptative permet d'anticiper les impacts, d'explorer les futurs possibles et de
renforcer la résilience des organisations.

*DISCOVER is both a **real-time decision-support tool** and a **crisis-management
exercise generator**. Its predictive and adaptive approach anticipates impacts,
explores possible futures and strengthens organizational resilience.*

---

## Concept

**FR**

Imaginez une cyberattaque paralysant plusieurs établissements de santé pendant le G7.
Le décideur décrit simplement la situation. DISCOVER :

1. **Comprend** la situation et en extrait les actifs, domaines et interdépendances.
2. **Active une société d'agents spécialisés** (cybersécurité, santé, RH, juridique,
   finance, communication, opérations, logistique…), chacun analysant les impacts
   dans son domaine et les interactions avec les autres.
3. **Modélise les effets domino** : propagation des conséquences sur le SI, les soins,
   les ressources humaines, les finances, les obligations réglementaires, l'image de
   l'organisation et l'impact sur le secteur de la santé du territoire.
4. **Génère plusieurs trajectoires** plausibles : *optimiste, intermédiaire, critique,
   rupture*.
5. **Visualise en temps réel** les causes, conséquences et chaînes de propagation.
6. **Aide à décider** via un scoring de conséquences et de décisions.
7. **(À venir) What-if temps réel** : tester des hypothèses et mesurer instantanément
   leurs effets.

**EN**

Imagine a cyberattack paralyzing several healthcare facilities during the G7 summit.
The decision-maker simply describes the situation. DISCOVER:

1. **Understands** the situation and extracts assets, domains and interdependencies.
2. **Activates a society of specialized agents** (cybersecurity, health, HR, legal,
   finance, communication, operations, logistics…), each analyzing impacts in its
   domain and the interactions with the others.
3. **Models domino effects**: propagation of consequences across the IS, care delivery,
   human resources, finances, regulatory obligations, the organization's reputation
   and the impact on the territory's healthcare sector.
4. **Generates several plausible trajectories**: *optimistic, intermediate, critical,
   breakdown*.
5. **Visualizes in real time** the causes, consequences and propagation chains.
6. **Supports decisions** through consequence and decision scoring.
7. **(Upcoming) Real-time What-if**: test hypotheses and instantly measure their effects.

### Paramètres modélisés / Modeled parameters

- **FR** — Risques : physique, numérique, juridique, géopolitique… · Interdépendances entre
  actifs et domaines · Événements observés et effets domino · Conséquences : SI, soins, RH,
  finances, conformité réglementaire, image, territoire.
- **EN** — Risks: physical, digital, legal, geopolitical… · Interdependencies between assets
  and domains · Observed events and domino effects · Consequences: IS, care, HR, finances,
  regulatory compliance, reputation, territory.

---

## Architecture

**FR —** DISCOVER est un fork de [MiroFish](https://github.com/666ghj/MiroFish) (moteur
d'intelligence collective, AGPL-3.0), dont on réutilise le squelette et la visualisation, en
**remplaçant le moteur de simulation sociale (OASIS) par une société d'agents experts et un
moteur d'effets domino**.

**EN —** DISCOVER is a fork of [MiroFish](https://github.com/666ghj/MiroFish) (swarm
intelligence engine, AGPL-3.0). We reuse its skeleton and visualization while **replacing the
social-simulation engine (OASIS) with a society of expert agents and a domino-effect engine**.

```
Frontend (Vue 3 + Vite + D3.js)
  1. Intake scénario   ->  2. Cartographie du graphe de crise
  3. Simulation agents ->  4. Trajectoires & scoring
        | REST + polling
Backend (Flask, Python)
  |- risk_repository          Referentiel de risques socle (64 scenarios, 9 familles)
  |- crisis_graph_extractor   Extraction actifs / domaines / interdependances (LLM)
  |- graph_builder (Zep)      Graphe d'interdependances (GraphRAG)
  |- expert_society           Societe d'agents experts par domaine (9 familles)
  |- domino_engine            Propagation des effets sur le graphe (famille resilience)
  |- trajectory_generator     4 trajectoires (optimiste -> rupture) [hybride + LLM]
  |- scoring_engine           Scoring consequences (1-5, 0-100) & decisions
  |- report_builder           Rapport de synthese Markdown (exercice / decision)
  |- (v2) whatif_engine       Injection d'hypotheses + re-simulation temps reel
        |
Services : LLM via OpenCode (defaut) ou API compatible OpenAI . Zep Cloud (graphe memoire)
```

---

## Modules & sujets de travail / Modules & work topics

| Module | Statut / Status | Description (FR / EN) |
|---|---|---|
| Squelette (Flask + Vue3 + tâches async) | Réutilisé / Reused | Base technique / Technical base |
| Client LLM, logs, retry, parsing fichiers | Réutilisé / Reused | Utilitaires / Utilities |
| `risk_repository` + référentiel | **Intégré / Integrated** | 64 scénarios, 9 familles, matrice de scoring / 64 scenarios, 9 families, scoring matrix |
| `crisis_graph_extractor` | Intégré / Integrated | Scénario NL → graphe de crise / NL scenario → crisis graph |
| Graphe d'interdépendances (Zep) | Adapté / Adapted | Actifs, domaines, dépendances pondérées / Assets, domains, weighted dependencies |
| `expert_society` | **Intégré / Integrated** | Agents des 9 familles (parallèle, spécialisation LLM) / 9-family expert agents |
| `domino_engine` | **Intégré / Integrated** | Propagation hybride (déterministe + narration LLM) / Hybrid propagation |
| `trajectory_generator` | **Intégré / Integrated** | 4 trajectoires (hybride paramétrique + narratif LLM) / 4 trajectories |
| `scoring_engine` | **Intégré / Integrated** | Scoring conséquences (domaine 1-5, indice 0-100) + décisions / Consequence + decision scoring |
| `report_builder` | **Intégré / Integrated** | Rapport de synthèse Markdown (contexte, analyses, chaînes, trajectoires, décisions) / Markdown synthesis report |
| Parcours & historique (frontend) | **Intégré / Integrated** | Fil d'Ariane, reprise, aperçu imprimable / Stepper, resume, printable preview |
| Navigation & métriques | **Intégré / Integrated** | Onglets, navigateur de simulations (renommer/rouvrir), tokens & durée par étape / Tabs, simulations browser, per-step tokens & duration |
| Visualisation D3 (causes/conséquences) | Réutilisé / Reused | Graphe de propagation temps réel / Real-time propagation graph |
| `whatif_engine` | v2 (après POC / after POC) | Hypothèses & effets instantanés / Hypotheses & instant effects |

---

## Feuille de route / Roadmap

- **Phase 0** — Fork, nettoyage (retrait OASIS), renommage, configuration
  *(Fork, cleanup (remove OASIS), renaming, configuration)* ✅
- **Phase 1** — Intake scénario + extraction et visualisation du graphe de crise
  *(Scenario intake + crisis-graph extraction and visualization)* ✅
- **Phase 2** — Société d'agents experts + moteur d'effets domino
  *(Expert-agent society + domino-effect engine)* ✅
- **Phase 3** — Génération des 4 trajectoires + scoring
  *(Generation of the 4 trajectories + scoring)* ✅
- **Phase 4** — Frontend simulation temps réel + trajectoires côte à côte
  *(Real-time simulation frontend + side-by-side trajectories)* ✅
  — parcours unifié (fil d'Ariane), historique & reprise, rapport de synthèse
  exportable, tableau de décisions consolidées, nettoyage du legacy.
- **v2** — What-if temps réel, replay, déploiement on-premise souverain
  *(Real-time What-if, replay, sovereign on-premise deployment)*

---

## Référentiel de risques / Risk referential

**FR —** DISCOVER intègre un **référentiel de risques socle** (`backend/app/data/risk_referentiel.json`,
reconstruit en CSV dans `data/referentiel_risques.csv`) organisé en :

- **8 catégories d'aléa** : Accident, Aléa naturel, Invasion, Médico-sanitaire, Mouvement social,
  Pénurie, Socio-culturel/politique/écologique, Terrorisme/malveillance.
- **64 scénarios** de crise (8 par catégorie), avec description et points sensibles (tags).
- **9 familles de risque** (domaines d'impact transversaux) = les domaines d'experts de DISCOVER :
  opérationnel, technique, RH, juridique, finance, communication, géopolitique, cybersécurité,
  **résilience** (cette dernière pilotant le moteur d'effets domino).
- **Scoring** : matrice Probabilité × Gravité → Criticité (qualitatif + numérique 1-5).

Le référentiel alimente l'**intake assisté** (sélection catégorie → scénario), le **contexte
d'extraction** du graphe de crise et l'**amorçage du scoring**. Régénération :
`python backend/scripts/build_referentiel.py`.

**EN —** DISCOVER ships a **baseline risk referential** (8 hazard categories, 64 crisis scenarios,
9 risk families = the expert domains, and a probability×gravity→criticality scoring matrix). It
powers assisted intake, crisis-graph extraction context and scoring seeding.

---

## Simulation de crise / Crisis simulation

**FR —** Une fois le graphe de crise extrait (Phase 1), DISCOVER simule la crise :

1. **Société d'agents experts** (`expert_society`) : un agent par domaine d'impact
   pertinent (parmi les 9 familles, `resilience` toujours actif) analyse la crise
   **en parallèle** via le harness OpenCode, en spécialisant les impacts/mesures
   génériques du référentiel au scénario réel. Sortie : impacts, sévérité (1-5),
   nœuds affectés, **propagations inter-domaines**, mesures.
2. **Moteur d'effets domino** (`domino_engine`) : propagation **déterministe** sur
   le graphe (poids d'arêtes × criticité, amplifiée par la famille `resilience`
   sur les chaînes multi-domaines), puis **narration/qualification LLM** des
   chaînes significatives. Sortie : graphe propagé (impact par nœud) + chaînes
   de propagation narrées.

API : `POST /api/simulation/run` (async + polling), `GET /api/simulation/<id>`.
Frontend : bouton « Lancer la simulation » → vue temps réel (graphe avec
surimpression d'impact + analyses par domaine + chaînes de propagation).

**EN —** After crisis-graph extraction, DISCOVER runs a **society of expert agents**
(one per relevant impact family, in parallel via OpenCode) then a **hybrid
domino-effect engine** (deterministic propagation + LLM narration) producing an
impacted graph and narrated propagation chains.

---

## Trajectoires & scoring / Trajectories & scoring

**FR —** À partir d'une simulation, DISCOVER génère **4 trajectoires** plausibles
(`optimiste, intermédiaire, critique, rupture`) par approche **hybride** :

1. `trajectory_generator` module des paramètres déterministes par branche (sévérité,
   mitigation, propagation, saturation `resilience`) et **rejoue le moteur domino**,
   puis produit les 4 **narratifs + bascules clés** en un seul appel LLM.
2. `scoring_engine` calcule, par trajectoire, un **scoring de conséquences**
   (criticité par domaine 1-5 + **indice global 0-100**) et un **scoring de décisions**
   (mesures classées par effet estimé) pour aider à la priorisation.

API : `POST /api/simulation/<id>/trajectories` (async), `GET …/trajectories`.
Frontend : bouton « Trajectoires & scoring » → vue comparant les **4 branches côte
à côte** + **heatmap domaine × trajectoire** + décisions prioritaires.

**EN —** From a simulation, DISCOVER generates **4 plausible trajectories** via a
hybrid approach (deterministic parameter variation + domino re-run + single LLM call
for narratives), each scored on consequences (per-domain 1-5, global 0-100) and
decisions (measures ranked by estimated effect).

---

## Navigation & métriques / Navigation & metrics

**FR —** Une simulation terminée est **entièrement navigable par onglets**
(**Graphe · Simulation · Trajectoires · Rapport**) dans les deux sens, y compris
le retour au graphe de crise. Toutes les simulations sont **persistées** et
gérées depuis un **navigateur** (`/simulations`, lien « Mes simulations ») :
titre **renommable**, statut, indice max, durée, tokens, avec rouvrir / renommer
/ supprimer.

La **consommation LLM est mesurée étape par étape** et affichée à chaque niveau :
- **Intake / Graphe** : extraction du graphe (durée, tokens, coût) ;
- **Simulation** : analyse experts, propagation, narration ;
- **Trajectoires** : génération des 4 trajectoires.

Chaque appel LLM (via OpenCode) fournit `tokens`, `cost` et le **modèle**
(`providerID/modelID`) ; le pipeline attribue la consommation par étape (snapshot
avant/après) et la stocke dans `Scenario.metrics` / `Simulation.metrics`. Le
**modèle utilisé** est affiché dans le panneau Métriques (les 3 vues), le
navigateur `/simulations` et la section « Métriques » du rapport exporté.

**EN —** A completed simulation is fully **tab-navigable** (Graph · Simulation ·
Trajectories · Report), including back to the crisis graph. All simulations are
persisted and managed from a **browser** (`/simulations`) with rename / reopen /
delete. **Per-step LLM consumption** (tokens, duration, cost) is captured and
shown at each stage (extraction, simulation, trajectories) and included in the
exported report.

---

## Trace d'exécution / Execution trace

**FR —** Pour comprendre **quels fichiers et fonctions du backend sont réellement
sollicités** lors d'une action, DISCOVER embarque un **traceur d'exécution** optionnel
(`backend/app/utils/exec_tracer.py`). Basé sur `sys.setprofile` + `threading.setprofile`
(compatible avec les tâches asynchrones), il est **filtré sur le package `app/`**,
**désactivé par défaut** (aucun surcoût) et écrit dans un fichier dédié
`backend/logs/trace-AAAA-MM-JJ.log`, séparé des logs applicatifs.

Il produit trois niveaux d'information :

1. **Arbre d'appels chronologique** par scope (requête HTTP *et* tâche de fond),
   ex. `→ services/expert_society.py:analyze:231`.
2. **Récapitulatif par scope** : liste **dédupliquée** des fichiers utilisés + nombre
   d'appels (`--- Fichiers utilisés — simulation:sim_xxx (N fichiers, M appels) ---`).
3. **Récapitulatif global** de session : inventaire dédupliqué de tous les fichiers
   `app/` sollicités, disponible **à la demande** via `GET /api/trace/summary` (JSON) et
   **à l'arrêt** du backend.

Activation dans `.env` :

```bash
TRACE_EXECUTION=true          # active la trace (défaut : false)
TRACE_INCLUDE_RETURNS=false   # inclure les retours (←) + durée par fonction
TRACE_MAX_DEPTH=0             # profondeur max d'appels (0 = illimité)
TRACE_SUMMARY=true            # écrire les récapitulatifs dédupliqués
TRACE_SUMMARY_MIN_FILES=1     # seuil anti-bruit des récaps de scope
```

**EN —** DISCOVER ships an optional **execution tracer** (`backend/app/utils/exec_tracer.py`)
to understand **which backend files/functions are actually exercised** per action. Built on
`sys.setprofile` + `threading.setprofile` (async-safe), filtered to the `app/` package,
**disabled by default** and written to a dedicated `backend/logs/trace-*.log`. It provides a
chronological call tree, a **per-scope deduplicated file summary** (with call counts, for HTTP
requests and background tasks), and a **global session summary** available on demand via
`GET /api/trace/summary` and at shutdown. Configured through the `TRACE_*` variables above
(see `.env.example`).

---

## Stack technique / Tech stack

- **Backend** : Python 3.11+, Flask
- **Frontend** : Vue 3 (Composition API), Vite, Vue Router, D3.js, Axios
- **LLM** : via le harness **OpenCode** (défaut) — l'auth et le modèle sont gérés par
  OpenCode ; repli optionnel sur une API compatible OpenAI (`LLM_BACKEND=openai`).
- **Communication** : REST + polling incrémental / REST + incremental polling

---

## Identité visuelle / Visual identity

**FR —** DISCOVER adopte un **thème clair** et un logo **papillon** (aile cyan / aile
orange) symbolisant la bascule des trajectoires et les effets domino. Le design
repose sur un système de **design tokens** CSS (`frontend/src/styles/theme.css`,
variables `:root`) et une **palette JavaScript centralisée** pour D3
(`frontend/src/styles/palette.js`) :

- **Marque** : cyan `#00B8D4` (accent UI : boutons, onglets, focus) ·
  orange `#F85810` (sémantique de danger : halo d'impact, arête active, gravité max).
- **Surfaces claires** : fond `#FBFBFB`, cartes `#FFFFFF`, bordures `#E3E7EC`.
- **Logo** : `frontend/src/assets/logo/butterfly.png` (fond transparent), décliné en
  favicons (`frontend/public/favicon-*.png`). Composant partagé
  `frontend/src/components/AppBrand.vue`.
- **Écran de chargement de marque** : `frontend/src/components/LoadingScreen.vue` — logo
  papillon centré, anneau cyan tournant et libellé d'étape, affiché pendant les attentes
  longues (extraction du graphe ~1 min, simulation jusqu'à ~2 min, trajectoires ~30 s).
  Seuil anti-flash de 300 ms (invisible sur les chargements rapides), en-tête laissé
  accessible, respect de `prefers-reduced-motion` et masquage à l'impression.

Le thème est centralisé : un mode sombre pourra être ajouté en surchargeant les
variables `:root` sans toucher aux composants.

**EN —** DISCOVER uses a **light theme** and a **butterfly** logo (cyan / orange wings)
evoking trajectory branching and domino effects. Styling relies on CSS **design
tokens** (`theme.css`, `:root` variables) and a centralized **JS palette**
(`palette.js`) for D3. Brand cyan `#00B8D4` drives the UI accent; brand orange
`#F85810` carries danger semantics. A branded **loading screen**
(`LoadingScreen.vue` — centered butterfly, spinning cyan ring, step label, 300 ms
anti-flash threshold, reduced-motion aware) covers long waits (extraction, simulation,
trajectories) while keeping the header accessible. The theme is centralized, making a
future dark mode a matter of overriding `:root`.

---

## LLM via OpenCode / LLM through OpenCode

**FR —** Par défaut (`LLM_BACKEND=opencode`), DISCOVER délègue tous les appels LLM au
harness [OpenCode](https://opencode.ai). Aucune clé LLM n'est stockée dans DISCOVER :
l'authentification et le choix du modèle sont gérés par OpenCode.

```bash
# 1. Installer OpenCode puis configurer un fournisseur/modèle
opencode auth login

# 2. DISCOVER lance et gère automatiquement 'opencode serve' (OPENCODE_MANAGED=true).
#    Pour utiliser un serveur déjà lancé : renseigner OPENCODE_SERVER_URL et OPENCODE_MANAGED=false.
```

**EN —** By default (`LLM_BACKEND=opencode`), DISCOVER delegates all LLM calls to the
[OpenCode](https://opencode.ai) harness. No LLM key is stored in DISCOVER: authentication
and model selection are handled by OpenCode. DISCOVER auto-starts and manages
`opencode serve`; set `OPENCODE_SERVER_URL` + `OPENCODE_MANAGED=false` to use an external server.

Les variables (`OPENCODE_*`, `LLM_BACKEND`) sont documentées dans `.env.example`.

---

## Cas d'usage / Use cases

- **FR** — Exercices de gestion de crise (secteur santé, collectivités, OIV…) · Aide à la
  décision en cellule de crise temps réel · Anticipation d'effets domino cyber-physiques ·
  Renforcement de la résilience organisationnelle.
- **EN** — Crisis-management exercises (healthcare, local authorities, critical operators…) ·
  Real-time decision support in crisis units · Anticipation of cyber-physical domino effects ·
  Strengthening organizational resilience.

---

## Licence / License

AGPL-3.0 (héritée de MiroFish / inherited from MiroFish). Voir / see `LICENSE`.

## Remerciements / Acknowledgments

**FR —** Basé sur [MiroFish](https://github.com/666ghj/MiroFish) (666ghj / Shanda Group) et son
écosystème. Moteur de simulation sociale d'origine : OASIS (CAMEL-AI).

**EN —** Based on [MiroFish](https://github.com/666ghj/MiroFish) (666ghj / Shanda Group) and its
ecosystem. Original social-simulation engine: OASIS (CAMEL-AI).
