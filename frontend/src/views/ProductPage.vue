<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, listAll } = useWorkspaceApi()
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronDown, ChevronRight, Database, ListFilter, Pencil, Plus, Search, Trash2, X } from 'lucide-vue-next'
import { listData } from '../api'
import { useAccessControl } from '../accessControl'
import { apiErrorMessage } from '../utils/apiErrors.js'
import { confirmDialog } from '../dialogs'
import { internalPagePath } from '../utils/modalNavigation'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import EntityDetailModal from '../components/EntityDetailModal.vue'
import SummaryCards from '../components/SummaryCards.vue'
import PageLoadState from '../components/PageLoadState.vue'
import ListEmptyState from '../components/ListEmptyState.vue'

const route = useRoute()
const router = useRouter()
const { can } = useAccessControl()
const products = ref([])
const suppliers = ref([])
const query = ref(typeof route.query.search === 'string' ? route.query.search : '')
const categoryFilter = ref(route.query.category || '')
const sortOrder = ref(route.query.sort || 'code')
const detailId = ref(null)
const categories = ref([])
const loading = ref(true), hasLoaded = ref(false), loadError = ref(''), allProductsExist = ref(false)
const referenceErrors = reactive({}), referenceLoaded = reactive({})
const formOptionsReady = computed(() => referenceLoaded.categories && referenceLoaded.suppliers && !referenceErrors.categories && !referenceErrors.suppliers)
const filteredProductEmpty = computed(() => Boolean((query.value || categoryFilter.value) && allProductsExist.value))
const saving = ref(false)
const modalOpen = ref(false)
const editingId = ref(null)
const keepDetailOpen = ref(false)
const detailRefresh = ref(0)
const editingProduct = ref(null)
const prefixReview = ref(null)
const pickerOpen = ref(false)
const pickerTarget = ref('primary')
const cascadePath = ref([])
const supplierQuery = ref('')
const message = reactive({ text: '', error: false })
const form = reactive({ code: '', name: '', name_en: '', sales_model_prefix: '', category: '', additional_categories: [], suppliers: [], status: 'active', description: '' })

const saveError = ref('')
const guard = useUnsavedChangesGuard({ data: () => form, enabled: () => modalOpen.value, busy: () => modalOpen.value && saving.value })
const orderedProducts = computed(() => [...products.value].sort((a, b) => sortOrder.value === 'name' ? a.name.localeCompare(b.name, 'zh-CN') : sortOrder.value === 'sku' ? Number(b.sku_count || 0) - Number(a.sku_count || 0) || a.code.localeCompare(b.code) : a.code.localeCompare(b.code)))
function applyFilters() { return router.replace({ path: route.path, query: { ...route.query, search: query.value || undefined, category: categoryFilter.value || undefined, sort: sortOrder.value === 'code' ? undefined : sortOrder.value } }) }
let loadVersion = 0, messageTimer
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
const productMetrics = computed(() => [
  { label: '产品总数', value: products.value.length, hint: '当前筛选范围' },
  { label: '在售产品', value: products.value.filter(row => row.status === 'active').length, hint: '可继续添加 SKU' },
  { label: '开发中', value: products.value.filter(row => row.status === 'development').length, hint: '尚未正式销售' },
  { label: 'SKU 总数', value: products.value.reduce((sum, row) => sum + Number(row.sku_count || 0), 0), hint: '产品下的 SKU' },
])
const categoryPickerLayout = computed(() => {
  const columnWidths = []
  const visit = (nodes, depth = 0) => {
    if (!nodes.length) return
    const longestName = Math.max(...nodes.map(node => Array.from(node.name || '').length))
    columnWidths[depth] = Math.max(columnWidths[depth] || 0, Math.min(210, Math.max(160, longestName * 14 + 52)))
    nodes.forEach(node => visit(node.children || [], depth + 1))
  }
  visit(roots.value)
  const widths = columnWidths.length ? columnWidths : [160]
  const pickerWidth = widths.reduce((sum, width) => sum + width, 0) + widths.length - 1
  const rightColumnWidth = Math.max(360, pickerWidth)
  return { columnWidths: widths, pickerWidth, modalWidth: Math.max(820, 360 + 17 + 44 + rightColumnWidth) }
})
const productModalStyle = computed(() => ({
  '--category-picker-width': `${categoryPickerLayout.value.pickerWidth}px`,
  '--product-modal-width': `${categoryPickerLayout.value.modalWidth}px`,
}))
const filteredSuppliers = computed(() => {
  const keyword = supplierQuery.value.trim().toLocaleLowerCase()
  if (!keyword) return suppliers.value
  return suppliers.value.filter(supplier => [supplier.name, supplier.contact_name, supplier.phone, supplier.email]
    .filter(Boolean)
    .some(value => String(value).toLocaleLowerCase().includes(keyword)))
})
const selectedSuppliers = computed(() => suppliers.value.filter(supplier => form.suppliers.map(Number).includes(Number(supplier.id))))

