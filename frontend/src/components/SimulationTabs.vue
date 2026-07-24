<template>
  <nav class="tabs">
    <button
      v-for="t in tabs"
      :key="t.key"
      class="tab"
      :class="{ 'tab--active': t.key === current, 'tab--disabled': !t.enabled }"
      :disabled="!t.enabled"
      @click="go(t)"
    >{{ t.label }}</button>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSimulation } from '../api/simulation'

const props = defineProps({
  simulationId: { type: String, required: true },
  current: { type: String, required: true }, // graph | simulation | trajectories | report
})

const router = useRouter()
const scenarioId = ref('')
const status = ref('')
const trajStatus = ref('none')

const tabs = computed(() => [
  { key: 'graph', label: 'Graphe', enabled: !!scenarioId.value },
  { key: 'simulation', label: 'Simulation', enabled: true },
  { key: 'trajectories', label: 'Trajectoires', enabled: status.value === 'completed' },
  { key: 'report', label: 'Rapport', enabled: status.value === 'completed' },
])

function go(t) {
  if (!t.enabled || t.key === props.current) return
  if (t.key === 'graph') router.push({ name: 'CrisisGraph', params: { scenarioId: scenarioId.value }, query: { sim: props.simulationId } })
  else if (t.key === 'simulation') router.push({ name: 'CrisisSimulation', params: { simulationId: props.simulationId } })
  else if (t.key === 'trajectories') router.push({ name: 'CrisisTrajectories', params: { simulationId: props.simulationId } })
  else if (t.key === 'report') router.push({ name: 'CrisisReport', params: { simulationId: props.simulationId } })
}

onMounted(async () => {
  try {
    const res = await getSimulation(props.simulationId)
    scenarioId.value = res.data.scenario_id || ''
    status.value = res.data.status || ''
    trajStatus.value = res.data.trajectories_status || 'none'
  } catch (e) { /* non bloquant */ }
})
</script>

<style scoped>
.tabs { display: flex; gap: 2px; }
.tab {
  background: none; border: none; border-bottom: 2px solid transparent;
  color: #9aa0a6; font-size: 13px; font-family: inherit; cursor: pointer;
  padding: 6px 12px;
}
.tab:not(.tab--disabled):hover { color: #e8eaed; }
.tab--active { color: #e8eaed; font-weight: 600; border-bottom-color: #e63946; }
.tab--disabled { opacity: 0.4; cursor: default; }
</style>
