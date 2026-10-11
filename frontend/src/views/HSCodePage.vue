<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Link2, Pencil, Plus, Search, X } from 'lucide-vue-next'
import { api, listAll } from '../api'
import { useAccessControl } from '../accessControl'
import SummaryCards from '../components/SummaryCards.vue'

const rows = ref([])
const products = ref([])
const query = ref('')
const loading = ref(true)
const saving = ref(false)
const canManage = ref(false)
const { can } = useAccessControl()
const mayCreate = computed(() => can('hs_codes', 'create') && canManage.value)
const mayUpdate = computed(() => can('hs_codes', 'update') && canManage.value)
const mayDelete = computed(() => can('hs_codes', 'delete') && canManage.value)
const message = reactive({ text: '', error: false })
const editingId = ref(null)
const formOpen = ref(false)
const assignmentOpen = ref(false)
const assignmentQuery = ref('')
const active = ref(null)
const form = reactive({ code: '', description: '', notes: '', active: true })
const selectedProductIds = ref([])

const filtered = computed(() => {
  const value = query.value.trim().toLowerCase()
  return value ? rows.value.filter(row => `${row.code} ${row.description} ${row.notes}`.toLowerCase().includes(value)) : rows.value
})
const assignmentProducts = computed(() => {
  const value = assignmentQuery.value.trim().toLowerCase()
  return value ? products.value.filter(product => `${product.code} ${product.name} ${product.name_en}`.toLowerCase().includes(value)) : products.value
})
const metrics = computed(() => [
  { label: 'HS 编码', value: rows.value.length, hint: '受控编码目录' },
  { label: '启用编码', value: rows.value.filter(row => row.active).length, hint: '可继续分配' },
  { label: '已分配产品', value: rows.value.reduce((sum, row) => sum + Number(row.product_count || 0), 0), hint: '当前关联记录' },
])

