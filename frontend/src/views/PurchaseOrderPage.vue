<script setup>
import TradeUnitPicker from '../components/TradeUnitPicker.vue'
import { fromTradeLine, tradePayload, baseQuantity, tradeLabel, withDefaultTradeUnit, restoreTradeLines } from '../utils/tradeUnits'
import PurchaseSupplierPicker from '../components/PurchaseSupplierPicker.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleDollarSign, PackagePlus, Plus, RefreshCw, Save, X } from 'lucide-vue-next'
import { api, listData, listAll } from '../api'
import PurchasePaymentModal from '../components/PurchasePaymentModal.vue'
import PurchaseCostAllocationModal from '../components/PurchaseCostAllocationModal.vue'
import SummaryCards from '../components/SummaryCards.vue'
import SkuPickerPanel from '../components/SkuPickerPanel.vue'
import { clearModalRoute } from '../utils/modalNavigation'
import ContractAmountAdjustments from '../components/ContractAmountAdjustments.vue'

const rows = ref([]), suppliers = ref([]), orders = ref([]), skus = ref([]), supplierSkuOptions = ref({})
const loading = ref(true), saving = ref(false), error = ref(''), notice = ref(''), openCreate = ref(false), expandedId = ref(null), editingPurchaseId = ref(null)
const route = useRoute()
const router = useRouter()
const today = new Date().toISOString().slice(0, 10)
function newDraft() { return { supplier: '', order: '', order_date: today, expected_arrival_date: '', status: 'draft', currency: 'CNY', exchange_rate: '1', notes: '', items: [] } }
const draft = ref(newDraft())
const costTarget = ref(null), paymentTarget = ref(null)
const currencies = [['CNY', '人民币'], ['USD', '美元'], ['EUR', '欧元'], ['GBP', '英镑'], ['HKD', '港币'], ['JPY', '日元'], ['AUD', '澳元'], ['CAD', '加元'], ['SGD', '新加坡元']]
function onCurrencyChanged() {
  draft.value.exchange_rate = draft.value.currency === 'CNY' ? '1' : ''
  draft.value.items.forEach(item => { item.unit_price = ''; applySupplierSkuPrice(item) })
}
async function paymentSaved() { paymentTarget.value = null; notice.value = '供应商付款已记录为支出流水。'; await load() }
const receiptTarget = ref(null), receiptSaving = ref(false)
const receiptForm = ref({})
const reversalTarget = ref(null), reversalSaving = ref(false), reversalReason = ref('')
function openReceipt(row, item) {
  receiptTarget.value = { row, item }
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
    await api.post(`/purchase-orders/${receiptTarget.value.row.id}/receive/`, payload)
    receiptTarget.value = null; notice.value = '验货入库已完成，库存、预留及在途数量已同步。'; await load()
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
  { label: '采购单数', value: rows.value.length, hint: '当前采购记录' },
  { label: '待到货', value: rows.value.filter(row => ['ordered', 'partial'].includes(row.status) && (row.items || []).some(item => Number(item.remaining_quantity || 0) > 0)).length, hint: '含未完成到货的采购单' },
  { label: '待付款', value: rows.value.filter(row => !['draft', 'cancelled'].includes(row.status) && Number(row.unpaid_amount || 0) > 0).length, hint: '仍有未付余额的采购单' },
  { label: '关联供应商', value: new Set(rows.value.map(row => row.supplier_name || row.supplier).filter(Boolean)).size, hint: '当前采购单涉及的供应商' },
])
const message = (err, fallback) => err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join(' ') || err.message || fallback
async function load() { loading.value = true; error.value = ''; try { const [a,b,c,d] = await Promise.all([listAll('/purchase-orders/'), listAll('/suppliers/'), listAll('/orders/'), listAll('/skus/')]); rows.value = a; suppliers.value = b; orders.value = c; skus.value = d; if (route.query.detail && rows.value.some(row => Number(row.id) === Number(route.query.detail))) expandedId.value = Number(route.query.detail) } catch (err) { error.value = message(err, '采购数据加载失败。') } finally { loading.value = false } }
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
function closeCreate() { openCreate.value = false; void clearModalRoute(router, route) }
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
async function place(row) { if (!window.confirm('确认下单后将生成应付计划并进入在途采购。是否继续？')) return; try { await api.post(`/purchase-orders/${row.id}/place/`); notice.value = '采购单已确认下单。'; await load() } catch (err) { error.value = message(err, '确认下单失败。') } }
async function cancelPurchase(row) { const reason = window.prompt('请填写取消采购原因：')?.trim(); if (!reason) return; try { await api.post(`/purchase-orders/${row.id}/cancel/`, { reason }); notice.value = '采购单已取消。'; await load() } catch (err) { error.value = message(err, '取消采购失败。') } }
async function deleteDraft(row) { if (!window.confirm(`确定删除草稿 ${row.purchase_no} 吗？`)) return; try { await api.delete(`/purchase-orders/${row.id}/`); notice.value = '采购草稿已删除。'; await load() } catch (err) { error.value = message(err, '删除采购草稿失败。') } }
function pay(row) { paymentTarget.value = row }
onMounted(async () => {
  await load()
  if (route.query.create === '1') startCreate()
})
watch(() => route.query.detail, id => {
  expandedId.value = id ? Number(id) : null
})
</script>

