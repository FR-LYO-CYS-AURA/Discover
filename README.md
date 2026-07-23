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
  |- crisis_graph_extractor   Extraction actifs / domaines / interdependances (LLM)
  |- graph_builder (Zep)      Graphe d'interdependances (GraphRAG)
  |- expert_society           Societe d'agents experts par domaine
  |- domino_engine            Propagation des effets sur le graphe
  |- trajectory_generator     4 trajectoires (optimiste -> rupture)
  |- scoring_engine           Scoring consequences & decisions
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
| `crisis_graph_extractor` | À développer / To build | Scénario NL → graphe de crise / NL scenario → crisis graph |
| Graphe d'interdépendances (Zep) | Adapté / Adapted | Actifs, domaines, dépendances pondérées / Assets, domains, weighted dependencies |
| `expert_society` | À développer / To build | Agents cyber/santé/RH/juridique/finance/comm/ops/logistique |
| `domino_engine` | À développer / To build | Propagation des effets domino / Domino-effect propagation |
| `trajectory_generator` | À développer / To build | 4 trajectoires plausibles / 4 plausible trajectories |
| `scoring_engine` | À développer / To build | Scoring par domaine + agrégé / Per-domain + aggregate scoring |
| Visualisation D3 (causes/conséquences) | Réutilisé / Reused | Graphe de propagation temps réel / Real-time propagation graph |
| `whatif_engine` | v2 (après POC / after POC) | Hypothèses & effets instantanés / Hypotheses & instant effects |

---

## Feuille de route / Roadmap

- **Phase 0** — Fork, nettoyage (retrait OASIS), renommage, configuration
  *(Fork, cleanup (remove OASIS), renaming, configuration)*
- **Phase 1** — Intake scénario + extraction et visualisation du graphe de crise
  *(Scenario intake + crisis-graph extraction and visualization)*
- **Phase 2** — Société d'agents experts + moteur d'effets domino
  *(Expert-agent society + domino-effect engine)*
- **Phase 3** — Génération des 4 trajectoires + scoring
  *(Generation of the 4 trajectories + scoring)*
- **Phase 4** — Frontend simulation temps réel + trajectoires côte à côte
  *(Real-time simulation frontend + side-by-side trajectories)*
- **v2** — What-if temps réel, replay, déploiement on-premise souverain
  *(Real-time What-if, replay, sovereign on-premise deployment)*

---

## Stack technique / Tech stack

- **Backend** : Python 3.11+, Flask, Zep Cloud
- **Frontend** : Vue 3 (Composition API), Vite, Vue Router, D3.js, Axios
- **LLM** : via le harness **OpenCode** (défaut) — l'auth et le modèle sont gérés par
  OpenCode ; repli optionnel sur une API compatible OpenAI (`LLM_BACKEND=openai`).
- **Communication** : REST + polling incrémental / REST + incremental polling

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
