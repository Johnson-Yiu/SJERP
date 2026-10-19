<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { apiErrorMessage } from '../utils/apiErrors'
import { useAccessControl } from '../accessControl'
import ReportBlock from '../components/reports/ReportBlock.vue'
import { reportBlocks, datePreset, canViewReportSource, canViewReportDimension, canViewReportConfig } from '../reports/registry'

const route = useRoute(), router = useRouter(), { can } = useAccessControl()
const catalog = ref(null), catalogLoading = ref(false), catalogError = ref(''), formError = ref(''), notice = ref(''), storageError = ref(''), refreshKey = ref(0)
const form = reactive({ ...datePreset('year'), source: 'sales', group_by: 'time', grain: 'month', date_field: 'order_date', metric: 'amount', view: 'line', title: '销售趋势', comparison: 'previous' })
const activeFilters = ref([]), applied = ref(null), appliedFilters = ref({}), preset = ref('sales-trend'), appliedLabels = ref([]), drillHistory = ref([])
const availableSources = computed(() => Object.fromEntries(Object.entries(catalog.value?.sources || {}).filter(([source]) => canViewReportSource(source, can))))
const availablePresets = computed(() => Object.fromEntries(Object.entries(reportBlocks).filter(([,block]) => availableSources.value[block.source]?.dimensions.includes(block.group_by) && canViewReportDimension(block.group_by, can))))
const sourceSpec = computed(() => catalog.value?.sources[form.source])
const dimensions = computed(() => (sourceSpec.value?.dimensions || []).filter(key => canViewReportDimension(key, can)))
const filterDimension = ref(''), filterValue = ref('__pick__'), filterOptions = ref([]), optionsLoading = ref(false), optionsError = ref('')
const storageKey = 'senju-report-blocks-v1', saved = ref([]), removedBlock = ref(null)
const datePresets = { today: '今天', week: '本周至今', month: '本月至今', quarter: '本季度至今', year: '本年至今', 'last-month': '上月', 'last-year': '去年', 30: '近30天', 90: '近90天' }
const configKeys = ['source', 'group_by', 'grain', 'date_field', 'metric', 'view', 'title', 'comparison']
const queryKeys = [...configKeys, 'date_from', 'date_to']
const clone = value => JSON.parse(JSON.stringify(value))
function draftConfig() { return Object.fromEntries(configKeys.map(key => [key, form[key]])) }
watch(() => [form.source, form.group_by, form.metric, form.view, form.title], () => {
  const block = availablePresets.value[preset.value]
  if (block && (block.source !== form.source || block.group_by !== form.group_by || block.view !== form.view || block.title !== form.title || (block.metric || 'amount') !== form.metric)) preset.value = ''
})
function draftFilters() { return { date_from: form.date_from, date_to: form.date_to, ...Object.fromEntries(activeFilters.value.map(item => [`filter_${item.dimension}`, item.value])) } }
const dirty = computed(() => applied.value && (JSON.stringify(draftConfig()) !== JSON.stringify(applied.value) || JSON.stringify(draftFilters()) !== JSON.stringify(appliedFilters.value)))
const rangeError = computed(() => !form.date_from || !form.date_to ? '请填写完整起止日期。' : form.date_from > form.date_to ? '开始日期不能晚于结束日期。' : '')
const sharedDates = computed(() => ({ date_from: appliedFilters.value.date_from, date_to: appliedFilters.value.date_to }))
const querySignature = computed(() => JSON.stringify(Object.entries(route.query).filter(([key]) => queryKeys.includes(key) || key.startsWith('filter_')).sort(([a],[b])=>a.localeCompare(b))))
function dimensionLabel(key, source = form.source) { return source === 'cash' && key === 'category' ? '收支分类' : catalog.value?.dimensions[key] || key }
function apply({ syncRoute = true, keepHistory = false } = {}) {
  if (rangeError.value) { formError.value = rangeError.value; return false }
  if (!form.title.trim()) { formError.value = '请填写图表名称。'; return false }
  const allowedMetrics = form.source === 'customers' ? ['count'] : form.source === 'inventory' ? ['count', 'quantity'] : ['amount', 'count', ...(form.source === 'profit' || form.source === 'cash' || form.source === 'actual_cash' ? [] : ['quantity'])]
  if (!sourceSpec.value?.dimensions.includes(form.group_by) || !sourceSpec.value?.dates[form.date_field] || !allowedMetrics.includes(form.metric)) { formError.value = '所选维度、日期口径或指标不适用于当前来源，请重新选择。'; return false }
  if (!sourceSpec.value || !canViewReportConfig({ ...draftConfig(), filters: draftFilters() }, can)) { formError.value = '当前账号没有所选数据来源或筛选维度的查看权限。'; return false }
  formError.value = ''; notice.value = ''
  applied.value = draftConfig(); appliedFilters.value = draftFilters(); appliedLabels.value = clone(activeFilters.value); refreshKey.value++
  if (!keepHistory) drillHistory.value = []
  if (syncRoute) {
    const query = { ...route.query }
    for (const key of Object.keys(query)) if (queryKeys.includes(key) || key.startsWith('filter_')) delete query[key]
    Object.assign(query, applied.value, appliedFilters.value)
    void router.replace({ path: route.path, query, hash: route.hash })
  }
  return true
}
function submitQuery() { apply() }
function chooseDates(key) { Object.assign(form, datePreset(key)) }
function sourceChanged() {
  invalidateOptions()
  if (!sourceSpec.value) return
  form.date_field = Object.keys(sourceSpec.value.dates)[0]; form.group_by = 'time'
  form.metric = form.source === 'customers' ? 'count' : form.source === 'inventory' ? 'quantity' : 'amount'
  form.title = sourceSpec.value.label; activeFilters.value = []; filterDimension.value = ''; preset.value = ''; formError.value = ''
}
function choosePreset() {
  const block = availablePresets.value[preset.value]
  if (!block) return
  const id = preset.value
  form.source = block.source; sourceChanged(); Object.assign(form, block); preset.value = id
}
let optionsSequence = 0
function invalidateOptions() { optionsSequence++; filterOptions.value = []; filterValue.value = '__pick__'; optionsLoading.value = false; optionsError.value = '' }
watch([() => form.source, () => form.date_field, () => form.date_from, () => form.date_to], invalidateOptions)
async function loadOptions() {
  const current = ++optionsSequence
  filterOptions.value = []; filterValue.value = '__pick__'; optionsError.value = ''
  if (!filterDimension.value || rangeError.value) { optionsLoading.value = false; optionsError.value = rangeError.value; return }
  optionsLoading.value = true
  try {
    const { data } = await api.get('/reports/data/', { params: { source: form.source, group_by: filterDimension.value, date_field: form.date_field, date_from: form.date_from, date_to: form.date_to } })
    if (current === optionsSequence) filterOptions.value = data.rows
  } catch (err) { if (current === optionsSequence) optionsError.value = apiErrorMessage(err) || '筛选选项加载失败，请重试。' }
  finally { if (current === optionsSequence) optionsLoading.value = false }
}
function addFilter() {
  const option = filterOptions.value.find(item => String(item.key) === String(filterValue.value))
  if (!option) return
  setFilter({ dimension: filterDimension.value, value: String(option.key), label: option.label })
}
function setFilter(item) { activeFilters.value = [...activeFilters.value.filter(existing => existing.dimension !== item.dimension), item] }
function snapshot() { return clone({ form, activeFilters: activeFilters.value, applied: applied.value, appliedFilters: appliedFilters.value, appliedLabels: appliedLabels.value, preset: preset.value }) }
function drill(item) {
  if (!item.config || !item.period) return
  drillHistory.value.push(snapshot())
  if (item.source !== form.source) { form.source = item.source; sourceChanged() }
  Object.assign(form, Object.fromEntries(configKeys.map(key => [key,item.config[key] ?? form[key]])), item.period)
  form.date_field = item.date_field; preset.value = ''; invalidateOptions(); filterDimension.value = ''
  activeFilters.value = clone(item.filter_summary || Object.entries(item.filters || {}).map(([dimension, value]) => ({ dimension, value, label: value || '未填写' })))
  setFilter({ dimension: item.dimension, value: String(item.value), label: item.label })
  apply({ keepHistory: true })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function previousDrill() {
  const previous = drillHistory.value.pop()
  if (!previous) return
  Object.assign(form, previous.form); activeFilters.value = previous.activeFilters; preset.value = previous.preset
  applied.value = previous.applied; appliedFilters.value = previous.appliedFilters; appliedLabels.value = previous.appliedLabels; refreshKey.value++; invalidateOptions(); formError.value = ''
  const query = { ...route.query }
  for (const key of Object.keys(query)) if (queryKeys.includes(key) || key.startsWith('filter_')) delete query[key]
  Object.assign(query, applied.value, appliedFilters.value)
  void router.replace({ path: route.path, query, hash: route.hash })
}
function loaded(result) {
  appliedLabels.value = clone(result.filter_summary || [])
  // Resolve labels only for the matching draft values, never replace draft filters.
  for (const item of activeFilters.value) {
    const resolved = result.filter_summary?.find(row => row.dimension === item.dimension && String(row.value) === String(item.value))
    if (resolved) item.label = resolved.label
  }
}
function persist(message) {
  notice.value = ''; storageError.value = ''
  try { localStorage.setItem(storageKey, JSON.stringify(saved.value)); notice.value = `${message} 设置仅保存在当前浏览器。` }
  catch { storageError.value = '浏览器无法保存设置；刷新页面后可能丢失本次修改。' }
}
function saveBlock() {
  if (!applied.value || dirty.value || saved.value.length >= 30) return
  const { date_from, date_to, ...filters } = appliedFilters.value
  saved.value.push({ id: crypto.randomUUID(), config: { ...applied.value, filters } }); persist('图表块已保存。')
}
function restoreBlock(block) {
  if (!canViewReportConfig(block.config, can)) return
  form.source = block.config.source; sourceChanged()
  Object.assign(form, Object.fromEntries(configKeys.filter(key=>block.config[key]!=null).map(key=>[key,block.config[key]])))
  activeFilters.value = Object.entries(block.config.filters || {}).filter(([key]) => key.startsWith('filter_')).map(([key,value]) => ({ dimension:key.slice(7),value:String(value),label:String(value) || '未填写' }))
  apply(); notice.value = '已载入图表配置，沿用本页日期。'; window.scrollTo({top:0,behavior:'smooth'})
}
function removeBlock(id) { const index = saved.value.findIndex(item=>item.id===id); removedBlock.value = {index,block:saved.value[index]}; saved.value.splice(index,1); persist('图表块已移除。') }
function undoRemove() { if (!removedBlock.value || saved.value.length>=30) return; saved.value.splice(Math.min(removedBlock.value.index,saved.value.length),0,removedBlock.value.block); removedBlock.value=null; persist('图表块已恢复。') }
function moveBlock(index, offset) { const target = index + offset; if (target < 0 || target >= saved.value.length) return; [saved.value[index], saved.value[target]] = [saved.value[target], saved.value[index]]; persist('图表块顺序已保存。') }
function hydrateRoute() {
  const value = key => Array.isArray(route.query[key]) ? route.query[key][0] : route.query[key]
  const source = value('source') || (availableSources.value.sales ? 'sales' : Object.keys(availableSources.value)[0])
  if (!availableSources.value[source]) { formError.value = '地址中的报表来源当前不可查看，请重新选择查询。'; applied.value = null; return }
  Object.assign(form, datePreset('year'), { source, group_by: 'time', grain: 'month', metric: 'amount', view: 'line', comparison: 'previous' })
  sourceChanged()
  if (source === 'sales') form.title = '销售趋势'
  for(const key of configKeys) if(typeof value(key)==='string') form[key]=value(key)
  for(const key of ['date_from','date_to']) if(typeof value(key)==='string') form[key]=value(key)
  if (!sourceSpec.value.dimensions.includes(form.group_by) || !sourceSpec.value.dates[form.date_field] || !catalog.value.grains[form.grain] || !['amount','count','quantity'].includes(form.metric) || !['line','bar','donut','table'].includes(form.view) || !['previous','year'].includes(form.comparison)) { formError.value='地址中的报表条件无效，请调整后查询。'; applied.value=null; return }
  if (Object.keys(route.query).some(key => key.startsWith('filter_') && (key === 'filter_time' || !sourceSpec.value.dimensions.includes(key.slice(7))))) { formError.value = '地址中的附加筛选不适用于当前来源，请重新选择。'; applied.value = null; return }
  preset.value = Object.keys(availablePresets.value).find(key => { const block = availablePresets.value[key]; return block.source === form.source && block.group_by === form.group_by && block.view === form.view && block.title === form.title && (block.metric || 'amount') === form.metric }) || ''
  activeFilters.value = Object.entries(route.query).filter(([key])=>key.startsWith('filter_') && sourceSpec.value.dimensions.includes(key.slice(7))).map(([key])=>({dimension:key.slice(7),value:String(value(key)),label:String(value(key))||'未填写'}))
  apply({syncRoute:false})
}
watch(querySignature, () => {
  if (!catalog.value || !Object.keys(availableSources.value).length) return
  if (!applied.value) { hydrateRoute(); return }
  const current = JSON.stringify(Object.entries({...applied.value,...appliedFilters.value}).map(([key,value])=>[key,String(value)]).sort(([a],[b])=>a.localeCompare(b)))
  if (current !== querySignature.value) hydrateRoute()
})
async function loadCatalog() {
  if (catalogLoading.value) return
  catalogLoading.value=true; catalogError.value=''
  try {
    catalog.value=(await api.get('/reports/catalog/')).data
    const first=Object.keys(availableSources.value)[0]
    if (!first) { applied.value=null; return }
    if (!availableSources.value[form.source]) { form.source=first; sourceChanged() }
    try {
      const entries=JSON.parse(localStorage.getItem(storageKey)||'[]')
      if(Array.isArray(entries)) saved.value=entries.filter(item=>item?.id && catalog.value.sources[item.config?.source]?.dimensions.includes(item.config.group_by)).slice(0,30)
    } catch { storageError.value='无法读取旧图表设置；本次可重新配置。' }
    hydrateRoute()
  } catch(err) { catalogError.value=apiErrorMessage(err)||'报表选项加载失败，请重试。' }
  finally { catalogLoading.value=false }
}
onMounted(loadCatalog)
</script>

<template>
  <div class="reports-page">
    <header class="report-intro"><p>选择报表与日期，查询后可继续筛选或保存图表。</p><RouterLink v-if="can('finance','view')" to="/finance">财务概览 →</RouterLink></header>
    <p v-if="catalogLoading" role="status" class="page-loading">正在加载报表选项…</p>
    <div v-if="catalogError" role="alert" class="page-error">{{ catalogError }}<button type="button" @click="loadCatalog">重新加载</button></div>
    <p v-if="storageError" role="alert" class="page-error">{{ storageError }}</p>
    <p v-if="notice" role="status" class="page-notice">{{ notice }}<button v-if="removedBlock" type="button" :disabled="saved.length>=30" @click="undoRemove">撤销移除</button></p>
    <p v-if="catalog && !Object.keys(availableSources).length" role="status" class="saved-empty">当前账号没有可查看的报表数据来源。</p>
    <form v-if="catalog && sourceSpec && Object.keys(availableSources).length" class="report-controls" aria-label="报表查询" @submit.prevent="submitQuery">
      <fieldset><legend>1. 选择报表</legend><div class="report-presets"><label>报表预设<select v-model="preset" @change="choosePreset"><option value="">自定义查询</option><option v-for="(block,key) in availablePresets" :key="key" :value="key">{{ block.title }}</option></select></label><p>选择预设后可调整条件，再点击“查询报表”。</p></div>
      <div class="report-control-grid"><label>数据来源<select v-model="form.source" @change="sourceChanged"><option v-for="(spec,key) in availableSources" :key="key" :value="key">{{ spec.label }}</option></select></label><label>统计维度<select v-model="form.group_by"><option v-for="key in dimensions" :key="key" :value="key">{{ dimensionLabel(key) }}</option></select></label><label>图表指标<select v-model="form.metric"><option v-if="!['customers','inventory'].includes(form.source)" value="amount">{{ form.source === 'cash' ? '金额（人民币折算参考）' : form.source === 'actual_cash' ? '金额（银行实际人民币净额）' : '金额（人民币）' }}</option><option value="count">去重单据 / 档案数</option><option v-if="['sales','purchase','inventory'].includes(form.source)" value="quantity">数量（按单位）</option></select></label><label>图表类型<select v-model="form.view"><option value="line">折线图</option><option value="bar">条形图</option><option value="donut">环形图</option><option value="table">数据表</option></select></label></div></fieldset>
      <fieldset><legend>2. 日期与比较</legend><div class="date-shortcuts" aria-label="日期快捷选择"><button v-for="(label,key) in datePresets" :key="key" type="button" @click="chooseDates(key)">{{ label }}</button></div><div class="report-control-grid"><label>日期口径<select v-model="form.date_field"><option v-for="(label,key) in sourceSpec.dates" :key="key" :value="key">{{ label }}</option></select></label><label>开始日期<input v-model="form.date_from" type="date" required></label><label>结束日期（含当天）<input v-model="form.date_to" type="date" required></label><label>比较方式<select v-model="form.comparison"><option value="previous">上一等长期间</option><option value="year">去年同期</option></select></label><label>时间粒度<select v-model="form.grain" :disabled="form.group_by !== 'time'"><option v-for="(label,key) in catalog.grains" :key="key" :value="key">{{ label }}</option></select></label></div><p class="source-note">{{ sourceSpec.note }}</p></fieldset>
      <fieldset><legend>3. 附加筛选</legend><div class="dimension-filter"><label>筛选维度<select v-model="filterDimension" @change="loadOptions"><option value="">选择维度</option><option v-for="key in dimensions.filter(key=>key!=='time')" :key="key" :value="key">{{ dimensionLabel(key) }}</option></select></label><label>可用值<select v-model="filterValue" :disabled="optionsLoading || !filterOptions.length"><option value="__pick__">{{ optionsLoading ? '加载中…' : '请选择' }}</option><option v-for="option in filterOptions" :key="option.key" :value="option.key">{{ option.label }}</option></select></label><button type="button" :disabled="!filterDimension || optionsLoading" @click="loadOptions">刷新选项</button><button type="button" :disabled="filterValue === '__pick__'" @click="addFilter">添加筛选</button></div><p v-if="optionsError" class="page-error" role="alert">{{ optionsError }}</p><p v-else-if="filterDimension && !optionsLoading && !filterOptions.length" class="option-note">当前日期口径下没有可用值；调整日期后可刷新选项。</p><div v-if="activeFilters.length" class="filter-chips" aria-label="待查询筛选条件"><button v-for="(item,index) in activeFilters" :key="item.dimension" type="button" :aria-label="`移除${dimensionLabel(item.dimension)}筛选`" @click="activeFilters.splice(index,1)">{{ dimensionLabel(item.dimension) }}：{{ item.label }} ×</button><button type="button" @click="activeFilters=[]">清除全部</button></div></fieldset>
      <div class="report-submit"><label>图表名称<input v-model="form.title" maxlength="80" required></label><button class="primary" type="submit">查询报表</button><button type="button" :disabled="!applied || !!dirty || saved.length>=30" @click="saveBlock">保存为图表块</button><span>最多 30 块，仅当前浏览器可用。</span></div><p v-if="formError" role="alert" class="page-error">{{ formError }}</p><p v-if="dirty" role="status" class="draft-note">条件已修改，当前图表仍显示上次查询结果；请查询后再保存。</p>
    </form>
    <section v-if="applied" class="applied-summary" aria-label="已查询条件"><div><strong>当前查询</strong><p>{{ catalog.sources[applied.source].label }} · {{ dimensionLabel(applied.group_by,applied.source) }} · {{ catalog.sources[applied.source].dates[applied.date_field] }} · {{ appliedFilters.date_from }} — {{ appliedFilters.date_to }}</p><p v-if="Object.keys(appliedFilters).some(key=>key.startsWith('filter_'))">附加筛选：{{ Object.entries(appliedFilters).filter(([key])=>key.startsWith('filter_')).map(([key,value])=>`${dimensionLabel(key.slice(7),applied.source)}：${appliedLabels.find(item=>item.dimension===key.slice(7)&&String(item.value)===String(value))?.label || value || '未填写'}`).join('；') }}</p></div><button v-if="drillHistory.length" type="button" @click="previousDrill">返回上次分析</button></section>
    <ReportBlock v-if="applied" :config="applied" :filters="appliedFilters" :refresh-key="refreshKey" @drill="drill" @loaded="loaded" />
    <section class="saved-heading"><h2>我的图表块 <span>{{ saved.length }} / 30</span></h2><p>保存来源、维度、指标和筛选；日期跟随本页已查询条件。设置仅在当前浏览器保存。</p></section>
    <p v-if="!saved.length" class="saved-empty">查询后点击“保存为图表块”，下次打开可继续使用。</p>
    <div v-for="(block,index) in saved" :key="block.id" class="saved-block"><div class="saved-actions"><span>图表 {{ index+1 }} / {{ saved.length }}</span><button type="button" :disabled="!canViewReportConfig(block.config,can)" @click="restoreBlock(block)">载入查询</button><button type="button" :disabled="index===0" @click="moveBlock(index,-1)">上移</button><button type="button" :disabled="index===saved.length-1" @click="moveBlock(index,1)">下移</button><button type="button" @click="removeBlock(block.id)">移除</button></div><ReportBlock v-if="applied" :config="block.config" :filters="sharedDates" :refresh-key="refreshKey" @drill="drill" /></div>
  </div>
</template>

<style scoped>
.reports-page{display:grid;gap:18px;min-width:0}.report-intro{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}.report-intro p{margin:0;color:#60756a}.report-intro a{color:#32684d;font-size:var(--text-body);text-decoration:none}.report-controls{background:#fff;border:1px solid #dfe7e2;padding:22px;border-radius:14px;min-width:0}.report-controls fieldset{min-width:0;margin:0 0 20px;padding:16px;border:1px solid #e4ebe5;border-radius:10px}.report-controls legend{padding:0 7px;color:#315b47;font-size:var(--text-body);font-weight:700}.reports-page label{display:flex;flex-direction:column;gap:6px;font-size:var(--text-caption);color:#5d7164;min-width:0}.reports-page input,.reports-page select{box-sizing:border-box;width:100%;height:40px;background:#fff;border:1px solid #d5dfd6;border-radius:7px;padding:0 10px;min-width:0;max-width:100%;color:#314a3c;font:inherit}.reports-page button{border:1px solid #d5dfd6;border-radius:7px;padding:9px 12px;background:#fff;color:#365d47;cursor:pointer;font-size:var(--text-body)}.reports-page button:disabled{opacity:.45;cursor:default}.report-control-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.report-presets{display:flex;align-items:end;gap:18px;margin-bottom:16px;flex-wrap:wrap}.report-presets label{width:min(300px,100%)}.report-presets p,.source-note,.option-note,.report-submit>span{font-size:var(--text-caption);line-height:1.7;color:#718377;margin:0}.source-note{margin-top:14px;padding:10px 12px;background:#f6f8f5;border-radius:7px;overflow-wrap:anywhere}.date-shortcuts{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}.date-shortcuts button{padding:6px 10px;font-size:var(--text-caption)}.dimension-filter{display:grid;grid-template-columns:minmax(140px,1fr) minmax(180px,2fr) auto auto;gap:10px;align-items:end}.dimension-filter button{min-height:40px;white-space:nowrap}.filter-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.filter-chips button{background:#eef5f0;text-align:left;max-width:100%;overflow-wrap:anywhere}.report-submit{display:flex;align-items:end;gap:10px;flex-wrap:wrap}.report-submit label{flex:1 1 200px;max-width:400px}.report-submit>button{min-height:40px}.report-submit .primary{background:#286c52;color:#fff;border-color:#286c52}.draft-note{padding:10px 12px;background:#fff7e9;border-radius:7px;color:#826431;font-size:var(--text-caption);margin-bottom:0}.applied-summary{display:flex;align-items:center;justify-content:space-between;gap:16px;border-left:3px solid #387a60;background:#eef5f0;padding:13px 16px;border-radius:8px;min-width:0}.applied-summary>div{min-width:0}.applied-summary strong{font-size:var(--text-body);color:#2e604a}.applied-summary p{font-size:var(--text-caption);line-height:1.7;margin:5px 0 0;color:#617567;overflow-wrap:anywhere}.applied-summary button{flex:none}.saved-heading h2{font-size:var(--text-section);margin:12px 0 7px;color:#294838}.saved-heading span{font-size:var(--text-body);font-weight:400;color:#718377;margin-left:7px}.saved-heading p{font-size:var(--text-caption);color:#6c7d70;line-height:1.7;margin:0}.saved-empty{padding:30px;text-align:center;border:1px dashed #c7d4c8;border-radius:12px;color:#718377;font-size:var(--text-body);margin:0}.saved-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-bottom:8px}.saved-actions span{margin-right:auto;color:#718377;font-size:var(--text-caption)}.saved-actions button{font-size:var(--text-caption);padding:7px 10px}.page-error{color:#a54335;background:#fff8f5;border:1px solid #edcbc5;border-radius:8px;padding:12px;line-height:1.7;overflow-wrap:anywhere;margin:0}.page-error button{margin-left:12px}.page-notice{font-size:var(--text-body);color:#376747;background:#f0f7f1;padding:12px;border-radius:8px;margin:0;overflow-wrap:anywhere}.page-notice button{margin-left:10px}.page-loading{color:#617567;padding:20px;margin:0}.option-note{margin-top:10px}
@media(max-width:1100px){.report-control-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.dimension-filter{grid-template-columns:minmax(140px,1fr) minmax(180px,2fr)}.dimension-filter button{width:100%}}@media(max-width:650px){.report-controls{padding:16px}.report-controls fieldset{padding:12px}.report-control-grid,.dimension-filter{grid-template-columns:1fr}.applied-summary{align-items:flex-start;flex-wrap:wrap}.report-submit label{max-width:none}.report-submit>button{flex:1}.saved-actions{justify-content:flex-start}.saved-actions span{flex-basis:100%}}
</style>
