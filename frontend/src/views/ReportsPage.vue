<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import ReportBlock from '../components/reports/ReportBlock.vue'
import { reportBlocks, datePreset } from '../reports/registry'

const catalog = ref(null), error = ref(''), notice = ref(''), refreshKey = ref(0)
const form = reactive({ ...datePreset('year'), source: 'sales', group_by: 'time', grain: 'month', date_field: 'order_date', metric: 'amount', view: 'line', title: '销售趋势', comparison: 'previous' })
const activeFilters = ref([]), applied = ref(null), appliedFilters = ref({}), preset = ref('sales-trend')
const sourceSpec = computed(() => catalog.value?.sources[form.source])
const filterDimension = ref(''), filterValue = ref('__pick__'), filterOptions = ref([]), optionsLoading = ref(false)
const storageKey = 'senju-report-blocks-v1'
const saved = ref([])
const datePresets = { today: '今天', week: '本周', month: '本月', quarter: '本季度', year: '本年', 'last-month': '上月', 'last-year': '去年', 30: '近30天', 90: '近90天' }
function apply() {
  if (!form.date_from || !form.date_to || form.date_from > form.date_to) { error.value = '请填写有效起止日期。'; return }
  error.value = ''
  applied.value = { source: form.source, group_by: form.group_by, grain: form.grain, date_field: form.date_field, metric: form.metric, view: form.view, title: form.title, comparison: form.comparison }
  appliedFilters.value = { date_from: form.date_from, date_to: form.date_to, ...Object.fromEntries(activeFilters.value.map(item => [`filter_${item.dimension}`, item.value])) }
  refreshKey.value++
}
function chooseDates(key) { Object.assign(form, datePreset(key)); filterOptions.value = []; apply() }
function sourceChanged() {
  optionsSequence++; optionsLoading.value = false; filterValue.value = '__pick__'
  form.date_field = Object.keys(sourceSpec.value.dates)[0]; form.group_by = 'time'
  form.metric = form.source === 'customers' ? 'count' : form.source === 'inventory' ? 'quantity' : 'amount'
  form.title = sourceSpec.value.label; activeFilters.value = []; filterDimension.value = ''; filterOptions.value = []; preset.value = ''
}
function choosePreset() {
  const block = reportBlocks[preset.value]
  if (!block) return
  form.source = block.source; sourceChanged()
  Object.assign(form, block)
  preset.value = Object.keys(reportBlocks).find(key => reportBlocks[key] === block)
  apply()
}
let optionsSequence = 0
async function loadOptions() {
  const current = ++optionsSequence
  filterOptions.value = []; filterValue.value = '__pick__'
  if (!filterDimension.value) return
  optionsLoading.value = true
  try {
    const { data } = await api.get('/reports/data/', { params: { source: form.source, group_by: filterDimension.value, date_field: form.date_field, date_from: form.date_from, date_to: form.date_to } })
    if (current === optionsSequence) filterOptions.value = data.rows
  } catch (err) { if (current === optionsSequence) error.value = err.message }
  finally { if (current === optionsSequence) optionsLoading.value = false }
}
function addFilter() {
  const option = filterOptions.value.find(item => item.key === filterValue.value)
  if (!option) return
  setFilter({ dimension: filterDimension.value, value: option.key, label: option.label })
}
function setFilter(item) { activeFilters.value = [...activeFilters.value.filter(existing => existing.dimension !== item.dimension), item]; apply() }
function drill(item) {
  if (item.source !== form.source) { form.source = item.source; sourceChanged() }
  form.date_field = item.date_field
  activeFilters.value = item.filter_summary || Object.entries(item.filters || {}).map(([dimension, value]) => ({ dimension, value, label: value || '未填写' }))
  setFilter(item)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function persist() {
  try { localStorage.setItem(storageKey, JSON.stringify(saved.value)); notice.value = '图表块设置已保存在当前浏览器。' }
  catch { notice.value = '浏览器无法保存设置；本次会话仍可使用。' }
}
function saveBlock() {
  if (!applied.value) return
  const { date_from, date_to, ...filters } = appliedFilters.value
  saved.value.push({ id: crypto.randomUUID(), config: { ...applied.value, filters } }); persist()
}
function removeBlock(id) { saved.value = saved.value.filter(item => item.id !== id); persist() }
function moveBlock(index, offset) { const target = index + offset; if (target < 0 || target >= saved.value.length) return; [saved.value[index], saved.value[target]] = [saved.value[target], saved.value[index]]; persist() }
const sharedDates = computed(() => ({ date_from: appliedFilters.value.date_from, date_to: appliedFilters.value.date_to }))
onMounted(async () => {
  try {
    catalog.value = (await api.get('/reports/catalog/')).data
    try {
      const entries = JSON.parse(localStorage.getItem(storageKey) || '[]')
      if (Array.isArray(entries)) saved.value = entries.filter(item => item?.id && catalog.value.sources[item.config?.source]?.dimensions.includes(item.config.group_by)).slice(0, 30)
    } catch { notice.value = '已忽略无法读取的旧图表设置。' }
    apply()
  } catch (err) { error.value = err.message }
})
</script>

<template>
  <div class="reports-page">
    <section class="report-intro"><div><small>REPORT LIBRARY</small><h2>从经营全貌，看到每一个维度</h2><p>销售、采购、供应商、客户、现金与库存变动。统一筛选，独立图表块，按需组合。</p></div><RouterLink to="/finance">查看应收应付与财务概览 →</RouterLink></section>
    <p v-if="error" role="alert" class="page-error">{{ error }}</p>
    <p v-if="notice" role="status" class="page-notice">{{ notice }}</p>
    <form v-if="catalog" class="report-controls" @submit.prevent="apply">
      <div class="report-presets"><label>常用报表 <select v-model="preset" @change="choosePreset"><option value="">自定义报表</option><option v-for="(block, key) in reportBlocks" :key="key" :value="key">{{ block.title }}</option></select></label><div class="date-shortcuts"><button v-for="(label, key) in datePresets" :key="key" type="button" @click="chooseDates(key)">{{ label }}</button></div></div>
      <div class="report-control-grid">
        <label>业务模块<select v-model="form.source" @change="sourceChanged"><option v-for="(spec, key) in catalog.sources" :key="key" :value="key">{{ spec.label }}</option></select></label>
        <label>日期口径<select v-model="form.date_field"><option v-for="(label, key) in sourceSpec.dates" :key="key" :value="key">{{ label }}</option></select></label>
        <label>开始日期<input v-model="form.date_from" type="date" required></label><label>结束日期（含当天）<input v-model="form.date_to" type="date" required></label>
        <label>统计维度<select v-model="form.group_by"><option v-for="key in sourceSpec.dimensions" :key="key" :value="key">{{ form.source === 'cash' && key === 'category' ? '收支分类' : catalog.dimensions[key] }}</option></select></label>
        <label>时间粒度<select v-model="form.grain"><option v-for="(label, key) in catalog.grains" :key="key" :value="key">{{ label }}</option></select></label>
        <label>图表指标<select v-model="form.metric"><option v-if="!['customers', 'inventory'].includes(form.source)" value="amount">金额（人民币）</option><option value="count">去重单据 / 档案数</option><option v-if="['sales', 'purchase', 'inventory'].includes(form.source)" value="quantity">数量（按单位）</option></select></label>
        <label>默认图形<select v-model="form.view"><option value="line">折线图</option><option value="bar">条形图</option><option value="donut">环形图</option><option value="table">数据表</option></select></label>
      </div>
      <div class="dimension-filter"><label>附加筛选<select v-model="filterDimension" @change="loadOptions"><option value="">选择维度</option><option v-for="key in sourceSpec.dimensions.filter(key => key !== 'time')" :key="key" :value="key">{{ form.source === 'cash' && key === 'category' ? '收支分类' : catalog.dimensions[key] }}</option></select></label><label>范围内的可用值<select v-model="filterValue" :disabled="optionsLoading"><option value="__pick__">{{ optionsLoading ? '加载中…' : '请选择' }}</option><option v-for="option in filterOptions" :key="option.key" :value="option.key">{{ option.label }}</option></select></label><button type="button" :disabled="!filterDimension || optionsLoading" @click="loadOptions">刷新选项</button><button type="button" :disabled="filterValue === '__pick__'" @click="addFilter">添加筛选</button></div>
      <div v-if="activeFilters.length" class="filter-chips"><button v-for="(item, index) in activeFilters" :key="item.dimension" type="button" @click="activeFilters.splice(index, 1); apply()">{{ catalog.dimensions[item.dimension] }}：{{ item.label }} ×</button><button type="button" @click="activeFilters = []; apply()">清除全部</button></div>
      <div class="report-submit"><label>比较方式<select v-model="form.comparison"><option value="previous">上一等长期间</option><option value="year">去年同期</option></select></label><label>图表块名称<input v-model="form.title" maxlength="80" required></label><button class="primary" type="submit">查询 / 刷新</button><button type="button" :disabled="!applied || saved.length >= 30" @click="saveBlock">将当前查询保存为图表块</button><span>最多保存 30 块；日期由本页统一控制。</span></div>
    </form>
    <ReportBlock v-if="applied" :config="applied" :filters="appliedFilters" :refresh-key="refreshKey" @drill="drill" />
    <section class="saved-heading"><h2>我的图表块 <span>{{ saved.length }}</span></h2><p>独立保存模块、维度、指标和附加筛选；跟随查询后的起止日期。设置仅保存在当前浏览器。</p></section>
    <div v-if="!saved.length" class="saved-empty">从上方选择常用报表，或配置自己的统计方式，再保存为图表块。</div>
    <div v-for="(block, index) in saved" :key="block.id" class="saved-block"><div class="saved-actions"><span>{{ index + 1 }} / {{ saved.length }}</span><button :disabled="index === 0" @click="moveBlock(index, -1)">上移</button><button :disabled="index === saved.length - 1" @click="moveBlock(index, 1)">下移</button><button @click="removeBlock(block.id)">移除</button></div><ReportBlock :config="block.config" :filters="sharedDates" :refresh-key="refreshKey" @drill="drill" /></div>
  </div>
</template>

<style scoped>
.reports-page{display:grid;gap:22px}.report-intro{display:flex;align-items:center;justify-content:space-between;gap:24px;background:#eaf1e9;padding:26px;border-radius:16px;flex-wrap:wrap}.report-intro small{letter-spacing:2px;color:#60816c;font-size:var(--text-caption)}.report-intro h2{font-size:var(--text-section);margin:10px 0}.report-intro p,.saved-heading p{color:#6c7d70;font-size:var(--text-body);line-height:1.8;margin:0}.report-intro a{color:#32684d;font-size:var(--text-body)}.report-controls{background:white;border:1px solid #dfe7e2;padding:22px;border-radius:16px}.report-presets,.date-shortcuts,.dimension-filter,.report-submit,.filter-chips,.saved-actions{display:flex;align-items:end;gap:10px;flex-wrap:wrap}.report-presets{justify-content:space-between;margin-bottom:20px}.reports-page label{display:flex;flex-direction:column;gap:7px;font-size:var(--text-caption);color:#5d7164}.reports-page input,.reports-page select{background:white;border:1px solid #d5dfd6;border-radius:7px;padding:9px 10px;min-width:0;color:#314a3c}.report-control-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px}.reports-page button{border:1px solid #d5dfd6;border-radius:7px;padding:9px 12px;background:white;color:#365d47;cursor:pointer;font-size:var(--text-body)}.reports-page button:disabled{opacity:.4;cursor:default}.date-shortcuts button{padding:7px 10px}.dimension-filter{margin-top:20px;padding-top:18px;border-top:1px solid #edf1ed}.dimension-filter select{max-width:280px;min-width:155px}.filter-chips{margin-top:12px}.filter-chips button{background:#edf4eb}.report-submit{margin-top:20px}.report-submit .primary{background:#286c52;color:white;border-color:#286c52}.report-submit span{font-size:var(--text-caption);color:#859183}.saved-heading h2{font-size:var(--text-section);margin-bottom:7px}.saved-heading span{font-size:var(--text-body);color:#7c917f}.saved-empty{padding:35px;text-align:center;border:1px dashed #c7d4c8;border-radius:14px;color:#7a8a7c;font-size:var(--text-body)}.saved-actions{justify-content:flex-end;margin-bottom:8px}.saved-actions span{font-size:var(--text-caption);color:#7a8a7c;margin-right:auto}.page-error{color:#a54335}.page-notice{font-size:var(--text-caption);color:#507250;margin:0}@media(max-width:1000px){.report-control-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:580px){.report-control-grid{grid-template-columns:1fr}.report-intro h2{font-size:var(--text-section)}}
</style>
