<script setup>
import { useWorkspaceNavigation } from '../composables/useWorkspaceNavigation'
const { workspace } = useWorkspaceNavigation()
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, downloadQuoteExport } = useWorkspaceApi()
import { compactDecimalInput } from '../utils/decimalInput'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { routeLocationKey, routerKey } from 'vue-router'
import { AlertTriangle, ArrowLeft, ArrowRight, Download, Eye, FileText, GitBranch, Pencil, Plus, ShoppingCart, StickyNote, X } from 'lucide-vue-next'

import { confirmDialog } from '../dialogs'
import QuotePreviewModal from './QuotePreviewModal.vue'
import RichTextEditor from './RichTextEditor.vue'
import OperationLogPanel from './OperationLogPanel.vue'
import PartyReplacementForm from './PartyReplacementForm.vue'
import PartyDetailsPanel from './PartyDetailsPanel.vue'
import PartyDetailsFields from './PartyDetailsFields.vue'
import PartyDetailsChanges from './PartyDetailsChanges.vue'
import { useDetailTab } from '../utils/useDetailTab'
import { useAccessControl } from '../accessControl'
import { formatApiError } from '../utils/apiErrors'

const props = defineProps({ id: { type: [Number, String], required: true }, refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['close', 'revise', 'status-updated', 'create-order', 'open-order'])
const { can } = useAccessControl()
const workbench = ref(null)
const activeTab = useDetailTab('/quotes', ['overview', 'items', 'lineage', 'orders', 'party-change', 'notes', 'operation_logs'], 'overview', () => props.id)
const loading = ref(true)
const error = ref('')
const preview = ref(null)
const noteContent = ref('')
const noteSaving = ref(false)
const noteEditorOpen = ref(false)
const versionHistory = ref([])
const route = inject(routeLocationKey, null)
const router = inject(routerKey, null)
const actionError = ref('')
const statusSaving = ref(false)
const operationLogs = ref([])
const operationLogsLoading = ref(false)
const auditEnabled = ref(false)
const partyFields = [['name', '名称'], ['country', '国家 / 地区'], ['address', '地址'], ['contact', '联系人'], ['phone', '电话'], ['email', '邮箱'], ['tax_id', '税号']]
const partyData = ref(null)
const partyDraft = ref({})
const partyReason = ref('')
const partyEvidence = ref('')
const partyLegalEntityConfirmed = ref(false)
const partyChangeType = ref('correction')
const partyNotes = ref({})
const partyTerminalNotes = ref({})
const replacementCreateId = ref(null)
const partyLoading = ref(false)
const partyBusy = ref(false)
const partyError = ref('')
let partyGeneration = 0

const quote = computed(() => workbench.value?.quote)
const partyFormal = computed(() => ['sent', 'accepted'].includes(quote.value?.status))
const partyCanApply = computed(() => can('quotes', 'create') && can('quotes', 'update'))
const canCreateOrder = computed(() => can('orders', 'create') && ['draft', 'sent', 'accepted'].includes(quote.value?.status))
const tabs = computed(() => [
  ['overview', '概览'], ['items', `报价明细 (${quote.value?.items?.length || 0})`],
  ['lineage', `版本谱系 (${workbench.value?.revisions?.length || 0})`], ['orders', `订单 (${workbench.value?.orders?.length || 0})`],
  ['party-change', '主体更正'],
  ['notes', `重要备注 (${workbench.value?.important_notes?.length || 0})`],
  ['operation_logs', `操作日志 (${operationLogs.value.length})`],
])
const subtotal = computed(() => (quote.value?.items || []).reduce((sum, item) => sum + Number(item.amount || 0), 0))
const partyName = computed(() => quote.value?.buyer_company_name || '历史主体未记录')
const partyMasterReference = computed(() => {
  if (!quote.value?.customer_name || !quote.value?.buyer_company_name || quote.value.customer_name === quote.value.buyer_company_name) return ''
  return `当前主档参考：${quote.value.customer_name}`
})
const revisionTreeRows = computed(() => {
  const rows = workbench.value?.revisions || []
  const children = new Map(rows.map(row => [row.id, []]))
  const roots = []
  rows.forEach(row => {
    if (row.parent_quote && children.has(row.parent_quote)) children.get(row.parent_quote).push(row)
    else roots.push(row)
  })
  const sortRows = list => list.sort((left, right) => left.revision_no - right.revision_no || left.id - right.id)
  const result = []
  const visit = (row, depth) => { result.push({ ...row, depth }); sortRows(children.get(row.id) || []).forEach(child => visit(child, depth + 1)) }
  sortRows(roots).forEach(row => visit(row, 0))
  return result
})
function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function revisionLabel(row) { return row.revision_no ? `修订版 ${row.revision_no}` : '原始报价' }
function isRichTextEmpty(value) { return !String(value || '').replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim() }
function dateTime(value) { return value ? new Date(value).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }) : '—' }

