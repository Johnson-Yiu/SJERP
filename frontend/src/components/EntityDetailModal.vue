<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ArrowLeft, CheckSquare, ChevronRight, ExternalLink, Pencil, Plus, Rows3, Search, Trash2, X } from 'lucide-vue-next'
import { api } from '../api'
import { resourceConfigs } from '../resourceConfigs'
import RelatedCreateModal from './RelatedCreateModal.vue'
import SKUPage from '../views/SKUPage.vue'

const props = defineProps({ entity: String, id: [Number, String] })
const emit = defineEmits(['close', 'edit'])
const data = ref(null), loading = ref(true), error = ref(''), activeTab = ref(''), stack = ref([])
const quickCreate = ref(null)
const skuCreateProductId = ref(null)
const operatorRole = ref('')
const selectedSkuIds = ref([])
const showInactiveSkus = ref(false)
const skuQuery = ref('')
const skuMultiSelect = ref(false)
const currentEntity = ref(props.entity), currentId = ref(props.id)

const activeSection = computed(() => data.value?.sections.find(s => s.key === activeTab.value) || data.value?.sections[0])
const documentEntities = new Set(['orders', 'quotes'])
const hasManagement = (entity) => Boolean(resourceConfigs[entity] || documentEntities.has(entity))
const quickCreatable = new Set(['contacts', 'follow-ups', 'orders', 'quotes', 'transactions', 'inventory-movements', 'skus', 'product-parameters', 'product-certificates', 'categories'])
const canManage = computed(() => Boolean(activeSection.value && quickCreatable.has(activeSection.value.entity)))
const isRoot = computed(() => currentEntity.value === props.entity && String(currentId.value) === String(props.id))
const isSkuSection = computed(() => currentEntity.value === 'products' && activeSection.value?.entity === 'skus')
const visibleSectionRows = computed(() => {
  const rows = activeSection.value?.rows || []
  if (!isSkuSection.value || !skuQuery.value.trim()) return rows
  const query = skuQuery.value.trim().toLowerCase()
  return rows.filter(row => [row.sku, row.specification, row.active ? '启用' : '已停用'].some(value => String(value || '').toLowerCase().includes(query)))
})
const canBulkDeleteSku = computed(() => /超级管理员|管理员/.test(operatorRole.value))
const selectableSkuRows = computed(() => visibleSectionRows.value.filter(row => row.active))
const allSkuSelected = computed(() => Boolean(selectableSkuRows.value.length) && selectableSkuRows.value.every(row => selectedSkuIds.value.includes(row.id)))
const selectedActiveSkuIds = computed(() => selectableSkuRows.value.filter(row => selectedSkuIds.value.includes(row.id)).map(row => row.id))
const selectedInactiveSkuIds = computed(() => visibleSectionRows.value.filter(row => !row.active && selectedSkuIds.value.includes(row.id)).map(row => row.id))