function notify(text, error = false) { clearTimeout(messageTimer); Object.assign(message, { text, error }); messageTimer = setTimeout(() => { message.text = '' }, 2600) }
async function load() {
  const request = ++loadVersion
  loading.value = true
  loadError.value = ''
  const [productResult, categoryResult, supplierResult] = await Promise.allSettled([
    listAll('/products/', { params: { search: query.value, category: categoryFilter.value } }),
    api.get('/categories/tree/'),
    listAll('/suppliers/'),
  ])
  if (request !== loadVersion) return
  if (productResult.status === 'fulfilled') {
    products.value = productResult.value
    hasLoaded.value = true
    allProductsExist.value = products.value.length > 0
    if (!products.value.length && (query.value || categoryFilter.value)) {
      let exists = false
      try { exists = (await listAll('/products/')).length > 0 } catch { /* Keep the empty-state fallback. */ }
      if (request !== loadVersion) return
      allProductsExist.value = exists
    }
  } else loadError.value = apiErrorMessage(productResult.reason)
  if (categoryResult.status === 'fulfilled') { categories.value = listData(categoryResult.value); referenceLoaded.categories = true; delete referenceErrors.categories }
  else referenceErrors.categories = `产品分类资料加载失败：${apiErrorMessage(categoryResult.reason)}`
  if (supplierResult.status === 'fulfilled') { suppliers.value = supplierResult.value; referenceLoaded.suppliers = true; delete referenceErrors.suppliers }
  else referenceErrors.suppliers = `供应商资料加载失败：${apiErrorMessage(supplierResult.reason)}`
  loading.value = false
}
function clearProductFilters() { query.value = ''; categoryFilter.value = ''; sortOrder.value = 'code'; return applyFilters() }
async function openCreate() {
  if (!can('products', 'create')) return
  keepDetailOpen.value = false
  editingId.value = null
  editingProduct.value = null
  prefixReview.value = null
  supplierQuery.value = ''
  Object.assign(form, { code: '', name: '', name_en: '', sales_model_prefix: '', category: '', additional_categories: [], suppliers: [], status: 'active', description: '' })
  try { form.code = (await api.get('/products/next-code/')).data.code } catch { form.code = '保存时自动生成' }
  saveError.value = ''; message.text = ''; pickerOpen.value = false
  modalOpen.value = true
  guard.markClean()
}
function openEdit(product, { keepDetail = false } = {}) {
  if (!can('products', 'update')) return
  keepDetailOpen.value = keepDetail
  editingId.value = product.id
  editingProduct.value = { ...product, additional_categories: [...(product.additional_categories || [])], suppliers: [...(product.suppliers || [])] }
  supplierQuery.value = ''
  Object.assign(form, { code: product.code, name: product.name, name_en: product.name_en || '', sales_model_prefix: product.sales_model_prefix || '', category: product.category || '', additional_categories: [...(product.additional_categories || [])], suppliers: [...(product.suppliers || [])], status: product.status, description: product.description || '' })
  saveError.value = ''; message.text = ''; pickerOpen.value = false
  modalOpen.value = true
  guard.markClean()
}
function closeModal() { return guard.requestClose(() => { modalOpen.value = false; keepDetailOpen.value = false; prefixReview.value = null; editingProduct.value = null; pickerOpen.value = false }) }
async function closeDetail() {
  const origin = internalPagePath(route.query.returnTo)
  if (origin) { void router.push(origin); return }
  const closedId = detailId.value
  detailId.value = null
  if (!route.query.detail) return
  const { detail, tab, returnTo, ...query } = route.query
  await router.replace({ path: route.path, query, hash: route.hash })
  await nextTick()
  const activePane = document.querySelector('.workspace-pane[aria-hidden="false"]')
  const row = [...(activePane?.querySelectorAll('[data-product-row]') || [])]
    .find(element => element.dataset.productRow === String(closedId))
  row?.focus({ preventScroll: true })
}
function openDetail(id) { return router.push({ path: route.path, query: { ...route.query, detail: String(id), tab: undefined } }) }
async function editDetail() {
  try { openEdit(products.value.find(product => product.id === detailId.value) || (await api.get(`/products/${detailId.value}/`)).data, { keepDetail: true }) }
  catch (error) { notify(apiErrorMessage(error), true) }
}
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
function toggleSupplier(id) {
  const normalized = Number(id)
  const selected = form.suppliers.map(Number)
  form.suppliers = selected.includes(normalized)
    ? selected.filter(item => item !== normalized)
    : [...selected, normalized]
}
function productPayload({ includePrefix = true } = {}) {
  const data = {
    name: form.name,
    name_en: form.name_en,
    category: form.category ? Number(form.category) : null,
    additional_categories: form.additional_categories.filter(Boolean).map(Number),
    suppliers: form.suppliers.map(Number),
    status: form.status,
    description: form.description,
  }
  if (includePrefix) data.sales_model_prefix = form.sales_model_prefix
  return data
}
function sameIds(left = [], right = []) {
  return left.map(Number).sort().join(',') === right.map(Number).sort().join(',')
}
function prefixChanged() {
  return Boolean(editingProduct.value) && form.sales_model_prefix !== (editingProduct.value.sales_model_prefix || '')
}
function hasOtherProductChanges() {
  const original = editingProduct.value
  return form.name !== original.name
    || form.name_en !== (original.name_en || '')
    || Number(form.category || 0) !== Number(original.category || 0)
    || !sameIds(form.additional_categories, original.additional_categories)
    || !sameIds(form.suppliers, original.suppliers)
    || form.status !== original.status
    || form.description !== (original.description || '')
}
async function save() {
  if (saving.value) return
  saveError.value = ''; message.text = ''
  if (!can('products', editingId.value ? 'update' : 'create')) return
  if (!formOptionsReady.value) return notify('产品分类或供应商资料未加载，请点“刷新”后再保存。', true)
  saving.value = true
  try {
    if (editingId.value && editingProduct.value?.sku_count > 0 && prefixChanged()) {
      if (hasOtherProductChanges()) {
        notify('已有 SKU 时，修改前缀需先预览并确认；其他产品资料请单独保存。', true)
        return
      }
      prefixReview.value = (await api.post(`/products/${editingId.value}/sales-model-prefix-preview/`, {
        sales_model_prefix: form.sales_model_prefix,
      })).data
      return
    }
    if (editingId.value) await api.put(`/products/${editingId.value}/`, productPayload())
    else await api.post('/products/', productPayload())
    const refreshDetail = keepDetailOpen.value
    guard.markClean(); modalOpen.value = false; notify(editingId.value ? '产品已更新' : '产品已创建'); await load()
    if (refreshDetail) detailRefresh.value += 1
    keepDetailOpen.value = false
  } catch (error) { saveError.value = apiErrorMessage(error); notify(saveError.value, true) } finally { saving.value = false }
}
async function confirmPrefixChange() {
  if (saving.value) return
  saveError.value = ''; message.text = ''
  if (!can('products', 'update')) return
  saving.value = true
  try {
    await api.post(`/products/${editingId.value}/sales-model-prefix-apply/`, {
      sales_model_prefix: prefixReview.value.new_prefix,
      baseline: prefixReview.value.baseline,
    })
    const refreshDetail = keepDetailOpen.value
    guard.markClean()
    prefixReview.value = null
    modalOpen.value = false
    notify('销售型号前缀及当前 SKU 销售型号已更新')
    await load()
    if (refreshDetail) detailRefresh.value += 1
    keepDetailOpen.value = false
  } catch (error) { saveError.value = apiErrorMessage(error); notify(saveError.value, true) } finally { saving.value = false }
}
async function remove(product) {
  if (!can('products', 'delete')) return
  if (!await confirmDialog({ title: '确认删除产品', message: `确定删除产品“${product.name}”吗？`, confirmText: '确认删除', danger: true })) return
  try { await api.delete(`/products/${product.id}/`); notify('产品已删除'); await load() } catch (error) { notify(error.message, true) }
}
onMounted(async () => {
  await load()
  if (route.query.detail) detailId.value = Number(route.query.detail)
})
watch(() => [route.query.search, route.query.category, route.query.sort], () => { query.value = route.query.search || ''; categoryFilter.value = route.query.category || ''; sortOrder.value = route.query.sort || 'code'; void load() })
watch(() => route.query.detail, id => { detailId.value = id ? Number(id) : null })
</script>

