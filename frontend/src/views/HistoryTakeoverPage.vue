<script setup>
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Check, CircleHelp, FileUp, History, RotateCcw, ShieldCheck } from 'lucide-vue-next'
import { api } from '../api'
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

const groups = computed(() => selected.value?.groups || [])
const statuses = {
  submitted: '待审核', in_review: '审核中', rejected: '已拒绝', partially_approved: '部分通过',
  approved: '已批准', executed: '已执行', withdrawn: '已撤回', pending: '待审核', blocked: '存在阻断',
  needs_reapproval: '需重新审核',
}
const eventNames = {
  application_submitted: '已提交申请', group_submitted: '关联组已提交', group_approved: '管理员已批准',
  group_rejected: '管理员已拒绝', group_executed: '已承接历史记录', group_withdrawn: '申请已撤回',
  master_resolution_added: '已登记主档关联', execution_stopped_reapproval_required: '执行前发现资料变化',
  late_fact_submitted: '已提交迟到记录', correction_submitted: '已提交追溯更正', voucher_added_submitted: '已补交凭证',
  correction_reviewed: '更正审核完成', duplicate_submission_reused: '重复提交已复用原申请',
}
const sourceRows = computed(() => selected.value?.groups?.find(group => group.id === selectedGroupId.value)?.source_rows || {})
const selectedGroupId = ref(null)
const selectedGroup = computed(() => groups.value.find(group => group.id === selectedGroupId.value) || groups.value[0] || null)
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
        <p>申请、核实和逐组承接；预检通过不代表已批准或已迁移。</p>
      </div>
      <div class="takeover-lock"><ShieldCheck :size="19" /><span>需要相关业务完整查看权限</span></div>
    </header>

    <section v-if="!canApply" class="takeover-alert" role="alert"><AlertTriangle :size="18" />当前账号缺少历史承接申请权限或相关业务查看范围。</section>
    <section v-if="error" class="takeover-alert" role="alert"><AlertTriangle :size="18" />{{ error }}</section>

    <section class="takeover-upload panel">
      <div class="takeover-section-title"><div><h3><FileUp :size="18" />提交承接申请</h3><p>来源行和凭证引用会纳入申请记录。</p></div><button class="takeover-secondary" :disabled="templateLoading" @click="downloadTemplate">{{ templateLoading ? '正在准备…' : '下载承接模板' }}</button></div>
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
        <p v-else-if="!applications.length" class="takeover-empty">还没有历史承接申请</p>
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
        <p class="takeover-caution">预检状态：{{ selected.preflight_summary?.overall_status || '未完成' }}。审核前须核实真实性、来源凭证、主档依赖和关联冲突。</p>

        <div class="takeover-groups">
          <button v-for="group in selected.groups" :key="group.id" class="takeover-group-tab" :class="{ active: selectedGroupId === group.id }" @click="selectedGroupId = group.id">
            {{ group.source_group_id }} <em>{{ statuses[group.status] || group.status }}</em>
          </button>
        </div>

        <article v-if="selectedGroup" class="takeover-group-detail">
          <div class="takeover-group-head"><div><h4>关联组 {{ selectedGroup.source_group_id }}</h4><p>{{ selectedGroup.source_system }} · {{ selectedGroup.coverage_status }} · {{ selectedGroup.truth_status }}</p></div><span class="takeover-status">{{ statuses[selectedGroup.status] || selectedGroup.status }}</span></div>
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
            <p>仅展示核实履约后的剩余数量；正式订单分配尚未接通。</p>
            <div v-for="order in openOrders" :key="order.source_record_id" class="takeover-remainder-item">
              <strong>{{ order.source_document_no }}</strong><span>{{ order.source_lifecycle_state }}</span>
              <small v-for="line in order.lines" :key="line.source_line_id">行 {{ line.source_line_id }}：已履约 {{ line.verified_net_fulfilled_quantity_base }} / {{ line.ordered_quantity_base }}，剩余 {{ line.remaining_quantity_base }} {{ line.unit_snapshot }}</small>
            </div>
          </div>

          <div v-if="canReview && selectedGroup.status !== 'executed' && !['rejected','withdrawn'].includes(selectedGroup.status)" class="takeover-review">
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
            <p>正式资金、库存流水、履约记录、采购成本分配均为 0；三类交接状态均为 not_connected。</p>
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
@media(max-width:900px){.takeover-columns{grid-template-columns:1fr}.takeover-list{position:static;grid-template-columns:repeat(2,minmax(0,1fr))}.takeover-list-head,.takeover-empty{grid-column:1/-1}}
@media(max-width:600px){.takeover-intro{display:grid;padding:16px}.takeover-lock{white-space:normal;width:max-content;max-width:100%}.takeover-upload,.takeover-list,.takeover-detail{padding:14px}.takeover-upload-row{display:grid}.takeover-file{align-items:flex-start;flex-direction:column}.takeover-file input{max-width:100%;width:100%}.takeover-list{grid-template-columns:1fr}.takeover-detail-head{display:grid}.takeover-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.takeover-form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.takeover-actions>*{flex:1}.takeover-actions button{min-height:40px}.takeover-group-tab{max-width:100%;flex-wrap:wrap}}
</style>
