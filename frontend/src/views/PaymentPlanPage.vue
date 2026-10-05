<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { api, listAll } from '../api'
import SummaryCards from '../components/SummaryCards.vue'
import { formatMoney } from '../utils/money'
import { orderDetailLocation, purchaseDetailLocation } from '../utils/detailNavigation'

const props = defineProps({ direction: { type: String, required: true } })
const rows = ref([]), loading = ref(false), error = ref(''), selected = ref(null)
const saving = ref(false)
const editing = ref(null), editForm = reactive({ due_date: '', planned_amount: '', notes: '' })
function openEdit(row) {
  editing.value = row; error.value = ''
  Object.assign(editForm, { due_date: row.due_date || '', planned_amount: row.planned_amount, notes: row.notes || '' })
}
async function savePlan() {
  if (saving.value) return
  saving.value = true
  try {
    const payload = { due_date: editForm.due_date || null, notes: editForm.notes }
    if (Number(editForm.planned_amount) !== Number(editing.value.planned_amount)) payload.planned_amount = editForm.planned_amount
    await api.patch(`/payment-plans/${editing.value.id}/`, payload)
    editing.value = null; await load()
  } catch (err) { error.value = err.message } finally { saving.value = false }
}
const filters = reactive({ status: 'open', overdue: false, dueFrom: '', dueTo: '' })
const searchInput = ref(''), searchTerm = ref('')
let searchTimer = null
const form = reactive({ amount: '', transaction_date: new Date().toISOString().slice(0, 10), exchange_rate: '1', payment_method: '', reference: '', notes: '' })
const title = computed(() => props.direction === 'receivable' ? '应收计划' : '应付计划')
const searchPlaceholder = computed(() => props.direction === 'receivable' ? '搜索客户或销售订单号…' : '搜索供应商或采购单号…')
const rangeError = computed(() => filters.dueFrom && filters.dueTo && filters.dueFrom > filters.dueTo ? '到期日开始日期不能晚于结束日期。' : '')
const actionLabel = computed(() => props.direction === 'receivable' ? '登记收款' : '登记付款')
const category = computed(() => props.direction === 'receivable' ? '客户收款' : '供应商付款')
function contractLocation(row) {
  if (props.direction === 'receivable' && row.order) return orderDetailLocation(row.order)
  if (props.direction === 'payable' && row.purchase_order) return purchaseDetailLocation(row.purchase_order)
  return null
}
const planMetrics = computed(() => [
  { label: '计划笔数', value: rows.value.length, hint: '当前筛选范围' },
  { label: '待结清', value: rows.value.filter(row => row.status === 'open').length, hint: '当前筛选结果' },
  { label: '已逾期', value: rows.value.filter(row => row.is_overdue).length, hint: '当前筛选结果' },
  { label: '待结金额', value: `¥ ${formatMoney(rows.value.filter(row => row.status === 'open').reduce((sum, row) => sum + Number(row.remaining_rmb || 0), 0))}`, hint: '当前筛选结果，按合同汇率折合人民币' },
])

async function load() {
  if (rangeError.value) { error.value = rangeError.value; return }
  loading.value = true; error.value = ''
  try {
    const params = { direction: props.direction }
    if (filters.status) params.status = filters.status
    if (filters.overdue) params.overdue = 'true'
    if (searchTerm.value) params.search = searchTerm.value
    if (filters.dueFrom) params.due_from = filters.dueFrom
    if (filters.dueTo) params.due_to = filters.dueTo
    rows.value = await listAll('/payment-plans/', { params })
  } catch (err) { error.value = err.message } finally { loading.value = false }
}
function resetFilters() {
  clearTimeout(searchTimer)
  resettingSearch = true
  searchInput.value = ''
  searchTerm.value = ''
  filters.status = 'open'
  filters.overdue = false
  filters.dueFrom = ''
  filters.dueTo = ''
  resettingSearch = false
  void load()
}
function openSettle(row) {
  selected.value = row
  form.amount = row.remaining_amount
  form.exchange_rate = row.exchange_rate || '1'
  form.transaction_date = new Date().toLocaleDateString('en-CA')
  form.payment_method = ''
  form.reference = row.contract_no
  form.notes = ''
}
async function settle() {
  if (saving.value) return
  saving.value = true
  try {
    await api.post(`/payment-plans/${selected.value.id}/settle/`, { ...form, currency: selected.value.currency, category: category.value })
    selected.value = null
    await load()
  } catch (err) { error.value = err.message } finally { saving.value = false }
}
let resettingSearch = false
watch(searchInput, value => {
  if (resettingSearch) return
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { searchTerm.value = value.trim(); void load() }, 300)
}, { flush: 'sync' })
watch(() => props.direction, () => {
  clearTimeout(searchTimer)
  searchTerm.value = searchInput.value.trim()
  void load()
})
onMounted(load)
onBeforeUnmount(() => clearTimeout(searchTimer))
</script>

