<template>
  <div class="crisis-graph" ref="containerRef">
    <svg ref="svgRef" class="crisis-graph__svg"></svg>

    <!-- Contrôles -->
    <div class="crisis-graph__controls" v-if="nodes.length">
      <button class="ctrl-btn" @click="recenter" title="Réajuster le graphe à la vue">
        Recentrer
      </button>
      <label class="ctrl-crit" :title="'Masquer les nœuds de criticité inférieure à ' + minCriticality">
        <span>Criticité ≥ {{ minCriticality }}</span>
        <input type="range" min="1" max="5" step="1" v-model.number="minCriticality" />
      </label>
    </div>

    <!-- Légende des familles (cliquable : masque/affiche une famille) -->
    <div class="crisis-graph__legend" v-if="families.length">
      <div class="legend-title">Familles</div>
      <button
        v-for="f in families"
        :key="f.id"
        :class="['legend-item', { 'legend-item--off': isHidden(f.id) }]"
        :title="f.domains.join(', ')"
        @click="toggleFamily(f.id)"
      >
        <span class="legend-dot" :style="{ background: f.color }"></span>
        <span class="legend-label">{{ f.label }}</span>
        <span class="legend-count">{{ f.count }}</span>
      </button>
    </div>

    <!-- Panneau de détail -->
    <div class="crisis-graph__detail" v-if="selected">
      <button class="detail-close" @click="selected = null">×</button>
      <template v-if="selected.kind === 'node'">
        <div class="detail-domain" :style="{ color: familyColor(selected.domain) }">
          {{ familyOf(selected.domain).label }} · {{ selected.domain }} · {{ selected.type }}
        </div>
        <div class="detail-title">{{ selected.label }}</div>
        <div class="detail-crit">Criticité : <strong>{{ selected.criticality }}/5</strong></div>
        <div class="detail-desc">{{ selected.description || '—' }}</div>
      </template>
      <template v-else>
        <div class="detail-domain">{{ relationStyle(selected.relation).label }}</div>
        <div class="detail-title">{{ selected.sourceLabel }} → {{ selected.targetLabel }}</div>
        <div class="detail-crit">Poids de propagation : <strong>{{ selected.weight }}</strong></div>
        <div class="detail-desc">{{ selected.description || '—' }}</div>
      </template>
    </div>

    <div class="crisis-graph__empty" v-if="!nodes.length">
      Aucun graphe à afficher.
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import * as d3 from 'd3'
import {
  GRAPH, DOMAIN_FAMILIES, familyOf, familyColor, relationStyle,
} from '@/styles/palette'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  impactMode: { type: Boolean, default: false },
})

const containerRef = ref(null)
const svgRef = ref(null)
const selected = ref(null)

// --- Filtres (état persistant entre deux rendus) ---
const hiddenFamilies = ref([])
const minCriticality = ref(1)
const isHidden = (id) => hiddenFamilies.value.includes(id)

function toggleFamily(id) {
  hiddenFamilies.value = isHidden(id)
    ? hiddenFamilies.value.filter((x) => x !== id)
    : [...hiddenFamilies.value, id]
}

// Familles réellement présentes dans le graphe, avec leur effectif.
const families = computed(() => {
  const counts = {}
  props.nodes.forEach((n) => {
    const f = familyOf(n.domain)
    counts[f.id] = (counts[f.id] || 0) + 1
  })
  return DOMAIN_FAMILIES
    .filter((f) => counts[f.id])
    .map((f) => ({ ...f, count: counts[f.id] }))
})

const LABEL_MAX = 24
const truncate = (s) => {
  const t = String(s || '')
  return t.length > LABEL_MAX ? t.slice(0, LABEL_MAX - 1).trimEnd() + '…' : t
}

// Mesure de texte réelle (pour dimensionner la force de collision).
let measureCtx = null
function textWidth(text, fontSize, weight) {
  if (!measureCtx) measureCtx = document.createElement('canvas').getContext('2d')
  measureCtx.font = `${weight} ${fontSize}px system-ui, sans-serif`
  return measureCtx.measureText(text).width
}

const nodeRadius = (d) => 8 + (d.criticality || 3) * 3
const labelSize = (d) => ((d.criticality || 3) >= 4 ? 12 : 10.5)
const labelWeight = (d) => ((d.criticality || 3) >= 4 ? 600 : 400)

