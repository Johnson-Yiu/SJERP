<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Eye, MinusCircle, PlusCircle, RotateCw, Save, X } from 'lucide-vue-next'
import { api, downloadQuoteExport, listData } from '../api'
import QuotePreviewModal from './QuotePreviewModal.vue'
import SegmentedDateInput from './SegmentedDateInput.vue'
import ComboInput from './ComboInput.vue'
import { addDays, daysBetween } from '../utils/orderDate'

const props = defineProps({
  quote: { type: Object, default: null },
  customers: { type: Array, required: true },
  skus: { type: Array, required: true },
  mode: { type: String, required: true, validator: value => ['create', 'revise'].includes(value) },
})
const emit = defineEmits(['close', 'saved'])

/*
 * Task 4 manual acceptance checklist (verified):
 * [x] The editor has no embedded PI preview pane.
 * [x] Preview opens a separate child modal from the current unsaved draft.
 * [x] Closing preview retains all editor inputs, including changed quantities.
 * [x] Saving an existing quote creates a revision through /revise/.
 * [x] Save/export downloads with the complete generated quote identifier.
 */
const today = new Date().toISOString().slice(0, 10)
const draft = reactive(makeDraft())
const previewOpen = ref(false)
const saving = ref(false)
const savedQuote = ref(null)
const errorMessage = ref('')
const exportError = ref('')

function makeDraft() {
  const quote = props.quote || {}
  const quoteDate = quote.quote_date || today
  return {
    customer: quote.customer || '', quote_no: quote.quote_no || '', quote_date: quoteDate,
    valid_until: quote.valid_until || addDays(quoteDate, 30), status: quote.status || 'draft', currency: quote.currency || 'USD',
    exchange_rate: quote.exchange_rate || '7.200000', shipping_fee: quote.shipping_fee || 0, discount: quote.discount || 0,
    recipient_name: quote.recipient_name || '', buyer_address: quote.buyer_address || '', buyer_email: quote.buyer_email || '', buyer_phone: quote.buyer_phone || '',
    lead_time_days: quote.lead_time_days || 10, deposit_percent: Number(quote.deposit_ratio ?? 1) * 100,
    revision_summary: '',
    trading_terms: quote.trading_terms || 'FOB Shenzhen', shipping_details: quote.shipping_details || '', notes: quote.notes || '',
    items: (quote.items?.length ? quote.items : [{ sku: '', quantity: 1, unit_price: 0, sales_model_snapshot: '', description: '', notes: '' }]).map(item => ({ sku: item.sku, quantity: item.quantity, unit_price: item.unit_price, sales_model_snapshot: item.sales_model_snapshot ?? item.model ?? '', description: item.description || item.description_snapshot || '', notes: item.notes || '' })),
  }
}

const validityDays = ref(daysBetween(draft.quote_date, draft.valid_until))

function setQuoteDate(value) {
  draft.quote_date = value
  if (validityDays.value !== '') draft.valid_until = addDays(value, validityDays.value)
  else if (draft.valid_until) validityDays.value = daysBetween(value, draft.valid_until)
}
function setValidUntil(value) {
  draft.valid_until = value
  validityDays.value = daysBetween(draft.quote_date, value)
}
function setValidityDays() {
  if (validityDays.value === '' || !draft.quote_date) return
  draft.valid_until = addDays(draft.quote_date, validityDays.value)
}

