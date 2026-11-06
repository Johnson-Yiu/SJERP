<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, listAll } = useWorkspaceApi()
import { BOOK_RMB_NOTE } from '../utils/financeBasis.js'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { apiErrorMessage } from '../utils/apiErrors.js'
import SummaryCards from '../components/SummaryCards.vue'
import PageLoadState from '../components/PageLoadState.vue'
import ListEmptyState from '../components/ListEmptyState.vue'
import { formatMoney } from '../utils/money'
import { orderDetailLocation, purchaseDetailLocation } from '../utils/detailNavigation'
import { useAccessControl } from '../accessControl'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'

const today = new Date().toLocaleDateString('en-CA')
const route = useRoute()
const router = useRouter()
const { can } = useAccessControl()
const rows = ref([]), error = ref(''), notice = ref(''), loadError = ref(''), hasLoaded = ref(false), allTransactionsExist = ref(false), query = ref(''), orderQuery = ref(''), showForm = ref(false), orders = ref([])
const selectedOrder = ref(null)
const customers = ref([]), suppliers = ref([]), purchases = ref([]), plans = ref([]), saving = ref(false), loading = ref(false)
const referenceErrors = ref([]), referencesLoaded = ref(false), referencesLoading = ref(true), orderSearchError = ref(''), orderSearchLoading = ref(false)
const allocation = ref(null), allocationPlan = ref(''), allocationAmount = ref('')
const voidTarget = ref(null), voidReason = ref(''), voidSaving = ref(false)
const filters = reactive({ status: 'confirmed', direction: '', date_from: '', date_to: '' })
const filterRangeError = computed(() => filters.date_from && filters.date_to && filters.date_from > filters.date_to ? '开始日期不能晚于结束日期。' : '')
const routeFilterKey = computed(() => JSON.stringify(['search', 'status', 'direction', 'date_from', 'date_to'].map(key => route.query[key] ?? null)))
const contractKinds = ['customer_receipt', 'order_expense', 'freight_expense', 'sample_expense', 'bank_fee', 'refund']
const eligiblePlans = computed(() => plans.value.filter(plan => plan.status === 'open' && plan.currency === allocation.value?.currency && plan.direction === (allocation.value?.direction === 'income' ? 'receivable' : 'payable') && (plan.order ? plan.customer_id === allocation.value?.customer : plan.supplier_id === allocation.value?.supplier)))

const kindGroups = [
  {
    direction: 'income',
    label: '收入',
    options: [
      { value: 'customer_receipt', label: '客户收款' },
      { value: 'unallocated_advance', label: '未分配预收款' },
      { value: 'supplier_refund', label: '供应商退款（原付款退回）' },
      { value: 'other_income', label: '其他收入' },
    ],
  },
  {
    direction: 'expense',
    label: '支出',
    options: [
      { value: 'supplier_payment', label: '供应商付款' },
      { value: 'order_expense', label: '订单费用' },
      { value: 'sample_expense', label: '样品费用' },
      { value: 'freight_expense', label: '运费/物流费' },
      { value: 'bank_fee', label: '银行手续费' },
      { value: 'tax_fee', label: '税费' },
      { value: 'salary_expense', label: '工资/福利' },
      { value: 'office_expense', label: '办公费用' },
      { value: 'travel_expense', label: '差旅/招待' },
      { value: 'marketing_expense', label: '营销推广' },
      { value: 'warehouse_expense', label: '仓储费用' },
      { value: 'asset_expense', label: '设备/固定资产' },
      { value: 'period_expense', label: '其他期间费用' },
      { value: 'unallocated_payment', label: '未分配预付款' },
      { value: 'refund', label: '客户退款（原收款退回）' },
      { value: 'exchange_difference', label: '汇兑损失' },
      { value: 'other_expense', label: '其他支出' },
    ],
  },
]
const kindLookup = new Map(kindGroups.flatMap(group => group.options.map(option => [option.value, { ...option, direction: group.direction }])))
const legacyKindLabels = { other: '其他收支', unallocated_advance: '未分配预收款' }
const currencies = [
  { value: 'CNY', label: 'CNY · 人民币' },
  { value: 'USD', label: 'USD · 美元' },
  { value: 'EUR', label: 'EUR · 欧元' },
  { value: 'GBP', label: 'GBP · 英镑' },
  { value: 'JPY', label: 'JPY · 日元' },
  { value: 'HKD', label: 'HKD · 港币' },
  { value: 'AUD', label: 'AUD · 澳元' },
]

