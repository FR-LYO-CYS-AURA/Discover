<template>
  <div class="crisis-graph" ref="containerRef">
    <svg ref="svgRef" class="crisis-graph__svg"></svg>

    <!-- Légende des domaines -->
    <div class="crisis-graph__legend" v-if="domains.length">
      <div class="legend-title">Domaines</div>
      <div class="legend-item" v-for="d in domains" :key="d">
        <span class="legend-dot" :style="{ background: colorFor(d) }"></span>
        <span class="legend-label">{{ d }}</span>
      </div>
    </div>

    <!-- Panneau de détail -->
    <div class="crisis-graph__detail" v-if="selected">
      <button class="detail-close" @click="selected = null">×</button>
      <template v-if="selected.kind === 'node'">
        <div class="detail-domain" :style="{ color: colorFor(selected.domain) }">{{ selected.domain }} · {{ selected.type }}</div>
        <div class="detail-title">{{ selected.label }}</div>
        <div class="detail-crit">Criticité : <strong>{{ selected.criticality }}/5</strong></div>
        <div class="detail-desc">{{ selected.description || '—' }}</div>
      </template>
      <template v-else>
        <div class="detail-domain">{{ selected.relation }}</div>
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

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
})

const containerRef = ref(null)
const svgRef = ref(null)
const selected = ref(null)

let simulation = null
let resizeObserver = null

// Palette par domaine
const DOMAIN_COLORS = {
  cybersecurite: '#e63946',
  sante: '#2a9d8f',
  rh: '#e9c46a',
  juridique: '#8d99ae',
  finance: '#457b9d',
  communication: '#f4a261',
  operations: '#6a4c93',
  logistique: '#264653',
  physique: '#b5838d',
  geopolitique: '#a44a3f',
  reglementaire: '#6d6875',
  reputation: '#ff8fab',
  autre: '#adb5bd',
}
function colorFor(domain) {
  return DOMAIN_COLORS[domain] || DOMAIN_COLORS.autre
}

const domains = computed(() => {
  const set = new Set(props.nodes.map(n => n.domain))
  return Array.from(set)
})

function render() {
  const svgEl = svgRef.value
  const container = containerRef.value
  if (!svgEl || !container) return

  const width = container.clientWidth || 800
  const height = container.clientHeight || 600

  const svg = d3.select(svgEl)
  svg.selectAll('*').remove()
  svg.attr('viewBox', [0, 0, width, height])

  if (!props.nodes.length) return

  // Copies pour d3 (mutations internes)
  const nodes = props.nodes.map(n => ({ ...n }))
  const idToLabel = Object.fromEntries(nodes.map(n => [n.id, n.label]))
  const links = props.edges.map(e => ({ ...e }))

  // Marqueur de flèche
  const defs = svg.append('defs')
  defs.append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#9aa0a6')

  const g = svg.append('g')

  const zoom = d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => g.attr('transform', event.transform))
  svg.call(zoom)

  // Arêtes
  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#9aa0a6')
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', d => 1 + (d.weight || 0.5) * 4)
    .attr('marker-end', 'url(#arrow)')
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

  // Noeuds
  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
    .on('click', (event, d) => {
      event.stopPropagation()
      selected.value = { kind: 'node', ...d }
    })

  node.append('circle')
    .attr('r', d => 8 + (d.criticality || 3) * 3)
    .attr('fill', d => colorFor(d.domain))
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)

  node.append('text')
    .text(d => d.label)
    .attr('x', 0)
    .attr('y', d => 8 + (d.criticality || 3) * 3 + 12)
    .attr('text-anchor', 'middle')
    .attr('font-size', '11px')
    .attr('fill', '#e8eaed')
    .attr('pointer-events', 'none')

  svg.on('click', () => { selected.value = null })

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(140))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide().radius(d => 20 + (d.criticality || 3) * 3))
    .on('tick', ticked)

  function ticked() {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)
    node.attr('transform', d => `translate(${d.x},${d.y})`)
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
</script>

<style scoped>
.crisis-graph {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 480px;
  background: #14161a;
  border-radius: 12px;
  overflow: hidden;
}
.crisis-graph__svg { width: 100%; height: 100%; display: block; }

.crisis-graph__legend {
  position: absolute;
  top: 12px; left: 12px;
  background: rgba(20, 22, 26, 0.85);
  border: 1px solid #2a2d33;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  color: #e8eaed;
  max-width: 180px;
}
.legend-title { font-weight: 600; margin-bottom: 6px; opacity: 0.8; }
.legend-item { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.legend-label { text-transform: capitalize; }

.crisis-graph__detail {
  position: absolute;
  top: 12px; right: 12px;
  width: 260px;
  background: rgba(20, 22, 26, 0.95);
  border: 1px solid #2a2d33;
  border-radius: 8px;
  padding: 14px;
  color: #e8eaed;
}
.detail-close {
  position: absolute; top: 6px; right: 8px;
  background: none; border: none; color: #9aa0a6;
  font-size: 18px; cursor: pointer;
}
.detail-domain { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }
.detail-title { font-size: 15px; font-weight: 600; margin: 4px 0 8px; }
.detail-crit { font-size: 13px; margin-bottom: 8px; }
.detail-desc { font-size: 13px; line-height: 1.4; opacity: 0.85; }

.crisis-graph__empty {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #6b7280;
}
</style>
