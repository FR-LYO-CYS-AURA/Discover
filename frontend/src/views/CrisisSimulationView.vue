<template>
  <div class="sim-view">
    <header class="sim-view__header">
      <button class="back" @click="goBack">← Retour</button>
      <div class="sim-view__title">
        <AppBrand /><span class="sep">/</span>
        <span>Simulation de crise</span>
      </div>
      <CrisisStepper current="simulation" :scenario-id="scenarioId" :simulation-id="simulationId" />
      <SimulationTabs :simulation-id="simulationId" current="simulation" />
      <span :class="['badge', 'badge--' + (sim ? sim.status : 'created')]">{{ statusLabel }}</span>
      <button v-if="sim && sim.status === 'completed'" class="btn-primary" @click="goTrajectories">
        Trajectoires &amp; scoring →
      </button>
    </header>

    <div class="sim-view__content">
      <LoadingScreen :visible="running" :label="progressText" />

      <div class="sim-view__body" v-if="sim">
      <div class="sim-view__panel">
        <CrisisGraph :nodes="graphNodes" :edges="graphEdges" :impact-mode="true" />
      </div>

      <aside class="sim-view__side">
        <div class="side-block" v-if="sim && sim.metrics && sim.metrics.steps">
          <MetricsPanel :metrics="sim.metrics" />
        </div>
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
    </div>

    <div v-if="error" class="overlay overlay--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import CrisisGraph from '../components/CrisisGraph.vue'
import CrisisStepper from '../components/CrisisStepper.vue'
import SimulationTabs from '../components/SimulationTabs.vue'
import MetricsPanel from '../components/MetricsPanel.vue'
import LoadingScreen from '../components/LoadingScreen.vue'
import { getSimulation } from '../api/simulation'
import { domainColor, sevColor } from '@/styles/palette'

const props = defineProps({ simulationId: { type: String, required: true } })
const router = useRouter()

const sim = ref(null)
const error = ref('')
let poll = null

const scenarioId = computed(() => sim.value?.scenario_id || '')

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
.sim-view { min-height: 100vh; background: var(--bg); color: var(--text); display: flex; flex-direction: column; }
.sim-view__header { display: flex; align-items: center; gap: 16px; padding: 14px 24px; border-bottom: 1px solid var(--border); }
.back { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 14px; }
.back:hover { color: var(--text); }
.sim-view__title { flex: 1; display: flex; align-items: center; gap: 10px; }
.sep { color: var(--text-subtle); }

.sim-view__content { position: relative; flex: 1; min-height: 320px; }

.sim-view__body { flex: 1; display: grid; grid-template-columns: 1fr 380px; }
.sim-view__panel { padding: 16px; min-height: 0; }
.sim-view__side { border-left: 1px solid var(--border); padding: 18px; overflow-y: auto; max-height: calc(100vh - 60px); }
.side-block { margin-bottom: 24px; }
.side-block h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.6px; color: var(--text-muted); margin: 0 0 10px; }
.muted { color: var(--text-subtle); font-size: 13px; }

.chain { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.chain__path { font-size: 13px; font-weight: 600; line-height: 1.4; }
.arrow { color: var(--accent); }
.chain__meta { display: flex; gap: 8px; align-items: center; margin: 6px 0; font-size: 11px; }
.chain__sev { color: var(--on-accent); padding: 1px 7px; border-radius: 10px; }
.chain__multi { color: var(--text-muted); }
.chain__w { color: var(--text-muted); }
.chain__narr { font-size: 12px; color: var(--text); line-height: 1.4; }

.expert { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.expert__head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.expert__dot { width: 10px; height: 10px; border-radius: 50%; }
.expert__label { font-weight: 600; font-size: 13px; flex: 1; }
.expert__sev { font-size: 11px; color: var(--text-muted); }
.expert__impacts { margin: 4px 0; padding-left: 16px; font-size: 12px; color: var(--text); }
.expert__impacts li { margin: 2px 0; }
.expert__prop { font-size: 12px; color: var(--brand-orange-deep); margin-top: 4px; }

.badge { font-size: 11px; padding: 3px 9px; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.4px; }
.badge--completed { background: var(--success-bg); color: var(--success); }
.badge--failed { background: var(--danger-bg); color: var(--danger); }
.badge--analyzing, .badge--propagating, .badge--narrating, .badge--created { background: var(--border); color: var(--text-muted); }
.btn-primary { background: var(--accent); border: none; color: var(--on-accent); border-radius: 8px; padding: 7px 14px; cursor: pointer; font-weight: 600; font-size: 13px; }

.overlay { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--overlay); }
.overlay--error { color: var(--danger); }

@media (max-width: 900px) { .sim-view__body { grid-template-columns: 1fr; } .sim-view__side { border-left: none; border-top: 1px solid var(--border); } }
</style>
