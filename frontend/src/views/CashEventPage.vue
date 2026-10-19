<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import { apiErrorMessage } from '../utils/apiErrors.js'
import PageLoadState from '../components/PageLoadState.vue'
import ListEmptyState from '../components/ListEmptyState.vue'
import { useAccessControl } from '../accessControl'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'

const { can } = useAccessControl()
const today = new Date().toLocaleDateString('en-CA')
const currencies = [
  { value: 'CNY', label: 'CNY · 人民币' },
  { value: 'USD', label: 'USD · 美元' },
  { value: 'EUR', label: 'EUR · 欧元' },
  { value: 'GBP', label: 'GBP · 英镑' },
  { value: 'HKD', label: 'HKD · 港币' },
  { value: 'AUD', label: 'AUD · 澳元' },
  { value: 'JPY', label: 'JPY · 日元' },
]
const events = ref([])
const loading = ref(true)
const hasLoaded = ref(false)
const loadError = ref('')
const error = ref('')
const notice = ref('')
const statusFilter = ref('')
const listSearch = ref('')
const selected = ref(null)
const showForm = ref(false)
const formStep = ref('form')
const saving = ref(false)
const confirming = ref(false)
const cancelling = ref(false)
const lookupLoading = ref(false)
const cancelReason = ref('')
const showCancelReason = ref(false)
const saveOutcome = ref('not-submitted')
const preview = ref(null)
const previewFingerprint = ref('')
const previewRequestId = ref(0)
const sourceRows = ref([])
const sourceLoading = ref(false)
const sourceError = ref('')
const sourceSearch = ref('')
const allocations = ref([])
const reviewConfirmed = ref(false)
const draftRestored = ref(false)
const draftRestoredRequiresEvidence = ref(false)
const draftStorageKey = 'sunjack:r1-fin-p2-b:cash-event-draft:v1'
const draftFormFields = [
  'event_no', 'request_key', 'kind', 'currency', 'direction', 'bank_date', 'bank_net_amount',
  'fee_mode', 'fee_amount', 'source_account', 'rmb_account', 'bank_reference', 'quoted_rate', 'fee_for',
]
const allocationAmountBaseline = new Map()
let sourceRequestId = 0
let sourceAbortController = null
const form = reactive({
  event_no: '', request_key: '', kind: 'fx_settlement', currency: 'USD', direction: 'income',
  bank_date: today, bank_net_amount: '', fee_mode: 'none', fee_amount: '0',
  source_account: '', rmb_account: '', bank_reference: '', evidence_reference: '',
  evidence_sha256: '', evidence_note: '', quoted_rate: '', fee_for: '',
})

function makeKey(prefix) {
  const uuid = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `P2B-${prefix}-${uuid}`.replace(/[^A-Za-z0-9_-]/g, '-')
}
function resetForm() {
  Object.assign(form, { event_no: makeKey('EVENT'), request_key: makeKey('REQUEST'), kind: 'fx_settlement', currency: 'USD', direction: 'income', bank_date: today, bank_net_amount: '', fee_mode: 'none', fee_amount: '0', source_account: '', rmb_account: '', bank_reference: '', evidence_reference: '', evidence_sha256: '', evidence_note: '', quoted_rate: '', fee_for: '' })
  allocations.value = []
  preview.value = null
  previewFingerprint.value = ''
  reviewConfirmed.value = false
  draftRestoredRequiresEvidence.value = false
  allocationAmountBaseline.clear()
  formStep.value = 'form'
  saveOutcome.value = 'not-submitted'
  showCancelReason.value = false
  cancelReason.value = ''
  error.value = ''
  sourceError.value = ''
  sourceSearch.value = ''
}
function clearDraftSnapshot() {
  if (typeof window === 'undefined') return
  try { window.localStorage.removeItem(draftStorageKey) } catch { /* Storage may be disabled. */ }
}
function persistedDraftForm() {
  return Object.fromEntries(draftFormFields.map(field => [field, form[field]]))
}
function draftSnapshot() {
  return {
    version: 2,
    saved_at: Date.now(),
    form: persistedDraftForm(),
    allocations: allocations.value.map(item => ({ id: item.id, amount: item.amount, verified: item.verified === true })),
  }
}
function persistDraftSnapshot() {
  if (typeof window === 'undefined' || !showForm.value || formStep.value !== 'form') return
  try { window.localStorage.setItem(draftStorageKey, JSON.stringify(draftSnapshot())) } catch { /* Keep the form usable when storage is unavailable. */ }
}
function clearExpiredDraftSnapshot() {
  if (typeof window === 'undefined') return
  try {
    const raw = window.localStorage.getItem(draftStorageKey)
    if (!raw) return
    const saved = JSON.parse(raw)
    if (!saved?.saved_at || Date.now() - saved.saved_at > 24 * 60 * 60 * 1000 || !saved.form?.request_key) clearDraftSnapshot()
  } catch {
    clearDraftSnapshot()
  }
}
function restoreDraftSnapshot() {
  if (typeof window === 'undefined') return false
  try {
    const raw = window.localStorage.getItem(draftStorageKey)
    if (!raw) return false
    const saved = JSON.parse(raw)
    if (!saved?.saved_at || Date.now() - saved.saved_at > 24 * 60 * 60 * 1000 || !saved.form?.request_key) {
      clearDraftSnapshot(); return false
    }
    const safeForm = Object.fromEntries(draftFormFields.map(field => [field, saved.form[field] ?? form[field]]))
    Object.assign(form, safeForm)
    allocations.value = Array.isArray(saved.allocations)
      ? saved.allocations.map(item => ({ id: item.id, amount: item.amount ?? '', verified: item.verified === true }))
      : []
    draftRestored.value = true
    draftRestoredRequiresEvidence.value = true
    return true
  } catch {
    clearDraftSnapshot(); return false
  }
}
function money(value, currency = 'CNY') {
  if (value === null || value === undefined || value === '') return '待核对'
  const digits = currency === 'JPY' ? 0 : 2
  return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}
