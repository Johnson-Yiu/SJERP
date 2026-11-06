<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { BOOK_RMB_NOTE } from '../utils/financeBasis.js'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import PageLoadState from '../components/PageLoadState.vue'
import { useAccessControl } from '../accessControl'
import { apiErrorMessage } from '../utils/apiErrors.js'

const data = ref({ metrics: {}, due_items: [] })
const actualCash = ref(null)
const actualCashLoading = ref(false)
const actualCashError = ref('')
const loading = ref(true)
const error = ref('')
const hasLoaded = ref(false)
const { can } = useAccessControl()
const route = useRoute(), router = useRouter()
const today = new Date().toLocaleDateString('en-CA')
const dateFrom = ref(`${today.slice(0, 7)}-01`), dateTo = ref(today)
const exporting = ref(false), actualCashExporting = ref(false), exportError = ref(''), actualCashExportError = ref(''), notice = ref('')
const drill = ref(null), drillLoading = ref(false), drillError = ref('')
const actualCashEvents = ref(null)
let loadVersion = 0
let actualCashVersion = 0
let drillVersion = 0
const rangeError = computed(() => dateFrom.value && dateTo.value && dateFrom.value > dateTo.value ? '开始日期不能晚于结束日期。' : '')
const periodCards = [
  ['sales_rmb', '合同销售额'], ['estimated_profit_rmb', '预计订单利润'], ['purchase_cost_rmb', '订单采购归属成本'], ['order_expense_rmb', '订单费用'],
  ['income_rmb', '账面收入（折算参考）'], ['expense_rmb', '账面支出（折算参考）'], ['net_cash_rmb', '账面净收支（折算参考）'],
]
const balanceCards = [
  ['receivable_count', '待收笔数', 'count'], ['receivable_rmb', '待收款（人民币折算参考）'], ['payable_count', '待付款笔数', 'count'], ['payable_rmb', '待付款（人民币折算参考）'],
  ['advance_receipt_rmb', '未核销预收款（人民币折算参考）'], ['advance_payment_rmb', '未核销预付款（人民币折算参考）'],
]

