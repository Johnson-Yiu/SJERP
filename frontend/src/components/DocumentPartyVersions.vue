<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { useAccessControl } from '../accessControl'
import { formatApiError } from '../utils/apiErrors'
import PartyReplacementForm from './PartyReplacementForm.vue'
import PartyDetailsFields from './PartyDetailsFields.vue'
import PartyDetailsChanges from './PartyDetailsChanges.vue'

const props = defineProps({ kind: { type: String, required: true }, id: { type: [String, Number], required: true }, sourcePartyId: { type: [String, Number], default: null } })
const emit = defineEmits(['updated'])
const { can } = useAccessControl()
const module = computed(() => props.kind === 'order' ? 'orders' : 'purchases')
const endpoint = computed(() => `/${props.kind === 'order' ? 'orders' : 'purchase-orders'}/${props.id}/party-change/`)
const fields = computed(() => [['name', '名称'], ...(props.kind === 'order' ? [['country', '国家 / 地区']] : []), ['address', '地址'], ['contact', '联系人'], ['phone', '电话'], ['email', '邮箱']])
const open = ref(false), loading = ref(false), busy = ref(false), data = ref(null), error = ref('')
const draft = ref({}), reason = ref(''), evidence = ref(''), legal = ref(false), notes = ref({})
const replacementOpen = ref(false), replacementCreateId = ref(null)
let generation = 0
async function load() {
  const current = ++generation
  loading.value = true; error.value = ''
  try {
    const response = await api.get(endpoint.value)
    if (current !== generation) return
    data.value = response.data; draft.value = { ...response.data.baseline.snapshot }
  } catch (err) { if (current === generation) { data.value = null; error.value = formatApiError(err?.response?.data) || '主体版本读取失败，请重试。' } }
  finally { if (current === generation) loading.value = false }
}
watch(() => [props.kind, props.id], () => { ++generation; open.value = false; data.value = null; error.value = '' })
async function action(operation, request = null) {
  if (busy.value || !data.value?.current_user_id || !can(module.value, 'update')) return
  let body
  if (operation === 'propose') {
    if (!legal.value || !reason.value.trim() || !evidence.value.trim()) { error.value = '请确认法律主体未变，并填写原因和依据。'; return }
    body = { expected_base_fingerprint: data.value.baseline.fingerprint, proposed_snapshot: { ...draft.value }, change_type: 'correction', reason: reason.value.trim(), evidence: evidence.value.trim(), source_trust: 'unverified' }
  } else {
    const note = (notes.value[request.id] || '').trim()
    if (operation !== 'apply' && !note) { error.value = '请填写处理原因或审批意见。'; return }
    body = operation === 'approve' ? { expected_content_fingerprint: request.content_fingerprint, note } : operation === 'apply' ? {} : { note }
  }
  const current = generation, url = operation === 'propose' ? endpoint.value : `${endpoint.value}${request.id}/${operation}/`
  busy.value = true; error.value = ''
  try { await api.post(url, body); if (current === generation) { reason.value = ''; evidence.value = ''; legal.value = false; notes.value = {}; await load(); if (operation === 'apply' && data.value) emit('updated', data.value.baseline.snapshot) } }
  catch (err) { if (current === generation) error.value = formatApiError(err?.response?.data) || '操作失败，请重试。' }
  finally { if (current === generation || !loading.value) busy.value = false }
}
function textValue(value) { return value == null || value === '' ? '未记录' : value }
function proposedTextValue(value) { return value == null ? '未知' : value === '' ? '已留空' : value }
function canReview(row) { return row.initiator_id && String(row.initiator_id) !== String(data.value?.current_user_id) }
</script>

