<template>
  <nav class="stepper">
    <button
      v-for="(s, i) in steps"
      :key="s.key"
      class="step"
      :class="{ 'step--active': s.key === current, 'step--done': isDone(i), 'step--disabled': !canGo(s) }"
      :disabled="!canGo(s)"
      @click="go(s)"
    >
      <span class="step__num">{{ i + 1 }}</span>
      <span class="step__label">{{ s.label }}</span>
      <span v-if="i < steps.length - 1" class="step__sep">›</span>
    </button>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  current: { type: String, required: true }, // intake | graph | simulation | trajectories
  scenarioId: { type: String, default: '' },
  simulationId: { type: String, default: '' },
})

const router = useRouter()

const steps = [
  { key: 'intake', label: 'Intake' },
  { key: 'graph', label: 'Graphe de crise' },
  { key: 'simulation', label: 'Simulation' },
  { key: 'trajectories', label: 'Trajectoires' },
]

const order = { intake: 0, graph: 1, simulation: 2, trajectories: 3 }

function isDone(i) {
  return i < order[props.current]
}

function canGo(s) {
  if (s.key === props.current) return false
  if (s.key === 'intake') return true
  if (s.key === 'graph') return !!props.scenarioId
  if (s.key === 'simulation' || s.key === 'trajectories') return !!props.simulationId
  return false
}

function go(s) {
  if (!canGo(s)) return
  if (s.key === 'intake') router.push({ name: 'Home' })
  else if (s.key === 'graph') router.push({ name: 'CrisisGraph', params: { scenarioId: props.scenarioId } })
  else if (s.key === 'simulation') router.push({ name: 'CrisisSimulation', params: { simulationId: props.simulationId } })
  else if (s.key === 'trajectories') router.push({ name: 'CrisisTrajectories', params: { simulationId: props.simulationId } })
}
</script>

<style scoped>
.stepper { display: flex; align-items: center; gap: 2px; }
.step {
  display: flex; align-items: center; gap: 6px;
  background: none; border: none; cursor: pointer;
  color: #6b7280; font-size: 12px; font-family: inherit; padding: 4px 6px;
}
.step__num {
  width: 18px; height: 18px; line-height: 18px; text-align: center;
  border-radius: 50%; background: #2a2d33; color: #9aa0a6; font-size: 11px; font-weight: 600;
}
.step__label { white-space: nowrap; }
.step__sep { color: #3a3d43; margin-left: 4px; }
.step--done { color: #b8bcc4; }
.step--done .step__num { background: #14432f; color: #5ee0a0; }
.step--active { color: #e8eaed; font-weight: 600; }
.step--active .step__num { background: #e63946; color: #fff; }
.step:not(.step--disabled):hover .step__label { color: #e8eaed; }
.step--disabled { cursor: default; opacity: 0.5; }
</style>
