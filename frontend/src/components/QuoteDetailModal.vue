<script setup>
import { compactDecimalInput } from '../utils/decimalInput'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { routeLocationKey, routerKey } from 'vue-router'
import { AlertTriangle, ArrowLeft, ArrowRight, Download, Eye, FileText, GitBranch, Pencil, Plus, ShoppingCart, StickyNote, X } from 'lucide-vue-next'
import { api, downloadQuoteExport } from '../api'
import { confirmDialog } from '../dialogs'
import QuotePreviewModal from './QuotePreviewModal.vue'
import RichTextEditor from './RichTextEditor.vue'
import OperationLogPanel from './OperationLogPanel.vue'
import { useDetailTab } from '../utils/useDetailTab'
import { useAccessControl } from '../accessControl'

const props = defineProps({ id: { type: [Number, String], required: true }, refreshKey: { type: Number, default: 0 } })
const emit = defineEmits(['close', 'revise', 'status-updated', 'create-order', 'open-order'])
const { can } = useAccessControl()
const workbench = ref(null)
const activeTab = useDetailTab('/quotes', ['overview', 'items', 'lineage', 'orders', 'notes', 'operation_logs'], 'overview', () => props.id)
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

const quote = computed(() => workbench.value?.quote)
const canCreateOrder = computed(() => can('orders', 'create') && ['draft', 'sent', 'accepted'].includes(quote.value?.status))
const tabs = computed(() => [
  ['overview', '概览'], ['items', `报价明细 (${quote.value?.items?.length || 0})`],
  ['lineage', `版本谱系 (${workbench.value?.revisions?.length || 0})`], ['orders', `订单 (${workbench.value?.orders?.length || 0})`],
  ['notes', `重要备注 (${workbench.value?.important_notes?.length || 0})`],
  ['operation_logs', `操作日志 (${operationLogs.value.length})`],
])
const subtotal = computed(() => (quote.value?.items || []).reduce((sum, item) => sum + Number(item.amount || 0), 0))
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
function revisionLabel(row) { return row.revision_no ? `迭代版 -${row.revision_no}` : '原始报价' }
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

onMounted(load)
watch(() => props.id, load)
watch(() => props.refreshKey, () => load(quote.value?.id || props.id))
</script>