async function load(id = props.id) {
  loading.value = true; error.value = ''; actionError.value = ''
  try {
    const [workbenchResult] = await Promise.all([
      api.get(`/quotes/${id}/workbench/`),
      loadOperationLogs(id),
    ])
    workbench.value = workbenchResult.data
  }
  catch (err) { error.value = err.message }
  finally { loading.value = false }
}
async function loadOperationLogs(id = props.id) {
  operationLogsLoading.value = true
  try {
    const [logsResult, operatorResult] = await Promise.all([
      api.get('/operation-logs/', { params: { entity: 'crm.quote', object_id: id, ordering: '-created_at' } }).catch(() => ({ data: [] })),
      api.get('/session/current-operator/').catch(() => ({ data: {} })),
    ])
    operationLogs.value = logsResult.data?.results || logsResult.data || []
    auditEnabled.value = Boolean(operatorResult.data?.audit_log_enabled)
  } finally { operationLogsLoading.value = false }
}
async function changeStatus(action) {
  if (!quote.value || statusSaving.value || !can('quotes', 'update')) return
  statusSaving.value = true
  actionError.value = ''
  try {
    await api.post(`/quotes/${quote.value.id}/${action}/`)
    await load()
    emit('status-updated')
  } catch (err) { actionError.value = err.message }
  finally { statusSaving.value = false }
}
async function openPreview(id = quote.value?.id) {
  actionError.value = ''
  try {
    const data = (await api.get(`/quotes/${id}/pi-data/`)).data
    preview.value = {
      ...data,
      quote_no: data.invoice_no,
      quote_date: data.terms.quote_date,
      valid_until: data.terms.valid_until,
      currency: data.totals.currency,
      buyer: { company_name: data.buyer.company_name, recipient: data.buyer.name, address: data.buyer.address, email: data.buyer.email, phone: data.buyer.phone },
      products: data.products.map((item, index) => ({ ...item, key: `${item.model || item.sku}-${index}` })),
    }
  } catch (err) { actionError.value = err.message }
}
async function exportQuote() {
  if (!can('quotes', 'export')) return
  actionError.value = ''
  try { await downloadQuoteExport(quote.value.id, quote.value.quote_no) } catch (err) { actionError.value = err.message }
}
async function createNote() {
  if (!can('quotes', 'update') || isRichTextEmpty(noteContent.value)) return
  noteSaving.value = true; actionError.value = ''
  try { await api.post(`/quotes/${quote.value.id}/important-notes/`, { content: noteContent.value }); noteContent.value = ''; noteEditorOpen.value = false; await load(quote.value.id) }
  catch (err) { actionError.value = err.message }
  finally { noteSaving.value = false }
}
async function deactivateNote(note) {
  if (!can('quotes', 'update')) return
  if (!await confirmDialog({ title: '确认停用备注', message: '标记后备注不会删除，但会显示为不再生效。确定继续吗？', confirmText: '确认停用', danger: true })) return
  actionError.value = ''
  try { await api.post(`/quotes/${quote.value.id}/important-notes/${note.id}/deactivate/`); await load(quote.value.id) }
  catch (err) { actionError.value = err.message }
}
async function restoreNote(note) {
  if (!can('quotes', 'update')) return
  actionError.value = ''
  try { await api.post(`/quotes/${quote.value.id}/important-notes/${note.id}/restore/`); await load(quote.value.id) }
  catch (err) { actionError.value = err.message }
}
function changeVersion(row) {
  if (row.id === quote.value.id) return
  versionHistory.value.push(quote.value.id)
  openVersion(row.id)
}
function openVersion(id) {
  if (route?.path === '/quotes' && route.query.detail) {
    void router.push({ path: '/quotes', query: { ...route.query, detail: String(id), tab: 'overview' }, hash: route.hash })
  } else { activeTab.value = 'overview'; void load(id) }
}
function returnToPreviousVersion() {
  const previousId = versionHistory.value.pop()
  if (previousId) openVersion(previousId)
}
function createOrder() { if (can('orders', 'create')) emit('create-order', { id: quote.value.id, quote_no: quote.value.quote_no }) }
function closeNoteEditor() { noteContent.value = ''; noteEditorOpen.value = false }

function partyValue(value) { return value == null ? '历史未记录' : value === '' ? '已留空' : value }
function partyRequestStatus(request) {
  if (request.application) return 'applied'
  if (request.terminal_event) return ['rejected', 'withdrawn', 'invalidated'].includes(request.status) ? request.status : 'terminal'
  if (request.status != null) return request.status
  return request.approval ? 'approved' : 'pending'
}
function partyStatusLabel(request) {
  return ({ pending: '待审批', approved: '已批准', applied: '已生成新草稿', rejected: '已拒绝', withdrawn: '已撤回', invalidated: '已失效', terminal: '已终止' })[partyRequestStatus(request)] || '状态未知'
}
function canHandlePartyRequest(request, operation) {
  const userId = partyData.value?.current_user_id
  if (!userId || partyBusy.value || !can('quotes', 'update') || request.application || request.terminal_event) return false
  const status = partyRequestStatus(request)
  const isInitiator = request.initiator_id != null && String(request.initiator_id) === String(userId)
  if (operation === 'withdraw') return status === 'pending' && !request.approval && isInitiator
  if (operation === 'reject') return status === 'pending' && !request.approval && request.initiator_id != null && !isInitiator
  if (operation === 'invalidate') return (status === 'pending' && !request.approval) || (status === 'approved' && Boolean(request.approval))
  return false
}
function partyMessage(err) {
  const labels = { name: '名称', country: '国家 / 地区', address: '地址', contact: '联系人', phone: '电话', email: '邮箱', tax_id: '税号', reason: '更正原因', evidence: '依据', note: '意见 / 处理原因', proposed_snapshot: '建议值', expected_base_fingerprint: '原始快照', expected_content_fingerprint: '申请内容', source_trust: '来源' }
  function localize(value) {
    if (Array.isArray(value)) return value.map(localize)
    if (!value || typeof value !== 'object') return value
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [labels[key] || key, localize(item)]))
  }
  const data = err?.response?.data ?? err?.data
  const message = formatApiError(localize(data))
  const status = Number(err?.response?.status ?? err?.status ?? 0)
  if (status === 401) return message ? `请先登录已认证账号。${message}` : '请先登录已认证账号后重试。'
  if (message) return message
  if (status === 403) return '当前账号无权操作，请确认登录和访问权限。'
  return typeof err?.message === 'string' && err.message !== '[object Object]' ? err.message : '操作失败，请重试。'
}
async function loadPartyChange() {
  const id = quote.value?.id
  if (!id) return
  const generation = ++partyGeneration
  partyData.value = null; partyDraft.value = {}; partyReason.value = ''; partyEvidence.value = ''; partyLegalEntityConfirmed.value = false; partyChangeType.value = 'correction'; partyNotes.value = {}; partyTerminalNotes.value = {}
  partyError.value = ''; partyLoading.value = true; partyBusy.value = false
  try {
    const { data } = await api.get(`/quotes/${id}/party-change/`)
    if (generation !== partyGeneration) return
    if (!data?.baseline?.snapshot || !data.baseline.fingerprint || !Array.isArray(data.requests) || !partyFields.every(([field]) => Object.hasOwn(data.baseline.snapshot, field))) throw new Error('主体更正资料不完整，请重试。')
    partyData.value = data
    partyDraft.value = { ...data.baseline.snapshot }
  } catch (err) { if (generation === partyGeneration) partyError.value = partyMessage(err) }
  finally { if (generation === partyGeneration) partyLoading.value = false }
}
async function submitPartyChange() {
  if (!partyData.value?.current_user_id || partyBusy.value || !partyFormal.value || !can('quotes', 'update')) return
  if (partyChangeType.value === 'correction' && !partyLegalEntityConfirmed.value) { partyError.value = '请确认法律主体未变。'; return }
  if (!partyReason.value.trim() || !partyEvidence.value.trim()) { partyError.value = '请填写原因和依据。'; return }
  const id = quote.value.id; const generation = partyGeneration
  partyBusy.value = true; partyError.value = ''
  try {
    await api.post(`/quotes/${id}/party-change/`, {
      expected_base_fingerprint: partyData.value.baseline.fingerprint,
      proposed_snapshot: { ...partyDraft.value }, change_type: partyChangeType.value,
      reason: partyReason.value.trim(), evidence: partyEvidence.value.trim(), source_trust: 'unverified',
    })
    if (generation === partyGeneration) await loadPartyChange()
  } catch (err) { if (generation === partyGeneration) partyError.value = partyMessage(err) }
  finally { if (generation === partyGeneration) partyBusy.value = false }
}
async function approvePartyChange(request) {
  if (!partyData.value?.current_user_id || request.initiator_id == null || String(request.initiator_id) === String(partyData.value.current_user_id) || request.approval || request.application || request.terminal_event || partyRequestStatus(request) !== 'pending' || !['correction', 'replacement'].includes(request.change_type) || partyBusy.value || !partyFormal.value || !can('quotes', 'update')) return
  const note = (partyNotes.value[request.id] || '').trim()
  if (!note) { partyError.value = '请填写审批意见。'; return }
  const id = quote.value.id; const generation = partyGeneration
  partyBusy.value = true; partyError.value = ''
  try {
    await api.post(`/quotes/${id}/party-change/${request.id}/approve/`, { expected_content_fingerprint: request.content_fingerprint, note })
    if (generation === partyGeneration) await loadPartyChange()
  } catch (err) { if (generation === partyGeneration) partyError.value = partyMessage(err) }
  finally { if (generation === partyGeneration) partyBusy.value = false }
}
async function applyPartyChange(request) {
  if (!partyData.value?.current_user_id || !request.approval || request.application || request.terminal_event || partyRequestStatus(request) !== 'approved' || request.change_type !== 'correction' || partyBusy.value || !partyFormal.value || !partyCanApply.value) return
  const id = quote.value.id; const generation = partyGeneration
  partyBusy.value = true; partyError.value = ''
  try {
    const { data } = await api.post(`/quotes/${id}/party-change/${request.id}/apply/`)
    if (generation !== partyGeneration) return
    if (!data?.result_quote_id) throw new Error('未返回新报价版本，请刷新后核对。')
    emit('status-updated')
    changeVersion({ id: data.result_quote_id })
  } catch (err) { if (generation === partyGeneration) partyError.value = partyMessage(err) }
  finally { if (generation === partyGeneration) partyBusy.value = false }
}
async function closePartyRequest(request, operation) {
  if (!canHandlePartyRequest(request, operation)) return
  const note = (partyTerminalNotes.value[request.id] || '').trim()
  if (!note) { partyError.value = '请填写处理原因。'; return }
  const id = quote.value.id; const generation = partyGeneration
  partyBusy.value = true; partyError.value = ''
  try {
    await api.post(`/quotes/${id}/party-change/${request.id}/${operation}/`, { note })
    if (generation === partyGeneration) await loadPartyChange()
  } catch (err) { if (generation === partyGeneration) partyError.value = partyMessage(err) }
  finally { if (generation === partyGeneration) partyBusy.value = false }
}

