<script setup>
import { BOOK_RMB_NOTE } from '../utils/financeBasis.js'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import PageLoadState from '../components/PageLoadState.vue'
import { useAccessControl } from '../accessControl'
import { apiErrorMessage } from '../utils/apiErrors.js'

const data = ref({ metrics: {}, due_items: [] })
const loading = ref(true)
const error = ref('')
const hasLoaded = ref(false)
const { can } = useAccessControl()
const route = useRoute(), router = useRouter()
const today = new Date().toLocaleDateString('en-CA')
const dateFrom = ref(`${today.slice(0, 7)}-01`), dateTo = ref(today)
const exporting = ref(false), notice = ref('')
const rangeError = computed(() => dateFrom.value && dateTo.value && dateFrom.value > dateTo.value ? '开始日期不能晚于结束日期。' : '')
const periodCards = [
  ['sales_rmb', '合同销售额'], ['estimated_profit_rmb', '预计订单利润'], ['purchase_cost_rmb', '订单采购归属成本'], ['order_expense_rmb', '订单费用'],
  ['income_rmb', '账面收入（折算参考）'], ['expense_rmb', '账面支出（折算参考）'], ['net_cash_rmb', '账面净收支（折算参考）'],
]
const balanceCards = [
  ['receivable_count', '待收笔数', 'count'], ['receivable_rmb', '待收款'], ['payable_count', '待付款笔数', 'count'], ['payable_rmb', '待付款'],
  ['advance_receipt_rmb', '未核销预收款'], ['advance_payment_rmb', '未核销预付款'],
]