<template>
  <div>
    <div class="page-head"><div><h2>产品管理</h2><p>维护产品名称、分类和销售状态；SKU 编码请在“SKU 管理”中维护。</p></div><button v-if="can('products', 'create')" class="btn btn-primary" @click="openCreate"><Plus :size="16" /> 新建产品</button></div>
    <SummaryCards v-if="hasLoaded" :items="productMetrics" />
    <div class="product-toolbar" @keydown.enter="applyFilters"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索产品编号或名称" aria-label="搜索产品" /></div><div class="filter-select"><ListFilter :size="16" aria-hidden="true" /><select v-model="categoryFilter" aria-label="产品分类筛选" @change="applyFilters"><option value="">全部分类</option><option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option></select><ChevronDown :size="16" aria-hidden="true" /></div><select v-model="sortOrder" aria-label="产品排序" @change="applyFilters"><option value="code">产品编号顺序</option><option value="name">产品名称顺序</option><option value="sku">SKU 数量最多</option></select><button class="btn btn-primary" @click="applyFilters">查询</button><button class="btn btn-secondary" @click="clearProductFilters">重置</button><button class="btn btn-secondary" :disabled="loading" @click="load">刷新</button></div>
    <div v-if="Object.keys(referenceErrors).length" class="option-load-error" role="alert"><span>{{ Object.values(referenceErrors).join('；') }}</span><button type="button" @click="load">重新加载关联资料</button></div>
    <section class="panel">
      <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="loadError" @retry="load" />
      <ListEmptyState v-if="hasLoaded && !products.length" entity="产品" :filtered="filteredProductEmpty" @clear="clearProductFilters"><template #action><p>选择“新建产品”添加产品资料。</p></template></ListEmptyState>
      <div v-else-if="hasLoaded && products.length" class="table-wrap"><table class="data-table product-list-table"><thead><tr><th>产品编号</th><th>产品名称</th><th>销售型号前缀</th><th>主分类</th><th>状态</th><th>SKU</th><th>参数</th><th>证书</th><th /></tr></thead><tbody><tr v-for="product in orderedProducts" :key="product.id" :data-product-row="product.id" class="clickable-row" tabindex="0" @click="openDetail(product.id)" @keydown.enter="openDetail(product.id)"><td class="primary-cell">{{ product.code }}</td><td><strong>{{ product.name }}</strong><small class="product-secondary">{{ product.name_en || '未填写英文名称' }}</small></td><td>{{ product.sales_model_prefix || '—' }}</td><td>{{ product.category_name }}</td><td><span class="tag">{{ product.status === 'active' ? '在售' : product.status === 'development' ? '开发中' : '停产' }}</span></td><td>{{ product.sku_count }}</td><td>{{ product.parameter_count }}</td><td>{{ product.certificate_count }}</td><td><div class="table-actions"><button v-if="can('products', 'update')" class="mini-btn" title="编辑产品" @click.stop="openEdit(product)"><Pencil :size="14" /></button><button v-if="can('products', 'delete')" class="mini-btn danger" title="删除产品" @click.stop="remove(product)"><Trash2 :size="14" /></button></div></td></tr></tbody></table></div>
    </section>

    <div v-if="modalOpen" class="modal-backdrop"><form class="modal product-modal" role="dialog" aria-modal="true" :aria-label="title" :style="productModalStyle" @submit.prevent="save"><div class="modal-head"><h3>{{ title }}</h3><button type="button" class="mini-btn" :disabled="saving" aria-label="关闭产品表单" @click="closeModal"><X :size="17" /></button></div><div class="modal-body"><p v-if="saveError" class="option-load-error" role="alert">{{ saveError }}</p><h4 class="product-group-title">基本资料</h4><div v-if="Object.keys(referenceErrors).length" class="option-load-error" role="alert"><p v-for="(message,key) in referenceErrors" :key="key">{{ message }} <button type="button" @click="load">重新加载</button></p></div><div class="form-grid" :inert="saving"><div class="field"><label>产品编号 <em>*</em></label><input v-model="form.code" class="readonly-input" readonly /></div><div class="field"><label>产品名称 <em>*</em></label><input v-model.trim="form.name" placeholder="如：BTY橱柜电源" required /></div>
        <div class="field"><label>销售型号前缀 <em v-if="!editingId">*</em></label><input v-model.trim="form.sales_model_prefix" maxlength="30" pattern="[A-Za-z0-9]+" placeholder="如：BTY、COB320、SMD120" :required="!editingId" @input="form.sales_model_prefix = form.sales_model_prefix.replace(/[^a-zA-Z0-9]/g, '').toUpperCase()" /><p class="field-help">仅填字母或数字，且不能与其他产品重复。已有 SKU 时，修改前缀需先预览并确认。</p></div>
        <div class="field"><label>产品英文名称</label><input v-model.trim="form.name_en" /></div>
        <h4 class="product-group-title full">分类与销售状态</h4><div class="field category-field"><label>主分类</label><button type="button" class="category-select" @click.stop="openPicker('primary')"><span>{{ categoryName(form.category) }}</span><ChevronDown :size="16" /></button><div v-if="pickerOpen && pickerTarget === 'primary'" class="category-picker"><div class="picker-head"><strong>选择分类</strong><span>点击分类展开；“选择”可直接归属到当前层级</span></div><div class="cascade-columns"><div v-for="(column, columnIndex) in cascadeColumns" :key="columnIndex" class="cascade-column" :style="{ width: `${categoryPickerLayout.columnWidths[columnIndex] || 160}px` }"><div v-for="category in column" :key="category.id" class="cascade-entry"><button v-if="categories.some(item => Number(item.parent || 0) === Number(category.id))" type="button" class="cascade-select" :aria-label="`选择分类 ${category.name}`" @click.stop="selectCategory(category.id)">选择</button><button type="button" class="cascade-option" :class="{ active: cascadePath[columnIndex] === category.id, selected: Number(form.category) === category.id }" @click.stop="chooseCascadeCategory(category, columnIndex)"><span>{{ category.name }}</span><ChevronRight v-if="categories.some(item => Number(item.parent || 0) === Number(category.id))" :size="15" /></button></div></div></div></div></div><div class="field"><label>状态 <em>*</em></label><select v-model="form.status"><option value="active">在售</option><option value="development">开发中</option><option value="discontinued">停产</option></select></div>
        <h4 class="product-group-title full">供应来源</h4><div class="field full supplier-field"><label>供应商</label><div class="supplier-picker"><div class="supplier-search"><Search :size="16" aria-hidden="true" /><input v-model.trim="supplierQuery" type="search" placeholder="搜索供应商名称、联系人、电话或邮箱" aria-label="搜索供应商" /><span v-if="form.suppliers.length" class="supplier-count">已选 {{ form.suppliers.length }}</span></div><div v-if="selectedSuppliers.length" class="selected-suppliers"><span v-for="supplier in selectedSuppliers" :key="supplier.id" class="supplier-chip">{{ supplier.name }}<button type="button" :aria-label="`移除供应商 ${supplier.name}`" @click="toggleSupplier(supplier.id)"><X :size="13" /></button></span></div><div class="supplier-options" role="listbox" aria-multiselectable="true"><label v-for="supplier in filteredSuppliers" :key="supplier.id" class="supplier-option" :class="{ selected: form.suppliers.map(Number).includes(Number(supplier.id)) }"><input type="checkbox" :checked="form.suppliers.map(Number).includes(Number(supplier.id))" @change="toggleSupplier(supplier.id)" /><span><strong>{{ supplier.name }}</strong><small>{{ [supplier.contact_name, supplier.phone, supplier.email].filter(Boolean).join(' · ') || '未维护联系人信息' }}</small></span></label><p v-if="!filteredSuppliers.length" class="supplier-empty">没有匹配的供应商</p></div></div><p class="field-help">可多选；输入关键词即可筛选供应商。</p></div>
        <div class="field full"><div class="additional-head"><label>附加分类</label><button type="button" class="text-add" @click.stop="addAdditionalCategory"><Plus :size="14" /> 新增</button></div><div v-if="form.additional_categories.length" class="additional-list"><div v-for="(id, index) in form.additional_categories" :key="index" class="additional-row category-field"><button type="button" class="category-select" @click.stop="openPicker(index)"><span>{{ categoryName(id) }}</span><ChevronDown :size="16" /></button><button type="button" class="mini-btn danger" title="移除附加分类" @click.stop="removeAdditionalCategory(index)"><Trash2 :size="14" /></button><div v-if="pickerOpen && pickerTarget === index" class="category-picker"><div class="picker-head"><strong>选择附加分类</strong><span>点击分类展开；“选择”可直接归属到当前层级</span></div><div class="cascade-columns"><div v-for="(column, columnIndex) in cascadeColumns" :key="columnIndex" class="cascade-column" :style="{ width: `${categoryPickerLayout.columnWidths[columnIndex] || 160}px` }"><div v-for="category in column" :key="category.id" class="cascade-entry"><button v-if="categories.some(item => Number(item.parent || 0) === Number(category.id))" type="button" class="cascade-select" :aria-label="`选择分类 ${category.name}`" @click.stop="selectCategory(category.id)">选择</button><button type="button" class="cascade-option" :class="{ active: cascadePath[columnIndex] === category.id, selected: form.additional_categories.map(Number).includes(category.id) }" @click.stop="chooseCascadeCategory(category, columnIndex)"><span>{{ category.name }}</span><ChevronRight v-if="categories.some(item => Number(item.parent || 0) === Number(category.id))" :size="15" /></button></div></div></div></div></div></div><p v-else class="field-help">可为产品添加其他分类，方便查找和统计。</p></div>
        <div class="field full"><label>产品描述</label><textarea v-model="form.description" /></div></div>
      </div><div class="modal-foot"><button type="button" class="btn btn-secondary" :disabled="saving" @click="closeModal">取消</button><button v-if="can('products', editingId ? 'update' : 'create')" class="btn btn-primary" :disabled="saving || !formOptionsReady">{{ saving ? '保存中…' : '保存' }}</button></div></form></div>
    <div v-if="prefixReview" class="modal-backdrop prefix-review-backdrop"><section class="modal prefix-review-modal"><div class="modal-head"><h3>确认销售型号前缀变更</h3><button type="button" class="mini-btn" :disabled="saving" aria-label="关闭前缀预览" @click="prefixReview = null"><X :size="17" /></button></div><div class="modal-body"><p>销售型号前缀将从 <strong>{{ prefixReview.old_prefix || '未设置' }}</strong> 改为 <strong>{{ prefixReview.new_prefix }}</strong>，并同步更新当前 SKU 的销售型号。SKU 编码及历史报价、订单、采购快照不变。</p><div v-if="prefixReview.affected_skus.length" class="prefix-review-list"><div v-for="sku in prefixReview.affected_skus" :key="sku.sku_id"><strong>{{ sku.sku_code }}</strong><span>{{ sku.old_sales_model || '—' }} → {{ sku.new_sales_model || '—' }}</span></div></div><p v-else class="field-help">没有需要更新的 SKU。</p></div><div class="modal-foot"><button type="button" class="btn btn-secondary" :disabled="saving" @click="prefixReview = null">取消</button><button type="button" class="btn btn-primary" :disabled="saving" @click="confirmPrefixChange">{{ saving ? '更新中…' : '确认更新' }}</button></div></section></div>
    <div v-if="message.text" class="toast" :class="{ error: message.error }">{{ message.text }}</div>
    <Transition name="detail-drawer" appear><EntityDetailModal v-if="detailId" entity="products" :id="detailId" :refresh-key="detailRefresh" @close="closeDetail" @edit="editDetail" /></Transition>
  </div>
