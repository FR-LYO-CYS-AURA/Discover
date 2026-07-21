<template>
  <div class="intake">
    <header class="intake__header">
      <div class="brand">
        <span class="brand__name">DISCOVER</span>
        <span class="brand__tag">Simulation de risques, crises & exercices</span>
      </div>
    </header>

    <main class="intake__main">
      <section class="intake__form">
        <h1>Décrivez la situation de crise</h1>
        <p class="intake__hint">
          Décrivez librement la situation. DISCOVER extrait automatiquement le graphe
          de crise : actifs, acteurs et interdépendances (support des effets domino).
        </p>

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
          <li v-for="s in scenarios" :key="s.scenario_id" class="history-item" @click="open(s.scenario_id)">
            <div class="history-item__title">{{ s.title }}</div>
            <div class="history-item__meta">
              <span :class="['badge', 'badge--' + s.status]">{{ statusLabel(s.status) }}</span>
              <span class="history-item__counts">{{ s.node_count }} noeuds · {{ s.edge_count }} arêtes</span>
            </div>
            <button class="history-item__del" @click.stop="remove(s.scenario_id)" title="Supprimer">×</button>
          </li>
        </ul>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createScenario, listScenarios, deleteScenario } from '../api/scenario'

const router = useRouter()
const title = ref('')
const description = ref('')
const context = ref('')
const loading = ref(false)
const error = ref('')
const scenarios = ref([])

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

async function remove(id) {
  try {
    await deleteScenario(id)
    await fetchScenarios()
  } catch (e) {
    console.error(e)
  }
}

onMounted(fetchScenarios)
</script>

<style scoped>
.intake { min-height: 100vh; background: #0f1115; color: #e8eaed; }
.intake__header {
  padding: 18px 32px; border-bottom: 1px solid #23262c;
  display: flex; align-items: center;
}
.brand__name { font-weight: 800; letter-spacing: 2px; font-size: 20px; }
.brand__tag { margin-left: 14px; color: #9aa0a6; font-size: 13px; }

.intake__main {
  max-width: 1100px; margin: 0 auto; padding: 32px;
  display: grid; grid-template-columns: 1.6fr 1fr; gap: 28px;
}
.intake__form h1 { font-size: 24px; margin: 0 0 8px; }
.intake__hint { color: #9aa0a6; font-size: 14px; margin: 0 0 20px; line-height: 1.5; }

.field { display: block; margin-bottom: 16px; }
.field__label { display: block; font-size: 13px; color: #b8bcc4; margin-bottom: 6px; }
.field input, .field textarea {
  width: 100%; box-sizing: border-box;
  background: #1a1d23; border: 1px solid #2a2d33; border-radius: 8px;
  color: #e8eaed; padding: 10px 12px; font-size: 14px; font-family: inherit;
  resize: vertical;
}
.field input:focus, .field textarea:focus { outline: none; border-color: #457b9d; }

.btn-primary {
  background: #e63946; color: #fff; border: none; border-radius: 8px;
  padding: 12px 20px; font-size: 15px; font-weight: 600; cursor: pointer;
  width: 100%;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.intake__error { color: #ff8fab; margin-top: 12px; font-size: 14px; }

.intake__history h2 { font-size: 16px; margin: 0 0 14px; }
.history-empty { color: #6b7280; font-size: 14px; }
.history-list { list-style: none; padding: 0; margin: 0; }
.history-item {
  position: relative;
  background: #1a1d23; border: 1px solid #2a2d33; border-radius: 8px;
  padding: 12px 14px; margin-bottom: 10px; cursor: pointer;
}
.history-item:hover { border-color: #457b9d; }
.history-item__title { font-weight: 600; font-size: 14px; margin-bottom: 6px; padding-right: 20px; }
.history-item__meta { display: flex; align-items: center; gap: 10px; }
.history-item__counts { color: #9aa0a6; font-size: 12px; }
.history-item__del {
  position: absolute; top: 8px; right: 10px;
  background: none; border: none; color: #6b7280; font-size: 18px; cursor: pointer;
}
.badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.4px; }
.badge--graph_ready { background: #14432f; color: #5ee0a0; }
.badge--failed { background: #4a1620; color: #ff8fab; }
.badge--extracting, .badge--created { background: #2a2d33; color: #b8bcc4; }

@media (max-width: 860px) {
  .intake__main { grid-template-columns: 1fr; }
}
</style>
