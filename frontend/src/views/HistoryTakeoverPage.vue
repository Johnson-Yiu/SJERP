<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { computed, onMounted, ref, watch } from 'vue'
import { AlertTriangle, Check, CircleHelp, FileUp, History, RotateCcw, ShieldCheck } from 'lucide-vue-next'

import { accessState, useAccessControl } from '../accessControl'

const { can } = useAccessControl()
const canApply = computed(() => can('imports', 'import'))
const canReview = computed(() => Boolean(accessState.operator?.can_manage_permissions || accessState.operator?.development_superadmin || accessState.operator?.has_all_permissions))
const applications = ref([])
const selected = ref(null)
const fileInput = ref(null)
const file = ref(null)
const loading = ref(false)
const saving = ref(false)
const templateLoading = ref(false)
const error = ref('')
const note = ref('')
const confirmManual = ref(false)
const mapping = ref({ sheet: '销售订单', row: '', field: 'customer_code', target_code: '', note: '' })
const mappingKind = ref('customer')
const masterSearch = ref('')
const masterOptions = ref([])
const masterLoading = ref(false)
let masterSearchVersion = 0
const newCorrection = () => ({
  kind: 'late_fact', occurred_at: '', reason: '', source_record_id: '',
  source_document_no: '', voucher_reference: '', description: '',
})
const correction = ref(newCorrection())
const correctionErrors = ref({})
const correctionReviewNotes = ref({})
const correctionEventTypes = ['late_fact_submitted', 'correction_submitted', 'voucher_added_submitted']
const correctionDetailLabels = {
  source_record_id: '原系统记录号', source_document_no: '原系统业务单据号',
  voucher_reference: '凭证编号或存放位置', description: '业务明细',
}
const financeSources = ref([])
const financeAccounts = ref([])
const financeVouchers = ref([])
const financeMapping = ref({ source_id: '', account: '', voucher: '', actual_date: '', amount: '', reason: '' })
const financePreview = ref(null)
const financeDuplicateChoice = ref('')
const financeDuplicateReason = ref('')
watch(financeMapping, () => { financePreview.value = null; financeDuplicateChoice.value = ''; financeDuplicateReason.value = '' }, { deep: true, flush: 'sync' })
const financeChangeReason = ref('')
const financeNoDebit = ref(false)
const inventoryStatus = ref(null)
const inventoryRows = ref([])
const inventoryReason = ref('')
const inventoryReviewNote = ref('')
const inventoryComplete = ref(false)
const operationalStatus = ref(null)
const operationalForms = ref({})
const operationalCutover = ref('')
const operationalReason = ref('')
const operationalReviewNote = ref('')
const operationalMoqReason = ref('')

const groups = computed(() => selected.value?.groups || [])
const statuses = {
  submitted: '待审核', in_review: '审核中', rejected: '已拒绝', partially_approved: '部分通过',
  approved: '已批准', executed: '已归档', withdrawn: '已撤回', pending: '待审核', blocked: '存在阻断',
  needs_reapproval: '需重新审核',
}
const coverageLabels = { complete: '完整', partial: '部分', unknown: '待核实' }
const truthLabels = { '真实': '真实资料', real: '真实资料', synthetic: '合成资料', '模拟': '合成资料', unknown: '待核实', '待核实': '待核实' }
const lifecycleLabels = { open: '未结', partial: '部分完成', partially_settled: '部分结清', settled: '已结清', completed: '已完成', cancelled: '已取消', unknown: '待核实' }
const directionLabels = { income: '收入', expense: '支出' }
const mappingFields = { customer: 'customer_code', supplier: 'supplier_code', sku: 'sku_code' }
const masterResources = { customer: '/customers/', supplier: '/suppliers/', sku: '/skus/' }
const handoffLabels = { not_connected: '尚未接续', pending_review: '待复核', approved: '已复核，待启用', posted: '已启用', reversed: '已撤销', sources_posted: '来源资金已记账', drafts_created: '未结余额已启用，接续草稿已生成', no_remaining: '无剩余履约', unmapped: '待映射', pending: '待复核', cancelled: '已取消', failed: '已核实失败', draft: '草稿', confirmed: '已确认', ordered: '已下单', partial: '部分到货', shipped: '已发货', completed: '已完成', production: '生产中' }
const overallLabels = { not_archived: '未归档', archived: '已归档，待准备接续', pending_review: '接续资料待复核', ready: '可接续或待确认接续单', connected: '适用项目已接续' }
function statusLabel(value) { return statuses[value] || '待核实' }
function handoffLabel(value) { return handoffLabels[value] || '待核实' }
function coverageLabel(value) { return coverageLabels[value] || '待核实' }
function truthLabel(value) { return truthLabels[value] || '待核实' }
function lifecycleLabel(value) { return lifecycleLabels[value] || '待核实' }
function directionLabel(value) { return directionLabels[value] || '待核实' }
function reviewStatusLabel(value) { return ({ '通过': '通过', '警告': '警告', '待人工核实': '待人工核实', '阻断': '阻断' })[value] || '待核实' }
function eventLabel(value) { return eventNames[value] || '待核实操作' }
function auditActorLabel(event) { return event.actor_kind === 'development' ? '开发操作（非实名）' : event.actor_label || '待核实操作人' }
function formatSubmittedAt(value) { return value ? new Date(value).toLocaleString('zh-CN') : '未记录' }
function masterLabel(item) {
  const code = item.code || item.sku || ''
  const name = item.name || item.display_name_cn || item.product_name || ''
  return [name || '未命名对象', code].filter(Boolean).join(' · ')
}
function skuBusinessLabel(source) {
  const name = source?.sku_name_snapshot || source?.display_name_snapshot || ''
  const code = source?.sku_code || ''
  return [name, code].filter(Boolean).join(' · ') || '待核实'
}
const eventNames = {
  application_submitted: '已提交申请', group_submitted: '关联组已提交', group_approved: '管理员已批准',
  group_rejected: '管理员已拒绝', group_executed: '已承接历史记录', group_withdrawn: '申请已撤回',
  master_resolution_added: '已登记主档关联', execution_stopped_reapproval_required: '执行前发现资料变化',
  late_fact_submitted: '已提交迟到记录', correction_submitted: '已提交追溯更正', voucher_added_submitted: '已补交凭证',
  correction_reviewed: '更正审核完成', duplicate_submission_reused: '重复提交已复用原申请',
  finance_instruction_submitted: '已保存历史资金指令', finance_instruction_approve: '已复核历史资金指令',
  finance_instruction_post: '已记入历史资金事实', finance_instruction_cancel: '已取消历史资金指令',
  finance_instruction_fail: '已核实资金指令失败', inventory_baseline_proposed: '已申请库存盘点基准',
  inventory_baseline_approved: '已复核库存盘点基准', inventory_baseline_posted: '已启用库存盘点基准',
  inventory_baseline_reversed: '已撤销库存盘点基准',
  operational_contract_proposed: '已申请未结业务接续', operational_contract_approved: '已复核未结业务接续',
  operational_contracts_created: '已建立未结计划与接续草稿', operational_contracts_reversed: '已撤销未使用的接续草稿',
}
const sourceRows = computed(() => selected.value?.groups?.find(group => group.id === selectedGroupId.value)?.source_rows || {})
const selectedGroupId = ref(null)
const selectedGroup = computed(() => groups.value.find(group => group.id === selectedGroupId.value) || groups.value[0] || null)
watch(selectedGroupId, () => {
  correction.value = newCorrection(); correctionErrors.value = {}; correctionReviewNotes.value = {}
  financeSources.value = []; financeAccounts.value = []; financeVouchers.value = []
  financeMapping.value = { source_id: '', account: '', voucher: '', actual_date: '', amount: '', reason: '' }
  financeChangeReason.value = ''; financeNoDebit.value = false
  inventoryStatus.value = null; inventoryRows.value = []; inventoryComplete.value = false
  operationalStatus.value = null; operationalForms.value = {}; operationalCutover.value = ''; operationalReason.value = ''; operationalReviewNote.value = ''
})
const reviewResults = computed(() => selectedGroup.value?.preflight_result?.results || [])
const sourceItems = computed(() => Object.entries(selectedGroup.value?.source_rows || {}).flatMap(([sheet, rows]) => rows.map(item => ({ sheet, ...item }))))
const openOrders = computed(() => {
  const summary = selectedGroup.value?.remainder_snapshot
  return [...(summary?.sales_orders || []), ...(summary?.purchase_orders || [])]
})

