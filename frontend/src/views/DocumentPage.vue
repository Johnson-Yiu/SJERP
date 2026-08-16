<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Search, Pencil, Trash2, FileX2, X, PlusCircle, MinusCircle, Download } from 'lucide-vue-next'
import { api, downloadQuoteExport, listData } from '../api'
import EntityDetailModal from '../components/EntityDetailModal.vue'
import QuoteEditorModal from '../components/QuoteEditorModal.vue'

const props = defineProps({ type: String })
const route = useRoute()
const isOrder = computed(() => props.type === 'orders')
const copy = computed(() => isOrder.value ? {
  title: '订单管理', description: '从客户需求到交付和回款，保持订单、产品与流水一一对应。', no: 'order_no', noLabel: '订单号', date: 'order_date', dateLabel: '订单日期', statuses: { draft: '草稿', confirmed: '已确认', production: '生产中', shipped: '已发货', completed: '已完成', cancelled: '已取消' }
} : {
  title: '报价管理', description: '建立标准化报价明细，记录有效期与客户反馈状态。', no: 'quote_no', noLabel: '报价单号', date: 'quote_date', dateLabel: '报价日期', statuses: { draft: '草稿', sent: '已发送', accepted: '已接受', rejected: '已拒绝', expired: '已过期' }
})

const rows = ref([]), customers = ref([]), skus = ref([]), quotes = ref([])
const loading = ref(true), saving = ref(false), open = ref(false), editingId = ref(null), query = ref('')
const detailId = ref(null)
const quoteEditorOpen = ref(false), quoteEditorQuote = ref(null)
const toast = reactive({ show: false, message: '', error: false })
const form = reactive({})
let timer

function fresh() {
  const now = new Date(), y = now.getFullYear(), m = String(now.getMonth() + 1).padStart(2, '0'), d = String(now.getDate()).padStart(2, '0')
  Object.keys(form).forEach(k => delete form[k])
  Object.assign(form, { customer: '', [copy.value.no]: `${isOrder.value ? 'SO' : 'QT'}-${y}-${String(Date.now()).slice(-5)}`, [copy.value.date]: `${y}-${m}-${d}`, status: isOrder.value ? 'confirmed' : 'draft', currency: 'USD', exchange_rate: '7.20', shipping_fee: 0, discount: 0, notes: '', items: [{ sku: '', quantity: 1, unit_price: 0, cost_price: 0, notes: '' }] })
  if (isOrder.value) Object.assign(form, { quote: '', expected_ship_date: '' })
  else form.valid_until = ''
}
function notify(message, error = false) { Object.assign(toast, { show: true, message, error }); setTimeout(() => toast.show = false, 2800) }
async function load() {
  loading.value = true
  try { rows.value = listData(await api.get(`/${props.type}/`, { params: { ...route.query, search: query.value } })) } catch (e) { notify(e.message, true) } finally { loading.value = false }
}
async function loadOptions() {
  try {
    const calls = [api.get('/customers/'), api.get('/skus/')]
    if (isOrder.value) calls.push(api.get('/quotes/'))
    const result = await Promise.all(calls); customers.value = listData(result[0]); skus.value = listData(result[1]); if (result[2]) quotes.value = listData(result[2])
  } catch (e) { notify(e.message, true) }
}
async function create() {
  if (!isOrder.value) {
    await loadOptions()
    quoteEditorQuote.value = route.query.customer ? { customer: Number(route.query.customer) } : null
    quoteEditorOpen.value = true
    return
  }
  editingId.value = null; fresh(); await loadOptions(); open.value = true
}
async function edit(row) {
  detailId.value = null
  if (!isOrder.value) {
    await loadOptions()
    quoteEditorQuote.value = row
    quoteEditorOpen.value = true
    return
  }
  editingId.value = row.id; fresh(); await loadOptions()
  Object.keys(form).forEach(k => { if (row[k] !== undefined && k !== 'items') form[k] = row[k] ?? '' })
  form.items = row.items.map(i => ({ sku: i.sku, quantity: i.quantity, unit_price: i.unit_price, cost_price: i.cost_price || 0, notes: i.notes || '' }))
  open.value = true
}
function selectSku(item) {
  const sku = skus.value.find(s => s.id === Number(item.sku))
  if (sku) { item.unit_price = sku.default_price; item.cost_price = sku.cost_price }
}
function addItem() { form.items.push({ sku: '', quantity: 1, unit_price: 0, cost_price: 0, notes: '' }) }
const subtotal = computed(() => (form.items || []).reduce((sum, i) => sum + Number(i.quantity || 0) * Number(i.unit_price || 0), 0))
const total = computed(() => subtotal.value + Number(form.shipping_fee || 0) - Number(form.discount || 0))
async function save() {
  if (!form.items.length || form.items.some(i => !i.sku)) return notify('请至少添加一条有效的 SKU 明细。', true)
  saving.value = true
  const data = { ...form, customer: Number(form.customer), items: form.items.map(i => ({ ...i, sku: Number(i.sku) })) }
  if (isOrder.value) data.quote = form.quote ? Number(form.quote) : null
  try { editingId.value ? await api.put(`/${props.type}/${editingId.value}/`, data) : await api.post(`/${props.type}/`, data); open.value = false; notify('单据已保存'); await load() } catch (e) { notify(e.message, true) } finally { saving.value = false }
}
async function handleQuoteSaved(row) { notify(`报价 ${row.quote_no} 已保存`); await load() }
async function exportQuote(row) { try { await downloadQuoteExport(row.id, row.quote_no) } catch (e) { notify(`导出 ${row.quote_no} 失败：${e.message}`, true) } }
async function remove(row) { if (!confirm(`确定删除 ${row[copy.value.no]} 吗？`)) return; try { await api.delete(`/${props.type}/${row.id}/`); notify('已删除'); load() } catch (e) { notify(e.message, true) } }
function delayed() { clearTimeout(timer); timer = setTimeout(load, 300) }
function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function editFromDetail() { const row = rows.value.find(r => r.id === detailId.value); if (row) edit(row) }
watch(() => props.type, load)
watch(() => route.query, load)
onMounted(async () => {
  await load()
  if (route.query.create === '1') {
    await create()
    if (route.query.customer && isOrder.value) form.customer = Number(route.query.customer)
    if (isOrder.value && route.query.quote) form.quote = Number(route.query.quote)
  }
})
</script>

