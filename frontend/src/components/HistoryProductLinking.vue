<script setup>
import { downloadBlob } from '../utils/downloadBlob.js'
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
import { accessState } from '../accessControl'
import { apiErrorMessage } from '../utils/apiErrors'
import { formatMoney } from '../utils/money'

const emit = defineEmits(['open-source', 'saved'])
const { api } = useWorkspaceApi()
const root = '/import/history-products/'
const labels = { pending: '待关联', linked: '已关联', review: '待核实' }
const operations = { link: '关联 SKU', change: '修改关联', unlink: '解除关联', review: '标记待核实' }
const filters = reactive({ q: '', source: '', batch: '', status: '', date_from: '', date_to: '', target: '' })
const applied = ref({})
const rows = ref([])
const count = ref(0)
const page = ref(1)
const selected = ref([])
const targets = ref([])
const targetSearch = ref('')
const operation = ref('link')
const target = ref('')
const reason = ref('')
const verifiedSpecification = ref('')
const saveRule = ref(false)
const preview = ref(null)
const conflicts = ref([])
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const dialog = ref(null)
const dialogOpen = ref(false)
const targetRequired = computed(() => ['link', 'change'].includes(operation.value))
const targetLabel = sku => [sku.code, sku.name, sku.specification, ...Object.values(sku.parameters || {}), sku.unit].filter(Boolean).join(' · ')
let session = 0
let searchVersion = 0

async function load(nextPage = 1, useFilters = false) {
  const version = ++searchVersion
  if (useFilters) applied.value = Object.fromEntries(Object.entries(filters).filter(([, value]) => value))
  loading.value = true
  error.value = ''
  selected.value = []
  try {
    const { data } = await api.get(root, { params: { ...applied.value, page: nextPage } })
    if (version !== searchVersion) return
    rows.value = data.results
    count.value = data.count
    page.value = nextPage
  } catch (err) {
    if (version === searchVersion) error.value = apiErrorMessage(err) || '无法加载历史商品，请重试。'
  } finally {
    if (version === searchVersion) loading.value = false
  }
}

async function searchTargets() {
  const generation = session
  busy.value = true
  error.value = ''
  try {
    const { data } = await api.get(root + 'targets/', { params: { q: targetSearch.value } })
    if (generation === session) targets.value = data
  } catch (err) {
    if (generation === session) error.value = apiErrorMessage(err) || '无法加载 SKU，请重试。'
  } finally {
    if (generation === session) busy.value = false
  }
}

async function openDialog() {
  preview.value = null
  conflicts.value = []
  targetSearch.value = ''
  target.value = ''
  reason.value = ''
  verifiedSpecification.value = ''
  saveRule.value = false
  operation.value = 'link'
  dialog.value.showModal()
  dialogOpen.value = true
  if (targetRequired.value) await searchTargets()
}
watch([operation, target, reason, saveRule, verifiedSpecification], () => { preview.value = null; conflicts.value = [] })

async function run(action) {
  if (busy.value) return
  const generation = session
  busy.value = true
  error.value = ''
  conflicts.value = []
  try {
    const payload = action === 'preview'
      ? { ids: selected.value, operation: operation.value, target: targetRequired.value ? target.value : null, reason: reason.value, save_rule: targetRequired.value && saveRule.value, ...(targetRequired.value && verifiedSpecification.value ? { verified_specification: verifiedSpecification.value } : {}) }
      : { token: preview.value.token }
    const { data } = await api.post(root + action + '/', payload)
    if (generation !== session) return
    if (action === 'preview') preview.value = data
    else {
      dialog.value.close()
      notice.value = `已更新 ${data.updated} 条历史商品。`
      await load(page.value)
      if (generation === session) emit('saved')
    }
  } catch (err) {
    if (generation !== session) return
    conflicts.value = err.response?.data?.conflicts || []
    if (conflicts.value.length || err.response?.status === 400) preview.value = null
    error.value = conflicts.value.length ? '关联未保存，请核对冲突后重新预览。' : apiErrorMessage(err) || '请求失败，请重试。'
  } finally {
    if (generation === session) busy.value = false
  }
}

