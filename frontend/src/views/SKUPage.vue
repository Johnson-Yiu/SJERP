<script setup>
import { useWorkspaceTeleportDisabled } from "../composables/useWorkspaceTeleport"
const workspaceTeleportDisabled = useWorkspaceTeleportDisabled()
import { useWorkspaceNavigation } from '../composables/useWorkspaceNavigation'
const { workspace } = useWorkspaceNavigation()
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, listAll } = useWorkspaceApi()
import { provideUnsavedChangesScope, useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'

import SkuCombinationRuleEditor from "../components/SkuCombinationRuleEditor.vue"
import { matchesCombinationRules } from "../utils/skuCombinationRules"
import { resolveDetailForPreview } from '../utils/skuDetails'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Database, History, Layers3, Pencil, Plus, Search, Trash2, X } from 'lucide-vue-next'
import { pinyin } from 'pinyin-pro'
import { listData } from '../api'
import { apiErrorMessage } from '../utils/apiErrors.js'
import { packagingError } from '../utils/packagingPresentation'
import { confirmDialog } from '../dialogs'
import EntityDetailModal from '../components/EntityDetailModal.vue'
import ComboInput from '../components/ComboInput.vue'
import { formatMoney, normalizeMoneyInput } from '../utils/money'
import SummaryCards from '../components/SummaryCards.vue'
import PageLoadState from '../components/PageLoadState.vue'
import ListEmptyState from '../components/ListEmptyState.vue'
import { clearModalRoute } from '../utils/modalNavigation'
import { useAccessControl } from '../accessControl'