const form = reactive({
  transaction_no: '', transaction_date: today, kind: 'period_expense', direction: 'expense', category: '其他期间费用',
  amount: '', currency: 'CNY', exchange_rate: '1', payment_method: '', reference: '', notes: '', order: null, customer: null, supplier: null, purchase_order: null,
})
const saveOutcome = ref('not-submitted')
const formGuard = useUnsavedChangesGuard({
  data: () => ({ ...form, orderQuery: orderQuery.value, selectedOrder: selectedOrder.value }),
  enabled: () => showForm.value,
  busy: () => saving.value,
  confirmOptions: () => saveOutcome.value === 'unknown' ? {
    title: '记账结果尚未确认',
    message: `流水号：${form.transaction_no}。该请求可能已经记账，请先按此编号核对流水。放弃表单不会撤销已保存记录，重新新建可能重复记账。请记录此编号后再决定是否放弃。`,
    cancelText: '返回核对', confirmText: '已记录编号，放弃表单',
  } : {},
})
function closeForm() { return formGuard.requestClose(() => { showForm.value = false }) }

const transactionMetrics = computed(() => {
  const sum = direction => rows.value.filter(row => row.direction === direction && row.status === 'confirmed').reduce((total, row) => total + Number(row.rmb_amount || 0), 0)
  return [
    { label: '流水笔数', value: rows.value.length, hint: '当前查询结果' },
    { label: '账面收入（人民币折算参考）', value: `¥ ${formatMoney(sum('income'))}`, hint: '按已确认流水汇总' },
    { label: '账面支出（人民币折算参考）', value: `¥ ${formatMoney(sum('expense'))}`, hint: '按已确认流水汇总' },
    { label: '关联订单', value: new Set(rows.value.map(row => row.order || row.order_no).filter(Boolean)).size, hint: '有业务归属的流水' },
  ]
})
const filtersActive = computed(() => Boolean(query.value.trim() || (filters.status && filters.status !== 'confirmed') || filters.direction || filters.date_from || filters.date_to))
const referenceErrorText = computed(() => referenceErrors.value.join(' '))

