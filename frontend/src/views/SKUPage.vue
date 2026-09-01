<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Database, Layers3, Pencil, Plus, Search, Trash2, X } from 'lucide-vue-next'
import { api, listData } from '../api'
import ComboInput from '../components/ComboInput.vue'

const props = defineProps({ embedded: Boolean, initialProduct: [Number, String] })
const emit = defineEmits(['close', 'saved'])
const rows = ref([]), products = ref([]), categories = ref([]), parameters = ref([]), packagingTemplates = ref([])
const route = useRoute(), router = useRouter()
const query = ref(''), loading = ref(true), modalOpen = ref(false), saving = ref(false), editingId = ref(null)
const toast = reactive({ text: '', error: false })
const form = reactive({ product: '', unit: 'pcs', cost_price: 0, default_price: 0, currency: 'USD', active: true })
const parameterValues = reactive({})
const salesModelAbbreviations = reactive({})
const abbreviationSuggestions = reactive({})
const details = ref([])
const suppliers = ref([])
const packagingPicker = ref('')
const packagingDialogOpen = ref(false), packagingSaving = ref(false), packagingTarget = ref(null)
const packagingForm = reactive({ name: '', supplier: '', carton_length: '', carton_width: '', carton_height: '', carton_tare_weight: 0, partial_carton_policy: 'SAME_CARTON', mixed_pack_allowed: false, active: true, description: '' })
const imageInput = ref(null), selectedImage = ref(null), imagePreviewUrl = ref(''), savedImageUrl = ref('')
const imageClearRequested = ref(false), pendingImageSkuIds = ref([])

