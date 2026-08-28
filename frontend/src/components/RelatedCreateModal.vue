<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { MinusCircle, PlusCircle, X } from 'lucide-vue-next'
import { api, listData } from '../api'
import { resourceConfigs } from '../resourceConfigs'
import ComboInput from './ComboInput.vue'
import SimpleRichTextEditor from './SimpleRichTextEditor.vue'
import SegmentedDateInput from './SegmentedDateInput.vue'
import { addDays, daysBetween } from '../utils/orderDate'

const props = defineProps({ entity: String, query: { type: Object, default: () => ({}) } })
const emit = defineEmits(['close', 'saved'])
const saving = ref(false)
const loading = ref(true)
const error = ref('')
const options = reactive({})
const form = reactive({})
const customers = ref([])
const skus = ref([])
const quotes = ref([])
const documentDurationDays = ref('')

const config = computed(() => resourceConfigs[props.entity])
const isDocument = computed(() => ['orders', 'quotes'].includes(props.entity))
const isOrder = computed(() => props.entity === 'orders')
const titleNames = {
  contacts: '联系人',
  'follow-ups': '跟进记录',
  transactions: '财务流水',
  'inventory-movements': '库存流水',
  skus: 'SKU',
  'product-parameters': '产品参数',
  'product-certificates': '产品证书',
  categories: '产品分类',
  orders: '订单',
  quotes: '报价',
}
const title = computed(() => `新增${titleNames[props.entity] || config.value?.title || '记录'}`)
const documentCopy = computed(() => isOrder.value ? {
  no: 'order_no', date: 'order_date', statuses: { draft: '草稿', confirmed: '已确认', production: '生产中', shipped: '已发货', completed: '已完成', cancelled: '已取消' },
} : {
  no: 'quote_no', date: 'quote_date', statuses: { draft: '草稿', sent: '已发送', accepted: '已接受', rejected: '已拒绝', expired: '已过期' },
})
const subtotal = computed(() => (form.items || []).reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0))
const total = computed(() => subtotal.value + Number(form.shipping_fee || 0) - Number(form.discount || 0))