function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
async function load() {
  if (rangeError.value) return
  loading.value = true
  error.value = ''
  try { data.value = (await api.get('/finance-dashboard/', { params: { date_from: dateFrom.value, date_to: dateTo.value } })).data; hasLoaded.value = true } catch (err) { error.value = apiErrorMessage(err) || '财务概览加载失败，请稍后重试。' } finally { loading.value = false }
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
  if (!can('finance', 'export')) return
  exporting.value = true
  error.value = ''
  try {
    const response = await api.get('/finance-dashboard/', { params: { date_from: data.value.period.date_from, date_to: data.value.period.date_to, export: 'csv' }, responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `账面收支参考-${data.value.period.date_from}-${data.value.period.date_to}.csv`; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    notice.value = 'CSV 已开始下载。'
  } catch (err) { error.value = apiErrorMessage(err) || '导出失败，请稍后重试。' } finally { exporting.value = false }
}
syncPeriod()
watch(() => [route.query.date_from, route.query.date_to], () => { syncPeriod(); void load() })
onMounted(load)
</script>

<template>
  <section class="finance-page">
    <header><div><p class="page-lede">合同、应收应付与账面收支分别列示。</p></div><button class="secondary" :disabled="loading" @click="load">刷新数据</button></header>
    <form class="report-filters" aria-label="概览日期范围" @submit.prevent="applyPeriod"><label>开始日期<input v-model="dateFrom" type="date" required></label><label>结束日期<input v-model="dateTo" type="date" required></label><button :disabled="loading || !!rangeError">查询</button><button type="button" class="secondary" @click="resetPeriod">本月至今</button><button v-if="can('finance', 'export')" type="button" class="secondary" :disabled="loading || exporting || !data.period || !!error" @click="exportReport">{{ exporting ? '正在导出…' : '导出 CSV' }}</button></form>
    <p v-if="rangeError" class="error" role="alert">{{ rangeError }}</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <p class="definition-note">合同销售额按订单日期，账面收支按流水发生日期。待收、待付按合同汇率折算，未核销预收预付按原流水汇率折算，均为当前参考值。预计订单利润 = 合同销售额 − 采购归属成本 − 订单费用，仅作经营估算。</p>
    <p class="definition-note">{{ data.cash_basis?.note || BOOK_RMB_NOTE }}</p>
    <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="error" @retry="load" />
    <template v-if="hasLoaded">
    <section class="metric-section"><header><div><h3>所选期间</h3><p>{{ data.period?.date_from }} 至 {{ data.period?.date_to }}</p></div></header><div class="cards period-cards">
      <article v-for="[key, label] in periodCards" :key="key"><span>{{ label }}</span><strong>¥{{ money(data.metrics[key]) }}</strong></article>
    </div></section>
    <section class="metric-section"><header><div><h3>当前待结与未核销</h3><p>截至当前的待结与未核销金额</p></div></header><div class="cards balance-cards">
      <article v-for="[key, label, kind] in balanceCards" :key="key"><span>{{ label }}</span><strong>{{ kind === 'count' ? `${data.metrics[key] || 0} 笔` : `¥${money(data.metrics[key])}` }}</strong></article>
    </div></section>
    <div class="report-tables"><div class="panel"><h3>月度账面收支（人民币折算参考）</h3><p v-if="!data.monthly_cash?.length">所选期间暂无已确认账面收支记录。</p><table v-else><thead><tr><th>月份</th><th>收入</th><th>支出</th><th>账面净收支</th></tr></thead><tbody><tr v-for="row in data.monthly_cash" :key="row.month"><td>{{ row.month }}</td><td>¥{{ money(row.income) }}</td><td>¥{{ money(row.expense) }}</td><td>¥{{ money(row.net) }}</td></tr></tbody></table></div>
    <div class="panel"><h3>账面收支分类（人民币折算参考）</h3><p v-if="!data.categories?.length">所选期间暂无账面收支分类记录。</p><table v-else><thead><tr><th>方向</th><th>分类</th><th>人民币折算参考</th></tr></thead><tbody><tr v-for="row in data.categories" :key="`${row.direction}-${row.category}`"><td>{{ row.direction === 'income' ? '收入' : '支出' }}</td><td>{{ row.category }}</td><td>¥{{ money(row.amount) }}</td></tr></tbody></table></div></div>
    <nav class="finance-links" aria-label="财务模块快捷入口"><RouterLink v-if="can('finance', 'view')" to="/receivables">查看应收计划</RouterLink><RouterLink v-if="can('finance', 'view')" to="/payables">查看应付计划</RouterLink><RouterLink v-if="can('transactions', 'view')" to="/transactions">查看财务流水</RouterLink></nav>
    <div class="panel"><h3>到期与逾期计划</h3><p v-if="!data.due_items.length">暂无到期或逾期计划。</p><table v-else><thead><tr><th>类型</th><th>合同</th><th>往来方</th><th>预计日期</th><th>待结金额</th></tr></thead><tbody><tr v-for="row in data.due_items" :key="row.id"><td>{{ row.direction === 'receivable' ? '应收' : '应付' }}</td><td><RouterLink v-if="row.order ? can('orders', 'view') : can('purchases', 'view')" :to="{ path: row.order ? '/orders' : '/purchase-orders', query: { detail: row.order || row.purchase_order } }">{{ row.contract_no }}</RouterLink><span v-else>{{ row.contract_no }}</span></td><td>{{ row.counterparty_name }}</td><td>{{ row.due_date }}</td><td>{{ row.currency }} {{ money(row.remaining_amount) }}</td></tr></tbody></table></div>
    </template>
  </section>
</template>

<style scoped>
.finance-page{padding:0}.finance-page>header,.metric-section>header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.page-lede{margin:0;color:#718078}.finance-page h3{margin:0;font-size:var(--text-section)}.finance-page p{color:#718078}.finance-page button{border:1px solid #d8e1dd;background:#0d4b40;color:#fff;border-radius:9px;padding:9px 14px;font-weight:700;white-space:nowrap}.finance-page button.secondary{background:#fff;color:#344d44}.finance-page button:disabled{opacity:.55;cursor:not-allowed}.report-filters{display:flex;gap:10px;align-items:end;flex-wrap:wrap;margin:20px 0;padding:15px 16px;border:1px solid #e2e8e4;border-radius:12px;background:#fff}.report-filters label{display:grid;gap:5px;color:#52655e;font-size:var(--text-caption)}.report-filters input{height:39px;padding:0 10px;border:1px solid #d8e1dd;border-radius:8px;background:#fff}.definition-note{margin:12px 0;padding:12px 14px;border-left:3px solid #8db7a7;border-radius:0 8px 8px 0;background:#f2f7f4;line-height:1.65}.notice{padding:10px 14px;border:1px solid #b8d8ca;border-radius:9px;background:#eff8f3;color:#1d4d40!important}.error{color:#b42318}.metric-section{margin-top:22px}.metric-section>header{align-items:end}.metric-section>header p{margin:4px 0 0;font-size:var(--text-caption)}.cards{display:grid;gap:12px;margin:12px 0 20px}.period-cards{grid-template-columns:repeat(4,minmax(0,1fr))}.balance-cards{grid-template-columns:repeat(3,minmax(0,1fr))}.cards article,.panel{min-width:0;background:#fff;border:1px solid #e2e8e4;border-radius:12px;padding:16px;box-shadow:0 4px 16px #1643340d}.cards span{color:#718078;display:block;font-size:var(--text-body)}.cards strong{display:block;font-size:clamp(20px,2vw,27px);margin-top:9px;color:#073f36;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.report-tables{display:grid;grid-template-columns:1.2fr 1fr;gap:14px}.panel{margin-top:12px;overflow:auto}.panel h3{margin:0 0 12px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:11px;border-bottom:1px solid #edf1ee;font-size:var(--text-body);white-space:nowrap}.finance-links{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}.finance-links a{display:inline-flex;padding:8px 12px;border:1px solid #cbdcd3;border-radius:8px;color:#0d5c4e;text-decoration:none;background:#fff;font-weight:700}.finance-links a:hover{background:#f1f8f4}@media(max-width:1000px){.period-cards{grid-template-columns:repeat(3,minmax(0,1fr))}.balance-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.report-tables{grid-template-columns:1fr}}@media(max-width:650px){.finance-page>header{align-items:stretch;flex-direction:column}.report-filters{display:grid;grid-template-columns:1fr 1fr}.report-filters label{min-width:0}.report-filters label input{width:100%}.report-filters button{min-height:39px;padding:7px 9px}.definition-note{font-size:var(--text-caption)}.period-cards,.balance-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.cards article,.panel{padding:13px}.cards strong{font-size:20px}}
</style>