onMounted(load)
watch(() => props.id, () => { ++partyGeneration; partyData.value = null; void load() })
watch(() => props.refreshKey, () => load(quote.value?.id || props.id))
watch(() => quote.value?.quote_no, title => { if (workspace && title) { workspace.objectTitle = String(title); workspace.title = String(title) } }, { immediate: true })
watch(partyChangeType, () => { partyLegalEntityConfirmed.value = false })
watch([() => quote.value?.id, activeTab], ([id, tab]) => {
  if (id && tab === 'party-change') void loadPartyChange()
  else { ++partyGeneration; partyData.value = null; partyLoading.value = false; partyError.value = '' }
})
onBeforeUnmount(() => { ++partyGeneration })
</script>

<template>
  <div class="modal-backdrop detail-backdrop" @mousedown.self="emit('close')">
    <article class="detail-modal quote-workbench" role="dialog" aria-modal="true" aria-label="报价工作台">
      <div v-if="loading" class="detail-loading"><div class="spinner" /> 正在加载报价工作台…</div>
      <div v-else-if="error" class="detail-error"><AlertTriangle :size="27" /><strong>加载失败</strong><p>{{ error }}</p><button class="btn btn-secondary" @click="load()">重试</button></div>
      <template v-else>
        <header class="detail-header">
          <div class="detail-nav"><div class="detail-nav-start"><button class="detail-close" aria-label="关闭报价详情" @click="emit('close')"><X :size="18" /> <span>关闭</span></button><button v-if="versionHistory.length" class="detail-back" @click="returnToPreviousVersion"><ArrowLeft :size="18" /> 返回上一版本</button><span v-else>报价工作台 · {{ workbench.root_quote_no }}</span></div></div>
          <div class="detail-identity"><div><p class="detail-subtitle">{{ partyName }} · {{ revisionLabel(quote) }}<small v-if="partyMasterReference" class="party-reference">{{ partyMasterReference }}</small></p><h2>{{ quote.quote_no }}</h2><small>原始报价：{{ workbench.root_quote_no }}</small></div><span class="detail-badge">{{ quote.status_display }}</span></div>
          <div v-if="can('quotes', 'update') && (quote.status === 'draft' || quote.status === 'sent')" class="quote-status-actions" aria-label="报价状态操作">
            <button v-if="quote.status === 'draft'" class="btn btn-secondary" :disabled="statusSaving" @click="changeStatus('mark-sent')">标记为已发送</button>
            <button class="btn btn-secondary" :disabled="statusSaving" @click="changeStatus('accept')">标记为客户已接受</button>
            <button class="btn btn-secondary" :disabled="statusSaving" @click="changeStatus('reject')">标记为客户已拒绝</button>
            <button v-if="quote.status === 'sent'" class="btn btn-secondary" :disabled="statusSaving" @click="changeStatus('expire')">标记为已过期</button>
          </div>
          <div class="workbench-actions"><button v-if="can('quotes', 'update')" class="btn btn-secondary" @click="emit('revise', quote)"><Pencil :size="14" /> 创建修订版</button><button class="btn btn-secondary" @click="openPreview()"><Eye :size="15" /> 预览 PI</button><button v-if="can('quotes', 'export')" class="btn quote-utility" @click="exportQuote"><Download :size="15" /> 导出 Excel</button><button v-if="canCreateOrder" class="btn btn-primary transfer-order" @click="createOrder"><ShoppingCart :size="15" /> 创建销售订单</button></div>
          <p v-if="!canCreateOrder" class="quote-order-unavailable">当前报价不能转单，请先创建修订版。</p>
          <p v-if="actionError" class="workbench-error">{{ actionError }}</p>
        </header>
        <main class="detail-content">
          <nav class="workbench-tabs" aria-label="报价详情分页"><button v-for="tab in tabs" :key="tab[0]" :class="{ active: activeTab === tab[0] }" @click="activeTab = tab[0]">{{ tab[1] }}</button></nav>

          <section v-if="activeTab === 'overview'" class="workbench-grid">
            <PartyDetailsPanel v-if="can('customers', 'view')" kind="quote" :id="quote.id" :status="quote.status" :can-edit="can('quotes', 'update') && !quote.parent_quote" />
            <div class="workbench-card summary-card"><h3>报价概览</h3><div class="summary-metrics"><div><small>报价总额</small><strong>{{ quote.currency }} {{ money(quote.total_amount) }}</strong></div><div><small>有效期至</small><strong>{{ quote.valid_until || '—' }}</strong></div><div><small>商品明细</small><strong>{{ quote.items.length }} 项</strong></div></div></div>
            <div class="workbench-card"><h3>基础信息</h3><dl class="data-list"><dt>报价日期</dt><dd>{{ quote.quote_date }}</dd><dt>币种 / 汇率</dt><dd>{{ quote.currency }} / {{ compactDecimalInput(quote.exchange_rate) }}</dd><dt>收件人</dt><dd>{{ quote.recipient_name || '—' }}</dd><dt>条款备注</dt><dd>{{ quote.notes || '—' }}</dd></dl></div>
            <div class="workbench-card version-summary"><div class="section-heading"><div><h3><GitBranch :size="16" /> 修订摘要</h3><p>共 {{ workbench.revisions.length }} 个版本，当前查看 {{ revisionLabel(quote) }}。</p></div><button class="text-btn" @click="activeTab = 'lineage'">查看修订历史</button></div><div class="summary-version-list"><article v-for="row in revisionTreeRows" :key="row.id" :class="{ current: row.id === quote.id, child: row.depth }" :style="{ '--depth': row.depth }"><div class="version-row-main"><span v-if="row.depth" class="version-tree-connector"><ArrowRight :size="13" /></span><strong>{{ row.quote_no }}</strong><span>{{ revisionLabel(row) }}</span><span>{{ dateTime(row.created_at) }}</span><span class="status" :class="row.status">{{ row.status_display }}</span><em v-if="row.revision_summary">修订：{{ row.revision_summary }}</em></div><div class="version-row-side"><b>{{ row.currency }} {{ money(row.total_amount) }}</b><div class="summary-version-actions"><button class="text-btn" @click="openPreview(row.id)">预览 PI</button><button class="text-btn" :disabled="row.id === quote.id" @click="changeVersion(row)">查看详情</button></div></div></article></div></div>
            <div class="workbench-card"><h3><ShoppingCart :size="16" /> 销售订单摘要</h3><p>已生成 {{ workbench.orders.length }} 张销售订单。</p><button class="text-btn" @click="activeTab = 'orders'">查看关联销售订单</button></div>
          </section>

          <section v-else-if="activeTab === 'items'" class="workbench-card"><div class="section-heading"><div><h3>报价明细</h3><p>当前报价版本的商品明细。</p></div><strong>{{ quote.currency }} {{ money(quote.total_amount) }}</strong></div><div class="workbench-table-wrap"><table class="workbench-table items-table"><thead><tr><th>Model</th><th>内部名称 / SKU Code</th><th>产品描述快照</th><th>数量</th><th>单位</th><th>单价</th><th>小计</th></tr></thead><tbody><tr v-for="item in quote.items" :key="item.id"><td>{{ item.sales_model_snapshot || item.model || '未设置' }}</td><td>{{ item.display_name_snapshot || item.product_name }}<small>{{ item.sku_code }}</small></td><td>{{ item.description_snapshot || item.description || '—' }}</td><td>{{ item.trade_quantity ?? item.quantity }}<small v-if="item.trade_unit">基础数量：{{ item.quantity }} {{ item.trade_snapshot.base_unit }}</small></td><td>{{ item.trade_snapshot?.unit || item.unit }}</td><td>{{ money(item.trade_unit_price ?? item.unit_price) }}</td><td>{{ money(item.amount) }}</td></tr></tbody></table></div><div class="quote-totals">商品小计 {{ money(subtotal) }}　运费 {{ money(quote.shipping_fee) }}　折扣 -{{ money(quote.discount) }}　<strong>合计 {{ quote.currency }} {{ money(quote.total_amount) }}</strong></div></section>

          <section v-else-if="activeTab === 'lineage'" class="workbench-card"><div class="section-heading"><div><h3>修订历史</h3><p>查看各报价修订版之间的关系。</p></div></div><ol class="lineage-list"><li v-for="row in revisionTreeRows" :key="row.id" :class="{ current: row.id === quote.id, child: row.depth }" :style="{ '--depth': row.depth }"><span class="lineage-connector"><span v-if="row.depth" class="version-tree-connector"><ArrowRight :size="13" /></span><i v-else class="lineage-dot" /></span><div class="lineage-row-main"><strong>{{ row.quote_no }}</strong><span>{{ revisionLabel(row) }}</span><span>{{ dateTime(row.created_at) }}</span><span class="status" :class="row.status">{{ row.status_display }}</span><em v-if="row.revision_summary">修订：{{ row.revision_summary }}</em></div><b>{{ row.currency }} {{ money(row.total_amount) }}</b><div class="lineage-actions"><button class="mini-btn" @click="openPreview(row.id)">预览 PI</button><button class="mini-btn" :disabled="row.id === quote.id" @click="changeVersion(row)">查看详情</button></div></li></ol></section>

          <section v-else-if="activeTab === 'orders'" class="workbench-card"><div class="section-heading"><div><h3>销售订单</h3><p>查看该报价及修订版生成的销售订单。</p></div></div><p v-if="!canCreateOrder" class="quote-order-unavailable">当前报价不能转单，请先创建修订版。</p><div v-if="!workbench.orders.length" class="workbench-empty"><ShoppingCart :size="28" /><strong>尚未创建销售订单</strong><p>创建销售订单后可继续编辑草稿。</p></div><div v-else class="order-list"><article v-for="order in workbench.orders" :key="order.id" class="order-card"><div><strong>{{ order.order_no }}</strong><small>来源报价：{{ order.source_quote_no || '—' }} · {{ order.order_date }}</small></div><div><span class="status" :class="order.status">{{ order.status_display }}</span><b>{{ order.currency }} {{ money(order.total_amount) }}</b></div><div class="order-actions"><button class="text-btn" @click="openPreview(order.quote)">预览来源 PI</button><button class="text-btn" @click="emit('open-order', order.id)">查看销售订单</button></div></article></div></section>

          <section v-else-if="activeTab === 'party-change'" class="workbench-card party-change-panel">
            <h3>主体变更申请</h3>
            <p>同一法律主体资料更正需由另一位已认证账号审批后生成报价草稿。系统不会自动核实法律主体是否变更，请由员工核对并提供依据。</p>
            <p>更换法律主体须选择新客户，经独立审批后填写新单；原单及其历史事实保留。</p>
            <p>匿名开发身份不能操作；需要两个不同的已认证账号。</p>
            <p v-if="!partyFormal" class="party-notice">仅已发送或已接受的报价可以提交、审批或生成草稿；当前报价状态不可操作，已有记录仍可查看。</p>
            <p v-if="partyLoading" role="status">正在加载主体资料…</p>
            <p v-if="partyError" role="alert" class="workbench-error">{{ partyError }}</p>
            <button v-if="partyError && !partyData && !partyLoading" type="button" class="btn btn-secondary" @click="loadPartyChange">重试</button>
            <template v-if="partyData">
              <p v-if="partyData.origin" class="party-notice">来源报价版本 ID：{{ partyData.origin.source_quote_id ?? '未记录' }} · 来源更正申请 ID：{{ partyData.origin.request_id ?? '未记录' }} · {{ partyData.origin.source_trust === 'unverified' ? '来源未核验' : '来源未知' }}。批准不代表历史资料已核实。</p>
              <p v-if="!partyData.current_user_id" class="party-notice">当前为匿名开发身份。主体更正需要两个不同的已认证账号：一人申请，另一人审批。</p>
              <p v-else class="party-notice">申请人不能审批自己的申请；最终由服务端验证身份和权限。</p>
              <label class="party-change-type">申请类型<select v-model="partyChangeType" :disabled="partyBusy || !partyFormal || !partyData.current_user_id || !can('quotes', 'update')"><option value="correction">同一法律主体资料更正</option><option value="replacement">更换法律主体</option></select></label>
              <p v-if="partyChangeType === 'correction'" class="party-notice">仅用于同一法律主体的资料更正；更换法律主体不能使用此选项。</p>
              <PartyReplacementForm v-else kind="quote" mode="propose" :source-id="quote.id" :source-party-id="quote.customer" :baseline="partyData.baseline" @completed="loadPartyChange" />
              <template v-if="partyChangeType === 'correction'">
              <div class="party-field-head"><strong>字段</strong><strong>原值</strong><strong>建议值</strong></div>
              <div v-for="[field, label] in partyFields" :key="field" class="party-field-row">
                <label :for="`party-${field}`">{{ label }}</label>
                <span class="party-original">{{ partyValue(partyData.baseline.snapshot[field]) }}</span>
                <div><input :id="`party-${field}`" :value="partyDraft[field] ?? ''" :placeholder="partyDraft[field] == null ? '历史未记录' : ''" :disabled="partyBusy || !partyFormal || !partyData.current_user_id || !can('quotes', 'update')" @input="partyDraft[field] = $event.target.value" /><button v-if="partyDraft[field] == null && partyData.current_user_id && can('quotes', 'update')" type="button" class="text-btn" :disabled="partyBusy || !partyFormal" @click="partyDraft[field] = ''">确认留空</button><small v-if="partyDraft[field] == null">未修改，仍为历史未知</small></div>
              </div>
              <div class="party-form-fields"><label>原因<textarea v-model="partyReason" :disabled="partyBusy || !partyFormal || !partyData.current_user_id || !can('quotes', 'update')" /></label><label>依据<textarea v-model="partyEvidence" :disabled="partyBusy || !partyFormal || !partyData.current_user_id || !can('quotes', 'update')" /></label></div>
              <template v-if="partyDraft.party_details"><h4>双方资料建议值</h4><PartyDetailsFields v-model="partyDraft.party_details" :editable="!partyBusy && partyFormal && !!partyData.current_user_id && can('quotes', 'update')" preserve-unknown /></template>
              <label v-if="partyChangeType === 'correction'" class="party-legal-confirm"><input v-model="partyLegalEntityConfirmed" type="checkbox" :disabled="partyBusy || !partyFormal || !partyData.current_user_id || !can('quotes', 'update')" /> 我已核对依据，确认法律主体未变</label>
              <button v-if="can('quotes', 'update')" type="button" class="btn btn-primary" :disabled="partyBusy || !partyFormal || !partyData.current_user_id" @click="submitPartyChange">{{ partyChangeType === 'correction' ? '提交更正申请' : '提交主体替换记录' }}</button>
              </template>
              <h3 class="party-requests-title">主体变更记录</h3>
              <p v-if="!partyData.requests.length">暂无主体变更申请。</p>
              <article v-for="request in partyData.requests" :key="request.id" class="party-request">
                <h4>申请 #{{ request.id }} · {{ request.change_type === 'correction' ? '法律主体资料更正' : '法律主体替换' }}</h4>
                <p>申请账号 ID：{{ request.initiator_id ?? '未记录' }} · 申请时间：{{ request.created_at ? dateTime(request.created_at) : '未记录' }} · {{ partyStatusLabel(request) }}</p>
                <p>原因：{{ request.reason }}　依据：{{ request.evidence }}</p>
                <p>来源：{{ request.source_trust === 'unverified' ? '未核验' : '未知' }}</p>
                <dl class="party-compare"><template v-for="[field, label] in partyFields" :key="field"><dt>{{ label }}</dt><dd>{{ partyValue(request.base_snapshot?.[field]) }} → {{ partyValue(request.proposed_snapshot?.[field]) }}</dd></template></dl>
                <PartyDetailsChanges :before="request.base_snapshot?.party_details" :after="request.proposed_snapshot?.party_details" />
          <p v-if="request.approval">审批账号 ID：{{ request.approval.approver_id ?? '未记录' }} · 审批时间：{{ request.approval.created_at ? dateTime(request.approval.created_at) : '未记录' }} · 意见：{{ request.approval.note || '未记录' }}</p>
                <p v-if="request.application">生效操作账号 ID：{{ request.application.applied_by_id ?? '未记录' }} · 生效时间：{{ request.application.created_at ? dateTime(request.application.created_at) : '未记录' }}</p>
                <p v-if="request.terminal_event">{{ partyStatusLabel(request) }} · 操作账号 ID：{{ request.terminal_event.actor_id ?? '未记录' }} · 时间：{{ request.terminal_event.created_at ? dateTime(request.terminal_event.created_at) : '未记录' }} · 原因：{{ request.terminal_event.note || '未记录' }}</p>
                <p v-if="partyRequestStatus(request) === 'pending' && !request.terminal_event && !request.approval && String(request.initiator_id) === String(partyData.current_user_id)">申请人不能审批自己的申请。</p>
                <template v-if="partyRequestStatus(request) === 'pending' && !request.terminal_event && !request.approval && request.initiator_id != null && ['correction', 'replacement'].includes(request.change_type) && partyData.current_user_id && String(request.initiator_id) !== String(partyData.current_user_id) && can('quotes', 'update')"><label class="party-approval-note">审批意见<input v-model="partyNotes[request.id]" :disabled="partyBusy || !partyFormal" /></label><button type="button" class="btn btn-secondary" :disabled="partyBusy || !partyFormal" @click="approvePartyChange(request)">{{ request.change_type === 'replacement' ? '批准主体替换记录' : '批准更正' }}</button></template>
                <p v-if="partyRequestStatus(request) === 'approved' && !request.terminal_event && request.change_type === 'correction' && request.approval && !request.application && partyData.current_user_id && can('quotes', 'update') && !partyCanApply">生成报价草稿需要报价创建和修改权限。</p>
                <button v-if="partyRequestStatus(request) === 'approved' && !request.terminal_event && request.change_type === 'correction' && request.approval && !request.application && partyData.current_user_id && can('quotes', 'update')" type="button" class="btn btn-primary" :disabled="partyBusy || !partyFormal || !partyCanApply" @click="applyPartyChange(request)">生成报价草稿</button>
                <button v-if="partyRequestStatus(request) === 'approved' && request.change_type === 'replacement' && request.replacement_target && partyCanApply" type="button" class="btn btn-primary" @click="replacementCreateId = replacementCreateId === request.id ? null : request.id">{{ replacementCreateId === request.id ? '收起新单' : '填写关联新单' }}</button>
                <PartyReplacementForm v-if="replacementCreateId === request.id && partyRequestStatus(request) === 'approved' && request.change_type === 'replacement'" kind="quote" mode="create" :source-id="quote.id" :request="request" @completed="loadPartyChange" />
                <template v-if="canHandlePartyRequest(request, 'withdraw') || canHandlePartyRequest(request, 'reject') || canHandlePartyRequest(request, 'invalidate')"><label class="party-approval-note">处理原因<input v-model="partyTerminalNotes[request.id]" :disabled="partyBusy" /></label><div class="party-terminal-actions"><button v-if="canHandlePartyRequest(request, 'withdraw')" type="button" class="btn btn-secondary" :disabled="partyBusy" @click="closePartyRequest(request, 'withdraw')">撤回申请</button><button v-if="canHandlePartyRequest(request, 'reject')" type="button" class="btn btn-secondary" :disabled="partyBusy" @click="closePartyRequest(request, 'reject')">拒绝申请</button><button v-if="canHandlePartyRequest(request, 'invalidate')" type="button" class="btn btn-secondary" :disabled="partyBusy" @click="closePartyRequest(request, 'invalidate')">标记失效</button></div></template>
                <button v-if="request.change_type === 'correction' && request.application?.result_quote_id" type="button" class="btn btn-secondary" @click="changeVersion({ id: request.application.result_quote_id })">查看新报价草稿</button>
                <button v-if="request.replacement_result?.result_quote_id" type="button" class="btn btn-secondary" @click="changeVersion({ id: request.replacement_result.result_quote_id })">查看关联报价</button>
              </article>
            </template>
          </section>

          <section v-else-if="activeTab === 'notes'" class="workbench-card notes-panel"><div class="note-caution"><AlertTriangle :size="18" /><p>备注可能已过时或不适用于最终订单，请核对来源版本和沟通记录。</p></div><div class="section-heading"><div><h3><StickyNote :size="16" /> 重要备注</h3><p>备注关联当前报价版本。</p></div><button v-if="can('quotes', 'update') && !noteEditorOpen" class="btn btn-primary" @click="noteEditorOpen = true"><Plus :size="15" /> 新增备注</button></div><template v-if="noteEditorOpen && can('quotes', 'update')"><RichTextEditor v-model="noteContent" /><div class="note-create"><button class="btn btn-secondary" @click="closeNoteEditor">取消</button><button class="btn btn-primary" :disabled="noteSaving || isRichTextEmpty(noteContent)" @click="createNote">{{ noteSaving ? '保存中…' : '保存重要备注' }}</button></div></template><div v-if="!workbench.important_notes.length" class="workbench-empty"><StickyNote :size="28" /><strong>暂无重要备注</strong></div><article v-for="note in workbench.important_notes" :key="note.id" class="important-note" :class="{ inactive: !note.is_active }"><header><div><strong>{{ note.is_active ? '有效备注' : '不再生效' }}</strong><small>备注于：{{ note.source_quote_no }}（{{ revisionLabel({ revision_no: note.source_revision_no }) }}） · {{ note.created_by_name }} · {{ dateTime(note.created_at) }}</small><small v-if="note.deactivated_at" class="note-deactivation">最近失效：{{ dateTime(note.deactivated_at) }} · {{ note.deactivated_by_name || '系统' }}</small><small v-else-if="!note.is_active" class="note-deactivation">最近失效：历史记录未保存操作时间和操作人</small></div><button v-if="can('quotes', 'update') && note.is_active" class="text-btn danger" @click="deactivateNote(note)">标记不再生效</button><button v-else-if="can('quotes', 'update')" class="text-btn restore" @click="restoreNote(note)">恢复生效</button></header><div class="important-note-content" v-html="note.content" /></article></section>

          <OperationLogPanel v-else :logs="operationLogs" :loading="operationLogsLoading" :enabled="auditEnabled" />
        </main>
      </template>
    </article>
    <QuotePreviewModal v-if="preview" :draft="preview" saved @close="preview = null" />
  </div>