const product = computed(() => products.value.find(item => Number(item.id) === Number(form.product)))
const productById = computed(() => new Map(products.value.map(item => [Number(item.id), item])))
const categoryMap = computed(() => new Map(categories.value.map(item => [item.id, item])))
const activeCategories = computed(() => {
  if (!product.value) return []
  return [product.value.category, ...(product.value.additional_categories || [])].filter(Boolean).map(id => categoryMap.value.get(Number(id))).filter(Boolean)
})
const categoryGroups = computed(() => activeCategories.value.map(category => ({
  ...category,
  attributes: (category.effective_attributes || []).filter(attribute => attribute.include_in_sku || attribute.include_in_sales_model),
})))
const skuAttributes = computed(() => {
  const seen = new Set()
  return categoryGroups.value.flatMap(group => group.attributes.map(attribute => ({ group, attribute }))).filter(({ attribute }) => {
    const key = String(attribute.key || attribute.name).toLowerCase()
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})
const optionsFor = (category, attribute) => {
  const values = new Map()
  const belongsToCategory = sourceProduct => sourceProduct && [sourceProduct.category, ...(sourceProduct.additional_categories || [])].some(id => Number(id) === Number(category.id))
  const addValue = value => {
    const text = String(value || '').trim()
    if (!text) return
    const key = text.toLocaleLowerCase()
    const current = values.get(key)
    const isUppercase = text === text.toLocaleUpperCase()
    const currentIsUppercase = current === current?.toLocaleUpperCase()
    if (!current || (isUppercase && !currentIsUppercase)) values.set(key, text)
  }
  parameters.value.filter(item => item.name === attribute.name && (!item.group || item.group === category.name) && belongsToCategory(productById.value.get(Number(item.product)))).forEach(item => addValue(item.value))
  rows.value.forEach(row => {
    if (!belongsToCategory(productById.value.get(Number(row.product)))) return
    const stored = row.parameter_values || {}
    const raw = stored[`${category.id}:${attribute.key}`] ?? stored[attribute.key] ?? stored[attribute.name]
    splitValues(raw).forEach(addValue)
  })
  addValue(attribute.default_value)
  return [...values.values()].map(value => ({ value, label: value }))
}
const splitValues = value => String(value || '').split(/\r?\n/).map(item => item.trim()).filter(Boolean)
const cartesian = arrays => arrays.reduce((result, items) => result.flatMap(prefix => items.map(item => [...prefix, item])), [[]])
const previewColumns = computed(() => skuAttributes.value.map(({ attribute }) => ({ key: attribute.key, name: attribute.name })))
const abbreviationKey = (group, attribute, value) => `${group.id}:${attribute.key}:${value}`
const abbreviationSuggestionKey = (group, attribute, value) => `${group.id}:${attribute.key}:${String(value || '').trim().toLocaleLowerCase()}`
function applyAbbreviationSuggestions() {
  categoryGroups.value.forEach(group => group.attributes.filter(attribute => attribute.include_in_sales_model).forEach(attribute => {
    splitValues(parameterValues[`${group.id}:${attribute.key}`]).forEach(value => {
      const key = abbreviationKey(group, attribute, value)
      const suggested = abbreviationSuggestions[abbreviationSuggestionKey(group, attribute, value)]
      if (!salesModelAbbreviations[key] && suggested) salesModelAbbreviations[key] = suggested
    })
  }))
}
async function loadAbbreviationSuggestions() {
  Object.keys(abbreviationSuggestions).forEach(key => delete abbreviationSuggestions[key])
  if (!activeCategories.value.length) return
  try {
    const responses = await Promise.all(activeCategories.value.map(category => api.get('/skus/sales-model-abbreviations/', { params: { category: category.id } })))
    responses.forEach(response => Object.assign(abbreviationSuggestions, response.data.abbreviations || {}))
    applyAbbreviationSuggestions()
  } catch (error) { notify(error.message, true) }
}
const previewSalesModel = base => {
  if (!base) return ''
  const used = new Set(rows.value.map(row => row.sales_model).filter(Boolean))
  let sequence = 1
  while (used.has(`${base}-${sequence}`)) sequence += 1
  return `${base}-${sequence}`
}
const allPreviews = computed(() => {
  const parts = skuAttributes.value.map(({ group, attribute }) => ({ group, attribute, values: splitValues(parameterValues[`${group.id}:${attribute.key}`]) }))
  const combinations = cartesian(parts.map(part => part.values.length ? part.values : ['']))
  return combinations.filter(values => values.some(Boolean) || !parts.length).map((values, combinationIndex) => {
    const attributeLabels = parts.map((part, index) => {
      const value = values[index]
      return value ? (part.attribute.uppercase ? value.toUpperCase() : value) : ''
    })
    const labels = attributeLabels.filter((label, index) => label && parts[index].attribute.include_in_sku)
    const parameterSnapshot = Object.fromEntries(parts.map((part, index) => [part.attribute.name, values[index]]).filter(([, value]) => value))
    const parameterValuesForSku = Object.fromEntries(parts.map((part, index) => [`${part.group.id}:${part.attribute.key}`, values[index]]).filter(([, value]) => value))
    const display_name_cn = [product.value?.name, ...labels].filter(Boolean).join(' ')
    const description_cn = [product.value?.name, ...labels].filter(Boolean).join('，')
    const description_en = [product.value?.name_en || product.value?.name, ...labels].filter(Boolean).join(', ')
    const sales_model_suffix = parts.map((part, index) => part.attribute.include_in_sales_model ? String(salesModelAbbreviations[abbreviationKey(part.group, part.attribute, values[index])] || '').trim().toUpperCase() : '').filter(Boolean).join('')
    const sales_model_base = sales_model_suffix ? [product.value?.sales_model_prefix, sales_model_suffix].filter(Boolean).join('-') : ''
    const sales_model = previewSalesModel(sales_model_base)
    const key = values.map(value => String(value || '')).join('|') || String(combinationIndex)
    return { key, display_name_cn, description_cn, description_en, specification: labels.join(' / '), parameterSnapshot, parameterValuesForSku, sales_model, attributeValues: Object.fromEntries(parts.map((part, index) => [part.attribute.key, attributeLabels[index] || ''])) }
  })
})
function newDetail(name = product.value?.name || '', key = '') { return { preview_key: key, product_name: name, unit: form.unit || 'pcs', notes: '', unit_weight: 0, carton_quantity: 0, packaging_template: '', packaging_query: '' } }
function detailFor(preview) { return details.value.find(detail => detail.preview_key === preview.key) || newDetail(product.value?.name || '', preview.key) }
function syncDetails(previews) {
  const saved = new Map(details.value.map(detail => [detail.preview_key, detail]))
  const existingSingle = previews.length === 1 && details.value.length === 1 ? details.value[0] : null
  details.value = previews.map(preview => saved.get(preview.key) || (existingSingle ? { ...existingSingle, preview_key: preview.key } : newDetail(product.value?.name || '', preview.key)))
}

function notify(text, error = false) { Object.assign(toast, { text, error }); setTimeout(() => { toast.text = '' }, 2600) }
function revokeImagePreview() {
  if (imagePreviewUrl.value.startsWith('blob:')) URL.revokeObjectURL(imagePreviewUrl.value)
}
function resetImagePicker(imageUrl = '') {
  revokeImagePreview()
  selectedImage.value = null
  imagePreviewUrl.value = imageUrl
  if (imageInput.value) imageInput.value.value = ''
}
function chooseImage() { imageInput.value?.click() }
function onImageSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!['image/gif', 'image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    event.target.value = ''
    return notify('仅支持 GIF、JPEG、PNG 或 WebP 图片。', true)
  }
  revokeImagePreview()
  imageClearRequested.value = false
  selectedImage.value = file
  imagePreviewUrl.value = URL.createObjectURL(file)
}
function clearImageSelection() {
  imageClearRequested.value = Boolean(savedImageUrl.value)
  resetImagePicker()
}
async function uploadImage(skuId, file) {
  const data = new FormData()
  data.append('image', file)
  return api.post(`/skus/${skuId}/image/`, data)
}
async function clearImage(skuId) { return api.delete(`/skus/${skuId}/image/`) }
async function load() {
  loading.value = true
  try { rows.value = listData(await api.get('/skus/', { params: { search: query.value } })) } catch (error) { notify(error.message, true) } finally { loading.value = false }
}
async function openCreate(productId = '') {
  editingId.value = null
  savedImageUrl.value = ''
  imageClearRequested.value = false
  pendingImageSkuIds.value = []
  resetImagePicker()
  Object.assign(form, { product: productId ? Number(productId) : '', unit: 'pcs', cost_price: 0, default_price: 0, currency: 'USD', active: true })
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  Object.keys(salesModelAbbreviations).forEach(key => delete salesModelAbbreviations[key])
  details.value = []
  modalOpen.value = true
}
function openCreateFromRoute() {
  if (route.query.create !== '1' || modalOpen.value) return
  openCreate(route.query.product)
}
function closeModal() {
  modalOpen.value = false
  resetImagePicker()
  if (props.embedded) return emit('close')
  if (route.query.create !== '1') return
  const { create, product: productId, ...remaining } = route.query
  router.replace({ query: remaining })
}
function openEdit(row) {
  editingId.value = row.id
  savedImageUrl.value = row.image || ''
  imageClearRequested.value = false
  pendingImageSkuIds.value = []
  resetImagePicker(savedImageUrl.value)
  Object.assign(form, { product: row.product, unit: row.unit, cost_price: row.cost_price, default_price: row.default_price, currency: row.currency, active: row.active })
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  Object.keys(salesModelAbbreviations).forEach(key => delete salesModelAbbreviations[key])
  Object.entries(row.parameter_values || {}).forEach(([key, value]) => { parameterValues[key] = value })
  Object.entries(row.sales_model_abbreviations || {}).forEach(([key, value]) => { salesModelAbbreviations[key] = value })
  details.value = [{ ...(row.product_details?.[0] || newDetail(row.product_name)), preview_key: '', packaging_template: row.packaging?.template || '', packaging_query: row.packaging?.template_name || '', carton_quantity: row.packaging?.effective_qty_per_carton || row.product_details?.[0]?.carton_quantity || 0 }]
  modalOpen.value = true
}
function onProductChanged() {
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  Object.keys(salesModelAbbreviations).forEach(key => delete salesModelAbbreviations[key])
  details.value = []
  void loadAbbreviationSuggestions()
}
function packagingText(template) { return [template.code, template.name, template.supplier_name, template.description, template.carton_length, template.carton_width, template.carton_height].filter(Boolean).join(' · ') }
function matchingPackaging(detail) { const search = String(detail.packaging_query || '').trim().toLocaleLowerCase(); return packagingTemplates.value.filter(template => !search || packagingText(template).toLocaleLowerCase().includes(search)).slice(0, 8) }
function choosePackaging(detail, template) { detail.packaging_template = template.id; detail.packaging_query = packagingText(template); packagingPicker.value = '' }
function clearPackaging(detail) { detail.packaging_template = ''; detail.packaging_query = ''; packagingPicker.value = '' }
function cleanDetail(detail) { const { preview_key, packaging_template, packaging_query, ...stored } = detail; return stored }
function resetPackagingForm() { Object.assign(packagingForm, { name: '', supplier: '', carton_length: '', carton_width: '', carton_height: '', carton_tare_weight: 0, partial_carton_policy: 'SAME_CARTON', mixed_pack_allowed: false, active: true, description: '' }) }
function closePackagingPickerOnOutsideClick(event) { if (!event.target.closest?.('.packaging-picker')) packagingPicker.value = '' }
async function createPackaging() {
  packagingSaving.value = true
  try {
    const template = (await api.post('/packaging-templates/', { ...packagingForm, supplier: packagingForm.supplier || null })).data
    packagingTemplates.value.push(template)
    if (packagingTarget.value) choosePackaging(packagingTarget.value, template)
    packagingDialogOpen.value = false
    packagingTarget.value = null
    resetPackagingForm()
  } catch (error) { notify(error.message, true) } finally { packagingSaving.value = false }
}
async function savePackaging(skuId, detail) {
  if (!detail.packaging_template) return
  if (!detail.carton_quantity || Number(detail.carton_quantity) <= 0) throw new Error(`销售型号 ${detail.sales_model || ''} 已选择包装信息，请填写大于 0 的整件数量。`)
  await api.put(`/skus/${skuId}/packaging/`, { packaging_template: Number(detail.packaging_template), qty_per_carton_override: Number(detail.carton_quantity), unit_net_weight: Number(detail.unit_weight || 0) })
}
async function save() {
  if (pendingImageSkuIds.value.length) {
    if (!selectedImage.value) return notify('请选择图片后重试上传，或取消本次编辑。', true)
    saving.value = true
    try {
      await Promise.all(pendingImageSkuIds.value.map(skuId => uploadImage(skuId, selectedImage.value)))
      pendingImageSkuIds.value = []
      closeModal(); emit('saved'); notify('SKU 图片已上传'); await load()
    } catch (error) { notify(`SKU 已创建，但图片上传失败：${error.message}`, true) } finally { saving.value = false }
    return
  }
  if (!form.product) return notify('请选择所属产品。', true)
  if (!allPreviews.value.length) return notify('请至少填写一个参与 SKU 或参与生成型号的参数值。', true)
  saving.value = true
  try {
    const shared = { product: Number(form.product), unit: form.unit, cost_price: Number(form.cost_price || 0), default_price: Number(form.default_price || 0), currency: form.currency, active: form.active, sales_model_abbreviations: salesModelAbbreviations }
    if (editingId.value) {
      const preview = allPreviews.value[0]
      const detail = detailFor(preview)
      await api.put(`/skus/${editingId.value}/`, { ...shared, specification: preview.specification, product_details: [cleanDetail(detail)], parameter_values: preview.parameterValuesForSku })
      await savePackaging(editingId.value, detail)
      if (imageClearRequested.value) await clearImage(editingId.value)
      else if (selectedImage.value) await uploadImage(editingId.value, selectedImage.value)
    } else {
      const createdRows = []
      for (const preview of allPreviews.value) {
        const detail = detailFor(preview)
        const row = (await api.post('/skus/', { ...shared, specification: preview.specification, product_details: [cleanDetail(detail)], parameter_values: preview.parameterValuesForSku })).data
        createdRows.push({ row, detail })
      }
      await Promise.all(createdRows.map(({ row, detail }) => savePackaging(row.id, detail)))
      if (selectedImage.value) {
        try { await Promise.all(createdRows.map(({ row }) => uploadImage(row.id, selectedImage.value))) }
        catch (error) {
          pendingImageSkuIds.value = createdRows.map(({ row }) => row.id)
          editingId.value = createdRows[0]?.row.id || null
          await load()
          return notify(`SKU 已创建，但图片上传失败：${error.message}`, true)
        }
      }
    }
    closeModal(); emit('saved'); notify(editingId.value ? 'SKU 已更新' : `已创建 ${allPreviews.value.length} 个 SKU`); await load()
  } catch (error) { notify(error.message, true) } finally { saving.value = false }
}
async function removeRow(row) { if (!confirm(`确定删除 SKU “${row.display_name_cn || row.sku_code || row.sku}”吗？`)) return; try { await api.delete(`/skus/${row.id}/`); await load(); notify('SKU 已删除') } catch (error) { notify(error.message, true) } }
watch(() => form.unit, value => details.value.forEach(detail => { detail.unit = value || 'pcs' }))
watch(() => form.product, () => { void loadAbbreviationSuggestions() })
watch(parameterValues, applyAbbreviationSuggestions, { deep: true })
watch(allPreviews, syncDetails, { immediate: true })
onMounted(async () => {
  document.addEventListener('pointerdown', closePackagingPickerOnOutsideClick)
  await Promise.all([
    load(),
    api.get('/products/').then(response => { products.value = listData(response) }),
    api.get('/categories/tree/').then(response => { categories.value = listData(response) }),
    api.get('/product-parameters/').then(response => { parameters.value = listData(response) }),
    api.get('/packaging-templates/').then(response => { packagingTemplates.value = listData(response).filter(item => item.active) }),
    api.get('/suppliers/').then(response => { suppliers.value = listData(response) }),
  ])
  if (props.embedded) openCreate(props.initialProduct)
  else openCreateFromRoute()
})
watch(() => route.query.create, () => { if (!props.embedded) openCreateFromRoute() })
onBeforeUnmount(() => { document.removeEventListener('pointerdown', closePackagingPickerOnOutsideClick); revokeImagePreview() })
</script>

<template>
  <div>
    <div class="page-head"><div><h2>SKU 管理</h2><p>按产品分类配置参数，实时生成可报价、可下单的 SKU 组合。</p></div><button class="btn btn-primary" @click="openCreate"><Plus :size="16" /> 新建 SKU</button></div>
    <div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索中文名称、销售型号、SKU 编号或规格..." @input="load" /></div></div>
    <section class="panel"><div v-if="loading" class="loading"><div class="spinner" /></div><div v-else-if="!rows.length" class="empty"><Database :size="32" /><h3>还没有 SKU</h3><p>点击“新建 SKU”开始配置产品规格。</p></div><div v-else class="table-wrap"><table class="data-table"><thead><tr><th>内部识别名称</th><th>对外型号</th><th>SKU Code</th><th>图片</th><th>库存</th><th>单位</th><th>默认售价</th><th /></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td class="primary-cell"><strong>{{ row.display_name_cn || row.product_name }}</strong><small>{{ row.specification || '—' }}</small></td><td><span v-if="row.sales_model">{{ row.sales_model }}</span><span v-else class="muted">未设置</span></td><td>{{ row.sku_code || row.sku }}</td><td><img v-if="row.image" class="sku-table-thumbnail" :src="row.image" :alt="`${row.display_name_cn || row.sku} 图片`" /><span v-else class="sku-image-empty">—</span></td><td>{{ row.stock_quantity }}</td><td>{{ row.unit }}</td><td>{{ row.default_price }} {{ row.currency }}</td><td><div class="table-actions"><button class="mini-btn" title="编辑" @click="openEdit(row)"><Pencil :size="14" /></button><button class="mini-btn danger" title="删除" @click="removeRow(row)"><Trash2 :size="14" /></button></div></td></tr></tbody></table></div></section>

    <Teleport to="body" :disabled="!embedded"><div v-if="modalOpen || route.query.create === '1'" class="modal-backdrop" @mousedown.self="closeModal"><form class="modal sku-modal" @submit.prevent="save"><div class="modal-head"><div><h3>{{ editingId ? '编辑 SKU' : '新建 SKU' }}</h3><p>参数按产品所属分类自动带入；每个值输入后按回车确认。</p></div><button type="button" class="mini-btn" @click="closeModal"><X :size="17" /></button></div><div class="modal-body sku-body">
      <section class="sku-basics"><div class="field"><label>所属产品 <em>*</em></label><select v-model="form.product" required @change="onProductChanged"><option value="">请选择产品</option><option v-for="item in products" :key="item.id" :value="item.id">{{ item.name }}</option></select></div><div class="field"><label>销售型号前缀</label><input :value="product?.sales_model_prefix || ''" placeholder="请先在产品中设置" readonly /><small class="field-help">取自产品主档，将与参数缩写和序号组成销售型号。</small></div><div class="field"><label>单位</label><input v-model.trim="form.unit" placeholder="如：pcs" /></div><div class="field"><label>成本价</label><input v-model.number="form.cost_price" type="number" min="0" step="0.0001" /></div><div class="field"><label>默认售价</label><input v-model.number="form.default_price" type="number" min="0" step="0.0001" /></div><div class="field"><label>币种</label><select v-model="form.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div><label class="check-field"><input v-model="form.active" type="checkbox" /> 启用</label><div class="sku-image-picker"><input ref="imageInput" type="file" accept="image/gif,image/jpeg,image/png,image/webp,.gif,.jpg,.jpeg,.png,.webp" hidden @change="onImageSelected" /><img v-if="imagePreviewUrl" class="sku-image-preview" :src="imagePreviewUrl" alt="SKU 图片预览" /><div v-else class="sku-image-placeholder">暂无图片</div><div class="sku-image-actions"><button type="button" class="btn btn-secondary" @click="chooseImage">选择图片</button><button v-if="selectedImage || imagePreviewUrl" type="button" class="btn btn-secondary" @click="clearImageSelection">清除</button></div></div></section>
      <section v-if="product" class="parameter-section"><div class="section-title"><div><small>参数资料</small><h4>按分类填写 SKU 参数</h4></div><span>{{ categoryGroups.length }} 个分类</span></div><p v-if="skuAttributes.length" class="rule-hint">展示参与 SKU 编码或参与生成型号的属性；大写规则将自动应用。</p><div v-if="!skuAttributes.length" class="section-empty">该产品的分类尚未配置 SKU 参数或销售型号参数，请先在产品分类中配置。</div><div v-for="group in categoryGroups" :key="group.id" class="parameter-group"><h5>{{ group.name }}</h5><div v-if="group.attributes.length" class="parameter-grid"><div v-for="attribute in group.attributes" :key="attribute.key" class="parameter-cell"><label>{{ attribute.name }}<small v-if="attribute.unit">（{{ attribute.unit }}）</small></label><ComboInput v-model="parameterValues[`${group.id}:${attribute.key}`]" :options="optionsFor(group, attribute)" :placeholder="`输入${attribute.name}后按回车确认`" multiple /><div v-if="attribute.include_in_sales_model && splitValues(parameterValues[`${group.id}:${attribute.key}`]).length" class="abbreviation-list"><div class="abbreviation-heading"><span>型号缩写</span><details class="abbreviation-help"><summary title="缩写填写说明">?</summary><p>为每个参数值填写 2–3 位字母或数字缩写。示例：10MM → 10；分控 → 2P；6000K → CW 或 6K；黑色 → BL；俄文 → RU。缩写会按参数顺序直接拼接到产品销售型号后。</p></details></div><label v-for="value in splitValues(parameterValues[`${group.id}:${attribute.key}`])" :key="value" class="abbreviation-input"><span>{{ value }}</span><input v-model.trim="salesModelAbbreviations[abbreviationKey(group, attribute, value)]" maxlength="3" pattern="[A-Za-z0-9]{2,3}" placeholder="如 BL" @input="salesModelAbbreviations[abbreviationKey(group, attribute, value)] = String(salesModelAbbreviations[abbreviationKey(group, attribute, value)] || '').replace(/[^a-zA-Z0-9]/g, '').toUpperCase()" /></label></div><p>按回车添加多个值</p></div></div><p v-else class="muted">本分类暂无 SKU 参数或销售型号参数。</p></div></section>
      <section v-if="product" class="preview-section"><div class="section-title"><div><h4>SKU 组合预览</h4><p class="preview-hint">每一行将自动生成一个 SKU；销售型号由产品前缀、参数缩写和序号组成。</p></div><span>{{ allPreviews.length }} 个组合</span></div><div v-if="!allPreviews.length" class="section-empty">填写参与 SKU 或参与生成型号的参数后将在这里预览。</div><div v-else class="preview-table-wrap"><table class="preview-table"><thead><tr><th>Sales Model</th><th v-for="column in previewColumns" :key="column.key">{{ column.name }}</th></tr></thead><tbody><tr v-for="item in allPreviews" :key="item.key"><td>{{ item.sales_model || '—' }}</td><td v-for="column in previewColumns" :key="column.key">{{ item.attributeValues[column.key] || '—' }}</td></tr></tbody></table></div></section>
      <section v-if="product" class="detail-section"><div class="section-title"><div><small>产品明细</small><h4>包装与发货信息</h4></div><span>{{ allPreviews.length }} 个销售型号</span></div><div class="detail-scroll"><div v-for="(preview, index) in allPreviews" :key="preview.key" class="detail-row"><div class="detail-index">{{ index + 1 }}</div><label>产品名称<input v-model.trim="detailFor(preview).product_name" /></label><label>销售型号<input :value="preview.sales_model" readonly /></label><label>单位<input v-model.trim="detailFor(preview).unit" /></label><label>备注<input v-model.trim="detailFor(preview).notes" /></label><label>单个重量 KG<input v-model.number="detailFor(preview).unit_weight" type="number" min="0" step="0.001" /></label><label>整件数量<input v-model.number="detailFor(preview).carton_quantity" type="number" min="0" /></label><div class="packaging-cell"><label>包装信息</label><div class="packaging-picker"><input v-model.trim="detailFor(preview).packaging_query" placeholder="未配置，输入任意文字搜索" @focus="packagingPicker = preview.key" @input="detailFor(preview).packaging_template = ''" /><div v-if="packagingPicker === preview.key" class="packaging-options"><button v-if="detailFor(preview).packaging_template || detailFor(preview).packaging_query" type="button" @click="clearPackaging(detailFor(preview))">清除选择</button><button v-for="template in matchingPackaging(detailFor(preview))" :key="template.id" type="button" @click="choosePackaging(detailFor(preview), template)">{{ packagingText(template) }}</button><button type="button" class="create-packaging" @click="resetPackagingForm(); packagingTarget = detailFor(preview); packagingDialogOpen = true">＋ 新建包装</button></div></div></div></div></div></section>
    </div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="closeModal">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : pendingImageSkuIds.length ? '重试上传图片' : editingId ? '保存 SKU' : `创建 ${allPreviews.length || ''} 个 SKU` }}</button></div></form></div></Teleport>
    <div v-if="packagingDialogOpen" class="modal-backdrop packaging-dialog-backdrop" @mousedown.self="packagingDialogOpen=false"><form class="modal inline-packaging-modal" @submit.prevent="createPackaging"><div class="modal-head"><div><h3>新建包装</h3><p>保存或取消后将返回当前 SKU 页面，已填写的数据会保留。</p></div><button type="button" class="mini-btn" @click="packagingDialogOpen=false"><X :size="17" /></button></div><div class="modal-body"><div class="inline-packaging-grid"><label>包装名称 <em>*</em><input v-model.trim="packagingForm.name" required /></label><label>包装供应商<select v-model="packagingForm.supplier"><option value="">未指定</option><option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">{{ supplier.name }}</option></select></label><label>长 (cm) <em>*</em><input v-model.number="packagingForm.carton_length" type="number" min="0.01" step="0.01" required /></label><label>宽 (cm) <em>*</em><input v-model.number="packagingForm.carton_width" type="number" min="0.01" step="0.01" required /></label><label>高 (cm) <em>*</em><input v-model.number="packagingForm.carton_height" type="number" min="0.01" step="0.01" required /></label><label>外箱皮重 (kg)<input v-model.number="packagingForm.carton_tare_weight" type="number" min="0" step="0.001" required /></label><label class="full">备注<textarea v-model.trim="packagingForm.description" /></label></div></div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="packagingDialogOpen=false">取消</button><button class="btn btn-primary" :disabled="packagingSaving">{{ packagingSaving ? '保存中...' : '保存并引用' }}</button></div></form></div>
    <div v-if="toast.text" class="toast" :class="{ error: toast.error }">{{ toast.text }}</div>
  </div>