<template>
  <div>
    <PurchasePaymentModal v-if="paymentTarget" :purchase="paymentTarget" @close="paymentTarget = null" @saved="paymentSaved" />
    <PurchaseCostAllocationModal v-if="costTarget" :purchase="costTarget" :orders="orders" @close="costTarget = null" @saved="notice = '成本分配已保存，订单预估毛利已更新。'" />
    <div class="page-head"><div><h2>采购管理</h2><p>整单录入采购，再按商品明细分配订单与库存成本。</p></div><div class="page-actions"><button class="btn btn-secondary" :disabled="loading" @click="load"><RefreshCw :size="16" /> 刷新</button><button class="btn btn-primary" @click="startCreate"><Plus :size="16" /> 新建采购单</button></div></div>
    <SummaryCards :items="purchaseMetrics" />
    <p v-if="notice" class="notice">{{ notice }}</p><p v-if="error" class="form-error">{{ error }}</p>
    <div v-if="openCreate" class="modal-backdrop purchase-create-backdrop" @mousedown.self="closeCreate"><section class="modal wide purchase-create-modal" role="dialog" aria-modal="true" aria-labelledby="purchase-create-title"><div class="section-heading modal-head"><div><h3 id="purchase-create-title">{{ editingPurchaseId ? '编辑采购草稿' : '新建采购单' }}</h3><p>采购数量可参考订单履约中的“待采购”；供应商来源仅作为采购识别与参考价，不改变内部 SKU。</p></div><button class="icon-btn" aria-label="关闭" @click="closeCreate"><X :size="17" /></button></div><form @submit.prevent="createPurchase"><div class="form-grid"><label>采购单号<input :value="draft.purchase_no || '保存后由系统自动生成'" class="readonly-input" readonly /></label><label>供应商<select v-model="draft.supplier" required :disabled="inheritedSupplier" @change="onSupplierChanged"><option value="">选择供应商</option><option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">{{ supplier.name }}</option></select></label><label>来源销售订单（可选）<select v-model="draft.order" :disabled="inheritedOrder"><option value="">不关联订单</option><option v-for="order in orders.filter(row => row.status !== 'cancelled')" :key="order.id" :value="order.id">{{ order.order_no }} · {{ order.customer_name }}</option></select></label><label>下单日期<input v-model="draft.order_date" type="date" required /></label><label>预计到货<input v-model="draft.expected_arrival_date" type="date" /></label><label>币种<select v-model="draft.currency" required @change="onCurrencyChanged"><option v-for="[code, name] in currencies" :key="code" :value="code">{{ code }} · {{ name }}</option></select></label><label v-if="draft.currency !== 'CNY'">对人民币汇率<input v-model="draft.exchange_rate" type="number" min="0.000001" step="0.000001" placeholder="1 单位外币兑换人民币金额" required /></label></div><div class="line-editor"><h4>采购明细 <small v-if="selectedOrder">关联：{{ selectedOrder.order_no }}</small></h4><SkuPickerPanel v-model="selectedSkuIds" v-model:active-id="activeSkuId" :skus="skus" :show-price="false" /><div v-for="(item,index) in draft.items" :key="index" class="purchase-line"><span class="purchase-sku"><b>{{ skus.find(sku => sku.id === Number(item.sku))?.display_name_cn || skus.find(sku => sku.id === Number(item.sku))?.product_name || '—' }}</b><small>SKU: {{ skus.find(sku => sku.id === Number(item.sku))?.sku_code || item.sku || '—' }} · Sales Model: {{ skus.find(sku => sku.id === Number(item.sku))?.sales_model || '—' }}</small><TradeUnitPicker :line="item" :sku="skus.find(sku => sku.id === Number(item.sku))" :supplier="draft.supplier" /><button type="button" class="text-btn" @click="draft.items.splice(index + 1, 0, { ...item })">增加规格行</button><button type="button" class="text-btn" @click="matchingItem = item">匹配供应商</button></span><select v-model="item.supplier_sku" :disabled="!draft.supplier || !item.sku" @change="applySupplierSkuPrice(item)"><option v-if="!draft.supplier || !item.sku" value="">供应商来源（可选）</option><option v-else-if="!supplierSourcesFor(item).length" value="">未维护供应商来源（本次采购仍可继续）</option><option v-for="source in supplierSourcesFor(item)" :key="source.id" :value="source.id">{{ source.supplier_model || source.supplier_sku_code }} · {{ source.supplier_sku_code }} · {{ source.purchase_price }} {{ source.currency }}</option></select><p v-if="supplierPriceWarning(item)" class="supplier-price-warning">{{ supplierPriceWarning(item) }}</p><input v-model="item.quantity" type="number" min="0.01" step="0.01" placeholder="采购数量" required /><input v-model="item.unit_price" v-money-input type="number" min="0" step="any" placeholder="采购单价" required /><button v-if="draft.items.length > 1" type="button" class="text-btn danger" @click="draft.items.splice(index, 1)">删除</button></div><p v-if="!draft.items.length" class="purchase-empty">请先从上方选择至少一个 SKU。</p></div><div class="editor-actions"><button type="button" class="btn btn-secondary" @click="closeCreate">取消</button><button class="btn btn-primary" :disabled="saving"><Save :size="16" /> {{ saving ? '保存中…' : (editingPurchaseId ? '保存采购草稿' : '创建采购单') }}</button></div></form></section></div>
    <section class="panel"><div v-if="loading" class="loading"><div class="spinner" /></div><div v-else-if="!rows.length" class="empty"><PackagePlus :size="32" /><h3>暂无采购单</h3><p>可独立创建采购草稿，确认下单后再进入收货、付款与成本分配。</p></div><div v-else class="table-wrap"><table class="data-table"><thead><tr><th>采购单号</th><th>供应商</th><th>来源订单</th><th>预计到货</th><th>采购金额</th><th>已付 / 未付</th><th>状态</th><th></th></tr></thead><tbody><template v-for="row in rows" :key="row.id"><tr><td class="primary-cell">{{ row.purchase_no }}</td><td>{{ row.supplier_name }}</td><td>{{ row.order_no || '—' }}</td><td>{{ row.expected_arrival_date || '—' }}</td><td>{{ row.currency }} {{ money(row.total_amount) }}</td><td>{{ money(row.paid_amount) }} / {{ money(row.unpaid_amount) }}</td><td><span class="status" :class="row.status">{{ row.status_display }}</span></td><td><button class="text-btn" @click="expandedId = expandedId === row.id ? null : row.id">{{ expandedId === row.id ? '收起' : '操作' }}</button></td></tr><tr v-if="expandedId === row.id" class="detail-row"><td colspan="8"><div class="detail-row-actions"><button v-if="row.status === 'draft'" class="btn btn-primary" @click="place(row)">确认下单</button><button v-if="row.status === 'draft'" class="btn btn-secondary" @click="editDraft(row)">编辑草稿</button><button v-if="row.status === 'draft'" class="btn btn-secondary" @click="deleteDraft(row)">删除草稿</button><button v-if="['draft', 'ordered'].includes(row.status)" class="btn btn-secondary" @click="cancelPurchase(row)">取消采购</button><button v-if="!['draft', 'cancelled'].includes(row.status)" class="btn btn-secondary" @click="costTarget = row">分配采购成本 / 公共费用</button></div><p v-if="row.status === 'cancelled' && row.cancellation_reason" class="purchase-empty">取消原因：{{ row.cancellation_reason }}<span v-if="row.cancelled_at"> · {{ row.cancelled_at }}</span></p><div v-if="row.status !== 'draft'" class="purchase-detail"><div><h4>分批验货入库</h4><p>核对型号、数量及外观后，登记合格数量。不合格品不计可用库存，在备注记录拒收或待补货情况。</p><p v-for="item in row.items" :key="item.id"><button class="text-btn" @click="costTarget = row">{{ item.display_name || skus.find(sku => sku.id === Number(item.sku))?.display_name_cn || item.sku_code }} · 分配成本</button><span v-if="item.supplier_name"> · {{ item.supplier_name }} / {{ item.supplier_model || item.supplier_sku_code }}</span><small v-if="Object.keys(item.supplier_characteristics_snapshot || {}).length"> · {{ Object.entries(item.supplier_characteristics_snapshot).map(([k,v]) => `${k}：${v}`).join('；') }}</small>　采购 {{ item.trade_quantity ?? item.quantity }} {{ tradeLabel(item) }}<small v-if="item.trade_unit">（{{ item.quantity }} {{ item.trade_snapshot.base_unit }}）</small> · 已到 {{ item.received_quantity }} {{ item.trade_snapshot?.base_unit }} · 剩余 {{ item.remaining_quantity }} {{ item.trade_snapshot?.base_unit }} <button class="text-btn" :disabled="row.status === 'cancelled'" @click="openReceipt(row, item)">验货入库</button><span v-if="item.receipts?.length" class="receipt-history"><b>入库记录</b><span v-for="receipt in item.receipts" :key="receipt.id" class="receipt-history-row">{{ receipt.receipt_date }} · {{ receipt.quantity }} · {{ receipt.unit_cost }}<button v-if="!receipt.reversed_at" class="text-btn" @click="openReceiptReversal(row, item, receipt)">冲销</button><span v-else>已冲销</span></span></span></p></div><div><h4>供应商付款</h4><p>已付 {{ row.currency }} {{ money(row.paid_amount) }}，未付 {{ row.currency }} {{ money(row.unpaid_amount) }}</p><button class="btn btn-secondary" :disabled="Number(row.unpaid_amount) <= 0 || row.status === 'cancelled'" @click="pay(row)"><CircleDollarSign :size="16" /> 登记付款</button></div></div><p v-else class="purchase-empty">草稿尚未下单；确认下单后才可登记到货、付款和成本分配。</p></td></tr></template></tbody></table></div></section>

    <ContractAmountAdjustments v-for="row in rows.filter(item => item.id === expandedId && item.status !== 'draft')" :key="`adjust-${row.id}`" contract-type="purchase_order" :contract="row" @changed="load" />
    <div v-if="receiptTarget" class="receipt-mask" @click.self="receiptTarget = null"><form class="receipt-dialog" @submit.prevent="submitReceipt"><h3>验货合格入库</h3><p>{{ receiptTarget.row.purchase_no }} · {{ receiptTarget.item.display_name || receiptTarget.item.sku_code }}</p><p>待到货 {{ receiptTarget.item.remaining_quantity }} {{ receiptTarget.item.trade_snapshot?.base_unit }}。不合格或拒收数量请写入备注，等待补货后再登记入库。</p><label>实际入库日期<input v-model="receiptForm.receipt_date" type="date" required></label><TradeUnitPicker :line="receiptForm" :sku="skus.find(s => s.id === receiptTarget.item.sku)" :supplier="receiptTarget.row.supplier" price-field="unit_cost" preserve-base-quantity :historical-unit="receiptTarget.item.trade_unit" /><label>合格入库数量<input v-model="receiptForm.quantity" type="number" min="0.01" step="0.01" required></label><label>实际单价（{{ receiptTarget.row.currency }}）<input v-model="receiptForm.unit_cost" type="number" min="0" step="0.0001" required></label><label v-if="baseQuantity(receiptForm) > Number(receiptTarget.item.remaining_quantity)"><span><input v-model="receiptForm.is_overage" type="checkbox" required> 确认超到</span><select v-model="receiptForm.overage_reason" required><option value="">选择超到原因</option><option value="overprocurement">超采</option><option value="gift">供应商赠品</option><option value="carton_variance">包装尾差</option></select></label><label>验货备注 / 异常说明<textarea v-model="receiptForm.notes" placeholder="例如：拒收破损 2 件，已联系供应商补货"></textarea></label><label><span><input v-model="receiptForm.checked" type="checkbox" required> 已核对型号、数量及外观，仅登记合格品</span></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="receiptTarget = null">取消</button><button :disabled="receiptSaving || !receiptForm.checked">{{ receiptSaving ? '保存中…' : '确认入库' }}</button></footer></form></div>
    <div v-if="reversalTarget" class="receipt-mask" @click.self="reversalTarget = null"><form class="receipt-dialog" @submit.prevent="submitReceiptReversal"><h3>冲销采购入库</h3><p>{{ reversalTarget.row.purchase_no }} · {{ reversalTarget.item.display_name || reversalTarget.item.sku_code }} · {{ reversalTarget.receipt.quantity }}</p><label>冲销原因<textarea v-model="reversalReason" maxlength="500" required placeholder="请填写冲销原因"></textarea></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="reversalTarget = null">取消</button><button :disabled="reversalSaving || !reversalReason.trim()">{{ reversalSaving ? '提交中…' : '确认冲销' }}</button></footer></form></div>
  </div>