</template>

<style scoped>
.party-change-panel>p{margin:8px 0 16px}.party-notice{padding:12px;background:#eef5f1;border-radius:8px;color:#315b4d}.party-field-head,.party-field-row{display:grid;grid-template-columns:minmax(90px,.7fr) minmax(140px,1fr) minmax(160px,1fr);gap:12px;align-items:start;padding:8px 0;border-bottom:1px solid #e5ece8}.party-field-head{color:#536b61}.party-field-row label{font-weight:600}.party-field-row input,.party-form-fields textarea,.party-approval-note input{width:100%;padding:8px;border:1px solid #b9c9c1;border-radius:6px;background:#fff}.party-field-row small{display:block;color:#6d7d75}.party-original,.party-compare dd{overflow-wrap:anywhere}.party-form-fields{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0}.party-form-fields label,.party-approval-note{display:grid;gap:6px}.party-form-fields textarea{min-height:75px;resize:vertical}.party-requests-title{margin-top:28px}.party-request{padding:16px 0;border-top:1px solid #e5ece8}.party-request p{margin:8px 0}.party-compare{display:grid;grid-template-columns:90px 1fr;gap:6px;margin:12px 0}.party-compare dd{margin:0}.party-approval-note{max-width:480px;margin:12px 0}.party-change-panel .workbench-error{color:#a12e2e}.party-change-panel button:disabled{opacity:.55}@media(max-width:700px){.party-field-head{display:none}.party-field-row{grid-template-columns:1fr;gap:5px}.party-original::before{content:'原值：'}.party-form-fields{grid-template-columns:1fr}}
.party-legal-confirm{display:flex;align-items:flex-start;gap:8px;margin:12px 0}.party-legal-confirm input{margin-top:4px;flex:none}
.party-terminal-actions{display:flex;flex-wrap:wrap;gap:8px}
.party-change-type{display:grid;gap:6px;margin:16px 0;max-width:480px;font-weight:600}.party-change-type select{width:100%;padding:9px;border:1px solid #b9c9c1;border-radius:6px;background:#fff}.party-replacement-notice{padding:12px;border:1px solid #d99b54;border-radius:8px;background:#fff5e5;color:#774214;font-weight:600}
.detail-backdrop{inset:0 0 0 248px;z-index:25;place-items:stretch end;padding:0;background:#0b221d66;backdrop-filter:blur(2px)}.detail-modal{height:100vh;width:min(1100px,100%);background:#f6f8f5;box-shadow:-24px 0 70px #06191452;overflow:auto;overscroll-behavior:contain}.detail-loading,.detail-error{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#71817b}.detail-error strong{color:#9d4444}.detail-error p{font-size:var(--text-body)}.detail-header{position:relative;overflow:hidden;padding:20px 28px 24px;background:#123c36;color:#fff}.detail-header:after{position:absolute;top:-140px;right:-80px;width:300px;height:300px;border:60px solid #ffffff08;border-radius:50%;content:''}.detail-nav,.detail-identity,.workbench-actions,.workbench-error{position:relative;z-index:1}.detail-nav,.detail-nav-start{display:flex;align-items:center}.detail-nav{justify-content:space-between;color:#91b6aa;font-size:var(--text-body);letter-spacing:.12em;text-transform:uppercase}.detail-nav-start{gap:10px}.detail-actions{display:flex;align-items:center;gap:8px}.detail-actions .btn{padding:7px 11px;color:#fff;font-size:var(--text-body);letter-spacing:0;text-transform:none;background:#ffffff12;border-color:#ffffff28}.detail-close{display:flex;align-items:center;gap:7px;min-height:38px;padding:8px 11px;border:1px solid #ffffff45;border-radius:9px;background:#ffffff1a;color:#fff;font-size:var(--text-body);font-weight:700;letter-spacing:0;text-transform:none}.detail-identity{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-top:23px}.detail-subtitle{margin:0;color:#9cc0b5;font-size:var(--text-caption)}.detail-identity h2{margin:5px 0 0;font-size:var(--text-page)}.detail-identity small{color:#b6d3ca;font-size:var(--text-caption)}.detail-badge{padding:6px 10px;border:1px solid #ffffff22;border-radius:20px;background:#ffffff14;font-size:var(--text-secondary)}.detail-content{padding:22px 25px 40px}.quote-workbench{font-size:var(--text-body)}.workbench-actions{display:flex;gap:8px;margin-top:18px}.workbench-actions .btn{padding:8px 11px;font-size:var(--text-body)}.workbench-error{margin:12px 0 0;color:#ffd9d9;font-size:var(--text-body)}.workbench-tabs{display:flex;gap:4px;margin:-22px -25px 18px;padding:0 25px;border-bottom:1px solid #e3eae6;overflow:auto;background:#fff}.workbench-tabs button{border:0;border-bottom:2px solid transparent;background:transparent;padding:13px 12px;color:#70807a;font-size:var(--text-body);white-space:nowrap}.workbench-tabs button.active{border-bottom-color:#1f6657;color:#174c41;font-weight:700}.workbench-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.workbench-card{padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.workbench-card h3{display:flex;align-items:center;gap:7px;margin:0;color:#1d3f36;font-size:var(--text-section)}.workbench-card p{margin:7px 0;color:#71817b;font-size:var(--text-body);line-height:1.55}.summary-card{grid-column:span 2;background:linear-gradient(135deg,#f8fcfa,#eef6f1)}.summary-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:16px}.summary-metrics small,.summary-metrics strong{display:block}.summary-metrics small{color:#7c8c85;font-size:var(--text-caption)}.summary-metrics strong{margin-top:5px;color:#164a3e;font-size:var(--text-dialog)}.data-list{display:grid;grid-template-columns:105px 1fr;gap:10px;margin:16px 0 0;font-size:var(--text-body)}.data-list dt{color:#7c8983}.data-list dd{margin:0;color:#31473f;word-break:break-word}.text-btn{border:0;background:transparent;padding:5px 0;color:#236657;font-size:var(--text-body);font-weight:700}.text-btn.danger{color:#aa4d4d}.section-heading{display:flex;align-items:start;justify-content:space-between;gap:12px;margin-bottom:16px}.section-heading p{margin-bottom:0}.workbench-table-wrap{overflow:auto;margin:0 -19px}.workbench-table{width:100%;min-width:760px;border-collapse:collapse}.workbench-table th,.workbench-table td{padding:11px 14px;border-top:1px solid #edf1ef;text-align:left;font-size:var(--text-body)}.workbench-table th{background:#f7faf8;color:#7d8c86;font-size:var(--text-body)}.workbench-table td:nth-last-child(-n+2){text-align:right;font-variant-numeric:tabular-nums}.quote-totals{margin-top:15px;text-align:right;color:#62736c;font-size:var(--text-body)}.quote-totals strong{color:#174b40;font-size:var(--text-body)}.lineage-list{display:grid;gap:0;margin:0;padding:0;list-style:none}.lineage-list li{display:grid;grid-template-columns:18px 1fr auto auto;gap:11px;align-items:center;padding:14px 5px;border-bottom:1px solid #edf1ef}.lineage-list li.current{background:#f0f7f3}.lineage-dot{width:10px;height:10px;border:3px solid #6a9b8c;border-radius:50%}.lineage-list strong,.lineage-list small{display:block}.lineage-list strong{color:#24463c}.lineage-list small{margin-top:3px;color:#7a8983;font-size:var(--text-caption)}.order-list{display:grid;gap:10px}.order-card{display:grid;grid-template-columns:1fr auto auto;gap:16px;align-items:center;padding:14px;border:1px solid #e2e9e5;border-radius:10px}.order-card strong,.order-card small{display:block}.order-card small{margin-top:4px;color:#7b8984;font-size:var(--text-caption)}.order-card b{display:block;margin-top:7px;color:#1a4c40;font-size:var(--text-body)}.order-actions{display:flex;gap:12px}.workbench-empty{display:grid;justify-items:center;padding:42px 15px;color:#82918b;text-align:center}.workbench-empty strong{margin-top:9px;color:#556961}.workbench-empty p{margin-top:4px}.note-caution{display:flex;gap:10px;margin-bottom:17px;padding:12px 14px;border:1px solid #efd6a4;border-radius:9px;background:#fff8e8;color:#82591f}.note-caution p{margin:0;color:inherit}.note-create{display:flex;justify-content:flex-end;margin:11px 0 20px}.important-note{padding:15px 0;border-top:1px solid #e5ece8}.important-note header{display:flex;justify-content:space-between;gap:10px;align-items:start}.important-note header strong,.important-note header small{display:block}.important-note header strong{color:#2b5346;font-size:var(--text-body)}.important-note header small{margin-top:4px;color:#7a8984;font-size:var(--text-caption)}.important-note.inactive header strong{color:#a05b5b}.important-note-content{margin-top:11px;color:#344a42;line-height:1.7;word-break:break-word}.important-note-content :deep(p){margin:0 0 8px}.important-note-content :deep(ul),.important-note-content :deep(ol){margin:4px 0;padding-left:22px}.important-note.inactive .important-note-content{text-decoration:line-through;color:#8a918e}@media(max-width:980px){.detail-backdrop{inset:0;z-index:60}}@media(max-width:700px){.detail-modal{width:100vw}.detail-header{padding:16px 17px 20px}.detail-identity h2{font-size:var(--text-page)}.detail-content{padding:12px}.workbench-grid{grid-template-columns:1fr}.summary-card{grid-column:auto}.summary-metrics{grid-template-columns:1fr}.workbench-tabs{margin-left:-12px;margin-right:-12px;padding:0 12px}.order-card{grid-template-columns:1fr}.order-actions{justify-content:flex-start}.lineage-list li{grid-template-columns:18px 1fr auto}.lineage-list li .mini-btn{grid-column:2}.workbench-actions .btn{padding:7px}.workbench-actions{flex-wrap:wrap}.detail-close span{display:none}.detail-close{padding:8px}}
.quote-status-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.quote-order-unavailable{position:relative;z-index:1;margin:12px 0 0;color:#ffe0ae;font-size:var(--text-body)}
.items-table td small { display: block; margin-top: 3px; color: var(--muted); line-height: 1.4; }
.party-reference{display:block;margin-top:3px;color:#b6d3ca;font-size:var(--text-caption)}
</style>

<style scoped>
.version-row-main,.lineage-row-main{display:flex;align-items:center;flex-wrap:wrap;gap:6px 8px}.summary-version-actions{display:flex;gap:12px;flex-wrap:wrap}
</style>

<style scoped>
.detail-header{padding:22px 26px}.detail-identity h2{font-size:var(--text-page);font-weight:700}.workbench-actions{flex-wrap:wrap;align-items:center}.workbench-actions .btn{min-height:36px;border-radius:8px}.workbench-actions .btn-secondary{background:#ffffff12;color:#fff;border:1px solid #ffffff28}.workbench-actions .transfer-order{order:-1;background:#f5fcf8;color:#174c41;border:1px solid #b8dccf;font-weight:700;padding:8px 13px}.workbench-actions .quote-utility{margin-left:auto;background:transparent;color:#b6d3ca;border:1px solid #ffffff28}.quote-status-actions .btn{min-height:30px;padding:5px 10px;background:transparent;color:#b6d3ca;border:1px solid #ffffff28;font-size:var(--text-caption)}.workbench-tabs button{min-height:44px;padding:10px 13px}.workbench-grid{gap:16px}.workbench-card{padding:16px}.workbench-table-wrap{margin-left:-16px;margin-right:-16px}.detail-nav{flex-wrap:wrap;gap:12px}
</style>
