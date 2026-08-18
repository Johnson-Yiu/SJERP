<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { AlertTriangle, Download, Eye, FileText, GitBranch, Pencil, Plus, ShoppingCart, StickyNote, X } from 'lucide-vue-next'
import { api, downloadQuoteExport } from '../api'
import QuotePreviewModal from './QuotePreviewModal.vue'
import RichTextEditor from './RichTextEditor.vue'

const props = defineProps({ id: { type: [Number, String], required: true } })
const emit = defineEmits(['close', 'revise', 'create-order', 'open-order'])
const workbench = ref(null)
const activeTab = ref('overview')
const loading = ref(true)
const error = ref('')
const preview = ref(null)
const noteContent = ref('')
const noteSaving = ref(false)
const actionError = ref('')

const quote = computed(() => workbench.value?.quote)
const tabs = computed(() => [
  ['overview', '概览'], ['items', `报价明细 (${quote.value?.items?.length || 0})`],
  ['lineage', `版本谱系 (${workbench.value?.revisions?.length || 0})`], ['orders', `订单 (${workbench.value?.orders?.length || 0})`],
  ['notes', `重要备注 (${workbench.value?.important_notes?.length || 0})`],
])
const subtotal = computed(() => (quote.value?.items || []).reduce((sum, item) => sum + Number(item.amount || 0), 0))
function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function revisionLabel(row) { return row.revision_no ? `迭代版 -${row.revision_no}` : '原始报价' }
function isRichTextEmpty(value) { return !String(value || '').replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim() }
function dateTime(value) { return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—' }

async function load(id = props.id) {
  loading.value = true; error.value = ''; actionError.value = ''
  try { workbench.value = (await api.get(`/quotes/${id}/workbench/`)).data }
  catch (err) { error.value = err.message }
  finally { loading.value = false }
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
      buyer: { company_name: data.buyer.company_name, recipient: data.buyer.name, address: data.buyer.address, email: data.buyer.email, phone: data.buyer.phone },
      products: data.products.map((item, index) => ({ ...item, key: `${item.sku}-${index}` })),
    }
  } catch (err) { actionError.value = err.message }
}
async function exportQuote() {
  actionError.value = ''
  try { await downloadQuoteExport(quote.value.id, quote.value.quote_no) } catch (err) { actionError.value = err.message }
}
async function createNote() {
  if (isRichTextEmpty(noteContent.value)) return
  noteSaving.value = true; actionError.value = ''
  try { await api.post(`/quotes/${quote.value.id}/important-notes/`, { content: noteContent.value }); noteContent.value = ''; await load(quote.value.id) }
  catch (err) { actionError.value = err.message }
  finally { noteSaving.value = false }
}
async function deactivateNote(note) {
  if (!window.confirm('标记后备注不会删除，但会显示为不再生效。确定继续吗？')) return
  actionError.value = ''
  try { await api.post(`/quotes/${quote.value.id}/important-notes/${note.id}/deactivate/`); await load(quote.value.id) }
  catch (err) { actionError.value = err.message }
}
function changeVersion(row) { activeTab.value = 'overview'; load(row.id) }
function createOrder() { emit('create-order', quote.value.id) }

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div class="modal-backdrop detail-backdrop" @mousedown.self="emit('close')">
    <article class="detail-modal quote-workbench" role="dialog" aria-modal="true" aria-label="报价工作台">
      <div v-if="loading" class="detail-loading"><div class="spinner" /> 正在加载报价工作台…</div>
      <div v-else-if="error" class="detail-error"><AlertTriangle :size="27" /><strong>加载失败</strong><p>{{ error }}</p><button class="btn btn-secondary" @click="load()">重试</button></div>
      <template v-else>
        <header class="detail-header">
          <div class="detail-nav"><span>报价工作台 · {{ workbench.root_quote_no }}</span><div class="detail-actions"><button class="btn btn-secondary" @click="emit('revise', quote)"><Pencil :size="14" /> 创建迭代版</button><button class="detail-close" aria-label="关闭报价详情" @click="emit('close')"><X :size="18" /></button></div></div>
          <div class="detail-identity"><div><p class="detail-subtitle">{{ quote.customer_name }} · {{ revisionLabel(quote) }}</p><h2>{{ quote.quote_no }}</h2><small>原始报价：{{ workbench.root_quote_no }}</small></div><span class="detail-badge">{{ quote.status_display }}</span></div>
          <div class="workbench-actions"><button class="btn btn-secondary" @click="openPreview()"><Eye :size="15" /> 预览 PI</button><button class="btn btn-secondary" @click="exportQuote"><Download :size="15" /> 导出 Excel</button><button class="btn btn-primary" @click="createOrder"><ShoppingCart :size="15" /> 转为订单</button></div>
          <p v-if="actionError" class="workbench-error">{{ actionError }}</p>
        </header>
        <main class="detail-content">
          <nav class="workbench-tabs" aria-label="报价详情分页"><button v-for="tab in tabs" :key="tab[0]" :class="{ active: activeTab === tab[0] }" @click="activeTab = tab[0]">{{ tab[1] }}</button></nav>

          <section v-if="activeTab === 'overview'" class="workbench-grid">
            <div class="workbench-card summary-card"><h3>报价概览</h3><div class="summary-metrics"><div><small>报价总额</small><strong>{{ quote.currency }} {{ money(quote.total_amount) }}</strong></div><div><small>有效期至</small><strong>{{ quote.valid_until || '—' }}</strong></div><div><small>商品明细</small><strong>{{ quote.items.length }} 项</strong></div></div></div>
            <div class="workbench-card"><h3>基础信息</h3><dl class="data-list"><dt>报价日期</dt><dd>{{ quote.quote_date }}</dd><dt>币种 / 汇率</dt><dd>{{ quote.currency }} / {{ quote.exchange_rate }}</dd><dt>收件人</dt><dd>{{ quote.recipient_name || '—' }}</dd><dt>条款备注</dt><dd>{{ quote.notes || '—' }}</dd></dl></div>
            <div class="workbench-card"><h3><GitBranch :size="16" /> 版本摘要</h3><p>该链共 {{ workbench.revisions.length }} 个版本，当前为 {{ revisionLabel(quote) }}。</p><button class="text-btn" @click="activeTab = 'lineage'">查看版本谱系</button></div>
            <div class="workbench-card"><h3><ShoppingCart :size="16" /> 订单摘要</h3><p>该原始报价链已转出 {{ workbench.orders.length }} 张订单。</p><button class="text-btn" @click="activeTab = 'orders'">查看关联订单</button></div>
          </section>

          <section v-else-if="activeTab === 'items'" class="workbench-card"><div class="section-heading"><div><h3>报价明细</h3><p>本页只展示当前版本的固定商品快照。</p></div><strong>{{ quote.currency }} {{ money(quote.total_amount) }}</strong></div><div class="workbench-table-wrap"><table class="workbench-table"><thead><tr><th>SKU</th><th>产品</th><th>描述</th><th>数量</th><th>单位</th><th>单价</th><th>小计</th></tr></thead><tbody><tr v-for="item in quote.items" :key="item.id"><td>{{ item.sku_code }}</td><td>{{ item.product_name }}</td><td>{{ item.description || '—' }}</td><td>{{ item.quantity }}</td><td>{{ item.unit }}</td><td>{{ money(item.unit_price) }}</td><td>{{ money(item.amount) }}</td></tr></tbody></table></div><div class="quote-totals">商品小计 {{ money(subtotal) }}　运费 {{ money(quote.shipping_fee) }}　折扣 -{{ money(quote.discount) }}　<strong>合计 {{ quote.currency }} {{ money(quote.total_amount) }}</strong></div></section>

          <section v-else-if="activeTab === 'lineage'" class="workbench-card"><div class="section-heading"><div><h3>版本谱系</h3><p>所有版本均保留，点击可切换查看其报价明细和 PI。</p></div></div><ol class="lineage-list"><li v-for="row in workbench.revisions" :key="row.id" :class="{ current: row.id === quote.id }"><span class="lineage-dot" /><div><strong>{{ row.quote_no }}</strong><small>{{ revisionLabel(row) }} · {{ row.quote_date }} · {{ row.currency }} {{ money(row.total_amount) }}</small></div><span class="status" :class="row.status">{{ row.status_display }}</span><button class="mini-btn" :disabled="row.id === quote.id" @click="changeVersion(row)">查看</button></li></ol></section>

          <section v-else-if="activeTab === 'orders'" class="workbench-card"><div class="section-heading"><div><h3>订单</h3><p>展示当前原始报价及全部迭代版本转出的订单。</p></div><button class="btn btn-primary" @click="createOrder"><Plus :size="15" /> 转为订单</button></div><div v-if="!workbench.orders.length" class="workbench-empty"><ShoppingCart :size="28" /><strong>尚未转为订单</strong><p>可从当前报价版本创建一张预填的订单草稿。</p></div><div v-else class="order-list"><article v-for="order in workbench.orders" :key="order.id" class="order-card"><div><strong>{{ order.order_no }}</strong><small>来源报价：{{ order.source_quote_no || '—' }} · {{ order.order_date }}</small></div><div><span class="status" :class="order.status">{{ order.status_display }}</span><b>{{ order.currency }} {{ money(order.total_amount) }}</b></div><div class="order-actions"><button class="text-btn" @click="openPreview(order.quote)">预览来源 PI</button><button class="text-btn" @click="emit('open-order', order.id)">查看订单</button></div></article></div></section>

          <section v-else class="workbench-card notes-panel"><div class="note-caution"><AlertTriangle :size="18" /><p>备注可能对应不同报价版本，部分内容可能已经过时，且未必适用于最终订单。请结合沟通记录和来源版本判断。</p></div><div class="section-heading"><div><h3><StickyNote :size="16" /> 重要备注</h3><p>新建备注会自动标记为当前报价版本的沟通记录。</p></div></div><RichTextEditor v-model="noteContent" /><div class="note-create"><button class="btn btn-primary" :disabled="noteSaving || isRichTextEmpty(noteContent)" @click="createNote">{{ noteSaving ? '保存中…' : '新增重要备注' }}</button></div><div v-if="!workbench.important_notes.length" class="workbench-empty"><StickyNote :size="28" /><strong>暂无重要备注</strong><p>将长期需要追溯的沟通信息记录在此处。</p></div><article v-for="note in workbench.important_notes" :key="note.id" class="important-note" :class="{ inactive: !note.is_active }"><header><div><strong>{{ note.is_active ? '有效备注' : '不再生效' }}</strong><small>备注于：{{ note.source_quote_no }}（{{ revisionLabel({ revision_no: note.source_revision_no }) }}） · {{ note.created_by_name }} · {{ dateTime(note.created_at) }}</small></div><button v-if="note.is_active" class="text-btn danger" @click="deactivateNote(note)">标记不再生效</button></header><div class="important-note-content" v-html="note.content" /></article></section>
        </main>
      </template>
    </article>
    <QuotePreviewModal v-if="preview" :draft="preview" @close="preview = null" />
  </div>
