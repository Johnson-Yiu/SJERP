<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronRight, Database, Pencil, Plus, Search, Trash2, UserRoundPlus, X } from 'lucide-vue-next'
import { api, listData } from '../api'
import EntityDetailModal from '../components/EntityDetailModal.vue'
import SimpleRichTextEditor from '../components/SimpleRichTextEditor.vue'
import ComboInput from '../components/ComboInput.vue'

const props = defineProps({ config: Object })
const route = useRoute()
const rows = ref([]), loading = ref(true), saving = ref(false), query = ref('')
const modalOpen = ref(false), detailId = ref(null), editingId = ref(null)
const form = reactive({}), options = reactive({})
const customerContacts = ref([])
const currentOperator = ref('')
const toast = reactive({ show: false, message: '', error: false })
let searchTimer

const statusLabels = { lead: '线索', contact: '联系人', opportunity: '商机', customer: '正式客户', company: '公司客户', development: '开发中', discontinued: '停产', draft: '草稿', confirmed: '已确认', production: '生产中', shipped: '已发货', completed: '已完成', cancelled: '已取消' }
const fieldOptions = computed(() => Object.fromEntries(props.config.fields.filter(field => field[2] === 'select').map(field => [field[0], field[4]])))
const title = computed(() => editingId.value ? `编辑${props.config.title.replace('管理', '')}` : `新建${props.config.title.replace('管理', '')}`)
const isCustomerCreate = computed(() => props.config.endpoint === 'customers' && !editingId.value)
const isWideForm = computed(() => isCustomerCreate.value || props.config.endpoint === 'follow-ups')

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
  try { rows.value = listData(await api.get(`/${props.config.endpoint}/`, { params: { ...route.query, search: query.value } })) }
  catch (e) { notify(e.message, true) } finally { loading.value = false }
}
function delayedSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(load, 300) }
async function loadOptions() {
  const remotes = props.config.fields.filter(f => ['remote', 'combo'].includes(f[2]))
  await Promise.all(remotes.map(async field => {
    if (options[field[4]]) return
    try { options[field[4]] = listData(await api.get(`/${field[4]}/`)) } catch { options[field[4]] = [] }
  }))
}
function visibleOptions(field) {
  const rows = options[field[4]] || []
  if (props.config.endpoint === 'follow-ups' && field[0] === 'contact' && form.customer) return rows.filter(row => Number(row.customer) === Number(form.customer))
  return rows
}
function applyDefaultContact() {
  if (props.config.endpoint !== 'follow-ups' || !form.customer) return
  const contacts = (options.contacts || []).filter(row => Number(row.customer) === Number(form.customer))
  const primary = contacts.find(row => row.is_primary) || contacts[0]
  form.contact = primary?.id || ''
}
function onFieldChange(field) {
  if (props.config.endpoint === 'follow-ups' && field[0] === 'customer') applyDefaultContact()
}
async function loadCurrentOperator() {
  if (currentOperator.value) return currentOperator.value
  try { currentOperator.value = (await api.get('/session/current-operator/')).data.name || '' } catch { currentOperator.value = '' }
  return currentOperator.value
}
function resetForm() {
  props.config.fields.forEach(([name, , type, , extra]) => {
    form[name] = type === 'checkbox' ? name === 'active' : type === 'select' ? Object.keys(extra)[0] : (route.query[name] || '')
  })
}
async function openCreate() {
  editingId.value = null; resetForm()
  customerContacts.value = props.config.endpoint === 'customers' ? [emptyContact(true)] : []
  await loadOptions()
  if (props.config.endpoint === 'customers') {
    try { form.code = (await api.get('/customers/next-code/')).data.code } catch { form.code = '保存时自动生成' }
  }
  if (props.config.endpoint === 'follow-ups' && !form.owner) form.owner = await loadCurrentOperator()
  applyDefaultContact()
  modalOpen.value = true
}
async function openEdit(row) {
  detailId.value = null; editingId.value = row.id; resetForm(); await loadOptions()
  props.config.fields.forEach(([name, , type]) => {
    let value = row[name]
    if (type === 'datetime-local' && value) value = value.slice(0, 16)
    form[name] = value ?? (type === 'checkbox' ? false : '')
  })
  modalOpen.value = true
}
function payload() {
  const data = {}
  props.config.fields.forEach(([name, , type]) => {
    let value = form[name]
    if (type === 'remote') value = value ? Number(value) : null
    if (type === 'number') value = value === '' ? 0 : value
    if (type === 'datetime-local' && value && value.length === 16) value += ':00+08:00'
    data[name] = value
  })
  if (isCustomerCreate.value) data.contacts = customerContacts.value
  return data
}
async function save() {
  saving.value = true
  try {
    editingId.value ? await api.put(`/${props.config.endpoint}/${editingId.value}/`, payload()) : await api.post(`/${props.config.endpoint}/`, payload())
    modalOpen.value = false; notify(editingId.value ? '更新成功' : '创建成功'); await load()
  } catch (e) { notify(e.message, true) } finally { saving.value = false }
}
async function remove(row) {
  if (!window.confirm(`确定删除“${row[props.config.key]}”吗？此操作无法撤销。`)) return
  try { await api.delete(`/${props.config.endpoint}/${row.id}/`); notify('删除成功'); await load() } catch (e) { notify(e.message, true) }
}
function display(value, type, fieldName = '') {
  if (value === null || value === undefined || value === '') return '—'
  if (type === 'money') return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
  if (type === 'rmb') return `¥ ${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
  if (type === 'number') return Number(value).toLocaleString('zh-CN')
  if (type === 'date') return String(value).slice(0, 10)
  if (type === 'datetime') return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  if (type === 'boolean') return value ? '是' : '否'
  if (type === 'status') return statusLabels[value] || fieldOptions.value[fieldName]?.[value] || value
  if (type === 'signed') return `${Number(value) > 0 ? '+' : ''}${Number(value).toLocaleString('zh-CN')}`
  return value
}
function cellClass(type, value) { return { amount: ['money', 'rmb'].includes(type), tag: type === 'tag', status: type === 'status', [value]: type === 'status', direction: type === 'direction', income: value === '收入', expense: value === '支出', positive: type === 'signed' && Number(value) > 0, negative: type === 'signed' && Number(value) < 0 } }
function editFromDetail() { const row = rows.value.find(r => r.id === detailId.value); if (row) openEdit(row) }

watch(() => route.query, load)
onMounted(async () => {
  await load()
  if (route.query.create === '1') await openCreate()
})
</script>

<template>
  <div>
    <div class="page-head"><div><h2>{{ config.title }}</h2><p>{{ config.description }}</p></div><button class="btn btn-primary" @click="openCreate"><Plus :size="16" /> 新建记录</button></div>
    <div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索当前列表..." @input="delayedSearch" /></div></div>
    <div class="panel">
      <div v-if="loading" class="loading"><div class="spinner" /></div>
      <div v-else-if="!rows.length" class="empty"><Database :size="32" /><h3>还没有数据</h3><p>点击“新建记录”开始建立业务资料。</p></div>
      <div v-else class="table-wrap"><table class="data-table"><thead><tr><th v-for="col in config.columns" :key="col[0]">{{ col[1] }}</th><th style="text-align:right">操作</th></tr></thead><tbody>
        <tr v-for="row in rows" :key="row.id" class="clickable-row" tabindex="0" @click="detailId = row.id" @keydown.enter="detailId = row.id">
          <td v-for="(col,index) in config.columns" :key="col[0]" :class="{ 'primary-cell': index === 0 }"><span :class="cellClass(col[2], row[col[0]])">{{ display(row[col[0]], col[2], col[0]) }}</span></td>
          <td><div class="table-actions"><button class="mini-btn" title="查看详情" @click.stop="detailId = row.id"><ChevronRight :size="14" /></button><button class="mini-btn" title="编辑" @click.stop="openEdit(row)"><Pencil :size="14" /></button><button class="mini-btn" title="删除" @click.stop="remove(row)"><Trash2 :size="14" /></button></div></td>
        </tr>
      </tbody></table></div>
    </div>

    <div v-if="modalOpen" class="modal-backdrop" @mousedown.self="modalOpen = false"><form class="modal" :class="{ wide: isWideForm }" @submit.prevent="save">
      <div class="modal-head"><h3>{{ title }}</h3><button type="button" class="mini-btn" @click="modalOpen = false"><X :size="17" /></button></div>
      <div class="modal-body"><div class="form-grid"><div v-for="field in config.fields" :key="field[0]" class="field" :class="{ full: field[2] === 'textarea' || (config.endpoint === 'follow-ups' && field[0] === 'subject') }">
        <label>{{ field[1] }} <em v-if="field[3]">*</em></label>
        <textarea v-if="field[2] === 'textarea'" v-model="form[field[0]]" :required="field[3]" />
        <SimpleRichTextEditor v-else-if="field[2] === 'richtext'" v-model="form[field[0]]" />
        <ComboInput v-else-if="field[2] === 'combo'" v-model="form[field[0]]" :options="options[field[4]] || []" :required="field[3]" />
        <select v-else-if="field[2] === 'select'" v-model="form[field[0]]" :required="field[3]"><option v-for="(label,key) in field[4]" :key="key" :value="key">{{ label }}</option></select>
        <select v-else-if="field[2] === 'remote'" v-model="form[field[0]]" :required="field[3]" @change="onFieldChange(field)"><option value="">请选择</option><option v-for="option in visibleOptions(field)" :key="option.id" :value="option.id">{{ option[field[5]] }}</option></select>
        <label v-else-if="field[2] === 'checkbox'" class="checkbox-line"><input v-model="form[field[0]]" type="checkbox" /> 是</label>
        <input v-else v-model="form[field[0]]" :type="field[2] === 'readonly' ? 'text' : (field[2] || 'text')" :readonly="field[2] === 'readonly'" :class="{ 'readonly-input': field[2] === 'readonly' }" :step="field[2] === 'number' ? '0.0001' : undefined" :required="field[3]" />
      </div></div>

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
      <div class="modal-foot"><button type="button" class="btn btn-secondary" @click="modalOpen = false">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button></div>
    </form></div>

    <Transition name="detail-drawer" appear>
      <EntityDetailModal v-if="detailId" :entity="config.endpoint" :id="detailId" @close="detailId = null" @edit="editFromDetail" />
    </Transition>
    <div v-if="toast.show" class="toast" :class="{ error: toast.error }">{{ toast.message }}</div>
  </div>
</template>

<style scoped>
.contact-create-section{margin-top:26px;padding-top:22px;border-top:1px solid var(--line)}
.contact-create-head,.contact-card-head,.contact-card-actions,.primary-switch{display:flex;align-items:center}
.contact-create-head,.contact-card-head{justify-content:space-between;gap:16px}
.contact-create-head>div>span{font-size:15px;font-weight:700;color:var(--ink)}
.contact-create-head p{margin:4px 0 0;color:var(--muted);font-size:12px}
.contact-count{flex:none;padding:4px 9px;border-radius:20px;background:#edf3f0;color:#47665c;font-size:11px;font-weight:600}
.contact-create-card{margin-top:14px;padding:16px;border:1px solid #dce5e0;border-radius:12px;background:#fbfcfb}
.contact-card-head strong{font-size:13px;color:#314740}
.contact-card-actions{gap:10px}
.primary-switch{gap:7px;margin:0;color:#53655f;font-size:12px;cursor:pointer}
.primary-switch input{position:absolute;opacity:0;pointer-events:none}
.switch-track{width:34px;height:19px;border-radius:20px;background:#cbd6d1;padding:2px;transition:.2s}
.switch-track i{display:block;width:15px;height:15px;border-radius:50%;background:white;box-shadow:0 1px 4px #173d3633;transition:.2s}
.primary-switch input:checked+.switch-track{background:var(--green-2)}
.primary-switch input:checked+.switch-track i{transform:translateX(15px)}
.contact-fields{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}
.mini-btn.danger{color:var(--danger)}
.add-contact-btn{width:100%;margin-top:12px;padding:11px;border:1px dashed #aac2ba;border-radius:9px;background:#f7faf8;color:var(--green-2);display:flex;align-items:center;justify-content:center;gap:7px;font-size:13px;font-weight:600}
.add-contact-btn:hover{background:#edf5f1;border-color:#719d8f}
.readonly-input{background:#f1f5f3!important;color:#557068!important;cursor:not-allowed}
@media(max-width:760px){.contact-fields{grid-template-columns:1fr 1fr}}
@media(max-width:520px){.contact-create-head,.contact-card-head{align-items:flex-start}.contact-card-head{flex-direction:column}.contact-fields{grid-template-columns:1fr}.contact-card-actions{width:100%;justify-content:space-between}}
</style>