<PurchaseSupplierPicker v-if="matchingItem" :sku="skus.find(s => s.id === Number(matchingItem.sku))" :fixed-supplier="inheritedSupplier ? draft.supplier : null" @close="matchingItem = null" @selected="matchedSupplier" />
</template>

<style scoped>
.receipt-mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:100}.receipt-dialog{width:min(540px,90vw);max-height:90vh;overflow:auto;padding:24px;background:white;border-radius:14px}.receipt-dialog label{display:grid;gap:6px;margin:14px 0}.receipt-dialog input:not([type=checkbox]),.receipt-dialog select,.receipt-dialog textarea{padding:9px;border:1px solid #d8e1dd;border-radius:7px}.receipt-dialog footer{display:flex;justify-content:flex-end;gap:10px}.receipt-dialog button{padding:9px 14px}.receipt-dialog p{font-size:var(--text-body);color:#718078}

.page-actions,.editor-actions,.detail-row-actions{display:flex;gap:9px}.notice{margin:0 0 14px;padding:10px 13px;border:1px solid #b9dfce;border-radius:9px;background:#eff9f3;color:#216348}.form-error{margin:0 0 14px;padding:10px 13px;border:1px solid #efcaca;border-radius:9px;background:#fff5f5;color:#a44343}.editor{margin-bottom:18px}.section-heading{display:flex;justify-content:space-between;gap:12px}.section-heading h3,.line-editor h4{margin:0;color:#1d493d}.section-heading p{margin:5px 0 0;color:#74847d;font-size:var(--text-body)}.form-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}.form-grid label{display:grid;gap:6px;color:#536961;font-size:var(--text-body);font-weight:700}.form-grid input,.form-grid select,.purchase-line input,.purchase-line select{min-height:38px;border:1px solid #d8e3de;border-radius:8px;padding:7px 9px;background:#fff;color:#263d35}.form-grid select:disabled{background:#f1f5f3;color:#5d756b;cursor:not-allowed}.line-editor{margin-top:20px;padding-top:16px;border-top:1px solid #e5ece8}.line-editor small{color:#778881;font-weight:400}.purchase-line{display:grid;grid-template-columns:2fr 2fr 1fr 1fr auto;gap:9px;margin:9px 0}.purchase-sku{min-width:0}.purchase-sku b,.purchase-sku small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.purchase-sku b{color:#294a41;font-size:var(--text-body)}.purchase-sku small{margin-top:3px;color:#81908a;font-size:var(--text-caption)}.purchase-empty{margin:10px 18px;padding:15px;border:1px dashed #cddbd4;border-radius:8px;color:#82918b;text-align:center;font-size:var(--text-body)}.editor-actions{justify-content:flex-end;margin-top:20px}.detail-row td{padding:0!important;background:#f7faf8}.detail-row-actions{padding:16px 18px 0}.purchase-detail{display:grid;grid-template-columns:2fr 1fr;gap:20px;padding:15px 18px}.purchase-detail h4{margin:0 0 8px;color:#234a3e}.purchase-detail p{margin:7px 0;color:#526961;font-size:var(--text-body)}.purchase-detail p span{color:#668278;font-size:var(--text-body)}.text-btn{border:0;background:transparent;padding:6px 8px;border-radius:6px;color:#28624e;font:inherit;font-size:var(--text-body);cursor:pointer}.text-btn:hover{background:#e7f1eb}.text-btn:disabled{opacity:.45;cursor:not-allowed}.danger{color:#a74b4b}@media(max-width:760px){.form-grid,.purchase-detail{grid-template-columns:1fr}.purchase-line{grid-template-columns:1fr}.page-head{align-items:flex-start}.page-actions{flex-wrap:wrap}}
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
