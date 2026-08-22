<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const data = ref({ metrics: {}, due_items: [] })
const loading = ref(true)
const error = ref('')
const cards = [
  ['receivable_count', '待收笔数', '笔'], ['receivable_rmb', '待收款', '¥'],
  ['payable_count', '待付款笔数', '笔'], ['payable_rmb', '待付款', '¥'],
  ['monthly_sales_rmb', '月度销售额', '¥'],
]

function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
async function load() {
  loading.value = true
  error.value = ''
  try { data.value = (await api.get('/finance-dashboard/')).data } catch (err) { error.value = err.message } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section class="finance-page">
    <header><div><h2>财务概览</h2><p>经营资金台账，所有金额按人民币汇总。</p></div><button @click="load">刷新数据</button></header>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="cards" v-if="!loading">
      <article v-for="[key, label, unit] in cards" :key="key"><span>{{ label }}</span><strong>{{ unit === '¥' ? `${unit}${money(data.metrics[key])}` : data.metrics[key] || 0 }}</strong></article>
    </div>
    <div class="panel"><h3>到期与逾期计划</h3><p v-if="loading">正在加载…</p><p v-else-if="!data.due_items.length">暂无到期或逾期计划。</p><table v-else><thead><tr><th>类型</th><th>合同</th><th>往来方</th><th>预计日期</th><th>待结金额</th></tr></thead><tbody><tr v-for="row in data.due_items" :key="row.id"><td>{{ row.direction === 'receivable' ? '应收' : '应付' }}</td><td>{{ row.contract_no }}</td><td>{{ row.counterparty_name }}</td><td>{{ row.due_date }}</td><td>{{ row.currency }} {{ row.remaining_amount }}</td></tr></tbody></table></div>
  </section>
</template>

<style scoped>
.finance-page{padding:34px}.finance-page header{display:flex;justify-content:space-between;align-items:start}.finance-page h2{margin:0;font-size:26px}.finance-page p{color:#718078}.finance-page button{border:1px solid #d8e1dd;background:#fff;border-radius:9px;padding:10px 16px;font-weight:700}.cards{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:16px;margin:24px 0}.cards article,.panel{background:#fff;border:1px solid #e2e8e4;border-radius:14px;padding:18px;box-shadow:0 6px 20px #1643340d}.cards span{color:#718078;display:block;font-size:13px}.cards strong{display:block;font-size:24px;margin-top:12px;color:#073f36}.panel h3{margin-top:0}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:11px;border-bottom:1px solid #edf1ee;font-size:14px}.error{color:#b42318}@media(max-width:900px){.cards{grid-template-columns:repeat(2,1fr)}.finance-page{padding:20px}}
</style>
