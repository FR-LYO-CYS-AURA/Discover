<template>
  <div class="intake">
    <header class="intake__header">
      <AppBrand tag="Simulation de risques, crises & exercices" />
      <router-link class="header-link" :to="{ name: 'Simulations' }">Mes simulations →</router-link>
    </header>

    <main class="intake__main">
      <section class="intake__form">
        <h1>Décrivez la situation de crise</h1>
        <p class="intake__hint">
          Décrivez librement la situation. DISCOVER extrait automatiquement le graphe
          de crise : actifs, acteurs et interdépendances (support des effets domino).
        </p>

        <div class="referentiel">
          <span class="referentiel__label">Partir d'un scénario du référentiel (optionnel)</span>
          <div class="referentiel__row">
            <select v-model="selectedCategory" @change="onCategoryChange">
              <option value="">— Catégorie d'aléa —</option>
              <option v-for="c in refCategories" :key="c.id" :value="c.id">{{ c.label }}</option>
            </select>
            <select v-model="selectedRefScenario" :disabled="!refScenarios.length">
              <option value="">— Scénario —</option>
              <option v-for="s in refScenarios" :key="s.id" :value="s.id">{{ s.type }}</option>
            </select>
            <button class="btn-ghost" :disabled="!selectedRefScenario" @click="loadRefScenario">Charger</button>
          </div>
        </div>

        <label class="field">
          <span class="field__label">Titre (optionnel)</span>
          <input v-model="title" type="text" placeholder="Ex. Cyberattaque hôpitaux — G7" />
        </label>

        <label class="field">
          <span class="field__label">Description de la crise *</span>
          <textarea
            v-model="description"
            rows="9"
            placeholder="Ex. Une cyberattaque par rançongiciel paralyse le système d'information de plusieurs établissements de santé pendant le sommet du G7. Les blocs opératoires sont perturbés, les dossiers patients inaccessibles..."
          ></textarea>
        </label>

        <label class="field">
          <span class="field__label">Contexte additionnel (optionnel)</span>
          <textarea
            v-model="context"
            rows="3"
            placeholder="Contraintes, périmètre, secteur, obligations réglementaires..."
          ></textarea>
        </label>

        <button class="btn-primary" :disabled="loading || !description.trim()" @click="submit">
          <span v-if="!loading">Générer le graphe de crise</span>
          <span v-else>Extraction en cours…</span>
        </button>

        <p v-if="error" class="intake__error">{{ error }}</p>
      </section>

      <aside class="intake__history">
        <h2>Scénarios récents</h2>
        <div v-if="scenarios.length === 0" class="history-empty">Aucun scénario pour l'instant.</div>
        <ul class="history-list">
          <li v-for="s in scenarios" :key="s.scenario_id" class="history-item">
            <div class="history-item__body" @click="open(s.scenario_id)">
              <div class="history-item__title">{{ s.title }}</div>
              <div class="history-item__meta">
                <span :class="['badge', 'badge--' + s.status]">{{ statusLabel(s.status) }}</span>
                <span class="history-item__counts">{{ s.node_count }} noeuds · {{ s.edge_count }} arêtes</span>
              </div>
            </div>
            <div class="history-item__row">
              <button class="mini" @click.stop="toggleSims(s.scenario_id)">
                {{ expanded[s.scenario_id] ? '▾' : '▸' }} Simulations
              </button>
              <button class="history-item__del" @click.stop="remove(s.scenario_id)" title="Supprimer">×</button>
            </div>
            <ul v-if="expanded[s.scenario_id]" class="sim-list">
              <li v-if="(sims[s.scenario_id] || []).length === 0" class="sim-empty">Aucune simulation.</li>
              <li v-for="sim in sims[s.scenario_id] || []" :key="sim.simulation_id" class="sim-item">
                <span :class="['dot', 'dot--' + sim.status]"></span>
                <span class="sim-item__id">{{ shortId(sim.simulation_id) }}</span>
                <button class="mini mini--link" @click.stop="goSim(sim.simulation_id)">Simulation</button>
                <button class="mini mini--link" @click.stop="goTraj(sim.simulation_id)">Trajectoires</button>
              </li>
            </ul>
          </li>
        </ul>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createScenario, listScenarios, deleteScenario } from '../api/scenario'
import { listSimulations } from '../api/simulation'
import AppBrand from '../components/AppBrand.vue'
import { getReferentielCategories, getReferentielScenarios, getReferentielScenario } from '../api/referentiel'

const router = useRouter()
const title = ref('')
const description = ref('')
const context = ref('')
const loading = ref(false)
const error = ref('')
const scenarios = ref([])

// --- Référentiel de risques (intake assisté) ---
const refCategories = ref([])
const refScenarios = ref([])
const selectedCategory = ref('')
const selectedRefScenario = ref('')

