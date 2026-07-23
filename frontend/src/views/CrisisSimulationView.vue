<template>
  <div class="sim-view">
    <header class="sim-view__header">
      <button class="back" @click="goBack">← Retour</button>
      <div class="sim-view__title">
        <span class="brand">DISCOVER</span><span class="sep">/</span>
        <span>Simulation de crise</span>
      </div>
      <span :class="['badge', 'badge--' + (sim ? sim.status : 'created')]">{{ statusLabel }}</span>
      <button v-if="sim && sim.status === 'completed'" class="btn-primary" @click="goTrajectories">
        Trajectoires &amp; scoring →
      </button>
    </header>

    <div v-if="running" class="progress">
      <div class="progress__spinner"></div>
      <div class="progress__text">{{ progressText }}</div>
    </div>

    <div class="sim-view__body" v-if="sim">
      <div class="sim-view__panel">
        <CrisisGraph :nodes="graphNodes" :edges="graphEdges" :impact-mode="true" />
      </div>

      <aside class="sim-view__side">
        <div class="side-block">
          <h3>Chaînes de propagation ({{ chains.length }})</h3>
          <div v-if="!chains.length" class="muted">Aucune chaîne significative.</div>
          <div v-for="c in chains" :key="c.id" class="chain">
            <div class="chain__path">
              <span v-for="(lab, i) in c.labels" :key="i">
                {{ lab }}<span v-if="i < c.labels.length - 1" class="arrow"> → </span>
              </span>
            </div>
            <div class="chain__meta">
              <span class="chain__sev" :style="{ background: sevColor(c.severity) }">sév. {{ c.severity || '—' }}/5</span>
              <span v-if="c.multi_domain" class="chain__multi">multi-domaine</span>
              <span class="chain__w">poids {{ c.weight }}</span>
            </div>
            <div v-if="c.narrative" class="chain__narr">{{ c.narrative }}</div>
          </div>
        </div>

        <div class="side-block">
          <h3>Analyses par domaine ({{ analyses.length }})</h3>
          <div v-for="a in analyses" :key="a.domain" class="expert">
            <div class="expert__head">
              <span class="expert__dot" :style="{ background: domainColor(a.domain) }"></span>
              <span class="expert__label">{{ a.domain_label }}</span>
              <span class="expert__sev">P{{ a.severity.probability }}·G{{ a.severity.gravity }}·C{{ a.severity.criticality }}</span>
            </div>
            <ul class="expert__impacts">
              <li v-for="(imp, i) in a.impacts.slice(0, 3)" :key="i">{{ imp }}</li>
            </ul>
            <div class="expert__prop" v-if="a.propagations.length">
              ↳ {{ a.propagations.length }} propagation(s) : {{ a.propagations.map(p => p.to_domain).join(', ') }}
            </div>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="error" class="overlay overlay--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import CrisisGraph from '../components/CrisisGraph.vue'
import { getSimulation } from '../api/simulation'

const props = defineProps({ simulationId: { type: String, required: true } })
const router = useRouter()

const sim = ref(null)
const error = ref('')
let poll = null

const STATUS = {
  created: 'Créée', analyzing: 'Analyse experts', propagating: 'Propagation',
  narrating: 'Qualification', completed: 'Terminée', failed: 'Échec',
}
const statusLabel = computed(() => (sim.value ? STATUS[sim.value.status] : '—'))
const running = computed(() => sim.value && !['completed', 'failed'].includes(sim.value.status))
const progressText = computed(() => statusLabel.value + '…')

const analyses = computed(() => sim.value?.expert_analyses || [])
const chains = computed(() => sim.value?.propagation_chains || [])
const graphNodes = computed(() => sim.value?.propagated_graph?.nodes || [])
const graphEdges = computed(() => sim.value?.propagated_graph?.edges || [])

const DOMAIN_COLORS = {
  cybersecurite: '#e63946', sante: '#2a9d8f', rh: '#e9c46a', juridique: '#8d99ae',
  finance: '#457b9d', communication: '#f4a261', geopolitique: '#a44a3f',
  operationnel: '#6a4c93', technique: '#264653', resilience: '#b5838d',
}
function domainColor(d) { return DOMAIN_COLORS[d] || '#adb5bd' }
function sevColor(s) {
  const c = ['#6b7280', '#2a9d8f', '#e9c46a', '#f4a261', '#e76f51', '#e63946']
  return c[s || 0] || '#6b7280'
}

