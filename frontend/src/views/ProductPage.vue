<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ChevronDown, ChevronRight, Database, ListFilter, Pencil, Plus, Search, Trash2, X } from 'lucide-vue-next'
import { api, listData } from '../api'
import EntityDetailModal from '../components/EntityDetailModal.vue'

const products = ref([])
const suppliers = ref([])
const query = ref('')
const categoryFilter = ref('')
const detailId = ref(null)
const categories = ref([])
const loading = ref(true)
const saving = ref(false)
const modalOpen = ref(false)
const editingId = ref(null)
const keepDetailOpen = ref(false)
const detailRefresh = ref(0)
const pickerOpen = ref(false)
const pickerTarget = ref('primary')
const cascadePath = ref([])
const message = reactive({ text: '', error: false })
const form = reactive({ code: '', name: '', name_en: '', hs_code: '', sales_model_prefix: '', category: '', additional_categories: [], suppliers: [], status: 'active', description: '' })

const byId = computed(() => new Map(categories.value.map(item => [item.id, { ...item, children: [] }])))
const roots = computed(() => {
  const map = byId.value
  for (const item of map.values()) if (item.parent && map.has(item.parent)) map.get(item.parent).children.push(item)
  const result = [...map.values()].filter(item => !item.parent || !map.has(item.parent))
  const sort = nodes => { nodes.sort((a, b) => a.sort_order - b.sort_order || a.id - b.id); nodes.forEach(item => sort(item.children)) }
  sort(result)
  return result
})
const cascadeColumns = computed(() => {
  const columns = [roots.value]
  for (const id of cascadePath.value) {
    const children = categories.value.filter(item => Number(item.parent || 0) === Number(id)).sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
    if (!children.length) break
    columns.push(children)
  }
  return columns
})
const categoryName = id => categories.value.find(item => item.id === Number(id))?.name || '请选择'
const title = computed(() => editingId.value ? '编辑产品' : '新建产品')

function notify(text, error = false) { Object.assign(message, { text, error }); setTimeout(() => { message.text = '' }, 2600) }
async function load() {
  loading.value = true
  try {
    const [productResponse, categoryResponse, supplierResponse] = await Promise.all([api.get('/products/', { params: { search: query.value, category: categoryFilter.value } }), api.get('/categories/tree/'), api.get('/suppliers/')])
    products.value = listData(productResponse)
    categories.value = listData(categoryResponse)
    suppliers.value = listData(supplierResponse)
  } catch (error) { notify(error.message, true) } finally { loading.value = false }
}
async function openCreate() {
  keepDetailOpen.value = false
  editingId.value = null
  Object.assign(form, { code: '', name: '', name_en: '', hs_code: '', sales_model_prefix: '', category: '', additional_categories: [], suppliers: [], status: 'active', description: '' })
  try { form.code = (await api.get('/products/next-code/')).data.code } catch { form.code = '保存时自动生成' }
  modalOpen.value = true
}
function openEdit(product, { keepDetail = false } = {}) {
  keepDetailOpen.value = keepDetail
  editingId.value = product.id
  Object.assign(form, { code: product.code, name: product.name, name_en: product.name_en || '', hs_code: product.hs_code || '', sales_model_prefix: product.sales_model_prefix || '', category: product.category || '', additional_categories: [...(product.additional_categories || [])], suppliers: [...(product.suppliers || [])], status: product.status, description: product.description || '' })
  modalOpen.value = true
}
function closeModal() { modalOpen.value = false; keepDetailOpen.value = false }
function categoryAncestors(id) {
  const path = []
  let current = categories.value.find(item => item.id === Number(id))
  while (current?.parent) { path.unshift(current.parent); current = categories.value.find(item => item.id === Number(current.parent)) }
  return path
}
function openPicker(target) {
  const isCurrent = pickerOpen.value && pickerTarget.value === target
  pickerTarget.value = target
  pickerOpen.value = !isCurrent
  if (!isCurrent) cascadePath.value = categoryAncestors(target === 'primary' ? form.category : form.additional_categories[target])
}
function chooseCascadeCategory(category, columnIndex) {
  const children = categories.value.filter(item => Number(item.parent || 0) === Number(category.id))
  if (children.length) { cascadePath.value = [...cascadePath.value.slice(0, columnIndex), category.id]; return }
  selectCategory(category.id)
}
function selectCategory(id) {
  if (pickerTarget.value === 'primary') form.category = id
  else form.additional_categories[pickerTarget.value] = id
  form.additional_categories = form.additional_categories.filter((id, index, list) => id && Number(id) !== Number(form.category) && list.indexOf(id) === index)
  pickerOpen.value = false
}
function addAdditionalCategory() { form.additional_categories.push(''); pickerTarget.value = form.additional_categories.length - 1; pickerOpen.value = true }
function removeAdditionalCategory(index) { form.additional_categories.splice(index, 1) }
async function save() {
  saving.value = true
  try {
    const data = { name: form.name, name_en: form.name_en, hs_code: form.hs_code, sales_model_prefix: form.sales_model_prefix, category: form.category ? Number(form.category) : null, additional_categories: form.additional_categories.filter(Boolean).map(Number), suppliers: form.suppliers.map(Number), status: form.status, description: form.description }
    if (editingId.value) await api.put(`/products/${editingId.value}/`, data)
    else await api.post('/products/', data)
    const refreshDetail = keepDetailOpen.value
    modalOpen.value = false; notify(editingId.value ? '产品已更新' : '产品已创建'); await load()
    if (refreshDetail) detailRefresh.value += 1
    keepDetailOpen.value = false
  } catch (error) { notify(error.message, true) } finally { saving.value = false }
}
async function remove(product) {
  if (!confirm(`确定删除产品“${product.name}”吗？`)) return
  try { await api.delete(`/products/${product.id}/`); notify('产品已删除'); await load() } catch (error) { notify(error.message, true) }
}
onMounted(load)
</script>