// Sélections d3 conservées pour appliquer les filtres sans relancer la simulation.
let simulation = null
let resizeObserver = null
let svgSel = null
let gSel = null
let zoomBehavior = null
let nodeSel = null
let linkSel = null

function render() {
  const svgEl = svgRef.value
  const container = containerRef.value
  if (!svgEl || !container) return

  const width = container.clientWidth || 800
  const height = container.clientHeight || 600

  const svg = d3.select(svgEl)
  svg.selectAll('*').remove()
  svg.attr('viewBox', [0, 0, width, height])
  svgSel = svg

  if (simulation) simulation.stop()
  if (!props.nodes.length) return

  // Copies pour d3 (mutations internes)
  const nodes = props.nodes.map((n) => ({ ...n }))
  const idToLabel = Object.fromEntries(nodes.map((n) => [n.id, n.label]))
  const links = props.edges.map((e) => ({ ...e }))

  // Voisinage, pour la focalisation au survol.
  const neighbors = {}
  nodes.forEach((n) => { neighbors[n.id] = new Set([n.id]) })
  links.forEach((l) => {
    const s = typeof l.source === 'object' ? l.source.id : l.source
    const t = typeof l.target === 'object' ? l.target.id : l.target
    if (neighbors[s]) neighbors[s].add(t)
    if (neighbors[t]) neighbors[t].add(s)
  })

  // --- Marqueurs de flèche ---
  // markerUnits='userSpaceOnUse' : sans cela, le marqueur est multiplié par
  // l'épaisseur du trait (jusqu'à 8), produisant des flèches de 30-48 px.
  const defs = svg.append('defs')
  const addMarker = (id, color) => {
    defs.append('marker')
      .attr('id', id)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 10)
      .attr('refY', 0)
      .attr('markerWidth', 9)
      .attr('markerHeight', 9)
      .attr('markerUnits', 'userSpaceOnUse')
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', color)
  }
  addMarker('arrow', GRAPH.edge)
  addMarker('arrow-active', GRAPH.edgeActive)

  const g = svg.append('g')
  gSel = g

  zoomBehavior = d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => g.attr('transform', event.transform))
  svg.call(zoomBehavior)

  const isActive = (d) => props.impactMode && d.active
  const edgeColor = (d) => (isActive(d) ? GRAPH.edgeActive : GRAPH.edge)

  // --- Arêtes (path : permet la courbure) ---
  const link = g.append('g')
    .selectAll('path')
    .data(links)
    .join('path')
    .attr('fill', 'none')
    .attr('stroke', edgeColor)
    .attr('stroke-opacity', 0.55)
    .attr('stroke-width', (d) => {
      const base = isActive(d) ? 1.5 + (d.flow || 0) * 4 : 0.9 + (d.weight || 0.5) * 2.2
      return relationStyle(d.relation).emphasis ? base * 1.35 : base
    })
    .attr('stroke-dasharray', (d) => relationStyle(d.relation).dash)
    .attr('marker-end', (d) => (isActive(d) ? 'url(#arrow-active)' : 'url(#arrow)'))
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      selected.value = {
        kind: 'edge',
        relation: d.relation,
        weight: d.weight,
        description: d.description,
        sourceLabel: idToLabel[typeof d.source === 'object' ? d.source.id : d.source] || d.source,
        targetLabel: idToLabel[typeof d.target === 'object' ? d.target.id : d.target] || d.target,
      }
    })
  link.append('title').text((d) => relationStyle(d.relation).label)
  linkSel = link

  // --- Nœuds ---
  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .style('cursor', 'pointer')
    .call(d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended))
    .on('click', (event, d) => {
      event.stopPropagation()
      selected.value = { kind: 'node', ...d }
    })
    .on('mouseenter', (event, d) => focusOn(d.id))
    .on('mouseleave', () => focusOn(null))
  nodeSel = node

  // Halo d'impact (mode propagation) — inséré sous le cercle principal.
  if (props.impactMode) {
    node.filter((d) => (d.impact_score || 0) > 0.05)
      .append('circle')
      .attr('class', 'impact-halo')
      .attr('r', (d) => nodeRadius(d) + 4 + (d.impact_score || 0) * 14)
      .attr('fill', 'none')
      .attr('stroke', GRAPH.impact)
      .attr('stroke-opacity', (d) => 0.25 + (d.impact_score || 0) * 0.6)
      .attr('stroke-width', (d) => 1 + (d.impact_score || 0) * 4)
  }

  node.append('circle')
    .attr('r', nodeRadius)
    .attr('fill', (d) => familyColor(d.domain))
    .attr('stroke', GRAPH.nodeStroke)
    .attr('stroke-width', 2)

  // Libellé : tronqué, avec halo clair pour rester lisible sur les arêtes.
  node.append('text')
    .text((d) => truncate(d.label))
    .attr('x', 0)
    .attr('y', (d) => nodeRadius(d) + 12)
    .attr('text-anchor', 'middle')
    .attr('font-size', (d) => `${labelSize(d)}px`)
    .attr('font-weight', labelWeight)
    .attr('fill', GRAPH.text)
    .attr('stroke', GRAPH.textHalo)
    .attr('stroke-width', 3)
    .attr('paint-order', 'stroke')
    .attr('pointer-events', 'none')

  // Libellé complet en infobulle native (le texte affiché est tronqué).
  node.append('title').text((d) => `${d.label} — criticité ${d.criticality || '?'}/5`)

  svg.on('click', () => { selected.value = null })

  // --- Focalisation au survol ---
  function focusOn(id) {
    if (!id) {
      node.style('opacity', null)
      link.style('opacity', null)
      applyFilters()
      return
    }
    const near = neighbors[id] || new Set([id])
    node.style('opacity', (d) => (near.has(d.id) ? 1 : GRAPH.dim))
    link.style('opacity', (d) => {
      const s = typeof d.source === 'object' ? d.source.id : d.source
      const t = typeof d.target === 'object' ? d.target.id : d.target
      return (s === id || t === id) ? 0.95 : GRAPH.dim
    })
  }

  // --- Forces ---
  const n = nodes.length
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id((d) => d.id)
      // Une dépendance forte rapproche, une dépendance faible éloigne.
      .distance((d) => 190 - (d.weight || 0.5) * 70)
      .strength((d) => 0.25 + (d.weight || 0.5) * 0.45))
    .force('charge', d3.forceManyBody().strength(n > 24 ? -900 : -650))
    .force('center', d3.forceCenter(width / 2, height / 2))
    // Rappel doux vers le centre : évite la dérive verticale observée.
    .force('x', d3.forceX(width / 2).strength(0.045))
    .force('y', d3.forceY(height / 2).strength(0.07))
    // Collision tenant compte de la largeur réelle du libellé. Le plafond doit
    // rester au-dessus de la demi-largeur maximale d'un libellé tronqué
    // (~85 px), sinon il écrête et les libellés longs se chevauchent à nouveau.
    .force('collide', d3.forceCollide().radius((d) => {
      const half = textWidth(truncate(d.label), labelSize(d), labelWeight(d)) / 2
      return Math.max(nodeRadius(d) + 10, Math.min(half + 6, 95))
    }).iterations(2))
    .on('tick', ticked)
    .on('end', () => fitToView(false))

  function linkPath(d) {
    const sx = d.source.x
    const sy = d.source.y
    const tx = d.target.x
    const ty = d.target.y
    const dx = tx - sx
    const dy = ty - sy
    const dist = Math.hypot(dx, dy) || 1
    // On raccourcit à la frontière du nœud cible pour que la pointe de flèche
    // ne soit pas masquée par le cercle.
    const gap = nodeRadius(d.target) + 9
    const ex = tx - (dx / dist) * gap
    const ey = ty - (dy / dist) * gap
    const dr = dist * 2.6 // grand rayon => courbure légère
    return `M${sx},${sy}A${dr},${dr} 0 0,1 ${ex},${ey}`
  }

  function ticked() {
    link.attr('d', linkPath)
    node.attr('transform', (d) => `translate(${d.x},${d.y})`)
  }

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    d.fx = d.x; d.fy = d.y
  }
  function dragged(event, d) { d.fx = event.x; d.fy = event.y }
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0)
    d.fx = null; d.fy = null
  }

  applyFilters()
}

