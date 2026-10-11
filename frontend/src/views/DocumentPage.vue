<script setup>
import { defaultExchangeRate, skuDefaultPrice, currencyHint, salesRateError, changeDocumentCurrency } from '../utils/documentCurrency'
import { compactDecimalInput } from '../utils/decimalInput'
import TradeUnitPicker from '../components/TradeUnitPicker.vue'
import { fromTradeLine, tradePayload, withDefaultTradeUnit, restoreTradeLines } from '../utils/tradeUnits'
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, Search, Pencil, Trash2, FileX2, X, MinusCircle, Download, ChevronDown, ChevronRight, FolderOpen, FileText, FilePenLine, Eye, Clock3, CircleCheck, CircleDollarSign, RotateCcw } from 'lucide-vue-next'
import { api, downloadQuoteExport, listAll } from '../api'
import { confirmDialog } from '../dialogs'
import QuoteDetailModal from '../components/QuoteDetailModal.vue'
import QuoteEditorModal from '../components/QuoteEditorModal.vue'
import OrderDraftModal from '../components/OrderDraftModal.vue'
import SkuPickerPanel from '../components/SkuPickerPanel.vue'
import OrderDetailModal from '../components/OrderDetailModal.vue'
import SegmentedDateInput from '../components/SegmentedDateInput.vue'
import SummaryCards from '../components/SummaryCards.vue'
import SkuContextBanner from '../components/SkuContextBanner.vue'
import { deliveryState } from '../utils/orderOverview.js'
import { addDays, daysBetween } from '../utils/orderDate'
import { clearModalRoute, modalOrigin } from '../utils/modalNavigation'
import { orderDetailLocation, quoteDetailLocation, workbenchCloseLocation } from '../utils/detailNavigation'
import { documentDetailState, withDocumentDetailQuery, withoutDocumentDetailQuery } from '../utils/documentDetailRoute'
import { routeDataQuery, routeDataQuerySignature } from '../utils/routePageState'
import { skuContextLabel, skuContextId, withoutSkuContext } from '../utils/skuContext'

const props = defineProps({ type: String })
const route = useRoute()
const router = useRouter()
const isOrder = computed(() => props.type === 'orders')
const inheritedCustomer = computed(() => isOrder.value && Boolean(route.query.customer))
const copy = computed(() => isOrder.value ? {
  title: '订单管理', description: '管理订单、交付和收款进度。', no: 'order_no', noLabel: '订单号', date: 'order_date', dateLabel: '订单日期', statuses: { draft: '草稿', confirmed: '已确认', production: '生产中', shipped: '已发货', completed: '已完成', cancelled: '已取消' }
} : {
  title: '报价管理', description: '管理报价版本、状态和成交转单。', no: 'quote_no', noLabel: '报价单号', date: 'quote_date', dateLabel: '创建时间', statuses: { draft: '草稿', sent: '已发送', accepted: '已接受', rejected: '已拒绝', expired: '已过期' }
})

const rows = ref([]), customers = ref([]), skus = ref([]), quotes = ref([])
const loading = ref(true), saving = ref(false), open = ref(false), editingId = ref(null), query = ref(typeof route.query.search === 'string' ? route.query.search : '')
const quoteStatusFilter = computed(() => typeof route.query.status === 'string' ? route.query.status : '')
const quoteCustomerFilter = computed(() => typeof route.query.customer === 'string' ? route.query.customer : '')
const quoteSort = computed(() => typeof route.query.ordering === 'string' ? route.query.ordering : '-updated_at')
const orderStatusFilter = computed(() => typeof route.query.status === 'string' ? route.query.status : '')
const orderTodoFilter = computed(() => typeof route.query.todo === 'string' ? route.query.todo : '')
const hasSkuContext = computed(() => isOrder.value && Boolean(skuContextId(route.query.sku)))
const activeSkuContextLabel = computed(() => skuContextLabel(rows.value, route.query.sku))
const quoteDetailId = ref(null), orderDetailId = ref(null)
const returnToOrderDetailId = ref(null)
const orderWorkbenchRefresh = ref(0)
const quoteEditorOpen = ref(false), quoteEditorQuote = ref(null)
const orderDraft = ref(null), workbenchRefresh = ref(0)
const orderLeadTimeDays = ref('')
const expandedQuoteNodes = ref(new Set())
const toast = reactive({ show: false, message: '', error: false })
const form = reactive({})
const activeSkuId = ref('')
const sourceQuoteLoading = ref(false)
let sourceQuoteRequest = 0
let freshOrderDefaults = {}
const eligibleSourceQuotes = computed(() => quotes.value.filter(q => ['draft', 'sent', 'accepted'].includes(q.status)))
const routeActionOpen = ref(false)
let routeActionVersion = 0
let timer

