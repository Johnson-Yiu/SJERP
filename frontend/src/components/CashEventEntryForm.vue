<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useWorkspaceNavigation } from '../composables/useWorkspaceNavigation'
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import { useAccessControl } from '../accessControl'
import { apiErrorMessage } from '../utils/apiErrors.js'
import { optionalSettlementId } from '../utils/cashEventPayload.js'

const props = defineProps({
  mode: { type: String, default: 'standalone' },
  initialEvent: { type: Object, default: null },
  receipt: { type: Object, default: null },
  order: { type: Object, default: null },
})
const emit = defineEmits(['close', 'created', 'updated', 'state-change'])
const { workspace, storageKey } = useWorkspaceNavigation()
const { api } = useWorkspaceApi()
const { can } = useAccessControl()
const linked = computed(() => props.mode === 'linked')
const today = new Date().toLocaleDateString('en-CA')
const currencies = [
  { value: 'CNY', label: 'CNY · 人民币' }, { value: 'USD', label: 'USD · 美元' },
  { value: 'EUR', label: 'EUR · 欧元' }, { value: 'GBP', label: 'GBP · 英镑' },
  { value: 'HKD', label: 'HKD · 港币' }, { value: 'AUD', label: 'AUD · 澳元' },
  { value: 'JPY', label: 'JPY · 日元' },
]
const events = ref([]), accounts = ref([]), accountError = ref('')
const error = ref(''), notice = ref(''), saving = ref(false), confirming = ref(false), cancelling = ref(false)
const lookupLoading = ref(false), sourceLoading = ref(false), sourceError = ref(''), sourceSearch = ref('')
const selected = ref(props.initialEvent), formStep = ref(props.initialEvent ? 'review' : 'form')
const saveOutcome = ref(props.initialEvent ? 'saved' : 'not-submitted')
const preview = ref(null), previewFingerprint = ref(''), previewRequestId = ref(0)
const sourceRows = ref([]), allocations = ref([]), reviewConfirmed = ref(false)
const duplicateCandidates = ref(null), duplicateReason = ref(''), cancelReason = ref(''), showCancelReason = ref(false)
const voucherFile = ref(null), voucherUploading = ref(false)
const draftRestoredRequiresEvidence = ref(false)
const draftStorageKey = 'sunjack:r1-fin-p2-b:cash-event-draft:v1'
const identityStorageKey = storageKey('sunjack:cash-event:request-identity:v1')
const allocationAmountBaseline = new Map()
let sourceRequestId = 0
let sourceAbortController = null
const form = reactive({
  event_no: '', request_key: '', kind: 'fx_settlement', currency: 'USD', direction: 'income',
  bank_date: today, bank_net_amount: '', gross_rmb_amount: '', actual_rate: '', fee_mode: 'none', fee_amount: '0',
  source_account: '', rmb_account: '', bank_reference: '', bank_counterparty: '', bank_summary: '', bank_transaction_id: '',
  evidence_reference: '', evidence_sha256: '', evidence_note: '', quoted_rate: '', fee_for: '', private_voucher: null,
})

function makeKey(prefix) {
  const uuid = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `P2B-${prefix}-${uuid}`.replace(/[^A-Za-z0-9_-]/g, '-')
}
function snapshotForParent() {
  return { ...form, allocations: allocations.value, step: formStep.value, selected: selected.value?.id || null, voucherFile: voucherFile.value?.name || '', busy: saving.value || confirming.value || cancelling.value }
}
function resetForm() {
  form.private_voucher = null; voucherFile.value = null
  Object.assign(form, {
    event_no: makeKey('EVENT'), request_key: makeKey('REQUEST'), kind: 'fx_settlement', currency: 'USD', direction: 'income',
    bank_date: today, bank_net_amount: '', gross_rmb_amount: '', actual_rate: '', fee_mode: 'none', fee_amount: '0', source_account: '', rmb_account: '',
    bank_reference: '', bank_counterparty: '', bank_summary: '', bank_transaction_id: '', evidence_reference: '',
    evidence_sha256: '', evidence_note: '', quoted_rate: '', fee_for: '',
  })
  allocations.value = []; preview.value = null; previewFingerprint.value = ''
  reviewConfirmed.value = false; duplicateCandidates.value = null; duplicateReason.value = ''
  draftRestoredRequiresEvidence.value = false; allocationAmountBaseline.clear()
  formStep.value = 'form'; saveOutcome.value = 'not-submitted'; showCancelReason.value = false
  cancelReason.value = ''; error.value = ''; sourceError.value = ''; sourceSearch.value = ''; notice.value = ''
}
function clearDraftSnapshot() {
  try { window.localStorage.removeItem(draftStorageKey); if (workspace) window.sessionStorage.removeItem(identityStorageKey) } catch { /* 浏览器存储可能不可用。 */ }
}
function persistDraftSnapshot() {
  if (!workspace || linked.value || formStep.value !== 'form') return
  const attempted = ['submitting', 'unknown'].includes(saveOutcome.value)
  try { window.sessionStorage.setItem(identityStorageKey, JSON.stringify({ event_no: form.event_no, request_key: form.request_key, saved_at: Date.now(), attempted })) } catch { /* 浏览器存储可能不可用。 */ }
}
function clearLegacyDraftSnapshot() {
  try {
    if (!window.localStorage.getItem(draftStorageKey)) return
    window.localStorage.removeItem(draftStorageKey)
    notice.value = '旧版浏览器草稿已清理。已提交的操作请核对资金记录。'
  } catch { /* 浏览器存储可能不可用。 */ }
}
function restoreDraftSnapshot() {
  if (!workspace || linked.value) return false
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(identityStorageKey) || 'null')
    if (!saved?.request_key || !saved.event_no || Date.now() - saved.saved_at > 24 * 60 * 60 * 1000) {
      window.sessionStorage.removeItem(identityStorageKey)
      return false
    }
    form.request_key = saved.request_key; form.event_no = saved.event_no
    draftRestoredRequiresEvidence.value = true
    if (saved.attempted) saveOutcome.value = 'unknown'
    return true
  } catch { return false }
}
function money(value, currency = 'CNY') {
  if (value === null || value === undefined || value === '') return '待核对'
  const digits = currency === 'JPY' ? 0 : 2
  return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}
