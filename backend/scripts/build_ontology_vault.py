"""
Générateur du vault Obsidian de l'ontologie DISCOVER.

Construit `data/onto/`, un vault Obsidian autonome présentant le référentiel
de risques comme un graphe de connaissance navigable.

POURQUOI NE PAS REPRENDRE LES 1152 LIGNES DU CSV
------------------------------------------------
`data/referentiel_risques.csv` est un PRODUIT CARTÉSIEN généré : 64 types
d'aléa x 18 intitulés de risque = 1152 lignes. Chaque aléa y est croisé avec
*tous* les risques : ces lignes ne portent donc aucune sélectivité. Une note
par ligne produirait 1152 noeuds et ~2300 arêtes toutes identiques, soit un
graphe illisible et sémantiquement vide.

On modélise donc l'ontologie réelle (~108 notes) et on ÉNONCE la règle de
croisement (note « Matrice aléa × famille ») au lieu de la matérialiser.

LE PONT ENTRE LES DEUX TAXONOMIES
---------------------------------
Les hiérarchies seules (Catégorie->Aléa, Famille->Risque) donneraient 17
étoiles déconnectées. Le lien sémantique réel est le SCORING :
  - la Probabilité est portée par l'aléa ;
  - la Gravité est portée par la famille ;
  - Criticité = f(Probabilité x Gravité) via la matrice du référentiel.
C'est ce qui fait du tout un véritable graphe de connaissance.

SOURCE
------
Lit `backend/app/data/risk_referentiel.json`, source normalisée dont le CSV
est lui-même dérivé (identifiants stables, tags en tableaux, probabilité par
aléa, matrice de scoring).

Usage : python backend/scripts/build_ontology_vault.py
Génération idempotente : relancer reconstruit le vault à l'identique.
"""

import json
import os
import re
import shutil

# --------------------------------------------------------------------------- #
# Chemins
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SOURCE = os.path.join(ROOT, 'backend', 'app', 'data', 'risk_referentiel.json')
VAULT = os.path.join(ROOT, 'data', 'onto')

DIR_CAT = 'Catégories'
DIR_ALEA = 'Aléas'
DIR_FAM = 'Familles'
DIR_RISK = 'Risques'
DIR_SCORE = 'Scoring'

# Caractères interdits dans un nom de fichier Obsidian. Le « / » est le plus
# piégeux : Obsidian y verrait une arborescence de dossiers.
FORBIDDEN = r'[\\/:*?"<>|#^\[\]]'


def safe_title(label: str) -> str:
    """Titre de note sûr. Le libellé exact est conservé en frontmatter et en H1."""
    return re.sub(r'\s+', ' ', re.sub(FORBIDDEN, '–', label)).strip()


def yaml_escape(value: str) -> str:
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def frontmatter(props: dict) -> str:
    lines = ['---']
    for key, val in props.items():
        if val is None or val == '':
            continue
        if isinstance(val, list):
            if not val:
                continue
            lines.append(f'{key}:')
            lines.extend(f'  - {yaml_escape(v)}' for v in val)
        else:
            lines.append(f'{key}: {yaml_escape(val)}')
    lines.append('---')
    return '\n'.join(lines)


def write_note(relative_dir: str, title: str, body: str) -> str:
    directory = os.path.join(VAULT, relative_dir) if relative_dir else VAULT
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f'{title}.md')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(body.rstrip() + '\n')
    return path


def tag_slug(tag: str) -> str:
    """Tag Obsidian valide : pas d'espace, pas de caractère de syntaxe."""
    slug = re.sub(r'\s+', '-', tag.strip())
    slug = re.sub(r'[^\w\-/àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ’\']', '', slug, flags=re.UNICODE)
    return slug.replace('’', '').replace("'", '')