</template>

<style scoped>
.quote-workbench{font-size:14px}.workbench-actions{position:relative;z-index:1;display:flex;gap:8px;margin-top:18px}.workbench-actions .btn{padding:8px 11px;font-size:12px}.workbench-error{position:relative;z-index:1;margin:12px 0 0;color:#ffd9d9;font-size:12px}.workbench-tabs{display:flex;gap:4px;margin:-22px -25px 18px;padding:0 25px;border-bottom:1px solid #e3eae6;overflow:auto;background:#fff}.workbench-tabs button{border:0;border-bottom:2px solid transparent;background:transparent;padding:13px 12px;color:#70807a;font-size:13px;white-space:nowrap}.workbench-tabs button.active{border-bottom-color:#1f6657;color:#174c41;font-weight:700}.workbench-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.workbench-card{padding:19px;border:1px solid #e0e8e4;border-radius:13px;background:#fff}.workbench-card h3{display:flex;align-items:center;gap:7px;margin:0;color:#1d3f36;font-size:16px}.workbench-card p{margin:7px 0;color:#71817b;font-size:13px;line-height:1.55}.summary-card{grid-column:span 2;background:linear-gradient(135deg,#f8fcfa,#eef6f1)}.summary-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:16px}.summary-metrics small,.summary-metrics strong{display:block}.summary-metrics small{color:#7c8c85;font-size:12px}.summary-metrics strong{margin-top:5px;color:#164a3e;font-size:19px}.data-list{display:grid;grid-template-columns:105px 1fr;gap:10px;margin:16px 0 0;font-size:13px}.data-list dt{color:#7c8983}.data-list dd{margin:0;color:#31473f;word-break:break-word}.text-btn{border:0;background:transparent;padding:5px 0;color:#236657;font-size:13px;font-weight:700}.text-btn.danger{color:#aa4d4d}.section-heading{display:flex;align-items:start;justify-content:space-between;gap:12px;margin-bottom:16px}.section-heading p{margin-bottom:0}.workbench-table-wrap{overflow:auto;margin:0 -19px}.workbench-table{width:100%;min-width:760px;border-collapse:collapse}.workbench-table th,.workbench-table td{padding:11px 14px;border-top:1px solid #edf1ef;text-align:left;font-size:12px}.workbench-table th{background:#f7faf8;color:#7d8c86;font-size:11px}.workbench-table td:nth-last-child(-n+2){text-align:right;font-variant-numeric:tabular-nums}.quote-totals{margin-top:15px;text-align:right;color:#62736c;font-size:12px}.quote-totals strong{color:#174b40;font-size:14px}.lineage-list{display:grid;gap:0;margin:0;padding:0;list-style:none}.lineage-list li{display:grid;grid-template-columns:18px 1fr auto auto;gap:11px;align-items:center;padding:14px 5px;border-bottom:1px solid #edf1ef}.lineage-list li.current{background:#f0f7f3}.lineage-dot{width:10px;height:10px;border:3px solid #6a9b8c;border-radius:50%}.lineage-list strong,.lineage-list small{display:block}.lineage-list strong{color:#24463c}.lineage-list small{margin-top:3px;color:#7a8983;font-size:12px}.order-list{display:grid;gap:10px}.order-card{display:grid;grid-template-columns:1fr auto auto;gap:16px;align-items:center;padding:14px;border:1px solid #e2e9e5;border-radius:10px}.order-card strong,.order-card small{display:block}.order-card small{margin-top:4px;color:#7b8984;font-size:12px}.order-card b{display:block;margin-top:7px;color:#1a4c40;font-size:13px}.order-actions{display:flex;gap:12px}.workbench-empty{display:grid;justify-items:center;padding:42px 15px;color:#82918b;text-align:center}.workbench-empty strong{margin-top:9px;color:#556961}.workbench-empty p{margin-top:4px}.note-caution{display:flex;gap:10px;margin-bottom:17px;padding:12px 14px;border:1px solid #efd6a4;border-radius:9px;background:#fff8e8;color:#82591f}.note-caution p{margin:0;color:inherit}.note-create{display:flex;justify-content:flex-end;margin:11px 0 20px}.important-note{padding:15px 0;border-top:1px solid #e5ece8}.important-note header{display:flex;justify-content:space-between;gap:10px;align-items:start}.important-note header strong,.important-note header small{display:block}.important-note header strong{color:#2b5346;font-size:13px}.important-note header small{margin-top:4px;color:#7a8984;font-size:12px}.important-note.inactive header strong{color:#a05b5b}.important-note-content{margin-top:11px;color:#344a42;line-height:1.7;word-break:break-word}.important-note-content :deep(p){margin:0 0 8px}.important-note-content :deep(ul),.important-note-content :deep(ol){margin:4px 0;padding-left:22px}.important-note.inactive .important-note-content{text-decoration:line-through;color:#8a918e}@media(max-width:700px){.workbench-grid{grid-template-columns:1fr}.summary-card{grid-column:auto}.summary-metrics{grid-template-columns:1fr}.workbench-tabs{margin-left:-12px;margin-right:-12px;padding:0 12px}.order-card{grid-template-columns:1fr}.order-actions{justify-content:flex-start}.lineage-list li{grid-template-columns:18px 1fr auto}.lineage-list li .mini-btn{grid-column:2}.detail-content{padding:12px}.workbench-actions .btn{padding:7px}.workbench-actions{flex-wrap:wrap}}
</style>