async function load() {
  try {
    const res = await getSimulation(props.simulationId)
    sim.value = res.data
    if (sim.value.status === 'failed') error.value = sim.value.error || 'Simulation en échec.'
    if (!running.value && poll) { clearInterval(poll); poll = null }
  } catch (e) {
    error.value = e?.message || 'Simulation introuvable.'
    if (poll) { clearInterval(poll); poll = null }
  }
}

function goBack() { router.back() }

function goTrajectories() {
  router.push({ name: 'CrisisTrajectories', params: { simulationId: props.simulationId } })
}

onMounted(() => {
  load()
  poll = setInterval(load, 2000)
})
onUnmounted(() => { if (poll) clearInterval(poll) })
</script>

<style scoped>
.sim-view { min-height: 100vh; background: #0f1115; color: #e8eaed; display: flex; flex-direction: column; }
.sim-view__header { display: flex; align-items: center; gap: 16px; padding: 14px 24px; border-bottom: 1px solid #23262c; }
.back { background: none; border: none; color: #9aa0a6; cursor: pointer; font-size: 14px; }
.back:hover { color: #e8eaed; }
.sim-view__title { flex: 1; display: flex; align-items: center; gap: 10px; }
.brand { font-weight: 800; letter-spacing: 2px; }
.sep { color: #3a3d43; }

.progress { display: flex; align-items: center; gap: 12px; padding: 12px 24px; color: #b8bcc4; }
.progress__spinner { width: 16px; height: 16px; border: 2px solid #2a2d33; border-top-color: #e63946; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.sim-view__body { flex: 1; display: grid; grid-template-columns: 1fr 380px; }
.sim-view__panel { padding: 16px; min-height: 0; }
.sim-view__side { border-left: 1px solid #23262c; padding: 18px; overflow-y: auto; max-height: calc(100vh - 60px); }
.side-block { margin-bottom: 24px; }
.side-block h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.6px; color: #9aa0a6; margin: 0 0 10px; }
.muted { color: #6b7280; font-size: 13px; }

.chain { background: #1a1d23; border: 1px solid #2a2d33; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.chain__path { font-size: 13px; font-weight: 600; line-height: 1.4; }
.arrow { color: #e63946; }
.chain__meta { display: flex; gap: 8px; align-items: center; margin: 6px 0; font-size: 11px; }
.chain__sev { color: #fff; padding: 1px 7px; border-radius: 10px; }
.chain__multi { color: #b5838d; }
.chain__w { color: #9aa0a6; }
.chain__narr { font-size: 12px; color: #cdd0d6; line-height: 1.4; }

.expert { background: #1a1d23; border: 1px solid #2a2d33; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.expert__head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.expert__dot { width: 10px; height: 10px; border-radius: 50%; }
.expert__label { font-weight: 600; font-size: 13px; flex: 1; }
.expert__sev { font-size: 11px; color: #9aa0a6; }
.expert__impacts { margin: 4px 0; padding-left: 16px; font-size: 12px; color: #cdd0d6; }
.expert__impacts li { margin: 2px 0; }
.expert__prop { font-size: 12px; color: #f4a261; margin-top: 4px; }

.badge { font-size: 11px; padding: 3px 9px; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.4px; }
.badge--completed { background: #14432f; color: #5ee0a0; }
.badge--failed { background: #4a1620; color: #ff8fab; }
.badge--analyzing, .badge--propagating, .badge--narrating, .badge--created { background: #2a2d33; color: #b8bcc4; }
.btn-primary { background: #e63946; border: none; color: #fff; border-radius: 8px; padding: 7px 14px; cursor: pointer; font-weight: 600; font-size: 13px; }

.overlay { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(15,17,21,.7); }
.overlay--error { color: #ff8fab; }

@media (max-width: 900px) { .sim-view__body { grid-template-columns: 1fr; } .sim-view__side { border-left: none; border-top: 1px solid #23262c; } }
</style>
