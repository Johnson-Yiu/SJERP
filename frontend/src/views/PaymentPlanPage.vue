<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, listAll } from '../api'
import SummaryCards from '../components/SummaryCards.vue'
import PageLoadState from '../components/PageLoadState.vue'
import ListEmptyState from '../components/ListEmptyState.vue'
import { formatMoney } from '../utils/money'
import { orderDetailLocation, purchaseDetailLocation } from '../utils/detailNavigation'
import { useAccessControl } from '../accessControl'

const props = defineProps({ direction: { type: String, required: true } })
const route = useRoute()
const router = useRouter()
const { can } = useAccessControl()
const rows = ref([]), loading = ref(false), error = ref(''), loadError = ref(''), hasLoaded = ref(false), allPlansExist = ref(false), selected = ref(null)
const saving = ref(false)
const editing = ref(null), editForm = reactive({ due_date: '', planned_amount: '', notes: '' })
const contextOrder = ref(null), contextLoading = ref(false), contextError = ref('')
let contextRequestVersion = 0
let listRequestVersion = 0
function openEdit(row) {
  if (!can('finance', 'update')) return
  editing.value = row; error.value = ''
  Object.assign(editForm, { due_date: row.due_date || '', planned_amount: row.planned_amount, notes: row.notes || '' })
}
async function savePlan() {
  if (saving.value || !can('finance', 'update')) return
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
const hasOrderContext = computed(() => props.direction === 'receivable' && Object.prototype.hasOwnProperty.call(route.query, 'order'))
const orderContextId = computed(() => {
  if (!hasOrderContext.value) return ''
  const raw = route.query.order
  if (typeof raw !== 'string' || !/^[1-9]\d*$/.test(raw) || !Number.isSafeInteger(Number(raw))) return ''
  return raw
})
const invalidOrderContext = computed(() => hasOrderContext.value && !orderContextId.value)
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
const filtersActive = computed(() => Boolean(searchTerm.value || filters.status || filters.overdue || filters.dueFrom || filters.dueTo || orderContextId.value))

async function load() {
  const requestVersion = ++listRequestVersion
  if (rangeError.value) { loadError.value = rangeError.value; loading.value = false; return }
  if (invalidOrderContext.value) {
    rows.value = []
    loadError.value = ''
    allPlansExist.value = false
    hasLoaded.value = true
    loading.value = false
    return
  }
  loading.value = true; loadError.value = ''
  try {
    const params = { direction: props.direction }
    if (orderContextId.value) params.order = orderContextId.value
    if (filters.status) params.status = filters.status
    if (filters.overdue) params.overdue = 'true'
    if (searchTerm.value) params.search = searchTerm.value
    if (filters.dueFrom) params.due_from = filters.dueFrom
    if (filters.dueTo) params.due_to = filters.dueTo
    const result = await listAll('/payment-plans/', { params })
    if (requestVersion === listRequestVersion) {
      rows.value = result
      hasLoaded.value = true
      allPlansExist.value = result.length > 0
      if (!result.length && filtersActive.value) {
        try { allPlansExist.value = (await listAll('/payment-plans/', { params: { direction: props.direction } })).length > 0 } catch { /* keep a real empty result if the comparison request is unavailable */ }
      }
    }
  } catch (err) { if (requestVersion === listRequestVersion) loadError.value = err.message || '收付款计划加载失败，请稍后重试。' } finally { if (requestVersion === listRequestVersion) loading.value = false }
}
async function loadOrderContext() {
  const requestVersion = ++contextRequestVersion
  contextOrder.value = null
  contextError.value = ''
  contextLoading.value = false
  if (!hasOrderContext.value) { void load(); return }
  if (!orderContextId.value) {
    contextError.value = '订单筛选编号无效，请清除订单筛选后重试。'
    void load()
    return
  }
  contextLoading.value = true
  try {
    const { data } = await api.get(`/orders/${orderContextId.value}/`)
    if (requestVersion !== contextRequestVersion) return
    if (!data?.order_no || (data.id != null && String(data.id) !== orderContextId.value)) throw new Error('订单资料不完整')
    contextOrder.value = data
  } catch {
    if (requestVersion === contextRequestVersion) contextError.value = '无法加载订单信息；应收列表仍按订单编号筛选。'
  } finally {
    if (requestVersion === contextRequestVersion) {
      contextLoading.value = false
      void load()
    }
  }
}
async function clearOrderContext() {
  const { order: _order, ...query } = route.query
  await router.replace({ path: route.path, query, hash: route.hash })
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
function clearListFilters() {
  clearTimeout(searchTimer)
  resettingSearch = true
  searchInput.value = ''
  searchTerm.value = ''
  filters.status = ''
  filters.overdue = false
  filters.dueFrom = ''
  filters.dueTo = ''
  resettingSearch = false
  void load()
}
function openSettle(row) {
  if (!can('finance', 'update')) return
  selected.value = row
  form.amount = row.remaining_amount
  form.exchange_rate = row.exchange_rate || '1'
  form.transaction_date = new Date().toLocaleDateString('en-CA')
  form.payment_method = ''
  form.reference = row.contract_no
  form.notes = ''
}
async function settle() {
  if (saving.value || !can('finance', 'update')) return
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
watch([() => props.direction, () => route.query.order], () => {
  clearTimeout(searchTimer)
  searchTerm.value = searchInput.value.trim()
  void loadOrderContext()
}, { immediate: true })
onBeforeUnmount(() => clearTimeout(searchTimer))
</script>

<template>
  <section class="plan-page">
    <header><div><h2>{{ title }}</h2><p>按合同原币跟踪计划、已核销与待结清金额。</p></div><button @click="load">刷新</button></header>
    <SummaryCards v-if="hasLoaded" :items="planMetrics" />
    <section v-if="hasOrderContext" class="order-context-banner" aria-label="订单应收筛选上下文">
      <div>
        <strong v-if="contextLoading">当前仅显示订单：正在加载…</strong>
        <strong v-else-if="contextOrder">当前仅显示订单：{{ contextOrder.order_no }}</strong>
        <p v-else class="error" role="alert">{{ contextError || '无法加载订单信息。' }}</p>
      </div>
      <nav aria-label="订单上下文操作">
        <RouterLink v-if="contextOrder && orderContextId" :to="orderDetailLocation(orderContextId)">查看订单</RouterLink>
        <button type="button" @click="clearOrderContext">清除订单筛选</button>
      </nav>
    </section>
    <div class="filters" aria-label="收付款计划筛选">
      <label class="plan-search"><span>搜索往来方或合同号</span><input v-model="searchInput" type="search" :placeholder="searchPlaceholder" aria-label="搜索往来方或合同号"></label>
      <label class="plan-status"><span>状态</span><select v-model="filters.status" aria-label="收付款计划状态" @change="load"><option value="open">待结清</option><option value="settled">已结清</option><option value="">全部状态</option></select></label>
      <label class="plan-overdue"><input v-model="filters.overdue" type="checkbox" aria-label="仅看逾期" @change="load"> 仅看逾期</label>
      <label class="plan-date"><span>到期日从</span><input v-model="filters.dueFrom" type="date" aria-label="到期日从" @change="load"></label>
      <label class="plan-date"><span>到期日至</span><input v-model="filters.dueTo" type="date" aria-label="到期日至" @change="load"></label>
      <button class="filter-reset" type="button" @click="resetFilters">重置</button>
    </div>
    <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="loadError" @retry="load" />
    <div v-if="hasLoaded" class="table-wrap"><ListEmptyState v-if="!rows.length" :entity="direction === 'receivable' ? '应收计划' : '应付计划'" :filtered="filtersActive && allPlansExist" @clear="clearListFilters"><template #action>暂时没有收付款计划。</template></ListEmptyState><table v-else><thead><tr><th>预计日期</th><th>合同</th><th>往来方</th><th>原币计划</th><th>已核销</th><th>待结</th><th>状态</th><th /></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td>{{ row.due_date || '—' }}</td><td><RouterLink v-if="contractLocation(row)" :to="contractLocation(row)" class="contract-link">{{ row.contract_no }}</RouterLink><span v-else>{{ row.contract_no }}</span></td><td>{{ row.counterparty_name }}</td><td>{{ row.currency }} {{ formatMoney(row.planned_amount) }}</td><td>{{ formatMoney(row.settled_amount) }}</td><td><strong>{{ formatMoney(row.remaining_amount) }}</strong></td><td><span :class="row.is_overdue ? 'overdue' : 'tag'">{{ row.is_overdue ? '已逾期' : row.status === 'settled' ? '已结清' : row.status === 'cancelled' ? '已取消' : '待结清' }}</span></td><td><button v-if="can('finance', 'update') && row.status !== 'cancelled'" class="link" @click="openEdit(row)">调整计划</button><button v-if="can('finance', 'update') && row.status === 'open'" class="link" @click="openSettle(row)">{{ actionLabel }}</button></td></tr></tbody></table></div>
    <div v-if="selected && can('finance', 'update')" class="mask" @click.self="selected = null"><form class="dialog" @submit.prevent="settle"><header><h3>{{ actionLabel }}</h3><button type="button" @click="selected = null">×</button></header><p>{{ selected.contract_no }} · {{ selected.counterparty_name }} · 待结 {{ selected.currency }} {{ formatMoney(selected.remaining_amount) }}</p><label>原币金额<input v-model="form.amount" v-money-input type="number" min="0.01" step="any" required></label><label>实际日期<input v-model="form.transaction_date" type="date" required></label><label>结汇汇率<input v-model="form.exchange_rate" type="number" min="0.000001" step="0.000001" required></label><label>支付方式<input v-model="form.payment_method"></label><label>参考号<input v-model="form.reference"></label><label>备注<textarea v-model="form.notes" /></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="selected = null">取消</button><button class="primary" :disabled="saving">确认{{ actionLabel }}</button></footer></form></div>
    <div v-if="editing && can('finance', 'update')" class="mask" @click.self="editing = null"><form class="dialog" @submit.prevent="savePlan"><h3>调整收付款计划</h3><p>{{ editing.contract_no }} · {{ editing.currency }}；已有收付款的计划可调整日期和备注。</p><label>预计日期<input v-model="editForm.due_date" type="date"></label><label>计划原币金额<input v-model="editForm.planned_amount" :disabled="Number(editing.settled_amount) > 0" type="number" min="0.0001" step="0.0001" required></label><label>备注<textarea v-model="editForm.notes" /></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="editing = null">取消</button><button :disabled="saving">保存计划</button></footer></form></div>
  </section>
</template>

<style scoped>
.contract-link{color:#08705f;font-weight:700;text-decoration:none}.contract-link:hover{text-decoration:underline}
.order-context-banner{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:16px 0;padding:14px 16px;border:1px solid #b8d8ca;border-radius:10px;background:#eff8f3;color:#1d4d40}.order-context-banner strong{font-size:var(--text-body)}.order-context-banner nav{display:flex;align-items:center;gap:12px}.order-context-banner a{color:#08705f;font-weight:700;text-decoration:none}.order-context-banner button{cursor:pointer}.order-context-banner p{margin:0}.order-context-banner .error{color:#b42318}@media(max-width:600px){.order-context-banner{align-items:flex-start;flex-direction:column}.order-context-banner nav{flex-wrap:wrap}}
.plan-page{padding:34px}.plan-page>header,.dialog header,.dialog footer{display:flex;justify-content:space-between;align-items:center}.plan-page h2,.dialog h3{margin:0}.plan-page p{color:#718078}.plan-page button{border:1px solid #d8e1dd;background:#fff;border-radius:8px;padding:8px 13px}.filters{display:flex;align-items:end;gap:10px;margin:20px 0;flex-wrap:wrap}.filters>label{display:grid;gap:5px;color:#52655e;font-size:var(--text-caption)}.filters .plan-search{flex:1 1 250px;min-width:220px}.filters input:not([type=checkbox]),.filters select{height:39px;box-sizing:border-box;padding:0 10px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#263e36;font:inherit;font-size:var(--text-body)}.filters .plan-status{min-width:130px}.filters .plan-overdue{display:flex;align-items:center;gap:7px;min-height:39px;white-space:nowrap}.filters .plan-date{min-width:150px}.filters .filter-reset{height:39px;cursor:pointer}.filters .filter-reset:hover{border-color:#a9cbbd;color:#1e6d59;background:#f4faf7}.table-wrap{background:#fff;border:1px solid #e2e8e4;border-radius:14px;overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:13px;text-align:left;border-bottom:1px solid #edf1ee;white-space:nowrap}.link{color:#08705f;font-weight:700}.tag,.overdue{padding:4px 8px;border-radius:12px;background:#e7f4ec;color:#08705f}.overdue{background:#fff1e9;color:#c45012}.error{color:#b42318}.mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:30}.dialog{width:min(520px,calc(100vw - 32px));background:#fff;padding:24px;border-radius:14px}.dialog label{display:grid;gap:6px;margin:12px 0;color:#496057;font-size:var(--text-body)}.dialog input,.dialog textarea{padding:9px;border:1px solid #d8e1dd;border-radius:7px}.dialog textarea{min-height:64px}.dialog footer{margin-top:18px}.primary{background:#08705f!important;color:white;border-color:#08705f!important}
</style>
