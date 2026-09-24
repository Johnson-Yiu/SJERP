<script setup>
import TradeUnitPicker from './TradeUnitPicker.vue'
import { tradePayload, baseQuantity, tradeLabel } from '../utils/tradeUnits'
import { computed, onMounted, ref, watch } from 'vue'
import { AlertTriangle, Boxes, FileText, PackageCheck, Pencil, Truck, WalletCards, X } from 'lucide-vue-next'
import { api } from '../api'
import OperationLogPanel from './OperationLogPanel.vue'
import SupplierAllocationModal from './SupplierAllocationModal.vue'

const props = defineProps({ id: { type: [Number, String], required: true }, refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['close', 'edit', 'open-quote'])
const workbench = ref(null)
const fulfillment = ref(null)
const packingPlan = ref(null)
const activeTab = ref('overview')
const loading = ref(true)
const error = ref('')
const operationLogs = ref([])
const operationLogsLoading = ref(false)
const auditEnabled = ref(false)
const allocationItem = ref(null)

const order = computed(() => workbench.value?.order)
const tabs = computed(() => [
  ['overview', '概览'], ['items', `订单明细 (${workbench.value?.items?.length || 0})`],
  ['payments', `回款 (${workbench.value?.payments?.length || 0})`], ['fulfillment', '采购与发货'], ['inventory', `库存流水 (${workbench.value?.inventory?.length || 0})`],
  ['operation_logs', `操作日志 (${operationLogs.value.length})`],
])
const paymentPercent = computed(() => {
  const total = Number(order.value?.total_amount || 0)
  return total ? Math.min(100, Math.max(0, Number(workbench.value?.payment_summary?.paid_amount || 0) / total * 100)) : 0
})
const fulfillmentPercent = computed(() => {
  const total = Number(workbench.value?.fulfillment_summary?.ordered_quantity || 0)
  return total ? Math.min(100, Math.max(0, Number(workbench.value?.fulfillment_summary?.shipped_quantity || 0) / total * 100)) : 0
})
const itemSubtotal = computed(() => (workbench.value?.items || []).reduce((sum, item) => sum + Number(item.amount || 0), 0))

function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function date(value) { return value || '—' }
const shipmentTarget = ref(null), shipmentSku = ref(null), shipmentSaving = ref(false)
const shipmentForm = ref({})
const shipmentReversalTarget = ref(null), shipmentReversalReason = ref(''), shipmentReversalSaving = ref(false)
async function ship(item) {
  error.value = ''
  try {
    shipmentSku.value = (await api.get(`/skus/${item.sku}/`)).data
    shipmentForm.value = { quantity: item.unshipped_quantity, overage_reason: '', trade_unit: null }
    shipmentTarget.value = { ...item, historical_unit: workbench.value?.items?.find(row => row.id === item.id)?.trade_unit }
  } catch (err) { error.value = err.message }
}
async function submitShipment() {
  if (shipmentSaving.value) return
  shipmentSaving.value = true
  try {
    await api.post(`/orders/${props.id}/ship/`, { shipment_date: new Date().toLocaleDateString('en-CA'), items: [tradePayload({ ...shipmentForm.value, order_item: shipmentTarget.value.id }, null)] })
    shipmentTarget.value = null
    await load()
  } catch (err) { error.value = err.response?.data?.detail || JSON.stringify(err.response?.data || err.message) }
  finally { shipmentSaving.value = false }
}
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
  try { packingPlan.value = (await api.post(`/orders/${props.id}/packing-plan/`)).data }
  catch (err) { error.value = err.message }
}
function openSupplierAllocation(item) { allocationItem.value = item }
async function supplierAllocationSaved() { allocationItem.value = null; await load() }
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [workbenchResult, fulfillmentResult, packingResult] = await Promise.all([api.get(`/orders/${props.id}/workbench/`), api.get(`/orders/${props.id}/fulfillment/`), api.get(`/orders/${props.id}/packing-plan/`).catch(() => null), loadOperationLogs()])
    workbench.value = workbenchResult.data
    fulfillment.value = fulfillmentResult.data
    packingPlan.value = packingResult?.data || null
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
  <Teleport to="body"><div v-if="shipmentTarget" class="trade-shipment-mask"><form class="trade-shipment-dialog" @submit.prevent="submitShipment"><h3>确认发货 · {{ shipmentTarget.sku_code }}</h3><p>待发 {{ shipmentTarget.unshipped_quantity }} {{ shipmentSku?.unit }}。选择实际发货规格，库存按基础单位扣减。</p><TradeUnitPicker :line="shipmentForm" :sku="shipmentSku" :price-field="null" preserve-base-quantity :historical-unit="shipmentTarget.historical_unit" /><label>发货数量<input v-model="shipmentForm.quantity" type="number" min="0.01" step="0.01" required /></label><label v-if="baseQuantity(shipmentForm) > Number(shipmentTarget.unshipped_quantity)">超发原因<select v-model="shipmentForm.overage_reason" required><option value="">请选择</option><option value="customer_addon">客户追加</option><option value="gift_or_sample">赠品或样品</option><option value="packing_variance">包装尾差</option></select></label><p v-if="error" role="alert">{{ error }}</p><footer><button type="button" class="btn btn-secondary" @click="shipmentTarget = null">取消</button><button class="btn btn-primary" :disabled="shipmentSaving">{{ shipmentSaving ? '保存中…' : '确认发货' }}</button></footer></form></div><div v-if="shipmentReversalTarget" class="trade-shipment-mask"><form class="trade-shipment-dialog" @submit.prevent="submitShipmentReversal"><h3>冲销发货 · {{ shipmentReversalTarget.shipment_no }}</h3><p>原发货记录将保留，并生成对应的库存回收入库流水。</p><label>冲销原因<textarea v-model="shipmentReversalReason" maxlength="500" rows="4" required /></label><p v-if="error" role="alert">{{ error }}</p><footer><button type="button" class="btn btn-secondary" @click="shipmentReversalTarget = null">取消</button><button class="btn btn-primary" :disabled="shipmentReversalSaving || !shipmentReversalReason.trim()">{{ shipmentReversalSaving ? '保存中…' : '确认冲销' }}</button></footer></form></div></Teleport>
  <div class="modal-backdrop detail-backdrop" @mousedown.self="emit('close')">
    <article class="detail-modal order-workbench" role="dialog" aria-modal="true" aria-label="订单工作台">
      <div v-if="loading" class="detail-loading"><div class="spinner" /> 正在加载订单工作台…</div>
      <div v-else-if="error" class="detail-error"><AlertTriangle :size="27" /><strong>加载失败</strong><p>{{ error }}</p><button class="btn btn-secondary" @click="load">重试</button></div>
      <template v-else>
        <header class="detail-header">
          <div class="detail-nav"><div class="detail-nav-start"><button class="detail-close" aria-label="关闭订单详情" @click="emit('close')"><X :size="18" /> <span>关闭</span></button><span>订单工作台 · 履约与回款</span></div><div class="detail-actions"><button class="btn btn-secondary" @click="emit('edit')"><Pencil :size="14" /> 编辑订单</button><button class="detail-close" aria-label="关闭订单详情" @click="emit('close')"><X :size="18" /> <span>关闭</span></button></div></div>
          <div class="detail-identity"><div><p class="detail-subtitle">{{ order.customer_name }} · 下单于 {{ date(order.order_date) }}</p><h2>{{ order.order_no }}</h2><small>预计交期：{{ date(order.expected_ship_date) }}</small></div><span class="detail-badge">{{ order.status_display }}</span></div>
        </header>
        <main class="detail-content">
          <nav class="workbench-tabs" aria-label="订单工作台分页"><button v-for="tab in tabs" :key="tab[0]" :class="{ active: activeTab === tab[0] }" @click="activeTab = tab[0]">{{ tab[1] }}</button></nav>

          <section v-if="activeTab === 'overview'" class="workbench-grid">
            <article class="workbench-card summary-card"><h3><PackageCheck :size="18" /> 订单概览</h3><div class="summary-metrics"><div><small>订单总额</small><strong>{{ order.currency }} {{ money(order.total_amount) }}</strong></div><div><small>已收款</small><strong>{{ order.currency }} {{ money(workbench.payment_summary.paid_amount) }}</strong></div><div><small>待收款</small><strong>{{ order.currency }} {{ money(workbench.payment_summary.balance_amount) }}</strong></div></div></article>
            <article class="workbench-card"><div class="section-heading"><div><h3><FileText :size="16" /> 来源报价</h3><p>保留成交时采用的报价版本，方便回溯。</p></div></div><template v-if="workbench.source_quote"><strong class="quote-no">{{ workbench.source_quote.quote_no }}</strong><p>{{ workbench.source_quote.status_display }} · {{ workbench.source_quote.currency }} {{ money(workbench.source_quote.total_amount) }}</p><button class="text-btn" @click="emit('open-quote', workbench.source_quote.id)">查看报价工作台</button></template><p v-else class="muted">该订单未关联来源报价。</p></article>
            <article class="workbench-card"><div class="section-heading"><div><h3><WalletCards :size="16" /> 回款进度</h3><p>包含已确认回款与预收核销，扣除客户退款。</p></div><b>{{ paymentPercent.toFixed(0) }}%</b></div><div class="progress-track"><i :style="{ width: `${paymentPercent}%` }" /></div><dl class="data-list compact"><dt>应收计划</dt><dd>{{ order.currency }} {{ money(workbench.payment_summary.planned_amount) }}</dd><dt>已收金额</dt><dd>{{ order.currency }} {{ money(workbench.payment_summary.paid_amount) }}</dd><dt>待收金额</dt><dd>{{ order.currency }} {{ money(workbench.payment_summary.balance_amount) }}</dd><dt>分配商品成本</dt><dd>¥ {{ money(workbench.profit_summary?.purchase_base_rmb) }}</dd><dt>分摊附加费用</dt><dd>¥ {{ money(workbench.profit_summary?.purchase_additional_rmb) }}</dd><dt>预估毛利</dt><dd>¥ {{ money(workbench.profit_summary?.estimated_gross_profit_rmb) }}</dd></dl></article>
            <article class="workbench-card"><div class="section-heading"><div><h3><Truck :size="16" /> 履约进度</h3><p>依据关联的销售出库流水计算。</p></div><b>{{ fulfillmentPercent.toFixed(0) }}%</b></div><div class="progress-track fulfillment"><i :style="{ width: `${fulfillmentPercent}%` }" /></div><dl class="data-list compact"><dt>订单数量</dt><dd>{{ workbench.fulfillment_summary.ordered_quantity }}</dd><dt>已出库</dt><dd>{{ workbench.fulfillment_summary.shipped_quantity }}</dd><dt>待出库</dt><dd>{{ workbench.fulfillment_summary.remaining_quantity }}</dd></dl></article>
          </section>

           <section v-else-if="activeTab === 'items'" class="workbench-card"><div class="section-heading"><div><h3><Boxes :size="16" /> 订单明细</h3><p>订单保存时固定销售型号、描述、单位和内部名称快照；本次采购供应商可单独分配。</p></div><strong>{{ workbench.items.length }} 项</strong></div><div class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>Model</th><th>内部名称 / SKU Code</th><th>Description</th><th>本次供应商</th><th>数量</th><th>单位</th><th>成交单价</th><th>成本单价</th><th>小计</th></tr></thead><tbody><tr v-for="item in workbench.items" :key="item.id"><td>{{ item.sales_model || item.model || '未设置' }}</td><td>{{ item.display_name || item.product_name }}<small>{{ item.sku_code }}</small></td><td>{{ item.description || '—' }}</td><td>{{ item.supplier_name || '未分配' }}<small>{{ item.supplier_sku_code || '' }}</small></td><td>{{ item.trade_quantity ?? item.quantity }}<small v-if="item.trade_unit">{{ item.quantity }} {{ item.trade_snapshot.base_unit }}</small></td><td>{{ tradeLabel(item) || '—' }}</td><td>{{ order.currency }} {{ money(item.trade_unit_price ?? item.unit_price) }}</td><td>{{ order.currency }} {{ money(item.cost_price) }}</td><td>{{ order.currency }} {{ money(item.amount) }}</td></tr></tbody></table></div><div class="order-totals"><span>商品小计 <b>{{ order.currency }} {{ money(itemSubtotal) }}</b></span><span>运费 <b>{{ order.currency }} {{ money(order.shipping_fee) }}</b></span><span>折扣 / 优惠 <b>- {{ order.currency }} {{ money(order.discount) }}</b></span><strong>订单总计 <b>{{ order.currency }} {{ money(order.total_amount) }}</b></strong></div></section>

          <section v-else-if="activeTab === 'payments'" class="workbench-card"><div class="section-heading"><div><h3><WalletCards :size="16" /> 回款流水</h3><p>确认付款后，订单的已收金额会自动更新。</p></div><strong>{{ workbench.payments.length }} 条</strong></div><div v-if="!workbench.payments.length" class="workbench-empty"><WalletCards :size="28" /><strong>暂无关联流水</strong><p>可在财务流水中关联此订单，记录定金与尾款。</p></div><div v-else class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>日期</th><th>流水号</th><th>类型</th><th>分类</th><th>状态</th><th>金额</th></tr></thead><tbody><tr v-for="payment in workbench.payments" :key="payment.id"><td>{{ date(payment.transaction_date) }}</td><td>{{ payment.transaction_no }}</td><td>{{ payment.direction_display }}</td><td>{{ payment.category }}</td><td><span class="status" :class="payment.status">{{ payment.status_display }}</span></td><td>{{ payment.currency }} {{ money(payment.amount) }}</td></tr></tbody></table></div></section>

          <section v-else-if="activeTab === 'inventory'" class="workbench-card"><div class="section-heading"><div><h3><Truck :size="16" /> 履约流水</h3><p>关联此订单的出入库动作会在这里集中展示。</p></div><strong>{{ workbench.inventory.length }} 条</strong></div><div v-if="!workbench.inventory.length" class="workbench-empty"><Truck :size="28" /><strong>暂无出入库流水</strong><p>在库存流水中关联本订单后，履约进度会自动更新。</p></div><div v-else class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>日期</th><th>流水号</th><th>类型</th><th>SKU</th><th>数量</th><th>仓库</th></tr></thead><tbody><tr v-for="movement in workbench.inventory" :key="movement.id"><td>{{ date(movement.movement_date) }}</td><td>{{ movement.movement_no }}</td><td>{{ movement.type_display }}</td><td>{{ movement.sku_code }}</td><td>{{ movement.signed_quantity }}</td><td>{{ movement.warehouse }}</td></tr></tbody></table></div></section>
          <OperationLogPanel v-else :logs="operationLogs" :loading="operationLogsLoading" :enabled="auditEnabled" />
        </main>
      </template>
      <section v-if="!loading && !error && activeTab === 'payments' && workbench?.advance_allocations?.length" class="workbench-card"><h3>预收款核销记录</h3><p>以下金额已计入本订单回款；原始收款可在财务流水中查看。</p><div class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>原始收款日期</th><th>流水号</th><th>核销金额</th><th>状态</th></tr></thead><tbody><tr v-for="row in workbench.advance_allocations" :key="row.id"><td>{{ row.transaction_date }}</td><td>{{ row.transaction_no }}</td><td>{{ row.currency }} {{ money(row.amount) }}</td><td>{{ row.is_active ? '已核销' : '已撤回' }}</td></tr></tbody></table></div></section>
       <section v-if="!loading && !error && activeTab === 'fulfillment'" class="fulfillment-panel"><div class="section-heading"><div><h3>采购与发货</h3><p>订单确认后会预留现货；缺口按采购、到货和在途数量持续更新。供应商选择只作用于本订单行，不改写 SKU 主档。</p></div></div><div class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>SKU</th><th>本次供应商</th><th>订单</th><th>预留</th><th>已采购</th><th>已到 / 在途</th><th>已发 / 待发</th><th></th></tr></thead><tbody><tr v-for="item in fulfillment?.items || []" :key="item.id"><td>{{ item.sku_code }}<small>基础单位：{{ item.base_unit }}</small></td><td>{{ item.supplier_name || '未分配' }}<small v-if="item.supplier_sku_code">{{ item.supplier_sku_code }}</small></td><td>{{ item.quantity }}</td><td>{{ item.allocated_quantity }}</td><td>{{ item.purchased_quantity }}</td><td>{{ item.arrived_quantity }} / {{ item.in_transit_quantity }}</td><td>{{ item.shipped_quantity }} / {{ item.unshipped_quantity }}</td><td><button class="text-btn" :disabled="['cancelled', 'completed'].includes(order.status)" @click="openSupplierAllocation(item)">{{ item.supplier_name ? '更换供应商' : '选择供应商' }}</button><button class="text-btn" :disabled="Number(item.unshipped_quantity) <= 0 || ['draft', 'cancelled', 'completed'].includes(order.status)" @click="ship(item)">确认发货</button></td></tr></tbody></table></div><p v-if="!(fulfillment?.purchase_orders || []).length" class="muted">尚未创建采购单；选择供应商后，按待采购数量建立采购单会优先继承订单行的 Supplier SKU。</p><div class="shipment-history"><div class="section-heading"><div><h3>发货记录</h3><p>已确认的发货单可以整单冲销；包含超发或增补的发货单需按后续业务处理。</p></div><strong>{{ (fulfillment?.shipments || []).length }} 条</strong></div><div v-if="!(fulfillment?.shipments || []).length" class="workbench-empty"><Truck :size="28" /><strong>暂无发货记录</strong></div><div v-else class="shipment-history-list"><article v-for="shipment in fulfillment.shipments" :key="shipment.id" class="shipment-history-card"><div class="shipment-history-head"><div><strong>{{ shipment.shipment_no }}</strong><small>{{ date(shipment.shipment_date) }}</small></div><span class="status" :class="shipment.status">{{ shipment.status === 'cancelled' ? '已冲销' : shipment.status === 'confirmed' ? '已确认' : shipment.status }}</span></div><div class="shipment-history-items"><span v-for="line in shipment.items" :key="line.id">{{ line.sku_code }} × {{ line.quantity }}</span></div><div class="shipment-history-actions"><span v-if="shipment.has_overage" class="muted">包含超发/增补，暂不能直接冲销</span><button v-else-if="shipment.status === 'confirmed'" class="text-btn" @click="openShipmentReversal(shipment)">冲销</button><span v-else-if="shipment.status === 'cancelled'" class="muted">已冲销</span><span v-else class="muted">暂不可操作</span></div></article></div></div></section>
     </article>
     <SupplierAllocationModal v-if="allocationItem" :order-id="props.id" :order-item="allocationItem" @close="allocationItem = null" @saved="supplierAllocationSaved" />
  </div>