/**
 * Applique les filtres par simple masquage visuel : la simulation n'est pas
 * relancée, le graphe ne se réorganise donc pas à chaque clic.
 */
function applyFilters() {
  if (!nodeSel || !linkSel) return
  const visible = (d) => !isHidden(familyOf(d.domain).id)
    && (d.criticality || 3) >= minCriticality.value

  nodeSel.style('display', (d) => (visible(d) ? null : 'none'))
  linkSel.style('display', (d) => {
    const s = typeof d.source === 'object' ? d.source : null
    const t = typeof d.target === 'object' ? d.target : null
    return (s && t && visible(s) && visible(t)) ? null : 'none'
  })
}

/** Ajuste le zoom pour que tout le graphe visible tienne dans le cadre. */
function fitToView(animate = true) {
  const container = containerRef.value
  if (!svgSel || !gSel || !zoomBehavior || !container) return
  const width = container.clientWidth || 800
  const height = container.clientHeight || 600

  const pts = []
  if (nodeSel) {
    nodeSel.each(function nodeBounds(d) {
      if (this.style.display === 'none') return
      pts.push([d.x, d.y])
    })
  }
  if (pts.length < 2) return

  const xs = pts.map((p) => p[0])
  const ys = pts.map((p) => p[1])
  const pad = 90 // marge pour les libellés, placés sous les nœuds
  const minX = Math.min(...xs) - pad
  const maxX = Math.max(...xs) + pad
  const minY = Math.min(...ys) - pad
  const maxY = Math.max(...ys) + pad
  const w = maxX - minX
  const h = maxY - minY
  if (!w || !h) return

  const scale = Math.min(2, 0.95 / Math.max(w / width, h / height))
  const tx = width / 2 - scale * (minX + w / 2)
  const ty = height / 2 - scale * (minY + h / 2)
  const transform = d3.zoomIdentity.translate(tx, ty).scale(scale)

  const target = animate ? svgSel.transition().duration(450) : svgSel
  target.call(zoomBehavior.transform, transform)
}