<template>
  <section class="document-party-versions">
    <button type="button" class="btn btn-secondary" @click="open = !open; if (open) load()">{{ open ? '收起主体版本' : '查看主体版本与更正' }}</button>
    <template v-if="open">
      <p>原始快照保留；主体更正和替换均须经另一认证账号批准。更换法律主体将新建关联单据。</p>
      <p v-if="loading" role="status">正在读取主体版本…</p>
      <p v-if="error" role="alert" class="party-error">{{ error }}</p>
      <button v-if="error && !data" type="button" class="btn btn-secondary" @click="load">重试</button>
      <template v-if="data">
        <h4>当前有效主体资料</h4>
        <dl class="party-grid"><template v-for="[key, label] in fields" :key="key"><dt>{{ label }}</dt><dd>{{ textValue(data.baseline.snapshot[key]) }}</dd></template></dl>
        <PartyDetailsFields v-if="data.baseline.snapshot.party_details" :model-value="data.baseline.snapshot.party_details" />
        <p>历史未记录的字段不能自动补填；来源未核验不等于已核实。</p>
        <template v-if="can(module, 'update')">
          <h4>申请同主体更正</h4>
          <label v-for="[key, label] in fields" :key="key" class="party-label">{{ label }}<input v-model="draft[key]" :disabled="busy || !data.current_user_id" /></label>
          <template v-if="draft.party_details"><h4>双方资料建议值</h4><PartyDetailsFields v-model="draft.party_details" :editable="!busy && !!data.current_user_id" preserve-unknown /></template>
          <label class="party-label">原因<textarea v-model="reason" :disabled="busy" /></label>
          <label class="party-label">依据<textarea v-model="evidence" :disabled="busy" /></label>
          <label><input v-model="legal" type="checkbox" :disabled="busy" /> 已核对依据，确认法律主体未变</label>
          <button type="button" class="btn btn-primary" :disabled="busy || !data.current_user_id" @click="action('propose')">提交更正申请</button>
          <button type="button" class="btn btn-secondary" :disabled="busy || !data.current_user_id" @click="replacementOpen = !replacementOpen">{{ replacementOpen ? '收起替换申请' : '申请更换法律主体' }}</button>
          <PartyReplacementForm v-if="replacementOpen" :kind="kind" mode="propose" :source-id="id" :source-party-id="sourcePartyId" :baseline="data.baseline" @completed="replacementOpen = false; load()" />
        </template>
        <h4>申请与版本记录</h4>
        <p v-if="!data.requests.length">暂无主体更正申请。</p>
        <article v-for="row in data.requests" :key="row.id" class="party-row">
          <strong>申请 #{{ row.id }} · {{ row.status === 'applied' && row.change_type === 'replacement' ? '已生成关联草稿' : (({pending:'待审批', approved:'已批准', applied:'已生效', rejected:'已拒绝', withdrawn:'已撤回', invalidated:'已失效'})[row.status] || '状态未知') }}</strong>
          <p>申请账号 ID：{{ row.initiator_id }} · {{ row.reason }} · 依据：{{ row.evidence }}</p>
          <dl class="party-grid"><template v-for="[key, label] in fields" :key="key"><dt>{{ label }}</dt><dd>{{ textValue(row.base_snapshot?.[key]) }} → {{ proposedTextValue(row.proposed_snapshot?.[key]) }}</dd></template></dl>
          <PartyDetailsChanges :before="row.base_snapshot?.party_details" :after="row.proposed_snapshot?.party_details" />
          <p v-if="row.approval">审批账号 ID：{{ row.approval.approver_id }} · {{ row.approval.note }}</p>
          <p v-if="row.terminal_event">处理账号 ID：{{ row.terminal_event.actor_id }} · {{ row.terminal_event.note }}</p>
          <p v-if="row.document_version">有效版本 #{{ row.document_version.version_no }} · 操作账号 ID：{{ row.document_version.applied_by_id }}</p>
          <template v-if="can(module, 'update') && ['pending', 'approved'].includes(row.status)">
            <label class="party-label">审批意见 / 处理原因<input v-model="notes[row.id]" :disabled="busy" /></label>
            <button v-if="row.status === 'pending' && canReview(row)" type="button" class="btn btn-secondary" :disabled="busy" @click="action('approve', row)">{{ row.change_type === 'replacement' ? '批准主体替换' : '批准更正' }}</button>
            <button v-if="row.status === 'pending' && canReview(row)" type="button" class="btn btn-secondary" :disabled="busy" @click="action('reject', row)">拒绝申请</button>
            <button v-if="row.status === 'pending' && !canReview(row)" type="button" class="btn btn-secondary" :disabled="busy" @click="action('withdraw', row)">撤回申请</button>
            <button v-if="row.status === 'approved' && row.change_type !== 'replacement'" type="button" class="btn btn-primary" :disabled="busy" @click="action('apply', row)">生效主体更正</button>
            <button v-if="row.status === 'approved' && row.change_type === 'replacement' && row.replacement_target && can(module, 'create')" type="button" class="btn btn-primary" :disabled="busy" @click="replacementCreateId = replacementCreateId === row.id ? null : row.id">填写关联新单</button>
            <PartyReplacementForm v-if="replacementCreateId === row.id && row.status === 'approved' && row.change_type === 'replacement'" :kind="kind" mode="create" :source-id="id" :request="row" @completed="replacementCreateId = null; load()" />
            <button type="button" class="btn btn-secondary" :disabled="busy" @click="action('invalidate', row)">标记失效</button>
          </template>
          <p v-if="row.replacement_result">已生成关联草稿 ID：{{ kind === 'order' ? row.replacement_result.result_order_id : row.replacement_result.result_purchase_order_id }} <a :href="`/${kind === 'order' ? 'orders' : 'purchase-orders'}?detail=${kind === 'order' ? row.replacement_result.result_order_id : row.replacement_result.result_purchase_order_id}`">查看关联单据</a></p>
        </article>
      </template>
    </template>
  </section>
</template>

<style scoped>
.document-party-versions{padding:16px;border:1px solid #dce6df;border-radius:10px;overflow-wrap:anywhere}.document-party-versions p{margin:10px 0}.document-party-versions h4{margin:18px 0 10px}.party-grid{display:grid;grid-template-columns:minmax(90px,.35fr) minmax(0,1fr);gap:8px;margin:8px 0}.party-grid dd{margin:0}.party-label{display:grid;gap:4px;margin:9px 0}.party-label input,.party-label textarea{width:100%;padding:8px;border:1px solid #b9c9c1;border-radius:6px}.party-label textarea{min-height:60px}.party-row{border-top:1px solid #dce6df;padding:14px 0}.party-row button{margin:4px 6px 4px 0}.party-error{color:#a12e2e}
</style>
