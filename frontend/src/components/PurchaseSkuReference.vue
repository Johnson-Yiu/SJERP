<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { apiErrorMessage } from '../utils/apiErrors.js'
import { useAccessControl } from '../accessControl'

const props = defineProps({
  sku: { type: Object, default: null },
})

const { can } = useAccessControl()
const reference = ref(null)
const loading = ref(false)
const error = ref('')
const versions = ref([])
const versionsOpen = ref(false)
const versionsLoading = ref(false)
const versionsError = ref('')
let requestId = 0
let versionsRequestId = 0
let versionsLoadedFor = 0

const skuId = computed(() => Number(props.sku?.id || 0))
const inventoryVisible = computed(() => can('inventory', 'view'))
const skuVisible = computed(() => can('skus', 'view'))
const current = computed(() => reference.value || props.sku)
const hasInventoryMetrics = computed(() => {
  const row = reference.value
  return row && ['actual_quantity', 'reserved_quantity', 'available_quantity', 'in_transit_quantity']
    .every(field => row[field] !== null && row[field] !== undefined)
})
const parameterEntries = computed(() => Object.entries(current.value?.parameter_values || {}).filter(([, value]) => String(value ?? '').trim()))
const detailEntries = computed(() => (Array.isArray(current.value?.product_details) ? current.value.product_details : []).filter(detail => detail && typeof detail === 'object'))

