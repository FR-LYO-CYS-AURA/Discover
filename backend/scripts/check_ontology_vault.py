"""Validation structurelle du vault Obsidian généré (`data/onto/`).

Obsidian n'étant pas installable ici, on ne peut pas valider le RENDU.
On valide donc tout ce qui est vérifiable mécaniquement :
  - chaque [[lien]] pointe vers une note existante (zéro lien non résolu) ;
  - aucun caractère interdit dans les noms de fichiers ;
  - frontmatter présent et parsable sur chaque note ;
  - comptages conformes au référentiel source ;
  - canvas : JSON valide, fichiers référencés existants, arêtes cohérentes ;
  - graph.json : JSON valide, requêtes de groupe pointant sur des dossiers réels.

Usage : python backend/scripts/check_ontology_vault.py
Sortie : code 0 si tout est conforme, 1 sinon.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
VAULT = os.path.join(ROOT, 'data', 'onto')
SOURCE = os.path.join(ROOT, 'backend', 'app', 'data', 'risk_referentiel.json')

FORBIDDEN = set('\\/:*?"<>|#^[]')
WIKILINK = re.compile(r'\[\[([^\]\|#]+)(?:[#\|][^\]]*)?\]\]')

failures = []


def check(ok: bool, label: str, detail: str = ''):
    print(f"  {'OK  ' if ok else 'ÉCHEC'} {label}{(' — ' + detail) if detail and not ok else ''}")
    if not ok:
        failures.append(label)


def main():
    with open(SOURCE, 'r', encoding='utf-8') as fh:
        ref = json.load(fh)

    # --- Index des notes ---
    notes = {}
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d != '.obsidian']
        for f in files:
            if f.endswith('.md'):
                notes[f[:-3]] = os.path.join(root, f)

    print('--- Structure ---')
    expected = (len(ref['categories']) + len(ref['scenarios']) + len(ref['families'])
                + len(ref['families']) * 2 + 7 + 2)
    check(len(notes) == expected, f'{len(notes)} notes (attendu {expected})')
    for folder in ('Catégories', 'Aléas', 'Familles', 'Risques', 'Scoring'):
        check(os.path.isdir(os.path.join(VAULT, folder)), f'dossier {folder}/')

    counts = {
        'Catégories': len(ref['categories']),
        'Aléas': len(ref['scenarios']),
        'Familles': len(ref['families']),
        'Risques': len(ref['families']) * 2,
    }
    for folder, n in counts.items():
        got = len([f for f in os.listdir(os.path.join(VAULT, folder)) if f.endswith('.md')])
        check(got == n, f'{folder}/ contient {got} notes (attendu {n})')

    # --- Noms de fichiers ---
    print('\n--- Noms de fichiers ---')
    bad = [t for t in notes if set(t) & FORBIDDEN]
    check(not bad, 'aucun caractère interdit dans les titres', str(bad[:3]))

    # --- Liens ---
    print('\n--- Liens ---')
    total, unresolved, incoming = 0, {}, {t: 0 for t in notes}
    for title, path in notes.items():
        txt = open(path, encoding='utf-8').read()
        for target in WIKILINK.findall(txt):
            target = target.strip()
            total += 1
            if target in notes:
                incoming[target] += 1
            else:
                unresolved.setdefault(target, []).append(title)
    check(not unresolved, f'{total} liens, 0 non résolu',
          '; '.join(f'[[{k}]] depuis {v[0]}' for k, v in list(unresolved.items())[:3]))
    orphans = [t for t, n in incoming.items() if n == 0]
    check(not orphans, 'aucune note orpheline (sans lien entrant)', str(orphans[:3]))

    # --- Frontmatter ---
    print('\n--- Frontmatter ---')
    missing, unbalanced = [], []
    for title, path in notes.items():
        txt = open(path, encoding='utf-8').read()
        if not txt.startswith('---\n'):
            missing.append(title)
            continue
        if txt.count('\n---\n') < 1:
            unbalanced.append(title)
    check(not missing, 'frontmatter présent sur toutes les notes', str(missing[:3]))
    check(not unbalanced, 'frontmatter correctement fermé', str(unbalanced[:3]))

    # --- Le pont de scoring (cohérence sémantique) ---
    print('\n--- Pont de scoring ---')
    probs = {s['base_probability'] for s in ref['scenarios']}
    gravs = {f['gravite'] for f in ref['families']}
    for p in probs:
        check(f'Probabilité {p}' in notes, f'note « Probabilité {p} »')
    for g in gravs:
        check(f'Gravité {g}' in notes, f'note « Gravité {g} »')
    check('Matrice de criticité' in notes, 'note « Matrice de criticité »')
    check('Matrice aléa × famille' in notes, 'note « Matrice aléa × famille »')

    # chaque aléa doit référencer sa catégorie ET sa probabilité
    bad_alea = []
    for s in ref['scenarios']:
        title = re.sub(r'[\\/:*?"<>|#^\[\]]', '–', s['type'])
        txt = open(notes[title], encoding='utf-8').read()
        if f"Probabilité {s['base_probability']}]]" not in txt:
            bad_alea.append(title)
    check(not bad_alea, 'chaque aléa est relié à sa probabilité', str(bad_alea[:3]))

    bad_fam = []
    for f in ref['families']:
        title = re.sub(r'[\\/:*?"<>|#^\[\]]', '–', f['label'])
        txt = open(notes[title], encoding='utf-8').read()
        if f"Gravité {f['gravite']}]]" not in txt or f['domain'] not in txt:
            bad_fam.append(title)
    check(not bad_fam, 'chaque famille est reliée à sa gravité et son domaine', str(bad_fam[:3]))

    # --- Absence du produit cartésien ---
    print('\n--- Garde-fou produit cartésien ---')
    check(len(notes) < 200, f'{len(notes)} notes, très en deçà des 1152 lignes du CSV')

    # --- La matrice du vault correspond-elle au moteur applicatif ? ---
    print('\n--- Cohérence avec le moteur de scoring ---')
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'scoring', os.path.join(ROOT, 'backend', 'app', 'utils', 'scoring.py'))
    scoring_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scoring_mod)   # module autonome, aucune dépendance Flask

    matrix_txt = open(notes['Matrice de criticité'], encoding='utf-8').read()
    gravs_sorted = sorted(gravs)
    mismatches = []
    for p in sorted(probs):
        rows = [l for l in matrix_txt.split('\n') if l.startswith(f'| [[Probabilité {p}]]')]
        if not rows:
            mismatches.append(f'ligne manquante pour {p}')
            continue
        cells = re.findall(r'\*\*([^*]+)\*\*', rows[0])
        for label, g in zip(cells, gravs_sorted):
            expected = scoring_mod.criticite_label(p, g)
            if label.strip() != expected:
                mismatches.append(f'{p}x{g}: vault={label.strip()} moteur={expected}')
    check(not mismatches, 'matrice de criticité conforme au moteur applicatif',
          '; '.join(mismatches[:3]))

    # --- Canvas ---
    print('\n--- Canvas ---')
    canvas_path = os.path.join(VAULT, 'Ontologie — schéma.canvas')
    check(os.path.exists(canvas_path), 'fichier canvas présent')
    if os.path.exists(canvas_path):
        try:
            canvas = json.load(open(canvas_path, encoding='utf-8'))
            check(True, 'canvas : JSON valide')
            ids = {n['id'] for n in canvas['nodes']}
            check(len(ids) == len(canvas['nodes']), 'canvas : identifiants de noeuds uniques')
            missing_files = [n['file'] for n in canvas['nodes']
                             if n.get('type') == 'file'
                             and not os.path.exists(os.path.join(VAULT, n['file']))]
            check(not missing_files, 'canvas : tous les fichiers référencés existent',
                  str(missing_files[:3]))
            dangling = [e['id'] for e in canvas['edges']
                        if e['fromNode'] not in ids or e['toNode'] not in ids]
            check(not dangling, 'canvas : aucune arête pendante', str(dangling[:3]))
            required = {'id', 'type', 'x', 'y', 'width', 'height'}
            malformed = [n.get('id') for n in canvas['nodes'] if not required <= set(n)]
            check(not malformed, 'canvas : noeuds conformes au format JSON Canvas',
                  str(malformed[:3]))
        except (ValueError, KeyError) as exc:
            check(False, 'canvas : JSON valide', str(exc))

    # --- graph.json ---
    print('\n--- Configuration de la vue graphe ---')
    gpath = os.path.join(VAULT, '.obsidian', 'graph.json')
    check(os.path.exists(gpath), 'fichier .obsidian/graph.json présent')
    if os.path.exists(gpath):
        try:
            cfg = json.load(open(gpath, encoding='utf-8'))
            check(True, 'graph.json : JSON valide')
            bad_q = []
            for grp in cfg.get('colorGroups', []):
                m = re.search(r'path:"([^"]+)"', grp.get('query', ''))
                if not m or not os.path.isdir(os.path.join(VAULT, m.group(1))):
                    bad_q.append(grp.get('query'))
            check(not bad_q, 'graph.json : chaque groupe cible un dossier réel', str(bad_q))
            check(all(isinstance(g['color']['rgb'], int) for g in cfg.get('colorGroups', [])),
                  'graph.json : couleurs au format entier attendu par Obsidian')
        except (ValueError, KeyError) as exc:
            check(False, 'graph.json : JSON valide', str(exc))

    print()
    if failures:
        print(f'{len(failures)} contrôle(s) en échec :')
        for f in failures:
            print(f'  - {f}')
        return 1
    print('Vault conforme : tous les contrôles passent.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