# --------------------------------------------------------------------------- #
# Génération
# --------------------------------------------------------------------------- #
def build():
    with open(SOURCE, 'r', encoding='utf-8') as fh:
        ref = json.load(fh)

    categories = ref['categories']
    scenarios = ref['scenarios']
    families = ref['families']
    scoring = ref['scoring']

    # Repartir d'un vault propre (sauf .obsidian, régénéré plus bas).
    if os.path.isdir(VAULT):
        for entry in os.listdir(VAULT):
            full = os.path.join(VAULT, entry)
            shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)
    os.makedirs(VAULT, exist_ok=True)

    cat_title = {c['id']: safe_title(c['label']) for c in categories}
    fam_title = {f['domain']: safe_title(f['label']) for f in families}

    # --- Valeurs de scoring effectivement présentes ---
    probs = sorted({s['base_probability'] for s in scenarios})
    gravs = sorted({f['gravite'] for f in families})
    prob_title = {p: safe_title(f'Probabilité {p}') for p in probs}
    grav_title = {g: safe_title(f'Gravité {g}') for g in gravs}

    def criticite(prob: str, grav: str) -> str:
        score = scoring['prob_value'][prob] * scoring['grav_value'][grav]
        return 'Moyenne' if score <= 12 else ('Élevée' if score <= 20 else 'Critique')

    crits = sorted({criticite(p, g) for p in probs for g in gravs})
    crit_title = {c: safe_title(f'Criticité {c}') for c in crits}

    counts = {'notes': 0, 'links': 0}

    def note(directory, title, body):
        write_note(directory, title, body)
        counts['notes'] += 1
        counts['links'] += len(re.findall(r'\[\[', body))

    # ----------------------------------------------------------------- #
    # Catégories d'aléa (8)
    # ----------------------------------------------------------------- #
    for cat in categories:
        members = [s for s in scenarios if s['category_id'] == cat['id']]
        body = '\n'.join([
            frontmatter({
                'type': 'Catégorie d’aléa',
                'label': cat['label'],
                'id': cat['id'],
                'nombre_aléas': str(len(members)),
            }),
            '',
            f"# {cat['label']}",
            '',
            f"**Catégorie d'aléa** regroupant {len(members)} types d'aléa.",
            '',
            "## Aléas de cette catégorie",
            '',
            *[f"- [[{safe_title(s['type'])}]] — {s['description']}" for s in members],
            '',
            '---',
            '',
            "> [!info] Place dans l'ontologie",
            "> `Catégorie d'aléa` → `Type d'aléa` → (croisement) → `Famille de risque` → `Risque`",
            '',
            f"Voir [[Ontologie]] · [[Matrice aléa × famille]]",
        ])
        note(DIR_CAT, cat_title[cat['id']], body)

    # ----------------------------------------------------------------- #
    # Types d'aléa (64)
    # ----------------------------------------------------------------- #
    for sc in scenarios:
        tags = [tag_slug(t) for t in sc.get('tags') or []]
        tag_line = ' '.join(f'#{t}' for t in tags if t)
        body = '\n'.join([
            frontmatter({
                'type': 'Type d’aléa',
                'label': sc['type'],
                'id': sc['id'],
                'catégorie': sc['category_label'],
                'probabilité': sc['base_probability'],
                'tags': sc.get('tags') or [],
            }),
            '',
            f"# {sc['type']}",
            '',
            f"> {sc['description']}",
            '',
            f"**Catégorie** : [[{cat_title[sc['category_id']]}]]",
            f"**Probabilité de base** : [[{prob_title[sc['base_probability']]}]]",
            '',
            "## Points sensibles",
            '',
            tag_line if tag_line else '_Aucun tag._',
            '',
            '---',
            '',
            "> [!note] Déclinaison en risques",
            "> Cet aléa se décline dans les **9 familles de risque** du référentiel.",
            "> Voir [[Matrice aléa × famille]].",
        ])
        note(DIR_ALEA, safe_title(sc['type']), body)

    # ----------------------------------------------------------------- #
    # Familles de risque (9)
    # ----------------------------------------------------------------- #
    for fam in families:
        body = '\n'.join([
            frontmatter({
                'type': 'Famille de risque',
                'label': fam['label'],
                'domaine_applicatif': fam['domain'],
                'gravité': fam['gravite'],
                'impacts': fam['impacts'],
                'prévention': fam['prevention'],
                'mitigation': fam['mitigation'],
            }),
            '',
            f"# {fam['label']}",
            '',
            f"**Famille de risque** — domaine d'expert DISCOVER : `{fam['domain']}`",
            f"**Gravité de base** : [[{grav_title[fam['gravite']]}]]",
            '',
            '## Impacts potentiels',
            '',
            fam['impacts'],
            '',
            '## Mesures de prévention',
            '',
            fam['prevention'],
            '',
            '## Mesures de mitigation',
            '',
            fam['mitigation'],
            '',
            '## Risques de cette famille',
            '',
            *[f"- [[{safe_title(e)}]]" for e in fam['examples']],
            '',
            '---',
            '',
            f"Voir [[Ontologie]] · [[Matrice aléa × famille]]",
        ])
        note(DIR_FAM, fam_title[fam['domain']], body)

    # ----------------------------------------------------------------- #
    # Intitulés de risque (18)
    # ----------------------------------------------------------------- #
    for fam in families:
        for example in fam['examples']:
            body = '\n'.join([
                frontmatter({
                    'type': 'Risque',
                    'label': example,
                    'famille': fam['label'],
                    'domaine_applicatif': fam['domain'],
                    'gravité': fam['gravite'],
                }),
                '',
                f"# {example}",
                '',
                f"**Famille** : [[{fam_title[fam['domain']]}]]",
                f"**Gravité** : [[{grav_title[fam['gravite']]}]]",
                '',
                "## Impacts potentiels",
                '',
                fam['impacts'],
                '',
                '---',
                '',
                "> [!tip] Lecture",
                "> Ce risque peut survenir à la suite de **n'importe lequel des 64 aléas** "
                "du référentiel ; sa criticité dépend de la probabilité de l'aléa déclencheur.",
                '',
                f"Voir [[Matrice de criticité]]",
            ])
            note(DIR_RISK, safe_title(example), body)

    # ----------------------------------------------------------------- #
    # Scoring : probabilités, gravités, criticités, matrice
    # ----------------------------------------------------------------- #
    for prob in probs:
        holders = [s for s in scenarios if s['base_probability'] == prob]
        body = '\n'.join([
            frontmatter({'type': 'Valeur de scoring', 'dimension': 'Probabilité',
                         'valeur': prob, 'poids': str(scoring['prob_value'][prob])}),
            '',
            f"# Probabilité {prob}",
            '',
            f"Dimension **Probabilité** · poids `{scoring['prob_value'][prob]}` "
            f"dans la matrice de criticité.",
            '',
            f"Portée par **{len(holders)} aléa(s)** sur {len(scenarios)}.",
            '',
            '## Aléas concernés',
            '',
            *[f"- [[{safe_title(s['type'])}]]" for s in holders[:40]],
            ('' if len(holders) <= 40 else f"\n_… et {len(holders) - 40} autres._"),
            '',
            f"Voir [[Matrice de criticité]]",
        ])
        note(DIR_SCORE, prob_title[prob], body)

    for grav in gravs:
        holders = [f for f in families if f['gravite'] == grav]
        body = '\n'.join([
            frontmatter({'type': 'Valeur de scoring', 'dimension': 'Gravité',
                         'valeur': grav, 'poids': str(scoring['grav_value'][grav])}),
            '',
            f"# Gravité {grav}",
            '',
            f"Dimension **Gravité** · poids `{scoring['grav_value'][grav]}` "
            f"dans la matrice de criticité.",
            '',
            f"Portée par **{len(holders)} famille(s)** de risque sur {len(families)}.",
            '',
            '## Familles concernées',
            '',
            *[f"- [[{fam_title[f['domain']]}]]" for f in holders],
            '',
            f"Voir [[Matrice de criticité]]",
        ])
        note(DIR_SCORE, grav_title[grav], body)

    for crit in crits:
        combos = [(p, g) for p in probs for g in gravs if criticite(p, g) == crit]
        body = '\n'.join([
            frontmatter({'type': 'Valeur de scoring', 'dimension': 'Criticité', 'valeur': crit}),
            '',
            f"# Criticité {crit}",
            '',
            'Résultat du croisement **Probabilité × Gravité**.',
            '',
            '## Combinaisons donnant cette criticité',
            '',
            *[f"- [[{prob_title[p]}]] × [[{grav_title[g]}]] "
              f"= `{scoring['prob_value'][p] * scoring['grav_value'][g]}`" for p, g in combos],
            '',
            f"Voir [[Matrice de criticité]]",
        ])
        note(DIR_SCORE, crit_title[crit], body)

    # Matrice de criticité — le pont entre les deux taxonomies
    header = '| Probabilité \\ Gravité | ' + ' | '.join(gravs) + ' |'
    sep = '|---' * (len(gravs) + 1) + '|'
    rows = []
    for p in probs:
        cells = [f"**{criticite(p, g)}** ({scoring['prob_value'][p] * scoring['grav_value'][g]})"
                 for g in gravs]
        rows.append(f"| [[{prob_title[p]}]] | " + ' | '.join(cells) + ' |')
    body = '\n'.join([
        frontmatter({'type': 'Règle', 'label': 'Matrice de criticité'}),
        '',
        '# Matrice de criticité',
        '',
        "C'est **le pont sémantique de l'ontologie** : la probabilité est portée par "
        "l'**aléa**, la gravité par la **famille de risque**. Leur croisement donne la "
        "criticité. Sans cette relation, les deux taxonomies resteraient disjointes.",
        '',
        f"> `{scoring['matrix']}`",
        '',
        header, sep, *rows,
        '',
        '## Dimensions',
        '',
        '**Probabilité** (portée par l’aléa) : ' + ' · '.join(f'[[{prob_title[p]}]]' for p in probs),
        '',
        '**Gravité** (portée par la famille) : ' + ' · '.join(f'[[{grav_title[g]}]]' for g in gravs),
        '',
        '**Criticité** (résultat) : ' + ' · '.join(f'[[{crit_title[c]}]]' for c in crits),
        '',
        f"Voir [[Ontologie]]",
    ])
    note(DIR_SCORE, 'Matrice de criticité', body)

    # ----------------------------------------------------------------- #
    # Matrice aléa × famille — la règle, pas les 1152 lignes
    # ----------------------------------------------------------------- #
    body = '\n'.join([
        frontmatter({'type': 'Règle', 'label': 'Matrice aléa × famille',
                     'lignes_csv_équivalentes': str(ref['meta']['rows_equivalent'])}),
        '',
        '# Matrice aléa × famille',
        '',
        f"Le référentiel est **exhaustif par construction** : chacun des **{len(scenarios)} "
        f"types d'aléa** se décline dans chacune des **{len(families)} familles de risque**, "
        f"à raison de 2 intitulés par famille.",
        '',
        f"> {len(scenarios)} aléas × {len(families)} familles × 2 intitulés "
        f"= **{ref['meta']['rows_equivalent']} lignes** dans `data/referentiel_risques.csv`",
        '',
        "> [!warning] Pourquoi ces 1152 combinaisons ne sont pas des notes",
        "> Le croisement étant **complet**, il ne porte aucune information "
        "distinctive : tout aléa est associé à tous les risques. Les matérialiser "
        "donnerait 1152 notes et ~2300 liens strictement équivalents, noyant "
        "l'ontologie réelle. La règle est donc énoncée ici une fois pour toutes.",
        '',
        '## Les 8 catégories d’aléa',
        '',
        *[f"- [[{cat_title[c['id']]}]] ({c['scenario_count']} aléas)" for c in categories],
        '',
        '## Les 9 familles de risque',
        '',
        *[f"- [[{fam_title[f['domain']]}]] — `{f['domain']}`" for f in families],
        '',
        '---',
        '',
        "La **criticité** de chaque combinaison se calcule via [[Matrice de criticité]].",
    ])
    note('', 'Matrice aléa × famille', body)

    # ----------------------------------------------------------------- #
    # Note d'accueil
    # ----------------------------------------------------------------- #
    body = '\n'.join([
        frontmatter({'type': 'Index', 'label': 'Ontologie DISCOVER'}),
        '',
        '# Ontologie du référentiel de risques',
        '',
        "Représentation en **graphe de connaissance** du référentiel de risques socle "
        "de DISCOVER (`data/referentiel_risques.csv`).",
        '',
        '## Classes',
        '',
        '| Classe | Nombre | Dossier | Porte |',
        '|---|---|---|---|',
        f"| Catégorie d’aléa | {len(categories)} | `{DIR_CAT}/` | — |",
        f"| Type d’aléa | {len(scenarios)} | `{DIR_ALEA}/` | description, tags, **probabilité** |",
        f"| Famille de risque | {len(families)} | `{DIR_FAM}/` | impacts, prévention, mitigation, **gravité** |",
        f"| Risque | {len(families) * 2} | `{DIR_RISK}/` | — |",
        f"| Valeur de scoring | {len(probs) + len(gravs) + len(crits)} | `{DIR_SCORE}/` | poids |",
        '',
        '## Relations',
        '',
        '```',
        'Catégorie d’aléa  ──comprend──▶  Type d’aléa',
        'Famille de risque ──comprend──▶  Risque',
        '',
        'Type d’aléa       ──probabilité──▶  ┐',
        '                                    ├──▶  Criticité',
        'Famille de risque ──gravité─────▶  ┘',
        '```',
        '',
        "Les deux taxonomies (aléas / risques) sont reliées par le **scoring** : "
        "voir [[Matrice de criticité]]. Le croisement exhaustif aléa × famille est "
        "décrit dans [[Matrice aléa × famille]].",
        '',
        '## Comment explorer',
        '',
        '1. **Vue graphe** (`Ctrl/Cmd + G`) — les couleurs par dossier sont préconfigurées.',
        '2. **Afficher les étiquettes** dans les options de la vue graphe pour faire '
        f'apparaître les tags transversaux entre aléas.',
        '3. **Canvas** `Ontologie — schéma.canvas` — disposition fixe, pour présenter.',
        '',
        '## Points d’entrée',
        '',
        '### Catégories d’aléa',
        '',
        *[f"- [[{cat_title[c['id']]}]]" for c in categories],
        '',
        '### Familles de risque',
        '',
        *[f"- [[{fam_title[f['domain']]}]]" for f in families],
        '',
        '---',
        '',
        "_Vault généré par `backend/scripts/build_ontology_vault.py` — ne pas éditer à la main._",
    ])
    note('', 'Ontologie', body)

    return {
        'counts': counts,
        'categories': categories, 'scenarios': scenarios, 'families': families,
        'cat_title': cat_title, 'fam_title': fam_title,
        'probs': probs, 'gravs': gravs, 'crits': crits,
        'prob_title': prob_title, 'grav_title': grav_title, 'crit_title': crit_title,
    }