function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function canDrill(metric) {
  if (metric === 'sales_rmb' || metric === 'receivable_count' || metric === 'receivable_rmb') return can('orders', 'view')
  if (['purchase_cost_rmb', 'order_expense_rmb', 'estimated_profit_rmb'].includes(metric)) return can('orders', 'view') && can('purchases', 'view')
  if (['payable_count', 'payable_rmb'].includes(metric)) return can('purchases', 'view')
  return can('transactions', 'view')
}
function drillAmount(row) {
  return drill.value?.amount_unit === '笔' ? `${row.amount || 0} 笔` : `¥${money(row.amount)}`
}
function drillBasisLabel(value) {
  return value === 'order_date' ? '订单日期' : value === 'transaction_date' ? '流水发生日期' : '当前余额'
}
async function openDrill(metric, page = 1, sortBy = 'date', sortOrder = 'asc') {
  if (!canDrill(metric) || !data.value.period) return
  const version = ++drillVersion
  drillLoading.value = true
  drillError.value = ''
  try {
    const response = await api.get('/finance-dashboard/details/', { params: { metric, date_from: data.value.period.date_from, date_to: data.value.period.date_to, page, page_size: 50, sort_by: sortBy, sort_order: sortOrder } })
    if (version !== drillVersion) return
    drill.value = response.data
  } catch (err) {
    if (version === drillVersion) drillError.value = apiErrorMessage(err) || '明细加载失败，请刷新后重试。'
  } finally {
    if (version === drillVersion) drillLoading.value = false
  }
}
function closeDrill() { drillVersion += 1; drill.value = null; drillError.value = ''; drillLoading.value = false }
function sortDrill(field) {
  if (!drill.value) return
  const sortOrder = drill.value.sort_by === field && drill.value.sort_order === 'asc' ? 'desc' : 'asc'
  void openDrill(drill.value.metric, 1, field, sortOrder)
}
function showActualCashEvents() { actualCashEvents.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }
async function load() {
  if (rangeError.value) return
  const version = ++loadVersion
  const from = dateFrom.value
  const to = dateTo.value
  loading.value = true
  error.value = ''
  closeDrill()
  const legacyRequest = api.get('/finance-dashboard/', { params: { date_from: from, date_to: to } })
  if (can('transactions', 'view')) void loadActualCash({ from, to })
  else {
    actualCashVersion += 1
    actualCash.value = null
    actualCashError.value = ''
    actualCashLoading.value = false
  }
  try {
    const response = await legacyRequest
    if (version !== loadVersion) return
    data.value = response.data
    hasLoaded.value = true
  } catch (err) {
    if (version === loadVersion) error.value = apiErrorMessage(err) || '财务概览加载失败，请稍后重试。'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}
async function loadActualCash({ from = dateFrom.value, to = dateTo.value } = {}) {
  if (!can('transactions', 'view')) return
  const version = ++actualCashVersion
  actualCashLoading.value = true
  actualCashError.value = ''
  actualCash.value = null
  try {
    const response = await api.get('/actual-rmb-cash/', { params: { date_from: from, date_to: to } })
    if (version !== actualCashVersion) return
    if (response.data?.basis !== 'bank_cash_confirmed_v1') throw new Error('银行实际资金统计口径无效。')
    actualCash.value = response.data
  } catch (err) {
    if (version === actualCashVersion) actualCashError.value = apiErrorMessage(err) || '银行实际资金加载失败，请稍后重试。'
  } finally {
    if (version === actualCashVersion) actualCashLoading.value = false
  }
}
async function applyPeriod() {
  if (rangeError.value) return
  if (route.query.date_from === dateFrom.value && route.query.date_to === dateTo.value) { await load(); return }
  await router.replace({ path: route.path, query: { ...route.query, date_from: dateFrom.value, date_to: dateTo.value }, hash: route.hash })
}
function syncPeriod() {
  if (typeof route.query.date_from === 'string') dateFrom.value = route.query.date_from
  if (typeof route.query.date_to === 'string') dateTo.value = route.query.date_to
}
function resetPeriod() {
  const now = new Date().toLocaleDateString('en-CA')
  dateFrom.value = `${now.slice(0, 7)}-01`; dateTo.value = now
  void applyPeriod()
}
async function exportReport() {
  if (!can('finance', 'export') || exporting.value || !data.value.period) return
  const period = { ...data.value.period }
  exporting.value = true
  exportError.value = ''; notice.value = ''
  try {
    const response = await api.get('/finance-dashboard/', { params: { date_from: period.date_from, date_to: period.date_to, export: 'csv' }, responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `账面收支参考-${period.date_from}-${period.date_to}.csv`; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    notice.value = 'CSV 已开始下载。'
  } catch (err) { exportError.value = apiErrorMessage(err) || '导出失败，请稍后重试。' } finally { exporting.value = false }
}
async function exportActualCash() {
  if (!can('transactions', 'view') || !can('reports', 'export') || !actualCash.value || actualCashExporting.value) return
  const period = { ...actualCash.value.period }
  actualCashExporting.value = true; actualCashExportError.value = ''; notice.value = ''
  try {
    const response = await api.get('/actual-rmb-cash/', { params: { date_from: period.date_from, date_to: period.date_to, export: 'csv' }, responseType: 'blob' })
    const url = URL.createObjectURL(response.data), anchor = document.createElement('a')
    anchor.href = url; anchor.download = `银行实际人民币资金-${period.date_from}-${period.date_to}.csv`; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
    notice.value = '银行实际资金 CSV 已开始下载。'
  } catch (err) { actualCashExportError.value = apiErrorMessage(err) || '银行实际资金导出失败，请稍后重试。' } finally { actualCashExporting.value = false }
}
syncPeriod()
watch(() => [route.query.date_from, route.query.date_to], () => { syncPeriod(); void load() })
onMounted(load)
</script>

<template>
  <section class="finance-page">
    <header><div><p class="page-lede">合同、应收应付和两种资金数据分开显示。合同按订单日期统计，账面收支按流水发生日期统计，银行实际资金按银行实际日期统计；待结与未核销显示当前余额。</p></div><button class="secondary" :disabled="loading" @click="load">刷新数据</button></header>
    <form class="report-filters" aria-label="概览日期范围" @submit.prevent="applyPeriod"><label>开始日期<input v-model="dateFrom" type="date" required></label><label>结束日期<input v-model="dateTo" type="date" required></label><button :disabled="loading || !!rangeError">查询</button><button type="button" class="secondary" @click="resetPeriod">本月至今</button><button v-if="can('finance', 'export')" type="button" class="secondary" :disabled="loading || exporting || !data.period || !!error" @click="exportReport">{{ exporting ? '正在导出…' : '导出 CSV' }}</button></form>
    <p v-if="rangeError" class="error" role="alert">{{ rangeError }}</p>
    <p v-if="exportError" class="error" role="alert">{{ exportError }}</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <p class="definition-note">合同销售额按订单日期，账面收支按流水发生日期。待收、待付按合同汇率折算，未核销预收预付按原流水汇率折算，均为当前参考值。银行实际人民币资金按银行实际日期统计；当前待结与未核销不受所选期间限制。预计订单利润 = 合同销售额 − 采购归属成本 − 订单费用，仅作经营估算。</p>
    <p class="definition-note">{{ data.cash_basis?.note || BOOK_RMB_NOTE }}</p>
    <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="error" @retry="load" />
    <template v-if="hasLoaded">
    <section class="metric-section"><header><div><h3>所选期间</h3><p>{{ data.period?.date_from }} 至 {{ data.period?.date_to }}</p></div></header><div class="cards period-cards">
      <article v-for="[key, label] in periodCards" :key="key"><span>{{ label }}</span><strong>¥{{ money(data.metrics[key]) }}</strong><button v-if="canDrill(key)" type="button" class="metric-drill" :disabled="drillLoading" @click="openDrill(key)">查看构成明细</button></article>
    </div></section>
    <section class="metric-section"><header><div><h3>当前待结与未核销（余额）</h3><p>截至当前的待结与未核销金额，不受所选期间筛选限制</p></div></header><div class="cards balance-cards">
      <article v-for="[key, label, kind] in balanceCards" :key="key"><span>{{ label }}</span><strong>{{ kind === 'count' ? `${data.metrics[key] || 0} 笔` : `¥${money(data.metrics[key])}` }}</strong><button v-if="canDrill(key)" type="button" class="metric-drill" :disabled="drillLoading" @click="openDrill(key)">查看构成明细</button></article>
    </div></section>
    <section v-if="drill || drillLoading || drillError" class="panel finance-drill-panel" aria-label="财务金额构成明细">
      <header class="drill-header"><div><h3>金额构成明细<span v-if="drill"> · {{ drill.title }}</span></h3><p v-if="drill">{{ drill.current_balance ? '当前余额，不受所选期间限制' : `${drill.period.date_from} 至 ${drill.period.date_to}，按${drillBasisLabel(drill.date_basis)}统计` }}</p></div><button type="button" class="secondary" @click="closeDrill">收起明细</button></header>
      <p v-if="drill?.basis_note" class="definition-note">{{ drill.basis_note }}</p>
      <p v-if="drillError" class="error" role="alert">{{ drillError }}</p>
      <p v-else-if="drillLoading" class="definition-note" role="status">正在加载构成明细…</p>
      <template v-else-if="drill">
        <p class="drill-total">明细合计：<strong>{{ drill.amount_unit === '笔' ? `${drill.total_amount || 0} 笔` : `¥${money(drill.total_amount)}` }}</strong> · {{ drill.total_count }} 条记录</p>
        <p v-if="!drill.rows?.length" class="empty-state">当前范围没有可展示的构成记录。</p>
        <table v-else><thead><tr><th><button type="button" class="table-sort" @click="sortDrill('record')">记录</button></th><th><button type="button" class="table-sort" @click="sortDrill('date')">日期</button></th><th>关联对象</th><th>状态</th><th><button type="button" class="table-sort" @click="sortDrill('amount')">金额</button></th><th>构成说明</th><th>操作</th></tr></thead><tbody><tr v-for="row in drill.rows" :key="`${drill.metric}-${row.id}`"><td>{{ row.record_label }}</td><td>{{ row.date || '—' }}</td><td>{{ row.relation_label }}</td><td>{{ row.status_label }}</td><td>{{ drillAmount(row) }}</td><td>{{ row.amount_note || '—' }}</td><td><RouterLink :to="row.detail_url">{{ row.detail_label || '查看原始记录' }}</RouterLink></td></tr></tbody></table>
        <nav v-if="drill.total_count > drill.page_size" class="drill-pagination" aria-label="构成明细分页"><button type="button" class="secondary" :disabled="drill.page <= 1 || drillLoading" @click="openDrill(drill.metric, drill.page - 1, drill.sort_by, drill.sort_order)">上一页</button><span>第 {{ drill.page }} 页 · 每页 {{ drill.page_size }} 条</span><button type="button" class="secondary" :disabled="!drill.has_more || drillLoading" @click="openDrill(drill.metric, drill.page + 1, drill.sort_by, drill.sort_order)">下一页</button></nav>
      </template>
    </section>
    <section v-if="can('transactions', 'view')" class="metric-section actual-cash-section" aria-label="银行实际人民币资金">
      <header><div><h3>{{ actualCash?.events?.some(row => row.id < 0) ? '实际人民币资金（银行与现金）' : '银行实际人民币资金' }}</h3><p>统计已登记、已核实的人民币实际变动，银行与现金分开列示；不代表公司全部银行余额或现金余额。</p></div><div class="header-actions"><button v-if="actualCash" type="button" class="secondary" @click="showActualCashEvents">查看构成明细</button><button v-if="can('reports', 'export')" type="button" class="secondary" :disabled="actualCashLoading || !actualCash || actualCashExporting" @click="exportActualCash">{{ actualCashExporting ? '导出中…' : '导出实际资金 CSV' }}</button></div></header>
      <p v-if="actualCashExportError" class="error" role="alert">{{ actualCashExportError }}</p>
      <p v-if="actualCashError" class="error" role="alert">{{ actualCashError }} <button type="button" class="secondary" @click="loadActualCash">重新加载</button></p>
      <p v-else-if="actualCashLoading" class="definition-note" role="status">正在加载已确认银行资金…</p>
      <template v-else-if="actualCash">
        <p class="definition-note">既有银行事实只统计系统中已登记并人工确认的银行资金事件；新增账户事实时，须核实账户是否自有、实际日期和私有凭证。基准与已核实内部本金不计入公司毛流量。</p>
        <div v-if="actualCash.by_account_type" class="cards actual-cash-cards"><article v-for="row in actualCash.by_account_type" :key="row.account_type"><span>{{ row.label }}净变动</span><strong>¥{{ money(row.net) }}</strong><p>流入 ¥{{ money(row.inflow) }} / 流出 ¥{{ money(row.outflow) }}</p></article></div>
        <p class="definition-note">{{ actualCash.note }} 未设置统计启用日期；本区域不推测未登记资金、期初余额、期末余额或公司全部银行余额。</p>
        <div class="cards actual-cash-cards"><article><span>实际流入</span><strong>¥{{ money(actualCash.totals.inflow) }}</strong></article><article><span>实际流出</span><strong>¥{{ money(actualCash.totals.outflow) }}</strong></article><article><span>净流入 / 净流出</span><strong>¥{{ money(actualCash.totals.net) }}</strong></article><article><span>已确认银行事件</span><strong>{{ actualCash.totals.count }} 笔</strong></article></div>
        <div class="report-tables"><div class="panel"><h3>按银行实际日期汇总</h3><p v-if="!actualCash.monthly?.length">所选期间暂无已确认银行资金。</p><table v-else><thead><tr><th>月份</th><th>流入</th><th>流出</th><th>净流量</th></tr></thead><tbody><tr v-for="row in actualCash.monthly" :key="row.month"><td>{{ row.month }}</td><td>¥{{ money(row.inflow) }}</td><td>¥{{ money(row.outflow) }}</td><td>¥{{ money(row.net) }}</td></tr></tbody></table></div><div class="panel"><h3>按资金类型</h3><p v-if="!actualCash.by_kind?.length">所选期间暂无已确认银行资金。</p><table v-else><thead><tr><th>类型</th><th>流入</th><th>流出</th><th>净流量</th></tr></thead><tbody><tr v-for="row in actualCash.by_kind" :key="row.kind"><td>{{ row.label }}</td><td>¥{{ money(row.inflow) }}</td><td>¥{{ money(row.outflow) }}</td><td>¥{{ money(row.net) }}</td></tr></tbody></table></div></div>
        <div ref="actualCashEvents" class="panel actual-cash-events"><h3>已确认银行资金明细</h3><p v-if="!actualCash.events?.length">所选期间暂无已确认银行资金事件。</p><table v-else><thead><tr><th>银行实际日期</th><th>事件编号</th><th>类型</th><th>方向</th><th>银行实际净额（CNY）</th><th>银行参考号</th><th>操作</th></tr></thead><tbody><tr v-for="row in actualCash.events" :key="row.id"><td>{{ row.bank_date }}</td><td>{{ row.event_no }}</td><td>{{ row.kind_label }}</td><td>{{ row.direction_label }}</td><td>¥{{ money(row.bank_net_amount) }}</td><td>{{ row.bank_reference }}</td><td><RouterLink v-if="row.detail_url" :to="row.detail_url">查看原始事件</RouterLink><span v-else>—</span></td></tr></tbody></table></div>
      </template>
    </section>
    <div class="report-tables"><div class="panel"><h3>月度账面收支（人民币折算参考）</h3><p v-if="!data.monthly_cash?.length">所选期间暂无已确认账面收支记录。</p><table v-else><thead><tr><th>月份</th><th>收入</th><th>支出</th><th>账面净收支</th></tr></thead><tbody><tr v-for="row in data.monthly_cash" :key="row.month"><td>{{ row.month }}</td><td>¥{{ money(row.income) }}</td><td>¥{{ money(row.expense) }}</td><td>¥{{ money(row.net) }}</td></tr></tbody></table></div>
    <div class="panel"><h3>账面收支分类（人民币折算参考）</h3><p v-if="!data.categories?.length">所选期间暂无账面收支分类记录。</p><table v-else><thead><tr><th>方向</th><th>分类</th><th>人民币折算参考</th></tr></thead><tbody><tr v-for="row in data.categories" :key="`${row.direction}-${row.category}`"><td>{{ row.direction === 'income' ? '收入' : '支出' }}</td><td>{{ row.category }}</td><td>¥{{ money(row.amount) }}</td></tr></tbody></table></div></div>
    <nav class="finance-links" aria-label="财务模块快捷入口"><RouterLink v-if="can('finance', 'view')" to="/receivables">查看应收计划</RouterLink><RouterLink v-if="can('finance', 'view')" to="/payables">查看应付计划</RouterLink><RouterLink v-if="can('transactions', 'view')" to="/transactions">查看财务流水</RouterLink><RouterLink v-if="can('transactions', 'view')" to="/rmb-cash-events">人民币资金记录</RouterLink></nav>
    <div class="panel"><h3>到期与逾期计划</h3><p v-if="!data.due_items.length">暂无到期或逾期计划。</p><table v-else><thead><tr><th>类型</th><th>合同</th><th>往来方</th><th>预计日期</th><th>待结金额</th></tr></thead><tbody><tr v-for="row in data.due_items" :key="row.id"><td>{{ row.direction === 'receivable' ? '应收' : '应付' }}</td><td><RouterLink v-if="row.order ? can('orders', 'view') : can('purchases', 'view')" :to="{ path: row.order ? '/orders' : '/purchase-orders', query: { detail: row.order || row.purchase_order } }">{{ row.contract_no }}</RouterLink><span v-else>{{ row.contract_no }}</span></td><td>{{ row.counterparty_name }}</td><td>{{ row.due_date }}</td><td>{{ row.currency }} {{ money(row.remaining_amount) }}</td></tr></tbody></table></div>
    </template>
  </section>
</template>

<style scoped>
.finance-page{padding:0}.finance-page>header,.metric-section>header,.drill-header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.page-lede{margin:0;color:#718078}.finance-page h3{margin:0;font-size:var(--text-section)}.finance-page p{color:#718078}.finance-page button{border:1px solid #d8e1dd;background:#0d4b40;color:#fff;border-radius:9px;padding:9px 14px;font-weight:700;white-space:nowrap}.finance-page button.secondary{background:#fff;color:#344d44}.finance-page button:disabled{opacity:.55;cursor:not-allowed}.report-filters{display:flex;gap:10px;align-items:end;flex-wrap:wrap;margin:20px 0;padding:15px 16px;border:1px solid #e2e8e4;border-radius:12px;background:#fff}.report-filters label{display:grid;gap:5px;color:#52655e;font-size:var(--text-caption)}.report-filters input{height:39px;padding:0 10px;border:1px solid #d8e1dd;border-radius:8px;background:#fff}.definition-note{margin:12px 0;padding:12px 14px;border-left:3px solid #8db7a7;border-radius:0 8px 8px 0;background:#f2f7f4;line-height:1.65}.notice{padding:10px 14px;border:1px solid #b8d8ca;border-radius:9px;background:#eff8f3;color:#1d4d40!important}.error{color:#b42318}.metric-section{margin-top:22px}.metric-section>header{align-items:end}.metric-section>header p{margin:4px 0 0;font-size:var(--text-caption)}.cards{display:grid;gap:12px;margin:12px 0 20px}.period-cards{grid-template-columns:repeat(4,minmax(0,1fr))}.balance-cards{grid-template-columns:repeat(3,minmax(0,1fr))}.actual-cash-cards{grid-template-columns:repeat(4,minmax(0,1fr))}.cards article,.panel{min-width:0;background:#fff;border:1px solid #e2e8e4;border-radius:12px;padding:16px;box-shadow:0 4px 16px #1643340d}.cards span{color:#718078;display:block;font-size:var(--text-body)}.cards strong{display:block;font-size:clamp(20px,2vw,27px);margin-top:9px;color:#073f36;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.metric-drill{margin-top:12px;padding:6px 9px!important;font-size:var(--text-caption);background:#f4faf7!important;color:#0d5c4e!important}.report-tables{display:grid;grid-template-columns:1.2fr 1fr;gap:14px}.panel{margin-top:12px;overflow:auto}.panel h3{margin:0 0 12px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:11px;border-bottom:1px solid #edf1ee;font-size:var(--text-body);white-space:nowrap}.table-sort{padding:0!important;border:0!important;background:transparent!important;color:inherit!important;font:inherit!important;font-weight:700!important}.finance-drill-panel{margin-top:18px}.drill-header{align-items:center}.drill-header p{margin:4px 0 0;font-size:var(--text-caption)}.drill-total{margin:12px 0!important}.drill-total strong{color:#073f36;font-size:18px}.empty-state{padding:12px 0}.drill-pagination{display:flex;align-items:center;justify-content:flex-end;gap:12px;margin-top:14px;color:#718078;font-size:var(--text-caption)}.header-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.actual-cash-events{margin-top:14px}.actual-cash-events a,.finance-drill-panel a{color:#0d5c4e;font-weight:700}.finance-links{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}.finance-links a{display:inline-flex;padding:8px 12px;border:1px solid #cbdcd3;border-radius:8px;color:#0d5c4e;text-decoration:none;background:#fff;font-weight:700}.finance-links a:hover{background:#f1f8f4}@media(max-width:1000px){.period-cards,.actual-cash-cards{grid-template-columns:repeat(3,minmax(0,1fr))}.balance-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.report-tables{grid-template-columns:1fr}}@media(max-width:650px){.finance-page>header{align-items:stretch;flex-direction:column}.report-filters{display:grid;grid-template-columns:1fr 1fr}.report-filters label{min-width:0}.report-filters label input{width:100%}.report-filters button{min-height:39px;padding:7px 9px}.definition-note{font-size:var(--text-caption)}.period-cards,.balance-cards,.actual-cash-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.cards article,.panel{padding:13px}.cards strong{font-size:20px}.drill-header{align-items:stretch;flex-direction:column}.header-actions{justify-content:flex-start}.drill-pagination{justify-content:space-between}}
</style>