function kindLabel(kind) { return kindLookup.get(kind)?.label || legacyKindLabels[kind] || kind || '—' }
function directionLabel(direction) { return direction === 'income' ? '收入' : direction === 'expense' ? '支出' : '—' }
function queryValue(value) { return Array.isArray(value) ? String(value[0] ?? '') : String(value ?? '') }
function syncFiltersFromRoute() {
  query.value = queryValue(route.query.search)
  const status = queryValue(route.query.status)
  filters.status = status === 'all' ? '' : ['confirmed', 'cancelled'].includes(status) ? status : 'confirmed'
  filters.direction = ['income', 'expense'].includes(queryValue(route.query.direction)) ? queryValue(route.query.direction) : ''
  filters.date_from = queryValue(route.query.date_from)
  filters.date_to = queryValue(route.query.date_to)
}
function nextFilterQuery() {
  const next = { ...route.query }
  for (const key of ['search', 'status', 'direction', 'date_from', 'date_to']) delete next[key]
  if (query.value.trim()) next.search = query.value.trim()
  next.status = filters.status || 'all'
  if (filters.direction) next.direction = filters.direction
  if (filters.date_from) next.date_from = filters.date_from
  if (filters.date_to) next.date_to = filters.date_to
  return next
}
async function applyFilters() {
  if (filterRangeError.value) return
  const query = nextFilterQuery()
  const before = routeFilterKey.value
  const after = JSON.stringify(['search', 'status', 'direction', 'date_from', 'date_to'].map(key => query[key] ?? null))
  if (before === after) { await load(); return }
  await router.push({ path: route.path, query, hash: route.hash })
}
function resetFilters() {
  query.value = ''
  Object.assign(filters, { status: 'confirmed', direction: '', date_from: '', date_to: '' })
  void applyFilters()
}
function clearFilters() {
  query.value = ''
  Object.assign(filters, { status: '', direction: '', date_from: '', date_to: '' })
  void applyFilters()
}
function submitFilters() { void applyFilters() }
function contractLocation(row) {
  if (row.order) return orderDetailLocation(row.order)
  if (row.purchase_order) return purchaseDetailLocation(row.purchase_order)
  return null
}
function allocationLocation(item) {
  if (item.order) return orderDetailLocation(item.order)
  if (item.purchase_order) return purchaseDetailLocation(item.purchase_order)
  return null
}
function syncKind() {
  const meta = kindLookup.get(form.kind)
  if (meta) {
    form.direction = meta.direction
    form.category = meta.label
  }
  form.customer = null; form.supplier = null; form.purchase_order = null
  if (!contractKinds.includes(form.kind)) {
    form.order = null
    selectedOrder.value = null
    orders.value = []
    orderQuery.value = ''
  }
}
function openForm() {
  if (saving.value || showForm.value || !can('transactions', 'create')) return
  Object.assign(form, { transaction_no: '', transaction_date: new Date().toLocaleDateString('en-CA'), kind: 'period_expense', direction: 'expense', category: '其他期间费用', amount: '', currency: 'CNY', exchange_rate: '1', payment_method: '', reference: '', notes: '', order: null, customer: null, supplier: null, purchase_order: null })
  selectedOrder.value = null
  orderQuery.value = ''
  orders.value = []
  error.value = ''
  notice.value = ''
  saveOutcome.value = 'not-submitted'
  showForm.value = true
  formGuard.markClean()
}
function onCurrencyChange() {
  if (form.currency === 'CNY') form.exchange_rate = '1'
  else if (form.exchange_rate === '1') form.exchange_rate = ''
}
async function load() {
  if (filterRangeError.value) { loadError.value = filterRangeError.value; loading.value = false; return }
  loading.value = true; loadError.value = ''
  try {
    const result = await listAll('/transactions/', { params: { ...filters, search: query.value } })
    rows.value = result
    hasLoaded.value = true
    allTransactionsExist.value = result.length > 0
    if (!result.length && filtersActive.value) {
      try { allTransactionsExist.value = (await listAll('/transactions/')).length > 0 } catch { /* only affects empty-state wording */ }
    }
  } catch (err) { loadError.value = apiErrorMessage(err) || '财务流水加载失败，请稍后重试。' } finally { loading.value = false }
}
async function searchOrders() {
  form.order = null
  selectedOrder.value = null
  orderSearchError.value = ''
  orderSearchLoading.value = true
  try { orders.value = (await listAll('/orders/', { params: { search: orderQuery.value } })).filter(row => !['draft', 'cancelled'].includes(row.status)) }
  catch (err) { orders.value = []; orderSearchError.value = apiErrorMessage(err) || '订单选项加载失败。' }
  finally { orderSearchLoading.value = false }
}
function chooseOrder(row) {
  form.order = row.id
  selectedOrder.value = { id: row.id, order_no: row.order_no }
  orderQuery.value = row.order_no
  if (['customer_receipt', 'refund'].includes(form.kind)) { form.currency = row.currency; form.exchange_rate = row.exchange_rate }
  orders.value = []
}
function choosePurchase() {
  const row = purchases.value.find(row => row.id === form.purchase_order)
  if (row) { form.currency = row.currency; form.exchange_rate = row.exchange_rate }
}
async function save() {
  if (saving.value || !can('transactions', 'create')) return
  if (!referencesLoaded.value) { error.value = '客户、供应商或采购单资料尚未加载完成，请重试后再保存。'; return }
  if (form.kind === 'customer_receipt' && (orderSearchLoading.value || orderSearchError.value)) { error.value = '订单选项尚未成功加载，请重试后再保存。'; return }
  saving.value = true
  error.value = ''; notice.value = ''
  let submitted = false
  try {
    // Keep one identity across transport failures. The existing unique constraint
    // rejects a replay even when the first response was lost after commit.
    if (!form.transaction_no) form.transaction_no = `FIN-${Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('').toUpperCase()}`
    const payload = { ...form }
    if (!payload.transaction_no) delete payload.transaction_no
    submitted = true
    await api.post('/transactions/', payload)
    saveOutcome.value = 'confirmed'
    formGuard.markClean()
    showForm.value = false
    await load()
    notice.value = '财务流水已保存。'
  } catch (err) {
    const status = err.response?.status
    const duplicateNumber = Boolean(err.response?.data?.transaction_no)
    // A lost response, timeout or server failure does not establish rollback.
    // A later rejection cannot resolve an earlier ambiguous submission either.
    const ambiguous = submitted && (!status || status >= 500 || status === 408 || duplicateNumber)
    if (ambiguous || saveOutcome.value === 'unknown') saveOutcome.value = 'unknown'
    else saveOutcome.value = 'rejected'
    error.value = duplicateNumber
      ? `此记账编号已存在，请先核对流水 ${form.transaction_no}。编号重复不代表本次保存成功，勿另建同笔记账。`
      : apiErrorMessage(err) || (saveOutcome.value === 'unknown' ? '未收到明确的保存结果。' : '请求未通过，请核对输入后重试。')
  } finally { saving.value = false }
}
function openVoid(row) {
  if (!can('transactions', 'update')) return
  voidTarget.value = row
  voidReason.value = ''
  error.value = ''
  notice.value = ''
}
async function submitVoid() {
  if (!can('transactions', 'update')) return
  const reason = voidReason.value.trim()
  if (!reason || voidSaving.value) return
  voidSaving.value = true
  error.value = ''; notice.value = ''
  try {
    await api.post(`/transactions/${voidTarget.value.id}/void/`, { reason })
    voidTarget.value = null
    voidReason.value = ''
    await load()
    notice.value = '财务流水已作废，相关计划已恢复。'
  } catch (err) { error.value = apiErrorMessage(err) || '流水作废失败，请重试。' } finally { voidSaving.value = false }
}
async function openAllocate(row) {
  if (!can('transactions', 'update')) return
  notice.value = ''; error.value = ''
  try { plans.value = await listAll('/payment-plans/', { params: { status: 'open' } }); allocation.value = row; allocationPlan.value = ''; allocationAmount.value = String(Number(row.amount) - Number(row.allocated_amount)) } catch (err) { error.value = apiErrorMessage(err) || '收付款计划加载失败，请重试。' }
}
async function allocate() {
  if (saving.value || !can('transactions', 'update')) return
  saving.value = true
  error.value = ''; notice.value = ''
  try { await api.post(`/transactions/${allocation.value.id}/allocate/`, { plan: allocationPlan.value, amount: allocationAmount.value }); allocation.value = null; await load(); notice.value = '核销已保存。' } catch (err) { error.value = apiErrorMessage(err) || '核销失败，请检查金额和计划后重试。' } finally { saving.value = false }
}
async function loadReferenceOptions() {
  referencesLoading.value = true
  const results = await Promise.allSettled([listAll('/customers/'), listAll('/suppliers/'), listAll('/purchase-orders/')])
  const errors = []
  if (results[0].status === 'fulfilled') customers.value = results[0].value; else errors.push(apiErrorMessage(results[0].reason) || '客户资料加载失败。')
  if (results[1].status === 'fulfilled') suppliers.value = results[1].value; else errors.push(apiErrorMessage(results[1].reason) || '供应商资料加载失败。')
  if (results[2].status === 'fulfilled') purchases.value = results[2].value; else errors.push(apiErrorMessage(results[2].reason) || '采购单资料加载失败。')
  referenceErrors.value = errors
  referencesLoaded.value = errors.length === 0
  referencesLoading.value = false
}
syncFiltersFromRoute()
watch(routeFilterKey, () => { syncFiltersFromRoute(); void load() })
onMounted(async () => { await Promise.all([load(), loadReferenceOptions()]) })
</script>

