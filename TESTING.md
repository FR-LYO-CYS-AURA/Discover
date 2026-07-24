# TESTING — DISCOVER

Guide de test manuel de DISCOVER + scénario de démonstration prêt à l'emploi.

---

## 1. Prérequis (une fois)

- **Node.js ≥ 18** et **npm**
- **Python 3.11–3.12** et **uv**
- **OpenCode installé et authentifié** (fournit le LLM) :
  ```bash
  opencode auth login      # choisir un provider (ex. github-copilot)
  ```

## 2. Configuration (une fois)

```bash
cd Discover
cp .env.example .env
```

Le `.env` par défaut suffit : `LLM_BACKEND=opencode`, `OPENCODE_MANAGED=true`.
**Aucune clé LLM ni Zep n'est requise** pour le parcours actuel
(intake → graphe → simulation → trajectoires → rapport).

## 3. Installation des dépendances (une fois)

```bash
npm run setup:all
```
(= `npm install` racine + `frontend/npm install` + `backend/uv sync`)

## 4. Démarrage

```bash
npm run dev
```

Lance en parallèle :

- Backend Flask → `http://localhost:5001`
- Frontend Vite → `http://localhost:3000` (s'ouvre automatiquement)
- Le backend lance/gère aussi **`opencode serve`** sur `127.0.0.1:47600`.

Démarrage séparé (utile au debug) :

```bash
npm run backend     # terminal 1 → :5001 (+ opencode serve)
npm run frontend    # terminal 2 → :3000
```

### Vérifier que les services répondent

```bash
curl http://localhost:5001/health                 # {"status":"ok","service":"DISCOVER Backend"}
curl http://127.0.0.1:47600/global/health          # {"healthy":true,...}
curl http://localhost:5001/api/referentiel/meta    # {categories:8, scenarios:64, families:9}
```

Si les trois répondent, l'application est prête.

---

## 5. Parcours de test dans l'UI (http://localhost:3000)

### Étape 1 — Intake
- (Optionnel) « Partir d'un scénario du référentiel » : choisir une **catégorie**
  → un **scénario** → **Charger** (pré-remplit titre + description).
- Ou saisir librement une description de crise.
- Cliquer **« Générer le graphe de crise »**.
- ⏱️ ~30-60 s (appel LLM) → redirection vers la vue graphe.

### Étape 2 — Graphe de crise
- Graphe **D3** interactif : nœuds colorés par domaine, taille = criticité,
  flèches = interdépendances.
- Tester : zoom / glisser, clic sur un nœud ou une arête → panneau de détail.
- Boutons : **Ré-extraire**, **Lancer la simulation**. Fil d'Ariane en haut.

### Étape 3 — Simulation
- Cliquer **« Lancer la simulation »**. Statuts : *Analyse experts → Propagation
  → Qualification → Terminée* (~1-2 min).
- Attendu : **analyses par domaine**, **chaînes de propagation narrées**, graphe
  avec **halo d'impact** rouge, et un **panneau Métriques** (durée + tokens par
  étape : analyse experts / propagation / narration).
- **Onglets** en haut (Graphe · Simulation · Trajectoires · Rapport) pour naviguer.
- Bouton **« Trajectoires & scoring → »**.

### Étape 4 — Trajectoires & scoring
- Cliquer **« Générer les trajectoires »** (~1 min).
- Attendu : **heatmap** domaine × trajectoire, **4 branches côte à côte**
  (optimiste / intermédiaire / critique / rupture) avec **indice global 0-100**
  croissant, narratifs, bascules clés, décisions ; **tableau de décisions
  consolidées** en haut.
- Bouton **« Rapport »**.

### Étape 5 — Rapport
- Aperçu imprimable (contexte → analyses → chaînes → trajectoires → décisions).
- Tester **« Télécharger .md »** et **« Imprimer / PDF »** (Ctrl+P navigateur).

### Historique & reprise
- Revenir à l'accueil (fil d'Ariane → *Intake*). Dans **« Scénarios récents »**,
  déplier **Simulations** d'un scénario → **reprendre** *Simulation* ou
  *Trajectoires*.
