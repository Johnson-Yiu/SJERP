<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api, listData } from '../api'

const props = defineProps({ direction: { type: String, required: true } })
const rows = ref([]), loading = ref(false), error = ref(''), selected = ref(null)
const filters = reactive({ status: 'open', overdue: false })
const form = reactive({ amount: '', transaction_date: new Date().toISOString().slice(0, 10), exchange_rate: '1', payment_method: '', reference: '', notes: '' })
const title = computed(() => props.direction === 'receivable' ? '应收计划' : '应付计划')
const actionLabel = computed(() => props.direction === 'receivable' ? '登记收款' : '登记付款')
const category = computed(() => props.direction === 'receivable' ? '客户收款' : '供应商付款')

async function load() {
  loading.value = true; error.value = ''
  try {
    const params = { direction: props.direction }
    if (filters.status) params.status = filters.status
    if (filters.overdue) params.overdue = 'true'
    rows.value = listData(await api.get('/payment-plans/', { params }))
  } catch (err) { error.value = err.message } finally { loading.value = false }
}
function openSettle(row) {
  selected.value = row
  form.amount = row.remaining_amount
  form.exchange_rate = '1'
  form.payment_method = ''
  form.reference = row.contract_no
  form.notes = ''
}
async function settle() {
  try {
    await api.post(`/payment-plans/${selected.value.id}/settle/`, { ...form, currency: selected.value.currency, category: category.value })
    selected.value = null
    await load()
  } catch (err) { error.value = err.message }
}
watch(() => props.direction, load)
onMounted(load)
</script>

<template>
  <section class="plan-page">
    <header><div><h2>{{ title }}</h2><p>按合同原币跟踪计划、已核销与待结清金额。</p></div><button @click="load">刷新</button></header>
    <div class="filters"><select v-model="filters.status" @change="load"><option value="open">待结清</option><option value="settled">已结清</option><option value="">全部状态</option></select><label><input v-model="filters.overdue" type="checkbox" @change="load"> 仅看逾期</label></div>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="table-wrap"><table><thead><tr><th>预计日期</th><th>合同</th><th>往来方</th><th>原币计划</th><th>已核销</th><th>待结</th><th>状态</th><th /></tr></thead><tbody><tr v-if="loading"><td colspan="8">正在加载…</td></tr><tr v-else-if="!rows.length"><td colspan="8">暂无计划。</td></tr><tr v-for="row in rows" :key="row.id"><td>{{ row.due_date || '—' }}</td><td>{{ row.contract_no }}</td><td>{{ row.counterparty_name }}</td><td>{{ row.currency }} {{ row.planned_amount }}</td><td>{{ row.settled_amount }}</td><td><strong>{{ row.remaining_amount }}</strong></td><td><span :class="row.is_overdue ? 'overdue' : 'tag'">{{ row.is_overdue ? '已逾期' : row.status === 'settled' ? '已结清' : '待结清' }}</span></td><td><button v-if="row.status === 'open'" class="link" @click="openSettle(row)">{{ actionLabel }}</button></td></tr></tbody></table></div>
    <div v-if="selected" class="mask" @click.self="selected = null"><form class="dialog" @submit.prevent="settle"><header><h3>{{ actionLabel }}</h3><button type="button" @click="selected = null">×</button></header><p>{{ selected.contract_no }} · {{ selected.counterparty_name }} · 待结 {{ selected.currency }} {{ selected.remaining_amount }}</p><label>原币金额<input v-model="form.amount" type="number" min="0.01" step="0.01" required></label><label>实际日期<input v-model="form.transaction_date" type="date" required></label><label>结汇汇率<input v-model="form.exchange_rate" type="number" min="0" step="0.000001" required></label><label>支付方式<input v-model="form.payment_method"></label><label>参考号<input v-model="form.reference"></label><label>备注<textarea v-model="form.notes" /></label><footer><button type="button" @click="selected = null">取消</button><button class="primary">确认{{ actionLabel }}</button></footer></form></div>
  </section>
</template>

<style scoped>
.plan-page{padding:34px}.plan-page>header,.dialog header,.dialog footer{display:flex;justify-content:space-between;align-items:center}.plan-page h2,.dialog h3{margin:0}.plan-page p{color:#718078}.plan-page button{border:1px solid #d8e1dd;background:#fff;border-radius:8px;padding:8px 13px}.filters{display:flex;gap:14px;margin:20px 0}.filters select{padding:8px;border:1px solid #d8e1dd;border-radius:8px}.table-wrap{background:#fff;border:1px solid #e2e8e4;border-radius:14px;overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:13px;text-align:left;border-bottom:1px solid #edf1ee;white-space:nowrap}.link{color:#08705f;font-weight:700}.tag,.overdue{padding:4px 8px;border-radius:12px;background:#e7f4ec;color:#08705f}.overdue{background:#fff1e9;color:#c45012}.error{color:#b42318}.mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:30}.dialog{width:min(520px,calc(100vw - 32px));background:#fff;padding:24px;border-radius:14px}.dialog label{display:grid;gap:6px;margin:12px 0;color:#496057;font-size:13px}.dialog input,.dialog textarea{padding:9px;border:1px solid #d8e1dd;border-radius:7px}.dialog textarea{min-height:64px}.dialog footer{margin-top:18px}.primary{background:#08705f!important;color:white;border-color:#08705f!important}
</style>
