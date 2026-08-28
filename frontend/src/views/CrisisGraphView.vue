<template>
  <div class="graph-view">
    <header class="graph-view__header">
      <button class="back" @click="goHome">← Retour</button>
      <div class="graph-view__title">
        <AppBrand />
        <span class="sep">/</span>
        <span class="scn-title">{{ scenario?.title || 'Scénario' }}</span>
      </div>
      <CrisisStepper v-if="!simContext" current="graph" :scenario-id="scenarioId" />
      <SimulationTabs v-else :simulation-id="simContext" current="graph" />
      <div class="graph-view__actions">
        <span v-if="scenario" :class="['badge', 'badge--' + scenario.status]">{{ statusLabel(scenario.status) }}</span>
        <button class="btn-ghost" :disabled="reextracting" @click="reextract">
          {{ reextracting ? 'Ré-extraction…' : 'Ré-extraire' }}
        </button>
        <button class="btn-primary" :disabled="simulating || !nodes.length" @click="launchSimulation">
          {{ simulating ? 'Lancement…' : 'Lancer la simulation' }}
        </button>
      </div>
    </header>

    <div class="graph-view__body">
      <div class="graph-view__panel">
        <CrisisGraph :nodes="nodes" :edges="edges" />
      </div>

      <aside class="graph-view__side">
        <div class="side-block">
          <h3>Synthèse</h3>
          <p class="summary">{{ scenario?.analysis_summary || '—' }}</p>
        </div>
        <div class="side-block side-stats">
          <div class="stat"><span class="stat__num">{{ nodes.length }}</span><span class="stat__lbl">noeuds</span></div>
          <div class="stat"><span class="stat__num">{{ edges.length }}</span><span class="stat__lbl">arêtes</span></div>
          <div class="stat"><span class="stat__num">{{ domainCount }}</span><span class="stat__lbl">domaines</span></div>
        </div>

        <div class="side-block" v-if="extractionMetrics">
          <MetricsPanel :metrics="extractionMetrics" />
        </div>
        <div class="side-block">
          <h3>Description</h3>
          <p class="desc">{{ scenario?.description }}</p>
        </div>
        <div class="side-block next">
          <p>Phase suivante : société d'agents experts &amp; effets domino.</p>
        </div>
      </aside>
    </div>

    <div v-if="loading" class="overlay">Chargement…</div>
    <div v-if="error" class="overlay overlay--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import CrisisGraph from '../components/CrisisGraph.vue'
import CrisisStepper from '../components/CrisisStepper.vue'
import SimulationTabs from '../components/SimulationTabs.vue'
import MetricsPanel from '../components/MetricsPanel.vue'
import { getScenario, extractScenario } from '../api/scenario'
import { runSimulation } from '../api/simulation'

const props = defineProps({ scenarioId: { type: String, required: true } })
const router = useRouter()
const route = useRoute()

const scenario = ref(null)
const loading = ref(true)
const error = ref('')
const reextracting = ref(false)
const simulating = ref(false)

// Contexte simulation (navigation par onglets depuis une simulation)
const simContext = computed(() => route.query.sim || '')

// Métriques d'extraction, mises au format MetricsPanel
const extractionMetrics = computed(() => {
  const ex = scenario.value?.metrics?.extraction
  if (!ex) return null
  return {
    total_duration_s: ex.duration_s,
    model: ex.model,
    steps: [{ name: 'extraction', duration_s: ex.duration_s, llm_calls: ex.llm_calls, tokens_total: ex.tokens_total }],
    totals: { llm_calls: ex.llm_calls, tokens_total: ex.tokens_total, cost: ex.cost },
  }
})

const nodes = computed(() => scenario.value?.nodes || [])
const edges = computed(() => scenario.value?.edges || [])
const domainCount = computed(() => new Set(nodes.value.map(n => n.domain)).size)

const STATUS_LABELS = {
  created: 'Créé', extracting: 'Extraction', graph_ready: 'Prêt', failed: 'Échec',
}
function statusLabel(s) { return STATUS_LABELS[s] || s }

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await getScenario(props.scenarioId)
    scenario.value = res.data
    if (scenario.value.status === 'failed' && scenario.value.error) {
      error.value = scenario.value.error
    }
  } catch (e) {
    error.value = e?.message || 'Scénario introuvable.'
  } finally {
    loading.value = false
  }
}

async function reextract() {
  reextracting.value = true
  error.value = ''
  try {
    const res = await extractScenario(props.scenarioId)
    scenario.value = res.data
  } catch (e) {
    error.value = e?.message || "Échec de la ré-extraction."
  } finally {
    reextracting.value = false
  }
}

function goHome() { router.push({ name: 'Home' }) }

async function launchSimulation() {
  simulating.value = true
  error.value = ''
  try {
    const res = await runSimulation(props.scenarioId)
    router.push({ name: 'CrisisSimulation', params: { simulationId: res.data.simulation_id } })
  } catch (e) {
    error.value = e?.message || 'Échec du lancement de la simulation.'
    simulating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.graph-view { min-height: 100vh; background: var(--bg); color: var(--text); display: flex; flex-direction: column; }
.graph-view__header {
  display: flex; align-items: center; gap: 16px;
  padding: 14px 24px; border-bottom: 1px solid var(--border);
}
.back { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 14px; }
.back:hover { color: var(--text); }
.graph-view__title { flex: 1; display: flex; align-items: center; gap: 10px; }
.sep { color: var(--text-subtle); }
.scn-title { color: var(--text-muted); }
.graph-view__actions { display: flex; align-items: center; gap: 12px; }
.btn-ghost {
  background: var(--surface); border: 1px solid var(--border); color: var(--text);
  border-radius: 8px; padding: 8px 14px; cursor: pointer; font-size: 13px;
}
.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary {
  background: var(--accent); border: none; color: var(--on-accent);
  border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 13px; font-weight: 600;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.graph-view__body { flex: 1; display: grid; grid-template-columns: 1fr 320px; gap: 0; }
.graph-view__panel { padding: 16px; min-height: 0; }
.graph-view__side { border-left: 1px solid var(--border); padding: 20px; overflow-y: auto; }

.side-block { margin-bottom: 22px; }
.side-block h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.6px; color: var(--text-muted); margin: 0 0 8px; }
.summary, .desc { font-size: 14px; line-height: 1.55; color: var(--text); margin: 0; }
.side-stats { display: flex; gap: 14px; }
.stat { flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; text-align: center; }
.stat__num { display: block; font-size: 22px; font-weight: 700; }
.stat__lbl { font-size: 12px; color: var(--text-muted); }
.next { color: var(--text-subtle); font-size: 13px; font-style: italic; }

.badge { font-size: 11px; padding: 3px 9px; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.4px; }
.badge--graph_ready { background: var(--success-bg); color: var(--success); }
.badge--failed { background: var(--danger-bg); color: var(--danger); }
.badge--extracting, .badge--created { background: var(--border); color: var(--text-muted); }

.overlay {
  position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
  background: var(--overlay); color: var(--text); font-size: 16px;
}
.overlay--error { color: var(--danger); }

@media (max-width: 860px) {
  .graph-view__body { grid-template-columns: 1fr; }
  .graph-view__side { border-left: none; border-top: 1px solid var(--border); }
}
</style>