<template>
  <div>
    <div class="page-head"><div><h2>产品管理</h2><p>维护产品主档、分类归属与销售状态；SKU 编码在 SKU 管理中维护。</p></div><button class="btn btn-primary" @click="openCreate"><Plus :size="16" /> 新建产品</button></div>
    <div class="product-toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索产品编号、中文/英文名称、HS 编码..." @input="load" /></div><div class="filter-select"><ListFilter :size="16" aria-hidden="true" /><select v-model="categoryFilter" aria-label="产品分类筛选" @change="load"><option value="">全部分类</option><option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option></select><ChevronDown :size="16" aria-hidden="true" /></div></div>
    <section class="panel">
      <div v-if="loading" class="loading"><div class="spinner" /></div>
      <div v-else-if="!products.length" class="empty"><Database :size="32" /><h3>还没有产品</h3><p>点击“新建产品”开始建立产品主档。</p></div>
      <div v-else class="table-wrap"><table class="data-table"><thead><tr><th>产品编号</th><th>产品名称</th><th>销售型号前缀</th><th>主分类</th><th>状态</th><th>SKU</th><th>参数</th><th>证书</th><th /></tr></thead><tbody><tr v-for="product in products" :key="product.id" class="clickable-row" @click="detailId = product.id"><td class="primary-cell">{{ product.code }}</td><td>{{ product.name }}</td><td>{{ product.sales_model_prefix || '—' }}</td><td>{{ product.category_name }}</td><td><span class="tag">{{ product.status === 'active' ? '在售' : product.status === 'development' ? '开发中' : '停产' }}</span></td><td>{{ product.sku_count }}</td><td>{{ product.parameter_count }}</td><td>{{ product.certificate_count }}</td><td><div class="table-actions"><button class="mini-btn" title="编辑产品" @click.stop="openEdit(product)"><Pencil :size="14" /></button><button class="mini-btn danger" title="删除产品" @click.stop="remove(product)"><Trash2 :size="14" /></button></div></td></tr></tbody></table></div>
    </section>

    <div v-if="modalOpen" class="modal-backdrop" @mousedown.self="closeModal"><form class="modal product-modal" @submit.prevent="save"><div class="modal-head"><h3>{{ title }}</h3><button type="button" class="mini-btn" @click="closeModal"><X :size="17" /></button></div><div class="modal-body"><div class="form-grid"><div class="field"><label>产品编号 <em>*</em></label><input v-model="form.code" class="readonly-input" readonly /></div><div class="field"><label>产品名称 <em>*</em></label><input v-model.trim="form.name" placeholder="如：BTY橱柜电源" required /></div>
        <div class="field"><label>销售型号前缀 <em v-if="!editingId">*</em></label><input v-model.trim="form.sales_model_prefix" maxlength="30" pattern="[A-Za-z0-9]+" placeholder="如：BTY、COB320、SMD120" :required="!editingId" @input="form.sales_model_prefix = form.sales_model_prefix.replace(/[^a-zA-Z0-9]/g, '').toUpperCase()" /><p class="field-help">仅字母和数字，且产品之间不可重复；将作为 SKU 销售型号的固定前缀。</p></div>
        <div class="field"><label>产品英文名称</label><input v-model.trim="form.name_en" /></div><div class="field"><label>HS 编码</label><input v-model.trim="form.hs_code" /></div>
        <div class="field category-field"><label>产品分类</label><button type="button" class="category-select" @click.stop="openPicker('primary')"><span>{{ categoryName(form.category) }}</span><ChevronDown :size="16" /></button><div v-if="pickerOpen && pickerTarget === 'primary'" class="category-picker"><div class="picker-head"><strong>选择分类</strong><span>逐级选择最终分类</span></div><div class="cascade-columns"><div v-for="(column, columnIndex) in cascadeColumns" :key="columnIndex" class="cascade-column"><button v-for="category in column" :key="category.id" type="button" class="cascade-option" :class="{ active: cascadePath[columnIndex] === category.id, selected: Number(form.category) === category.id }" @click.stop="chooseCascadeCategory(category, columnIndex)"><span>{{ category.name }}</span><ChevronRight v-if="categories.some(item => Number(item.parent || 0) === Number(category.id))" :size="15" /></button></div></div></div></div><div class="field"><label>状态 <em>*</em></label><select v-model="form.status"><option value="active">在售</option><option value="development">开发中</option><option value="discontinued">停产</option></select></div>
        <div class="field full"><label>供应商</label><select v-model="form.suppliers" class="supplier-select" multiple><option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">{{ supplier.name }}{{ supplier.contact_name ? ` · ${supplier.contact_name}` : '' }}</option></select><p class="field-help">按住 Ctrl / ⌘ 可选择多个供应商；未选择时可后续在编辑产品中补充。</p></div>
        <div class="field full"><div class="additional-head"><label>附加分类</label><button type="button" class="text-add" @click.stop="addAdditionalCategory"><Plus :size="14" /> 新增</button></div><div v-if="form.additional_categories.length" class="additional-list"><div v-for="(id, index) in form.additional_categories" :key="index" class="additional-row category-field"><button type="button" class="category-select" @click.stop="openPicker(index)"><span>{{ categoryName(id) }}</span><ChevronDown :size="16" /></button><button type="button" class="mini-btn danger" title="移除附加分类" @click.stop="removeAdditionalCategory(index)"><Trash2 :size="14" /></button><div v-if="pickerOpen && pickerTarget === index" class="category-picker"><div class="picker-head"><strong>选择附加分类</strong><span>逐级选择最终分类</span></div><div class="cascade-columns"><div v-for="(column, columnIndex) in cascadeColumns" :key="columnIndex" class="cascade-column"><button v-for="category in column" :key="category.id" type="button" class="cascade-option" :class="{ active: cascadePath[columnIndex] === category.id, selected: form.additional_categories.map(Number).includes(category.id) }" @click.stop="chooseCascadeCategory(category, columnIndex)"><span>{{ category.name }}</span><ChevronRight v-if="categories.some(item => Number(item.parent || 0) === Number(category.id))" :size="15" /></button></div></div></div></div></div><p v-else class="field-help">可为同一产品添加第二、第三个分类，用于多维筛选与分析。</p></div>
        <div class="field full"><label>产品描述</label><textarea v-model="form.description" /></div></div>
      </div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="closeModal">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button></div></form></div>
    <div v-if="message.text" class="toast" :class="{ error: message.error }">{{ message.text }}</div>
    <Transition name="detail-drawer" appear><EntityDetailModal v-if="detailId" entity="products" :id="detailId" :refresh-key="detailRefresh" @close="detailId = null" @edit="openEdit(products.find(product => product.id === detailId), { keepDetail: true })" /></Transition>
  </div>