function statusLabel(value) { return ({ pending: '待确认', confirmed: '已确认', cancelled: '已放弃' })[value] || value || '—' }
function kindLabel(value) { return ({ fx_settlement: '外币结汇到账', cny_direct: '人民币直接收付', bank_fee: '独立银行扣费' })[value] || value || '—' }
function directionLabel(value) { return value === 'income' ? '流入' : value === 'expense' ? '流出' : '—' }
function sourceLabel(row) { return `${row.transaction_no || `流水 #${row.id}`} · ${row.currency} ${money(row.amount, row.currency)}` }
function allocationFor(id) { return allocations.value.find(item => item.id === id) }
function needsExplicitPrecision(value, currency) {
  const digits = currency === 'JPY' ? 0 : 2
  return String(value).split('.')[1]?.length > digits
}
function sourceTotal() { return allocations.value.reduce((total, item) => total + (Number(item.amount) || 0), 0) }
function filteredSources() {
  const keyword = sourceSearch.value.trim().toLowerCase()
  return sourceRows.value.filter(row => !keyword || `${row.transaction_no} ${row.id}`.toLowerCase().includes(keyword))
}
function stableSerialize(value) {
  if (Array.isArray(value)) return `[${value.map(stableSerialize).join(',')}]`
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableSerialize(value[key])}`).join(',')}}`
  return JSON.stringify(value)
}
function payloadFingerprint(payload) { return stableSerialize(payload) }
function eventPayload() {
  return {
    event_no: form.event_no.trim(), request_key: form.request_key.trim(), kind: form.kind, currency: form.currency,
    direction: form.direction, bank_date: form.bank_date, bank_net_amount: form.bank_net_amount, fee_mode: form.fee_mode,
    fee_amount: form.fee_mode === 'included' ? form.fee_amount : '0', source_account: form.source_account.trim(), rmb_account: form.rmb_account.trim(),
    bank_reference: form.bank_reference.trim(), evidence_reference: form.evidence_reference.trim(), evidence_sha256: form.evidence_sha256.trim(),
    evidence_note: String(form.evidence_note || '').trim(), quoted_rate: form.quoted_rate === null || form.quoted_rate === undefined || form.quoted_rate === '' ? null : String(form.quoted_rate).trim(), fee_for: form.fee_for ? Number(form.fee_for) : null,
    correction_of: null, sources: allocations.value.filter(item => item.amount !== '' && Number(item.amount) > 0).map(item => ({ transaction_id: item.id, amount: String(item.amount).trim(), verified: item.verified === true })),
  }
}
function clientError() {
  if (!form.event_no || !form.request_key) return '请先填写事件编号和稳定请求键。'
  if (!form.bank_date || !form.bank_reference) return '请填写银行日期和银行参考号。'
  if (draftRestoredRequiresEvidence.value && (!form.evidence_reference || !form.evidence_sha256 || !form.evidence_note)) return '恢复的草稿未保存凭证资料，请重新填写凭证引用、SHA256和人工核实说明。'
  if (!form.source_account || !form.rmb_account) return '请填写受控账户标识；账户未配置时确认仍会被后端阻止。'
  if (!form.bank_net_amount || Number(form.bank_net_amount) <= 0) return '请填写大于0的银行净额。'
  if (!allocations.value.length) return '请至少选择一条来源流水。'
  if (allocations.value.some(item => !item.amount || Number(item.amount) <= 0)) return '每条来源都要填写大于0的分配金额。'
  if (allocations.value.some(item => item.verified !== true)) return '请逐条核实来源流水后再预览。'
  if (form.kind === 'fx_settlement' && form.currency === 'CNY') return '结汇来源必须是外币；人民币直接收付请选择对应类型。'
  if (form.kind === 'fx_settlement' && form.direction !== 'income') return '结汇只支持人民币资金流入。'
  if (form.kind === 'bank_fee' && !form.fee_for) return '独立银行扣费需要关联已确认结汇事件。'
  return ''
}
async function loadEvents() {
  loading.value = true; loadError.value = ''
  try { events.value = (await api.get('/rmb-cash-events/')).data.results || []; hasLoaded.value = true }
  catch (err) { loadError.value = apiErrorMessage(err) || '人民币资金记录加载失败，请重试。' }
  finally { loading.value = false }
}
async function loadSources() {
  const requestId = ++sourceRequestId
  sourceAbortController?.abort()
  sourceAbortController = typeof AbortController !== 'undefined' ? new AbortController() : null
  const currency = form.currency
  sourceLoading.value = true; sourceError.value = ''; sourceRows.value = []
  try {
    const response = await api.get('/rmb-cash-events/sources/', { params: { currency }, signal: sourceAbortController?.signal })
    if (requestId !== sourceRequestId || form.currency !== currency) return
    sourceRows.value = response.data.results || []
  } catch (err) {
    if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError' || requestId !== sourceRequestId) return
    sourceRows.value = []; sourceError.value = apiErrorMessage(err) || '来源流水加载失败，请重试。'
  } finally { if (requestId === sourceRequestId) sourceLoading.value = false }
}
function openCreate() {
  if (!can('transactions', 'create')) return
  resetForm(); draftRestored.value = false; showForm.value = true; selected.value = null
  formGuard.markClean()
  const restored = restoreDraftSnapshot()
  if (restored) notice.value = '已恢复未完成草稿；凭证资料未保存在本地，请重新填写后再预览。'
  void loadSources()
}
function closeForm() { return formGuard.requestClose(() => { clearDraftSnapshot(); showForm.value = false; selected.value = null; preview.value = null; previewFingerprint.value = '' }) }
function addSource(row) {
  if (row.blocked_reason || row.remaining_candidate_amount === null || allocationFor(row.id)) return
  allocations.value.push({ id: row.id, amount: needsExplicitPrecision(row.remaining_candidate_amount, form.currency) ? '' : row.remaining_candidate_amount, verified: false })
}
function removeSource(id) { allocations.value = allocations.value.filter(item => item.id !== id); allocationAmountBaseline.delete(id) }
function markAllocationEdited(item) { item.verified = false }
function onKindChange() {
  if (form.kind === 'fx_settlement') { form.currency = form.currency === 'CNY' ? 'USD' : form.currency; form.direction = 'income'; form.fee_for = '' }
  if (form.kind === 'cny_direct' || form.kind === 'bank_fee') { form.currency = 'CNY'; if (form.kind === 'bank_fee') form.direction = 'expense'; form.quoted_rate = '1' }
  allocations.value = []
  void loadSources()
}
function onCurrencyChange() { allocations.value = []; void loadSources() }
async function previewEvent() {
  error.value = ''; notice.value = ''; saveOutcome.value = 'submitting'
  const localError = clientError(); if (localError) { error.value = localError; saveOutcome.value = 'not-submitted'; return }
  saving.value = true
  const requestId = ++previewRequestId.value
  const payload = eventPayload()
  const fingerprint = payloadFingerprint(payload)
  try {
    const response = await api.post('/rmb-cash-events/preview/', payload)
    if (requestId !== previewRequestId.value || payloadFingerprint(eventPayload()) !== fingerprint) {
      preview.value = null; previewFingerprint.value = ''; saveOutcome.value = 'not-submitted'; notice.value = '表单已修改，旧预览已失效，请重新预览。'; return
    }
    preview.value = response.data; previewFingerprint.value = fingerprint; notice.value = '后端预览已完成；来源额度尚未占用。'; saveOutcome.value = 'previewed'
  }
  catch (err) { saveOutcome.value = 'failed'; error.value = apiErrorMessage(err) || '预览失败，已保留全部输入。' }
  finally { saving.value = false }
}
async function registerDraft() {
  error.value = ''; notice.value = ''
  const localError = clientError(); if (localError) { error.value = localError; return }
  if (!preview.value || !previewFingerprint.value || payloadFingerprint(eventPayload()) !== previewFingerprint.value) { preview.value = null; previewFingerprint.value = ''; saveOutcome.value = 'not-submitted'; error.value = '预览已失效，请重新预览后再登记。'; return }
  saving.value = true; saveOutcome.value = 'submitting'
  try {
    const response = await api.post('/rmb-cash-events/', eventPayload())
    selected.value = response.data; formStep.value = 'review'; showCancelReason.value = false; preview.value = null; previewFingerprint.value = ''; reviewConfirmed.value = false; clearDraftSnapshot(); formGuard.markClean(); saveOutcome.value = 'saved'; notice.value = response.status === 200 ? '已按稳定请求键回查原资金事件。' : '已登记待确认资金事件。'
    await loadEvents()
  } catch (err) {
    saveOutcome.value = 'unknown'
    const status = err?.status || err?.response?.status
    error.value = status ? (apiErrorMessage(err) || '登记失败，输入仍已保留。') : `登记结果尚未确认。请按请求键 ${form.request_key} 回查，不要新建同笔记录。`
  } finally { saving.value = false }
}
async function lookupRequest() {
  if (!form.request_key || lookupLoading.value) return
  lookupLoading.value = true; error.value = ''
  try { selected.value = (await api.get('/rmb-cash-events/by-request-key/', { params: { request_key: form.request_key } })).data; formStep.value = 'review'; reviewConfirmed.value = false; clearDraftSnapshot(); formGuard.markClean(); notice.value = '已按稳定请求键找到历史结果。'; await loadEvents() }
  catch (err) { error.value = apiErrorMessage(err) || '未找到可查看的资金事件；请保留请求键并核对后端。' }
  finally { lookupLoading.value = false }
}
async function confirmEvent() {
  if (!selected.value || confirming.value || !reviewConfirmed.value) return
  confirming.value = true; error.value = ''; notice.value = ''
  try { selected.value = (await api.post(`/rmb-cash-events/${selected.value.id}/confirm/`, { voucher_checked: true })).data; notice.value = '资金事件已确认，已保存银行凭证核实结果。'; reviewConfirmed.value = false; clearDraftSnapshot(); formGuard.markClean(); await loadEvents() }
  catch (err) { error.value = apiErrorMessage(err) || '确认失败；记录仍保留为待确认。' }
  finally { confirming.value = false }
}
async function cancelDraft() {
  if (!selected.value || cancelling.value || !cancelReason.value.trim()) return
  cancelling.value = true; error.value = ''; notice.value = ''
  try { selected.value = (await api.post(`/rmb-cash-events/${selected.value.id}/cancel/`, { reason: cancelReason.value.trim() })).data; showCancelReason.value = false; notice.value = '待确认草稿已留痕放弃，来源额度未被释放为银行事实。'; reviewConfirmed.value = false; clearDraftSnapshot(); formGuard.markClean(); await loadEvents() }
  catch (err) { error.value = apiErrorMessage(err) || '草稿放弃失败，原记录仍保留。' }
  finally { cancelling.value = false }
}
function openDetail(row) { selected.value = row; reviewConfirmed.value = false; showForm.value = false; error.value = ''; notice.value = '' }
function filteredEvents() {
  const keyword = listSearch.value.trim().toLowerCase()
  return events.value.filter(row => (!statusFilter.value || row.status === statusFilter.value) && (!keyword || `${row.event_no} ${row.request_key} ${row.bank_reference}`.toLowerCase().includes(keyword)))
}
const filtered = computed(filteredEvents)
const canCreate = computed(() => can('transactions', 'create'))
const formGuard = useUnsavedChangesGuard({
  data: () => ({ ...form, allocations: allocations.value, step: formStep.value }),
  enabled: () => showForm.value && formStep.value === 'form',
  busy: () => saving.value || confirming.value || cancelling.value,
  confirmOptions: () => saveOutcome.value === 'unknown' ? { title: '登记结果尚未确认', message: `请求键：${form.request_key}。后端可能已经登记，请先按请求键回查；放弃当前表单不会撤销已保存记录。`, cancelText: '继续核对', confirmText: '已记录请求键，放弃表单' } : {},
})
watch(() => form.kind, value => { if (value === 'fx_settlement' && form.currency === 'CNY') form.currency = 'USD' })
watch([form, allocations], () => {
  if (showForm.value && formStep.value === 'form') {
    const presentIds = new Set()
    allocations.value.forEach(item => {
      presentIds.add(item.id)
      const amount = String(item.amount ?? '').trim()
      const previousAmount = allocationAmountBaseline.get(item.id)
      if (previousAmount !== undefined && previousAmount !== amount) item.verified = false
      allocationAmountBaseline.set(item.id, amount)
    })
    for (const id of allocationAmountBaseline.keys()) if (!presentIds.has(id)) allocationAmountBaseline.delete(id)
    persistDraftSnapshot()
    if (preview.value || previewFingerprint.value) {
      previewRequestId.value += 1; preview.value = null; previewFingerprint.value = ''; saveOutcome.value = 'not-submitted'; notice.value = '表单已修改，旧预览已失效，请重新预览。'
    }
  }
}, { deep: true })
onMounted(() => { clearExpiredDraftSnapshot(); loadEvents() })
</script>