function formatQuantity(value) {
  if (value === null || value === undefined || value === '') return '—'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function displayDetail(detail) {
  const values = Object.entries(detail)
    .filter(([key, value]) => !['preview_key', 'product_name', 'model', 'length', 'width', 'height'].includes(key) && String(value ?? '').trim())
    .map(([key, value]) => `${key}：${value}`)
  return values.join('；')
}

async function loadReference(force = false) {
  const id = skuId.value
  if (!id || !inventoryVisible.value) return
  if (!force && reference.value?.id === id) return
  const currentRequest = ++requestId
  loading.value = true
  error.value = ''
  reference.value = null
  try {
    const response = await api.get(`/skus/${id}/`)
    if (currentRequest !== requestId || id !== skuId.value) return
    reference.value = response.data
  } catch (requestError) {
    if (currentRequest === requestId) error.value = apiErrorMessage(requestError) || '库存参考加载失败。'
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

async function loadVersions(force = false) {
  const id = skuId.value
  if (!id || !skuVisible.value) return
  versionsOpen.value = true
  if (!force && versions.value.length && versionsLoadedFor === id) return
  const currentRequest = ++versionsRequestId
  versionsLoading.value = true
  versionsError.value = ''
  versions.value = []
  try {
    const response = await api.get(`/skus/${id}/versions/`)
    if (currentRequest !== versionsRequestId || id !== skuId.value) return
    versions.value = response.data || []
    versionsLoadedFor = id
  } catch (requestError) {
    if (currentRequest === versionsRequestId) versionsError.value = apiErrorMessage(requestError) || 'SKU 历史版本加载失败。'
  } finally {
    if (currentRequest === versionsRequestId) versionsLoading.value = false
  }
}

function reset() {
  requestId += 1
  versionsRequestId += 1
  reference.value = null
  loading.value = false
  error.value = ''
  versions.value = []
  versionsOpen.value = false
  versionsLoading.value = false
  versionsError.value = ''
  versionsLoadedFor = 0
  void loadReference()
}

watch(skuId, reset, { immediate: true })
</script>

<template>
  <section v-if="sku" class="purchase-sku-reference" data-testid="purchase-sku-reference" aria-label="SKU 库存参考">
    <div class="purchase-sku-reference-head">
      <div>
        <strong>SKU 库存参考</strong>
        <small>仅供采购判断；不自动分配库存、不改采购数量。</small>
      </div>
      <div class="purchase-sku-reference-actions">
        <RouterLink v-if="inventoryVisible" class="text-btn" :to="{ path: '/inventory', query: { detail: String(sku.id) } }">查看库存详情</RouterLink>
        <RouterLink v-if="skuVisible" class="text-btn" :to="{ path: '/skus', query: { detail: String(sku.id) } }">查看 SKU 资料</RouterLink>
      </div>
    </div>

    <div class="purchase-sku-identity">
      <strong>{{ sku.sku_code || sku.sku || '—' }}</strong>
      <span>{{ sku.display_name_cn || sku.product_name || '未命名 SKU' }}</span>
      <small>基础单位：{{ sku.unit || '—' }}</small>
    </div>

    <p v-if="!inventoryVisible" class="purchase-sku-reference-state">当前账号无库存查看权限，库存数量不在采购页面显示。</p>
    <p v-else-if="loading" class="purchase-sku-reference-state" role="status">正在加载库存参考…</p>
    <p v-else-if="error" class="purchase-sku-reference-state warning" role="alert">{{ error }} 未显示库存数量，采购仍可继续。<button type="button" class="text-btn" @click="loadReference(true)">重试</button></p>
    <p v-else-if="!hasInventoryMetrics" class="purchase-sku-reference-state">暂无可用库存参考数据，采购仍可继续。</p>
    <dl v-else class="purchase-sku-metrics">
      <div><dt>实际库存</dt><dd>{{ formatQuantity(current.actual_quantity) }} {{ current.unit || sku.unit || '' }}</dd></div>
      <div><dt>已预留</dt><dd>{{ formatQuantity(current.reserved_quantity) }} {{ current.unit || sku.unit || '' }}</dd></div>
      <div><dt>可用库存</dt><dd>{{ formatQuantity(current.available_quantity) }} {{ current.unit || sku.unit || '' }}</dd></div>
      <div><dt>在途采购</dt><dd>{{ formatQuantity(current.in_transit_quantity) }} {{ current.unit || sku.unit || '' }}</dd></div>
    </dl>

    <details v-if="skuVisible" class="purchase-sku-materials">
      <summary>规格与资料</summary>
      <dl>
        <div><dt>规格</dt><dd>{{ current.specification || '暂无规格说明' }}</dd></div>
        <div><dt>中文描述</dt><dd>{{ current.description_cn || '暂无中文描述' }}</dd></div>
        <div v-if="current.description_en"><dt>英文描述</dt><dd>{{ current.description_en }}</dd></div>
        <div v-if="parameterEntries.length"><dt>参数</dt><dd>{{ parameterEntries.map(([key, value]) => `${key}：${value}`).join('；') }}</dd></div>
        <div v-if="detailEntries.length"><dt>定制 / 特点</dt><dd>{{ detailEntries.map(displayDetail).filter(Boolean).join('；') || '暂无相关说明' }}</dd></div>
      </dl>
      <p class="purchase-sku-version-note">SKU 历史版本记录主档变更，不代表库存批次版本。</p>
      <button type="button" class="text-btn" @click="loadVersions(versionsOpen)">{{ versionsOpen ? '重新加载版本记录' : '查看版本记录' }}</button>
      <div v-if="versionsOpen" class="purchase-sku-versions">
        <p v-if="versionsLoading" class="purchase-sku-reference-state">正在加载版本记录…</p>
        <p v-else-if="versionsError" class="purchase-sku-reference-state warning" role="alert">{{ versionsError }} <button type="button" class="text-btn" @click="loadVersions(true)">重试</button></p>
        <p v-else-if="!versions.length" class="purchase-sku-reference-state">暂无历史版本记录。</p>
        <ul v-else>
          <li v-for="version in versions" :key="version.id"><strong>v{{ version.version_no }}</strong><span>{{ version.changed_at }} · {{ version.changed_fields?.join('、') || '主档变更' }}</span></li>
        </ul>
      </div>
    </details>
  </section>
</template>

<style scoped>
.purchase-sku-reference{margin:0 0 12px;padding:11px 12px;border:1px solid #d2e3d9;border-radius:9px;background:#f8fcf9;color:#355b4d}.purchase-sku-reference-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.purchase-sku-reference-head>div:first-child{display:grid;gap:3px;min-width:0}.purchase-sku-reference-head strong{color:#1f4f40;font-size:13px}.purchase-sku-reference-head small{color:#71877d;font-size:11px;line-height:1.5}.purchase-sku-reference-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.purchase-sku-reference-actions .text-btn{padding:3px 5px;font-size:12px;white-space:nowrap}.purchase-sku-identity{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin:8px 0 7px}.purchase-sku-identity strong{color:#254f42;font-size:13px;overflow-wrap:anywhere}.purchase-sku-identity span{min-width:0;overflow-wrap:anywhere;font-size:12px}.purchase-sku-identity small{color:#71877d;font-size:11px}.purchase-sku-reference-state{margin:8px 0 0;color:#71877d;font-size:12px;line-height:1.5}.purchase-sku-reference-state.warning{color:#8b6426}.purchase-sku-reference-state .text-btn{padding:0 3px;font-size:12px}.purchase-sku-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:8px 0 0}.purchase-sku-metrics>div{min-width:0;padding:7px 8px;border-radius:7px;background:#edf6f0}.purchase-sku-metrics dt{color:#71877d;font-size:11px}.purchase-sku-metrics dd{margin:3px 0 0;color:#214f40;font-size:12px;font-weight:700;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.purchase-sku-materials{margin-top:9px;border-top:1px solid #deebe3;padding-top:7px;font-size:12px}.purchase-sku-materials summary{cursor:pointer;color:#315e4e;font-weight:700}.purchase-sku-materials>dl{display:grid;gap:5px;margin:8px 0}.purchase-sku-materials>dl>div{display:grid;grid-template-columns:70px minmax(0,1fr);gap:7px}.purchase-sku-materials dt{color:#81948b}.purchase-sku-materials dd{min-width:0;margin:0;color:#456258;overflow-wrap:anywhere;line-height:1.5}.purchase-sku-version-note{margin:8px 0;color:#81948b;font-size:11px;line-height:1.5}.purchase-sku-versions ul{display:grid;gap:5px;margin:7px 0 0;padding:0;list-style:none}.purchase-sku-versions li{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;color:#456258}.purchase-sku-versions li strong{color:#315e4e}.purchase-sku-versions li span{overflow-wrap:anywhere}
@media(max-width:760px){.purchase-sku-reference-head{display:grid}.purchase-sku-reference-actions{justify-content:flex-start}.purchase-sku-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