function fresh() {
  sourceQuoteRequest += 1
  sourceQuoteLoading.value = false
  const now = new Date(), y = now.getFullYear(), m = String(now.getMonth() + 1).padStart(2, '0'), d = String(now.getDate()).padStart(2, '0')
  Object.keys(form).forEach(k => delete form[k])
  activeSkuId.value = ''
  Object.assign(form, { customer: '', ...(isOrder.value ? {} : { quote_no: '' }), [copy.value.date]: `${y}-${m}-${d}`, status: 'draft', currency: 'USD', exchange_rate: '7.2', shipping_fee: 0, discount: 0, notes: '', items: [] })
  if (isOrder.value) {
    Object.assign(form, { quote: '', expected_ship_date: '' })
    orderLeadTimeDays.value = ''
    freshOrderDefaults = Object.fromEntries(['order_date', 'expected_ship_date', 'currency', 'exchange_rate'].map(key => [key, form[key]]))
  }
  else form.valid_until = ''
}
function notify(message, error = false) { Object.assign(toast, { show: true, message, error }); setTimeout(() => toast.show = false, 2800) }
async function load() {
  loading.value = true
  try {
    const quoteParams = !isOrder.value ? { status: quoteStatusFilter.value, customer: quoteCustomerFilter.value, ordering: quoteSort.value } : {}
    rows.value = await listAll(`/${props.type}/`, { params: { ...routeDataQuery(route.query), search: route.query.search || '', ...quoteParams } })
    const visibleQuoteIds = new Set(rows.value.map(row => row.id))
    expandedQuoteNodes.value = new Set([...expandedQuoteNodes.value].filter(id => visibleQuoteIds.has(id)))
  } catch (e) { notify(e.message, true) } finally { loading.value = false }
}
let customerOptionsPromise
function loadCustomerOptions() {
  if (!customerOptionsPromise) customerOptionsPromise = listAll('/customers/').then(result => {
    customers.value = result
    return result
  }).catch(error => { customerOptionsPromise = null; throw error })
  return customerOptionsPromise
}
function loadQuoteCustomerOptions() {
  if (!isOrder.value) void loadCustomerOptions().catch(e => notify(e.message, true))
}
async function loadOptions() {
  try {
    const calls = [loadCustomerOptions(), listAll('/skus/')]
    if (isOrder.value) calls.push(listAll('/quotes/'))
    const result = await Promise.all(calls); customers.value = result[0]; skus.value = result[1]; if (result[2]) quotes.value = result[2]
  } catch (e) { notify(e.message, true) }
}
async function create({ isCurrent = () => true } = {}) {
  if (!isOrder.value) {
    await loadOptions()
    if (!isCurrent()) return
    quoteEditorQuote.value = route.query.customer ? { customer: Number(route.query.customer) } : null
    quoteEditorOpen.value = true
    return
  }
  returnToOrderDetailId.value = null
  editingId.value = null; fresh()
  form.customer = route.query.customer ? Number(route.query.customer) : ''
  await loadOptions(); if (isCurrent()) open.value = true
}
async function edit(row, { closeDetail = true, isCurrent = () => true } = {}) {
  if (closeDetail) await closeDocumentDetail()
  if (!isOrder.value) {
    await loadOptions()
    if (!isCurrent()) return
    quoteEditorQuote.value = row
    quoteEditorOpen.value = true
    return
  }
  returnToOrderDetailId.value = closeDetail ? null : row.id
  editingId.value = row.id; fresh(); await loadOptions()
  if (!isCurrent()) return
  Object.keys(form).forEach(k => { if (row[k] !== undefined && k !== 'items') form[k] = row[k] ?? '' })
  form.exchange_rate = compactDecimalInput(form.exchange_rate)
  form.items = row.items.map(i => fromTradeLine({ ...i, cost_price: i.cost_price || 0, notes: i.notes || '' }))
  orderLeadTimeDays.value = daysBetween(form.order_date, form.expected_ship_date)
  open.value = true
}
function setOrderDate(value) {
  form.order_date = value
  if (orderLeadTimeDays.value !== '') form.expected_ship_date = addDays(value, orderLeadTimeDays.value)
  else if (form.expected_ship_date) orderLeadTimeDays.value = daysBetween(value, form.expected_ship_date)
}
function setExpectedShipDate(value) {
  form.expected_ship_date = value
  orderLeadTimeDays.value = daysBetween(form.order_date, value)
}
function setOrderLeadTimeDays() {
  if (orderLeadTimeDays.value === '' || !form.order_date) return
  form.expected_ship_date = addDays(form.order_date, orderLeadTimeDays.value)
}
function closeEditor() { sourceQuoteRequest += 1; sourceQuoteLoading.value = false; open.value = false; returnToOrderDetailId.value = null; void clearModalRoute(router, route) }
function closeQuoteEditor() { quoteEditorOpen.value = false; void clearModalRoute(router, route) }
async function changeCurrency(event) {
  const currency = event.target.value
  event.target.value = form.currency
  await changeDocumentCurrency(form, currency, skus.value, confirmDialog)
  event.target.value = form.currency
}
function selectSku(item) {
  const sku = skus.value.find(s => s.id === Number(item.sku))
  if (sku) { item.unit_price = skuDefaultPrice(sku, form.currency); item.cost_price = sku.cost_price }
}
async function loadSourceQuote(value, { confirmOverwrite = true } = {}) {
  if (sourceQuoteLoading.value || (editingId.value && form.quote)) return
  if (!value) { form.quote = ''; notify('解除来源不会回滚已载入的订单内容。'); return }
  if (!eligibleSourceQuotes.value.some(q => Number(q.id) === Number(value))) return notify('请选择有效的来源报价。', true)
  const changedDefaults = Object.keys(freshOrderDefaults).some(key => key === 'exchange_rate'
    ? compactDecimalInput(form[key]) !== compactDecimalInput(freshOrderDefaults[key])
    : form[key] !== freshOrderDefaults[key])
  const hasContent = form.customer || form.items?.length || Number(form.shipping_fee) || Number(form.discount) || form.notes?.trim() || changedDefaults
  const request = ++sourceQuoteRequest
  sourceQuoteLoading.value = true
  try {
    if (confirmOverwrite && hasContent && !await confirmDialog({ title: '从报价载入', message: '载入报价将覆盖当前订单草稿中的客户、商品、价格、日期、币种、汇率及条款。是否继续？', confirmText: '载入报价' })) return
    if (request !== sourceQuoteRequest) return
    const draft = (await api.get(`/quotes/${value}/order-draft/`)).data
    if (request !== sourceQuoteRequest) return
    Object.assign(form, {
      customer: draft.customer, quote: draft.quote, order_date: draft.order_date,
      currency: draft.currency, exchange_rate: compactDecimalInput(draft.exchange_rate),
      shipping_fee: draft.shipping_fee, discount: draft.discount, notes: draft.notes,
      expected_ship_date: draft.expected_ship_date || '',
      items: draft.items.map(item => fromTradeLine({ ...item })),
    })
    orderLeadTimeDays.value = daysBetween(form.order_date, form.expected_ship_date)
    activeSkuId.value = String(form.items[0]?.sku || '')
  } catch (error) { notify(`无法载入报价：${error.message}`, true) }
  finally { if (request === sourceQuoteRequest) sourceQuoteLoading.value = false }
}
async function changeSourceQuote(event) {
  const value = event.target.value
  event.target.value = form.quote || ''
  await loadSourceQuote(value)
  event.target.value = form.quote || ''
}
const subtotal = computed(() => (form.items || []).reduce((sum, i) => sum + Number(i.quantity || 0) * Number(i.unit_price || 0), 0))
const total = computed(() => subtotal.value + Number(form.shipping_fee || 0) - Number(form.discount || 0))
async function save() {
  if (saving.value || sourceQuoteLoading.value) return
  if (!form.items.length || form.items.some(i => !i.sku)) return notify('请至少添加一条有效的 SKU 明细。', true)
  if (form.items.some(i => Number(i.quantity) <= 0)) return notify('每条 SKU 明细的数量必须大于 0。', true)
  if (salesRateError(form)) return notify(salesRateError(form), true)
  if (form.items.some(item => item.unit_price === '' || item.unit_price == null || Number(item.unit_price) < 0)) return notify('请填写每条 SKU 的本次售价。', true)
  saving.value = true
  const data = { ...form, customer: Number(form.customer), items: form.items.map(i => tradePayload({ ...i, sku: Number(i.sku) })) }
  if (isOrder.value) { delete data.status; delete data.order_no }
  if (isOrder.value) {
    data.quote = form.quote ? Number(form.quote) : null
    data.expected_ship_date = form.expected_ship_date || null
  }
  try {
    const origin = modalOrigin(route)
    const response = editingId.value ? await api.put(`/${props.type}/${editingId.value}/`, data) : await api.post(`/${props.type}/`, data)
    const detailId = returnToOrderDetailId.value || (isOrder.value ? response.data.id : null)
    open.value = false
    notify('单据已保存')
    await clearModalRoute(router, route)
    await load()
    if (detailId && !origin) await router.push(withDocumentDetailQuery(route, detailId))
    if (detailId && returnToOrderDetailId.value) orderWorkbenchRefresh.value += 1
    returnToOrderDetailId.value = null
  } catch (e) { notify(e.message, true) } finally { saving.value = false }
}
async function handleQuoteSaved(row) {
  const origin = modalOrigin(route)
  notify(`报价 ${row.quote_no} 已保存`)
  await clearModalRoute(router, route)
  await load()
  if (quoteDetailId.value) workbenchRefresh.value += 1
  if (!origin) await router.push(withDocumentDetailQuery(route, row.id))
}
async function handleQuoteStatusUpdated() { await load() }
async function exportQuote(row) { try { await downloadQuoteExport(row.id, row.quote_no) } catch (e) { notify(`导出 ${row.quote_no} 失败：${e.message}`, true) } }
async function remove(row) { if (!isOrder.value || !await confirmDialog({ title: '确认删除订单', message: `确定删除 ${row[copy.value.no]} 吗？`, confirmText: '确认删除', danger: true })) return; try { await api.delete(`/${props.type}/${row.id}/`); notify('已删除'); load() } catch (e) { notify(e.message, true) } }
function delayed() {
  clearTimeout(timer)
  timer = setTimeout(() => {
    const nextQuery = { ...route.query }
    if (query.value) nextQuery.search = query.value
    else delete nextQuery.search
    if (routeDataQuerySignature(nextQuery) !== routeDataQuerySignature(route.query)) void router.replace({ path: route.path, query: nextQuery, hash: route.hash })
  }, 300)
}
onBeforeUnmount(() => clearTimeout(timer))
function setOrderFilter(key, value) {
  if (!isOrder.value || !['status', 'todo'].includes(key)) return
  const nextQuery = { ...route.query }
  if (value) nextQuery[key] = value
  else delete nextQuery[key]
  if (JSON.stringify(nextQuery) === JSON.stringify(route.query)) return
  void router.push({ path: route.path, query: nextQuery, hash: route.hash })
}
function resetOrderFilters() {
  query.value = ''
  clearTimeout(timer)
  const nextQuery = { ...route.query }
  delete nextQuery.search
  delete nextQuery.status
  delete nextQuery.todo
  if (routeDataQuerySignature(nextQuery) !== routeDataQuerySignature(route.query)) void router.push({ path: route.path, query: nextQuery, hash: route.hash })
}
function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function documentTimestamp(row) {
  const timestamp = row.updated_at || row.created_at
  if (!timestamp) return row[copy.value.date] || '—'
  return new Date(timestamp).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false })
}
const selectedSkuIds = computed({
  get: () => [...new Set((form.items || []).map(item => String(item.sku || '')).filter(Boolean))],
  set: syncSelectedSkus,
})
function syncSelectedSkus(ids) {
  const selected = [...new Set((ids || []).map(String))]
  const previousLines = [...(form.items || [])]
  const existing = new Map((form.items || []).map(item => [String(item.sku), item]))
  form.items = selected.map(id => existing.get(id) || (() => {
    const item = { sku: Number(id), quantity: 1, unit_price: 0, cost_price: 0, notes: '' }
    selectSku(item)
    return withDefaultTradeUnit(item, skus.value.find(s => s.id === Number(id)))
  })())
  form.items = restoreTradeLines(form.items, previousLines)
  if (!selected.includes(String(activeSkuId.value))) activeSkuId.value = selected[0] || ''
}
function syncDetailFromRoute() {
  const detailState = documentDetailState(props.type, route.query.detail)
  quoteDetailId.value = detailState.quoteDetailId
  orderDetailId.value = detailState.orderDetailId
}
function routeCreatePrefillSignature() {
  const fields = isOrder.value ? ['customer', 'quote'] : ['customer']
  return JSON.stringify(fields.map(field => [field, route.query[field] ?? null]))
}
async function syncModalFromRoute() {
  const version = ++routeActionVersion
  const isCurrent = () => version === routeActionVersion
  if (route.query.create === '1') {
    routeActionOpen.value = true
    await create({ isCurrent })
    if (!isCurrent() || route.query.create !== '1') return
    if (isOrder.value) {
      form.customer = route.query.customer ? Number(route.query.customer) : ''
      if (route.query.quote) await loadSourceQuote(route.query.quote, { confirmOverwrite: false })
    }
    return
  }
  if (route.query.edit) {
    routeActionOpen.value = true
    try {
      const row = (await api.get(`/${props.type}/${route.query.edit}/`)).data
      if (isCurrent() && String(route.query.edit) === String(row.id)) await edit(row, { isCurrent })
    } catch (error) { if (isCurrent()) notify(`无法读取单据：${error.message}`, true) }
    return
  }
  if (routeActionOpen.value) {
    routeActionOpen.value = false
    open.value = false
    quoteEditorOpen.value = false
    orderDraft.value = null
    returnToOrderDetailId.value = null
  }
}
async function closeDocumentDetail() {
  quoteDetailId.value = null
  orderDetailId.value = null
  if (route.query.detail !== undefined) await router.replace(workbenchCloseLocation(route))
}
function openDetail(row) { void router.push(withDocumentDetailQuery(route, row.id)) }
function clearSkuFilter() { void router.push(withoutSkuContext(route)) }
function activateQuoteTreeRow(row) { openDetail(row) }
function toggleQuoteNode(quoteId) {
  const next = new Set(expandedQuoteNodes.value)
  next.has(quoteId) ? next.delete(quoteId) : next.add(quoteId)
  expandedQuoteNodes.value = next
}
const quoteTreeRows = computed(() => {
  const nodes = new Map(rows.value.map(row => [row.id, { ...row, children: [] }]))
  const roots = []
  // Backend ordering is authoritative for roots and siblings. Attach every
  // child before rendering so a globally earlier revision cannot escape its
  // root group.
  rows.value.forEach(row => {
    const node = nodes.get(row.id)
    const parent = node.parent_quote && nodes.get(node.parent_quote)
    if (parent) parent.children.push(node)
    else roots.push(node)
  })
  const output = []
  const visit = (node, depth = 0) => {
    const hasChildren = node.children.length > 0
    output.push({ ...node, depth, hasChildren, isRoot: !node.parent_quote })
    if (hasChildren && expandedQuoteNodes.value.has(node.id)) node.children.forEach(child => visit(child, depth + 1))
  }
  roots.forEach(root => visit(root))
  return output
})
const quoteCustomers = computed(() => [...customers.value].sort((a, b) => a.name.localeCompare(b.name)))
const quoteMetrics = computed(() => ({
  projects: rows.value.filter(row => !row.parent_quote).length,
  versions: rows.value.length,
  pending: rows.value.filter(row => ['draft', 'sent'].includes(row.status)).length,
  accepted: rows.value.filter(row => row.status === 'accepted').length,
}))
const orderMetrics = computed(() => [
  { label: '执行中', value: rows.value.filter(row => ['confirmed', 'production', 'shipped'].includes(row.status)).length, hint: '已确认 / 生产中 / 已发货' },
  { label: '待出库', value: rows.value.filter(row => ['confirmed', 'production'].includes(row.status)).length, hint: '尚未完成发货' },
  { label: '待收款', value: rows.value.filter(row => Number(row.balance_amount || 0) > 0 && !['draft', 'cancelled'].includes(row.status)).length, hint: '仍有应收余额' },
  { label: '已完成', value: rows.value.filter(row => row.status === 'completed').length, hint: '已完成交付' },
])
function setQuoteFilter(key, value) {
  const next = { ...route.query }
  if (value) next[key] = value
  else delete next[key]
  void router.push({ path: route.path, query: next, hash: route.hash })
}
function resetQuoteFilters() {
  clearTimeout(timer)
  query.value = ''
  const { search, status, customer, ordering, ...next } = route.query
  if (routeDataQuerySignature(next) === routeDataQuerySignature(route.query)) {
    return
  }
  void router.push({ path: route.path, query: next, hash: route.hash })
}
function reviseFromDetail(row) { if (row) edit(row, { closeDetail: false }) }
async function openOrderDraft(sourceQuote) {
  await loadOptions()
  try {
    const quoteId = typeof sourceQuote === 'object' ? sourceQuote.id : sourceQuote
    const draft = (await api.get(`/quotes/${quoteId}/order-draft/`)).data
    orderDraft.value = { ...draft, source_quote_no: sourceQuote?.quote_no || draft.source_quote_no }
  }
  catch (error) { notify(`无法创建订单草稿：${error.message}`, true) }
}
async function handleOrderDraftSaved(row) {
  orderDraft.value = null
  notify(`订单 ${row.order_no} 已保存`)
  await load()
  quoteDetailId.value = null
  await router.push(orderDetailLocation(row.id, 'overview', route.fullPath))
}
function openOrderDetail(id) { void router.push(orderDetailLocation(id, 'overview', route.fullPath)) }
function openSourceQuote(id) { void router.push(quoteDetailLocation(id, 'overview', route.fullPath)) }
async function editRelatedOrder() {
  if (!orderDetailId.value) return
  try {
    const row = (await api.get(`/orders/${orderDetailId.value}/`)).data
    await edit(row, { closeDetail: false })
  } catch (error) { notify(`无法读取订单最新数据：${error.message}`, true) }
}
async function handleOrderEdit() {
  if (isOrder.value) await editRelatedOrder()
  else notify('请前往订单管理编辑订单。')
}
watch(() => props.type, () => { load(); loadQuoteCustomerOptions() })
watch(() => route.query.search, () => {
  clearTimeout(timer); query.value = typeof route.query.search === 'string' ? route.query.search : ''
})
watch(() => routeDataQuerySignature(route.query), load)
watch([() => props.type, () => route.query.detail], syncDetailFromRoute, { immediate: true })
watch([() => props.type, () => route.query.create, () => route.query.edit, routeCreatePrefillSignature], (current, previous) => {
  const prefillOnlyChanged = previous && current[0] === previous[0] && current[1] === previous[1] && current[2] === previous[2]
  if (prefillOnlyChanged && route.query.create !== '1') return
  void syncModalFromRoute()
}, { immediate: true })
onMounted(() => { load(); loadQuoteCustomerOptions() })
</script>

