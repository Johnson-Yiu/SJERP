<script setup>
import TradeUnitPicker from '../components/TradeUnitPicker.vue'
import { fromTradeLine, tradePayload, baseQuantity, tradeLabel, withDefaultTradeUnit, restoreTradeLines } from '../utils/tradeUnits'
import PurchaseSupplierPicker from '../components/PurchaseSupplierPicker.vue'
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, PackagePlus, Plus, RefreshCw, Save, X } from 'lucide-vue-next'
import { api, listData, listAll } from '../api'
import { confirmDialog, inputDialog } from '../dialogs'
import PurchasePaymentModal from '../components/PurchasePaymentModal.vue'
import PurchaseCostAllocationModal from '../components/PurchaseCostAllocationModal.vue'
import SummaryCards from '../components/SummaryCards.vue'
import SkuContextBanner from '../components/SkuContextBanner.vue'
import SkuPickerPanel from '../components/SkuPickerPanel.vue'
import { clearModalRoute } from '../utils/modalNavigation'
import { orderDetailLocation } from '../utils/detailNavigation'
import { withoutDocumentDetailQuery } from '../utils/documentDetailRoute'
import { skuContextLabel, skuContextId, withoutSkuContext } from '../utils/skuContext'
import PurchaseDetailModal from '../components/PurchaseDetailModal.vue'
import { purchaseArrival } from '../utils/purchaseOverview.js'
import { parseDocumentDetailId, withDocumentDetailQuery } from '../utils/documentDetailRoute'