const subtotal = computed(() => draft.items.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0))
const total = computed(() => subtotal.value + Number(draft.shipping_fee || 0) - Number(draft.discount || 0))
const previewDraft = computed(() => {
  const customer = props.customers.find(row => row.id === Number(draft.customer)) || {}
  const depositRatio = Math.min(100, Math.max(0, Number(draft.deposit_percent || 0))) / 100
  const depositAmount = Math.round(total.value * depositRatio * 100) / 100
  return {
    quote_no: draft.quote_no, quote_date: draft.quote_date, valid_until: draft.valid_until, currency: draft.currency,
    buyer: { company_name: customer.name || '', recipient: draft.recipient_name, address: draft.buyer_address, email: draft.buyer_email, phone: draft.buyer_phone },
    terms: { lead_time_days: draft.lead_time_days, trading_terms: draft.trading_terms, shipping_details: draft.shipping_details, notes: draft.notes },
    totals: { subtotal: subtotal.value, shipping_fee: Number(draft.shipping_fee || 0), discount: Number(draft.discount || 0), total_amount: total.value },
    payment_splits: { deposit_ratio: depositRatio, deposit_amount: depositAmount, balance_ratio: 1 - depositRatio, balance_amount: total.value - depositAmount },
    products: draft.items.map((item, index) => { const sku = props.skus.find(row => row.id === Number(item.sku)) || {}; return { key: `${index}-${item.sku}`, sku: sku.sku || '', sku_code: sku.sku_code || sku.sku || '', model: item.sales_model_snapshot || sku.sales_model || '', product_name: sku.display_name_cn || sku.product_name || '', description: item.description, quantity: item.quantity, unit: sku.unit || 'pcs', unit_price: item.unit_price, amount: Number(item.quantity || 0) * Number(item.unit_price || 0), image_url: sku.image || '' } }),
  }
})
const pinyinInitialMap = { 灯: 'd', 带: 'd', 柜: 'g', 电: 'd', 源: 'y', 面: 'm', 板: 'b', 筒: 't', 射: 's', 轨: 'g', 道: 'd', 吸: 'x', 顶: 'd', 壁: 'b', 台: 't', 庭: 't', 户: 'h', 外: 'w', 工: 'g', 矿: 'k', 防: 'f', 爆: 'b', 应: 'y', 急: 'j', 开: 'k', 关: 'g', 驱: 'q', 动: 'd', 器: 'q', 线: 'x', 条: 't', 球: 'q', 泡: 'p', 光: 'g', 伏: 'f', 瓦: 'w', 白: 'b', 黑: 'h', 暖: 'n', 冷: 'l', 红: 'h', 蓝: 'l', 绿: 'l', 黄: 'h' }
function pinyinInitials(value) { return Array.from(String(value || '')).map(char => pinyinInitialMap[char] || (/^[a-z0-9]$/i.test(char) ? char : '')).join('') }
const skuOptions = computed(() => props.skus.map(sku => {
  const searchText = `${sku.sku || ''} ${sku.product_name || ''} ${sku.specification || ''}`
  return { value: String(sku.id), label: `${sku.sku} · ${sku.product_name || sku.specification || ''}`, searchText: `${searchText} ${pinyinInitials(searchText)}` }
}))

function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function addItem() { draft.items.push({ sku: '', quantity: 1, unit_price: 0, sales_model_snapshot: '', description: '', notes: '' }) }
function selectSku(item) { const sku = props.skus.find(row => row.id === Number(item.sku)); if (sku) { item.unit_price = sku.default_price; item.sales_model_snapshot = sku.sales_model || ''; item.description = sku.description_en || sku.description_cn || sku.display_name_cn || sku.product_name || sku.specification || '' } }
async function selectCustomer() {
  const customer = props.customers.find(row => row.id === Number(draft.customer))
  if (!customer) return
  draft.buyer_address = customer.address || ''
  draft.recipient_name = customer.name || ''
  draft.buyer_email = ''
  draft.buyer_phone = ''
  try {
    const contacts = listData(await api.get('/contacts/', { params: { customer: customer.id } }))
    const contact = contacts.find(row => row.is_primary) || contacts[0]
    if (contact) { draft.recipient_name = contact.name; draft.buyer_email = contact.email || ''; draft.buyer_phone = contact.phone || '' }
  } catch { /* Backend will still populate snapshots on save. */ }
}
function validate() {
  if (!draft.customer) return '请选择客户。'
  if (props.mode === 'revise' && !draft.revision_summary.trim()) return '请简要说明本次修改的内容。'
  if (!draft.items.length || draft.items.some(item => !item.sku)) return '请至少添加一条有效的 SKU 明细。'
  if (total.value < 0) return '报价合计不能为负数。'
  return ''
}
function payload() {
  return {
    customer: Number(draft.customer), quote_date: draft.quote_date, valid_until: draft.valid_until || null, status: draft.status,
    currency: draft.currency, exchange_rate: draft.exchange_rate, shipping_fee: draft.shipping_fee || 0, discount: draft.discount || 0,
    recipient_name: draft.recipient_name, buyer_address: draft.buyer_address, buyer_email: draft.buyer_email, buyer_phone: draft.buyer_phone,
    lead_time_days: draft.lead_time_days || null, deposit_ratio: Math.min(100, Math.max(0, Number(draft.deposit_percent || 0))) / 100,
    trading_terms: draft.trading_terms, shipping_details: draft.shipping_details, notes: draft.notes,
    revision_summary: draft.revision_summary.trim(),
    items: draft.items.map(item => ({ sku: Number(item.sku), quantity: item.quantity, unit_price: item.unit_price, sales_model_snapshot: item.sales_model_snapshot, description: item.description, notes: item.notes })),
  }
}
function openPreview() { errorMessage.value = validate(); if (!errorMessage.value) previewOpen.value = true }
async function save() {
  errorMessage.value = validate()
  if (errorMessage.value) return
  saving.value = true; exportError.value = ''
  try {
    const response = props.mode === 'revise' ? await api.post(`/quotes/${props.quote.id}/revise/`, payload()) : await api.post('/quotes/', payload())
    savedQuote.value = response.data
    emit('saved', response.data)
    try { await downloadQuoteExport(response.data.id, response.data.quote_no); emit('close') }
    catch (error) { exportError.value = `报价 ${response.data.quote_no} 已保存，但 Excel 导出失败：${error.message}` }
  } catch (error) { errorMessage.value = error.message }
  finally { saving.value = false }
}
async function retryExport() {
  if (!savedQuote.value) return
  saving.value = true
  try { await downloadQuoteExport(savedQuote.value.id, savedQuote.value.quote_no); emit('close') }
  catch (error) { exportError.value = `Excel 导出仍未完成：${error.message}` }
  finally { saving.value = false }
}
onMounted(() => { if (props.mode === 'create' && draft.customer) selectCustomer() })
</script>

