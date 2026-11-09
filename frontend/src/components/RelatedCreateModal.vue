<script setup>
import { useWorkspaceTeleportDisabled } from "../composables/useWorkspaceTeleport"
const workspaceTeleportDisabled = useWorkspaceTeleportDisabled()
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, listAll } = useWorkspaceApi()
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'

import { followUpError } from '../utils/followUpSafety'
import TradeUnitPicker from './TradeUnitPicker.vue'
import { fromTradeLine, tradePayload, withDefaultTradeUnit, restoreTradeLines } from '../utils/tradeUnits'
import CategoryMultiPicker from "./CategoryMultiPicker.vue"
import { computed, onMounted, reactive, ref } from 'vue'
import { MinusCircle, Paperclip, X } from 'lucide-vue-next'
import { listData } from '../api'
import QuoteEditorModal from './QuoteEditorModal.vue'
import { resourceConfigs } from '../resourceConfigs'
import ComboInput from './ComboInput.vue'
import SkuPickerPanel from './SkuPickerPanel.vue'
import SimpleRichTextEditor from './SimpleRichTextEditor.vue'
import SegmentedDateInput from './SegmentedDateInput.vue'
import { addDays, daysBetween } from '../utils/orderDate'
import { useAccessControl } from '../accessControl'

const props = defineProps({ entity: String, query: { type: Object, default: () => ({}) } })
const emit = defineEmits(['close', 'saved'])
const { can } = useAccessControl()
const saving = ref(false)
const loading = ref(true)
const error = ref('')
const options = reactive({})
const form = reactive({})
const guard = useUnsavedChangesGuard({ data: () => ({ form, files: pendingFollowUpFiles.value }), enabled: () => !loading.value && !isQuote.value })
const requestClose = () => guard.requestClose(() => emit('close'))
const customers = ref([])
const skus = ref([])
const quotes = ref([])
const documentDurationDays = ref('')
const followUpDays = ref('')
const currentFollowUpPlan = computed(() => (options.customers || []).find(customer => String(customer.id) === String(form.customer))?.next_follow_up)
function visibleGenericField(field) { return !(props.entity === 'follow-ups' && field[0] === 'next_follow_up' && form.next_follow_up_mode !== 'set') }
function changeFollowUpMode() { if (form.next_follow_up_mode !== 'set') { form.next_follow_up = ''; followUpDays.value = '' } }
const pendingFollowUpFiles = ref([])
const usdCnyReference = ref(null)
const loadingUsdCnyReference = ref(false)
const activeSkuId = ref('')
const tailPolicyHelpOpen = ref(false)
const tailPolicyLabels = { SAME_CARTON: '整箱优先', REPACK: '尾箱待确认', MANUAL: '人工装箱' }

const config = computed(() => resourceConfigs[props.entity])
const accessModule = computed(() => ({ 'follow-ups': 'followups', 'product-parameters': 'parameters', 'product-certificates': 'certificates', 'purchase-orders': 'purchases' }[props.entity] || props.entity))
const isQuote = computed(() => props.entity === 'quotes')
const isDocument = computed(() => props.entity === 'orders')
const quoteSeed = ref(null)
const savedQuote = ref(null)
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
const title = computed(() => props.entity === 'follow-ups' ? '新建跟进记录' : props.entity === 'orders' ? '新建订单' : `新增${titleNames[props.entity] || config.value?.title || '记录'}`)
const documentCopy = computed(() => isOrder.value ? {
  no: 'order_no', date: 'order_date', statuses: { draft: '草稿', confirmed: '已确认', production: '生产中', shipped: '已发货', completed: '已完成', cancelled: '已取消' },
} : {
  no: 'quote_no', date: 'quote_date', statuses: { draft: '草稿', sent: '已发送', accepted: '已接受', rejected: '已拒绝', expired: '已过期' },
})
const subtotal = computed(() => (form.items || []).reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0))
const total = computed(() => subtotal.value + Number(form.shipping_fee || 0) - Number(form.discount || 0))
const visibleDocumentSkus = computed(() => {
  const skuId = props.query?.sku
  const productId = props.query?.product
  if (skuId) return skus.value.filter(row => Number(row.id) === Number(skuId))
  if (productId) return skus.value.filter(row => Number(row.product) === Number(productId))
  return skus.value
})
const selectedSkuIds = computed({
  get: () => [...new Set((form.items || []).map(item => String(item.sku || '')).filter(Boolean))],
  set: syncSelectedSkus,
})