<template>
  <div class="modal-backdrop detail-backdrop" @mousedown.self="emit('close')">
    <article class="detail-modal quote-workbench" role="dialog" aria-modal="true" aria-label="报价工作台">
      <div v-if="loading" class="detail-loading"><div class="spinner" /> 正在加载报价工作台…</div>
      <div v-else-if="error" class="detail-error"><AlertTriangle :size="27" /><strong>加载失败</strong><p>{{ error }}</p><button class="btn btn-secondary" @click="load()">重试</button></div>
      <template v-else>
        <header class="detail-header">
          <div class="detail-nav"><div class="detail-nav-start"><button class="detail-close" aria-label="关闭报价详情" @click="emit('close')"><X :size="18" /> <span>关闭</span></button><button v-if="versionHistory.length" class="detail-back" @click="returnToPreviousVersion"><ArrowLeft :size="18" /> 返回上一版本</button><span v-else>报价工作台 · {{ workbench.root_quote_no }}</span></div></div>
          <div class="detail-identity"><div><p class="detail-subtitle">{{ quote.customer_name }} · {{ revisionLabel(quote) }}</p><h2>{{ quote.quote_no }}</h2><small>原始报价：{{ workbench.root_quote_no }}</small></div><span class="detail-badge">{{ quote.status_display }}</span></div>
          <div v-if="can('quotes', 'update') && (quote.status === 'draft' || quote.status === 'sent')" class="quote-status-actions" aria-label="报价状态操作">
            <button v-if="quote.status === 'draft'" class="btn btn-secondary" :disabled="statusSaving" @click="changeStatus('mark-sent')">标记已发送</button>
            <button class="btn btn-secondary" :disabled="statusSaving" @click="changeStatus('accept')">客户接受</button>
            <button class="btn btn-secondary" :disabled="statusSaving" @click="changeStatus('reject')">客户拒绝</button>
            <button v-if="quote.status === 'sent'" class="btn btn-secondary" :disabled="statusSaving" @click="changeStatus('expire')">标记过期</button>
          </div>
          <div class="workbench-actions"><button v-if="can('quotes', 'update')" class="btn btn-secondary" @click="emit('revise', quote)"><Pencil :size="14" /> 创建修订版</button><button class="btn btn-secondary" @click="openPreview()"><Eye :size="15" /> 预览 PI</button><button v-if="can('quotes', 'export')" class="btn quote-utility" @click="exportQuote"><Download :size="15" /> 导出 Excel</button><button v-if="canCreateOrder" class="btn btn-primary transfer-order" @click="createOrder"><ShoppingCart :size="15" /> 转为订单</button></div>
          <p v-if="!canCreateOrder" class="quote-order-unavailable">报价已拒绝或过期，请先创建修订版。</p>
          <p v-if="actionError" class="workbench-error">{{ actionError }}</p>
        </header>
        <main class="detail-content">
          <nav class="workbench-tabs" aria-label="报价详情分页"><button v-for="tab in tabs" :key="tab[0]" :class="{ active: activeTab === tab[0] }" @click="activeTab = tab[0]">{{ tab[1] }}</button></nav>

          <section v-if="activeTab === 'overview'" class="workbench-grid">
            <div class="workbench-card summary-card"><h3>报价概览</h3><div class="summary-metrics"><div><small>报价总额</small><strong>{{ quote.currency }} {{ money(quote.total_amount) }}</strong></div><div><small>有效期至</small><strong>{{ quote.valid_until || '—' }}</strong></div><div><small>商品明细</small><strong>{{ quote.items.length }} 项</strong></div></div></div>
            <div class="workbench-card"><h3>基础信息</h3><dl class="data-list"><dt>报价日期</dt><dd>{{ quote.quote_date }}</dd><dt>币种 / 汇率</dt><dd>{{ quote.currency }} / {{ compactDecimalInput(quote.exchange_rate) }}</dd><dt>收件人</dt><dd>{{ quote.recipient_name || '—' }}</dd><dt>条款备注</dt><dd>{{ quote.notes || '—' }}</dd></dl></div>
            <div class="workbench-card version-summary"><div class="section-heading"><div><h3><GitBranch :size="16" /> 版本摘要</h3><p>共 {{ workbench.revisions.length }} 个版本，当前为 {{ revisionLabel(quote) }}。</p></div><button class="text-btn" @click="activeTab = 'lineage'">查看版本谱系</button></div><div class="summary-version-list"><article v-for="row in revisionTreeRows" :key="row.id" :class="{ current: row.id === quote.id, child: row.depth }" :style="{ '--depth': row.depth }"><div class="version-row-main"><span v-if="row.depth" class="version-tree-connector"><ArrowRight :size="13" /></span><strong>{{ row.quote_no }}</strong><span>{{ revisionLabel(row) }}</span><span>{{ dateTime(row.created_at) }}</span><span class="status" :class="row.status">{{ row.status_display }}</span><em v-if="row.revision_summary">修改：{{ row.revision_summary }}</em></div><div class="version-row-side"><b>{{ row.currency }} {{ money(row.total_amount) }}</b><div class="summary-version-actions"><button class="text-btn" @click="openPreview(row.id)">预览 PI</button><button class="text-btn" :disabled="row.id === quote.id" @click="changeVersion(row)">查看详情</button></div></div></article></div></div>
            <div class="workbench-card"><h3><ShoppingCart :size="16" /> 订单摘要</h3><p>已生成 {{ workbench.orders.length }} 张订单。</p><button class="text-btn" @click="activeTab = 'orders'">查看关联订单</button></div>
          </section>

          <section v-else-if="activeTab === 'items'" class="workbench-card"><div class="section-heading"><div><h3>报价明细</h3><p>当前版本的商品明细。</p></div><strong>{{ quote.currency }} {{ money(quote.total_amount) }}</strong></div><div class="workbench-table-wrap"><table class="workbench-table items-table"><thead><tr><th>Model</th><th>内部名称 / SKU Code</th><th>Description 快照</th><th>数量</th><th>单位</th><th>单价</th><th>小计</th></tr></thead><tbody><tr v-for="item in quote.items" :key="item.id"><td>{{ item.sales_model_snapshot || item.model || '未设置' }}</td><td>{{ item.display_name_snapshot || item.product_name }}<small>{{ item.sku_code }}</small></td><td>{{ item.description_snapshot || item.description || '—' }}</td><td>{{ item.trade_quantity ?? item.quantity }}<small v-if="item.trade_unit">基础数量：{{ item.quantity }} {{ item.trade_snapshot.base_unit }}</small></td><td>{{ item.trade_snapshot?.unit || item.unit }}</td><td>{{ money(item.trade_unit_price ?? item.unit_price) }}</td><td>{{ money(item.amount) }}</td></tr></tbody></table></div><div class="quote-totals">商品小计 {{ money(subtotal) }}　运费 {{ money(quote.shipping_fee) }}　折扣 -{{ money(quote.discount) }}　<strong>合计 {{ quote.currency }} {{ money(quote.total_amount) }}</strong></div></section>

          <section v-else-if="activeTab === 'lineage'" class="workbench-card"><div class="section-heading"><div><h3>版本谱系</h3><p>查看各修订版之间的关系。</p></div></div><ol class="lineage-list"><li v-for="row in revisionTreeRows" :key="row.id" :class="{ current: row.id === quote.id, child: row.depth }" :style="{ '--depth': row.depth }"><span class="lineage-connector"><span v-if="row.depth" class="version-tree-connector"><ArrowRight :size="13" /></span><i v-else class="lineage-dot" /></span><div class="lineage-row-main"><strong>{{ row.quote_no }}</strong><span>{{ revisionLabel(row) }}</span><span>{{ dateTime(row.created_at) }}</span><span class="status" :class="row.status">{{ row.status_display }}</span><em v-if="row.revision_summary">修改：{{ row.revision_summary }}</em></div><b>{{ row.currency }} {{ money(row.total_amount) }}</b><div class="lineage-actions"><button class="mini-btn" @click="openPreview(row.id)">预览 PI</button><button class="mini-btn" :disabled="row.id === quote.id" @click="changeVersion(row)">查看详情</button></div></li></ol></section>

          <section v-else-if="activeTab === 'orders'" class="workbench-card"><div class="section-heading"><div><h3>订单</h3><p>查看该报价及修订版生成的订单。</p></div></div><p v-if="!canCreateOrder" class="quote-order-unavailable">报价已拒绝或过期，请先创建修订版。</p><div v-if="!workbench.orders.length" class="workbench-empty"><ShoppingCart :size="28" /><strong>尚未转为订单</strong><p>转为订单后可编辑订单草稿。</p></div><div v-else class="order-list"><article v-for="order in workbench.orders" :key="order.id" class="order-card"><div><strong>{{ order.order_no }}</strong><small>来源报价：{{ order.source_quote_no || '—' }} · {{ order.order_date }}</small></div><div><span class="status" :class="order.status">{{ order.status_display }}</span><b>{{ order.currency }} {{ money(order.total_amount) }}</b></div><div class="order-actions"><button class="text-btn" @click="openPreview(order.quote)">预览来源 PI</button><button class="text-btn" @click="emit('open-order', order.id)">查看订单</button></div></article></div></section>

          <section v-else-if="activeTab === 'notes'" class="workbench-card notes-panel"><div class="note-caution"><AlertTriangle :size="18" /><p>备注可能已过时或不适用于最终订单，请核对来源版本和沟通记录。</p></div><div class="section-heading"><div><h3><StickyNote :size="16" /> 重要备注</h3><p>备注关联当前报价版本。</p></div><button v-if="can('quotes', 'update') && !noteEditorOpen" class="btn btn-primary" @click="noteEditorOpen = true"><Plus :size="15" /> 新增备注</button></div><template v-if="noteEditorOpen && can('quotes', 'update')"><RichTextEditor v-model="noteContent" /><div class="note-create"><button class="btn btn-secondary" @click="closeNoteEditor">取消</button><button class="btn btn-primary" :disabled="noteSaving || isRichTextEmpty(noteContent)" @click="createNote">{{ noteSaving ? '保存中…' : '保存重要备注' }}</button></div></template><div v-if="!workbench.important_notes.length" class="workbench-empty"><StickyNote :size="28" /><strong>暂无重要备注</strong></div><article v-for="note in workbench.important_notes" :key="note.id" class="important-note" :class="{ inactive: !note.is_active }"><header><div><strong>{{ note.is_active ? '有效备注' : '不再生效' }}</strong><small>备注于：{{ note.source_quote_no }}（{{ revisionLabel({ revision_no: note.source_revision_no }) }}） · {{ note.created_by_name }} · {{ dateTime(note.created_at) }}</small><small v-if="note.deactivated_at" class="note-deactivation">最近失效：{{ dateTime(note.deactivated_at) }} · {{ note.deactivated_by_name || '系统' }}</small><small v-else-if="!note.is_active" class="note-deactivation">最近失效：历史记录未保存操作时间和操作人</small></div><button v-if="can('quotes', 'update') && note.is_active" class="text-btn danger" @click="deactivateNote(note)">标记不再生效</button><button v-else-if="can('quotes', 'update')" class="text-btn restore" @click="restoreNote(note)">恢复生效</button></header><div class="important-note-content" v-html="note.content" /></article></section>

          <OperationLogPanel v-else :logs="operationLogs" :loading="operationLogsLoading" :enabled="auditEnabled" />
        </main>
      </template>
    </article>
    <QuotePreviewModal v-if="preview" :draft="preview" saved @close="preview = null" />
  </div>
