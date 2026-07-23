<template>
  <div class="graph-view">
    <header class="graph-view__header">
      <button class="back" @click="goHome">← Retour</button>
      <div class="graph-view__title">
        <span class="brand">DISCOVER</span>
        <span class="sep">/</span>
        <span class="scn-title">{{ scenario?.title || 'Scénario' }}</span>
      </div>
      <CrisisStepper current="graph" :scenario-id="scenarioId" />
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
import { useRouter } from 'vue-router'
import CrisisGraph from '../components/CrisisGraph.vue'
import CrisisStepper from '../components/CrisisStepper.vue'
import { getScenario, extractScenario } from '../api/scenario'
import { runSimulation } from '../api/simulation'

const props = defineProps({ scenarioId: { type: String, required: true } })
const router = useRouter()

const scenario = ref(null)
const loading = ref(true)
const error = ref('')
const reextracting = ref(false)
const simulating = ref(false)

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
.graph-view { min-height: 100vh; background: #0f1115; color: #e8eaed; display: flex; flex-direction: column; }
.graph-view__header {
  display: flex; align-items: center; gap: 16px;
  padding: 14px 24px; border-bottom: 1px solid #23262c;
}
.back { background: none; border: none; color: #9aa0a6; cursor: pointer; font-size: 14px; }
.back:hover { color: #e8eaed; }
.graph-view__title { flex: 1; display: flex; align-items: center; gap: 10px; }
.brand { font-weight: 800; letter-spacing: 2px; }
.sep { color: #3a3d43; }
.scn-title { color: #b8bcc4; }
.graph-view__actions { display: flex; align-items: center; gap: 12px; }
.btn-ghost {
  background: #1a1d23; border: 1px solid #2a2d33; color: #e8eaed;
  border-radius: 8px; padding: 8px 14px; cursor: pointer; font-size: 13px;
}
.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary {
  background: #e63946; border: none; color: #fff;
  border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 13px; font-weight: 600;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.graph-view__body { flex: 1; display: grid; grid-template-columns: 1fr 320px; gap: 0; }
.graph-view__panel { padding: 16px; min-height: 0; }
.graph-view__side { border-left: 1px solid #23262c; padding: 20px; overflow-y: auto; }

.side-block { margin-bottom: 22px; }
.side-block h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.6px; color: #9aa0a6; margin: 0 0 8px; }
.summary, .desc { font-size: 14px; line-height: 1.55; color: #cdd0d6; margin: 0; }
.side-stats { display: flex; gap: 14px; }
.stat { flex: 1; background: #1a1d23; border: 1px solid #2a2d33; border-radius: 8px; padding: 12px; text-align: center; }
.stat__num { display: block; font-size: 22px; font-weight: 700; }
.stat__lbl { font-size: 12px; color: #9aa0a6; }
.next { color: #6b7280; font-size: 13px; font-style: italic; }

.badge { font-size: 11px; padding: 3px 9px; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.4px; }
.badge--graph_ready { background: #14432f; color: #5ee0a0; }
.badge--failed { background: #4a1620; color: #ff8fab; }
.badge--extracting, .badge--created { background: #2a2d33; color: #b8bcc4; }

.overlay {
  position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
  background: rgba(15, 17, 21, 0.7); color: #e8eaed; font-size: 16px;
}
.overlay--error { color: #ff8fab; }

@media (max-width: 860px) {
  .graph-view__body { grid-template-columns: 1fr; }
  .graph-view__side { border-left: none; border-top: 1px solid #23262c; }
}
</style>