</template>

<style scoped>
.detail-backdrop{inset:0 0 0 248px;z-index:25;place-items:stretch end;padding:0;background:#0b221d66;backdrop-filter:blur(2px)}.detail-modal{height:100vh;width:min(1080px,100%);background:#f6f8f5;box-shadow:-24px 0 70px #06191452;overflow:auto;overscroll-behavior:contain}.detail-loading,.detail-error{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#71817b}.detail-error strong{color:#9d4444}.detail-error p{font-size:var(--text-body)}.detail-header{position:relative;overflow:hidden;padding:20px 28px 24px;background:#123c36;color:#fff}.detail-header:after{position:absolute;top:-140px;right:-80px;width:300px;height:300px;border:60px solid #ffffff08;border-radius:50%;content:''}.detail-nav,.detail-identity{position:relative;z-index:1}.detail-nav,.detail-nav-start{display:flex;align-items:center}.detail-nav{justify-content:space-between;color:#91b6aa;font-size:var(--text-body);letter-spacing:.12em;text-transform:uppercase}.detail-nav-start{gap:10px}.detail-actions{display:flex;align-items:center;gap:8px}.detail-actions .btn{padding:7px 11px;color:#fff;font-size:var(--text-body);letter-spacing:0;text-transform:none;background:#ffffff12;border-color:#ffffff28}.detail-close{display:flex;align-items:center;gap:7px;min-height:38px;padding:8px 11px;border:1px solid #ffffff45;border-radius:9px;background:#ffffff1a;color:#fff;font-size:var(--text-body);font-weight:700;letter-spacing:0;text-transform:none}.detail-identity{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-top:23px}.detail-subtitle{margin:0;color:#9cc0b5;font-size:var(--text-caption)}.detail-identity h2{margin:5px 0 0;font-size:var(--text-page)}.detail-identity small{color:#b6d3ca;font-size:var(--text-caption)}.detail-badge{padding:6px 10px;border:1px solid #ffffff22;border-radius:20px;background:#ffffff14;font-size:var(--text-secondary)}.detail-content{padding:22px 25px 40px}.order-workbench{font-size:var(--text-body)}.workbench-tabs{display:flex;gap:4px;margin:-22px -25px 18px;padding:0 25px;border-bottom:1px solid #e3eae6;overflow:auto;background:#fff}.workbench-tabs button{border:0;border-bottom:2px solid transparent;background:transparent;padding:13px 12px;color:#70807a;font-size:var(--text-body);white-space:nowrap}.workbench-tabs button.active{border-bottom-color:#1f6657;color:#174c41;font-weight:700}.workbench-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.workbench-card{padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.workbench-card h3{display:flex;align-items:center;gap:7px;margin:0;color:#1d3f36;font-size:var(--text-section)}.workbench-card p{margin:7px 0;color:#71817b;font-size:var(--text-body);line-height:1.55}.summary-card{grid-column:span 2;background:linear-gradient(135deg,#f8fcfa,#eef6f1)}.summary-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:16px}.summary-metrics small,.summary-metrics strong{display:block}.summary-metrics small{color:#7c8c85;font-size:var(--text-caption)}.summary-metrics strong{margin-top:5px;color:#164a3e;font-size:var(--text-dialog)}.section-heading{display:flex;align-items:start;justify-content:space-between;gap:12px;margin-bottom:16px}.section-heading p{margin-bottom:0}.section-heading>b{color:#1a5e4f}.quote-no{color:#214d41;font-size:var(--text-section)}.text-btn{border:0;background:transparent;padding:5px 0;color:#236657;font-size:var(--text-body);font-weight:700}.muted{color:#81908a!important}.progress-track{height:8px;overflow:hidden;border-radius:99px;background:#e6eee9}.progress-track i{display:block;height:100%;border-radius:inherit;background:#27755f}.progress-track.fulfillment i{background:#2e779c}.data-list{display:grid;grid-template-columns:105px 1fr;gap:10px;margin:16px 0 0;font-size:var(--text-body)}.data-list dt{color:#7c8983}.data-list dd{margin:0;color:#31473f;word-break:break-word}.data-list.compact{margin-top:14px}.workbench-table-wrap{overflow:auto;margin:0 -19px}.workbench-table{width:100%;min-width:720px;border-collapse:collapse}.workbench-table th,.workbench-table td{padding:11px 14px;border-top:1px solid #edf1ef;text-align:left;font-size:var(--text-body)}.workbench-table th{background:#f7faf8;color:#7d8c86;font-size:var(--text-body)}.workbench-table td:last-child{text-align:right;font-variant-numeric:tabular-nums}.order-totals{display:grid;justify-content:end;gap:7px;margin-top:16px;color:#62736c;font-size:var(--text-body);text-align:right}.order-totals span,.order-totals strong{display:flex;justify-content:space-between;gap:28px;min-width:260px}.order-totals strong{margin-top:5px;padding-top:10px;border-top:1px solid #dfe8e3;color:#174b40;font-size:var(--text-body)}.order-totals b{font-variant-numeric:tabular-nums}.workbench-empty{display:grid;justify-items:center;padding:42px 15px;color:#82918b;text-align:center}.workbench-empty strong{margin-top:9px;color:#556961}.workbench-empty p{margin-top:4px}@media(max-width:980px){.detail-backdrop{inset:0;z-index:60}}@media(max-width:700px){.detail-modal{width:100vw}.detail-header{padding:16px 17px 20px}.detail-identity h2{font-size:var(--text-page)}.detail-content{padding:12px}.workbench-grid{grid-template-columns:1fr}.summary-card{grid-column:auto}.summary-metrics{grid-template-columns:1fr}.workbench-tabs{margin-left:-12px;margin-right:-12px;padding:0 12px}.detail-close span{display:none}.detail-close{padding:8px}.order-totals span,.order-totals strong{min-width:230px}}
</style>

<style scoped>
.trade-shipment-mask{position:fixed;inset:0;z-index:150;background:#10261d77;display:grid;place-items:center}.trade-shipment-dialog{background:white;padding:24px;border-radius:14px;width:min(520px,92vw)}.trade-shipment-dialog label{display:grid;gap:8px;margin:16px 0}.trade-shipment-dialog input,.trade-shipment-dialog select,.trade-shipment-dialog textarea{padding:9px;border:1px solid #d0dfd8;border-radius:6px;font:inherit}.trade-shipment-dialog footer{display:flex;justify-content:flex-end;gap:12px}.shipment-history{margin-top:20px;padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.shipment-history-list{display:grid;gap:10px}.shipment-history-card{padding:12px 14px;border:1px solid #e3ebe7;border-radius:10px;background:#fbfdfc}.shipment-history-head,.shipment-history-actions{display:flex;align-items:center;justify-content:space-between;gap:12px}.shipment-history-head strong,.shipment-history-head small{display:block}.shipment-history-head small{margin-top:4px;color:#71817b}.shipment-history-items{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;color:#425b51}.shipment-history-actions{margin-top:9px}
</style>