</template>

<style scoped>
.detail-backdrop{inset:0 0 0 248px;z-index:25;place-items:stretch end;padding:0;background:#0b221d66;backdrop-filter:blur(2px)}.detail-modal{height:100vh;width:min(1100px,100%);background:#f6f8f5;box-shadow:-24px 0 70px #06191452;overflow:auto;overscroll-behavior:contain}.detail-loading,.detail-error{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#71817b}.detail-error strong{color:#9d4444}.detail-error p{font-size:var(--text-body)}.detail-header{position:relative;overflow:hidden;padding:20px 28px 24px;background:#123c36;color:#fff}.detail-header:after{position:absolute;top:-140px;right:-80px;width:300px;height:300px;border:60px solid #ffffff08;border-radius:50%;content:''}.detail-nav,.detail-identity,.workbench-actions,.workbench-error{position:relative;z-index:1}.detail-nav,.detail-nav-start{display:flex;align-items:center}.detail-nav{justify-content:space-between;color:#91b6aa;font-size:var(--text-body);letter-spacing:.12em;text-transform:uppercase}.detail-nav-start{gap:10px}.detail-actions{display:flex;align-items:center;gap:8px}.detail-actions .btn{padding:7px 11px;color:#fff;font-size:var(--text-body);letter-spacing:0;text-transform:none;background:#ffffff12;border-color:#ffffff28}.detail-close{display:flex;align-items:center;gap:7px;min-height:38px;padding:8px 11px;border:1px solid #ffffff45;border-radius:9px;background:#ffffff1a;color:#fff;font-size:var(--text-body);font-weight:700;letter-spacing:0;text-transform:none}.detail-identity{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-top:23px}.detail-subtitle{margin:0;color:#9cc0b5;font-size:var(--text-caption)}.detail-identity h2{margin:5px 0 0;font-size:var(--text-page)}.detail-identity small{color:#b6d3ca;font-size:var(--text-caption)}.detail-badge{padding:6px 10px;border:1px solid #ffffff22;border-radius:20px;background:#ffffff14;font-size:var(--text-secondary)}.detail-content{padding:22px 25px 40px}.quote-workbench{font-size:var(--text-body)}.workbench-actions{display:flex;gap:8px;margin-top:18px}.workbench-actions .btn{padding:8px 11px;font-size:var(--text-body)}.workbench-error{margin:12px 0 0;color:#ffd9d9;font-size:var(--text-body)}.workbench-tabs{display:flex;gap:4px;margin:-22px -25px 18px;padding:0 25px;border-bottom:1px solid #e3eae6;overflow:auto;background:#fff}.workbench-tabs button{border:0;border-bottom:2px solid transparent;background:transparent;padding:13px 12px;color:#70807a;font-size:var(--text-body);white-space:nowrap}.workbench-tabs button.active{border-bottom-color:#1f6657;color:#174c41;font-weight:700}.workbench-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.workbench-card{padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.workbench-card h3{display:flex;align-items:center;gap:7px;margin:0;color:#1d3f36;font-size:var(--text-section)}.workbench-card p{margin:7px 0;color:#71817b;font-size:var(--text-body);line-height:1.55}.summary-card{grid-column:span 2;background:linear-gradient(135deg,#f8fcfa,#eef6f1)}.summary-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:16px}.summary-metrics small,.summary-metrics strong{display:block}.summary-metrics small{color:#7c8c85;font-size:var(--text-caption)}.summary-metrics strong{margin-top:5px;color:#164a3e;font-size:var(--text-dialog)}.data-list{display:grid;grid-template-columns:105px 1fr;gap:10px;margin:16px 0 0;font-size:var(--text-body)}.data-list dt{color:#7c8983}.data-list dd{margin:0;color:#31473f;word-break:break-word}.text-btn{border:0;background:transparent;padding:5px 0;color:#236657;font-size:var(--text-body);font-weight:700}.text-btn.danger{color:#aa4d4d}.section-heading{display:flex;align-items:start;justify-content:space-between;gap:12px;margin-bottom:16px}.section-heading p{margin-bottom:0}.workbench-table-wrap{overflow:auto;margin:0 -19px}.workbench-table{width:100%;min-width:760px;border-collapse:collapse}.workbench-table th,.workbench-table td{padding:11px 14px;border-top:1px solid #edf1ef;text-align:left;font-size:var(--text-body)}.workbench-table th{background:#f7faf8;color:#7d8c86;font-size:var(--text-body)}.workbench-table td:nth-last-child(-n+2){text-align:right;font-variant-numeric:tabular-nums}.quote-totals{margin-top:15px;text-align:right;color:#62736c;font-size:var(--text-body)}.quote-totals strong{color:#174b40;font-size:var(--text-body)}.lineage-list{display:grid;gap:0;margin:0;padding:0;list-style:none}.lineage-list li{display:grid;grid-template-columns:18px 1fr auto auto;gap:11px;align-items:center;padding:14px 5px;border-bottom:1px solid #edf1ef}.lineage-list li.current{background:#f0f7f3}.lineage-dot{width:10px;height:10px;border:3px solid #6a9b8c;border-radius:50%}.lineage-list strong,.lineage-list small{display:block}.lineage-list strong{color:#24463c}.lineage-list small{margin-top:3px;color:#7a8983;font-size:var(--text-caption)}.order-list{display:grid;gap:10px}.order-card{display:grid;grid-template-columns:1fr auto auto;gap:16px;align-items:center;padding:14px;border:1px solid #e2e9e5;border-radius:10px}.order-card strong,.order-card small{display:block}.order-card small{margin-top:4px;color:#7b8984;font-size:var(--text-caption)}.order-card b{display:block;margin-top:7px;color:#1a4c40;font-size:var(--text-body)}.order-actions{display:flex;gap:12px}.workbench-empty{display:grid;justify-items:center;padding:42px 15px;color:#82918b;text-align:center}.workbench-empty strong{margin-top:9px;color:#556961}.workbench-empty p{margin-top:4px}.note-caution{display:flex;gap:10px;margin-bottom:17px;padding:12px 14px;border:1px solid #efd6a4;border-radius:9px;background:#fff8e8;color:#82591f}.note-caution p{margin:0;color:inherit}.note-create{display:flex;justify-content:flex-end;margin:11px 0 20px}.important-note{padding:15px 0;border-top:1px solid #e5ece8}.important-note header{display:flex;justify-content:space-between;gap:10px;align-items:start}.important-note header strong,.important-note header small{display:block}.important-note header strong{color:#2b5346;font-size:var(--text-body)}.important-note header small{margin-top:4px;color:#7a8984;font-size:var(--text-caption)}.important-note.inactive header strong{color:#a05b5b}.important-note-content{margin-top:11px;color:#344a42;line-height:1.7;word-break:break-word}.important-note-content :deep(p){margin:0 0 8px}.important-note-content :deep(ul),.important-note-content :deep(ol){margin:4px 0;padding-left:22px}.important-note.inactive .important-note-content{text-decoration:line-through;color:#8a918e}@media(max-width:980px){.detail-backdrop{inset:0;z-index:60}}@media(max-width:700px){.detail-modal{width:100vw}.detail-header{padding:16px 17px 20px}.detail-identity h2{font-size:var(--text-page)}.detail-content{padding:12px}.workbench-grid{grid-template-columns:1fr}.summary-card{grid-column:auto}.summary-metrics{grid-template-columns:1fr}.workbench-tabs{margin-left:-12px;margin-right:-12px;padding:0 12px}.order-card{grid-template-columns:1fr}.order-actions{justify-content:flex-start}.lineage-list li{grid-template-columns:18px 1fr auto}.lineage-list li .mini-btn{grid-column:2}.workbench-actions .btn{padding:7px}.workbench-actions{flex-wrap:wrap}.detail-close span{display:none}.detail-close{padding:8px}}
.quote-status-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.quote-order-unavailable{position:relative;z-index:1;margin:12px 0 0;color:#ffe0ae;font-size:var(--text-body)}
.items-table td small { display: block; margin-top: 3px; color: var(--muted); line-height: 1.4; }
</style>

<style scoped>
.version-row-main,.lineage-row-main{display:flex;align-items:center;flex-wrap:wrap;gap:6px 8px}.summary-version-actions{display:flex;gap:12px;flex-wrap:wrap}
</style>

<style scoped>
.detail-header{padding:22px 26px}.detail-identity h2{font-size:var(--text-page);font-weight:700}.workbench-actions{flex-wrap:wrap;align-items:center}.workbench-actions .btn{min-height:36px;border-radius:8px}.workbench-actions .btn-secondary{background:#ffffff12;color:#fff;border:1px solid #ffffff28}.workbench-actions .transfer-order{order:-1;background:#f5fcf8;color:#174c41;border:1px solid #b8dccf;font-weight:700;padding:8px 13px}.workbench-actions .quote-utility{margin-left:auto;background:transparent;color:#b6d3ca;border:1px solid #ffffff28}.quote-status-actions .btn{min-height:30px;padding:5px 10px;background:transparent;color:#b6d3ca;border:1px solid #ffffff28;font-size:var(--text-caption)}.workbench-tabs button{min-height:44px;padding:10px 13px}.workbench-grid{gap:16px}.workbench-card{padding:16px}.workbench-table-wrap{margin-left:-16px;margin-right:-16px}.detail-nav{flex-wrap:wrap;gap:12px}
</style>
