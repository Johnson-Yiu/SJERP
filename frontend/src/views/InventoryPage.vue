<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowDownUp, Database, PackageSearch, RefreshCw, Search, X } from 'lucide-vue-next'
import { api, listData } from '../api'

const rows = ref([]), query = ref(''), loading = ref(true), error = ref('')
const sortKey = ref('sku'), sortDirection = ref('asc')
const selectedSku = ref(null), detail = ref(null), detailLoading = ref(false), detailError = ref('')
const detailTab = ref('purchases'), detailQuery = ref(''), detailSortKey = ref(''), detailSortDirection = ref('asc')
const columns = [
  ['sku', 'SKU'], ['product_name', '产品'], ['actual_quantity', '实际'], ['reserved_quantity', '预留'],
  ['available_quantity', '可用'], ['in_transit_quantity', '在途'], ['to_procure_quantity', '待采购'], ['status', '状态'],
]
const detailTabs = [
  { key: 'purchases', title: '采购记录', empty: '暂无关联采购记录。', columns: [{ key: 'purchase_no', label: '采购单' }, { key: 'supplier_name', label: '供应商' }, { key: 'quantity', secondaryKey: 'received_quantity', label: '采购 / 到货', type: 'quantity' }, { key: 'status_display', label: '状态' }] },
  { key: 'shipments', title: '出库记录', empty: '暂无关联出库记录。', columns: [{ key: 'shipment_no', label: '发货单' }, { key: 'order_no', label: '订单' }, { key: 'shipment_date', label: '日期', type: 'date' }, { key: 'quantity', label: '数量', type: 'number' }] },
  { key: 'orders', title: '关联订单', empty: '暂无关联订单记录。', columns: [{ key: 'order_no', label: '订单号' }, { key: 'customer_name', label: '客户' }, { key: 'quantity', secondaryKey: 'shipped_quantity', label: '订单 / 已发', type: 'quantity' }, { key: 'status_display', label: '状态' }] },
]
const activeDetailTab = computed(() => detailTabs.find(tab => tab.key === detailTab.value) || detailTabs[0])
const detailRows = computed(() => detail.value?.[activeDetailTab.value.key] || [])
const visibleDetailRows = computed(() => {
  const keyword = detailQuery.value.trim().toLowerCase()
  const rows = keyword ? detailRows.value.filter(row => activeDetailTab.value.columns.some(column => String(row[column.key] ?? '').toLowerCase().includes(keyword))) : detailRows.value
  if (!detailSortKey.value) return rows
  const column = activeDetailTab.value.columns.find(item => item.key === detailSortKey.value)
  return [...rows].sort((left, right) => {
    const first = detailSortValue(left, column), second = detailSortValue(right, column)
    const comparison = typeof first === 'number' && typeof second === 'number' ? first - second : String(first).localeCompare(String(second), 'zh-CN', { numeric: true, sensitivity: 'base' })
    return detailSortDirection.value === 'asc' ? comparison : -comparison
  })
})
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
function detailSortValue(row, column) {
  if (['number', 'quantity'].includes(column?.type)) return Number(row[column.key] || 0)
  if (column?.type === 'date') return new Date(row[column.key] || 0).getTime()
  return row[column?.key] ?? ''
}
function toggleDetailSort(key) { if (detailSortKey.value === key) detailSortDirection.value = detailSortDirection.value === 'asc' ? 'desc' : 'asc'; else { detailSortKey.value = key; detailSortDirection.value = 'asc' } }
function detailSortLabel(key) { return detailSortKey.value === key ? (detailSortDirection.value === 'asc' ? '升序' : '降序') : '未排序' }
function formatDetailCell(row, column) {
  if (column.type === 'quantity') return `${formatQuantity(row[column.key])} / ${formatQuantity(row[column.secondaryKey])}`
  if (column.type === 'number') return formatQuantity(row[column.key])
  return row[column.key] || '—'
}
function selectDetailTab(key) { detailTab.value = key; detailQuery.value = ''; detailSortKey.value = ''; detailSortDirection.value = 'asc' }
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
  selectedSku.value = row; detail.value = null; detailError.value = ''; detailLoading.value = true; selectDetailTab('purchases')
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
    <div v-if="selectedSku" class="detail-backdrop" @mousedown.self="closeDetail"><aside class="sku-detail" aria-label="库存详情"><header><div><small>SKU 库存详情</small><h2>{{ selectedSku.sku }}</h2><p>{{ selectedSku.product_name }}</p></div><button class="icon-btn" aria-label="关闭库存详情" @click="closeDetail"><X :size="18" /></button><div class="detail-metrics"><div><small>实际库存</small><strong>{{ formatQuantity(selectedSku.actual_quantity ?? selectedSku.stock_quantity) }}</strong></div><div><small>已预留</small><strong>{{ formatQuantity(selectedSku.reserved_quantity) }}</strong></div><div><small>可用库存</small><strong>{{ formatQuantity(selectedSku.available_quantity ?? selectedSku.stock_quantity) }}</strong></div><div><small>在途采购</small><strong>{{ formatQuantity(selectedSku.in_transit_quantity) }}</strong></div><div><small>待采购</small><strong>{{ formatQuantity(selectedSku.to_procure_quantity) }}</strong></div><div><small>库存状态</small><strong :class="stockState(selectedSku).className">{{ stockState(selectedSku).label }}</strong></div></div></header><div v-if="detailLoading" class="detail-state"><div class="spinner" /> 正在加载关联记录…</div><div v-else-if="detailError" class="detail-state error"><strong>加载失败</strong><p>{{ detailError }}</p></div><main v-else class="detail-content"><nav class="detail-tabs" aria-label="库存关联记录"><button v-for="tab in detailTabs" :key="tab.key" :class="{ active: detailTab === tab.key }" @click="selectDetailTab(tab.key)">{{ tab.title }} <span>{{ detail?.[tab.key]?.length || 0 }}</span></button></nav><section class="detail-section"><div class="detail-section-head"><div><h3>{{ activeDetailTab.title }}</h3><p>支持按关键词筛选，点击列标题切换排序。</p></div><label class="detail-filter"><Search :size="15" /><input v-model.trim="detailQuery" :placeholder="`筛选${activeDetailTab.title}...`" /><span v-if="detailQuery">{{ visibleDetailRows.length }} / {{ detailRows.length }}</span></label></div><p v-if="!visibleDetailRows.length" class="muted">{{ detailQuery ? `未找到匹配的${activeDetailTab.title}。` : activeDetailTab.empty }}</p><div v-else class="detail-table-wrap"><table><thead><tr><th v-for="column in activeDetailTab.columns" :key="column.key"><button class="detail-sort-header" :aria-label="`${column.label}：${detailSortLabel(column.key)}`" @click="toggleDetailSort(column.key)">{{ column.label }}<ArrowDownUp :size="12" :class="{ active: detailSortKey === column.key, desc: detailSortKey === column.key && detailSortDirection === 'desc' }" /></button></th></tr></thead><tbody><tr v-for="(row, index) in visibleDetailRows" :key="row.id || index"><td v-for="column in activeDetailTab.columns" :key="column.key">{{ formatDetailCell(row, column) }}</td></tr></tbody></table></div></section></main></aside></div>
  </div>
