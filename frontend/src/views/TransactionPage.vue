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
import CashEventEntryForm from '../components/CashEventEntryForm.vue'
import { formatMoney } from '../utils/money'
import { orderDetailLocation, purchaseDetailLocation } from '../utils/detailNavigation'
import { useAccessControl } from '../accessControl'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import { saveOrVerifyCustomerReceipt } from '../utils/customerReceiptSettlement.js'

const today = new Date().toLocaleDateString('en-CA')
const route = useRoute()
const router = useRouter()
const { can } = useAccessControl()
const rows = ref([]), error = ref(''), notice = ref(''), loadError = ref(''), hasLoaded = ref(false), allTransactionsExist = ref(false), query = ref(''), orderQuery = ref(''), showForm = ref(false), orders = ref([])
const selectedOrder = ref(null)
const settlementOpen = ref(false), savedReceipt = ref(null), settlementSnapshot = ref(null), receiptLookupLoading = ref(false)
const customers = ref([]), suppliers = ref([]), purchases = ref([]), plans = ref([]), saving = ref(false), loading = ref(false)
const referenceErrors = ref([]), referencesLoaded = ref(false), referencesLoading = ref(true), orderSearchError = ref(''), orderSearchLoading = ref(false)
const allocation = ref(null), allocationPlan = ref(''), allocationAmount = ref('')
const voidTarget = ref(null), voidReason = ref(''), voidSaving = ref(false)
const detailTarget = ref(null), receiptAdjustments = ref([]), receiptRemittance = ref(''), receiptPlanChoices = ref([])
const receiptAllocations = ref([]), multiOrderMode = ref(false), adjustmentUploadBusy = ref(false)
const pendingCurrency = ref(''), pendingOrder = ref(null), currencyChangeMessage = ref('')
const pendingPurchase = ref(null), pendingCustomer = ref(undefined)
const pendingKind = ref(''), previousKind = ref('period_expense'), approvedReceiptChanges = ref([]), receiptChangeLoadId = ref(0)
const filters = reactive({ status: 'confirmed', direction: '', date_from: '', date_to: '' })
const filterRangeError = computed(() => filters.date_from && filters.date_to && filters.date_from > filters.date_to ? '开始日期不能晚于结束日期。' : '')
const routeFilterKey = computed(() => JSON.stringify(['search', 'status', 'direction', 'date_from', 'date_to'].map(key => route.query[key] ?? null)))
const contractKinds = ['customer_receipt', 'order_expense', 'freight_expense', 'sample_expense', 'bank_fee', 'refund']
const eligiblePlans = computed(() => plans.value.filter(plan => plan.status === 'open' && plan.currency === allocation.value?.currency && plan.direction === (allocation.value?.direction === 'income' ? 'receivable' : 'payable') && (plan.order ? plan.customer_id === allocation.value?.customer : plan.supplier_id === allocation.value?.supplier)))
const eligibleReceiptPlans = computed(() => receiptPlanChoices.value.filter(plan => plan.status === 'open' && plan.direction === 'receivable' && plan.currency === form.currency && plan.customer_id === form.customer))
const receiptBankFees = computed(() => receiptAdjustments.value.filter(row => row.nature === 'bank_fee').reduce((sum, row) => sum + (Number(row.amount) || 0), 0))
const receiptPendingDifference = computed(() => receiptAdjustments.value.filter(row => row.nature === 'pending_difference').reduce((sum, row) => sum + (Number(row.amount) || 0), 0))
const receiptRemittancePreview = computed(() => Number(form.amount || 0) + receiptBankFees.value + receiptPendingDifference.value)
const incompatibleRelations = computed(() => (form.order && !contractKinds.includes(form.kind)) || (form.purchase_order && !['supplier_payment', 'supplier_refund'].includes(form.kind)) || (form.customer && !['customer_receipt', 'unallocated_advance'].includes(form.kind) && !form.order) || (form.supplier && !['supplier_payment', 'supplier_refund', 'unallocated_payment'].includes(form.kind) && !form.purchase_order))

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
      { value: 'period_expense', label: '其他期间费用', displayLabel: '其他期间费用（如水电费、物业费、软件订阅费等）' },
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
  data: () => ({ ...form, orderQuery: orderQuery.value, selectedOrder: selectedOrder.value, settlementOpen: settlementOpen.value, savedReceipt: savedReceipt.value?.id || null, settlement: settlementSnapshot.value, receiptAdjustments: receiptAdjustments.value, receiptRemittance: receiptRemittance.value, receiptAllocations: receiptAllocations.value, multiOrderMode: multiOrderMode.value }),
  enabled: () => showForm.value,
  busy: () => saving.value || receiptLookupLoading.value || Boolean(settlementSnapshot.value?.busy),
  confirmOptions: () => saveOutcome.value === 'unknown' ? {
    title: '记账结果尚未确认',
    message: `流水号：${form.transaction_no}。该请求可能已经记账，请先按此编号核对流水。放弃表单不会撤销已保存记录，重新新建可能重复记账。请记录此编号后再决定是否放弃。`,
    cancelText: '返回核对', confirmText: '已记录编号，放弃表单',
  } : savedReceipt.value ? { title: '收款已保存', message: '收款流水已经保存。关闭后仍会保留收款；尚未登记的结汇信息将不再保留。', cancelText: '继续登记结汇', confirmText: '关闭并保留收款' } : {},
})
function closeForm() { return formGuard.requestClose(() => { showForm.value = false }) }

function openSavedReceiptSettlement(row) {
  if (row.kind !== 'customer_receipt' || row.currency === 'CNY' || row.status !== 'confirmed' || Number(row.fx_available_amount) <= 0) return
  detailTarget.value = null
  openForm(true)
  Object.assign(form, { transaction_no: row.transaction_no, transaction_date: row.transaction_date, kind: 'customer_receipt', direction: 'income', category: '客户收款', amount: String(row.amount), currency: row.currency, exchange_rate: row.exchange_rate || '', customer: row.customer })
  previousKind.value = 'customer_receipt'
  form.payment_method = row.payment_method || ''; form.reference = row.reference || ''; form.notes = row.notes || ''
  receiptRemittance.value = String(row.remitted_amount_display ?? row.amount)
  receiptAdjustments.value = (row.receipt_adjustment_rows || []).map(item => ({ ...item, evidence_name: item.evidence_name || '', file: null }))
  savedReceipt.value = row
  settlementOpen.value = true
  saveOutcome.value = 'confirmed'
  formGuard.markClean()
}

const transactionMetrics = computed(() => {
  const sum = direction => rows.value.filter(row => row.direction === direction && row.status === 'confirmed').reduce((total, row) => total + Number(row.rmb_amount || 0), 0)
  return [
    { label: '流水笔数', value: rows.value.length, hint: '当前查询结果' },
    { label: '账面收入（人民币折算参考）', value: `¥ ${formatMoney(sum('income'))}`, hint: '按已确认流水汇总' },
    { label: '账面支出（人民币折算参考）', value: `¥ ${formatMoney(sum('expense'))}`, hint: '按已确认流水汇总' },
    { label: '关联订单', value: new Set(rows.value.flatMap(row => [row.order ? 'order-' + row.order : row.order_no, ...(row.allocations || []).filter(item => item.is_active && item.order).map(item => 'order-' + item.order)]).filter(Boolean)).size, hint: '有业务归属的流水' },
  ]
})
const filtersActive = computed(() => Boolean(query.value.trim() || (filters.status && filters.status !== 'confirmed') || filters.direction || filters.date_from || filters.date_to))
const referenceErrorText = computed(() => referenceErrors.value.join(' '))

