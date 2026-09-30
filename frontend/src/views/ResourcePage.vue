<script setup>
import CategoryMultiPicker from "../components/CategoryMultiPicker.vue"
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronRight, Database, Paperclip, Pencil, Plus, Search, Trash2, UserRoundPlus, X } from 'lucide-vue-next'
import { api, listAll } from '../api'
import EntityDetailModal from '../components/EntityDetailModal.vue'
import SimpleRichTextEditor from '../components/SimpleRichTextEditor.vue'
import ComboInput from '../components/ComboInput.vue'
import SegmentedDateInput from '../components/SegmentedDateInput.vue'
import SummaryCards from '../components/SummaryCards.vue'
import InventoryMovementCreateModal from '../components/InventoryMovementCreateModal.vue'
import { addDays, daysBetween } from '../utils/orderDate'
import { clearModalRoute } from '../utils/modalNavigation'

const props = defineProps({ config: Object })
const route = useRoute()
const router = useRouter()
const rows = ref([]), loading = ref(true), saving = ref(false), query = ref('')
const modalOpen = ref(false), detailId = ref(null), editingId = ref(null)
const detailRefresh = ref(0), keepDetailOpen = ref(false)
const form = reactive({}), options = reactive({})
const customerContacts = ref([])
const followUpDays = ref('')
const followUpAttachments = ref([])
const pendingFollowUpFiles = ref([])
const followUpFileInput = ref(null)
const currentOperator = ref('')
const supplierCodeServerError = ref('')
const toast = reactive({ show: false, message: '', error: false })
let searchTimer