const props = defineProps({ embedded: Boolean, inline: Boolean, initialProduct: [Number, String] })
const emit = defineEmits(['close', 'saved'])
const { can } = useAccessControl()
const routeCreateOpen = ref(false)
const rows = ref([]), products = ref([]), categories = ref([]), parameters = ref([]), packagingTemplates = ref([])
const route = useRoute(), router = useRouter()
const query = ref(props.embedded ? '' : route.query.search || ''), loading = ref(true), hasLoaded = ref(false), loadError = ref(''), modalOpen = ref(false), saving = ref(false), editingId = ref(null)
const productFilter = ref(route.query.productFilter || ''), statusFilter = ref(route.query.status || ''), parameterSearch = ref('')
const visibleRows = computed(() => rows.value.filter(row => (!productFilter.value || Number(row.product) === Number(productFilter.value)) && (!statusFilter.value || (statusFilter.value === 'active' ? row.active !== false : row.active === false))))
function applyListFilters() { return router.replace({path:route.path,query:{...route.query,search:query.value || undefined,productFilter:productFilter.value || undefined,status:statusFilter.value || undefined}}) }
const detailId = ref(route.query.detail || null), detailRefresh = ref(0)
async function editDetail() { try { openEdit(rows.value.find(row=>Number(row.id)===Number(detailId.value)) || (await api.get('/skus/' + detailId.value + '/')).data) } catch(error) { notify(apiErrorMessage(error),true) } }
function openDetail(row) { return router.push({path:route.path,query:{...route.query,detail:String(row.id)}}) }
function closeDetail() { const {detail,tab,...query}=route.query; return router.replace({path:route.path,query}) }
const optionErrors = reactive({}), optionLoaded = reactive({})
const skuOptionsReady = computed(() => ['products', 'categories', 'parameters', 'packagingTemplates', 'suppliers'].every(key => optionLoaded[key] && !optionErrors[key]))
const filteredSkuEmpty = computed(() => Boolean((query.value || productFilter.value || statusFilter.value) && historyRows.value.length))
const identityReviewOpen = ref(false), identityReviewSaving = ref(false), identityReviewError = ref(''), pendingIdentitySave = ref(null)
const toast = reactive({ text: '', error: false })
const saveError = ref('')
const editorBody = ref(null), editorStep = ref(1)
const editorSteps = [{ number: 1, title: '基本信息', hint: '产品与描述' }, { number: 2, title: '参数配置', hint: '填写 SKU 参数' }, { number: 3, title: '组合预览', hint: '确认生成结果' }, { number: 4, title: '包装与发货', hint: '选填' }, { number: 5, title: '完成', hint: '确认并保存' }]
function goToEditorStep(number) {
  const section = editorBody.value?.querySelector(`[data-sku-step="${number}"]`)
  if (!section) return
  editorStep.value = number
  section.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function trackEditorStep() {
  if (!editorBody.value) return
  const top = editorBody.value.getBoundingClientRect().top
  const sections = [...editorBody.value.querySelectorAll('[data-sku-step]')]
  const current = sections.filter(section => section.getBoundingClientRect().top <= top + 100).at(-1)
  editorStep.value = Number(current?.dataset.skuStep || 1)
}

const form = reactive({ sku: '', product: '', sales_model: '', description_cn: '', description_en: '', unit: 'pcs', currency: 'USD', default_price: '0.00', cost_price: '0.00', cost_currency: 'CNY', active: true })
const parameterValues = reactive({})
const salesModelAbbreviations = reactive({})
const abbreviationSuggestions = reactive({})
const systemAbbreviationDefaults = reactive({})
const abbreviationGuideOpen = ref(false)
const lightingTermTranslations = [
  ['橱柜电源', 'Cabinet LED Driver'], ['橱柜灯', 'Cabinet Light'], ['户外电源', 'Outdoor LED Driver'], ['室内电源', 'Indoor LED Driver'],
  ['轨道射灯', 'Track Spotlight'], ['磁吸轨道灯', 'Magnetic Track Light'], ['筒灯', 'Downlight'], ['射灯', 'Spotlight'], ['面板灯', 'Panel Light'], ['线性灯', 'Linear Light'],
  ['灯带', 'LED Strip'], ['灯条', 'LED Bar'], ['投光灯', 'Floodlight'], ['壁灯', 'Wall Light'], ['吊灯', 'Pendant Light'], ['吸顶灯', 'Ceiling Light'], ['台灯', 'Table Lamp'], ['路灯', 'Street Light'], ['庭院灯', 'Garden Light'],
  ['驱动电源', 'LED Driver'], ['电源', 'Power Supply'], ['黑色', 'Black'], ['白色', 'White'], ['银色', 'Silver'], ['金色', 'Gold'], ['灰色', 'Grey'],
  ['暖白', 'Warm White'], ['中性白', 'Neutral White'], ['冷白', 'Cool White'], ['日光白', 'Daylight'], ['可调光', 'Dimmable'], ['不调光', 'Non-dimmable'],
  ['防水', 'Waterproof'], ['防尘', 'Dustproof'], ['感应', 'Sensor'], ['人体感应', 'PIR Sensor'], ['微波感应', 'Microwave Sensor'], ['应急', 'Emergency'], ['铝', 'Aluminum'], ['不锈钢', 'Stainless Steel'], ['透明', 'Clear'], ['磨砂', 'Frosted'],
].sort(([left], [right]) => right.length - left.length)
function translateLightingTerms(value) {
  return lightingTermTranslations.reduce((text, [chinese, english]) => text.replaceAll(chinese, english), String(value || ''))
}
const abbreviationReferenceGroups = [
  { title: '电气与功率', rows: [['12V / 24V / 48V', '12V / 24V / 48V'], ['36W / 60W / 100W', '36 / 60 / 100'], ['AC / DC / AC/DC', 'AC / DC / ACDC']] },
  { title: '光色与光学', rows: [['黑 / 白 / 暖白 / 中性白 / 冷白 / 日光白', 'BL / WH / WW / NW / CW / DL'], ['2700K / 3000K / 4000K / 6500K', '27K / 30K / 40K / 65K'], ['红 / 绿 / 蓝 / 琥珀 / RGB / RGBW', 'RD / GN / BU / AM / RGB / RGBW'], ['15° / 24° / 36° / 60°', '15D / 24D / 36D / 60D']] },
  { title: '性能与控制', rows: [['Ra80 / Ra90 / Ra95', 'CRI80 / CRI90 / CRI95'], ['IP65 / IK08 / L70 / 3 SDCM', 'IP65 / IK08 / L70 / 3SDCM'], ['不调光 / 可调光', 'ND / DIM'], ['0-10V / DALI / PWM / TRIAC / DMX', '0-10V / DALI / PWM / TRIAC / DMX'], ['CCT 可调 / 三色变光 / 暖调光', 'CCT / 3CCT / DTW']] },
  { title: '结构与功能', rows: [['明装 / 嵌入式 / 吊装 / 壁装 / 轨道', 'SM / REC / PEN / WM / TRK'], ['铝 / PC / 玻璃 / 不锈钢', 'AL / PC / GL / SS'], ['应急 / 非应急 / PIR / 微波感应 / 光感', 'EM / NE / PIR / MW / PC']] },
]
const selectedCombinations = ref(new Set())
const chosenPreviews = computed(() => allPreviews.value.filter(p => !p.duplicate && selectedCombinations.value.has(p.key)))
function chooseCombination(key, checked) { const next = new Set(selectedCombinations.value); checked ? next.add(key) : next.delete(key); selectedCombinations.value = next }
const details = ref([])
const suppliers = ref([])
const packagingPicker = ref('')
const batchSalesModelQuery = ref('')
const batchPackagingTemplate = ref('')
const batchTagFilters = reactive({})
const batchFillHistory = ref([])
const batchFillBaseline = new Map()
const batchDetailFields = reactive({ unit: '', notes: '', unit_weight: '', carton_quantity: '' })
const packagingDialogOpen = ref(false), packagingSaving = ref(false), packagingTarget = ref(null), packagingSaveError=ref(''), editingPackaging=ref(null)
const packagingStatusLabels={NOT_CONFIGURED:'未配置',PARTIAL:'资料不完整',COMPLETE:'待验证',VERIFIED:'已验证'}
function tradeUnitsLocation(){const {create,edit,returnTo,...context}=props.embedded?{}:route.query;const listPath=router.resolve({path:'/skus',query:context}).fullPath;return {path:'/sku-trade-units',query:{sku:String(editingId.value),returnTo:router.resolve({path:'/skus',query:{...context,edit:String(editingId.value),returnTo:listPath}}).fullPath}}}
const packagingForm = reactive({ name: '', supplier: '', carton_length: '', carton_width: '', carton_height: '', carton_tare_weight: 0, partial_carton_policy: 'SAME_CARTON', active: true, description: '' })
const imageInput = ref(null), selectedImage = ref(null), imagePreviewUrl = ref(''), savedImageUrl = ref('')
const imageClearRequested = ref(false), pendingImageSkuIds = ref([]), pendingImageFailurePrefix = ref('SKU 已创建，图片上传失败。请重试。')
const editorScope = provideUnsavedChangesScope()
const guard = useUnsavedChangesGuard({ data: () => ({ form, parameters: parameterValues, abbreviations: salesModelAbbreviations, details: details.value, combinations: selectedCombinations.value, image: selectedImage.value, clearImage: imageClearRequested.value }), enabled: () => modalOpen.value, busy: () => modalOpen.value && (saving.value || identityReviewSaving.value || supplierSourceSaving.value || packagingSaving.value), scope: editorScope })
const versionsOpen = ref(false), versions = ref([]), versionsLoading = ref(false), versionsError = ref(''), versionsRow = ref(null)
const supplierTraitsText = ref('')
const supplierSources = ref([]), supplierSourcesLoading = ref(false), supplierSourcesError = ref(''), supplierSourceDialogOpen = ref(false), supplierSourceSaving = ref(false), supplierSourceEditingId = ref(null)
const supplierSourceError = ref('')
const supplierSourceForm = reactive({ supplier: '', supplier_model: '', supplier_product_name: '', supplier_sku_code: '', supplier_barcode: '', purchase_price: '0.00', currency: 'USD', moq: 0, lead_time_days: 0, is_active: true, is_preferred: false, remarks: '' })
const costVerification = reactive({ state: 'missing', verifiedAt: '', verifiedBy: '' })
const verificationLabels = { missing: '未维护', unverified: '待核实', expired: '已过期', current: '已核实' }
function verificationText(state) { return verificationLabels[state] || '未知' }
function verificationDate(value) { return value ? new Date(value).toLocaleDateString('zh-CN') : '—' }
function setCostVerification(row) {
  costVerification.state = row?.cost_verification_state || 'missing'
  costVerification.verifiedAt = row?.cost_verified_at || ''
  costVerification.verifiedBy = row?.cost_verified_by_name || ''
}
function skuCostNeedsSave() {
  const row = rows.value.find(item => Number(item.id) === Number(editingId.value))
  if (!row) return false
  return normalizeMoneyInput(form.cost_price) !== normalizeMoneyInput(row.cost_price) || String(form.cost_currency || '') !== String(row.cost_currency || '')
}
function supplierCostNeedsSave(source) {
  if (!supplierSourceEditingId.value || Number(supplierSourceEditingId.value) !== Number(source.id)) return false
  return normalizeMoneyInput(supplierSourceForm.purchase_price) !== normalizeMoneyInput(source.purchase_price) || String(supplierSourceForm.currency || '') !== String(source.currency || '')
}
const supplierSourceGuard = useUnsavedChangesGuard({ data: () => ({ form: supplierSourceForm, traits: supplierTraitsText.value }), enabled: () => supplierSourceDialogOpen.value, busy: () => supplierSourceDialogOpen.value && supplierSourceSaving.value, routeGuard: false, scope: editorScope })
const packagingGuard = useUnsavedChangesGuard({ data: () => packagingForm, enabled: () => packagingDialogOpen.value, busy:()=>packagingSaving.value, routeGuard: false, scope: editorScope })
const requestSupplierSourceClose = () => supplierSourceGuard.requestClose(() => { supplierSourceDialogOpen.value = false })
const requestPackagingClose = () => packagingGuard.requestClose(() => { packagingDialogOpen.value = false })

const product = computed(() => products.value.find(item => Number(item.id) === Number(form.product)))
const inheritedProduct = computed(() => !editingId.value && Boolean(props.initialProduct || route.query.product))
const compactCreate = computed(() => props.inline && inheritedProduct.value)
const productById = computed(() => new Map(products.value.map(item => [Number(item.id), item])))
const categoryMap = computed(() => new Map(categories.value.map(item => [item.id, item])))
const activeCategories = computed(() => {
  if (!product.value) return []
  return [product.value.category, ...(product.value.additional_categories || [])].filter(Boolean).map(id => categoryMap.value.get(Number(id))).filter(Boolean)
})
const categoryGroups = computed(() => product.value?.sku_definitions != null
  ? Object.values(product.value.sku_definitions.reduce((groups, attribute) => {
      if (!attribute.include_in_sku && !attribute.include_in_sales_model) return groups
      const id = attribute.category_id
      groups[id] ||= { id, name: categoryMap.value.get(id)?.name || '产品参数', attributes: [] }
      groups[id].attributes.push(attribute)
      return groups
    }, {}))
  : activeCategories.value.map(category => ({
  ...category,
  attributes: (category.effective_attributes || []).filter(attribute => attribute.include_in_sku || attribute.include_in_sales_model),
})))
const ordinaryAttributes = computed(() => (product.value?.sku_definitions || activeCategories.value.flatMap(c => c.effective_attributes || []))
  .filter(a => !a.include_in_sku && !a.include_in_sales_model))
const ordinaryValues = () => Object.fromEntries(ordinaryAttributes.value.map(a => {
  const key = `${a.category_id || a.category || 0}:${a.key}`
  return [key, parameterValues[key] ?? a.default_value ?? '']
}))
const skuAttributes = computed(() => {
  const seen = new Set()
  return categoryGroups.value.flatMap(group => group.attributes.map(attribute => ({ group, attribute }))).filter(({ attribute }) => {
    const key = String(attribute.key || attribute.name).toLowerCase()
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})
const historyRows = ref([])
const visibleCategoryGroups = computed(() => categoryGroups.value.map(group => ({...group,attributes:group.attributes.filter(attribute => `${group.name} ${attribute.name} ${attribute.key}`.toLowerCase().includes(parameterSearch.value.trim().toLowerCase()))})).filter(group => group.attributes.length))
const duplicateInputKeys = computed(() => { const seen=new Set(), repeated=new Set(); allPreviews.value.forEach(row => {if(seen.has(row.key)) repeated.add(row.key); seen.add(row.key)}); return repeated })
const previewSummary = computed(() => `已选 ${chosenPreviews.value.length} 项 · 已存在 ${allPreviews.value.filter(row=>row.duplicate).length} 项${duplicateInputKeys.value.size ? ` · 输入重复 ${duplicateInputKeys.value.size} 项` : ''}`)
const optionsFor = (category, attribute, includeDefault = true) => {
  const values = new Map()
  const belongsToCategory = sourceProduct => {
    if (!sourceProduct) return false
    if (Number(sourceProduct.id) === Number(form.product)) return true
    return [sourceProduct.category, ...(sourceProduct.additional_categories || [])].some(id => {
      const seen = new Set()
      while (id && !seen.has(Number(id))) {
        if (Number(id) === Number(category.id)) return true
        seen.add(Number(id))
        id = categoryMap.value.get(Number(id))?.parent
      }
      return false
    })
  }
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
  historyRows.value.forEach(row => {
    if (!belongsToCategory(productById.value.get(Number(row.product)))) return
    const stored = row.parameter_values || {}
    const aliases = [attribute.key, attribute.name, attribute.key?.split('/')[0]].filter(Boolean).map(key => key.toLocaleLowerCase())
    const matches = Object.entries(stored).filter(([key]) => aliases.includes(key.split(':').at(-1).toLocaleLowerCase()))
    const raw = stored[`${category.id}:${attribute.key}`] ?? stored[attribute.key] ?? stored[attribute.name] ?? (matches.length === 1 ? matches[0][1] : undefined)
    splitValues(raw).forEach(addValue)
  })
  if (includeDefault) addValue(attribute.default_value)
  return [...values.values()].map(value => ({ value, label: value }))
}
const splitValues = value => String(value || '').split(/\r?\n/).map(item => item.trim()).filter(Boolean)
function useHistoricalValue(group, attribute, value) {
  const key = parameterKey(group, attribute)
  const values = splitValues(parameterValues[key])
  const normalized = attribute.uppercase ? value.toUpperCase() : value
  if (!values.some(item => item.toLocaleLowerCase() === normalized.toLocaleLowerCase())) {
    parameterValues[key] = [...values, normalized].join('\n')
  }
}

const cartesian = arrays => arrays.reduce((result, items) => result.flatMap(prefix => items.map(item => [...prefix, item])), [[]])
const previewColumns = computed(() => skuAttributes.value.map(({ attribute }) => ({ key: attribute.key, name: attribute.name })))
const skuMetrics = computed(() => [
  { label: 'SKU 总数', value: visibleRows.value.length, hint: '当前查询结果' },
  { label: '已启用', value: visibleRows.value.filter(row => row.active).length, hint: '可用于报价与下单' },
  { label: '已设型号', value: visibleRows.value.filter(row => row.sales_model).length, hint: '对外 Sales Model 已完整' },
  { label: '关联产品', value: new Set(visibleRows.value.map(row => row.product).filter(Boolean)).size, hint: '已配置销售规格的产品' },
])
const normalizeAbbreviationKey = key => {
  const parts = String(key || '').split(':')
  if (parts.length < 3) return String(key || '').trim()
  return `${parts.shift().trim()}:${parts.shift().trim().toLocaleLowerCase()}:${parts.join(':').trim().toLocaleLowerCase().replace(/\s+/g, ' ')}`
}
const parameterKey = (group, attribute) => `${attribute.category || attribute.category_id || group.id}:${attribute.key}`
const abbreviationKey = (group, attribute, value) => normalizeAbbreviationKey(`${parameterKey(group, attribute)}:${value}`)
const abbreviationSuggestionKey = (group, attribute, value) => abbreviationKey(group, attribute, value)
const defaultAbbreviationKey = value => String(value || '').trim().toLocaleLowerCase().replace(/\s+/g, '')
function suggestedAbbreviation(group, attribute, value) {
  const normalizedValues = [value, formatParameterValue(attribute, value)].map(defaultAbbreviationKey)
  return normalizedValues.map(key => systemAbbreviationDefaults[key]).find(Boolean) || abbreviationSuggestions[abbreviationSuggestionKey(group, attribute, value)] || ''
}
function applyAbbreviationSuggestions() {
  categoryGroups.value.forEach(group => group.attributes.filter(attribute => attribute.include_in_sales_model).forEach(attribute => {
    splitValues(parameterValues[parameterKey(group, attribute)]).forEach(value => {
      const key = abbreviationKey(group, attribute, value)
      const suggested = suggestedAbbreviation(group, attribute, value)
      if (!salesModelAbbreviations[key] && suggested) salesModelAbbreviations[key] = suggested
    })
  }))
}
async function loadAbbreviationSuggestions() {
  Object.keys(abbreviationSuggestions).forEach(key => delete abbreviationSuggestions[key])
  Object.keys(systemAbbreviationDefaults).forEach(key => delete systemAbbreviationDefaults[key])
  if (!activeCategories.value.length) return
  try {
    const responses = await Promise.all(activeCategories.value.map(category => api.get('/skus/sales-model-abbreviations/', { params: { category: category.id } })))
    responses.forEach(response => { Object.assign(abbreviationSuggestions, response.data.abbreviations || {}); Object.assign(systemAbbreviationDefaults, response.data.defaults || {}) })
    applyAbbreviationSuggestions()
  } catch (error) { notify(error.message, true) }
}
function diffSegments(oldValue, newValue, side = 'new') {
  const oldText = String(oldValue || ''), newText = String(newValue || '')
  if (oldText === newText) return [{ text: newText || '—', changed: false }]
  let prefix = 0
  while (prefix < oldText.length && prefix < newText.length && oldText[prefix] === newText[prefix]) prefix += 1
  let suffix = 0
  while (suffix < oldText.length - prefix && suffix < newText.length - prefix && oldText[oldText.length - suffix - 1] === newText[newText.length - suffix - 1]) suffix += 1
  const oldMiddle = oldText.slice(prefix, oldText.length - suffix), newMiddle = newText.slice(prefix, newText.length - suffix)
  return [
    { text: newText.slice(0, prefix), changed: false },
    { text: (side === 'old' ? oldMiddle : newMiddle) || (side === 'old' && oldMiddle ? '∅' : ''), changed: true },
    { text: newText.slice(newText.length - suffix), changed: false },
  ].filter(segment => segment.text)
}
const identityReview = computed(() => {
  const pending = pendingIdentitySave.value
  if (!pending) return { oldName: '', newName: '', oldModel: '', newModel: '' }
  return {
    oldName: pending.editingRow?.display_name_cn || '',
    newName: pending.editingPreview?.display_name_cn || '',
    oldModel: pending.editingRow?.sales_model || '',
    newModel: form.sales_model || '',
  }
})
const formatParameterValue = (attribute, value) => {
  let formatted = String(value || '').trim()
  const unit = String(attribute.unit || '').trim()
  if (formatted && unit && !formatted.toLocaleLowerCase().endsWith(unit.toLocaleLowerCase())) formatted = `${formatted}${unit}`
  return attribute.uppercase ? formatted.toUpperCase() : formatted
}
function applyDefaultAbbreviation(group, attribute, value) {
  const suggested = suggestedAbbreviation(group, attribute, value)
  if (!suggested) return notify(`“${value}”暂未配置默认型号缩写。`, true)
  salesModelAbbreviations[abbreviationKey(group, attribute, value)] = suggested
}
const theoreticalPreviews = computed(() => {
  const parts = skuAttributes.value.map(({ group, attribute }) => ({ group, attribute, values: splitValues(parameterValues[parameterKey(group, attribute)]) }))
  if (parts.reduce((n,part) => n * Math.max(1,part.values.length),1) > 1000) return []
  const combinations = cartesian(parts.map(part => part.values.length ? part.values : ['']))
  return combinations.filter(values => values.some(Boolean) || !parts.length).map((values, combinationIndex) => {
    const attributeLabels = parts.map((part, index) => {
      const value = values[index]
      return value ? formatParameterValue(part.attribute, value) : ''
    })
    const labels = attributeLabels.filter((label, index) => label && parts[index].attribute.include_in_sku)
    const parameterSnapshot = Object.fromEntries(parts.map((part, index) => [part.attribute.name, values[index]]).filter(([, value]) => value))
    const parameterValuesForSku = { ...ordinaryValues(), ...Object.fromEntries(parts.map((part, index) => [parameterKey(part.group, part.attribute), values[index]]).filter(([, value]) => value)) }
    const display_name_cn = [product.value?.name, ...labels].filter(Boolean).join('-')
    const description_cn = [product.value?.name, ...labels].filter(Boolean).join('，')
    const description_en = translateLightingTerms([product.value?.name_en || product.value?.name, ...labels].filter(Boolean).join(', '))
    const sales_model_suffix = parts.map((part, index) => part.attribute.include_in_sales_model ? String(salesModelAbbreviations[abbreviationKey(part.group, part.attribute, values[index])] || '').trim().toUpperCase() : '').filter(Boolean).join('')
    const sales_model_base = sales_model_suffix ? [product.value?.sales_model_prefix, sales_model_suffix].filter(Boolean).join('-') : ''
    const sales_model = sales_model_base
    const key = values.map(value => String(value || '')).join('|') || String(combinationIndex)
    return { key, duplicate: historyRows.value.some(row => row.active !== false && Number(row.product) === Number(form.product) && Number(row.id) !== Number(editingId.value) && normalizedParameterValues(row.parameter_values) === normalizedParameterValues(parameterValuesForSku)), display_name_cn, description_cn, description_en, specification: labels.join(' / '), parameterSnapshot, parameterValuesForSku, sales_model, attributeValues: Object.fromEntries(parts.map((part, index) => [part.attribute.key, attributeLabels[index] || ''])) }
  })
})
const previewRules = ref(null), combinationRulesDirty = ref(false)
const ruleDefinitions = computed(() => skuAttributes.value.map(({ group, attribute }) => ({ key: parameterKey(group, attribute), name: attribute.name, unit: attribute.unit, values: [...new Set([...splitValues(parameterValues[parameterKey(group, attribute)]), ...optionsFor(group, attribute).map(o => o.value)])] })))
const allPreviews = computed(() => theoreticalPreviews.value.filter(preview => matchesCombinationRules(preview.parameterValuesForSku, previewRules.value ?? product.value?.combination_rules ?? [], ruleDefinitions.value)))
function previewCombinationRules(rules) {
  previewRules.value = rules
  if (rules !== null) selectedCombinations.value = new Set(allPreviews.value.filter(p => !p.duplicate).map(p => p.key))
}
function savedCombinationRules(rules) {
  product.value.combination_rules = rules
  combinationRulesDirty.value = false
  previewCombinationRules(rules)
}
watch([() => route.query.search, () => route.query.productFilter, () => route.query.status], ([search, product, status]) => {
  if (props.embedded) return
  query.value = search || ''; productFilter.value = product || ''; statusFilter.value = status || ''
  void load()
})
watch(() => route.query.detail, value => {detailId.value=value || null})
watch(() => form.product, () => { previewRules.value = null; combinationRulesDirty.value = false })
function newDetail(name = product.value?.name || '', key = '') { return { preview_key: key, product_name: name, unit: form.unit || 'pcs', notes: '', unit_weight: 0, carton_quantity: 0, packaging_template: '', packaging_query: '' } }
function detailFor(preview) {
  return resolveDetailForPreview(details.value, preview, allPreviews.value.length,
    () => newDetail(product.value?.name || '', preview.key))
}
function syncDetails(previews) {
  const saved = new Map(details.value.map(detail => [detail.preview_key, detail]))
  const existingSingle = previews.length === 1 && details.value.length === 1 ? details.value[0] : null
  details.value = previews.map(preview => saved.get(preview.key) || (existingSingle ? { ...existingSingle, preview_key: preview.key } : newDetail(product.value?.name || '', preview.key)))
}

let toastTimer
function notify(text, error = false) { clearTimeout(toastTimer); Object.assign(toast, { text, error }); toastTimer = setTimeout(() => { toast.text = '' }, 2600) }
function reportSaveError(error, prefix = '') {
  const message = `${prefix}${apiErrorMessage(error)}`
  saveError.value = message
  notify(message, true)
}
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
function updateSavedRow(saved) {
  if (!saved?.id) return
  for (const list of [rows, historyRows]) {
    list.value = list.value.map(row => row.id === saved.id ? { ...row, ...saved } : row)
  }
}
async function uploadImage(skuId, file) {
  const data = new FormData()
  data.append('image', file)
  const response = await api.post(`/skus/${skuId}/image/`, data)
  updateSavedRow(response.data)
}
async function clearImage(skuId) {
  const response = await api.delete(`/skus/${skuId}/image/`)
  updateSavedRow(response.data)
}
async function uploadPendingImages() {
  const results = await Promise.allSettled(pendingImageSkuIds.value.map(async skuId => {
    await uploadImage(skuId, selectedImage.value)
    pendingImageSkuIds.value = pendingImageSkuIds.value.filter(id => id !== skuId)
  }))
  const failed = results.find(result => result.status === 'rejected')
  if (failed) throw failed.reason
}
let loadVersion = 0
let supplierSourcesVersion = 0
async function load() {
  const version = ++loadVersion
  const search = query.value
  loading.value = true
  loadError.value = ''
  try {
    // Search results drive the list; unfiltered history still drives duplicate detection.
    const [visible, history] = await Promise.all([listAll('/skus/', { params: { search, include_inactive: '1' } }), search ? listAll('/skus/', {params:{include_inactive:'1'}}) : Promise.resolve(null)])
    // Publish both results together, only for the latest logical load.
    if (version !== loadVersion) return
    rows.value = visible
    historyRows.value = history || visible
    hasLoaded.value = true
  } catch (error) {
    if (version === loadVersion) loadError.value = apiErrorMessage(error)
  } finally {
    if (version === loadVersion) loading.value = false
  }
}
async function loadSkuReferenceOptions() {
  const tasks = [
    ['products', '产品', async () => { products.value = await listAll('/products/') }],
    ['categories', '产品分类', async () => { categories.value = listData(await api.get('/categories/tree/')) }],
    ['parameters', '产品参数', async () => { parameters.value = await listAll('/product-parameters/') }],
    ['packagingTemplates', '包装模板', async () => { packagingTemplates.value = (await listAll('/packaging-templates/')).filter(item => item.active) }],
    ['suppliers', '供应商', async () => { suppliers.value = await listAll('/suppliers/') }],
  ]
  await Promise.all(tasks.map(async ([key, label, loadOption]) => {
    try { await loadOption(); optionLoaded[key] = true; delete optionErrors[key] }
    catch (error) { optionErrors[key] = `${label}资料加载失败：${apiErrorMessage(error)}` }
  }))
}
function clearSkuFilters() {query.value = ''; productFilter.value = ''; statusFilter.value = ''; return applyListFilters()}
async function openCreate(productId = '') {
  if(typeof productId === 'object') productId = ''
  if (!can('skus', 'create')) return
  parameterSearch.value = ''; saveError.value = ''; toast.text = ''
  supplierSourcesVersion++
  editingId.value = null
  identityReviewOpen.value = false; identityReviewError.value = ''; pendingIdentitySave.value = null
  supplierSources.value = []
  supplierSourceDialogOpen.value = false
  savedImageUrl.value = ''
  imageClearRequested.value = false
  pendingImageSkuIds.value = []
  resetImagePicker()
  Object.assign(form, { sku: '', product: productId ? Number(productId) : '', sales_model: '', description_cn: '', description_en: '', unit: 'pcs', currency: 'USD', default_price: '0.00', cost_price: '0.00', cost_currency: 'CNY', active: true })
  setCostVerification(null)
  if (compactCreate.value) {
    form.unit = product.value?.unit || 'pcs'
    form.currency = product.value?.currency || 'USD'
  }
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  Object.keys(salesModelAbbreviations).forEach(key => delete salesModelAbbreviations[key])
  details.value = []
  resetBatchFillState()
  await loadAbbreviationSuggestions()
  await nextTick()
  guard.markClean()
  modalOpen.value = true
}
function openCreateFromRoute() {
  if (route.query.create !== '1' || (modalOpen.value && !routeCreateOpen.value)) return
  routeCreateOpen.value = true
  openCreate(route.query.product)
}
const closeModal = () => { if(saving.value || identityReviewSaving.value || supplierSourceSaving.value || packagingSaving.value) return; return editorScope.requestClose(discardModal) }
function discardModal() {
  supplierSourcesVersion++
  identityReviewOpen.value = false; identityReviewError.value = ''; pendingIdentitySave.value = null
  modalOpen.value = false
  routeCreateOpen.value = false
  supplierSourceDialogOpen.value = false
  resetImagePicker()
  if (props.embedded) return emit('close')
  void clearModalRoute(router, route)
}
async function openEdit(row) {
  parameterSearch.value = ''; saveError.value = ''; toast.text = ''
  if (!can('skus', 'update')) return
  supplierSourcesVersion++
  editingId.value = row.id
  editingPackaging.value = row.packaging || null
  identityReviewOpen.value = false; identityReviewError.value = ''; pendingIdentitySave.value = null
  supplierSources.value = []
  supplierSourceDialogOpen.value = false
  savedImageUrl.value = row.image || ''
  imageClearRequested.value = false
  pendingImageSkuIds.value = []
  resetImagePicker(savedImageUrl.value)
  Object.assign(form, { sku: row.sku_code || row.sku || '', product: row.product, sales_model: row.sales_model || '', description_cn: row.description_cn || '', description_en: row.description_en || '', unit: row.unit, currency: row.currency, default_price: normalizeMoneyInput(row.default_price), cost_price: row.cost_price == null ? '0.00' : normalizeMoneyInput(row.cost_price), cost_currency: row.cost_currency || '', active: row.active })
  setCostVerification(row)
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  Object.keys(salesModelAbbreviations).forEach(key => delete salesModelAbbreviations[key])
  resetBatchFillState()
  Object.entries(row.parameter_values || {}).forEach(([key, value]) => { parameterValues[key] = value })
  skuAttributes.value.forEach(({group, attribute}) => {
    const key = parameterKey(group,attribute)
    if (!(key in parameterValues)) {
      const aliases = [attribute.key.toLowerCase(), attribute.name.toLowerCase(), attribute.key.split('/')[0].toLowerCase()]
      const values = Object.entries(row.parameter_values || {}).filter(([k]) => aliases.includes(k.split(':').at(-1).toLowerCase()))
      if (values.length === 1) parameterValues[key] = values[0][1]
    }
  })
  Object.entries(row.sales_model_abbreviations || {}).forEach(([key, value]) => { salesModelAbbreviations[normalizeAbbreviationKey(key)] = String(value || '').trim().toUpperCase() })
  details.value = [{ ...(row.product_details?.[0] || newDetail(row.product_name)), preview_key: '', packaging_template: row.packaging?.template || '', packaging_query: row.packaging?.template_name || '', unit_weight: row.packaging?.unit_net_weight ?? row.product_details?.[0]?.unit_weight ?? 0, carton_quantity: row.packaging?.effective_qty_per_carton || row.product_details?.[0]?.carton_quantity || 0 }]
  await loadAbbreviationSuggestions()
  await nextTick()
  guard.markClean()
  modalOpen.value = true
  void loadSupplierSources(row.id)
}
async function loadSupplierSources(skuId) {
  if (!skuId) return
  supplierSourcesLoading.value = true
  supplierSourcesError.value = ''
  const version = ++supplierSourcesVersion
  try {
    const sources = await listAll('/supplier-skus/', { params: { sku: skuId } })
    if (version === supplierSourcesVersion) supplierSources.value = sources
  } catch (error) {
    if (version === supplierSourcesVersion) supplierSourcesError.value = `供应商来源加载失败：${apiErrorMessage(error)}`
  } finally {
    if (version === supplierSourcesVersion) supplierSourcesLoading.value = false
  }
}
function resetSupplierSourceForm() { supplierSourceError.value = ''; toast.text = ''; supplierTraitsText.value = ''; Object.assign(supplierSourceForm, { supplier: '', supplier_model: '', supplier_product_name: '', supplier_sku_code: '', supplier_barcode: '', purchase_price: '0.00', currency: 'USD', moq: 0, lead_time_days: 0, is_active: true, is_preferred: false, remarks: '' }) }
async function openSupplierSourceCreate() { if (!can('suppliers', 'create')) return; supplierSourceEditingId.value = null; resetSupplierSourceForm(); await nextTick(); supplierSourceGuard.markClean(); supplierSourceDialogOpen.value = true }
async function openSupplierSourceEdit(source) { supplierSourceError.value = ''; toast.text = ''; if (!can('suppliers', 'update')) return; supplierTraitsText.value = Object.entries(source.characteristics || {}).map(([k,v]) => `${k}：${v}`).join('\n'); supplierSourceEditingId.value = source.id; Object.assign(supplierSourceForm, { supplier: source.supplier, supplier_model: source.supplier_model || '', supplier_product_name: source.supplier_product_name || '', supplier_sku_code: source.supplier_sku_code || '', supplier_barcode: source.supplier_barcode || '', purchase_price: normalizeMoneyInput(source.purchase_price), currency: source.currency || 'USD', moq: source.moq, lead_time_days: source.lead_time_days, is_active: source.is_active, is_preferred: source.is_preferred, remarks: source.remarks || '' }); await nextTick(); supplierSourceGuard.markClean(); supplierSourceDialogOpen.value = true }
const closeSupplierSourceDialog = requestSupplierSourceClose
async function saveSupplierSource() {
  if(supplierSourceSaving.value) return
  supplierSourceError.value = ''; toast.text = ''
  if (!can('suppliers', supplierSourceEditingId.value ? 'update' : 'create')) return
  if (!optionLoaded.suppliers || optionErrors.suppliers) return notify('供应商资料尚未加载，请重试后再保存。', true)
  if (!editingId.value || !supplierSourceForm.supplier || !supplierSourceForm.supplier_sku_code.trim()) { supplierSourceError.value = '请选择供应商并填写供应商 SKU 编码。'; return }
  supplierSourceSaving.value = true
  try {
    const characteristics = {}
    for (const line of supplierTraitsText.value.split('\n').filter(v=>v.trim())) { const parts = line.split(/[:：]/); const key = parts.shift().trim(); if (!key || !parts.length) throw new Error('供货特点请每行填写：名称：内容'); characteristics[key] = parts.join('：').trim() }
    const payload = { ...supplierSourceForm, characteristics, sku: Number(editingId.value), supplier: Number(supplierSourceForm.supplier), purchase_price: Number(supplierSourceForm.purchase_price || 0), moq: Number(supplierSourceForm.moq || 0), lead_time_days: Number(supplierSourceForm.lead_time_days || 0), is_active: Boolean(supplierSourceForm.is_active), is_preferred: Boolean(supplierSourceForm.is_preferred) }
    if (supplierSourceEditingId.value) await api.patch(`/supplier-skus/${supplierSourceEditingId.value}/`, payload)
    else await api.post('/supplier-skus/', payload)
    supplierSourceGuard.markClean()
    supplierSourceDialogOpen.value = false
    await loadSupplierSources(editingId.value)
    detailRefresh.value++; notify('供应商 SKU 来源已保存')
  } catch (error) { supplierSourceError.value = /supplier, supplier_sku_code/.test(apiErrorMessage(error)) ? '该供应商已使用这个来源编码，请修改编码后重试。' : apiErrorMessage(error); notify(supplierSourceError.value, true) } finally { supplierSourceSaving.value = false }
}
async function setSupplierSourcePreferred(source) {
  if (!can('suppliers', 'update')) return
  try { await api.post(`/supplier-skus/${source.id}/set-preferred/`); await loadSupplierSources(editingId.value); notify('已设为该 SKU 的首选供应来源') } catch (error) { notify(error.message, true) }
}
async function toggleSupplierSource(source) {
  if (!can('suppliers', 'update')) return
  if (source.is_active && !await confirmDialog({ title: '停用供应来源', message: '停用后不再作为新的可用供应来源，已有采购记录及快照保留。', confirmText: '确认停用', danger: true })) return
  try { await api.patch(`/supplier-skus/${source.id}/`, { is_active: !source.is_active, is_preferred: false }); await loadSupplierSources(editingId.value); notify(source.is_active ? '供应商 SKU 来源已停用' : '供应商 SKU 来源已启用') } catch (error) { notify(error.message, true) }
}
async function verifySkuCost() {
  if (!editingId.value || !can('purchases', 'update')) return
  if (skuCostNeedsSave()) return notify('请先保存当前 SKU 成本价格和成本币种，再进行核实。', true)
  if (!Number.isFinite(Number(form.cost_price)) || Number(form.cost_price) <= 0 || !String(form.cost_currency || '').trim()) return notify('SKU 内部成本必须大于 0 且成本币种已维护后才能核实。', true)
  try {
    const response = await api.post(`/skus/${editingId.value}/verify-cost/`)
    Object.assign(form, { cost_price: response.data.cost_price == null ? form.cost_price : normalizeMoneyInput(response.data.cost_price), cost_currency: response.data.cost_currency || '' })
    setCostVerification(response.data)
    detailRefresh.value++
    notify('SKU 内部成本已重新核实')
  } catch (error) { notify(apiErrorMessage(error), true) }
}
async function verifySupplierSource(source) {
  if (!can('purchases', 'update')) return
  if (supplierCostNeedsSave(source)) return notify('请先保存当前供应商参考价和采购币种，再进行核实。', true)
  if (!Number.isFinite(Number(source.purchase_price)) || Number(source.purchase_price) <= 0 || !String(source.currency || '').trim()) return notify('采购参考价必须大于 0 且采购币种已维护后才能核实。', true)
  try {
    await api.post(`/supplier-skus/${source.id}/verify-price/`)
    await loadSupplierSources(editingId.value)
    notify('供应商参考采购价已重新核实')
  } catch (error) { notify(apiErrorMessage(error), true) }
}
function onProductChanged() {
  selectedCombinations.value = new Set()
  if (inheritedProduct.value) {
    form.product = Number(props.initialProduct || route.query.product)
    return
  }
  Object.keys(parameterValues).forEach(key => delete parameterValues[key])
  Object.keys(salesModelAbbreviations).forEach(key => delete salesModelAbbreviations[key])
  details.value = []
  resetBatchFillState()
  void loadAbbreviationSuggestions()
}
function packagingText(template) { return template.name || '未命名包装' }
function packagingSearchText(template) {
  const name = packagingText(template)
  const syllables = pinyin(name, { toneType: 'none', type: 'array' })
  return [name, syllables.join(''), syllables.map(syllable => syllable[0]).join('')].filter(Boolean).join(' ')
}
const packagingOptions = computed(() => packagingTemplates.value.map(template => ({ value: String(template.id), label: packagingText(template), searchText: packagingSearchText(template) })))
function matchingPackaging(detail) { const search = String(detail.packaging_query || '').trim().toLocaleLowerCase(); return packagingTemplates.value.filter(template => !search || packagingText(template).toLocaleLowerCase().includes(search)).slice(0, 8) }
function choosePackaging(detail, template) { detail.packaging_template = template.id; detail.packaging_query = packagingText(template); packagingPicker.value = '' }
function clearPackaging(detail) { detail.packaging_template = ''; detail.packaging_query = ''; packagingPicker.value = '' }
const batchParameterTags = computed(() => skuAttributes.value.flatMap(({ group, attribute }) => splitValues(parameterValues[parameterKey(group, attribute)]).map(value => ({
  id: `${parameterKey(group, attribute)}:${value}`,
  filterKey: parameterKey(group, attribute),
  value,
  label: `${attribute.name}：${formatParameterValue(attribute, value)}`,
  name: attribute.name,
  valueLabel: formatParameterValue(attribute, value),
}))))
const batchParameterGroups = computed(() => {
  const groups = new Map()
  for (const tag of batchParameterTags.value) {
    if (!groups.has(tag.filterKey)) groups.set(tag.filterKey, { key: tag.filterKey, name: tag.name, tags: [] })
    groups.get(tag.filterKey).tags.push(tag)
  }
  return [...groups.values()]
})
const filteredDetailPreviews = computed(() => {
  const modelQuery = batchSalesModelQuery.value.trim().toLocaleLowerCase()
  const tagFilters = Object.keys(batchTagFilters).map(id => batchParameterTags.value.find(tag => tag.id === id)).filter(Boolean).reduce((groups, tag) => {
    if (!groups[tag.filterKey]) groups[tag.filterKey] = []
    groups[tag.filterKey].push(tag.value)
    return groups
  }, {})
  return allPreviews.value.filter(preview => {
    if (modelQuery && ![preview.sales_model, preview.display_name_cn].some(value => String(value || '').toLocaleLowerCase().includes(modelQuery))) return false
    return Object.entries(tagFilters).every(([filterKey, values]) => values.includes(String(preview.parameterValuesForSku?.[filterKey] || '')))
  })
})
function isBatchTagActive(tag) { return Boolean(batchTagFilters[tag.id]) }
function toggleBatchTag(tag) {
  if (isBatchTagActive(tag)) delete batchTagFilters[tag.id]
  else batchTagFilters[tag.id] = true
}
function clearBatchFilters() {
  batchSalesModelQuery.value = ''
  Object.keys(batchTagFilters).forEach(key => delete batchTagFilters[key])
}
function resetBatchFillState() {
  clearBatchFilters()
  clearBatchFillInputs()
  batchFillHistory.value = []
  batchFillBaseline.clear()
}
function clearBatchFillInputs() {
  batchPackagingTemplate.value = ''
  Object.keys(batchDetailFields).forEach(key => { batchDetailFields[key] = '' })
}
function detailSnapshot(detail) { return { packaging_template: detail.packaging_template, packaging_query: detail.packaging_query, unit: detail.unit, notes: detail.notes, unit_weight: detail.unit_weight, carton_quantity: detail.carton_quantity } }
function restoreDetailSnapshot(detail, snapshot) { Object.assign(detail, snapshot) }
function applyBatchPackaging() {
  const template = packagingTemplates.value.find(item => String(item.id) === String(batchPackagingTemplate.value))
  const enabledFields = Object.keys(batchDetailFields).filter(key => batchDetailFields[key] !== '')
  if (batchPackagingTemplate.value && !template) return notify('选择的包装不存在，请重新选择。', true)
  if (!template && !enabledFields.length) return notify('请选择包装，或填写至少一个需要批量填充的字段。', true)
  const targets = filteredDetailPreviews.value
  if (!targets.length) return notify('当前筛选没有匹配的 SKU，无法批量填充。', true)
  const changes = targets.map(preview => {
    const detail = detailFor(preview)
    const before = detailSnapshot(detail)
    if (!batchFillBaseline.has(preview.key)) batchFillBaseline.set(preview.key, before)
    if (template) choosePackaging(detail, template)
    enabledFields.forEach(field => {
      detail[field] = ['unit_weight', 'carton_quantity'].includes(field) ? Number(batchDetailFields[field] || 0) : batchDetailFields[field]
    })
    return { key: preview.key, before }
  })
  batchFillHistory.value.push(changes)
  clearBatchFillInputs()
  notify(`已为 ${changes.length} 个销售型号批量填充。`)
}
function undoBatchFill() {
  const changes = batchFillHistory.value.pop()
  if (!changes) return notify('没有可撤销的批量填充操作。', true)
  changes.forEach(change => {
    const detail = details.value.find(item => item.preview_key === change.key)
    if (detail) restoreDetailSnapshot(detail, change.before)
  })
  notify(`已撤销上一步对 ${changes.length} 个销售型号的填充。`)
}
function clearBatchFills() {
  if (!batchFillBaseline.size) return notify('当前没有可清空的批量填充数据。', true)
  batchFillBaseline.forEach((snapshot, key) => {
    const detail = details.value.find(item => item.preview_key === key)
    if (detail) restoreDetailSnapshot(detail, snapshot)
  })
  batchFillBaseline.clear()
  batchFillHistory.value = []
  notify('已清空本次全部批量填充数据。')
}
function cleanDetail(detail) { const { preview_key, packaging_template, packaging_query, ...stored } = detail; return stored }
function resetPackagingForm() { packagingSaveError.value=''; Object.assign(packagingForm, { name: '', supplier: '', carton_length: '', carton_width: '', carton_height: '', carton_tare_weight: 0, partial_carton_policy: 'SAME_CARTON', active: true, description: '' }) }
async function openPackagingCreate(target) { if (!can('packaging', 'create')) return; resetPackagingForm(); packagingTarget.value = target; await nextTick(); packagingGuard.markClean(); packagingDialogOpen.value = true }
function closePackagingPickerOnOutsideClick(event) { if (!event.target.closest?.('.packaging-picker')) packagingPicker.value = '' }
async function createPackaging() {
  if(packagingSaving.value)return
  packagingSaveError.value=''
  if (!can('packaging', 'create')) return
  if (!optionLoaded.suppliers || optionErrors.suppliers) return notify('供应商资料尚未加载，请重试后再保存。', true)
  packagingSaving.value = true
  try {
    const template = (await api.post('/packaging-templates/', { ...packagingForm, supplier: packagingForm.supplier || null })).data
    packagingTemplates.value.push(template)
    if (packagingTarget.value) choosePackaging(packagingTarget.value, template)
    packagingGuard.markClean()
    packagingDialogOpen.value = false
    packagingTarget.value = null
    resetPackagingForm()
  } catch (error) { packagingSaveError.value=packagingError(error) } finally { packagingSaving.value = false }
}
function packagingInput(detail) {
  if (!detail.packaging_template) return {}
  return { packaging_profile_input: { packaging_template: Number(detail.packaging_template), qty_per_carton_override: Number(detail.carton_quantity), unit_net_weight: Number(detail.unit_weight || 0) } }
}
async function openVersions(row) {
  versionsOpen.value = true; versionsLoading.value = true; versions.value = []; versionsError.value = ''; versionsRow.value = row
  try { versions.value = (await api.get(`/skus/${row.id}/versions/`)).data } catch (error) { versionsError.value = apiErrorMessage(error) } finally { versionsLoading.value = false }
}
const normalizedParameterValues = values => JSON.stringify(skuAttributes.value.map(({group,attribute}) => {
  const key = parameterKey(group,attribute)
  const aliases = [attribute.key.toLowerCase(), attribute.name.toLowerCase(), attribute.key.split('/')[0].toLowerCase()]
  const raw = values?.[key] ?? Object.entries(values || {}).find(([k]) => aliases.includes(k.split(':').at(-1).toLowerCase()))?.[1] ?? ''
  return [key.toLowerCase(), String(raw).trim().toLowerCase()]
}).sort(([a],[b])=>a.localeCompare(b)))
async function persistSave({ editingRow, editingPreview, parameterChanged, productChanged, identityChanged }) {
  saveError.value = ''
  if (!skuOptionsReady.value) { saveError.value = '产品、参数、包装或供应商资料未加载，请点“重新加载关联资料”后再保存。'; return false }
  saving.value = true
  const wasEditing = Boolean(editingId.value)
  try {
    const shared = { product: Number(form.product), unit: form.unit, currency: form.currency, default_price: Number(form.default_price || 0), active: form.active, sales_model_abbreviations: salesModelAbbreviations }
    if (typeof can === 'function' && can('purchases', 'update')) Object.assign(shared, { cost_price: Number(form.cost_price || 0), cost_currency: form.cost_currency || null })
    if (editingId.value) {
      const preview = editingPreview || allPreviews.value[0]
      const detail = detailFor(preview)
      const specification = parameterChanged || productChanged ? preview.specification : (editingRow?.specification || preview.specification)
      const parameters = parameterChanged || productChanged ? preview.parameterValuesForSku : { ...(editingRow?.parameter_values || preview.parameterValuesForSku), ...ordinaryValues() }
      const salesModel = form.sales_model || null
      const response = await api.put(`/skus/${editingId.value}/`, { ...shared, ...packagingInput(detail), sales_model: salesModel, description_cn: form.description_cn || preview.description_cn, description_en: translateLightingTerms(form.description_en || preview.description_en), specification, product_details: [cleanDetail(detail)], parameter_values: parameters, identity_change_confirmed: identityChanged })
      updateSavedRow(response.data)
      guard.markClean()
      try {
        if (imageClearRequested.value) await clearImage(editingId.value)
        else if (selectedImage.value) await uploadImage(editingId.value, selectedImage.value)
      } catch (error) {
        pendingImageSkuIds.value = [editingId.value]
        pendingImageFailurePrefix.value = imageClearRequested.value
          ? 'SKU 已更新，图片清除失败。请重试。'
          : 'SKU 已更新，图片上传失败。请重试。'
        await load()
        await nextTick(); guard.markClean()
        saveError.value = pendingImageFailurePrefix.value
        return false
      }
    } else {
      const previews = [...chosenPreviews.value]
      const payloads = previews.map(preview => {
        const detail = detailFor(preview)
        return { ...shared, ...packagingInput(detail), sales_model: null, description_cn: form.description_cn || preview.description_cn, description_en: translateLightingTerms(form.description_en || preview.description_en), specification: preview.specification, product_details: [cleanDetail(detail)], parameter_values: preview.parameterValuesForSku }
      })
      const created = (await api.post('/skus/batch-create/', { items: payloads })).data
      guard.markClean()
      const createdRows = created.map((row,index) => ({ row, detail: detailFor(previews[index]) }))
      if (selectedImage.value) {
        pendingImageSkuIds.value = createdRows.map(({ row }) => row.id)
        try { await uploadPendingImages() }
        catch (error) {
          pendingImageFailurePrefix.value = 'SKU 已创建，图片上传失败。请重试。'
          editingId.value = createdRows[0]?.row.id || null
          await load()
          await nextTick(); guard.markClean()
          saveError.value = pendingImageFailurePrefix.value
          return false
        }
      }
    }
    guard.markClean(); discardModal(); detailRefresh.value++; emit('saved'); notify(wasEditing ? 'SKU 已更新' : `已创建 ${chosenPreviews.value.length} 个 SKU`); await load()
    return true
  } catch (error) {
    reportSaveError(error, wasEditing ? '保存 SKU 失败：' : '创建 SKU 失败：')
    return false
  } finally { saving.value = false }
}
async function confirmIdentitySave() {
  if (!pendingIdentitySave.value || identityReviewSaving.value) return
  identityReviewError.value = ''
  identityReviewSaving.value = true
  try {
    const saved = await persistSave(pendingIdentitySave.value)
    if (saved) { pendingIdentitySave.value = null; identityReviewOpen.value = false }
    else identityReviewError.value = saveError.value || '保存失败，请处理提示后重试。'
  } finally { identityReviewSaving.value = false }
}
function cancelIdentitySave() { if(identityReviewSaving.value || saving.value) return; identityReviewOpen.value = false; identityReviewError.value = ''; pendingIdentitySave.value = null }
async function save() {
  if(saving.value || identityReviewSaving.value) return
  toast.text = ''
  if(!editingId.value && duplicateInputKeys.value.size) { saveError.value = '参数值存在重复，生成前请移除重复值。'; return }
  if (!can('skus', editingId.value ? 'update' : 'create')) return
  if (!skuOptionsReady.value) { saveError.value = '产品、参数、包装或供应商资料未加载，请点“重新加载关联资料”后再保存。'; return }
  if (!editingId.value && combinationRulesDirty.value) return notify("请先保存 SKU 组合规则，再创建 SKU。", true)
  saveError.value = ''
  if (pendingImageSkuIds.value.length) {
    if (!imageClearRequested.value && !selectedImage.value) {
      saveError.value = '请选择图片后重试，或取消本次编辑。'
      return
    }
    saving.value = true
    try {
      if (imageClearRequested.value) await clearImage(pendingImageSkuIds.value[0])
      else await uploadPendingImages()
      const message = imageClearRequested.value ? 'SKU 图片已清除' : 'SKU 图片已上传'
      pendingImageSkuIds.value = []
      guard.markClean(); discardModal(); detailRefresh.value++; emit('saved'); notify(message); await load()
    } catch { saveError.value = pendingImageFailurePrefix.value } finally { saving.value = false }
    return
  }
  if (!form.product) return notify('请选择所属产品。', true)
  const missingRequired = skuAttributes.value
    .filter(({ group, attribute }) => attribute.required && !splitValues(parameterValues[parameterKey(group, attribute)]).length)
    .map(({ attribute }) => attribute.name)
  if (missingRequired.length) return notify(`请填写必填参数：${[...new Set(missingRequired)].join('、')}。`, true)
  if (!allPreviews.value.length) return notify('请至少填写一个用于 SKU 或 Sales Model 的参数值。', true)
  const editingRow = editingId.value ? rows.value.find(row => Number(row.id) === Number(editingId.value)) : null
  if (editingId.value && allPreviews.value.length !== 1) return notify('编辑已有 SKU 时只能保留一个参数组合。', true)
  const editingPreview = editingId.value ? allPreviews.value[0] : null
  const parameterChanged = Boolean(editingRow && editingPreview && normalizedParameterValues(editingRow.parameter_values) !== normalizedParameterValues(editingPreview.parameterValuesForSku))
  const productChanged = Boolean(editingRow && Number(editingRow.product) !== Number(form.product))
  const salesModelChanged = Boolean(editingRow && String(editingRow.sales_model || '') !== String(form.sales_model || ''))
  const identityChanged = parameterChanged || productChanged || salesModelChanged
  if (!editingId.value && !chosenPreviews.value.length) return notify('请勾选至少一个尚未创建的组合。', true)
  const pending = { editingRow, editingPreview, parameterChanged, productChanged, identityChanged }
  if (identityChanged) {
    pendingIdentitySave.value = pending
    identityReviewError.value = ''
    identityReviewOpen.value = true
    return
  }
  await persistSave(pending)
}
async function deactivateRow(row) { if (!can('skus', 'update') || !await confirmDialog({ title: '确认停用 SKU', message: `确定停用 SKU “${row.display_name_cn || row.sku_code || row.sku}”吗？停用后会保留历史记录。`, confirmText: '确认停用', danger: true })) return; try { await api.patch(`/skus/${row.id}/`, { active: false }); await load(); notify('SKU 已停用') } catch (error) { notify(apiErrorMessage(error), true) } }
watch(() => form.unit, value => details.value.forEach(detail => { detail.unit = value || 'pcs' }))
watch(() => form.description_en, value => {
  const translated = translateLightingTerms(value)
  if (translated !== value) form.description_en = translated
})
watch(() => form.product, () => { void loadAbbreviationSuggestions() })
watch(parameterValues, applyAbbreviationSuggestions, { deep: true })
watch(allPreviews, syncDetails, { immediate: true })
onMounted(async () => {
  if (!workspace || workspace.active) document.addEventListener('pointerdown', closePackagingPickerOnOutsideClick)
  await Promise.all([load(), loadSkuReferenceOptions()])
  if (props.embedded) openCreate(props.initialProduct)
  else { openCreateFromRoute(); await openEditFromRoute() }
})
async function openEditFromRoute(){if(props.embedded||!route.query.edit||!can('skus','update'))return;const id=Number(route.query.edit);if(!Number.isSafeInteger(id)||id<=0)return;try{await openEdit(rows.value.find(row=>row.id===id)||(await api.get(`/skus/${id}/`)).data)}catch(error){notify(apiErrorMessage(error),true)}}
watch(()=>route.query.edit,()=>{if(hasLoaded.value)void openEditFromRoute()})
watch([() => route.query.create, () => route.query.product], ([value]) => {
  if (props.embedded) return
  if (value === '1') openCreateFromRoute()
  else if (routeCreateOpen.value) {
    routeCreateOpen.value = false
    closeModal()
  }
})
watch(() => workspace?.active, active => { document.removeEventListener('pointerdown', closePackagingPickerOnOutsideClick); if (active) document.addEventListener('pointerdown', closePackagingPickerOnOutsideClick) })
onBeforeUnmount(() => { supplierSourcesVersion++; loadVersion++; document.removeEventListener('pointerdown', closePackagingPickerOnOutsideClick); revokeImagePreview() })
</script>

<template>
  <div :class="{ 'has-inherited-product': inheritedProduct, 'inline-sku-editor': inline }">
    <div v-if="abbreviationGuideOpen" class="modal-backdrop abbreviation-guide-backdrop"><section class="modal abbreviation-guide-modal"><div class="modal-head"><div><h3>通用参数值缩写表</h3><p>默认缩写会自动带入；手动修改后不会被系统覆盖。</p></div><button type="button" class="mini-btn" @click="abbreviationGuideOpen=false"><X :size="17" /></button></div><div class="modal-body abbreviation-guide-body"><p>缩写允许 1–8 位英文字母、数字或连字符，均会自动转为大写。</p><section v-for="group in abbreviationReferenceGroups" :key="group.title" class="abbreviation-reference-group"><h4>{{ group.title }}</h4><table><thead><tr><th>参数值 / 别名</th><th>系统默认缩写</th></tr></thead><tbody><tr v-for="row in group.rows" :key="row[0]"><td>{{ row[0] }}</td><td><code>{{ row[1] }}</code></td></tr></tbody></table></section></div></section></div>
    <template v-if="!embedded">
    <div class="page-head"><div><h2>SKU 管理</h2><p>为产品添加可报价、可下单的 SKU，并维护对应规格。</p></div><button v-if="can('skus', 'create')" class="btn btn-primary" @click="openCreate"><Plus :size="16" /> 新建 SKU</button></div>
    <SummaryCards v-if="hasLoaded" :items="skuMetrics" />
    <div class="toolbar sku-list-filters"><div class="search-box"><Search :size="17" /><input v-model="query" aria-label="搜索 SKU" placeholder="SKU Code、Sales Model、名称或规格" @keydown.enter="applyListFilters" /></div><select v-model="productFilter" aria-label="SKU 所属产品" @change="applyListFilters"><option value="">全部产品</option><option v-for="item in products" :key="item.id" :value="String(item.id)">{{ item.code }} · {{ item.name }}</option></select><select v-model="statusFilter" aria-label="SKU 状态" @change="applyListFilters"><option value="">全部状态</option><option value="active">启用</option><option value="inactive">停用</option></select><button class="btn btn-primary" @click="applyListFilters">查询</button><button class="btn btn-secondary" @click="clearSkuFilters">重置</button><button class="btn btn-secondary" :disabled="loading" @click="load">刷新</button></div>
    <div v-if="Object.keys(optionErrors).length" class="sku-load-error" role="alert"><p v-for="(message,key) in optionErrors" :key="key">{{ message }}</p><button type="button" @click="loadSkuReferenceOptions">重新加载关联资料</button></div>
      <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="loadError" @retry="load" /><section class="panel" v-if="hasLoaded"><div v-if="loading && !hasLoaded" class="loading"><div class="spinner" /></div><ListEmptyState v-else-if="!visibleRows.length" entity="SKU" :filtered="filteredSkuEmpty" @clear="clearSkuFilters"><template #action><p v-if="can('skus', 'create')">选择“新建 SKU”，为产品添加销售规格。</p></template></ListEmptyState><div v-else class="table-wrap"><table class="data-table sku-list-table"><thead><tr><th>内部识别名称</th><th>对外型号 / Sales Model</th><th>分类信息</th><th>状态</th><th>报价次数</th><th>订单次数</th><th>图片</th><th>库存</th><th>单位</th><th>默认售价</th><th /></tr></thead><tbody><tr v-for="row in visibleRows" :key="row.id" class="sku-data-row" tabindex="0" @click="openDetail(row)" @keydown.enter="openDetail(row)"><td class="primary-cell"><strong>{{ row.display_name_cn || row.product_name }}</strong><small class="sku-code-hint">SKU Code：{{ row.sku_code || row.sku }}</small><small v-if="row.historical_matches?.length" class="history-hit">命中历史：{{ row.historical_matches.map(item => item.display_name_cn_snapshot || item.sales_model_snapshot).filter(Boolean).join('、') }}</small></td><td><span v-if="row.sales_model">{{ row.sales_model }}</span><span v-else class="muted">未设置</span></td><td class="category-cell">{{ row.category_names?.join('、') || '未分类' }}</td><td><span :class="['status-tag', { inactive: !row.active }]">{{ row.status_label || (row.active ? '启用' : '停用') }}</span></td><td>{{ row.quote_count || 0 }}</td><td>{{ row.order_count || 0 }}</td><td><img v-if="row.image_thumbnail" class="sku-table-thumbnail" :src="row.image_thumbnail" loading="lazy" decoding="async" width="42" height="42" :alt="`${row.display_name_cn || row.sku} 图片`" /><span v-else class="sku-image-empty">—</span></td><td>{{ row.stock_quantity }}</td><td>{{ row.unit }}</td><td>{{ formatMoney(row.default_price) }} {{ row.currency }}</td><td><div class="table-actions"><button class="mini-btn" title="历史版本" @click.stop="openVersions(row)"><History :size="14" /></button><button v-if="can('skus', 'update')" class="mini-btn" title="编辑" @click.stop="openEdit(row)"><Pencil :size="14" /></button><button v-if="row.active && can('skus', 'update')" class="mini-btn danger" title="停用" @click.stop="deactivateRow(row)"><Trash2 :size="14" /></button></div></td></tr></tbody></table></div></section>

    </template>
    <Teleport to="body" :disabled="workspaceTeleportDisabled || inline || !embedded"><div v-if="(modalOpen || route.query.create === '1') && can('skus', editingId ? 'update' : 'create')" class="modal-backdrop" :class="{ 'inline-sku-backdrop': inline }"><form class="modal sku-modal" role="dialog" aria-modal="true" :aria-label="editingId ? '编辑 SKU' : '新建 SKU'" :class="{ 'sku-create-layout': !editingId }" @submit.prevent="save"><div class="modal-head"><div><h3>{{ editingId ? '编辑 SKU' : '新建 SKU' }}</h3><p>参数按产品所属分类自动带入；每个值输入后按回车确认。</p></div><div class="sku-header-actions"><button v-if="!editingId" type="button" class="btn btn-secondary" :disabled="saving || identityReviewSaving || supplierSourceSaving" @click="closeModal">取消</button><button v-if="!editingId && can('skus', 'create')" class="btn btn-primary" :disabled="saving || !skuOptionsReady || (!editingId && combinationRulesDirty)">{{ saving ? '保存中…' : pendingImageSkuIds.length ? (imageClearRequested ? '重试清除图片' : '重试上传图片') : '保存并创建' }}</button><button type="button" class="mini-btn" :disabled="saving || identityReviewSaving || supplierSourceSaving" aria-label="关闭 SKU 窗口" @click="closeModal"><X :size="17" /></button></div></div><p v-if="saveError" class="sku-save-error" role="alert">{{ saveError }}</p><div v-if="Object.keys(optionErrors).length" class="sku-save-error" role="alert"><p v-for="(message,key) in optionErrors" :key="key">{{ message }}</p><button type="button" class="btn btn-secondary" @click="loadSkuReferenceOptions">重新加载关联资料</button></div>
    <div class="sku-editor-layout"><aside v-if="!editingId" class="sku-step-sidebar"><nav aria-label="新建 SKU 步骤"><button v-for="step in editorSteps" :key="step.number" type="button" :class="{ active: editorStep === step.number }" :aria-current="editorStep === step.number ? 'step' : undefined" @click="goToEditorStep(step.number)"><span class="step-dot">{{ step.number }}</span><span><strong>{{ step.title }}</strong><small>{{ step.hint }}</small></span></button></nav><div class="sku-step-help"><strong>ⓘ 操作提示</strong><p>带 * 为必填项；<br />参数值输入后按回车确认；<br />勾选需要创建的实际组合。</p></div></aside>
    <div ref="editorBody" class="modal-body sku-body" :inert="saving || identityReviewSaving" @scroll.passive="trackEditorStep">
    <section class="sku-basic-card" data-sku-step="1"><div v-if="!editingId" class="section-title"><div class="sku-card-heading"><span class="step-dot">1</span><h4>基本信息</h4><small>SKU Basic Information</small></div></div>
       <section class="sku-basics"><div v-if="editingId" class="field"><label>SKU Code</label><input :value="form.sku" readonly /></div><div class="field"><label>所属产品 <em>*</em></label><select v-model="form.product" :disabled="inheritedProduct" required @change="onProductChanged"><option value="">请选择产品</option><option v-for="item in products" :key="item.id" :value="item.id">{{ item.name }}</option></select></div><div class="field"><label>销售型号前缀</label><input :value="product?.sales_model_prefix || ''" placeholder="请先在产品中设置" readonly /><small class="field-help">用于自动生成 Sales Model。</small></div><div v-if="editingId" class="field sales-model-field"><label>Sales Model</label><input v-model.trim="form.sales_model" placeholder="修改后将保存历史型号" /><small v-if="rows.find(row => row.id === editingId)?.quote_count || rows.find(row => row.id === editingId)?.order_count" class="field-help warning">该 SKU 已有报价或订单引用；保存会保留历史版本，历史单据不变。</small></div><div class="field"><label>单位</label><input v-model.trim="form.unit" placeholder="如：pcs" /></div><div class="field sku-price-field"><label>默认售价</label><input v-model="form.default_price" type="number" min="0" step="any" @blur="form.default_price = normalizeMoneyInput(form.default_price)" /></div><div class="field sku-currency"><label>销售币种</label><select v-model="form.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div><template v-if="can('purchases', 'view')"><div class="field sku-cost-field"><label>内部成本</label><input v-model="form.cost_price" type="number" min="0" step="any" @blur="form.cost_price = normalizeMoneyInput(form.cost_price)" /><small class="field-help">{{ verificationText(costVerification.state) }} · {{ verificationDate(costVerification.verifiedAt) }}{{ costVerification.verifiedBy ? ` · ${costVerification.verifiedBy}` : '' }}</small></div><div class="field sku-cost-currency"><label>成本币种</label><select v-model="form.cost_currency"><option value="">历史币种未知</option><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div><div class="cost-verification-actions"><button v-if="can('purchases', 'update') && editingId" type="button" class="text-btn" @click="verifySkuCost">确认价格仍有效</button></div></template><label class="check-field sku-active"><input v-model="form.active" type="checkbox" /> 启用</label><div class="description-fields"><div class="field"><label>中文描述</label><textarea v-model.trim="form.description_cn" placeholder="留空则按产品与属性生成" /></div><div class="field"><label>英文描述</label><textarea v-model.trim="form.description_en" placeholder="留空则按产品与属性生成" /></div></div><div class="sku-image-picker"><input ref="imageInput" type="file" accept="image/gif,image/jpeg,image/png,image/webp,.gif,.jpg,.jpeg,.png,.webp" hidden @change="onImageSelected" /><img v-if="imagePreviewUrl" class="sku-image-preview" :src="imagePreviewUrl" alt="SKU 图片预览" /><div v-else class="sku-image-placeholder">暂无图片</div><div class="sku-image-actions"><button type="button" class="btn btn-secondary" @click="chooseImage">选择图片</button><button v-if="selectedImage || imagePreviewUrl" type="button" class="btn btn-secondary" @click="clearImageSelection">清除</button></div></div></section></section>
<section v-if="editingId" class="sku-packaging-section"><h4>交易单位与包装规格</h4><p>基础单位：{{ form.unit }}。交易规格与装箱模板不会自动改变基础单位。</p><p v-if="editingPackaging">当前已保存包装：{{ editingPackaging.template_name || '未关联模板' }} · {{ packagingStatusLabels[editingPackaging.status] || editingPackaging.status }}。模板或有效包装参数变化后需重新验证。</p><RouterLink class="btn btn-secondary" :to="tradeUnitsLocation()">管理此 SKU 的交易单位</RouterLink></section><section v-if="editingId" class="supplier-sources-section"><div class="section-title"><div><small>供应商映射</small><h4>供应来源</h4></div><button v-if="can('suppliers', 'create')" type="button" class="btn btn-secondary supplier-add-btn" @click="openSupplierSourceCreate"><Plus :size="15" /> 添加供应商来源</button></div><p class="rule-hint">同一 SKU 可配置多个供应来源。候选供应商不等于实际采购供应商，采购时仍需选定具体来源；历史采购行保留快照。</p><div v-if="supplierSourcesLoading" class="section-empty">加载供应商来源中…</div><div v-else-if="supplierSourcesError" class="section-empty" role="alert">{{ supplierSourcesError }} <button type="button" @click="loadSupplierSources(editingId)">重新加载</button></div><div v-else-if="!supplierSources.length" class="section-empty">尚未配置供应商来源。</div><div v-else class="supplier-source-table-wrap"><table class="supplier-source-table"><thead><tr><th>供应商</th><th>供应商型号 / Code</th><th>采购参考价</th><th>MOQ / 交期</th><th>状态</th><th /></tr></thead><tbody><tr v-for="source in supplierSources" :key="source.id"><td><strong>{{ source.supplier_name }}</strong><small v-if="source.supplier_product_name">{{ source.supplier_product_name }}</small></td><td><strong>{{ source.supplier_model || '—' }}</strong><small>{{ source.supplier_sku_code }}</small><small v-if="source.supplier_barcode">条码：{{ source.supplier_barcode }}</small></td><td><template v-if="can('purchases', 'view')"><strong v-if="source.purchase_price != null">{{ formatMoney(source.purchase_price) }} {{ source.currency }}</strong><strong v-else>采购价已隐藏</strong><small>{{ verificationText(source.purchase_price_verification_state) }} · {{ verificationDate(source.purchase_price_verified_at) }}{{ source.purchase_price_verified_by_name ? ` · ${source.purchase_price_verified_by_name}` : '' }}</small></template><span v-else>采购价已隐藏</span></td><td>{{ source.moq || '未设 MOQ' }} / {{ source.lead_time_days || 0 }} 天</td><td><span :class="['status-tag', { inactive: !source.is_active }]">{{ source.is_active ? '启用' : '停用' }}</span><span v-if="source.is_preferred" class="preferred-tag">首选</span></td><td><div class="table-actions"><button v-if="can('purchases', 'update')" type="button" class="text-btn" @click="verifySupplierSource(source)">确认价格仍有效</button><button v-if="can('suppliers', 'update')" type="button" class="mini-btn" title="编辑" @click="openSupplierSourceEdit(source)"><Pencil :size="14" /></button><button v-if="can('suppliers', 'update') && !source.is_preferred && source.is_active" type="button" class="text-btn" @click="setSupplierSourcePreferred(source)">设为首选</button><button v-if="can('suppliers', 'update')" type="button" class="text-btn" @click="toggleSupplierSource(source)">{{ source.is_active ? '停用' : '启用' }}</button></div></td></tr></tbody></table></div></section>
      <details v-if="compactCreate" class="sku-more-settings">
        <summary>更多设置 <span>单位：{{ form.unit }} · 币种：{{ form.currency }}</span></summary>
        <p class="rule-hint">默认沿用当前产品的单位和币种；新 SKU 默认启用。描述自动生成，图片可在创建后进入 SKU 档案设置。</p>
        <div class="sku-basics">
          <div class="field"><label>单位</label><input v-model.trim="form.unit" placeholder="如：pcs" /></div>
          <div class="field"><label>币种</label><select v-model="form.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
        </div>
      </details>
      <section v-if="product" class="parameter-section" data-sku-step="2"><div class="section-title"><div class="sku-card-heading"><span v-if="!editingId" class="step-dot">2</span><h4>参数配置</h4><small>SKU Parameters</small></div><button type="button" class="sku-section-help" @click="abbreviationGuideOpen = true">参数配置说明 ⓘ</button></div><p v-if="skuAttributes.length" class="rule-hint">展示“生成中文SKU”或“生成销售型号”的属性；自动大写规则将自动应用。</p><div v-if="skuAttributes.length" class="parameter-search"><label>查找参数<input v-model="parameterSearch" aria-label="查找 SKU 参数" placeholder="参数名称、分类或编码" /></label><span>筛选只影响展示，已填写的参数仍保留。</span></div><p v-if="parameterSearch && !visibleCategoryGroups.length" class="section-empty">没有匹配的参数，请修改关键词。</p><div v-if="!skuAttributes.length" class="section-empty">该产品的分类尚未配置生成中文SKU或生成销售型号参数，请先在产品分类中配置。</div><div v-for="group in visibleCategoryGroups" :key="group.id" class="parameter-group"><h5>{{ group.name }}</h5><div v-if="group.attributes.length" class="parameter-grid"><div v-for="attribute in group.attributes" :key="attribute.key" class="parameter-cell"><label>{{ attribute.name }}<em v-if="attribute.required">*</em><small v-if="attribute.unit">（{{ attribute.unit }}）</small></label><ComboInput v-model="parameterValues[parameterKey(group, attribute)]" :label="attribute.name" :options="optionsFor(group, attribute)" :uppercase="attribute.uppercase" :placeholder="`输入${attribute.name}后按回车确认`" multiple /><div class="parameter-history" aria-label="历史保存的参数值"><div v-if="optionsFor(group, attribute, false).length" class="parameter-history-values"><button v-for="option in optionsFor(group, attribute, false)" :key="option.value" type="button" @click="useHistoricalValue(group, attribute, option.value)">{{ option.label }}</button></div><small v-else>暂无历史保存值</small></div><div v-if="attribute.include_in_sales_model && splitValues(parameterValues[parameterKey(group, attribute)]).length" class="abbreviation-list"><div class="abbreviation-heading"><span>型号缩写</span><button type="button" class="abbreviation-help-button" title="查看通用参数缩写表" @click="abbreviationGuideOpen = true">?</button></div><label v-for="value in splitValues(parameterValues[parameterKey(group, attribute)])" :key="value" class="abbreviation-input"><span class="abbreviation-value">{{ value }} <i aria-hidden="true">→</i></span><input :aria-label="`${value} 的型号缩写`" v-model.trim="salesModelAbbreviations[abbreviationKey(group, attribute, value)]" maxlength="8" pattern="[A-Za-z0-9-]{1,8}" placeholder="如 BL" @input="salesModelAbbreviations[abbreviationKey(group, attribute, value)] = String(salesModelAbbreviations[abbreviationKey(group, attribute, value)] || '').replace(/[^a-zA-Z0-9-]/g, '').toUpperCase()" /><button type="button" class="default-abbreviation-btn" :disabled="!suggestedAbbreviation(group, attribute, value)" @click="applyDefaultAbbreviation(group, attribute, value)">默认值</button></label></div><p>按回车添加多个值</p></div></div><p v-else class="muted">本分类暂无生成中文SKU或生成销售型号参数。</p></div></section>
      <section v-if="ordinaryAttributes.length" class="ordinary-attributes-section"><div class="section-title"><h4>普通属性</h4></div><div class="ordinary-attributes-grid"><div v-for="a in ordinaryAttributes" :key="`${a.category_id || a.category || 0}:${a.key}`" class="field"><label>{{ a.name }}</label><input v-model="parameterValues[`${a.category_id || a.category || 0}:${a.key}`]" /></div></div></section><section v-if="product" class="preview-section" data-sku-step="3"><div class="section-title"><div><div class="sku-card-heading"><span v-if="!editingId" class="step-dot">3</span><h4>组合预览</h4><small>SKU Combinations Preview</small></div><p class="preview-hint">仅创建勾选的实际组合；不会自动创建所有理论组合。</p><p v-if="editingId && form.sales_model !== allPreviews[0]?.sales_model" class="preview-hint">当前保存型号：{{ form.sales_model || '未设置' }}。预览基于当前参数缩写；未修改身份参数或型号时，普通保存保留原型号。</p></div><span>{{ allPreviews.length }} 个组合 · {{ previewSummary }}</span></div><SkuCombinationRuleEditor v-if="!editingId" :key="form.product" :product-id="form.product" :definitions="ruleDefinitions" :saved-rules="product.combination_rules || []" :valid-count="allPreviews.length" :total-count="theoreticalPreviews.length" @dirty="combinationRulesDirty = $event" @preview="previewCombinationRules" @saved="savedCombinationRules" /><div v-if="!allPreviews.length" class="section-empty">暂无有效组合。请填写参数或检查组合规则；每次最多支持 1000 个理论组合。</div><div v-else class="preview-table-wrap"><table class="preview-table"><thead><tr><th v-if="!editingId">创建</th><th>Sales Model</th><th v-for="column in previewColumns" :key="column.key">{{ column.name }}</th></tr></thead><tbody><tr v-for="item in allPreviews" :key="item.key"><td v-if="!editingId"><input type="checkbox" :disabled="item.duplicate" :checked="!item.duplicate && selectedCombinations.has(item.key)" @change="chooseCombination(item.key,$event.target.checked)" /></td><td><span :class="{ 'duplicate-sku': item.duplicate }">{{ item.sales_model || '—' }}</span><span v-if="item.duplicate" class="duplicate-sku duplicate-sku-warning">已有相同 SKU，请使用现有记录</span></td><td v-for="column in previewColumns" :key="column.key">{{ item.attributeValues[column.key] || '—' }}</td></tr></tbody></table></div></section>
      <section v-if="product" class="detail-section" data-sku-step="4"><div class="section-title"><div class="sku-card-heading"><span v-if="!editingId" class="step-dot">4</span><h4>包装与发货信息</h4><small>Packaging &amp; Shipping（选填）</small></div><span>{{ allPreviews.length }} 个销售型号</span></div><div class="batch-fill-panel"><div class="batch-filter-row"><div class="batch-model-search"><label for="sku-batch-search">销售型号 / 中文 SKU 名称筛选</label><div class="batch-search-input"><input id="sku-batch-search" v-model.trim="batchSalesModelQuery" placeholder="模糊搜索型号或中文名称" /><button type="button" :disabled="!batchSalesModelQuery && !Object.keys(batchTagFilters).length" @click="clearBatchFilters">清空筛选</button></div></div><label class="batch-quantity-field">单个重量 KG<input v-model.number="batchDetailFields.unit_weight" type="number" min="0" step="0.001" placeholder="填写即参与" /></label><label class="batch-quantity-field">整件数量<input v-model.number="batchDetailFields.carton_quantity" type="number" min="0" placeholder="填写即参与" /></label><label class="batch-quantity-field">单位<input v-model.trim="batchDetailFields.unit" placeholder="如：pcs" /></label><label class="batch-notes-field">备注<input v-model.trim="batchDetailFields.notes" placeholder="批量备注" /></label><label class="batch-packaging-select">批量包装<ComboInput v-model="batchPackagingTemplate" :options="packagingOptions" :allow-custom="false" placeholder="搜索并选择包装名称" /></label><div class="batch-fill-actions"><button type="button" class="btn btn-primary" :disabled="!filteredDetailPreviews.length" @click="applyBatchPackaging">批量填充 {{ filteredDetailPreviews.length }} 项</button><button type="button" class="btn btn-secondary" :disabled="!batchFillHistory.length" @click="undoBatchFill">撤销上一步</button><button type="button" class="btn btn-secondary" :disabled="!batchFillHistory.length" @click="clearBatchFills">清空批量填充</button></div></div><div v-if="batchParameterGroups.length" class="batch-parameter-groups" aria-label="参数筛选"><fieldset v-for="group in batchParameterGroups" :key="group.key" class="batch-parameter-group"><legend>{{ group.name }}</legend><div><button v-for="tag in group.tags" :key="tag.id" type="button" :class="['parameter-filter-tag', { active: isBatchTagActive(tag) }]" :aria-label="tag.label" :aria-pressed="isBatchTagActive(tag)" @click="toggleBatchTag(tag)">{{ tag.valueLabel }}</button></div></fieldset></div><p class="batch-fill-hint">销售型号、中文 SKU 名称和参数标签可单独或组合筛选；已填写的字段直接参与批量填充，留空则保留原值。</p></div><div v-if="!filteredDetailPreviews.length" class="section-empty">没有匹配当前筛选条件的销售型号。</div><div v-else class="detail-scroll"><div v-for="(preview, index) in filteredDetailPreviews" :key="preview.key" class="detail-row"><div class="detail-index">{{ index + 1 }}</div><label>中文 SKU 名称<input :value="preview.display_name_cn" readonly /></label><label>销售型号<input :value="preview.sales_model" :class="{ 'duplicate-sku': preview.duplicate }" readonly /></label><label>单位<input v-model.trim="detailFor(preview).unit" /></label><label>备注<input v-model.trim="detailFor(preview).notes" /></label><label>单个重量 KG<input v-model.number="detailFor(preview).unit_weight" type="number" min="0" step="0.001" /></label><label>整件数量<input v-model.number="detailFor(preview).carton_quantity" type="number" min="0" /></label><div class="packaging-cell"><label>包装信息</label><div class="packaging-picker"><input v-model.trim="detailFor(preview).packaging_query" placeholder="未配置，输入任意文字搜索" @focus="packagingPicker = preview.key" @input="detailFor(preview).packaging_template = ''" /><div v-if="packagingPicker === preview.key" class="packaging-options"><button v-if="detailFor(preview).packaging_template || detailFor(preview).packaging_query" type="button" @click="clearPackaging(detailFor(preview))">清除选择</button><button v-for="template in matchingPackaging(detailFor(preview))" :key="template.id" type="button" @click="choosePackaging(detailFor(preview), template)">{{ packagingText(template) }}</button><button v-if="can('packaging', 'create')" type="button" class="create-packaging" @click="openPackagingCreate(detailFor(preview))">＋ 新建包装</button></div></div></div></div></div></section>
    <section class="sku-finish-card" data-sku-step="5"><div v-if="!editingId" class="sku-card-heading"><span class="step-dot">5</span><h4>确认并保存</h4><small>已选 {{ chosenPreviews.length }} 个组合</small></div><div class="modal-foot"><button type="button" class="btn btn-secondary" :disabled="saving || identityReviewSaving || supplierSourceSaving" @click="closeModal">取消</button><button v-if="can('skus', editingId ? 'update' : 'create')" class="btn btn-primary" :disabled="saving || (!editingId && combinationRulesDirty)">{{ saving ? '保存中...' : pendingImageSkuIds.length ? (imageClearRequested ? '重试清除图片' : '重试上传图片') : editingId ? '保存 SKU' : `创建 ${chosenPreviews.length} 个 SKU` }}</button></div></section>
    </div></div></form></div></Teleport>
    <Teleport to="body" :disabled="workspaceTeleportDisabled"><div v-if="identityReviewOpen" class="modal-backdrop identity-review-backdrop"><section class="modal identity-review-modal"><div class="modal-head"><div><h3>确认 SKU 身份更新</h3><p>系统将保留 SKU Code，并把旧名称和型号保存到历史记录；历史报价、订单和库存单据不会被改写。</p></div><button type="button" class="mini-btn" @click="cancelIdentitySave"><X :size="17" /></button></div><div class="modal-body"><div class="identity-review-grid"><div class="identity-review-label">内部中文名称</div><div class="identity-review-old"><small>修改前</small><p><span v-for="(segment,index) in diffSegments(identityReview.oldName, identityReview.newName, 'old')" :key="`old-name-${index}`" :class="{ 'diff-removed': segment.changed }">{{ segment.text }}</span></p></div><div class="identity-review-new"><small>修改后</small><p><span v-for="(segment,index) in diffSegments(identityReview.oldName, identityReview.newName)" :key="`new-name-${index}`" :class="{ 'diff-added': segment.changed }">{{ segment.text }}</span></p></div><div class="identity-review-label">Sales Model</div><div class="identity-review-old"><small>修改前</small><p><span v-for="(segment,index) in diffSegments(identityReview.oldModel, identityReview.newModel, 'old')" :key="`old-model-${index}`" :class="{ 'diff-removed': segment.changed }">{{ segment.text }}</span></p></div><div class="identity-review-new"><small>修改后</small><p><span v-for="(segment,index) in diffSegments(identityReview.oldModel, identityReview.newModel)" :key="`new-model-${index}`" :class="{ 'diff-added': segment.changed }">{{ segment.text }}</span></p></div></div><p v-if="identityReviewError" class="sku-save-error" role="alert">{{ identityReviewError }}</p><p class="identity-review-hint">确认后系统会再次检查中文名称、Sales Model 和参数组合是否与其他 SKU 重复；发现重复时不会保存。</p></div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="cancelIdentitySave">取消</button><button type="button" class="btn btn-primary" :disabled="identityReviewSaving" @click="confirmIdentitySave">{{ identityReviewSaving ? '检查并保存中…' : '确认并保存' }}</button></div></section></div></Teleport>
    <div v-if="supplierSourceDialogOpen && can('suppliers', supplierSourceEditingId ? 'update' : 'create')" class="modal-backdrop supplier-source-backdrop"><form class="modal supplier-source-modal" role="dialog" aria-modal="true" :aria-label="supplierSourceEditingId ? '编辑供应商来源' : '添加供应商来源'" @submit.prevent="saveSupplierSource"><div class="modal-head"><div><h3>{{ supplierSourceEditingId ? '编辑供应商来源' : '添加供应商来源' }}</h3><p>供应商型号与内部 SKU 分离保存；同一供应商的来源编码不能重复。</p></div><button type="button" class="mini-btn" :disabled="supplierSourceSaving" aria-label="关闭供应来源表单" @click="closeSupplierSourceDialog"><X :size="17" /></button></div><div class="modal-body supplier-source-form" :inert="supplierSourceSaving"><p v-if="supplierSourceError" class="sku-save-error" role="alert">{{ supplierSourceError }}</p><p v-if="optionErrors.suppliers" class="option-load-error" role="alert">{{ optionErrors.suppliers }} <button type="button" @click="loadSkuReferenceOptions">重新加载</button></p><label>供应商 <em>*</em><select v-model="supplierSourceForm.supplier" required><option value="">选择供应商</option><option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">{{ supplier.name }}</option></select></label><label>供应商 SKU Code <em>*</em><input v-model.trim="supplierSourceForm.supplier_sku_code" required maxlength="100" /></label><label>供应商型号<input v-model.trim="supplierSourceForm.supplier_model" maxlength="120" /></label><label>供应商产品名称<input v-model.trim="supplierSourceForm.supplier_product_name" maxlength="200" /></label><label>供应商条码<input v-model.trim="supplierSourceForm.supplier_barcode" maxlength="100" /></label><label>参考采购价<input v-model="supplierSourceForm.purchase_price" type="number" min="0" step="any" @blur="supplierSourceForm.purchase_price = normalizeMoneyInput(supplierSourceForm.purchase_price)" /></label><label>币种<select v-model="supplierSourceForm.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></label><label>MOQ<input v-model.number="supplierSourceForm.moq" type="number" min="0" step="0.01" /></label><label>交期（天）<input v-model.number="supplierSourceForm.lead_time_days" type="number" min="0" step="1" /></label><label class="check-field"><input v-model="supplierSourceForm.is_active" type="checkbox" /> 启用</label><label class="check-field"><input v-model="supplierSourceForm.is_preferred" type="checkbox" /> 设为该 SKU 首选来源</label><label class="full-description">供货特点<textarea v-model="supplierTraitsText" placeholder="PCB：白色&#10;背胶：3M&#10;包装：10米/卷" /></label><label class="full-description">备注<textarea v-model.trim="supplierSourceForm.remarks" /></label></div><div class="modal-foot"><button type="button" class="btn btn-secondary" :disabled="supplierSourceSaving" @click="closeSupplierSourceDialog">取消</button><button v-if="can('suppliers', supplierSourceEditingId ? 'update' : 'create')" class="btn btn-primary" :disabled="supplierSourceSaving || !optionLoaded.suppliers || !!optionErrors.suppliers">{{ supplierSourceSaving ? '保存中…' : '保存来源' }}</button></div></form></div>
    <div v-if="packagingDialogOpen && can('packaging', 'create')" class="modal-backdrop packaging-dialog-backdrop"><form class="modal inline-packaging-modal" role="dialog" aria-modal="true" aria-label="新建包装" @submit.prevent="createPackaging"><div class="modal-head"><div><h3>新建包装</h3><p>保存模板后带入当前表单，仍需保存 SKU 才能建立关联。</p></div><button type="button" class="mini-btn" aria-label="关闭新建包装" :disabled="packagingSaving" @click="requestPackagingClose"><X :size="17" /></button></div><div class="modal-body"><p v-if="optionErrors.suppliers" class="option-load-error" role="alert">{{ optionErrors.suppliers }} <button type="button" @click="loadSkuReferenceOptions">重新加载</button></p><p v-if="packagingSaveError" class="sku-save-error" role="alert">{{ packagingSaveError }}</p><div class="inline-packaging-grid" :inert="packagingSaving"><label>包装名称 <em>*</em><input v-model.trim="packagingForm.name" required /></label><label>包装供应商<select v-model="packagingForm.supplier"><option value="">未指定</option><option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">{{ supplier.name }}</option></select></label><label>长 (cm) <em>*</em><input v-model.number="packagingForm.carton_length" type="number" min="0.01" step="0.01" required /></label><label>宽 (cm) <em>*</em><input v-model.number="packagingForm.carton_width" type="number" min="0.01" step="0.01" required /></label><label>高 (cm) <em>*</em><input v-model.number="packagingForm.carton_height" type="number" min="0.01" step="0.01" required /></label><label>外箱皮重 (kg)<input v-model.number="packagingForm.carton_tare_weight" type="number" min="0" step="0.001" required /></label><label class="full">备注<textarea v-model.trim="packagingForm.description" /></label></div></div><div class="modal-foot"><button type="button" class="btn btn-secondary" :disabled="packagingSaving" @click="requestPackagingClose">取消</button><button v-if="can('packaging', 'create')" class="btn btn-primary" :disabled="packagingSaving || !optionLoaded.suppliers || !!optionErrors.suppliers">{{ packagingSaving ? '保存中...' : '保存并引用' }}</button></div></form></div>
    <div v-if="versionsOpen" class="modal-backdrop"><section class="modal version-modal" role="dialog" aria-modal="true" aria-label="SKU 历史版本"><div class="modal-head"><div><h3>SKU 历史版本</h3><p>记录保存前的商业身份；历史报价和订单不会被改写。</p></div><button type="button" class="mini-btn" aria-label="关闭历史版本" @click="versionsOpen=false"><X :size="17" /></button></div><div class="modal-body"><p v-if="versionsLoading" class="muted">加载中…</p><p v-else-if="versionsError" role="alert">{{ versionsError }} <button type="button" @click="openVersions(versionsRow)">重试</button></p><p v-else-if="!versions.length" class="muted">暂无关键字段变更记录。</p><table v-else class="version-table"><thead><tr><th>版本</th><th>时间</th><th>旧 Sales Model</th><th>旧内部名称</th><th>变更字段</th></tr></thead><tbody><tr v-for="version in versions" :key="version.id"><td>v{{ version.version_no }}</td><td>{{ version.changed_at }}</td><td>{{ version.sales_model_snapshot || '—' }}</td><td>{{ version.display_name_cn_snapshot || '—' }}</td><td>{{ version.changed_fields?.join('、') }}</td></tr></tbody></table></div></section></div>
    <Teleport to="body" :disabled="workspaceTeleportDisabled"><div v-if="toast.text" class="toast" :class="{ error: toast.error }" role="status">{{ toast.text }}</div></Teleport>
  </div>
<EntityDetailModal v-if="detailId && !embedded" entity="skus" :id="detailId" :refresh-key="detailRefresh" @close="closeDetail" @edit="editDetail" />
</template>

<style scoped>
.inline-sku-editor{min-width:0}
.sku-more-settings{border:1px solid #dce7e1;border-radius:10px;padding:12px 14px}
.sku-more-settings summary{cursor:pointer;color:var(--ink);font-weight:600}
.sku-more-settings summary span{margin-left:12px;color:var(--muted);font-weight:400;font-size:var(--text-caption)}
.sku-more-settings .sku-basics{margin-top:12px}
.inline-sku-editor .inline-sku-backdrop{position:static;inset:auto;display:block;padding:0;background:transparent;backdrop-filter:none;z-index:auto}
.inline-sku-editor .sku-modal{width:100%;max-width:100%;height:auto;max-height:none;margin:0;border:1px solid #dce7e1;border-radius:12px;box-shadow:none}
.inline-sku-editor .sku-body{max-height:62vh;overflow:auto;padding:14px;min-width:0}
.inline-sku-editor .sku-basics{grid-template-columns:repeat(2,minmax(0,1fr))}
.inline-sku-editor .description-fields{grid-template-columns:1fr}
.inline-sku-editor .modal-head,.inline-sku-editor .modal-foot{padding:14px;flex-wrap:wrap}
.inline-sku-editor .parameter-grid{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}

.sku-modal{width:min(1475px,calc(100vw - 16px));max-height:calc(100vh - 44px)}.embedded-backdrop{position:absolute;inset:0;z-index:50;padding:0;background:#0b221d66}.embedded-modal{width:100%;max-width:100%;height:100%;max-height:100%;border-radius:0}.modal-head>div p{margin:4px 0 0;color:var(--muted);font-size:var(--text-body)}.sku-body{display:grid;gap:18px;max-height:calc(100vh - 185px);overflow:auto}.embedded-modal .sku-body{max-height:calc(100% - 145px)}.sku-basics{display:grid;grid-template-columns:minmax(220px,2.2fr) repeat(4,minmax(88px,.72fr)) auto;gap:10px;align-items:end;padding:14px;border:1px solid #dfe9e4;border-radius:11px;background:#fbfdfc}.sku-basics .field:not(:first-child) input,.sku-basics .field:not(:first-child) select{min-width:0}.description-fields{grid-column:1/-1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.description-fields textarea{width:100%;min-height:56px;box-sizing:border-box}.check-field{height:40px;display:flex;align-items:center;gap:7px;font-size:var(--text-body);color:#36594e;white-space:nowrap}.section-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.section-title small{color:#678278;font-size:var(--text-caption);font-weight:700}.section-title h4{margin:3px 0 0;font-size:var(--text-section)}.section-title>span{padding:4px 9px;border-radius:99px;background:#e7f2ed;color:#37715f;font-size:var(--text-body);font-weight:700}.parameter-section,.preview-section,.detail-section{padding:16px;border:1px solid #dbe7e1;border-radius:12px;background:#fff}.parameter-group{margin-top:14px}.parameter-group h5,.preview-group h5{margin:0 0 9px;color:#365a4d;font-size:var(--text-section)}.parameter-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.parameter-cell label,.detail-row label{display:block;color:#596b65;font-size:var(--text-body);font-weight:600}.parameter-cell label small{color:#889790;font-weight:400}.parameter-cell p{margin:5px 0 0;color:#9aa6a1;font-size:var(--text-caption)}.rule-hint{margin:8px 0 0;color:#678278;font-size:var(--text-caption)}.section-empty{margin-top:13px;padding:16px;border:1px dashed #cbdad4;border-radius:8px;background:#f8fbf9;color:#789087;text-align:center;font-size:var(--text-body)}.muted{color:var(--muted);font-size:var(--text-secondary)}.preview-section{background:#f7faf8}.preview-groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin-top:14px}.preview-group{border:1px solid #d5e4dd;border-radius:9px;background:#fff;overflow:hidden}.preview-group h5{display:flex;justify-content:space-between;padding:10px 11px;margin:0;background:#edf5f1}.preview-group h5 b{font-size:var(--text-section);color:#578074}.preview-list{max-height:156px;overflow:auto}.preview-card{padding:9px 11px;border-top:1px solid #eef2f0}.preview-card strong,.preview-card span{display:block}.preview-card strong{color:#193d33;font-size:var(--text-body)}.preview-card span{margin-top:3px;color:#778882;font-size:var(--text-body)}.detail-section .btn{padding:8px 11px}.detail-scroll{margin-top:13px;overflow-x:auto}.detail-row{width:100%;min-width:940px;display:grid;grid-template-columns:25px minmax(145px,1.45fr) minmax(96px,.9fr) minmax(66px,.6fr) minmax(118px,1.15fr) repeat(5,minmax(82px,.78fr)) 30px;gap:8px;align-items:end;padding:10px 0;border-top:1px solid #edf1ef}.detail-index{padding-bottom:11px;color:#7c8d86;font-size:var(--text-body);font-weight:700}.detail-row input{width:100%;min-width:0;margin-top:5px;border:1px solid #dce4df;border-radius:7px;padding:8px 9px;color:var(--ink);outline:0}.detail-row input:focus{border-color:#72a897;box-shadow:0 0 0 3px #e2efeb}.detail-row .mini-btn{margin-bottom:1px}.table-actions{display:flex;justify-content:flex-end;gap:6px}.mini-btn.danger{color:var(--danger)}@media(max-width:850px){.sku-modal{width:100%;height:100%;max-height:100vh;border-radius:0}.sku-basics{grid-template-columns:repeat(2,minmax(0,1fr))}.description-fields{grid-template-columns:1fr}.parameter-grid{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}}@media(max-width:520px){.sku-basics,.parameter-grid{grid-template-columns:1fr}.sku-body{max-height:calc(100vh - 165px)}}
.sku-image-picker{grid-column:1/-1;display:flex;align-items:center;gap:11px;padding-top:4px}.sku-image-preview,.sku-image-placeholder{width:64px;height:64px;border:1px solid #d6e2dc;border-radius:8px;background:#fff;object-fit:cover}.sku-image-placeholder{display:grid;place-items:center;color:#93a29c;font-size:var(--text-body)}.sku-image-actions{display:flex;gap:7px}.sku-image-actions .btn{padding:8px 10px;font-size:var(--text-body)}
.preview-hint{margin:5px 0 0;color:#678278;font-size:var(--text-caption);font-weight:400}.preview-table-wrap{max-height:180px;margin-top:13px;overflow:auto;border:1px solid #d5e4dd;border-radius:9px;background:#fff}.preview-table{width:100%;border-collapse:collapse;font-size:var(--text-body)}.preview-table th,.preview-table td{padding:9px 11px;border-bottom:1px solid #e8f0ec;text-align:left;white-space:nowrap}.preview-table th{position:sticky;top:0;background:#edf5f1;color:#365a4d;font-weight:700}.preview-table tr:last-child td{border-bottom:0}
.abbreviation-list{display:grid;gap:6px;margin-top:9px;padding:8px;border:1px solid #d7e7e0;border-radius:7px;background:#f7fbf9}.abbreviation-heading{display:flex;align-items:center;justify-content:space-between;color:#55766b;font-size:var(--text-body);font-weight:700}.abbreviation-help{position:relative}.abbreviation-help summary{display:grid;width:18px;height:18px;place-items:center;border:1px solid #8db6a8;border-radius:50%;color:#2a7560;cursor:help;list-style:none}.abbreviation-help summary::-webkit-details-marker{display:none}.abbreviation-help p{position:absolute;z-index:5;right:0;width:260px;margin:6px 0 0;padding:9px 10px;border:1px solid #c8ddd5;border-radius:7px;background:#fff;color:#48645b;font-size:var(--text-caption);font-weight:400;line-height:1.5;box-shadow:0 7px 18px #173d3620}.abbreviation-input{display:grid;grid-template-columns:minmax(0,1fr) 76px;align-items:center;gap:8px;color:#526b62;font-size:var(--text-body)}.abbreviation-input span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.abbreviation-input input{width:100%;min-width:0;border:1px solid #cdded7;border-radius:6px;padding:6px 8px;background:#fff;color:#214c40;font:700 var(--text-body)/1 inherit;text-transform:uppercase}.abbreviation-input input:focus{outline:0;border-color:#62a28d;box-shadow:0 0 0 2px #dcefe7}
.sku-basics{align-items:start}.sku-basics .field input[readonly]{background:#f1f5f3;color:#557068;cursor:not-allowed}
.batch-fill-panel{display:grid;gap:9px;margin-top:13px;padding:12px;border:1px solid #d5e5de;border-radius:9px;background:#f7fbf9}.batch-filter-row{display:flex;flex-wrap:wrap;align-items:end;gap:9px}.batch-filter-row label{display:grid;gap:4px;color:#587067;font-size:var(--text-body);font-weight:700}.batch-filter-row input,.batch-filter-row select{height:35px;min-width:170px;border:1px solid #cbdcd5;border-radius:7px;padding:0 9px;background:#fff;color:var(--ink)}.batch-model-search input{width:205px}.batch-packaging-select select{width:min(330px,32vw)}.batch-filter-row .btn{height:35px;padding:0 11px;font-size:var(--text-body)}.batch-filter-row .btn:disabled{opacity:.5;cursor:not-allowed}.batch-tag-row{display:flex;flex-wrap:wrap;align-items:center;gap:6px;color:#647b72;font-size:var(--text-secondary)}.parameter-filter-tag,.clear-filter-btn{border:1px solid #cfe1d9;border-radius:99px;padding:4px 8px;background:#fff;color:#4e7064;font-size:var(--text-body);cursor:pointer}.parameter-filter-tag.active{border-color:#237d65;background:#dff1e9;color:#145b49;font-weight:700}.clear-filter-btn{border-color:transparent;background:transparent;color:#6a8077;text-decoration:underline}.batch-fill-hint{margin:0;color:#7a9087;font-size:var(--text-caption)}@media(max-width:850px){.batch-filter-row{align-items:stretch}.batch-filter-row label,.batch-model-search input,.batch-packaging-select select{width:100%}.batch-filter-row .btn{flex:1 1 auto}}
.batch-detail-fields{display:flex;flex-wrap:wrap;align-items:center;gap:8px;color:#647b72;font-size:var(--text-body)}.batch-detail-fields>span{font-weight:700}.batch-detail-fields label{display:flex;align-items:center;gap:5px;min-width:0;white-space:nowrap}.batch-detail-fields input[type="text"],.batch-detail-fields input[type="number"]{width:90px;height:30px;border:1px solid #cbdcd5;border-radius:6px;padding:0 8px;background:#fff;color:var(--ink)}.batch-detail-fields input:disabled{background:#f0f4f2;color:#99a8a1;cursor:not-allowed}.batch-detail-fields input[type="checkbox"]{accent-color:#237d65}@media(max-width:850px){.batch-detail-fields{align-items:flex-start}.batch-detail-fields label{flex:1 1 175px}}
.batch-quantity-field input{width:104px}.abbreviation-input{grid-template-columns:minmax(52px,.65fr) minmax(0,1fr) auto!important}.abbreviation-input>span{grid-column:1;grid-row:1}.abbreviation-input>input{grid-column:2;grid-row:1}.default-abbreviation-btn{grid-column:3;grid-row:1;height:30px;border:1px solid #bcd9ce;border-radius:6px;padding:0 8px;background:#edf7f2;color:#246b58;font-size:var(--text-body);font-weight:700;cursor:pointer;white-space:nowrap}.default-abbreviation-btn:disabled{border-color:#e0e7e3;background:#f4f6f5;color:#a0ada7;cursor:not-allowed}
.abbreviation-help-button{display:grid;width:20px;height:20px;place-items:center;border:1px solid #8db6a8;border-radius:50%;background:#fff;color:#2a7560;cursor:pointer;font:700 var(--text-caption)/1 inherit}.abbreviation-guide-backdrop{z-index:120}.abbreviation-guide-modal{width:min(740px,calc(100vw - 32px));max-height:min(760px,calc(100vh - 44px))}.abbreviation-guide-body{display:grid;gap:14px;max-height:calc(100vh - 170px);overflow:auto}.abbreviation-guide-body>p{margin:0;color:#678278;font-size:var(--text-body)}.abbreviation-reference-group{overflow:hidden;border:1px solid #d7e5df;border-radius:8px}.abbreviation-reference-group h4{margin:0;padding:8px 10px;background:#edf5f1;color:#365a4d;font-size:var(--text-section)}.abbreviation-reference-group table{width:100%;border-collapse:collapse;font-size:var(--text-body)}.abbreviation-reference-group th,.abbreviation-reference-group td{padding:8px 10px;border-top:1px solid #e8f0ec;text-align:left}.abbreviation-reference-group th{color:#61786f;font-weight:700}.abbreviation-reference-group code{color:#17654f;font-weight:800;font-family:inherit}
.sku-basics .full-description{grid-column:span 2}.sku-basics textarea{width:100%;min-height:58px;margin-top:5px;border:1px solid #cdded7;border-radius:7px;padding:8px 9px;resize:vertical}.field-help.warning{color:#9a671d}.history-hit{display:block;margin-top:3px;color:#9a671d;font-size:var(--text-caption)}.version-modal{width:min(760px,calc(100vw - 28px))}.version-table{width:100%;border-collapse:collapse;font-size:var(--text-body)}.version-table th,.version-table td{padding:9px;border-bottom:1px solid #e5ece8;text-align:left}.version-table th{color:#607b70;background:#f3f8f5}
.sku-packaging-section{padding:16px;border:1px solid #cfe1d8;border-radius:12px;background:#f8fbf9}.sku-packaging-section>p{margin:7px 0 13px;color:#678278;font-size:var(--text-body)}.sku-packaging-fields{display:grid;grid-template-columns:minmax(260px,1.8fr) minmax(160px,.7fr);gap:12px}.sku-packaging-fields .field label{display:block;margin-bottom:5px;color:#596b65;font-size:var(--text-body);font-weight:600}.sku-packaging-fields select,.sku-packaging-fields input{width:100%;height:38px;border:1px solid #cdded7;border-radius:7px;padding:0 10px;background:#fff}.sku-packaging-fields input:disabled{background:#f0f4f2;color:#9aa6a1}@media(max-width:520px){.sku-packaging-fields{grid-template-columns:1fr}}
.status-tag{display:inline-flex;padding:3px 8px;border-radius:99px;background:#e7f3ed;color:#257054;font-size:var(--text-secondary);font-weight:700}.status-tag.inactive{background:#f3eded;color:#9a5353}
.category-cell{min-width:180px;white-space:normal;line-height:1.5}
.detail-row{min-width:1120px;grid-template-columns:25px minmax(130px,1.3fr) minmax(130px,1.2fr) minmax(64px,.6fr) minmax(115px,1fr) minmax(92px,.8fr) minmax(92px,.8fr) minmax(250px,2.2fr)}.detail-row input[readonly]{background:#f1f5f3;color:#49675d}.packaging-cell{position:relative}.packaging-cell>label{display:block;color:#596b65;font-size:var(--text-body);font-weight:600}.packaging-picker input{margin-top:5px}.packaging-options{position:absolute;z-index:12;right:0;top:100%;width:min(430px,34vw);max-height:215px;overflow:auto;padding:5px;border:1px solid #c9ddd5;border-radius:8px;background:#fff;box-shadow:0 10px 24px #173d3622}.packaging-options button{display:block;width:100%;padding:8px 9px;border:0;border-radius:5px;background:transparent;color:#35564b;font-size:var(--text-body);text-align:left;cursor:pointer}.packaging-options button:hover{background:#edf5f1}.packaging-options .create-packaging{border-top:1px solid #dbe8e2;color:#197256;font-weight:700}.packaging-dialog-backdrop{z-index:80}.inline-packaging-modal{width:min(680px,calc(100vw - 28px))}.inline-packaging-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.inline-packaging-grid label{display:flex;flex-direction:column;gap:6px;color:#41574e;font-size:var(--text-body);font-weight:650}.inline-packaging-grid em{color:var(--danger);font-style:normal}.inline-packaging-grid input,.inline-packaging-grid select,.inline-packaging-grid textarea{border:1px solid #cdded7;border-radius:7px;padding:8px 9px;background:#fff}.inline-packaging-grid textarea{min-height:70px;resize:vertical}.inline-packaging-grid .full{grid-column:1/-1}@media(max-width:680px){.inline-packaging-grid{grid-template-columns:1fr}}
.supplier-sources-section{padding:16px;border:1px solid #cfe1d8;border-radius:12px;background:#f8fbf9}.supplier-sources-section .section-title{align-items:center}.supplier-add-btn{display:inline-flex;align-items:center;gap:5px;padding:7px 10px;font-size:var(--text-body)}.supplier-source-table-wrap{margin-top:13px;overflow:auto;border:1px solid #d5e4dd;border-radius:9px;background:#fff}.supplier-source-table{width:100%;min-width:780px;border-collapse:collapse;font-size:var(--text-body)}.supplier-source-table th,.supplier-source-table td{padding:9px 11px;border-bottom:1px solid #e8f0ec;text-align:left;vertical-align:middle}.supplier-source-table th{background:#edf5f1;color:#365a4d;font-weight:700;white-space:nowrap}.supplier-source-table tr:last-child td{border-bottom:0}.supplier-source-table td strong,.supplier-source-table td small{display:block}.supplier-source-table td small{margin-top:3px;color:#82928b;font-size:var(--text-caption)}.preferred-tag{display:inline-flex;margin-left:5px;padding:3px 7px;border-radius:99px;background:#fff1d9;color:#9a671d;font-size:var(--text-secondary);font-weight:700}.supplier-source-table .table-actions{align-items:center;flex-wrap:wrap}.supplier-source-backdrop{z-index:90}.supplier-source-modal{width:min(760px,calc(100vw - 28px))}.supplier-source-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.supplier-source-form label{display:flex;flex-direction:column;gap:6px;color:#41574e;font-size:var(--text-body);font-weight:650}.supplier-source-form em{color:var(--danger);font-style:normal}.supplier-source-form input,.supplier-source-form select,.supplier-source-form textarea{border:1px solid #cdded7;border-radius:7px;padding:8px 9px;background:#fff;color:var(--ink)}.supplier-source-form textarea{min-height:72px;resize:vertical}.supplier-source-form .check-field{height:auto;display:flex;flex-direction:row;align-items:center;gap:7px;padding-top:23px}.supplier-source-form .check-field input{width:auto}.supplier-source-form .full-description{grid-column:1/-1}@media(max-width:680px){.supplier-source-form{grid-template-columns:1fr}.supplier-source-form .full-description{grid-column:auto}}
.has-inherited-product .sku-basics .field:first-child select{background:#f1f5f3;color:#557068;cursor:not-allowed;pointer-events:none}
.sku-basics{grid-template-columns:minmax(220px,2.1fr) minmax(125px,.8fr) minmax(135px,.9fr) minmax(82px,.5fr) minmax(90px,.6fr) minmax(62px,.42fr);align-items:end}.sku-basics .full-description{grid-column:span 3}.sku-basics .sku-active{align-self:end;padding-bottom:10px}.sku-basics .sku-code{grid-column:span 2}@media(max-width:850px){.sku-basics{grid-template-columns:repeat(2,minmax(0,1fr))}.sku-basics .full-description,.sku-basics .sku-code{grid-column:span 1}}@media(max-width:520px){.sku-basics{grid-template-columns:1fr}.sku-basics .full-description,.sku-basics .sku-code{grid-column:auto}.sku-basics .sku-active{padding-bottom:0}}
.sku-cost-field .field-help{display:block;min-height:1.45em;line-height:1.45}.cost-verification-actions{align-self:end;padding-bottom:9px}.cost-verification-actions .text-btn{white-space:nowrap}
.sku-basics>.field:first-child:has(input[readonly]){grid-column:1/-1}.sku-data-row{cursor:pointer}.sku-data-row:focus{outline:2px solid #72a897;outline-offset:-2px}
.sku-save-error{margin:0;padding:10px 22px;border-bottom:1px solid #f0c6c6;background:#fff0f0;color:#9a3535;font-size:var(--text-body);font-weight:700}
.batch-packaging-select{width:min(330px,32vw)}.batch-packaging-select :deep(.combo-input){width:100%}.batch-packaging-select :deep(.combo-control){min-height:35px;padding-top:1px;padding-bottom:1px}
.batch-detail-fields input[type="text"],.batch-detail-fields input[type="number"]{width:104px;height:35px}
.duplicate-sku,.detail-row input[readonly].duplicate-sku{color:#c62828}.duplicate-sku-warning{display:inline-block;margin-left:12px;white-space:normal;vertical-align:top;max-width:420px;font-size:var(--text-caption)}.duplicate-sku-warning strong{font-size:var(--text-section);font-weight:900}
.batch-model-search{display:grid;gap:4px}.batch-search-input{position:relative}.batch-search-input input{width:310px;max-width:100%;box-sizing:border-box;padding-right:78px}.batch-search-input button{position:absolute;right:5px;top:50%;transform:translateY(-50%);padding:4px;border:0;border-radius:4px;background:#fff;color:#237d65;font-size:var(--text-body);cursor:pointer}.batch-search-input button:disabled{color:#8a9b94;cursor:default}.batch-search-input button:focus-visible{outline:2px solid #237d65}@media(max-width:850px){.batch-model-search,.batch-search-input,.batch-search-input input{width:100%}}
.identity-review-backdrop{z-index:140}.identity-review-modal{width:min(900px,calc(100vw - 28px));max-height:calc(100vh - 48px)}.identity-review-grid{display:grid;grid-template-columns:150px minmax(0,1fr) minmax(0,1fr);gap:0 12px;border:1px solid #dbe7e1;border-radius:10px;overflow:hidden}.identity-review-grid>div{padding:12px;border-top:1px solid #edf2ef}.identity-review-grid>div:nth-child(-n+3){border-top:0}.identity-review-label{display:flex;align-items:center;background:#f3f8f5;color:#45695d;font-weight:700}.identity-review-old{background:#fff9f8}.identity-review-new{background:#f5fbf8}.identity-review-old small,.identity-review-new small{display:block;color:#7b8983;font-size:var(--text-caption);margin-bottom:5px}.identity-review-old p,.identity-review-new p{margin:0;min-height:24px;word-break:break-word;color:#29483e;font-size:var(--text-body);line-height:1.6}.diff-removed{background:#ffd9d5;color:#a52f24;text-decoration:line-through;border-radius:3px;padding:1px 2px}.diff-added{background:#ccefdc;color:#176443;border-radius:3px;padding:1px 2px}.identity-review-hint{margin:12px 0 0;color:#687c73;font-size:var(--text-caption);line-height:1.7}.sku-save-error{margin:12px 0 0;padding:10px;border-radius:7px;background:#fff2f0;color:#b42318;font-size:var(--text-body)}@media(max-width:650px){.identity-review-grid{grid-template-columns:1fr}.identity-review-grid>div:nth-child(2),.identity-review-grid>div:nth-child(3){border-top:1px solid #edf2ef}.identity-review-label{border-top:1px solid #dbe7e1!important}}

/* Create dialog: a single scrolling form with a persistent section navigator. */
.sku-editor-layout{min-height:0;display:flex;flex:1}.sku-editor-layout>.sku-body{flex:1;min-width:0}
.sku-header-actions{display:flex;align-items:center;gap:10px}.sku-card-heading{display:flex;align-items:center;gap:12px;min-width:0}.sku-card-heading h4{margin:0;font-size:16px;color:#202d40}.sku-card-heading>small{font-size:12px;font-weight:400;color:#77849a}.sku-section-help{border:0;background:transparent;color:#146b5c;font-size:12px;cursor:pointer;white-space:nowrap}.step-dot{display:grid;place-items:center;flex:none;width:32px;height:32px;border-radius:50%;background:linear-gradient(140deg,#158673,#005346);color:white;font-size:14px;font-weight:700}
.sku-create-layout.sku-modal{width:min(1320px,calc(100vw - 48px));height:calc(100dvh - 48px);max-height:calc(100dvh - 48px);background:#f5f8fb;border-radius:16px;overflow:hidden;display:flex;flex-direction:column}.sku-create-layout>.modal-head{padding:22px 26px 18px;border-bottom:0;align-items:flex-start;flex:none;background:transparent}.sku-create-layout>.modal-head h3{font-size:23px;color:#192a40}.sku-create-layout>.modal-head p{font-size:12px;color:#768297;line-height:1.7}.sku-create-layout .sku-editor-layout{overflow:hidden}.sku-step-sidebar{width:182px;flex:none;padding:6px 12px 20px 18px;overflow:auto}.sku-step-sidebar nav{position:relative;display:grid;gap:8px}.sku-step-sidebar nav:before{content:'';position:absolute;left:24px;top:28px;bottom:32px;width:1px;background:#cddcdF}.sku-step-sidebar nav button{position:relative;display:flex;align-items:flex-start;gap:13px;padding:13px 9px;min-height:70px;text-align:left;background:transparent;border:0;border-radius:10px;cursor:pointer;color:#344155}.sku-step-sidebar nav button.active{background:#e7f0f0;color:#086557}.sku-step-sidebar nav .step-dot{width:30px;height:30px;background:#fff;border:1px solid #d3deea;color:#69788d;font-size:12px}.sku-step-sidebar nav button.active .step-dot{background:#086557;color:white;border-color:#086557}.sku-step-sidebar strong{display:block;font-size:13px;line-height:1.7}.sku-step-sidebar small{display:block;font-size:11px;line-height:1.8;color:#7f8c9e}.sku-step-help{margin-top:23px;padding:16px 12px;border-radius:10px;background:#edf3f6;font-size:11px;line-height:1.9;color:#748196}.sku-step-help strong{color:#344155}.sku-step-help p{margin:7px 0 0}
.sku-create-layout .sku-body{max-height:none!important;padding:6px 22px 24px 8px!important;overflow-y:auto;display:flex;flex-direction:column;gap:16px;scroll-behavior:smooth;scroll-padding-top:8px}.sku-create-layout .sku-body>section{flex:none;scroll-margin-top:8px}.sku-create-layout .sku-basic-card,.sku-create-layout .parameter-section,.sku-create-layout .preview-section,.sku-create-layout .detail-section,.sku-create-layout .sku-finish-card{padding:18px;border:1px solid #e2eaf1;border-radius:11px;background:white;box-shadow:0 4px 16px #20354f03}.sku-create-layout .section-title{margin-bottom:16px}.sku-create-layout .sku-basics{grid-template-columns:repeat(12,minmax(0,1fr));padding:0;border:0;background:transparent;gap:16px 14px;margin-top:18px;align-items:start}.sku-create-layout .sku-basics>.field{grid-column:span 3}.sku-create-layout .sku-basics>.field:nth-child(3),.sku-create-layout .sku-basics>.field:nth-child(4){grid-column:span 2}.sku-create-layout .sku-active{grid-column:span 2;padding:24px 0 0;align-self:start;height:auto}.sku-create-layout .description-fields{grid-column:1/9;grid-template-columns:1fr 1fr;gap:14px}.sku-create-layout .description-fields textarea{min-height:120px;margin-top:7px}.sku-create-layout .sku-image-picker{grid-column:9/13;display:flex;flex-wrap:wrap;gap:9px;align-items:center;border:0;background:transparent;padding:0;margin:0}.sku-create-layout .sku-image-picker:before{content:'产品图片';display:block;flex-basis:100%;font-weight:600;font-size:12px;color:#38485b}.sku-create-layout .sku-image-preview,.sku-create-layout .sku-image-placeholder{width:104px;height:120px;object-fit:cover;border-radius:6px}.sku-create-layout .sku-image-placeholder{display:grid;place-items:center;border:1px dashed #cedbe5;background:#f8fafc;color:#8996a6;font-size:12px}.sku-create-layout .sku-image-actions{flex:1;display:grid;gap:8px;min-width:76px}.sku-create-layout .field>label{font-size:12px;color:#374457;font-weight:600}.sku-create-layout .field input,.sku-create-layout .field select,.sku-create-layout textarea{border-color:#dbe4ed;border-radius:6px;font-size:12px;min-height:36px}.sku-create-layout .field-help{font-size:11px;line-height:1.6}.sku-create-layout .parameter-group{padding:13px;background:#f3f7f9;border-radius:9px;margin-top:14px}.sku-create-layout .parameter-group h5{font-size:13px;color:#344155;margin-bottom:12px}.sku-create-layout .parameter-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.sku-create-layout .parameter-cell{background:#fff;border-radius:7px;padding:10px;min-width:0}.sku-create-layout .parameter-cell>label{font-size:12px;margin-bottom:7px;color:#38485b}.sku-create-layout .abbreviation-list{background:#f2f6f8;border:0;border-radius:6px;padding:9px;margin-top:8px}.sku-create-layout .preview-table-wrap{border:1px solid #e0e8ef;border-radius:7px;overflow:auto}.sku-create-layout .preview-table{margin:0}.sku-create-layout .preview-table th{background:#f4f7fa;color:#526075;font-size:12px}.sku-create-layout .preview-table td{font-size:12px;padding:12px}.sku-create-layout .preview-hint{margin:10px 0 0;font-size:11px}.sku-create-layout .batch-fill-panel{background:transparent;border:0;padding:0}.sku-create-layout .batch-filter-row{display:grid;grid-template-columns:minmax(180px,2fr) minmax(100px,1fr) minmax(100px,1fr) minmax(140px,1.3fr) auto;gap:12px;align-items:end}.sku-create-layout .batch-model-search,.sku-create-layout .batch-packaging-select{min-width:0;width:auto}.sku-create-layout .batch-filter-row>.btn-secondary{justify-self:start}.sku-create-layout .batch-quantity-field{width:auto;min-width:0}.sku-create-layout .batch-detail-fields{padding:12px 0;border-top:1px solid #edf1f4;margin-top:12px}.sku-create-layout .detail-row{grid-template-columns:28px minmax(180px,1.5fr) minmax(150px,1.2fr) 66px minmax(120px,1fr) 96px 96px minmax(150px,1.2fr);min-width:1040px;padding:12px 8px}.sku-create-layout .detail-scroll{border:1px solid #e0e8ef;border-radius:7px}.sku-create-layout .detail-row label{font-size:11px;color:#6c7c8e}.sku-create-layout .sku-finish-card{display:flex;align-items:center;justify-content:space-between;gap:12px}.sku-create-layout .sku-finish-card .modal-foot{padding:0;border:0;background:transparent}.sku-create-layout .btn{border-radius:7px;font-size:12px;min-height:36px}.sku-create-layout .btn-primary{background:#006455;border-color:#006455}.sku-create-layout .sku-save-error{flex:none;margin:0 22px 8px}.sku-basic-card>.sku-basics{margin-bottom:0}
.inline-sku-editor .sku-create-layout.sku-modal{height:auto;max-height:none;width:100%}.inline-sku-editor .sku-create-layout .sku-editor-layout{max-height:72vh}.inline-sku-editor .sku-create-layout .sku-step-sidebar{width:150px;padding-left:10px}.inline-sku-editor .sku-create-layout .sku-basics{grid-template-columns:repeat(12,minmax(0,1fr))}.inline-sku-editor .sku-create-layout .description-fields{grid-template-columns:1fr 1fr}
@media(max-width:1000px){.sku-step-sidebar{width:152px;padding-left:10px}.sku-create-layout .batch-filter-row{grid-template-columns:repeat(2,minmax(0,1fr))}.sku-create-layout .description-fields{grid-column:1/8;grid-template-columns:1fr}.sku-create-layout .sku-image-picker{grid-column:8/13}.sku-create-layout .sku-card-heading>small{display:none}}
@media(max-width:700px){.sku-create-layout.sku-modal{width:100vw;height:100dvh;max-height:100dvh;border-radius:0}.sku-create-layout>.modal-head{padding:15px;gap:12px}.sku-create-layout>.modal-head h3{font-size:20px}.sku-header-actions{gap:5px}.sku-header-actions>.btn-secondary{display:none}.sku-create-layout .sku-editor-layout{flex-direction:column}.sku-step-sidebar,.inline-sku-editor .sku-create-layout .sku-step-sidebar{width:auto;padding:0 12px 10px;overflow:auto;flex:none}.sku-step-sidebar nav{display:flex;gap:5px}.sku-step-sidebar nav:before,.sku-step-help,.sku-step-sidebar small{display:none}.sku-step-sidebar nav button{min-height:0;padding:8px;gap:6px;white-space:nowrap;align-items:center}.sku-step-sidebar nav .step-dot{width:23px;height:23px}.sku-step-sidebar strong{font-size:11px}.sku-create-layout .sku-body{padding:2px 12px 18px!important}.sku-create-layout .sku-basics,.inline-sku-editor .sku-create-layout .sku-basics{grid-template-columns:1fr 1fr}.sku-create-layout .sku-basics>.field,.sku-create-layout .sku-basics>.field:nth-child(3),.sku-create-layout .sku-basics>.field:nth-child(4){grid-column:auto}.sku-create-layout .description-fields,.sku-create-layout .sku-image-picker{grid-column:1/-1}.sku-create-layout .sku-active{grid-column:1/-1;padding:0}.sku-create-layout .parameter-grid{grid-template-columns:1fr}.sku-create-layout .sku-finish-card{flex-wrap:wrap}.sku-create-layout .sku-finish-card .modal-foot{margin-left:auto}.sku-create-layout .sku-card-heading{gap:9px}.sku-create-layout .sku-card-heading h4{font-size:14px}}


.parameter-history{margin-top:9px;padding:9px;background:#f2f6f8;border-radius:6px}.parameter-history>span{display:block;font-size:11px;color:#758494;margin-bottom:7px}.parameter-history>small{font-size:11px;color:#93a0ac}.parameter-history-values{display:flex;flex-wrap:wrap;gap:6px;max-height:96px;overflow:auto}.parameter-history-values button{border:1px solid transparent;border-radius:6px;padding:4px 10px;background:#e6edef;color:#405565;font-size:12px;cursor:pointer}.parameter-history-values button:hover{border-color:#79b9aa;color:#006455;background:#e4f3ed}
.sku-modal .batch-filter-row{display:flex;flex-wrap:wrap;gap:10px;align-items:end}.sku-modal .batch-model-search{flex:1.8 1 180px;min-width:180px;width:auto}.sku-modal .batch-quantity-field{flex:1 1 85px;min-width:85px;width:auto}.sku-modal .batch-notes-field{display:flex;flex-direction:column;gap:6px;flex:1.4 1 120px;min-width:120px;font-size:12px;color:#526b62}.sku-modal .batch-notes-field input{width:100%;min-width:0;border:1px solid #cdded7;border-radius:6px;padding:8px 9px;height:36px}.sku-modal .batch-packaging-select{flex:1.4 1 145px;min-width:145px;width:auto}.sku-modal .batch-fill-actions{display:flex;flex:1 0 100%;justify-content:flex-end;gap:8px;flex-wrap:wrap}

/* Keep value-to-model mappings compact even inside parameter-cell label rules. */
.sku-modal .parameter-grid{align-items:start}
.sku-modal .parameter-cell{container:sku-parameter / inline-size}
.sku-modal .parameter-cell .abbreviation-input{display:grid;grid-template-columns:minmax(44px,.8fr) minmax(64px,1.2fr) auto!important;align-items:center;gap:6px;min-width:0;margin:0;font-weight:400}
.sku-modal .abbreviation-value{display:flex;justify-content:space-between;gap:8px;align-items:center}.abbreviation-value i{font-style:normal;color:#92a49d}
.sku-modal .abbreviation-input input{height:32px;margin:0;box-sizing:border-box;font-size:12px}.sku-modal .default-abbreviation-btn{height:30px;font-size:11px;font-weight:500}.sku-modal .abbreviation-list{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px 14px;padding:10px}.sku-modal .abbreviation-heading{grid-column:1/-1;font-size:12px;margin-bottom:2px}
@container sku-parameter (max-width:390px){.sku-modal .abbreviation-list{grid-template-columns:minmax(0,1fr)}}
.sku-modal .parameter-history{padding:7px 9px}.sku-modal .batch-fill-panel{container-type:inline-size}
.sku-modal .batch-filter-row{display:grid;grid-template-columns:minmax(220px,2fr) repeat(3,minmax(90px,1fr)) minmax(135px,1.3fr) minmax(165px,1.5fr);gap:14px;align-items:end}
.sku-modal .batch-filter-row>label,.sku-modal .batch-model-search{min-width:0;width:100%;display:grid;gap:7px;font-size:12px}.sku-modal .batch-search-input{width:100%;min-width:0}
.sku-modal .batch-filter-row input{width:100%;max-width:100%;min-width:0;box-sizing:border-box;height:36px;margin:0}.sku-modal .batch-search-input input{padding-right:70px}
.sku-modal .batch-fill-actions{grid-column:1/-1;margin-top:2px}
@container(max-width:940px){.sku-modal .batch-filter-row{grid-template-columns:repeat(4,minmax(0,1fr))}.sku-modal .batch-model-search,.sku-modal .batch-notes-field{grid-column:span 2}}
@container(max-width:560px){.sku-modal .batch-filter-row{grid-template-columns:repeat(2,minmax(0,1fr))}.sku-modal .batch-model-search{grid-column:1/-1}.sku-modal .batch-notes-field{grid-column:auto}}

.ordinary-attributes-section{padding:18px;border:1px solid #e2eaf1;border-radius:11px;background:white}.ordinary-attributes-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.ordinary-attributes-grid .field{min-width:0}.ordinary-attributes-grid input{width:100%;box-sizing:border-box}.batch-parameter-groups{display:flex;flex-wrap:wrap;gap:12px;margin-top:16px}.batch-parameter-group{min-width:150px;max-width:100%;margin:0;padding:10px 12px 12px;border:1px solid #dce7e1;border-radius:8px;background:#f6faf8;box-sizing:border-box}.batch-parameter-group legend{padding:0 5px;font-size:12px;font-weight:600;color:#48665a}.batch-parameter-group>div{display:flex;flex-wrap:wrap;gap:8px}.batch-parameter-group .parameter-filter-tag{margin:0}.batch-parameter-group .parameter-filter-tag:focus-visible{outline:2px solid #26856a;outline-offset:2px}@media(max-width:700px){.ordinary-attributes-grid{grid-template-columns:1fr}.batch-parameter-group{flex:1 1 140px}}
.sku-list-filters{display:flex;flex-wrap:wrap;gap:10px}.sku-list-filters .search-box{flex:1 1 260px}.sku-list-filters select{min-width:0;max-width:280px;padding:10px;border:1px solid var(--line);border-radius:8px;background:white}.sku-list-table{min-width:1240px;table-layout:fixed}.sku-list-table th:nth-child(1){width:260px}.sku-list-table th:nth-child(2){width:210px}.sku-list-table th:nth-child(3){width:190px}.sku-list-table td{white-space:normal;overflow-wrap:anywhere;vertical-align:top}.sku-list-table th:last-child,.sku-list-table td:last-child{position:sticky;right:0;width:100px;background:white}.sku-code-hint{display:block;color:#74847c;font-weight:400;margin-top:6px}.parameter-search{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:12px 0}.parameter-search label{display:grid;gap:6px}.parameter-search input{padding:10px;border:1px solid var(--line);border-radius:8px}.parameter-search span{font-size:var(--text-caption);color:#70847a}.supplier-source-form>p{grid-column:1/-1}.supplier-source-form label{min-width:0}.supplier-source-form input,.supplier-source-form select{max-width:100%;min-width:0}.supplier-source-modal .modal-foot{position:sticky;bottom:0;background:white}
.sku-modal{width:min(1475px,calc(100vw - 48px));max-width:100%;min-width:0}.sku-body{min-width:0;overflow-x:hidden}.sku-basics .field{min-width:0}.sku-basics input,.sku-basics select{max-width:100%;min-width:0}.supplier-source-table{table-layout:fixed}.supplier-source-table td{white-space:normal;overflow-wrap:anywhere}.supplier-source-table th:first-child{width:190px}.supplier-source-table th:nth-child(2){width:220px}@media(max-width:1200px){.sku-basics{grid-template-columns:repeat(2,minmax(0,1fr))}.sku-header-actions{flex-wrap:wrap}}
.sku-body{grid-template-columns:minmax(0,1fr)}.sku-body>*{min-width:0}:global(body:has(.modal-backdrop:not(.inline-sku-backdrop)>.sku-modal)){overflow:hidden}
:global(body:has(.version-modal)){overflow:hidden}
.version-table th{white-space:nowrap}.version-table td{overflow-wrap:anywhere}
.sku-list-table th:nth-child(4){width:70px}.sku-list-table .status-tag{white-space:nowrap}
/* Keep edit fields full width after the later tablet two-column override. */
@media(max-width:520px){.sku-modal:not(.sku-create-layout) .sku-basics{grid-template-columns:minmax(0,1fr)}}
</style>
