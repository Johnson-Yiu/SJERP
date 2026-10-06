<script setup>
import TradeUnitPicker from './TradeUnitPicker.vue'
import { tradePayload, baseQuantity, tradeLabel } from '../utils/tradeUnits'
import { computed, onMounted, ref, watch } from 'vue'
import { AlertTriangle, Boxes, FileText, PackageCheck, Pencil, Truck, WalletCards, X } from 'lucide-vue-next'
import { api } from '../api'
import { confirmDialog } from '../dialogs'
import { purchaseDetailLocation } from '../utils/detailNavigation'
import OperationLogPanel from './OperationLogPanel.vue'
import SupplierAllocationModal from './SupplierAllocationModal.vue'
import ProcurementDraftModal from './ProcurementDraftModal.vue'
import ContractAmountAdjustments from './ContractAmountAdjustments.vue'

const props = defineProps({ id: { type: [Number, String], required: true }, refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['close', 'edit', 'open-quote'])
const workbench = ref(null)
const fulfillment = ref(null)
const packingPlan = ref(null)
const packingSaving = ref(false)
const activeTab = ref('overview')
const loading = ref(true)
const error = ref('')
const operationLogs = ref([])
const operationLogsLoading = ref(false)
const auditEnabled = ref(false)
const allocationItem = ref(null)
const procurementPlan = ref(null)
const procurementOpen = ref(false)
const procurementMessage = ref('')

const order = computed(() => workbench.value?.order)
const tabs = computed(() => [
  ['overview', '概览'], ['items', `订单明细 (${workbench.value?.items?.length || 0})`],
  ['payments', `回款 (${workbench.value?.payments?.length || 0})`], ['fulfillment', '采购与发货'], ['packing', '预计装箱'], ['inventory', `库存流水 (${workbench.value?.inventory?.length || 0})`],
  ['operation_logs', `操作日志 (${operationLogs.value.length})`],
])
const paymentPercent = computed(() => {
  const total = Number(workbench.value?.payment_summary?.planned_amount || 0)
  return total ? Math.min(100, Math.max(0, Number(workbench.value?.payment_summary?.paid_amount || 0) / total * 100)) : 0
})
const contractAmountLabel = computed(() => order.value?.status === 'cancelled' ? '历史合同额' : order.value?.status === 'draft' ? '合同草稿金额' : '订单总额')
const receivableStatus = computed(() => order.value?.status === 'draft' ? '尚未生效' : order.value?.status === 'cancelled' ? '已取消' : null)
const canViewReceivable = computed(() => {
  const balance = Number(workbench.value?.payment_summary?.balance_amount)
  return Number.isFinite(balance) && balance > 0 && !['draft', 'cancelled'].includes(order.value?.status)
})
const fulfillmentPercent = computed(() => {
  const total = Number(workbench.value?.fulfillment_summary?.ordered_quantity || 0)
  return total ? Math.min(100, Math.max(0, Number(workbench.value?.fulfillment_summary?.shipped_quantity || 0) / total * 100)) : 0
})
const itemSubtotal = computed(() => (workbench.value?.items || []).reduce((sum, item) => sum + Number(item.amount || 0), 0))
const canOpenProcurement = computed(() => ['confirmed', 'production'].includes(order.value?.status) && (procurementPlan.value?.items || []).some(item => Number(item.draftable_quantity) > 0))
const canShipOrder = computed(() => ['confirmed', 'production', 'shipped'].includes(order.value?.status))
const shippableItems = computed(() => (fulfillment.value?.items || []).filter(item => Number(item.unshipped_quantity) > 0))
const canBatchShip = computed(() => canShipOrder.value && shippableItems.value.length > 0)

function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function date(value) { return value || '—' }
function localDateInputValue(value = new Date()) {
  const localeDate = value.toLocaleDateString('en-CA')
  if (/^\d{4}-\d{2}-\d{2}$/.test(localeDate)) return localeDate
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}
const shipmentDialogOpen = ref(false)
const shipmentDate = ref('')
const shipmentLines = ref([])
const shipmentSkuDetails = ref(new Map())
const shipmentSkuCache = new Map()
const shipmentSkuLoading = ref(false)
const shipmentSkuFailed = ref(false)
const shipmentSaving = ref(false)
const shipmentError = ref('')
const selectedShipmentLines = computed(() => shipmentLines.value.filter(line => line.selected))
const overageShipmentLines = computed(() => selectedShipmentLines.value.filter(line => baseQuantity(line) > Number(line.unshipped_quantity)))
const shipmentReversalTarget = ref(null), shipmentReversalReason = ref(''), shipmentReversalSaving = ref(false)
const lifecycleSaving = ref(false)
const cancelOpen = ref(false), cancellationReason = ref('')
const overageReasonLabels = { customer_addon: '客户追加', gift_or_sample: '赠品/样品', packing_variance: '包装尾差' }

function shipmentLineValid(line) {
  return Number.isFinite(baseQuantity(line)) && baseQuantity(line) > 0 &&
    (baseQuantity(line) <= Number(line.unshipped_quantity) || Object.hasOwn(overageReasonLabels, line.overage_reason))
}
const shipmentCanSubmit = computed(() => !shipmentSaving.value && !shipmentSkuLoading.value && !shipmentSkuFailed.value &&
  selectedShipmentLines.value.length > 0 && selectedShipmentLines.value.every(shipmentLineValid))

function getShipmentSku(skuId) {
  const id = Number(skuId)
  if (!shipmentSkuCache.has(id)) {
    const request = api.get(`/skus/${id}/`).then(response => response.data).catch(err => {
      shipmentSkuCache.delete(id)
      throw err
    })
    shipmentSkuCache.set(id, request)
  }
  return shipmentSkuCache.get(id)
}

async function openShipmentDialog(initialOrderItemIds = null) {
  if (!canShipOrder.value) return
  const eligible = shippableItems.value
  if (!eligible.length) return
  const selectedIds = initialOrderItemIds == null ? null : new Set(initialOrderItemIds.map(Number))
  shipmentDate.value = localDateInputValue()
  shipmentError.value = ''
  shipmentSkuFailed.value = false
  shipmentLines.value = eligible.map(item => {
    const historicalItem = (workbench.value?.items || []).find(row => Number(row.id) === Number(item.id))
    const unit = item.base_unit || historicalItem?.trade_snapshot?.base_unit || 'pcs'
    return {
      order_item: Number(item.id),
      sku: Number(item.sku),
      sku_code: item.sku_code,
      display_name: item.display_name || item.product_name || item.sku_code,
      base_unit: unit,
      unshipped_quantity: Number(item.unshipped_quantity),
      historical_unit: historicalItem?.trade_unit || null,
      selected: selectedIds == null || selectedIds.has(Number(item.id)),
      quantity: String(item.unshipped_quantity),
      trade_unit: null,
      trade_snapshot: { name: '', unit, base_unit: unit, factor: '1' },
      overage_reason: '',
    }
  })
  shipmentDialogOpen.value = true
  shipmentSkuLoading.value = true
  const skuIds = [...new Set(shipmentLines.value.map(line => line.sku))]
  const results = await Promise.allSettled(skuIds.map(async id => ({ id, sku: await getShipmentSku(id) })))
  const details = new Map(shipmentSkuDetails.value)
  const failed = []
  for (const result of results) {
    if (result.status === 'fulfilled') details.set(result.value.id, result.value.sku)
    else failed.push(result.reason)
  }
  shipmentSkuDetails.value = details
  if (failed.length) {
    shipmentSkuFailed.value = true
    shipmentError.value = failed[0]?.message || 'SKU 规格资料加载失败，请关闭后重试。'
  }
  shipmentSkuLoading.value = false
}

function closeShipmentDialog() {
  if (shipmentSaving.value) return
  shipmentDialogOpen.value = false
}

function shipmentOverageSummary(lines) {
  const details = lines.map(line => {
    const quantity = baseQuantity(line)
    const extra = quantity - Number(line.unshipped_quantity)
    return `${line.sku_code} · 明细 #${line.order_item}：待发 ${line.unshipped_quantity}，发货 ${quantity}，超出 ${extra} ${line.base_unit} · ${overageReasonLabels[line.overage_reason]}`
  })
  return `以下发货明细超过原待发数量：\n\n${details.join('\n')}\n\n确认后系统会按现有超发规则生成相应增补记录。`
}

function shipmentErrorMessage(err) {
  const data = err.response?.data
  return data?.detail || (data && typeof data === 'object' ? Object.values(data).flat().join('；') : '') || err.message || '发货失败，请修正明细后重试。'
}

async function submitShipment() {
  if (shipmentSaving.value || shipmentSkuLoading.value) return
  const selected = selectedShipmentLines.value
  if (!selected.length) { shipmentError.value = '请至少选择一条发货明细。'; return }
  if (new Set(selected.map(line => line.order_item)).size !== selected.length) { shipmentError.value = '发货明细不能重复。'; return }
  if (selected.some(line => baseQuantity(line) <= 0)) { shipmentError.value = '每条已选择的发货数量都必须大于零。'; return }
  if (selected.some(line => baseQuantity(line) > Number(line.unshipped_quantity) && !Object.hasOwn(overageReasonLabels, line.overage_reason))) {
    shipmentError.value = '每条超发明细都必须分别选择超发原因。'
    return
  }
  if (overageShipmentLines.value.length && !await confirmDialog({
    title: '确认批量超发',
    message: shipmentOverageSummary(overageShipmentLines.value),
    confirmText: '确认发货',
    danger: true,
  })) return

  shipmentSaving.value = true
  shipmentError.value = ''
  try {
    const items = selected.map(line => tradePayload({
      order_item: line.order_item,
      quantity: line.quantity,
      trade_unit: line.trade_unit,
      trade_snapshot: line.trade_snapshot,
      overage_reason: baseQuantity(line) > Number(line.unshipped_quantity) ? line.overage_reason : '',
    }, null))
    await api.post(`/orders/${props.id}/ship/`, { shipment_date: shipmentDate.value, items })
    shipmentDialogOpen.value = false
    await load()
  } catch (err) { shipmentError.value = shipmentErrorMessage(err) }
  finally { shipmentSaving.value = false }
}
async function lifecycleAction(path, confirmation) {
  if (lifecycleSaving.value || (confirmation && !await confirmDialog({ title: '确认订单操作', message: confirmation, confirmText: '确认继续', danger: true }))) return
  lifecycleSaving.value = true
  error.value = ''
  try { await api.post(`/orders/${props.id}/${path}/`); await load() }
  catch (err) { error.value = err.message }
  finally { lifecycleSaving.value = false }
}
function openCancellation() { cancellationReason.value = ''; error.value = ''; cancelOpen.value = true }
async function submitCancellation() {
  const reason = cancellationReason.value.trim()
  if (!reason || lifecycleSaving.value) return
  lifecycleSaving.value = true
  try { await api.post(`/orders/${props.id}/cancel/`, { reason }); cancelOpen.value = false; await load() }
  catch (err) { error.value = err.message }
  finally { lifecycleSaving.value = false }
}
function ship(item) { return openShipmentDialog([item.id]) }
function openShipmentReversal(shipment) {
  shipmentReversalTarget.value = shipment
  shipmentReversalReason.value = ''
  error.value = ''
}
async function submitShipmentReversal() {
  const reason = shipmentReversalReason.value.trim()
  if (!reason || shipmentReversalSaving.value) return
  shipmentReversalSaving.value = true
  error.value = ''
  try {
    await api.post(`/shipments/${shipmentReversalTarget.value.id}/reverse/`, { reason })
    shipmentReversalTarget.value = null
    shipmentReversalReason.value = ''
    await load()
  } catch (err) { error.value = err.response?.data?.detail || JSON.stringify(err.response?.data || err.message) }
  finally { shipmentReversalSaving.value = false }
}
async function generatePackingPlan() {
  if (packingSaving.value) return
  packingSaving.value = true
  try { packingPlan.value = (await api.post(`/orders/${props.id}/packing-plan/`)).data }
  catch (err) { error.value = err.response?.data?.detail || err.message }
  finally { packingSaving.value = false }
}
async function regeneratePackingPlan() {
  if (packingSaving.value) return
  if (!await confirmDialog({ title: '确认重新生成', message: '重新生成会使用当前 SKU 包装配置，并替换当前订单的预计装箱方案。', confirmText: '确认重新生成', danger: true })) return
  await generatePackingPlan()
}
function packingStatusLabel(status) {
  return { generated: '已生成', needs_attention: '待处理' }[status] || status || '—'
}
function packingTemplateName(snapshot) {
  return snapshot?.name || snapshot?.code || '未记录包装模板'
}
function openSupplierAllocation(item) { allocationItem.value = item }
async function supplierAllocationSaved() { allocationItem.value = null; await load() }
function openProcurementDrafts() { procurementMessage.value = ''; procurementOpen.value = true }
async function procurementDraftsCreated(result) {
  procurementOpen.value = false
  procurementMessage.value = `已生成 ${result.created_count} 张采购草稿：${(result.purchase_orders || []).map(row => row.purchase_no).join('、')}`
  await load()
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [workbenchResult, fulfillmentResult, packingResult, procurementResult] = await Promise.all([api.get(`/orders/${props.id}/workbench/`), api.get(`/orders/${props.id}/fulfillment/`), api.get(`/orders/${props.id}/packing-plan/`).catch(() => null), api.get(`/orders/${props.id}/procurement-plan/`).catch(() => null), loadOperationLogs()])
    workbench.value = workbenchResult.data
    fulfillment.value = fulfillmentResult.data
    packingPlan.value = packingResult?.data || null
    procurementPlan.value = procurementResult?.data || null
  }
  catch (err) { error.value = err.message }
  finally { loading.value = false }
}
async function loadOperationLogs(id = props.id) {
  operationLogsLoading.value = true
  try {
    const [logsResult, operatorResult] = await Promise.all([
      api.get('/operation-logs/', { params: { entity: 'crm.order', object_id: id, ordering: '-created_at' } }).catch(() => ({ data: [] })),
      api.get('/session/current-operator/').catch(() => ({ data: {} })),
    ])
    operationLogs.value = logsResult.data?.results || logsResult.data || []
    auditEnabled.value = Boolean(operatorResult.data?.audit_log_enabled)
  } finally { operationLogsLoading.value = false }
}