function syncSelectedSkus(ids) {
  const selected = [...new Set((ids || []).map(String))]
  const previousLines = [...(form.items || [])]
  const existing = new Map((form.items || []).map(item => [String(item.sku), item]))
  form.items = selected.map(id => existing.get(id) || (() => {
    const item = { sku: Number(id), quantity: 1, unit_price: 0, cost_price: 0, notes: '' }
    selectSku(item)
    return withDefaultTradeUnit(item, skus.value.find(s => s.id === Number(id)))
  })())
  form.items = restoreTradeLines(form.items, previousLines)
  if (!selected.includes(String(activeSkuId.value))) activeSkuId.value = selected[0] || ''
}

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
function syncFollowUpDaysFromDate() {
  if (props.entity !== 'follow-ups') return
  const startDate = String(form.followed_at || '').slice(0, 10)
  followUpDays.value = startDate && form.next_follow_up ? daysBetween(startDate, form.next_follow_up) : ''
}
function updateFollowUpDate() {
  if (props.entity !== 'follow-ups') return
  const startDate = String(form.followed_at || '').slice(0, 10)
  if (!startDate || followUpDays.value === '' || followUpDays.value === null) {
    form.next_follow_up = ''
    return
  }
  form.next_follow_up = addDays(startDate, followUpDays.value)
}
function setFollowUpDate(value) {
  form.next_follow_up = value
  syncFollowUpDaysFromDate()
}
function addFollowUpFiles(files) {
  if (props.entity !== 'follow-ups') return
  const additions = Array.from(files || []).filter(file => file?.name && file.size <= 20 * 1024 * 1024)
  const rejected = Array.from(files || []).filter(file => file?.size > 20 * 1024 * 1024)
  if (rejected.length) error.value = '单个附件不能超过 20 MB。'
  const existingKeys = new Set(pendingFollowUpFiles.value.map(file => `${file.name}:${file.size}:${file.lastModified}`))
  pendingFollowUpFiles.value = [...pendingFollowUpFiles.value, ...additions.filter(file => {
    const key = `${file.name}:${file.size}:${file.lastModified}`
    if (existingKeys.has(key)) return false
    existingKeys.add(key)
    return true
  })]
}
function removePendingFollowUpFile(index) { pendingFollowUpFiles.value.splice(index, 1) }
function onFollowUpFileInput(event) {
  addFollowUpFiles(event.target.files)
  event.target.value = ''
}
function onFollowUpFileDrop(event) { addFollowUpFiles(event.dataTransfer?.files) }
async function uploadFollowUpFiles(id) {
  if (props.entity !== 'follow-ups' || !id || !pendingFollowUpFiles.value.length) return
  const data = new FormData()
  pendingFollowUpFiles.value.forEach(file => data.append('files', file, file.name))
  await api.post(`/follow-ups/${id}/attachments/`, data, { timeout: 120000 })
  pendingFollowUpFiles.value = []
}
function onDateFieldChange(field, value) {
  form[field[0]] = value
  if (props.entity === 'follow-ups' && field[0] === 'followed_at') syncFollowUpDaysFromDate()
}
function visibleOptions(field) {
  const rows = options[field[4]] || []
  if (props.entity === 'follow-ups' && field[0] === 'contact' && form.customer) {
    return rows.filter(row => Number(row.customer) === Number(form.customer))
  }
  if (props.entity === 'inventory-movements' && field[0] === 'sku' && props.query?.product) {
    return rows.filter(row => Number(row.product) === Number(props.query.product))
  }
  return rows
}
function isInherited(fieldName) {
  const value = props.query?.[fieldName]
  return value !== undefined && value !== null && value !== ''
}
function applyDefaultContact() {
  if (props.entity !== 'follow-ups' || !form.customer) return
  if (isInherited('contact')) return
  const rows = (options.contacts || []).filter(row => Number(row.customer) === Number(form.customer))
  form.contact = (rows.find(row => row.is_primary) || rows[0])?.id || ''
}
function onFieldChange(field) {
  if (props.entity === 'follow-ups' && field[0] === 'customer') {
    const contactQuery = props.query?.contact
    if (contactQuery === undefined || contactQuery === null || contactQuery === '') applyDefaultContact()
  }
}
async function initGeneric() {
  config.value.fields.forEach(([name, , type, , extra]) => {
    form[name] = type === 'remote_multi' ? [] : type === 'checkbox'
      ? name === 'active'
      : type === 'select'
        ? Object.keys(extra)[0]
        : type === 'followup_schedule' ? 'keep' : (props.query[name] || '')
  })
  if (props.entity === 'follow-ups' && !form.followed_at) form.followed_at = datetimeLocal()
  const optionFields = config.value.fields.filter(field => ['remote', 'combo', 'remote_multi'].includes(field[2]))
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
    syncFollowUpDaysFromDate()
  }
}
async function initDocument() {
  const { date } = dateParts()
  const calls = [api.get('/customers/'), api.get('/skus/')]
  if (isOrder.value) calls.push(api.get('/quotes/'))
  const result = await Promise.all(calls)
  customers.value = listData(result[0])
  skus.value = listData(result[1])
  quotes.value = result[2] ? listData(result[2]) : []
  Object.assign(form, {
    customer: props.query.customer || '',
    [documentCopy.value.date]: date,
    status: 'draft',
    currency: 'USD', exchange_rate: '7.20', shipping_fee: 0, discount: 0, notes: '',
    items: props.query.sku ? [{ sku: props.query.sku, quantity: 1, unit_price: 0, cost_price: 0, notes: '' }] : [],
  })
  activeSkuId.value = props.query.sku ? String(props.query.sku) : ''
  if (isOrder.value) Object.assign(form, { quote: props.query.quote || '', expected_ship_date: '', tail_goods_policy: 'SAME_CARTON' })
  else form.valid_until = addDays(date, 30)
  if (form.items[0]?.sku) selectSku(form.items[0])
  documentDurationDays.value = daysBetween(form[documentCopy.value.date], form[isOrder.value ? 'expected_ship_date' : 'valid_until'])
  if (!isOrder.value) void loadUsdCnyReference()
}
async function loadUsdCnyReference() {
  loadingUsdCnyReference.value = true
  try { usdCnyReference.value = (await api.get('/exchange-rates/usd-cny/')).data }
  catch { usdCnyReference.value = null }
  finally { loadingUsdCnyReference.value = false }
}
function applyUsdCnyReference() { if (usdCnyReference.value?.rate) form.exchange_rate = usdCnyReference.value.rate }
async function init() {
  loading.value = true
  error.value = ''
  try {
    if (isQuote.value) await initQuote()
    else if (isDocument.value) await initDocument()
    else await initGeneric()
  } catch (e) {
    error.value = e.message
  } finally {
    guard.markClean()
    loading.value = false
  }
}
async function initQuote() {
  const [customerRows, skuRows] = await Promise.all([listAll('/customers/'), listAll('/skus/')])
  customers.value = customerRows
  skus.value = skuRows
  const sku = skuRows.find(row => Number(row.id) === Number(props.query.sku))
  quoteSeed.value = {
    customer: props.query.customer ? Number(props.query.customer) : '',
    items: sku ? [{ sku: sku.id, quantity: 1, unit_price: sku.default_price || 0, sales_model_snapshot: sku.sales_model || '', description: sku.description_en || sku.description_cn || sku.display_name_cn || sku.product_name || sku.specification || '', notes: '' }] : [],
  }
}
function closeQuote() {
  // Keep export failures and retry controls visible until the editor closes.
  if (savedQuote.value) emit('saved', savedQuote.value)
  else emit('close')
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
    if (type === 'remote_multi') value = (value || []).map(Number)
    if (type === 'remote') value = value ? Number(value) : null
    if (type === 'number') value = value === '' ? 0 : value
    if (type === 'date' && value === '') value = null
    if (type === 'datetime-local' && value && value.length === 16) value += ':00+08:00'
    if (props.entity === 'follow-ups' && name === 'next_follow_up' && form.next_follow_up_mode !== 'set') value = null
    data[name] = value
  })
  return data
}
async function save() {
  if (!can(accessModule.value, 'create')) return
  if (isQuote.value) return
  if (props.entity === 'follow-ups' && followUpError(form)) { error.value = followUpError(form); return }
  saving.value = true
  error.value = ''
  try {
    let response
    if (isDocument.value) {
      if (!form.items.length || form.items.some(item => !item.sku)) throw new Error('请至少添加一条有效的 SKU 明细。')
      const data = { ...form, customer: Number(form.customer), items: form.items.map(item => tradePayload({ ...item, sku: Number(item.sku) })) }
      if (isOrder.value) { data.quote = form.quote ? Number(form.quote) : null; delete data.order_no; delete data.status }
      response = await api.post(`/${props.entity}/`, data)
    } else {
      response = await api.post(`/${config.value.endpoint}/`, payloadGeneric())
    }
    guard.markClean()
    if (props.entity === 'follow-ups' && pendingFollowUpFiles.value.length) {
      try {
        await uploadFollowUpFiles(response.data.id)
      } catch (uploadError) {
        error.value = `记录已保存，但${uploadError.message || '附件上传失败'}`
        return
      }
    }
    guard.markClean()
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
function formatAttachmentSize(value) {
  const size = Number(value || 0)
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
onMounted(init)
</script>

<template>
  <Teleport to="body" :disabled="workspaceTeleportDisabled">
    <QuoteEditorModal v-if="isQuote && can('quotes', 'create') && !loading && !error" class="related-quote-editor" :quote="quoteSeed" :customers="customers" :skus="visibleDocumentSkus" mode="create" @saved="savedQuote = $event" @close="closeQuote" />
    <div v-else-if="can(accessModule, 'create')" class="modal-backdrop related-create-backdrop">
      <form class="modal related-create-modal" @submit.prevent="save">
        <div class="modal-head">
          <h3>{{ title }}</h3>
          <button type="button" class="mini-btn" @click="requestClose"><X :size="17" /></button>
        </div>
        <div class="modal-body">
          <div v-if="error" class="inline-error">{{ error }}</div>
          <div v-if="loading" class="modal-loading">正在加载...</div>

          <template v-else-if="!isQuote && !isDocument && config">
            <div class="form-grid">
              <div v-for="field in config.fields.filter(visibleGenericField)" :key="field[0]" class="field" :class="{ full: ['textarea', 'remote_multi'].includes(field[2]) || (entity === 'follow-ups' && ['subject', 'next_follow_up_mode'].includes(field[0])) }">
                <label>{{ field[1] }} <em v-if="field[3]">*</em></label>
                <div v-if="field[2] === 'followup_schedule'" class="follow-up-schedule" role="radiogroup" aria-label="下次跟进安排">
                  <label v-for="(label, mode) in { keep: '保留当前计划', set: '设置新的跟进日期', clear: '暂不安排后续跟进' }" :key="mode"><input v-model="form.next_follow_up_mode" type="radio" name="next_follow_up_mode" :value="mode" @change="changeFollowUpMode" /> {{ label }}</label>
                  <p v-if="form.next_follow_up_mode === 'keep'">当前计划：{{ currentFollowUpPlan || '暂无跟进日期' }}</p>
                  <p v-else-if="form.next_follow_up_mode === 'clear'">这会清除该客户当前的下次跟进日期。</p>
                </div>
                <textarea v-else-if="field[2] === 'textarea'" v-model="form[field[0]]" :required="field[3]" :disabled="isInherited(field[0])" />
                <SimpleRichTextEditor v-else-if="field[2] === 'richtext'" v-model="form[field[0]]" @paste-files="addFollowUpFiles" />
                <ComboInput v-else-if="field[2] === 'combo'" v-model="form[field[0]]" :options="options[field[4]] || []" :required="field[3]" :disabled="isInherited(field[0])" />
                <select v-else-if="field[2] === 'select'" v-model="form[field[0]]" :required="field[3]" :disabled="isInherited(field[0])">
                  <option v-for="(label, key) in field[4]" :key="key" :value="key">{{ label }}</option>
                </select>
                <CategoryMultiPicker v-else-if="field[2] === 'remote_multi'" v-model="form[field[0]]" :categories="options[field[4]] || []" />
                <select v-else-if="field[2] === 'remote'" v-model="form[field[0]]" :required="field[3]" :disabled="isInherited(field[0])" @change="onFieldChange(field)">
                  <option value="">请选择</option>
                  <option v-for="option in visibleOptions(field)" :key="option.id" :value="option.id">{{ option[field[5]] }}</option>
                </select>
                <label v-else-if="field[2] === 'checkbox'" class="checkbox-line"><input v-model="form[field[0]]" type="checkbox" :disabled="isInherited(field[0])" /> 是</label>
                <div v-else-if="entity === 'follow-ups' && field[0] === 'next_follow_up'" class="follow-up-date-control">
                  <input v-model="followUpDays" type="number" min="0" step="1" placeholder="天数" aria-label="下次跟进天数" @input="updateFollowUpDate" />
                  <span>天后</span>
                  <SegmentedDateInput :model-value="form.next_follow_up" @update:model-value="setFollowUpDate" />
                </div>
                <SegmentedDateInput v-else-if="field[2] === 'date' || field[2] === 'datetime-local'" :model-value="form[field[0]]" :required="field[3]" :with-time="field[2] === 'datetime-local'" @update:model-value="value => onDateFieldChange(field, value)" />
                <input v-else v-model="form[field[0]]" :type="field[2] || 'text'" :step="field[2] === 'number' ? '0.0001' : undefined" :required="field[3]" :disabled="isInherited(field[0])" />
              </div>
            </div>
            <section v-if="entity === 'follow-ups'" class="related-follow-up-attachment-editor" @dragover.prevent @drop.prevent="onFollowUpFileDrop">
              <div class="related-follow-up-attachment-head"><div><strong><Paperclip :size="16" /> 附件</strong><span>支持在编辑器中粘贴图片或附件，也可拖拽、选择文件</span></div><label><Paperclip :size="14" /> 添加附件<input type="file" multiple @change="onFollowUpFileInput" /></label></div>
              <div v-if="pendingFollowUpFiles.length" class="related-follow-up-attachment-list"><div v-for="(file, index) in pendingFollowUpFiles" :key="`${file.name}-${file.size}-${file.lastModified}`"><Paperclip :size="16" /><span><strong>{{ file.name }}</strong><small>待上传 · {{ formatAttachmentSize(file.size) }}</small></span><button type="button" aria-label="移除附件" @click="removePendingFollowUpFile(index)"><X :size="14" /></button></div></div>
              <div v-else class="related-follow-up-attachment-empty"><Paperclip :size="16" /> 尚未添加附件</div>
            </section>
          </template>

          <template v-else-if="isDocument">
            <div class="form-grid">
              <div class="field"><label>{{ isOrder ? '订单号' : '报价单号' }}</label><input v-if="isOrder" value="保存后由系统自动生成" class="readonly-input" readonly /><input v-else value="保存后自动生成" class="readonly-input" disabled /></div>
              <div class="field"><label>客户 *</label><select v-model="form.customer" required :disabled="isInherited('customer')"><option value="">请选择</option><option v-for="customer in customers" :key="customer.id" :value="customer.id">{{ customer.name }}</option></select></div>
              <div class="field"><label>{{ isOrder ? '订单日期' : '报价日期' }} *</label><SegmentedDateInput :model-value="form[documentCopy.date]" required @update:model-value="setDocumentDate" /></div>
              <div class="field"><label>{{ isOrder ? '预计交期' : '有效期' }}</label><div class="lead-time-input"><input v-model="documentDurationDays" type="number" min="0" step="1" placeholder="天数" :aria-label="isOrder ? '交期天数' : '有效期天数'" @input="setDocumentDurationDays" /><span>天</span><SegmentedDateInput :model-value="form[isOrder ? 'expected_ship_date' : 'valid_until']" @update:model-value="setDocumentTargetDate" /></div></div>
              <div class="field"><label>状态 *</label><select v-model="form.status"><option v-for="(label, key) in documentCopy.statuses" :key="key" :value="key">{{ label }}</option></select></div>
              <div v-if="isOrder" class="field"><label>来源报价</label><select v-model="form.quote" :disabled="isInherited('quote')"><option value="">无</option><option v-for="quote in quotes" :key="quote.id" :value="quote.id">{{ quote.quote_no }}</option></select></div>
              <div v-if="isOrder" class="field tail-policy-field"><label>尾货策略 <button type="button" class="policy-help-trigger" aria-label="查看尾货策略说明" @click="tailPolicyHelpOpen = !tailPolicyHelpOpen">?</button></label><select v-model="form.tail_goods_policy"><option v-for="(label, key) in tailPolicyLabels" :key="key" :value="key">{{ label }}</option></select><div v-if="tailPolicyHelpOpen" class="policy-help" role="note"><strong>不同策略的区别</strong><ul><li><b>整箱优先：</b>尾货自动使用标准箱尺寸、皮重和 CBM。</li><li><b>尾箱待确认：</b>保留尾货箱数并标记待确认，尺寸和 CBM 等待补充。</li><li><b>人工装箱：</b>不自动生成尾货箱，余数作为警告交由人工处理。</li></ul><small>此选择对整张订单统一生效，优先于 SKU 包装模板。</small></div></div>
              <div class="field"><label>币种</label><select v-model="form.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
              <div class="field"><label>对人民币汇率 <span v-if="!isOrder" class="rate-reference"><span v-if="loadingUsdCnyReference">正在获取 USD/CNY…</span><template v-else-if="usdCnyReference">参考 USD/CNY {{ Number(usdCnyReference.rate).toFixed(4) }} · {{ usdCnyReference.date }}<button type="button" @click="applyUsdCnyReference">带入</button></template><span v-else>参考汇率暂不可用</span></span></label><input v-model="form.exchange_rate" type="number" step="0.000001" /></div>
            </div>
            <div class="quick-items-head"><div><strong>产品明细</strong><small>先选择一个或多个 SKU，再填写数量与价格。</small></div></div>
            <SkuPickerPanel v-model="selectedSkuIds" v-model:active-id="activeSkuId" :skus="visibleDocumentSkus" />
            <div class="quick-lines">
              <div v-for="(item, index) in form.items" :key="index" class="quick-line" :class="{ order: isOrder }">
                <span class="quick-sku"><b>{{ skus.find(sku => sku.id === Number(item.sku))?.display_name_cn || skus.find(sku => sku.id === Number(item.sku))?.product_name || '—' }}</b><small>SKU: {{ skus.find(sku => sku.id === Number(item.sku))?.sku_code || item.sku || '—' }} · Sales Model: {{ skus.find(sku => sku.id === Number(item.sku))?.sales_model || '—' }}</small><TradeUnitPicker :line="item" :sku="skus.find(sku => sku.id === Number(item.sku))" /><button type="button" class="text-btn" @click="form.items.splice(index + 1, 0, { ...item })">增加规格行</button></span>
                <input v-model="item.quantity" type="number" min="0.01" step="0.01" required />
                <input v-model="item.unit_price" v-money-input type="number" min="0" step="any" required />
                <input v-if="isOrder" v-model="item.cost_price" v-money-input type="number" min="0" step="any" />
                <span>{{ form.currency }} {{ money(Number(item.quantity) * Number(item.unit_price)) }}</span>
                <button type="button" :disabled="isInherited('sku') && index === 0" @click="form.items.splice(index, 1)"><MinusCircle :size="17" /></button>
              </div>
              <p v-if="!form.items.length" class="quick-items-empty">请先从上方选择至少一个 SKU。</p>
            </div>
            <div class="quick-totals">
              <label>运费 <input v-model="form.shipping_fee" v-money-input type="number" step="any" /></label>
              <label>折扣 <input v-model="form.discount" v-money-input type="number" step="any" /></label>
              <strong>合计 {{ form.currency }} {{ money(total) }}</strong>
            </div>
            <div class="field full"><label>条款 / 备注</label><textarea v-model="form.notes" /></div>
          </template>
        </div>
        <div class="modal-foot">
          <p v-if="entity === 'follow-ups' && error" class="follow-up-validation" role="alert">{{ error }}</p>
          <button type="button" class="btn btn-secondary" @click="requestClose">取消</button>
          <button v-if="isQuote && error" type="button" class="btn btn-primary" :disabled="loading" @click="init">重新加载</button>
          <button v-else-if="!isQuote" class="btn btn-primary" :disabled="saving || loading">{{ saving ? '保存中…' : props.entity === 'follow-ups' ? '保存跟进' : '保存' }}</button>
        </div>
      </form>
    </div>
    <p v-else class="related-create-denied" role="alert">无权新建此类记录。</p>
  </Teleport>
</template>

<style scoped>
.follow-up-schedule { display: flex; flex-wrap: wrap; gap: 12px 20px; }
.follow-up-schedule label { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.follow-up-schedule input[type="radio"] { width: 16px; min-width: 16px; height: 16px; min-height: 16px; flex: 0 0 16px; padding: 0; }
.follow-up-schedule p { flex-basis: 100%; margin: 0; color: var(--muted); font-size: var(--text-caption); }
.follow-up-validation { flex: 1; min-width: 0; align-self: center; margin: 0; color: #a23b32; font-size: var(--text-body); }

.related-quote-editor{z-index:85}
.related-create-backdrop{z-index:85}.related-create-modal{width:min(1120px,calc(100% - 48px));max-height:94vh}.inline-error{margin-bottom:14px;padding:10px 12px;background:#fff0f0;color:#a84444;border-radius:8px;font-size:var(--text-body)}.modal-loading{padding:50px;text-align:center;color:#74847e}.lead-time-input,.follow-up-date-control{display:flex;align-items:center;gap:6px}.lead-time-input>input,.follow-up-date-control>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.lead-time-input>span,.follow-up-date-control>span{color:#70817b;font-size:var(--text-body);white-space:nowrap}.lead-time-input :deep(.segmented-date),.follow-up-date-control :deep(.segmented-date){flex:1 1 auto;min-width:0}.quick-items-head{display:flex;align-items:center;justify-content:space-between;margin:24px 0 9px;padding-top:18px;border-top:1px solid #e3e8e4}.quick-items-head strong{font-size:var(--text-body)}.quick-lines{border:1px solid #e0e6e2;border-radius:9px;overflow:hidden}.quick-line{display:grid;grid-template-columns:2fr .6fr .8fr 1fr 32px;gap:8px;align-items:center;padding:9px;border-top:1px solid #edf0ee}.quick-line:first-child{border-top:0}.quick-line.order{grid-template-columns:2fr .55fr .7fr .7fr 1fr 32px}.quick-line select,.quick-line input{min-width:0;width:100%;padding:8px;border:1px solid #dce3df;border-radius:7px}.quick-line span{text-align:right;font-size:var(--text-body);font-weight:600}.quick-line button{border:0;background:transparent;color:#b05b5b}.quick-line button:disabled{opacity:.25}.quick-totals{display:flex;justify-content:flex-end;align-items:end;gap:13px;margin:14px 0 20px}.quick-totals label{font-size:var(--text-caption);color:#788680}.quick-totals input{display:block;width:100px;margin-top:4px;padding:7px;border:1px solid #dce3df;border-radius:7px}.quick-totals strong{padding:8px 0 8px 16px;border-left:1px solid #dce3df;color:#173f36}.related-create-modal :deep(.simple-editor textarea){min-height:155px}
.related-follow-up-attachment-editor{margin-top:24px;padding-top:20px;border-top:1px solid #e3e8e4}.related-follow-up-attachment-head{display:flex;align-items:center;justify-content:space-between;gap:16px}.related-follow-up-attachment-head>div{min-width:0}.related-follow-up-attachment-head strong{display:flex;align-items:center;gap:7px;color:#29473d;font-size:var(--text-body)}.related-follow-up-attachment-head strong svg{color:#28735b}.related-follow-up-attachment-head span{display:block;margin-top:4px;color:#7d8e87;font-size:var(--text-body)}.related-follow-up-attachment-head label{display:flex;align-items:center;gap:6px;flex:none;padding:8px 11px;border:1px solid #c8ddd4;border-radius:7px;background:#f1f8f4;color:#28735b;font-size:var(--text-body);font-weight:600;cursor:pointer}.related-follow-up-attachment-head label:hover{background:#e6f3ec}.related-follow-up-attachment-head input{display:none}.related-follow-up-attachment-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}.related-follow-up-attachment-list>div{display:flex;align-items:center;gap:8px;min-width:0;padding:9px 10px;border:1px solid #dfe9e4;border-radius:8px;background:#fbfdfc;color:#315a4c}.related-follow-up-attachment-list>div>svg{flex:none;color:#5e9c86}.related-follow-up-attachment-list>div>span{display:grid;flex:1;min-width:0;gap:2px}.related-follow-up-attachment-list strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--text-body)}.related-follow-up-attachment-list small{color:#81938b;font-size:var(--text-caption)}.related-follow-up-attachment-list button{display:grid;place-items:center;flex:none;padding:3px;border:0;background:transparent;color:#9a6b6b;cursor:pointer}.related-follow-up-attachment-empty{display:flex;align-items:center;justify-content:center;gap:7px;min-height:60px;margin-top:12px;border:1px dashed #bfd4ca;border-radius:8px;background:#fbfdfc;color:#879991;font-size:var(--text-body)}.related-follow-up-attachment-empty svg{color:#abc1b7}
.related-create-modal select:disabled,.related-create-modal input:disabled,.related-create-modal textarea:disabled{background:#f1f5f3;color:#5d756b;cursor:not-allowed}
.rate-reference{display:inline-flex;align-items:center;gap:5px;margin-left:6px;color:#75867f;font-size:var(--text-caption);font-weight:400}.rate-reference button{border:0;border-bottom:1px solid #76a596;background:transparent;padding:0;color:#26715d;font-size:var(--text-body);cursor:pointer}.rate-reference button:hover{color:#144f40}
.tail-policy-field{position:relative}.policy-help-trigger{display:inline-grid;place-items:center;width:18px;height:18px;margin-left:4px;border:1px solid #83ab9d;border-radius:50%;background:#f3faf6;color:#26715d;font:700 var(--text-caption)/1 inherit;cursor:pointer}.policy-help-trigger:hover{background:#dff1e8}.policy-help{position:relative;z-index:2;margin-top:8px;padding:10px 12px;border:1px solid #bed8cc;border-radius:8px;background:#f7fcf9;color:#3e5e53;font-size:var(--text-caption);line-height:1.55;box-shadow:0 5px 13px #173f3612}.policy-help strong,.policy-help small{display:block}.policy-help ul{margin:6px 0;padding-left:18px}.policy-help li+li{margin-top:3px}.policy-help small{color:#6c8379}
@media(max-width:700px){.related-create-modal{width:100%;height:100%;max-height:100%;border-radius:0}.quick-lines{overflow:auto}.quick-line,.quick-line.order{min-width:750px}.quick-totals{flex-wrap:wrap}.related-follow-up-attachment-head{align-items:flex-start;flex-direction:column}.related-follow-up-attachment-head label{width:100%;justify-content:center}.related-follow-up-attachment-list{grid-template-columns:1fr}}
.policy-help{position:absolute;z-index:12;top:48px;left:0;width:min(360px,calc(100vw - 64px));margin:0;box-shadow:0 8px 20px #173f3624}
.supply-category-options{display:flex;flex-wrap:wrap;gap:10px;padding:10px;max-height:190px;overflow:auto;border:1px solid #dce7e1;border-radius:8px}.supply-category-options label{display:flex;gap:5px;align-items:center}.supply-category-options small{width:100%;color:#71857b}
</style>

<style scoped>
.quick-line>span:not(.quick-sku){text-align:right;font-size:var(--text-body);font-weight:600}
.quick-sku{min-width:0;text-align:left!important;font-weight:400!important}
.quick-sku b,.quick-sku small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.quick-sku b{color:#294a41;font-size:var(--text-body)}
.quick-sku small{margin-top:3px;color:#81908a;font-size:var(--text-caption)}
.quick-items-empty{margin:10px 0;padding:15px;border:1px dashed #cddbd4;border-radius:8px;color:#82918b;text-align:center;font-size:var(--text-body)}
.supply-category-options{display:flex;flex-wrap:wrap;gap:10px;padding:10px;max-height:190px;overflow:auto;border:1px solid #dce7e1;border-radius:8px}.supply-category-options label{display:flex;gap:5px;align-items:center}.supply-category-options small{width:100%;color:#71857b}
</style>