function kindLabel(kind) { return kindLookup.get(kind)?.label || legacyKindLabels[kind] || kind || '—' }
function feeResponsibilityLabel(value) { return ({ company: '我方承担', customer: '客户承担', unknown: '待查', mixed: '按明细区分' })[value] || '待分类' }
function adjustmentNatureLabel(value) { return ({ discount: '优惠/减免', bank_fee: '银行手续费', pending_difference: '待核实差额', other: '其他扣减' })[value] || value }
function adjustmentHandlingLabel(value) { return ({ company: '我方承担，不减少客户汇款额', customer: '客户承担，保留应收差额', pending: '待核实，不抵减应收', applied: '已核准抵减应收', already_in_order: '已计入订单金额，不重复抵减' })[value] || value }
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
function openDetail(row) { detailTarget.value = row }
function allocationLocation(item) {
  if (item.order) return orderDetailLocation(item.order)
  if (item.purchase_order) return purchaseDetailLocation(item.purchase_order)
  return null
}
function syncKind() {
  const nextKind = form.kind
  const oldKind = previousKind.value
  if (oldKind === 'customer_receipt' && nextKind !== 'customer_receipt' && hasReceiptAmounts()) {
    pendingKind.value = nextKind
    form.kind = oldKind
    currencyChangeMessage.value = '切换业务类型会清除客户汇款、扣减明细和收款分配，请确认后继续。'
    return
  }
  previousKind.value = nextKind
  const meta = kindLookup.get(nextKind)
  if (meta) {
    form.direction = meta.direction
    form.category = meta.label
  }
  if (nextKind === 'customer_receipt') {
    const preferredCurrency = selectedOrder.value?.currency || 'USD'
    if (form.currency !== preferredCurrency) {
      if (form.amount || receiptRemittance.value || receiptAdjustments.value.length || receiptAllocations.value.length) {
        pendingCurrency.value = preferredCurrency
        currencyChangeMessage.value = `客户收款默认使用${preferredCurrency}。切换会清空现有金额和收款明细，请先确认。`
      } else applyCurrency(preferredCurrency)
    }
    if (selectedOrder.value) form.customer = selectedOrder.value.customer
    void loadReceiptPlans()
  }
  if (nextKind !== 'customer_receipt') { settlementOpen.value = false; savedReceipt.value = null; settlementSnapshot.value = null }
  if (!pendingCurrency.value) currencyChangeMessage.value = ''
}
function confirmKindChange() {
  if (!pendingKind.value) return
  const nextKind = pendingKind.value
  pendingKind.value = ''
  form.amount = ''; receiptRemittance.value = ''; receiptAdjustments.value = []; receiptAllocations.value = []
  receiptPlanChoices.value = []; approvedReceiptChanges.value = []; multiOrderMode.value = false
  settlementOpen.value = false; savedReceipt.value = null; settlementSnapshot.value = null
  form.kind = nextKind; previousKind.value = nextKind
  const meta = kindLookup.get(nextKind)
  if (meta) { form.direction = meta.direction; form.category = meta.label }
  currencyChangeMessage.value = ''
}
function clearIncompatibleRelations() {
  form.order = null; selectedOrder.value = null; form.purchase_order = null; form.customer = null; form.supplier = null
  orderQuery.value = ''; orders.value = []; receiptPlanChoices.value = []; receiptAllocations.value = []
}
function openForm(forSavedReceipt = false) {
  if (saving.value || showForm.value || (!can('transactions', 'create') && !(forSavedReceipt && can('finance', 'create')))) return
  Object.assign(form, { transaction_no: '', transaction_date: new Date().toLocaleDateString('en-CA'), kind: 'period_expense', direction: 'expense', category: '其他期间费用', amount: '', currency: 'CNY', exchange_rate: '1', payment_method: '', reference: '', notes: '', order: null, customer: null, supplier: null, purchase_order: null })
  settlementOpen.value = false; savedReceipt.value = null; settlementSnapshot.value = null
  receiptAdjustments.value = []; receiptRemittance.value = ''; receiptPlanChoices.value = []; receiptAllocations.value = []; multiOrderMode.value = false
  pendingCurrency.value = ''; pendingOrder.value = null; pendingPurchase.value = null; pendingCustomer.value = undefined; currencyChangeMessage.value = ''
  pendingKind.value = ''; previousKind.value = 'period_expense'
  selectedOrder.value = null
  orderQuery.value = ''
  orders.value = []
  error.value = ''
  notice.value = ''
  saveOutcome.value = 'not-submitted'
  showForm.value = true
  formGuard.markClean()
}
function hasReceiptAmounts() {
  return Boolean(form.amount || receiptRemittance.value || receiptAdjustments.value.some(row => row.amount || row.evidence || row.reason) || receiptAllocations.value.some(row => row.plan || row.amount))
}
function applyCurrency(currency) {
  form.currency = currency
  form.exchange_rate = currency === 'CNY' ? '1' : selectedOrder.value?.currency === currency ? String(selectedOrder.value.exchange_rate || '') : ''
  if (currency === 'CNY') { settlementOpen.value = false; settlementSnapshot.value = null }
  if (form.kind === 'customer_receipt' && form.customer) void loadReceiptPlans()
}
function requestCurrencyChange(event) {
  const currency = event.target.value
  if (currency === form.currency) return
  if (hasReceiptAmounts() || (selectedOrder.value && selectedOrder.value.currency !== currency)) {
    pendingCurrency.value = currency
    currencyChangeMessage.value = `切换到${currency}会清空当前金额、扣减明细和核销分配，请先确认。`
    event.target.value = form.currency
    return
  }
  applyCurrency(currency)
}
function confirmCurrencyChange() {
  if (!pendingCurrency.value) return
  form.amount = ''; receiptRemittance.value = ''; receiptAdjustments.value = []; receiptAllocations.value = []
  if (selectedOrder.value && selectedOrder.value.currency !== pendingCurrency.value) {
    form.order = null; selectedOrder.value = null; orderQuery.value = ''
  }
  applyCurrency(pendingCurrency.value)
  pendingCurrency.value = ''; currencyChangeMessage.value = ''
}
function cancelCurrencyChange() { pendingCurrency.value = ''; pendingOrder.value = null; pendingPurchase.value = null; pendingCustomer.value = undefined; pendingKind.value = ''; currencyChangeMessage.value = '' }
function requestCustomerChange(event) {
  const customer = Number(event.target.value) || null
  if (hasReceiptAmounts()) {
    pendingCustomer.value = customer
    currencyChangeMessage.value = '更换客户会清空当前金额、扣减明细和核销分配，请先确认。'
    event.target.value = form.customer || ''
    return
  }
  form.customer = customer; receiptPlanChoices.value = []; receiptAllocations.value = []
  form.order = null; selectedOrder.value = null; orderQuery.value = ''
  if (form.kind === 'customer_receipt') void loadReceiptPlans()
}
function confirmCustomerChange() {
  if (pendingCustomer.value === undefined) return
  form.amount = ''; receiptRemittance.value = ''; receiptAdjustments.value = []; receiptAllocations.value = []
  form.order = null; selectedOrder.value = null; orderQuery.value = ''
  form.customer = pendingCustomer.value; pendingCustomer.value = undefined; currencyChangeMessage.value = ''
  void loadReceiptPlans()
}
function applyOrder(row, { clearReceiptValues = false } = {}) {
  if (clearReceiptValues) { form.amount = ''; receiptRemittance.value = ''; receiptAdjustments.value = []; receiptAllocations.value = [] }
  form.order = row.id
  form.customer = row.customer
  selectedOrder.value = { id: row.id, order_no: row.order_no, currency: row.currency, customer: row.customer, exchange_rate: row.exchange_rate }
  orderQuery.value = row.order_no
  if (['customer_receipt', 'refund'].includes(form.kind)) applyCurrency(row.currency)
  orders.value = []
  pendingOrder.value = null; currencyChangeMessage.value = ''
  if (form.kind === 'customer_receipt') void loadReceiptPlans()
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
  orderSearchError.value = ''
  orderSearchLoading.value = true
  try { orders.value = (await listAll('/orders/', { params: { search: orderQuery.value } })).filter(row => !['draft', 'cancelled'].includes(row.status)) }
  catch (err) { orders.value = []; orderSearchError.value = apiErrorMessage(err) || '订单选项加载失败。' }
  finally { orderSearchLoading.value = false }
}
function chooseOrder(row) {
  const relationshipChange = (selectedOrder.value && selectedOrder.value.id !== row.id) || (form.customer && form.customer !== row.customer)
  const currencyChange = form.currency !== row.currency
  if ((relationshipChange || currencyChange) && hasReceiptAmounts()) {
    pendingOrder.value = row
    currencyChangeMessage.value = currencyChange
      ? `订单币种为${row.currency}，切换会清空现有收款金额和扣减明细。`
      : '更换订单会清空已选核销分配和订单扣减明细。'
    orders.value = []
    return
  }
  applyOrder(row)
}
function confirmOrderChange() {
  if (!pendingOrder.value) return
  const row = pendingOrder.value
  const clearValues = hasReceiptAmounts() && (row.currency !== form.currency || row.customer !== form.customer)
  if (!clearValues) {
    receiptAllocations.value = []
    receiptAdjustments.value.forEach(line => { line.plan = '' })
  }
  applyOrder(row, { clearReceiptValues: clearValues })
}
function choosePurchase() {
  const row = purchases.value.find(row => row.id === form.purchase_order)
  if (row) {
    if (hasReceiptAmounts() && form.currency !== row.currency) {
      pendingPurchase.value = row; pendingCurrency.value = row.currency
      currencyChangeMessage.value = `采购单币种为${row.currency}，切换会清空现有金额。`
      form.purchase_order = null
      return
    }
    applyCurrency(row.currency); form.supplier = row.supplier
  }
}
function confirmPurchaseChange() {
  if (!pendingPurchase.value) return
  form.amount = ''; applyCurrency(pendingPurchase.value.currency); form.purchase_order = pendingPurchase.value.id; form.supplier = pendingPurchase.value.supplier
  pendingPurchase.value = null; pendingCurrency.value = ''; currencyChangeMessage.value = ''
}
async function loadReceiptPlans() {
  if (!form.customer) { receiptPlanChoices.value = []; approvedReceiptChanges.value = []; return }
  try {
    receiptPlanChoices.value = (await listAll('/payment-plans/', { params: { status: 'open' } })).filter(plan => plan.customer_id === form.customer && plan.direction === 'receivable' && plan.currency === form.currency)
    if (form.order) await loadReceiptContractChanges(form.order)
  } catch (err) { receiptPlanChoices.value = []; orderSearchError.value = apiErrorMessage(err) || '应收计划加载失败，请重试。' }
}
async function loadReceiptContractChanges(orderId) {
  const requestId = ++receiptChangeLoadId.value
  if (!orderId) { approvedReceiptChanges.value = []; return }
  try {
    const rows = await listAll('/contract-changes/', { params: { order: orderId } })
    if (requestId === receiptChangeLoadId.value) approvedReceiptChanges.value = rows.filter(row => row.status === 'approved' && Number(row.amount_delta) < 0)
  } catch { if (requestId === receiptChangeLoadId.value) approvedReceiptChanges.value = [] }
}
async function onReceiptAdjustmentPlanChange(line) {
  if (!form.order && line.plan) {
    const plan = eligibleReceiptPlans.value.find(item => item.id === Number(line.plan))
    if (plan?.order) await loadReceiptContractChanges(plan.order)
  }
}
function addReceiptAdjustment() { receiptAdjustments.value.push({ nature: 'bank_fee', amount: '', handling: 'company', reason: '', evidence: null, evidence_name: '', file: null, plan: '', contract_change: '' }) }
function removeReceiptAdjustment(index) { receiptAdjustments.value.splice(index, 1) }
function onAdjustmentNatureChange(line) { line.handling = line.nature === 'bank_fee' ? 'company' : 'pending'; line.plan = ''; line.contract_change = '' }
function adjustmentHandlingOptions(nature) {
  if (nature === 'bank_fee') return [{ value: 'company', label: '我方承担' }, { value: 'customer', label: '客户承担' }, { value: 'pending', label: '待核实' }]
  if (nature === 'discount') return [{ value: 'applied', label: '授权抵减应收' }, { value: 'already_in_order', label: '已计入订单金额' }, { value: 'pending', label: '待核实' }]
  if (nature === 'other') return [{ value: 'applied', label: '凭证核准抵减应收' }, { value: 'pending', label: '待核实' }]
  return [{ value: 'pending', label: '待核实' }]
}
async function uploadAdjustmentEvidence(line) {
  if (!line.file || adjustmentUploadBusy.value) return
  adjustmentUploadBusy.value = true
  try {
    const body = new FormData(); body.append('file', line.file)
    const proof = (await api.post('/transactions/voucher-upload/', body)).data
    line.evidence = proof.id; line.evidence_name = proof.name; line.file = null
  } catch (err) { error.value = apiErrorMessage(err) || '扣减凭证上传失败，请重试。' }
  finally { adjustmentUploadBusy.value = false }
}
function addReceiptAllocation() { multiOrderMode.value = true; receiptAllocations.value.push({ plan: '', amount: '' }) }
function removeReceiptAllocation(index) { receiptAllocations.value.splice(index, 1) }
async function save() {
  if (saving.value || !can('transactions', 'create')) return
  if (savedReceipt.value) return
  if (!referencesLoaded.value) { error.value = '客户、供应商或采购单资料尚未加载完成，请重试后再保存。'; return }
  if (form.kind === 'customer_receipt' && (orderSearchLoading.value || orderSearchError.value)) { error.value = '订单选项尚未成功加载，请重试后再保存。'; return }
  if (currencyChangeMessage.value || pendingKind.value) { error.value = '请先确认或取消当前业务类型、币种或关联变更。'; return }
  if (incompatibleRelations.value) { error.value = '所选客户或合同与当前业务类型不匹配，请清除不适用的关联。'; return }
  if (form.kind === 'customer_receipt') {
    if (!form.customer) { error.value = '请选择收款客户。'; return }
    if (!form.amount || Number(form.amount) <= 0) { error.value = '请填写银行实际到账原币金额。'; return }
    if (form.order && (selectedOrder.value?.currency !== form.currency || selectedOrder.value?.customer !== form.customer)) { error.value = '收款币种和客户必须与所选订单一致。'; return }
    const missingProof = receiptAdjustments.value.find(line => ['bank_fee'].includes(line.nature) || line.handling === 'applied' ? !line.evidence : false)
    if (missingProof) { error.value = '银行手续费和抵减应收的扣减项必须先上传依据凭证。'; return }
    const invalidLine = receiptAdjustments.value.find(line => !line.amount || Number(line.amount) <= 0 || String(line.reason || '').trim().length < (line.handling === 'applied' ? 5 : 3))
    if (invalidLine) { error.value = '请补齐每条扣减明细的正数金额和处理原因。'; return }
    if (multiOrderMode.value) {
      const ids = receiptAllocations.value.map(line => Number(line.plan))
      if (!ids.length || ids.some(id => !id) || new Set(ids).size !== ids.length || receiptAllocations.value.some(line => !line.amount || Number(line.amount) <= 0)) {
        error.value = '多订单核销请为每个应收计划填写不同的订单和正数金额。'; return
      }
    }
  }
  if (form.kind !== 'customer_receipt') {
    saving.value = true
    error.value = ''; notice.value = ''
    let submitted = false
    try {
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
      const ambiguous = submitted && (!status || status >= 500 || status === 408 || duplicateNumber)
      if (ambiguous || saveOutcome.value === 'unknown') saveOutcome.value = 'unknown'
      else saveOutcome.value = 'rejected'
      error.value = duplicateNumber
        ? `此记账编号已存在，请先核对流水 ${form.transaction_no}。编号重复不代表本次保存成功，勿另建同笔记账。`
        : apiErrorMessage(err) || (saveOutcome.value === 'unknown' ? '未收到明确的保存结果。' : '请求未通过，请核对输入后重试。')
    } finally { saving.value = false }
    return
  }
  const outcomeBeforeSubmit = saveOutcome.value
  saving.value = outcomeBeforeSubmit !== 'unknown'
  receiptLookupLoading.value = outcomeBeforeSubmit === 'unknown'
  error.value = ''; notice.value = ''
  try {
    if (!form.transaction_no) form.transaction_no = `FIN-${Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('').toUpperCase()}`
    const payload = { ...form }
    payload.receipt_adjustments = receiptAdjustments.value.map(line => ({
      nature: line.nature, amount: line.amount, handling: line.handling, reason: line.reason,
      evidence: line.evidence || null, plan: line.plan || null, contract_change: line.contract_change || null,
    }))
    if (receiptRemittance.value) payload.remittance_amount = receiptRemittance.value
    else delete payload.remittance_amount
    if (form.exchange_rate === '') delete payload.exchange_rate
    if (multiOrderMode.value) payload.plan_allocations = receiptAllocations.value.map(line => ({ plan: line.plan, amount: line.amount }))
    else delete payload.plan_allocations
    delete payload.bank_fee_amount; delete payload.fee_responsibility; delete payload.fee_reason; delete payload.fee_evidence
    if (!payload.transaction_no) delete payload.transaction_no
    const attempt = await saveOrVerifyCustomerReceipt({
      outcome: outcomeBeforeSubmit,
      lookup: async () => {
        const matches = await listAll('/transactions/', { params: { search: form.transaction_no, status: 'confirmed' } })
        return matches.find(row => row.transaction_no === form.transaction_no && row.kind === 'customer_receipt') || null
      },
      save: async () => (await api.post('/transactions/', payload)).data,
    })
    if (attempt.status === 'missing') {
      saveOutcome.value = 'rejected'
      error.value = '未找到原收款流水。已核对后，可按原编号重试保存。'
      return
    }
    if (attempt.status === 'lookup-failed') {
      saveOutcome.value = 'unknown'
      error.value = apiErrorMessage(attempt.error) || '暂时无法核对收款流水，请稍后重试。'
      return
    }
    if (attempt.status === 'unknown' || attempt.status === 'rejected') {
      saveOutcome.value = attempt.status
      error.value = apiErrorMessage(attempt.error) || (attempt.status === 'unknown' ? '收款结果尚未确认。请先核对原流水。' : '收款保存失败，请核对输入后重试。')
      return
    }
    const receipt = attempt.receipt
    saveOutcome.value = 'confirmed'
    if (form.kind === 'customer_receipt' && settlementOpen.value && form.currency !== 'CNY') {
      savedReceipt.value = { ...receipt, order_no: receipt.order_no || selectedOrder.value?.order_no, order: receipt.order || form.order, currency: receipt.currency || form.currency }
      error.value = ''
      await load()
      notice.value = '收款已保存。正在使用该收款流水准备结汇信息。'
      return
    }
    formGuard.markClean()
    showForm.value = false
    await load()
    notice.value = '财务流水已保存。'
  } catch (err) {
    saveOutcome.value = outcomeBeforeSubmit === 'unknown' ? 'unknown' : 'rejected'
    error.value = apiErrorMessage(err) || (saveOutcome.value === 'unknown' ? '无法核对原收款流水，请稍后重试。' : '收款保存失败，请核对输入后重试。')
  } finally { saving.value = false; receiptLookupLoading.value = false }
}
function onSettlementStateChange(value) { settlementSnapshot.value = value }
async function onSettlementCreated(row) {
  settlementSnapshot.value = { ...settlementSnapshot.value, busy: false }
  formGuard.markClean()
  notice.value = '结汇信息已登记，等待银行凭证核对。'
  await load()
  if (row) notice.value = '结汇信息已登记，等待银行凭证核对。'
}
async function onSettlementUpdated(row) {
  settlementSnapshot.value = { ...settlementSnapshot.value, busy: false }
  formGuard.markClean()
  notice.value = row?.status === 'confirmed' ? '银行凭证已核对，结汇信息已确认。' : '结汇记录已更新。'
  await load()
}
watch(() => form.currency, value => {
  if (value === 'CNY' && !savedReceipt.value) { settlementOpen.value = false; settlementSnapshot.value = null }
})
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
  try { plans.value = await listAll('/payment-plans/', { params: { status: 'open' } }); allocation.value = row; allocationPlan.value = ''; allocationAmount.value = String(row.unallocated_amount ?? Math.max(0, Number(row.allocation_capacity ?? row.amount) - Number(row.allocated_amount))) } catch (err) { error.value = apiErrorMessage(err) || '收付款计划加载失败，请重试。' }
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
      <div><p class="page-lede">登记原币收付款、订单费用与期间费用。流水发生日期用于业务记账，不是银行入账日期；银行实际日期请在银行资金记录中查看。</p></div>
      <RouterLink v-if="can('transactions', 'view')" class="cash-link" to="/rmb-cash-events">银行资金记录</RouterLink>
      <button v-if="can('transactions', 'create')" :disabled="!referencesLoaded" @click="openForm()">新增记账</button>
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
      <thead><tr><th>流水日期 / 编号</th><th>收支 / 类型</th><th>往来方 / 订单</th><th>原币实际收付</th><th>人民币折算参考</th><th>已核销 / 未分配</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-if="!rows.length"><td colspan="7"><ListEmptyState entity="财务流水" :filtered="filtersActive && allTransactionsExist" @clear="clearFilters"><template #action>当前还没有财务流水。</template></ListEmptyState></td></tr>
        <tr v-for="row in rows" :key="row.id">
          <td>{{ row.transaction_date }}<small>{{ row.transaction_no }}<span v-if="row.split_from"> · 拆分记录</span></small></td>
          <td>{{ row.direction_display || directionLabel(row.direction) }}<small>{{ kindLabel(row.kind) }}</small></td>
          <td>{{ row.customer_name || row.supplier_name || '—' }}<small><RouterLink v-if="contractLocation(row)" :to="contractLocation(row)" class="contract-link">{{ row.order ? row.order_no : row.purchase_no }}</RouterLink><span v-else>{{ row.allocations?.some(item => item.is_active) ? '按核销计划关联' : '未关联订单' }}</span></small></td>
          <td>{{ row.currency }} {{ formatMoney(row.amount) }}<small v-if="row.kind === 'customer_receipt'">银行实际到账</small><small v-if="row.kind === 'customer_receipt'">客户汇款 {{ row.currency }} {{ formatMoney(row.remitted_amount_display) }}</small><small v-if="row.kind === 'customer_receipt' && Number(row.bank_fee_amount) > 0">银行扣费 {{ row.currency }} {{ formatMoney(row.bank_fee_amount) }} · {{ feeResponsibilityLabel(row.fee_responsibility) }}</small></td>
          <td>{{ row.reference_rate_missing ? '未录入' : '¥' + formatMoney(row.rmb_amount) }}</td>
          <td>{{ row.status_display }}<small v-if="row.kind === 'customer_receipt'">本笔核销 {{ row.currency }} {{ formatMoney(row.settlement_amount || 0) }}</small><small v-if="Number(row.unallocated_amount) > 0">未分配 {{ row.currency }} {{ formatMoney(row.unallocated_amount) }}</small><small v-for="item in row.allocations" :key="item.id"><RouterLink v-if="allocationLocation(item)" :to="allocationLocation(item)" class="contract-link">{{ item.contract_no }}</RouterLink><span v-else>{{ item.contract_no }}</span>：核销 {{ formatMoney(item.amount) }}，订单剩余 {{ formatMoney(item.remaining_amount) }}</small><small v-if="row.status === 'cancelled' && row.void_reason">作废原因：{{ row.void_reason }}{{ row.voided_at ? ' · ' + row.voided_at : '' }}</small></td>
          <td><button type="button" @click="openDetail(row)">详情</button><button v-if="can('transactions', 'update') && row.status === 'confirmed' && Number(row.unallocated_amount) > 0 && (['unallocated_advance', 'unallocated_payment'].includes(row.kind) || row.kind === 'customer_receipt' && !row.order && !row.plan)" @click="openAllocate(row)">核销</button><button v-if="can('transactions', 'update') && row.status === 'confirmed' && !row.split_from" @click="openVoid(row)">作废</button><small v-if="row.split_from">由原始流水统一作废</small><small v-else-if="row.status === 'cancelled'">已作废</small></td>
        </tr>
      </tbody>
    </table>
    </template>

    <div v-if="detailTarget" class="mask">
      <section class="dialog detail-dialog" role="dialog" aria-modal="true" aria-labelledby="transaction-detail-title">
        <header class="dialog-head"><div><h3 id="transaction-detail-title">流水详情</h3><p>{{ detailTarget.transaction_no }} · {{ detailTarget.transaction_date }}</p></div><button type="button" class="close" aria-label="关闭" @click="detailTarget = null">×</button></header>
        <div class="detail-grid">
          <div><span>往来方</span><strong>{{ detailTarget.customer_name || detailTarget.supplier_name || '—' }}</strong></div>
          <div><span>币种</span><strong>{{ detailTarget.currency }}</strong></div>
          <div><span>{{ detailTarget.kind === 'customer_receipt' ? '银行实际到账原币' : '流水金额' }}</span><strong>{{ detailTarget.currency }} {{ formatMoney(detailTarget.amount) }}</strong></div>
          <div v-if="detailTarget.kind === 'customer_receipt'"><span>客户实际汇款</span><strong>{{ detailTarget.currency }} {{ formatMoney(detailTarget.remitted_amount_display) }}</strong></div>
          <div v-if="detailTarget.kind === 'customer_receipt'"><span>已核销应收</span><strong>{{ detailTarget.currency }} {{ formatMoney(detailTarget.settlement_amount || 0) }}</strong></div>
          <div v-if="detailTarget.kind === 'customer_receipt'"><span>未分配，可继续核销</span><strong>{{ detailTarget.currency }} {{ formatMoney(detailTarget.unallocated_amount || 0) }}</strong></div>
          <div v-if="detailTarget.kind === 'customer_receipt'"><span>尚未结汇原币</span><strong>{{ detailTarget.currency }} {{ formatMoney(detailTarget.fx_available_amount || 0) }}</strong></div>
          <div><span>{{ detailTarget.currency === 'CNY' ? '人民币实际金额' : '人民币折算参考' }}</span><strong>{{ detailTarget.reference_rate_missing ? '未录入' : '¥' + formatMoney(detailTarget.rmb_amount) }}</strong></div>
          <div><span>状态</span><strong>{{ detailTarget.status_display }}</strong></div>
        </div>
        <section v-if="detailTarget.allocations?.length"><h4>订单核销</h4><ul class="detail-list"><li v-for="item in detailTarget.allocations" :key="item.id"><RouterLink v-if="allocationLocation(item)" :to="allocationLocation(item)" class="contract-link">{{ item.contract_no }}</RouterLink><span v-else>{{ item.contract_no }}</span>：已核销 {{ detailTarget.currency }} {{ formatMoney(item.amount) }}；订单剩余 {{ detailTarget.currency }} {{ formatMoney(item.remaining_amount) }}<small>其中到账 {{ formatMoney(item.cash_amount ?? item.amount) }}，我方承担手续费核销 {{ formatMoney(item.fee_credit_amount || 0) }}</small></li></ul></section>
        <section v-if="detailTarget.receipt_adjustment_rows?.length"><h4>扣减明细</h4><ul class="detail-list"><li v-for="item in detailTarget.receipt_adjustment_rows" :key="item.id"><strong>{{ adjustmentNatureLabel(item.nature) }} · {{ detailTarget.currency }} {{ formatMoney(item.amount) }}</strong><small>{{ adjustmentHandlingLabel(item.handling) }}：{{ item.reason }}</small><small v-if="item.evidence_name">凭证：<a :href="`/api/transactions/${detailTarget.id}/receipt-adjustments/${item.id}/evidence/`">{{ item.evidence_name }}</a></small><small v-if="item.contract_no">关联订单：{{ item.contract_no }}</small><small v-if="item.contract_change">订单金额修订：#{{ item.contract_change }}</small></li></ul></section>
        <section v-if="detailTarget.cash_settlements?.length"><h4>结汇记录</h4><ul class="detail-list"><li v-for="item in detailTarget.cash_settlements" :key="item.id"><strong>{{ item.event_no }} · {{ item.status === 'confirmed' ? '已核实' : '待核实' }}</strong><small>兑换 {{ item.amount }} {{ item.currency }}；实际汇率 {{ item.actual_rate }}；扣费前兑换额 ¥{{ item.gross_rmb_amount }}；结汇手续费 ¥{{ item.fee_amount }}；人民币净到账 ¥{{ item.bank_net_amount }}</small><small v-if="item.quoted_rate">参考汇率 {{ item.quoted_rate }} · 与参考汇率差额 ¥{{ item.quoted_reference_delta }}（按扣费前兑换额比较，不自动计入汇损）</small><small v-if="item.book_reference_amount !== null && item.book_reference_amount !== undefined">账面比较基准 ¥{{ item.book_reference_amount }} · 与账面基准差额 ¥{{ item.book_reference_delta }}</small><small v-else-if="!item.quoted_rate">未录入已确认的账面比较基准，不显示账面汇率差额</small></li></ul></section>
        <section v-if="detailTarget.writeoffs?.length"><h4>授权抹零 / 非现金抵减</h4><ul class="detail-list"><li v-for="item in detailTarget.writeoffs" :key="item.id">{{ item.nature === 'discount' ? '优惠减免' : item.nature === 'other' ? '其他有依据扣减' : '授权抹零' }} {{ detailTarget.currency }} {{ formatMoney(item.amount) }} · {{ item.reason }}<small>确认人记录：{{ item.confirmed_actor?.kind === 'authenticated_user' ? '用户 #' + item.confirmed_actor.user_id : item.confirmed_actor?.kind === 'development_superadmin' ? '开发超级管理员（未登录）' : '待核实' }}</small></li></ul></section>
        <section><h4>备注</h4><p>{{ detailTarget.notes || '—' }}</p><p v-if="detailTarget.reference">银行参考号：{{ detailTarget.reference }}</p></section>
        <button v-if="detailTarget.kind === 'customer_receipt' && detailTarget.currency !== 'CNY' && detailTarget.status === 'confirmed' && Number(detailTarget.fx_available_amount) > 0 && can('finance', 'create')" type="button" @click="openSavedReceiptSettlement(detailTarget)">登记结汇到账</button>
      </section>
    </div>

    <div v-if="showForm && (can('transactions', 'create') || (savedReceipt && can('finance', 'create')))" class="mask">
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="transaction-form-title" @submit.prevent="save">
        <header class="dialog-head"><div><h3 id="transaction-form-title">{{ savedReceipt ? '登记结汇到账' : '新增记账' }}</h3><p>{{ form.kind === 'customer_receipt' ? '分别登记客户汇款、银行实际到账和应收核销；外币结汇可稍后办理。' : '记录业务收付款；银行账户资金确认仍按资金事件流程办理。' }}</p></div><button type="button" class="close" aria-label="关闭" @click="closeForm" :disabled="saving">×</button></header>
        <div v-if="saveOutcome === 'unknown'" class="error" role="alert"><strong>记账结果尚未确认</strong><p>请先按下方流水号核对实际记录，再决定是否重试。重试沿用原编号；不要另建同笔记账。</p></div>
        <fieldset v-if="!savedReceipt" :disabled="saving"><legend>流水信息（业务记账）</legend>
        <label>类型
          <select v-model="form.kind" required @change="syncKind">
            <optgroup v-for="group in kindGroups" :key="group.direction" :label="group.label"><option v-for="option in group.options" :key="option.value" :value="option.value">{{ option.displayLabel || option.label }}</option></optgroup>
          </select>
          <small class="field-hint">已按收入 / 支出分组；选择类型后会自动确定收支方向。</small>
        </label>
        <label>流水发生日期<input v-model="form.transaction_date" type="date" required></label>
        <p class="category-hint">分类由所选类型自动生成：{{ form.category }}，无需重复填写。</p>
        <label>{{ form.kind === 'customer_receipt' ? '银行实际到账金额' : '原币金额' }}<input v-model="form.amount" v-money-input type="number" min="0.0001" step="any" required></label>
        <label>币种<select :value="form.currency" required @change="requestCurrencyChange"><option v-for="currency in currencies" :key="currency.value" :value="currency.value">{{ currency.label }}</option></select></label>
        <label v-if="form.currency !== 'CNY'">账面折算参考汇率 <small>{{ form.kind === 'customer_receipt' ? '可留空；结汇时另记银行实际汇率' : '1原币对应人民币，仅用于账面折算' }}</small><input v-model="form.exchange_rate" type="number" min="0.000001" step="0.000001" :required="form.kind !== 'customer_receipt'"></label>
        <p v-if="form.kind === 'customer_receipt' && form.currency === 'CNY'" class="field-hint">人民币收款的参考汇率为1。</p>
        </fieldset>
        <fieldset v-if="!savedReceipt" :disabled="saving"><legend>业务关联</legend>
        <label v-if="form.kind === 'customer_receipt'">客户<select :value="form.customer || ''" :disabled="Boolean(form.order)" required @change="requestCustomerChange"><option value="">请选择客户</option><option v-for="row in customers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        <div v-if="contractKinds.includes(form.kind)" class="order-picker">
          <label>关联订单（客户收款可暂不选择）<input v-model="orderQuery" placeholder="客户或订单号" @input="searchOrders"></label><small v-if="orderSearchLoading">正在加载订单…</small><p v-if="orderSearchError" class="option-load-error-text" role="alert">{{ orderSearchError }} <button type="button" @click="searchOrders">重试</button></p>
          <button v-for="row in orders" :key="row.id" type="button" class="order" @click="chooseOrder(row)">{{ row.customer_name }}｜{{ row.customer_country || '—' }}｜{{ row.order_no }}｜{{ row.currency }} {{ formatMoney(row.total_amount) }}</button>
          <p v-if="form.order">已选择订单：{{ selectedOrder?.order_no }}</p>
        </div>
        <label v-if="['supplier_payment', 'supplier_refund'].includes(form.kind)">采购单<select v-model="form.purchase_order" required @change="choosePurchase"><option :value="null">请选择采购单</option><option v-for="row in purchases.filter(row => !['draft', 'cancelled'].includes(row.status))" :key="row.id" :value="row.id">{{ row.purchase_no }} · {{ row.supplier_name }} · {{ row.currency }}</option></select></label>
        <label v-if="form.kind === 'unallocated_advance'">客户<select v-model="form.customer" required><option :value="null">请选择客户</option><option v-for="row in customers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        <label v-if="form.kind === 'unallocated_payment'">供应商<select v-model="form.supplier" required><option :value="null">请选择供应商</option><option v-for="row in suppliers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        </fieldset>
        <div v-if="currencyChangeMessage" class="change-confirm" role="alert"><p>{{ currencyChangeMessage }}</p><button v-if="pendingKind" type="button" @click="confirmKindChange">切换类型并清空收款输入</button><button v-else-if="pendingOrder" type="button" @click="confirmOrderChange">更换订单</button><button v-else-if="pendingPurchase" type="button" @click="confirmPurchaseChange">更换采购单</button><button v-else-if="pendingCustomer !== undefined" type="button" @click="confirmCustomerChange">更换客户</button><button v-else type="button" @click="confirmCurrencyChange">清空金额并切换币种</button><button type="button" class="secondary" @click="cancelCurrencyChange">取消</button></div>
        <p v-if="incompatibleRelations" class="error" role="alert">当前类型与已选择的客户或合同不匹配。<button type="button" @click="clearIncompatibleRelations">清除不适用的关联</button></p>
        <fieldset v-if="!savedReceipt && form.kind === 'customer_receipt'" class="receipt-adjustments" :disabled="saving || !!savedReceipt"><legend>收款扣减与核销</legend>
          <label>客户实际汇款金额（{{ form.currency }}）<input v-model="receiptRemittance" v-money-input type="number" min="0" step="any" placeholder="留空时按到账与差额明细计算"></label>
          <p class="field-hint">银行实际到账 {{ form.currency }} {{ formatMoney(form.amount || 0) }}；预计客户汇款 {{ form.currency }} {{ formatMoney(receiptRemittance || receiptRemittancePreview) }}。结汇额度只按银行核实的原币到账计算。</p>
          <div v-for="(line, index) in receiptAdjustments" :key="index" class="adjustment-card">
            <header><strong>扣减明细 {{ index + 1 }}</strong><button type="button" class="secondary" @click="removeReceiptAdjustment(index)">移除</button></header>
            <div class="adjustment-grid">
              <label>性质<select v-model="line.nature" @change="onAdjustmentNatureChange(line)"><option value="discount">优惠/减免</option><option value="bank_fee">银行手续费</option><option value="pending_difference">待核实差额</option><option value="other">其他扣减</option></select></label>
              <label>金额（{{ form.currency }}）<input v-model="line.amount" v-money-input type="number" min="0.0001" step="any" required></label>
              <label>处理方式<select v-model="line.handling"><option v-for="option in adjustmentHandlingOptions(line.nature)" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
              <label v-if="line.nature === 'discount' || line.handling === 'applied'">关联应收计划<select v-model="line.plan" @change="onReceiptAdjustmentPlanChange(line)"><option value="">请选择</option><option v-for="plan in eligibleReceiptPlans" :key="plan.id" :value="plan.id">{{ plan.contract_no }} · 剩余应收 {{ formatMoney(plan.remaining_amount) }}</option></select></label>
              <label v-if="line.nature === 'discount' && line.handling === 'already_in_order' && approvedReceiptChanges.length">订单金额修订<select v-model="line.contract_change"><option value="">按订单已有优惠金额</option><option v-for="change in approvedReceiptChanges" :key="change.id" :value="change.id">修订 #{{ change.id }} · {{ change.amount_delta }} {{ form.currency }}</option></select></label>
            </div>
            <label>原因<textarea v-model="line.reason" rows="2" maxlength="500" required></textarea></label>
            <label>依据凭证<input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="line.file = $event.target.files[0]"></label>
            <div class="proof-line"><span>{{ line.evidence_name || (line.evidence ? '凭证已关联' : '未上传凭证') }}</span><button type="button" class="secondary" :disabled="adjustmentUploadBusy || !line.file" @click="uploadAdjustmentEvidence(line)">{{ adjustmentUploadBusy ? '上传中…' : '上传凭证' }}</button></div>
            <p v-if="line.nature === 'bank_fee'" class="field-hint">银行扣费会解释汇款额与到账额差异；手续费只记录一次，不重复减少到账金额。</p>
            <p v-else-if="line.nature === 'discount' && line.handling === 'already_in_order'" class="field-hint">只记录订单已有优惠，不会再次抵减应收。</p>
            <p v-else-if="line.handling === 'pending'" class="field-hint">待核实项目不会自动冲减订单应收。</p>
          </div>
          <button type="button" class="secondary" @click="addReceiptAdjustment">添加扣减明细</button>
          <div v-if="form.customer && eligibleReceiptPlans.length" class="receipt-plan-area">
            <p>单个订单可按应收计划顺序核销；需要分配多张订单时添加计划。</p>
            <button v-if="!multiOrderMode" type="button" class="secondary" @click="addReceiptAllocation">分配到多张订单</button>
            <div v-for="(item, index) in receiptAllocations" :key="index" class="adjustment-grid receipt-allocation-row">
              <label>订单应收计划<select v-model="item.plan" required><option value="">请选择</option><option v-for="plan in eligibleReceiptPlans" :key="plan.id" :value="plan.id">{{ plan.contract_no }} · {{ plan.currency }} · 剩余 {{ formatMoney(plan.remaining_amount) }}</option></select></label>
              <label>本次核销金额（{{ form.currency }}）<input v-model="item.amount" v-money-input type="number" min="0.0001" step="any" required></label>
              <button type="button" class="secondary" @click="removeReceiptAllocation(index)">移除计划</button>
            </div>
            <button v-if="multiOrderMode" type="button" class="secondary" @click="addReceiptAllocation">添加订单计划</button>
          </div>
        </fieldset>
        <fieldset v-if="!savedReceipt" :disabled="saving"><legend>收付款信息</legend>
        <label>支付方式<input v-model="form.payment_method" placeholder="银行转账、现金等"></label><label>银行参考号<input v-model="form.reference"></label><label>备注<input v-model="form.notes"></label>
        </fieldset>
        <p v-if="!savedReceipt && form.kind === 'customer_receipt'">未核实差额保留应收；实际到账超出核销金额的部分保留为未分配预收款。</p>
        <p v-else-if="form.kind === 'supplier_payment'">款项按采购单付款计划核销；超出计划的部分保留为未分配预付款。</p>
        <div v-if="form.kind === 'customer_receipt' && form.currency === 'CNY'" class="empty-note">本笔收款无需登记外币结汇。</div>
        <button v-if="form.kind === 'customer_receipt' && form.currency !== 'CNY' && !settlementOpen && !savedReceipt" type="button" class="settlement-expand" @click="settlementOpen = true">登记结汇到账</button>
        <section v-if="settlementOpen && form.kind === 'customer_receipt' && form.currency !== 'CNY'" class="settlement-inline-area">
          <p v-if="savedReceipt" class="notice" role="status">收款已保存，流水号 {{ savedReceipt.transaction_no }}。结汇失败时重试只会提交结汇信息。</p>
          <CashEventEntryForm mode="linked" :order="selectedOrder" :receipt="savedReceipt" @state-change="onSettlementStateChange" @created="onSettlementCreated" @updated="onSettlementUpdated" />
        </section>
        <p v-if="form.kind === 'refund'">用于退回已经收到的订单货款；售后赔偿、运费补贴等请登记为订单费用。</p>
        <p v-else-if="form.kind === 'supplier_refund'">用于供应商退回已经支付的采购款。</p>
        <p v-if="error" class="error">{{ error }}</p>
        <footer>
          <button type="button" @click="closeForm" :disabled="saving || receiptLookupLoading || settlementSnapshot?.busy">{{ savedReceipt ? '关闭' : '取消' }}</button>
          <button v-if="!savedReceipt" :disabled="saving || adjustmentUploadBusy || receiptLookupLoading || !referencesLoaded || (form.kind === 'customer_receipt' && (orderSearchLoading || !!orderSearchError))">{{ saving ? '保存中…' : adjustmentUploadBusy ? '凭证上传中…' : receiptLookupLoading ? '核对中…' : saveOutcome === 'unknown' && form.kind === 'customer_receipt' ? '核对收款流水' : saveOutcome === 'unknown' ? '按原编号重试' : saveOutcome === 'rejected' && settlementOpen ? '按原编号重试保存' : settlementOpen && form.kind === 'customer_receipt' && form.currency !== 'CNY' ? '保存收款并继续' : '保存' }}</button>
        </footer>
      </form>
    </div>
    <div v-if="allocation && can('transactions', 'update')" class="mask"><form class="dialog" role="dialog" aria-modal="true" aria-labelledby="allocation-title" @submit.prevent="allocate"><header class="dialog-head"><div><h3 id="allocation-title">核销预收预付款</h3><p>仅分配现有余额，不会新增现金流水。</p></div><button type="button" class="close" aria-label="关闭" @click="allocation = null">×</button></header><p class="dialog-context">{{ allocation.customer_name || allocation.supplier_name }} · {{ allocation.currency }} 可分配 {{ formatMoney(allocation.unallocated_amount ?? Math.max(0, Number(allocation.allocation_capacity ?? allocation.amount) - Number(allocation.allocated_amount))) }}</p><label>待结计划<select v-model="allocationPlan" required><option value="">请选择</option><option v-for="plan in eligiblePlans" :key="plan.id" :value="plan.id">{{ plan.contract_no }} · {{ plan.notes || '无备注' }} · 待结 {{ formatMoney(plan.remaining_amount) }}</option></select></label><p v-if="!eligiblePlans.length" class="empty-note">暂无币种与往来方匹配的待结计划。</p><label>核销金额（{{ allocation.currency }}）<input v-model="allocationAmount" type="number" min="0.0001" step="0.0001" required></label><p v-if="error" class="error" role="alert">{{ error }}</p><footer><button type="button" class="secondary" @click="allocation = null">取消</button><button :disabled="saving || !allocationPlan">{{ saving ? '保存中…' : '确认核销' }}</button></footer></form></div>
    <div v-if="voidTarget && can('transactions', 'update')" class="mask"><form class="dialog" role="dialog" aria-modal="true" aria-labelledby="void-title" @submit.prevent="submitVoid"><header class="dialog-head"><div><h3 id="void-title">作废财务流水</h3><p>此操作会同步作废拆分流水，并恢复关联收付款计划。</p></div><button type="button" class="close" aria-label="关闭" @click="voidTarget = null">×</button></header><dl class="void-summary"><dt>流水号</dt><dd>{{ voidTarget.transaction_no }}</dd><dt>金额</dt><dd>{{ voidTarget.currency }} {{ formatMoney(voidTarget.amount) }}</dd><dt>往来方 / 合同</dt><dd>{{ voidTarget.customer_name || voidTarget.supplier_name || '—' }} / {{ voidTarget.order_no || voidTarget.purchase_no || '未关联合同' }}</dd></dl><label>作废原因<textarea v-model="voidReason" maxlength="500" rows="4" required /></label><p v-if="error" class="error" role="alert">{{ error }}</p><footer><button type="button" class="secondary" @click="voidTarget = null">取消</button><button :disabled="voidSaving || !voidReason.trim()">{{ voidSaving ? '保存中…' : '确认作废' }}</button></footer></form></div>
  </section>