onMounted(load)
watch(() => props.id, load)
watch(() => props.refreshKey, load)
</script>

<template>
  <Teleport to="body">
    <div v-if="shipmentDialogOpen" class="trade-shipment-mask">
      <form class="trade-shipment-dialog shipment-batch-dialog" role="dialog" aria-modal="true" aria-labelledby="shipment-dialog-title" @submit.prevent="submitShipment">
        <h3 id="shipment-dialog-title">确认发货</h3>
        <label class="shipment-date-field">发货日期<input v-model="shipmentDate" aria-label="发货日期" type="date" required /></label>
        <p>每条订单明细独立录入规格和数量；同一 SKU 的不同订单行仍保持独立。</p>
        <p class="shipment-atomic-note">整批作为一张发货单一次确认；任一明细失败时，本批次整体不生效。</p>
        <p v-if="shipmentSkuLoading" role="status">正在加载 SKU 规格…</p>
        <p class="shipment-selected-count">已选 {{ selectedShipmentLines.length }} 条明细</p>
        <div class="shipment-batch-lines">
          <section v-for="line in shipmentLines" :key="line.order_item" class="shipment-batch-line">
            <header>
              <label class="shipment-line-toggle"><input v-model="line.selected" type="checkbox" :aria-label="`选择 ${line.sku_code} 明细 #${line.order_item}`" />{{ line.display_name }} · {{ line.sku_code }} · 明细 #{{ line.order_item }}</label>
              <strong>待发 {{ line.unshipped_quantity }} {{ line.base_unit }}</strong>
            </header>
            <div v-if="line.selected" class="shipment-line-fields">
              <TradeUnitPicker :line="line" :sku="shipmentSkuDetails.get(line.sku)" :price-field="null" preserve-base-quantity :historical-unit="line.historical_unit" />
              <label>发货数量<input v-model="line.quantity" :aria-label="`发货数量 ${line.sku_code} 明细 #${line.order_item}`" type="number" min="0.01" step="0.01" required /></label>
              <p v-if="line.trade_unit">交易数量 {{ line.quantity }} {{ line.trade_snapshot?.unit }}，折合 {{ baseQuantity(line) }} {{ line.base_unit }}</p>
              <label v-if="baseQuantity(line) > Number(line.unshipped_quantity)">超发原因<select v-model="line.overage_reason" :aria-label="`超发原因 ${line.sku_code} 明细 #${line.order_item}`" required><option value="">请选择</option><option value="customer_addon">客户追加</option><option value="gift_or_sample">赠品或样品</option><option value="packing_variance">包装尾差</option></select></label>
            </div>
          </section>
        </div>
        <p v-if="shipmentError" role="alert">{{ shipmentError }}</p>
        <footer><button type="button" class="btn btn-secondary" :disabled="shipmentSaving" @click="closeShipmentDialog">取消</button><button type="submit" class="btn btn-primary" :disabled="!shipmentCanSubmit">{{ shipmentSaving ? '保存中…' : '确认发货' }}</button></footer>
      </form>
    </div>
    <div v-if="shipmentReversalTarget" class="trade-shipment-mask"><form class="trade-shipment-dialog" @submit.prevent="submitShipmentReversal"><h3>冲销发货 · {{ shipmentReversalTarget.shipment_no }}</h3><p>{{ shipmentReversalTarget.has_overage ? '该发货单包含超发/增补。冲销会同步撤销系统生成的增补订单明细；客户追加产生的未收款应收计划也会取消。如已发生收款，系统将拒绝冲销。' : '原发货记录将保留，并生成对应的库存回收入库流水。' }}</p><label>冲销原因<textarea v-model="shipmentReversalReason" maxlength="500" rows="4" required /></label><p v-if="error" role="alert">{{ error }}</p><footer><button type="button" class="btn btn-secondary" @click="shipmentReversalTarget = null">取消</button><button class="btn btn-primary" :disabled="shipmentReversalSaving || !shipmentReversalReason.trim()">{{ shipmentReversalSaving ? '保存中…' : '确认冲销' }}</button></footer></form></div>
    <div v-if="cancelOpen" class="trade-shipment-mask"><form class="trade-shipment-dialog" @submit.prevent="submitCancellation"><h3>取消订单</h3><p>取消会释放库存预留并取消未结应收计划；已有不可逆业务记录时系统会拒绝操作。</p><label>取消原因<textarea v-model="cancellationReason" maxlength="500" rows="4" required /></label><p v-if="error" role="alert">{{ error }}</p><footer><button type="button" class="btn btn-secondary" @click="cancelOpen = false">返回</button><button class="btn btn-primary" :disabled="lifecycleSaving || !cancellationReason.trim()">{{ lifecycleSaving ? '提交中…' : '确认取消' }}</button></footer></form></div>
  </Teleport>
  <div class="modal-backdrop detail-backdrop" @mousedown.self="emit('close')">
    <article class="detail-modal order-workbench" role="dialog" aria-modal="true" aria-label="订单工作台">
      <div v-if="loading" class="detail-loading"><div class="spinner" /> 正在加载订单工作台…</div>
      <div v-else-if="error" class="detail-error"><AlertTriangle :size="27" /><strong>加载失败</strong><p>{{ error }}</p><button class="btn btn-secondary" @click="load">重试</button></div>
      <template v-else>
        <header class="detail-header">
          <div class="detail-nav"><div class="detail-nav-start"><button class="detail-close" aria-label="关闭订单详情" @click="emit('close')"><X :size="18" /> <span>关闭</span></button><span>订单工作台 · 履约与回款</span></div><div class="detail-actions"><button v-if="order.status === 'draft'" class="btn btn-secondary" @click="emit('edit')"><Pencil :size="14" /> 编辑草稿</button><button v-if="order.status === 'draft'" class="btn btn-secondary" :disabled="lifecycleSaving" @click="lifecycleAction('confirm', '确认后订单将进入正式履约，并生成库存预留和应收计划。是否继续？')">确认订单</button><button v-if="order.status === 'confirmed'" class="btn btn-secondary" :disabled="lifecycleSaving" @click="lifecycleAction('start-production')">开始生产</button><button v-if="order.status === 'shipped'" class="btn btn-secondary" :disabled="lifecycleSaving" @click="lifecycleAction('complete')">完成订单</button><button v-if="['draft', 'confirmed', 'production'].includes(order.status)" class="btn btn-secondary" :disabled="lifecycleSaving" @click="openCancellation">取消订单</button><button class="detail-close" aria-label="关闭订单详情" @click="emit('close')"><X :size="18" /> <span>关闭</span></button></div></div>
          <div class="detail-identity"><div><p class="detail-subtitle">{{ order.customer_name }} · 下单于 {{ date(order.order_date) }}</p><h2>{{ order.order_no }}</h2><small>预计交期：{{ date(order.expected_ship_date) }}</small><p v-if="order.status === 'cancelled' && order.cancellation_reason" class="cancelled-context">取消原因：{{ order.cancellation_reason }}<span v-if="order.cancelled_at"> · {{ date(order.cancelled_at) }}</span></p></div><span class="detail-badge">{{ order.status_display }}</span></div>
        </header>
        <main class="detail-content">
          <nav class="workbench-tabs" aria-label="订单工作台分页"><button v-for="tab in tabs" :key="tab[0]" :class="{ active: activeTab === tab[0] }" @click="activeTab = tab[0]">{{ tab[1] }}</button></nav>

          <section v-if="activeTab === 'overview'" class="workbench-grid">
            <article class="workbench-card summary-card"><h3><PackageCheck :size="18" /> 订单概览</h3><div class="summary-metrics"><div><small>{{ contractAmountLabel }}</small><strong>{{ order.currency }} {{ money(order.total_amount) }}</strong></div><div><small>已收款</small><strong>{{ order.currency }} {{ money(workbench.payment_summary.paid_amount) }}</strong></div><div><small>当前待收</small><strong v-if="!receivableStatus">{{ order.currency }} {{ money(workbench.payment_summary.balance_amount) }}</strong><strong v-else>{{ receivableStatus }}</strong></div></div></article>
            <article class="workbench-card"><div class="section-heading"><div><h3><FileText :size="16" /> 来源报价</h3><p>保留成交时采用的报价版本，方便回溯。</p></div></div><template v-if="workbench.source_quote"><strong class="quote-no">{{ workbench.source_quote.quote_no }}</strong><p>{{ workbench.source_quote.status_display }} · {{ workbench.source_quote.currency }} {{ money(workbench.source_quote.total_amount) }}</p><button class="text-btn" @click="emit('open-quote', workbench.source_quote.id)">查看报价工作台</button></template><p v-else class="muted">该订单未关联来源报价。</p></article>
            <article class="workbench-card"><div class="section-heading"><div><h3><WalletCards :size="16" /> 回款进度</h3><p>包含已确认回款与预收核销，扣除客户退款。</p></div><b>{{ paymentPercent.toFixed(0) }}%</b></div><div class="progress-track"><i :style="{ width: `${paymentPercent}%` }" /></div><dl class="data-list compact"><dt>应收计划</dt><dd>{{ order.currency }} {{ money(workbench.payment_summary.planned_amount) }}</dd><dt>已收金额</dt><dd>{{ order.currency }} {{ money(workbench.payment_summary.paid_amount) }}</dd><dt>当前待收</dt><dd v-if="!receivableStatus">{{ order.currency }} {{ money(workbench.payment_summary.balance_amount) }}</dd><dd v-else>{{ receivableStatus }}</dd><dt>分配商品成本</dt><dd>¥ {{ money(workbench.profit_summary?.purchase_base_rmb) }}</dd><dt>分摊附加费用</dt><dd>¥ {{ money(workbench.profit_summary?.purchase_additional_rmb) }}</dd><dt>预估毛利</dt><dd>¥ {{ money(workbench.profit_summary?.estimated_gross_profit_rmb) }}</dd></dl><RouterLink v-if="canViewReceivable" class="receivable-cta" :to="{ path: '/receivables', query: { order: String(order.id) } }">查看 / 登记本单应收</RouterLink></article>
            <article class="workbench-card"><div class="section-heading"><div><h3><Truck :size="16" /> 履约进度</h3><p>依据关联的销售出库流水计算。</p></div><b>{{ fulfillmentPercent.toFixed(0) }}%</b></div><div class="progress-track fulfillment"><i :style="{ width: `${fulfillmentPercent}%` }" /></div><dl class="data-list compact"><dt>订单数量</dt><dd>{{ workbench.fulfillment_summary.ordered_quantity }}</dd><dt>已出库</dt><dd>{{ workbench.fulfillment_summary.shipped_quantity }}</dd><dt>待出库</dt><dd>{{ workbench.fulfillment_summary.remaining_quantity }}</dd></dl></article>
          </section>
          <ContractAmountAdjustments v-if="activeTab === 'overview' && order" contract-type="order" :contract="order" @changed="load" />

           <section v-else-if="activeTab === 'items'" class="workbench-card"><div class="section-heading"><div><h3><Boxes :size="16" /> 订单明细</h3><p>订单保存时固定销售型号、描述、单位和内部名称快照；当前采购来源可单独分配；已生成采购单保留原来源。</p></div><strong>{{ workbench.items.length }} 项</strong></div><div class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>Model</th><th>内部名称 / SKU Code</th><th>Description</th><th>当前采购来源</th><th>数量</th><th>单位</th><th>成交单价</th><th>参考成本单价</th><th>小计</th></tr></thead><tbody><tr v-for="item in workbench.items" :key="item.id"><td>{{ item.sales_model || item.model || '未设置' }}</td><td>{{ item.display_name || item.product_name }}<small>{{ item.sku_code }}</small></td><td>{{ item.description || '—' }}</td><td>{{ item.supplier_name || '未分配' }}<small>{{ item.supplier_sku_code || '' }}</small></td><td>{{ item.trade_quantity ?? item.quantity }}<small v-if="item.trade_unit">{{ item.quantity }} {{ item.trade_snapshot.base_unit }}</small></td><td>{{ tradeLabel(item) || '—' }}</td><td>{{ order.currency }} {{ money(item.trade_unit_price ?? item.unit_price) }}</td><td>{{ order.currency }} {{ money(item.cost_price) }}</td><td>{{ order.currency }} {{ money(item.amount) }}</td></tr></tbody></table></div><div class="order-totals"><span>商品小计 <b>{{ order.currency }} {{ money(itemSubtotal) }}</b></span><span>运费 <b>{{ order.currency }} {{ money(order.shipping_fee) }}</b></span><span>折扣 / 优惠 <b>- {{ order.currency }} {{ money(order.discount) }}</b></span><strong>订单总计 <b>{{ order.currency }} {{ money(order.total_amount) }}</b></strong></div></section>

          <section v-else-if="activeTab === 'payments'" class="workbench-card"><div class="section-heading"><div><h3><WalletCards :size="16" /> 回款流水</h3><p>确认付款后，订单的已收金额会自动更新。</p></div><strong>{{ workbench.payments.length }} 条</strong></div><div v-if="!workbench.payments.length" class="workbench-empty"><WalletCards :size="28" /><strong>暂无关联流水</strong><p>可在财务流水中关联此订单，记录定金与尾款。</p></div><div v-else class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>日期</th><th>流水号</th><th>类型</th><th>分类</th><th>状态</th><th>金额</th></tr></thead><tbody><tr v-for="payment in workbench.payments" :key="payment.id"><td>{{ date(payment.transaction_date) }}</td><td>{{ payment.transaction_no }}</td><td>{{ payment.direction_display }}</td><td>{{ payment.category }}</td><td><span class="status" :class="payment.status">{{ payment.status_display }}</span></td><td>{{ payment.currency }} {{ money(payment.amount) }}</td></tr></tbody></table></div></section>

          <section v-else-if="activeTab === 'packing'" class="packing-plan-panel">
            <div class="section-heading"><div><h3><Boxes :size="16" /> 预计装箱</h3><p>预计装箱方案只保存当前订单的包装快照，不会自动创建发货或实际装箱记录。</p></div></div>
            <div v-if="!packingPlan" class="workbench-empty packing-plan-empty"><Boxes :size="28" /><strong>尚未生成预计装箱方案</strong><p>生成后会根据当前 SKU 包装配置保存可追溯的箱规快照。</p><button type="button" class="btn btn-primary" :disabled="packingSaving" @click="generatePackingPlan">{{ packingSaving ? '生成中…' : '生成预计装箱方案' }}</button></div>
            <template v-else>
              <div class="packing-plan-toolbar"><div><span class="packing-status" :class="packingPlan.status">{{ packingStatusLabel(packingPlan.status) }}</span><span class="packing-plan-caption">重新生成会替换当前方案</span></div><button type="button" class="btn btn-secondary" :disabled="packingSaving" @click="regeneratePackingPlan">{{ packingSaving ? '生成中…' : '重新生成预计装箱方案' }}</button></div>
              <div class="packing-plan-summary"><div><small>预计箱数</small><strong>{{ packingPlan.total_cartons }}</strong></div><div><small>预计净重</small><strong>{{ packingPlan.total_net_weight }} kg</strong></div><div><small>预计毛重</small><strong>{{ packingPlan.total_gross_weight }} kg</strong></div><div><small>预计 CBM</small><strong>{{ packingPlan.total_cbm }} m³</strong></div></div>
              <div v-if="packingPlan.warnings?.length" class="packing-plan-warnings" role="alert"><AlertTriangle :size="17" /><div><strong>包装方案需要注意</strong><p v-for="warning in packingPlan.warnings" :key="warning">{{ warning }}</p><p>如提示 SKU 包装资料未配置，请先在报价编辑器/包装配置中补充 SKU 默认包装。</p></div></div>
              <div v-if="!packingPlan.cartons?.length" class="workbench-empty"><Boxes :size="28" /><strong>暂无箱明细</strong><p>请根据上方警告补充包装配置后，再重新生成方案。</p></div>
              <div v-else class="packing-carton-list"><article v-for="carton in packingPlan.cartons" :key="carton.id" class="packing-carton-card"><header><div><strong>第 {{ carton.carton_no }} 箱</strong><span>{{ packingTemplateName(carton.packaging_template_snapshot) }}</span></div><div class="packing-carton-flags"><span v-if="carton.is_partial">尾箱</span><span v-if="carton.requires_confirmation">待确认</span></div></header><dl class="packing-carton-data"><dt>包装模板快照</dt><dd>{{ carton.packaging_template_snapshot?.name || carton.packaging_template_snapshot?.code || '—' }}</dd><dt>每箱数量快照</dt><dd>{{ carton.qty_per_carton_snapshot ?? '—' }}</dd><dt>尺寸</dt><dd>{{ carton.length ?? '—' }} × {{ carton.width ?? '—' }} × {{ carton.height ?? '—' }} cm</dd><dt>预计净重</dt><dd>{{ carton.estimated_net_weight }} kg</dd><dt>预计毛重</dt><dd>{{ carton.estimated_gross_weight }} kg</dd><dt>预计 CBM</dt><dd>{{ carton.estimated_cbm }} m³</dd></dl><div class="packing-carton-items"><span v-for="item in carton.items || []" :key="item.id">{{ item.sku_code_snapshot }} · {{ item.sku_name_snapshot }} × {{ item.quantity }}</span></div></article></div>
            </template>
          </section>
          <section v-else-if="activeTab === 'inventory'" class="workbench-card"><div class="section-heading"><div><h3><Truck :size="16" /> 履约流水</h3><p>关联此订单的出入库动作会在这里集中展示。</p></div><strong>{{ workbench.inventory.length }} 条</strong></div><div v-if="!workbench.inventory.length" class="workbench-empty"><Truck :size="28" /><strong>暂无出入库流水</strong><p>在库存流水中关联本订单后，履约进度会自动更新。</p></div><div v-else class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>日期</th><th>流水号</th><th>类型</th><th>SKU</th><th>数量</th><th>仓库</th></tr></thead><tbody><tr v-for="movement in workbench.inventory" :key="movement.id"><td>{{ date(movement.movement_date) }}</td><td>{{ movement.movement_no }}</td><td>{{ movement.type_display }}</td><td>{{ movement.sku_code }}</td><td>{{ movement.signed_quantity }}</td><td>{{ movement.warehouse }}</td></tr></tbody></table></div></section>
          <OperationLogPanel v-else :logs="operationLogs" :loading="operationLogsLoading" :enabled="auditEnabled" />
        </main>
      </template>
      <section v-if="!loading && !error && activeTab === 'payments' && workbench?.advance_allocations?.length" class="workbench-card"><h3>预收款核销记录</h3><p>以下金额已计入本订单回款；原始收款可在财务流水中查看。</p><div class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>原始收款日期</th><th>流水号</th><th>核销金额</th><th>状态</th></tr></thead><tbody><tr v-for="row in workbench.advance_allocations" :key="row.id"><td>{{ row.transaction_date }}</td><td>{{ row.transaction_no }}</td><td>{{ row.currency }} {{ money(row.amount) }}</td><td>{{ row.is_active ? '已核销' : '已撤回' }}</td></tr></tbody></table></div></section>
       <section v-if="!loading && !error && activeTab === 'fulfillment'" class="fulfillment-panel"><div class="section-heading"><div><h3>采购与发货</h3><p>待采购是库存与正式采购后的真实缺口；采购草稿单独展示，尚未等同于已下单。</p></div><div class="fulfillment-header-actions"><button v-if="canBatchShip" class="btn btn-primary" @click="openShipmentDialog()">批量发货</button><button class="btn btn-primary" :disabled="!canOpenProcurement" @click="openProcurementDrafts">生成采购草稿</button></div></div><p v-if="procurementMessage" class="procurement-success">{{ procurementMessage }}</p><div class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>SKU</th><th>当前采购来源</th><th>订单</th><th>预留</th><th>待采购</th><th>采购草稿</th><th>已采购</th><th>已到 / 在途</th><th>已发 / 待发</th><th>操作</th></tr></thead><tbody><tr v-for="item in fulfillment?.items || []" :key="item.id"><td>{{ item.sku_code }}<small>基础单位：{{ item.base_unit }}</small></td><td>{{ item.supplier_name || '未分配' }}<small v-if="item.supplier_sku_code">{{ item.supplier_sku_code }}</small></td><td>{{ item.quantity }}</td><td>{{ item.allocated_quantity }}</td><td>{{ item.to_procure_quantity }}<small>可建 {{ item.draftable_quantity }}</small></td><td>{{ item.draft_procurement_quantity }}</td><td>{{ item.purchased_quantity }}</td><td>{{ item.arrived_quantity }} / {{ item.in_transit_quantity }}</td><td>{{ item.shipped_quantity }} / {{ item.unshipped_quantity }}</td><td><button class="text-btn" :disabled="!['draft', 'confirmed', 'production'].includes(order.status)" @click="openSupplierAllocation(item)">{{ item.supplier_name ? '更换当前来源' : '选择采购来源' }}</button><button class="text-btn" :disabled="Number(item.unshipped_quantity) <= 0 || !canShipOrder" @click="ship(item)">确认发货</button></td></tr></tbody></table></div><p v-if="!(fulfillment?.purchase_orders || []).length" class="muted">尚未创建关联采购单；请先选择供应商后生成采购草稿。</p><div v-else class="purchase-history"><div class="section-heading"><div><h3>关联采购单</h3><p>草稿不计入正式采购覆盖；已下单、部分到货和完成状态按当前履约数据计算。</p></div></div><article v-for="purchase in fulfillment.purchase_orders" :key="purchase.id" class="purchase-history-card"><div><RouterLink class="purchase-navigation-link" :to="purchaseDetailLocation(purchase.id)">{{ purchase.purchase_no }} · 查看采购单</RouterLink><small>{{ purchase.supplier_name }} · {{ purchase.currency }} {{ money(purchase.total_amount) }}</small></div><div><span class="status" :class="purchase.status">{{ purchase.status_display }}</span><small>预计 {{ date(purchase.expected_arrival_date) }}</small></div><p>{{ (purchase.items || []).map(line => `${line.sku_code} × ${line.quantity}`).join(' / ') }}</p></article></div><div class="shipment-history"><div class="section-heading"><div><h3>发货记录</h3><p>已确认的发货单均可整单冲销；超发或增补将按关联业务记录一并安全撤销。</p></div><strong>{{ (fulfillment?.shipments || []).length }} 条</strong></div><div v-if="!(fulfillment?.shipments || []).length" class="workbench-empty"><Truck :size="28" /><strong>暂无发货记录</strong></div><div v-else class="shipment-history-list"><article v-for="shipment in fulfillment.shipments" :key="shipment.id" class="shipment-history-card"><div class="shipment-history-head"><div><strong>{{ shipment.shipment_no }}</strong><small>{{ date(shipment.shipment_date) }}</small></div><span class="status" :class="shipment.status">{{ shipment.status === 'cancelled' ? '已冲销' : shipment.status === 'confirmed' ? '已确认' : shipment.status }}</span></div><div class="shipment-history-items"><span v-for="line in shipment.items" :key="line.id">{{ line.sku_code }} × {{ line.quantity }}</span></div><div class="shipment-history-actions"><button v-if="shipment.status === 'confirmed'" class="text-btn" @click="openShipmentReversal(shipment)">冲销</button><span v-else-if="shipment.status === 'cancelled'" class="muted">已冲销</span><span v-else class="muted">暂不可操作</span></div></article></div></div></section>
     </article>
     <SupplierAllocationModal v-if="allocationItem" :order-id="props.id" :order-item="allocationItem" @close="allocationItem = null" @saved="supplierAllocationSaved" />
     <ProcurementDraftModal v-if="procurementOpen && procurementPlan" :order-id="props.id" :plan="procurementPlan" @close="procurementOpen = false" @created="procurementDraftsCreated" />
  </div>
