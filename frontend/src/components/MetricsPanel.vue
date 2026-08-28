<template>
  <div class="metrics" v-if="metrics && metrics.steps && metrics.steps.length">
    <h3>Métriques</h3>
    <div class="metrics__totals">
      <span class="chip chip--model" v-if="metrics.model">🧠 {{ metrics.model }}</span>
      <span class="chip">⏱ {{ fmtDur(metrics.total_duration_s) }}</span>
      <span class="chip">🎟 {{ fmtNum(totals.tokens_total) }} tokens</span>
      <span class="chip">↳ {{ totals.llm_calls }} appels LLM</span>
      <span class="chip" v-if="totals.cost">💲 {{ totals.cost }}</span>
    </div>
    <table class="metrics__table">
      <thead>
        <tr><th>Étape</th><th>Durée</th><th>Appels</th><th>Tokens</th></tr>
      </thead>
      <tbody>
        <tr v-for="s in metrics.steps" :key="s.name">
          <td>{{ labelFor(s.name) }}</td>
          <td>{{ fmtDur(s.duration_s) }}</td>
          <td>{{ s.llm_calls }}</td>
          <td>{{ fmtNum(s.tokens_total) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ metrics: { type: Object, default: () => ({}) } })
const totals = computed(() => props.metrics?.totals || {})

const LABELS = {
  extraction: 'Extraction graphe',
  analyse_experts: 'Analyse experts',
  propagation: 'Propagation domino',
  narration: 'Narration chaînes',
  trajectoires: 'Trajectoires',
}
function labelFor(n) { return LABELS[n] || n }
function fmtDur(s) { return s == null ? '—' : (s < 60 ? `${s.toFixed(1)} s` : `${Math.floor(s / 60)}m${Math.round(s % 60)}s`) }
function fmtNum(n) { return n == null ? '—' : n.toLocaleString('fr-FR') }
</script>

<style scoped>
.metrics { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
.metrics h3 { font-size: 13px; text-transform: uppercase; letter-spacing: .5px; color: var(--text-muted); margin: 0 0 10px; }
.metrics__totals { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.chip { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; padding: 2px 9px; font-size: 12px; color: var(--text); }
.chip--model { border-color: var(--link); color: var(--link); }
.metrics__table { width: 100%; border-collapse: collapse; font-size: 12px; }
.metrics__table th { text-align: left; color: var(--text-muted); padding: 4px 6px; border-bottom: 1px solid var(--border); font-weight: 500; }
.metrics__table td { padding: 4px 6px; color: var(--text); }
</style>
