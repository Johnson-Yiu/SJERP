<script setup>
import { compactDecimalInput } from '../utils/decimalInput'
import { movementSource, sourceLabels, movementStatus, signedMovement } from '../utils/inventoryLedger'
import CertificateExpiryBadge from './CertificateExpiryBadge.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CheckSquare, ChevronRight, ExternalLink, Paperclip, Pencil, Plus, Rows3, Search, Trash2, X } from 'lucide-vue-next'
import { api, listData } from '../api'
import { confirmDialog } from '../dialogs'
import { resourceConfigs } from '../resourceConfigs'
import { renderRichText as richText } from '../utils/richText'
import RelatedCreateModal from './RelatedCreateModal.vue'
import OperationLogPanel from './OperationLogPanel.vue'
import SKUPage from '../views/SKUPage.vue'
import ProductWorkspace from './ProductWorkspace.vue'
import { canCreateRelated, relationWorkbenchLocation } from '../utils/detailNavigation'

const props = defineProps({ entity: String, id: [Number, String], refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['close', 'edit', 'changed'])
const data = ref(null), loading = ref(true), error = ref(''), activeTab = ref(''), stack = ref([])
const movementRecord = ref(null)
const isMovementDetail = computed(() => currentEntity.value === 'inventory-movements')
const detailInfo = computed(() => {
  if (!isMovementDetail.value || !movementRecord.value) return data.value?.info || []
  const row = movementRecord.value
  const sku = data.value?.sections?.find(section => section.key === 'sku')?.rows?.[0]
  const unit = row.trade_snapshot?.base_unit || sku?.unit || ''
  return [['流水号',row.movement_no],['日期',row.movement_date],['SKU',row.sku_code || sku?.sku || '—'],['类型',row.type_display],['数量变化',signedMovement(row,unit)],['交易单位 / 登记规格',row.trade_snapshot?.name || '基础单位登记'],['交易数量',row.trade_unit ? `${row.trade_quantity} ${row.trade_snapshot?.unit || ''}` : '—'],['仓库',row.warehouse],['关联订单',(row.related_order_nos || []).join('、') || row.order_no || '—'],['关联单据',row.reference || row.source_no || '—'],['来源',sourceLabels[movementSource(row)] || '未标注'],['备注',row.notes || '—'],['冲销状态',movementStatus(row)],['冲销记录',row.reversal_status || '—'],['超到说明',row.overage_summary || '—'],['单位成本',compactDecimalInput(row.unit_cost)]]
})
const operationLogs = ref([]), operationLogsLoading = ref(false), auditEnabled = ref(false)
const quickCreate = ref(null)
const skuCreateOpen = ref(false)
const route = useRoute()
const router = useRouter()
const operatorRole = ref('')
const selectedSkuIds = ref([])
const showInactiveSkus = ref(false)
const skuQuery = ref('')
const skuMultiSelect = ref(false)
const productDrawer = ref(null)
const isProduct = computed(() => currentEntity.value === 'products')
const currentEntity = ref(props.entity), currentId = ref(props.id)

const activeSection = computed(() => activeTab.value === '__operation_logs' ? null : (data.value?.sections.find(s => s.key === activeTab.value) || data.value?.sections[0]))
const documentEntities = new Set(['orders', 'quotes', 'purchase-orders'])
const hasManagement = (entity) => Boolean(resourceConfigs[entity] || documentEntities.has(entity))
const canManage = computed(() => canCreateRelated(currentEntity.value, activeSection.value))
const isRoot = computed(() => currentEntity.value === props.entity && String(currentId.value) === String(props.id))
const showRelatedCreate = computed(() => canManage.value && !(isRoot.value && currentEntity.value === 'customers' && ['followups', 'quotes'].includes(activeSection.value?.key)))
const isCustomerRoot = computed(() => isRoot.value && currentEntity.value === 'customers' && route.path === '/customers')
function restoreCustomerTab() {
  if (!isRoot.value || route.path !== `/${props.entity}` || !data.value) return
  const key = route.query.tab
  const valid = key === 'operation_logs' || (isProduct.value && ['__overview', 'sales-rules'].includes(key)) || data.value.sections.some(section => section.key === key)
  const fallback = isCustomerRoot.value ? 'followups' : isProduct.value ? '__overview' : data.value.sections[0]?.key || ''
  activeTab.value = key === 'operation_logs' ? '__operation_logs' : valid ? key : fallback
  if (!valid && key !== undefined) void router.replace({ path: route.path, query: { ...route.query, tab: fallback }, hash: route.hash })
}
async function selectSection(key) {
  if (isRoot.value) await router.replace({ path: route.path, query: { ...route.query, tab: key === '__operation_logs' ? 'operation_logs' : key }, hash: route.hash })
  activeTab.value = key
}
const isSkuSection = computed(() => currentEntity.value === 'products' && activeSection.value?.entity === 'skus')
const visibleSectionRows = computed(() => {
  const rows = activeSection.value?.rows || []
  if (!isSkuSection.value || !skuQuery.value.trim()) return rows
  const query = skuQuery.value.trim().toLowerCase()
  return rows.filter(row => [row.sku, row.display_name_cn, row.sales_model, row.specification, row.active ? '启用' : '已停用'].some(value => String(value || '').toLowerCase().includes(query)))
})
const canBulkDeleteSku = computed(() => /超级管理员|管理员/.test(operatorRole.value))
const selectableSkuRows = computed(() => visibleSectionRows.value.filter(row => row.active))
const allSkuSelected = computed(() => Boolean(selectableSkuRows.value.length) && selectableSkuRows.value.every(row => selectedSkuIds.value.includes(row.id)))
const selectedActiveSkuIds = computed(() => selectableSkuRows.value.filter(row => selectedSkuIds.value.includes(row.id)).map(row => row.id))
const selectedInactiveSkuIds = computed(() => visibleSectionRows.value.filter(row => !row.active && selectedSkuIds.value.includes(row.id)).map(row => row.id))
const isFollowUpDetail = computed(() => currentEntity.value === 'follow-ups')
const followUpInfo = computed(() => Object.fromEntries((data.value?.info || []).map(item => [item[0], item[1]])))
const followUpCustomer = computed(() => data.value?.sections?.find(section => section.key === 'customer')?.rows?.[0] || null)
const relationCustomerId = computed(() => relationContext().customer)
const hasRelationCustomerId = computed(() => {
  const customerId = Number(relationCustomerId.value)
  return Number.isSafeInteger(customerId) && customerId > 0
})
const followUpContact = computed(() => data.value?.sections?.find(section => section.key === 'contact')?.rows?.[0] || null)
const followUpCreatedAt = computed(() => {
  const parts = String(data.value?.subtitle || '').split(' · ')
  return parts.slice(1).join(' · ') || '—'
})
const followUpTags = computed(() => [data.value?.badge, followUpInfo.value['下次跟进'] ? '计划跟进' : '待安排'].filter(Boolean))
const followUpAttachments = computed(() => data.value?.attachments || [])
const isOperationLogTab = computed(() => activeTab.value === '__operation_logs')
const auditEntityName = entity => `crm.${({
  customers: 'customer', suppliers: 'supplier', contacts: 'contact', 'follow-ups': 'followup', categories: 'productcategory',
  products: 'product', skus: 'sku', 'sku-versions': 'skuversion', 'product-parameters': 'productparameter', 'product-certificates': 'productcertificate',
  quotes: 'quote', orders: 'order', 'purchase-orders': 'purchaseorder', transactions: 'transaction', 'inventory-movements': 'inventorymovement',
  'packaging-templates': 'packagingtemplate', 'sku-packaging-profiles': 'skupackagingprofile', 'supplier-skus': 'suppliersku',
  'category-attributes': 'categoryattribute', 'organization-units': 'organizationunit', positions: 'position', employees: 'employeeprofile',
  'access-roles': 'accessrole', 'role-permissions': 'rolepermission', 'payment-plans': 'paymentplan', 'contract-changes': 'contractchangerequest', shipments: 'shipment',
}[entity] || String(entity).replaceAll('-', ''))}`

async function refreshSkuManagement() {
  try {
    data.value = (await api.get(`/context/${currentEntity.value}/${currentId.value}/`)).data
    emit('changed')
  } catch (e) { console.warn('产品摘要刷新失败', e) }
}
async function load(entity = currentEntity.value, id = currentId.value) {
  loading.value = true; error.value = ''
  try {
    const [contextResponse, movementResponse] = await Promise.all([
      api.get(`/context/${entity}/${id}/`, { params: entity === 'products' && showInactiveSkus.value ? { include_inactive: '1' } : {} }),
      entity === 'inventory-movements' ? api.get(`/inventory-movements/${id}/`) : Promise.resolve(null),
      loadOperationLogs(entity, id),
    ])
    data.value = contextResponse.data
    movementRecord.value = movementResponse?.data || null
    currentEntity.value = entity; currentId.value = id
    activeTab.value = entity === 'products' ? '__overview' : data.value.sections[0]?.key || ''
    restoreCustomerTab()
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
async function loadOperationLogs(entity = currentEntity.value, id = currentId.value) {
  operationLogsLoading.value = true
  try {
    operationLogs.value = listData(await api.get('/operation-logs/', { params: { entity: auditEntityName(entity), object_id: id, ordering: '-created_at' } }))
  } catch {
    operationLogs.value = []
  } finally { operationLogsLoading.value = false }
}
async function drill(row) {
  const targetEntity = row._target_entity || activeSection.value?.entity
  const targetId = row._target_id || row.id
  if (!targetEntity || !targetId) return
  const workbench = relationWorkbenchLocation(targetEntity, targetId, currentEntity.value, activeTab.value, detailReturnPath())
  if (workbench) { await router.push(workbench); return }
  if (isProduct.value) { productDrawer.value = { entity: targetEntity, id: targetId }; return }
  stack.value.push({ entity: currentEntity.value, id: currentId.value, title: data.value.title })
  await load(targetEntity, targetId)
}
async function back() {
  const previous = stack.value.pop()
  if (previous) await load(previous.entity, previous.id)
}
function sectionRowId(key) {
  const row = data.value?.sections?.find(section => section.key === key)?.rows?.[0]
  return row?._target_id || row?.id || ''
}
function openWhatsApp() {
  const phone = String(followUpContact.value?.phone || '').replace(/\D/g, '')
  if (phone) window.open(`https://wa.me/${phone}`, '_blank', 'noopener')
}
async function deleteFollowUp() {
  if (!isFollowUpDetail.value || !await confirmDialog({ title: '确认删除跟进记录', message: '确定删除这条跟进记录吗？此操作无法撤销。', confirmText: '确认删除', danger: true })) return
  try {
    await api.delete(`/follow-ups/${currentId.value}/`)
    emit('changed')
    if (stack.value.length) await back()
    else emit('close')
  } catch (e) {
    error.value = e.message || '删除跟进记录失败'
  }
}
function relationContext() {
  const root = data.value?.entity
  const ids = { customer: '', contact: '', supplier: '', order: '', purchase_order: '', product: '', sku: '', quote: '' }
  const id = currentId.value
  if (root === 'customers') ids.customer = id
  if (root === 'contacts') { ids.contact = id; ids.customer = sectionRowId('company') }
  if (root === 'suppliers') ids.supplier = id
  if (root === 'products') ids.product = id
  if (root === 'skus') { ids.sku = id; ids.product = sectionRowId('product') }
  if (root === 'quotes') { ids.quote = id; ids.customer = sectionRowId('customer') }
  if (root === 'orders') { ids.order = id; ids.customer = sectionRowId('customer') }
  if (root === 'purchase-orders') { ids.purchase_order = id; ids.supplier = sectionRowId('supplier'); ids.order = sectionRowId('order') }
  if (root === 'follow-ups') { ids.customer = sectionRowId('customer'); ids.contact = sectionRowId('contact') }
  if (root === 'transactions') { ids.customer = sectionRowId('customer'); ids.supplier = sectionRowId('supplier'); ids.order = sectionRowId('order'); ids.purchase_order = sectionRowId('purchase-order') }
  if (root === 'inventory-movements') { ids.sku = sectionRowId('sku'); ids.product = sectionRowId('product'); ids.order = sectionRowId('order') }
  return ids
}
function openQuoteForCustomer(customerId) {
  const rawId = String(customerId ?? '').trim()
  if (!/^\d+$/.test(rawId)) return
  const id = Number(rawId)
  if (!Number.isSafeInteger(id) || id <= 0) return
  quickCreate.value = { entity: 'quotes', query: { customer: id } }
}
function relationQuery(section) {
  const ids = relationContext()
  const entity = section?.entity
  if (entity === 'contacts') return ids.customer ? { customer: ids.customer } : {}
  if (entity === 'follow-ups') return Object.fromEntries([['customer', ids.customer], ['contact', ids.contact]].filter(([, value]) => value))
  if (entity === 'orders' || entity === 'quotes') return Object.fromEntries([['customer', ids.customer], ['quote', entity === 'orders' ? ids.quote : ''], ['sku', entity === 'orders' ? ids.sku : ''], ['product', ids.product]].filter(([, value]) => value))
  if (entity === 'purchase-orders') return Object.fromEntries([['supplier', ids.supplier], ['order', ids.order]].filter(([, value]) => value))
  if (entity === 'transactions') return Object.fromEntries([['customer', ids.customer], ['supplier', ids.supplier], ['order', ids.order], ['purchase_order', ids.purchase_order]].filter(([, value]) => value))
  if (entity === 'inventory-movements') return Object.fromEntries([['sku', ids.sku], ['product', ids.product], ['order', ids.order]].filter(([, value]) => value))
  if (['skus', 'product-parameters', 'product-certificates'].includes(entity)) return ids.product ? { product: ids.product } : {}
  return {}
}
function createLabel(section) {
  const labels = { contacts: '联系人', orders: '订单', quotes: '报价', 'purchase-orders': '采购单', 'follow-ups': '跟进记录', transactions: '财务流水', 'inventory-movements': '库存流水', skus: 'SKU', 'product-parameters': '产品参数', 'product-certificates': '产品证书' }
  return `新增${labels[section?.entity] || section?.title || '记录'}`
}
function openCustomerFollowUp() {
  quickCreate.value = { entity: 'follow-ups', query: { customer: currentId.value } }
}
const managementTarget = computed(() => documentEntities.has(currentEntity.value)
  ? relationWorkbenchLocation(currentEntity.value, currentId.value, '', '', detailReturnPath())
  : isMovementDetail.value ? { path: '/inventory-movements', query: route.query.sku ? { sku: route.query.sku } : {} }
  : `/${currentEntity.value}`)
const managementLabel = computed(() => currentEntity.value === 'quotes' ? '打开报价工作台' : currentEntity.value === 'orders' ? '打开订单工作台' : currentEntity.value === 'purchase-orders' ? '打开采购工作台' : isMovementDetail.value ? '返回库存流水' : '打开管理页')
function managementNavigation() {
  if (!documentEntities.has(currentEntity.value) && !isMovementDetail.value) emit('close')
}
function openRelatedCreate() {
  if (!canManage.value) return
  const query = relationQuery(activeSection.value)
  if (activeSection.value.entity === 'purchase-orders') {
    router.push({ path: '/purchase-orders', query: { create: '1', ...query, returnTo: detailReturnPath() } })
    return
  }
  quickCreate.value = { entity: activeSection.value.entity, query }
}
function detailReturnPath() {
  if (!isRoot.value) return route.fullPath
  return router.resolve({ path: route.path, query: { ...route.query, detail: String(props.id), tab: activeTab.value === '__operation_logs' ? 'operation_logs' : activeTab.value }, hash: route.hash }).fullPath
}
function openSkuCreate() { activeTab.value = 'skus'; skuCreateOpen.value = true }
async function skuCreated() {
  skuCreateOpen.value = false
  const previousTab = activeTab.value
  await load()
  if (data.value?.sections.some(section => section.key === previousTab)) activeTab.value = previousTab
}
async function relatedSaved() {
  const previousTab = activeTab.value
  quickCreate.value = null
  await load()
  if (data.value?.sections.some(section => section.key === previousTab)) activeTab.value = previousTab
  emit('changed')
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
  if (!ids.length || !await confirmDialog({ title: '确认停用 SKU', message: `确定停用选中的 ${ids.length} 个 SKU 吗？停用后将默认从 ERP 列表隐藏。`, confirmText: '确认停用', danger: true })) return
  try {
    await Promise.all(ids.map(id => api.patch(`/skus/${id}/`, { active: false })))
    selectedSkuIds.value = []
    await load()
  } catch (e) { error.value = e.message || 'SKU 停用失败' }
}
async function reactivateSelectedSkus() {
  const ids = selectedInactiveSkuIds.value
  if (!ids.length || !await confirmDialog({ title: '确认重新启用 SKU', message: `确定重新启用选中的 ${ids.length} 个 SKU 吗？`, confirmText: '确认启用' })) return
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
function format(value, type) {
  if (value === null || value === undefined || value === '') return '—'
  if (type === 'money') return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (type === 'rmb') return `¥ ${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
function formatAttachmentSize(value) {
  const size = Number(value || 0)
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
function valueClass(type, value) { return { 'ctx-status': type === 'status', 'ctx-money': ['money', 'rmb'].includes(type), 'inactive-status': type === 'sku-active' && !value, positive: type === 'signed' && Number(value) > 0, negative: type === 'signed' && Number(value) < 0 } }

watch(() => [props.entity, props.id], () => { stack.value = []; currentEntity.value = props.entity; currentId.value = props.id; selectedSkuIds.value = []; skuMultiSelect.value = false; load() })
watch(() => props.refreshKey, () => load())
watch(() => route.query.tab, restoreCustomerTab)
watch(activeTab, key => {
  if (isProduct.value && isRoot.value && route.path === '/products' && !loading.value && route.query.tab !== key) {
    void router.replace({ path: route.path, query: { ...route.query, tab: key }, hash: route.hash })
  }
})
watch(activeTab, () => { selectedSkuIds.value = []; skuQuery.value = ''; skuMultiSelect.value = false })
onMounted(async () => {
  await Promise.all([
    load(),
    api.get('/session/current-operator/').then(response => { operatorRole.value = response.data.role || ''; auditEnabled.value = Boolean(response.data.audit_log_enabled) }).catch(() => { operatorRole.value = ''; auditEnabled.value = false }),
  ])
})
</script>

<template>
  <div class="modal-backdrop detail-backdrop" :class="{ 'follow-up-detail-backdrop': isFollowUpDetail, 'product-detail-backdrop': isProduct }" @mousedown.self="emit('close')">
    <article class="detail-modal" :class="{ 'follow-up-detail-modal': isFollowUpDetail, 'product-detail-modal': isProduct, 'customer-detail-root': isCustomerRoot, 'movement-detail': isMovementDetail }" :aria-label="isFollowUpDetail ? '跟进详情' : isMovementDetail ? '库存流水详情' : isCustomerRoot ? '客户详情' : '关联详情'">
      <div v-if="loading" class="detail-loading"><div class="spinner" /><span>正在整理关联数据...</span></div>
      <div v-else-if="error" class="detail-error"><strong>详情加载失败</strong><p>{{ error }}</p><button class="btn btn-secondary" @click="load()">重试</button></div>
      <template v-else-if="data">
        <template v-if="isFollowUpDetail">
          <header class="follow-up-hero">
            <div class="follow-up-hero-nav">
              <button class="follow-up-return" @click="stack.length ? back() : emit('close')"><ArrowLeft :size="17" /> {{ stack.length ? `返回 ${stack[stack.length - 1].title}` : '返回列表' }}</button>
              <span class="follow-up-hero-label">跟进详情</span>
              <div class="follow-up-actions">
                <button class="follow-up-action" @click="emit('edit', { entity: currentEntity, id: currentId })"><Pencil :size="15" /> 编辑</button>
                <button class="follow-up-action" @click="deleteFollowUp"><Trash2 :size="15" /> 删除</button>
                <button class="follow-up-action" @click="stack.length ? back() : emit('close')"><ArrowLeft :size="15" /> 返回</button>
                <button v-if="hasRelationCustomerId" class="follow-up-action" @click="openQuoteForCustomer(relationCustomerId)"><Plus :size="15" /> 新建报价</button>
                <button class="follow-up-action primary" :disabled="!followUpContact?.phone" @click="openWhatsApp"><ExternalLink :size="15" /> 发送 WhatsApp</button>
              </div>
            </div>
            <div class="follow-up-hero-identity">
              <div><span>跟进记录 · 创建时间：{{ followUpCreatedAt }}</span><h1>跟进记录详情</h1><h2>{{ data.title }}</h2></div>
              <span class="follow-up-channel">{{ data.badge }}</span>
            </div>
            <div class="follow-up-summary">
              <div><small>跟进对象</small><strong>{{ followUpCustomer?.name || '—' }}<template v-if="followUpCustomer?.country">（{{ followUpCustomer.country }}）</template></strong></div>
              <div><small>跟进方式 / 主题</small><strong>{{ data.title }}</strong><span>{{ data.badge }}</span></div>
              <div><small>跟进结果</small><div class="follow-up-summary-result"><i class="summary-dot" /><div v-html="richText(followUpInfo['客户回复 / 客户疑问'] || '待记录')" /></div></div>
              <div><small>下次跟进时间</small><strong>{{ followUpInfo['下次跟进'] || '未安排' }}</strong></div>
              <div><small>负责人</small><strong><span class="owner-avatar">{{ String(followUpInfo['跟进人'] || '—').slice(0, 1) }}</span>{{ followUpInfo['跟进人'] || '—' }}</strong></div>
            </div>
          </header>
          <main class="follow-up-detail-content">
            <div class="follow-up-detail-main-column">
              <section class="follow-up-card follow-up-content-card">
                <div class="follow-up-card-head"><h3><Rows3 :size="16" /> 跟进内容</h3><span>本次沟通记录</span></div>
                <div class="follow-up-richtext" v-html="richText(followUpInfo['跟进记录 / 解决方案'])" />
                <div v-if="followUpInfo['下一步'] && followUpInfo['下一步'] !== '—'" class="follow-up-next-action"><strong>下一步计划</strong><p>{{ followUpInfo['下一步'] }}</p></div>
              </section>
              <section class="follow-up-card follow-up-feedback-card"><div class="follow-up-card-head"><h3><Rows3 :size="16" /> 客户反馈 / 问题</h3></div><div class="follow-up-richtext" v-html="richText(followUpInfo['客户回复 / 客户疑问'] || '暂无客户反馈。')" /></section>
              <section class="follow-up-card follow-up-attachments-card">
                <div class="follow-up-card-head"><h3><Paperclip :size="16" /> 附件</h3><span>{{ followUpAttachments.length }} 个附件</span></div>
                <div v-if="followUpAttachments.length" class="follow-up-attachment-list">
                  <a v-for="attachment in followUpAttachments" :key="attachment.id" class="follow-up-attachment-item" :href="attachment.url || attachment.file" target="_blank" rel="noreferrer" download>
                    <img v-if="attachment.content_type?.startsWith('image/')" :src="attachment.url || attachment.file" :alt="attachment.name" loading="lazy" />
                    <Paperclip v-else :size="18" />
                    <span><strong>{{ attachment.name }}</strong><small>{{ formatAttachmentSize(attachment.size) }}</small></span>
                    <ExternalLink :size="14" />
                  </a>
                </div>
                <div v-else class="follow-up-attachments-empty"><Paperclip :size="18" /><span>暂无附件</span></div>
              </section>
            </div>
            <aside class="follow-up-detail-side-rail">
              <section class="follow-up-card follow-up-timeline-card">
                <div class="follow-up-card-head"><h3><ArrowLeft :size="16" /> 跟进记录时间线</h3><span>{{ followUpInfo['跟进人'] || '—' }}</span></div>
                <div class="follow-up-timeline">
                  <div class="follow-up-timeline-item current"><i /><div><strong>本次跟进（最新）</strong><p>{{ data.title }}</p><span class="timeline-tag success">已记录</span></div><time>{{ followUpCreatedAt }}</time></div>
                  <div v-if="followUpInfo['下次跟进'] && followUpInfo['下次跟进'] !== '—'" class="follow-up-timeline-item planned"><i /><div><strong>下一次跟进（计划中）</strong><p>{{ followUpInfo['下一步'] || '待确认下一步动作' }}</p><span class="timeline-tag planned-tag">计划中</span></div><time>{{ followUpInfo['下次跟进'] }}</time></div>
                </div>
              </section>
              <section class="follow-up-card follow-up-tags-card"><div class="follow-up-card-head"><h3><CheckSquare :size="16" /> 标签</h3></div><div class="follow-up-tags"><span v-for="tag in followUpTags" :key="tag">{{ tag }}</span></div></section>
              <section class="follow-up-card follow-up-related-card"><div class="follow-up-card-head"><h3><ExternalLink :size="16" /> 相关数据</h3></div><button v-if="followUpCustomer" class="follow-up-related-row" @click="drill(followUpCustomer)"><span class="related-icon customer-icon">▦</span><span><strong>{{ followUpCustomer.name }}</strong><small>客户 · {{ followUpCustomer.code || '—' }}</small></span><ChevronRight :size="16" /></button><button v-if="followUpContact" class="follow-up-related-row" @click="drill(followUpContact)"><span class="related-icon contact-icon">●</span><span><strong>{{ followUpContact.name }}</strong><small>{{ followUpContact.title || '联系人' }}</small></span><ChevronRight :size="16" /></button></section>
              <OperationLogPanel :logs="operationLogs" :loading="operationLogsLoading" :enabled="auditEnabled" />
            </aside>
          </main>
        </template>
        <template v-else>
        <header class="detail-header">
          <div class="detail-nav">
            <div class="detail-nav-start">
              <button v-if="!isProduct" class="detail-close" aria-label="关闭详情" @click="emit('close')"><X :size="19" /><span>关闭</span></button>
              <button v-if="stack.length" class="detail-back" @click="back"><ArrowLeft :size="17" /> 返回 {{ stack[stack.length - 1].title }}</button>
              <span v-if="currentEntity === 'follow-ups'">跟进详情</span>
              <span v-else-if="isProduct">产品管理 / 产品详情</span><span v-else-if="isMovementDetail">库存流水详情</span><span v-else-if="isCustomerRoot">客户详情</span><span v-else-if="!stack.length">关联详情</span>
            </div>
            <div class="detail-actions">
              <button v-if="isRoot && currentEntity === 'customers'" class="btn btn-secondary" @click="openCustomerFollowUp"><Plus :size="14" /> 新增跟进</button>
              <button v-if="isRoot && currentEntity === 'customers' && hasRelationCustomerId" class="btn btn-secondary" @click="openQuoteForCustomer(relationCustomerId)"><Plus :size="14" /> 新建报价</button>
              <button v-if="isRoot && currentEntity !== 'inventory-movements'" class="btn btn-secondary" @click="emit('edit')"><Pencil :size="14" /> {{ currentEntity === 'customers' ? '编辑客户' : '编辑主档' }}</button>
              <RouterLink v-else-if="!isMovementDetail && hasManagement(currentEntity)" class="btn btn-secondary" :to="managementTarget" @click="managementNavigation"><ExternalLink :size="14" /> {{ managementLabel }}</RouterLink>
              <button v-if="isProduct" class="detail-close" aria-label="关闭详情" @click="emit('close')"><X :size="19" /><span>关闭</span></button>
            </div>
          </div>
          <div class="detail-identity"><div><span class="detail-subtitle">{{ data.subtitle }}</span><h2>{{ data.title }}</h2><small v-if="isCustomerRoot && data.info?.find(item => item[0] === '负责人')?.[1]" class="detail-owner">负责人：{{ data.info.find(item => item[0] === '负责人')[1] }}</small><small v-if="isMovementDetail && movementRecord" class="movement-identity">{{ movementRecord.sku_code || detailInfo.find(item => item[0] === 'SKU')?.[1] }} · {{ sourceLabels[movementSource(movementRecord)] }} · {{ movementStatus(movementRecord) }}</small></div><span class="detail-badge">{{ data.badge }}</span></div>
          <div v-if="data.metrics.length" class="detail-metrics"><div v-for="metric in data.metrics" :key="metric[0]"><small>{{ metric[0] }}</small><strong>{{ format(metric[1], metric[2]) }}</strong></div></div>
        </header>

        <component :is="isProduct ? ProductWorkspace : 'div'" :class="{ 'detail-content': !isProduct }" :data="data" :product-id="currentId" @changed="refreshSkuManagement" v-model:active-tab="activeTab" @drill="drill" @create-sku="openSkuCreate">
          <section v-if="!isProduct" class="detail-info"><h3>基础信息</h3><div class="info-grid"><div v-for="item in detailInfo" :key="item[0]"><small>{{ item[0] }}</small><div v-if="item[2] === 'richtext'" class="richtext-view" v-html="richText(item[1])" /><span v-else>{{ item[1] }}</span><small v-if="currentEntity === 'customers' && item[0] === '下次跟进'" class="computed-field-note">随最新跟进自动更新</small></div></div></section>
          <div :class="{ 'sku-create-workspace': isSkuSection && skuCreateOpen }">
          <SKUPage v-if="isSkuSection && skuCreateOpen" embedded inline :initial-product="currentId" @close="skuCreateOpen = false" @saved="skuCreated" />
          <section v-if="!isSkuSection" class="relation-area">
            <div class="relation-top"><div><h3>{{ isProduct ? activeSection?.title || '操作日志' : currentEntity === 'customers' ? '业务记录' : isMovementDetail ? '关联记录' : '关联数据' }}</h3><p v-if="currentEntity !== 'customers' && !isMovementDetail">点击记录查看详情</p></div><div class="relation-actions"><button v-if="isSkuSection && canBulkDeleteSku" class="manage-link" :class="{ 'multi-select-active': skuMultiSelect }" @click="toggleSkuMultiSelect"><CheckSquare :size="13" /> {{ skuMultiSelect ? '取消多选' : '多选' }}</button><button v-if="isSkuSection && canBulkDeleteSku && skuMultiSelect && selectedActiveSkuIds.length" class="manage-link danger-link" @click="deactivateSelectedSkus"><Trash2 :size="13" /> 停用 {{ selectedActiveSkuIds.length }} 个 SKU</button><button v-if="isSkuSection && canBulkDeleteSku && skuMultiSelect && selectedInactiveSkuIds.length" class="manage-link restore-link" @click="reactivateSelectedSkus"><CheckSquare :size="13" /> 重新启用 {{ selectedInactiveSkuIds.length }} 个 SKU</button><button v-if="isSkuSection" class="manage-link" :class="{ 'inactive-toggle': showInactiveSkus }" @click="toggleInactiveSkus"><CheckSquare :size="13" /> {{ showInactiveSkus ? '隐藏已停用 SKU' : '显示已停用 SKU' }}</button><button v-if="isSkuSection" class="manage-link" @click="openSkuCreate"><Plus :size="13" /> 新增 SKU</button><button v-else-if="showRelatedCreate" class="manage-link" @click="openRelatedCreate"><Plus :size="13" /> {{ createLabel(activeSection) }}</button></div></div>
              <label v-if="isSkuSection" class="sku-context-search"><Search :size="16" /><input v-model.trim="skuQuery" placeholder="搜索中文名称、销售型号、SKU Code 或规格..." /><span v-if="skuQuery">{{ visibleSectionRows.length }} / {{ activeSection.rows.length }}</span></label>
            <div v-if="!isProduct" class="detail-tabs"><button v-for="section in data.sections" :key="section.key" :class="{ active: activeTab === section.key }" @click="selectSection(section.key)">{{ currentEntity === 'customers' && section.key === 'orders' ? '订单记录' : section.title }} <span>{{ section.rows.length }}</span></button><button :class="{ active: isOperationLogTab }" @click="selectSection('__operation_logs')">{{ isMovementDetail ? '流水操作日志' : '操作日志' }} <span>{{ operationLogs.length }}</span></button></div>
            <OperationLogPanel v-if="isOperationLogTab" :title="isMovementDetail ? '流水操作日志' : '操作日志'" :logs="operationLogs" :loading="operationLogsLoading" :enabled="auditEnabled" />
            <div v-else-if="activeSection" class="context-table-wrap">
              <div v-if="!visibleSectionRows.length" class="context-empty"><Rows3 :size="27" /><strong>{{ isSkuSection && skuQuery ? '未找到匹配的 SKU' : currentEntity === 'customers' ? ({ followups: '暂无跟进记录', quotes: '暂无报价', orders: '暂无订单', contacts: '暂无联系人', sold_items: '暂无成交商品记录', cash: '暂无财务流水' }[activeSection.key] || `暂无${activeSection.title}`) : `暂无${activeSection.title}` }}</strong><p v-if="currentEntity !== 'customers' && !isMovementDetail && canManage">{{ isSkuSection && skuQuery ? '请调整关键词后重试。' : '点击右上角新增关联记录。' }}</p></div>
              <table v-else class="context-table" :class="{ 'followup-table': activeSection.key === 'followups', 'sku-context-table': isSkuSection, 'multi-select-table': skuMultiSelect }"><thead><tr><th v-if="isSkuSection && canBulkDeleteSku && skuMultiSelect" class="selection-cell"><label class="selection-check"><input type="checkbox" :checked="allSkuSelected" @click.stop @change="toggleAllSkuSelection" /><CheckSquare :size="15" /></label></th><th v-for="column in activeSection.columns" :key="column[0]">{{ column[1] }}</th><th></th></tr></thead><tbody>
                <tr v-for="(row,index) in visibleSectionRows" :key="row.id || index" :class="{ 'inactive-row': isSkuSection && !row.active }" @click="!skuMultiSelect && drill(row)"><td v-if="isSkuSection && canBulkDeleteSku && skuMultiSelect" class="selection-cell"><label class="selection-check" :class="{ restore: !row.active }" @click.stop><input type="checkbox" :checked="selectedSkuIds.includes(row.id)" @change="toggleSkuSelection(row.id)" /><CheckSquare :size="15" /></label></td><td v-for="(column,colIndex) in activeSection.columns" :key="column[0]" :class="{ primary: colIndex === 0, 'excerpt-cell': column[2] === 'excerpt' }"><CertificateExpiryBadge v-if="column[2] === 'certificate-expiry'" :certificate="row" /><span v-else :class="valueClass(column[2], row[column[0]])" :title="column[2] === 'excerpt' ? String(row[column[0]] || '') : undefined">{{ format(row[column[0]], column[2]) }}</span></td><td class="drill-cell"><button v-if="!skuMultiSelect" class="context-drill" :aria-label="`查看 ${row.sku || '记录'} 详情`" @click.stop="drill(row)"><ChevronRight :size="17" /></button></td></tr>
              </tbody></table>
            </div>
          </section>
          </div>
        </component>
        </template>
      </template>
    </article>
    <EntityDetailModal v-if="productDrawer" class="product-context-drawer" :entity="productDrawer.entity" :id="productDrawer.id" @close="productDrawer = null" @changed="refreshSkuManagement" />
    <RelatedCreateModal v-if="quickCreate" :entity="quickCreate.entity" :query="quickCreate.query" @close="quickCreate = null" @saved="relatedSaved" />

  </div>
</template>

<style scoped>
.sku-create-workspace{display:grid;grid-template-columns:minmax(0,1fr);gap:16px;align-items:start;min-width:0}
.sku-create-workspace>.relation-area{min-width:0;margin:0}
.sku-create-workspace .context-table-wrap{max-height:62vh;overflow:auto}
.sku-create-workspace .context-table th{position:sticky;top:0;z-index:1}
@media(max-width:800px){.sku-create-workspace .context-table-wrap{max-height:35vh}}

.detail-backdrop{inset:0 0 0 248px;z-index:25;place-items:stretch end;padding:0;background:#0b221d66;backdrop-filter:blur(2px)}.detail-modal{height:100vh;width:min(1100px,100%);background:#f6f8f5;box-shadow:-24px 0 70px #06191452;overflow:auto;overscroll-behavior:contain;will-change:transform}.detail-loading,.detail-error{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#71817b}.detail-error strong{color:#9d4444}.detail-error p{font-size:var(--text-body)}.detail-header{background:#123c36;color:#fff;padding:20px 28px 24px;position:relative;overflow:hidden}.detail-header:after{content:'';position:absolute;width:300px;height:300px;border:60px solid #ffffff08;border-radius:50%;right:-80px;top:-140px}.detail-nav,.detail-nav-start{display:flex;align-items:center}.detail-nav{justify-content:space-between;position:relative;z-index:1;font-size:var(--text-body);color:#91b6aa;text-transform:uppercase;letter-spacing:.12em}.detail-nav-start{gap:10px}.detail-back{border:0;background:transparent;color:#b6d3ca;display:flex;gap:7px;align-items:center;padding:0}.detail-actions{display:flex;gap:8px;align-items:center}.detail-actions .btn{padding:7px 11px;font-size:var(--text-body);text-transform:none;letter-spacing:0;text-decoration:none}.detail-close{width:32px;height:32px;border:1px solid #ffffff28;background:#ffffff12;color:white;border-radius:8px;display:grid;place-items:center}.detail-identity{display:flex;gap:20px;align-items:end;justify-content:space-between;margin-top:23px;position:relative;z-index:1}.detail-subtitle{font-size:var(--text-caption);color:#9cc0b5}.detail-identity h2{font-size:var(--text-page);margin:5px 0 0}.detail-badge{background:#ffffff14;border:1px solid #ffffff22;padding:6px 10px;border-radius:20px;font-size:var(--text-secondary)}.detail-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;background:#ffffff18;margin-top:22px;border-radius:10px;overflow:hidden;position:relative;z-index:1}.detail-metrics>div{padding:13px 15px;background:#18473f}.detail-metrics small,.detail-metrics strong{display:block}.detail-metrics small{font-size:var(--text-caption);color:#93b7ad}.detail-metrics strong{font-size:var(--text-metric);margin-top:5px}.detail-content{padding:22px 25px 40px}.detail-info,.relation-area{background:white;border:1px solid #e1e7e3;border-radius:13px;padding:19px;margin-bottom:15px}.detail-info h3,.relation-top h3{font-size:var(--text-section);margin:0}.info-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px 22px;margin-top:16px}.info-grid small,.info-grid span{display:block}.info-grid small{font-size:var(--text-caption);color:#8a9792;margin-bottom:4px}.info-grid span{font-size:var(--text-body);color:#3d5049;white-space:pre-wrap;word-break:break-word}.richtext-view{font-size:13px;color:#3d5049;word-break:break-word}.richtext-view :deep(p){margin:0 0 4px}.richtext-view :deep(ul),.richtext-view :deep(ol){margin:3px 0;padding-left:18px}.relation-top{display:flex;justify-content:space-between;align-items:center}.relation-top p{font-size:var(--text-caption);color:#8a9792;margin:4px 0 0}.manage-link{border:0;font-size:var(--text-body);color:#245e50;text-decoration:none;display:flex;align-items:center;gap:5px;background:#eaf3ef;padding:7px 10px;border-radius:7px}.detail-tabs{display:flex;gap:4px;margin:18px -19px 0;padding:0 19px;border-bottom:1px solid #e6ebe8;overflow:auto}.detail-tabs button{border:0;background:transparent;padding:10px 12px;color:#75837e;font-size:var(--text-body);white-space:nowrap;border-bottom:2px solid transparent}.detail-tabs button.active{color:#174c41;border-bottom-color:#1f6657;font-weight:700}.detail-tabs button span{background:#edf1ef;padding:2px 5px;border-radius:10px;margin-left:4px;font-size:var(--text-body)}.context-table-wrap{overflow:auto;margin:0 -19px -19px}.context-table{width:100%;min-width:650px;border-collapse:collapse}.context-table th{font-size:var(--text-body);text-transform:uppercase;letter-spacing:.07em;color:#84918d;text-align:left;background:#f8faf8;padding:10px 13px}.context-table td{font-size:var(--text-body);color:#586660;padding:12px 13px;border-top:1px solid #edf0ee}.context-table td.primary{font-weight:600;color:#253a33}.context-table tr{cursor:pointer}.context-table tbody tr:hover{background:#f5f9f7}.context-table td:last-child{width:30px;color:#9ba7a2}.ctx-status{background:#e6f1ec;color:#286851;border-radius:20px;padding:3px 7px}.ctx-money{font-variant-numeric:tabular-nums;font-weight:600}.positive{color:#287258;font-weight:700}.negative{color:#b44f4f;font-weight:700}.context-empty{text-align:center;padding:42px;color:#99a5a0}.context-empty strong,.context-empty p{display:block}.context-empty strong{font-size:var(--text-body);color:#586963;margin-top:8px}.context-empty p{font-size:var(--text-caption);margin:4px 0}.detail-actions .btn-secondary{background:#ffffff12;color:white;border-color:#ffffff28}
/* 同类详情模块的分区字号：顶部 +1px，基础信息与关联数据 +2px。 */
.detail-modal{font-size:var(--text-body)}
.detail-nav,.detail-actions .btn{font-size:var(--text-body)}
.detail-subtitle{font-size:var(--text-caption)}
.detail-badge{font-size:var(--text-secondary)}
.detail-identity h2{font-size:var(--text-page)}.detail-metrics small{font-size:var(--text-caption)}.detail-metrics strong{font-size:var(--text-metric)}
.detail-info h3,.relation-top h3{font-size:var(--text-section)}.info-grid small{font-size:var(--text-caption)}.info-grid span,.richtext-view{font-size:var(--text-body)}
.relation-top p{font-size:var(--text-caption)}.manage-link,.detail-tabs button{font-size:var(--text-body)}.detail-tabs button span{font-size:var(--text-secondary)}
.context-table th{font-size:var(--text-body)}.context-table td{font-size:var(--text-body)}.context-empty strong{font-size:var(--text-section)}.context-empty p{font-size:var(--text-caption)}
.followup-table{table-layout:fixed;min-width:900px}.followup-table th:nth-child(1){width:105px}.followup-table th:nth-child(2){width:140px}.followup-table th:nth-child(3),.followup-table th:nth-child(4){width:220px}.followup-table th:nth-child(5){width:72px}.followup-table th:nth-child(6){width:105px}.followup-table th:last-child{width:34px}.excerpt-cell span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:980px){.detail-backdrop{inset:0;z-index:60}}
@media(max-width:700px){.detail-modal{width:100vw}.detail-header{padding:16px 17px 20px}.detail-identity h2{font-size:var(--text-page)}.detail-metrics{grid-template-columns:repeat(2,1fr)}.detail-content{padding:12px}.detail-info,.relation-area{padding:15px}.info-grid{grid-template-columns:repeat(2,1fr)}.detail-tabs{margin-left:-15px;margin-right:-15px;padding:0 15px}.context-table-wrap{margin-left:-15px;margin-right:-15px}.detail-actions .btn{display:none}}
.restore-link{background:#e9f5ef;color:#27725a}.selection-check.restore{color:#d27878}
.sku-context-search{display:flex;align-items:center;gap:8px;width:min(360px,100%);margin:13px 0 -4px;color:#82928b;border:1px solid #dce6e1;border-radius:8px;padding:0 10px;background:#fbfdfc}.sku-context-search input{min-width:0;flex:1;border:0;outline:0;padding:9px 0;background:transparent;color:#27463c;font-size:var(--text-body)}.sku-context-search span{font-size:var(--text-body);color:#6e8d82;white-space:nowrap}
.drill-cell{width:52px!important;padding:0!important}.context-drill{width:52px;height:100%;min-height:45px;border:0;background:transparent;display:grid;place-items:center;color:#8a9d96;cursor:pointer}.context-drill:hover{background:#eaf3ef;color:#17604f}.context-drill:focus-visible{outline:3px solid #bcdace;outline-offset:-3px}
.multi-select-active{background:#1f6657!important;color:#fff!important}.multi-select-table tbody tr{cursor:default}.multi-select-table .drill-cell{width:30px!important}
.product-detail-modal>.detail-header{padding:20px 30px 24px}.product-context-drawer{left:0;z-index:60}.product-context-drawer :deep(.detail-modal){width:min(620px,100vw)}
.product-detail-backdrop{inset:0;z-index:60;display:flex;justify-content:flex-end;align-items:stretch;padding:0;overflow:hidden;background:#0b221d66;backdrop-filter:blur(2px)}
.product-detail-modal{flex:none;width:min(1800px,calc(100vw - 24px));max-width:100vw;height:100dvh;border-radius:16px 0 0 16px;border-left:1px solid #d5e3dc;box-shadow:-20px 0 60px #06191440;overflow-y:auto;overflow-x:hidden;animation:product-drawer-enter .22s ease-out}
.product-detail-modal .relation-top{flex-wrap:wrap;gap:12px}.product-detail-modal .relation-actions{flex-wrap:wrap}
@keyframes product-drawer-enter{from{transform:translateX(100%)}to{transform:translateX(0)}}
@media(max-width:1000px){.product-detail-modal{width:calc(100vw - 16px)}}@media(max-width:600px){.product-detail-modal{width:100vw;border-radius:0}.product-detail-modal>.detail-header{padding:16px}}
@media(prefers-reduced-motion:reduce){.product-detail-modal{animation:none}}
</style>

<style scoped>
@media(max-width:420px){.detail-metrics{grid-template-columns:1fr}}
</style>
<style scoped>
/* Follow-up detail workbench: a full-page layout matching the CRM detail reference. */
.follow-up-detail-backdrop{inset:0 0 0 248px;z-index:25;place-items:stretch end;padding:0;background:#0b221d66}
.follow-up-detail-modal{width:100%;max-width:none;background:#f3f7f5;color:#29493f;box-shadow:none;overflow:auto}
.follow-up-hero{position:relative;overflow:hidden;padding:20px 46px 27px;background:linear-gradient(135deg,#0e3d35 0%,#0c322b 58%,#123f36 100%);color:#fff}
.follow-up-hero:after{content:'';position:absolute;width:380px;height:380px;border:58px solid #ffffff08;border-radius:50%;right:-100px;top:-230px;pointer-events:none}
.follow-up-hero-nav,.follow-up-actions,.follow-up-return,.follow-up-action{display:flex;align-items:center}
.follow-up-hero-nav{position:relative;z-index:1;gap:18px}
.follow-up-return,.follow-up-action{gap:7px;border:1px solid #ffffff3d;border-radius:8px;background:#ffffff12;color:#fff;padding:9px 13px;font:inherit;font-size:var(--text-body);line-height:1;cursor:pointer;white-space:nowrap}
.follow-up-return:hover,.follow-up-action:hover{background:#ffffff22}
.follow-up-hero-label{color:#a7c6bc;font-size:var(--text-body)}
.follow-up-actions{margin-left:auto;gap:9px;flex-wrap:wrap;justify-content:flex-end}
.follow-up-action.primary{border-color:#42c890;background:#42c890;color:#063b2c;font-weight:700}
.follow-up-action.primary:hover{background:#58d3a0;border-color:#58d3a0}
.follow-up-action:disabled{opacity:.55;cursor:not-allowed}
.follow-up-hero-identity{position:relative;z-index:1;display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin-top:27px}
.follow-up-hero-identity>div>span{display:block;color:#aac8be;font-size:var(--text-body)}
.follow-up-hero-identity h1{margin:9px 0 3px;font-size:var(--text-page);line-height:1.15;letter-spacing:.01em}
.follow-up-hero-identity h2{margin:0;color:#f8fffc;font-size:var(--text-page);line-height:1.3}
.follow-up-channel{padding:8px 13px;border:1px solid #ffffff38;border-radius:22px;background:#ffffff15;color:#e4f5ef;font-size:var(--text-body);white-space:nowrap}
.follow-up-summary{position:relative;z-index:1;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));margin-top:25px;border:1px solid #ffffff2e;border-radius:11px;background:#ffffff10;overflow:hidden}
.follow-up-summary>div{min-width:0;padding:14px 17px;border-right:1px solid #ffffff24}
.follow-up-summary>div:last-child{border-right:0}
.follow-up-summary small{display:block;margin-bottom:7px;color:#a8c5bc;font-size:var(--text-caption)}
.follow-up-summary strong{display:flex;align-items:center;gap:6px;min-width:0;overflow:hidden;color:#fff;font-size:var(--text-body);font-weight:600;line-height:1.35;white-space:nowrap;text-overflow:ellipsis}
.follow-up-summary-result{display:flex;align-items:flex-start;gap:6px;max-height:5.4em;overflow:auto;color:#fff;font-size:var(--text-body);font-weight:600;line-height:1.35;white-space:normal;word-break:break-word}.follow-up-summary-result>div{min-width:0}.follow-up-summary-result :deep(p){margin:0 0 2px}.follow-up-summary-result :deep(ul),.follow-up-summary-result :deep(ol){margin:2px 0;padding-left:16px}.follow-up-summary-result :deep(img){max-width:100%;height:auto}
.follow-up-summary span:not(.owner-avatar){display:block;margin-top:4px;color:#a8c5bc;font-size:var(--text-body)}
.summary-dot{display:inline-block;width:8px;height:8px;flex:0 0 auto;border-radius:50%;background:#42d69c}
.owner-avatar{display:inline-grid!important;place-items:center;width:23px;height:23px;margin-right:3px;border-radius:50%;background:#d6e7e1;color:#1e5548!important;font-size:var(--text-body)!important}
.follow-up-detail-content{display:grid;grid-template-columns:minmax(0,4fr) minmax(180px,1fr);align-items:stretch;gap:16px 18px;max-width:1500px;margin:0 auto;padding:22px 46px 45px}
.follow-up-detail-main-column{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:minmax(360px,1fr) auto;align-items:stretch;align-self:stretch;gap:16px 18px;min-width:0;min-height:0}
.follow-up-card{overflow:hidden;border:1px solid #dfe9e4;border-radius:12px;background:#fff;box-shadow:0 1px 2px #1a4d3b0a}
.follow-up-card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 19px;border-bottom:1px solid #e6eee9}
.follow-up-card-head h3{display:flex;align-items:center;gap:8px;margin:0;color:#244a40;font-size:var(--text-section);font-weight:700}
.follow-up-card-head>span{color:#7b8d85;font-size:var(--text-body);white-space:nowrap}
.follow-up-content-card,.follow-up-feedback-card{height:100%;min-height:360px}
.follow-up-content-card{display:flex;flex-direction:column}
.follow-up-feedback-card{display:flex;flex-direction:column}
.follow-up-feedback-card .follow-up-card-head{flex:0 0 auto}
.follow-up-richtext{flex:1;min-height:180px;padding:19px 20px;color:#40574e;font-size:var(--text-body);line-height:1.75;word-break:break-word}
.follow-up-richtext :deep(p){margin:0 0 9px}.follow-up-richtext :deep(p:last-child){margin-bottom:0}.follow-up-richtext :deep(ul),.follow-up-richtext :deep(ol){margin:7px 0;padding-left:22px}
.follow-up-richtext :deep(img){display:block;max-width:100%;height:auto;margin:10px 0;border-radius:8px}
.follow-up-next-action{margin:0 20px 20px;padding:13px 15px;border-left:3px solid #42b889;border-radius:9px;background:#eff8f3}
.follow-up-next-action strong{color:#24735a;font-size:var(--text-body)}.follow-up-next-action p{margin:5px 0 0;color:#506960;font-size:var(--text-body)}
.follow-up-attachments-card{grid-column:1 / -1}
.follow-up-attachments-empty{display:flex;align-items:center;justify-content:center;gap:8px;min-height:72px;padding:14px 20px;color:#91a19a;font-size:var(--text-body);background:#fbfdfc}
.follow-up-attachments-empty svg{color:#abc0b7}
.follow-up-attachment-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;padding:14px 19px}
.follow-up-attachment-item{display:flex;align-items:center;gap:10px;min-width:0;padding:10px 11px;border:1px solid #e2ebe6;border-radius:8px;background:#fbfdfc;color:#315a4c;text-decoration:none}
.follow-up-attachment-item:hover{border-color:#abd1c0;background:#f2faf6}
.follow-up-attachment-item>img{width:34px;height:34px;flex:0 0 auto;object-fit:cover;border-radius:5px}.follow-up-attachment-item>svg{flex:0 0 auto;color:#5e9c86}
.follow-up-attachment-item>span{display:grid;flex:1;min-width:0;gap:3px}.follow-up-attachment-item strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--text-body)}.follow-up-attachment-item small{color:#86978f;font-size:var(--text-caption)}.follow-up-attachment-item>svg:last-child{color:#91aaa0}
.follow-up-timeline{padding:18px 22px 19px}
.follow-up-timeline-item{position:relative;display:grid;grid-template-columns:18px minmax(0,1fr) auto;gap:11px;padding:0 0 22px}
.follow-up-timeline-item:last-child{padding-bottom:0}.follow-up-timeline-item:before{content:'';position:absolute;left:7px;top:15px;bottom:0;border-left:1px dashed #c7d8d1}.follow-up-timeline-item:last-child:before{display:none}
.follow-up-timeline-item>i{z-index:1;width:15px;height:15px;margin-top:2px;border:2px solid #2d9a78;border-radius:50%;background:#fff}.follow-up-timeline-item.planned>i{border-color:#b5c3bd}
.follow-up-timeline-item strong{display:block;color:#2f5a4d;font-size:var(--text-body)}.follow-up-timeline-item p{margin:5px 0;color:#536a61;font-size:var(--text-body)}.follow-up-timeline-item time{color:#71857c;font-size:var(--text-body);white-space:nowrap}
.follow-up-detail-side-rail .follow-up-timeline-item{grid-template-columns:18px minmax(0,1fr)}.follow-up-detail-side-rail .follow-up-timeline-item time{grid-column:2;margin-top:3px;white-space:normal}
.timeline-tag{display:inline-block;padding:3px 7px;border-radius:5px;font-size:var(--text-secondary)}.timeline-tag.success{background:#e3f7ed;color:#2d8766}.timeline-tag.planned-tag{background:#fff1d8;color:#b77b25}
.follow-up-feedback-card>.follow-up-richtext{min-height:180px;padding:16px 19px;color:#526960;font-size:var(--text-body);line-height:1.7;word-break:break-word}
.follow-up-detail-side-rail{display:grid;grid-column:2;grid-row:1;align-content:start;align-self:start;gap:16px;min-width:0}
.follow-up-tags{display:flex;flex-wrap:wrap;gap:7px;padding:16px 19px}.follow-up-tags span{padding:6px 9px;border-radius:6px;background:#e8f5ef;color:#28735b;font-size:var(--text-secondary)}
.follow-up-related-row{display:flex;align-items:center;width:100%;gap:10px;padding:13px 18px;border:0;border-top:1px solid #edf2ef;background:#fff;color:#33594d;text-align:left;cursor:pointer}.follow-up-related-row:hover{background:#f5faf7}.related-icon{display:grid;place-items:center;width:28px;height:28px;border-radius:7px;font-size:var(--text-section)}.customer-icon{background:#dff2e9;color:#2d966e}.contact-icon{background:#fff0d7;color:#bf812b}.follow-up-related-row>span:nth-child(2){display:grid;flex:1;gap:3px;min-width:0}.follow-up-related-row strong{font-size:var(--text-body);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.follow-up-related-row small{color:#819189;font-size:var(--text-caption)}.follow-up-related-row>svg{flex:0 0 auto;color:#9aa9a2}
@media(max-width:980px){.follow-up-detail-backdrop{inset:0;z-index:25;place-items:stretch}}
@media(max-width:1050px){.follow-up-hero{padding-left:28px;padding-right:28px}.follow-up-detail-content{padding-left:28px;padding-right:28px;grid-template-columns:1fr}.follow-up-detail-main-column{grid-template-rows:auto auto;align-self:start;height:auto}.follow-up-detail-side-rail{grid-column:auto;grid-row:auto;grid-template-columns:repeat(3,minmax(0,1fr));align-items:start}.follow-up-summary{grid-template-columns:repeat(3,minmax(0,1fr))}.follow-up-summary>div:nth-child(3){border-right:0}.follow-up-summary>div:nth-child(-n+3){border-bottom:1px solid #ffffff24}}
@media(max-width:760px){.follow-up-hero{padding:17px 20px 22px}.follow-up-detail-content{grid-template-columns:1fr;padding:16px 20px 32px}.follow-up-detail-main-column{grid-template-columns:1fr;grid-template-rows:auto auto}.follow-up-attachments-card{grid-column:auto}.follow-up-detail-side-rail{grid-template-columns:1fr}.follow-up-hero-identity{align-items:flex-start;flex-direction:column}.follow-up-actions{margin-left:0;justify-content:flex-start}.follow-up-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.follow-up-summary>div:nth-child(3){border-right:1px solid #ffffff24}.follow-up-summary>div:nth-child(2n){border-right:0}.follow-up-summary>div:nth-child(4),.follow-up-summary>div:nth-child(5){border-bottom:0}.follow-up-summary>div:nth-child(3),.follow-up-summary>div:nth-child(4){border-bottom:1px solid #ffffff24}.follow-up-hero-identity h1{font-size:var(--text-page)}}
@media(max-width:520px){.follow-up-hero{padding:15px 16px 19px}.follow-up-detail-content{padding:13px 16px 26px}.follow-up-hero-nav{align-items:flex-start;flex-wrap:wrap}.follow-up-actions{width:100%;gap:7px}.follow-up-action{flex:1;justify-content:center;padding:9px 8px}.follow-up-summary{grid-template-columns:1fr}.follow-up-summary>div,.follow-up-summary>div:nth-child(3){border-right:0;border-bottom:1px solid #ffffff24}.follow-up-summary>div:last-child{border-bottom:0}.follow-up-timeline-item{grid-template-columns:18px minmax(0,1fr)}.follow-up-timeline-item time{grid-column:2}.follow-up-card-head{padding-left:15px;padding-right:15px}}
.product-detail-modal>.detail-header{padding:20px 30px 24px}.product-context-drawer{left:0;z-index:60}.product-context-drawer :deep(.detail-modal){width:min(620px,100vw)}
.product-detail-backdrop{inset:0;z-index:60;display:flex;justify-content:flex-end;align-items:stretch;padding:0;overflow:hidden;background:#0b221d66;backdrop-filter:blur(2px)}
.product-detail-modal{flex:none;width:min(1800px,calc(100vw - 24px));max-width:100vw;height:100dvh;border-radius:16px 0 0 16px;border-left:1px solid #d5e3dc;box-shadow:-20px 0 60px #06191440;overflow-y:auto;overflow-x:hidden;animation:product-drawer-enter .22s ease-out}
.product-detail-modal .relation-top{flex-wrap:wrap;gap:12px}.product-detail-modal .relation-actions{flex-wrap:wrap}
@keyframes product-drawer-enter{from{transform:translateX(100%)}to{transform:translateX(0)}}
@media(max-width:1000px){.product-detail-modal{width:calc(100vw - 16px)}}@media(max-width:600px){.product-detail-modal{width:100vw;border-radius:0}.product-detail-modal>.detail-header{padding:16px}}
@media(prefers-reduced-motion:reduce){.product-detail-modal{animation:none}}
</style>
<style scoped>
.relation-actions{display:flex;align-items:center;gap:8px}.danger-link{background:#fff0f0;color:#ad4545}.inactive-toggle{background:#fff6f6;color:#ad4545}.selection-cell{width:40px;padding-left:12px!important;padding-right:4px!important;text-align:center}.selection-check{position:relative;display:inline-grid;place-items:center;cursor:pointer;color:#bdc9c4}.selection-check input{position:absolute;opacity:0}.selection-check svg{pointer-events:none}.selection-check input:checked+svg{color:#21745f}.selection-check input:focus-visible+svg{outline:3px solid #c6dfd7;outline-offset:2px;border-radius:3px}.sku-context-table tbody tr:has(.selection-check input:checked){background:#eff7f3}.sku-context-table th.selection-cell{padding-top:8px;padding-bottom:8px}.inactive-row{background:#fff7f7!important}.inactive-row td,.inactive-row td.primary{color:#b45757!important}.inactive-status{display:inline-block;border-radius:20px;padding:3px 7px;background:#ffeded;color:#ba4545;font-weight:700}.detail-back,.detail-close{min-height:38px;border-radius:9px;font-weight:700;letter-spacing:0;text-transform:none}.detail-back{display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid #ffffff45;background:#ffffff1a;color:#fff;font-size:var(--text-body)}.detail-close{display:flex;width:auto;gap:7px;align-items:center;padding:8px 11px;border:1px solid #ffffff45;background:#ffffff1a;color:#fff;font-size:var(--text-body)}.detail-close:hover,.detail-back:hover{background:#ffffff2b}@media(max-width:700px){.detail-close span{display:none}.detail-close{padding:8px}.detail-back{font-size:var(--text-body);padding:7px 9px}}
.product-detail-modal>.detail-header{padding:20px 30px 24px}.product-context-drawer{left:0;z-index:60}.product-context-drawer :deep(.detail-modal){width:min(620px,100vw)}
.product-detail-backdrop{inset:0;z-index:60;display:flex;justify-content:flex-end;align-items:stretch;padding:0;overflow:hidden;background:#0b221d66;backdrop-filter:blur(2px)}
.product-detail-modal{flex:none;width:min(1800px,calc(100vw - 24px));max-width:100vw;height:100dvh;border-radius:16px 0 0 16px;border-left:1px solid #d5e3dc;box-shadow:-20px 0 60px #06191440;overflow-y:auto;overflow-x:hidden;animation:product-drawer-enter .22s ease-out}
.product-detail-modal .relation-top{flex-wrap:wrap;gap:12px}.product-detail-modal .relation-actions{flex-wrap:wrap}
@keyframes product-drawer-enter{from{transform:translateX(100%)}to{transform:translateX(0)}}
@media(max-width:1000px){.product-detail-modal{width:calc(100vw - 16px)}}@media(max-width:600px){.product-detail-modal{width:100vw;border-radius:0}.product-detail-modal>.detail-header{padding:16px}}
@media(prefers-reduced-motion:reduce){.product-detail-modal{animation:none}}
</style>

<style scoped>
.customer-detail-root .detail-header,.movement-detail .detail-header{padding:22px 26px}.customer-detail-root .detail-identity h2,.movement-detail .detail-identity h2{font-size:var(--text-page);font-weight:700;overflow-wrap:anywhere}.detail-owner,.movement-identity{display:block;margin-top:8px;font-size:var(--text-caption);color:#b6d3ca}.customer-detail-root .detail-info,.customer-detail-root .relation-area,.movement-detail .detail-info,.movement-detail .relation-area{padding:16px;border-color:#e0e8e4;margin-bottom:16px}.customer-detail-root .detail-tabs,.movement-detail .detail-tabs{margin-left:-16px;margin-right:-16px;padding:0 16px}.customer-detail-root .detail-tabs button,.movement-detail .detail-tabs button{min-height:44px;padding:10px 13px}.customer-detail-root .context-table-wrap,.movement-detail .context-table-wrap{margin-left:-16px;margin-right:-16px;margin-bottom:-16px}.customer-detail-root .detail-nav,.movement-detail .detail-nav{gap:14px;flex-wrap:wrap}.customer-detail-root .detail-actions{flex-wrap:wrap}.customer-detail-root .detail-actions .btn:first-child{background:#f5fcf8;color:#174c41;border-color:#b8dccf;font-weight:700}
</style>