<template>
  <section class="txn">
    <header>
      <div><p class="page-lede">登记原币收付款、订单费用与期间费用。流水发生日期用于业务记账，不是银行入账日期；银行实际日期请在银行结汇与凭证中查看。</p></div>
      <RouterLink v-if="can('transactions', 'view')" class="cash-link" to="/rmb-cash-events">银行结汇与凭证</RouterLink>
      <button v-if="can('transactions', 'create')" :disabled="!referencesLoaded" @click="openForm">新增记账</button>
    </header>
    <p class="page-lede">{{ BOOK_RMB_NOTE }}</p>
    <p class="page-lede">退款只用于退回原收付款；作废只更正系统流水和关联计划，不会撤回银行实际资金或自动完成反向更正。历史资金归属请按原始凭证核对。</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <div v-if="referenceErrorText" class="option-load-error" role="alert"><span>新增记账所需的关联资料未能全部加载，暂不能新增。{{ referenceErrorText }}</span><button type="button" @click="loadReferenceOptions">重试加载</button></div>
    <p v-else-if="referencesLoading" class="option-loading-note" role="status">正在加载客户、供应商和采购单资料…</p>
    <SummaryCards v-if="hasLoaded" :items="transactionMetrics" />
    <form class="filters" aria-label="财务流水筛选" @submit.prevent="submitFilters">
      <label class="filter-search"><span>搜索</span><input v-model="query" type="search" placeholder="流水号、往来方或合同号"></label>
      <label><span>状态</span><select v-model="filters.status"><option value="confirmed">已确认</option><option value="cancelled">已作废</option><option value="">全部状态</option></select></label>
      <label><span>收支方向</span><select v-model="filters.direction"><option value="">全部</option><option value="income">收入</option><option value="expense">支出</option></select></label>
      <label><span>流水发生日期从</span><input v-model="filters.date_from" type="date"></label>
      <label><span>流水发生日期至</span><input v-model="filters.date_to" type="date"></label>
      <div class="filter-actions"><button type="submit" :disabled="loading || !!filterRangeError">查询</button><button type="button" class="secondary" @click="resetFilters">重置</button></div>
      <p v-if="filterRangeError" class="error filter-error" role="alert">{{ filterRangeError }}</p>
    </form>
    <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="loadError" @retry="load" />
    <p v-if="error && !showForm && !allocation && !voidTarget" class="error" role="alert">{{ error }}</p>
    <template v-if="hasLoaded">
    <table>
      <thead><tr><th>流水发生日期 / 流水号</th><th>收支 / 类型</th><th>往来方 / 合同</th><th>原币金额</th><th>人民币折算参考</th><th>状态 / 核销</th><th>操作</th></tr></thead>
      <tbody><tr v-if="!rows.length"><td colspan="7"><ListEmptyState entity="财务流水" :filtered="filtersActive && allTransactionsExist" @clear="clearFilters"><template #action>当前还没有财务流水。</template></ListEmptyState></td></tr><tr v-for="row in rows" :key="row.id"><td>{{ row.transaction_date }}<small>{{ row.transaction_no }}<span v-if="row.split_from"> · 拆分记录</span></small></td><td>{{ row.direction_display || directionLabel(row.direction) }}<small>{{ kindLabel(row.kind) }}</small></td><td>{{ row.customer_name || row.supplier_name || '—' }}<small><RouterLink v-if="contractLocation(row)" :to="contractLocation(row)" class="contract-link">{{ row.order ? row.order_no : row.purchase_no }}</RouterLink><span v-else>未关联合同</span></small></td><td>{{ row.currency }} {{ formatMoney(row.amount) }}</td><td>¥{{ formatMoney(row.rmb_amount) }}</td><td>{{ row.status_display }}<small v-if="['unallocated_advance', 'unallocated_payment'].includes(row.kind)">未核销 {{ row.currency }} {{ formatMoney(Number(row.amount) - Number(row.allocated_amount)) }}</small><small v-for="item in row.allocations" :key="item.id"><RouterLink v-if="allocationLocation(item)" :to="allocationLocation(item)" class="contract-link">{{ item.contract_no }}</RouterLink><span v-else>{{ item.contract_no }}</span>：{{ formatMoney(item.amount) }} {{ item.is_active ? '已核销' : '已撤回' }}</small><small v-if="row.status === 'cancelled' && row.void_reason">作废原因：{{ row.void_reason }}{{ row.voided_at ? ' · ' + row.voided_at : '' }}</small></td><td><button v-if="can('transactions', 'update') && row.status === 'confirmed' && ['unallocated_advance', 'unallocated_payment'].includes(row.kind) && Number(row.amount) > Number(row.allocated_amount)" @click="openAllocate(row)">核销</button><button v-if="can('transactions', 'update') && row.status === 'confirmed' && !row.split_from" @click="openVoid(row)">作废</button><small v-if="row.split_from">由原始流水统一作废</small><small v-else-if="row.status === 'cancelled'">已作废</small></td></tr></tbody>
    </table>
    </template>

    <div v-if="showForm && can('transactions', 'create')" class="mask" @click.self="closeForm">
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="transaction-form-title" @submit.prevent="save">
        <header class="dialog-head"><div><h3 id="transaction-form-title">新增记账</h3><p>保存后只更新系统流水及可核销计划，不代表银行资金已到账。</p></div><button type="button" class="close" aria-label="关闭" @click="closeForm" :disabled="saving">×</button></header>
        <div v-if="saveOutcome === 'unknown'" class="error" role="alert"><strong>记账结果尚未确认</strong><p>请先按下方流水号核对实际记录，再决定是否重试。重试沿用原编号；不要另建同笔记账。</p></div>
        <label v-if="form.transaction_no">本次流水号<input :value="form.transaction_no" readonly></label>
        <fieldset :disabled="saving"><legend>流水信息（业务记账）</legend>
        <label>类型
          <select v-model="form.kind" required @change="syncKind">
            <optgroup v-for="group in kindGroups" :key="group.direction" :label="group.label"><option v-for="option in group.options" :key="option.value" :value="option.value">{{ option.label }}</option></optgroup>
          </select>
          <small class="field-hint">已按收入 / 支出分组；选择类型后会自动确定收支方向。</small>
        </label>
        <label>流水发生日期<input v-model="form.transaction_date" type="date" required></label>
        <p class="category-hint">分类由所选类型自动生成：{{ form.category }}，无需重复填写。</p>
        <label>原币金额<input v-model="form.amount" v-money-input type="number" min="0.0001" step="any" required></label>
        <label>币种<select v-model="form.currency" required @change="onCurrencyChange"><option v-for="currency in currencies" :key="currency.value" :value="currency.value">{{ currency.label }}</option></select></label>
        <label>参考折算汇率 <small>1 原币对应人民币，仅用于账面折算</small><input v-model="form.exchange_rate" type="number" min="0.000001" step="0.000001" required></label>
        </fieldset>
        <fieldset :disabled="saving"><legend>业务关联</legend>
        <div v-if="contractKinds.includes(form.kind)" class="order-picker">
          <label>关联订单（客户收款必选，费用可选）<input v-model="orderQuery" placeholder="客户或订单号" @input="searchOrders"></label><small v-if="orderSearchLoading">正在加载订单…</small><p v-if="orderSearchError" class="option-load-error-text" role="alert">{{ orderSearchError }} <button type="button" @click="searchOrders">重试</button></p>
          <button v-for="row in orders" :key="row.id" type="button" class="order" @click="chooseOrder(row)">{{ row.customer_name }}｜{{ row.customer_country || '—' }}｜{{ row.order_no }}｜{{ row.currency }} {{ formatMoney(row.total_amount) }}</button>
          <p v-if="form.order">已选择订单：{{ selectedOrder?.order_no }}</p>
        </div>
        <label v-if="['supplier_payment', 'supplier_refund'].includes(form.kind)">采购单<select v-model="form.purchase_order" required @change="choosePurchase"><option :value="null">请选择采购单</option><option v-for="row in purchases.filter(row => !['draft', 'cancelled'].includes(row.status))" :key="row.id" :value="row.id">{{ row.purchase_no }} · {{ row.supplier_name }} · {{ row.currency }}</option></select></label>
        <label v-if="form.kind === 'unallocated_advance'">客户<select v-model="form.customer" required><option :value="null">请选择客户</option><option v-for="row in customers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        <label v-if="form.kind === 'unallocated_payment'">供应商<select v-model="form.supplier" required><option :value="null">请选择供应商</option><option v-for="row in suppliers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        </fieldset>
        <fieldset :disabled="saving"><legend>付款信息</legend>
        <label>支付方式<input v-model="form.payment_method" placeholder="银行转账、现金等"></label><label>银行参考号<input v-model="form.reference"></label><label>备注<input v-model="form.notes"></label>
        </fieldset>
        <p v-if="['customer_receipt', 'supplier_payment'].includes(form.kind)">款项将按合同计划顺序在系统内核销；超出计划的部分转为未分配预收预付，不等于银行资金已确认。</p>
        <p v-if="form.kind === 'refund'">用于退回已经收到的订单货款；售后赔偿、运费补贴等请登记为订单费用。</p>
        <p v-else-if="form.kind === 'supplier_refund'">用于供应商退回已经支付的采购款。</p>
        <p v-if="error" class="error">{{ error }}</p>
        <footer><button type="button" @click="closeForm" :disabled="saving">取消</button><button :disabled="saving || !referencesLoaded || (form.kind === 'customer_receipt' && (orderSearchLoading || !!orderSearchError))">{{ saving ? '保存中…' : '保存' }}</button></footer>
      </form>
    </div>
    <div v-if="allocation && can('transactions', 'update')" class="mask" @click.self="allocation = null"><form class="dialog" role="dialog" aria-modal="true" aria-labelledby="allocation-title" @submit.prevent="allocate"><header class="dialog-head"><div><h3 id="allocation-title">核销预收预付款</h3><p>仅分配现有余额，不会新增现金流水。</p></div><button type="button" class="close" aria-label="关闭" @click="allocation = null">×</button></header><p class="dialog-context">{{ allocation.customer_name || allocation.supplier_name }} · {{ allocation.currency }} 可分配 {{ formatMoney(Number(allocation.amount) - Number(allocation.allocated_amount)) }}</p><label>待结计划<select v-model="allocationPlan" required><option value="">请选择</option><option v-for="plan in eligiblePlans" :key="plan.id" :value="plan.id">{{ plan.contract_no }} · {{ plan.notes || '无备注' }} · 待结 {{ formatMoney(plan.remaining_amount) }}</option></select></label><p v-if="!eligiblePlans.length" class="empty-note">暂无币种与往来方匹配的待结计划。</p><label>核销金额（{{ allocation.currency }}）<input v-model="allocationAmount" type="number" min="0.0001" step="0.0001" required></label><p v-if="error" class="error" role="alert">{{ error }}</p><footer><button type="button" class="secondary" @click="allocation = null">取消</button><button :disabled="saving || !allocationPlan">{{ saving ? '保存中…' : '确认核销' }}</button></footer></form></div>
    <div v-if="voidTarget && can('transactions', 'update')" class="mask" @click.self="voidTarget = null"><form class="dialog" role="dialog" aria-modal="true" aria-labelledby="void-title" @submit.prevent="submitVoid"><header class="dialog-head"><div><h3 id="void-title">作废财务流水</h3><p>此操作会同步作废拆分流水，并恢复关联收付款计划。</p></div><button type="button" class="close" aria-label="关闭" @click="voidTarget = null">×</button></header><dl class="void-summary"><dt>流水号</dt><dd>{{ voidTarget.transaction_no }}</dd><dt>金额</dt><dd>{{ voidTarget.currency }} {{ formatMoney(voidTarget.amount) }}</dd><dt>往来方 / 合同</dt><dd>{{ voidTarget.customer_name || voidTarget.supplier_name || '—' }} / {{ voidTarget.order_no || voidTarget.purchase_no || '未关联合同' }}</dd></dl><label>作废原因<textarea v-model="voidReason" maxlength="500" rows="4" required /></label><p v-if="error" class="error" role="alert">{{ error }}</p><footer><button type="button" class="secondary" @click="voidTarget = null">取消</button><button :disabled="voidSaving || !voidReason.trim()">{{ voidSaving ? '保存中…' : '确认作废' }}</button></footer></form></div>
  </section>
