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
const correction = ref({ kind: 'late_fact', occurred_at: '', reason: '', details: '' })
const financeSources = ref([])
const financeAccounts = ref([])
const financeVouchers = ref([])
const financeMapping = ref({ source_id: '', account: '', voucher: '', actual_date: '', amount: '', reason: '' })
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
const coverageLabels = { complete: '资料完整', partial: '资料不完整', unknown: '资料范围待核实' }
const handoffLabels = { not_connected: '尚未接续', pending_review: '待复核', approved: '已复核，待启用', posted: '已启用', reversed: '已撤销', sources_posted: '来源资金已记账', drafts_created: '未结余额已启用，接续草稿已生成', no_remaining: '无剩余履约', unmapped: '待映射', pending: '待复核', cancelled: '已取消', failed: '已核实失败', draft: '草稿', confirmed: '已确认', ordered: '已下单', partial: '部分到货', shipped: '已发货', completed: '已完成', production: '生产中' }
const overallLabels = { not_archived: '未归档', archived: '已归档，待准备接续', pending_review: '接续资料待复核', ready: '可接续或待确认接续单', connected: '适用项目已接续' }
function handoffLabel(value) { return handoffLabels[value] || value }
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

async function downloadTemplate() {
  if (templateLoading.value) return
  templateLoading.value = true; error.value = ''
  try {
    const response = await api.get('/import/history-takeovers/template/', { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'history-takeover-template-v1.xlsx'; anchor.click()
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

function submitCorrection() {
  let details
  try { details = JSON.parse(correction.value.details) }
  catch { error.value = '请用有效 JSON 填写更正内容。'; return }
  groupAction(selectedGroup.value, 'correction', { ...correction.value, details })
}

function reviewCorrection(event, decision) {
  groupAction(selectedGroup.value, 'correction-review', { event_id: event.id, decision, note: note.value })
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
        <p class="takeover-eyebrow">受控流程</p>
        <h2>历史资料承接</h2>
        <p>提交申请后，核实资料并逐组承接。预检通过后仍需审核批准，才能承接。</p>
      </div>
      <div class="takeover-intro-actions">
        <RouterLink class="takeover-preflight-link" to="/history-preflight">只预检文件</RouterLink>
        <div class="takeover-lock"><ShieldCheck :size="19" /><span>需要相关业务完整查看权限</span></div>
      </div>
    </header>

    <section v-if="!canApply" class="takeover-alert" role="alert"><AlertTriangle :size="18" />当前账号缺少历史承接申请权限或相关业务查看范围。</section>
    <section v-if="error" class="takeover-alert" role="alert"><AlertTriangle :size="18" />{{ error }}</section>

    <section class="takeover-upload panel">
      <div class="takeover-section-title"><div><h3><FileUp :size="18" />提交承接申请</h3><p>申请记录会保留来源行和凭证引用。</p></div><button class="takeover-secondary" :disabled="templateLoading" @click="downloadTemplate">{{ templateLoading ? '正在准备…' : '下载承接模板' }}</button></div>
      <div class="takeover-upload-row">
        <label class="takeover-file"><span>{{ file?.name || '选择 .xlsx 文件' }}</span><input ref="fileInput" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" :disabled="!canApply || saving" @change="chooseFile" /></label>
        <button class="takeover-primary" :disabled="!canApply || !file || saving" @click="submitApplication">{{ saving ? '正在提交…' : '提交申请并预检' }}</button>
      </div>
      <p class="takeover-caution"><CircleHelp :size="16" />模拟或待核实资料只留在暂存区；不会创建主档、资金流水、库存流水或履约记录。</p>
    </section>

    <div class="takeover-columns">
      <aside class="takeover-list panel">
        <div class="takeover-list-head"><h3><History :size="18" />申请记录</h3><button class="takeover-text-button" :disabled="loading" @click="loadApplications()">刷新</button></div>
        <p v-if="loading && !applications.length" class="takeover-empty">正在读取申请…</p>
        <p v-else-if="!applications.length" class="takeover-empty">暂无可显示的申请记录。提交申请后可在这里查看。</p>
        <button v-for="application in applications" :key="application.id" class="takeover-list-item" :class="{ active: selected?.id === application.id }" @click="loadApplication(application.id)">
          <strong>{{ application.source_file_name }}</strong><span>{{ statuses[application.status] || application.status }} · {{ application.groups?.length || 0 }} 组</span>
          <small>SHA256 {{ application.source_sha256?.slice(0, 12) }}</small>
        </button>
      </aside>

      <section v-if="selected" class="takeover-detail panel">
        <div class="takeover-detail-head">
          <div><p class="takeover-eyebrow">申请 #{{ selected.id }} · {{ statuses[selected.status] || selected.status }}</p><h3>{{ selected.source_file_name }}</h3><p>申请人：{{ selected.created_by_label || '开发身份（非实名）' }} · {{ selected.created_actor_kind === 'development' ? '不得作为实名审核人' : '实名账号' }}</p></div>
          <button class="takeover-secondary" @click="downloadReport">下载核验报告</button>
        </div>

        <div class="takeover-summary">
          <span>行数 <strong>{{ formatCount(selected.preflight_summary?.total_rows) }}</strong></span>
          <span>阻断 <strong>{{ formatCount(selected.preflight_summary?.blocked) }}</strong></span>
          <span>待核实 <strong>{{ formatCount(selected.preflight_summary?.manual_review) }}</strong></span>
          <span>警告 <strong>{{ formatCount(selected.preflight_summary?.warnings) }}</strong></span>
        </div>
        <p class="takeover-caution">预检状态：{{ selected.preflight_summary?.overall_status || '未完成' }}。审核前请核实资料真实性、来源凭证、主档依赖和关联冲突。</p>

        <div class="takeover-groups">
          <button v-for="group in selected.groups" :key="group.id" class="takeover-group-tab" :class="{ active: selectedGroupId === group.id }" @click="selectedGroupId = group.id">
            {{ group.source_group_id }} <em>{{ statuses[group.status] || group.status }}</em>
          </button>
        </div>

        <article v-if="selectedGroup" class="takeover-group-detail">
          <div class="takeover-group-head"><div><h4>关联组 {{ selectedGroup.source_group_id }}</h4><p>{{ selectedGroup.source_system }} · {{ coverageLabels[selectedGroup.coverage_status] || selectedGroup.coverage_status }} · {{ selectedGroup.truth_status }}</p></div><span class="takeover-status">{{ statuses[selectedGroup.status] || selectedGroup.status }}</span></div>
          <p v-if="selectedGroup.evidence_reference" class="takeover-evidence">来源凭证：{{ selectedGroup.evidence_reference }}</p>
          <div v-for="result in reviewResults" :key="`${result.sheet}-${result.row}`" class="takeover-result-row" :class="`state-${result.status}`">
            <strong>{{ result.sheet }} · 第 {{ result.row }} 行 · {{ result.status }}</strong>
            <ul v-if="result.reasons?.length"><li v-for="reason in result.reasons" :key="reason.message">{{ reason.message }} {{ reason.status === '阻断' ? '请核实来源或主档关联。' : '' }}</li></ul>
          </div>

          <details class="takeover-resolution" v-if="canReview && selectedGroup.status !== 'executed'">
            <summary>人工关联现有主档</summary>
            <p>仅选择已存在的客户、供应商或 SKU；不会自动新建主档。修正后需重新审核。</p>
            <div class="takeover-form-grid">
              <label>工作表<input v-model="mapping.sheet" list="takeover-sheets" /></label>
              <datalist id="takeover-sheets"><option v-for="item in sourceItems" :key="item.sheet" :value="item.sheet" /></datalist>
              <label>原行号<input v-model="mapping.row" type="number" min="2" /></label>
              <label>字段<input v-model="mapping.field" list="takeover-fields" /></label>
              <datalist id="takeover-fields"><option value="customer_code" /><option value="supplier_code" /><option value="sku_code" /></datalist>
              <label>现有主档编码<input v-model="mapping.target_code" /></label>
              <label class="wide">关联依据<input v-model="mapping.note" /></label>
            </div>
            <button class="takeover-secondary" :disabled="saving || !mapping.row || !mapping.target_code || !mapping.note" @click="addMasterResolution">保存关联并重新预检</button>
          </details>

          <div v-if="selectedGroup.remainder_snapshot?.sales_orders?.length || selectedGroup.remainder_snapshot?.purchase_orders?.length" class="takeover-remainder">
            <h4>未结业务测算</h4>
            <p>这里显示核实履约后的剩余数量；审核并启用后，可以建立接续草稿。</p>
            <div v-for="order in openOrders" :key="order.source_record_id" class="takeover-remainder-item">
              <strong>{{ order.source_document_no }}</strong><span>{{ order.source_lifecycle_state }}</span>
              <small v-for="line in order.lines" :key="line.source_line_id">行 {{ line.source_line_id }}：已履约 {{ line.verified_net_fulfilled_quantity_base }} / {{ line.ordered_quantity_base }}，剩余 {{ line.remaining_quantity_base }} {{ line.unit_snapshot }}</small>
            </div>
          </div>

          <div v-if="canReview && selectedGroup.status !== 'executed' && !['rejected','withdrawn'].includes(selectedGroup.status)" class="takeover-review">
            <label>审核依据<textarea v-model="note" rows="3" placeholder="写明真实性、来源凭证和依赖核对结果" /></label>
            <label class="takeover-checkbox"><input v-model="confirmManual" type="checkbox" />已依据原始凭证核实所有待核实项</label>
            <div class="takeover-actions">
              <button class="takeover-secondary" :disabled="saving || !note.trim()" @click="review(selectedGroup, 'reject')">拒绝</button>
              <button class="takeover-primary" :disabled="saving || !note.trim()" @click="review(selectedGroup, 'approve')"><Check :size="16" />批准</button>
              <button v-if="selectedGroup.status === 'approved'" class="takeover-primary" :disabled="saving" @click="groupAction(selectedGroup, 'execute')">承接</button>
              <button class="takeover-text-button" :disabled="saving" @click="groupAction(selectedGroup, 'withdraw', { reason: note })"><RotateCcw :size="15" />撤回</button>
            </div>
          </div>

          <div v-if="selectedGroup.status === 'executed'" class="takeover-execution">
            <h4>执行结果</h4><p>历史销售单 {{ selectedGroup.execution_result?.orders?.length || 0 }} 张；历史采购单 {{ selectedGroup.execution_result?.purchase_orders?.length || 0 }} 张。</p>
            <p>整体进度：{{ overallLabels[selectedGroup.operational_overall?.state] || '已归档，待核查接续' }}。</p>
            <p>归档阶段未产生正式资金、库存流水或履约记录。资金交接：{{ handoffLabel(selectedGroup.finance_handoff_status) }}；库存交接：{{ handoffLabel(inventoryStatus?.status || selectedGroup.inventory_handoff_status) }}；履约交接：{{ handoffLabel(operationalStatus?.status || selectedGroup.fulfillment_handoff_status) }}。</p>
            <details v-if="canReview" class="takeover-resolution">
              <summary>历史资金接续</summary>
              <p>先在资金管理中建立自有账户并上传实际凭证。填写实际人民币金额和实际日期；保存后须由另一名授权人员复核，再核对凭证记账。</p>
              <button class="takeover-secondary" :disabled="saving" @click="loadFinance">加载资金来源、账户和凭证</button>
              <div v-for="item in financeSources" :key="item.source_id" class="takeover-remainder-item">
                <strong>{{ item.source_record_id }} · {{ item.source.direction }} {{ item.source.amount }} {{ item.source.currency }}</strong>
                <span>{{ handoffLabel(item.status) }}<template v-if="item.fact_id"> · 资金事实 #{{ item.fact_id }}</template></span>
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
                <label>实际凭证<select v-model="financeMapping.voucher"><option value="">请选择</option><option v-for="item in financeVouchers" :key="item.id" :value="item.id">{{ item.name }} · {{ item.sha256?.slice(0, 12) }}</option></select></label>
                <label>实际发生日期<input v-model="financeMapping.actual_date" type="date" /></label>
                <label>实际人民币金额<input v-model="financeMapping.amount" inputmode="decimal" placeholder="0.00" /></label>
                <label class="wide">核实依据<input v-model="financeMapping.reason" /></label>
              </div>
              <button class="takeover-secondary" :disabled="saving || !financeMapping.source_id || !financeMapping.account || !financeMapping.voucher || !financeMapping.actual_date || !financeMapping.amount || !financeMapping.reason" @click="financeAction('finance-submit')">保存资金指令</button>
            </details>
            <details v-if="canReview" class="takeover-resolution">
              <summary>库存盘点基准</summary>
              <p>盘点基准不会重新登记历史出入库。请分别核实仓库归属和货物所有权；只有自有货物计入可用库存。已有库存流水或预留的 SKU 需先人工核对。</p>
              <button class="takeover-secondary" :disabled="saving" @click="loadInventory">加载盘点来源</button>
              <p v-if="inventoryStatus">当前状态：{{ handoffLabel(inventoryStatus.status) }}；基准记录 {{ inventoryStatus.baselines?.length || 0 }} 条。</p>
              <div v-for="row in inventoryRows" :key="row.source_id" class="takeover-remainder-item">
                <strong>{{ row.source.sku_code }} · {{ row.source.counted_quantity }} {{ row.source.unit_snapshot }}</strong>
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
              <button class="takeover-secondary" :disabled="saving" @click="loadOperational">加载合同与未结来源</button>
              <p v-if="operationalStatus">当前状态：{{ handoffLabel(operationalStatus.status) }}。</p>
              <template v-if="operationalStatus && !['drafts_created', 'reversed'].includes(operationalStatus.status)">
                <div class="takeover-form-grid">
                  <label>启用日期<input v-model="operationalCutover" type="date" /></label>
                  <label class="wide">接续核实依据<input v-model="operationalReason" /></label>
                </div>
                <section v-for="doc in operationalStatus.contracts" :key="doc.source_id" class="takeover-remainder">
                  <h4>{{ doc.record_type }} · {{ doc.source.order_no || doc.source.purchase_no }} · {{ doc.source.currency }}</h4>
                  <p>来源状态：{{ doc.source.lifecycle_state }}；有剩余数量的明细 {{ doc.remaining_lines.length }} 条。</p>
                  <div class="takeover-form-grid">
                    <label>未结承接方式<select v-model="operationalForms[doc.source_id].balance_mode"><option value="">请选择</option><option value="itemized">逐笔核实全部来源计划</option><option value="balance_only">按核实余额承接</option></select></label>
                    <label v-if="operationalForms[doc.source_id].balance_mode === 'balance_only'">未结原币余额<input v-model="operationalForms[doc.source_id].balance_amount" inputmode="decimal" /></label>
                    <label v-if="operationalForms[doc.source_id].balance_mode === 'balance_only'">预计结算日期<input v-model="operationalForms[doc.source_id].due_date" type="date" /></label>
                    <label class="wide">余额核实依据<input v-model="operationalForms[doc.source_id].evidence_reference" /></label>
                  </div>
                  <p v-if="operationalForms[doc.source_id].balance_mode === 'itemized'">逐笔方式会核对本合同全部来源计划及其已确认流水；没有完整计划时请选择余额承接。</p>
                  <div v-for="plan in doc.plans" :key="plan.source_id" class="takeover-remainder-item"><strong>计划 {{ plan.source_record_id }}</strong><span>{{ plan.source.lifecycle_state }}</span><small>计划 {{ plan.source.planned_amount }} / 已核销 {{ plan.source.settled_amount }} {{ plan.source.currency }} · {{ plan.source.voucher_reference }}</small></div>
                  <div v-for="(line, index) in doc.remaining_lines" :key="line.source_id" class="takeover-remainder-item">
                    <strong>{{ line.source.sku_code }} · 剩余 {{ line.remaining_quantity }} {{ line.source.base_unit_snapshot }}</strong><span>{{ line.source_record_id }}</span>
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
                <p>原单保留为历史记录，未结计划只反映启用时仍欠的金额；之后如需更改金额，请通过正式修订办理。</p>
                <div v-for="link in operationalStatus.links" :key="link.id" class="takeover-remainder-item">
                  <strong>{{ link.archived_no }} · 未结 {{ link.outstanding_balance }} {{ link.currency }}</strong><span>{{ handoffLabel(link.continuation_status) }}</span>
                  <small v-if="link.continuation_no">接续单：{{ link.continuation_no }}</small><small v-else>没有剩余履约</small>
                  <small v-for="plan in link.plans" :key="plan.id">未结计划 #{{ plan.id }} · {{ plan.planned_amount }} / 已结 {{ plan.settled_amount }}</small>
                  <div class="takeover-actions wide"><a :href="link.record_type === '销售订单' ? '/receivables' : '/payables'">查看未结计划</a><a v-if="link.continuation_id" :href="link.record_type === '销售订单' ? '/orders' : '/purchase-orders'">查看接续单</a>
                    <button v-if="link.continuation_status === 'draft'" class="takeover-secondary" :disabled="saving" @click="confirmContinuation(link)">{{ link.record_type === '销售订单' ? '确认销售接续单' : '确认采购下单' }}</button></div>
                </div>
                <label>采购低于 MOQ 时的例外原因<input v-model="operationalMoqReason" /></label>
                <label v-if="operationalStatus.status === 'drafts_created'">撤销原因<input v-model="operationalReviewNote" /></label>
                <button v-if="operationalStatus.status === 'drafts_created'" class="takeover-secondary" :disabled="saving || !operationalReviewNote.trim()" @click="operationalAction('operational-reverse')">撤销未使用的接续草稿</button>
              </template>
            </details>
            <div class="takeover-actions"><label>追溯类型<select v-model="correction.kind"><option value="late_fact">迟到记录</option><option value="correction">审计更正</option><option value="voucher_added">补交凭证</option></select></label><label>实际发生日期<input v-model="correction.occurred_at" type="date" /></label></div>
            <label>更正原因<textarea v-model="correction.reason" rows="2" /></label>
            <label>新增资料（JSON）<textarea v-model="correction.details" rows="3" placeholder='例如：{"source_record_id":"LATE-1","voucher_reference":"VCH-1"}' /></label>
            <button class="takeover-secondary" :disabled="saving || !correction.reason || !correction.details" @click="submitCorrection">提交追溯更正申请</button>
          </div>
        </article>

        <section class="takeover-audit"><h4>申请与操作记录</h4><ol><li v-for="event in selected.events" :key="event.id"><span>{{ eventNames[event.event_type] || event.event_type }}</span><small>{{ event.actor_label || '未记录实名操作人' }} · {{ new Date(event.created_at).toLocaleString('zh-CN') }}</small><p v-if="['late_fact_submitted','correction_submitted','voucher_added_submitted'].includes(event.event_type)">发生日期：{{ event.details?.occurred_at || '未提供' }} · {{ event.details?.reason }}</p><div v-if="canReview && ['late_fact_submitted','correction_submitted','voucher_added_submitted'].includes(event.event_type) && !selectedGroup.verified_correction_ids?.includes(event.id)" class="takeover-actions"><button class="takeover-secondary" :disabled="saving || !note.trim()" @click="reviewCorrection(event,'reject')">退回更正</button><button class="takeover-primary" :disabled="saving || !note.trim()" @click="reviewCorrection(event,'approve')">核实并保留更正轨迹</button></div></li></ol></section>
      </section>
      <section v-else class="takeover-detail panel takeover-empty">选择一条申请，查看分组核验结果。</section>
    </div>
  </main>
</template>

<style scoped>
.takeover-page{display:grid;gap:16px;min-width:0;color:#243b33}.takeover-intro,.takeover-upload,.takeover-list,.takeover-detail{background:#fff;border:1px solid #dfe7e2;border-radius:13px;padding:20px;min-width:0}.takeover-intro{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.takeover-intro h2{margin:0;font-size:22px}.takeover-intro p:not(.takeover-eyebrow){margin:6px 0 0;color:#6c7d74}.takeover-eyebrow{margin:0 0 5px;color:#788b80;font-size:12px;letter-spacing:.08em}.takeover-lock{display:flex;align-items:center;gap:7px;padding:8px 11px;border-radius:8px;background:#f1f6f2;color:#426657;font-size:12px;white-space:nowrap}.takeover-columns{display:grid;grid-template-columns:minmax(230px,.72fr) minmax(0,2fr);gap:16px;align-items:start}.takeover-list{position:sticky;top:98px;display:grid;gap:8px}.takeover-list-head,.takeover-detail-head,.takeover-section-title,.takeover-group-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.takeover-list h3,.takeover-section-title h3{display:flex;align-items:center;gap:8px;margin:0;font-size:16px}.takeover-section-title p,.takeover-detail-head p,.takeover-group-head p{margin:5px 0 0;color:#74847c;font-size:13px}.takeover-upload-row{display:flex;gap:10px;margin-top:14px}.takeover-file{display:flex;align-items:center;justify-content:space-between;gap:12px;flex:1;min-width:0;min-height:42px;padding:8px 11px;border:1px dashed #a8beb2;border-radius:8px;color:#566d61}.takeover-file span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.takeover-file input{max-width:190px;font-size:12px}.takeover-primary,.takeover-secondary,.takeover-text-button{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid #1c5c4c;border-radius:8px;padding:9px 13px;background:#1c5c4c;color:#fff;font-weight:700;cursor:pointer}.takeover-secondary{border-color:#cddbd3;background:#fff;color:#315c4a}.takeover-text-button{border:0;background:transparent;color:#456b5a;padding:7px}.takeover-primary:disabled,.takeover-secondary:disabled,.takeover-text-button:disabled{opacity:.55;cursor:not-allowed}.takeover-caution{display:flex;align-items:flex-start;gap:7px;margin:12px 0 0;padding:10px 12px;border-radius:8px;background:#f1f6f3;color:#4c6d5b;font-size:13px;line-height:1.6}.takeover-caution svg{flex:none;margin-top:2px}.takeover-alert{display:flex;gap:8px;align-items:center;padding:11px 13px;border:1px solid #e8c2b9;border-radius:8px;background:#fff7f5;color:#8b3b30;overflow-wrap:anywhere}.takeover-list-item{display:grid;gap:4px;width:100%;padding:11px;border:1px solid #e6ece8;border-radius:8px;background:#fff;text-align:left;color:#385246;cursor:pointer}.takeover-list-item.active{border-color:#71a18b;background:#f2f8f4}.takeover-list-item strong{overflow-wrap:anywhere}.takeover-list-item span,.takeover-list-item small{color:#718078;font-size:12px}.takeover-empty{padding:18px;color:#718078}.takeover-detail{display:grid;gap:14px}.takeover-detail-head h3{margin:2px 0 0;font-size:18px;overflow-wrap:anywhere}.takeover-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.takeover-summary span{padding:9px 11px;border:1px solid #e7ede9;border-radius:8px;color:#708078;font-size:12px}.takeover-summary strong{display:block;margin-top:2px;color:#244c3a;font-size:16px}.takeover-groups{display:flex;flex-wrap:wrap;gap:8px}.takeover-group-tab{display:flex;align-items:center;gap:8px;border:1px solid #dce7df;border-radius:8px;background:#fff;padding:8px 10px;color:#355c48;cursor:pointer}.takeover-group-tab.active{background:#eaf4ee;border-color:#94b9a4}.takeover-group-tab em,.takeover-status{font-style:normal;color:#718078;font-size:12px}.takeover-group-detail{display:grid;gap:10px;padding-top:13px;border-top:1px solid #e7ece8}.takeover-group-head h4,.takeover-remainder h4,.takeover-execution h4,.takeover-audit h4{margin:0;font-size:15px}.takeover-evidence{margin:0;color:#607669;overflow-wrap:anywhere;font-size:13px}.takeover-result-row{padding:9px 11px;border-left:3px solid #7bac8d;background:#f6faf7;border-radius:0 7px 7px 0}.takeover-result-row strong{font-size:13px}.takeover-result-row ul{margin:5px 0 0;padding-left:19px;color:#596e63;font-size:12px;line-height:1.55}.takeover-result-row.state-阻断{border-color:#bd5146;background:#fff7f5}.takeover-result-row.state-待人工核实{border-color:#d69642;background:#fffbf3}.takeover-resolution{padding:11px;border:1px solid #e2e9e4;border-radius:8px}.takeover-resolution summary{cursor:pointer;font-weight:700;color:#365d49}.takeover-resolution p{margin:7px 0;color:#738178;font-size:12px}.takeover-form-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:10px 0}.takeover-page label{display:grid;gap:5px;color:#5d7164;font-size:12px}.takeover-page input,.takeover-page select,.takeover-page textarea{width:100%;min-width:0;border:1px solid #d4dfd8;border-radius:7px;padding:8px;background:#fff;color:#283f35}.takeover-form-grid .wide{grid-column:1/-1}.takeover-remainder,.takeover-execution,.takeover-review{display:grid;gap:9px;padding:12px;border:1px solid #e3eae5;border-radius:9px;background:#fbfcfb}.takeover-remainder>p,.takeover-execution>p{margin:0;color:#6e7f76;font-size:12px}.takeover-remainder-item{display:grid;grid-template-columns:1fr auto;gap:4px;padding-top:8px;border-top:1px solid #e9eeeb}.takeover-remainder-item small{grid-column:1/-1;color:#61766b;overflow-wrap:anywhere}.takeover-checkbox{display:flex!important;align-items:center;grid-template-columns:auto 1fr}.takeover-checkbox input{width:auto}.takeover-actions{display:flex;align-items:center;flex-wrap:wrap;gap:8px}.takeover-actions label{min-width:150px}.takeover-audit{border-top:1px solid #e5ebe7;padding-top:12px}.takeover-audit ol{display:grid;gap:7px;margin:9px 0 0;padding-left:20px}.takeover-audit li{padding-left:2px;color:#41644f}.takeover-audit li small{display:block;color:#7a8981;font-size:11px}.takeover-audit li span{font-size:13px}
.takeover-remainder-item > .wide{grid-column:1/-1;min-width:0}
.takeover-intro-actions{display:grid;justify-items:end;gap:8px}.takeover-preflight-link{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:7px 11px;border:1px solid #cddbd3;border-radius:8px;background:#fff;color:#315c4a;font-size:13px;font-weight:700;text-decoration:none}.takeover-preflight-link:hover{background:#f3f8f5;border-color:#9ebca9}
@media(max-width:900px){.takeover-columns{grid-template-columns:1fr}.takeover-list{position:static;grid-template-columns:repeat(2,minmax(0,1fr))}.takeover-list-head,.takeover-empty{grid-column:1/-1}}
@media(max-width:600px){.takeover-intro{display:grid;padding:16px}.takeover-intro-actions{justify-items:start;width:100%}.takeover-lock{white-space:normal;width:max-content;max-width:100%}.takeover-upload,.takeover-list,.takeover-detail{padding:14px}.takeover-upload-row{display:grid}.takeover-file{align-items:flex-start;flex-direction:column}.takeover-file input{max-width:100%;width:100%}.takeover-list{grid-template-columns:1fr}.takeover-detail-head{display:grid}.takeover-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.takeover-form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.takeover-actions>*{flex:1}.takeover-actions button{min-height:40px}.takeover-group-tab{max-width:100%;flex-wrap:wrap}}
</style>