async function download() {
  const generation = session
  try {
    const { data } = await api.get(root + 'export/', { params: applied.value, responseType: 'blob' })
    if (generation !== session) return
    downloadBlob(data, '历史商品明细.csv')
  } catch {
    if (generation === session) error.value = '导出失败，请重试。'
  }
}

watch(() => accessState.operator, operator => {
  session++
  searchVersion++
  dialog.value?.close()
  dialogOpen.value = false
  rows.value = []
  targets.value = []
  selected.value = []
  preview.value = null
  count.value = 0
  loading.value = false
  busy.value = false
  notice.value = ''
  error.value = ''
  if (operator) load()
}, { immediate: true })
onBeforeUnmount(() => { session++; searchVersion++ })
</script>

<template>
  <section class="history-products">
    <header><h3>历史商品关联</h3><p>核对原商品与正式 SKU。原名称、规格和单位会保留。</p></header>
    <form class="filters" @submit.prevent="load(1, true)">
      <label>原名称或编码<input v-model.trim="filters.q" /></label>
      <label>来源系统<input v-model.trim="filters.source" /></label>
      <label>来源批次<input v-model.trim="filters.batch" /></label>
      <label>关联状态<select v-model="filters.status"><option value="">全部</option><option v-for="(label, key) in labels" :key="key" :value="key">{{ label }}</option></select></label>
      <label>开始日期<input v-model="filters.date_from" type="date" /></label>
      <label>结束日期<input v-model="filters.date_to" type="date" /></label>
      <label>目标 SKU 编码<input v-model.trim="filters.target" /></label>
      <button type="submit" :disabled="loading">查询</button>
    </form>
    <div class="actions">
      <button type="button" :disabled="!selected.length || loading" @click="openDialog">处理所选商品（{{ selected.length }}）</button>
      <button type="button" :disabled="loading || !count" @click="download">导出 CSV</button>
    </div>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="error && !dialogOpen" role="alert">{{ error }}</p>
    <p v-if="loading" role="status">正在加载历史商品…</p>
    <p v-else-if="!rows.length">没有符合条件的历史商品。</p>
    <ul v-else class="product-rows">
      <li v-for="row in rows" :key="row.id">
        <label class="check"><input v-model="selected" type="checkbox" :value="row.id" /><strong>{{ row.name }}</strong></label>
        <span>{{ [row.code, row.specification, row.quantity + ' ' + row.unit, row.currency && row.currency + ' ' + formatMoney(row.amount)].filter(Boolean).join(' · ') }}</span>
        <span>{{ row.source_system }} · {{ row.order_number }} · {{ row.source_number }}</span>
        <span>{{ labels[row.status] }}<RouterLink v-if="row.sku" :to="{ path: '/skus', query: { detail: row.sku.id } }"> · {{ row.sku.code }} {{ row.sku.name }}</RouterLink></span>
        <button type="button" @click="emit('open-source', row.application, row.group)">查看原资料</button>
      </li>
    </ul>
    <div v-if="count > 50" class="actions">
      <button type="button" :disabled="page === 1 || loading" @click="load(page - 1)">上一页</button>
      <span>第 {{ page }} 页 · 共 {{ count }} 条</span>
      <button type="button" :disabled="page * 50 >= count || loading" @click="load(page + 1)">下一页</button>
    </div>
    <dialog ref="dialog" aria-labelledby="history-product-dialog-title" @close="dialogOpen = false" @cancel="busy && $event.preventDefault()">
      <h3 id="history-product-dialog-title">处理历史商品</h3>
      <div class="dialog-body">
      <label>操作<select v-model="operation" :disabled="busy"><option v-for="(label, key) in operations" :key="key" :value="key">{{ label }}</option></select></label>
      <template v-if="targetRequired">
        <form class="actions" @submit.prevent="searchTargets"><label>搜索正式 SKU<input v-model.trim="targetSearch" /></label><button type="submit" :disabled="busy">搜索</button></form>
        <label>正式 SKU<select v-model="target" aria-label="正式 SKU" :disabled="busy"><option value="">请选择</option><option v-for="sku in targets" :key="sku.id" :value="sku.id">{{ targetLabel(sku) }}</option></select></label>
        <label class="check"><input v-model="saveRule" type="checkbox" :disabled="busy" />保存为本来源的下次匹配候选</label>
      </template>
      <label v-if="targetRequired">补核规格（仅原规格缺失时）<input v-model.trim="verifiedSpecification" maxlength="1000" :disabled="busy" /></label>
      <label>原因{{ operation === 'link' && !verifiedSpecification ? '（选填）' : '（必填）' }}<textarea v-model.trim="reason" :disabled="busy" maxlength="1000" rows="2" /></label>
      <p v-if="error" role="alert">{{ error }}</p>
      <ul v-if="conflicts.length"><li v-for="(row, index) in conflicts" :key="index">{{ row.source_number }} {{ row.reason }}</li></ul>
      <section v-if="preview" aria-label="关联预览">
        <h4>影响 {{ preview.count }} 条明细</h4>
        <p v-if="preview.target">目标 SKU　{{ targetLabel(preview.target) }}</p>
        <p v-for="(value, unit) in preview.quantities" :key="unit">数量 {{ value }} {{ unit || '单位待核实' }}</p>
        <p v-for="(value, currency) in preview.amounts" :key="currency">商品金额 {{ currency }} {{ formatMoney(value) }}</p>
        <ul><li v-for="row in preview.rows" :key="row.id">{{ row.source_system }} · {{ row.source_number }} · {{ row.name }} · 原关联 {{ row.sku?.code || '无' }}</li></ul>
      </section>
      </div>
      <div class="actions dialog-actions">
        <button type="button" :disabled="busy" @click="dialog.close()">关闭</button>
        <button type="button" :disabled="busy || (targetRequired && !target) || ((operation !== 'link' || Boolean(verifiedSpecification)) && !reason)" @click="run('preview')">生成预览</button>
        <button v-if="preview" class="confirm" type="button" :disabled="busy" @click="run('apply')">{{ busy ? '处理中…' : '确认保存' }}</button>
      </div>
    </dialog>
  </section>