<template>
  <div>
    <div class="page-head"><div><h2>{{ copy.title }}</h2><p>{{ copy.description }}</p></div><button class="btn btn-primary" @click="create"><Plus :size="16" /> 新建{{ isOrder ? '订单' : '报价' }}</button></div>
    <div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" :placeholder="`搜索${copy.noLabel}或客户...`" @input="delayed" /></div></div>
    <div class="panel">
      <div v-if="loading" class="loading"><div class="spinner" /></div>
      <div v-else-if="!rows.length" class="empty"><FileX2 :size="32" /><h3>还没有{{ isOrder ? '订单' : '报价' }}</h3><p>创建第一张业务单据，产品和客户数据会自动关联。</p></div>
      <div v-else class="table-wrap"><table class="data-table"><thead><tr><th>{{ copy.noLabel }}</th><th>客户</th><th>{{ copy.dateLabel }}</th><th>状态</th><th>明细</th><th>总金额</th><th v-if="isOrder">已收 / 未收</th><th style="text-align:right">操作</th></tr></thead>
        <tbody><tr v-for="row in rows" :key="row.id" class="clickable-row" tabindex="0" @click="detailId = row.id" @keydown.enter="detailId = row.id"><td class="primary-cell">{{ row[copy.no] }}</td><td>{{ row.customer_name }}</td><td>{{ row[copy.date] }}</td><td><span class="status" :class="row.status">{{ row.status_display }}</span></td><td>{{ row.items.length }} 项</td><td class="amount">{{ row.currency }} {{ money(row.total_amount) }}</td><td v-if="isOrder"><span class="paid">{{ money(row.paid_amount) }}</span> / <span class="owing">{{ money(row.balance_amount) }}</span></td><td><div class="table-actions"><button v-if="!isOrder" class="mini-btn" :aria-label="`导出 ${row[copy.no]}`" @click.stop="exportQuote(row)"><Download :size="14" /></button><button class="mini-btn" :aria-label="`编辑 ${row[copy.no]}`" @click.stop="edit(row)"><Pencil :size="14" /></button><button class="mini-btn" :aria-label="`删除 ${row[copy.no]}`" @click.stop="remove(row)"><Trash2 :size="14" /></button></div></td></tr></tbody>
      </table></div>
    </div>

    <div v-if="open && isOrder" class="modal-backdrop" @mousedown.self="open = false"><form class="modal wide" @submit.prevent="save">
      <div class="modal-head"><h3>{{ editingId ? '编辑' : '新建' }}{{ isOrder ? '订单' : '报价' }}</h3><button type="button" class="mini-btn" @click="open = false"><X :size="17" /></button></div>
      <div class="modal-body">
        <div class="form-grid">
          <div class="field"><label>{{ copy.noLabel }} *</label><input v-model="form[copy.no]" required /></div>
          <div class="field"><label>客户 *</label><select v-model="form.customer" required><option value="">请选择</option><option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option></select></div>
          <div class="field"><label>{{ copy.dateLabel }} *</label><input v-model="form[copy.date]" type="date" required /></div>
          <div class="field"><label>{{ isOrder ? '预计交期' : '有效期至' }}</label><input v-model="form[isOrder ? 'expected_ship_date' : 'valid_until']" type="date" /></div>
          <div class="field"><label>状态 *</label><select v-model="form.status"><option v-for="(label,key) in copy.statuses" :key="key" :value="key">{{ label }}</option></select></div>
          <div v-if="isOrder" class="field"><label>来源报价</label><select v-model="form.quote"><option value="">无</option><option v-for="q in quotes" :key="q.id" :value="q.id">{{ q.quote_no }}</option></select></div>
          <div class="field"><label>币种</label><select v-model="form.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
          <div class="field"><label>对人民币汇率</label><input v-model="form.exchange_rate" type="number" step="0.000001" /></div>
        </div>
        <div class="items-head"><div><strong>产品明细</strong><small>单据成交的 SKU、数量和价格</small></div><button type="button" class="btn btn-secondary" @click="addItem"><PlusCircle :size="15" /> 添加一行</button></div>
        <div class="line-items">
          <div class="line-header"><span>SKU</span><span>数量</span><span>单价</span><span v-if="isOrder">成本</span><span>小计</span><span></span></div>
          <div v-for="(item,index) in form.items" :key="index" class="line-row" :class="{ order: isOrder }">
            <select v-model="item.sku" required @change="selectSku(item)"><option value="">选择 SKU</option><option v-for="sku in skus" :key="sku.id" :value="sku.id">{{ sku.sku }} · {{ sku.product_name }}</option></select>
            <input v-model="item.quantity" type="number" min="0.01" step="0.01" required />
            <input v-model="item.unit_price" type="number" min="0" step="0.0001" required />
            <input v-if="isOrder" v-model="item.cost_price" type="number" min="0" step="0.0001" />
            <span class="amount">{{ money(Number(item.quantity)*Number(item.unit_price)) }}</span>
            <button type="button" class="remove-line" :disabled="form.items.length === 1" @click="form.items.splice(index,1)"><MinusCircle :size="17" /></button>
          </div>
        </div>
        <div class="totals"><label>运费 <input v-model="form.shipping_fee" type="number" step="0.01" /></label><label>折扣 <input v-model="form.discount" type="number" step="0.01" /></label><div><span>合计</span><strong>{{ form.currency }} {{ money(total) }}</strong></div></div>
        <div class="field notes"><label>条款 / 备注</label><textarea v-model="form.notes" /></div>
      </div>
      <div class="modal-foot"><button type="button" class="btn btn-secondary" @click="open = false">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存单据' }}</button></div>
    </form></div>
    <QuoteEditorModal v-if="quoteEditorOpen" :quote="quoteEditorQuote" :customers="customers" :skus="skus" :mode="quoteEditorQuote?.id ? 'revise' : 'create'" @close="quoteEditorOpen = false" @saved="handleQuoteSaved" />
    <Transition name="detail-drawer" appear>
      <EntityDetailModal v-if="detailId" :entity="type" :id="detailId" @close="detailId = null" @edit="editFromDetail" />
    </Transition>
    <div v-if="toast.show" class="toast" :class="{ error: toast.error }">{{ toast.message }}</div>
  </div>