</template>

<style scoped>
.sku-modal{width:min(1475px,calc(100vw - 16px));max-height:calc(100vh - 44px)}.embedded-backdrop{position:absolute;inset:0;z-index:50;padding:0;background:#0b221d66}.embedded-modal{width:100%;max-width:100%;height:100%;max-height:100%;border-radius:0}.modal-head>div p{margin:4px 0 0;color:var(--muted);font-size:12px}.sku-body{display:grid;gap:18px;max-height:calc(100vh - 185px);overflow:auto}.embedded-modal .sku-body{max-height:calc(100% - 145px)}.sku-basics{display:grid;grid-template-columns:minmax(220px,2.2fr) repeat(4,minmax(88px,.72fr)) auto;gap:10px;align-items:end;padding:14px;border:1px solid #dfe9e4;border-radius:11px;background:#fbfdfc}.sku-basics .field:not(:first-child) input,.sku-basics .field:not(:first-child) select{min-width:0}.check-field{height:40px;display:flex;align-items:center;gap:7px;font-size:13px;color:#36594e;white-space:nowrap}.section-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.section-title small{color:#678278;font-size:11px;font-weight:700}.section-title h4{margin:3px 0 0;font-size:15px}.section-title>span{padding:4px 9px;border-radius:99px;background:#e7f2ed;color:#37715f;font-size:11px;font-weight:700}.parameter-section,.preview-section,.detail-section{padding:16px;border:1px solid #dbe7e1;border-radius:12px;background:#fff}.parameter-group{margin-top:14px}.parameter-group h5,.preview-group h5{margin:0 0 9px;color:#365a4d;font-size:13px}.parameter-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.parameter-cell label,.detail-row label{display:block;color:#596b65;font-size:12px;font-weight:600}.parameter-cell label small{color:#889790;font-weight:400}.parameter-cell p{margin:5px 0 0;color:#9aa6a1;font-size:10px}.rule-hint{margin:8px 0 0;color:#678278;font-size:11px}.section-empty{margin-top:13px;padding:16px;border:1px dashed #cbdad4;border-radius:8px;background:#f8fbf9;color:#789087;text-align:center;font-size:12px}.muted{color:var(--muted);font-size:12px}.preview-section{background:#f7faf8}.preview-groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin-top:14px}.preview-group{border:1px solid #d5e4dd;border-radius:9px;background:#fff;overflow:hidden}.preview-group h5{display:flex;justify-content:space-between;padding:10px 11px;margin:0;background:#edf5f1}.preview-group h5 b{font-size:11px;color:#578074}.preview-list{max-height:156px;overflow:auto}.preview-card{padding:9px 11px;border-top:1px solid #eef2f0}.preview-card strong,.preview-card span{display:block}.preview-card strong{color:#193d33;font-size:13px}.preview-card span{margin-top:3px;color:#778882;font-size:11px}.detail-section .btn{padding:8px 11px}.detail-scroll{margin-top:13px;overflow-x:auto}.detail-row{width:100%;min-width:940px;display:grid;grid-template-columns:25px minmax(145px,1.45fr) minmax(96px,.9fr) minmax(66px,.6fr) minmax(118px,1.15fr) repeat(5,minmax(82px,.78fr)) 30px;gap:8px;align-items:end;padding:10px 0;border-top:1px solid #edf1ef}.detail-index{padding-bottom:11px;color:#7c8d86;font-size:12px;font-weight:700}.detail-row input{width:100%;min-width:0;margin-top:5px;border:1px solid #dce4df;border-radius:7px;padding:8px 9px;color:var(--ink);outline:0}.detail-row input:focus{border-color:#72a897;box-shadow:0 0 0 3px #e2efeb}.detail-row .mini-btn{margin-bottom:1px}.table-actions{display:flex;justify-content:flex-end;gap:6px}.mini-btn.danger{color:var(--danger)}@media(max-width:850px){.sku-modal{width:100%;height:100%;max-height:100vh;border-radius:0}.sku-basics{grid-template-columns:repeat(2,minmax(0,1fr))}.parameter-grid{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}}@media(max-width:520px){.sku-basics,.parameter-grid{grid-template-columns:1fr}.sku-body{max-height:calc(100vh - 165px)}}
.sku-image-picker{grid-column:1/-1;display:flex;align-items:center;gap:11px;padding-top:4px}.sku-image-preview,.sku-image-placeholder{width:64px;height:64px;border:1px solid #d6e2dc;border-radius:8px;background:#fff;object-fit:cover}.sku-image-placeholder{display:grid;place-items:center;color:#93a29c;font-size:11px}.sku-image-actions{display:flex;gap:7px}.sku-image-actions .btn{padding:8px 10px;font-size:12px}
.preview-hint{margin:5px 0 0;color:#678278;font-size:11px;font-weight:400}.preview-table-wrap{max-height:180px;margin-top:13px;overflow:auto;border:1px solid #d5e4dd;border-radius:9px;background:#fff}.preview-table{width:100%;border-collapse:collapse;font-size:12px}.preview-table th,.preview-table td{padding:9px 11px;border-bottom:1px solid #e8f0ec;text-align:left;white-space:nowrap}.preview-table th{position:sticky;top:0;background:#edf5f1;color:#365a4d;font-weight:700}.preview-table tr:last-child td{border-bottom:0}
.abbreviation-list{display:grid;gap:6px;margin-top:9px;padding:8px;border:1px solid #d7e7e0;border-radius:7px;background:#f7fbf9}.abbreviation-heading{display:flex;align-items:center;justify-content:space-between;color:#55766b;font-size:11px;font-weight:700}.abbreviation-help{position:relative}.abbreviation-help summary{display:grid;width:18px;height:18px;place-items:center;border:1px solid #8db6a8;border-radius:50%;color:#2a7560;cursor:help;list-style:none}.abbreviation-help summary::-webkit-details-marker{display:none}.abbreviation-help p{position:absolute;z-index:5;right:0;width:260px;margin:6px 0 0;padding:9px 10px;border:1px solid #c8ddd5;border-radius:7px;background:#fff;color:#48645b;font-size:11px;font-weight:400;line-height:1.5;box-shadow:0 7px 18px #173d3620}.abbreviation-input{display:grid;grid-template-columns:minmax(0,1fr) 76px;align-items:center;gap:8px;color:#526b62;font-size:11px}.abbreviation-input span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.abbreviation-input input{width:100%;min-width:0;border:1px solid #cdded7;border-radius:6px;padding:6px 8px;background:#fff;color:#214c40;font:700 12px/1 inherit;text-transform:uppercase}.abbreviation-input input:focus{outline:0;border-color:#62a28d;box-shadow:0 0 0 2px #dcefe7}
.sku-basics{align-items:start}.sku-basics .field input[readonly]{background:#f1f5f3;color:#557068;cursor:not-allowed}
.sku-packaging-section{padding:16px;border:1px solid #cfe1d8;border-radius:12px;background:#f8fbf9}.sku-packaging-section>p{margin:7px 0 13px;color:#678278;font-size:12px}.sku-packaging-fields{display:grid;grid-template-columns:minmax(260px,1.8fr) minmax(160px,.7fr);gap:12px}.sku-packaging-fields .field label{display:block;margin-bottom:5px;color:#596b65;font-size:12px;font-weight:600}.sku-packaging-fields select,.sku-packaging-fields input{width:100%;height:38px;border:1px solid #cdded7;border-radius:7px;padding:0 10px;background:#fff}.sku-packaging-fields input:disabled{background:#f0f4f2;color:#9aa6a1}@media(max-width:520px){.sku-packaging-fields{grid-template-columns:1fr}}
.detail-row{min-width:1120px;grid-template-columns:25px minmax(130px,1.3fr) minmax(130px,1.2fr) minmax(64px,.6fr) minmax(115px,1fr) minmax(92px,.8fr) minmax(92px,.8fr) minmax(250px,2.2fr)}.detail-row input[readonly]{background:#f1f5f3;color:#49675d}.packaging-cell{position:relative}.packaging-cell>label{display:block;color:#596b65;font-size:12px;font-weight:600}.packaging-picker input{margin-top:5px}.packaging-options{position:absolute;z-index:12;right:0;top:100%;width:min(430px,34vw);max-height:215px;overflow:auto;padding:5px;border:1px solid #c9ddd5;border-radius:8px;background:#fff;box-shadow:0 10px 24px #173d3622}.packaging-options button{display:block;width:100%;padding:8px 9px;border:0;border-radius:5px;background:transparent;color:#35564b;font-size:12px;text-align:left;cursor:pointer}.packaging-options button:hover{background:#edf5f1}.packaging-options .create-packaging{border-top:1px solid #dbe8e2;color:#197256;font-weight:700}.packaging-dialog-backdrop{z-index:80}.inline-packaging-modal{width:min(680px,calc(100vw - 28px))}.inline-packaging-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.inline-packaging-grid label{display:flex;flex-direction:column;gap:6px;color:#41574e;font-size:12px;font-weight:650}.inline-packaging-grid em{color:var(--danger);font-style:normal}.inline-packaging-grid input,.inline-packaging-grid select,.inline-packaging-grid textarea{border:1px solid #cdded7;border-radius:7px;padding:8px 9px;background:#fff}.inline-packaging-grid textarea{min-height:70px;resize:vertical}.inline-packaging-grid .full{grid-column:1/-1}@media(max-width:680px){.inline-packaging-grid{grid-template-columns:1fr}}
</style>