function recenter() {
  fitToView(true)
}

onMounted(() => {
  render()
  resizeObserver = new ResizeObserver(() => render())
  if (containerRef.value) resizeObserver.observe(containerRef.value)
})

onBeforeUnmount(() => {
  if (simulation) simulation.stop()
  if (resizeObserver) resizeObserver.disconnect()
})

watch(() => [props.nodes, props.edges], () => {
  selected.value = null
  render()
}, { deep: true })

// Les filtres ne redessinent pas : ils masquent, puis réajustent le cadrage.
watch([hiddenFamilies, minCriticality], () => {
  applyFilters()
  fitToView(true)
})
</script>

<style scoped>
.crisis-graph {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 480px;
  background: var(--surface-alt);
  border-radius: 12px;
  overflow: hidden;
}
.crisis-graph__svg { width: 100%; height: 100%; display: block; }

/* --- Contrôles --- */
.crisis-graph__controls {
  position: absolute;
  top: 12px; left: 50%;
  transform: translateX(-50%);
  display: flex; align-items: center; gap: 14px;
  background: var(--overlay);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text);
}
.ctrl-btn {
  background: none; border: 1px solid var(--border-strong);
  border-radius: 6px; padding: 3px 10px;
  font-size: 12px; color: var(--text); cursor: pointer;
}
.ctrl-btn:hover { border-color: var(--accent); color: var(--accent); }
.ctrl-crit { display: flex; align-items: center; gap: 8px; white-space: nowrap; }
.ctrl-crit input { width: 90px; accent-color: var(--accent); cursor: pointer; }

/* --- Légende --- */
.crisis-graph__legend {
  position: absolute;
  top: 12px; left: 12px;
  background: var(--overlay);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  color: var(--text);
  max-width: 200px;
}
.legend-title { font-weight: 600; margin-bottom: 6px; opacity: 0.8; }
.legend-item {
  display: flex; align-items: center; gap: 6px;
  margin: 2px 0; padding: 2px 4px;
  width: 100%; background: none; border: none; border-radius: 4px;
  font-size: 12px; color: inherit; text-align: left; cursor: pointer;
}
.legend-item:hover { background: var(--surface-alt); }
.legend-item--off { opacity: 0.4; text-decoration: line-through; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex: none; }
.legend-label { flex: 1; }
.legend-count { color: var(--text-subtle); font-variant-numeric: tabular-nums; }

/* --- Panneau de détail --- */
.crisis-graph__detail {
  position: absolute;
  top: 12px; right: 12px;
  width: 260px;
  background: var(--overlay);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  color: var(--text);
}
.detail-close {
  position: absolute; top: 6px; right: 8px;
  background: none; border: none; color: var(--text-muted);
  font-size: 18px; cursor: pointer;
}
.detail-domain { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }
.detail-title { font-size: 15px; font-weight: 600; margin: 4px 0 8px; }
.detail-crit { font-size: 13px; margin-bottom: 8px; }
.detail-desc { font-size: 13px; line-height: 1.4; opacity: 0.85; }

.crisis-graph__empty {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-subtle);
}
</style>