- Lien **« Mes simulations → »** (en haut de l'accueil) : navigateur listant
  toutes les simulations (titre, scénario, statut, indice max, durée, tokens)
  avec **rouvrir / renommer (✎) / supprimer**, et accès direct Trajectoires/Rapport.

---

## 6. Test API seul (sans UI, optionnel)

```bash
# 1) Créer un scénario (extraction du graphe)
curl -s -X POST http://localhost:5001/api/scenario/create \
  -H 'Content-Type: application/json' \
  -d '{"title":"Cyber G7","description":"Rançongiciel paralysant plusieurs hôpitaux pendant le G7."}'
# -> récupérer scenario_id

# 2) Lancer la simulation
curl -s -X POST http://localhost:5001/api/simulation/run \
  -H 'Content-Type: application/json' -d '{"scenario_id":"scn_xxx"}'
# -> récupérer simulation_id ; suivre GET /api/simulation/<id>/status jusqu'à "completed"

# 3) Générer les trajectoires
curl -s -X POST http://localhost:5001/api/simulation/<id>/trajectories
# suivre le task via POST /api/simulation/run/status {"task_id":"..."}
curl -s http://localhost:5001/api/simulation/<id>/trajectories

# 4) Rapport
curl -s http://localhost:5001/api/simulation/<id>/report/download -o rapport.md
```

---

## 7. Scénario de démonstration — Cyberattaque hôpitaux, G7 Évian

### Paramétrage
- **Référentiel** : Catégorie *Terrorisme ou malveillance* → Scénario
  *Cyberattaque* → **Charger**.
- **Titre** :
  ```
  Cyberattaque hôpitaux — G7 Évian 12/06/2026
  ```

### Description (champ principal, à coller tel quel)

```
Le 12 juin 2026, pendant le sommet du G7 à Évian-les-Bains (Haute-Savoie), une
attaque par rançongiciel (double extorsion) frappe simultanément les Hôpitaux du
Léman (Thonon–Évian) et le Centre Hospitalier Annemasse-Bonneville, désignés
comme établissements de recours sanitaire du sommet. À 04h10, le système
d'information hospitalier (SIH) et le dossier patient informatisé (DPI) sont
chiffrés, la PACS d'imagerie et le laboratoire de biologie médicale deviennent
inaccessibles, la messagerie et la téléphonie sur IP tombent. Les sauvegardes
récentes sont partiellement chiffrées. Le groupe attaquant menace de publier des
données de santé, dont celles de personnalités des délégations du G7.

Les blocs opératoires basculent en mode dégradé papier, les urgences sont
saturées et des transferts vers Annecy et Genève sont envisagés. La cellule de
crise sanitaire est activée avec l'ARS Auvergne-Rhône-Alpes, la préfecture de
Haute-Savoie, le SAMU/SDIS 74, l'ANSSI et le CERT Santé. Le prestataire
d'hébergement du SIH et l'opérateur télécom sont mobilisés. La pression
médiatique est maximale (presse nationale et internationale présente pour le
G7), avec un risque de rumeurs et de désinformation. Des obligations
réglementaires s'appliquent (notification CNIL/RGPD sous 72h, signalement
incident, cadre NIS2/OIV). Le contexte diplomatique impose une coordination
avec la sécurité du sommet et une priorisation nationale des moyens.
```

### Contexte additionnel (champ optionnel)

```
Site sensible (sommet G7, délégations étrangères, VIP). Établissements de
recours désignés. Contraintes : continuité des soins vitaux, protection des
données de santé, souveraineté et image de l'État hôte, coordination
inter-services renforcée, fenêtre médiatique internationale.
```

### Ce que le scénario exerce (les 9 familles)

| Domaine | Éléments injectés |
|---|---|
| cybersécurité | rançongiciel, SIH/DPI chiffrés, PACS, sauvegardes compromises |
| technique | téléphonie/messagerie IP, hébergeur, opérateur télécom |
| santé (secteur) | blocs, urgences, labo, transferts Annecy/Genève |
| rh | bascule mode papier, surcharge, stress équipes |
| juridique | RGPD/CNIL 72h, NIS2/OIV, exfiltration de données |
| finance | rançon, pertes d'exploitation, remise en état |
| communication | presse internationale, rumeurs, données VIP |
| géopolitique | préfecture, ARS, ANSSI, sécurité du sommet, priorisation nationale |
| résilience | domino SI → soins → RH → image → régulateur, sauvegardes HS |

### Checklist de validation

1. **Graphe** : ~15-22 nœuds, plusieurs domaines, nœuds vitaux (SIH, blocs,
   urgences) en criticité 4-5.
2. **Simulation** : 9 agents actifs (dont `resilience`) ; ≥2 chaînes domino
   narrées (ex. `SIH → PACS/labo → blocs/urgences → transferts → image/ARS`).
3. **Trajectoires** : indices globaux **croissants**
   optimiste < intermédiaire < critique < rupture (rupture ≈ 90+).
4. **Décisions consolidées** : mitigation (isolement/segmentation, mode dégradé,
   restauration, cellule) devant prévention ; effets élevés sur cyber/santé.
5. **Rapport** : les 6 sections présentes ; export `.md` + impression PDF OK.

### Variantes

- **Court** : « Rançongiciel paralyse le SIH des hôpitaux du Léman pendant le G7
  d'Évian ; blocs et dossiers patients inaccessibles. » (extraction minimale).
- **Aggravé** : ajouter « coupure électrique concomitante sur le site » → doit
  renforcer la famille `resilience` (domino multi-réseaux).
- **Comparaison** : lancer 2 simulations sur le même scénario et comparer via
  l'historique (reprise).

---

## 8. Dépannage

| Symptôme | Cause probable / solution |
|---|---|
| 503 « Backend LLM indisponible » | OpenCode non prêt : vérifier `curl 127.0.0.1:47600/global/health` ; sinon lancer `opencode serve --port 47600` et mettre `OPENCODE_MANAGED=false` |
| Erreur config LLM au démarrage | `opencode auth login` non fait, ou binaire introuvable → renseigner `OPENCODE_BIN` dans `.env` |
| Extraction/simulation lente | Normal (appels LLM) ; des descriptions concises accélèrent |
| Port occupé (5001 / 3000 / 47600) | Libérer le port ou ajuster `FLASK_PORT` / port Vite / `OPENCODE_SERVER_URL` |
| Frontend blanc | Vérifier la console navigateur ; confirmer que le backend répond sur 5001 |