function notify(text, error = false) { Object.assign(message, { text, error }); setTimeout(() => { message.text = '' }, 3000) }
function resetForm(row = null) { Object.assign(form, { code: row?.code || '', description: row?.description || '', notes: row?.notes || '', active: row?.active ?? true }) }
async function load() {
  loading.value = true
  try {
    const [codes, productRows, session] = await Promise.all([listAll('/hs-codes/'), listAll('/products/'), api.get('/session/current-operator/')])
    rows.value = codes
    products.value = productRows
    canManage.value = session.data.can_manage_hs_codes === true
  }
  catch (error) { notify(error.message, true) }
  finally { loading.value = false }
}
function create() { if (!mayCreate.value) return; editingId.value = null; resetForm(); formOpen.value = true }
function edit(row) { if (!mayUpdate.value) return; editingId.value = row.id; resetForm(row); formOpen.value = true }
async function save() {
  if (!(editingId.value ? mayUpdate.value : mayCreate.value)) return
  saving.value = true
  try {
    const payload = { ...form, code: form.code.trim().toUpperCase() }
    if (editingId.value) await api.put(`/hs-codes/${editingId.value}/`, payload)
    else await api.post('/hs-codes/', payload)
    formOpen.value = false
    await load()
    notify(editingId.value ? 'HS 编码已更新' : 'HS 编码已创建')
  } catch (error) { notify(error.message, true) }
  finally { saving.value = false }
}
function openAssignment(row) {
  if (!mayUpdate.value) return
  active.value = row
  assignmentQuery.value = ''
  selectedProductIds.value = products.value.filter(product => Number(product.hs_code) === Number(row.id)).map(product => Number(product.id))
  assignmentOpen.value = true
}
function toggleProduct(id) {
  if (!mayUpdate.value) return
  const normalized = Number(id)
  selectedProductIds.value = selectedProductIds.value.includes(normalized)
    ? selectedProductIds.value.filter(item => item !== normalized)
    : [...selectedProductIds.value, normalized]
}
async function saveAssignment() {
  if (!mayUpdate.value) return
  if (!active.value) return
  saving.value = true
  try {
    await api.put(`/hs-codes/${active.value.id}/assign-products/`, { product_ids: selectedProductIds.value })
    assignmentOpen.value = false
    await load()
    notify(`已为 ${selectedProductIds.value.length} 个产品分配 ${active.value.code}`)
  } catch (error) { notify(error.message, true) }
  finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <section class="hs-code-page">
    <div class="page-head"><div><h2>HS 编码维护</h2><p>由管理员统一维护编码目录，并在此处分配给产品；产品建档不再填写 HS 编码。</p></div><button v-if="mayCreate" class="btn btn-primary" @click="create"><Plus :size="16" /> 新建 HS 编码</button></div>
    <SummaryCards :items="metrics" />
    <section class="panel hs-list"><div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索 HS 编码、商品描述或备注" /></div></div><div v-if="loading" class="loading"><div class="spinner" /></div><div v-else-if="!filtered.length" class="empty"><Search :size="32" /><h3>尚无 HS 编码</h3><p>请先建立受控编码，再为产品统一分配。</p></div><div v-else class="table-wrap"><table class="data-table"><thead><tr><th>HS 编码</th><th>商品描述</th><th>状态</th><th>关联产品</th><th>备注</th><th>操作</th></tr></thead><tbody><tr v-for="row in filtered" :key="row.id"><td class="primary-cell">{{ row.code }}</td><td>{{ row.description || '—' }}</td><td><span class="tag" :class="{ inactive: !row.active }">{{ row.active ? '启用' : '停用' }}</span></td><td>{{ row.product_count || 0 }} 个</td><td class="notes-cell">{{ row.notes || '—' }}</td><td><div v-if="mayUpdate" class="table-actions"><button class="mini-btn" title="分配产品" @click="openAssignment(row)"><Link2 :size="15" /></button><button class="mini-btn" title="编辑 HS 编码" @click="edit(row)"><Pencil :size="15" /></button></div></td></tr></tbody></table></div></section>

    <div v-if="formOpen && (editingId ? mayUpdate : mayCreate)" class="modal-backdrop" @mousedown.self="formOpen=false"><form class="modal hs-modal" @submit.prevent="save"><div class="modal-head"><div><h3>{{ editingId ? '编辑 HS 编码' : '新建 HS 编码' }}</h3><p>编码由管理员维护，产品页面不可直接修改。</p></div><button type="button" class="mini-btn" @click="formOpen=false"><X :size="17" /></button></div><div class="modal-body"><div class="form-grid"><div class="field"><label>HS 编码 <em>*</em></label><input v-model="form.code" required maxlength="30" placeholder="如：8539510000" /></div><div class="field"><label>商品描述</label><input v-model.trim="form.description" maxlength="300" placeholder="如：LED 灯具" /></div><label class="check"><input v-model="form.active" type="checkbox" /> 启用编码</label><div class="field full"><label>备注</label><textarea v-model.trim="form.notes" placeholder="适用范围或归类说明" /></div></div></div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="formOpen=false">取消</button><button v-if="editingId ? mayUpdate : mayCreate" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button></div></form></div>

    <div v-if="assignmentOpen && active && mayUpdate" class="modal-backdrop" @mousedown.self="assignmentOpen=false"><section class="modal wide assignment-modal"><div class="modal-head"><div><h3>分配产品 · {{ active.code }}</h3><p>勾选的产品将绑定此 HS 编码；取消勾选会解除当前编码的绑定。已绑定其他编码的产品将改用此编码。</p></div><button class="mini-btn" @click="assignmentOpen=false"><X :size="17" /></button></div><div class="modal-body"><div class="search-box"><Search :size="17" /><input v-model="assignmentQuery" placeholder="搜索产品编号或名称" /></div><div class="assignment-list"><label v-for="product in assignmentProducts" :key="product.id" :class="{ selected: selectedProductIds.includes(Number(product.id)) }"><input type="checkbox" :checked="selectedProductIds.includes(Number(product.id))" @change="toggleProduct(product.id)" /><span><strong>{{ product.name }}</strong><small>{{ product.code }} · 当前：{{ product.hs_code_value || '未分配' }}</small></span></label><p v-if="!assignmentProducts.length">没有匹配的产品。</p></div></div><div class="modal-foot"><button class="btn btn-secondary" @click="assignmentOpen=false">取消</button><button v-if="mayUpdate" class="btn btn-primary" :disabled="saving" @click="saveAssignment">{{ saving ? '保存中…' : `保存 ${selectedProductIds.length} 项分配` }}</button></div></section></div>
    <div v-if="message.text" class="toast" :class="{ error: message.error }">{{ message.text }}</div>
  </section>
</template>

<style scoped>
.hs-list{padding:0}.toolbar{padding:17px 20px;border-bottom:1px solid var(--line)}.toolbar .search-box{max-width:440px}.notes-cell{max-width:330px;color:var(--muted)}.table-actions{display:flex;justify-content:flex-end;gap:6px}.tag.inactive{background:#f2eded;color:#9d5959}.hs-modal{width:min(650px,calc(100vw - 28px))}.assignment-modal{width:min(760px,calc(100vw - 28px))}.modal-head>div p{margin:4px 0 0;color:var(--muted);font-size:var(--text-body)}.check{display:flex;align-items:center;gap:8px;padding-top:25px;color:#40534c;font-size:var(--text-body)}.check input{accent-color:var(--green-2)}.assignment-list{max-height:420px;margin-top:14px;overflow:auto;border:1px solid var(--line);border-radius:9px}.assignment-list label{display:flex;align-items:center;gap:10px;padding:11px 13px;border-bottom:1px solid #e9eeeb;cursor:pointer}.assignment-list label:last-child{border-bottom:0}.assignment-list label:hover,.assignment-list label.selected{background:#eff8f3}.assignment-list input{width:16px;height:16px;accent-color:var(--green-2)}.assignment-list span{display:grid;gap:3px;min-width:0}.assignment-list strong{font-size:var(--text-body);color:#294b40}.assignment-list small{color:#7e9088;font-size:var(--text-caption)}.assignment-list p{margin:0;padding:32px;color:var(--muted);text-align:center}@media(max-width:680px){.page-head{align-items:flex-start;flex-direction:column}.page-head .btn{width:100%}.check{padding-top:0}}
</style>