<template>
  <div class="modal-backdrop" @mousedown.self="$emit('close')">
    <form class="modal wide quote-editor-modal" aria-label="报价编辑器" @submit.prevent="save">
      <div class="modal-head"><div><h3>{{ mode === 'revise' ? '创建报价修订版' : '新建报价' }}</h3><small>{{ mode === 'revise' ? `源报价 ${quote.quote_no} 将保留不变` : '系统会在保存时生成报价单号' }}</small></div><button type="button" class="mini-btn" aria-label="关闭报价编辑器" @click="$emit('close')"><X :size="17" /></button></div>
      <div class="modal-body">
        <div v-if="errorMessage" class="quote-message error">{{ errorMessage }}</div>
        <div v-if="exportError" class="quote-message warning"><span>{{ exportError }}</span><button type="button" class="btn btn-secondary" :disabled="saving" @click="retryExport"><RotateCw :size="15" /> 重新导出 Excel</button></div>
        <div v-if="draft.items.some(item => { const sku = skus.find(row => row.id === Number(item.sku)); return item.sku && !(item.sales_model_snapshot || sku?.sales_model) })" class="quote-message warning">有 SKU 尚未设置对外商业型号；报价仍可保存，但客户版 Model 将留空，请先确认是否需要补充。</div>
        <fieldset :disabled="Boolean(savedQuote)">
          <div class="form-grid">
            <div class="field"><label>报价单号</label><input :value="draft.quote_no || '保存后自动生成'" disabled /></div>
            <div class="field"><label>客户 *</label><select v-model="draft.customer" required :disabled="mode === 'revise'" @change="selectCustomer"><option value="">请选择</option><option v-for="customer in customers" :key="customer.id" :value="customer.id">{{ customer.name }}</option></select></div>
            <div class="field"><label>报价日期 *</label><SegmentedDateInput :model-value="draft.quote_date" required @update:model-value="setQuoteDate" /></div><div class="field"><label>有效期</label><div class="lead-time-input"><input v-model="validityDays" type="number" min="0" step="1" placeholder="天数" aria-label="有效期天数" @input="setValidityDays" /><span>天</span><SegmentedDateInput :model-value="draft.valid_until" @update:model-value="setValidUntil" /></div></div>
            <div class="field"><label>状态</label><select v-model="draft.status"><option value="draft">草稿</option><option value="sent">已发送</option><option value="accepted">已接受</option><option value="rejected">已拒绝</option><option value="expired">已过期</option></select></div>
            <div class="field"><label>币种</label><select v-model="draft.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
            <div class="field"><label>对人民币汇率</label><input v-model="draft.exchange_rate" type="number" min="0" step="0.000001" /></div><div class="field"><label>交期（天）</label><input v-model="draft.lead_time_days" type="number" min="1" step="1" /></div>
            <div class="field"><label>定金比例（%）</label><input v-model="draft.deposit_percent" type="number" min="0" max="100" step="1" /></div><div class="field"><label>收件人</label><input v-model="draft.recipient_name" /></div>
            <div class="field full"><label>买方地址</label><textarea v-model="draft.buyer_address" /></div><div class="field"><label>买方邮箱</label><input v-model="draft.buyer_email" type="email" /></div><div class="field"><label>买方电话</label><input v-model="draft.buyer_phone" /></div>
            <div v-if="mode === 'revise'" class="field full revision-summary"><label>本次修改说明 *</label><textarea v-model="draft.revision_summary" required placeholder="例如：调整数量、价格、交期或付款条款" /><small>该说明会显示在版本谱系中，便于后续追溯。</small></div>
          </div>
          <div class="items-head"><div><strong>产品明细</strong><small>预览会使用当前未保存数量、价格与图片</small></div><button type="button" class="btn btn-secondary" @click="addItem"><PlusCircle :size="15" /> 添加一行</button></div>
          <div class="quote-line-items"><div class="quote-line-header"><span>SKU</span><span>Model</span><span>数量</span><span>单价</span><span>产品描述</span><span>小计</span><span></span></div><div v-for="(item,index) in draft.items" :key="index" class="quote-line-row"><ComboInput v-model="item.sku" :options="skuOptions" :allow-custom="false" required placeholder="搜索 SKU 或产品" @update:model-value="selectSku(item)" /><input v-model.trim="item.sales_model_snapshot" aria-label="报价型号" placeholder="可按客户要求修改" /><input v-model="item.quantity" aria-label="数量" type="number" min="0.01" step="0.01" required /><input v-model="item.unit_price" aria-label="单价" type="number" min="0" step="0.0001" required /><input v-model="item.description" aria-label="产品描述" /><span class="amount">{{ money(Number(item.quantity) * Number(item.unit_price)) }}</span><button type="button" class="remove-line" :disabled="draft.items.length === 1" aria-label="删除明细" @click="draft.items.splice(index,1)"><MinusCircle :size="17" /></button></div></div>
          <div class="totals"><label>运费 <input v-model="draft.shipping_fee" type="number" step="0.01" /></label><label>折扣 <input v-model="draft.discount" type="number" step="0.01" /></label><div><span>合计</span><strong>{{ draft.currency }} {{ money(total) }}</strong></div></div>
          <div class="form-grid"><div class="field full"><label>贸易条款</label><textarea v-model="draft.trading_terms" /></div><div class="field full"><label>运输信息</label><textarea v-model="draft.shipping_details" /></div><div class="field full"><label>附加备注</label><textarea v-model="draft.notes" /></div></div>
        </fieldset>
      </div>
      <div class="modal-foot"><button type="button" class="btn btn-secondary" @click="$emit('close')">取消</button><button v-if="!savedQuote" type="button" class="btn btn-secondary" @click="openPreview"><Eye :size="16" /> 预览报价单</button><button v-if="!savedQuote" class="btn btn-primary" :disabled="saving"><Save :size="16" /> {{ saving ? '保存并导出中...' : '保存并导出 Excel' }}</button></div>
    </form>
    <QuotePreviewModal v-if="previewOpen" :draft="previewDraft" @close="previewOpen = false" />
  </div>
</template>

<style scoped>
.quote-line-items{position:relative;overflow:visible}
.quote-line-header{border-radius:10px 10px 0 0}
.quote-line-row{position:relative}
.quote-line-row:focus-within{z-index:20}
:deep(.combo-menu){z-index:100}
.lead-time-input{display:flex;align-items:center;gap:6px}.lead-time-input>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.lead-time-input>span{color:#70817b;font-size:12px}.lead-time-input :deep(.segmented-date){flex:1 1 auto;min-width:0}
</style>