const rows = ref([]), suppliers = ref([]), orders = ref([]), skus = ref([]), supplierSkuOptions = ref({})
const loading = ref(true), saving = ref(false), error = ref(''), notice = ref(''), openCreate = ref(false), expandedId = ref(null), editingPurchaseId = ref(null)
const route = useRoute()
const router = useRouter()
const searchInput = ref(String(route.query.search || ''))
const searchQuery = computed(() => String(route.query.search || ''))
const pendingFilterQuery = shallowRef(null)
const statusFilter = computed({ get: () => String((pendingFilterQuery.value || route.query).status || ''), set: value => updateFilter('status', value) })
const pendingReceiptOnly = computed({ get: () => (pendingFilterQuery.value || route.query).pending_receipt === '1', set: value => updateFilter('pending_receipt', value ? '1' : '') })
const detailPurchase = ref(null), detailLoading = ref(false), detailError = ref('')
let detailRequest = 0
function updateFilter(key, value) {
  const query = { ...(pendingFilterQuery.value || route.query) }
  if (value) query[key] = value
  else delete query[key]
  pendingFilterQuery.value = query
  return router.push({ path: route.path, query, hash: route.hash }).finally(() => { if (pendingFilterQuery.value === query) pendingFilterQuery.value = null })
}
async function loadDetail() {
  const id = parseDocumentDetailId(route.query.detail)
  const request = ++detailRequest
  expandedId.value = id
  detailError.value = ''
  detailPurchase.value = null
  detailLoading.value = Boolean(id)
  if (!id) return
  try {
    const row = rows.value.find(row => Number(row.id) === id)
    const purchase = row || (await api.get(`/purchase-orders/${id}/`)).data
    if (request === detailRequest) detailPurchase.value = purchase
  } catch (err) {
    if (request === detailRequest) detailError.value = message(err, '采购详情加载失败。')
  } finally { if (request === detailRequest) detailLoading.value = false }
}
function closeDetail() { return router.push(withoutDocumentDetailQuery(route)) }
const hasSkuContext = computed(() => Boolean(skuContextId(route.query.sku)))
const activeSkuContextLabel = computed(() => skuContextLabel(rows.value, route.query.sku))
const hasActiveFilters = computed(() => Boolean(searchQuery.value || statusFilter.value || pendingReceiptOnly.value || hasSkuContext.value))
const routeCreateOpen = ref(false)
let routeCreateSignature = ''
let searchDebounceTimer
let purchaseListRequest = 0
let pageLoadRequest = 0
const today = new Date().toISOString().slice(0, 10)
function newDraft() { return { supplier: '', order: '', order_date: today, expected_arrival_date: '', status: 'draft', currency: 'CNY', exchange_rate: '1', notes: '', items: [] } }
const draft = ref(newDraft())
const costTarget = ref(null), paymentTarget = ref(null)
const draftAmount = computed(() => draft.value.items.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0))
const lineAmount = item => Number(item.quantity || 0) * Number(item.unit_price || 0)
const itemSku = item => skus.value.find(sku => Number(sku.id) === Number(item.sku))
const itemBaseUnit = item => item.trade_snapshot?.base_unit || itemSku(item)?.unit || ''
const currencies = [['CNY', '人民币'], ['USD', '美元'], ['EUR', '欧元'], ['GBP', '英镑'], ['HKD', '港币'], ['JPY', '日元'], ['AUD', '澳元'], ['CAD', '加元'], ['SGD', '新加坡元']]
function onCurrencyChanged() {
  draft.value.exchange_rate = draft.value.currency === 'CNY' ? '1' : ''
  draft.value.items.forEach(item => { item.unit_price = ''; applySupplierSkuPrice(item) })
}
async function paymentSaved() { paymentTarget.value = null; notice.value = '供应商付款已记录为支出流水。'; await load() }
const receiptTarget = ref(null), receiptSaving = ref(false)
const receiptForm = ref({})
const receiptRemaining = computed(() => Number(receiptTarget.value?.item.remaining_quantity || 0) - baseQuantity(receiptForm.value))
const receiptSuccess = ref(null)
const reversalTarget = ref(null), reversalSaving = ref(false), reversalReason = ref('')
function openReceipt(row, item) {
  receiptTarget.value = { row, item }
  receiptSuccess.value = null
  receiptForm.value = { purchase_item: item.id, receipt_date: new Date().toLocaleDateString('en-CA'), quantity: Math.max(0, Number(item.remaining_quantity)), unit_cost: item.unit_price, is_overage: false, overage_reason: '', notes: '', checked: false }
  if (item.trade_unit && Number(item.remaining_quantity) % Number(item.trade_snapshot.factor) === 0) Object.assign(receiptForm.value, { trade_unit: item.trade_unit, trade_snapshot: item.trade_snapshot, quantity: Number(item.remaining_quantity) / Number(item.trade_snapshot.factor), unit_cost: item.trade_unit_price })
  error.value = ''
}
async function submitReceipt() {
  if (receiptSaving.value || !receiptForm.value.checked) return
  receiptSaving.value = true
  try {
    const { checked, ...payload } = receiptForm.value
    Object.assign(payload, tradePayload(payload, 'unit_cost'))
    payload.notes = `已核对型号、数量与外观；仅合格数量入库。${payload.notes}`
    const relatedOrders = receiptTarget.value.row.related_orders || []
    const purchaseId = receiptTarget.value.row.id
    await api.post(`/purchase-orders/${purchaseId}/receive/`, payload)
    receiptTarget.value = null
    notice.value = ''
    receiptSuccess.value = { purchaseId, message: '验货入库已完成，库存、预留及在途数量已同步。', relatedOrders }
    await load()
  } catch (err) { error.value = message(err, '验货入库失败。') } finally { receiptSaving.value = false }
}
function openReceiptReversal(row, item, receipt) {
  reversalTarget.value = { row, item, receipt }
  reversalReason.value = ''
  error.value = ''
}
async function submitReceiptReversal() {
  if (reversalSaving.value || !reversalReason.value.trim()) return
  reversalSaving.value = true
  try {
    await api.post(`/purchase-orders/${reversalTarget.value.row.id}/receipts/${reversalTarget.value.receipt.id}/reverse/`, { reason: reversalReason.value.trim() })
    reversalTarget.value = null
    notice.value = '采购入库已冲销，库存、预留及采购状态已同步。'
    await load()
  } catch (err) { error.value = message(err, '采购入库冲销失败。') } finally { reversalSaving.value = false }
}
const selectedOrder = computed(() => orders.value.find(row => Number(row.id) === Number(draft.value.order)))
const inheritedSupplier = computed(() => Boolean(route.query.supplier))
const inheritedOrder = computed(() => Boolean(route.query.order))
const money = value => Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const purchaseMetrics = computed(() => [
  { label: '执行中', value: rows.value.filter(row => ['ordered', 'partial'].includes(row.status)).length, hint: '当前筛选结果' },
  { label: '待到货', value: rows.value.filter(row => ['ordered', 'partial'].includes(row.status) && (row.items || []).some(item => Number(item.remaining_quantity || 0) > 0)).length, hint: '当前结果中有剩余到货数量' },
  { label: '待付款', value: rows.value.filter(row => !['draft', 'cancelled'].includes(row.status) && Number(row.unpaid_amount || 0) > 0).length, hint: '当前结果中仍有未付余额' },
  { label: '已完成', value: rows.value.filter(row => row.status === 'completed').length, hint: '当前结果中已完成采购' },
])
const message = (err, fallback) => err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join(' ') || err.message || fallback
function purchaseListParams() {
  const params = {}
  if (hasSkuContext.value) params.sku = skuContextId(route.query.sku)
  if (searchQuery.value) params.search = searchQuery.value
  if (statusFilter.value) params.status = statusFilter.value
  if (pendingReceiptOnly.value) params.pending_receipt = '1'
  return params
}
async function loadPurchaseRows() {
  const requestId = ++purchaseListRequest
  const nextRows = await listAll('/purchase-orders/', { params: purchaseListParams() })
  if (requestId !== purchaseListRequest) return
  rows.value = nextRows
  await loadDetail()
}
async function loadReferenceOptions() {
  const [nextSuppliers, nextOrders, nextSkus] = await Promise.all([
    listAll('/suppliers/'), listAll('/orders/'), listAll('/skus/'),
  ])
  suppliers.value = nextSuppliers
  orders.value = nextOrders
  skus.value = nextSkus
}
async function load({ includeReferenceData = false } = {}) {
  const requestId = ++pageLoadRequest
  loading.value = true
  error.value = ''
  try {
    const requests = [loadPurchaseRows()]
    if (includeReferenceData) requests.push(loadReferenceOptions())
    await Promise.all(requests)
  } catch (err) {
    if (requestId === pageLoadRequest) error.value = message(err, '采购数据加载失败。')
  } finally {
    if (requestId === pageLoadRequest) loading.value = false
  }
}
function resetFilters() {
  clearTimeout(searchDebounceTimer)
  searchInput.value = ''
  const query = { ...route.query }
  for (const key of ['search', 'status', 'pending_receipt']) delete query[key]
  void router.push({ path: route.path, query, hash: route.hash })
}
function clearSkuFilter() { void router.push(withoutSkuContext(route)) }
function togglePurchaseDetail(row) { void router.push(withDocumentDetailQuery(route, row.id)) }
function startCreate() {
  editingPurchaseId.value = null
  draft.value = { ...newDraft(), supplier: route.query.supplier || '', order: route.query.order || '' }
  activeSkuId.value = ''
  supplierSkuOptions.value = {}; notice.value = ''; openCreate.value = true
}
async function editDraft(row) {
  editingPurchaseId.value = row.id
  draft.value = {
    purchase_no: row.purchase_no,
    supplier: row.supplier || '',
    order: row.order || '',
    order_date: row.order_date,
    expected_arrival_date: row.expected_arrival_date || '',
    status: 'draft',
    currency: row.currency,
    exchange_rate: row.exchange_rate,
    notes: row.notes || '',
    items: (row.items || []).map(item => fromTradeLine({
      sku: item.sku,
      supplier_sku: item.supplier_sku || '',
      quantity: item.quantity,
      unit_price: item.unit_price,
      trade_unit: item.trade_unit || null,
      trade_snapshot: item.trade_snapshot || {},
      trade_quantity: item.trade_quantity,
      trade_unit_price: item.trade_unit_price,
    })),
  }
  activeSkuId.value = String(draft.value.items[0]?.sku || '')
  supplierSkuOptions.value = {}; notice.value = ''; error.value = ''; openCreate.value = true
  await Promise.all(draft.value.items.map(loadSupplierSkuOptions))
}
function closeCreate() { openCreate.value = false; routeCreateOpen.value = false; routeCreateSignature = ''; void clearModalRoute(router, route) }
const matchingItem = ref(null)
async function matchedSupplier(selection) {
  const item = matchingItem.value
  if (!item) return
  if (Number(draft.value.supplier) !== selection.supplier) {
    draft.value.supplier = selection.supplier
    draft.value.items.forEach(resetSupplierLine)
    await Promise.all(draft.value.items.map(loadSupplierSkuOptions))
  } else await loadSupplierSkuOptions(item)
  item.supplier_sku = selection.supplier_sku
  applySupplierSkuPrice(item)
  matchingItem.value = null
}
function supplierSourceKey(item) { return `${draft.value.supplier || ''}:${item.sku || ''}` }
function supplierSourcesFor(item) { return supplierSkuOptions.value[supplierSourceKey(item)] || [] }
async function loadSupplierSkuOptions(item) {
  const key = supplierSourceKey(item)
  supplierSkuOptions.value[key] = []
  if (!draft.value.supplier || !item.sku) return
  try {
    const options = listData(await api.get('/supplier-skus/', { params: { supplier: draft.value.supplier, sku: item.sku, is_active: '1' } }))
    supplierSkuOptions.value[key] = options
    if (options.length === 1 && !item.supplier_sku) {
      item.supplier_sku = options[0].id
      applySupplierSkuPrice(item)
    }
  } catch (err) { error.value = message(err, '供应商 SKU 来源加载失败。') }
}
function resetSupplierLine(item) { item.supplier_sku = ''; item.unit_price = ''; item.trade_unit = null; item.trade_snapshot = {} }
function onSupplierChanged() { draft.value.items.forEach(item => { resetSupplierLine(item); void loadSupplierSkuOptions(item) }) }
function supplierPriceWarning(item) {
  const source = supplierSourcesFor(item).find(row => Number(row.id) === Number(item.supplier_sku))
  return source && source.currency !== draft.value.currency
    ? `供应商参考价为 ${source.purchase_price} ${source.currency}，当前采购单币种为 ${draft.value.currency}，参考价未自动带入，请填写本次实际采购单价。`
    : ''
}
function applySupplierSkuPrice(item) {
  const source = supplierSourcesFor(item).find(row => Number(row.id) === Number(item.supplier_sku))
  if (!source || source.currency !== draft.value.currency) { item.unit_price = ''; return }
  if (source.purchase_price !== null && source.purchase_price !== undefined) item.unit_price = Number(source.purchase_price) * Number(item.trade_unit ? item.trade_snapshot?.factor || 1 : 1)
}
const activeSkuId = ref('')
const selectedSkuIds = computed({
  get: () => [...new Set((draft.value.items || []).map(item => String(item.sku || '')).filter(Boolean))],
  set: syncSelectedSkus,
})
function syncSelectedSkus(ids) {
  const selected = [...new Set((ids || []).map(String))]
  const previousLines = [...(draft.value.items || [])]
  const existing = new Map((draft.value.items || []).map(item => [String(item.sku), item]))
  draft.value.items = selected.map(id => existing.get(id) || withDefaultTradeUnit({ sku: Number(id), supplier_sku: '', quantity: '', unit_price: '' }, skus.value.find(s => s.id === Number(id)), draft.value.supplier))
  draft.value.items = restoreTradeLines(draft.value.items, previousLines)
  selected.forEach(id => {
    const item = draft.value.items.find(row => String(row.sku) === id)
    if (item && !existing.has(id)) void loadSupplierSkuOptions(item)
  })
  if (!selected.includes(String(activeSkuId.value))) activeSkuId.value = selected[0] || ''
}
async function createPurchase() { if (!draft.value.items.length || draft.value.items.some(item => !item.sku || !Number(item.quantity) || Number(item.quantity) <= 0 || item.unit_price === '')) { error.value = '请至少选择一个 SKU，并填写每个 SKU 的采购数量和单价。'; return } saving.value = true; notice.value = ''; error.value = ''; try { const { status, purchase_no, ...draftPayload } = draft.value; const payload = { ...draftPayload, order: draft.value.order ? Number(draft.value.order) : null, expected_arrival_date: draft.value.expected_arrival_date || null, items: draft.value.items.map(row => tradePayload({ ...row, sku: Number(row.sku), supplier_sku: row.supplier_sku ? Number(row.supplier_sku) : null })) }; const response = editingPurchaseId.value ? await api.put(`/purchase-orders/${editingPurchaseId.value}/`, payload) : await api.post('/purchase-orders/', payload); closeCreate(); notice.value = editingPurchaseId.value ? '采购草稿已更新。确认下单后才会生成应付计划，并开放收货和付款。' : `采购草稿 ${response.data.purchase_no} 已保存。确认下单后才会生成应付计划，并开放收货和付款。`; await load() } catch (err) { error.value = message(err, '采购草稿保存失败。') } finally { saving.value = false } }
async function place(row) { if (!await confirmDialog({ title: '确认采购下单', message: '确认下单后将生成应付计划并进入在途采购。是否继续？', confirmText: '确认下单', danger: true })) return; try { await api.post(`/purchase-orders/${row.id}/place/`); notice.value = '采购单已确认下单。'; await load() } catch (err) { error.value = message(err, '确认下单失败。') } }
async function cancelPurchase(row) { const reason = await inputDialog({ title: '取消采购', message: `请填写取消采购单 ${row.purchase_no} 的原因。`, label: '取消原因', placeholder: '请输入取消原因', required: true, maxLength: 500, confirmText: '确认取消', danger: true }); if (!reason) return; try { await api.post(`/purchase-orders/${row.id}/cancel/`, { reason }); notice.value = '采购单已取消。'; await load() } catch (err) { error.value = message(err, '取消采购失败。') } }
async function deleteDraft(row) { if (!await confirmDialog({ title: '确认删除采购草稿', message: `确定删除草稿 ${row.purchase_no} 吗？`, confirmText: '确认删除', danger: true })) return; try { await api.delete(`/purchase-orders/${row.id}/`); notice.value = '采购草稿已删除。'; if (Number(route.query.detail) === row.id) await closeDetail(); await load() } catch (err) { error.value = message(err, '删除采购草稿失败。') } }
function pay(row) { paymentTarget.value = row }
onMounted(() => load({ includeReferenceData: true }))
watch(searchInput, value => {
  clearTimeout(searchDebounceTimer)
  if (value === searchQuery.value) return
  searchDebounceTimer = setTimeout(() => { void updateFilter('search', value.trim()) }, 300)
})
watch(() => route.query.search, () => {
  clearTimeout(searchDebounceTimer)
  searchInput.value = searchQuery.value
})
watch(() => [route.query.search, route.query.status, route.query.pending_receipt, route.query.sku], () => { void load() })
onBeforeUnmount(() => clearTimeout(searchDebounceTimer))
watch(() => [route.query.create, route.query.order, route.query.supplier], ([create, order, supplier]) => {
  if (create === '1') {
    const signature = JSON.stringify([create, order, supplier])
    if (!routeCreateOpen.value || signature !== routeCreateSignature) {
      routeCreateOpen.value = true
      routeCreateSignature = signature
      startCreate()
    }
    return
  }
  if (routeCreateOpen.value) {
    routeCreateOpen.value = false
    routeCreateSignature = ''
    openCreate.value = false
    editingPurchaseId.value = null
  }
}, { immediate: true })
watch(() => route.query.detail, id => {
  void loadDetail()
})
</script>