# --------------------------------------------------------------------------- #
# Configuration de la vue graphe Obsidian
# --------------------------------------------------------------------------- #
def rgb_int(hex_color: str) -> int:
    """Obsidian stocke les couleurs de groupe en entier (r<<16 | g<<8 | b)."""
    h = hex_color.lstrip('#')
    return int(h[0:2], 16) << 16 | int(h[2:4], 16) << 8 | int(h[4:6], 16)


def build_graph_config():
    """Groupes de couleurs préconfigurés : le graphe est présentable à l'ouverture."""
    groups = [
        (f'path:"{DIR_CAT}"', '#D6336C'),    # Catégories d'aléa
        (f'path:"{DIR_ALEA}"', '#E8A400'),   # Types d'aléa
        (f'path:"{DIR_FAM}"', '#1098AD'),    # Familles de risque
        (f'path:"{DIR_RISK}"', '#7048E8'),   # Risques
        (f'path:"{DIR_SCORE}"', '#868E96'),  # Scoring
    ]
    config = {
        'collapse-filter': True,
        'search': '',
        'showTags': False,          # activable en direct pour révéler les tags
        'showAttachments': False,
        'hideUnresolved': False,
        'showOrphans': True,
        'collapse-color-groups': False,
        'colorGroups': [
            {'query': q, 'color': {'a': 1, 'rgb': rgb_int(c)}} for q, c in groups
        ],
        'collapse-display': True,
        'showArrows': True,
        'textFadeMultiplier': -0.8,  # libellés visibles même dézoomé
        'nodeSizeMultiplier': 1.3,
        'lineSizeMultiplier': 1,
        'collapse-forces': True,
        'centerStrength': 0.45,
        'repelStrength': 12,
        'linkStrength': 0.8,
        'linkDistance': 180,
        'scale': 0.6,
        'close': False,
    }
    directory = os.path.join(VAULT, '.obsidian')
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, 'graph.json'), 'w', encoding='utf-8') as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
    return len(groups)