function statusLabel(value) { return ({ pending: '待确认', confirmed: '已确认', cancelled: '已放弃' })[value] || value || '—' }
function kindLabel(value) { return ({ fx_settlement: '外币结汇流入', cny_direct: '人民币直接收付', bank_fee: '独立银行扣费' })[value] || value || '—' }
function directionLabel(value) { return value === 'income' ? '流入' : value === 'expense' ? '流出' : '—' }
function sourceLabel(row) { return `${row.transaction_no || `流水 #${row.id}`} · ${row.currency} ${money(row.amount, row.currency)}` }
function allocationFor(id) { return allocations.value.find(item => item.id === id) }
function needsExplicitPrecision(value, currency) { const digits = currency === 'JPY' ? 0 : 2; return String(value).split('.')[1]?.length > digits }
function exactCashAmount(value, currency) {
  const digits = currency === 'JPY' ? 0 : 2
  const [whole, fraction = ''] = String(value ?? '').split('.')
  if (/[^0]/.test(fraction.slice(digits))) return ''
  return digits ? `${whole}.${fraction.slice(0, digits).padEnd(digits, '0')}` : whole
}
function sourceTotal() { return allocations.value.reduce((total, item) => total + (Number(item.amount) || 0), 0) }
function grossRmbAmount() { return form.kind === 'fx_settlement' ? Number(form.gross_rmb_amount) || 0 : Number(form.bank_net_amount) || 0 }
function bankNetAmount() {
  if (form.kind !== 'fx_settlement') return String(form.bank_net_amount ?? '').trim()
  const fee = form.fee_mode === 'included' ? Number(form.fee_amount) || 0 : 0
  return Math.max(0, grossRmbAmount() - fee).toFixed(2)
}
function actualRate() {
  const total = sourceTotal()
  return total > 0 ? (grossRmbAmount() / total).toFixed(6) : ''
}
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
  const receiptId = linked.value ? Number(props.receipt?.id) : null
  return {
    ...(receiptId ? { source_receipt_id: receiptId } : {}),
    ...(form.private_voucher ? { private_voucher: form.private_voucher } : {}),
    event_no: form.event_no.trim(), request_key: form.request_key.trim(), kind: form.kind, currency: form.currency,
    direction: form.direction, bank_date: form.bank_date, bank_net_amount: bankNetAmount(),
    ...(form.kind === 'fx_settlement' ? { gross_rmb_amount: String(form.gross_rmb_amount ?? '').trim(), actual_rate: actualRate() } : {}), fee_mode: form.fee_mode,
    fee_amount: form.fee_mode === 'included' ? String(form.fee_amount ?? '').trim() : '0', source_account: form.source_account.trim(), rmb_account: form.rmb_account.trim(),
    bank_reference: form.bank_reference.trim(), bank_counterparty: form.bank_counterparty.trim(), bank_summary: form.bank_summary.trim(), bank_transaction_id: form.bank_transaction_id.trim(),
    evidence_reference: form.evidence_reference.trim(), evidence_sha256: form.evidence_sha256.trim(), evidence_note: String(form.evidence_note || '').trim(),
    quoted_rate: form.quoted_rate === null || form.quoted_rate === undefined || form.quoted_rate === '' ? null : String(form.quoted_rate).trim(),
    fee_for: optionalSettlementId(form.fee_for), correction_of: null,
    sources: allocations.value.filter(item => item.amount !== '' && Number(item.amount) > 0).map(item => ({ transaction_id: item.id, amount: String(item.amount).trim(), verified: item.verified === true })),
  }
}
async function loadAccounts() {
  accountError.value = ''
  try { accounts.value = (await api.get('/rmb-cash-events/accounts/')).data.results || [] }
  catch (err) { accounts.value = []; accountError.value = apiErrorMessage(err) || '资金账户加载失败，请稍后重试。' }
}
async function loadEvents() {
  try { events.value = (await api.get('/rmb-cash-events/')).data.results || [] }
  catch (err) { error.value = apiErrorMessage(err) || '人民币资金记录加载失败，请重试。' }
}
async function loadSources() {
  const requestId = ++sourceRequestId
  sourceAbortController?.abort()
  sourceAbortController = typeof AbortController !== 'undefined' ? new AbortController() : null
  const currency = form.currency
  sourceLoading.value = true; sourceError.value = ''; sourceRows.value = []
  try {
    const params = { currency }
    if (linked.value && props.receipt?.id) params.family_root = props.receipt.id
    const response = await api.get('/rmb-cash-events/sources/', { params, signal: sourceAbortController?.signal })
    if (requestId !== sourceRequestId || form.currency !== currency) return
    sourceRows.value = response.data.results || []
    if (linked.value && props.receipt?.id) {
      allocations.value = sourceRows.value.filter(row => Number(row.remaining_candidate_amount) > 0 && !row.blocked_reason)
        .map(row => { const amount = exactCashAmount(row.remaining_candidate_amount, currency); return { id: row.id, amount, verified: Boolean(amount) } })
      allocationAmountBaseline.clear()
      allocations.value.forEach(item => allocationAmountBaseline.set(item.id, String(item.amount)))
    }
  } catch (err) {
    if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError' || requestId !== sourceRequestId) return
    sourceRows.value = []; sourceError.value = apiErrorMessage(err) || '来源流水加载失败，请重试。'
  } finally { if (requestId === sourceRequestId) sourceLoading.value = false }
}
function addSource(row) {
  if (linked.value || row.blocked_reason || row.remaining_candidate_amount === null || allocationFor(row.id)) return
  allocations.value.push({ id: row.id, amount: needsExplicitPrecision(row.remaining_candidate_amount, form.currency) ? '' : row.remaining_candidate_amount, verified: false })
}
function removeSource(id) { if (linked.value) return; allocations.value = allocations.value.filter(item => item.id !== id); allocationAmountBaseline.delete(id) }
function markAllocationEdited(item) { item.verified = false }
function onKindChange() {
  if (form.kind === 'fx_settlement') { form.currency = form.currency === 'CNY' ? 'USD' : form.currency; form.direction = 'income'; form.fee_for = '' }
  if (form.kind === 'cny_direct' || form.kind === 'bank_fee') { form.currency = 'CNY'; if (form.kind === 'bank_fee') form.direction = 'expense'; form.quoted_rate = '1'; form.fee_for = '' }
  allocations.value = []; void loadSources()
}
function onCurrencyChange() { allocations.value = []; syncAccountSelection(); void loadSources() }
function syncAccountSelection() {
  if (form.source_account && !sourceAccountOptions.value.some(item => item.code === form.source_account)) form.source_account = ''
  if (form.rmb_account && !rmbAccountOptions.value.some(item => item.code === form.rmb_account)) form.rmb_account = ''
}
function clientError() {
  if (!form.bank_date || !form.bank_reference) return '请填写银行实际日期和银行参考号。'
  if (draftRestoredRequiresEvidence.value && (!form.private_voucher || !form.evidence_note)) return '请重新上传实际银行凭证并填写核对说明。'
  if (!form.source_account || !form.rmb_account) return sourceAccountOptions.value.length && rmbAccountOptions.value.length ? '请选择资金账户。' : '暂无匹配的资金账户；请先在财务台账登记对应币种账户，并联系系统管理员完成账户配置。'
  if (form.kind === 'fx_settlement') {
    if (!form.gross_rmb_amount || grossRmbAmount() <= 0) return '请填写大于0的扣费前人民币兑换额。'
    if (form.fee_mode === 'included' && Number(form.fee_amount) > grossRmbAmount()) return '含扣手续费不能超过扣费前兑换额。'
    if (Number(bankNetAmount()) <= 0) return '银行净到账必须大于0。'
  } else if (!form.bank_net_amount || Number(form.bank_net_amount) <= 0) return '请填写大于0的银行净额。'
  if (linked.value && !props.receipt?.id) return '请先保存本笔收款，再继续登记结汇。'
  if (!allocations.value.length) return linked.value ? '本笔收款没有可用的结汇来源额度。' : '请至少选择一条来源流水。'
  if (allocations.value.some(item => !item.amount || Number(item.amount) <= 0)) return '每条来源都要填写大于0的分配金额。'
  if (allocations.value.some(item => item.verified !== true)) return '请逐条核实来源流水后再预览。'
  if (form.kind === 'fx_settlement' && form.currency === 'CNY') return '结汇来源必须是外币；人民币直接收付请选择对应类型。'
  if (form.kind === 'fx_settlement' && form.direction !== 'income') return '结汇只支持人民币资金流入。'
  if (form.fee_for !== '' && form.fee_for !== null && optionalSettlementId(form.fee_for) === null) return '请选择有效的结汇事件，或选择“不关联结汇”。'
  return ''
}
const sourceAccountOptions = computed(() => accounts.value.filter(item => item.currency === form.currency))
const rmbAccountOptions = computed(() => accounts.value.filter(item => item.currency === 'CNY'))
const confirmedSettlementEvents = computed(() => events.value.filter(event => event.status === 'confirmed' && event.kind === 'fx_settlement' && (!form.rmb_account || event.rmb_account === form.rmb_account)))
const formGuard = useUnsavedChangesGuard({
  data: () => ({ ...form, allocations: allocations.value, step: formStep.value }),
  enabled: () => !linked.value && formStep.value === 'form',
  busy: () => saving.value || confirming.value || cancelling.value,
  confirmOptions: () => saveOutcome.value === 'unknown' ? { title: '登记结果尚未确认', message: '系统没有收到明确的登记结果。请先核对资金记录，不要重复创建同一笔事件。', cancelText: '继续核对', confirmText: '确认放弃当前输入' } : {},
})
function openCreate() {
  resetForm(); selected.value = null
  formGuard.markClean()
  const restored = restoreDraftSnapshot()
  if (restored) notice.value = '已恢复未完成的资金登记。请重新核对内容并上传实际凭证。'
  void loadSources()
}
function closeForm() {
  if (linked.value) return
  return formGuard.requestClose(() => { clearDraftSnapshot(); emit('close') })
}
async function uploadPrivateVoucher() {
  const existing = formStep.value === 'review' ? selected.value : null
  const ids = existing ? existing.sources.map(s => s.transaction_id) : allocations.value.map(s => s.id)
  if (!voucherFile.value || !ids.length) { error.value = '请先选择来源流水，再选择实际凭证文件。'; return }
  voucherUploading.value = true; error.value = ''
  try {
    const body = new FormData(); body.append('file', voucherFile.value); body.append('sources', JSON.stringify(ids))
    const proof = (await api.post('/rmb-cash-events/voucher-upload/', body)).data
    if (existing) selected.value = (await api.post(`/rmb-cash-events/${existing.id}/bind-voucher/`, { private_voucher: proof.id })).data
    else { form.private_voucher = proof.id; form.evidence_sha256 = proof.sha256; if (!form.evidence_reference) form.evidence_reference = `PRIVATE-${proof.id}`; preview.value = null }
    notice.value = '实际凭证已保存，系统已完成文件校验。'
  } catch (err) { error.value = apiErrorMessage(err) }
  finally { voucherUploading.value = false }
}
async function previewEvent() {
  error.value = ''; notice.value = ''; saveOutcome.value = 'submitting'
  const localError = clientError(); if (localError) { error.value = localError; saveOutcome.value = 'not-submitted'; return }
  saving.value = true
  const requestId = ++previewRequestId.value
  const payload = eventPayload(), fingerprint = payloadFingerprint(payload)
  try {
    const response = await api.post('/rmb-cash-events/preview/', payload)
    if (requestId !== previewRequestId.value || payloadFingerprint(eventPayload()) !== fingerprint) {
      preview.value = null; previewFingerprint.value = ''; saveOutcome.value = 'not-submitted'; notice.value = '表单已修改，请重新预览。'; return
    }
    preview.value = response.data; previewFingerprint.value = fingerprint; notice.value = '结汇信息已核对，来源额度尚未占用。'; saveOutcome.value = 'previewed'
  } catch (err) { saveOutcome.value = 'failed'; error.value = apiErrorMessage(err) || '结汇信息核对失败，已保留全部输入。' }
  finally { saving.value = false }
}
async function registerDraft() {
  error.value = ''; notice.value = ''
  const localError = clientError(); if (localError) { error.value = localError; return }
  if (!preview.value || !previewFingerprint.value || payloadFingerprint(eventPayload()) !== previewFingerprint.value) { preview.value = null; previewFingerprint.value = ''; saveOutcome.value = 'not-submitted'; error.value = '预览已失效，请重新预览后再登记。'; return }
  saving.value = true; saveOutcome.value = 'submitting'; persistDraftSnapshot()
  try {
    const response = await api.post('/rmb-cash-events/', eventPayload())
    selected.value = response.data; formStep.value = 'review'; showCancelReason.value = false; preview.value = null; previewFingerprint.value = ''; reviewConfirmed.value = false
    clearDraftSnapshot(); saveOutcome.value = 'saved'; notice.value = '结汇信息已登记，等待核对银行凭证。'
    emit('created', response.data)
    await loadEvents()
  } catch (err) {
    const status = err?.status || err?.response?.status
    saveOutcome.value = status && status < 500 && status !== 408 ? 'failed' : 'unknown'
    error.value = apiErrorMessage(err) || (saveOutcome.value === 'unknown' ? '登记结果尚未确认。请先核对资金记录，再决定是否重试。' : '登记失败，输入仍已保留。')
  } finally { saving.value = false }
}
async function lookupRequest() {
  if (!form.request_key || lookupLoading.value) return
  lookupLoading.value = true; error.value = ''
  try { selected.value = (await api.get('/rmb-cash-events/by-request-key/', { params: { request_key: form.request_key } })).data; formStep.value = 'review'; reviewConfirmed.value = false; clearDraftSnapshot(); formGuard.markClean(); notice.value = '已找到原资金事件。'; emit('created', selected.value); await loadEvents() }
  catch (err) {
    const status = err?.status || err?.response?.status
    if (status === 404) saveOutcome.value = 'failed'
    error.value = status === 404 ? '未找到原资金事件。请核对后按原登记内容重试。' : (apiErrorMessage(err) || '暂时无法核对资金记录，请稍后重试。')
  }
  finally { lookupLoading.value = false }
}
async function confirmEvent() {
  if (!selected.value || confirming.value || !reviewConfirmed.value || !selected.value.private_voucher) return
  confirming.value = true; error.value = ''; notice.value = ''
  try {
    if (!duplicateCandidates.value) {
      duplicateCandidates.value = (await api.get(`/rmb-cash-events/${selected.value.id}/duplicate-candidates/`)).data
      if (duplicateCandidates.value.count) { error.value = '请核对疑似重复记录并填写放行说明，再次确认。'; return }
    }
    const body = { voucher_checked: true }
    if (duplicateCandidates.value.count) { body.duplicate_token = duplicateCandidates.value.token; body.duplicate_reason = duplicateReason.value.trim() }
    selected.value = (await api.post(`/rmb-cash-events/${selected.value.id}/confirm/`, body)).data
    notice.value = '资金事件已确认。'; reviewConfirmed.value = false; clearDraftSnapshot(); formGuard.markClean(); emit('updated', selected.value); await loadEvents()
  } catch (err) { duplicateCandidates.value = null; error.value = apiErrorMessage(err) || '确认失败；记录仍保留为待确认。' }
  finally { confirming.value = false }
}
async function cancelDraft() {
  if (!selected.value || cancelling.value || !cancelReason.value.trim()) return
  cancelling.value = true; error.value = ''; notice.value = ''
  try {
    selected.value = (await api.post(`/rmb-cash-events/${selected.value.id}/cancel/`, { reason: cancelReason.value.trim() })).data
    showCancelReason.value = false; notice.value = '待确认草稿已放弃，来源额度未计入已确认资金。'; reviewConfirmed.value = false
    clearDraftSnapshot(); formGuard.markClean(); emit('updated', selected.value); await loadEvents()
  } catch (err) { error.value = apiErrorMessage(err) || '草稿放弃失败，原记录仍保留。' }
  finally { cancelling.value = false }
}
function openReview(row) { selected.value = row; reviewConfirmed.value = false; showCancelReason.value = false; duplicateCandidates.value = null; error.value = ''; notice.value = '' }
function beginCancel() { showCancelReason.value = true; cancelReason.value = '' }
watch(() => props.initialEvent, value => { if (value) { openReview(value); formStep.value = 'review'; saveOutcome.value = 'saved' } else if (!linked.value) openCreate() }, { immediate: true })
watch(() => props.order?.currency, value => {
  if (linked.value && !props.receipt?.id && value) form.currency = value
}, { immediate: true })
watch(() => props.receipt, receipt => {
  if (!linked.value) return
  if (receipt?.id) { if (receipt.currency) form.currency = receipt.currency; void loadSources(); if (!events.value.length) void loadEvents() }
  else { sourceRows.value = []; allocations.value = []; sourceLoading.value = false }
}, { immediate: true, deep: false })
watch([form, allocations], () => {
  if (formStep.value === 'form') {
    const presentIds = new Set()
    allocations.value.forEach(item => {
      presentIds.add(item.id)
      const amount = String(item.amount ?? ''), previous = allocationAmountBaseline.get(item.id)
      if (previous !== undefined && previous !== amount) item.verified = false
      allocationAmountBaseline.set(item.id, amount)
    })
    for (const id of allocationAmountBaseline.keys()) if (!presentIds.has(id)) allocationAmountBaseline.delete(id)
    persistDraftSnapshot()
    if (preview.value || previewFingerprint.value) { previewRequestId.value += 1; preview.value = null; previewFingerprint.value = ''; saveOutcome.value = 'not-submitted'; notice.value = '表单已修改，请重新预览。' }
  }
  emit('state-change', snapshotForParent())
}, { deep: true })
watch(() => form.kind, value => { if (value === 'fx_settlement' && form.currency === 'CNY') form.currency = 'USD' })
watch(() => form.currency, syncAccountSelection)
onMounted(() => { if (!props.initialEvent) { if (!linked.value) { clearLegacyDraftSnapshot(); if (formStep.value !== 'form') openCreate() }; void loadAccounts(); void loadEvents(); if (!linked.value) void loadSources() } })
</script>