<template>
  <div>
    <PurchasePaymentModal v-if="paymentTarget" :purchase="paymentTarget" @close="paymentTarget = null" @saved="paymentSaved" />
    <PurchaseCostAllocationModal v-if="costTarget" :purchase="costTarget" :orders="orders" @close="costTarget = null" @saved="notice = '成本分配已保存，订单预估毛利已更新。'" />
    <div class="page-head"><div><h2>采购管理</h2><p>整单录入采购，再按商品明细分配订单与库存成本。</p></div><div class="page-actions"><button class="btn btn-secondary" :disabled="loading" @click="load({ includeReferenceData: true })"><RefreshCw :size="16" /> 刷新</button><button class="btn btn-primary" @click="startCreate"><Plus :size="16" /> 新建采购单</button></div></div>
    <SummaryCards :items="purchaseMetrics" />
    <SkuContextBanner v-if="hasSkuContext" :label="activeSkuContextLabel" @clear="clearSkuFilter" />
    <div class="purchase-list-toolbar" aria-label="采购单筛选">
      <label class="purchase-search"><span>搜索</span><input v-model="searchInput" type="search" placeholder="搜索采购单号、供应商、来源订单…" aria-label="搜索采购单号、供应商、来源订单" /></label>
      <label class="purchase-status-filter"><span>状态</span><select v-model="statusFilter" aria-label="按状态筛选"><option value="">全部状态</option><option value="draft">草稿</option><option value="ordered">已下单</option><option value="partial">部分到货</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select></label>
      <label class="purchase-pending-filter"><input v-model="pendingReceiptOnly" type="checkbox" /> 仅看待到货</label>
      <button class="btn btn-secondary" type="button" :disabled="!hasActiveFilters && !searchInput" @click="resetFilters">重置</button>
    </div>
    <p v-if="notice && !expandedId" class="notice">{{ notice }}</p><p v-if="error && !expandedId" class="form-error">{{ error }}</p>
    <div v-if="openCreate" class="modal-backdrop purchase-create-backdrop" @mousedown.self="closeCreate">
      <section class="modal wide purchase-create-modal" role="dialog" aria-modal="true" aria-labelledby="purchase-create-title">
        <div class="section-heading modal-head">
          <div><h3 id="purchase-create-title">{{ editingPurchaseId ? '编辑采购草稿' : '新建采购单' }}</h3><p>先确认采购基本信息，再逐条填写商品的规格、供货档案、数量和价格。</p></div>
          <button class="icon-btn" aria-label="关闭" @click="closeCreate"><X :size="17" /></button>
        </div>
        <form @submit.prevent="createPurchase">
          <section class="draft-section">
            <div class="draft-section-heading"><h4>采购基本信息</h4><label class="purchase-identity">采购单号<input :value="draft.purchase_no || '保存后由系统自动生成'" class="readonly-input" readonly /></label></div>
            <div class="form-grid">
              <label>供应商 <span v-if="inheritedSupplier" class="inherited-badge">由订单履约带入</span><select v-model="draft.supplier" aria-label="供应商" required :disabled="inheritedSupplier" @change="onSupplierChanged"><option value="">选择供应商</option><option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">{{ supplier.name }}</option></select><small>当前采购单的全部商品将向同一供应商采购。</small></label>
              <label>来源销售订单（可选）<select v-model="draft.order" aria-label="来源销售订单（可选）" :disabled="inheritedOrder"><option value="">不关联订单</option><option v-for="order in orders.filter(row => row.status !== 'cancelled')" :key="order.id" :value="order.id">{{ order.order_no }} · {{ order.customer_name }}</option></select><small>这里只记录本采购单的主要来源订单；多订单成本归属仍在“成本分配”中处理。</small></label>
              <label>下单日期<input v-model="draft.order_date" type="date" required /></label>
              <label>预计到货<input v-model="draft.expected_arrival_date" type="date" /></label>
              <label>币种<select v-model="draft.currency" required @change="onCurrencyChanged"><option v-for="[code, name] in currencies" :key="code" :value="code">{{ code }} · {{ name }}</option></select></label>
              <label v-if="draft.currency !== 'CNY'">对人民币汇率<input v-model="draft.exchange_rate" type="number" min="0.000001" step="0.000001" placeholder="1 单位外币兑换人民币金额" required /></label>
            </div>
          </section>
          <section class="draft-section line-editor">
            <div class="draft-section-heading"><h4>采购商品</h4><small v-if="selectedOrder">关联：{{ selectedOrder.order_no }}</small></div>
            <p class="section-help">先选择 SKU，再为每条采购明细确认规格、供应商供货档案、数量与价格。</p>
            <SkuPickerPanel v-model="selectedSkuIds" v-model:active-id="activeSkuId" :skus="skus" :show-price="false" />
            <article v-for="(item,index) in draft.items" :key="index" class="purchase-line">
              <header class="purchase-line-heading"><div class="purchase-sku"><b>{{ itemSku(item)?.display_name_cn || itemSku(item)?.product_name || '—' }}</b><small>SKU: {{ itemSku(item)?.sku_code || item.sku || '—' }} · Sales Model: {{ itemSku(item)?.sales_model || '—' }}</small></div><button type="button" class="text-btn danger" @click="draft.items.splice(index, 1)">删除</button></header>
              <div class="line-source-grid">
                <div class="line-field"><span>交易单位 / 包装规格</span><TradeUnitPicker :line="item" :sku="itemSku(item)" :supplier="draft.supplier" /></div>
                <label class="line-field">供应商供货档案<select v-model="item.supplier_sku" :disabled="!draft.supplier || !item.sku" @change="applySupplierSkuPrice(item)"><option v-if="!draft.supplier || !item.sku" value="">供应商供货档案（可选）</option><option v-else-if="!supplierSourcesFor(item).length" value="">暂无供货档案</option><option v-for="source in supplierSourcesFor(item)" :key="source.id" :value="source.id">{{ source.supplier_model || source.supplier_sku_code }} · {{ source.supplier_sku_code }} · {{ source.purchase_price }} {{ source.currency }}</option></select><small v-if="draft.supplier && item.sku && !supplierSourcesFor(item).length">未维护供应商供货档案，本次采购仍可继续。</small></label>
                <button type="button" class="supplier-match-action" @click="matchingItem = item">查找其他供应商</button>
              </div>
              <p v-if="supplierPriceWarning(item)" class="supplier-price-warning">{{ supplierPriceWarning(item) }}</p>
              <div class="line-business-grid">
                <label class="line-field">采购数量<input v-model="item.quantity" type="number" min="0.01" step="0.01" placeholder="采购数量" required /><small v-if="item.trade_unit">折合 {{ baseQuantity(item) }} {{ itemBaseUnit(item) }}</small></label>
                <label class="line-field">采购单价（{{ draft.currency }}）<input v-model="item.unit_price" v-money-input type="number" min="0" step="any" placeholder="采购单价" required /></label>
                <div class="line-field line-total"><span>本行金额</span><strong>{{ draft.currency }} {{ money(lineAmount(item)) }}</strong></div>
              </div>
              <footer class="purchase-line-footer"><button type="button" class="text-btn" title="用于同一 SKU 以不同包装规格采购。" @click="draft.items.splice(index + 1, 0, { ...item })">增加同 SKU 规格行</button><small>用于同一 SKU 以不同包装规格采购。</small></footer>
            </article>
            <p v-if="!draft.items.length" class="purchase-empty">请先从上方选择至少一个 SKU。</p>
          </section>
          <section class="purchase-total-summary"><h4>采购金额汇总</h4><div><span>商品项数 <b>{{ draft.items.length }}</b></span><span>币种 <b>{{ draft.currency }}</b></span><span>商品金额 <strong>{{ draft.currency }} {{ money(draftAmount) }}</strong></span></div></section>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <div class="editor-actions"><small>草稿保存不会生成应付或在途采购；确认下单后才进入正式采购流程。</small><div><button type="button" class="btn btn-secondary" @click="closeCreate">取消</button><button class="btn btn-primary" :disabled="saving"><Save :size="16" /> {{ saving ? '保存中…' : (editingPurchaseId ? '保存采购草稿' : '创建采购单') }}</button></div></div>
        </form>
      </section>
    </div>
    <section class="panel"><div v-if="loading && !rows.length" class="loading"><div class="spinner" /></div><div v-else-if="!rows.length" class="empty"><PackagePlus :size="32" /><h3>{{ hasActiveFilters ? '没有符合筛选条件的采购单' : '暂无采购单' }}</h3><p>{{ hasActiveFilters ? '请调整筛选条件或重置筛选。' : '可独立创建采购草稿，确认下单后再进入收货、付款与成本分配。' }}</p></div><div v-else class="table-wrap"><table class="data-table"><thead><tr><th>采购单号</th><th>供应商</th><th>来源订单</th><th>下单日期</th><th>预计到货</th><th>状态</th><th>采购金额</th><th>已付 / 未付</th><th>操作</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id" class="purchase-list-row" tabindex="0" @click="togglePurchaseDetail(row)" @keydown.enter.self="togglePurchaseDetail(row)"><td class="primary-cell">{{ row.purchase_no }}</td><td>{{ row.supplier_name }}</td><td><RouterLink v-if="row.order && row.order_no" @click.stop class="order-navigation-link" :aria-label="`查看来源订单 ${row.order_no}`" :to="orderDetailLocation(row.order)">{{ row.order_no }}</RouterLink><span v-else>—</span></td><td>{{ row.order_date || '—' }}</td><td><div>{{ row.expected_arrival_date || '—' }}</div><small v-if="purchaseArrival(row)" class="arrival-helper" :class="purchaseArrival(row).kind">{{ purchaseArrival(row).label }}</small></td><td><span class="status" :class="row.status">{{ row.status_display }}</span></td><td>{{ row.currency }} {{ money(row.total_amount) }}</td><td>{{ money(row.paid_amount) }} / {{ money(row.unpaid_amount) }}</td><td><button class="text-btn" @click.stop="togglePurchaseDetail(row)" :aria-label="`查看采购单 ${row.purchase_no}`"><Eye :size="16" /></button></td></tr></tbody></table></div></section>

    <PurchaseDetailModal v-if="expandedId" :key="expandedId" :purchase="detailPurchase" :loading="detailLoading" :error="detailError" :skus="skus" @close="closeDetail" @retry="loadDetail" @confirm="place" @edit="editDraft" @delete="deleteDraft" @cancel="cancelPurchase" @pay="pay" @allocate-cost="costTarget = $event" @receive="openReceipt" @reverse-receipt="openReceiptReversal" @changed="load"><template #feedback><p v-if="notice" class="notice">{{ notice }}</p><p v-if="error" class="form-error">{{ error }}</p><div v-if="receiptSuccess && expandedId === receiptSuccess.purchaseId" class="notice receipt-success" role="status"><span>{{ receiptSuccess.message }}</span><RouterLink v-if="receiptSuccess.relatedOrders.length === 1" class="order-navigation-link" :to="orderDetailLocation(receiptSuccess.relatedOrders[0].id)">查看关联订单 {{ receiptSuccess.relatedOrders[0].order_no }}</RouterLink><div v-else-if="receiptSuccess.relatedOrders.length > 1" class="receipt-success-orders"><span>关联订单：</span><RouterLink v-for="order in receiptSuccess.relatedOrders" :key="order.id" class="order-navigation-link" :to="orderDetailLocation(order.id)">{{ order.order_no }}</RouterLink></div></div></template></PurchaseDetailModal>
    <div v-if="receiptTarget" class="receipt-mask" @click.self="receiptTarget = null">
      <form class="receipt-dialog goods-receipt-dialog" role="dialog" aria-modal="true" aria-labelledby="receipt-title" @submit.prevent="submitReceipt">
        <header><h3 id="receipt-title">验货合格入库</h3><p>{{ receiptTarget.row.purchase_no }} · {{ receiptTarget.item.sku_code }} / {{ receiptTarget.item.display_name || itemSku(receiptTarget.item)?.display_name_cn || '—' }}</p><p>供应商：{{ receiptTarget.row.supplier_name || '—' }}</p></header>
        <div class="receipt-progress"><div><small>下单数量</small><strong>{{ receiptTarget.item.quantity }} {{ itemBaseUnit(receiptTarget.item) }}</strong></div><div><small>已到货</small><strong>{{ receiptTarget.item.received_quantity }} {{ itemBaseUnit(receiptTarget.item) }}</strong></div><div><small>当前待到</small><strong>{{ receiptTarget.item.remaining_quantity }} {{ itemBaseUnit(receiptTarget.item) }}</strong></div></div>
        <p>不合格或拒收数量请写入备注，等待补货后再登记入库。</p>
        <label>实际入库日期<input v-model="receiptForm.receipt_date" type="date" required></label>
        <div class="receipt-unit-field"><span>交易单位 / 包装规格</span><TradeUnitPicker :line="receiptForm" :sku="skus.find(s => s.id === receiptTarget.item.sku)" :supplier="receiptTarget.row.supplier" price-field="unit_cost" preserve-base-quantity :historical-unit="receiptTarget.item.trade_unit" /></div>
        <label>本次合格入库数量<input v-model="receiptForm.quantity" type="number" min="0.01" step="0.01" required></label>
        <div class="receipt-quantity-preview"><span>本次入库：{{ receiptForm.quantity || 0 }} {{ tradeLabel(receiptForm, itemBaseUnit(receiptTarget.item)) }}<template v-if="receiptForm.trade_unit"> = {{ baseQuantity(receiptForm) }} {{ itemBaseUnit(receiptTarget.item) }}</template></span><strong v-if="receiptRemaining >= 0">入库后预计待到：{{ Number(receiptRemaining.toFixed(6)) }} {{ itemBaseUnit(receiptTarget.item) }}</strong><strong v-else>超到：{{ Number((-receiptRemaining).toFixed(6)) }} {{ itemBaseUnit(receiptTarget.item) }}</strong></div>
        <label>实际采购单价（{{ receiptTarget.row.currency }}）<input v-model="receiptForm.unit_cost" type="number" min="0" step="0.0001" required></label>
        <section v-if="baseQuantity(receiptForm) > Number(receiptTarget.item.remaining_quantity)" class="receipt-overage-panel"><h4>本次数量超过当前待到数量</h4><p>待到 {{ receiptTarget.item.remaining_quantity }} · 本次 {{ baseQuantity(receiptForm) }} · 超到 {{ Number((-receiptRemaining).toFixed(6)) }} {{ itemBaseUnit(receiptTarget.item) }}</p><label class="receipt-check"><input v-model="receiptForm.is_overage" type="checkbox" required> 确认超到</label><label>超到原因<select v-model="receiptForm.overage_reason" required><option value="">选择超到原因</option><option value="overprocurement">超采</option><option value="gift">供应商赠品</option><option value="carton_variance">包装尾差</option></select></label></section>
        <label>验货备注 / 异常说明<textarea v-model="receiptForm.notes" placeholder="例如：拒收破损 2 件，已联系供应商补货"></textarea></label>
        <label class="receipt-check inspection-acknowledgement"><input v-model="receiptForm.checked" type="checkbox" required> 已核对型号、数量及外观，仅登记合格品</label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <footer><small>保存后将立即更新：库存、订单预留、采购到货数量、在途数量。</small><div><button type="button" class="btn btn-secondary" @click="receiptTarget = null">取消</button><button class="btn btn-primary" :disabled="receiptSaving || !receiptForm.checked">{{ receiptSaving ? '保存中…' : '确认入库' }}</button></div></footer>
      </form>
    </div>
    <div v-if="reversalTarget" class="receipt-mask" @click.self="reversalTarget = null"><form class="receipt-dialog" @submit.prevent="submitReceiptReversal"><h3>冲销采购入库</h3><p>{{ reversalTarget.row.purchase_no }} · {{ reversalTarget.item.sku_code }} / {{ reversalTarget.item.display_name || '—' }} · 原入库 {{ reversalTarget.receipt.quantity }} {{ itemBaseUnit(reversalTarget.item) }}</p><label>冲销原因<textarea v-model="reversalReason" maxlength="500" required placeholder="请填写冲销原因"></textarea></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="reversalTarget = null">取消</button><button class="receipt-danger" :disabled="reversalSaving || !reversalReason.trim()">{{ reversalSaving ? '提交中…' : '确认冲销' }}</button></footer></form></div>
  </div>