onMounted(loadApplications)

async function loadApplications(preferredId = selected.value?.id) {
  loading.value = true; error.value = ''
  try {
    const response = await api.get('/import/history-takeovers/')
    applications.value = response.data.results || []
    const id = preferredId || applications.value[0]?.id
    if (id) await loadApplication(id)
    else selected.value = null
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

async function loadApplication(id) {
  try {
    const response = await api.get(`/import/history-takeovers/${id}/`)
    selected.value = response.data
    selectedGroupId.value = response.data.groups?.[0]?.id || null
    if (applications.value.length) {
      const index = applications.value.findIndex(item => item.id === id)
      if (index >= 0) applications.value[index] = { ...applications.value[index], ...response.data }
    }
  } catch (e) { error.value = e.message }
}

function chooseFile(event) { file.value = event.target.files?.[0] || null; error.value = '' }

async function searchMasters() {
  const request = ++masterSearchVersion
  const kind = mappingKind.value
  const query = masterSearch.value.trim()
  masterOptions.value = []
  masterLoading.value = false
  if (!query || query.length < 1) return
  masterLoading.value = true
  try {
    const response = await api.get(masterResources[kind], { params: { search: query } })
    if (request !== masterSearchVersion || kind !== mappingKind.value) return
    const rows = response.data?.results || response.data || []
    masterOptions.value = rows.slice(0, 50).filter(item => kind === 'sku' ? item.sku : item.code)
  } catch (e) {
    if (request === masterSearchVersion) error.value = `读取现有${kind === 'customer' ? '客户' : kind === 'supplier' ? '供应商' : 'SKU'}失败：${e.message}`
  } finally {
    if (request === masterSearchVersion) masterLoading.value = false
  }
}

function changeMappingKind() {
  mapping.value.field = mappingFields[mappingKind.value]
  mapping.value.target_code = ''
  masterSearch.value = ''
  masterOptions.value = []
  masterLoading.value = false
  masterSearchVersion++
}

async function downloadTemplate() {
  if (templateLoading.value) return
  templateLoading.value = true; error.value = ''
  try {
    const response = await api.get('/import/history-takeovers/template/', { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'history-takeover-template-v2.xlsx'; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (e) { error.value = e.message }
  finally { templateLoading.value = false }
}

async function submitApplication() {
  if (!canApply.value || !file.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const data = new FormData(); data.append('file', file.value)
    const response = await api.post('/import/history-takeovers/', data)
    file.value = null
    if (fileInput.value) fileInput.value.value = ''
    await loadApplications(response.data.id)
  } catch (e) { error.value = e.message }
  finally { saving.value = false }
}

async function groupAction(group, action, payload = {}) {
  if (saving.value) return
  if (action === 'execute' && !window.confirm(`将仅承接“${group.source_group_id}”组的历史分析单据。资金、库存和履约不会写入正式流水。继续执行？`)) return
  saving.value = true; error.value = ''
  try {
    await api.post(`/import/history-takeovers/${selected.value.id}/groups/${group.id}/${action}/`, payload)
    await loadApplications(selected.value.id)
    return true
  } catch (e) { error.value = e.message }
  finally { saving.value = false }
}

async function loadFinance() {
  if (!selectedGroup.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const [status, ledger] = await Promise.all([
      api.post(`/import/history-takeovers/${selected.value.id}/groups/${selectedGroup.value.id}/finance-status/`, {}),
      api.get('/finance-ledger/'),
    ])
    financeSources.value = status.data.sources || []
    if (status.data.overall) selectedGroup.value.operational_overall = status.data.overall
    financeAccounts.value = (ledger.data.accounts || []).filter(item => item.ownership === 'own' && item.currency === 'CNY' && item.is_active)
    financeVouchers.value = ledger.data.vouchers || []
  } catch (e) { error.value = e.message }
  finally { saving.value = false }
}

async function financeAction(action, sourceId = financeMapping.value.source_id) {
  if (!selectedGroup.value || saving.value || !sourceId) return
  saving.value = true; error.value = ''
  try {
    const mapping = { account: financeMapping.value.account, voucher: financeMapping.value.voucher,
      actual_date: financeMapping.value.actual_date, amount: financeMapping.value.amount, reason: financeMapping.value.reason }
    const payload = { source_id: Number(sourceId) }
    if (action === 'finance-submit') {
      if (!financePreview.value || financePreview.value.restricted || (financePreview.value.items?.length && (!financeDuplicateChoice.value || !financeDuplicateReason.value.trim()))) return
      if (financePreview.value.items?.length) {
        mapping.duplicate_review_token = financePreview.value.token
        mapping.duplicate_review_reason = financeDuplicateReason.value.trim()
        if (financeDuplicateChoice.value !== 'distinct') mapping.same_legacy_event = Number(financeDuplicateChoice.value)
      }
      payload.mapping = mapping
      const selectedSource = financeSources.value.find(item => item.source_id === Number(sourceId))
      if (selectedSource && ['cancelled', 'failed'].includes(selectedSource.status)) {
        action = 'finance-replace'; payload.replaces = selectedSource.instruction_id
      }
    }
    if (action === 'finance-post') payload.voucher_checked = true
    if (['finance-cancel', 'finance-fail'].includes(action)) payload.reason = financeChangeReason.value
    if (action === 'finance-fail') payload.no_debit_confirmed = financeNoDebit.value
    if (action === 'finance-post' && !window.confirm('已核对实际资金凭证，确认记账？')) return
    await api.post(`/import/history-takeovers/${selected.value.id}/groups/${selectedGroup.value.id}/${action}/`, payload)
  } catch (e) { error.value = e.message; return }
  finally { saving.value = false }
  await loadFinance()
}

async function previewFinance() {
  if (!selectedGroup.value || saving.value) return
  const snapshot = JSON.stringify(financeMapping.value)
  const applicationId = selected.value.id; const groupId = selectedGroup.value.id
  const mapping = { account: financeMapping.value.account, voucher: financeMapping.value.voucher,
    actual_date: financeMapping.value.actual_date, amount: financeMapping.value.amount, reason: financeMapping.value.reason }
  saving.value = true; error.value = ''; financePreview.value = null
  try {
    const response = await api.post(`/import/history-takeovers/${applicationId}/groups/${groupId}/finance-preview/`,
      { source_id: Number(financeMapping.value.source_id), mapping })
    if (selected.value?.id === applicationId && selectedGroup.value?.id === groupId && snapshot === JSON.stringify(financeMapping.value)) financePreview.value = response.data
  } catch (e) { error.value = e.message }
  finally { saving.value = false }
}

async function loadInventory() {
  if (!selectedGroup.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const response = await api.post(`/import/history-takeovers/${selected.value.id}/groups/${selectedGroup.value.id}/inventory-status/`, {})
    inventoryStatus.value = response.data
    if (response.data.overall) selectedGroup.value.operational_overall = response.data.overall
    const previous = new Map((response.data.proposal?.rows || []).map(row => [row.source_id, row]))
    inventoryRows.value = (response.data.sources || []).map(item => ({ ...item, goods_ownership: previous.get(item.source_id)?.goods_ownership || '',
      unit_cost: previous.get(item.source_id)?.unit_cost || '', cost_currency: previous.get(item.source_id)?.cost_currency || '', no_lot: previous.get(item.source_id)?.no_lot || false }))
    inventoryReason.value = response.data.proposal?.reason || ''
  } catch (e) { error.value = e.message }
  finally { saving.value = false }
}

async function inventoryAction(action) {
  if (!selectedGroup.value || saving.value) return
  let payload = {}
  if (action === 'inventory-propose') payload = { rows: inventoryRows.value.map(row => ({ source_id: row.source_id, goods_ownership: row.goods_ownership,
    unit_cost: row.unit_cost, cost_currency: row.cost_currency, no_lot: row.no_lot })), reason: inventoryReason.value, complete_sku_inventory: inventoryComplete.value }
  if (action === 'inventory-approve') payload = { note: inventoryReviewNote.value }
  if (action === 'inventory-reverse') payload = { reason: inventoryReviewNote.value }
  if (action === 'inventory-execute' && !window.confirm('确认启用已复核盘点基准？系统会重新检查库存流水和预留。')) return
  saving.value = true; error.value = ''
  try { await api.post(`/import/history-takeovers/${selected.value.id}/groups/${selectedGroup.value.id}/${action}/`, payload) }
  catch (e) { error.value = e.message; return }
  finally { saving.value = false }
  await loadInventory()
}

async function loadOperational() {
  if (!selectedGroup.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const response = await api.post(`/import/history-takeovers/${selected.value.id}/groups/${selectedGroup.value.id}/operational-status/`, {})
    operationalStatus.value = response.data
    if (response.data.overall) selectedGroup.value.operational_overall = response.data.overall
    const proposal = response.data.proposal
    operationalCutover.value = proposal?.cutover_date || ''
    operationalReason.value = proposal?.reason || ''
    const previous = new Map((proposal?.contracts || []).map(item => [Number(item.source_id), item]))
    const forms = {}
    for (const doc of response.data.contracts || []) {
      forms[doc.source_id] = previous.has(doc.source_id) ? structuredClone(previous.get(doc.source_id)) : {
        source_id: doc.source_id, balance_mode: '', balance_amount: '', due_date: '', evidence_reference: '', plan_source_ids: [],
        remaining_shipping_fee: '', remaining_discount: '', amount_evidence: '', no_additional_costs: false, additional_costs_pending: false, costs_evidence: '',
        line_options: doc.remaining_lines.map(line => doc.record_type === '销售订单'
          ? { source_id: line.source_id, unit_cost: '', cost_currency: '', cost_evidence: '' }
          : { source_id: line.source_id, supplier_sku_id: '', manual_reason: '', target: '', sales_source_id: '' }),
      }
    }
    operationalForms.value = forms
  } catch (e) { error.value = e.message }
  finally { saving.value = false }
}

async function operationalAction(action) {
  if (!selectedGroup.value || saving.value) return
  let payload = {}
  if (action === 'operational-propose') payload = { cutover_date: operationalCutover.value, reason: operationalReason.value,
    contracts: (operationalStatus.value?.contracts || []).map(doc => {
      const form = JSON.parse(JSON.stringify(operationalForms.value[doc.source_id]))
      form.plan_source_ids = form.balance_mode === 'itemized' ? doc.plans.map(plan => plan.source_id) : []
      if (doc.record_type === '采购订单') form.line_options = form.line_options.map(line => ({ ...line,
        supplier_sku_id: line.supplier_sku_id || null, sales_source_id: line.target === 'order' ? line.sales_source_id : null }))
      return form
    }) }
  if (action === 'operational-approve') payload = { note: operationalReviewNote.value }
  if (action === 'operational-reverse') payload = { reason: operationalReviewNote.value }
  if (action === 'operational-execute' && !window.confirm('确认建立已复核的未结计划及剩余业务草稿？原始历史流水不会重复登记。')) return
  saving.value = true; error.value = ''
  try { await api.post(`/import/history-takeovers/${selected.value.id}/groups/${selectedGroup.value.id}/${action}/`, payload) }
  catch (e) { error.value = e.message; return }
  finally { saving.value = false }
  await loadOperational()
}

async function confirmContinuation(link) {
  if (!link.continuation_id || saving.value) return
  const sales = link.record_type === '销售订单'
  const path = sales ? `/orders/${link.continuation_id}/confirm/` : `/purchase-orders/${link.continuation_id}/place/`
  if (!window.confirm(`确认${sales ? '销售订单' : '采购下单'} ${link.continuation_no}？`)) return
  saving.value = true; error.value = ''
  try { await api.post(path, sales ? {} : { moq_exception_reason: operationalMoqReason.value }) }
  catch (e) { error.value = e.message; return }
  finally { saving.value = false }
  await loadOperational()
}

function review(group, decision) {
  groupAction(group, 'review', { decision, note: note.value, confirm_manual: confirmManual.value })
}

function addMasterResolution() {
  groupAction(selectedGroup.value, 'resolve-master', { ...mapping.value, row: Number(mapping.value.row) })
}

async function submitCorrection() {
  const form = correction.value
  const group = selectedGroup.value
  if (!group || saving.value) return
  const { kind, occurred_at, reason, ...fields } = form
  const details = Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, value.trim()]).filter(([, value]) => value))
  const errors = {}
  if (!details.source_record_id && !details.source_document_no) errors.source_record_id = '请填写原系统记录号或业务单据号。'
  if (kind === 'late_fact' && !occurred_at) errors.occurred_at = '请选择迟到记录的实际发生日期。'
  if (kind === 'voucher_added' && !details.voucher_reference) errors.voucher_reference = '请填写补交凭证的编号或存放位置。'
  if (kind !== 'voucher_added' && !details.description) errors.description = kind === 'late_fact' ? '请说明迟到记录的业务明细。' : '请写明原值、更正值及涉及的字段。'
  if (!reason.trim()) errors.reason = '请填写提交原因。'
  correctionErrors.value = errors
  if (Object.keys(errors).length) return
  if (await groupAction(group, 'correction', { kind, occurred_at, reason: reason.trim(), details }) && correction.value === form) {
    correction.value = { ...newCorrection(), kind }
  }
}

function reviewCorrection(event, decision) {
  const reviewNote = correctionReviewNotes.value[event.id]?.trim()
  if (!reviewNote || event.group_id !== selectedGroup.value?.id) return
  groupAction(selectedGroup.value, 'correction-review', { event_id: event.id, decision, note: reviewNote })
}

function downloadReport() {
  window.open(`/api/import/history-takeovers/${selected.value.id}/review-report.csv`, '_blank', 'noopener')
}

function formatCount(value) { return Number(value || 0).toLocaleString('zh-CN') }
</script>

<template>
  <main class="takeover-page">
    <header class="takeover-intro">
      <div>
        <p class="takeover-eyebrow">申请与核验</p>
        <h2>历史资料承接</h2>
        <p>先检查来源资料，再逐组审核和承接。预检通过不代表已批准或已入账。</p>
      </div>
      <div class="takeover-intro-actions">
        <RouterLink class="takeover-preflight-link" to="/history-preflight">只预检文件</RouterLink>
        <div class="takeover-lock"><ShieldCheck :size="19" /><span>需要相关业务完整查看权限</span></div>
      </div>
    </header>

    <section v-if="!canApply" class="takeover-alert" role="alert"><AlertTriangle :size="18" />当前账号缺少历史承接申请权限或相关业务查看范围。</section>
    <section v-if="error" class="takeover-alert" role="alert"><AlertTriangle :size="18" />{{ error }}</section>

    <section class="takeover-upload panel">
      <div class="takeover-section-title"><div><h3><span class="takeover-step-number">01</span><FileUp :size="18" />选择资料</h3><p>提交后会建立申请与核验记录，不会立即创建正式订单、资金或库存记录。</p></div><button class="takeover-secondary" :disabled="templateLoading" @click="downloadTemplate">{{ templateLoading ? '正在准备…' : '下载承接模板' }}</button></div>
      <div class="takeover-upload-row">
        <label class="takeover-file"><span>{{ file?.name || '选择 .xlsx 文件' }}</span><input ref="fileInput" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" :disabled="!canApply || saving" @change="chooseFile" /></label>
        <button class="takeover-primary" :disabled="!canApply || !file || saving" @click="submitApplication">{{ saving ? '正在检查…' : '提交资料并检查' }}</button>
      </div>
      <p class="takeover-caution"><CircleHelp :size="16" />合成或待核实资料留在申请区；不会自动创建主档、资金流水、库存流水或履约记录。</p>
    </section>

    <div class="takeover-columns">
      <aside class="takeover-list panel">
        <div class="takeover-list-head"><h3><History :size="18" />申请记录</h3><button class="takeover-text-button" :disabled="loading" @click="loadApplications()">刷新</button></div>
        <p v-if="loading && !applications.length" class="takeover-empty">正在读取申请…</p>
        <p v-else-if="!applications.length" class="takeover-empty">还没有历史承接申请</p>
        <button v-for="application in applications" :key="application.id" class="takeover-list-item" :class="{ active: selected?.id === application.id }" @click="loadApplication(application.id)">
          <strong>{{ application.source_file_name }}</strong><span>{{ statusLabel(application.status) }} · {{ application.groups?.length || 0 }} 组</span>
        </button>
      </aside>

      <section v-if="selected" class="takeover-detail panel">
        <div class="takeover-detail-head">
          <div><p class="takeover-eyebrow"><span class="takeover-step-number">02</span>检查结果 · {{ statusLabel(selected.status) }}</p><h3>{{ selected.source_file_name }}</h3><p>提交时间：{{ formatSubmittedAt(selected.submitted_at) }}</p></div>
          <button class="takeover-secondary" @click="downloadReport">下载核验报告</button>
        </div>

        <div class="takeover-summary">
          <span>行数 <strong>{{ formatCount(selected.preflight_summary?.total_rows) }}</strong></span>
          <span>阻断 <strong>{{ formatCount(selected.preflight_summary?.blocked) }}</strong></span>
          <span>待核实 <strong>{{ formatCount(selected.preflight_summary?.manual_review) }}</strong></span>
          <span>警告 <strong>{{ formatCount(selected.preflight_summary?.warnings) }}</strong></span>
        </div>
        <p class="takeover-caution">预检状态：{{ reviewStatusLabel(selected.preflight_summary?.overall_status) }}。审核前须核实真实性、来源凭证、主档依赖和关联冲突。来源关联组编号用于回查原资料并核对同组记录。</p>

        <div class="takeover-groups">
          <button v-for="group in selected.groups" :key="group.id" class="takeover-group-tab" :class="{ active: selectedGroupId === group.id }" @click="selectedGroupId = group.id">
            {{ group.source_group_id }} <em>{{ statusLabel(group.status) }}</em>
          </button>
        </div>

        <article v-if="selectedGroup" class="takeover-group-detail">
          <div class="takeover-group-head"><div><h4>关联组 {{ selectedGroup.source_group_id }}</h4><p>{{ selectedGroup.source_system }} · 覆盖：{{ coverageLabel(selectedGroup.coverage_status) }} · 资料：{{ truthLabel(selectedGroup.truth_status) }}</p></div><span class="takeover-status">{{ statusLabel(selectedGroup.status) }}</span></div>
          <p v-if="selectedGroup.evidence_reference" class="takeover-evidence">来源凭证：{{ selectedGroup.evidence_reference }}</p>
          <div v-for="result in reviewResults" :key="`${result.sheet}-${result.row}`" class="takeover-result-row" :class="`state-${result.status}`">
              <strong>{{ result.sheet }} · 第 {{ result.row }} 行 · {{ reviewStatusLabel(result.status) }}</strong>
            <ul v-if="result.reasons?.length"><li v-for="reason in result.reasons" :key="reason.message">{{ reason.message }} {{ reason.status === '阻断' ? '请核实来源或主档关联。' : '' }}</li></ul>
          </div>

          <details class="takeover-resolution" v-if="canReview && selectedGroup.status !== 'executed'">
            <summary><span class="takeover-step-number">03</span>修正问题 · 关联现有主档</summary>
            <p>仅选择已存在的客户、供应商或 SKU；不会自动新建主档。修正后需重新审核。</p>
            <div class="takeover-form-grid">
              <label>工作表<input v-model="mapping.sheet" list="takeover-sheets" /></label>
              <datalist id="takeover-sheets"><option v-for="item in sourceItems" :key="item.sheet" :value="item.sheet" /></datalist>
              <label>原资料行号<input v-model="mapping.row" type="number" min="2" /></label>
              <label>对象类型<select v-model="mappingKind" @change="changeMappingKind"><option value="customer">客户</option><option value="supplier">供应商</option><option value="sku">SKU</option></select></label>
              <label>搜索现有对象<input v-model="masterSearch" :placeholder="mappingKind === 'sku' ? '输入 SKU 编号或名称' : '输入名称或业务编号'" @input="searchMasters" /></label>
              <label class="wide">选择现有对象<select v-model="mapping.target_code" :disabled="masterLoading || !masterOptions.length"><option value="">{{ masterLoading ? '正在查找…' : masterOptions.length ? '请选择匹配对象' : '先搜索现有对象' }}</option><option v-for="item in masterOptions" :key="item.id" :value="item.code || item.sku">{{ masterLabel(item) }}</option></select></label>
              <label class="wide">关联依据<input v-model="mapping.note" /></label>
            </div>
            <button class="takeover-secondary" :disabled="saving || !mapping.row || !mapping.target_code || !mapping.note" @click="addMasterResolution">保存关联并重新预检</button>
          </details>

          <div v-if="selectedGroup.remainder_snapshot?.sales_orders?.length || selectedGroup.remainder_snapshot?.purchase_orders?.length" class="takeover-remainder">
            <h4>未结业务测算</h4>
            <p>展示核实履约后的剩余数量；审核并启用后可建立接续草稿。</p>
            <div v-for="order in openOrders" :key="order.source_record_id" class="takeover-remainder-item">
              <strong>原系统单据 {{ order.source_document_no }}</strong><span>{{ lifecycleLabel(order.source_lifecycle_state) }}</span>
              <small v-for="line in order.lines" :key="line.source_line_id">行 {{ line.source_line_id }}：已履约 {{ line.verified_net_fulfilled_quantity_base }} / {{ line.ordered_quantity_base }}，剩余 {{ line.remaining_quantity_base }} {{ line.unit_snapshot }}</small>
            </div>
          </div>

          <div v-if="canReview && selectedGroup.status !== 'executed' && !['rejected','withdrawn'].includes(selectedGroup.status)" class="takeover-review">
            <h4><span class="takeover-step-number">04</span>确认承接</h4>
            <p>逐组审核通过后，仍须单独执行承接；历史资金、库存和履约不会在此步骤自动入账。</p>
            <label>审核依据<textarea v-model="note" rows="3" placeholder="写明真实性、来源凭证和依赖核对结果" /></label>
            <label class="takeover-checkbox"><input v-model="confirmManual" type="checkbox" />已依据原始凭证核实所有待核实项</label>
            <div class="takeover-actions">
              <button class="takeover-secondary" :disabled="saving || !note.trim()" @click="review(selectedGroup, 'reject')">拒绝本组</button>
              <button class="takeover-primary" :disabled="saving || !note.trim()" @click="review(selectedGroup, 'approve')"><Check :size="16" />批准本组</button>
              <button v-if="selectedGroup.status === 'approved'" class="takeover-primary" :disabled="saving" @click="groupAction(selectedGroup, 'execute')">逐组执行</button>
              <button class="takeover-text-button" :disabled="saving" @click="groupAction(selectedGroup, 'withdraw', { reason: note })"><RotateCcw :size="15" />撤回</button>
            </div>
          </div>

          <div v-if="selectedGroup.status === 'executed'" class="takeover-execution">
            <h4>执行结果</h4><p>历史销售单 {{ selectedGroup.execution_result?.orders?.length || 0 }} 张；历史采购单 {{ selectedGroup.execution_result?.purchase_orders?.length || 0 }} 张。</p>
            <p>整体进度：{{ overallLabels[selectedGroup.operational_overall?.state] || '待核实' }}。</p>
            <p>归档阶段未产生正式资金、库存流水或履约记录。资金交接：{{ handoffLabel(selectedGroup.finance_handoff_status) }}；库存交接：{{ handoffLabel(inventoryStatus?.status || selectedGroup.inventory_handoff_status) }}；履约交接：{{ handoffLabel(operationalStatus?.status || selectedGroup.fulfillment_handoff_status) }}。</p>
            <details v-if="canReview" class="takeover-resolution">
              <summary>历史资金接续</summary>
              <p>先在资金管理中建立自有账户并上传实际凭证。填写实际人民币金额和实际日期；保存后须由另一名授权人员复核，再核对凭证记账。</p>
              <button class="takeover-secondary" :disabled="saving" @click="loadFinance">读取资金来源、账户和凭证</button>
              <div v-for="item in financeSources" :key="item.source_id" class="takeover-remainder-item">
                <strong>原系统记录 {{ item.source_record_id }} · {{ directionLabel(item.source.direction) }} {{ item.source.amount }} {{ item.source.currency }}</strong>
                <span>{{ handoffLabel(item.status) }}</span>
                <div v-if="item.instruction_id" class="takeover-actions">
                  <button v-if="item.status === 'pending'" class="takeover-secondary" :disabled="saving" @click="financeAction('finance-approve', item.source_id)">复核指令</button>
                  <button v-if="item.status === 'approved'" class="takeover-primary" :disabled="saving" @click="financeAction('finance-post', item.source_id)">核对凭证并记账</button>
                  <button v-if="['pending','approved'].includes(item.status)" class="takeover-secondary" :disabled="saving || !financeChangeReason" @click="financeAction('finance-cancel', item.source_id)">取消指令</button>
                  <button v-if="['pending','approved'].includes(item.status)" class="takeover-secondary" :disabled="saving || !financeChangeReason || !financeNoDebit" @click="financeAction('finance-fail', item.source_id)">登记未扣款失败</button>
                </div>
              </div>
              <label v-if="financeSources.some(row => ['pending','approved'].includes(row.status))">取消或失败原因<input v-model="financeChangeReason" /></label>
              <label v-if="financeSources.some(row => ['pending','approved'].includes(row.status))" class="takeover-checkbox"><input v-model="financeNoDebit" type="checkbox" />已核实未发生扣款；结果未知不能标记失败</label>
              <div class="takeover-form-grid">
                <label>历史收付款来源<select v-model="financeMapping.source_id"><option value="">请选择</option><option v-for="item in financeSources.filter(row => !row.instruction_id || ['cancelled','failed'].includes(row.status))" :key="item.source_id" :value="item.source_id">{{ item.source_record_id }} · {{ item.source.amount }} {{ item.source.currency }}{{ item.instruction_id ? '（修订）' : '' }}</option></select></label>
                <label>自有人民币账户<select v-model="financeMapping.account"><option value="">请选择</option><option v-for="item in financeAccounts" :key="item.id" :value="item.id">{{ item.name }} ({{ item.code }})</option></select></label>
                <label>实际凭证<select v-model="financeMapping.voucher"><option value="">请选择</option><option v-for="item in financeVouchers" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
                <label>实际发生日期<input v-model="financeMapping.actual_date" type="date" /></label>
                <label>实际人民币金额<input v-model="financeMapping.amount" inputmode="decimal" placeholder="0.00" /></label>
                <label class="wide">核实依据<input v-model="financeMapping.reason" /></label>
              </div>
              <button class="takeover-secondary" :disabled="saving || !financeMapping.source_id || !financeMapping.account || !financeMapping.voucher || !financeMapping.actual_date || !financeMapping.amount || !financeMapping.reason" @click="previewFinance">核对可能重复的资金</button>
              <p v-if="financePreview?.restricted">存在无法查看的银行记录，暂不能保存，请联系财务核实。</p>
              <div v-else-if="financePreview?.items?.length" class="takeover-remainder-item">
                <p>发现可能重复的资金，请核对凭证。若与已有账户资金为同一笔，请停止保存并联系财务处理。</p>
                <ul><li v-for="item in financePreview.items" :key="item.id">{{ item.label }}</li></ul>
                <label>核对结果<select v-model="financeDuplicateChoice"><option value="">请选择</option><option value="distinct">已核实为另一笔</option><option v-for="item in financePreview.items.filter(row => row.type === 'bank_event')" :key="item.id" :value="String(-item.id)">与 {{ item.label }} 为同一笔</option></select></label>
                <label>核对说明<input v-model="financeDuplicateReason" /></label>
              </div>
              <p v-else-if="financePreview">未发现同账户、同日期、同方向和同金额的候选记录。</p>
              <button class="takeover-secondary" :disabled="saving || !financePreview || financePreview.restricted || (financePreview.items?.length && (!financeDuplicateChoice || !financeDuplicateReason.trim()))" @click="financeAction('finance-submit')">保存资金指令</button>
            </details>
            <details v-if="canReview" class="takeover-resolution">
              <summary>库存盘点基准</summary>
              <p>盘点基准不会重放历史出入库。仓库归属和货物所有权分别核实；只有自有货物计入可用库存。已有库存流水或预留的 SKU 需先人工核对。</p>
              <button class="takeover-secondary" :disabled="saving" @click="loadInventory">读取盘点来源</button>
              <p v-if="inventoryStatus">当前状态：{{ handoffLabel(inventoryStatus.status) }}；基准记录 {{ inventoryStatus.baselines?.length || 0 }} 条。</p>
              <div v-for="row in inventoryRows" :key="row.source_id" class="takeover-remainder-item">
                <strong>SKU {{ skuBusinessLabel(row.source) }} · {{ row.source.counted_quantity }} {{ row.source.unit_snapshot }}</strong>
                <span>{{ row.source.warehouse_type }} · {{ row.source.warehouse }} · {{ row.source.lot_reference || '无批次/货位' }}</span>
                <div class="takeover-form-grid wide">
                  <label>货物所有权<select v-model="row.goods_ownership"><option value="">请选择</option><option value="own">自有货物</option><option value="third_party">第三方货物</option></select></label>
                  <label>核实单位成本<input v-model="row.unit_cost" inputmode="decimal" /></label>
                  <label>成本币种<input v-model="row.cost_currency" maxlength="3" placeholder="例如 USD" /></label>
                  <label v-if="!row.source.lot_reference" class="takeover-checkbox"><input v-model="row.no_lot" type="checkbox" />已核实批次/货位不适用</label>
                </div>
              </div>
              <label v-if="inventoryRows.length" class="takeover-checkbox"><input v-model="inventoryComplete" type="checkbox" />已核实这些 SKU 的盘点范围完整</label>
              <label v-if="inventoryRows.length">盘点与成本依据<input v-model="inventoryReason" /></label>
              <label v-if="inventoryStatus">复核或撤销依据<input v-model="inventoryReviewNote" /></label>
              <div v-if="inventoryStatus" class="takeover-actions">
                <button v-if="!['posted','reversed'].includes(inventoryStatus.status)" class="takeover-secondary" :disabled="saving || !inventoryComplete || !inventoryReason" @click="inventoryAction('inventory-propose')">保存基准申请</button>
                <button v-if="inventoryStatus.status === 'pending_review'" class="takeover-secondary" :disabled="saving || !inventoryReviewNote" @click="inventoryAction('inventory-approve')">复核基准</button>
                <button v-if="inventoryStatus.status === 'approved'" class="takeover-primary" :disabled="saving" @click="inventoryAction('inventory-execute')">启用盘点基准</button>
                <button v-if="inventoryStatus.status === 'posted'" class="takeover-secondary" :disabled="saving || !inventoryReviewNote" @click="inventoryAction('inventory-reverse')">撤销基准</button>
              </div>
            </details>
            <details v-if="canReview" class="takeover-resolution">
              <summary>未结余额与剩余业务</summary>
              <p>逐项核实原币未结余额、剩余明细和依据。历史收付款不会再次产生资金流水；剩余业务先生成草稿，再通过正常确认、下单和履约办理。</p>
              <button class="takeover-secondary" :disabled="saving" @click="loadOperational">读取合同与未结来源</button>
              <p v-if="operationalStatus">当前状态：{{ handoffLabel(operationalStatus.status) }}。</p>
              <template v-if="operationalStatus && !['drafts_created', 'reversed'].includes(operationalStatus.status)">
                <div class="takeover-form-grid">
                  <label>启用日期<input v-model="operationalCutover" type="date" /></label>
                  <label class="wide">接续核实依据<input v-model="operationalReason" /></label>
                </div>
                <section v-for="doc in operationalStatus.contracts" :key="doc.source_id" class="takeover-remainder">
                  <h4>{{ doc.record_type }} · {{ doc.source.order_no || doc.source.purchase_no }} · {{ doc.source.currency }}</h4>
                  <p>来源状态：{{ lifecycleLabel(doc.source.lifecycle_state) }}；有剩余数量的明细 {{ doc.remaining_lines.length }} 条。</p>
                  <div class="takeover-form-grid">
                    <label>未结承接方式<select v-model="operationalForms[doc.source_id].balance_mode"><option value="">请选择</option><option value="itemized">逐笔核实全部来源计划</option><option value="balance_only">按核实余额承接</option></select></label>
                    <label v-if="operationalForms[doc.source_id].balance_mode === 'balance_only'">未结原币余额<input v-model="operationalForms[doc.source_id].balance_amount" inputmode="decimal" /></label>
                    <label v-if="operationalForms[doc.source_id].balance_mode === 'balance_only'">预计结算日期<input v-model="operationalForms[doc.source_id].due_date" type="date" /></label>
                    <label class="wide">余额核实依据<input v-model="operationalForms[doc.source_id].evidence_reference" /></label>
                  </div>
                  <p v-if="operationalForms[doc.source_id].balance_mode === 'itemized'">逐笔方式会核对本合同全部来源计划及其已确认流水；没有完整计划时请选择余额承接。</p>
                  <div v-for="plan in doc.plans" :key="plan.source_id" class="takeover-remainder-item"><strong>原系统收付款计划 {{ plan.source_record_id }}</strong><span>{{ lifecycleLabel(plan.source.lifecycle_state) }}</span><small>计划 {{ plan.source.planned_amount }} / 已核销 {{ plan.source.settled_amount }} {{ plan.source.currency }} · {{ plan.source.voucher_reference }}</small></div>
                  <div v-for="(line, index) in doc.remaining_lines" :key="line.source_id" class="takeover-remainder-item">
                    <strong>SKU {{ skuBusinessLabel(line.source) }} · 剩余 {{ line.remaining_quantity }} {{ line.source.base_unit_snapshot }}</strong><span>原系统明细 {{ line.source_record_id }}</span>
                    <div v-if="doc.record_type === '销售订单'" class="takeover-form-grid wide">
                      <label>核实单位成本<input v-model="operationalForms[doc.source_id].line_options[index].unit_cost" inputmode="decimal" /></label>
                      <label>成本币种（SKU：{{ line.sku_currency }}）<input v-model="operationalForms[doc.source_id].line_options[index].cost_currency" /></label>
                      <label>成本依据<input v-model="operationalForms[doc.source_id].line_options[index].cost_evidence" /></label>
                    </div>
                    <div v-else class="takeover-form-grid wide">
                      <label>供货档案<select v-model="operationalForms[doc.source_id].line_options[index].supplier_sku_id"><option value="">无档案，手工核实</option><option v-for="supplier in line.supplier_sources" :key="supplier.id" :value="supplier.id">{{ supplier.supplier_sku_code }} · MOQ {{ supplier.moq }}</option></select></label>
                      <label>手工来源依据<input v-model="operationalForms[doc.source_id].line_options[index].manual_reason" /></label>
                      <label>采购归属<select v-model="operationalForms[doc.source_id].line_options[index].target"><option value="">请选择</option><option value="inventory">库存</option><option value="order">接续销售订单</option></select></label>
                      <label v-if="operationalForms[doc.source_id].line_options[index].target === 'order'">销售订单<select v-model="operationalForms[doc.source_id].line_options[index].sales_source_id"><option value="">请选择</option><option v-for="sales in operationalStatus.contracts.filter(item => item.record_type === '销售订单' && item.remaining_lines.some(candidate => candidate.source.sku_code === line.source.sku_code))" :key="sales.source_id" :value="sales.source_id">{{ sales.source.order_no }}</option></select></label>
                    </div>
                  </div>
                  <div v-if="doc.remaining_lines.length && doc.record_type === '销售订单'" class="takeover-form-grid">
                    <label>剩余运费<input v-model="operationalForms[doc.source_id].remaining_shipping_fee" inputmode="decimal" /></label>
                    <label>剩余折扣<input v-model="operationalForms[doc.source_id].remaining_discount" inputmode="decimal" /></label>
                    <label>金额依据<input v-model="operationalForms[doc.source_id].amount_evidence" /></label>
                  </div>
                  <template v-if="doc.remaining_lines.length && doc.record_type === '采购订单'">
                    <label class="takeover-checkbox"><input v-model="operationalForms[doc.source_id].no_additional_costs" type="checkbox" />已核实本次接续没有额外公共费用</label>
                    <label class="takeover-checkbox"><input v-model="operationalForms[doc.source_id].additional_costs_pending" type="checkbox" />有公共费用，先建立草稿并在采购成本分配中登记</label>
                    <label>费用核实依据<input v-model="operationalForms[doc.source_id].costs_evidence" /></label>
                  </template>
                </section>
                <label>复核依据<input v-model="operationalReviewNote" /></label>
                <div class="takeover-actions">
                  <button class="takeover-secondary" :disabled="saving || !operationalCutover || !operationalReason" @click="operationalAction('operational-propose')">保存接续申请</button>
                  <button v-if="operationalStatus.status === 'pending_review'" class="takeover-secondary" :disabled="saving || !operationalReviewNote" @click="operationalAction('operational-approve')">复核接续申请</button>
                  <button v-if="operationalStatus.status === 'approved'" class="takeover-primary" :disabled="saving" @click="operationalAction('operational-execute')">启用未结并建立草稿</button>
                </div>
              </template>
              <template v-if="operationalStatus?.links?.length">
                <p>原单保留历史记录，未结计划只反映启用时仍欠金额；后续金额变更走正式修订。</p>
                <div v-for="link in operationalStatus.links" :key="link.id" class="takeover-remainder-item">
                  <strong>{{ link.archived_no }} · 未结 {{ link.outstanding_balance }} {{ link.currency }}</strong><span>{{ handoffLabel(link.continuation_status) }}</span>
                  <small v-if="link.continuation_no">接续单：{{ link.continuation_no }}</small><small v-else>没有剩余履约</small>
                  <small v-for="plan in link.plans" :key="plan.id">未结计划 · {{ plan.planned_amount }} / 已结 {{ plan.settled_amount }}</small>
                  <div class="takeover-actions wide"><a :href="link.record_type === '销售订单' ? '/receivables' : '/payables'">查看未结计划</a><a v-if="link.continuation_id" :href="link.record_type === '销售订单' ? '/orders' : '/purchase-orders'">查看接续单</a>
                    <button v-if="link.continuation_status === 'draft'" class="takeover-secondary" :disabled="saving" @click="confirmContinuation(link)">{{ link.record_type === '销售订单' ? '确认销售接续单' : '确认采购下单' }}</button></div>
                </div>
                <label>采购低于 MOQ 时的例外原因<input v-model="operationalMoqReason" /></label>
                <label v-if="operationalStatus.status === 'drafts_created'">撤销原因<input v-model="operationalReviewNote" /></label>
                <button v-if="operationalStatus.status === 'drafts_created'" class="takeover-secondary" :disabled="saving || !operationalReviewNote.trim()" @click="operationalAction('operational-reverse')">撤销未使用的接续草稿</button>
              </template>
            </details>
            <form class="takeover-fields" novalidate @submit.prevent="submitCorrection">
              <label>追溯类型<select v-model="correction.kind" @change="correctionErrors = {}"><option value="late_fact">迟到记录</option><option value="correction">审计更正</option><option value="voucher_added">补交凭证</option></select></label>
              <label>原系统记录号<input v-model="correction.source_record_id" list="correction-source-records" aria-describedby="correction-source-error" />
                <datalist id="correction-source-records"><option v-for="record in [...new Set(sourceItems.map(item => item.data?.source_record_id).filter(Boolean))]" :key="record" :value="record" /></datalist>
              </label>
              <label>原系统业务单据号<input v-model="correction.source_document_no" aria-describedby="correction-source-error" /></label>
              <small v-if="correctionErrors.source_record_id" id="correction-source-error" role="alert">{{ correctionErrors.source_record_id }}</small>
              <label>实际发生日期{{ correction.kind === 'late_fact' ? '（必填）' : '（选填）' }}<input v-model="correction.occurred_at" type="date" />
                <small v-if="correctionErrors.occurred_at" role="alert">{{ correctionErrors.occurred_at }}</small>
              </label>
              <label>凭证编号或存放位置{{ correction.kind === 'voucher_added' ? '（必填）' : '（选填）' }}<input v-model="correction.voucher_reference" />
                <small v-if="correctionErrors.voucher_reference" role="alert">{{ correctionErrors.voucher_reference }}</small>
              </label>
              <label>{{ { late_fact: '迟到记录明细', correction: '更正明细（原值、更正值）', voucher_added: '补充说明（选填）' }[correction.kind] }}<textarea v-model="correction.description" rows="3" />
                <small v-if="correctionErrors.description" role="alert">{{ correctionErrors.description }}</small>
              </label>
              <label>提交原因（必填）<textarea v-model="correction.reason" rows="2" />
                <small v-if="correctionErrors.reason" role="alert">{{ correctionErrors.reason }}</small>
              </label>
              <button type="submit" class="takeover-secondary" :disabled="saving">提交追溯更正申请</button>
            </form>
          </div>
        </article>

        <section class="takeover-audit">
          <h4>申请与操作记录</h4>
          <ol>
            <li v-for="event in selected.events" :key="event.id">
              <span>{{ eventLabel(event.event_type) }}</span>
              <small>{{ auditActorLabel(event) }} · {{ new Date(event.created_at).toLocaleString('zh-CN') }}</small>
              <template v-if="correctionEventTypes.includes(event.event_type)">
                <p>发生日期：{{ event.details?.occurred_at || '未提供' }} · {{ event.details?.reason }}</p>
                <dl>
                  <template v-for="(label, key) in correctionDetailLabels" :key="key">
                    <template v-if="event.details?.details?.[key]"><dt>{{ label }}</dt><dd>{{ event.details.details[key] }}</dd></template>
                  </template>
                </dl>
                <div v-if="canReview && event.group_id === selectedGroup?.id && !selectedGroup.verified_correction_ids?.includes(event.id) && !selected.events.some(review => review.event_type === 'correction_reviewed' && review.details?.source_event_id === event.id)" class="takeover-fields">
                  <label>更正审核依据<textarea v-model="correctionReviewNotes[event.id]" rows="2" /></label>
                  <div class="takeover-actions">
                    <button class="takeover-secondary" :disabled="saving || !correctionReviewNotes[event.id]?.trim()" @click="reviewCorrection(event, 'reject')">退回更正</button>
                    <button class="takeover-primary" :disabled="saving || !correctionReviewNotes[event.id]?.trim()" @click="reviewCorrection(event, 'approve')">核实并保留更正轨迹</button>
                  </div>
                </div>
              </template>
              <p v-if="event.event_type === 'correction_reviewed'">{{ event.details?.decision === 'approve' ? '已核实' : '已退回' }} · {{ event.details?.note }}</p>
            </li>
          </ol>
        </section>
      </section>
      <section v-else class="takeover-detail panel takeover-empty">选择一条申请，查看分组核验结果。</section>
    </div>
  </main>
</template>

<style scoped>
.takeover-page{display:grid;gap:16px;min-width:0}
.takeover-intro,.takeover-section-title,.takeover-list-head,.takeover-detail-head,.takeover-group-head,.takeover-upload-row{
  display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap
}
.takeover-intro,.takeover-upload,.takeover-list,.takeover-detail{padding:18px;min-width:0}
.takeover-intro{border-radius:12px;background:#eaf3ee}
.takeover-intro h2,.takeover-section-title h3,.takeover-list-head h3,.takeover-detail-head h3,.takeover-group-head h4{margin:0;overflow-wrap:anywhere}
.takeover-section-title h3,.takeover-list-head h3,.takeover-lock,.takeover-caution,.takeover-alert{display:flex;align-items:center;gap:8px}
.takeover-eyebrow{color:#527264;margin:0 0 5px;font-size:var(--text-caption)}
.takeover-intro p,.takeover-section-title p,.takeover-detail-head p,.takeover-group-head p{margin:6px 0}
.takeover-columns{display:grid;grid-template-columns:minmax(200px,1fr) minmax(0,3fr);gap:16px;align-items:start}
.takeover-list{display:grid;gap:8px}
.takeover-list-item,.takeover-group-tab{display:grid;gap:3px;text-align:left;min-width:0;overflow-wrap:anywhere}
.takeover-list-item.active,.takeover-group-tab.active{background:#edf6f1;border-color:#8ab4a3}
.takeover-summary,.takeover-form-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}
.takeover-summary span{padding:10px;border-radius:8px;background:#f1f5f3}
.takeover-groups,.takeover-actions{display:flex;flex-wrap:wrap;gap:8px}
.takeover-group-detail,.takeover-resolution,.takeover-result-row,.takeover-remainder-item{margin-top:12px;padding:12px;border:1px solid #dce8e1;border-radius:9px}
.takeover-resolution{background:#f7faf8}
.takeover-remainder-item{display:grid;gap:6px;background:white}
.takeover-form-grid label,.takeover-remainder-item label{display:grid;align-content:start;gap:5px;min-width:0;color:#345849}
.takeover-form-grid input,.takeover-form-grid select,.takeover-form-grid textarea,.takeover-remainder-item select,.takeover-remainder-item input{
  width:100%;min-height:36px;padding:6px 8px;border:1px solid #cbdcd3;border-radius:7px;background:#fff;color:#223d32
}
.takeover-form-grid .wide{grid-column:1/-1}
.takeover-primary,.takeover-secondary,.takeover-text-button,.takeover-list-item,.takeover-group-tab{
  min-height:36px;padding:7px 11px;border:1px solid #cddbd3;border-radius:8px;background:#fff;color:#315c4a;font-weight:650;white-space:normal
}
.takeover-primary{background:#195c49;color:#fff;border-color:#195c49}
.takeover-page button:not(:disabled){cursor:pointer}
.takeover-page button:disabled{opacity:.55;cursor:not-allowed}
.takeover-lock,.takeover-caution,.takeover-alert{flex-wrap:wrap;padding:9px 11px;border-radius:8px;background:#edf6f1}
.takeover-alert{color:#972a2a;background:#fff0ec}
.takeover-file,.takeover-evidence{min-width:0;overflow-wrap:anywhere}
.takeover-file input{max-width:100%}
.takeover-resolution > button{margin:4px 8px 4px 0;max-width:100%}
.takeover-remainder-item > .wide{grid-column:1/-1;min-width:0}
.takeover-intro-actions{display:grid;justify-items:end;gap:8px}.takeover-preflight-link{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:7px 11px;border:1px solid #cddbd3;border-radius:8px;background:#fff;color:#315c4a;font-size:13px;font-weight:700;text-decoration:none}.takeover-preflight-link:hover{background:#f3f8f5;border-color:#9ebca9}
@media(max-width:900px){.takeover-columns{grid-template-columns:1fr}.takeover-list{position:static;grid-template-columns:repeat(2,minmax(0,1fr))}.takeover-list-head,.takeover-empty{grid-column:1/-1}}
.takeover-step-number{display:inline-grid;place-items:center;min-width:22px;height:22px;margin-right:5px;border-radius:50%;background:#e7f1eb;color:#285c49;font-size:11px;vertical-align:middle}.takeover-group-head,.takeover-remainder-item,.takeover-result-row,.takeover-audit{min-width:0}.takeover-result-row,.takeover-result-row li,.takeover-remainder-item,.takeover-group-tab,.takeover-audit li{overflow-wrap:anywhere;word-break:break-word}.takeover-form-grid input,.takeover-form-grid select{min-width:0;max-width:100%}.takeover-resolution summary{cursor:pointer;font-weight:700}.takeover-resolution p{line-height:1.6}
@media(max-width:600px){.takeover-intro{display:grid;padding:16px}.takeover-intro-actions{justify-items:start;width:100%}.takeover-lock{white-space:normal;width:max-content;max-width:100%}.takeover-upload,.takeover-list,.takeover-detail{padding:14px}.takeover-upload-row{display:grid}.takeover-file{align-items:flex-start;flex-direction:column}.takeover-file input{max-width:100%;width:100%}.takeover-list{grid-template-columns:1fr}.takeover-detail-head{display:grid}.takeover-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.takeover-form-grid{grid-template-columns:minmax(0,1fr)}.takeover-actions>*{flex:1}.takeover-actions button{min-height:40px}.takeover-group-tab{max-width:100%;flex-wrap:wrap}.takeover-step-number{flex:none}}
.takeover-fields { display: grid; gap: .75rem; }
.takeover-audit dd { overflow-wrap: anywhere; white-space: pre-wrap; }
</style>