<template>
  <div class="core-list-page">
    <div class="page-head list-intro"><p>{{ copy.description }}</p><button class="btn btn-primary" @click="create"><Plus :size="16" /> 新建{{ isOrder ? '订单' : '报价' }}</button></div>
    <SummaryCards v-if="isOrder" :items="orderMetrics" />
    <SkuContextBanner v-if="hasSkuContext" :label="activeSkuContextLabel" @clear="clearSkuFilter" />
    <section v-if="!isOrder" class="quote-metrics" aria-label="报价汇总"><article><span>报价项目</span><strong>{{ quoteMetrics.projects }}</strong><i class="metric-icon mint"><FolderOpen :size="19" /></i><small>报价主单数</small></article><article><span>报价版本</span><strong>{{ quoteMetrics.versions }}</strong><i class="metric-icon blue"><FileText :size="19" /></i><small>含所有修订版</small></article><article><span>进行中</span><strong>{{ quoteMetrics.pending }}</strong><i class="metric-icon amber"><Clock3 :size="19" /></i><small>草稿或已发送</small></article><article><span>已接受</span><strong>{{ quoteMetrics.accepted }}</strong><i class="metric-icon green"><CircleCheck :size="19" /></i><small>客户已接受</small></article></section>
    <div class="toolbar" :class="{ 'quote-toolbar': !isOrder }"><div class="search-box"><Search :size="17" /><input v-model="query" :placeholder="`搜索${copy.noLabel}或客户...`" @input="delayed" /></div><template v-if="isOrder"><select :value="orderStatusFilter" aria-label="按订单状态筛选" @change="setOrderFilter('status', $event.target.value)"><option value="">全部状态</option><option value="draft">草稿</option><option value="confirmed">已确认</option><option value="production">生产中</option><option value="shipped">已发货</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select><select :value="orderTodoFilter" aria-label="按订单待办筛选" @change="setOrderFilter('todo', $event.target.value)"><option value="">全部待办</option><option value="unshipped">待出库</option><option value="due">交期已到</option></select><button type="button" class="filter-reset" @click="resetOrderFilters"><RotateCcw :size="15" /> 重置</button></template><template v-else><select :value="quoteStatusFilter" aria-label="按报价状态筛选" @change="setQuoteFilter('status', $event.target.value)"><option value="">全部状态</option><option value="draft">草稿</option><option value="sent">已发送</option><option value="accepted">已接受</option><option value="rejected">已拒绝</option><option value="expired">已过期</option></select><select :value="quoteCustomerFilter" aria-label="按客户筛选" @change="setQuoteFilter('customer', $event.target.value)"><option value="">全部客户</option><option v-for="customer in quoteCustomers" :key="customer.id" :value="customer.id">{{ customer.name }}</option></select><select :value="quoteSort" aria-label="报价排序" @change="setQuoteFilter('ordering', $event.target.value)"><option value="-updated_at">最近更新时间</option><option value="updated_at">最早更新时间</option><option value="-quote_date">报价日期（新到旧）</option><option value="quote_date">报价日期（旧到新）</option></select><button type="button" class="filter-reset" @click="resetQuoteFilters"><RotateCcw :size="15" /> 重置</button></template></div>
    <div class="panel">
      <div v-if="loading" class="loading"><div class="spinner" /></div>
      <div v-else-if="!rows.length" class="empty"><FileX2 :size="32" /><h3>{{ (query || (isOrder ? orderStatusFilter || orderTodoFilter : quoteStatusFilter || quoteCustomerFilter)) ? `没有匹配的${isOrder ? '订单' : '报价'}` : `暂无${isOrder ? '订单' : '报价'}` }}</h3><p>{{ (query || (isOrder ? orderStatusFilter || orderTodoFilter : quoteStatusFilter || quoteCustomerFilter)) ? '请调整筛选条件。' : `点击“新建${isOrder ? '订单' : '报价'}”开始录入。` }}</p></div>
      <div v-else-if="isOrder" class="table-wrap"><table class="data-table order-list-table"><thead><tr><th>{{ copy.noLabel }}</th><th>客户</th><th>订单日期</th><th>预计交期</th><th>状态</th><th>明细</th><th>订单金额</th><th>已收 / 待收</th><th style="text-align:right">操作</th></tr></thead>
        <tbody><tr v-for="row in rows" :key="row.id" class="clickable-row" tabindex="0" @click="openDetail(row)" @keydown.enter="openDetail(row)"><td class="primary-cell">{{ row[copy.no] }}</td><td>{{ row.customer_name }}</td><td>{{ row.order_date || '—' }}</td><td><span :class="{ muted: !row.expected_ship_date }">{{ row.expected_ship_date || '未设置' }}</span><small v-if="deliveryState(row)" class="delivery-helper" :class="deliveryState(row).kind">{{ deliveryState(row).label }}</small></td><td><span class="status" :class="row.status">{{ row.status_display }}</span></td><td>{{ row.items.length }} 项</td><td class="amount">{{ row.currency }} {{ money(row.total_amount) }}</td><td><template v-if="row.status === 'draft'"><span class="paid">{{ money(row.paid_amount) }}</span> / <span class="owing">尚未生效</span></template><template v-else-if="row.status === 'cancelled'"><span class="paid">{{ money(row.paid_amount) }}</span> / <span class="owing">已取消</span></template><template v-else><span class="paid">{{ money(row.paid_amount) }}</span> / <span class="owing">{{ money(row.balance_amount) }}</span></template></td><td><div class="table-actions"><button v-if="row.status === 'draft'" class="mini-btn" :aria-label="`编辑 ${row[copy.no]}`" @click.stop="edit(row)"><Pencil :size="14" /></button><button v-if="row.status === 'draft'" class="mini-btn" :aria-label="`删除 ${row[copy.no]}`" @click.stop="remove(row)"><Trash2 :size="14" /></button></div></td></tr></tbody>
      </table></div>
      <div v-else class="table-wrap"><table class="data-table quote-table"><thead><tr><th>报价单 / 层级</th><th>客户</th><th>更新时间</th><th>状态</th><th>明细</th><th>金额</th><th style="text-align:right">操作</th></tr></thead>
        <tbody><tr v-for="row in quoteTreeRows" :key="row.id" class="clickable-row quote-tree-row" :class="{ 'quote-root-row': row.isRoot, 'quote-child-row': !row.isRoot }" tabindex="0" @click="activateQuoteTreeRow(row)" @keydown.enter="activateQuoteTreeRow(row)"><td class="primary-cell"><div class="quote-tree-cell" :style="{ '--tree-depth': row.depth }"><span class="tree-indent" /><button v-if="row.hasChildren" class="quote-expand" :aria-label="`${expandedQuoteNodes.has(row.id) ? '收起' : '展开'} ${row.quote_no} 的修订报价`" @click.stop="toggleQuoteNode(row.id)" @keydown.enter.stop><ChevronDown v-if="expandedQuoteNodes.has(row.id)" :size="16" /><ChevronRight v-else :size="16" /></button><span v-else class="quote-expand-placeholder" /><span v-if="!row.isRoot" class="tree-branch" /><component :is="row.isRoot ? FolderOpen : row.depth > 1 ? FilePenLine : FileText" :size="18" class="quote-tree-icon" :class="row.isRoot ? 'root-icon' : 'revision-icon'" /><span class="quote-tree-copy"><strong>{{ row.quote_no }}</strong><small>{{ row.isRoot ? '原始报价' : (row.revision_summary || `基于 ${row.parent_quote_no} 修订`) }}</small></span></div></td><td>{{ row.customer_name }}</td><td>{{ documentTimestamp(row) }}</td><td><span class="status" :class="row.status">{{ row.status_display }}</span></td><td>{{ row.items.length }} 项</td><td class="amount">{{ row.currency }} {{ money(row.total_amount) }}</td><td><div class="table-actions"><button class="mini-btn" :aria-label="`查看 ${row.quote_no}`" @click.stop="openDetail(row)"><Eye :size="14" /></button><button class="mini-btn" :aria-label="`创建修订版 ${row.quote_no}`" @click.stop="edit(row)"><Pencil :size="14" /></button><button class="mini-btn" :aria-label="`导出 ${row.quote_no}`" @click.stop="exportQuote(row)"><Download :size="14" /></button></div></td></tr></tbody>
      </table></div>
    </div>

    <div v-if="open && isOrder" class="modal-backdrop" @mousedown.self="closeEditor"><form class="modal wide" novalidate @submit.prevent="save">
      <div class="modal-head"><div><h3>{{ editingId ? '编辑' : '新建' }}{{ isOrder ? '订单' : '报价' }}</h3><small v-if="editingId">{{ rows.find(row => row.id === editingId)?.order_no }}</small></div><button type="button" class="mini-btn" @click="closeEditor"><X :size="17" /></button></div>
      <div class="modal-body">
        <div class="form-grid">
          <div class="field"><label>{{ copy.noLabel }}</label><input v-if="isOrder" :value="(editingId ? rows.find(row => row.id === editingId)?.order_no : form.order_no) || '保存后由系统自动生成'" class="readonly-input" readonly /><input v-else v-model="form[copy.no]" required /></div>
          <div class="field"><label>客户 *</label><select v-model="form.customer" required :disabled="inheritedCustomer || Boolean(form.quote) || sourceQuoteLoading"><option value="">请选择</option><option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option></select></div>
          <div class="field"><label>{{ copy.dateLabel }} *</label><SegmentedDateInput :model-value="form[copy.date]" required @update:model-value="setOrderDate" /></div>
          <div class="field"><label>预计交期</label><div class="lead-time-input"><input v-model="orderLeadTimeDays" type="number" min="0" step="1" placeholder="天数" aria-label="交期天数" @input="setOrderLeadTimeDays" /><span>天</span><SegmentedDateInput :model-value="form.expected_ship_date" @update:model-value="setExpectedShipDate" /></div></div>
          <div v-if="isOrder" class="field"><label>状态</label><input value="草稿" readonly /><small class="field-hint">保存为草稿，确认后开始履约。</small></div><div v-else class="field"><label>状态 *</label><select v-model="form.status"><option v-for="([key,label]) in Object.entries(copy.statuses)" :key="key" :value="key">{{ label }}</option></select></div>
          <div v-if="isOrder" class="field"><label>从报价载入（可选）</label><input v-if="editingId && form.quote" :value="quotes.find(q => q.id === Number(form.quote))?.quote_no || '—'" readonly /><select v-else :value="form.quote" :disabled="sourceQuoteLoading" aria-label="从报价载入（可选）" @change="changeSourceQuote"><option value="">不关联报价</option><option v-for="q in eligibleSourceQuotes" :key="q.id" :value="q.id">{{ q.quote_no }}</option></select></div>
          <div class="field"><label>币种</label><select :value="form.currency" aria-label="单据币种" @change="changeCurrency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
          <div class="field"><label>对人民币汇率</label><input v-model="form.exchange_rate" :readonly="form.currency === 'CNY'" aria-label="对人民币汇率" type="number" step="0.000001" /></div>
        </div>
        <div class="items-head"><div><strong>产品明细</strong><small>先选择一个或多个 SKU，再填写数量与价格</small></div></div>
        <SkuPickerPanel v-model="selectedSkuIds" v-model:active-id="activeSkuId" :skus="skus" />
        <div class="line-items">
          <div class="line-header"><span>SKU</span><span>数量 *</span><span>单价 *</span><span v-if="isOrder">成本</span><span>小计</span><span></span></div>
          <div v-for="(item,index) in form.items" :key="index" class="line-row" :class="{ order: isOrder }">
            <span class="sku-cell"><b>{{ skus.find(sku => sku.id === Number(item.sku))?.display_name_cn || skus.find(sku => sku.id === Number(item.sku))?.product_name || '—' }}</b><small>SKU: {{ skus.find(sku => sku.id === Number(item.sku))?.sku_code || item.sku || '—' }} · Sales Model: {{ skus.find(sku => sku.id === Number(item.sku))?.sales_model || '—' }}</small><small v-if="currencyHint(skus.find(sku => sku.id === Number(item.sku)), form.currency, item.unit_price)" class="currency-hint">{{ currencyHint(skus.find(sku => sku.id === Number(item.sku)), form.currency, item.unit_price) }}</small><TradeUnitPicker :line="item" :sku="skus.find(sku => sku.id === Number(item.sku))" /><button type="button" class="text-btn" @click="form.items.splice(index + 1, 0, { ...item })">增加规格行</button></span>
            <input v-model="item.quantity" type="number" min="0.01" step="0.01" required />
            <input v-model="item.unit_price" v-money-input type="number" min="0" step="any" required />
            <input v-if="isOrder" v-model="item.cost_price" v-money-input type="number" min="0" step="any" />
            <span class="amount">{{ money(Number(item.quantity)*Number(item.unit_price)) }}</span>
            <button type="button" class="remove-line" @click="form.items.splice(index, 1)"><MinusCircle :size="17" /></button>
          </div>
          <p v-if="!form.items.length" class="quote-items-empty">请先从上方选择至少一个 SKU。</p>
        </div>
        <div class="totals"><label>运费 <input v-model="form.shipping_fee" v-money-input type="number" step="any" /></label><label>折扣 <input v-model="form.discount" v-money-input type="number" step="any" /></label><div><small>商品小计 {{ form.currency }} {{ money(subtotal) }}</small><span>合计</span><strong>{{ form.currency }} {{ money(total) }}</strong></div></div>
        <div class="field notes"><label>条款 / 备注</label><textarea v-model="form.notes" /></div>
      </div>
      <div class="modal-foot"><button type="button" class="btn btn-secondary" @click="closeEditor">取消</button><button class="btn btn-primary" :disabled="saving || sourceQuoteLoading">{{ saving ? '保存中…' : '保存订单' }}</button></div>
    </form></div>
    <QuoteEditorModal v-if="quoteEditorOpen" :quote="quoteEditorQuote" :customers="customers" :skus="skus" :mode="quoteEditorQuote?.id ? 'revise' : 'create'" @close="closeQuoteEditor" @saved="handleQuoteSaved" />
    <OrderDraftModal v-if="orderDraft" :draft="orderDraft" :customers="customers" :skus="skus" @close="orderDraft = null" @saved="handleOrderDraftSaved" />
    <Transition name="detail-drawer" appear>
      <QuoteDetailModal v-if="quoteDetailId" :id="quoteDetailId" :refresh-key="workbenchRefresh" @close="closeDocumentDetail" @revise="reviseFromDetail" @status-updated="handleQuoteStatusUpdated" @create-order="openOrderDraft" @open-order="openOrderDetail" />
    </Transition>
    <Transition name="detail-drawer" appear>
      <OrderDetailModal v-if="orderDetailId" :id="orderDetailId" :refresh-key="orderWorkbenchRefresh" @close="closeDocumentDetail" @edit="handleOrderEdit" @open-quote="openSourceQuote" />
    </Transition>
    <div v-if="toast.show" class="toast" :class="{ error: toast.error }">{{ toast.message }}</div>
  </div>