<template>
  <div v-if="!linked" class="cash-entry-mask" @keydown.esc="closeForm">
    <section class="cash-entry-dialog" role="dialog" aria-modal="true" :aria-labelledby="formStep === 'form' ? 'cash-entry-title' : 'cash-review-title'">
      <header class="dialog-head"><div><p class="eyebrow">人民币资金</p><h3 :id="formStep === 'form' ? 'cash-entry-title' : 'cash-review-title'">{{ formStep === 'form' ? '新增资金事件' : '资金事件详情' }}</h3><p v-if="formStep === 'form'">核对银行实际到账信息后预览并登记。</p></div><button type="button" class="close-button" aria-label="关闭资金表单" :disabled="saving || confirming || cancelling" @click="closeForm">×</button></header>
      <div v-if="saveOutcome === 'unknown'" class="warning-box" role="alert"><strong>登记结果尚未确认</strong><p>请先核对原资金记录，再决定是否重试。</p><button type="button" class="secondary" :disabled="lookupLoading" @click="lookupRequest">{{ lookupLoading ? '核对中…' : '核对登记结果' }}</button></div>
      <template v-if="formStep === 'form'">
        <fieldset :disabled="saving"><legend>银行到账信息</legend><div class="form-grid">
          <label>事件类型<select v-model="form.kind" @change="onKindChange"><option value="fx_settlement">外币结汇流入</option><option value="cny_direct">人民币直接收付</option><option value="bank_fee">独立银行扣费</option></select></label>
          <label>来源币种<select v-model="form.currency" @change="onCurrencyChange"><option v-for="item in currencies" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
          <label v-if="form.kind !== 'fx_settlement'">资金方向<select v-model="form.direction"><option value="income">流入</option><option value="expense">流出</option></select></label>
          <label>实际到账日期<input v-model="form.bank_date" type="date" required></label>
           <label v-if="form.kind === 'fx_settlement'">扣费前兑换额（CNY）<input v-model="form.gross_rmb_amount" type="number" min="0.01" step="0.01" required></label>
           <label v-else>银行净额（CNY）<input v-model="form.bank_net_amount" type="number" min="0.01" step="0.01" required></label>
          <label>手续费<select v-model="form.fee_mode"><option value="none">无</option><option value="included">银行净额已含扣</option></select></label>
          <label v-if="form.fee_mode === 'included'">手续费（CNY）<input v-model="form.fee_amount" type="number" min="0.01" step="0.01" required></label>
           <label v-if="form.kind === 'fx_settlement'">银行净到账（CNY）<input :value="bankNetAmount()" type="number" readonly></label>
           <label v-if="form.kind === 'fx_settlement'">实际汇率<input :value="actualRate()" readonly></label>
          <label>来源账户<select v-model="form.source_account" required><option value="">请选择账户</option><option v-for="item in sourceAccountOptions" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
          <label>人民币账户<select v-model="form.rmb_account" required><option value="">请选择账户</option><option v-for="item in rmbAccountOptions" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
          <label>银行参考号<input v-model="form.bank_reference" maxlength="120" required></label>
          <label v-if="form.kind === 'bank_fee'">关联结汇事件（可选）<select v-model="form.fee_for"><option value="">不关联结汇</option><option v-for="event in confirmedSettlementEvents" :key="event.id" :value="event.id">{{ event.event_no }} · {{ event.bank_reference }} · CNY {{ money(event.bank_net_amount) }}</option></select></label>
          <label v-if="form.kind === 'fx_settlement'">参考折算汇率（可选）<input v-model="form.quoted_rate" inputmode="decimal" placeholder="仅用于金额对照"></label>
        </div><p v-if="!sourceAccountOptions.length || !rmbAccountOptions.length || accountError" class="field-hint" role="status">{{ accountError || '暂无匹配的资金账户。请先在财务台账登记对应币种账户，并联系系统管理员完成账户配置。' }}</p></fieldset>
        <fieldset :disabled="saving"><legend>银行凭证与核对说明</legend><div class="form-grid">
          <label class="wide">银行凭证文件<input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="voucherFile = $event.target.files[0]"></label>
          <button type="button" class="secondary wide" :disabled="voucherUploading || saving || !voucherFile" @click="uploadPrivateVoucher">{{ voucherUploading ? '上传中…' : '上传并校验凭证' }}</button>
          <p v-if="form.private_voucher" class="wide field-hint">实际凭证已绑定，确认时系统会再次校验文件。</p>
          <label class="wide">核对说明<textarea v-model="form.evidence_note" maxlength="500" rows="2" placeholder="记录银行凭证核对结果"></textarea></label>
          <details class="wide"><summary>更多银行信息（可选）</summary><div class="form-grid"><label>交易对手<input v-model="form.bank_counterparty" maxlength="200"></label><label>银行交易标识<input v-model="form.bank_transaction_id" maxlength="120"></label><label class="wide">银行摘要<textarea v-model="form.bank_summary" maxlength="500" rows="2"></textarea></label></div></details>
        </div><p class="field-hint">未配置资金账户时，请先维护账户名称并完成系统账户配置，再确认资金事件。</p></fieldset>
        <fieldset :disabled="saving"><legend>{{ linked ? '本笔收款来源' : '结汇来源' }}</legend>
          <div v-if="linked" class="linked-receipt-summary"><p>关联订单：<strong>{{ props.receipt?.orders?.[0]?.order_no || props.receipt?.order_no || props.order?.order_no || '保存后读取' }}</strong></p><p>财务流水：<strong>{{ props.receipt?.transaction_no || '收款保存后读取' }}</strong></p><p class="field-hint">按已保存收款及其拆分流水取用结汇额度；未分配预收仍显示为单独来源，不计作订单计划核销。</p></div>
          <template v-else><div class="source-toolbar"><input v-model="sourceSearch" type="search" placeholder="搜索流水号"><button type="button" class="secondary" @click="loadSources">刷新来源</button></div><p v-if="sourceError" class="error" role="alert">{{ sourceError }} <button type="button" class="secondary" @click="loadSources">重试</button></p><p v-else-if="sourceLoading" class="field-hint" role="status">正在加载来源…</p><div v-else class="source-list"><div v-for="row in filteredSources()" :key="row.id" class="source-option"><div><strong>{{ sourceLabel(row) }}</strong><small>{{ row.kind === 'unallocated_advance' ? '未分配预收款' : row.order_no ? `订单 ${row.order_no}` : '财务流水' }} · 可用 {{ row.remaining_candidate_amount === null ? '待核对' : `${row.currency} ${money(row.remaining_candidate_amount, row.currency)}` }}</small><small v-if="row.blocked_reason" class="blocked">{{ row.blocked_reason }}</small></div><button type="button" :disabled="Boolean(row.blocked_reason) || row.remaining_candidate_amount === null || Boolean(allocationFor(row.id))" @click="addSource(row)">{{ allocationFor(row.id) ? '已选择' : row.remaining_candidate_amount === null ? '待核对' : '选择' }}</button></div><p v-if="!filteredSources().length" class="empty-note">没有可选择的来源流水。</p></div></template>
          <p v-if="sourceError && linked" class="error" role="alert">{{ sourceError }}</p><p v-else-if="sourceLoading && linked" class="field-hint" role="status">正在读取已保存收款流水…</p>
          <div v-if="allocations.length" class="allocation-table"><table><thead><tr><th>来源流水</th><th>可用金额</th><th>本次结汇</th><th>核实</th><th v-if="!linked"></th></tr></thead><tbody><tr v-for="item in allocations" :key="item.id"><td>{{ sourceRows.find(row => row.id === item.id)?.transaction_no || `流水 #${item.id}` }}<small v-if="sourceRows.find(row => row.id === item.id)?.kind === 'unallocated_advance'"> · 未分配预收款</small></td><td>{{ form.currency }} {{ money(sourceRows.find(row => row.id === item.id)?.remaining_candidate_amount, form.currency) }}</td><td><input v-model="item.amount" type="number" min="0.01" :max="sourceRows.find(row => row.id === item.id)?.remaining_candidate_amount" :step="form.currency === 'JPY' ? '1' : '0.01'" required @input="markAllocationEdited(item)"></td><td><label class="verification-toggle"><input v-model="item.verified" type="checkbox"><span>{{ item.verified ? '已核实' : '待核实' }}</span></label></td><td v-if="!linked"><button type="button" class="text-button" @click="removeSource(item.id)">移除</button></td></tr></tbody></table><p class="allocation-total">本次结汇来源合计 {{ form.currency }} {{ money(sourceTotal(), form.currency) }}</p></div>
        </fieldset>
        <p v-if="preview" class="preview-box" role="status"><strong>结汇信息已核对</strong>：来源合计 {{ form.currency }} {{ money(preview.source_total, form.currency) }}，银行净额 CNY {{ money(preview.bank_net_amount) }}。来源额度尚未占用。</p>
        <p v-if="notice" class="notice" role="status">{{ notice }}</p><p v-if="error" class="error" role="alert">{{ error }}</p>
        <footer class="dialog-actions"><button v-if="!linked" type="button" class="secondary" :disabled="saving" @click="closeForm">取消</button><button v-if="!preview" type="button" class="primary" :disabled="saving || (linked && !props.receipt?.id)" @click="previewEvent">{{ saving ? '核对中…' : '预览结汇信息' }}</button><button v-else type="button" class="primary" :disabled="saving" @click="registerDraft">{{ saving ? '登记中…' : '登记待确认结汇' }}</button></footer>
      </template>
      <section v-else class="review-step">
        <section class="private-bank-proof"><p v-if="selected?.private_voucher">银行凭证已保存并完成系统校验。<a :href="`/api/rmb-cash-events/${selected.id}/voucher-download/`">下载凭证</a></p><template v-else><p>这条历史记录缺少实际凭证，请补传原始文件后再确认。</p><label>补传银行凭证<input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="voucherFile = $event.target.files[0]"></label><button type="button" :disabled="voucherUploading || !voucherFile" @click="uploadPrivateVoucher">{{ voucherUploading ? '上传中…' : '补传并校验凭证' }}</button></template></section>
        <div class="review-banner"><span class="status" :class="selected?.status">{{ statusLabel(selected?.status) }}</span><strong>{{ selected?.event_no }}</strong></div>
        <div class="detail-grid"><div><span>实际到账日期</span><strong>{{ selected?.bank_date }}</strong></div><div><span>银行参考号</span><strong>{{ selected?.bank_reference }}</strong></div><div><span>类型 / 方向</span><strong>{{ kindLabel(selected?.kind) }} · {{ directionLabel(selected?.direction) }}</strong></div><div><span>来源金额</span><strong>{{ selected?.currency }} {{ money(selected?.amount, selected?.currency) }}</strong></div><div><span>银行净额</span><strong>CNY {{ money(selected?.bank_net_amount) }}</strong></div><div><span>手续费</span><strong>{{ selected?.fee_mode === 'included' ? '含扣 CNY ' + money(selected?.fee_amount) : '无' }}</strong></div><div><span>来源账户</span><strong>{{ selected?.source_account_name || '账户名称待配置' }}</strong></div><div><span>人民币账户</span><strong>{{ selected?.rmb_account_name || '账户名称待配置' }}</strong></div><div><span>关联订单</span><strong>{{ selected?.orders?.map(item => item.order_no).filter(Boolean).join('、') || '—' }}</strong></div><div><span>来源流水</span><strong>{{ selected?.sources?.map(source => source.snapshot?.transaction_no || `流水 #${source.transaction_id}`).join('、') }}</strong></div></div>
        <p v-if="selected?.evidence_note" class="definition-note">{{ selected.evidence_note }}</p>
        <section v-if="selected?.sources?.length" class="review-sources"><h4>来源分配</h4><table class="source-detail"><thead><tr><th>流水</th><th>本次结汇</th><th>核实</th></tr></thead><tbody><tr v-for="source in selected.sources" :key="source.transaction_id"><td>{{ source.snapshot?.transaction_no || `流水 #${source.transaction_id}` }}</td><td>{{ source.currency }} {{ money(source.amount, source.currency) }}</td><td>已通过登记校验</td></tr></tbody></table></section>
        <p v-if="selected?.status === 'pending'" class="field-hint">请核对实际到账日期、银行参考号、凭证、账户、净额、手续费和来源分配。账户未配置或凭证无效时，系统不会确认该事件。</p>
        <p v-if="selected?.status === 'pending' && !selected?.private_voucher" class="error" role="alert">请先补传并校验实际银行凭证。</p>
        <label v-if="selected?.status === 'pending'" class="review-confirm"><input v-model="reviewConfirmed" type="checkbox">我已核对银行凭证和来源分配，确认提交核实结果。</label>
        <div v-if="duplicateCandidates?.count" class="warning-box" role="alert"><strong>发现 {{ duplicateCandidates.count }} 条疑似重复银行记录</strong><p>请核对同一账户、日期、方向和银行净额相同的记录。</p><p v-if="duplicateCandidates.restricted">部分记录无权查看，请联系有权人员核对。</p><ul v-else><li v-for="item in duplicateCandidates.items" :key="item.id">{{ item.event_no }}；{{ item.bank_reference || '未提供银行参考号' }}</li></ul><label v-if="!duplicateCandidates.restricted">核实放行说明<textarea v-model="duplicateReason" maxlength="500" rows="3" placeholder="说明为何属于不同银行交易"></textarea></label></div>
        <div v-if="selected?.status === 'pending' && showCancelReason" class="cancel-box"><label>放弃原因<textarea v-model="cancelReason" maxlength="500" rows="3" required placeholder="说明放弃原因"></textarea></label><div class="dialog-actions"><button type="button" class="secondary" @click="showCancelReason = false">继续核对</button><button type="button" class="danger" :disabled="cancelling || !cancelReason.trim()" @click="cancelDraft">{{ cancelling ? '保存中…' : '确认放弃草稿' }}</button></div></div>
        <p v-if="notice" class="notice" role="status">{{ notice }}</p><p v-if="error" class="error" role="alert">{{ error }}</p>
        <footer class="dialog-actions"><button type="button" class="secondary" @click="closeForm">关闭</button><button v-if="selected?.status === 'pending' && !showCancelReason" type="button" class="secondary" @click="beginCancel">放弃草稿</button><button v-if="selected?.status === 'pending'" type="button" class="primary" :disabled="confirming || showCancelReason || !reviewConfirmed || !selected?.private_voucher || duplicateCandidates?.restricted" @click="confirmEvent">{{ confirming ? '确认中…' : '确认银行凭证' }}</button></footer>
      </section>
    </section>
  </div>
  <section v-else class="inline-cash-entry" aria-labelledby="linked-settlement-title">
    <header><div><p class="eyebrow">外币收款结汇</p><h4 id="linked-settlement-title">结汇信息</h4></div></header>
    <template v-if="formStep === 'form'">
      <fieldset :disabled="saving"><div class="form-grid">
        <label>实际到账日期<input v-model="form.bank_date" type="date" required></label>
        <label>来源币种<input :value="form.currency" readonly></label>
          <label>扣费前兑换额（CNY）<input v-model="form.gross_rmb_amount" type="number" min="0.01" step="0.01" required></label>
        <label>手续费<select v-model="form.fee_mode"><option value="none">无</option><option value="included">银行净额已含扣</option></select></label>
        <label v-if="form.fee_mode === 'included'">手续费（CNY）<input v-model="form.fee_amount" type="number" min="0.01" step="0.01" required></label>
          <label>银行净到账（CNY）<input :value="bankNetAmount()" type="number" readonly></label>
          <label>实际汇率<input :value="actualRate()" readonly></label>
        <label>来源账户<select v-model="form.source_account" required><option value="">请选择账户</option><option v-for="item in sourceAccountOptions" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
        <label>人民币账户<select v-model="form.rmb_account" required><option value="">请选择账户</option><option v-for="item in rmbAccountOptions" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
        <label>银行参考号<input v-model="form.bank_reference" maxlength="120" required></label>
        <label>参考折算汇率（可选）<input v-model="form.quoted_rate" inputmode="decimal" placeholder="仅用于金额对照"></label>
        <label class="wide">银行凭证文件<input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="voucherFile = $event.target.files[0]"></label>
        <button type="button" class="secondary wide" :disabled="voucherUploading || saving || !voucherFile || !allocations.length" @click="uploadPrivateVoucher">{{ voucherUploading ? '上传中…' : '上传并校验凭证' }}</button>
        <p v-if="form.private_voucher" class="wide field-hint">实际凭证已绑定，确认时系统会再次校验文件。</p>
        <label class="wide">核对说明<textarea v-model="form.evidence_note" maxlength="500" rows="2" placeholder="记录银行凭证核对结果"></textarea></label>
      </div><p v-if="!sourceAccountOptions.length || !rmbAccountOptions.length || accountError" class="field-hint" role="status">{{ accountError || '暂无匹配的资金账户。请先在财务台账登记对应币种账户，并联系系统管理员完成账户配置。' }}</p></fieldset>
      <div class="linked-receipt-summary"><p>关联订单：<strong>{{ props.receipt?.order_no || props.receipt?.orders?.[0]?.order_no || props.order?.order_no || '保存后读取' }}</strong></p><p>财务流水：<strong>{{ props.receipt?.transaction_no || '收款保存后读取' }}</strong></p><p class="field-hint">结汇来源只取本笔已保存收款及其拆分流水；未分配预收单独列示，不计作订单计划核销。</p></div>
      <p v-if="sourceError" class="error" role="alert">{{ sourceError }}</p><p v-else-if="sourceLoading" class="field-hint" role="status">正在读取已保存收款流水…</p>
      <div v-if="allocations.length" class="allocation-table"><table><thead><tr><th>来源流水</th><th>类型</th><th>可用金额</th><th>本次结汇</th><th>核实</th></tr></thead><tbody><tr v-for="item in allocations" :key="item.id"><td>{{ sourceRows.find(row => row.id === item.id)?.transaction_no }}</td><td>{{ sourceRows.find(row => row.id === item.id)?.kind === 'unallocated_advance' ? '未分配预收款' : '客户收款' }}</td><td>{{ form.currency }} {{ money(sourceRows.find(row => row.id === item.id)?.remaining_candidate_amount, form.currency) }}</td><td>{{ form.currency }} {{ money(item.amount, form.currency) }}</td><td>已核实</td></tr></tbody></table><p class="allocation-total">本次结汇来源合计 {{ form.currency }} {{ money(sourceTotal(), form.currency) }}</p></div>
      <p v-if="preview" class="preview-box" role="status"><strong>结汇信息已核对</strong>：来源合计 {{ form.currency }} {{ money(preview.source_total, form.currency) }}，银行净额 CNY {{ money(preview.bank_net_amount) }}。来源额度尚未占用。</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <footer class="dialog-actions"><button v-if="!preview" type="button" class="primary" :disabled="saving || !props.receipt?.id" @click="previewEvent">{{ saving ? '核对中…' : '预览结汇信息' }}</button><button v-else type="button" class="primary" :disabled="saving" @click="registerDraft">{{ saving ? '登记中…' : '登记待确认结汇' }}</button></footer>
    </template>
    <section v-else class="inline-review"><p class="review-banner"><span class="status" :class="selected?.status">{{ statusLabel(selected?.status) }}</span> <strong>{{ selected?.event_no }}</strong></p><div class="detail-grid"><div><span>关联订单</span><strong>{{ selected?.orders?.map(item => item.order_no).filter(Boolean).join('、') || '—' }}</strong></div><div><span>收款流水</span><strong>{{ selected?.source_receipt?.transaction_no || '—' }}</strong></div><div><span>实际到账日期</span><strong>{{ selected?.bank_date }}</strong></div><div><span>银行参考号</span><strong>{{ selected?.bank_reference }}</strong></div><div><span>银行净额</span><strong>CNY {{ money(selected?.bank_net_amount) }}</strong></div><div><span>手续费</span><strong>{{ selected?.fee_mode === 'included' ? '含扣 CNY ' + money(selected?.fee_amount) : '无' }}</strong></div><div><span>来源账户</span><strong>{{ selected?.source_account_name || '账户名称待配置' }}</strong></div><div><span>人民币账户</span><strong>{{ selected?.rmb_account_name || '账户名称待配置' }}</strong></div></div><p>来源流水：{{ selected?.sources?.map(source => source.snapshot?.transaction_no).filter(Boolean).join('、') || '—' }}</p><div v-if="!selected?.private_voucher" class="private-bank-proof"><p>这条结汇记录缺少实际凭证，请补传原始文件后再确认。</p><label>补传银行凭证<input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="voucherFile = $event.target.files[0]"></label><button type="button" :disabled="voucherUploading || !voucherFile" @click="uploadPrivateVoucher">{{ voucherUploading ? '上传中…' : '补传并校验凭证' }}</button></div><p v-if="selected?.private_voucher">银行凭证已保存并完成系统校验。</p><p v-if="selected?.evidence_note" class="definition-note">{{ selected.evidence_note }}</p><label v-if="selected?.status === 'pending'" class="review-confirm"><input v-model="reviewConfirmed" type="checkbox">我已核对银行凭证和来源分配，确认提交核实结果。</label><p v-if="duplicateCandidates?.count" class="warning-box">发现 {{ duplicateCandidates.count }} 条疑似重复记录，请核对并填写放行说明。</p><label v-if="duplicateCandidates?.count && !duplicateCandidates.restricted">核实放行说明<textarea v-model="duplicateReason" maxlength="500" rows="2"></textarea></label><p v-if="error" class="error" role="alert">{{ error }}</p><footer class="dialog-actions"><button v-if="selected?.status === 'pending'" type="button" class="primary" :disabled="confirming || !reviewConfirmed || !selected?.private_voucher || duplicateCandidates?.restricted" @click="confirmEvent">{{ confirming ? '确认中…' : '确认银行凭证' }}</button></footer></section>
  </section>