const statusLabels = { lead: '线索', contact: '已建立联系', opportunity: '已进入报价阶段', customer: '已有1张正式订单', company: '已有2张及以上正式订单', development: '开发中', discontinued: '停产', draft: '草稿', confirmed: '已确认', production: '生产中', shipped: '已发货', completed: '已完成', cancelled: '已取消' }
const fieldOptions = computed(() => Object.fromEntries(props.config.fields.filter(field => field[2] === 'select').map(field => [field[0], field[4]])))
const title = computed(() => editingId.value ? `编辑${props.config.title.replace('管理', '')}` : `新建${props.config.title.replace('管理', '')}`)
const isCustomerCreate = computed(() => props.config.endpoint === 'customers' && !editingId.value)
const isWideForm = computed(() => isCustomerCreate.value || props.config.endpoint === 'follow-ups')
const isTransactionPage = computed(() => props.config.endpoint === 'transactions')
const supplierCodeConflict = computed(() => {
  if (props.config.endpoint !== 'suppliers') return null
  const code = String(form.code || '').trim().toUpperCase()
  if (code.length !== 2) return null
  const match = rows.value.find(row => String(row.code || '').toUpperCase() === code && Number(row.id) !== Number(editingId.value))
  return match ? `${code} 与 ${match.name}-${match.code} 重复` : null
})
const supplierCodeError = computed(() => supplierCodeConflict.value || supplierCodeServerError.value)
const resourceMetrics = computed(() => {
  const endpoint = props.config.endpoint
  const total = rows.value.length
  const today = new Date().toISOString().slice(0, 10)
  if (endpoint === 'customers') return [
    { label: '客户总数', value: total, hint: '当前客户档案' },
    { label: '正式客户', value: rows.value.filter(row => ['customer', 'company'].includes(row.status)).length, hint: '已成交或有返单' },
    { label: '待开发', value: rows.value.filter(row => ['lead', 'contact', 'opportunity'].includes(row.status)).length, hint: '线索、联系人与商机' },
    { label: '累计销售额', value: `¥ ${rows.value.reduce((sum, row) => sum + Number(row.sales_amount || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, hint: '当前列表客户累计值' },
  ]
  if (endpoint === 'follow-ups') return [
    { label: '跟进记录', value: total, hint: '当前查询结果' },
    { label: '已关联客户', value: new Set(rows.value.map(row => row.customer || row.customer_name).filter(Boolean)).size, hint: '有沟通记录的客户' },
    { label: '计划日期已到记录', value: rows.value.filter(row => row.next_follow_up && String(row.next_follow_up).slice(0, 10) <= today).length, hint: '历史跟进记录统计；当前待跟进以经营概览为准' },
    { label: '本月记录', value: rows.value.filter(row => String(row.followed_at || '').slice(0, 7) === today.slice(0, 7)).length, hint: '按跟进时间统计' },
  ]
  if (endpoint === 'transactions') return [
    { label: '流水笔数', value: total, hint: '当前查询结果' },
    { label: '收入合计', value: `¥ ${rows.value.filter(row => row.direction === 'income').reduce((sum, row) => sum + Number(row.rmb_amount || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, hint: '折合人民币' },
    { label: '支出合计', value: `¥ ${rows.value.filter(row => row.direction === 'expense').reduce((sum, row) => sum + Number(row.rmb_amount || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, hint: '折合人民币' },
    { label: '关联订单', value: new Set(rows.value.map(row => row.order || row.order_no).filter(Boolean)).size, hint: '有业务归属的流水' },
  ]
  const primary = endpoint === 'contacts' ? rows.value.filter(row => row.is_primary).length : rows.value.filter(row => ['active', 'development', 'draft'].includes(row.status)).length
  const linked = new Set(rows.value.map(row => row.customer || row.customer_name || row.product || row.product_name || row.supplier || row.supplier_name).filter(Boolean)).size
  return [
    { label: `${props.config.title.replace('管理', '')}总数`, value: total, hint: '当前查询结果' },
    { label: endpoint === 'contacts' ? '主联系人' : '启用 / 进行中', value: primary, hint: endpoint === 'contacts' ? '客户的主要联系人' : '当前有效记录' },
    { label: '关联主体', value: linked, hint: '客户、产品或供应商' },
    { label: '本月新增', value: rows.value.filter(row => String(row.created_at || '').slice(0, 7) === today.slice(0, 7)).length, hint: '按创建时间统计' },
  ]
})

function emptyContact(primary = false) {
  return { name: '', title: '', email: '', phone: '', whatsapp: '', notes: '', is_primary: primary }
}
function addCustomerContact() { customerContacts.value.push(emptyContact(false)) }
function removeCustomerContact(index) {
  if (customerContacts.value.length === 1) return
  const removedPrimary = customerContacts.value[index].is_primary
  customerContacts.value.splice(index, 1)
  if (removedPrimary) customerContacts.value[0].is_primary = true
}
function setPrimaryContact(index) {
  customerContacts.value.forEach((contact, contactIndex) => { contact.is_primary = contactIndex === index })
}

function notify(message, error = false) { Object.assign(toast, { show: true, message, error }); setTimeout(() => { toast.show = false }, 2800) }
async function load() {
  loading.value = true
  try { rows.value = await listAll(`/${props.config.endpoint}/`, { params: { ...route.query, search: query.value } }) }
  catch (e) { notify(e.message, true) } finally { loading.value = false }
}
function delayedSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(load, 300) }
async function loadOptions() {
  const remotes = props.config.fields.filter(f => ['remote', 'combo', 'remote_multi'].includes(f[2]))
  await Promise.all(remotes.map(async field => {
    if (options[field[4]]) return
    try { options[field[4]] = await listAll(`/${field[4]}/`) } catch { options[field[4]] = [] }
  }))
}
function visibleOptions(field) {
  const rows = options[field[4]] || []
  if (props.config.endpoint === 'follow-ups' && field[0] === 'contact' && form.customer) return rows.filter(row => Number(row.customer) === Number(form.customer))
  return rows
}
function datetimeLocal() {
  const now = new Date()
  const date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  return `${date}T${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}
function syncFollowUpDaysFromDate() {
  if (props.config.endpoint !== 'follow-ups') return
  const startDate = String(form.followed_at || '').slice(0, 10)
  followUpDays.value = startDate && form.next_follow_up ? daysBetween(startDate, form.next_follow_up) : ''
}
function updateFollowUpDate() {
  if (props.config.endpoint !== 'follow-ups') return
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
  if (props.config.endpoint !== 'follow-ups') return
  const additions = Array.from(files || []).filter(file => file?.name && file.size <= 20 * 1024 * 1024)
  const rejected = Array.from(files || []).filter(file => file?.size > 20 * 1024 * 1024)
  if (rejected.length) notify('单个附件不能超过 20 MB。', true)
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
  if (!id || !pendingFollowUpFiles.value.length) return null
  const data = new FormData()
  pendingFollowUpFiles.value.forEach(file => data.append('files', file, file.name))
  const response = await api.post(`/follow-ups/${id}/attachments/`, data, { timeout: 120000 })
  return response.data
}
function onDateFieldChange(field, value) {
  form[field[0]] = value
  if (props.config.endpoint === 'follow-ups' && field[0] === 'followed_at') syncFollowUpDaysFromDate()
}
function applyDefaultContact() {
  if (props.config.endpoint !== 'follow-ups' || !form.customer) return
  if (form.contact) return
  const contacts = (options.contacts || []).filter(row => Number(row.customer) === Number(form.customer))
  const primary = contacts.find(row => row.is_primary) || contacts[0]
  form.contact = primary?.id || ''
}
function onFieldChange(field) {
  if (props.config.endpoint === 'follow-ups' && field[0] === 'customer') {
    form.contact = ''
    applyDefaultContact()
  }
}
function normalizeSupplierCode() {
  supplierCodeServerError.value = ''
  form.code = String(form.code || '').replace(/[^a-z]/gi, '').slice(0, 2).toUpperCase()
}
async function loadCurrentOperator() {
  if (currentOperator.value) return currentOperator.value
  try { currentOperator.value = (await api.get('/session/current-operator/')).data.name || '' } catch { currentOperator.value = '' }
  return currentOperator.value
}
function resetForm() {
  props.config.fields.forEach(([name, , type, , extra]) => {
    const supplierDefault = props.config.endpoint === 'suppliers' && !editingId.value
      ? { country: '中国', payment_terms: '30%预付款，70%尾款发货前结清' }[name]
      : undefined
    form[name] = type === 'remote_multi' ? [] : type === 'checkbox' ? name === 'active' : type === 'select' ? Object.keys(extra)[0] : (route.query[name] ?? supplierDefault ?? '')
  })
  supplierCodeServerError.value = ''
}
function normalizeWebsite(value) {
  const website = String(value || '').trim()
  if (!website || /^[a-z][a-z\d+.-]*:\/\//i.test(website)) return website
  return `https://${website}`
}
function isInherited(fieldName) {
  const value = route.query?.[fieldName]
  return !editingId.value && value !== undefined && value !== null && value !== ''
}
async function openCreate() {
  keepDetailOpen.value = false
  editingId.value = null; resetForm()
  if (props.config.endpoint === 'follow-ups' && !form.followed_at) form.followed_at = datetimeLocal()
  customerContacts.value = props.config.endpoint === 'customers' ? [emptyContact(true)] : []
  await loadOptions()
  if (props.config.endpoint === 'customers') {
    try { form.code = (await api.get('/customers/next-code/')).data.code } catch { form.code = '保存时自动生成' }
  }
  if (['customers', 'follow-ups'].includes(props.config.endpoint) && !form.owner) form.owner = await loadCurrentOperator()
  followUpAttachments.value = []
  pendingFollowUpFiles.value = []
  applyDefaultContact()
  syncFollowUpDaysFromDate()
  modalOpen.value = true
}
async function openEdit(row, { keepDetail = false } = {}) {
  if (!keepDetail) detailId.value = null
  keepDetailOpen.value = keepDetail
  editingId.value = row.id; resetForm(); await loadOptions()
  props.config.fields.forEach(([name, , type]) => {
    let value = row[name]
    if (type === 'datetime-local' && value) value = value.slice(0, 16)
    form[name] = value ?? (type === 'checkbox' ? false : '')
  })
  followUpAttachments.value = props.config.endpoint === 'follow-ups' ? (row.attachments || []) : []
  pendingFollowUpFiles.value = []
  syncFollowUpDaysFromDate()
  modalOpen.value = true
}
function closeModal() {
  modalOpen.value = false; keepDetailOpen.value = false; followUpDays.value = ''; followUpAttachments.value = []; pendingFollowUpFiles.value = []
  void clearModalRoute(router, route)
}
function closeDetail() {
  detailId.value = null
  if (!route.query.detail) return
  const { detail, ...query } = route.query
  void router.replace({ path: route.path, query, hash: route.hash })
}
function detailReturnPath() {
  const query = new URLSearchParams()
  Object.entries(route.query).forEach(([key, value]) => {
    if (!['create', 'edit', 'returnTo', 'detail'].includes(key) && typeof value === 'string') query.set(key, value)
  })
  if (detailId.value) query.set('detail', String(detailId.value))
  return `${route.path}?${query.toString()}`
}
function payload() {
  const data = {}
  props.config.fields.forEach(([name, , type]) => {
    let value = form[name]
    if (type === 'remote_multi') value = (value || []).map(Number)
    if (type === 'remote') value = value ? Number(value) : null
    if (type === 'number') value = value === '' ? 0 : value
    if (type === 'date' && value === '') value = null
    if (type === 'datetime-local' && value && value.length === 16) value += ':00+08:00'
    if (['website', 'store_url'].includes(name)) value = normalizeWebsite(value)
    data[name] = value
  })
  if (isCustomerCreate.value) data.contacts = customerContacts.value
  return data
}
async function save() {
  if (supplierCodeError.value) return notify(supplierCodeError.value, true)
  saving.value = true
  try {
    const wasEditing = Boolean(editingId.value)
    const response = wasEditing ? await api.put(`/${props.config.endpoint}/${editingId.value}/`, payload()) : await api.post(`/${props.config.endpoint}/`, payload())
    const savedId = response.data?.id || editingId.value
    let attachmentError = ''
    if (props.config.endpoint === 'follow-ups' && pendingFollowUpFiles.value.length) {
      try {
        const uploaded = await uploadFollowUpFiles(savedId)
        followUpAttachments.value = [...followUpAttachments.value, ...(uploaded || [])]
        pendingFollowUpFiles.value = []
      } catch (error) {
        attachmentError = error.message || '附件上传失败'
      }
    }
    const refreshDetail = keepDetailOpen.value
    modalOpen.value = false; notify(attachmentError ? `记录已保存，但${attachmentError}` : (wasEditing ? '更新成功' : '创建成功'), Boolean(attachmentError)); await load()
    if (refreshDetail) detailRefresh.value += 1
    keepDetailOpen.value = false
  } catch (e) {
    if (props.config.endpoint === 'suppliers' && /重复|二字代码/.test(e.message || '')) supplierCodeServerError.value = e.message
    notify(e.message, true)
  } finally { saving.value = false }
}
async function handleInventoryMovementCreated(records) {
  modalOpen.value = false
  notify(`已创建 ${Array.isArray(records) ? records.length : 1} 条库存流水`)
  await load()
}
async function remove(row) {
  if (!window.confirm(`确定删除“${row[props.config.key]}”吗？此操作无法撤销。`)) return
  try { await api.delete(`/${props.config.endpoint}/${row.id}/`); notify('删除成功'); await load() } catch (e) { notify(e.message, true) }
}
function display(value, type, fieldName = '') {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.length ? value.join('、') : '—'
  if (type === 'money') return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (type === 'rmb') return `¥ ${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  if (type === 'labels') return Array.isArray(value) ? value.join('、') || '未设置' : '未设置'
  if (type === 'number') return Number(value).toLocaleString('zh-CN')
  if (type === 'date') return String(value).slice(0, 10)
  if (type === 'datetime') return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  if (type === 'boolean') return value ? '是' : '否'
  if (type === 'status') return statusLabels[value] || fieldOptions.value[fieldName]?.[value] || value
  if (type === 'signed') return `${Number(value) > 0 ? '+' : ''}${Number(value).toLocaleString('zh-CN')}`
  return value
}
function isReadOnlyAutomaticMovement(row) { return props.config.endpoint === 'inventory-movements' && row.is_automatic === true }
function formatAttachmentSize(value) {
  const size = Number(value || 0)
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
function cellClass(type, value) { return { amount: ['money', 'rmb'].includes(type), tag: type === 'tag', status: type === 'status', [value]: type === 'status', direction: type === 'direction', income: value === '收入', expense: value === '支出', positive: type === 'signed' && Number(value) > 0, negative: type === 'signed' && Number(value) < 0 } }
async function editFromDetail(target = {}) {
  const targetEntity = target?.entity || props.config.endpoint
  const targetId = target?.id || detailId.value
  if (!targetId) return
  if (targetEntity !== props.config.endpoint) {
    if (targetEntity === 'follow-ups') router.push({ path: '/follow-ups', query: { edit: String(targetId), returnTo: detailReturnPath() } })
    return
  }
  const row = rows.value.find(item => String(item.id) === String(targetId))
  if (row) await openEdit(row, { keepDetail: true })
}
async function handleDetailChanged() {
  await load()
  if (detailId.value) detailRefresh.value += 1
}

watch(() => route.query, load)
onMounted(async () => {
  await load()
  if (route.query.detail) detailId.value = Number(route.query.detail)
  if (route.query.create === '1') await openCreate()
  if (route.query.edit && props.config.endpoint === 'follow-ups') {
    try { await openEdit((await api.get(`/follow-ups/${route.query.edit}/`)).data) } catch (e) { notify(e.message, true) }
  }
})
watch(() => route.query.detail, id => { detailId.value = id ? Number(id) : null })
</script>

<template>
  <div class="resource-page" :class="{ 'finance-resource-page': isTransactionPage }">
    <div class="page-head"><div><h2>{{ config.title }}</h2><p>{{ config.description }}</p></div><button class="btn btn-primary" @click="openCreate"><Plus :size="16" /> 新建记录</button></div>
    <SummaryCards :items="resourceMetrics" />
    <div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索当前列表..." @input="delayedSearch" /></div></div>
    <div class="panel">
      <div v-if="loading" class="loading"><div class="spinner" /></div>
      <div v-else-if="!rows.length" class="empty"><Database :size="32" /><h3>还没有数据</h3><p>点击“新建记录”开始建立业务资料。</p></div>
      <div v-else class="table-wrap"><table class="data-table"><thead><tr><th v-for="col in config.columns" :key="col[0]">{{ col[1] }}</th><th style="text-align:right">操作</th></tr></thead><tbody>
        <tr v-for="row in rows" :key="row.id" class="clickable-row" tabindex="0" @click="detailId = row.id" @keydown.enter="detailId = row.id">
          <td v-for="(col,index) in config.columns" :key="col[0]" :class="{ 'primary-cell': index === 0, 'numeric-cell': ['money', 'rmb'].includes(col[2]) }"><span :class="cellClass(col[2], row[col[0]])">{{ display(row[col[0]], col[2], col[0]) }}</span></td>
          <td><div class="table-actions"><button class="mini-btn" title="查看详情" @click.stop="detailId = row.id"><ChevronRight :size="14" /></button><button v-if="!isReadOnlyAutomaticMovement(row)" class="mini-btn" title="编辑" @click.stop="openEdit(row)"><Pencil :size="14" /></button><button v-if="!isReadOnlyAutomaticMovement(row)" class="mini-btn" title="删除" @click.stop="remove(row)"><Trash2 :size="14" /></button></div></td>
        </tr>
      </tbody></table></div>
    </div>

    <InventoryMovementCreateModal v-if="modalOpen && config.endpoint === 'inventory-movements' && !editingId" @close="closeModal" @saved="handleInventoryMovementCreated" />
    <div v-else-if="modalOpen" class="modal-backdrop" @mousedown.self="closeModal"><form class="modal" :class="{ wide: isWideForm }" @submit.prevent="save">
      <div class="modal-head"><h3>{{ title }}</h3><button type="button" class="mini-btn" @click="closeModal"><X :size="17" /></button></div>
      <div class="modal-body"><div class="form-grid"><div v-for="field in config.fields" :key="field[0]" class="field" :class="{ full: ['textarea', 'remote_multi'].includes(field[2]) || (config.endpoint === 'follow-ups' && field[0] === 'subject'), 'finance-amount-field': isTransactionPage && ['amount', 'exchange_rate'].includes(field[0]) }">
        <label>{{ field[1] }} <em v-if="field[3]">*</em></label>
        <textarea v-if="field[2] === 'textarea'" v-model="form[field[0]]" :required="field[3]" :disabled="isInherited(field[0])" />
        <SimpleRichTextEditor v-else-if="field[2] === 'richtext'" v-model="form[field[0]]" @paste-files="addFollowUpFiles" />
        <ComboInput v-else-if="field[2] === 'combo'" v-model="form[field[0]]" :options="options[field[4]] || []" :required="field[3]" :disabled="isInherited(field[0])" />
        <select v-else-if="field[2] === 'select'" v-model="form[field[0]]" :required="field[3]" :disabled="isInherited(field[0])"><option v-for="(label,key) in field[4]" :key="key" :value="key">{{ label }}</option></select>
        <CategoryMultiPicker v-else-if="field[2] === 'remote_multi'" v-model="form[field[0]]" :categories="options[field[4]] || []" />
        <select v-else-if="field[2] === 'remote'" v-model="form[field[0]]" :required="field[3]" :disabled="isInherited(field[0])" @change="onFieldChange(field)"><option value="">请选择</option><option v-for="option in visibleOptions(field)" :key="option.id" :value="option.id">{{ option[field[5]] }}</option></select>
        <label v-else-if="field[2] === 'checkbox'" class="checkbox-line"><input v-model="form[field[0]]" type="checkbox" :disabled="isInherited(field[0])" /> 是</label>
        <div v-else-if="config.endpoint === 'follow-ups' && field[0] === 'next_follow_up'" class="follow-up-date-control">
          <input v-model="followUpDays" type="number" min="0" step="1" placeholder="天数" aria-label="下次跟进天数" @input="updateFollowUpDate" />
          <span>天后</span>
          <SegmentedDateInput :model-value="form.next_follow_up" @update:model-value="setFollowUpDate" />
        </div>
        <SegmentedDateInput v-else-if="field[2] === 'date' || field[2] === 'datetime-local'" :model-value="form[field[0]]" :required="field[3]" :with-time="field[2] === 'datetime-local'" @update:model-value="value => onDateFieldChange(field, value)" />
        <input v-else v-model="form[field[0]]" :type="field[2] === 'readonly' || ['website', 'store_url'].includes(field[0]) ? 'text' : (field[2] || 'text')" :readonly="field[2] === 'readonly'" :placeholder="field[0] === 'store_url' ? 'https://...' : undefined" :class="{ 'readonly-input': field[2] === 'readonly', 'field-invalid': config.endpoint === 'suppliers' && field[0] === 'code' && supplierCodeError }" :aria-invalid="config.endpoint === 'suppliers' && field[0] === 'code' && supplierCodeError ? 'true' : undefined" :step="field[2] === 'number' ? '0.0001' : undefined" :maxlength="config.endpoint === 'suppliers' && field[0] === 'code' ? 2 : undefined" :pattern="config.endpoint === 'suppliers' && field[0] === 'code' ? '[A-Za-z]{2}' : undefined" :required="field[3]" :disabled="isInherited(field[0])" @input="config.endpoint === 'suppliers' && field[0] === 'code' && normalizeSupplierCode()" />
        <p v-if="config.endpoint === 'suppliers' && field[0] === 'code'" class="field-help" :class="{ error: supplierCodeError }">{{ supplierCodeError || '填写两个英文字母，用于供应商 SKU 编码。' }}</p>
      </div></div>

        <section v-if="config.endpoint === 'follow-ups'" class="follow-up-attachment-editor" @dragover.prevent @drop.prevent="onFollowUpFileDrop">
          <div class="follow-up-attachment-editor-head">
            <div><strong><Paperclip :size="16" /> 附件</strong><span>支持在编辑器中粘贴图片或附件，也可拖拽、选择文件</span></div>
            <label class="follow-up-attachment-picker"><Paperclip :size="14" /> 添加附件<input ref="followUpFileInput" type="file" multiple @change="onFollowUpFileInput" /></label>
          </div>
          <div v-if="followUpAttachments.length || pendingFollowUpFiles.length" class="follow-up-attachment-editor-list">
            <div v-for="attachment in followUpAttachments" :key="`saved-${attachment.id}`" class="follow-up-attachment-editor-item saved"><Paperclip :size="16" /><span><strong>{{ attachment.name }}</strong><small>已上传 · {{ formatAttachmentSize(attachment.size) }}</small></span></div>
            <div v-for="(file, index) in pendingFollowUpFiles" :key="`pending-${file.name}-${file.size}-${file.lastModified}`" class="follow-up-attachment-editor-item"><Paperclip :size="16" /><span><strong>{{ file.name }}</strong><small>待上传 · {{ formatAttachmentSize(file.size) }}</small></span><button type="button" aria-label="移除附件" @click="removePendingFollowUpFile(index)"><X :size="14" /></button></div>
          </div>
          <div v-else class="follow-up-attachment-editor-empty"><Paperclip :size="16" /> 尚未添加附件</div>
        </section>

        <section v-if="isCustomerCreate" class="contact-create-section">
          <div class="contact-create-head">
            <div><span>联系人信息</span><p>新建客户时至少登记一位联系人，第一位默认设为主联系人。</p></div>
            <span class="contact-count">{{ customerContacts.length }} 位</span>
          </div>
          <div v-for="(contact, index) in customerContacts" :key="index" class="contact-create-card">
            <div class="contact-card-head">
              <strong>联系人 {{ index + 1 }}</strong>
              <div class="contact-card-actions">
                <label class="primary-switch">
                  <input type="checkbox" :checked="contact.is_primary" @change="setPrimaryContact(index)" />
                  <span class="switch-track"><i /></span>
                  <span>默认联系人</span>
                </label>
                <button v-if="customerContacts.length > 1" type="button" class="mini-btn danger" aria-label="删除联系人" @click="removeCustomerContact(index)"><Trash2 :size="14" /></button>
              </div>
            </div>
            <div class="contact-fields">
              <div class="field"><label>姓名 <em>*</em></label><input v-model.trim="contact.name" required /></div>
              <div class="field"><label>职位</label><input v-model.trim="contact.title" /></div>
              <div class="field"><label>邮箱</label><input v-model.trim="contact.email" type="email" /></div>
              <div class="field"><label>电话</label><input v-model.trim="contact.phone" /></div>
              <div class="field"><label>WhatsApp</label><input v-model.trim="contact.whatsapp" /></div>
              <div class="field"><label>备注</label><input v-model.trim="contact.notes" /></div>
            </div>
          </div>
          <button type="button" class="add-contact-btn" @click="addCustomerContact"><UserRoundPlus :size="16" /> 新增联系人</button>
        </section>
      </div>
      <div class="modal-foot"><button type="button" class="btn btn-secondary" @click="closeModal">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button></div>
    </form></div>

    <Transition name="detail-drawer" appear>
      <EntityDetailModal v-if="detailId" :entity="config.endpoint" :id="detailId" :refresh-key="detailRefresh" @close="closeDetail" @edit="editFromDetail" @changed="handleDetailChanged" />
    </Transition>
    <div v-if="toast.show" class="toast" :class="{ error: toast.error }">{{ toast.message }}</div>
  </div>
</template>

<style scoped>
.contact-create-section{margin-top:26px;padding-top:22px;border-top:1px solid var(--line)}
.follow-up-date-control{display:flex;align-items:center;gap:6px}.follow-up-date-control>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.follow-up-date-control>span{color:#70817b;font-size:var(--text-body);white-space:nowrap}.follow-up-date-control :deep(.segmented-date){flex:1 1 auto;min-width:0}
.follow-up-attachment-editor{margin-top:24px;padding-top:20px;border-top:1px solid var(--line)}
.follow-up-attachment-editor-head{display:flex;align-items:center;justify-content:space-between;gap:16px}.follow-up-attachment-editor-head>div{min-width:0}.follow-up-attachment-editor-head strong{display:flex;align-items:center;gap:7px;color:var(--ink);font-size:var(--text-body)}.follow-up-attachment-editor-head strong svg{color:var(--green-2)}.follow-up-attachment-editor-head span{display:block;margin-top:4px;color:var(--muted);font-size:var(--text-body)}
.follow-up-attachment-picker{display:flex;align-items:center;gap:6px;flex:none;padding:8px 11px;border:1px solid #c8ddd4;border-radius:7px;background:#f1f8f4;color:var(--green-2);font-size:var(--text-body);font-weight:600;cursor:pointer}.follow-up-attachment-picker:hover{background:#e6f3ec}.follow-up-attachment-picker input{display:none}
.follow-up-attachment-editor-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}.follow-up-attachment-editor-item{display:flex;align-items:center;gap:8px;min-width:0;padding:9px 10px;border:1px solid #dfe9e4;border-radius:8px;background:#fbfdfc;color:#315a4c}.follow-up-attachment-editor-item>svg{flex:none;color:#5e9c86}.follow-up-attachment-editor-item>span{display:grid;flex:1;min-width:0;gap:2px}.follow-up-attachment-editor-item strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--text-body)}.follow-up-attachment-editor-item small{color:#81938b;font-size:var(--text-caption)}.follow-up-attachment-editor-item.saved{background:#f3faf6}.follow-up-attachment-editor-item button{display:grid;place-items:center;flex:none;padding:3px;border:0;background:transparent;color:#9a6b6b;cursor:pointer}.follow-up-attachment-editor-empty{display:flex;align-items:center;justify-content:center;gap:7px;min-height:60px;margin-top:12px;border:1px dashed #bfd4ca;border-radius:8px;background:#fbfdfc;color:#879991;font-size:var(--text-body)}.follow-up-attachment-editor-empty svg{color:#abc1b7}
.contact-create-head,.contact-card-head,.contact-card-actions,.primary-switch{display:flex;align-items:center}
.contact-create-head,.contact-card-head{justify-content:space-between;gap:16px}
.contact-create-head>div>span{font-size:var(--text-section);font-weight:700;color:var(--ink)}
.contact-create-head p{margin:4px 0 0;color:var(--muted);font-size:var(--text-body)}
.contact-count{flex:none;padding:4px 9px;border-radius:20px;background:#edf3f0;color:#47665c;font-size:var(--text-body);font-weight:600}
.contact-create-card{margin-top:14px;padding:16px;border:1px solid #dce5e0;border-radius:12px;background:#fbfcfb}
.contact-card-head strong{font-size:var(--text-body);color:#314740}
.contact-card-actions{gap:10px}
.primary-switch{gap:7px;margin:0;color:#53655f;font-size:var(--text-body);cursor:pointer}
.primary-switch input{position:absolute;opacity:0;pointer-events:none}
.switch-track{width:34px;height:19px;border-radius:20px;background:#cbd6d1;padding:2px;transition:.2s}
.switch-track i{display:block;width:15px;height:15px;border-radius:50%;background:white;box-shadow:0 1px 4px #173d3633;transition:.2s}
.primary-switch input:checked+.switch-track{background:var(--green-2)}
.primary-switch input:checked+.switch-track i{transform:translateX(15px)}
.contact-fields{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}
.mini-btn.danger{color:var(--danger)}
.add-contact-btn{width:100%;margin-top:12px;padding:11px;border:1px dashed #aac2ba;border-radius:9px;background:#f7faf8;color:var(--green-2);display:flex;align-items:center;justify-content:center;gap:7px;font-size:var(--text-body);font-weight:600}
.add-contact-btn:hover{background:#edf5f1;border-color:#719d8f}
.readonly-input{background:#f1f5f3!important;color:#557068!important;cursor:not-allowed}
.field-invalid{border-color:#d85b5b!important;background:#fff8f8!important;box-shadow:0 0 0 3px #fbe4e4!important}
.field-help.error{color:#c33f3f;font-size:var(--text-caption);font-weight:600}
.finance-resource-page{font-family:var(--font-sans)}
.finance-resource-page .page-head h2,.finance-resource-page .page-head p,.finance-resource-page .data-table,.finance-resource-page .modal{font-family:inherit}
.finance-resource-page .data-table th{background:#f8faf8;color:#81908b}
.finance-resource-page .data-table td{color:#43504c}
.finance-resource-page .data-table .direction{font-weight:700}
.finance-resource-page .data-table .direction.income{color:#267255}
.finance-resource-page .data-table .direction.expense{color:#bd4e4e}
.finance-resource-page .numeric-cell{text-align:right;white-space:nowrap}
.finance-resource-page .numeric-cell .amount{display:inline-block;min-width:7.5ch;text-align:right;font-variant-numeric:tabular-nums}
.finance-resource-page .data-table td:nth-last-child(2){padding-right:22px}
.finance-resource-page .finance-amount-field input{font-variant-numeric:tabular-nums}
.finance-resource-page .modal .field label{letter-spacing:.01em}
@media(max-width:760px){.contact-fields{grid-template-columns:1fr 1fr}.follow-up-attachment-editor-head{align-items:flex-start;flex-direction:column}.follow-up-attachment-picker{width:100%;justify-content:center}.follow-up-attachment-editor-list{grid-template-columns:1fr}}
@media(max-width:520px){.contact-create-head,.contact-card-head{align-items:flex-start}.contact-card-head{flex-direction:column}.contact-fields{grid-template-columns:1fr}.contact-card-actions{width:100%;justify-content:space-between}}
.supply-category-options{display:flex;flex-wrap:wrap;gap:10px;max-height:190px;overflow:auto;padding:12px;border:1px solid #dce7e1;border-radius:8px}.supply-category-options label{display:flex;align-items:center;gap:6px}.supply-category-options small{flex-basis:100%;color:#71857b}
</style>
