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

// Couleurs du graphe D3 (thème clair).
export const GRAPH = {
  text: '#1A1D23',        // labels de nœuds
  edge: '#8A94A2',        // arêtes au repos
  edgeActive: '#F85810',  // arête active (mode propagation)
  nodeStroke: '#FFFFFF',  // contour de nœud (séparation)
  impact: '#F85810',      // halo d'impact
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