</template>

<style scoped>
.cash-entry-mask{position:fixed;inset:0;z-index:120;display:grid;place-items:center;padding:16px;background:#10261d77}.cash-entry-dialog{width:min(880px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;padding:24px;background:#fff;border-radius:14px;box-shadow:0 22px 60px #001a1340}.inline-cash-entry{margin-top:18px;padding:18px;border:1px solid #b9d9cc;border-radius:12px;background:#f8fcf9}.inline-cash-entry>header,.dialog-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:14px}.dialog-head h3,.inline-cash-entry h4{margin:0;color:#173d30;font-size:var(--text-dialog)}.dialog-head p{margin:5px 0 0;color:#718078;line-height:1.5}.inline-cash-entry h4{font-size:var(--text-section)}.eyebrow{margin:0 0 4px;color:#618075;font-size:var(--text-caption);text-transform:uppercase;letter-spacing:.04em}.close-button{padding:2px 8px;border:0;background:transparent;font-size:22px;line-height:1;cursor:pointer}.cash-entry-dialog fieldset,.inline-cash-entry fieldset{min-width:0;margin:0 0 14px;padding:12px 14px;border:1px solid #e2e9e3;border-radius:10px}.cash-entry-dialog legend,.inline-cash-entry legend{padding:0 6px;color:#27584b;font-weight:700}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px 14px}.cash-entry-dialog label,.inline-cash-entry label{display:grid;gap:5px;color:#40554b;font-size:var(--text-body)}.cash-entry-dialog input,.cash-entry-dialog select,.cash-entry-dialog textarea,.inline-cash-entry input,.inline-cash-entry select,.inline-cash-entry textarea{box-sizing:border-box;width:100%;padding:9px;border:1px solid #d8e1dd;border-radius:7px;background:#fff;color:#253b33;font:inherit}.cash-entry-dialog textarea,.inline-cash-entry textarea{resize:vertical}.wide{grid-column:1/-1}.field-hint{margin:8px 0;color:#718078;font-size:var(--text-caption);line-height:1.55}.source-toolbar{display:flex;gap:8px;margin-bottom:9px}.source-toolbar input{flex:1}.source-list{display:grid;gap:7px;max-height:180px;overflow:auto}.source-option{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:9px 10px;border:1px solid #e7eee8;border-radius:8px;background:#fff}.source-option strong,.source-option small{display:block}.source-option small{margin-top:3px;color:#718078}.source-option .blocked{color:#a33c2f}.source-option button{flex:none}.allocation-table{margin-top:12px;overflow:auto}.allocation-table table,.source-detail{width:100%;border-collapse:collapse}.allocation-table th,.allocation-table td,.source-detail th,.source-detail td{padding:8px;text-align:left;border-bottom:1px solid #edf1ee;white-space:nowrap}.allocation-table td small{display:block;color:#718078}.allocation-table input{width:120px}.allocation-total{margin:9px 0 0;color:#31594b;font-weight:700}.linked-receipt-summary{margin:8px 0 12px;padding:10px 12px;border-radius:8px;background:#eef6f1}.linked-receipt-summary p{margin:4px 0}.linked-receipt-summary strong{overflow-wrap:anywhere}.verification-toggle,.review-confirm{display:flex!important;grid-template-columns:auto 1fr!important;align-items:center;gap:7px!important}.verification-toggle input,.review-confirm input{width:auto!important}.dialog-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-top:16px}.dialog-actions button,.cash-entry-dialog button,.inline-cash-entry button{padding:8px 13px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#344d44;cursor:pointer}.dialog-actions .primary,.cash-entry-dialog .primary,.inline-cash-entry .primary{background:#0d4b40;color:#fff;border-color:#0d4b40}.dialog-actions button:disabled,.cash-entry-dialog button:disabled,.inline-cash-entry button:disabled{opacity:.55;cursor:not-allowed}.preview-box,.warning-box,.notice{margin:12px 0;padding:11px 13px;border:1px solid #b8d8ca;border-radius:8px;background:#eff8f3;color:#245c48;line-height:1.6}.warning-box{border-color:#eed7a3;background:#fff7e6;color:#795c25}.warning-box p{margin:5px 0 9px}.notice{color:#1d4d40}.error{color:#b42318}.private-bank-proof{margin-bottom:14px;padding:12px;border:1px solid #eed7a3;border-radius:9px;background:#fffaf0}.private-bank-proof p{margin:0 0 8px}.private-bank-proof label{margin:8px 0}.review-banner{display:flex;align-items:center;gap:10px;padding:12px;background:#f4f8f5;border-radius:9px}.status{display:inline-block;padding:3px 8px;border-radius:999px;background:#edf3ef}.status.confirmed{background:#e8f5eb;color:#1f6b41}.status.pending{background:#fff5df;color:#805b14}.detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:14px 0}.detail-grid>div{padding:10px 12px;border:1px solid #e6ede7;border-radius:8px}.detail-grid span{display:block;color:#718078;font-size:var(--text-caption)}.detail-grid strong{display:block;margin-top:5px;color:#25463a;overflow-wrap:anywhere}.review-sources{margin-top:16px}.review-sources h4{margin:0 0 8px}.definition-note{padding:10px 12px;background:#f6f8f6;border-radius:8px}.empty-note{padding:10px 12px;border-radius:8px;background:#f6f8f6}.text-button{border:0!important;background:transparent!important;color:#a33c2f!important}.cancel-box{padding:12px;border:1px solid #eed7a3;border-radius:9px;background:#fffaf0}.inline-review{padding-top:4px}.inline-review .review-banner{display:block}.inline-review .review-banner strong{margin-left:8px}
@media(max-width:700px){.cash-entry-dialog{padding:16px}.inline-cash-entry{padding:13px}.form-grid,.detail-grid{grid-template-columns:1fr}.source-toolbar{flex-direction:column}.dialog-actions button{flex:1}.cash-entry-dialog{width:calc(100vw - 20px);max-height:calc(100vh - 20px)}}
</style>