</template>

<style scoped>
.paid{color:#277258;font-weight:600}.owing{color:#b66d2f;font-weight:600}.quote-table{border-collapse:separate;border-spacing:0 8px;margin-top:-8px}.quote-table thead th{border-bottom:0}.quote-table .quote-group-row td{background:#fff;border-top:1px solid #dfe8e4;border-bottom:1px solid #dfe8e4;box-shadow:0 3px 8px #163f3510}.quote-table .quote-group-row td:first-child{border-left:1px solid #dfe8e4;border-radius:10px 0 0 10px}.quote-table .quote-group-row td:last-child{border-right:1px solid #dfe8e4;border-radius:0 10px 10px 0}.quote-group-row:hover td{background:#f2f8f5}.quote-group-row.is-expanded td{background:#dceee7;border-color:#bdd9cc;box-shadow:0 4px 10px #174d3c15}.quote-group-row.is-expanded td:first-child{box-shadow:inset 4px 0 #23765d,0 4px 10px #174d3c15}.quote-chain-summary{display:grid;gap:3px;align-content:center}.quote-chain-summary strong{font-size:var(--text-body);color:#29483e}.quote-chain-summary small{color:#71847d;font-size:var(--text-caption)}.quote-group-chip{width:max-content;padding:2px 6px;border-radius:10px;background:#e8f3ee;color:#28745e;font-size:var(--text-caption);font-weight:700;letter-spacing:.04em}.quote-version-row td{background:#f8fbf9;border-top:1px solid #e2ece7;border-bottom:1px solid #e2ece7}.quote-version-row td:first-child{position:relative;padding-left:41px;border-left:1px solid #e2ece7;border-radius:8px 0 0 8px}.quote-version-row td:last-child{border-right:1px solid #e2ece7;border-radius:0 8px 8px 0}.quote-version-row:hover td{background:#eef7f2}.quote-chain-summary.child strong{color:#477167}.quote-version-rail{position:absolute;left:15px;top:0;bottom:0;width:17px;display:flex;align-items:center;color:#4d9a83}.quote-version-rail:before{content:'';position:absolute;left:7px;top:-9px;bottom:50%;width:1px;background:#8fc4b2}.quote-version-rail svg{position:relative;z-index:1;background:#f8fbf9}.quote-version-node{display:inline-grid;place-items:center;min-width:25px;height:20px;margin-right:7px;border-radius:5px;background:#e3f2eb;color:#23765d;font-size:var(--text-caption);font-weight:800;vertical-align:1px}.quote-expand{display:inline-grid;width:24px;height:24px;margin:0 5px 0 -4px;padding:0;place-items:center;vertical-align:middle;border:1px solid #d8e6df;border-radius:7px;background:#f7fbf9;color:#397060}.quote-expand:hover{background:#c8e5d8;border-color:#add1bf}.quote-expand-placeholder{display:inline-block;width:24px;margin-right:5px}.items-head{display:flex;justify-content:space-between;align-items:center;margin:26px 0 10px;padding-top:22px;border-top:1px solid #e5eae7}.items-head strong,.items-head small{display:block}.items-head strong{font-size:var(--text-body)}.items-head small{font-size:var(--text-caption);color:#82908b;margin-top:3px}.line-items{border:1px solid #e0e6e2;border-radius:10px;overflow:hidden}.line-header,.line-row{display:grid;grid-template-columns:2fr .6fr .8fr .8fr 34px;gap:8px;align-items:center;padding:8px 10px}.line-header:has(+ .order),.line-row.order{grid-template-columns:2fr .55fr .7fr .7fr .8fr 34px}.line-header{background:#f5f8f6;color:#7a8984;font-size:var(--text-caption);text-transform:uppercase}.line-row{border-top:1px solid #edf0ee}.line-row select,.line-row input{min-width:0;width:100%;border:1px solid #dce3df;border-radius:7px;padding:8px;font-size:var(--text-body)}.line-row .amount{text-align:right}.sku-cell{min-width:0}.sku-cell b,.sku-cell small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sku-cell b{color:#294a41;font-size:var(--text-body)}.sku-cell small{margin-top:3px;color:#81908a;font-size:var(--text-caption)}.remove-line{border:0;background:transparent;color:#b05b5b;display:grid;place-items:center}.remove-line:disabled{opacity:.25}.totals{margin:15px 0 22px;display:flex;justify-content:flex-end;gap:14px;align-items:end}.totals label{font-size:var(--text-body);color:#778680}.totals input{display:block;width:105px;margin-top:5px;border:1px solid #dce3df;border-radius:7px;padding:8px}.totals div{border-left:1px solid #dae2de;padding-left:18px}.totals span,.totals strong{display:block}.totals span{font-size:var(--text-body);color:#788680}.totals strong{font-size:var(--text-dialog);color:#123c36;margin-top:5px}.notes textarea{min-height:65px}@media(max-width:700px){.quote-table{border-spacing:0 5px}.line-items{overflow:auto}.line-header,.line-row,.line-header:has(+ .order),.line-row.order{min-width:700px}.totals{flex-wrap:wrap}}
.lead-time-input{display:flex;align-items:center;gap:6px}.lead-time-input>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.lead-time-input>span{color:#70817b;font-size:var(--text-body)}.lead-time-input :deep(.segmented-date){flex:1 1 auto;min-width:0}
.quote-table{border-collapse:collapse;border-spacing:0;margin:0}.quote-table thead th{border-bottom:1px solid #e3ece8;background:#f7faf8;color:#6c7e77}.quote-tree-row td{height:66px;background:#fff;border-bottom:1px solid #e7eeea}.quote-tree-row:hover td{background:#f3faf6}.quote-root-row td{background:#fcfefd}.quote-root-row:hover td{background:#eef8f3}.quote-tree-cell{--tree-depth:0;display:flex;min-width:340px;align-items:center}.tree-indent{width:calc(var(--tree-depth) * 27px);height:34px;flex:0 0 calc(var(--tree-depth) * 27px);border-left:1px solid transparent}.quote-child-row .tree-indent{border-left-color:#c8e4d8}.quote-expand,.quote-expand-placeholder{width:24px;height:24px;margin:0 7px 0 0;flex:0 0 24px}.quote-expand{display:grid;padding:0;place-items:center;border:1px solid #d4e3dc;border-radius:6px;background:#fff;color:#397060}.quote-expand:hover{background:#dff1e8;border-color:#9fcdb7}.quote-expand-placeholder{display:inline-block}.tree-branch{position:relative;width:15px;height:24px;margin:0 4px 0 -2px;flex:0 0 15px;border-left:1px solid #9acdb9;border-bottom:1px solid #9acdb9;border-radius:0 0 0 6px}.tree-branch:before{content:'';position:absolute;top:11px;left:-1px;width:12px;border-top:1px solid #9acdb9}.quote-tree-icon{margin-right:9px;flex:0 0 auto}.root-icon{color:#087b70}.revision-icon{color:#4f8ac6}.quote-tree-copy{display:grid;gap:3px;min-width:0}.quote-tree-copy strong{color:#173f36;font-size:var(--text-body);font-weight:750}.quote-tree-copy small{overflow:hidden;color:#789088;font-size:var(--text-caption);text-overflow:ellipsis;white-space:nowrap}.quote-child-row .quote-tree-copy strong{font-weight:650}.quote-child-row td:first-child{box-shadow:inset 3px 0 #d4ebdf}.quote-root-row td:first-child{box-shadow:inset 3px 0 #13806f}.quote-table .table-actions{justify-content:flex-end}.quote-table .mini-btn{width:30px;height:30px}.quote-table .amount{font-weight:650;color:#1e5146}
.quote-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:0 0 16px}.quote-metrics article{position:relative;min-height:114px;padding:16px 18px;border:1px solid #e3ebe7;border-radius:12px;background:#fff;box-shadow:0 4px 14px #143f330b}.quote-metrics span,.quote-metrics small{display:block;color:#80908a;font-size:var(--text-caption)}.quote-metrics strong{display:block;margin:12px 42px 7px 0;color:#123f36;font-size:var(--text-page);line-height:1.1}.quote-metrics article:last-child strong{font-size:var(--text-dialog)}.quote-metrics small{font-size:var(--text-caption)}.metric-icon{position:absolute;right:18px;top:28px;width:40px;height:40px;border-radius:50%;display:grid;place-items:center}.metric-icon.mint{background:#ddf4f0;color:#008a80}.metric-icon.amber{background:#fff0de;color:#e28b31}.metric-icon.green{background:#e1f6e8;color:#2da45c}.metric-icon.blue{background:#e7f0ff;color:#4382df}.quote-toolbar{align-items:center;flex-wrap:wrap}.quote-toolbar select,.filter-reset{height:39px;border:1px solid #dce6e1;border-radius:8px;background:#fff;color:#52655e;padding:0 11px;font:inherit;font-size:var(--text-body)}.quote-toolbar select:focus{outline:0;border-color:#8ab8a8;box-shadow:0 0 0 3px #dcebe6}.filter-reset{display:inline-flex;align-items:center;gap:6px;cursor:pointer}.filter-reset:hover{border-color:#a9cbbd;color:#1e6d59;background:#f4faf7}@media(max-width:980px){.quote-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.quote-metrics{grid-template-columns:1fr}.quote-toolbar select,.filter-reset{flex:1}.quote-toolbar .search-box{width:100%}}
.currency-hint{display:block!important;white-space:normal!important;overflow:visible!important;color:#8b602c!important;font-size:var(--text-caption);line-height:1.5;margin-top:5px}
</style>

<style scoped>
.delivery-helper{display:block;width:max-content;margin-top:4px;font-size:12px;color:#71817B}.delivery-helper.today,.delivery-helper.overdue{font-weight:600;border-radius:6px;padding:2px 6px}.delivery-helper.today{color:#A25F22;background:#FFF0DC}.delivery-helper.overdue{color:#A84444;background:#FBE5E5}
.currency-hint{display:block!important;white-space:normal!important;overflow:visible!important;color:#8b602c!important;font-size:var(--text-caption);line-height:1.5;margin-top:5px}
</style>