<template>
  <section class="plan-page">
    <header><div><h2>{{ title }}</h2><p>按合同原币跟踪计划、已核销与待结清金额。</p></div><button @click="load">刷新</button></header>
    <SummaryCards :items="planMetrics" />
    <div class="filters" aria-label="收付款计划筛选">
      <label class="plan-search"><span>搜索往来方或合同号</span><input v-model="searchInput" type="search" :placeholder="searchPlaceholder" aria-label="搜索往来方或合同号"></label>
      <label class="plan-status"><span>状态</span><select v-model="filters.status" aria-label="收付款计划状态" @change="load"><option value="open">待结清</option><option value="settled">已结清</option><option value="">全部状态</option></select></label>
      <label class="plan-overdue"><input v-model="filters.overdue" type="checkbox" aria-label="仅看逾期" @change="load"> 仅看逾期</label>
      <label class="plan-date"><span>到期日从</span><input v-model="filters.dueFrom" type="date" aria-label="到期日从" @change="load"></label>
      <label class="plan-date"><span>到期日至</span><input v-model="filters.dueTo" type="date" aria-label="到期日至" @change="load"></label>
      <button class="filter-reset" type="button" @click="resetFilters">重置</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="table-wrap"><table><thead><tr><th>预计日期</th><th>合同</th><th>往来方</th><th>原币计划</th><th>已核销</th><th>待结</th><th>状态</th><th /></tr></thead><tbody><tr v-if="loading"><td colspan="8">正在加载…</td></tr><tr v-else-if="!rows.length"><td colspan="8">暂无计划。</td></tr><tr v-for="row in rows" :key="row.id"><td>{{ row.due_date || '—' }}</td><td><RouterLink v-if="contractLocation(row)" :to="contractLocation(row)" class="contract-link">{{ row.contract_no }}</RouterLink><span v-else>{{ row.contract_no }}</span></td><td>{{ row.counterparty_name }}</td><td>{{ row.currency }} {{ formatMoney(row.planned_amount) }}</td><td>{{ formatMoney(row.settled_amount) }}</td><td><strong>{{ formatMoney(row.remaining_amount) }}</strong></td><td><span :class="row.is_overdue ? 'overdue' : 'tag'">{{ row.is_overdue ? '已逾期' : row.status === 'settled' ? '已结清' : row.status === 'cancelled' ? '已取消' : '待结清' }}</span></td><td><button v-if="row.status !== 'cancelled'" class="link" @click="openEdit(row)">调整计划</button><button v-if="row.status === 'open'" class="link" @click="openSettle(row)">{{ actionLabel }}</button></td></tr></tbody></table></div>
    <div v-if="selected" class="mask" @click.self="selected = null"><form class="dialog" @submit.prevent="settle"><header><h3>{{ actionLabel }}</h3><button type="button" @click="selected = null">×</button></header><p>{{ selected.contract_no }} · {{ selected.counterparty_name }} · 待结 {{ selected.currency }} {{ formatMoney(selected.remaining_amount) }}</p><label>原币金额<input v-model="form.amount" v-money-input type="number" min="0.01" step="any" required></label><label>实际日期<input v-model="form.transaction_date" type="date" required></label><label>结汇汇率<input v-model="form.exchange_rate" type="number" min="0.000001" step="0.000001" required></label><label>支付方式<input v-model="form.payment_method"></label><label>参考号<input v-model="form.reference"></label><label>备注<textarea v-model="form.notes" /></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="selected = null">取消</button><button class="primary" :disabled="saving">确认{{ actionLabel }}</button></footer></form></div>
    <div v-if="editing" class="mask" @click.self="editing = null"><form class="dialog" @submit.prevent="savePlan"><h3>调整收付款计划</h3><p>{{ editing.contract_no }} · {{ editing.currency }}；已有收付款的计划可调整日期和备注。</p><label>预计日期<input v-model="editForm.due_date" type="date"></label><label>计划原币金额<input v-model="editForm.planned_amount" :disabled="Number(editing.settled_amount) > 0" type="number" min="0.0001" step="0.0001" required></label><label>备注<textarea v-model="editForm.notes" /></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="editing = null">取消</button><button :disabled="saving">保存计划</button></footer></form></div>
  </section>
</template>

<style scoped>
.contract-link{color:#08705f;font-weight:700;text-decoration:none}.contract-link:hover{text-decoration:underline}
.plan-page{padding:34px}.plan-page>header,.dialog header,.dialog footer{display:flex;justify-content:space-between;align-items:center}.plan-page h2,.dialog h3{margin:0}.plan-page p{color:#718078}.plan-page button{border:1px solid #d8e1dd;background:#fff;border-radius:8px;padding:8px 13px}.filters{display:flex;align-items:end;gap:10px;margin:20px 0;flex-wrap:wrap}.filters>label{display:grid;gap:5px;color:#52655e;font-size:var(--text-caption)}.filters .plan-search{flex:1 1 250px;min-width:220px}.filters input:not([type=checkbox]),.filters select{height:39px;box-sizing:border-box;padding:0 10px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#263e36;font:inherit;font-size:var(--text-body)}.filters .plan-status{min-width:130px}.filters .plan-overdue{display:flex;align-items:center;gap:7px;min-height:39px;white-space:nowrap}.filters .plan-date{min-width:150px}.filters .filter-reset{height:39px;cursor:pointer}.filters .filter-reset:hover{border-color:#a9cbbd;color:#1e6d59;background:#f4faf7}.table-wrap{background:#fff;border:1px solid #e2e8e4;border-radius:14px;overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:13px;text-align:left;border-bottom:1px solid #edf1ee;white-space:nowrap}.link{color:#08705f;font-weight:700}.tag,.overdue{padding:4px 8px;border-radius:12px;background:#e7f4ec;color:#08705f}.overdue{background:#fff1e9;color:#c45012}.error{color:#b42318}.mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:30}.dialog{width:min(520px,calc(100vw - 32px));background:#fff;padding:24px;border-radius:14px}.dialog label{display:grid;gap:6px;margin:12px 0;color:#496057;font-size:var(--text-body)}.dialog input,.dialog textarea{padding:9px;border:1px solid #d8e1dd;border-radius:7px}.dialog textarea{min-height:64px}.dialog footer{margin-top:18px}.primary{background:#08705f!important;color:white;border-color:#08705f!important}
</style>
