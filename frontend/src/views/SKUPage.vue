<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Database, Layers3, Pencil, Plus, Search, Trash2, X } from 'lucide-vue-next'
import { api, listData } from '../api'
import ComboInput from '../components/ComboInput.vue'

const props = defineProps({ embedded: Boolean, initialProduct: [Number, String] })
const emit = defineEmits(['close', 'saved'])
const rows = ref([]), products = ref([]), categories = ref([]), parameters = ref([])
const route = useRoute(), router = useRouter()
const query = ref(''), loading = ref(true), modalOpen = ref(false), saving = ref(false), editingId = ref(null)
const toast = reactive({ text: '', error: false })
const form = reactive({ product: '', sales_model: '', unit: 'pcs', cost_price: 0, default_price: 0, currency: 'USD', active: true })
const parameterValues = reactive({})
const details = ref([])
const imageInput = ref(null), selectedImage = ref(null), imagePreviewUrl = ref(''), savedImageUrl = ref('')
const imageClearRequested = ref(false), pendingImageSkuIds = ref([])

const product = computed(() => products.value.find(item => Number(item.id) === Number(form.product)))
const categoryMap = computed(() => new Map(categories.value.map(item => [item.id, item])))
const activeCategories = computed(() => {
  if (!product.value) return []
  return [product.value.category, ...(product.value.additional_categories || [])].filter(Boolean).map(id => categoryMap.value.get(Number(id))).filter(Boolean)
})
const categoryGroups = computed(() => activeCategories.value.map(category => ({
  ...category,
  attributes: (category.effective_attributes || []).filter(attribute => attribute.include_in_sku),
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
  const values = new Set()
  parameters.value.filter(item => item.name === attribute.name && (!item.group || item.group === category.name)).forEach(item => values.add(item.value))
  if (attribute.default_value) values.add(attribute.default_value)
  return [...values].map(value => ({ value, label: value }))
}
const splitValues = value => String(value || '').split(/\r?\n/).map(item => item.trim()).filter(Boolean)
const cartesian = arrays => arrays.reduce((result, items) => result.flatMap(prefix => items.map(item => [...prefix, item])), [[]])
const allPreviews = computed(() => {
  const parts = skuAttributes.value.map(({ group, attribute }) => ({ attribute, values: splitValues(parameterValues[`${group.id}:${attribute.key}`]) }))
  const combinations = cartesian(parts.map(part => part.values.length ? part.values : ['']))
  // 销售型号不再由参数拼接；参数只用于内部名称和 Description 预览。
  const modelDetails = details.value.map((detail, detailIndex) => ({ ...detail, detailIndex, model: String(detail.model || '').trim().toUpperCase() }))
  return modelDetails.flatMap(detail => combinations.filter(values => values.some(Boolean) || detail.model || !parts.length).map((values, combinationIndex) => {
    const labels = parts.map((part, index) => {
      const value = values[index]
      return value ? (part.attribute.uppercase ? value.toUpperCase() : value) : ''
    }).filter(Boolean)
    const parameterSnapshot = Object.fromEntries(parts.map((part, index) => [part.attribute.name, values[index]]).filter(([, value]) => value))
    const display_name_cn = [product.value?.name, detail.model, ...labels].filter(Boolean).join(' ')
    const description_cn = [product.value?.name, detail.model, ...labels].filter(Boolean).join('，')
    const description_en = [product.value?.name_en || product.value?.name, detail.model, ...labels].filter(Boolean).join(', ')
    return { key: `${detail.detailIndex}-${combinationIndex}`, display_name_cn, description_cn, description_en, specification: [detail.model, ...labels].filter(Boolean).join(' / '), parameterSnapshot, detail }
  }))
})

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
function newDetail(name = product.value?.name || '') { return { product_name: name, model: '', unit: form.unit || 'pcs', notes: '', unit_weight: 0, length: 0, width: 0, height: 0, carton_quantity: 0, carton_weight: 0, cbm: 0, volume_weight: 0 } }
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
  Object.assign(form, { product: productId ? Number(productId) : '', sales_model: '', unit: 'pcs', cost_price: 0, default_price: 0, currency: 'USD', active: true })
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  details.value = [newDetail(product.value?.name || '')]
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
  Object.assign(form, { product: row.product, sales_model: row.sales_model || '', unit: row.unit, cost_price: row.cost_price, default_price: row.default_price, currency: row.currency, active: row.active })
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  Object.entries(row.parameter_values || {}).forEach(([key, value]) => { parameterValues[key] = value })
  details.value = row.product_details?.length ? row.product_details : [newDetail(row.product_name)]
  modalOpen.value = true
}
function onProductChanged() {
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  details.value = [newDetail()]
}
function addDetail() { details.value.push(newDetail(product.value?.name || details.value.at(-1)?.product_name || '')) }
function removeDetail(index) { if (details.value.length > 1) details.value.splice(index, 1) }
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
  if (!allPreviews.value.length) return notify('请至少填写型号或一个参与 SKU 的参数值。', true)
  saving.value = true
  try {
    const shared = { product: Number(form.product), sales_model: String(form.sales_model || '').trim() || null, unit: form.unit, cost_price: Number(form.cost_price || 0), default_price: Number(form.default_price || 0), currency: form.currency, active: form.active }
    if (editingId.value) {
      const preview = allPreviews.value[0]
      await api.put(`/skus/${editingId.value}/`, { ...shared, specification: preview.specification, product_details: [preview.detail], parameter_values: parameterValues })
      if (imageClearRequested.value) await clearImage(editingId.value)
      else if (selectedImage.value) await uploadImage(editingId.value, selectedImage.value)
    } else {
      const createdRows = await Promise.all(allPreviews.value.map(async ({ detail, specification }) => (await api.post('/skus/', { ...shared, sales_model: allPreviews.value.length === 1 ? shared.sales_model : null, specification, product_details: [detail], parameter_values: parameterValues })).data))
      if (selectedImage.value) {
        try { await Promise.all(createdRows.map(row => uploadImage(row.id, selectedImage.value))) }
        catch (error) {
          pendingImageSkuIds.value = createdRows.map(row => row.id)
          editingId.value = createdRows[0]?.id || null
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
watch(details, value => value.forEach(detail => {
  if (detail.model) detail.model = String(detail.model).toUpperCase()
}), { deep: true })
onMounted(async () => {
  await Promise.all([
    load(),
    api.get('/products/').then(response => { products.value = listData(response) }),
    api.get('/categories/tree/').then(response => { categories.value = listData(response) }),
    api.get('/product-parameters/').then(response => { parameters.value = listData(response) }),
  ])
  if (props.embedded) openCreate(props.initialProduct)
  else openCreateFromRoute()
})
watch(() => route.query.create, () => { if (!props.embedded) openCreateFromRoute() })
onBeforeUnmount(revokeImagePreview)
</script>

<template>
  <div>
    <div class="page-head"><div><h2>SKU 管理</h2><p>按产品分类配置参数，实时生成可报价、可下单的 SKU 组合。</p></div><button class="btn btn-primary" @click="openCreate"><Plus :size="16" /> 新建 SKU</button></div>
    <div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索中文名称、销售型号、SKU 编号或规格..." @input="load" /></div></div>
    <section class="panel"><div v-if="loading" class="loading"><div class="spinner" /></div><div v-else-if="!rows.length" class="empty"><Database :size="32" /><h3>还没有 SKU</h3><p>点击“新建 SKU”开始配置产品规格。</p></div><div v-else class="table-wrap"><table class="data-table"><thead><tr><th>内部识别名称</th><th>对外型号</th><th>SKU Code</th><th>图片</th><th>库存</th><th>单位</th><th>默认售价</th><th /></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td class="primary-cell"><strong>{{ row.display_name_cn || row.product_name }}</strong><small>{{ row.specification || '—' }}</small></td><td><span v-if="row.sales_model">{{ row.sales_model }}</span><span v-else class="muted">未设置</span></td><td>{{ row.sku_code || row.sku }}</td><td><img v-if="row.image" class="sku-table-thumbnail" :src="row.image" :alt="`${row.display_name_cn || row.sku} 图片`" /><span v-else class="sku-image-empty">—</span></td><td>{{ row.stock_quantity }}</td><td>{{ row.unit }}</td><td>{{ row.default_price }} {{ row.currency }}</td><td><div class="table-actions"><button class="mini-btn" title="编辑" @click="openEdit(row)"><Pencil :size="14" /></button><button class="mini-btn danger" title="删除" @click="removeRow(row)"><Trash2 :size="14" /></button></div></td></tr></tbody></table></div></section>

    <Teleport to="body" :disabled="!embedded"><div v-if="modalOpen || route.query.create === '1'" class="modal-backdrop" @mousedown.self="closeModal"><form class="modal sku-modal" @submit.prevent="save"><div class="modal-head"><div><h3>{{ editingId ? '编辑 SKU' : '新建 SKU' }}</h3><p>参数按产品所属分类自动带入；每个值输入后按回车确认。</p></div><button type="button" class="mini-btn" @click="closeModal"><X :size="17" /></button></div><div class="modal-body sku-body">
      <section class="sku-basics"><div class="field"><label>所属产品 <em>*</em></label><select v-model="form.product" required @change="onProductChanged"><option value="">请选择产品</option><option v-for="item in products" :key="item.id" :value="item.id">{{ item.name }}</option></select></div><div class="field"><label>对外商业型号</label><input v-model.trim="form.sales_model" placeholder="可选，如 CB8-24-A1" /><small class="field-help">不填写也可以先保存，报价时会提示。</small></div><div class="field"><label>单位</label><input v-model.trim="form.unit" placeholder="如：pcs" /></div><div class="field"><label>成本价</label><input v-model.number="form.cost_price" type="number" min="0" step="0.0001" /></div><div class="field"><label>默认售价</label><input v-model.number="form.default_price" type="number" min="0" step="0.0001" /></div><div class="field"><label>币种</label><select v-model="form.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div><label class="check-field"><input v-model="form.active" type="checkbox" /> 启用</label><div class="sku-image-picker"><input ref="imageInput" type="file" accept="image/gif,image/jpeg,image/png,image/webp,.gif,.jpg,.jpeg,.png,.webp" hidden @change="onImageSelected" /><img v-if="imagePreviewUrl" class="sku-image-preview" :src="imagePreviewUrl" alt="SKU 图片预览" /><div v-else class="sku-image-placeholder">暂无图片</div><div class="sku-image-actions"><button type="button" class="btn btn-secondary" @click="chooseImage">选择图片</button><button v-if="selectedImage || imagePreviewUrl" type="button" class="btn btn-secondary" @click="clearImageSelection">清除</button></div></div></section>
      <section v-if="product" class="parameter-section"><div class="section-title"><div><small>参数资料</small><h4>按分类填写 SKU 参数</h4></div><span>{{ categoryGroups.length }} 个分类</span></div><p v-if="skuAttributes.length" class="rule-hint">仅展示分类中勾选“参与 SKU 编码”的属性；大写规则将自动应用。</p><div v-if="!skuAttributes.length" class="section-empty">该产品的分类尚未配置“参与 SKU 编码”的参数，请先在产品分类中配置。</div><div v-for="group in categoryGroups" :key="group.id" class="parameter-group"><h5>{{ group.name }}</h5><div v-if="group.attributes.length" class="parameter-grid"><div v-for="attribute in group.attributes" :key="attribute.key" class="parameter-cell"><label>{{ attribute.name }}<small v-if="attribute.unit">（{{ attribute.unit }}）</small></label><ComboInput v-model="parameterValues[`${group.id}:${attribute.key}`]" :options="optionsFor(group, attribute)" :placeholder="`输入${attribute.name}后按回车确认`" multiple /><p>按回车添加多个值</p></div></div><p v-else class="muted">本分类暂无参与 SKU 命名的参数。</p></div></section>
      <section v-if="product" class="preview-section"><div class="section-title"><h4>内部名称与描述预览</h4><span>{{ allPreviews.length }} 个组合</span></div><div v-if="!allPreviews.length" class="section-empty">填写产品参数后将在这里预览内部名称。</div><div v-else class="preview-list"><div v-for="item in allPreviews" :key="item.key" class="preview-card"><strong>{{ item.display_name_cn }}</strong><span>{{ item.description_en }}</span></div></div></section>
      <section v-if="product" class="detail-section"><div class="section-title"><div><small>产品明细</small><h4>包装与发货信息</h4></div><button type="button" class="btn btn-secondary" @click="addDetail"><Plus :size="14" /> 新增</button></div><div class="detail-scroll"><div v-for="(detail, index) in details" :key="index" class="detail-row"><div class="detail-index">{{ index + 1 }}</div><label>产品名称<input v-model.trim="detail.product_name" /></label><label>型号<input v-model.trim="detail.model" placeholder="如：60W" /></label><label>单位<input v-model.trim="detail.unit" /></label><label>备注<input v-model.trim="detail.notes" /></label><label>单个重量 KG<input v-model.number="detail.unit_weight" type="number" min="0" step="0.001" /></label><label>长 CM<input v-model.number="detail.length" type="number" min="0" step="0.1" /></label><label>宽 CM<input v-model.number="detail.width" type="number" min="0" step="0.1" /></label><label>高 CM<input v-model.number="detail.height" type="number" min="0" step="0.1" /></label><label>整件数量<input v-model.number="detail.carton_quantity" type="number" min="0" /></label><button v-if="details.length > 1" type="button" class="mini-btn danger" title="删除此行" @click="removeDetail(index)"><Trash2 :size="14" /></button></div></div></section>
    </div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="closeModal">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : pendingImageSkuIds.length ? '重试上传图片' : editingId ? '保存 SKU' : `创建 ${allPreviews.length || ''} 个 SKU` }}</button></div></form></div></Teleport>
    <div v-if="toast.text" class="toast" :class="{ error: toast.error }">{{ toast.text }}</div>
  </div>
</template>

<style scoped>
.sku-modal{width:min(1475px,calc(100vw - 16px));max-height:calc(100vh - 44px)}.embedded-backdrop{position:absolute;inset:0;z-index:50;padding:0;background:#0b221d66}.embedded-modal{width:100%;max-width:100%;height:100%;max-height:100%;border-radius:0}.modal-head>div p{margin:4px 0 0;color:var(--muted);font-size:12px}.sku-body{display:grid;gap:18px;max-height:calc(100vh - 185px);overflow:auto}.embedded-modal .sku-body{max-height:calc(100% - 145px)}.sku-basics{display:grid;grid-template-columns:minmax(220px,2.2fr) repeat(4,minmax(88px,.72fr)) auto;gap:10px;align-items:end;padding:14px;border:1px solid #dfe9e4;border-radius:11px;background:#fbfdfc}.sku-basics .field:not(:first-child) input,.sku-basics .field:not(:first-child) select{min-width:0}.check-field{height:40px;display:flex;align-items:center;gap:7px;font-size:13px;color:#36594e;white-space:nowrap}.section-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.section-title small{color:#678278;font-size:11px;font-weight:700}.section-title h4{margin:3px 0 0;font-size:15px}.section-title>span{padding:4px 9px;border-radius:99px;background:#e7f2ed;color:#37715f;font-size:11px;font-weight:700}.parameter-section,.preview-section,.detail-section{padding:16px;border:1px solid #dbe7e1;border-radius:12px;background:#fff}.parameter-group{margin-top:14px}.parameter-group h5,.preview-group h5{margin:0 0 9px;color:#365a4d;font-size:13px}.parameter-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.parameter-cell label,.detail-row label{display:block;color:#596b65;font-size:12px;font-weight:600}.parameter-cell label small{color:#889790;font-weight:400}.parameter-cell p{margin:5px 0 0;color:#9aa6a1;font-size:10px}.rule-hint{margin:8px 0 0;color:#678278;font-size:11px}.section-empty{margin-top:13px;padding:16px;border:1px dashed #cbdad4;border-radius:8px;background:#f8fbf9;color:#789087;text-align:center;font-size:12px}.muted{color:var(--muted);font-size:12px}.preview-section{background:#f7faf8}.preview-groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin-top:14px}.preview-group{border:1px solid #d5e4dd;border-radius:9px;background:#fff;overflow:hidden}.preview-group h5{display:flex;justify-content:space-between;padding:10px 11px;margin:0;background:#edf5f1}.preview-group h5 b{font-size:11px;color:#578074}.preview-list{max-height:156px;overflow:auto}.preview-card{padding:9px 11px;border-top:1px solid #eef2f0}.preview-card strong,.preview-card span{display:block}.preview-card strong{color:#193d33;font-size:13px}.preview-card span{margin-top:3px;color:#778882;font-size:11px}.detail-section .btn{padding:8px 11px}.detail-scroll{margin-top:13px;overflow-x:auto}.detail-row{width:100%;min-width:940px;display:grid;grid-template-columns:25px minmax(145px,1.45fr) minmax(96px,.9fr) minmax(66px,.6fr) minmax(118px,1.15fr) repeat(5,minmax(82px,.78fr)) 30px;gap:8px;align-items:end;padding:10px 0;border-top:1px solid #edf1ef}.detail-index{padding-bottom:11px;color:#7c8d86;font-size:12px;font-weight:700}.detail-row input{width:100%;min-width:0;margin-top:5px;border:1px solid #dce4df;border-radius:7px;padding:8px 9px;color:var(--ink);outline:0}.detail-row input:focus{border-color:#72a897;box-shadow:0 0 0 3px #e2efeb}.detail-row .mini-btn{margin-bottom:1px}.table-actions{display:flex;justify-content:flex-end;gap:6px}.mini-btn.danger{color:var(--danger)}@media(max-width:850px){.sku-modal{width:100%;height:100%;max-height:100vh;border-radius:0}.sku-basics{grid-template-columns:repeat(2,minmax(0,1fr))}.parameter-grid{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}}@media(max-width:520px){.sku-basics,.parameter-grid{grid-template-columns:1fr}.sku-body{max-height:calc(100vh - 165px)}}
.detail-row label:nth-of-type(6),.detail-row label:nth-of-type(7),.detail-row label:nth-of-type(8){font-size:0}.detail-row label:nth-of-type(6)::before,.detail-row label:nth-of-type(7)::before,.detail-row label:nth-of-type(8)::before{display:block;font-size:12px;line-height:15px}.detail-row label:nth-of-type(6)::before{content:'外箱长 CM'}.detail-row label:nth-of-type(7)::before{content:'外箱宽 CM'}.detail-row label:nth-of-type(8)::before{content:'外箱高 CM'}.detail-row label:nth-of-type(6) input,.detail-row label:nth-of-type(7) input,.detail-row label:nth-of-type(8) input{font-size:14px}
.sku-image-picker{grid-column:1/-1;display:flex;align-items:center;gap:11px;padding-top:4px}.sku-image-preview,.sku-image-placeholder{width:64px;height:64px;border:1px solid #d6e2dc;border-radius:8px;background:#fff;object-fit:cover}.sku-image-placeholder{display:grid;place-items:center;color:#93a29c;font-size:11px}.sku-image-actions{display:flex;gap:7px}.sku-image-actions .btn{padding:8px 10px;font-size:12px}
</style>