</template>

<style scoped>
.sort-header,.detail-sort-header{display:inline-flex;align-items:center;gap:5px;border:0;padding:0;background:transparent;color:inherit;font:inherit;font-weight:inherit;cursor:pointer}.sort-header svg,.detail-sort-header svg{color:#a2b0aa}.sort-header svg.active,.detail-sort-header svg.active{color:#1c6756}.sort-header svg.desc,.detail-sort-header svg.desc{transform:rotate(180deg)}.inventory-row{cursor:pointer}.inventory-row:hover td{background:#f0f7f3}.detail-backdrop{position:fixed;inset:0 0 0 248px;z-index:50;display:grid;justify-items:end;background:#0b221d66;backdrop-filter:blur(2px)}.sku-detail{width:min(720px,100%);height:100vh;overflow:auto;background:#f6f8f5;box-shadow:-24px 0 70px #06191452}.sku-detail header{position:relative;padding:24px 27px;background:#123c36;color:white}.sku-detail header .icon-btn{position:absolute;top:22px;right:27px}.sku-detail header small{color:#9cc0b5;font-size:11px}.sku-detail h2{margin:5px 0;font-size:25px}.sku-detail p{margin:0;color:#bfd4cc;font-size:13px}.detail-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:1px;margin-top:20px;overflow:hidden;border-radius:9px;background:#ffffff1a}.detail-metrics>div{padding:10px 11px;background:#18473f}.detail-metrics small,.detail-metrics strong{display:block}.detail-metrics small{color:#9ec0b6;font-size:10px}.detail-metrics strong{margin-top:4px;color:#fff;font-size:16px;font-variant-numeric:tabular-nums}.detail-metrics strong.negative{color:#ffb8b8}.detail-metrics strong.empty-stock{color:#f3d28e}.detail-metrics strong.positive-stock{color:#a9e4c8}.detail-content{padding:0 20px 20px}.detail-tabs{display:flex;gap:3px;margin:0 -20px 16px;padding:0 20px;border-bottom:1px solid #dfe8e3;background:#fff;overflow:auto}.detail-tabs button{padding:13px 11px;border:0;border-bottom:2px solid transparent;background:transparent;color:#71817b;font-size:13px;white-space:nowrap;cursor:pointer}.detail-tabs button.active{border-bottom-color:#1f6657;color:#174c41;font-weight:700}.detail-tabs span{display:inline-block;margin-left:4px;padding:1px 5px;border-radius:10px;background:#edf2ef;font-size:10px}.detail-section{overflow:hidden;border:1px solid #e0e8e4;border-radius:12px;background:#fff}.detail-section-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:15px 16px;border-bottom:1px solid #e8eeeb}.detail-section-head h3{margin:0;color:#24483e;font-size:15px}.detail-section-head p{margin-top:4px;color:#81908a;font-size:12px}.detail-filter{display:flex;align-items:center;gap:7px;min-width:220px;padding:0 9px;border:1px solid #dce6e1;border-radius:8px;background:#fbfdfc;color:#82928b}.detail-filter input{width:100%;min-width:0;border:0;outline:0;padding:8px 0;background:transparent;color:#27463c;font-size:12px}.detail-filter span{white-space:nowrap;color:#6e8d82;font-size:11px}.detail-table-wrap{overflow:auto}.detail-content table{width:100%;border-collapse:collapse}.detail-content th,.detail-content td{padding:10px 13px;border-top:1px solid #edf1ef;text-align:left;color:#42584f;font-size:12px}.detail-content th{border-top:0;background:#f8faf9;color:#7b8b84;font-size:11px}.detail-sort-header{width:100%;text-align:left}.detail-sort-header:hover{color:#1c6756}.muted{padding:18px!important;color:#81908a!important}.detail-state{display:grid;place-items:center;gap:11px;padding:70px 20px;color:#71817b}.detail-state.error strong{color:#a44343}@media(max-width:980px){.detail-backdrop{inset:0}.sku-detail{width:min(720px,100vw)}.detail-metrics{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:620px){.detail-section-head{align-items:stretch;flex-direction:column}.detail-filter{min-width:0}.detail-content{padding:0 12px 12px}.detail-tabs{margin-left:-12px;margin-right:-12px;padding:0 12px}.sku-detail header{padding:20px 17px}.sku-detail header .icon-btn{top:18px;right:17px}.detail-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
