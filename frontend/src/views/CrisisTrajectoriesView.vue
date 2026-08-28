<template>
  <div class="traj">
    <header class="traj__header">
      <button class="back" @click="goBack">← Retour</button>
      <div class="traj__title">
        <AppBrand /><span class="sep">/</span>
        <span>Trajectoires & scoring</span>
      </div>
      <CrisisStepper current="trajectories" :scenario-id="scenarioId" :simulation-id="simulationId" />
      <SimulationTabs :simulation-id="simulationId" current="trajectories" />
      <button v-if="trajectories.length" class="btn-ghost" @click="goReport">Rapport</button>
      <button v-if="status === 'none' || status === 'failed'" class="btn-primary"
              :disabled="generating" @click="launch">
        {{ generating ? 'Génération…' : 'Générer les trajectoires' }}
      </button>
    </header>

    <div v-if="status === 'generating' || generating" class="progress">
      <div class="progress__spinner"></div>
      <div>Génération des 4 trajectoires…</div>
    </div>

    <div v-if="trajectories.length" class="traj__body">
      <!-- Métriques (dont l'étape trajectoires) -->
      <section class="metrics-section" v-if="simMetrics && simMetrics.steps">
        <MetricsPanel :metrics="simMetrics" />
      </section>

      <!-- Décisions consolidées -->
      <section class="consolidated" v-if="consolidatedDecisions.length">
        <h3>Décisions prioritaires (consolidées)</h3>
        <div class="cons-list">
          <div v-for="(d, i) in consolidatedDecisions" :key="i" class="cons">
            <span class="cons__rank">{{ i + 1 }}</span>
            <div class="cons__bar"><div class="cons__fill" :style="{ width: d.max_effect + '%', background: idxColor(d.max_effect) }"></div></div>
            <div class="cons__txt">
              <span class="cons__type">{{ d.type === 'mitigation' ? 'M' : 'P' }}</span>
              {{ d.measure }}
              <span class="cons__dom">{{ d.domain_label }}</span>
              <span class="cons__score">{{ d.max_effect }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Heatmap domaine x trajectoire -->
      <section class="heatmap">
        <h3>Criticité par domaine et trajectoire</h3>
        <table>
          <thead>
            <tr>
              <th>Domaine</th>
              <th v-for="t in trajectories" :key="t.type">{{ t.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="dom in domains" :key="dom.key">
              <td class="dom">{{ dom.label }}</td>
              <td v-for="t in trajectories" :key="t.type"
                  class="cell" :style="cellStyle(t, dom.key)">
                {{ cellVal(t, dom.key) || '·' }}
              </td>
            </tr>
            <tr class="global-row">
              <td class="dom">Indice global</td>
              <td v-for="t in trajectories" :key="t.type" class="cell cell--global"
                  :style="{ background: idxColor(t.scores.global_index) }">
                {{ t.scores.global_index }}
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 4 branches côte à côte -->
      <section class="branches">
        <article v-for="t in trajectories" :key="t.type" class="branch">
          <div class="branch__head" :style="{ borderColor: idxColor(t.scores.global_index) }">
            <span class="branch__label">{{ t.label }}</span>
            <span class="branch__idx" :style="{ background: idxColor(t.scores.global_index) }">
              {{ t.scores.global_index }}/100
            </span>
          </div>
          <p class="branch__hypo">{{ t.hypothesis }}</p>
          <p class="branch__narr" v-if="t.narrative">{{ t.narrative }}</p>

          <div class="branch__section" v-if="t.key_bifurcations && t.key_bifurcations.length">
            <h4>Bascules clés</h4>
            <ul><li v-for="(b, i) in t.key_bifurcations" :key="i">{{ b }}</li></ul>
          </div>

          <div class="branch__section" v-if="t.decisions && t.decisions.length">
            <h4>Décisions prioritaires</h4>
            <div v-for="(d, i) in t.decisions.slice(0, 4)" :key="i" class="decision">
              <div class="decision__bar">
                <div class="decision__fill" :style="{ width: d.effect_score + '%', background: idxColor(d.effect_score) }"></div>
              </div>
              <div class="decision__txt">
                <span class="decision__type">{{ d.type === 'mitigation' ? 'M' : 'P' }}</span>
                {{ d.measure }} <span class="decision__score">{{ d.effect_score }}</span>
              </div>
            </div>
          </div>
        </article>
      </section>
    </div>

    <div v-if="error" class="overlay overlay--error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import CrisisStepper from '../components/CrisisStepper.vue'
import SimulationTabs from '../components/SimulationTabs.vue'
import MetricsPanel from '../components/MetricsPanel.vue'
import { getTrajectories, generateTrajectories, getTaskStatus, getSimulation } from '../api/simulation'
import { idxColor, heatCell } from '@/styles/palette'

const props = defineProps({ simulationId: { type: String, required: true } })
const router = useRouter()

const status = ref('none')
const trajectories = ref([])
const generating = ref(false)
const error = ref('')
const scenarioId = ref('')
const simMetrics = ref(null)
let poll = null

const domains = computed(() => {
  const map = {}
  for (const t of trajectories.value) {
    for (const [key, v] of Object.entries(t.scores.domain_scores || {})) {
      if (!map[key]) map[key] = v.label || key
    }
  }
  return Object.entries(map).map(([key, label]) => ({ key, label }))
})

const consolidatedDecisions = computed(() => {
  const agg = {}
  for (const t of trajectories.value) {
    for (const d of (t.decisions || [])) {
      const key = d.domain + '|' + (d.measure || '').toLowerCase()
      if (!agg[key]) {
        agg[key] = { measure: d.measure, type: d.type, domain_label: d.domain_label, max_effect: d.effect_score, trajectories: [t.type] }
      } else {
        agg[key].max_effect = Math.max(agg[key].max_effect, d.effect_score)
        if (!agg[key].trajectories.includes(t.type)) agg[key].trajectories.push(t.type)
      }
    }
  }
  return Object.values(agg).sort((a, b) => b.max_effect - a.max_effect).slice(0, 8)
})

function cellVal(t, dom) {
  const d = t.scores.domain_scores[dom]
  return d ? d.criticality : null
}
function cellStyle(t, dom) {
  return heatCell(cellVal(t, dom))
}

async function load() {
  try {
    const res = await getTrajectories(props.simulationId)
    status.value = res.data.trajectories_status
    trajectories.value = res.data.trajectories || []
    if (status.value !== 'generating' && poll) { clearInterval(poll); poll = null; generating.value = false }
    // rafraîchir les métriques (l'étape 'trajectoires' y est ajoutée après génération)
    if (status.value === 'completed') {
      try { simMetrics.value = (await getSimulation(props.simulationId)).data.metrics || simMetrics.value } catch (e) { /* ignore */ }
    }
  } catch (e) {
    error.value = e?.message || 'Simulation introuvable.'
  }
}

async function launch() {
  generating.value = true
  error.value = ''
  try {
    const res = await generateTrajectories(props.simulationId)
    const taskId = res.data.task_id
    poll = setInterval(async () => {
      const st = await getTaskStatus(taskId)
      if (['completed', 'failed'].includes(st.data.status)) {
        clearInterval(poll); poll = null
        if (st.data.status === 'failed') error.value = st.data.error || 'Échec de la génération.'
        await load()
        generating.value = false
      }
    }, 2000)
  } catch (e) {
    error.value = e?.message || 'Échec du lancement.'
    generating.value = false
  }
}

function goBack() { router.back() }

function goReport() {
  router.push({ name: 'CrisisReport', params: { simulationId: props.simulationId } })
}

onMounted(async () => {
  try {
    const s = await getSimulation(props.simulationId)
    scenarioId.value = s.data.scenario_id || ''
    simMetrics.value = s.data.metrics || null
  } catch (e) { /* non bloquant */ }
  load()
})
onUnmounted(() => { if (poll) clearInterval(poll) })
</script>

<style scoped>
.traj { min-height: 100vh; background: var(--bg); color: var(--text); }
.traj__header { display: flex; align-items: center; gap: 16px; padding: 14px 24px; border-bottom: 1px solid var(--border); }
.back { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 14px; }
.back:hover { color: var(--text); }
.traj__title { flex: 1; display: flex; align-items: center; gap: 10px; }
.brand { font-weight: 800; letter-spacing: 2px; }
.sep { color: var(--text-subtle); }
.btn-primary { background: var(--accent); border: none; color: var(--on-accent); border-radius: 8px; padding: 8px 16px; cursor: pointer; font-weight: 600; font-size: 13px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 8px 14px; cursor: pointer; font-size: 13px; }

.consolidated { margin-bottom: 28px; }
.metrics-section { margin-bottom: 28px; }.cons-list { display: flex; flex-direction: column; gap: 6px; }
.cons { display: flex; align-items: center; gap: 10px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; }
.cons__rank { width: 20px; text-align: center; color: var(--text-muted); font-weight: 700; }
.cons__bar { width: 90px; height: 5px; background: var(--border); border-radius: 3px; overflow: hidden; flex-shrink: 0; }
.cons__fill { height: 100%; }
.cons__txt { font-size: 13px; color: var(--text); flex: 1; }
.cons__type { display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; background: var(--border); border-radius: 3px; font-size: 10px; margin-right: 6px; }
.cons__dom { color: var(--text-muted); font-size: 11px; margin-left: 8px; }
.cons__score { color: var(--danger); float: right; font-weight: 600; }

.progress { display: flex; align-items: center; gap: 12px; padding: 40px 24px; color: var(--text-muted); justify-content: center; }
.progress__spinner { width: 18px; height: 18px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.traj__body { padding: 24px; max-width: 1400px; margin: 0 auto; }

.heatmap { margin-bottom: 28px; }
.heatmap h3, .branch__section h4 { font-size: 13px; text-transform: uppercase; letter-spacing: .5px; color: var(--text-muted); margin: 0 0 10px; }
.heatmap table { border-collapse: collapse; width: 100%; font-size: 13px; }
.heatmap th { text-align: center; padding: 8px; color: var(--text-muted); border-bottom: 1px solid var(--border); }
.heatmap th:first-child, .dom { text-align: left; }
.cell { text-align: center; padding: 8px 10px; font-weight: 600; border: 1px solid var(--surface-alt); }
.dom { padding: 8px 10px; color: var(--text); }
.cell--global { font-size: 15px; }
.global-row td { border-top: 2px solid var(--border); }

.branches { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.branch { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px; }
.branch__head { display: flex; align-items: center; justify-content: space-between; border-left: 3px solid; padding-left: 8px; margin-bottom: 8px; }
.branch__label { font-weight: 700; font-size: 15px; }
.branch__idx { color: var(--on-accent); font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.branch__hypo { font-size: 12px; color: var(--text-muted); font-style: italic; margin: 0 0 8px; }
.branch__narr { font-size: 13px; color: var(--text); line-height: 1.45; margin: 0 0 10px; }
.branch__section { margin-top: 10px; }
.branch__section ul { margin: 0; padding-left: 16px; font-size: 12px; color: var(--text); }
.branch__section li { margin: 2px 0; }
.decision { margin-bottom: 8px; }
.decision__bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; margin-bottom: 3px; }
.decision__fill { height: 100%; }
.decision__txt { font-size: 12px; color: var(--text); }
.decision__type { display: inline-block; width: 15px; height: 15px; line-height: 15px; text-align: center; background: var(--border); border-radius: 3px; font-size: 10px; margin-right: 4px; }
.decision__score { color: var(--text-muted); float: right; }

.overlay { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--overlay); }
.overlay--error { color: var(--danger); }

@media (max-width: 1000px) { .branches { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .branches { grid-template-columns: 1fr; } }
</style>
