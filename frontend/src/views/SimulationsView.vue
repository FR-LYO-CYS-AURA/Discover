<template>
  <div class="sims">
    <header class="sims__header">
      <button class="back" @click="goHome">← Accueil</button>
      <div class="sims__title"><AppBrand /><span class="sep">/</span><span>Mes simulations</span></div>
    </header>

    <main class="sims__main">
      <div v-if="items.length === 0" class="empty">Aucune simulation enregistrée.</div>

      <table v-else class="sims__table">
        <thead>
          <tr>
            <th>Titre</th><th>Scénario</th><th>Statut</th><th>Indice max</th>
            <th>Modèle</th><th>Durée</th><th>Tokens</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in items" :key="s.simulation_id">
            <td>
              <template v-if="editing === s.simulation_id">
                <input v-model="editTitle" class="edit" @keyup.enter="saveRename(s)" @keyup.esc="editing=null" />
                <button class="mini" @click="saveRename(s)">✓</button>
                <button class="mini" @click="editing=null">×</button>
              </template>
              <template v-else>
                <span class="title" @click="reopen(s)">{{ s.title }}</span>
                <button class="mini" title="Renommer" @click="startRename(s)">✎</button>
              </template>
            </td>
            <td class="muted">{{ s.scenario_title }}</td>
            <td><span :class="['badge','badge--'+s.status]">{{ statusLabel(s.status) }}</span></td>
            <td>
              <span v-if="s.max_global_index != null" class="idx" :style="{ background: idxColor(s.max_global_index) }">{{ s.max_global_index }}</span>
              <span v-else class="muted">—</span>
            </td>
            <td class="muted model">{{ s.model || '—' }}</td>
            <td class="muted">{{ fmtDur(s.duration_s) }}</td>
            <td class="muted">{{ s.tokens_total != null ? s.tokens_total.toLocaleString('fr-FR') : '—' }}</td>
            <td class="actions">
              <button class="mini mini--link" @click="reopen(s)">Ouvrir</button>
              <button v-if="s.status==='completed'" class="mini mini--link" @click="goTraj(s)">Trajectoires</button>
              <button v-if="s.status==='completed'" class="mini mini--link" @click="goReport(s)">Rapport</button>
              <button class="mini mini--del" @click="remove(s)">Suppr.</button>
            </td>
          </tr>
        </tbody>
      </table>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listSimulations, deleteSimulation, renameSimulation } from '../api/simulation'
import { idxColor } from '@/styles/palette'

const router = useRouter()
const items = ref([])
const editing = ref(null)
const editTitle = ref('')

const STATUS = { created: 'Créée', analyzing: 'Analyse', propagating: 'Propagation', narrating: 'Qualif.', completed: 'Terminée', failed: 'Échec' }
function statusLabel(s) { return STATUS[s] || s }
function fmtDur(s) { return s == null ? '—' : (s < 60 ? `${s.toFixed(0)} s` : `${Math.floor(s / 60)}m${Math.round(s % 60)}s`) }


async function load() {
  try { items.value = (await listSimulations()).data || [] } catch (e) { console.error(e) }
}
function reopen(s) { router.push({ name: 'CrisisSimulation', params: { simulationId: s.simulation_id } }) }
function goTraj(s) { router.push({ name: 'CrisisTrajectories', params: { simulationId: s.simulation_id } }) }
function goReport(s) { router.push({ name: 'CrisisReport', params: { simulationId: s.simulation_id } }) }
function goHome() { router.push({ name: 'Home' }) }
function startRename(s) { editing.value = s.simulation_id; editTitle.value = s.title }
async function saveRename(s) {
  const t = editTitle.value.trim()
  if (t) { try { await renameSimulation(s.simulation_id, t); s.title = t } catch (e) { console.error(e) } }
  editing.value = null
}
async function remove(s) {
  try { await deleteSimulation(s.simulation_id); items.value = items.value.filter(x => x.simulation_id !== s.simulation_id) } catch (e) { console.error(e) }
}

onMounted(load)
</script>

<style scoped>
.sims { min-height: 100vh; background: var(--bg); color: var(--text); }
.sims__header { display: flex; align-items: center; gap: 16px; padding: 14px 24px; border-bottom: 1px solid var(--border); }
.back { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 14px; }
.sims__title { display: flex; align-items: center; gap: 10px; }
.brand { font-weight: 800; letter-spacing: 2px; }
.sep { color: var(--text-subtle); }
.sims__main { max-width: 1100px; margin: 0 auto; padding: 24px; }
.empty { color: var(--text-subtle); padding: 40px; text-align: center; }
.sims__table { width: 100%; border-collapse: collapse; font-size: 13px; }
.sims__table th { text-align: left; color: var(--text-muted); padding: 8px 10px; border-bottom: 1px solid var(--border); font-weight: 500; }
.sims__table td { padding: 8px 10px; border-bottom: 1px solid var(--surface); }
.muted { color: var(--text-muted); }
.model { font-size: 11px; }
.title { cursor: pointer; font-weight: 600; }
.title:hover { color: var(--link-hover); }
.edit { background: var(--bg); border: 1px solid var(--link); border-radius: 6px; color: var(--text); padding: 3px 6px; font-family: inherit; }
.idx { color: var(--on-accent); padding: 1px 8px; border-radius: 10px; font-weight: 600; }
.actions { white-space: nowrap; text-align: right; }
.mini { background: none; border: none; color: var(--text-muted); font-size: 12px; cursor: pointer; padding: 2px 5px; }
.mini--link { color: var(--link); }
.mini--link:hover { color: var(--link-hover); }
.mini--del { color: var(--danger); }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.badge--completed { background: var(--success-bg); color: var(--success); }
.badge--failed { background: var(--danger-bg); color: var(--danger); }
.badge--analyzing, .badge--propagating, .badge--narrating, .badge--created { background: var(--border); color: var(--text-muted); }
</style>