</template>

<style scoped>
.product-toolbar{display:flex;gap:12px;margin-bottom:14px}.product-toolbar .search-box{flex:1;max-width:430px}.filter-select{position:relative;display:flex;align-items:center;min-width:192px;height:42px;padding:0 11px;gap:8px;border:1px solid #d7e2dd;border-radius:10px;background:#fff;color:#3e655a;box-shadow:0 1px 2px #173d3608;transition:border-color .18s,box-shadow .18s,background .18s}.filter-select:focus-within{border-color:#2c8068;background:#fcfffd;box-shadow:0 0 0 3px #d9eee6}.filter-select>svg:first-child{color:#2f806a}.filter-select>svg:last-child{margin-left:auto;pointer-events:none;color:#6d877e;transition:transform .18s}.filter-select:focus-within>svg:last-child{transform:rotate(180deg)}.filter-select select{appearance:none;min-width:0;flex:1;height:100%;padding:0;border:0;outline:0;background:transparent;color:#193d33;font:600 var(--text-body) inherit;cursor:pointer}.product-modal{width:min(820px,calc(100vw - 64px))}.readonly-input{background:#f1f5f3!important;color:#557068!important;cursor:not-allowed}.hs-code-input{display:flex;gap:8px}.hs-code-input input{min-width:0;flex:1}.hs-query-btn{height:40px;padding:0 11px;display:inline-flex;align-items:center;justify-content:center;gap:5px;border:1px solid #b8d5c9;border-radius:8px;background:#edf7f2;color:#246954;font-size:var(--text-body);font-weight:700;white-space:nowrap;text-decoration:none}.hs-query-btn:hover{border-color:#4c917b;background:#dff0e9;color:#174f3f}.category-field{position:relative}.category-select{width:100%;height:40px;padding:0 11px;display:flex;align-items:center;justify-content:space-between;border:1px solid var(--line);border-radius:8px;background:white;color:var(--ink);font:inherit;font-size:var(--text-body);text-align:left}.category-select:hover{border-color:#8eb6a8}.supplier-select{min-height:104px;padding:6px 8px}.supplier-select option{padding:7px 8px;border-radius:4px}.additional-head{display:flex;align-items:center;justify-content:space-between}.text-add{display:inline-flex;align-items:center;gap:4px;border:0;background:transparent;color:var(--green-2);font-weight:700}.additional-list{display:grid;gap:8px;margin-top:8px}.additional-row{display:flex;gap:8px}.additional-row .mini-btn{flex:none}.field-help{margin:7px 0 0;color:var(--muted);font-size:var(--text-caption)}.category-picker{position:absolute;z-index:12;left:0;top:calc(100% + 5px);width:max-content;min-width:100%;max-width:min(720px,calc(100vw - 80px));border:1px solid #c8ddd5;border-radius:10px;overflow:hidden;background:#fbfdfc;box-shadow:0 12px 26px #173d3624}.additional-row .category-picker{width:max-content;min-width:calc(100% - 40px)}.picker-head{display:flex;justify-content:space-between;align-items:center;padding:11px 13px;background:#edf5f1;border-bottom:1px solid #dceae4}.picker-head strong{font-size:var(--text-body)}.picker-head span{font-size:var(--text-body);color:#69827a}.cascade-columns{display:flex;min-height:210px;max-height:260px;overflow:auto;background:#fff}.cascade-column{width:180px;min-width:160px;padding:6px;overflow-y:auto;border-right:1px solid #e1ebe6}.cascade-column:last-child{border-right:0}.cascade-option{width:100%;min-height:34px;padding:6px 8px;display:flex;align-items:center;justify-content:space-between;gap:8px;border:0;border-radius:6px;background:transparent;color:#29473e;font:inherit;font-size:var(--text-body);text-align:left;cursor:pointer}.cascade-option:hover,.cascade-option.active,.cascade-option.selected{background:#e1f0ea}.cascade-option svg{flex:none;color:#69827a}.table-actions{display:flex;justify-content:flex-end;gap:6px}.mini-btn.danger{color:var(--danger)}
.supplier-picker{border:1px solid #d7e2dd;border-radius:9px;background:#fff;overflow:hidden}.supplier-search{display:flex;align-items:center;gap:8px;padding:0 10px;border-bottom:1px solid #e3ece8;color:#668178}.supplier-search:focus-within{box-shadow:inset 0 0 0 1px #74aa99}.supplier-search input{min-width:0;height:40px;padding:0;border:0;outline:0;box-shadow:none}.supplier-count{margin-left:auto;padding:3px 7px;border-radius:999px;background:#e4f2eb;color:#26715b;font-size:var(--text-body);font-weight:700;white-space:nowrap}.selected-suppliers{display:flex;flex-wrap:wrap;gap:6px;padding:8px 10px;border-bottom:1px solid #e3ece8;background:#f8fbf9}.supplier-chip{display:inline-flex;align-items:center;gap:4px;max-width:100%;padding:4px 6px 4px 8px;border-radius:6px;background:#dff0e9;color:#246954;font-size:var(--text-body);font-weight:700}.supplier-chip button{display:grid;place-items:center;padding:0;border:0;background:transparent;color:#246954;cursor:pointer}.supplier-options{max-height:148px;overflow-y:auto;padding:5px}.supplier-option{display:flex;align-items:center;gap:9px;padding:8px;border-radius:6px;cursor:pointer}.supplier-option:hover,.supplier-option.selected{background:#edf7f2}.supplier-option input{width:15px;height:15px;flex:none;accent-color:#287a64}.supplier-option span{display:grid;gap:2px;min-width:0}.supplier-option strong{font-size:var(--text-body);color:#27473d}.supplier-option small{overflow:hidden;color:#70867e;font-size:var(--text-caption);text-overflow:ellipsis;white-space:nowrap}.supplier-empty{margin:0;padding:18px 10px;color:#70867e;font-size:var(--text-body);text-align:center}
.product-modal{width:min(var(--product-modal-width,820px),calc(100vw - 64px))}.product-modal .form-grid{grid-template-columns:minmax(360px,1fr) minmax(var(--category-picker-width,360px),1fr)}.category-picker,.additional-row .category-picker{width:var(--category-picker-width,100%);min-width:100%;max-width:none}.cascade-columns{overflow:hidden}.cascade-column{min-width:0;flex:0 0 auto}.cascade-option{white-space:nowrap;overflow:hidden}.cascade-option span{overflow:hidden;text-overflow:ellipsis}@media(max-width:1120px){.product-modal{width:calc(100vw - 32px)}.product-modal .form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.category-picker,.additional-row .category-picker{width:min(var(--category-picker-width,100%),calc(100vw - 76px));max-width:calc(100vw - 76px)}.cascade-columns{overflow-x:auto}}@media(max-width:760px){.product-modal .form-grid{grid-template-columns:1fr}}
.prefix-review-backdrop{z-index:140}.prefix-review-modal{width:min(620px,calc(100vw - 32px))}.prefix-review-list{display:grid;gap:8px;margin-top:14px}.prefix-review-list div{display:flex;justify-content:space-between;gap:16px;padding:9px 11px;border:1px solid #d7e5de;border-radius:7px;background:#f8fbf9}.prefix-review-list span{color:#47675b}
.product-toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center}.product-toolbar .search-box{flex:1 1 240px}.product-toolbar>select{max-width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;background:white}.product-list-table{min-width:960px;table-layout:fixed}.product-list-table th:nth-child(1){width:150px}.product-list-table th:nth-child(2){width:250px}.product-list-table th:nth-child(3){width:120px}.product-list-table th:nth-child(4){width:150px}.product-list-table td{white-space:normal;overflow-wrap:anywhere;vertical-align:top}.product-list-table th:last-child,.product-list-table td:last-child{position:sticky;right:0;background:white;width:90px}.product-secondary{display:block;color:#788a82;margin-top:5px;font-size:var(--text-caption)}.product-group-title.full{grid-column:1/-1}.product-group-title{margin:8px 0;color:#285b4b;font-size:var(--text-section)}.product-modal .field{min-width:0}.product-modal .modal-foot{position:sticky;bottom:0;background:white}.supplier-chip{overflow-wrap:anywhere;min-width:0}.product-modal input,.product-modal select,.product-modal textarea{max-width:100%;min-width:0}
.product-list-table th:nth-child(5){width:80px}.product-list-table .tag{white-space:nowrap}
.cascade-entry{display:flex;align-items:stretch;gap:3px}.cascade-entry .cascade-option{flex:1;min-width:0}.cascade-select{min-width:42px;padding:0 6px;border:0;border-radius:6px;background:#f0f7f3;color:#286950;font-size:var(--text-caption);font-weight:700;cursor:pointer}.cascade-select:hover{background:#dcefe7}
</style>