# --------------------------------------------------------------------------- #
# Canvas de présentation (format JSON Canvas)
# --------------------------------------------------------------------------- #
def build_canvas(ctx):
    """Disposition FIXE du schéma d'ontologie.

    La vue graphe d'Obsidian est force-directed : sa disposition change à
    chaque ouverture. Un Canvas donne un rendu identique à chaque fois, et
    reste cliquable (les noeuds-fichiers ouvrent les notes).
    """
    categories, families = ctx['categories'], ctx['families']
    cat_title, fam_title = ctx['cat_title'], ctx['fam_title']
    nodes, edges = [], []

    def node(**kw):
        nodes.append(kw)
        return kw['id']

    def edge(src, dst, from_side, to_side, label=None):
        e = {'id': f'e{len(edges)}', 'fromNode': src, 'fromSide': from_side,
             'toNode': dst, 'toSide': to_side}
        if label:
            e['label'] = label
        edges.append(e)

    ROW = 130
    # --- Titre ---
    node(id='titre', type='text', x=-420, y=-980, width=1040, height=110,
         text='# Ontologie du référentiel de risques\n'
              '_DISCOVER — 8 catégories · 64 aléas · 9 familles · 18 risques_')

    # --- Colonne gauche : catégories d'aléa ---
    h_left = 90 + len(categories) * ROW
    node(id='grp_aleas', type='group', x=-1500, y=-760, width=620, height=h_left,
         label=f'ALÉAS — {len(categories)} catégories, {len(ctx["scenarios"])} types', color='2')
    for i, c in enumerate(categories):
        node(id=f'cat{i}', type='file', file=f'{DIR_CAT}/{cat_title[c["id"]]}.md',
             x=-1450, y=-690 + i * ROW, width=520, height=100, color='2')

    # --- Colonne droite : familles de risque ---
    h_right = 90 + len(families) * ROW
    node(id='grp_risques', type='group', x=900, y=-760, width=620, height=h_right,
         label=f'RISQUES — {len(families)} familles, {len(families) * 2} intitulés', color='5')
    for i, f in enumerate(families):
        node(id=f'fam{i}', type='file', file=f'{DIR_FAM}/{fam_title[f["domain"]]}.md',
             x=950, y=-690 + i * ROW, width=520, height=100, color='5')

    # --- Centre : la règle de croisement ---
    node(id='croisement', type='file', file='Matrice aléa × famille.md',
         x=-400, y=-700, width=1000, height=140, color='3')
    node(id='note_cart', type='text', x=-400, y=-520, width=1000, height=120,
         text='**Croisement exhaustif** : tout aléa se décline dans les 9 familles.\n'
              f'{len(ctx["scenarios"])} × {len(families)} × 2 = **1152 lignes** du CSV — '
              'règle énoncée, non matérialisée.')

    # --- Centre bas : le pont de scoring ---
    node(id='pont', type='text', x=-400, y=-250, width=1000, height=90,
         text='## Le pont entre les deux taxonomies')
    node(id='prob', type='text', x=-400, y=-120, width=470, height=110,
         text='**Probabilité**\n_portée par l’aléa_', color='6')
    node(id='grav', type='text', x=130, y=-120, width=470, height=110,
         text='**Gravité**\n_portée par la famille_', color='6')
    node(id='crit', type='file', file=f'{DIR_SCORE}/Matrice de criticité.md',
         x=-400, y=60, width=1000, height=140, color='6')

    # --- Arêtes : groupes vers le centre, puis le scoring ---
    edge('grp_aleas', 'croisement', 'right', 'left', 'se décline en')
    edge('grp_risques', 'croisement', 'left', 'right', 'regroupe')
    edge('grp_aleas', 'prob', 'bottom', 'left', 'porte')
    edge('grp_risques', 'grav', 'bottom', 'right', 'porte')
    edge('prob', 'crit', 'bottom', 'top')
    edge('grav', 'crit', 'bottom', 'top')

    path = os.path.join(VAULT, 'Ontologie — schéma.canvas')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({'nodes': nodes, 'edges': edges}, fh, ensure_ascii=False, indent=2)
    return len(nodes), len(edges)


if __name__ == '__main__':
    ctx = build()
    n_groups = build_graph_config()
    n_nodes, n_edges = build_canvas(ctx)
    print(f"Vault généré : {VAULT}")
    print(f"  notes            : {ctx['counts']['notes']}")
    print(f"  liens            : {ctx['counts']['links']}")
    print(f"  groupes couleur  : {n_groups}")
    print(f"  canvas           : {n_nodes} noeuds, {n_edges} arêtes")