async function fetchReferentiel() {
  try {
    const res = await getReferentielCategories()
    refCategories.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

async function onCategoryChange() {
  selectedRefScenario.value = ''
  refScenarios.value = []
  if (!selectedCategory.value) return
  try {
    const res = await getReferentielScenarios(selectedCategory.value)
    refScenarios.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

async function loadRefScenario() {
  if (!selectedRefScenario.value) return
  try {
    const res = await getReferentielScenario(selectedRefScenario.value)
    const scn = res.data
    title.value = `${scn.type}`
    description.value = `${scn.type} — ${scn.description}. Points sensibles : ${(scn.tags || []).join(', ')}.`
  } catch (e) {
    console.error(e)
  }
}

const STATUS_LABELS = {
  created: 'Créé',
  extracting: 'Extraction',
  graph_ready: 'Prêt',
  failed: 'Échec',
}
function statusLabel(s) { return STATUS_LABELS[s] || s }

async function fetchScenarios() {
  try {
    const res = await listScenarios(30)
    scenarios.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const res = await createScenario({
      title: title.value.trim(),
      description: description.value.trim(),
      context: context.value.trim() || undefined,
      referentiel_scenario_id: selectedRefScenario.value || undefined,
    })
    const id = res.data.scenario_id
    router.push({ name: 'CrisisGraph', params: { scenarioId: id } })
  } catch (e) {
    error.value = e?.message || "Échec de l'extraction du graphe de crise."
  } finally {
    loading.value = false
  }
}

function open(id) {
  router.push({ name: 'CrisisGraph', params: { scenarioId: id } })
}

// --- Historique des simulations par scénario ---
const expanded = reactive({})
const sims = reactive({})

async function toggleSims(scenarioId) {
  expanded[scenarioId] = !expanded[scenarioId]
  if (expanded[scenarioId] && !sims[scenarioId]) {
    try {
      const res = await listSimulations(scenarioId)
      sims[scenarioId] = res.data || []
    } catch (e) {
      sims[scenarioId] = []
    }
  }
}
function shortId(id) { return (id || '').replace('sim_', '').slice(0, 8) }
function goSim(id) { router.push({ name: 'CrisisSimulation', params: { simulationId: id } }) }
function goTraj(id) { router.push({ name: 'CrisisTrajectories', params: { simulationId: id } }) }

async function remove(id) {
  try {
    await deleteScenario(id)
    await fetchScenarios()
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchScenarios()
  fetchReferentiel()
})
</script>

<style scoped>
.intake { min-height: 100vh; background: var(--bg); color: var(--text); }
.intake__header {
  padding: 18px 32px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center;
}
.header-link { margin-left: auto; color: var(--link); text-decoration: none; font-size: 14px; }
.header-link:hover { color: var(--link-hover); }
.brand__name { font-weight: 800; letter-spacing: 2px; font-size: 20px; }
.brand__tag { margin-left: 14px; color: var(--text-muted); font-size: 13px; }

.intake__main {
  max-width: 1100px; margin: 0 auto; padding: 32px;
  display: grid; grid-template-columns: 1.6fr 1fr; gap: 28px;
}
.intake__form h1 { font-size: 24px; margin: 0 0 8px; }
.intake__hint { color: var(--text-muted); font-size: 14px; margin: 0 0 20px; line-height: 1.5; }

.field { display: block; margin-bottom: 16px; }
.field__label { display: block; font-size: 13px; color: var(--text-muted); margin-bottom: 6px; }
.field input, .field textarea {
  width: 100%; box-sizing: border-box;
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); padding: 10px 12px; font-size: 14px; font-family: inherit;
  resize: vertical;
}
.field input:focus, .field textarea:focus { outline: none; border-color: var(--link); }

.referentiel {
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 14px; margin-bottom: 18px;
}
.referentiel__label { display: block; font-size: 13px; color: var(--text-muted); margin-bottom: 8px; }
.referentiel__row { display: flex; gap: 8px; flex-wrap: wrap; }
.referentiel__row select {
  flex: 1; min-width: 140px; background: var(--bg); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); padding: 8px 10px; font-size: 13px; font-family: inherit;
}
.referentiel__row select:disabled { opacity: 0.5; }
.btn-ghost {
  background: var(--bg); border: 1px solid var(--border); color: var(--text);
  border-radius: 6px; padding: 8px 14px; cursor: pointer; font-size: 13px;
}
.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-primary {
  background: var(--accent); color: var(--on-accent); border: none; border-radius: 8px;
  padding: 12px 20px; font-size: 15px; font-weight: 600; cursor: pointer;
  width: 100%;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.intake__error { color: var(--danger); margin-top: 12px; font-size: 14px; }

.intake__history h2 { font-size: 16px; margin: 0 0 14px; }
.history-empty { color: var(--text-subtle); font-size: 14px; }
.history-list { list-style: none; padding: 0; margin: 0; }
.history-item {
  position: relative;
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 14px; margin-bottom: 10px;
}
.history-item:hover { border-color: var(--link); }
.history-item__body { cursor: pointer; }
.history-item__title { font-weight: 600; font-size: 14px; margin-bottom: 6px; padding-right: 20px; }
.history-item__meta { display: flex; align-items: center; gap: 10px; }
.history-item__counts { color: var(--text-muted); font-size: 12px; }
.history-item__row { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.history-item__del {
  background: none; border: none; color: var(--text-subtle); font-size: 18px; cursor: pointer; line-height: 1;
}
.mini { background: none; border: none; color: var(--text-muted); font-size: 12px; cursor: pointer; padding: 2px 4px; }
.mini:hover { color: var(--text); }
.mini--link { color: var(--link); }
.mini--link:hover { color: var(--link-hover); }
.sim-list { list-style: none; padding: 8px 0 0; margin: 6px 0 0; border-top: 1px solid var(--border); }
.sim-empty { color: var(--text-subtle); font-size: 12px; }
.sim-item { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 3px 0; }
.sim-item__id { color: var(--text-muted); font-family: monospace; flex: 1; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-subtle); }
.dot--completed { background: var(--success); }
.dot--failed { background: var(--danger); }
.dot--analyzing, .dot--propagating, .dot--narrating { background: var(--warning); }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.4px; }
.badge--graph_ready { background: var(--success-bg); color: var(--success); }
.badge--failed { background: var(--danger-bg); color: var(--danger); }
.badge--extracting, .badge--created { background: var(--border); color: var(--text-muted); }

@media (max-width: 860px) {
  .intake__main { grid-template-columns: 1fr; }
}
</style>
