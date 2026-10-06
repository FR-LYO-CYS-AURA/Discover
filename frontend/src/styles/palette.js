/*
 * DISCOVER — palette des couleurs utilisées côté JavaScript (D3, heatmaps, chips).
 * Source unique : évite les duplications/divergences entre composants.
 * Teintes ajustées pour rester lisibles sur le thème CLAIR.
 */

// Couleur par domaine d'impact (remplit les nœuds du graphe, pastilles, etc.).
// Union des clés utilisées par le graphe et par la vue simulation.
export const DOMAIN_COLORS = {
  cybersecurite: '#D6336C',
  sante: '#0CA678',
  rh: '#E8A400',
  juridique: '#5C6BC0',
  finance: '#1C7ED6',
  communication: '#F76707',
  operations: '#7048E8',
  operationnel: '#7048E8',
  logistique: '#1098AD',
  technique: '#1098AD',
  physique: '#A9518A',
  resilience: '#A9518A',
  geopolitique: '#C0392B',
  reglementaire: '#6D6875',
  reputation: '#E64980',
  autre: '#868E96',
}

export function colorFor(domain) {
  return DOMAIN_COLORS[domain] || DOMAIN_COLORS.autre
}
export const domainColor = colorFor

/*
 * Familles de domaines — lisibilité du graphe de crise.
 *
 * Les nœuds peuvent porter 15 domaines (9 familles d'experts + 6 domaines
 * "secteur"). Sur un graphe de ~20 nœuds, cela produit autant de teintes que
 * de nœuds : la couleur ne porte plus aucun signal et la légende devient
 * illisible. On regroupe donc en 7 familles + "autre".
 * Le domaine précis reste affiché dans le panneau de détail.
 *
 * `technique` et `cybersecurite` sont délibérément SÉPARÉS : le référentiel
 * les définit distinctement (« Industriel / technique » vs « Informatique /
 * numérique ») et, dans les graphes réels, `technique` porte les ACTIFS
 * attaqués (Active Directory, DPI, messagerie) tandis que `cybersecurite`
 * porte la MENACE et la défense (rançongiciel, EDR, ANSSI). C'est la
 * distinction la plus structurante d'une crise cyber ; les fusionner
 * masquait la relation cause/cible et concentrait 31 % des nœuds sur une
 * seule couleur.
 *
 * Choix de l'ambre pour `si` plutôt que du vert : le vert offre un meilleur
 * contraste en vision normale (ΔE 120 contre le magenta du cyber) mais s'en
 * rapproche dangereusement en deutéranopie (ΔE 15). L'ambre reste lisible
 * sur les trois visions (88 / 61 / 80).
 */
export const DOMAIN_FAMILIES = [
  { id: 'si', label: 'SI & technique', color: '#E8A400',
    domains: ['technique'] },
  { id: 'cyber', label: 'Cybersécurité', color: '#D6336C',
    domains: ['cybersecurite'] },
  { id: 'ops', label: 'Opérations & terrain', color: '#1098AD',
    domains: ['operationnel', 'operations', 'logistique', 'physique', 'sante'] },
  { id: 'humain', label: 'Humain & juridique', color: '#5C6BC0',
    domains: ['rh', 'juridique', 'reglementaire'] },
  { id: 'finance', label: 'Finance', color: '#1C7ED6',
    domains: ['finance'] },
  { id: 'image', label: 'Image & géopolitique', color: '#F76707',
    domains: ['communication', 'reputation', 'geopolitique'] },
  { id: 'resilience', label: 'Résilience', color: '#7048E8',
    domains: ['resilience'] },
  { id: 'autre', label: 'Autre', color: '#868E96', domains: ['autre'] },
]

const DOMAIN_TO_FAMILY = DOMAIN_FAMILIES.reduce((acc, f) => {
  f.domains.forEach((d) => { acc[d] = f })
  return acc
}, {})

/** Famille d'un domaine (objet complet). Repli sur « Autre ». */
export function familyOf(domain) {
  return DOMAIN_TO_FAMILY[domain] || DOMAIN_TO_FAMILY.autre
}

/** Couleur de famille — utilisée pour les nœuds du graphe. */
export function familyColor(domain) {
  return familyOf(domain).color
}

// Couleurs du graphe D3 (thème clair).
export const GRAPH = {
  text: '#1A1D23',        // labels de nœuds
  edge: '#8A94A2',        // arêtes au repos
  edgeActive: '#F85810',  // arête active (mode propagation)
  nodeStroke: '#FFFFFF',  // contour de nœud (séparation)
  impact: '#F85810',      // halo d'impact
  textHalo: '#FBFBFB',    // contour des libellés (lisibilité sur arête)
  dim: 0.12,              // opacité des éléments hors focus
}

/*
 * Style d'arête par type de relation.
 * Les relations du modèle étaient rendues à l'identique : l'information
 * existait dans les données mais n'était pas visible.
 *  - dépendances structurelles : trait plein
 *  - flux d'information / contrôle : pointillé
 *  - impacte / propage_vers    : accentué (relations d'effet domino)
 * Liste alignée sur ALLOWED_RELATIONS (backend crisis_graph_extractor.py)
 * + 'propage_vers', généré par le moteur domino pour les arêtes virtuelles.
 */
export const RELATION_STYLES = {
  depend_de: { dash: null, label: 'dépend de' },
  fournit: { dash: null, label: 'fournit' },
  heberge: { dash: null, label: 'héberge' },
  impacte: { dash: null, label: 'impacte', emphasis: true },
  propage_vers: { dash: '6,3', label: 'propage vers', emphasis: true },
  communique: { dash: '5,4', label: 'communique' },
  regule: { dash: '2,3', label: 'régule' },
  protege: { dash: '2,3', label: 'protège' },
}

export function relationStyle(relation) {
  return RELATION_STYLES[relation] || { dash: null, label: relation || '—' }
}


// Échelle de sévérité 0..5 (pastilles).
export function sevColor(s) {
  const c = ['#8A94A2', '#0CA678', '#E0A100', '#F0871E', '#EF6C3B', '#F85810']
  return c[s || 0] || c[0]
}

// Indice de criticité 0..100 (fond de chip/barre, texte blanc dessus).
export function idxColor(i) {
  if (i >= 75) return '#C0392B'
  if (i >= 55) return '#E8590C'
  if (i >= 35) return '#B7791F'
  if (i >= 18) return '#2F9E44'
  return '#2B8A3E'
}

// Cellule de heatmap criticité 1..5 (fond clair + texte foncé).
export function heatCell(v) {
  if (!v) return { background: 'var(--surface-alt)', color: 'var(--text-subtle)' }
  const c = ['', '#DDF3E4', '#FBEFC7', '#F8D9A6', '#F3A88A', '#E8836B']
  return { background: c[v] || c[5], color: '#1A1D23' }
}