</template>

<style scoped>
.cash-link{display:inline-flex;align-items:center;padding:8px 12px;border:1px solid #cbdcd3;border-radius:8px;color:#0d5c4e;text-decoration:none;background:#fff;font-weight:700;white-space:nowrap}.cash-link:hover{background:#f1f8f4}
.contract-link{color:#08705f;text-decoration:none}.contract-link:hover{text-decoration:underline}
.txn{padding:0}.txn>header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.page-lede{margin:0;color:#718078}.txn p{color:#718078}.txn button{padding:8px 13px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;cursor:pointer}.txn button:hover{border-color:#8db7a7;background:#f5faf7}.txn button:disabled{opacity:.55;cursor:not-allowed}.filters{display:grid;grid-template-columns:minmax(220px,1.5fr) repeat(4,minmax(130px,1fr)) auto;gap:10px;align-items:end;margin:20px 0;padding:16px;border:1px solid #e2e8e4;border-radius:12px;background:#fff}.filters label{display:grid;gap:5px;color:#586b63;font-size:var(--text-caption)}.filters input,.filters select{width:100%;height:39px;padding:0 10px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#253b33}.filters .filter-actions{display:flex;gap:8px}.filters .filter-error{grid-column:1/-1;margin:0}.filters button,.dialog footer button{white-space:nowrap}.filters .secondary,.dialog .secondary{background:#fff;color:#344d44}.notice{margin:12px 0;padding:10px 14px;border:1px solid #b8d8ca;border-radius:9px;background:#eff8f3;color:#1d4d40!important}.txn td small{display:block;color:#718078;font-size:var(--text-caption);margin-top:4px}.txn>table{display:block;overflow:auto;background:#fff;width:100%;border-collapse:collapse;border:1px solid #e2e8e4;border-radius:12px;white-space:nowrap}.txn th,.txn td{padding:12px;text-align:left;border-bottom:1px solid #edf1ee}.txn th{color:#60736b;background:#f6faf8;font-size:var(--text-body)}.mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:60;padding:16px}.dialog{background:#fff;padding:24px;border-radius:14px;width:min(620px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;box-shadow:0 22px 60px #001a1340}.dialog h3{margin:0;font-size:var(--text-dialog)}.dialog-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:16px}.dialog-head p{margin:5px 0 0;font-size:var(--text-caption)}.dialog-head .close{padding:2px 8px;font-size:22px;line-height:1}.dialog label{display:grid;gap:5px;margin:10px 0;color:#3d5149;font-size:var(--text-body)}.dialog input,.dialog select,.dialog textarea{box-sizing:border-box;width:100%;padding:9px;border:1px solid #d8e1dd;border-radius:7px;background:#fff;color:#253b33;font:inherit}.dialog textarea{resize:vertical}.dialog fieldset{min-width:0;margin:0 0 14px;padding:12px 14px;border:1px solid #e2e8e4;border-radius:10px}.dialog legend{padding:0 6px;color:#27584b;font-weight:700}.dialog label>small{font-size:var(--text-caption);color:#71847c;font-weight:400}.void-summary{display:grid;grid-template-columns:110px minmax(0,1fr);gap:8px;margin:0 0 14px;font-size:var(--text-body)}.void-summary dt{color:#718078}.void-summary dd{margin:0;color:#253b33;overflow-wrap:anywhere}.field-hint,.category-hint{display:block;margin:-4px 0 10px;color:#71847c;font-size:var(--text-caption)}.category-hint{padding:8px 10px;border-radius:7px;background:#f3f8f5}.order-picker{margin-top:8px}.order-picker>p{margin:8px 0 0;font-size:var(--text-caption)}.order{display:block;width:100%;margin:5px 0;text-align:left}.dialog footer{display:flex;justify-content:end;gap:8px;margin-top:18px}.dialog footer button:last-child{background:#0d4b40;color:#fff;border-color:#0d4b40}.error{color:#b42318}.empty-note{padding:10px 12px;border-radius:8px;background:#f6f8f6}.txn .summary-cards{margin-top:16px}@media(max-width:1050px){.filters{grid-template-columns:repeat(3,minmax(140px,1fr))}.filters .filter-search{grid-column:span 2}}@media(max-width:620px){.txn>header{align-items:stretch;flex-direction:column}.txn>header>button{width:100%}.filters{grid-template-columns:1fr 1fr}.filters .filter-search{grid-column:1/-1}.filters .filter-actions{grid-column:1/-1}.filters .filter-actions button{flex:1}.txn>table{white-space:nowrap}.dialog{padding:18px}.dialog fieldset{padding:10px}.void-summary{grid-template-columns:80px minmax(0,1fr)}}
</style>
