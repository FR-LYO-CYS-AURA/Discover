<template>
  <div class="report">
    <header class="report__header no-print">
      <button class="back" @click="goBack">← Retour</button>
      <div class="report__title">
        <AppBrand /><span class="sep">/</span>
        <span>Rapport de synthèse</span>
      </div>
      <SimulationTabs :simulation-id="simulationId" current="report" />
      <div class="report__actions">
        <a class="btn-ghost" :href="downloadUrl" download>Télécharger .md</a>
        <button class="btn-primary" @click="print">Imprimer / PDF</button>
      </div>
    </header>

    <div v-if="loading" class="report__loading no-print">Chargement…</div>
    <div v-if="error" class="report__error no-print">{{ error }}</div>

    <article class="report__doc" v-html="html"></article>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SimulationTabs from '../components/SimulationTabs.vue'
import { getReport, downloadReportUrl } from '../api/simulation'

const props = defineProps({ simulationId: { type: String, required: true } })
const router = useRouter()

const markdown = ref('')
const loading = ref(true)
const error = ref('')

const downloadUrl = computed(() => downloadReportUrl(props.simulationId))
const html = computed(() => mdToHtml(markdown.value))

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function inline(s) {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
}
function mdToHtml(md) {
  if (!md) return ''
  const lines = md.split('\n')
  const out = []
  let i = 0
  let inList = false
  const closeList = () => { if (inList) { out.push('</ul>'); inList = false } }
  while (i < lines.length) {
    const line = lines[i]
    if (/^\|/.test(line) && i + 1 < lines.length && /^\|[\s:|-]+\|/.test(lines[i + 1])) {
      closeList()
      const header = line.split('|').slice(1, -1).map(c => c.trim())
      out.push('<table><thead><tr>' + header.map(h => `<th>${inline(h)}</th>`).join('') + '</tr></thead><tbody>')
      i += 2
      while (i < lines.length && /^\|/.test(lines[i])) {
        const cells = lines[i].split('|').slice(1, -1).map(c => c.trim())
        out.push('<tr>' + cells.map(c => `<td>${inline(c)}</td>`).join('') + '</tr>')
        i++
      }
      out.push('</tbody></table>')
      continue
    }
    if (/^### /.test(line)) { closeList(); out.push(`<h3>${inline(line.slice(4))}</h3>`) }
    else if (/^## /.test(line)) { closeList(); out.push(`<h2>${inline(line.slice(3))}</h2>`) }
    else if (/^# /.test(line)) { closeList(); out.push(`<h1>${inline(line.slice(2))}</h1>`) }
    else if (/^> /.test(line)) { closeList(); out.push(`<blockquote>${inline(line.slice(2))}</blockquote>`) }
    else if (/^---\s*$/.test(line)) { closeList(); out.push('<hr/>') }
    else if (/^\s*- /.test(line)) {
      if (!inList) { out.push('<ul>'); inList = true }
      out.push(`<li>${inline(line.replace(/^\s*- /, ''))}</li>`)
    }
    else if (line.trim() === '') { closeList() }
    else { closeList(); out.push(`<p>${inline(line)}</p>`) }
    i++
  }
  closeList()
  return out.join('\n')
}

async function load() {
  loading.value = true
  try {
    const res = await getReport(props.simulationId)
    markdown.value = res.data.markdown || ''
  } catch (e) {
    error.value = e?.message || 'Rapport indisponible.'
  } finally {
    loading.value = false
  }
}
function print() { window.print() }
function goBack() { router.back() }

onMounted(load)
</script>

<style scoped>
.report { min-height: 100vh; background: var(--bg); color: var(--text); }
.report__header { display: flex; align-items: center; gap: 16px; padding: 14px 24px; border-bottom: 1px solid var(--border); position: sticky; top: 0; background: var(--bg); }
.back { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 14px; }
.report__title { flex: 1; display: flex; align-items: center; gap: 10px; }
.brand { font-weight: 800; letter-spacing: 2px; }
.sep { color: var(--text-subtle); }
.report__actions { display: flex; gap: 10px; }
.btn-ghost { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 8px 14px; font-size: 13px; text-decoration: none; }
.btn-primary { background: var(--accent); border: none; color: var(--on-accent); border-radius: 8px; padding: 8px 14px; font-weight: 600; font-size: 13px; cursor: pointer; }
.report__loading, .report__error { padding: 16px 24px; color: var(--text-muted); }
.report__error { color: var(--danger); }

.report__doc { max-width: 820px; margin: 0 auto; padding: 32px 24px 80px; line-height: 1.55; }
.report__doc :deep(h1) { font-size: 26px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
.report__doc :deep(h2) { font-size: 20px; margin-top: 28px; color: var(--brand-orange-deep); }
.report__doc :deep(h3) { font-size: 16px; margin-top: 18px; }
.report__doc :deep(blockquote) { border-left: 3px solid var(--link); padding-left: 12px; color: var(--text-muted); font-style: italic; }
.report__doc :deep(ul) { padding-left: 20px; }
.report__doc :deep(li) { margin: 3px 0; }
.report__doc :deep(table) { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
.report__doc :deep(th), .report__doc :deep(td) { border: 1px solid var(--border); padding: 6px 10px; text-align: left; }
.report__doc :deep(th) { background: var(--surface); }
.report__doc :deep(hr) { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
.report__doc :deep(strong) { color: var(--on-accent); }

@media print {
  .no-print { display: none !important; }
  .report, .report__doc { background: var(--on-accent); color: #000; }
  .report__doc :deep(h2) { color: #b5642a; }
  .report__doc :deep(th) { background: #f0f0f0; }
  .report__doc :deep(th), .report__doc :deep(td) { border-color: #ccc; }
}
</style>