async function load(entity = currentEntity.value, id = currentId.value) {
  loading.value = true; error.value = ''
  try {
    data.value = (await api.get(`/context/${entity}/${id}/`, { params: entity === 'products' && showInactiveSkus.value ? { include_inactive: '1' } : {} })).data
    currentEntity.value = entity; currentId.value = id
    activeTab.value = data.value.sections[0]?.key || ''
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
async function drill(row) {
  if (!row._target_entity || !row._target_id) return
  stack.value.push({ entity: currentEntity.value, id: currentId.value, title: data.value.title })
  await load(row._target_entity, row._target_id)
}
async function back() {
  const previous = stack.value.pop()
  if (previous) await load(previous.entity, previous.id)
}
function relationQuery(section) {
  const root = data.value?.entity, id = currentId.value
  if (root === 'products') return { product: id }
  if (root === 'skus') return { sku: id }
  if (root === 'customers') return { customer: id }
  if (root === 'orders') return { order: id }
  return {}
}
function createLabel(section) {
  const labels = { contacts: '联系人', orders: '订单', quotes: '报价', 'follow-ups': '跟进记录', transactions: '财务流水', 'inventory-movements': '库存流水', skus: 'SKU', 'product-parameters': '产品参数', 'product-certificates': '产品证书' }
  return `新增${labels[section?.entity] || section?.title || '记录'}`
}
function openRelatedCreate() { if (activeSection.value) quickCreate.value = { entity: activeSection.value.entity, query: relationQuery(activeSection.value) } }
function openSkuCreate() { skuCreateProductId.value = currentId.value }
async function relatedSaved() {
  const previousTab = activeTab.value
  quickCreate.value = null
  await load()
  if (data.value?.sections.some(section => section.key === previousTab)) activeTab.value = previousTab
}
async function skuSaved() {
  const previousTab = activeTab.value
  skuCreateProductId.value = null
  await load()
  if (data.value?.sections.some(section => section.key === previousTab)) activeTab.value = previousTab
}
function toggleSkuSelection(id) {
  selectedSkuIds.value = selectedSkuIds.value.includes(id)
    ? selectedSkuIds.value.filter(item => item !== id)
    : [...selectedSkuIds.value, id]
}
function toggleAllSkuSelection() {
  selectedSkuIds.value = allSkuSelected.value ? [] : selectableSkuRows.value.map(row => row.id)
}
function toggleSkuMultiSelect() {
  skuMultiSelect.value = !skuMultiSelect.value
  selectedSkuIds.value = []
}
async function deactivateSelectedSkus() {
  const ids = selectedActiveSkuIds.value
  if (!ids.length || !confirm(`确定停用选中的 ${ids.length} 个 SKU 吗？停用后将默认从 ERP 列表隐藏。`)) return
  try {
    await Promise.all(ids.map(id => api.patch(`/skus/${id}/`, { active: false })))
    selectedSkuIds.value = []
    await load()
  } catch (e) { error.value = e.message || 'SKU 停用失败' }
}
async function reactivateSelectedSkus() {
  const ids = selectedInactiveSkuIds.value
  if (!ids.length || !confirm(`确定重新启用选中的 ${ids.length} 个 SKU 吗？`)) return
  try {
    await Promise.all(ids.map(id => api.patch(`/skus/${id}/`, { active: true })))
    selectedSkuIds.value = []
    await load()
  } catch (e) { error.value = e.message || 'SKU 重新启用失败' }
}
async function toggleInactiveSkus() {
  const previousTab = activeTab.value
  showInactiveSkus.value = !showInactiveSkus.value
  selectedSkuIds.value = []
  await load()
  if (data.value?.sections.some(section => section.key === previousTab)) activeTab.value = previousTab
}
function richText(value) {
  const escape = String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  const inline = text => text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/_(.+?)_/g, '<em>$1</em>')
  const lines = escape.split('\n')
  let html = '', listType = ''
  const closeList = () => { if (listType) { html += `</${listType}>`; listType = '' } }
  lines.forEach(line => {
    const unordered = line.match(/^\s*-\s+(.+)$/), ordered = line.match(/^\s*\d+\.\s+(.+)$/)
    const nextType = unordered ? 'ul' : ordered ? 'ol' : ''
    if (nextType) {
      if (listType !== nextType) { closeList(); listType = nextType; html += `<${listType}>` }
      html += `<li>${inline((unordered || ordered)[1])}</li>`
    } else { closeList(); html += `<p>${inline(line) || '&nbsp;'}</p>` }
  })
  closeList()
  return html
}
function format(value, type) {
  if (value === null || value === undefined || value === '') return '—'
  if (type === 'money') return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (type === 'rmb') return `¥ ${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
  if (type === 'number') return Number(value).toLocaleString('zh-CN')
  if (type === 'date') return String(value).slice(0, 10)
  if (type === 'datetime') return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  if (type === 'boolean') return value ? '是' : '否'
  if (type === 'sku-active') return value ? '启用' : '已停用'
  if (type === 'signed') return `${Number(value) > 0 ? '+' : ''}${Number(value).toLocaleString('zh-CN')}`
  if (type === 'excerpt') {
    const firstLine = String(value).split(/\r?\n/).find(line => line.trim()) || ''
    return firstLine.replace(/^\s*(?:[-*]|\d+\.)\s+/, '').replace(/\*\*|__/g, '').replace(/(^|\s)[*_](?=\S)|(?<=\S)[*_](?=\s|$)/g, '$1') || '—'
  }
  return value
}
function valueClass(type, value) { return { 'ctx-status': type === 'status', 'ctx-money': ['money', 'rmb'].includes(type), 'inactive-status': type === 'sku-active' && !value, positive: type === 'signed' && Number(value) > 0, negative: type === 'signed' && Number(value) < 0 } }

watch(() => [props.entity, props.id], () => { stack.value = []; currentEntity.value = props.entity; currentId.value = props.id; selectedSkuIds.value = []; skuMultiSelect.value = false; load() })
watch(activeTab, () => { selectedSkuIds.value = []; skuQuery.value = ''; skuMultiSelect.value = false })
onMounted(async () => {
  await Promise.all([
    load(),
    api.get('/session/current-operator/').then(response => { operatorRole.value = response.data.role || '' }).catch(() => { operatorRole.value = '' }),
  ])
})
</script>

<template>
  <div class="modal-backdrop detail-backdrop" @mousedown.self="emit('close')">
    <article class="detail-modal">
      <div v-if="loading" class="detail-loading"><div class="spinner" /><span>正在整理关联数据...</span></div>
      <div v-else-if="error" class="detail-error"><strong>详情加载失败</strong><p>{{ error }}</p><button class="btn btn-secondary" @click="load()">重试</button></div>
      <template v-else-if="data">
        <header class="detail-header">
          <div class="detail-nav">
            <button v-if="stack.length" class="detail-back" @click="back"><ArrowLeft :size="17" /> 返回 {{ stack[stack.length - 1].title }}</button>
            <span v-else>关联详情</span>
            <div class="detail-actions">
              <button v-if="isRoot" class="btn btn-secondary" @click="emit('edit')"><Pencil :size="14" /> {{ currentEntity === 'customers' ? '编辑客户' : '编辑主档' }}</button>
              <RouterLink v-else-if="hasManagement(currentEntity)" class="btn btn-secondary" :to="`/${currentEntity}`" @click="emit('close')"><ExternalLink :size="14" /> 打开管理页</RouterLink>
              <button class="detail-close" @click="emit('close')"><X :size="19" /></button>
            </div>
          </div>
          <div class="detail-identity"><div><span class="detail-subtitle">{{ data.subtitle }}</span><h2>{{ data.title }}</h2></div><span class="detail-badge">{{ data.badge }}</span></div>
          <div v-if="data.metrics.length" class="detail-metrics"><div v-for="metric in data.metrics" :key="metric[0]"><small>{{ metric[0] }}</small><strong>{{ format(metric[1], metric[2]) }}</strong></div></div>
        </header>

        <div class="detail-content">
          <section class="detail-info"><h3>基础信息</h3><div class="info-grid"><div v-for="item in data.info" :key="item[0]"><small>{{ item[0] }}</small><div v-if="item[2] === 'richtext'" class="richtext-view" v-html="richText(item[1])" /><span v-else>{{ item[1] }}</span></div></div></section>
          <section class="relation-area">
            <div class="relation-top"><div><h3>关联数据</h3><p>点击任意记录，可继续查看它的上下文。</p></div><div class="relation-actions"><button v-if="isSkuSection && canBulkDeleteSku" class="manage-link" :class="{ 'multi-select-active': skuMultiSelect }" @click="toggleSkuMultiSelect"><CheckSquare :size="13" /> {{ skuMultiSelect ? '取消多选' : '多选' }}</button><button v-if="isSkuSection && canBulkDeleteSku && skuMultiSelect && selectedActiveSkuIds.length" class="manage-link danger-link" @click="deactivateSelectedSkus"><Trash2 :size="13" /> 停用 {{ selectedActiveSkuIds.length }} 个 SKU</button><button v-if="isSkuSection && canBulkDeleteSku && skuMultiSelect && selectedInactiveSkuIds.length" class="manage-link restore-link" @click="reactivateSelectedSkus"><CheckSquare :size="13" /> 重新启用 {{ selectedInactiveSkuIds.length }} 个 SKU</button><button v-if="isSkuSection" class="manage-link" :class="{ 'inactive-toggle': showInactiveSkus }" @click="toggleInactiveSkus"><CheckSquare :size="13" /> {{ showInactiveSkus ? '隐藏已停用 SKU' : '显示已停用 SKU' }}</button><button v-if="isSkuSection" class="manage-link" @click="openSkuCreate"><Plus :size="13" /> 新增 SKU</button><button v-else-if="canManage" class="manage-link" @click="openRelatedCreate"><Plus :size="13" /> {{ createLabel(activeSection) }}</button></div></div>
            <label v-if="isSkuSection" class="sku-context-search"><Search :size="16" /><input v-model.trim="skuQuery" placeholder="搜索 SKU 编码、规格或状态..." /><span v-if="skuQuery">{{ visibleSectionRows.length }} / {{ activeSection.rows.length }}</span></label>
            <div class="detail-tabs"><button v-for="section in data.sections" :key="section.key" :class="{ active: activeTab === section.key }" @click="activeTab = section.key">{{ section.title }} <span>{{ section.rows.length }}</span></button></div>
            <div v-if="activeSection" class="context-table-wrap">
              <div v-if="!visibleSectionRows.length" class="context-empty"><Rows3 :size="27" /><strong>{{ isSkuSection && skuQuery ? '未找到匹配的 SKU' : `暂无${activeSection.title}` }}</strong><p>{{ isSkuSection && skuQuery ? '请调整关键词后重试。' : '点击右上角新增记录并自动建立关联。' }}</p></div>
              <table v-else class="context-table" :class="{ 'followup-table': activeSection.key === 'followups', 'sku-context-table': isSkuSection, 'multi-select-table': skuMultiSelect }"><thead><tr><th v-if="isSkuSection && canBulkDeleteSku && skuMultiSelect" class="selection-cell"><label class="selection-check"><input type="checkbox" :checked="allSkuSelected" @click.stop @change="toggleAllSkuSelection" /><CheckSquare :size="15" /></label></th><th v-for="column in activeSection.columns" :key="column[0]">{{ column[1] }}</th><th></th></tr></thead><tbody>
                <tr v-for="(row,index) in visibleSectionRows" :key="row.id || index" :class="{ 'inactive-row': isSkuSection && !row.active }" @click="!skuMultiSelect && drill(row)"><td v-if="isSkuSection && canBulkDeleteSku && skuMultiSelect" class="selection-cell"><label class="selection-check" :class="{ restore: !row.active }" @click.stop><input type="checkbox" :checked="selectedSkuIds.includes(row.id)" @change="toggleSkuSelection(row.id)" /><CheckSquare :size="15" /></label></td><td v-for="(column,colIndex) in activeSection.columns" :key="column[0]" :class="{ primary: colIndex === 0, 'excerpt-cell': column[2] === 'excerpt' }"><span :class="valueClass(column[2], row[column[0]])" :title="column[2] === 'excerpt' ? String(row[column[0]] || '') : undefined">{{ format(row[column[0]], column[2]) }}</span></td><td class="drill-cell"><button v-if="!skuMultiSelect" class="context-drill" :aria-label="`查看 ${row.sku || '记录'} 详情`" @click.stop="drill(row)"><ChevronRight :size="17" /></button></td></tr>
              </tbody></table>
            </div>
          </section>
        </div>
      </template>
    </article>
    <RelatedCreateModal v-if="quickCreate" :entity="quickCreate.entity" :query="quickCreate.query" @close="quickCreate = null" @saved="relatedSaved" />
    <SKUPage v-if="skuCreateProductId" embedded :initial-product="skuCreateProductId" @close="skuCreateProductId = null" @saved="skuSaved" />
  </div>
</template>

<style scoped>
.detail-backdrop{inset:0 0 0 248px;z-index:25;place-items:stretch end;padding:0;background:#0b221d66;backdrop-filter:blur(2px)}.detail-modal{height:100vh;width:min(1100px,100%);background:#f6f8f5;box-shadow:-24px 0 70px #06191452;overflow:auto;overscroll-behavior:contain;will-change:transform}.detail-loading,.detail-error{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#71817b}.detail-error strong{color:#9d4444}.detail-error p{font-size:13px}.detail-header{background:#123c36;color:#fff;padding:20px 28px 24px;position:relative;overflow:hidden}.detail-header:after{content:'';position:absolute;width:300px;height:300px;border:60px solid #ffffff08;border-radius:50%;right:-80px;top:-140px}.detail-nav{display:flex;justify-content:space-between;align-items:center;position:relative;z-index:1;font-size:11px;color:#91b6aa;text-transform:uppercase;letter-spacing:.12em}.detail-back{border:0;background:transparent;color:#b6d3ca;display:flex;gap:7px;align-items:center;padding:0}.detail-actions{display:flex;gap:8px;align-items:center}.detail-actions .btn{padding:7px 11px;font-size:11px;text-transform:none;letter-spacing:0;text-decoration:none}.detail-close{width:32px;height:32px;border:1px solid #ffffff28;background:#ffffff12;color:white;border-radius:8px;display:grid;place-items:center}.detail-identity{display:flex;gap:20px;align-items:end;justify-content:space-between;margin-top:23px;position:relative;z-index:1}.detail-subtitle{font-size:11px;color:#9cc0b5}.detail-identity h2{font-size:26px;margin:5px 0 0}.detail-badge{background:#ffffff14;border:1px solid #ffffff22;padding:6px 10px;border-radius:20px;font-size:11px}.detail-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#ffffff18;margin-top:22px;border-radius:10px;overflow:hidden;position:relative;z-index:1}.detail-metrics>div{padding:13px 15px;background:#18473f}.detail-metrics small,.detail-metrics strong{display:block}.detail-metrics small{font-size:10px;color:#93b7ad}.detail-metrics strong{font-size:18px;margin-top:5px}.detail-content{padding:22px 25px 40px}.detail-info,.relation-area{background:white;border:1px solid #e1e7e3;border-radius:13px;padding:19px;margin-bottom:15px}.detail-info h3,.relation-top h3{font-size:14px;margin:0}.info-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px 22px;margin-top:16px}.info-grid small,.info-grid span{display:block}.info-grid small{font-size:10px;color:#8a9792;margin-bottom:4px}.info-grid span{font-size:12px;color:#3d5049;white-space:pre-wrap;word-break:break-word}.richtext-view{font-size:12px;color:#3d5049;word-break:break-word}.richtext-view :deep(p){margin:0 0 4px}.richtext-view :deep(ul),.richtext-view :deep(ol){margin:3px 0;padding-left:18px}.relation-top{display:flex;justify-content:space-between;align-items:center}.relation-top p{font-size:10px;color:#8a9792;margin:4px 0 0}.manage-link{border:0;font-size:11px;color:#245e50;text-decoration:none;display:flex;align-items:center;gap:5px;background:#eaf3ef;padding:7px 10px;border-radius:7px}.detail-tabs{display:flex;gap:4px;margin:18px -19px 0;padding:0 19px;border-bottom:1px solid #e6ebe8;overflow:auto}.detail-tabs button{border:0;background:transparent;padding:10px 12px;color:#75837e;font-size:11px;white-space:nowrap;border-bottom:2px solid transparent}.detail-tabs button.active{color:#174c41;border-bottom-color:#1f6657;font-weight:700}.detail-tabs button span{background:#edf1ef;padding:2px 5px;border-radius:10px;margin-left:4px;font-size:9px}.context-table-wrap{overflow:auto;margin:0 -19px -19px}.context-table{width:100%;min-width:650px;border-collapse:collapse}.context-table th{font-size:9px;text-transform:uppercase;letter-spacing:.07em;color:#84918d;text-align:left;background:#f8faf8;padding:10px 13px}.context-table td{font-size:11px;color:#586660;padding:12px 13px;border-top:1px solid #edf0ee}.context-table td.primary{font-weight:600;color:#253a33}.context-table tr{cursor:pointer}.context-table tbody tr:hover{background:#f5f9f7}.context-table td:last-child{width:30px;color:#9ba7a2}.ctx-status{background:#e6f1ec;color:#286851;border-radius:20px;padding:3px 7px}.ctx-money{font-variant-numeric:tabular-nums;font-weight:600}.positive{color:#287258;font-weight:700}.negative{color:#b44f4f;font-weight:700}.context-empty{text-align:center;padding:42px;color:#99a5a0}.context-empty strong,.context-empty p{display:block}.context-empty strong{font-size:13px;color:#586963;margin-top:8px}.context-empty p{font-size:10px;margin:4px 0}.detail-actions .btn-secondary{background:#ffffff12;color:white;border-color:#ffffff28}
/* 同类详情模块的分区字号：顶部 +1px，基础信息与关联数据 +2px。 */
.detail-modal{font-size:17px}
.detail-nav,.detail-actions .btn,.detail-subtitle,.detail-badge{font-size:12px}
.detail-identity h2{font-size:27px}.detail-metrics small{font-size:11px}.detail-metrics strong{font-size:19px}
.detail-info h3,.relation-top h3{font-size:16px}.info-grid small{font-size:12px}.info-grid span,.richtext-view{font-size:14px}
.relation-top p{font-size:12px}.manage-link,.detail-tabs button{font-size:13px}.detail-tabs button span{font-size:11px}
.context-table th{font-size:11px}.context-table td{font-size:13px}.context-empty strong{font-size:15px}.context-empty p{font-size:12px}
.followup-table{table-layout:fixed;min-width:900px}.followup-table th:nth-child(1){width:105px}.followup-table th:nth-child(2){width:140px}.followup-table th:nth-child(3),.followup-table th:nth-child(4){width:220px}.followup-table th:nth-child(5){width:72px}.followup-table th:nth-child(6){width:105px}.followup-table th:last-child{width:34px}.excerpt-cell span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:980px){.detail-backdrop{inset:0;z-index:60}}
@media(max-width:700px){.detail-modal{width:100vw}.detail-header{padding:16px 17px 20px}.detail-identity h2{font-size:22px}.detail-metrics{grid-template-columns:repeat(2,1fr)}.detail-content{padding:12px}.detail-info,.relation-area{padding:15px}.info-grid{grid-template-columns:repeat(2,1fr)}.detail-tabs{margin-left:-15px;margin-right:-15px;padding:0 15px}.context-table-wrap{margin-left:-15px;margin-right:-15px}.detail-actions .btn{display:none}}
.restore-link{background:#e9f5ef;color:#27725a}.selection-check.restore{color:#d27878}
.sku-context-search{display:flex;align-items:center;gap:8px;width:min(360px,100%);margin:13px 0 -4px;color:#82928b;border:1px solid #dce6e1;border-radius:8px;padding:0 10px;background:#fbfdfc}.sku-context-search input{min-width:0;flex:1;border:0;outline:0;padding:9px 0;background:transparent;color:#27463c;font-size:13px}.sku-context-search span{font-size:11px;color:#6e8d82;white-space:nowrap}
.drill-cell{width:52px!important;padding:0!important}.context-drill{width:52px;height:100%;min-height:45px;border:0;background:transparent;display:grid;place-items:center;color:#8a9d96;cursor:pointer}.context-drill:hover{background:#eaf3ef;color:#17604f}.context-drill:focus-visible{outline:3px solid #bcdace;outline-offset:-3px}
.multi-select-active{background:#1f6657!important;color:#fff!important}.multi-select-table tbody tr{cursor:default}.multi-select-table .drill-cell{width:30px!important}
</style>
<style scoped>
.relation-actions{display:flex;align-items:center;gap:8px}.danger-link{background:#fff0f0;color:#ad4545}.inactive-toggle{background:#fff6f6;color:#ad4545}.selection-cell{width:40px;padding-left:12px!important;padding-right:4px!important;text-align:center}.selection-check{position:relative;display:inline-grid;place-items:center;cursor:pointer;color:#bdc9c4}.selection-check input{position:absolute;opacity:0}.selection-check svg{pointer-events:none}.selection-check input:checked+svg{color:#21745f}.selection-check input:focus-visible+svg{outline:3px solid #c6dfd7;outline-offset:2px;border-radius:3px}.sku-context-table tbody tr:has(.selection-check input:checked){background:#eff7f3}.sku-context-table th.selection-cell{padding-top:8px;padding-bottom:8px}.inactive-row{background:#fff7f7!important}.inactive-row td,.inactive-row td.primary{color:#b45757!important}.inactive-status{display:inline-block;border-radius:20px;padding:3px 7px;background:#ffeded;color:#ba4545;font-weight:700}
</style>
