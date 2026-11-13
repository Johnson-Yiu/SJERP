<script setup>
import { downloadBlob } from '../../utils/downloadBlob.js'
import { useWorkspaceApi } from '../../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { BOOK_RMB_NOTE } from '../../utils/financeBasis.js'
import { computed, ref, watch, onBeforeUnmount } from 'vue'

import { resolveBlock, canViewReportConfig, reportDimensionLabels } from '../../reports/registry'
import { apiErrorMessage } from '../../utils/apiErrors'
import { useAccessControl } from '../../accessControl'
import ReportDetailPanel from './ReportDetailPanel.vue'

const props = defineProps({ blockId: { type: String, default: 'sales-trend' }, config: { type: Object, default: () => ({}) }, filters: { type: Object, default: () => ({}) }, sharedTemplateId: { type: [String, Number], default: '' }, refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['drill', 'loaded'])
const { can } = useAccessControl()
const definition = computed(() => resolveBlock(props.blockId, props.config))
const permitted = computed(() => canViewReportConfig({ ...definition.value, filters: { ...props.filters, ...definition.value.filters } }, can))
const params = computed(() => {
  const d = definition.value
  return { ...props.filters, ...(props.sharedTemplateId ? { shared_template: props.sharedTemplateId } : {}), source: d.source, group_by: d.group_by, ...(d.group_by_2 ? { group_by_2: d.group_by_2 } : {}), grain: d.grain, comparison: d.comparison || 'previous', ...(d.date_field ? { date_field: d.date_field } : {}), ...(d.filters || {}) }
})
const data = ref(null), error = ref(''), loading = ref(false), exporting = ref(false), page = ref(1), unit = ref(''), viewOverride = ref(''), exportError = ref(''), exportNotice = ref('')
const detailSelection = ref(null)
let sequence = 0, controller
async function load() {
  const current = ++sequence
  controller?.abort(); controller = new AbortController()
  loading.value = false; error.value = ''; exportError.value = ''; exportNotice.value = ''; data.value = null
  if (!permitted.value) return
  loading.value = true
  try {
    const response = await api.get('/reports/data/', { params: params.value, signal: controller.signal })
    if (current !== sequence) return
    data.value = response.data; page.value = 1
    unit.value = Object.keys(data.value.totals.quantities)[0] || ''
    emit('loaded', data.value)
  } catch (err) { if (current === sequence) error.value = apiErrorMessage(err) || '图表数据加载失败，请重试。' }
  finally { if (current === sequence) loading.value = false }
}
watch([params, permitted, () => props.refreshKey], load, { immediate: true, deep: true })
watch(definition, () => { viewOverride.value = '' }, { deep: true })
watch(params, () => { detailSelection.value = null }, { deep: true })
onBeforeUnmount(() => { sequence++; controller?.abort() })
const numeric = value => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(Number(value || 0))
const axisNumeric = value => Math.abs(Number(value)) >= 100000000 ? `${numeric(Number(value) / 100000000)}亿` : Math.abs(Number(value)) >= 10000 ? `${numeric(Number(value) / 10000)}万` : numeric(value)
const quantityText = quantities => Object.entries(quantities || {}).map(([key, value]) => `${numeric(value)} ${key}`).join(' / ') || '—'
const metric = computed(() => definition.value.metric)
const metricLabel = computed(() => metric.value === 'amount' ? (definition.value.source === 'cash' ? '金额（人民币折算参考）' : definition.value.source === 'actual_cash' ? '金额（银行实际人民币净额）' : '金额（人民币）') : metric.value === 'quantity' ? `数量（${unit.value || '无单位数据'}）` : '去重单据 / 档案数')
const valueOf = row => Number(metric.value === 'quantity' ? row.quantities?.[unit.value] || 0 : row[metric.value] || 0)
const rows = computed(() => data.value?.rows || [])
const multiDimensional = computed(() => Boolean(definition.value.group_by_2))
const chartRows = computed(() => definition.value.group_by === 'time' && !multiDimensional.value ? rows.value : [...rows.value].sort((a, b) => Math.abs(valueOf(b)) - Math.abs(valueOf(a))).slice(0, 12))
const chartView = computed(() => viewOverride.value || definition.value.view)
const hasNegative = computed(() => chartRows.value.some(row => valueOf(row) < 0))
const effectiveView = computed(() => multiDimensional.value && chartView.value === 'line' ? 'bar' : chartView.value === 'donut' && hasNegative.value ? 'bar' : chartView.value)
const maxValue = computed(() => Math.max(1, ...chartRows.value.map(row => Math.abs(valueOf(row)))))
const positiveTotal = computed(() => chartRows.value.reduce((sum, row) => sum + Math.max(0, valueOf(row)), 0))
const colors = ['#237969', '#4e91bd', '#c29143', '#8e79b2', '#d37869', '#7c9d57']
const slices = computed(() => {
  let offset = 0
  return chartRows.value.map((row, i) => { const percent = positiveTotal.value ? valueOf(row) / positiveTotal.value * 100 : 0; const slice = { row, percent, offset, color: colors[i % colors.length] }; offset += percent; return slice })
})
const yRange = computed(() => { const values = chartRows.value.map(valueOf); return { min: Math.min(0, ...values), max: Math.max(1, ...values) } })
const y = value => 170 - (value - yRange.value.min) / (yRange.value.max - yRange.value.min) * 140
const points = computed(() => chartRows.value.map((row, index) => ({ row, x: 130 + index / Math.max(1, chartRows.value.length - 1) * 560, y: y(valueOf(row)) })))
const line = computed(() => points.value.map(point => `${point.x},${point.y}`).join(' '))
const visibleRows = computed(() => rows.value.slice((page.value - 1) * 15, page.value * 15))
const monetary = computed(() => !['customers', 'inventory'].includes(definition.value.source))
const comparison = computed(() => {
  const change = data.value?.changes?.[metric.value]
  return change == null ? '基期为零或该指标不适用' : `${change > 0 ? '+' : ''}${numeric(change)}%`
})
const groupColumns = computed(() => [definition.value.group_by, ...(definition.value.group_by_2 ? [definition.value.group_by_2] : [])])
const rowGroups = row => row.groups?.length ? row.groups : [{ dimension: definition.value.group_by, key: row.key, label: row.label }]
const groupLabel = dimension => definition.value.source === 'cash' && dimension === 'category' ? '收支分类' : reportDimensionLabels[dimension] || dimension
function drill(row, groupIndex = 0) {
  const group = rowGroups(row)[groupIndex]
  if (!group || group.dimension === 'time') return
  const other = multiDimensional.value ? rowGroups(row)[groupIndex === 0 ? 1 : 0] : null
  emit('drill', { dimension: group.dimension, value: group.key, label: group.label, next_group_by: other?.dimension || null, source: definition.value.source, date_field: data.value.date_field, filters: data.value.filters, filter_summary: data.value.filter_summary, period: data.value.period, config: { ...definition.value } })
}
function openDetails(row) {
  if (!['sales', 'purchase'].includes(definition.value.source)) return
  detailSelection.value = { groups: rowGroups(row), label: row.label }
}
const detailQuery = computed(() => ({ ...params.value, date_from: data.value?.period?.date_from || props.filters.date_from, date_to: data.value?.period?.date_to || props.filters.date_to }))
const detailKey = computed(() => detailSelection.value ? `${detailSelection.value.groups.map(group => `${group.dimension}:${group.key}`).join('|')}:${detailQuery.value.date_from}:${detailQuery.value.date_to}` : '')
async function exportCsv() {
  if (!can('reports', 'export') || !permitted.value || !data.value || loading.value || exporting.value) return
  const exportSequence = sequence
  const exportParams = { ...params.value }
  const exportName = `${definition.value.title || '统计报表'}-${data.value.period.date_from}-${data.value.period.date_to}.csv`
  exporting.value = true; exportError.value = ''; exportNotice.value = ''
  try {
    const response = await api.get('/reports/data/', { params: { ...exportParams, export: 'csv' }, responseType: 'blob' })
    downloadBlob(response.data, exportName)
    if (exportSequence === sequence) exportNotice.value = 'CSV 已生成，请查看浏览器下载。'
  } catch (err) { if (exportSequence === sequence) exportError.value = apiErrorMessage(err) || '导出失败，请重试。' }
  finally { exporting.value = false }
}
</script>

<template>
  <article class="report-block" :aria-busy="loading" :aria-label="definition.title || '自定义报表'">
    <header class="block-header"><div><small>经营报表</small><h2>{{ definition.title || '自定义报表' }}</h2></div><div v-if="permitted" class="block-actions"><select v-model="viewOverride" aria-label="图表显示方式"><option value="">默认图表</option><option value="bar">条形图</option><option v-if="!multiDimensional" value="line">折线图</option><option value="donut">环形图</option><option value="table">仅表格</option></select><button v-if="can('reports', 'export')" :disabled="loading || !data || exporting" @click="exportCsv">{{ exporting ? '导出中…' : '导出 CSV' }}</button></div></header>
    <p v-if="!permitted" class="report-empty" role="status">当前账号没有此报表的数据权限，未加载该报表。</p>
    <p v-else-if="loading" role="status">正在加载报表数据…</p>
    <div v-else-if="error" role="alert" class="report-error">{{ error }} <button @click="load">重试</button></div>
    <template v-else-if="data">
      <div class="block-kpis"><div v-if="monetary"><small>{{ definition.source === 'cash' ? '账面净收支（折算参考）' : definition.source === 'actual_cash' ? '银行实际净流入/净流出' : '金额合计（人民币）' }}</small><strong>{{ data.totals.amount === null ? '成本待核实' : '¥ ' + numeric(data.totals.amount) }}</strong></div><div><small>去重单据 / 档案数</small><strong>{{ data.totals.count }}</strong></div><div v-if="Object.keys(data.totals.quantities).length"><small>数量合计（按单位）</small><strong class="quantity-kpi">{{ quantityText(data.totals.quantities) }}</strong></div></div>
      <p class="report-caption">{{ data.date_label }} · {{ data.period.date_from }} — {{ data.period.date_to }} · {{ data.comparison === 'year' ? '去年同期' : '上一等长期间' }} {{ data.comparison_period.date_from }} — {{ data.comparison_period.date_to }} · {{ metricLabel }}变化：{{ comparison }}</p>
      <p v-if="data.filter_summary?.length" class="report-caption">附加筛选：<span v-for="item in data.filter_summary" :key="item.dimension">{{ item.name }}：{{ item.label }}； </span></p>
      <p class="report-note">{{ definition.source === 'cash' ? BOOK_RMB_NOTE : data.note }} 分组单据数可能交叉，不应相加；空日期不纳入该日期口径。</p>
      <p v-if="!data.totals.count" class="report-empty" role="status">此筛选条件下暂无数据，可调整日期、日期口径或筛选条件。</p>
      <template v-else>
        <div class="chart-caption"><strong>{{ metricLabel }}</strong><label v-if="metric === 'quantity'">单位 <select v-model="unit"><option v-for="key in Object.keys(data.totals.quantities)" :key="key">{{ key }}</option></select></label><span v-if="definition.group_by !== 'time' || multiDimensional">图表按绝对值显示前 12 项；表格及导出包含全部 {{ rows.length }} 项，点击分组可继续下钻</span></div>
        <p v-if="hasNegative && chartView === 'donut'" class="report-caption">含负值，自动使用条形图以保留收支 / 出入库方向。</p>
        <p v-if="metric === 'amount' && data.totals.amount === null">部分订单成本待核实，请查看下方明细。</p>
        <div v-else-if="effectiveView === 'bar'" class="report-bars" role="img" :aria-label="`${definition.title}，详细数值见下方表格`"><div v-for="row in chartRows" :key="row.key" class="report-bar-row"><button v-if="definition.group_by !== 'time'" class="bar-label" :title="row.label" @click="drill(row)">{{ row.label }}</button><span v-else class="bar-label">{{ row.label }}</span><div class="bar-track"><div :class="{ negative: valueOf(row) < 0 }" :style="{ width: `${Math.abs(valueOf(row)) / maxValue * 100}%` }" /></div><span>{{ numeric(valueOf(row)) }}</span></div></div>
        <div v-else-if="effectiveView === 'line'" class="report-line"><svg viewBox="0 0 720 220" role="img" :aria-label="`${definition.title}，详细数值见下方表格`"><text x="4" y="23">{{ axisNumeric(yRange.max) }}</text><text x="4" y="180">{{ axisNumeric(yRange.min) }}</text><line x1="130" :y1="y(0)" x2="690" :y2="y(0)" stroke="#cad7d2" /><polyline :points="line" fill="none" stroke="#237969" stroke-width="3" /><circle v-for="point in points" :key="point.row.key" :cx="point.x" :cy="point.y" r="3" fill="#237969"><title>{{ point.row.label }}：{{ numeric(valueOf(point.row)) }}</title></circle><text x="130" y="207">{{ chartRows[0]?.label }}</text><text x="690" y="207" text-anchor="end">{{ chartRows.at(-1)?.label }}</text></svg></div>
        <div v-else-if="effectiveView === 'donut'" class="report-donut"><svg viewBox="0 0 42 42" role="img" :aria-label="`${definition.title}，占显示项目合计比例`"><circle cx="21" cy="21" r="15.9155" fill="none" stroke="#edf1ee" stroke-width="6" /><circle v-for="slice in slices" :key="slice.row.key" cx="21" cy="21" r="15.9155" fill="none" :stroke="slice.color" stroke-width="6" :stroke-dasharray="`${slice.percent} ${100 - slice.percent}`" :stroke-dashoffset="25 - slice.offset"><title>{{ slice.row.label }}：{{ numeric(valueOf(slice.row)) }}</title></circle></svg><div><p v-for="slice in slices" :key="slice.row.key"><i :style="{ background: slice.color }" />{{ slice.row.label }} · {{ numeric(slice.percent) }}%</p><small>占图中显示项目的比例；全零时不显示扇区。</small></div></div>
        <div class="report-table"><table><thead><tr><th v-for="dimension in groupColumns" :key="dimension">{{ groupLabel(dimension) }}</th><th v-if="monetary">{{ definition.source === 'cash' ? '金额（人民币折算参考）' : definition.source === 'actual_cash' ? '金额（银行实际人民币净额）' : '金额（人民币）' }}</th><th>去重单据 / 档案数</th><th v-if="['sales', 'purchase', 'inventory'].includes(definition.source)">数量（按单位）</th><th v-if="['sales', 'purchase'].includes(definition.source)">操作</th></tr></thead><tbody><tr v-for="row in visibleRows" :key="row.key"><td v-for="(group,index) in rowGroups(row)" :key="group.dimension"><button v-if="group.dimension !== 'time'" class="report-link" @click="drill(row,index)">{{ group.label }}</button><span v-else>{{ group.label }}</span></td><td v-if="monetary">{{ row.amount === null ? '成本待核实' : numeric(row.amount) }}</td><td>{{ row.count }}</td><td v-if="['sales', 'purchase', 'inventory'].includes(definition.source)">{{ quantityText(row.quantities) }}</td><td v-if="['sales', 'purchase'].includes(definition.source)"><button type="button" class="detail-link" @click.stop="openDetails(row)">查看构成明细</button></td></tr></tbody></table></div>
        <footer class="report-pagination"><span>共 {{ rows.length }} 项<span v-if="definition.group_by !== 'time' || multiDimensional"> · 点击分组继续下钻</span></span><button :disabled="page <= 1" @click="page--">上一页</button><span>{{ page }} / {{ Math.max(1, Math.ceil(rows.length / 15)) }}</span><button :disabled="page * 15 >= rows.length" @click="page++">下一页</button></footer>
        <ReportDetailPanel v-if="detailSelection" :key="detailKey" :query="detailQuery" :selection="detailSelection" :source-label="definition.source === 'purchase' ? '采购 / 供应商报表' : '销售报表'" @close="detailSelection = null" />
      </template>
    </template>
    <p v-if="exportError" class="report-error" role="alert">{{ exportError }}</p>
    <p v-if="exportNotice" class="export-notice" role="status">{{ exportNotice }}</p>
  </article>
</template>

<style scoped>
.report-block{background:white;border:1px solid #dfe7e2;border-radius:16px;padding:24px;min-width:0}.block-header,.block-actions,.chart-caption,.report-pagination{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.block-header{justify-content:space-between}.block-header h2{font-size:var(--text-section);margin:6px 0 18px}.block-header small,.report-caption,.chart-caption span,.report-pagination,.report-donut small{color:#697d74;font-size:var(--text-caption)}.report-block select,.report-block button{padding:7px 10px;border:1px solid #d7e2db;border-radius:7px;background:#fff;color:#265d4d;cursor:pointer}.report-block button:disabled{opacity:.45;cursor:default}.block-kpis{display:flex;gap:30px;flex-wrap:wrap;padding:18px;background:#f5f8f5;border-radius:10px}.block-kpis small{display:block;color:#687b71;font-size:var(--text-caption)}.block-kpis strong{display:block;font-size:var(--text-metric);margin-top:8px}.block-kpis .quantity-kpi{font-size:var(--text-dialog);max-width:360px}.report-caption{line-height:1.8}.report-note{font-size:var(--text-caption);color:#627066;background:#faf9f4;padding:12px;line-height:1.8;border-radius:8px}.report-empty{padding:40px;text-align:center;color:#77877e}.chart-caption{margin:24px 0 18px;font-size:var(--text-caption);justify-content:space-between}.report-bar-row{display:grid;grid-template-columns:minmax(90px,180px) 1fr 100px;align-items:center;gap:12px;margin:9px 0;font-size:var(--text-caption)}.report-bar-row .bar-label{border:0;padding:0;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bar-track{height:14px;background:#f1f5f2;border-radius:3px;overflow:hidden}.bar-track div{height:100%;background:#358a75;border-radius:3px}.bar-track div.negative{background:#c37764}.report-bar-row>span{text-align:right}.report-line svg{width:100%;max-height:280px}.report-line text{font-size:var(--text-caption);fill:#75857a}.report-donut{display:flex;align-items:center;gap:24px;flex-wrap:wrap}.report-donut svg{width:210px;height:210px}.report-donut p{font-size:var(--text-caption);margin:8px 0}.report-donut i{display:inline-block;width:9px;height:9px;margin-right:8px;border-radius:50%}.report-table{overflow:auto;margin-top:24px}.report-table table{width:100%;border-collapse:collapse;font-size:var(--text-body)}.report-table th,.report-table td{padding:12px;text-align:left;border-bottom:1px solid #edf1ed;white-space:nowrap}.report-table th{background:#f6f8f5;color:#68776c}.report-table .report-link{border:0;background:none;padding:0;text-align:left}.report-pagination{justify-content:flex-end;margin-top:15px}.report-pagination>span:first-child{margin-right:auto}.report-error{color:#a34636;padding:24px}@media(max-width:650px){.report-block{padding:16px}.block-kpis{gap:18px}.block-kpis strong{font-size:var(--text-dialog)}.report-bar-row{grid-template-columns:90px 1fr 70px}}

.block-header>div:first-child{min-width:0;flex:1}.block-header h2{overflow-wrap:anywhere;margin:5px 0 8px}.block-header small{letter-spacing:0}.block-kpis{margin-top:16px;gap:18px}.block-kpis>div{min-width:0;flex:1 1 180px}.block-kpis strong{font-size:clamp(22px,2vw,30px);overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.report-note{overflow-wrap:anywhere}.report-bar-row{grid-template-columns:minmax(90px,1.2fr) minmax(50px,2fr) minmax(100px,1fr)}.report-bar-row>span{overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.report-table th:first-child,.report-table td:first-child{white-space:normal;min-width:160px;max-width:320px;overflow-wrap:anywhere}.report-table .report-link{overflow-wrap:anywhere;max-width:100%}.report-table .detail-link{border:1px solid #cfe0d4;background:#f7fbf8;padding:6px 8px;font-size:var(--text-caption);white-space:nowrap}.report-donut>div{flex:1;min-width:160px}.report-donut p{overflow-wrap:anywhere}.report-error{overflow-wrap:anywhere;border:1px solid #edcbc5;border-radius:8px;background:#fff8f5;margin:14px 0 0;padding:14px}.export-notice{color:#28634a;font-size:var(--text-caption)}.report-caption{overflow-wrap:anywhere}.report-pagination>span:first-child{min-width:0;overflow-wrap:anywhere}@media(max-width:1024px){.report-block{padding:18px}.block-header{align-items:flex-start}.block-actions{justify-content:flex-end;gap:8px}.report-bar-row{grid-template-columns:minmax(90px,1fr) minmax(35px,1fr) minmax(100px,1fr)}}
</style>