</template>

<style scoped>
.history-products { border: 1px solid #dfe7e2; border-radius: 12px; padding: 16px; background: white; min-width: 0; overflow-wrap: anywhere; }
.history-products h3, .history-products p { margin: 0 0 10px; }
.filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 145px), 1fr)); align-items: end; gap: 10px; }
label { display: grid; gap: 4px; min-width: 0; }
input, select, textarea { box-sizing: border-box; width: 100%; min-width: 0; border: 1px solid #bdcec2; border-radius: 6px; padding: 7px; background: #fff; color: #233b30; font: inherit; }
button { border: 1px solid #bdcec2; border-radius: 6px; padding: 7px 10px; background: #fff; color: #233b30; font: inherit; cursor: pointer; }
button:disabled { opacity: .6; cursor: default; }
button.confirm { color: #fff; background: #245b45; border-color: #245b45; }
.actions { display: flex; flex-wrap: wrap; align-items: end; gap: 8px; margin: 12px 0; }
.product-rows { list-style: none; padding: 0; }
.product-rows li { display: grid; justify-items: start; gap: 4px; padding: 10px 0; border-top: 1px solid #e6ede7; }
.check { display: flex; align-items: start; gap: 8px; }
.check input { width: auto; }
dialog { width: min(620px, calc(100% - 30px)); max-height: calc(100% - 30px); box-sizing: border-box; padding: 16px; border: 1px solid #bfcfc5; border-radius: 12px; overflow: hidden; }
dialog::backdrop { background: #182d24a0; }
dialog[open] { display: flex; flex-direction: column; }
.dialog-body { min-height: 0; overflow-y: auto; padding-inline-end: 3px; }
.dialog-body > label { margin: 8px 0; }
.dialog-actions { flex-shrink: 0; padding-top: 10px; margin: 0; border-top: 1px solid #e6ede7; }
[role="alert"] { color: #922f24; }
</style>