<PurchaseSupplierPicker v-if="matchingItem" :sku="skus.find(s => s.id === Number(matchingItem.sku))" :fixed-supplier="inheritedSupplier ? draft.supplier : null" @close="matchingItem = null" @selected="matchedSupplier" />
</template>

<style scoped>
.purchase-list-toolbar{display:grid;grid-template-columns:minmax(240px,1fr) minmax(150px,210px) auto auto;align-items:end;gap:12px;margin:16px 0 18px;padding:14px;border:1px solid var(--line);border-radius:10px;background:#fff}.purchase-search,.purchase-status-filter{display:grid;gap:6px;color:#536961;font-size:var(--text-caption);font-weight:700}.purchase-search input,.purchase-status-filter select{box-sizing:border-box;width:100%;min-height:38px;border:1px solid #d8e3de;border-radius:8px;padding:7px 9px;background:#fff;color:#263d35;font:inherit}.purchase-pending-filter{display:flex;align-items:center;gap:8px;min-height:38px;color:#39564b;font-size:var(--text-body);white-space:nowrap}.purchase-pending-filter input{width:16px;height:16px;accent-color:#236657}.purchase-list-toolbar>.btn{min-height:38px;white-space:nowrap}@media(max-width:760px){.purchase-list-toolbar{grid-template-columns:minmax(0,1fr) minmax(130px,1fr)}.purchase-search{grid-column:1/-1}.purchase-pending-filter{grid-column:1}.purchase-list-toolbar>.btn{justify-self:end}}
.receipt-mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:100}.receipt-dialog{width:min(540px,90vw);max-height:90vh;overflow:auto;padding:24px;background:white;border-radius:14px}.receipt-dialog label{display:grid;gap:6px;margin:14px 0}.receipt-dialog input:not([type=checkbox]),.receipt-dialog select,.receipt-dialog textarea{padding:9px;border:1px solid #d8e1dd;border-radius:7px}.receipt-dialog footer{display:flex;justify-content:flex-end;gap:10px}.receipt-dialog button{padding:9px 14px}.receipt-dialog p{font-size:var(--text-body);color:#718078}

.page-actions,.editor-actions{display:flex;gap:9px}.notice{margin:0 0 14px;padding:10px 13px;border:1px solid #b9dfce;border-radius:9px;background:#eff9f3;color:#216348}.form-error{margin:0 0 14px;padding:10px 13px;border:1px solid #efcaca;border-radius:9px;background:#fff5f5;color:#a44343}.editor{margin-bottom:18px}.section-heading{display:flex;justify-content:space-between;gap:12px}.section-heading h3,.line-editor h4{margin:0;color:#1d493d}.section-heading p{margin:5px 0 0;color:#74847d;font-size:var(--text-body)}.form-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}.form-grid label{display:grid;gap:6px;color:#536961;font-size:var(--text-body);font-weight:700}.form-grid input,.form-grid select,.purchase-line input,.purchase-line select{min-height:38px;border:1px solid #d8e3de;border-radius:8px;padding:7px 9px;background:#fff;color:#263d35}.form-grid select:disabled{background:#f1f5f3;color:#5d756b;cursor:not-allowed}.line-editor{margin-top:20px;padding-top:16px;border-top:1px solid #e5ece8}.line-editor small{color:#778881;font-weight:400}.purchase-sku{min-width:0}.purchase-sku b,.purchase-sku small{display:block;overflow-wrap:anywhere}.purchase-sku b{color:#294a41;font-size:var(--text-body)}.purchase-sku small{margin-top:3px;color:#81908a;font-size:var(--text-caption)}.purchase-empty{margin:10px 18px;padding:15px;border:1px dashed #cddbd4;border-radius:8px;color:#82918b;text-align:center;font-size:var(--text-body)}.editor-actions{justify-content:flex-end;margin-top:20px}.text-btn{border:0;background:transparent;padding:6px 8px;border-radius:6px;color:#28624e;font:inherit;font-size:var(--text-body);cursor:pointer}.text-btn:hover{background:#e7f1eb}.text-btn:disabled{opacity:.45;cursor:not-allowed}.danger{color:#a74b4b}@media(max-width:760px){.form-grid{grid-template-columns:1fr}.purchase-line{grid-template-columns:1fr}.page-head{align-items:flex-start}.page-actions{flex-wrap:wrap}}
</style>

<style scoped>
.order-navigation-link,.purchase-navigation-link{display:inline-flex;align-items:center;gap:5px;color:#236657;font-weight:700;text-decoration:none}
.order-navigation-link:hover,.purchase-navigation-link:hover{text-decoration:underline}
.related-order-panel{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:12px 18px 0;padding:10px 12px;border:1px solid #e2ebe6;border-radius:8px;background:#fff}
.related-order-panel>strong{color:#405d52;font-size:var(--text-body)}
.related-order-links{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.receipt-success{display:grid;gap:6px}
.receipt-success-orders{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
</style>

<style scoped>
.receipt-mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:100}.receipt-dialog{width:min(540px,90vw);max-height:90vh;overflow:auto;padding:24px;background:white;border-radius:14px}.receipt-dialog label{display:grid;gap:6px;margin:14px 0}.receipt-dialog input:not([type=checkbox]),.receipt-dialog select,.receipt-dialog textarea{padding:9px;border:1px solid #d8e1dd;border-radius:7px}.receipt-dialog footer{display:flex;justify-content:flex-end;gap:10px}.receipt-dialog button{padding:9px 14px}.receipt-dialog p{font-size:var(--text-body);color:#718078}

.purchase-create-backdrop{z-index:70}
.purchase-create-modal{width:min(1100px,calc(100vw - 40px));max-height:94vh;overflow:auto;padding:0}
.purchase-create-modal>form{padding:0 22px 22px}
.purchase-create-modal .form-grid{margin-top:0}
.purchase-create-modal .editor-actions{position:sticky;bottom:-22px;margin:20px -22px -22px;padding:16px 22px;background:#fafbfa;border-top:1px solid var(--line);z-index:2}
@media(max-width:560px){.purchase-create-modal{width:100%;height:100%;max-height:100vh;border-radius:0}.purchase-create-modal>form{padding:0 16px 16px}.purchase-create-modal .editor-actions{bottom:-16px;margin:20px -16px -16px;padding:14px 16px}}
</style>

<style scoped>
.purchase-list-row{cursor:pointer}.purchase-list-row:hover{background:#F8FBF9}.arrival-helper{display:inline-block;margin-top:4px;font-size:12px;color:#71817B}.arrival-helper.today,.arrival-helper.overdue{font-weight:600;border-radius:6px;padding:2px 6px}.arrival-helper.today{color:#A25F22;background:#FFF0DC}.arrival-helper.overdue{color:#A84444;background:#FBE5E5}
</style>

<style scoped>
.purchase-create-modal>form{background:#F6F8F5;padding-top:18px}.draft-section{background:#fff;border:1px solid #E0E8E4;border-radius:13px;padding:18px;margin-bottom:16px}.draft-section-heading{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}.draft-section h4,.purchase-total-summary h4{margin:0;font-size:16px;font-weight:700;color:#1D3F36}.purchase-identity{display:flex;align-items:center;gap:8px;font-size:12px;color:#81908A}.purchase-identity .readonly-input{width:180px;height:28px;min-height:0;border:0;background:transparent;color:#61756D;font-size:12px;padding:0;box-shadow:none}.purchase-create-modal .form-grid{margin-top:18px;gap:14px;align-items:start}.form-grid label,.line-field{font-size:12px;font-weight:600;color:#61756D}.form-grid small,.line-field small,.section-help,.purchase-line-footer small{font-size:12px;font-weight:400;color:#81908A;line-height:1.6}.form-grid input,.form-grid select,.line-field input,.line-field select{box-sizing:border-box;min-width:0;width:100%;height:38px;border:1px solid #D8E3DE;border-radius:8px;padding:0 10px;font:inherit;color:#263D35;background:#fff}.form-grid select:disabled{background:#F1F5F3}.inherited-badge{justify-self:start;border-radius:5px;background:#EFF7F3;padding:2px 6px;color:#3B665A;font-size:11px}.line-editor{margin-top:0;padding-top:18px;border-top:1px solid #E0E8E4}.section-help{margin:8px 0 14px}.purchase-line{display:grid;gap:12px;background:#fff;border:1px solid #E1E9E5;border-radius:10px;padding:15px;margin-top:10px}.purchase-line-heading{display:flex;justify-content:space-between;align-items:start;gap:12px}.purchase-sku b{font-size:14px;font-weight:700;color:#294A41}.purchase-sku small{font-size:12px;color:#81908A}.line-source-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.4fr) auto;gap:12px;align-items:start}.line-business-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;align-items:start}.line-field{display:grid;gap:6px;min-width:0}.line-field :deep(.trade-unit-picker){margin-top:0}.line-field :deep(.trade-unit-picker select){box-sizing:border-box;height:38px;border:1px solid #D8E3DE;border-radius:8px;padding:0 10px}.supplier-match-action{height:30px;margin-top:24px;padding:0 9px;border:1px solid #D3E1DB;border-radius:7px;background:#F8FBF9;color:#3B665A;font-size:12px;font-weight:600;cursor:pointer}.line-total strong{display:flex;align-items:center;min-height:38px;font-size:16px;color:#174C41;font-weight:700;overflow-wrap:anywhere}.purchase-line-footer{display:flex;align-items:center;gap:10px;flex-wrap:wrap;border-top:1px solid #EDF2EF;padding-top:8px}.supplier-price-warning{margin:0;background:#FFF8E8;border:1px solid #EADBB5;border-radius:7px;padding:8px 10px;color:#805C25;font-size:12px;line-height:1.6}.purchase-total-summary{background:#F4F9F6;border:1px solid #D9E8E0;border-radius:10px;padding:14px 16px}.purchase-total-summary>div{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-top:12px;color:#61756D;font-size:12px}.purchase-total-summary b{margin-left:8px;color:#294A41}.purchase-total-summary strong{margin-left:10px;font-size:20px;font-weight:700;color:#174C41}.purchase-create-modal .editor-actions{bottom:0;align-items:center;justify-content:space-between;gap:16px}.editor-actions>small{font-size:12px;color:#71817B;line-height:1.6;max-width:440px}.editor-actions>div{display:flex;gap:9px;flex-shrink:0}.goods-receipt-dialog{width:min(620px,calc(100vw - 32px));box-sizing:border-box}.goods-receipt-dialog h3{margin:0;color:#1D3F36;font-size:20px}.goods-receipt-dialog header p{margin:6px 0;overflow-wrap:anywhere}.receipt-progress{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:18px}.receipt-progress>div{background:#F7FAF8;border:1px solid #E3EBE7;border-radius:8px;padding:10px 12px}.receipt-progress small{display:block;color:#71817B;font-size:11px}.receipt-progress strong{display:block;margin-top:5px;color:#294A41;font-size:15px;font-weight:700;overflow-wrap:anywhere}.goods-receipt-dialog label,.receipt-unit-field{font-size:12px;color:#61756D;font-weight:600}.receipt-unit-field{margin:14px 0}.receipt-quantity-preview{display:grid;gap:5px;background:#EFF7F3;border-radius:7px;padding:8px 10px;color:#315C4E;font-size:12px}.receipt-quantity-preview strong{font-weight:600}.receipt-overage-panel{background:#FFF7E8;border:1px solid #EDD6AA;border-radius:9px;padding:12px;margin:14px 0}.receipt-overage-panel h4{margin:0;color:#875B1D;font-size:13px;font-weight:700}.receipt-overage-panel p{color:#875B1D}.goods-receipt-dialog .receipt-check{display:flex;align-items:center;gap:8px}.inspection-acknowledgement{background:#F5F9F7;border:1px solid #DCE8E2;border-radius:8px;padding:10px 12px}.goods-receipt-dialog .error{background:#FFF5F5;border:1px solid #EFCACA;border-radius:8px;padding:10px;color:#A44343}.goods-receipt-dialog footer{display:grid;gap:12px;padding-top:14px;border-top:1px solid #E0E8E4}.goods-receipt-dialog footer small{font-size:12px;color:#71817B;line-height:1.6}.goods-receipt-dialog footer>div{display:flex;justify-content:flex-end;gap:10px}.goods-receipt-dialog footer button{height:38px;padding:0 14px;border-radius:8px}.receipt-dialog .receipt-danger{background:#FFF7F7;color:#A84444;border:1px solid #E7CACA;border-radius:8px}.receipt-dialog .receipt-danger:disabled{opacity:.5}@media(max-width:760px){.line-source-grid{grid-template-columns:1fr 1fr}.supplier-match-action{margin-top:0;justify-self:start}.line-business-grid{grid-template-columns:1fr 1fr}.line-total{grid-column:1/-1}.purchase-create-modal .editor-actions{align-items:flex-start;flex-wrap:wrap}.editor-actions>div{margin-left:auto}}@media(max-width:560px){.line-source-grid,.line-business-grid{grid-template-columns:1fr}.purchase-total-summary>div{align-items:flex-start;flex-direction:column}.purchase-identity{flex-wrap:wrap}.goods-receipt-dialog{padding:18px}.receipt-progress>div{padding:8px}.receipt-progress strong{font-size:13px}}
</style>