</template>

<style scoped>
.product-toolbar{display:flex;gap:12px;margin-bottom:14px}.product-toolbar .search-box{flex:1;max-width:430px}.filter-select{position:relative;display:flex;align-items:center;min-width:192px;height:42px;padding:0 11px;gap:8px;border:1px solid #d7e2dd;border-radius:10px;background:#fff;color:#3e655a;box-shadow:0 1px 2px #173d3608;transition:border-color .18s,box-shadow .18s,background .18s}.filter-select:focus-within{border-color:#2c8068;background:#fcfffd;box-shadow:0 0 0 3px #d9eee6}.filter-select>svg:first-child{color:#2f806a}.filter-select>svg:last-child{margin-left:auto;pointer-events:none;color:#6d877e;transition:transform .18s}.filter-select:focus-within>svg:last-child{transform:rotate(180deg)}.filter-select select{appearance:none;min-width:0;flex:1;height:100%;padding:0;border:0;outline:0;background:transparent;color:#193d33;font:600 14px inherit;cursor:pointer}.product-modal{width:min(820px,calc(100vw - 64px))}.readonly-input{background:#f1f5f3!important;color:#557068!important;cursor:not-allowed}.category-field{position:relative}.category-select{width:100%;height:40px;padding:0 11px;display:flex;align-items:center;justify-content:space-between;border:1px solid var(--line);border-radius:8px;background:white;color:var(--ink);font:inherit;font-size:14px;text-align:left}.category-select:hover{border-color:#8eb6a8}.supplier-select{min-height:104px;padding:6px 8px}.supplier-select option{padding:7px 8px;border-radius:4px}.additional-head{display:flex;align-items:center;justify-content:space-between}.text-add{display:inline-flex;align-items:center;gap:4px;border:0;background:transparent;color:var(--green-2);font-weight:700}.additional-list{display:grid;gap:8px;margin-top:8px}.additional-row{display:flex;gap:8px}.additional-row .mini-btn{flex:none}.field-help{margin:7px 0 0;color:var(--muted);font-size:12px}.category-picker{position:absolute;z-index:12;left:0;top:calc(100% + 5px);width:max-content;min-width:100%;max-width:min(720px,calc(100vw - 80px));border:1px solid #c8ddd5;border-radius:10px;overflow:hidden;background:#fbfdfc;box-shadow:0 12px 26px #173d3624}.additional-row .category-picker{width:max-content;min-width:calc(100% - 40px)}.picker-head{display:flex;justify-content:space-between;align-items:center;padding:11px 13px;background:#edf5f1;border-bottom:1px solid #dceae4}.picker-head strong{font-size:13px}.picker-head span{font-size:11px;color:#69827a}.cascade-columns{display:flex;min-height:210px;max-height:260px;overflow:auto;background:#fff}.cascade-column{width:180px;min-width:160px;padding:6px;overflow-y:auto;border-right:1px solid #e1ebe6}.cascade-column:last-child{border-right:0}.cascade-option{width:100%;min-height:34px;padding:6px 8px;display:flex;align-items:center;justify-content:space-between;gap:8px;border:0;border-radius:6px;background:transparent;color:#29473e;font:inherit;font-size:14px;text-align:left;cursor:pointer}.cascade-option:hover,.cascade-option.active,.cascade-option.selected{background:#e1f0ea}.cascade-option svg{flex:none;color:#69827a}.table-actions{display:flex;justify-content:flex-end;gap:6px}.mini-btn.danger{color:var(--danger)}
</style>