function dateParts() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return { now, y, date: `${y}-${m}-${d}` }
}
function datetimeLocal() {
  const { now, date } = dateParts()
  return `${date}T${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}
function visibleOptions(field) {
  const rows = options[field[4]] || []
  if (props.entity === 'follow-ups' && field[0] === 'contact' && form.customer) {
    return rows.filter(row => Number(row.customer) === Number(form.customer))
  }
  return rows
}
function applyDefaultContact() {
  if (props.entity !== 'follow-ups' || !form.customer) return
  const rows = (options.contacts || []).filter(row => Number(row.customer) === Number(form.customer))
  form.contact = (rows.find(row => row.is_primary) || rows[0])?.id || ''
}
function onFieldChange(field) {
  if (props.entity === 'follow-ups' && field[0] === 'customer') applyDefaultContact()
}
async function initGeneric() {
  config.value.fields.forEach(([name, , type, , extra]) => {
    form[name] = type === 'checkbox'
      ? name === 'active'
      : type === 'select'
        ? Object.keys(extra)[0]
        : (props.query[name] || '')
  })
  if (props.entity === 'follow-ups' && !form.followed_at) form.followed_at = datetimeLocal()
  const optionFields = config.value.fields.filter(field => ['remote', 'combo'].includes(field[2]))
  await Promise.all(optionFields.map(async field => {
    options[field[4]] = listData(await api.get(`/${field[4]}/`))
  }))
  if (props.entity === 'contacts' && form.customer) {
    const existing = listData(await api.get('/contacts/', { params: { customer: form.customer } }))
    form.is_primary = existing.length === 0
  }
  if (props.entity === 'follow-ups') {
    form.owner = (await api.get('/session/current-operator/')).data.name || ''
    applyDefaultContact()
  }
}
async function initDocument() {
  const { y, date } = dateParts()
  const calls = [api.get('/customers/'), api.get('/skus/')]
  if (isOrder.value) calls.push(api.get('/quotes/'))
  const result = await Promise.all(calls)
  customers.value = listData(result[0])
  skus.value = listData(result[1])
  quotes.value = result[2] ? listData(result[2]) : []
  Object.assign(form, {
    customer: props.query.customer || '',
    [documentCopy.value.no]: `${isOrder.value ? 'SO' : 'QT'}-${y}-${String(Date.now()).slice(-5)}`,
    [documentCopy.value.date]: date,
    status: isOrder.value ? 'confirmed' : 'draft',
    currency: 'USD', exchange_rate: '7.20', shipping_fee: 0, discount: 0, notes: '',
    items: [{ sku: '', quantity: 1, unit_price: 0, cost_price: 0, notes: '' }],
  })
  if (isOrder.value) Object.assign(form, { quote: props.query.quote || '', expected_ship_date: '' })
  else form.valid_until = addDays(date, 30)
  documentDurationDays.value = daysBetween(form[documentCopy.value.date], form[isOrder.value ? 'expected_ship_date' : 'valid_until'])
}
async function init() {
  try {
    if (isDocument.value) await initDocument()
    else await initGeneric()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
function selectSku(item) {
  const sku = skus.value.find(row => row.id === Number(item.sku))
  if (sku) {
    item.unit_price = sku.default_price
    item.cost_price = sku.cost_price
  }
}
function setDocumentDate(value) {
  form[documentCopy.value.date] = value
  const target = isOrder.value ? 'expected_ship_date' : 'valid_until'
  if (documentDurationDays.value !== '') form[target] = addDays(value, documentDurationDays.value)
  else if (form[target]) documentDurationDays.value = daysBetween(value, form[target])
}
function setDocumentTargetDate(value) {
  const target = isOrder.value ? 'expected_ship_date' : 'valid_until'
  form[target] = value
  documentDurationDays.value = daysBetween(form[documentCopy.value.date], value)
}
function setDocumentDurationDays() {
  if (documentDurationDays.value === '' || !form[documentCopy.value.date]) return
  form[isOrder.value ? 'expected_ship_date' : 'valid_until'] = addDays(form[documentCopy.value.date], documentDurationDays.value)
}
function payloadGeneric() {
  const data = {}
  config.value.fields.forEach(([name, , type]) => {
    let value = form[name]
    if (type === 'remote') value = value ? Number(value) : null
    if (type === 'number') value = value === '' ? 0 : value
    if (type === 'datetime-local' && value && value.length === 16) value += ':00+08:00'
    data[name] = value
  })
  return data
}
async function save() {
  saving.value = true
  error.value = ''
  try {
    let response
    if (isDocument.value) {
      if (!form.items.length || form.items.some(item => !item.sku)) throw new Error('请至少添加一条有效的 SKU 明细。')
      const data = { ...form, customer: Number(form.customer), items: form.items.map(item => ({ ...item, sku: Number(item.sku) })) }
      if (isOrder.value) data.quote = form.quote ? Number(form.quote) : null
      response = await api.post(`/${props.entity}/`, data)
    } else {
      response = await api.post(`/${config.value.endpoint}/`, payloadGeneric())
    }
    emit('saved', response.data)
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}
function money(value) {
  return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
onMounted(init)
</script>

<template>
  <Teleport to="body">
    <div class="modal-backdrop related-create-backdrop" @mousedown.self="emit('close')">
      <form class="modal related-create-modal" @submit.prevent="save">
        <div class="modal-head">
          <h3>{{ title }}</h3>
          <button type="button" class="mini-btn" @click="emit('close')"><X :size="17" /></button>
        </div>
        <div class="modal-body">
          <div v-if="error" class="inline-error">{{ error }}</div>
          <div v-if="loading" class="modal-loading">正在加载...</div>

          <template v-else-if="!isDocument && config">
            <div class="form-grid">
              <div v-for="field in config.fields" :key="field[0]" class="field" :class="{ full: field[2] === 'textarea' || (entity === 'follow-ups' && field[0] === 'subject') }">
                <label>{{ field[1] }} <em v-if="field[3]">*</em></label>
                <textarea v-if="field[2] === 'textarea'" v-model="form[field[0]]" :required="field[3]" />
                <SimpleRichTextEditor v-else-if="field[2] === 'richtext'" v-model="form[field[0]]" />
                <ComboInput v-else-if="field[2] === 'combo'" v-model="form[field[0]]" :options="options[field[4]] || []" :required="field[3]" />
                <select v-else-if="field[2] === 'select'" v-model="form[field[0]]" :required="field[3]">
                  <option v-for="(label, key) in field[4]" :key="key" :value="key">{{ label }}</option>
                </select>
                <select v-else-if="field[2] === 'remote'" v-model="form[field[0]]" :required="field[3]" @change="onFieldChange(field)">
                  <option value="">请选择</option>
                  <option v-for="option in visibleOptions(field)" :key="option.id" :value="option.id">{{ option[field[5]] }}</option>
                </select>
                <label v-else-if="field[2] === 'checkbox'" class="checkbox-line"><input v-model="form[field[0]]" type="checkbox" /> 是</label>
                <SegmentedDateInput v-else-if="field[2] === 'date' || field[2] === 'datetime-local'" v-model="form[field[0]]" :required="field[3]" :with-time="field[2] === 'datetime-local'" />
                <input v-else v-model="form[field[0]]" :type="field[2] || 'text'" :step="field[2] === 'number' ? '0.0001' : undefined" :required="field[3]" />
              </div>
            </div>
          </template>

          <template v-else-if="isDocument">
            <div class="form-grid">
              <div class="field"><label>{{ isOrder ? '订单号' : '报价单号' }} *</label><input v-model="form[documentCopy.no]" required /></div>
              <div class="field"><label>客户 *</label><select v-model="form.customer" required><option value="">请选择</option><option v-for="customer in customers" :key="customer.id" :value="customer.id">{{ customer.name }}</option></select></div>
              <div class="field"><label>{{ isOrder ? '订单日期' : '报价日期' }} *</label><SegmentedDateInput :model-value="form[documentCopy.date]" required @update:model-value="setDocumentDate" /></div>
              <div class="field"><label>{{ isOrder ? '预计交期' : '有效期' }}</label><div class="lead-time-input"><input v-model="documentDurationDays" type="number" min="0" step="1" placeholder="天数" :aria-label="isOrder ? '交期天数' : '有效期天数'" @input="setDocumentDurationDays" /><span>天</span><SegmentedDateInput :model-value="form[isOrder ? 'expected_ship_date' : 'valid_until']" @update:model-value="setDocumentTargetDate" /></div></div>
              <div class="field"><label>状态 *</label><select v-model="form.status"><option v-for="(label, key) in documentCopy.statuses" :key="key" :value="key">{{ label }}</option></select></div>
              <div v-if="isOrder" class="field"><label>来源报价</label><select v-model="form.quote"><option value="">无</option><option v-for="quote in quotes" :key="quote.id" :value="quote.id">{{ quote.quote_no }}</option></select></div>
              <div class="field"><label>币种</label><select v-model="form.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
              <div class="field"><label>对人民币汇率</label><input v-model="form.exchange_rate" type="number" step="0.000001" /></div>
            </div>
            <div class="quick-items-head">
              <strong>产品明细</strong>
              <button type="button" class="btn btn-secondary" @click="form.items.push({ sku: '', quantity: 1, unit_price: 0, cost_price: 0, notes: '' })"><PlusCircle :size="15" /> 添加一行</button>
            </div>
            <div class="quick-lines">
              <div v-for="(item, index) in form.items" :key="index" class="quick-line" :class="{ order: isOrder }">
                <select v-model="item.sku" required @change="selectSku(item)"><option value="">选择 SKU</option><option v-for="sku in skus" :key="sku.id" :value="sku.id">{{ sku.sku }} · {{ sku.product_name }}</option></select>
                <input v-model="item.quantity" type="number" min="0.01" step="0.01" />
                <input v-model="item.unit_price" type="number" min="0" step="0.0001" />
                <input v-if="isOrder" v-model="item.cost_price" type="number" min="0" step="0.0001" />
                <span>{{ form.currency }} {{ money(Number(item.quantity) * Number(item.unit_price)) }}</span>
                <button type="button" :disabled="form.items.length === 1" @click="form.items.splice(index, 1)"><MinusCircle :size="17" /></button>
              </div>
            </div>
            <div class="quick-totals">
              <label>运费 <input v-model="form.shipping_fee" type="number" step="0.01" /></label>
              <label>折扣 <input v-model="form.discount" type="number" step="0.01" /></label>
              <strong>合计 {{ form.currency }} {{ money(total) }}</strong>
            </div>
            <div class="field full"><label>条款 / 备注</label><textarea v-model="form.notes" /></div>
          </template>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn btn-secondary" @click="emit('close')">取消</button>
          <button class="btn btn-primary" :disabled="saving || loading">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<style scoped>
.related-create-backdrop{z-index:85}.related-create-modal{width:min(1120px,calc(100% - 48px));max-height:94vh}.inline-error{margin-bottom:14px;padding:10px 12px;background:#fff0f0;color:#a84444;border-radius:8px;font-size:12px}.modal-loading{padding:50px;text-align:center;color:#74847e}.lead-time-input{display:flex;align-items:center;gap:6px}.lead-time-input>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.lead-time-input>span{color:#70817b;font-size:12px}.lead-time-input :deep(.segmented-date){flex:1 1 auto;min-width:0}.quick-items-head{display:flex;align-items:center;justify-content:space-between;margin:24px 0 9px;padding-top:18px;border-top:1px solid #e3e8e4}.quick-items-head strong{font-size:14px}.quick-lines{border:1px solid #e0e6e2;border-radius:9px;overflow:hidden}.quick-line{display:grid;grid-template-columns:2fr .6fr .8fr 1fr 32px;gap:8px;align-items:center;padding:9px;border-top:1px solid #edf0ee}.quick-line:first-child{border-top:0}.quick-line.order{grid-template-columns:2fr .55fr .7fr .7fr 1fr 32px}.quick-line select,.quick-line input{min-width:0;width:100%;padding:8px;border:1px solid #dce3df;border-radius:7px}.quick-line span{text-align:right;font-size:11px;font-weight:600}.quick-line button{border:0;background:transparent;color:#b05b5b}.quick-line button:disabled{opacity:.25}.quick-totals{display:flex;justify-content:flex-end;align-items:end;gap:13px;margin:14px 0 20px}.quick-totals label{font-size:10px;color:#788680}.quick-totals input{display:block;width:100px;margin-top:4px;padding:7px;border:1px solid #dce3df;border-radius:7px}.quick-totals strong{padding:8px 0 8px 16px;border-left:1px solid #dce3df;color:#173f36}.related-create-modal :deep(.simple-editor textarea){min-height:155px}
@media(max-width:700px){.related-create-modal{width:100%;height:100%;max-height:100%;border-radius:0}.quick-lines{overflow:auto}.quick-line,.quick-line.order{min-width:750px}.quick-totals{flex-wrap:wrap}}
</style>