</template>

<style scoped>
.detail-backdrop{inset:0 0 0 248px;z-index:25;place-items:stretch end;padding:0;background:#0b221d66;backdrop-filter:blur(2px)}.detail-modal{height:100vh;width:min(1080px,100%);background:#f6f8f5;box-shadow:-24px 0 70px #06191452;overflow:auto;overscroll-behavior:contain}.detail-loading,.detail-error{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#71817b}.detail-error strong{color:#9d4444}.detail-error p{font-size:var(--text-body)}.detail-header{position:relative;overflow:hidden;padding:20px 28px 24px;background:#123c36;color:#fff}.detail-header:after{position:absolute;top:-140px;right:-80px;width:300px;height:300px;border:60px solid #ffffff08;border-radius:50%;content:''}.detail-nav,.detail-identity{position:relative;z-index:1}.detail-nav,.detail-nav-start{display:flex;align-items:center}.detail-nav{justify-content:space-between;color:#91b6aa;font-size:var(--text-body);letter-spacing:.12em;text-transform:uppercase}.detail-nav-start{gap:10px}.detail-actions{display:flex;align-items:center;gap:8px}.detail-actions .btn{padding:7px 11px;color:#fff;font-size:var(--text-body);letter-spacing:0;text-transform:none;background:#ffffff12;border-color:#ffffff28}.detail-close{display:flex;align-items:center;gap:7px;min-height:38px;padding:8px 11px;border:1px solid #ffffff45;border-radius:9px;background:#ffffff1a;color:#fff;font-size:var(--text-body);font-weight:700;letter-spacing:0;text-transform:none}.detail-identity{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-top:23px}.detail-subtitle{margin:0;color:#9cc0b5;font-size:var(--text-caption)}.detail-identity h2{margin:5px 0 0;font-size:var(--text-page)}.detail-identity small{color:#b6d3ca;font-size:var(--text-caption)}.detail-badge{padding:6px 10px;border:1px solid #ffffff22;border-radius:20px;background:#ffffff14;font-size:var(--text-secondary)}.detail-content{padding:22px 25px 40px}.order-workbench{font-size:var(--text-body)}.workbench-tabs{display:flex;gap:4px;margin:-22px -25px 18px;padding:0 25px;border-bottom:1px solid #e3eae6;overflow:auto;background:#fff}.workbench-tabs button{border:0;border-bottom:2px solid transparent;background:transparent;padding:13px 12px;color:#70807a;font-size:var(--text-body);white-space:nowrap}.workbench-tabs button.active{border-bottom-color:#1f6657;color:#174c41;font-weight:700}.workbench-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.workbench-card{padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.workbench-card h3{display:flex;align-items:center;gap:7px;margin:0;color:#1d3f36;font-size:var(--text-section)}.workbench-card p{margin:7px 0;color:#71817b;font-size:var(--text-body);line-height:1.55}.summary-card{grid-column:span 2;background:linear-gradient(135deg,#f8fcfa,#eef6f1)}.summary-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:16px}.summary-metrics small,.summary-metrics strong{display:block}.summary-metrics small{color:#7c8c85;font-size:var(--text-caption)}.summary-metrics strong{margin-top:5px;color:#164a3e;font-size:var(--text-dialog)}.section-heading{display:flex;align-items:start;justify-content:space-between;gap:12px;margin-bottom:16px}.section-heading p{margin-bottom:0}.section-heading>b{color:#1a5e4f}.quote-no{color:#214d41;font-size:var(--text-section)}.text-btn{border:0;background:transparent;padding:5px 0;color:#236657;font-size:var(--text-body);font-weight:700}.muted{color:#81908a!important}.progress-track{height:8px;overflow:hidden;border-radius:99px;background:#e6eee9}.progress-track i{display:block;height:100%;border-radius:inherit;background:#27755f}.progress-track.fulfillment i{background:#2e779c}.data-list{display:grid;grid-template-columns:105px 1fr;gap:10px;margin:16px 0 0;font-size:var(--text-body)}.data-list dt{color:#7c8983}.data-list dd{margin:0;color:#31473f;word-break:break-word}.data-list.compact{margin-top:14px}.workbench-table-wrap{overflow:auto;margin:0 -19px}.workbench-table{width:100%;min-width:720px;border-collapse:collapse}.workbench-table th,.workbench-table td{padding:11px 14px;border-top:1px solid #edf1ef;text-align:left;font-size:var(--text-body)}.workbench-table th{background:#f7faf8;color:#7d8c86;font-size:var(--text-body)}.workbench-table td:last-child{text-align:right;font-variant-numeric:tabular-nums}.order-totals{display:grid;justify-content:end;gap:7px;margin-top:16px;color:#62736c;font-size:var(--text-body);text-align:right}.order-totals span,.order-totals strong{display:flex;justify-content:space-between;gap:28px;min-width:260px}.order-totals strong{margin-top:5px;padding-top:10px;border-top:1px solid #dfe8e3;color:#174b40;font-size:var(--text-body)}.order-totals b{font-variant-numeric:tabular-nums}.workbench-empty{display:grid;justify-items:center;padding:42px 15px;color:#82918b;text-align:center}.workbench-empty strong{margin-top:9px;color:#556961}.workbench-empty p{margin-top:4px}@media(max-width:980px){.detail-backdrop{inset:0;z-index:60}}@media(max-width:700px){.detail-modal{width:100vw}.detail-header{padding:16px 17px 20px}.detail-identity h2{font-size:var(--text-page)}.detail-content{padding:12px}.workbench-grid{grid-template-columns:1fr}.summary-card{grid-column:auto}.summary-metrics{grid-template-columns:1fr}.workbench-tabs{margin-left:-12px;margin-right:-12px;padding:0 12px}.detail-close span{display:none}.detail-close{padding:8px}.order-totals span,.order-totals strong{min-width:230px}}
</style>

<style scoped>
.purchase-navigation-link{display:inline-flex;align-items:center;gap:5px;color:#236657;font-weight:700;text-decoration:none}
.purchase-navigation-link:hover{text-decoration:underline}
</style>

<style scoped>
.receivable-cta{display:inline-flex;align-items:center;justify-content:center;margin-top:16px;padding:9px 13px;border:1px solid #1e6d59;border-radius:8px;background:#1e6d59;color:#fff;font-weight:700;text-decoration:none}
.receivable-cta:hover{background:#165744}
</style>

<style scoped>
.trade-shipment-mask{position:fixed;inset:0;z-index:150;background:#10261d77;display:grid;place-items:center}.trade-shipment-dialog{background:white;padding:24px;border-radius:14px;width:min(520px,92vw)}.trade-shipment-dialog label{display:grid;gap:8px;margin:16px 0}.trade-shipment-dialog input,.trade-shipment-dialog select,.trade-shipment-dialog textarea{padding:9px;border:1px solid #d0dfd8;border-radius:6px;font:inherit}.trade-shipment-dialog footer{display:flex;justify-content:flex-end;gap:12px}.shipment-batch-dialog{width:min(900px,94vw);max-height:90vh;overflow:auto}.shipment-batch-dialog>p{margin:8px 0;color:#526960}.shipment-atomic-note{padding:9px 12px;border-radius:8px;background:#edf5f0;color:#315c4e!important}.shipment-date-field{max-width:260px}.shipment-selected-count{font-weight:700}.shipment-batch-lines{display:grid;gap:10px;max-height:52vh;overflow:auto;padding:2px}.shipment-batch-line{padding:14px;border:1px solid #e1e9e5;border-radius:10px;background:#fbfdfc}.shipment-batch-line>header{display:flex;align-items:center;justify-content:space-between;gap:12px}.shipment-batch-line>header strong{color:#315c4e}.trade-shipment-dialog .shipment-line-toggle{display:flex;align-items:center;gap:9px;margin:0;font-weight:700}.shipment-line-toggle input{width:auto}.shipment-line-fields{display:grid;grid-template-columns:minmax(180px,1fr) minmax(150px,220px) minmax(180px,1fr);align-items:end;gap:10px}.shipment-line-fields>label{margin:10px 0}.shipment-line-fields>p{margin:0 0 18px;color:#526960}.fulfillment-header-actions{display:flex;align-items:center;gap:10px}.shipment-history{margin-top:20px;padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.shipment-history-list{display:grid;gap:10px}.shipment-history-card{padding:12px 14px;border:1px solid #e3ebe7;border-radius:10px;background:#fbfdfc}.shipment-history-head,.shipment-history-actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.shipment-history-head strong,.shipment-history-head small{display:block}.shipment-history-head small{margin-top:4px;color:#71817b}.shipment-history-items{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;color:#425b51}.shipment-history-actions{margin-top:9px}.packing-plan-panel{margin-top:20px;padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.packing-plan-empty{gap:10px;padding:50px 20px}.packing-plan-empty .btn{margin-top:5px}.packing-plan-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px}.packing-plan-toolbar>div{display:flex;align-items:center;gap:10px}.packing-status{display:inline-flex;padding:5px 9px;border-radius:999px;background:#e7f3ed;color:#1e6751;font-size:var(--text-caption);font-weight:700}.packing-status.needs_attention{background:#fff3da;color:#93620c}.packing-plan-caption{color:#71817b;font-size:var(--text-caption)}.packing-plan-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:16px}.packing-plan-summary>div{padding:12px;border:1px solid #e5ece8;border-radius:9px;background:#f8fbf9}.packing-plan-summary small,.packing-plan-summary strong{display:block}.packing-plan-summary small{color:#71817b;font-size:var(--text-caption)}.packing-plan-summary strong{margin-top:5px;color:#214e42;font-size:var(--text-body)}.packing-plan-warnings{display:flex;gap:10px;margin-bottom:16px;padding:12px 14px;border:1px solid #efd7a8;border-radius:9px;background:#fff9ed;color:#76511a}.packing-plan-warnings p{margin:4px 0 0;color:#76511a}.packing-carton-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.packing-carton-card{padding:14px;border:1px solid #e3ebe7;border-radius:10px;background:#fbfdfc}.packing-carton-card header{display:flex;align-items:start;justify-content:space-between;gap:12px}.packing-carton-card header strong,.packing-carton-card header span{display:block}.packing-carton-card header span{margin-top:4px;color:#71817b;font-size:var(--text-caption)}.packing-carton-flags{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}.packing-carton-flags span{padding:3px 7px;border-radius:999px;background:#fff3da;color:#93620c;font-size:var(--text-caption)}.packing-carton-data{display:grid;grid-template-columns:120px 1fr;gap:7px 10px;margin:14px 0 0;font-size:var(--text-body)}.packing-carton-data dt{color:#71817b}.packing-carton-data dd{margin:0;color:#31473f}.packing-carton-items{display:flex;flex-wrap:wrap;gap:7px;margin-top:13px;padding-top:10px;border-top:1px solid #e8efeb;color:#425b51;font-size:var(--text-caption)}.packing-carton-items span{padding:4px 7px;border-radius:6px;background:#edf5f0}@media(max-width:700px){.packing-plan-toolbar{align-items:stretch;flex-direction:column}.packing-plan-toolbar>div{justify-content:space-between}.packing-plan-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.packing-carton-list{grid-template-columns:1fr}.packing-carton-data{grid-template-columns:105px 1fr}.shipment-line-fields{grid-template-columns:1fr}.shipment-batch-line>header{align-items:flex-start;flex-direction:column}.fulfillment-header-actions{align-items:stretch;flex-direction:column}}
.purchase-history{margin-top:20px;padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.purchase-history-card{display:grid;grid-template-columns:1fr auto;gap:8px;margin-top:10px;padding:12px 14px;border:1px solid #e3ebe7;border-radius:10px;background:#fbfdfc}.purchase-history-card strong,.purchase-history-card small{display:block}.purchase-history-card small{margin-top:4px;color:#71817b;font-size:var(--text-caption)}.purchase-history-card>div:last-of-type{text-align:right}.purchase-history-card p{grid-column:1/-1;margin:3px 0 0;color:#526960;font-size:var(--text-caption)}.procurement-success{margin:0 0 12px;padding:10px 12px;border-radius:8px;background:#e7f5ed;color:#1e6751;font-size:var(--text-body)}
</style>