<template>
  <section class="cash-events-page">
    <header class="cash-page-head">
      <div><p class="eyebrow">人民币实际资金</p><h2>银行资金记录</h2><p class="page-lede">记录银行凭证确认的人民币净到账或扣款。结汇不新增客户收款，也不改变应收核销。</p></div>
      <div class="head-actions"><RouterLink class="secondary-link" to="/transactions">查看财务流水</RouterLink><button v-if="canCreate" class="primary" type="button" @click="openCreate">新建资金事件</button></div>
    </header>
    <p class="definition-note"><strong>口径：</strong>只有人工核实银行凭证的事件可以确认。参考折算只用于对照，不代表银行实际到账；手续费按银行净额说明，不重复扣除。</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <p v-if="error && !showForm" class="error" role="alert">{{ error }}</p>
    <form class="cash-filters" aria-label="人民币资金筛选" @submit.prevent>
      <label>状态<select v-model="statusFilter"><option value="">全部状态</option><option value="pending">待确认</option><option value="confirmed">已确认</option><option value="cancelled">已放弃</option></select></label>
      <label class="search-field">搜索<input v-model="listSearch" type="search" placeholder="事件编号、请求键或银行参考号"></label>
      <button type="button" class="secondary" @click="loadEvents">刷新</button>
    </form>
    <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="loadError" @retry="loadEvents" />
    <table v-if="hasLoaded" class="cash-table"><thead><tr><th>银行日期 / 事件编号</th><th>类型</th><th>原币来源</th><th>银行净额</th><th>手续费</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr v-if="!filtered.length"><td colspan="7"><ListEmptyState entity="人民币资金事件" :filtered="Boolean(statusFilter || listSearch)" @clear="statusFilter = ''; listSearch = ''"><template #action>当前还没有人民币资金事件。</template></ListEmptyState></td></tr>
      <tr v-for="row in filtered" :key="row.id" class="cash-row" @click="openDetail(row)"><td>{{ row.bank_date }}<small>{{ row.event_no }}</small></td><td>{{ kindLabel(row.kind) }}<small>{{ directionLabel(row.direction) }}</small></td><td>{{ row.currency }} {{ money(row.amount, row.currency) }}<small>{{ row.sources?.length || 0 }} 条来源</small></td><td>CNY {{ money(row.bank_net_amount) }}<small>{{ row.bank_reference }}</small></td><td>{{ row.fee_mode === 'included' ? `含扣 CNY ${money(row.fee_amount)}` : '无' }}</td><td><span class="status" :class="row.status">{{ statusLabel(row.status) }}</span></td><td><button type="button" class="row-action" @click.stop="openDetail(row)">查看详情</button></td></tr>
    </tbody></table>

    <div v-if="selected && !showForm" class="cash-detail-panel" role="dialog" aria-modal="true" aria-labelledby="cash-detail-title"><header><div><p class="eyebrow">银行资金事件</p><h3 id="cash-detail-title">{{ selected.event_no }}</h3></div><button type="button" class="close-button" aria-label="关闭资金详情" @click="selected = null">×</button></header><div class="detail-status"><span class="status" :class="selected.status">{{ statusLabel(selected.status) }}</span><span>{{ kindLabel(selected.kind) }} · {{ directionLabel(selected.direction) }}</span></div><dl class="detail-grid"><dt>银行日期</dt><dd>{{ selected.bank_date }}</dd><dt>银行净额</dt><dd>CNY {{ money(selected.bank_net_amount) }}</dd><dt>原币来源</dt><dd>{{ selected.currency }} {{ money(selected.amount, selected.currency) }}</dd><dt>手续费</dt><dd>{{ selected.fee_mode === 'included' ? `含扣 CNY ${money(selected.fee_amount)}` : '无' }}</dd><dt>银行参考号</dt><dd>{{ selected.bank_reference }}</dd><dt>凭证引用</dt><dd>{{ selected.evidence_reference || '待确认' }}</dd><dt>来源账户</dt><dd>{{ selected.source_account }}</dd><dt>人民币账户</dt><dd>{{ selected.rmb_account }}</dd><dt>参考折算</dt><dd>CNY {{ money(selected.reference_amount) }}（差额 {{ money(selected.net_minus_reference_information_only) }}，仅供信息对照）</dd><dt>请求键</dt><dd>{{ selected.request_key }}</dd></dl><p class="detail-note">{{ selected.note }}</p><section><h4>来源分配</h4><table class="source-detail"><thead><tr><th>流水</th><th>分配</th><th>状态</th></tr></thead><tbody><tr v-for="source in selected.sources" :key="source.transaction_id"><td>{{ source.snapshot?.transaction_no || `流水 #${source.transaction_id}` }}</td><td>{{ source.currency }} {{ money(source.amount, source.currency) }}</td><td>已锁定来源快照</td></tr></tbody></table></section><footer class="detail-actions"><button type="button" class="secondary" @click="selected = null">关闭</button></footer></div>

    <div v-if="showForm" class="mask" @click.self="closeForm"><form class="cash-dialog" role="dialog" aria-modal="true" aria-labelledby="cash-form-title" @submit.prevent="formStep === 'form' ? (preview ? registerDraft() : previewEvent()) : undefined"><header class="dialog-head"><div><p class="eyebrow">人工凭证流程</p><h3 id="cash-form-title">{{ formStep === 'form' ? '新建人民币资金事件' : '资金事件待确认' }}</h3><p v-if="formStep === 'form'">先预览，再登记待确认草稿，最后单独确认银行凭证。</p><p v-else>已登记的事件只读，确认或放弃都会保留审计留痕。</p></div><button type="button" class="close-button" aria-label="关闭资金表单" :disabled="saving || confirming || cancelling" @click="closeForm">×</button></header>
      <div v-if="saveOutcome === 'unknown'" class="warning-box" role="alert"><strong>登记结果尚未确认</strong><p>请按请求键回查，不要生成新的请求键。请求键：<code>{{ form.request_key }}</code></p><button type="button" class="secondary" :disabled="lookupLoading" @click="lookupRequest">{{ lookupLoading ? '回查中…' : '按请求键回查' }}</button></div>
      <div v-if="formStep === 'form'">
        <fieldset :disabled="saving"><legend>1. 事件与银行金额</legend><div class="form-grid"><label>事件编号<input v-model="form.event_no" maxlength="64" required></label><label>稳定请求键<input v-model="form.request_key" maxlength="128" required><small>重试必须沿用此编号。</small></label><label>事件类型<select v-model="form.kind" @change="onKindChange"><option value="fx_settlement">外币结汇到账</option><option value="cny_direct">人民币直接收付</option><option value="bank_fee">独立银行扣费</option></select></label><label>来源币种<select v-model="form.currency" @change="onCurrencyChange"><option v-for="item in currencies" :key="item.value" :value="item.value">{{ item.label }}</option></select></label><label>资金方向<select v-model="form.direction" :disabled="form.kind === 'fx_settlement'"><option value="income">流入</option><option value="expense">流出</option></select></label><label>银行实际日期<input v-model="form.bank_date" type="date" required></label><label>银行净额（CNY）<input v-model="form.bank_net_amount" type="number" min="0.01" step="0.01" required><small>以银行凭证净到账/扣款为准。</small></label><label>参考折算汇率<input v-model="form.quoted_rate" type="text" inputmode="decimal" placeholder="可留空"><small>仅作差异对照，不覆盖银行净额；保留原始十进制输入。</small></label><label>手续费方式<select v-model="form.fee_mode"><option value="none">无含扣手续费</option><option value="included">净额已含扣费</option></select></label><label v-if="form.fee_mode === 'included'">含扣手续费（CNY）<input v-model="form.fee_amount" type="number" min="0.01" step="0.01" required></label></div></fieldset>
        <fieldset :disabled="saving"><legend>2. 银行凭证与受控账户</legend><div class="form-grid"><label>来源银行账户标识<input v-model="form.source_account" maxlength="40" placeholder="例如 SYNTH-FX-01" required></label><label>人民币账户标识<input v-model="form.rmb_account" maxlength="40" placeholder="例如 SYNTH-CNY-01" required></label><label>银行参考号<input v-model="form.bank_reference" maxlength="120" required></label><label>凭证引用<input v-model="form.evidence_reference" maxlength="200" placeholder="文件名或内部凭证编号"></label><label class="wide">凭证 SHA256<input v-model="form.evidence_sha256" maxlength="64" placeholder="确认时必填"></label><label class="wide">人工核实说明<textarea v-model="form.evidence_note" maxlength="500" rows="2" placeholder="确认时必填，记录核对人和核对内容"></textarea></label></div><p class="field-hint">账户标识仅用于后端受控校验，不填写银行登录信息。当前环境未配置账户时，确认会被安全阻止。</p></fieldset>
        <fieldset :disabled="saving"><legend>3. 来源分配</legend><div class="source-toolbar"><input v-model="sourceSearch" type="search" placeholder="搜索流水号"><button type="button" class="secondary" @click="loadSources">刷新来源</button></div><p v-if="sourceError" class="error" role="alert">{{ sourceError }} <button type="button" class="secondary" @click="loadSources">重试</button></p><p v-else-if="sourceLoading" class="field-hint" role="status">正在加载可用来源…</p><div v-else class="source-list"><div v-for="row in filteredSources()" :key="row.id" class="source-option"><div><strong>{{ sourceLabel(row) }}</strong><small>{{ row.direction === 'income' ? '收入' : '支出' }} · 可用 {{ row.remaining_candidate_amount === null ? '待核对' : `${row.currency} ${money(row.remaining_candidate_amount, row.currency)}` }}</small><small v-if="row.blocked_reason" class="blocked">{{ row.blocked_reason }}</small></div><button type="button" :disabled="Boolean(row.blocked_reason) || row.remaining_candidate_amount === null || Boolean(allocationFor(row.id))" @click="addSource(row)">{{ allocationFor(row.id) ? '已选择' : row.remaining_candidate_amount === null ? '待核对' : '选择' }}</button></div><p v-if="!filteredSources().length" class="empty-note">没有可选择的来源流水。</p></div><div v-if="allocations.length" class="allocation-table"><table><thead><tr><th>来源</th><th>可用额度</th><th>本次分配</th><th>人工核实</th><th></th></tr></thead><tbody><tr v-for="item in allocations" :key="item.id"><td>{{ sourceRows.find(row => row.id === item.id)?.transaction_no || `流水 #${item.id}` }}</td><td>{{ sourceRows.find(row => row.id === item.id)?.remaining_candidate_amount === null ? '待核对' : `${form.currency} ${money(sourceRows.find(row => row.id === item.id)?.remaining_candidate_amount, form.currency)}` }}</td><td><input v-model="item.amount" @input="markAllocationEdited(item)" type="number" min="0.01" :step="form.currency === 'JPY' ? '1' : '0.01'" required></td><td><label class="verification-toggle"><input v-model="item.verified" type="checkbox"><span>{{ item.verified ? '已核实' : '待核实' }}</span></label></td><td><button type="button" class="text-button" @click="removeSource(item.id)">移除</button></td></tr></tbody></table><p class="allocation-total">已分配 {{ form.currency }} {{ money(sourceTotal(), form.currency) }} · 银行净额 CNY {{ money(form.bank_net_amount) }}</p></div></fieldset>
        <p v-if="allocations.some(item => !item.amount)" class="field-hint">历史来源保留了更高精度，请按币种精度人工填写本次分配；系统不会自动舍入历史金额。</p>
        <p v-if="preview" class="preview-box" role="status"><strong>后端预览通过</strong>：来源合计 {{ form.currency }} {{ money(preview.source_total, form.currency) }}，银行净额 CNY {{ money(preview.bank_net_amount) }}。预览不会占用额度；修改金额、日期、手续费、来源或凭证后必须重新预览。</p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <footer class="dialog-actions"><button type="button" class="secondary" :disabled="saving" @click="closeForm">取消</button><button v-if="!preview" class="primary" :disabled="saving" @click="previewEvent">{{ saving ? '预览中…' : '后端预览' }}</button><button v-else class="primary" :disabled="saving" @click="registerDraft">{{ saving ? '登记中…' : '登记待确认草稿' }}</button></footer>
      </div>
      <div v-else class="review-step"><div class="review-banner"><span class="status" :class="selected?.status">{{ statusLabel(selected?.status) }}</span><strong>{{ selected?.event_no }}</strong><small>请求键：{{ selected?.request_key }}</small></div><div class="detail-grid"><div><span>银行日期</span><strong>{{ selected?.bank_date }}</strong></div><div><span>银行参考号</span><strong>{{ selected?.bank_reference }}</strong></div><div><span>类型 / 方向</span><strong>{{ kindLabel(selected?.kind) }} · {{ directionLabel(selected?.direction) }}</strong></div><div><span>来源币种总额</span><strong>{{ selected?.currency }} {{ money(selected?.amount, selected?.currency) }}</strong></div><div><span>银行净额</span><strong>CNY {{ money(selected?.bank_net_amount) }}</strong></div><div><span>手续费</span><strong>{{ selected?.fee_mode === 'included' ? '含扣 CNY ' + money(selected?.fee_amount) : '无含扣手续费' }}</strong></div><div><span>来源银行账户</span><strong>{{ selected?.source_account }}</strong></div><div><span>人民币账户</span><strong>{{ selected?.rmb_account }}</strong></div><div><span>凭证引用</span><strong>{{ selected?.evidence_reference || '待确认' }}</strong></div><div><span>参考差异</span><strong>CNY {{ money(selected?.net_minus_reference_information_only) }}</strong></div></div><p class="definition-note">{{ selected?.note }}</p><section class="review-sources"><h4>来源分配</h4><table class="source-detail"><thead><tr><th>流水</th><th>分配</th><th>核实</th></tr></thead><tbody><tr v-for="source in selected?.sources" :key="source.transaction_id"><td>{{ source.snapshot?.transaction_no || ('流水 #' + source.transaction_id) }}</td><td>{{ source.currency }} {{ money(source.amount, source.currency) }}</td><td>{{ source.verified === false ? '未核实' : '已核实（已通过登记校验）' }}</td></tr></tbody></table></section><p v-if="selected?.status === 'pending'" class="field-hint">请核对银行日期、参考号、凭证、账户、净额、手续费和每条来源分配。未配置受控账户时，后端会拒绝确认并保留待确认状态。</p><label v-if="selected?.status === 'pending'" class="review-confirm"><input v-model="reviewConfirmed" type="checkbox">我已核对以上银行凭证和来源分配，确认提交人工核实结果。</label><div v-if="selected?.status === 'pending' && showCancelReason" class="cancel-box"><label>放弃原因<textarea v-model="cancelReason" maxlength="500" rows="3" required placeholder="说明为什么放弃此草稿"></textarea></label><div class="dialog-actions"><button type="button" class="secondary" @click="showCancelReason = false">继续核对</button><button type="button" class="danger" :disabled="cancelling || !cancelReason.trim()" @click="cancelDraft">{{ cancelling ? '保存中…' : '确认放弃草稿' }}</button></div></div><p v-if="error" class="error" role="alert">{{ error }}</p><footer class="dialog-actions"><button type="button" class="secondary" @click="closeForm">关闭</button><button v-if="selected?.status === 'pending' && !showCancelReason" type="button" class="secondary" @click="showCancelReason = true">放弃草稿</button><button v-if="selected?.status === 'pending'" type="button" class="primary" :disabled="confirming || showCancelReason || !reviewConfirmed" @click="confirmEvent">{{ confirming ? '确认中…' : '确认银行凭证' }}</button></footer></div>
    </form></div>
  </section>
