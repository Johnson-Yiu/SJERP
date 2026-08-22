<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowDownUp, Database, PackageSearch, RefreshCw, Search, X } from 'lucide-vue-next'
import { api, listData } from '../api'

const rows = ref([]), query = ref(''), loading = ref(true), error = ref('')
const sortKey = ref('sku'), sortDirection = ref('asc')
const selectedSku = ref(null), detail = ref(null), detailLoading = ref(false), detailError = ref('')
const columns = [
  ['sku', 'SKU'], ['product_name', '产品'], ['actual_quantity', '实际'], ['reserved_quantity', '预留'],
  ['available_quantity', '可用'], ['in_transit_quantity', '在途'], ['to_procure_quantity', '待采购'], ['status', '状态'],
]
const filteredRows = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  if (!keyword) return rows.value
  return rows.value.filter(row => [row.sku, row.product_name, row.product_code, row.specification].some(value => String(value || '').toLowerCase().includes(keyword)))
})
const visibleRows = computed(() => [...filteredRows.value].sort((left, right) => {
  const leftValue = sortValue(left, sortKey.value), rightValue = sortValue(right, sortKey.value)
  const comparison = typeof leftValue === 'number' && typeof rightValue === 'number' ? leftValue - rightValue : String(leftValue).localeCompare(String(rightValue), 'zh-CN')
  return sortDirection.value === 'asc' ? comparison : -comparison
}))
const totalSkus = computed(() => filteredRows.value.length)
const totalQuantity = computed(() => filteredRows.value.reduce((sum, row) => sum + Number(row.actual_quantity ?? row.stock_quantity ?? 0), 0))
const totalAvailable = computed(() => filteredRows.value.reduce((sum, row) => sum + Number(row.available_quantity ?? row.stock_quantity ?? 0), 0))
const totalInTransit = computed(() => filteredRows.value.reduce((sum, row) => sum + Number(row.in_transit_quantity || 0), 0))
const lowOrEmptyCount = computed(() => filteredRows.value.filter(row => row.has_anomaly || Number(row.available_quantity ?? row.stock_quantity ?? 0) <= 0).length)
const formatQuantity = value => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(Number(value || 0))
function sortValue(row, key) {
  if (key === 'status') return stockState(row).label
  return ['actual_quantity', 'reserved_quantity', 'available_quantity', 'in_transit_quantity', 'to_procure_quantity'].includes(key) ? Number(row[key] ?? 0) : row[key] ?? ''
}
function toggleSort(key) { if (sortKey.value === key) sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'; else { sortKey.value = key; sortDirection.value = 'asc' } }
function sortLabel(key) { return sortKey.value === key ? (sortDirection.value === 'asc' ? '升序' : '降序') : '未排序' }
function stockState(row) {
  const quantity = Number(row.available_quantity ?? row.stock_quantity ?? 0)
  if (row.has_anomaly || quantity < 0) return { label: '需处理', className: 'negative' }
  if (quantity === 0) return { label: '无库存', className: 'empty-stock' }
  return { label: '有库存', className: 'positive-stock' }
}
async function load() {
  loading.value = true; error.value = ''
  try { rows.value = listData(await api.get('/skus/', { params: { include_inactive: 1 } })) }
  catch (requestError) { error.value = requestError.message || '库存数据加载失败，请稍后重试。' }
  finally { loading.value = false }
}
async function openDetail(row) {
  selectedSku.value = row; detail.value = null; detailError.value = ''; detailLoading.value = true
  try { detail.value = (await api.get(`/skus/${row.id}/inventory-detail/`)).data }
  catch (requestError) { detailError.value = requestError.response?.data?.detail || requestError.message || '库存详情加载失败。' }
  finally { detailLoading.value = false }
}
function closeDetail() { selectedSku.value = null; detail.value = null }
onMounted(load)
</script>

<template>
  <div class="inventory-page">
    <div class="page-head"><div><h2>库存</h2><p>按 SKU 汇总库存数量，数据会随出入库流水实时更新。</p></div><button class="btn btn-secondary" :disabled="loading" @click="load"><RefreshCw :size="16" :class="{ spinning: loading }" /> 刷新数据</button></div>
    <section class="inventory-summary" aria-label="库存概览"><article><span>SKU 数量</span><strong>{{ totalSkus }}</strong><small>当前筛选范围</small></article><article><span>实际库存</span><strong>{{ formatQuantity(totalQuantity) }}</strong><small>所有 SKU 实物合计</small></article><article><span>可用库存</span><strong>{{ formatQuantity(totalAvailable) }}</strong><small>扣除订单预留后</small></article><article><span>在途采购</span><strong>{{ formatQuantity(totalInTransit) }}</strong><small>已下单未到货</small></article><article class="attention"><span>待关注</span><strong>{{ lowOrEmptyCount }}</strong><small>无可用库存或异常</small></article></section>
    <div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索 SKU、产品、规格..." /></div></div>
    <section class="panel"><div v-if="loading" class="loading"><div class="spinner" /></div><div v-else-if="error" class="empty"><PackageSearch :size="32" /><h3>无法加载库存</h3><p>{{ error }}</p></div><div v-else-if="!visibleRows.length" class="empty"><Database :size="32" /><h3>没有匹配的库存记录</h3><p>请调整搜索条件，或先创建 SKU 并登记入库。</p></div><div v-else class="table-wrap"><table class="data-table inventory-table"><thead><tr><th v-for="column in columns" :key="column[0]"><button class="sort-header" :aria-label="`${column[1]}：${sortLabel(column[0])}`" @click="toggleSort(column[0])">{{ column[1] }}<ArrowDownUp :size="13" :class="{ active: sortKey === column[0], desc: sortKey === column[0] && sortDirection === 'desc' }" /></button></th></tr></thead><tbody><tr v-for="row in visibleRows" :key="row.id" class="inventory-row" tabindex="0" @click="openDetail(row)" @keyup.enter="openDetail(row)"><td class="primary-cell">{{ row.sku }}</td><td>{{ row.product_name }}</td><td>{{ formatQuantity(row.actual_quantity ?? row.stock_quantity) }}</td><td>{{ formatQuantity(row.reserved_quantity) }}</td><td class="stock-quantity" :class="stockState(row).className">{{ formatQuantity(row.available_quantity ?? row.stock_quantity) }}</td><td>{{ formatQuantity(row.in_transit_quantity) }}</td><td>{{ formatQuantity(row.to_procure_quantity) }}</td><td><span class="stock-status" :class="stockState(row).className">{{ stockState(row).label }}</span></td></tr></tbody></table></div></section>
    <div v-if="selectedSku" class="detail-backdrop" @mousedown.self="closeDetail"><aside class="sku-detail" aria-label="库存详情"><header><div><small>SKU 库存详情</small><h2>{{ selectedSku.sku }}</h2><p>{{ selectedSku.product_name }}</p></div><button class="icon-btn" aria-label="关闭库存详情" @click="closeDetail"><X :size="18" /></button></header><div v-if="detailLoading" class="detail-state"><div class="spinner" /> 正在加载关联记录…</div><div v-else-if="detailError" class="detail-state error"><strong>加载失败</strong><p>{{ detailError }}</p></div><main v-else class="detail-content"><section><h3>采购记录</h3><p v-if="!detail?.purchases?.length" class="muted">暂无关联采购记录。</p><table v-else><thead><tr><th>采购单</th><th>供应商</th><th>采购 / 到货</th><th>状态</th></tr></thead><tbody><tr v-for="purchase in detail.purchases" :key="purchase.id"><td>{{ purchase.purchase_no }}</td><td>{{ purchase.supplier_name }}</td><td>{{ formatQuantity(purchase.quantity) }} / {{ formatQuantity(purchase.received_quantity) }}</td><td>{{ purchase.status_display }}</td></tr></tbody></table></section><section><h3>出库记录</h3><p v-if="!detail?.shipments?.length" class="muted">暂无关联出库记录。</p><table v-else><thead><tr><th>发货单</th><th>订单</th><th>日期</th><th>数量</th></tr></thead><tbody><tr v-for="shipment in detail.shipments" :key="shipment.id"><td>{{ shipment.shipment_no }}</td><td>{{ shipment.order_no }}</td><td>{{ shipment.shipment_date }}</td><td>{{ formatQuantity(shipment.quantity) }}</td></tr></tbody></table></section><section><h3>关联订单</h3><p v-if="!detail?.orders?.length" class="muted">暂无关联订单记录。</p><table v-else><thead><tr><th>订单号</th><th>客户</th><th>订单 / 已发</th><th>状态</th></tr></thead><tbody><tr v-for="order in detail.orders" :key="order.id"><td>{{ order.order_no }}</td><td>{{ order.customer_name }}</td><td>{{ formatQuantity(order.quantity) }} / {{ formatQuantity(order.shipped_quantity) }}</td><td>{{ order.status_display }}</td></tr></tbody></table></section></main></aside></div>
  </div>
</template>

<style scoped>
.sort-header{display:inline-flex;align-items:center;gap:5px;border:0;padding:0;background:transparent;color:inherit;font:inherit;font-weight:inherit;cursor:pointer}.sort-header svg{color:#a2b0aa}.sort-header svg.active{color:#1c6756}.sort-header svg.desc{transform:rotate(180deg)}.inventory-row{cursor:pointer}.inventory-row:hover td{background:#f0f7f3}.detail-backdrop{position:fixed;inset:0 0 0 248px;z-index:50;display:grid;justify-items:end;background:#0b221d66;backdrop-filter:blur(2px)}.sku-detail{width:min(720px,100%);height:100vh;overflow:auto;background:#f6f8f5;box-shadow:-24px 0 70px #06191452}.sku-detail header{display:flex;justify-content:space-between;align-items:start;padding:24px 27px;background:#123c36;color:white}.sku-detail header small{color:#9cc0b5;font-size:11px}.sku-detail h2{margin:5px 0;font-size:25px}.sku-detail p{margin:0;color:#bfd4cc;font-size:13px}.detail-content{display:grid;gap:14px;padding:20px}.detail-content section{overflow:hidden;border:1px solid #e0e8e4;border-radius:12px;background:#fff}.detail-content h3{margin:0;padding:15px 16px;border-bottom:1px solid #e8eeeb;color:#24483e;font-size:15px}.detail-content table{width:100%;border-collapse:collapse}.detail-content th,.detail-content td{padding:10px 13px;border-top:1px solid #edf1ef;text-align:left;color:#42584f;font-size:12px}.detail-content th{border-top:0;background:#f8faf9;color:#7b8b84;font-size:11px}.muted{padding:18px!important;color:#81908a!important}.detail-state{display:grid;place-items:center;gap:11px;padding:70px 20px;color:#71817b}.detail-state.error strong{color:#a44343}@media(max-width:980px){.detail-backdrop{inset:0}.sku-detail{width:min(720px,100vw)}}
</style>