</template>

<style scoped>
.cash-link{display:inline-flex;align-items:center;padding:8px 12px;border:1px solid #cbdcd3;border-radius:8px;color:#0d5c4e;text-decoration:none;background:#fff;font-weight:700;white-space:nowrap}.cash-link:hover{background:#f1f8f4}
.contract-link{color:#08705f;text-decoration:none}.contract-link:hover{text-decoration:underline}
.txn{padding:0}.txn>header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.page-lede{margin:0;color:#718078}.txn p{color:#718078}.txn button{padding:8px 13px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;cursor:pointer}.txn button:hover{border-color:#8db7a7;background:#f5faf7}.txn button:disabled{opacity:.55;cursor:not-allowed}.filters{display:grid;grid-template-columns:minmax(220px,1.5fr) repeat(4,minmax(130px,1fr)) auto;gap:10px;align-items:end;margin:20px 0;padding:16px;border:1px solid #e2e8e4;border-radius:12px;background:#fff}.filters label{display:grid;gap:5px;color:#586b63;font-size:var(--text-caption)}.filters input,.filters select{width:100%;height:39px;padding:0 10px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#253b33}.filters .filter-actions{display:flex;gap:8px}.filters .filter-error{grid-column:1/-1;margin:0}.filters button,.dialog footer button{white-space:nowrap}.filters .secondary,.dialog .secondary{background:#fff;color:#344d44}.notice{margin:12px 0;padding:10px 14px;border:1px solid #b8d8ca;border-radius:9px;background:#eff8f3;color:#1d4d40!important}.txn td small{display:block;color:#718078;font-size:var(--text-caption);margin-top:4px}.txn>table{display:block;overflow:auto;background:#fff;width:100%;border-collapse:collapse;border:1px solid #e2e8e4;border-radius:12px;white-space:nowrap}.txn th,.txn td{padding:12px;text-align:left;border-bottom:1px solid #edf1ee}.txn th{color:#60736b;background:#f6faf8;font-size:var(--text-body)}.mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:60;padding:16px}.dialog{background:#fff;padding:24px;border-radius:14px;width:min(620px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;box-shadow:0 22px 60px #001a1340}.dialog h3{margin:0;font-size:var(--text-dialog)}.dialog-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:16px}.dialog-head p{margin:5px 0 0;font-size:var(--text-caption)}.dialog-head .close{padding:2px 8px;font-size:22px;line-height:1}.dialog label{display:grid;gap:5px;margin:10px 0;color:#3d5149;font-size:var(--text-body)}.dialog input,.dialog select,.dialog textarea{box-sizing:border-box;width:100%;padding:9px;border:1px solid #d8e1dd;border-radius:7px;background:#fff;color:#253b33;font:inherit}.dialog textarea{resize:vertical}.dialog fieldset{min-width:0;margin:0 0 14px;padding:12px 14px;border:1px solid #e2e8e4;border-radius:10px}.dialog legend{padding:0 6px;color:#27584b;font-weight:700}.dialog label>small{font-size:var(--text-caption);color:#71847c;font-weight:400}.void-summary{display:grid;grid-template-columns:110px minmax(0,1fr);gap:8px;margin:0 0 14px;font-size:var(--text-body)}.void-summary dt{color:#718078}.void-summary dd{margin:0;color:#253b33;overflow-wrap:anywhere}.field-hint,.category-hint{display:block;margin:-4px 0 10px;color:#71847c;font-size:var(--text-caption)}.category-hint{padding:8px 10px;border-radius:7px;background:#f3f8f5}.order-picker{margin-top:8px}.order-picker>p{margin:8px 0 0;font-size:var(--text-caption)}.order{display:block;width:100%;margin:5px 0;text-align:left}.dialog footer{display:flex;justify-content:end;gap:8px;margin-top:18px}.dialog footer button:last-child{background:#0d4b40;color:#fff;border-color:#0d4b40}.error{color:#b42318}.empty-note{padding:10px 12px;border-radius:8px;background:#f6f8f6}.txn .summary-cards{margin-top:16px}@media(max-width:1050px){.filters{grid-template-columns:repeat(3,minmax(140px,1fr))}.filters .filter-search{grid-column:span 2}}@media(max-width:620px){.txn>header{align-items:stretch;flex-direction:column}.txn>header>button{width:100%}.filters{grid-template-columns:1fr 1fr}.filters .filter-search{grid-column:1/-1}.filters .filter-actions{grid-column:1/-1}.filters .filter-actions button{flex:1}.txn>table{white-space:nowrap}.dialog{padding:18px}.dialog fieldset{padding:10px}.void-summary{grid-template-columns:80px minmax(0,1fr)}}
.mask{z-index:1600}.detail-grid,.adjustment-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.detail-grid>div{padding:10px 12px;background:#f5f8f6;border-radius:8px}.detail-grid span{display:block;color:#65776f;font-size:var(--text-caption)}.detail-grid strong{display:block;margin-top:5px;overflow-wrap:anywhere}.detail-list{list-style:none;padding:0;margin:8px 0}.detail-list li{padding:10px 0;border-bottom:1px solid #e4ece7;overflow-wrap:anywhere}.detail-list small{display:block;margin-top:5px;color:#62766c}.adjustment-card{border:1px solid #dce7e0;border-radius:8px;padding:12px;margin:12px 0}.adjustment-card>header{display:flex;justify-content:space-between;align-items:center}.proof-line{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.change-confirm{padding:12px;background:#fff5df;border:1px solid #ead5a4;border-radius:8px;margin-bottom:12px}.change-confirm button{margin-right:8px}.detail-dialog section{margin-top:18px}.detail-dialog h4{margin:0 0 8px}@media(max-width:620px){.mask{z-index:1600}.detail-grid,.adjustment-grid{grid-template-columns:1fr}}
</style>