</template>

<style scoped>
.cash-events-page{display:grid;gap:16px;min-width:0}.cash-page-head{display:flex;justify-content:space-between;align-items:flex-start;gap:20px}.cash-page-head h2{margin:0;color:#173d30;font-size:var(--text-page)}.eyebrow{margin:0 0 5px;color:#4b7564;font-size:var(--text-caption);font-weight:700;letter-spacing:.04em}.page-lede{margin:6px 0 0;color:#718078;line-height:1.6}.head-actions{display:flex;gap:9px;align-items:center;flex-wrap:wrap}.cash-events-page button,.secondary-link{border:1px solid #d6e1da;border-radius:8px;background:#fff;color:#31594b;padding:9px 13px;cursor:pointer;font:inherit;text-decoration:none;white-space:nowrap}.cash-events-page button:hover,.secondary-link:hover{border-color:#8db7a7;background:#f4faf6}.cash-events-page button:disabled{opacity:.5;cursor:not-allowed}.cash-events-page button.primary{background:#0d4b40;color:#fff;border-color:#0d4b40}.cash-events-page button.danger{background:#a33c2f;color:#fff;border-color:#a33c2f}.definition-note{margin:0;padding:12px 14px;border-left:3px solid #8db7a7;border-radius:0 8px 8px 0;background:#f2f7f4;color:#52675d;line-height:1.7}.notice{margin:0;padding:11px 14px;border:1px solid #b8d8ca;border-radius:9px;background:#eff8f3;color:#1d4d40}.error{margin:0;color:#a33c2f;background:#fff7f5;border:1px solid #edcbc5;border-radius:8px;padding:10px 12px;line-height:1.6}.cash-filters{display:flex;align-items:end;gap:10px;flex-wrap:wrap;padding:14px 16px;border:1px solid #e2e8e4;border-radius:12px;background:#fff}.cash-filters label{display:grid;gap:5px;color:#52655e;font-size:var(--text-caption)}.cash-filters select,.cash-filters input{height:39px;border:1px solid #d8e1dd;border-radius:8px;padding:0 10px;background:#fff;color:#253b33;font:inherit}.search-field{flex:1 1 260px}.cash-table{width:100%;display:block;overflow:auto;border-collapse:collapse;background:#fff;border:1px solid #e2e8e4;border-radius:12px}.cash-table th,.cash-table td{padding:12px;text-align:left;border-bottom:1px solid #edf1ee;white-space:nowrap}.cash-table th{color:#60736b;background:#f6faf8;font-size:var(--text-body)}.cash-table td small{display:block;color:#718078;margin-top:4px}.cash-row{cursor:pointer}.cash-row:hover{background:#f8fbf9}.row-action{padding:6px 9px!important;font-size:var(--text-caption)!important}.status{display:inline-flex;padding:4px 8px;border-radius:999px;background:#eef3f0;color:#426153;font-size:var(--text-caption);white-space:nowrap}.status.pending{background:#fff3d9;color:#856426}.status.confirmed{background:#e5f4eb;color:#216244}.status.cancelled{background:#f1eded;color:#7a5550}.mask{position:fixed;inset:0;z-index:60;background:#10261d66;display:grid;place-items:center;padding:16px}.cash-dialog{width:min(880px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;padding:24px;background:#fff;border-radius:14px;box-shadow:0 22px 60px #001a1340}.dialog-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:18px}.dialog-head h3{margin:0;color:#173d30;font-size:var(--text-dialog)}.dialog-head p{margin:5px 0 0;color:#718078;line-height:1.6}.close-button{padding:2px 8px!important;font-size:22px!important;line-height:1}.cash-dialog fieldset{margin:0 0 14px;padding:14px 16px;border:1px solid #e1e8e3;border-radius:10px;min-width:0}.cash-dialog legend{padding:0 7px;color:#27584b;font-weight:700}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px 14px}.cash-dialog label{display:grid;gap:5px;color:#40554b;font-size:var(--text-body)}.cash-dialog input,.cash-dialog select,.cash-dialog textarea{box-sizing:border-box;width:100%;padding:9px;border:1px solid #d8e1dd;border-radius:7px;background:#fff;color:#253b33;font:inherit}.cash-dialog textarea{resize:vertical}.cash-dialog label small,.field-hint{color:#718078;font-size:var(--text-caption);line-height:1.5}.wide{grid-column:1/-1}.source-toolbar{display:flex;gap:8px;margin-bottom:9px}.source-toolbar input{flex:1}.source-list{display:grid;gap:7px;max-height:210px;overflow:auto}.source-option{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:9px 10px;border:1px solid #e7eee8;border-radius:8px;background:#fbfdfb}.source-option strong,.source-option small{display:block}.source-option small{color:#718078;margin-top:3px}.source-option .blocked{color:#a33c2f}.source-option button{flex:none;padding:6px 9px}.allocation-table{margin-top:12px;overflow:auto}.allocation-table table,.source-detail{width:100%;border-collapse:collapse}.allocation-table th,.allocation-table td,.source-detail th,.source-detail td{padding:8px;text-align:left;border-bottom:1px solid #edf1ee;white-space:nowrap}.allocation-table input{width:140px}.text-button{border:0!important;background:none!important;padding:3px!important;color:#a33c2f!important}.allocation-total{margin:9px 0 0;color:#31594b;font-weight:700}.preview-box,.warning-box{margin:12px 0;padding:11px 13px;border-radius:8px;line-height:1.6}.preview-box{background:#eff8f3;border:1px solid #b8d8ca;color:#245c48}.warning-box{background:#fff7e6;border:1px solid #eed7a3;color:#795c25}.warning-box p{margin:5px 0 9px}.warning-box code{word-break:break-all}.dialog-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:16px}.review-banner{display:grid;grid-template-columns:auto 1fr;gap:6px 10px;align-items:center;padding:13px;background:#f4f8f5;border-radius:9px}.review-banner small{grid-column:2;color:#718078;word-break:break-all}.detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:14px 0}.detail-grid>div{padding:11px 12px;border:1px solid #e6ede7;border-radius:8px}.detail-grid span,.detail-grid dt{display:block;color:#718078;font-size:var(--text-caption)}.detail-grid strong,.detail-grid dd{display:block;margin-top:5px;color:#25463a;overflow-wrap:anywhere}.detail-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.detail-grid dt{margin-top:8px}.detail-grid dd{margin-left:0}.review-step .definition-note{margin-top:12px}.cancel-box{padding:12px;border:1px solid #eed7a3;border-radius:9px;background:#fffaf0}.cancel-box label{margin:0}.cash-detail-panel{position:fixed;z-index:55;right:24px;top:84px;width:min(560px,calc(100vw - 48px));max-height:calc(100vh - 108px);overflow:auto;padding:22px;background:#fff;border:1px solid #dce7df;border-radius:14px;box-shadow:0 22px 60px #001a1330}.cash-detail-panel header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.cash-detail-panel h3{margin:0;color:#173d30;font-size:var(--text-dialog);word-break:break-all}.cash-detail-panel .detail-status{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:14px 0}.cash-detail-panel .detail-grid{display:grid;grid-template-columns:130px minmax(0,1fr);gap:8px;margin:0}.cash-detail-panel section{margin-top:18px}.cash-detail-panel h4{margin:0 0 8px}.detail-note{padding:10px 12px;background:#f6f8f6;border-radius:8px;color:#62776a;line-height:1.6}.detail-actions{display:flex;justify-content:flex-end;margin-top:16px}@media(max-width:850px){.cash-page-head{flex-direction:column}.head-actions{width:100%}.head-actions>*{flex:1;text-align:center}.cash-dialog{padding:18px}.form-grid,.detail-grid{grid-template-columns:1fr}}@media(max-width:560px){.cash-filters{display:grid;grid-template-columns:1fr 1fr}.cash-filters .search-field{grid-column:1/-1}.cash-filters button{width:100%}.cash-dialog{width:calc(100vw - 20px);max-height:calc(100vh - 20px);padding:14px}.cash-detail-panel{right:10px;top:70px;width:calc(100vw - 20px);max-height:calc(100vh - 80px)}.source-toolbar{flex-direction:column}.dialog-actions button{flex:1}.detail-grid{grid-template-columns:1fr 1fr}}
.verification-toggle,.review-confirm{display:flex!important;align-items:center;gap:7px!important;min-width:max-content}.verification-toggle input,.review-confirm input{width:auto!important}.review-sources{margin-top:14px}
</style>
