<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const data = ref({ metrics: {}, due_items: [] })
const loading = ref(true)
const error = ref('')
const today = new Date().toLocaleDateString('en-CA')
const dateFrom = ref(`${today.slice(0, 7)}-01`), dateTo = ref(today)
const cards = [
  ['receivable_count', '待收笔数', '笔'], ['receivable_rmb', '待收款', '¥'],
  ['payable_count', '待付款笔数', '笔'], ['payable_rmb', '待付款', '¥'],
  ['sales_rmb', '期间销售额', '¥'], ['estimated_profit_rmb', '预计订单利润', '¥'],
  ['purchase_cost_rmb', '期间订单采购归属成本', '¥'], ['order_expense_rmb', '期间订单费用', '¥'],
  ['income_rmb', '期间实际收入', '¥'], ['expense_rmb', '期间实际支出', '¥'], ['net_cash_rmb', '期间净现金流', '¥'],
  ['advance_receipt_rmb', '未核销预收款', '¥'], ['advance_payment_rmb', '未核销预付款', '¥'],
]

function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
async function load() {
  loading.value = true
  error.value = ''
  try { data.value = (await api.get('/finance-dashboard/', { params: { date_from: dateFrom.value, date_to: dateTo.value } })).data } catch (err) { error.value = err.message } finally { loading.value = false }
}
function exportReport() {
  const rows = [['收支报表', data.value.period?.date_from, data.value.period?.date_to], ['月份', '实际收入（人民币）', '实际支出（人民币）', '净现金流（人民币）'],
    ...(data.value.monthly_cash || []).map(row => [row.month, row.income, row.expense, row.net]), [], ['方向', '分类', '人民币金额'],
    ...(data.value.categories || []).map(row => [row.direction === 'income' ? '收入' : '支出', row.category, row.amount])]
  const cell = value => `"${String(value ?? '').replace(/^[=+@-]/, "'$&").replaceAll('"', '""')}"`
  const url = URL.createObjectURL(new Blob(['\uFEFF', rows.map(row => row.map(cell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = `收支报表-${data.value.period?.date_from}-${data.value.period?.date_to}.csv`; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
onMounted(load)
</script>

<template>
  <section class="finance-page">
    <header><div><h2>财务概览</h2><p>经营资金台账，所有金额按人民币汇总。</p></div><button :disabled="loading" @click="load">刷新数据</button></header>
    <form class="report-filters" @submit.prevent="load"><label>开始日期 <input v-model="dateFrom" type="date" required></label><label>结束日期 <input v-model="dateTo" type="date" required></label><button :disabled="loading">查询报表</button><button type="button" :disabled="loading || !data.period || !!error" @click="exportReport">导出 CSV</button></form>
    <p>销售额按订单日期，现金收支按实际发生日期。预计订单利润 = 期间销售额 - 采购归属成本 - 订单费用，是经营估算，不等同于会计净利润。</p>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="cards" v-if="!loading">
      <article v-for="[key, label, unit] in cards" :key="key"><span>{{ label }}</span><strong>{{ unit === '¥' ? `${unit}${money(data.metrics[key])}` : data.metrics[key] || 0 }}</strong></article>
    </div>
    <div class="panel"><h3>月度现金收支</h3><p v-if="!data.monthly_cash?.length">所选期间暂无已确认收支。</p><table v-else><thead><tr><th>月份</th><th>收入</th><th>支出</th><th>净现金流</th></tr></thead><tbody><tr v-for="row in data.monthly_cash" :key="row.month"><td>{{ row.month }}</td><td>¥{{ money(row.income) }}</td><td>¥{{ money(row.expense) }}</td><td>¥{{ money(row.net) }}</td></tr></tbody></table></div>
    <div class="panel"><h3>收支分类汇总</h3><p v-if="!data.categories?.length">暂无分类收支。</p><table v-else><thead><tr><th>方向</th><th>分类</th><th>人民币金额</th></tr></thead><tbody><tr v-for="row in data.categories" :key="`${row.direction}-${row.category}`"><td>{{ row.direction === 'income' ? '收入' : '支出' }}</td><td>{{ row.category }}</td><td>¥{{ money(row.amount) }}</td></tr></tbody></table></div>
    <p><RouterLink to="/receivables">管理应收</RouterLink> · <RouterLink to="/payables">管理应付</RouterLink> · <RouterLink to="/transactions">登记及核对流水</RouterLink></p>
    <div class="panel"><h3>到期与逾期计划</h3><p v-if="loading">正在加载…</p><p v-else-if="!data.due_items.length">暂无到期或逾期计划。</p><table v-else><thead><tr><th>类型</th><th>合同</th><th>往来方</th><th>预计日期</th><th>待结金额</th></tr></thead><tbody><tr v-for="row in data.due_items" :key="row.id"><td>{{ row.direction === 'receivable' ? '应收' : '应付' }}</td><td>{{ row.contract_no }}</td><td>{{ row.counterparty_name }}</td><td>{{ row.due_date }}</td><td>{{ row.currency }} {{ money(row.remaining_amount) }}</td></tr></tbody></table></div>
  </section>
</template>

<style scoped>
.report-filters{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:20px}.report-filters input{padding:8px;border:1px solid #d8e1dd;border-radius:8px}.panel{margin-top:18px;overflow:auto}
.finance-page{padding:34px}.finance-page header{display:flex;justify-content:space-between;align-items:start}.finance-page h2{margin:0;font-size:var(--text-section)}.finance-page p{color:#718078}.finance-page button{border:1px solid #d8e1dd;background:#fff;border-radius:9px;padding:10px 16px;font-weight:700}.cards{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:16px;margin:24px 0}.cards article,.panel{background:#fff;border:1px solid #e2e8e4;border-radius:14px;padding:18px;box-shadow:0 6px 20px #1643340d}.cards span{color:#718078;display:block;font-size:var(--text-body)}.cards strong{display:block;font-size:var(--text-page);margin-top:12px;color:#073f36}.panel h3{margin-top:0}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:11px;border-bottom:1px solid #edf1ee;font-size:var(--text-body)}.error{color:#b42318}@media(max-width:900px){.cards{grid-template-columns:repeat(2,1fr)}.finance-page{padding:20px}}
</style>
