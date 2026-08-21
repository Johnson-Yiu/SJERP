<script setup>
import { computed, onMounted, ref } from 'vue'
import { Database, PackageSearch, RefreshCw, Search } from 'lucide-vue-next'
import { api, listData } from '../api'

const rows = ref([])
const query = ref('')
const loading = ref(true)
const error = ref('')
const filteredRows = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  if (!keyword) return rows.value
  return rows.value.filter(row => [row.sku, row.product_name, row.product_code, row.specification].some(value => String(value || '').toLowerCase().includes(keyword)))
})
const totalSkus = computed(() => filteredRows.value.length)
const totalQuantity = computed(() => filteredRows.value.reduce((sum, row) => sum + Number(row.actual_quantity ?? row.stock_quantity ?? 0), 0))
const totalAvailable = computed(() => filteredRows.value.reduce((sum, row) => sum + Number(row.available_quantity ?? row.stock_quantity ?? 0), 0))
const totalInTransit = computed(() => filteredRows.value.reduce((sum, row) => sum + Number(row.in_transit_quantity || 0), 0))
const lowOrEmptyCount = computed(() => filteredRows.value.filter(row => row.has_anomaly || Number(row.available_quantity ?? row.stock_quantity ?? 0) <= 0).length)
const formatQuantity = value => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(Number(value || 0))
function stockState(row) {
  const quantity = Number(row.available_quantity ?? row.stock_quantity ?? 0)
  if (row.has_anomaly) return { label: '需处理', className: 'negative' }
  if (quantity < 0) return { label: '库存为负', className: 'negative' }
  if (quantity === 0) return { label: '无库存', className: 'empty-stock' }
  return { label: '有库存', className: 'positive-stock' }
}
async function load() {
  loading.value = true; error.value = ''
  try { rows.value = listData(await api.get('/skus/', { params: { include_inactive: 1 } })) }
  catch (requestError) { error.value = requestError.message || '库存数据加载失败，请稍后重试。' }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="inventory-page">
    <div class="page-head"><div><h2>库存</h2><p>按 SKU 汇总库存数量，数据会随出入库流水实时更新。</p></div><button class="btn btn-secondary" :disabled="loading" @click="load"><RefreshCw :size="16" :class="{ spinning: loading }" /> 刷新数据</button></div>
    <section class="inventory-summary" aria-label="库存概览"><article><span>SKU 数量</span><strong>{{ totalSkus }}</strong><small>当前筛选范围</small></article><article><span>实际库存</span><strong>{{ formatQuantity(totalQuantity) }}</strong><small>所有 SKU 实物合计</small></article><article><span>可用库存</span><strong>{{ formatQuantity(totalAvailable) }}</strong><small>扣除订单预留后</small></article><article><span>在途采购</span><strong>{{ formatQuantity(totalInTransit) }}</strong><small>已下单未到货</small></article><article class="attention"><span>待关注</span><strong>{{ lowOrEmptyCount }}</strong><small>无可用库存或异常</small></article></section>
    <div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索 SKU、产品、规格..." /></div></div>
    <section class="panel"><div v-if="loading" class="loading"><div class="spinner" /></div><div v-else-if="error" class="empty"><PackageSearch :size="32" /><h3>无法加载库存</h3><p>{{ error }}</p></div><div v-else-if="!filteredRows.length" class="empty"><Database :size="32" /><h3>没有匹配的库存记录</h3><p>请调整搜索条件，或先创建 SKU 并登记入库。</p></div><div v-else class="table-wrap"><table class="data-table inventory-table"><thead><tr><th>SKU</th><th>产品</th><th>实际</th><th>预留</th><th>可用</th><th>在途</th><th>待采购</th><th>状态</th></tr></thead><tbody><tr v-for="row in filteredRows" :key="row.id"><td class="primary-cell">{{ row.sku }}</td><td>{{ row.product_name }}</td><td>{{ formatQuantity(row.actual_quantity ?? row.stock_quantity) }}</td><td>{{ formatQuantity(row.reserved_quantity) }}</td><td class="stock-quantity" :class="stockState(row).className">{{ formatQuantity(row.available_quantity ?? row.stock_quantity) }}</td><td>{{ formatQuantity(row.in_transit_quantity) }}</td><td>{{ formatQuantity(row.to_procure_quantity) }}</td><td><span class="stock-status" :class="stockState(row).className">{{ stockState(row).label }}</span></td></tr></tbody></table></div></section>
  </div>
</template>