</template>

<style scoped>
.paid{color:#277258;font-weight:600}.owing{color:#b66d2f;font-weight:600}.items-head{display:flex;justify-content:space-between;align-items:center;margin:26px 0 10px;padding-top:22px;border-top:1px solid #e5eae7}.items-head strong,.items-head small{display:block}.items-head strong{font-size:14px}.items-head small{font-size:11px;color:#82908b;margin-top:3px}.line-items{border:1px solid #e0e6e2;border-radius:10px;overflow:hidden}.line-header,.line-row{display:grid;grid-template-columns:2fr .6fr .8fr .8fr 34px;gap:8px;align-items:center;padding:8px 10px}.line-header:has(+ .order),.line-row.order{grid-template-columns:2fr .55fr .7fr .7fr .8fr 34px}.line-header{background:#f5f8f6;color:#7a8984;font-size:10px;text-transform:uppercase}.line-row{border-top:1px solid #edf0ee}.line-row select,.line-row input{min-width:0;width:100%;border:1px solid #dce3df;border-radius:7px;padding:8px;font-size:12px}.line-row .amount{text-align:right}.remove-line{border:0;background:transparent;color:#b05b5b;display:grid;place-items:center}.remove-line:disabled{opacity:.25}.totals{margin:15px 0 22px;display:flex;justify-content:flex-end;gap:14px;align-items:end}.totals label{font-size:11px;color:#778680}.totals input{display:block;width:105px;margin-top:5px;border:1px solid #dce3df;border-radius:7px;padding:8px}.totals div{border-left:1px solid #dae2de;padding-left:18px}.totals span,.totals strong{display:block}.totals span{font-size:11px;color:#788680}.totals strong{font-size:20px;color:#123c36;margin-top:5px}.notes textarea{min-height:65px}@media(max-width:700px){.line-items{overflow:auto}.line-header,.line-row,.line-header:has(+ .order),.line-row.order{min-width:700px}.totals{flex-wrap:wrap}}
</style>
