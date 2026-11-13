<script setup>
import { financeAttemptError, useFinanceAttempts } from '../composables/useFinanceAttempts'
const financeAttempts = useFinanceAttempts()
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
const allocationAttempt = ref(null)
const receiptAttempt = ref(null), pendingReceiptAttempts = ref([])
const receiptAdjustments = ref([]), receiptAllocations = ref([]), receiptPlanChoices = ref([]), approvedReceiptChanges = ref([])
const multiOrderMode = ref(false), adjustmentUploadBusy = ref(false), pendingReceiptChange = ref(null), previousKind = ref('period_expense')
let receiptPlanRequestId = 0, receiptChangeRequestId = 0
const writeoffPlan = ref(''), writeoffAmount = ref(''), writeoffReason = ref(''), writeoffRequestKey = ref(''), writeoffSaving = ref(false)
const correctionTarget = ref(null), correctionAmount = ref(''), correctionReason = ref(''), correctionRequestKey = ref(''), correctionSaving = ref(false)
const voidAttempt = ref(null)
const voidTarget = ref(null), voidReason = ref(''), voidSaving = ref(false)
const detailTarget = ref(null), settlementTarget = ref(null), detailSettlementSnapshot = ref(null), writeoffTarget = ref(null), feeVoucherFile = ref(null), feeVoucherUploading = ref(false)
const refundTarget = ref(null), refundFile = ref(null), refundUploading = ref(false), refundSaving = ref(false), refundAttempt = ref(null)
const refundForm = reactive({ actual_date: '', order: '', amount: '', reason: '', voucher: '', voucherName: '' })
const refundOrders = computed(() => [...new Map((refundTarget.value?.allocations || []).filter(a => a.is_active && a.order).map(a => [a.order, { id: a.order, label: a.contract_no }])).values()])
const filters = reactive({ status: 'confirmed', direction: '', date_from: '', date_to: '' })
const filterRangeError = computed(() => filters.date_from && filters.date_to && filters.date_from > filters.date_to ? '开始日期不能晚于结束日期。' : '')
const routeFilterKey = computed(() => JSON.stringify(['search', 'status', 'direction', 'date_from', 'date_to'].map(key => route.query[key] ?? null)))
const contractKinds = ['customer_receipt', 'order_expense', 'freight_expense', 'sample_expense', 'bank_fee', 'refund']
const orderExpenseCategories = ['样品与打样', '模具', '验货', '运费', '报关', '仓储', '佣金', '其他订单费用']
const receiptFee = computed(() => {
  if (!(['customer_receipt', 'unallocated_advance'].includes(form.kind) && form.direction === 'income')) return 0
  const remitted = Number(form.remittance_amount || form.amount || 0)
  const received = Number(form.amount || 0)
  return Number.isFinite(remitted) && Number.isFinite(received) ? Math.max(0, remitted - received) : 0
})
const eligiblePlans = computed(() => plans.value.filter(plan => plan.status === 'open' && plan.currency === allocation.value?.currency && plan.direction === (allocation.value?.direction === 'income' ? 'receivable' : 'payable') && (plan.order ? plan.customer_id === allocation.value?.customer : plan.supplier_id === allocation.value?.supplier)))
const eligibleReceiptPlans = computed(() => receiptPlanChoices.value.filter(plan => plan.status === 'open' && plan.currency === form.currency && plan.direction === 'receivable' && Number(plan.customer_id) === Number(form.customer)))
const writeoffPlanSource = computed(() => writeoffTarget.value || detailTarget.value)
const writeoffPlans = computed(() => {
  const seen = new Set()
  return (writeoffPlanSource.value?.allocations || []).filter(row => {
    if (!row.is_active || !row.order || Number(row.remaining_amount) <= 0 || seen.has(row.plan)) return false
    seen.add(row.plan)
    return true
  })
})

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
      { value: 'other_expense', label: '其他支出' },
    ],
  },
]
const kindLookup = new Map(kindGroups.flatMap(group => group.options.map(option => [option.value, { ...option, direction: group.direction }])))
const legacyKindLabels = { other: '其他收支', unallocated_advance: '未分配预收款', refund: '客户退款（原收款退回）', exchange_difference: '历史汇兑差额' }
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
  remittance_amount: '', bank_fee_amount: '0', fee_responsibility: '', fee_reason: '', fee_evidence: null,
})
const saveOutcome = ref('not-submitted')
function refreshReceiptAttempts() {
  try {
    pendingReceiptAttempts.value = financeAttempts.list('finance-receipt-').map(key => {
      const saved = JSON.parse(financeAttempts.get(key) || 'null')
      return saved?.payload?.transaction_no ? saved : null
    }).filter(Boolean)
  } catch { pendingReceiptAttempts.value = [] }
}
function recoverReceipt(attempt) {
  openForm()
  if (!showForm.value) return
  Object.assign(form, attempt.payload)
  form.exchange_rate = attempt.payload.exchange_rate ?? (attempt.payload.currency === 'CNY' ? '1' : '')
  form.remittance_amount = attempt.payload.remittance_amount ?? ''
  receiptAdjustments.value = (attempt.payload.receipt_adjustments || []).map(line => ({ ...line, evidence_name: line.evidence_name || '', file: null }))
  receiptAllocations.value = (attempt.payload.plan_allocations || []).map(line => ({ ...line }))
  multiOrderMode.value = Boolean(attempt.payload.plan_allocations?.length)
  previousKind.value = 'customer_receipt'
  selectedOrder.value = attempt.selectedOrder || null
  orderQuery.value = selectedOrder.value?.order_no || ''
  settlementOpen.value = Boolean(attempt.settlementOpen)
  receiptAttempt.value = attempt
  saveOutcome.value = 'unknown'
  formGuard.markClean()
}
const formGuard = useUnsavedChangesGuard({
  data: () => ({ ...form, orderQuery: orderQuery.value, selectedOrder: selectedOrder.value, settlementOpen: settlementOpen.value, savedReceipt: savedReceipt.value?.id || null, settlement: settlementSnapshot.value, receiptAdjustments: receiptAdjustments.value, receiptAllocations: receiptAllocations.value }),
  enabled: () => showForm.value,
  busy: () => saving.value || receiptLookupLoading.value || Boolean(settlementSnapshot.value?.busy),
  confirmOptions: () => saveOutcome.value === 'unknown' ? {
    title: '记账结果尚未确认',
    message: `流水号：${form.transaction_no}。该请求可能已经记账，请先按此编号核对流水。放弃表单不会撤销已保存记录，重新新建可能重复记账。请记录此编号后再决定是否放弃。`,
    cancelText: '返回核对', confirmText: '已记录编号，放弃表单',
  } : savedReceipt.value ? { title: '收款已保存', message: '收款流水已经保存。关闭后仍会保留收款；尚未登记的结汇信息将不再保留。', cancelText: '继续登记结汇', confirmText: '关闭并保留收款' } : {},
})
function closeForm() { return formGuard.requestClose(() => { showForm.value = false }) }
const settlementGuard = useUnsavedChangesGuard({
  data: () => detailSettlementSnapshot.value,
  enabled: () => Boolean(settlementTarget.value),
  busy: () => Boolean(detailSettlementSnapshot.value?.busy),
})
const allocationGuard = useUnsavedChangesGuard({
  data: () => ({ plan: allocationPlan.value, amount: allocationAmount.value }),
  enabled: () => Boolean(allocation.value), busy: () => saving.value,
})
const voidGuard = useUnsavedChangesGuard({
  data: () => ({ reason: voidReason.value }),
  enabled: () => Boolean(voidTarget.value), busy: () => voidSaving.value,
})
const writeoffGuard = useUnsavedChangesGuard({
  data: () => ({ plan: writeoffPlan.value, amount: writeoffAmount.value, reason: writeoffReason.value }),
  enabled: () => Boolean(writeoffTarget.value), busy: () => writeoffSaving.value,
})
const correctionGuard = useUnsavedChangesGuard({
  data: () => ({ amount: correctionAmount.value, reason: correctionReason.value, request: correctionRequestKey.value }),
  enabled: () => Boolean(correctionTarget.value), busy: () => correctionSaving.value,
})
const refundGuard = useUnsavedChangesGuard({ data: () => ({ ...refundForm, file: refundFile.value?.name || '' }), enabled: () => Boolean(refundTarget.value), busy: () => refundSaving.value || refundUploading.value })
function closeSettlement() { return settlementGuard.requestClose(async () => { settlementTarget.value = null; detailSettlementSnapshot.value = null; await load() }) }
function closeAllocation() { return allocationGuard.requestClose(() => { allocation.value = null }) }
function closeVoid() { return voidGuard.requestClose(() => { voidTarget.value = null }) }
function closeWriteoff() { return writeoffGuard.requestClose(() => { writeoffTarget.value = null }) }
function closeCorrection() { return correctionGuard.requestClose(() => { correctionTarget.value = null }) }
function closeRefund() { return refundGuard.requestClose(() => { refundTarget.value = null }) }

const transactionMetrics = computed(() => {
  const sum = direction => rows.value.filter(row => row.direction === direction && row.status === 'confirmed').reduce((total, row) => total + Number(row.rmb_amount || 0), 0)
  return [
    { label: '流水笔数', value: rows.value.length, hint: '当前查询结果' },
    { label: '账面收入（人民币折算参考）', value: `¥ ${formatMoney(sum('income'))}`, hint: '按已确认流水汇总' },
    { label: '账面支出（人民币折算参考）', value: `¥ ${formatMoney(sum('expense'))}`, hint: '按已确认流水汇总' },
    { label: '业务归属流水', value: rows.value.filter(row => row.order || row.purchase_order || row.order_no || row.purchase_no || (row.allocations || []).length).length, hint: '含核销分配及直接关联合同' },
  ]
})
const filtersActive = computed(() => Boolean(query.value.trim() || (filters.status && filters.status !== 'confirmed') || filters.direction || filters.date_from || filters.date_to))
const referenceErrorText = computed(() => referenceErrors.value.join(' '))

