<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { api } from '../../api'
import { resolveBlock } from '../../reports/registry'

const props = defineProps({ blockId: { type: String, default: 'sales-trend' }, config: { type: Object, default: () => ({}) }, filters: { type: Object, default: () => ({}) }, refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['drill', 'loaded'])
const definition = computed(() => resolveBlock(props.blockId, props.config))
const params = computed(() => {
  const d = definition.value
  return { ...props.filters, source: d.source, group_by: d.group_by, grain: d.grain, comparison: d.comparison || 'previous', ...(d.date_field ? { date_field: d.date_field } : {}), ...(d.filters || {}) }
})
const data = ref(null), error = ref(''), loading = ref(false), exporting = ref(false), page = ref(1), unit = ref(''), viewOverride = ref('')
let sequence = 0, controller
async function load() {
  const current = ++sequence
  controller?.abort(); controller = new AbortController()
  loading.value = true; error.value = ''; data.value = null
  try {
    const response = await api.get('/reports/data/', { params: params.value, signal: controller.signal })
    if (current !== sequence) return
    data.value = response.data; page.value = 1
    unit.value = Object.keys(data.value.totals.quantities)[0] || ''
    emit('loaded', data.value)
  } catch (err) { if (current === sequence) error.value = err.message }
  finally { if (current === sequence) loading.value = false }
}
watch([params, () => props.refreshKey], load, { immediate: true, deep: true })
watch(() => definition.value.view, () => { viewOverride.value = '' })
onBeforeUnmount(() => { sequence++; controller?.abort() })
const numeric = value => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(Number(value || 0))
const quantityText = quantities => Object.entries(quantities || {}).map(([key, value]) => `${numeric(value)} ${key}`).join(' / ') || '—'
const metric = computed(() => definition.value.metric)
const metricLabel = computed(() => metric.value === 'amount' ? '金额（人民币）' : metric.value === 'quantity' ? `数量（${unit.value || '无单位数据'}）` : '去重单据 / 档案数')
const valueOf = row => Number(metric.value === 'quantity' ? row.quantities?.[unit.value] || 0 : row[metric.value] || 0)
const rows = computed(() => data.value?.rows || [])
const chartRows = computed(() => definition.value.group_by === 'time' ? rows.value : [...rows.value].sort((a, b) => Math.abs(valueOf(b)) - Math.abs(valueOf(a))).slice(0, 12))
const chartView = computed(() => viewOverride.value || definition.value.view)
const hasNegative = computed(() => chartRows.value.some(row => valueOf(row) < 0))
const effectiveView = computed(() => chartView.value === 'donut' && hasNegative.value ? 'bar' : chartView.value)
const maxValue = computed(() => Math.max(1, ...chartRows.value.map(row => Math.abs(valueOf(row)))))
const positiveTotal = computed(() => chartRows.value.reduce((sum, row) => sum + Math.max(0, valueOf(row)), 0))
const colors = ['#237969', '#4e91bd', '#c29143', '#8e79b2', '#d37869', '#7c9d57']
const slices = computed(() => {
  let offset = 0
  return chartRows.value.map((row, i) => { const percent = positiveTotal.value ? valueOf(row) / positiveTotal.value * 100 : 0; const slice = { row, percent, offset, color: colors[i % colors.length] }; offset += percent; return slice })
})
const yRange = computed(() => { const values = chartRows.value.map(valueOf); return { min: Math.min(0, ...values), max: Math.max(1, ...values) } })
const y = value => 170 - (value - yRange.value.min) / (yRange.value.max - yRange.value.min) * 140
const points = computed(() => chartRows.value.map((row, index) => ({ row, x: 55 + index / Math.max(1, chartRows.value.length - 1) * 615, y: y(valueOf(row)) })))
const line = computed(() => points.value.map(point => `${point.x},${point.y}`).join(' '))
const visibleRows = computed(() => rows.value.slice((page.value - 1) * 15, page.value * 15))
const monetary = computed(() => !['customers', 'inventory'].includes(definition.value.source))
const comparison = computed(() => {
  const change = data.value?.changes[metric.value]
  return change == null ? '基期为零或该指标不适用' : `${change > 0 ? '+' : ''}${numeric(change)}%`
})
function drill(row) { if (definition.value.group_by !== 'time') emit('drill', { dimension: definition.value.group_by, value: row.key, label: row.label, source: definition.value.source, date_field: data.value.date_field, filters: data.value.filters, filter_summary: data.value.filter_summary }) }
async function exportCsv() {
  exporting.value = true
  try {
    const response = await api.get('/reports/data/', { params: { ...params.value, export: 'csv' }, responseType: 'blob' })
    const url = URL.createObjectURL(response.data), anchor = document.createElement('a')
    anchor.href = url; anchor.download = `${definition.value.title || '统计报表'}-${data.value.period.date_from}-${data.value.period.date_to}.csv`; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (err) { error.value = err.message }
  finally { exporting.value = false }
}
</script>

<template>
  <article class="report-block" :aria-busy="loading">
    <header class="block-header"><div><small>经营统计</small><h2>{{ definition.title || '自定义报表' }}</h2></div><div class="block-actions"><select v-model="viewOverride" aria-label="图表显示方式"><option value="">默认图表</option><option value="bar">条形图</option><option value="line">折线图</option><option value="donut">环形图</option><option value="table">仅表格</option></select><button :disabled="loading || !data || exporting" @click="exportCsv">{{ exporting ? '导出中…' : '导出 CSV' }}</button></div></header>
    <p v-if="loading" role="status">正在汇总完整数据…</p>
    <div v-else-if="error" role="alert" class="report-error">{{ error }} <button @click="load">重试</button></div>
    <template v-else-if="data">
      <div class="block-kpis"><div v-if="monetary"><small>{{ definition.source === 'cash' ? '净现金流（人民币）' : '金额合计（人民币）' }}</small><strong>¥ {{ numeric(data.totals.amount) }}</strong></div><div><small>去重单据 / 档案数</small><strong>{{ data.totals.count }}</strong></div><div v-if="Object.keys(data.totals.quantities).length"><small>数量合计（按单位）</small><strong class="quantity-kpi">{{ quantityText(data.totals.quantities) }}</strong></div></div>
      <p class="report-caption">{{ data.date_label }} · {{ data.period.date_from }} — {{ data.period.date_to }} · {{ data.comparison === 'year' ? '去年同期' : '上一等长期间' }} {{ data.comparison_period.date_from }} — {{ data.comparison_period.date_to }} · {{ metricLabel }}变化：{{ comparison }}</p>
      <p v-if="data.filter_summary?.length" class="report-caption">附加筛选：<span v-for="item in data.filter_summary" :key="item.dimension">{{ item.name }}：{{ item.label }}； </span></p>
      <p class="report-note">{{ data.note }} 分组单据数可能交叉，不应相加；空日期不纳入该日期口径。</p>
      <p v-if="!data.totals.count" class="report-empty">此筛选条件下暂无数据，可调整日期、日期口径或筛选条件。</p>
      <template v-else>
        <div class="chart-caption"><strong>{{ metricLabel }}</strong><label v-if="metric === 'quantity'">单位 <select v-model="unit"><option v-for="key in Object.keys(data.totals.quantities)" :key="key">{{ key }}</option></select></label><span v-if="definition.group_by !== 'time'">图表按绝对值显示前 12 项；表格及导出包含全部 {{ rows.length }} 项</span></div>
        <p v-if="hasNegative && chartView === 'donut'" class="report-caption">含负值，自动使用条形图以保留收支 / 出入库方向。</p>
        <div v-if="effectiveView === 'bar'" class="report-bars" role="img" :aria-label="`${definition.title}，详细数值见下方表格`"><div v-for="row in chartRows" :key="row.key" class="report-bar-row"><button class="bar-label" :title="row.label" @click="drill(row)">{{ row.label }}</button><div class="bar-track"><div :class="{ negative: valueOf(row) < 0 }" :style="{ width: `${Math.abs(valueOf(row)) / maxValue * 100}%` }" /></div><span>{{ numeric(valueOf(row)) }}</span></div></div>
        <div v-else-if="effectiveView === 'line'" class="report-line"><svg viewBox="0 0 720 220" role="img" :aria-label="`${definition.title}，详细数值见下方表格`"><text x="4" y="23">{{ numeric(yRange.max) }}</text><text x="4" y="180">{{ numeric(yRange.min) }}</text><line x1="55" :y1="y(0)" x2="670" :y2="y(0)" stroke="#cad7d2" /><polyline :points="line" fill="none" stroke="#237969" stroke-width="3" /><circle v-for="point in points" :key="point.row.key" :cx="point.x" :cy="point.y" r="3" fill="#237969"><title>{{ point.row.label }}：{{ numeric(valueOf(point.row)) }}</title></circle><text x="55" y="207">{{ chartRows[0]?.label }}</text><text x="670" y="207" text-anchor="end">{{ chartRows.at(-1)?.label }}</text></svg></div>
        <div v-else-if="effectiveView === 'donut'" class="report-donut"><svg viewBox="0 0 42 42" role="img" :aria-label="`${definition.title}，占显示项目合计比例`"><circle cx="21" cy="21" r="15.9155" fill="none" stroke="#edf1ee" stroke-width="6" /><circle v-for="slice in slices" :key="slice.row.key" cx="21" cy="21" r="15.9155" fill="none" :stroke="slice.color" stroke-width="6" :stroke-dasharray="`${slice.percent} ${100 - slice.percent}`" :stroke-dashoffset="25 - slice.offset"><title>{{ slice.row.label }}：{{ numeric(valueOf(slice.row)) }}</title></circle></svg><div><p v-for="slice in slices" :key="slice.row.key"><i :style="{ background: slice.color }" />{{ slice.row.label }} · {{ numeric(slice.percent) }}%</p><small>占图中显示项目的比例；全零时不显示扇区。</small></div></div>
        <div class="report-table"><table><thead><tr><th>统计分组</th><th v-if="monetary">金额（人民币）</th><th>去重单据 / 档案数</th><th v-if="['sales', 'purchase', 'inventory'].includes(definition.source)">数量（按单位）</th></tr></thead><tbody><tr v-for="row in visibleRows" :key="row.key"><td><button v-if="definition.group_by !== 'time'" class="report-link" @click="drill(row)">{{ row.label }}</button><span v-else>{{ row.label }}</span></td><td v-if="monetary">{{ numeric(row.amount) }}</td><td>{{ row.count }}</td><td v-if="['sales', 'purchase', 'inventory'].includes(definition.source)">{{ quantityText(row.quantities) }}</td></tr></tbody></table></div>
        <footer class="report-pagination"><span>共 {{ rows.length }} 项 · 点击分组可筛选后切换维度继续分析</span><button :disabled="page <= 1" @click="page--">上一页</button><span>{{ page }} / {{ Math.max(1, Math.ceil(rows.length / 15)) }}</span><button :disabled="page * 15 >= rows.length" @click="page++">下一页</button></footer>
      </template>
    </template>
  </article>
</template>

<style scoped>
.report-block{background:white;border:1px solid #dfe7e2;border-radius:16px;padding:24px;min-width:0}.block-header,.block-actions,.chart-caption,.report-pagination{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.block-header{justify-content:space-between}.block-header h2{font-size:var(--text-section);margin:6px 0 18px}.block-header small,.report-caption,.chart-caption span,.report-pagination,.report-donut small{color:#697d74;font-size:var(--text-caption)}.report-block select,.report-block button{padding:7px 10px;border:1px solid #d7e2db;border-radius:7px;background:#fff;color:#265d4d;cursor:pointer}.report-block button:disabled{opacity:.45;cursor:default}.block-kpis{display:flex;gap:30px;flex-wrap:wrap;padding:18px;background:#f5f8f5;border-radius:10px}.block-kpis small{display:block;color:#687b71;font-size:var(--text-caption)}.block-kpis strong{display:block;font-size:var(--text-metric);margin-top:8px}.block-kpis .quantity-kpi{font-size:var(--text-dialog);max-width:360px}.report-caption{line-height:1.8}.report-note{font-size:var(--text-caption);color:#627066;background:#faf9f4;padding:12px;line-height:1.8;border-radius:8px}.report-empty{padding:40px;text-align:center;color:#77877e}.chart-caption{margin:24px 0 18px;font-size:var(--text-caption);justify-content:space-between}.report-bar-row{display:grid;grid-template-columns:minmax(90px,180px) 1fr 100px;align-items:center;gap:12px;margin:9px 0;font-size:var(--text-caption)}.report-bar-row .bar-label{border:0;padding:0;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bar-track{height:14px;background:#f1f5f2;border-radius:3px;overflow:hidden}.bar-track div{height:100%;background:#358a75;border-radius:3px}.bar-track div.negative{background:#c37764}.report-bar-row>span{text-align:right}.report-line svg{width:100%;max-height:280px}.report-line text{font-size:var(--text-caption);fill:#75857a}.report-donut{display:flex;align-items:center;gap:24px;flex-wrap:wrap}.report-donut svg{width:210px;height:210px}.report-donut p{font-size:var(--text-caption);margin:8px 0}.report-donut i{display:inline-block;width:9px;height:9px;margin-right:8px;border-radius:50%}.report-table{overflow:auto;margin-top:24px}.report-table table{width:100%;border-collapse:collapse;font-size:var(--text-body)}.report-table th,.report-table td{padding:12px;text-align:left;border-bottom:1px solid #edf1ed;white-space:nowrap}.report-table th{background:#f6f8f5;color:#68776c}.report-table .report-link{border:0;background:none;padding:0;text-align:left}.report-pagination{justify-content:flex-end;margin-top:15px}.report-pagination>span:first-child{margin-right:auto}.report-error{color:#a34636;padding:24px}@media(max-width:650px){.report-block{padding:16px}.block-kpis{gap:18px}.block-kpis strong{font-size:var(--text-dialog)}.report-bar-row{grid-template-columns:90px 1fr 70px}}
</style>