function kindLabel(kind) { return kindLookup.get(kind)?.label || legacyKindLabels[kind] || kind || '—' }
function transactionKindLabel(row) {
  if (row?.kind === 'unallocated_advance' && Number(row.allocated_amount) > 0) return '客户收款'
  if (row?.kind === 'unallocated_payment' && Number(row.allocated_amount) > 0) return '供应商付款'
  return kindLabel(row?.kind)
}
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
  if (form.kind !== previousKind.value && (form.kind === 'customer_receipt' || previousKind.value === 'customer_receipt') && (hasReceiptInputs() || form.order || form.customer)) {
    pendingReceiptChange.value = { type: 'kind', value: form.kind, message: '切换类型会清空当前金额及收款明细，请确认。' }
    form.kind = previousKind.value
    return
  }
  applyKind(form.kind)
}
function applyKind(kind) {
  const oldKind = previousKind.value
  form.kind = kind; previousKind.value = kind
  const meta = kindLookup.get(form.kind)
  if (meta) {
    form.direction = meta.direction
    form.category = meta.label
  }
  if (form.kind === 'order_expense') form.category = orderExpenseCategories[0]
  form.customer = null; form.supplier = null; form.purchase_order = null
  if (form.kind !== 'customer_receipt') { settlementOpen.value = false; savedReceipt.value = null; settlementSnapshot.value = null }
  if (!(['customer_receipt', 'unallocated_advance'].includes(form.kind) && form.direction === 'income')) {
    Object.assign(form, { remittance_amount: '', bank_fee_amount: '0', fee_responsibility: '', fee_reason: '', fee_evidence: null })
    feeVoucherFile.value = null
  }
  if (!contractKinds.includes(form.kind)) {
    form.order = null
    selectedOrder.value = null
    orders.value = []
    orderQuery.value = ''
  }
  if (kind === 'customer_receipt') {
    form.customer = selectedOrder.value?.customer || null
    form.currency = selectedOrder.value?.currency || 'USD'
    form.exchange_rate = form.currency === 'CNY' ? '1' : ''
    void loadReceiptPlans()
  } else if (oldKind === 'customer_receipt') {
    form.currency = 'CNY'; form.exchange_rate = '1'
  }
}
function hasReceiptInputs() { return Boolean(form.amount || form.remittance_amount || (form.currency !== 'CNY' && form.exchange_rate) || receiptAdjustments.value.length || receiptAllocations.value.length) }
function clearReceiptInputs() { form.amount = ''; form.remittance_amount = ''; form.exchange_rate = form.currency === 'CNY' ? '1' : ''; receiptAdjustments.value = []; receiptAllocations.value = []; multiOrderMode.value = false; approvedReceiptChanges.value = [] }
function setReceiptCurrency(currency) { const changed = form.currency !== currency; form.currency = currency; if (changed || currency === 'CNY') form.exchange_rate = currency === 'CNY' ? '1' : ''; if (currency === 'CNY') { settlementOpen.value = false; settlementSnapshot.value = null }; void loadReceiptPlans() }
function requestCurrencyChange(event) {
  const currency = event.target.value
  if (currency === form.currency) return
  if (form.kind === 'customer_receipt' && (hasReceiptInputs() || (selectedOrder.value && selectedOrder.value.currency !== currency))) {
    event.target.value = form.currency
    pendingReceiptChange.value = { type: 'currency', value: currency, message: `切换到 ${currency} 会清空收款金额、扣减和核销分配，并解除不匹配的订单。` }
  } else { form.currency = currency; onCurrencyChange(); if (form.kind === 'customer_receipt') void loadReceiptPlans() }
}
function requestCustomerChange(event) {
  const customer = Number(event.target.value) || null
  if (customer === Number(form.customer || 0)) return
  if (hasReceiptInputs()) { event.target.value = form.customer || ''; pendingReceiptChange.value = { type: 'customer', value: customer, message: '更换客户会清空收款金额、扣减和核销分配，请确认。' }; return }
  applyReceiptCustomer(customer)
}
function applyReceiptCustomer(customer) { form.customer = customer; form.order = null; selectedOrder.value = null; orderQuery.value = ''; receiptAllocations.value = []; void loadReceiptPlans() }
function confirmReceiptChange() {
  const change = pendingReceiptChange.value
  if (!change) return
  clearReceiptInputs(); pendingReceiptChange.value = null
  if (change.type === 'kind') { form.order = null; selectedOrder.value = null; orderQuery.value = ''; applyKind(change.value) }
  else if (change.type === 'customer') applyReceiptCustomer(change.value)
  else if (change.type === 'currency') { if (selectedOrder.value && selectedOrder.value.currency !== change.value) { form.order = null; selectedOrder.value = null; orderQuery.value = '' }; setReceiptCurrency(change.value) }
  else if (change.type === 'order') applyReceiptOrder(change.value)
}
function openForm() {
  if (saving.value || showForm.value || !can('transactions', 'create')) return
  Object.assign(form, { transaction_no: '', transaction_date: new Date().toLocaleDateString('en-CA'), kind: 'period_expense', direction: 'expense', category: '其他期间费用', amount: '', currency: 'CNY', exchange_rate: '1', payment_method: '', reference: '', notes: '', order: null, customer: null, supplier: null, purchase_order: null, remittance_amount: '', bank_fee_amount: '0', fee_responsibility: '', fee_reason: '', fee_evidence: null })
  settlementOpen.value = false; savedReceipt.value = null; settlementSnapshot.value = null
  feeVoucherFile.value = null
  receiptAdjustments.value = []; receiptAllocations.value = []; receiptPlanChoices.value = []; approvedReceiptChanges.value = []; multiOrderMode.value = false; pendingReceiptChange.value = null; previousKind.value = 'period_expense'
  receiptPlanRequestId++; receiptChangeRequestId++
  selectedOrder.value = null
  orderQuery.value = ''
  orders.value = []
  error.value = ''
  notice.value = ''
  saveOutcome.value = 'not-submitted'
  receiptAttempt.value = null
  showForm.value = true
  formGuard.markClean()
}
function onCurrencyChange() {
  if (form.currency === 'CNY') form.exchange_rate = '1'
  else if (form.exchange_rate === '1') form.exchange_rate = ''
}
function openDetail(row) { detailTarget.value = row }
function openSettlement(row) {
  if (!can('transactions', 'create') || row.status !== 'confirmed' || row.direction !== 'income' || row.currency === 'CNY') return
  settlementTarget.value = row
  detailSettlementSnapshot.value = null
  settlementGuard.markClean()
}
function onDetailSettlementStateChange(value) { detailSettlementSnapshot.value = value }
async function onDetailSettlementCreated() { detailSettlementSnapshot.value = { ...detailSettlementSnapshot.value, busy: false }; settlementGuard.markClean(); await load() }
async function onDetailSettlementUpdated() { detailSettlementSnapshot.value = { ...detailSettlementSnapshot.value, busy: false }; settlementGuard.markClean(); await load() }
function unallocatedAmount(row) { return Number(row.unallocated_amount ?? (Number(row.amount) - Number(row.allocated_amount))) }
function hasPendingAllocation(row) {
  try {
    const value = JSON.parse(financeAttempts.get(`finance-allocation-${row.id}`) || 'null')
    return Boolean(value?.key && value?.plan && value?.amount)
  } catch { return false }
}
function canAllocateReceipt(row) {
  const flexible = ['unallocated_advance', 'unallocated_payment'].includes(row.kind) || (row.kind === 'customer_receipt' && !row.plan && !row.order)
  return flexible && (hasPendingAllocation(row) || Number(row.allocation_capacity ?? row.amount) > Number(row.allocated_amount || 0))
}
function appliedAmount(row) { return (row.allocations || []).filter(item => item.is_active).reduce((sum, item) => sum + Number(item.amount || 0), 0) }
function readableTime(value) { return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—' }
function confirmerDisplay(actor) { return actor?.kind === 'development_superadmin' ? '开发身份' : actor?.kind === 'authenticated_user' ? `账号 #${actor.user_id}` : '—' }
async function copyRecordNumber(value) { try { await navigator.clipboard.writeText(value); notice.value = '流水号已复制。' } catch { error.value = '无法自动复制，请手动选择流水号。' } }
function adjustmentNatureLabel(value) { return ({ discount: '优惠/减免', bank_fee: '银行手续费', pending_difference: '待核实差额', other: '其他扣减' })[value] || value }
function adjustmentHandlingLabel(value) { return ({ company: '我方承担', customer: '客户承担，保留应收差额', pending: '待核实，不自动抵减', applied: '已授权抵减应收', already_in_order: '已计入订单金额' })[value] || value }
async function uploadReceiptProof() {
  if (!feeVoucherFile.value || feeVoucherUploading.value) return
  feeVoucherUploading.value = true; error.value = ''
  try {
    const body = new FormData(); body.append('file', feeVoucherFile.value)
    const response = await api.post('/transactions/voucher-upload/', body)
    form.fee_evidence = response.data.id
    notice.value = `凭证上传成功：${response.data.name}`
  } catch (err) { error.value = apiErrorMessage(err) || '收款凭证上传失败，请重试。' }
  finally { feeVoucherUploading.value = false }
}
function openRefund(row) {
  refundTarget.value = row; refundFile.value = null; refundAttempt.value = null; error.value = ''; notice.value = ''
  Object.assign(refundForm, { actual_date: new Date().toLocaleDateString('en-CA'), order: refundOrders.value.length === 1 && Number(row.unallocated_amount) === 0 ? refundOrders.value[0].id : '', amount: '', reason: '', voucher: '', voucherName: '' })
  try { refundAttempt.value = JSON.parse(financeAttempts.get(`finance-refund-${row.id}`) || 'null') } catch { /* submission checks storage */ }
  if (refundAttempt.value?.key) { Object.assign(refundForm, refundAttempt.value.payload); notice.value = '上次退款结果待确认，请按原内容重试。' }
  refundGuard.markClean()
}
async function uploadRefundProof() {
  if (!refundFile.value || refundUploading.value || refundAttempt.value) return
  refundUploading.value = true; error.value = ''
  try {
    const body = new FormData(); body.append('file', refundFile.value)
    const result = await api.post('/transactions/voucher-upload/', body)
    refundForm.voucher = result.data.id; refundForm.voucherName = result.data.name
    notice.value = `退款凭证上传成功：${result.data.name}`
  } catch (err) { error.value = apiErrorMessage(err) || '凭证上传失败，请重试。' }
  finally { refundUploading.value = false }
}
async function submitRefund() {
  if (refundSaving.value || !refundTarget.value) return
  const existing = refundAttempt.value
  const attempt = existing || { key: `REF-${crypto.randomUUID()}`, payload: { ...refundForm } }
  const storageKey = `finance-refund-${refundTarget.value.id}`
  try { financeAttempts.save(storageKey, JSON.stringify(attempt)) }
  catch (err) { error.value = financeAttemptError(err, '浏览器无法保存本次退款身份，请恢复浏览器存储后重试。'); return }
  refundAttempt.value = attempt; refundSaving.value = true; error.value = ''; notice.value = ''
  const { voucherName, ...payload } = attempt.payload
  try {
    await api.post(`/transactions/${refundTarget.value.id}/refund-cash/`, payload, { headers: { 'Idempotency-Key': attempt.key } })
    financeAttempts.remove(storageKey, JSON.stringify(attempt)); refundAttempt.value = null; refundGuard.markClean(); refundTarget.value = null
    await load(); notice.value = '退款已登记，原收款和凭证已保留。'
  } catch (err) {
    if (!existing && err.response?.status === 400) {
      financeAttempts.remove(storageKey, JSON.stringify(attempt)); refundAttempt.value = null
      error.value = apiErrorMessage(err) || '退款未保存，请检查信息。'
    } else error.value = apiErrorMessage(err) || '退款结果待确认，请按原内容重试。'
  } finally { refundSaving.value = false }
}
async function load() {
  if (filterRangeError.value) { loadError.value = filterRangeError.value; loading.value = false; return }
  loading.value = true; loadError.value = ''
  try {
    const result = await listAll('/transactions/', { params: { ...filters, search: query.value } })
    rows.value = result
    if (detailTarget.value) detailTarget.value = result.find(row => row.id === detailTarget.value.id) || null
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
  if (form.kind === 'customer_receipt' && hasReceiptInputs() && (Number(form.order || 0) !== Number(row.id) || form.currency !== row.currency || (form.customer && Number(form.customer) !== Number(row.customer)))) {
    pendingReceiptChange.value = { type: 'order', value: row, message: '更换订单会清空当前金额、扣减和核销分配，请确认。' }; return
  }
  if (form.kind === 'customer_receipt') { applyReceiptOrder(row); return }
  form.order = row.id
  selectedOrder.value = { id: row.id, order_no: row.order_no, currency: row.currency }
  orderQuery.value = row.order_no
  if (['customer_receipt', 'refund'].includes(form.kind)) { form.currency = row.currency; form.exchange_rate = row.exchange_rate }
  orders.value = []
}
function applyReceiptOrder(row) {
  form.order = row.id; form.customer = row.customer
  selectedOrder.value = { id: row.id, order_no: row.order_no, currency: row.currency, customer: row.customer }
  orderQuery.value = row.order_no; orders.value = []; setReceiptCurrency(row.currency)
  void loadReceiptContractChanges(row.id)
}
async function loadReceiptPlans() {
  const requestId = ++receiptPlanRequestId, customer = form.customer, currency = form.currency
  if (!customer) { receiptPlanChoices.value = []; return }
  try { const rows = await listAll('/payment-plans/', { params: { status: 'open' } }); if (requestId === receiptPlanRequestId) receiptPlanChoices.value = rows.filter(plan => Number(plan.customer_id) === Number(customer) && plan.direction === 'receivable' && plan.currency === currency) }
  catch (err) { if (requestId === receiptPlanRequestId) { receiptPlanChoices.value = []; error.value = apiErrorMessage(err) || '应收计划加载失败，请重试。' } }
}
async function loadReceiptContractChanges(orderId) {
  const requestId = ++receiptChangeRequestId
  if (!orderId) { approvedReceiptChanges.value = []; return }
  try { const rows = await listAll('/contract-changes/', { params: { order: orderId } }); if (requestId === receiptChangeRequestId) approvedReceiptChanges.value = rows.filter(row => row.status === 'approved' && Number(row.amount_delta) < 0) }
  catch { if (requestId === receiptChangeRequestId) approvedReceiptChanges.value = [] }
}
function onReceiptAdjustmentPlanChange(line) { const plan = eligibleReceiptPlans.value.find(item => Number(item.id) === Number(line.plan)); void loadReceiptContractChanges(plan?.order || form.order) }
function addReceiptAdjustment() { receiptAdjustments.value.push({ nature: 'bank_fee', amount: '', handling: 'pending', reason: '', evidence: null, evidence_name: '', file: null, plan: '', contract_change: '' }) }
function onAdjustmentNatureChange(line) { line.handling = 'pending'; line.plan = ''; line.contract_change = '' }
function adjustmentHandlingOptions(nature) {
  if (nature === 'bank_fee') return [{ value: 'pending', label: '待核实' }, { value: 'company', label: '我方承担' }, { value: 'customer', label: '客户承担' }]
  if (nature === 'discount') return [{ value: 'pending', label: '待核实' }, { value: 'applied', label: '授权抵减应收' }, { value: 'already_in_order', label: '已计入订单金额' }]
  if (nature === 'other') return [{ value: 'pending', label: '待核实' }, { value: 'applied', label: '凭证核准抵减应收' }]
  return [{ value: 'pending', label: '待核实' }]
}
async function uploadAdjustmentEvidence(line) {
  if (!line.file || adjustmentUploadBusy.value) return
  adjustmentUploadBusy.value = true; error.value = ''
  try { const body = new FormData(); body.append('file', line.file); const proof = (await api.post('/transactions/voucher-upload/', body)).data; line.evidence = proof.id; line.evidence_name = proof.name; line.file = null }
  catch (err) { error.value = apiErrorMessage(err) || '扣减凭证上传失败，请重试。' }
  finally { adjustmentUploadBusy.value = false }
}
function choosePurchase() {
  const row = purchases.value.find(row => row.id === form.purchase_order)
  if (row) { form.currency = row.currency; form.exchange_rate = row.exchange_rate }
}
async function save() {
  if (saving.value || !can('transactions', 'create')) return
  if (savedReceipt.value) return
  if (!referencesLoaded.value) { error.value = '客户、供应商或采购单资料尚未加载完成，请重试后再保存。'; return }
  if (form.kind === 'customer_receipt' && (orderSearchLoading.value || orderSearchError.value)) { error.value = '订单选项尚未成功加载，请重试后再保存。'; return }
  if (pendingReceiptChange.value) { error.value = '请先确认或取消当前关联变更。'; return }
  if (form.kind === 'unallocated_advance' && form.direction === 'income') {
    form.bank_fee_amount = receiptFee.value.toFixed(4)
    if (String(form.remittance_amount || '').trim() && Number(form.remittance_amount) < Number(form.amount)) { error.value = '客户汇款金额不能低于银行实际到账金额。'; return }
    if (receiptFee.value > 0 && !form.fee_responsibility) { error.value = '请选择银行扣费承担方；尚未查清时可选“待查”。'; return }
    if (receiptFee.value > 0 && !String(form.fee_reason || '').trim()) { error.value = '请填写扣费原因或核实说明。'; return }
    if (Number(form.bank_fee_amount || 0) > 0 && !form.fee_evidence) { error.value = '请先上传银行收款凭证。'; return }
  }
  if (form.kind === 'customer_receipt') {
    if (!form.customer) { error.value = '请选择收款客户，可以暂不关联订单。'; return }
    if (form.order && (Number(selectedOrder.value?.customer) !== Number(form.customer) || selectedOrder.value?.currency !== form.currency)) { error.value = '收款客户和币种须与所选订单一致。'; return }
    if (receiptAdjustments.value.some(line => !line.amount || Number(line.amount) <= 0 || String(line.reason || '').trim().length < (line.handling === 'applied' ? 5 : 3))) { error.value = '请补齐每条扣减明细的金额和原因。'; return }
    if (receiptAdjustments.value.some(line => (line.nature === 'bank_fee' || line.handling === 'applied') && !line.evidence)) { error.value = '银行扣费及已核准抵减须上传依据凭证。'; return }
    const planIds = receiptAllocations.value.map(line => Number(line.plan))
    if (multiOrderMode.value && (!planIds.length || planIds.some(id => !id) || new Set(planIds).size !== planIds.length || receiptAllocations.value.some(line => !line.amount || Number(line.amount) <= 0))) { error.value = '请选择不同的应收计划并填写正数核销金额。'; return }
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
    const payload = receiptAttempt.value?.payload || { ...form,
      receipt_adjustments: receiptAdjustments.value.map(line => ({ nature: line.nature, amount: line.amount, handling: line.handling, reason: line.reason, evidence: line.evidence || null, plan: line.plan || null, contract_change: line.contract_change || null })),
      ...(multiOrderMode.value ? { plan_allocations: receiptAllocations.value.map(line => ({ plan: line.plan, amount: line.amount })) } : {}) }
    if (!receiptAttempt.value) {
      if (!String(payload.remittance_amount || '').trim()) delete payload.remittance_amount
      if (payload.exchange_rate === '') delete payload.exchange_rate
      delete payload.bank_fee_amount; delete payload.fee_responsibility; delete payload.fee_reason; delete payload.fee_evidence
    }
    if (!payload.transaction_no) delete payload.transaction_no
    const existingAttempt = receiptAttempt.value
    const savedAttempt = existingAttempt || { payload, selectedOrder: selectedOrder.value, settlementOpen: settlementOpen.value }
    const storageKey = `finance-receipt-${payload.transaction_no}`
    try { financeAttempts.save(storageKey, JSON.stringify(savedAttempt)) }
    catch (err) { saveOutcome.value = 'rejected'; error.value = financeAttemptError(err, '浏览器无法保存本次收款标识，请检查浏览器存储后重试。'); return }
    receiptAttempt.value = savedAttempt
    refreshReceiptAttempts()
    const attempt = await saveOrVerifyCustomerReceipt({
      outcome: outcomeBeforeSubmit,
      safeReplay: Boolean(existingAttempt),
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
      if (attempt.status === 'rejected' && !existingAttempt) {
        financeAttempts.remove(storageKey, JSON.stringify(savedAttempt)); receiptAttempt.value = null; refreshReceiptAttempts()
      }
      saveOutcome.value = existingAttempt ? 'unknown' : attempt.status
      const duplicateNumber = Boolean(attempt.error?.response?.data?.transaction_no)
      error.value = duplicateNumber ? '编号重复不代表本次保存成功，请核对原流水。' : apiErrorMessage(attempt.error) || (attempt.status === 'unknown' ? '收款结果尚未确认。请先核对原流水。' : '收款保存失败，请核对输入后重试。')
      return
    }
    const receipt = attempt.receipt
    financeAttempts.remove(storageKey, JSON.stringify(savedAttempt)); receiptAttempt.value = null; refreshReceiptAttempts()
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
watch(() => financeAttempts.isReady(), refreshReceiptAttempts, { immediate: true })
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
  try { voidAttempt.value = JSON.parse(financeAttempts.get(`finance-void-${row.id}`) || 'null') } catch { voidAttempt.value = null }
  voidReason.value = voidAttempt.value?.payload.reason || ''
  error.value = ''
  notice.value = ''
  voidGuard.markClean()
}
async function submitVoid() {
  if (!can('transactions', 'update')) return
  const reason = voidReason.value.trim()
  if (!reason || voidSaving.value) return
  voidSaving.value = true
  error.value = ''; notice.value = ''
  try {
    const storageKey = `finance-void-${voidTarget.value.id}`
    const attempt = voidAttempt.value || { key: `VOID-${crypto.randomUUID()}`, payload: { reason } }
    financeAttempts.save(storageKey, JSON.stringify(attempt))
    const replaying = Boolean(voidAttempt.value)
    voidAttempt.value = attempt
    try {
      await api.post(`/transactions/${voidTarget.value.id}/void/`, attempt.payload, { headers: { 'Idempotency-Key': attempt.key } })
    } catch (err) {
      if (!replaying && err.response?.status === 400) { financeAttempts.remove(storageKey, JSON.stringify(attempt)); voidAttempt.value = null }
      throw err
    }
    financeAttempts.remove(storageKey, JSON.stringify(attempt))
    voidAttempt.value = null
    voidGuard.markClean()
    voidTarget.value = null
    voidReason.value = ''
    await load()
    notice.value = '财务流水已作废，相关计划已恢复。'
  } catch (err) { error.value = financeAttemptError(err, apiErrorMessage(err) || '流水作废失败，请重试。') } finally { voidSaving.value = false }
}
async function openAllocate(row) {
  if (!can('transactions', 'update')) return
  notice.value = ''; error.value = ''
  try {
    plans.value = await listAll('/payment-plans/', { params: { status: 'open' } })
    allocation.value = row
    let pending = null
    try { pending = JSON.parse(financeAttempts.get(`finance-allocation-${row.id}`) || 'null') } catch { /* unavailable storage is checked before submission */ }
    allocationAttempt.value = pending?.key && pending?.plan && pending?.amount ? pending : null
    allocationPlan.value = allocationAttempt.value?.plan || ''
    allocationAmount.value = allocationAttempt.value?.amount || String(unallocatedAmount(row))
    if (allocationAttempt.value) notice.value = '上次核销结果待确认，请按原内容重试。'
    allocationGuard.markClean()
  } catch (err) { error.value = apiErrorMessage(err) || '收付款计划加载失败，请重试。' }
}
async function allocate() {
  if (saving.value || !can('transactions', 'update')) return
  const existing = allocationAttempt.value
  const selected = eligiblePlans.value.find(item => String(item.id) === String(allocationPlan.value))
  const attempt = existing || { key: `ALLOC-${crypto.randomUUID()}`, plan: allocationPlan.value, amount: String(allocationAmount.value), planLabel: selected?.contract_no || '所选计划' }
  const storageKey = `finance-allocation-${allocation.value.id}`
  try { financeAttempts.save(storageKey, JSON.stringify(attempt)) }
  catch (err) { error.value = financeAttemptError(err, '浏览器无法保存本次核销标识，请检查浏览器存储后重试。'); return }
  allocationAttempt.value = attempt
  saving.value = true
  error.value = ''; notice.value = ''
  try {
    await api.post(`/transactions/${allocation.value.id}/allocate/`, { plan: attempt.plan, amount: attempt.amount }, { headers: { 'Idempotency-Key': attempt.key } })
    financeAttempts.remove(storageKey, JSON.stringify(attempt))
    allocationAttempt.value = null; allocationGuard.markClean(); allocation.value = null
    await load(); notice.value = '核销已保存。'
  } catch (err) {
    if (!existing && err.response?.status === 400) {
      financeAttempts.remove(storageKey, JSON.stringify(attempt)); allocationAttempt.value = null
      error.value = apiErrorMessage(err) || '核销未保存，请检查金额和计划。'
    } else error.value = apiErrorMessage(err) || '核销结果待确认，请按原内容重试。'
  } finally { saving.value = false }
}
function openWriteoff(row) {
  if (!can('transactions', 'update') || row.status !== 'confirmed' || row.direction !== 'income') return
  writeoffTarget.value = row
  writeoffPlan.value = ''
  writeoffAmount.value = ''
  writeoffReason.value = ''
  writeoffRequestKey.value = `WOF-${crypto.randomUUID()}`
  error.value = ''; notice.value = ''
  writeoffGuard.markClean()
}
function selectWriteoffPlan() {
  const selected = writeoffPlans.value.find(row => String(row.plan) === String(writeoffPlan.value))
  writeoffAmount.value = selected?.remaining_amount || ''
}
async function submitWriteoff() {
  if (writeoffSaving.value || !can('transactions', 'update') || !writeoffTarget.value) return
  writeoffSaving.value = true; error.value = ''; notice.value = ''
  try {
    await api.post(`/transactions/${writeoffTarget.value.id}/writeoff/`, {
      plan: writeoffPlan.value, amount: writeoffAmount.value,
      reason: writeoffReason.value.trim(), request_key: writeoffRequestKey.value,
    })
    writeoffTarget.value = null
    writeoffGuard.markClean()
    await load()
    notice.value = '授权抹零已登记，未新增现金收款。'
  } catch (err) { error.value = apiErrorMessage(err) || '抹零登记失败，请核对剩余应收后重试。' }
  finally { writeoffSaving.value = false }
}
function openCorrection(source, writeoff) {
  const remaining = Number(writeoff.amount) - Number(writeoff.corrected_amount || 0)
  if (!can('transactions', 'update') || remaining <= 0) return
  correctionTarget.value = { source, writeoff }
  correctionAmount.value = remaining.toFixed(4)
  correctionReason.value = ''
  correctionRequestKey.value = `WOF-CORR-${crypto.randomUUID()}`
  error.value = ''; notice.value = ''
  correctionGuard.markClean()
}
async function submitCorrection() {
  if (correctionSaving.value || !can('transactions', 'update') || !correctionTarget.value) return
  correctionSaving.value = true; error.value = ''; notice.value = ''
  try {
    await api.post(`/transactions/${correctionTarget.value.source.id}/writeoff-corrections/`, {
      writeoff: correctionTarget.value.writeoff.id, amount: correctionAmount.value,
      reason: correctionReason.value.trim(), request_key: correctionRequestKey.value,
    })
    const sourceId = correctionTarget.value.source.id
    correctionGuard.markClean(); correctionTarget.value = null
    await load()
    if (detailTarget.value?.id === sourceId) detailTarget.value = rows.value.find(row => row.id === sourceId) || detailTarget.value
    notice.value = '抹零更正已追加，应收计划已重新计算；未新增现金收付款。'
  } catch (err) { error.value = apiErrorMessage(err) || '抹零更正未完成，请核对后按原请求编号重试。' }
  finally { correctionSaving.value = false }
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
      <div><p class="page-lede">登记客户、供应商收付款和日常费用。流水发生日期用于记账，银行实际日期请在银行资金记录中查看。</p></div>
      <RouterLink v-if="can('transactions', 'view')" class="cash-link" to="/rmb-cash-events">银行资金记录</RouterLink>
      <button v-if="can('transactions', 'create')" :disabled="!referencesLoaded || saving || receiptLookupLoading" @click="openForm">新增记账</button>
    </header>
    <p class="page-lede">{{ BOOK_RMB_NOTE }}</p>
    <p class="page-lede">流水记录实际收付；核销、退款与结汇保留各自业务关系。银行退回和更正须关联原凭证。</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <p v-if="financeAttempts.hasLegacy()" role="status">此浏览器留有旧版待核对记录。请先在财务流水核对原操作结果，再决定是否另行登记。</p>
    <div v-if="pendingReceiptAttempts.length" class="notice" role="status">有 {{ pendingReceiptAttempts.length }} 笔收款结果待确认。<button v-for="item in pendingReceiptAttempts" :key="item.payload.transaction_no" type="button" :disabled="!referencesLoaded || showForm" @click="recoverReceipt(item)">按原内容核对</button></div>
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
      <thead><tr><th>流水发生日期 / 流水号</th><th>收支 / 类型</th><th>往来方 / 合同</th><th>实际收付（原币）</th><th>人民币折算参考</th><th>状态 / 核销</th><th>操作</th></tr></thead>
      <tbody><tr v-if="!rows.length"><td colspan="7"><ListEmptyState entity="财务流水" :filtered="filtersActive && allTransactionsExist" @clear="clearFilters"><template #action>当前还没有财务流水。</template></ListEmptyState></td></tr><tr v-for="row in rows" :key="row.id"><td>{{ row.transaction_date }}<small>{{ row.transaction_no }}<span v-if="row.split_from"> · 拆分记录</span></small></td><td>{{ row.direction_display || directionLabel(row.direction) }}<small>{{ transactionKindLabel(row) }}</small></td><td>{{ row.customer_name || row.supplier_name || '—' }}<small><RouterLink v-if="contractLocation(row)" :to="contractLocation(row)" class="contract-link">{{ row.order ? row.order_no : row.purchase_no }}</RouterLink><span v-else>未关联合同</span></small></td><td>{{ row.currency }} {{ formatMoney(row.amount) }}<small v-if="row.remitted_amount_display && Number(row.remitted_amount_display) !== Number(row.amount)">客户汇款 {{ row.currency }} {{ formatMoney(row.remitted_amount_display) }}</small><small v-if="Number(row.bank_fee_amount) > 0">银行扣费 {{ row.currency }} {{ formatMoney(row.bank_fee_amount) }} · {{ row.fee_responsibility === 'company' ? '我方承担' : row.fee_responsibility === 'customer' ? '客户承担' : row.fee_responsibility === 'mixed' ? '按明细区分' : '待查' }}</small></td><td>{{ row.rmb_amount == null ? '未录入参考汇率' : `¥${formatMoney(row.rmb_amount)}` }}</td><td>{{ row.status_display }}<small v-if="['unallocated_advance', 'unallocated_payment'].includes(row.kind) || (row.kind === 'customer_receipt' && !row.plan && !row.order)">未分配 {{ row.currency }} {{ formatMoney(unallocatedAmount(row)) }}</small><small v-for="item in row.allocations" :key="item.id"><RouterLink v-if="allocationLocation(item)" :to="allocationLocation(item)" class="contract-link">{{ item.contract_no }}</RouterLink><span v-else>{{ item.contract_no }}</span>：{{ formatMoney(item.amount) }} {{ item.is_active ? '已核销' : '已撤回' }}</small><small v-if="row.status === 'cancelled' && row.void_reason">作废原因：{{ row.void_reason }}{{ row.voided_at ? ' · ' + row.voided_at : '' }}</small></td><td><button type="button" @click="openDetail(row)">详情</button><button v-if="can('transactions', 'create') && row.status === 'confirmed' && row.direction === 'income' && row.currency !== 'CNY'" type="button" @click="openSettlement(row)">登记结汇到账</button><button v-if="can('transactions', 'update') && row.status === 'confirmed' && canAllocateReceipt(row)" @click="openAllocate(row)">核销</button><button v-if="can('transactions', 'update') && (row.status === 'confirmed' || financeAttempts.has(`finance-void-${row.id}`)) && !row.split_from" @click="openVoid(row)">作废</button><small v-if="row.split_from">由原始流水统一作废</small><small v-else-if="row.status === 'cancelled'">已作废</small></td></tr></tbody>
    </table>
    </template>

    <div v-if="detailTarget" class="mask">
      <section class="txn-detail dialog" role="dialog" aria-modal="true" aria-labelledby="transaction-detail-title">
        <header class="dialog-head"><div><h3 id="transaction-detail-title">财务流水详情</h3><p>{{ detailTarget.transaction_date }} · {{ transactionKindLabel(detailTarget) }} · {{ detailTarget.customer_name || detailTarget.supplier_name || '未关联往来方' }}</p><p class="record-number">{{ detailTarget.transaction_no }} <button type="button" @click="copyRecordNumber(detailTarget.transaction_no)">复制流水号</button></p></div><button type="button" class="close" aria-label="关闭详情" @click="detailTarget = null">×</button></header>
        <p v-if="notice" class="notice" role="status">{{ notice }}</p><p v-if="error" class="error" role="alert">{{ error }}</p><dl class="txn-detail-grid">
          <dt>原币实收 / 实付</dt><dd>{{ detailTarget.currency }} {{ formatMoney(detailTarget.amount) }}</dd>
          <dt>账面人民币折算参考</dt><dd>{{ detailTarget.rmb_amount == null ? '未录入参考汇率' : `¥${formatMoney(detailTarget.rmb_amount)}` }}</dd>
          <template v-if="Number(detailTarget.bank_fee_amount) > 0">
            <dt>客户汇款</dt><dd>{{ detailTarget.currency }} {{ formatMoney(detailTarget.remitted_amount_display) }}</dd>
            <dt>银行扣费</dt><dd>{{ detailTarget.currency }} {{ formatMoney(detailTarget.bank_fee_amount) }} · {{ detailTarget.fee_responsibility === 'company' ? '我方承担' : detailTarget.fee_responsibility === 'customer' ? '客户承担' : detailTarget.fee_responsibility === 'mixed' ? '按明细区分' : '待查' }}</dd>
            <dt>扣费依据</dt><dd>{{ detailTarget.fee_reason || '—' }}</dd>
            <dt>凭证</dt><dd><a v-if="detailTarget.fee_evidence" :href="`/api/transactions/${detailTarget.id}/voucher-download/`">{{ detailTarget.fee_evidence_name || '下载收款凭证' }}</a><span v-else>未关联</span></dd>
          </template>
          <dt>已核销</dt><dd>{{ detailTarget.currency }} {{ formatMoney(appliedAmount(detailTarget)) }}</dd>
          <dt>未分配余额</dt><dd>{{ detailTarget.currency }} {{ formatMoney(unallocatedAmount(detailTarget)) }}</dd>
          <template v-if="['customer_receipt', 'unallocated_advance'].includes(detailTarget.kind) && detailTarget.direction === 'income'"><dt>尚未结汇及退款的现金</dt><dd>{{ detailTarget.currency }} {{ formatMoney(detailTarget.refundable_cash_amount) }}</dd></template>
          <dt>备注</dt><dd>{{ detailTarget.notes || '—' }}</dd>
        </dl>
        <section v-if="detailTarget.allocations?.length" class="txn-detail-section">
          <h4>核销分配</h4>
          <table><thead><tr><th>订单 / 采购单</th><th>本次核销</th><th>该计划还差</th><th>状态</th></tr></thead>
            <tbody><tr v-for="item in detailTarget.allocations" :key="item.id"><td><RouterLink v-if="allocationLocation(item)" class="contract-link" :to="allocationLocation(item)">{{ item.contract_no }}</RouterLink><span v-else>{{ item.contract_no }}</span></td><td>{{ detailTarget.currency }} {{ formatMoney(item.amount) }}</td><td>{{ detailTarget.currency }} {{ formatMoney(item.remaining_amount) }}</td><td>{{ item.is_active ? '已核销' : '已撤回' }}</td></tr></tbody>
          </table>
        </section>
        <section v-if="detailTarget.receipt_adjustment_rows?.length" class="txn-detail-section"><h4>扣减明细</h4><ul class="detail-list"><li v-for="item in detailTarget.receipt_adjustment_rows" :key="item.id"><strong>{{ adjustmentNatureLabel(item.nature) }} · {{ item.currency }} {{ formatMoney(item.amount) }}</strong><small>{{ adjustmentHandlingLabel(item.handling) }}<template v-if="item.contract_no"> · {{ item.contract_no }}</template> · {{ item.reason }}</small><a v-if="item.evidence" :href="`/api/transactions/${detailTarget.id}/adjustment-voucher-download/?id=${item.id}`">{{ item.evidence_name || '查看依据凭证' }}</a><small v-else>未关联凭证</small></li></ul></section>
        <section v-if="detailTarget.writeoffs?.length" class="txn-detail-section">
          <h4>授权抹零（不计现金）</h4>
          <table><thead><tr><th>订单</th><th>抹零 / 更正</th><th>原因与审核轨迹</th><th>操作</th></tr></thead>
            <tbody><tr v-for="item in detailTarget.writeoffs" :key="item.id"><td>{{ item.contract_no }}</td><td>{{ detailTarget.currency }} {{ formatMoney(item.amount) }}<small>已更正 {{ formatMoney(item.corrected_amount) }} · 有效 {{ formatMoney(Number(item.amount) - Number(item.corrected_amount || 0)) }}</small></td><td>{{ item.reason }}<small>{{ item.confirmed_actor_name || confirmerDisplay(item.confirmed_actor) }} · {{ readableTime(item.created_at) }}</small><small v-for="entry in item.corrections" :key="entry.id">更正 {{ formatMoney(entry.amount) }}：{{ entry.reason }} · {{ entry.actor_name || confirmerDisplay(entry.actor) }} · {{ readableTime(entry.created_at) }}</small></td><td><button v-if="can('transactions', 'update') && Number(item.amount) > Number(item.corrected_amount || 0)" type="button" @click="openCorrection(detailTarget, item)">更正抹零</button></td></tr></tbody>
          </table>
        </section>
        <section v-if="detailTarget.cash_settlements?.length" class="txn-detail-section">
          <h4>结汇到账</h4>
          <table><thead><tr><th>银行日期 / 事件</th><th>兑换原币</th><th>汇率</th><th>扣费前兑换额</th><th>手续费</th><th>人民币净到账</th></tr></thead>
            <tbody><tr v-for="item in detailTarget.cash_settlements" :key="item.id"><td>{{ item.bank_date }}<small>{{ item.event_no }} · {{ item.status === 'confirmed' ? '已确认' : item.status === 'pending' ? '待确认' : '已放弃' }}</small></td><td>{{ item.currency }} {{ formatMoney(item.amount) }}</td><td>{{ item.actual_rate || '未录入' }}</td><td>¥{{ formatMoney(item.gross_rmb_amount) }}</td><td>¥{{ formatMoney(item.fee_amount) }}</td><td>¥{{ formatMoney(item.bank_net_amount) }}<small v-if="item.quoted_reference_delta != null">{{ item.source_count > 1 ? '整笔结汇：' : '' }}扣费前与参考汇率差额 ¥{{ formatMoney(item.quoted_reference_delta) }}</small><small v-else-if="item.pre_fee_reference_delta != null">{{ item.source_count > 1 ? '整笔结汇：' : '' }}扣费前与来源折算参考差额 ¥{{ formatMoney(item.pre_fee_reference_delta) }}</small><small v-else>参考汇率未录入，差额待核实</small></td></tr></tbody>
          </table>
        </section>
        <section v-if="detailTarget.receipt_refunds?.length" class="txn-detail-section"><h4>已登记退款</h4><p v-for="item in detailTarget.receipt_refunds" :key="item.id">{{ item.date }} · {{ item.currency }} {{ formatMoney(item.amount) }} · {{ item.reason }} · <a :href="`/api/transactions/${detailTarget.id}/refund-voucher-download/?id=${item.id}`">{{ item.voucher_name }}</a></p></section>
        <footer><button type="button" class="secondary" @click="detailTarget = null">关闭</button><button v-if="can('transactions', 'update') && ['customer_receipt', 'unallocated_advance'].includes(detailTarget.kind) && detailTarget.status === 'confirmed' && detailTarget.direction === 'income'" type="button" @click="openRefund(detailTarget)">从本笔登记退款</button><button v-if="can('transactions', 'update') && writeoffPlans.length && detailTarget.status === 'confirmed' && detailTarget.direction === 'income'" type="button" @click="openWriteoff(detailTarget)">登记授权抹零</button><button v-if="can('transactions', 'create') && detailTarget.status === 'confirmed' && detailTarget.direction === 'income' && detailTarget.currency !== 'CNY'" type="button" @click="openSettlement(detailTarget)">登记结汇到账</button></footer>
      </section>
    </div>

    <div v-if="refundTarget" class="mask">
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="receipt-refund-title" @submit.prevent="submitRefund">
        <header class="dialog-head"><div><h3 id="receipt-refund-title">登记退款</h3><p>原收款 {{ refundTarget.transaction_no }} · 尚未结汇及退款 {{ refundTarget.currency }} {{ formatMoney(refundTarget.refundable_cash_amount) }}</p></div><button type="button" class="close" aria-label="关闭退款" :disabled="refundSaving" @click="closeRefund">×</button></header>
        <p v-if="refundAttempt" class="error" role="alert">上次结果待确认，请按原内容重试。</p>
        <fieldset :disabled="refundSaving || !!refundAttempt"><label>实际退款日期<input v-model="refundForm.actual_date" type="date" required></label><label>退款对应订单<select v-model="refundForm.order"><option v-if="Number(refundTarget.unallocated_amount) > 0" value="">未分配预收款</option><option v-else disabled value="">请选择原订单</option><option v-for="order in refundOrders" :key="order.id" :value="order.id">{{ order.label }}</option></select></label><label>实际退款金额（{{ refundTarget.currency }}）<input v-model="refundForm.amount" type="number" min="0.0001" step="0.0001" required></label><label>退款依据<textarea v-model="refundForm.reason" minlength="5" maxlength="500" rows="3" required></textarea></label><label>实际退款凭证<input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="refundFile = $event.target.files[0]"></label><button type="button" :disabled="refundUploading || !refundFile" @click="uploadRefundProof">{{ refundUploading ? '上传中…' : '上传凭证' }}</button><p v-if="refundForm.voucher">凭证已上传：{{ refundForm.voucherName }}</p></fieldset>
        <p>已结汇金额及非现金扣减不能作为本次可退原币现金；有效订单退款会恢复对应应收，已取消订单的应收保持为零。</p><p v-if="error" class="error" role="alert">{{ error }}</p><footer><button type="button" class="secondary" :disabled="refundSaving" @click="closeRefund">关闭</button><button :disabled="refundSaving || !refundForm.voucher">{{ refundSaving ? '登记中…' : refundAttempt ? '按原内容重试' : '确认登记' }}</button></footer>
      </form>
    </div>

    <div v-if="settlementTarget" class="mask">
      <section class="dialog settlement-dialog" role="dialog" aria-modal="true" aria-labelledby="detail-settlement-title">
        <header class="dialog-head"><div><h3 id="detail-settlement-title">结汇到账</h3><p>{{ settlementTarget.transaction_no }} · {{ settlementTarget.currency }} {{ formatMoney(settlementTarget.amount) }} 实收</p></div><button type="button" class="close" aria-label="关闭结汇登记" @click="closeSettlement">×</button></header>
        <CashEventEntryForm mode="linked" :receipt="settlementTarget" @state-change="onDetailSettlementStateChange" @created="onDetailSettlementCreated" @updated="onDetailSettlementUpdated" />
        <footer><button type="button" class="secondary" :disabled="detailSettlementSnapshot?.busy" @click="closeSettlement">关闭</button></footer>
      </section>
    </div>

    <div v-if="writeoffTarget && can('transactions', 'update')" class="mask">
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="writeoff-title" @submit.prevent="submitWriteoff">
        <header class="dialog-head"><div><h3 id="writeoff-title">登记授权抹零</h3><p>减少未结应收，不新增现金收款。</p></div><button type="button" class="close" aria-label="关闭抹零登记" :disabled="writeoffSaving" @click="closeWriteoff">×</button></header>
        <p class="dialog-context">原收款 {{ writeoffTarget.transaction_no }} · 实收 {{ writeoffTarget.currency }} {{ formatMoney(writeoffTarget.amount) }}</p>
        <label>关联订单计划<select v-model="writeoffPlan" required @change="selectWriteoffPlan"><option value="">请选择</option><option v-for="item in writeoffPlans" :key="item.plan" :value="item.plan">{{ item.contract_no }} · 尚欠 {{ formatMoney(item.remaining_amount) }} {{ writeoffTarget.currency }}</option></select></label>
        <label>抹零金额（{{ writeoffTarget.currency }}）<input v-model="writeoffAmount" type="number" min="0.0001" step="0.0001" required></label>
        <label>授权原因<textarea v-model="writeoffReason" minlength="5" maxlength="500" rows="3" placeholder="记录客户确认抹零的原因" required /></label>
        <p class="field-hint">订单降价或质量赔偿请使用正式订单修订及对应依据。</p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <footer><button type="button" class="secondary" :disabled="writeoffSaving" @click="closeWriteoff">取消</button><button :disabled="writeoffSaving || !writeoffPlan || !writeoffReason.trim()">{{ writeoffSaving ? '保存中…' : '确认并登记' }}</button></footer>
      </form>
    </div>

    <div v-if="correctionTarget && can('transactions', 'update')" class="mask">
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="writeoff-correction-title" @submit.prevent="submitCorrection">
        <header class="dialog-head"><div><h3 id="writeoff-correction-title">更正授权抹零</h3><p>原记录会保留，并追加原因、操作身份和审核留痕。</p></div><button type="button" class="close" aria-label="关闭抹零更正" :disabled="correctionSaving" @click="closeCorrection">×</button></header>
        <p class="dialog-context">原收款 {{ correctionTarget.source.transaction_no }} · 抹零 {{ formatMoney(correctionTarget.writeoff.amount) }} · 尚可更正 {{ formatMoney(Number(correctionTarget.writeoff.amount) - Number(correctionTarget.writeoff.corrected_amount || 0)) }}</p>
        <label>更正金额（{{ correctionTarget.source.currency }}）<input v-model="correctionAmount" type="number" min="0.0001" :max="Number(correctionTarget.writeoff.amount) - Number(correctionTarget.writeoff.corrected_amount || 0)" step="0.0001" required /></label>
        <label>更正原因<textarea v-model="correctionReason" minlength="5" maxlength="500" rows="3" required placeholder="说明原抹零记录需要调整的原因" /></label>
        <p class="field-hint">更正恢复应收余额，不新增现金收付款；网络结果不明时沿用同一请求编号重试。</p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <footer><button type="button" class="secondary" :disabled="correctionSaving" @click="closeCorrection">取消</button><button :disabled="correctionSaving || !correctionReason.trim()">{{ correctionSaving ? '保存中…' : '追加更正' }}</button></footer>
      </form>
    </div>

    <div v-if="showForm && can('transactions', 'create')" class="mask">
      <form class="dialog" :class="{ 'receipt-dialog': form.kind === 'customer_receipt' }" role="dialog" aria-modal="true" aria-labelledby="transaction-form-title" @submit.prevent="save">
        <header class="dialog-head"><div><h3 id="transaction-form-title">新增记账</h3><p>保存后只更新系统流水及可核销计划，不代表银行资金已到账。</p></div><button type="button" class="close" aria-label="关闭" @click="closeForm" :disabled="saving">×</button></header>
        <div v-if="saveOutcome === 'unknown'" class="error" role="alert"><strong>记账结果尚未确认</strong><p>请按原内容重试；系统会核对原操作，避免重复登记。</p></div>
        <fieldset :disabled="saving || !!savedReceipt || saveOutcome === 'unknown'"><legend>流水信息（业务记账）</legend>
        <label>类型
          <select v-model="form.kind" required @change="syncKind">
            <optgroup v-for="group in kindGroups" :key="group.direction" :label="group.label"><option v-for="option in group.options" :key="option.value" :value="option.value">{{ option.displayLabel || option.label }}</option></optgroup>
          </select>
          <small class="field-hint">已按收入 / 支出分组；选择类型后会自动确定收支方向。</small>
        </label>
        <label>流水发生日期<input v-model="form.transaction_date" type="date" required></label>
        <p v-if="form.kind !== 'order_expense'" class="category-hint">分类由所选类型自动生成：{{ form.category }}。</p>
        <p v-else class="category-hint">订单费用可选择费用类别，并关联对应订单。</p>
        <label v-if="form.kind === 'order_expense'">费用类别<select v-model="form.category" required><option v-for="category in orderExpenseCategories" :key="category" :value="category">{{ category }}</option></select></label>
        <label>{{ ['customer_receipt', 'unallocated_advance'].includes(form.kind) && form.direction === 'income' ? '银行实际到账原币金额' : '原币金额' }}<input v-model="form.amount" v-money-input type="number" min="0.0001" step="any" required></label>
        <label>币种<select :value="form.currency" required @change="requestCurrencyChange"><option v-for="currency in currencies" :key="currency.value" :value="currency.value">{{ currency.label }}</option></select></label>
        <label>参考折算汇率 <small>1 原币对应人民币；客户收款可暂不填写</small><input v-model="form.exchange_rate" type="number" min="0.000001" step="0.000001" :required="form.kind !== 'customer_receipt'"></label>
        </fieldset>
        <fieldset :disabled="saving || !!savedReceipt || saveOutcome === 'unknown'"><legend>往来方与业务</legend><label v-if="form.kind === 'customer_receipt'">客户<select :value="form.customer || ''" required @change="requestCustomerChange"><option value="">请选择客户</option><option v-for="row in customers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        <div v-if="contractKinds.includes(form.kind)" class="order-picker">
          <label>关联订单（客户收款可暂不选择）<input v-model="orderQuery" placeholder="客户或订单号" @input="searchOrders"></label><small v-if="orderSearchLoading">正在加载订单…</small><p v-if="orderSearchError" class="option-load-error-text" role="alert">{{ orderSearchError }} <button type="button" @click="searchOrders">重试</button></p>
          <button v-for="row in orders" :key="row.id" type="button" class="order" @click="chooseOrder(row)">{{ row.customer_name }}｜{{ row.customer_country || '—' }}｜{{ row.order_no }}｜{{ row.currency }} {{ formatMoney(row.total_amount) }}</button>
          <p v-if="form.order">已选择订单：{{ selectedOrder?.order_no }}</p>
        </div>
        <label v-if="['supplier_payment', 'supplier_refund'].includes(form.kind)">采购单<select v-model="form.purchase_order" required @change="choosePurchase"><option :value="null">请选择采购单</option><option v-for="row in purchases.filter(row => !['draft', 'cancelled'].includes(row.status))" :key="row.id" :value="row.id">{{ row.purchase_no }} · {{ row.supplier_name }} · {{ row.currency }}</option></select></label>
        <label v-if="form.kind === 'unallocated_advance'">客户<select v-model="form.customer" required><option :value="null">请选择客户</option><option v-for="row in customers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        <label v-if="form.kind === 'unallocated_payment'">供应商<select v-model="form.supplier" required><option :value="null">请选择供应商</option><option v-for="row in suppliers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        </fieldset>
        <div v-if="pendingReceiptChange" class="change-confirm" role="alert"><p>{{ pendingReceiptChange.message }}</p><button type="button" @click="confirmReceiptChange">确认变更并清空相关输入</button><button type="button" @click="pendingReceiptChange = null">取消</button></div>
        <fieldset v-if="!savedReceipt && form.kind === 'customer_receipt'" class="receipt-adjustments" :disabled="saving || !!savedReceipt || saveOutcome === 'unknown'"><legend>收款扣减与核销</legend>
          <label>客户实际汇款金额（{{ form.currency }}）<input v-model="form.remittance_amount" v-money-input type="number" min="0" step="any" placeholder="留空时按到账与差额明细计算"></label>
          <p class="field-hint">留空时按银行实到与银行扣费、待核实差额计算客户汇款；优惠另计，不增加现金或结汇额度。</p>
          <div v-for="(line, index) in receiptAdjustments" :key="index" class="adjustment-card">
            <header><strong>扣减明细 {{ index + 1 }}</strong><button type="button" class="secondary" @click="receiptAdjustments.splice(index, 1)">移除</button></header>
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
            <button v-if="!multiOrderMode" type="button" class="secondary" @click="multiOrderMode = true; receiptAllocations.push({ plan: '', amount: '' })">分配到多张订单</button>
            <div v-for="(item, index) in receiptAllocations" :key="index" class="adjustment-grid receipt-allocation-row">
              <label>订单应收计划<select v-model="item.plan" required><option value="">请选择</option><option v-for="plan in eligibleReceiptPlans" :key="plan.id" :value="plan.id">{{ plan.contract_no }} · {{ plan.currency }} · 剩余 {{ formatMoney(plan.remaining_amount) }}</option></select></label>
              <label>本次核销金额（{{ form.currency }}）<input v-model="item.amount" v-money-input type="number" min="0.0001" step="any" required></label>
              <button type="button" class="secondary" @click="receiptAllocations.splice(index, 1); if (!receiptAllocations.length) multiOrderMode = false">移除计划</button>
            </div>
            <button v-if="multiOrderMode" type="button" class="secondary" @click="multiOrderMode = true; receiptAllocations.push({ plan: '', amount: '' })">添加订单计划</button>
          </div>
        </fieldset>
        <fieldset v-if="form.kind === 'unallocated_advance' && form.direction === 'income'" :disabled="saving || !!savedReceipt || saveOutcome === 'unknown'"><legend>客户汇款与银行扣费</legend>
          <label>客户汇款金额（{{ form.currency }}）<input v-model="form.remittance_amount" type="number" min="0.0001" step="0.0001" placeholder="与实际到账相同则无需修改"></label>
          <p class="category-hint">客户汇款 {{ form.currency }} {{ formatMoney(form.remittance_amount || form.amount) }} · 银行扣费 {{ form.currency }} {{ formatMoney(receiptFee) }} · 实际到账 {{ form.currency }} {{ formatMoney(form.amount) }}</p>
          <template v-if="receiptFee > 0">
            <label>扣费承担方<select v-model="form.fee_responsibility" required><option value="">请选择</option><option value="company">我方承担（凭证齐全后按客户汇款额核销）</option><option value="customer">客户承担（保留未收差额）</option><option value="unknown">待查（保留未收差额）</option></select></label>
            <label>扣费原因或核实说明<textarea v-model="form.fee_reason" maxlength="500" rows="2" placeholder="例如：中转行扣费，银行回单注明由我方承担" required /></label>
            <label>收款凭证（PDF、PNG 或 JPEG）<input type="file" accept="application/pdf,image/png,image/jpeg" @change="feeVoucherFile = $event.target.files?.[0] || null"></label>
            <button type="button" :disabled="feeVoucherUploading || !feeVoucherFile" @click="uploadReceiptProof">{{ feeVoucherUploading ? '上传中…' : form.fee_evidence ? '重新上传凭证' : '上传并关联凭证' }}</button>
            <small v-if="form.fee_evidence">收款凭证已上传并关联。</small>
          </template>
        </fieldset>
        <fieldset :disabled="saving || !!savedReceipt || saveOutcome === 'unknown'"><legend>收付款信息</legend>
        <label>支付方式<input v-model="form.payment_method" placeholder="银行转账、现金等"></label><label>银行参考号<input v-model="form.reference"></label><label>备注<input v-model="form.notes"></label>
        </fieldset>
        <p v-if="['customer_receipt', 'supplier_payment'].includes(form.kind)">款项将按合同计划顺序在系统内核销；超出计划的部分转为未分配预收预付，不等于银行资金已确认。</p>
        <div v-if="form.kind === 'customer_receipt' && form.currency === 'CNY'" class="empty-note">本笔收款无需登记外币结汇。</div>
        <button v-if="form.kind === 'customer_receipt' && form.currency !== 'CNY' && !settlementOpen && !savedReceipt" type="button" class="settlement-expand" @click="settlementOpen = true">登记收汇记录</button>
        <section v-if="settlementOpen && form.kind === 'customer_receipt' && form.currency !== 'CNY'" class="settlement-inline-area">
          <p v-if="savedReceipt" class="notice" role="status">收款已保存，流水号 {{ savedReceipt.transaction_no }}。结汇失败时重试只会提交结汇信息。</p>
          <CashEventEntryForm mode="linked" :order="selectedOrder" :receipt="savedReceipt" @state-change="onSettlementStateChange" @created="onSettlementCreated" @updated="onSettlementUpdated" />
        </section>
        <p v-if="form.kind === 'refund'">用于退回已经收到的订单货款；售后赔偿、运费补贴等请登记为订单费用。</p>
        <p v-else-if="form.kind === 'supplier_refund'">用于供应商退回已经支付的采购款。</p>
        <p v-if="error" class="error">{{ error }}</p>
        <footer>
          <button type="button" @click="closeForm" :disabled="saving || receiptLookupLoading || settlementSnapshot?.busy">{{ savedReceipt ? '关闭' : '取消' }}</button>
          <button v-if="!savedReceipt" :disabled="saving || adjustmentUploadBusy || receiptLookupLoading || !referencesLoaded || (form.kind === 'customer_receipt' && (orderSearchLoading || !!orderSearchError))">{{ saving ? '保存中…' : receiptLookupLoading ? '核对中…' : saveOutcome === 'unknown' && form.kind === 'customer_receipt' ? '按原内容重试' : saveOutcome === 'unknown' ? '按原编号重试' : saveOutcome === 'rejected' && settlementOpen ? '按原编号重试保存' : settlementOpen && form.kind === 'customer_receipt' && form.currency !== 'CNY' ? '保存收款并继续' : '保存' }}</button>
        </footer>
      </form>
    </div>
    <div v-if="allocation && can('transactions', 'update')" class="mask"><form class="dialog" role="dialog" aria-modal="true" aria-labelledby="allocation-title" @submit.prevent="allocate"><header class="dialog-head"><div><h3 id="allocation-title">核销预收预付款</h3><p>仅分配现有余额，不会新增现金流水。</p></div><button type="button" class="close" aria-label="关闭" :disabled="saving" @click="closeAllocation">×</button></header><p class="dialog-context">{{ allocation.customer_name || allocation.supplier_name }} · {{ allocation.currency }} 未分配现金 {{ formatMoney(unallocatedAmount(allocation)) }}</p><p v-if="allocationAttempt" class="field-hint" role="status">上次核销结果待确认，请按原内容重试。</p><label>待结计划<select v-model="allocationPlan" :disabled="Boolean(allocationAttempt)" required><option value="">请选择</option><option v-if="allocationAttempt && !eligiblePlans.some(plan => String(plan.id) === String(allocationAttempt.plan))" :value="allocationAttempt.plan">{{ allocationAttempt.planLabel }}（结果待确认）</option><option v-for="plan in eligiblePlans" :key="plan.id" :value="plan.id">{{ plan.contract_no }} · {{ plan.notes || '无备注' }} · 待结 {{ formatMoney(plan.remaining_amount) }}</option></select></label><p v-if="!eligiblePlans.length" class="empty-note">暂无币种与往来方匹配的待结计划。</p><label>核销金额（{{ allocation.currency }}）<input v-model="allocationAmount" type="text" inputmode="decimal" :disabled="Boolean(allocationAttempt)" required></label><p v-if="error" class="error" role="alert">{{ error }}</p><footer><button type="button" class="secondary" :disabled="saving" @click="closeAllocation">取消</button><button :disabled="saving || !allocationPlan">{{ saving ? '保存中…' : allocationAttempt ? '按原内容重试' : '确认核销' }}</button></footer></form></div>
    <div v-if="voidTarget && can('transactions', 'update')" class="mask"><form class="dialog" role="dialog" aria-modal="true" aria-labelledby="void-title" @submit.prevent="submitVoid"><header class="dialog-head"><div><h3 id="void-title">作废财务流水</h3><p>此操作会同步作废拆分流水，并恢复关联收付款计划。</p></div><button type="button" class="close" aria-label="关闭" :disabled="voidSaving" @click="closeVoid">×</button></header><dl class="void-summary"><dt>流水号</dt><dd>{{ voidTarget.transaction_no }}</dd><dt>金额</dt><dd>{{ voidTarget.currency }} {{ formatMoney(voidTarget.amount) }}</dd><dt>往来方 / 合同</dt><dd>{{ voidTarget.customer_name || voidTarget.supplier_name || '—' }} / {{ voidTarget.order_no || voidTarget.purchase_no || '未关联合同' }}</dd></dl><label>作废原因<textarea v-model="voidReason" :readonly="!!voidAttempt" maxlength="500" rows="4" required /></label><p v-if="error" class="error" role="alert">{{ error }}</p><footer><button type="button" class="secondary" :disabled="voidSaving" @click="closeVoid">取消</button><button :disabled="voidSaving || !voidReason.trim()">{{ voidSaving ? '保存中…' : '确认作废' }}</button></footer></form></div>
  </section>
</template>

<style scoped>
.cash-link{display:inline-flex;align-items:center;padding:8px 12px;border:1px solid #cbdcd3;border-radius:8px;color:#0d5c4e;text-decoration:none;background:#fff;font-weight:700;white-space:nowrap}.cash-link:hover{background:#f1f8f4}
.contract-link{color:#08705f;text-decoration:none}.contract-link:hover{text-decoration:underline}
.txn{padding:0}.txn>header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.page-lede{margin:0;color:#718078}.txn p{color:#718078}.txn button{padding:8px 13px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;cursor:pointer}.txn button:hover{border-color:#8db7a7;background:#f5faf7}.txn button:disabled{opacity:.55;cursor:not-allowed}.filters{display:grid;grid-template-columns:minmax(220px,1.5fr) repeat(4,minmax(130px,1fr)) auto;gap:10px;align-items:end;margin:20px 0;padding:16px;border:1px solid #e2e8e4;border-radius:12px;background:#fff}.filters label{display:grid;gap:5px;color:#586b63;font-size:var(--text-caption)}.filters input,.filters select{width:100%;height:39px;padding:0 10px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#253b33}.filters .filter-actions{display:flex;gap:8px}.filters .filter-error{grid-column:1/-1;margin:0}.filters button,.dialog footer button{white-space:nowrap}.filters .secondary,.dialog .secondary{background:#fff;color:#344d44}.notice{margin:12px 0;padding:10px 14px;border:1px solid #b8d8ca;border-radius:9px;background:#eff8f3;color:#1d4d40!important}.txn td small{display:block;color:#718078;font-size:var(--text-caption);margin-top:4px}.txn>table{display:block;overflow:auto;background:#fff;width:100%;border-collapse:collapse;border:1px solid #e2e8e4;border-radius:12px;white-space:nowrap}.txn th,.txn td{padding:12px;text-align:left;border-bottom:1px solid #edf1ee}.txn th{color:#60736b;background:#f6faf8;font-size:var(--text-body)}.mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:60;padding:16px}.dialog{background:#fff;padding:24px;border-radius:14px;width:min(620px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;box-shadow:0 22px 60px #001a1340}.dialog h3{margin:0;font-size:var(--text-dialog)}.dialog-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:16px}.dialog-head p{margin:5px 0 0;font-size:var(--text-caption)}.dialog-head .close{padding:2px 8px;font-size:22px;line-height:1}.dialog label{display:grid;gap:5px;margin:10px 0;color:#3d5149;font-size:var(--text-body)}.dialog input,.dialog select,.dialog textarea{box-sizing:border-box;width:100%;padding:9px;border:1px solid #d8e1dd;border-radius:7px;background:#fff;color:#253b33;font:inherit}.dialog textarea{resize:vertical}.dialog fieldset{min-width:0;margin:0 0 14px;padding:12px 14px;border:1px solid #e2e8e4;border-radius:10px}.dialog legend{padding:0 6px;color:#27584b;font-weight:700}.dialog label>small{font-size:var(--text-caption);color:#71847c;font-weight:400}.void-summary{display:grid;grid-template-columns:110px minmax(0,1fr);gap:8px;margin:0 0 14px;font-size:var(--text-body)}.void-summary dt{color:#718078}.void-summary dd{margin:0;color:#253b33;overflow-wrap:anywhere}.field-hint,.category-hint{display:block;margin:-4px 0 10px;color:#71847c;font-size:var(--text-caption)}.category-hint{padding:8px 10px;border-radius:7px;background:#f3f8f5}.order-picker{margin-top:8px}.order-picker>p{margin:8px 0 0;font-size:var(--text-caption)}.order{display:block;width:100%;margin:5px 0;text-align:left}.dialog footer{display:flex;justify-content:end;gap:8px;margin-top:18px}.dialog footer button:last-child{background:#0d4b40;color:#fff;border-color:#0d4b40}.txn .error{color:#b42318}.empty-note{padding:10px 12px;border-radius:8px;background:#f6f8f6}.txn .summary-cards{margin-top:16px}@media(max-width:1250px){.filters{grid-template-columns:repeat(3,minmax(140px,1fr))}.filters .filter-search{grid-column:span 2}}@media(max-width:620px){.txn>header{align-items:stretch;flex-direction:column}.txn>header>button{width:100%}.filters{grid-template-columns:1fr 1fr}.filters .filter-search{grid-column:1/-1}.filters .filter-actions{grid-column:1/-1}.filters .filter-actions button{flex:1}.txn>table{white-space:nowrap}.dialog{padding:18px}.dialog fieldset{padding:10px}.void-summary{grid-template-columns:80px minmax(0,1fr)}}
.receipt-dialog{width:min(900px,calc(100vw - 32px))}.adjustment-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.adjustment-card{border:1px solid #dce7e0;border-radius:8px;padding:12px;margin:12px 0}.adjustment-card>header,.proof-line{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}.change-confirm{padding:12px;background:#fff5df;border:1px solid #ead5a4;border-radius:8px;margin-bottom:12px}.change-confirm button{margin-right:8px}@media(max-width:620px){.adjustment-grid{grid-template-columns:1fr}.receipt-dialog{padding:18px}}
.detail-list{list-style:none;padding:0;margin:8px 0}.detail-list li{padding:10px 0;border-bottom:1px solid #e4ece7;overflow-wrap:anywhere}.detail-list small{display:block;margin-top:5px;color:#62766c}
.txn-detail{width:min(1080px,calc(100vw - 32px));box-sizing:border-box}.txn-detail-grid{display:grid;grid-template-columns:minmax(110px,auto) minmax(0,1fr) minmax(110px,auto) minmax(0,1fr);gap:10px 14px;padding:16px;border-radius:10px;background:#f5f8f6}.txn-detail-grid dt{color:#62766c}.txn-detail-grid dd{margin:0;min-width:0;overflow-wrap:anywhere}.txn-detail-section{min-width:0;margin-top:20px}.txn-detail-section h4{margin:0 0 10px}.txn-detail-section table{display:block;width:100%;max-width:100%;overflow-x:auto;border-collapse:collapse;white-space:nowrap}.txn-detail-section th,.txn-detail-section td{padding:10px;border-bottom:1px solid #e4ece7;text-align:left;vertical-align:top}.txn-detail-section td small{white-space:normal;min-width:130px}.txn-detail footer{flex-wrap:wrap}.record-number{font-size:12px!important;overflow-wrap:anywhere}.record-number button{font-size:12px;padding:3px 6px}@media(max-width:620px){.txn-detail-grid{grid-template-columns:minmax(88px,auto) minmax(0,1fr)}.txn-detail footer button{flex:1 1 42%}}
</style>
