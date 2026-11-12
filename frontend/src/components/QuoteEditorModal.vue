<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, downloadQuoteExport, listAll } = useWorkspaceApi()
import { provideUnsavedChangesScope, useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'

import { defaultExchangeRate, skuDefaultPrice, currencyHint, salesRateError, changeDocumentCurrency } from '../utils/documentCurrency'
import { confirmDialog } from '../dialogs'
import { compactDecimalInput } from '../utils/decimalInput'
import { roundPiMoney } from '../utils/piMoney'
import TradeUnitPicker from './TradeUnitPicker.vue'
import { fromTradeLine, tradePayload, baseQuantity, tradeLabel, withDefaultTradeUnit, restoreTradeLines } from '../utils/tradeUnits'
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { AlertTriangle, Box, Eye, MinusCircle, PackageCheck, RotateCw, Save, Settings2, X } from 'lucide-vue-next'

import QuotePreviewModal from './QuotePreviewModal.vue'
import QuoteRiskNotice from './QuoteRiskNotice.vue'
import SkuPickerPanel from './SkuPickerPanel.vue'
import SegmentedDateInput from './SegmentedDateInput.vue'
import { addDays, daysBetween } from '../utils/orderDate'
import { useAccessControl } from '../accessControl'

const props = defineProps({
  quote: { type: Object, default: null },
  customers: { type: Array, required: true },
  skus: { type: Array, required: true },
  mode: { type: String, required: true, validator: value => ['create', 'revise'].includes(value) },
})
const emit = defineEmits(['close', 'saved'])
const { can } = useAccessControl()

/*
 * Task 4 manual acceptance checklist (verified):
 * [x] The editor has no embedded PI preview pane.
 * [x] Preview opens a separate child modal from the current unsaved draft.
 * [x] Closing preview retains all editor inputs, including changed quantities.
 * [x] Saving an existing quote creates a revision through /revise/.
 * [x] Save and save/export are separate operations; export downloads with the complete generated quote identifier.
 */
const today = new Date().toISOString().slice(0, 10)
const draft = reactive(makeDraft())
const initialized = ref(false)
const editorScope = provideUnsavedChangesScope()
const guard = useUnsavedChangesGuard({ data: () => draft, scope: editorScope })
const requestClose = () => editorScope.requestClose(() => emit('close'))
const previewOpen = ref(false)
const previewTemplate = ref(null)
const saving = ref(false)
const savedQuote = ref(null)
const errorMessage = ref('')
const editorForm = ref(null)
const exportError = ref('')
const riskNoticeOpen = ref(false)
const riskRows = ref([])
const riskCheckUnavailable = ref(false)
const packagingTemplates = ref([])
const packagingOverrides = reactive({})
const packingOpen = ref(false), packagingSku = ref(null), packagingSaving = ref(false)
const packagingForm = reactive({ template: '', qty_per_carton: '', unit_net_weight: '' })
const packagingGuard = useUnsavedChangesGuard({ data: () => packagingForm, enabled: () => Boolean(packagingSku.value), routeGuard: false, scope: editorScope })
const requestPackagingClose = () => packagingGuard.requestClose(() => { packagingSku.value = null })

function makeDraft() {
  const quote = props.quote || {}
  const quoteDate = quote.quote_date || today
  return {
    customer: quote.customer || '', quote_no: quote.quote_no || '', quote_date: quoteDate,
    valid_until: quote.valid_until || addDays(quoteDate, 30), status: quote.status || 'draft', currency: quote.currency || 'USD',
    exchange_rate: compactDecimalInput(quote.exchange_rate ?? defaultExchangeRate(quote.currency || 'USD')), shipping_fee: quote.shipping_fee || 0, discount: quote.discount || 0,
    recipient_name: quote.recipient_name || '', buyer_address: quote.buyer_address || '', buyer_email: quote.buyer_email || '', buyer_phone: quote.buyer_phone || '', buyer_tax_id: quote.buyer_tax_id ?? (props.mode === 'revise' ? null : ''),
    lead_time_days: quote.lead_time_days ?? 10, deposit_percent: Number(quote.deposit_ratio ?? 0.30) * 100,
    revision_summary: '',
    trading_terms: quote.trading_terms || 'FOB Shenzhen', shipping_details: quote.shipping_details || '', notes: quote.notes || '',
    items: (quote.items || []).map(item => ({ ...fromTradeLine(item), sku: item.sku, quantity: item.trade_quantity ?? item.quantity, unit_price: item.trade_unit_price ?? item.unit_price, sales_model_snapshot: item.sales_model_snapshot ?? item.model ?? '', description: item.description || item.description_snapshot || '', notes: item.notes || '' })),
  }
}

const validityDays = ref(daysBetween(draft.quote_date, draft.valid_until))
const inheritedCustomer = computed(() => props.mode === 'create' && Boolean(props.quote?.customer))

function setQuoteDate(value) {
  draft.quote_date = value
  if (validityDays.value !== '') draft.valid_until = addDays(value, validityDays.value)
  else if (draft.valid_until) validityDays.value = daysBetween(value, draft.valid_until)
}
function setValidUntil(value) {
  draft.valid_until = value
  validityDays.value = daysBetween(draft.quote_date, value)
}
function setValidityDays() {
  if (validityDays.value === '' || !draft.quote_date) return
  draft.valid_until = addDays(draft.quote_date, validityDays.value)
}

const subtotal = computed(() => roundPiMoney(draft.items.reduce((sum, item) => sum + roundPiMoney(Number(item.quantity || 0) * Number(item.unit_price || 0)), 0)))
const total = computed(() => roundPiMoney(subtotal.value + roundPiMoney(draft.shipping_fee || 0) - roundPiMoney(draft.discount || 0)))
const previewDraft = computed(() => {
  const customer = props.customers.find(row => row.id === Number(draft.customer)) || {}
  const depositRatio = Math.min(100, Math.max(0, Number(draft.deposit_percent || 0))) / 100
  const depositAmount = Math.round(total.value * depositRatio * 100) / 100
  return {
    quote_no: draft.quote_no, quote_date: draft.quote_date, valid_until: draft.valid_until, currency: draft.currency,
    ...(previewTemplate.value || {}),
    buyer: { company_name: props.mode === 'revise' ? (props.quote?.buyer_company_name ?? '') : (customer.name || ''), recipient: draft.recipient_name, address: draft.buyer_address, email: draft.buyer_email, phone: draft.buyer_phone, tax_id: draft.buyer_tax_id },
    terms: { lead_time_days: draft.lead_time_days, trading_terms: draft.trading_terms, shipping_details: draft.shipping_details, notes: draft.notes },
    totals: { subtotal: subtotal.value, shipping_fee: roundPiMoney(draft.shipping_fee || 0), discount: roundPiMoney(draft.discount || 0), total_amount: total.value },
    payment_splits: { deposit_ratio: depositRatio, deposit_amount: depositAmount, balance_ratio: 1 - depositRatio, balance_amount: total.value - depositAmount },
    products: draft.items.map((item, index) => { const sku = props.skus.find(row => row.id === Number(item.sku)) || {}; return { key: `${index}-${item.sku}`, sku: sku.sku || '', sku_code: sku.sku_code || sku.sku || '', model: item.sales_model_snapshot || sku.sales_model || '', product_name: sku.display_name_cn || sku.product_name || '', description: item.description + (item.trade_unit ? `\n${item.trade_snapshot?.name}: 1 ${item.trade_snapshot?.unit} = ${item.trade_snapshot?.factor} ${item.trade_snapshot?.base_unit}; Total ${baseQuantity(item)} ${item.trade_snapshot?.base_unit}` : ''), quantity: item.quantity, unit: tradeLabel(item, sku.unit || 'pcs'), unit_price: item.unit_price, amount: roundPiMoney(Number(item.quantity || 0) * Number(item.unit_price || 0)), image_url: sku.image || '' } }),
  }
})
async function changeCurrency(event) {
  const currency = event.target.value
  event.target.value = draft.currency
  await changeDocumentCurrency(draft, currency, props.skus, confirmDialog)
  event.target.value = draft.currency
}
function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
const activeSkuId = ref('')
function skuDescription(sku) { return sku?.description_en || sku?.description_cn || sku?.display_name_cn || sku?.product_name || sku?.specification || '' }
function makeItem(sku) { return withDefaultTradeUnit({ sku: sku.id, quantity: 1, unit_price: skuDefaultPrice(sku, draft.currency), sales_model_snapshot: sku.sales_model || '', description: skuDescription(sku), notes: '' }, sku) }
const selectedSkuIds = computed({
  get: () => [...new Set(draft.items.map(item => String(item.sku)).filter(Boolean))],
  set: syncSelectedSkus,
})
const activeSku = computed(() => props.skus.find(sku => String(sku.id) === String(activeSkuId.value)) || props.skus.find(sku => String(sku.id) === selectedSkuIds.value[0]) || null)
const activeItem = computed(() => draft.items.find(item => String(item.sku) === String(activeSku.value?.id)) || null)
const availabilityBySku = ref({})
const availabilityLoading = ref(false)
const availabilityError = ref(false)
const availabilityLastRefreshed = ref('')
let availabilityRequest = 0
const availabilitySkuSetKey = computed(() => selectedSkuIds.value
  .map(Number)
  .filter(id => Number.isSafeInteger(id) && id > 0)
  .sort((left, right) => left - right)
  .join(','))
const quoteDemandBySku = computed(() => {
  const demand = {}
  draft.items.forEach(item => {
    const skuId = Number(item.sku)
    const quantity = baseQuantity(item)
    if (!Number.isSafeInteger(skuId) || skuId <= 0 || !Number.isFinite(quantity)) return
    demand[skuId] = (demand[skuId] || 0) + quantity
  })
  return demand
})
const inventoryReferenceRows = computed(() => selectedSkuIds.value.map(value => {
  const skuId = Number(value)
  const sku = props.skus.find(row => Number(row.id) === skuId)
  const metrics = availabilityBySku.value[skuId] || null
  const demand = Number(quoteDemandBySku.value[skuId] || 0)
  const available = metrics ? Number(metrics.available_quantity) : null
  return {
    skuId,
    sku,
    metrics,
    demand,
    unit: sku?.unit || 'pcs',
    shortage: metrics ? Math.max(0, demand - available) : null,
  }
}))
function formatInventoryQuantity(value) {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(Number(value || 0))
}
async function refreshInventoryAvailability() {
  const skuIds = availabilitySkuSetKey.value ? availabilitySkuSetKey.value.split(',').map(Number) : []
  const request = ++availabilityRequest
  if (!skuIds.length) {
    availabilityBySku.value = {}
    availabilityLoading.value = false
    availabilityError.value = false
    availabilityLastRefreshed.value = ''
    return
  }

  availabilityLoading.value = true
  availabilityError.value = false
  availabilityBySku.value = {}
  availabilityLastRefreshed.value = ''
  try {
    const response = await api.post('/quotes/availability-preview/', { sku_ids: skuIds })
    if (request !== availabilityRequest || availabilitySkuSetKey.value !== skuIds.join(',')) return
    const selectedIds = new Set(skuIds)
    availabilityBySku.value = Object.fromEntries((response.data?.items || [])
      .filter(item => selectedIds.has(Number(item.sku)))
      .map(item => [Number(item.sku), item]))
    availabilityLastRefreshed.value = new Intl.DateTimeFormat('zh-CN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }).format(new Date())
  } catch {
    if (request === availabilityRequest && availabilitySkuSetKey.value === skuIds.join(',')) availabilityError.value = true
  } finally {
    if (request === availabilityRequest) availabilityLoading.value = false
  }
}
watch(availabilitySkuSetKey, () => { void refreshInventoryAvailability() }, { immediate: true })
function packagingFor(sku) { return packagingOverrides[sku.id] || sku.packaging || {} }
const packingProjection = computed(() => {
  const cartons = [], missing = [], warnings = []
  draft.items.forEach(item => {
    const sku = props.skus.find(row => row.id === Number(item.sku)); if (!sku || Number(item.quantity) <= 0) return
    const pack = packagingFor(sku)
    const required = ['template', 'effective_qty_per_carton', 'effective_length', 'effective_width', 'effective_height', 'effective_carton_tare_weight', 'unit_net_weight']
    if (required.some(field => pack[field] === null || pack[field] === undefined || pack[field] === '')) { missing.push(sku); return }
    const qty = Number(pack.effective_qty_per_carton), amount = baseQuantity(item), full = Math.floor(amount / qty), remainder = amount - full * qty
    const addCarton = quantity => { const net = Number(pack.unit_net_weight) * quantity; const cbm = Number(pack.effective_length) * Number(pack.effective_width) * Number(pack.effective_height) / 1000000; cartons.push({ sku, quantity, length: Number(pack.effective_length), width: Number(pack.effective_width), height: Number(pack.effective_height), net, gross: net + Number(pack.effective_carton_tare_weight), cbm, partial: quantity !== qty }) }
    Array.from({ length: full }, () => addCarton(qty))
    if (remainder > 0.000001) { if (pack.partial_carton_policy === 'MANUAL') warnings.push(`${sku.sku} 剩余 ${remainder} 件需人工装箱`); else addCarton(remainder) }
  })
  return { cartons, missing, warnings, totalPieces: cartons.reduce((sum, row) => sum + row.quantity, 0), totalNet: cartons.reduce((sum, row) => sum + row.net, 0), totalGross: cartons.reduce((sum, row) => sum + row.gross, 0), totalCbm: cartons.reduce((sum, row) => sum + row.cbm, 0) }
})
function openPackaging(sku) { const pack = packagingFor(sku); Object.assign(packagingForm, { template: pack.template || '', qty_per_carton: pack.effective_qty_per_carton || '', unit_net_weight: pack.unit_net_weight || '' }); packagingGuard.markClean(); packagingSku.value = sku }
async function savePackaging() {
  if (!packagingSku.value || !packagingForm.template || Number(packagingForm.qty_per_carton) <= 0 || Number(packagingForm.unit_net_weight) < 0) return
  packagingSaving.value = true
  try { const response = await api.put(`/skus/${packagingSku.value.id}/packaging/`, { packaging_template: Number(packagingForm.template), qty_per_carton_override: Number(packagingForm.qty_per_carton), unit_net_weight: Number(packagingForm.unit_net_weight) }); packagingOverrides[packagingSku.value.id] = response.data.effective; packagingGuard.markClean(); packagingSku.value = null; packingOpen.value = true }
  catch (error) { errorMessage.value = `保存 ${packagingSku.value.sku} 的默认包装失败：${error.message}` }
  finally { packagingSaving.value = false }
}
function syncSelectedSkus(ids) {
  const selected = [...new Set((ids || []).map(String))]
  const previousLines = [...(draft.items || [])]
  const existing = new Map(draft.items.map(item => [String(item.sku), item]))
  draft.items.splice(0, draft.items.length, ...selected.map(id => existing.get(id) || makeItem(props.skus.find(sku => String(sku.id) === id))).filter(Boolean))
  draft.items = restoreTradeLines(draft.items, previousLines)
  if (!selected.includes(String(activeSkuId.value))) activeSkuId.value = selected[0] || ''
}
function activateSku(id) { activeSkuId.value = String(id) }
const recipientFields = ['recipient_name', 'buyer_address', 'buyer_email', 'buyer_phone']
const editedRecipientFields = new Set(recipientFields.filter(field => Object.hasOwn(props.quote || {}, field)))
let contactRequest = 0
function editRecipient(field) { editedRecipientFields.add(field) }
async function selectCustomer() {
  const request = ++contactRequest
  const customer = props.customers.find(row => row.id === Number(draft.customer))
  if (!customer) return
  const prefill = values => {
    if (request !== contactRequest || Number(draft.customer) !== customer.id) return
    for (const [field, value] of Object.entries(values)) {
      if (!editedRecipientFields.has(field)) draft[field] = value
    }
  }
  prefill({ buyer_address: customer.address || '', recipient_name: customer.name || '', buyer_email: '', buyer_phone: '' })
  try {
    const contacts = await listAll('/contacts/', { params: { customer: customer.id } })
    const contact = contacts.find(row => row.is_primary) || contacts[0]
    if (contact) prefill({ recipient_name: contact.name, buyer_email: contact.email || '', buyer_phone: contact.phone || '' })
  } catch { /* Keep the editable recipient values, including explicit blanks. */ }
}
function focusLineField(index, label) {
  const input = editorForm.value?.querySelectorAll('.quote-line-row')[index]?.querySelector(`input[aria-label="${label}"]`)
  input?.focus({ preventScroll: true })
  input?.scrollIntoView({ block: 'center', inline: 'nearest' })
}

function quoteSaveError(error) {
  const modelError = Object.entries(error.data?.items ?? {}).find(([index, item]) =>
    /^\d+$/.test(index) && Array.isArray(item?.sales_model_snapshot) && item.sales_model_snapshot.length)
  if (!modelError) return error.message
  const [index, item] = modelError
  focusLineField(Number(index), '报价型号')
  return `第 ${Number(index) + 1} 条商品 · 报价型号：${item.sales_model_snapshot.join('；')}`
}
function validate() {
  if (salesRateError(draft)) return salesRateError(draft)
  const invalidPrice = draft.items.findIndex(item => item.unit_price === '' || item.unit_price == null || Number(item.unit_price) < 0)
  if (invalidPrice !== -1) {
    focusLineField(invalidPrice, '单价')
    return `第 ${invalidPrice + 1} 条商品 · 单价：请填写有效单价。`
  }
  if (!draft.customer) return '请选择客户。'
  if (props.mode === 'revise' && !draft.revision_summary.trim()) return '请简要说明本次修改的内容。'
  if (draft.quote_date && draft.valid_until && draft.valid_until < draft.quote_date) return '有效期不能早于报价日期。'
  if (!draft.items.length || draft.items.some(item => !item.sku)) return '请至少添加一条有效的 SKU 明细。'
  if (total.value < 0) return '报价合计不能为负数。'
  return ''
}
function payload() {
  return {
    customer: Number(draft.customer), quote_date: draft.quote_date, valid_until: draft.valid_until || null,
    currency: draft.currency, exchange_rate: draft.exchange_rate, shipping_fee: draft.shipping_fee || 0, discount: draft.discount || 0,
    recipient_name: draft.recipient_name, buyer_address: draft.buyer_address, buyer_email: draft.buyer_email, buyer_phone: draft.buyer_phone,
    ...((props.mode === 'create' || props.quote?.can_revise_buyer_tax_id === true) ? { buyer_tax_id: draft.buyer_tax_id } : {}),
    lead_time_days: draft.lead_time_days === '' ? null : draft.lead_time_days ?? null, deposit_ratio: Math.min(100, Math.max(0, Number(draft.deposit_percent || 0))) / 100,
    trading_terms: draft.trading_terms, shipping_details: draft.shipping_details, notes: draft.notes,
    revision_summary: draft.revision_summary.trim(),
    items: draft.items.map(item => tradePayload({ ...item, sku: Number(item.sku) })),
  }
}
const salesChecks = ref([]), salesCheckError = ref('')
let salesTimer, salesRequest = 0
async function checkSalesRules() {
  const request = ++salesRequest
  if (!draft.items.length || draft.items.some(i => !i.sku) || !draft.quote_date) { salesChecks.value = []; return false }
  try {
    const response = await api.post('/sales-rules/check-quote/', { quote_date: draft.quote_date, items: draft.items.map(i => ({ sku: Number(i.sku), quantity: baseQuantity(i) })) })
    if (request !== salesRequest) return false
    salesChecks.value = response.data; salesCheckError.value = ''
    return !response.data.some(row => row.errors.length)
  } catch (e) { if (request === salesRequest) { salesChecks.value = []; salesCheckError.value = e.message }; return false }
}
watch(() => JSON.stringify([draft.quote_date, draft.items.map(i => [i.sku, i.quantity, i.trade_unit])]), () => {
  ++salesRequest; salesChecks.value = []; salesCheckError.value = ''; clearTimeout(salesTimer)
  salesTimer = setTimeout(checkSalesRules, 300)
}, { immediate: true })
onBeforeUnmount(() => { clearTimeout(salesTimer); ++salesRequest; ++availabilityRequest; ++contactRequest })
async function openPreview() {
  errorMessage.value = validate()
  if (errorMessage.value) return
  clearTimeout(salesTimer)
  if (!await checkSalesRules()) { errorMessage.value = salesCheckError.value || '请先处理下方销售规则提示。'; return }
  try {
    const params = { discount: Number(draft.discount || 0) ? '1' : '0' }
    if (props.mode === 'revise') params.quote_id = props.quote.id
    previewTemplate.value = (await api.get('/quotes/preview-template/', { params })).data
    previewOpen.value = true
  } catch (e) { errorMessage.value = e.response?.data?.detail || '卖方或模板来源不可用，请核实后重试。' }
}
async function previewQuoteRisks(quote) {
  const skuIds = [...new Set((quote?.items || []).map(item => Number(item.sku)).filter(id => Number.isSafeInteger(id) && id > 0))]
  if (!skuIds.length) return []
  const response = await api.get('/quotes/risk-preview/', { params: { sku_ids: skuIds.join(',') } })
  return (response.data?.items || []).filter(item => item.has_risk)
}
async function prepareQuoteExport(quote) {
  riskRows.value = []
  riskCheckUnavailable.value = false
  try {
    riskRows.value = await previewQuoteRisks(quote)
  } catch {
    riskCheckUnavailable.value = true
  }
  if (riskCheckUnavailable.value || riskRows.value.length) {
    riskNoticeOpen.value = true
    return false
  }
  return true
}
function finishSavedQuote() {
  if (!savedQuote.value) return
  emit('saved', savedQuote.value)
  emit('close')
}
async function exportSavedQuote(quote) {
  try {
    await downloadQuoteExport(quote.id, quote.quote_no)
    finishSavedQuote()
    return true
  } catch (error) {
    exportError.value = `报价 ${quote.quote_no} 已保存，但 Excel 导出失败：${error.message}`
    return false
  }
}
async function continueRiskExport() {
  if (!savedQuote.value || saving.value) return
  riskNoticeOpen.value = false
  riskCheckUnavailable.value = false
  saving.value = true
  try { await exportSavedQuote(savedQuote.value) }
  finally { saving.value = false }
}
function cancelRiskExport() {
  riskNoticeOpen.value = false
  exportError.value = '报价已保存，可稍后重新导出 Excel。'
  riskCheckUnavailable.value = false
  finishSavedQuote()
}
async function save(shouldExport = false) {
  if (saving.value) return
  if (shouldExport && !can('quotes', 'export')) return
  errorMessage.value = validate()
  if (errorMessage.value) return
  saving.value = true; exportError.value = ''
  try {
    clearTimeout(salesTimer)
    if (!await checkSalesRules()) { errorMessage.value = salesCheckError.value || '请先处理下方销售规则提示。'; return }
    const response = props.mode === 'revise' ? await api.post(`/quotes/${props.quote.id}/revise/`, payload()) : await api.post('/quotes/', payload())
    guard.markClean()
    savedQuote.value = response.data
    if (!shouldExport) { finishSavedQuote(); return }
    await prepareQuoteExport(response.data)
    if (!riskNoticeOpen.value) await exportSavedQuote(response.data)
  } catch (error) { errorMessage.value = quoteSaveError(error) }
  finally { saving.value = false }
}
async function retryExport() {
  if (!savedQuote.value || !can('quotes', 'export')) return
  saving.value = true
  try {
    await prepareQuoteExport(savedQuote.value)
    if (!riskNoticeOpen.value) await exportSavedQuote(savedQuote.value)
  }
  finally { saving.value = false }
}
onMounted(async () => { if (props.mode === 'create' && draft.customer) await selectCustomer(); guard.markClean(); initialized.value = true; try { packagingTemplates.value = (await listAll('/packaging-templates/')).filter(item => item.active) } catch { packagingTemplates.value = [] } })
</script>

<template>
  <div class="modal-backdrop quote-editor-backdrop">
    <form ref="editorForm" class="modal wide quote-editor-modal" aria-label="报价编辑器" @submit.prevent="save(false)">
      <div class="modal-head"><div><h3>{{ mode === 'revise' ? '创建报价修订版' : '新建报价单' }}</h3><small>{{ mode === 'revise' ? `基于 ${quote.quote_no} 创建修订版；原报价保留。` : '报价单草稿' }}</small></div><button type="button" class="mini-btn" aria-label="关闭报价编辑器" @click="requestClose"><X :size="17" /></button></div>
      <div class="modal-body">
        <div v-if="errorMessage" class="quote-message error">{{ errorMessage }}</div>
        <div v-if="exportError" class="quote-message warning"><span>{{ exportError }}</span><button v-if="can('quotes', 'export')" type="button" class="btn btn-secondary" :disabled="saving" @click="retryExport"><RotateCw :size="15" /> 重新导出 Excel</button></div>
        <div v-if="draft.items.some(item => { const sku = skus.find(row => row.id === Number(item.sku)); return item.sku && !(item.sales_model_snapshot || sku?.sales_model) })" class="quote-message warning">有 SKU 尚未设置对外商业型号；报价仍可保存，但客户版 Model 将留空，请先确认是否需要补充。</div>
        <fieldset :disabled="!initialized || Boolean(savedQuote)">
          <div class="form-grid">
            <div class="field"><label>客户 *</label><select v-model="draft.customer" required :disabled="mode === 'revise' || inheritedCustomer" @change="selectCustomer"><option value="">请选择</option><option v-for="customer in customers" :key="customer.id" :value="customer.id">{{ customer.name }}</option></select></div>
            <div class="field"><label>报价单号</label><input :value="draft.quote_no || '保存后自动生成'" disabled /></div>
            <div class="field"><label>报价日期 *</label><SegmentedDateInput :model-value="draft.quote_date" required @update:model-value="setQuoteDate" /></div><div class="field"><label>有效期</label><div class="lead-time-input"><input v-model="validityDays" type="number" min="0" step="1" placeholder="天数" aria-label="有效期天数" @input="setValidityDays" /><span>天</span><SegmentedDateInput :model-value="draft.valid_until" @update:model-value="setValidUntil" /></div></div>
            <div class="field"><label>状态</label><input value="草稿" readonly /></div>
            <div class="field"><label>币种</label><select :value="draft.currency" aria-label="单据币种" @change="changeCurrency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
            <div class="field"><label>对人民币汇率</label><input v-model="draft.exchange_rate" :readonly="draft.currency === 'CNY'" aria-label="对人民币汇率" type="number" min="0" step="0.000001" /></div><div class="field"><label>交期（天）</label><input v-model="draft.lead_time_days" type="number" min="0" step="1" /></div>
            <div class="field"><label>定金比例（%）</label><input v-model="draft.deposit_percent" type="number" min="0" max="100" step="1" /></div>

            <div v-if="mode === 'revise'" class="field full revision-summary"><label>修订说明 *</label><textarea v-model="draft.revision_summary" required placeholder="例如：调整数量、价格、交期或付款条款" /><small>说明本次调整内容。</small></div>
          </div>
          <div class="items-head"><div><strong>报价明细</strong><small>选择 SKU 后填写数量、交易单位和单价。</small></div></div>
          <SkuPickerPanel class="sku-selection-panel" v-model="selectedSkuIds" v-model:active-id="activeSkuId" :skus="skus"><template #preview><label>客户版产品描述<small>可按本次报价调整</small><textarea v-if="activeItem" v-model="activeItem.description" aria-label="已选 SKU 的客户版产品描述" /></label></template></SkuPickerPanel>
          <div v-if="draft.items.length" class="quote-line-items"><div class="quote-line-header"><span>SKU</span><span>Model</span><span>数量 *</span><span>单价 *</span><span>产品描述</span><span>小计</span><span></span></div><div v-for="(item,index) in draft.items" :key="index" class="quote-line-row"><span class="quote-sku">{{ skus.find(sku => sku.id === Number(item.sku))?.sku || '—' }}<small v-if="currencyHint(skus.find(sku => sku.id === Number(item.sku)), draft.currency, item.unit_price)" class="currency-hint">{{ currencyHint(skus.find(sku => sku.id === Number(item.sku)), draft.currency, item.unit_price) }}</small><TradeUnitPicker :line="item" :sku="skus.find(sku => sku.id === Number(item.sku))" /><button type="button" class="text-btn" @click="draft.items.splice(index + 1, 0, { ...item })">增加规格行</button></span><input v-model.trim="item.sales_model_snapshot" aria-label="报价型号" placeholder="可按客户要求修改" /><input v-model="item.quantity" aria-label="数量" type="number" min="0.01" step="0.01" required /><input v-model="item.unit_price" v-money-input aria-label="单价" type="number" min="0" step="any" required /><input v-model="item.description" aria-label="产品描述" /><span class="amount">{{ money(Number(item.quantity) * Number(item.unit_price)) }}</span><button type="button" class="remove-line" aria-label="取消选择该 SKU" @click="draft.items.splice(index, 1)"><MinusCircle :size="17" /></button></div></div><p v-else class="quote-items-empty">请先从上方选择至少一个 SKU。</p>
          <section v-if="inventoryReferenceRows.length" class="quote-inventory-reference" aria-label="库存参考">
            <header class="quote-inventory-head"><div><strong>库存参考 · 按 SKU 基础单位</strong><small v-if="availabilityLastRefreshed">最近刷新 {{ availabilityLastRefreshed }}</small></div><button type="button" class="btn btn-secondary" :disabled="availabilityLoading" @click="refreshInventoryAvailability"><RotateCw :size="15" :class="{ spinning: availabilityLoading }" /> {{ availabilityLoading ? '正在刷新…' : '刷新库存' }}</button></header>
            <p class="quote-inventory-disclaimer">库存数据为当前参考值，报价不会锁定库存。在途数量不计入当前可用量，最终以订单确认时的库存及采购状态为准。</p>
            <p class="quote-inventory-lead-time">本报价参考交期：{{ Number(draft.lead_time_days || 0) }} 天</p>
            <p v-if="availabilityLoading" class="quote-inventory-state">正在读取库存参考…</p>
            <p v-else-if="availabilityError" class="quote-inventory-state warning">库存参考暂时无法读取，可继续报价。</p>
            <div class="quote-inventory-rows"><article v-for="row in inventoryReferenceRows" :key="row.skuId" class="quote-inventory-row">
              <div class="quote-inventory-row-head"><strong>{{ row.sku?.sku || row.skuId }} · {{ row.sku?.display_name_cn || row.sku?.product_name || 'SKU' }}</strong><span v-if="row.metrics" :class="row.shortage > 0 ? 'shortage' : 'covered'">{{ row.shortage > 0 ? '库存不足' : '库存可覆盖' }}</span><span v-else>暂无库存参考</span></div>
              <dl v-if="row.metrics"><div><dt>实际</dt><dd>{{ formatInventoryQuantity(row.metrics.actual_quantity) }} {{ row.unit }}</dd></div><div><dt>预留</dt><dd>{{ formatInventoryQuantity(row.metrics.reserved_quantity) }} {{ row.unit }}</dd></div><div><dt>可用</dt><dd>{{ formatInventoryQuantity(row.metrics.available_quantity) }} {{ row.unit }}</dd></div><div><dt>本报价需求</dt><dd>{{ formatInventoryQuantity(row.demand) }} {{ row.unit }}</dd></div><div><dt>在途</dt><dd>{{ formatInventoryQuantity(row.metrics.in_transit_quantity) }} {{ row.unit }}</dd></div></dl>
              <p v-if="row.metrics && row.shortage > 0" class="quote-inventory-shortage">缺口：{{ formatInventoryQuantity(row.shortage) }} {{ row.unit }}</p>
            </article></div>
          </section>
          <section v-if="salesCheckError || salesChecks.some(row => row.rules.length)" class="sales-rule-notices" aria-live="polite"><h4>销售规则校验</h4><p v-if="salesCheckError" class="sales-rule-error">{{ salesCheckError }}</p><div v-for="row in salesChecks.filter(r => r.rules.length)" :key="row.line"><strong>第 {{ row.line }} 行</strong><span v-for="rule in row.rules" :key="rule.id"> · {{ rule.name }}：最低 {{ Number(rule.minimum_quantity) }} {{ rule.unit }}</span><p v-for="message in row.errors" :key="message" class="sales-rule-error">{{ message }}</p></div></section>
          <section v-if="draft.items.length" class="packing-estimate"><div class="packing-head"><div><small>预计装箱方案</small><h4>按 SKU 默认包装配置估算</h4></div><button type="button" class="btn btn-secondary" @click="packingOpen = !packingOpen"><Box :size="15" /> {{ packingOpen ? '收起预计装箱方案' : '生成预计装箱方案' }}</button></div><template v-if="packingOpen"><div v-if="packingProjection.missing.length" class="packing-warning"><AlertTriangle :size="18" /><div><strong>以下 SKU 缺少包装配置，请补充。</strong><p>补充后会保存为该 SKU 的默认包装配置，供后续报价、订单和出货使用。</p><div class="packing-missing-list"><button v-for="sku in packingProjection.missing" :key="sku.id" type="button" @click="openPackaging(sku)"><Settings2 :size="14" /> {{ sku.sku }} · 补充默认包装</button></div></div></div><template v-else><div class="packing-summary"><div><span>预计件数</span><strong>{{ packingProjection.cartons.length }} 箱</strong></div><div><span>产品数量</span><strong>{{ packingProjection.totalPieces }}</strong></div><div><span>总净重</span><strong>{{ packingProjection.totalNet.toFixed(3) }} kg</strong></div><div><span>总重量</span><strong>{{ packingProjection.totalGross.toFixed(3) }} kg</strong></div><div><span>总体积</span><strong>{{ packingProjection.totalCbm.toFixed(4) }} m³</strong></div></div><p v-for="warning in packingProjection.warnings" :key="warning" class="packing-note">{{ warning }}</p><div class="packing-table-wrap"><table><thead><tr><th>SKU</th><th>件数</th><th>包装尺寸 (cm)</th><th>包装重量</th><th>单件体积</th><th>总体积</th></tr></thead><tbody><tr v-for="(carton, index) in packingProjection.cartons" :key="`${carton.sku.id}-${index}`"><td>{{ carton.sku.sku }}<small v-if="carton.partial">尾箱</small></td><td>{{ carton.quantity }}</td><td>{{ carton.length }} × {{ carton.width }} × {{ carton.height }}</td><td>{{ carton.gross.toFixed(3) }} kg</td><td>{{ carton.cbm.toFixed(4) }} m³</td><td>{{ carton.cbm.toFixed(4) }} m³</td></tr></tbody></table></div></template></template></section>
          <div class="totals"><label>运费 <input v-model="draft.shipping_fee" v-money-input type="number" step="any" /></label><label>折扣 <input v-model="draft.discount" v-money-input type="number" step="any" /></label><div><small>商品小计 {{ draft.currency }} {{ money(subtotal) }}</small><span>合计</span><strong>{{ draft.currency }} {{ money(total) }}</strong></div></div>
          <div class="items-head"><strong>收件信息 / 条款</strong></div>
          <div class="form-grid"><div class="field"><label for="quote-recipient">收件人</label><input id="quote-recipient" v-model="draft.recipient_name" @input="editRecipient('recipient_name')" /></div><div class="field"><label for="quote-buyer-tax-id">买方税号（选填）</label><input id="quote-buyer-tax-id" v-model="draft.buyer_tax_id" type="text" maxlength="200" :readonly="mode === 'revise' && quote?.can_revise_buyer_tax_id !== true" :placeholder="mode === 'revise' && draft.buyer_tax_id == null ? '历史未记录' : ''" /></div><div class="field full"><label for="quote-buyer-address">买方地址</label><textarea id="quote-buyer-address" v-model="draft.buyer_address" @input="editRecipient('buyer_address')" /></div><div class="field"><label for="quote-buyer-email">买方邮箱</label><input id="quote-buyer-email" v-model="draft.buyer_email" type="email" @input="editRecipient('buyer_email')" /></div><div class="field"><label for="quote-buyer-phone">买方电话</label><input id="quote-buyer-phone" v-model="draft.buyer_phone" @input="editRecipient('buyer_phone')" /></div></div>
          <div class="form-grid"><div class="field full"><label>贸易条款</label><textarea v-model="draft.trading_terms" /></div><div class="field full"><label>运输信息</label><textarea v-model="draft.shipping_details" /></div><div class="field full"><label>补充备注</label><textarea v-model="draft.notes" /></div></div>
        </fieldset>
      </div>
      <div class="modal-foot quote-editor-actions"><button type="button" class="btn btn-secondary quote-action-cancel" @click="requestClose">取消</button><button v-if="!savedQuote" type="button" class="btn btn-secondary quote-action-preview" @click="openPreview"><Eye :size="16" /> 预览报价单</button><button v-if="!savedQuote" type="button" class="btn btn-primary quote-action-save" :disabled="saving" @click="save(false)"><Save :size="16" /> {{ saving ? '保存中...' : '保存报价' }}</button><button v-if="!savedQuote && can('quotes', 'export')" type="button" class="btn btn-secondary quote-action-save-export" :disabled="saving" @click="save(true)"><Save :size="16" /> {{ saving ? '保存中...' : '保存并导出 Excel' }}</button></div>
    </form>
    <div v-if="packagingSku" class="modal-backdrop packaging-config-backdrop"><form class="modal packaging-config-modal" @submit.prevent="savePackaging"><div class="modal-head"><div><h3>补充 SKU 默认包装</h3><small>{{ packagingSku.sku }} · 保存后将作为该 SKU 的默认包装配置</small></div><button type="button" class="mini-btn" @click="requestPackagingClose"><X :size="17" /></button></div><div class="modal-body"><div class="form-grid"><div class="field full"><label>包装模板 *</label><select v-model="packagingForm.template" required><option value="">请选择包装模板</option><option v-for="template in packagingTemplates" :key="template.id" :value="template.id">{{ template.name }}<template v-if="template.supplier_name"> · {{ template.supplier_name }}</template></option></select></div><div class="field"><label>装箱数 (pcs) *</label><input v-model="packagingForm.qty_per_carton" type="number" min="0.01" step="0.01" required /></div><div class="field"><label>单件净重 (kg) *</label><input v-model="packagingForm.unit_net_weight" type="number" min="0" step="0.001" required /></div></div></div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="requestPackagingClose">取消</button><button class="btn btn-primary" :disabled="packagingSaving"><PackageCheck :size="15" /> {{ packagingSaving ? '保存中...' : '保存默认包装' }}</button></div></form></div>
    <QuotePreviewModal v-if="previewOpen" :draft="previewDraft" @close="previewOpen = false" />
     <QuoteRiskNotice v-if="riskNoticeOpen" :risks="riskRows" :risk-check-unavailable="riskCheckUnavailable" @cancel="cancelRiskExport" @continue="continueRiskExport" />
  </div>
</template>

<style scoped>
.quote-editor-backdrop{z-index:70;grid-template-columns:minmax(0,1fr)}
.quote-editor-modal,.quote-editor-modal .modal-body{min-width:0}
.quote-editor-modal fieldset > .form-grid:first-child{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.revision-summary textarea{min-height:64px}@media(max-width:850px){.quote-editor-modal fieldset > .form-grid:first-child{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.quote-editor-modal fieldset > .form-grid:first-child{grid-template-columns:1fr}}
.quote-editor-actions .btn{white-space:nowrap;flex:0 0 auto}
@media(max-width:480px){.quote-editor-modal .quote-editor-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));justify-content:stretch;gap:8px;padding:12px}.quote-editor-actions .btn{min-width:0;min-height:46px;padding:10px 12px;white-space:normal;line-height:1.35;text-align:center;word-break:normal;overflow-wrap:normal}.quote-editor-actions .quote-action-save,.quote-editor-actions .quote-action-save-export{grid-column:1/-1;width:100%}}
.quote-line-items{position:relative;overflow:visible}
@media(max-width:760px){.quote-line-items{overflow-x:auto}}
.quote-line-header{border-radius:10px 10px 0 0}
.quote-line-row{position:relative}
.quote-line-row:focus-within{z-index:20}
.quote-editor-modal > .modal-head,.quote-editor-modal > .modal-foot{z-index:21}
.quote-line-header,.quote-line-row{grid-template-columns:1.7fr 1fr .55fr .7fr 1.7fr .75fr 34px}
.quote-sku{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--text-body);color:#294a41}
.sku-selection-panel{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(270px,.85fr);height:268px;margin:0 0 14px;border:1px solid #dbe5df;border-radius:10px;overflow:hidden;background:#fff}.sku-picker-list{display:flex;flex-direction:column;min-width:0;border-right:1px solid #e4ece7}.sku-picker-head{padding:11px;border-bottom:1px solid #e8efeb}.sku-picker-head strong{display:block;margin-bottom:8px;font-size:var(--text-body)}.sku-picker-filters{display:grid;grid-template-columns:minmax(0,1fr) 130px;gap:7px}.sku-picker-head input,.sku-picker-head select{width:100%;border:1px solid #d7e1dc;border-radius:7px;padding:8px 10px;background:#fff;font-size:var(--text-body)}.sku-picker-options{flex:1 1 auto;min-height:0;overflow:auto}.sku-picker-options label{display:grid;grid-template-columns:18px minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 11px;cursor:pointer;border-bottom:1px solid #f0f4f1}.sku-picker-options label:hover,.sku-picker-options label.active{background:#eff8f4}.sku-picker-options input{margin:0}.sku-picker-options b,.sku-picker-options small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sku-picker-options b{font-size:var(--text-body);color:#23473d}.sku-picker-options small{margin-top:2px;color:#81908a;font-size:var(--text-caption)}.sku-picker-options .sku-identifiers{display:flex;gap:12px}.sku-picker-options .sku-identifiers span{min-width:0;overflow:hidden;text-overflow:ellipsis}.sku-picker-options em{font-style:normal;color:#436d60;font-size:var(--text-body)}.sku-picker-options p,.sku-picker-preview>p{margin:0;padding:18px;color:#81908a;font-size:var(--text-body)}.sku-picker-preview{padding:14px;background:#f7fbf9}.sku-picker-preview>small{display:block;color:#799087;font-size:var(--text-caption)}.sku-picker-preview>strong{display:block;margin:4px 0 10px;color:#1d4d40;font-size:var(--text-section)}.sku-picker-preview dl{margin:0 0 11px}.sku-picker-preview dl div{display:grid;grid-template-columns:105px 1fr;gap:8px;margin-top:5px;font-size:var(--text-body)}.sku-picker-preview dt{color:#7a8983}.sku-picker-preview dd{margin:0;color:#38564d}.sku-picker-preview label{display:block;color:#526d64;font-size:var(--text-body)}.sku-picker-preview textarea{display:block;width:100%;min-height:54px;margin-top:5px;border:1px solid #b8d3c7;border-radius:7px;padding:7px;resize:vertical;font:inherit;font-size:var(--text-body)}.quote-items-empty{margin:0 0 12px;padding:12px;border:1px dashed #cddbd4;border-radius:8px;text-align:center;color:#82918b;font-size:var(--text-body)}
.lead-time-input{display:flex;align-items:center;gap:6px}.lead-time-input>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.lead-time-input>span{color:#70817b;font-size:var(--text-body)}.lead-time-input :deep(.segmented-date){flex:1 1 auto;min-width:0}
.packing-estimate{margin-top:18px;padding:16px;border:1px solid #cfe2d8;border-radius:11px;background:#f8fbf9}.packing-head{display:flex;align-items:center;justify-content:space-between;gap:14px}.packing-head small{color:#648477;font-size:var(--text-caption);font-weight:700}.packing-head h4{margin:3px 0 0;color:#23473d;font-size:var(--text-section)}.packing-head .btn{padding:8px 11px;font-size:var(--text-body)}.packing-warning{display:flex;gap:10px;margin-top:14px;padding:13px;border:1px solid #f0cf9d;border-radius:8px;background:#fff8ec;color:#855817}.packing-warning strong{font-size:var(--text-body)}.packing-warning p{margin:4px 0 9px;font-size:var(--text-body);line-height:1.5}.packing-missing-list{display:flex;flex-wrap:wrap;gap:7px}.packing-missing-list button{display:inline-flex;align-items:center;gap:5px;border:1px solid #e2b970;border-radius:6px;background:#fff;color:#8b5d16;padding:6px 8px;cursor:pointer;font-size:var(--text-body)}.packing-missing-list button:hover{background:#fff1d7}.packing-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:14px}.packing-summary>div{padding:10px;border:1px solid #dce9e2;border-radius:8px;background:#fff}.packing-summary span,.packing-summary strong{display:block}.packing-summary span{color:#71877e;font-size:var(--text-caption)}.packing-summary strong{margin-top:4px;color:#204b40;font-size:var(--text-body);white-space:nowrap}.packing-note{margin:10px 0 0;color:#9a671d;font-size:var(--text-body)}.packing-table-wrap{margin-top:13px;overflow:auto;border:1px solid #dce8e2;border-radius:8px;background:#fff}.packing-table-wrap table{width:100%;min-width:710px;border-collapse:collapse;font-size:var(--text-body)}.packing-table-wrap th,.packing-table-wrap td{padding:9px 10px;border-bottom:1px solid #e7efea;text-align:left;white-space:nowrap}.packing-table-wrap th{background:#edf5f1;color:#628176;font-size:var(--text-body)}.packing-table-wrap tr:last-child td{border-bottom:0}.packing-table-wrap td small{display:block;margin-top:2px;color:#a66e27;font-size:var(--text-caption)}.packaging-config-backdrop{z-index:80}.packaging-config-modal{width:min(520px,calc(100vw - 28px))}.packaging-config-modal small{display:block;margin-top:4px;color:#71867d;font-size:var(--text-caption);font-weight:400}.packaging-config-modal select,.packaging-config-modal input{width:100%;height:38px;border:1px solid #d5e2dc;border-radius:7px;padding:0 10px;background:#fff}@media(max-width:850px){.packing-summary{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:520px){.packing-head{align-items:flex-start;flex-direction:column}.packing-summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
/* Keep the SKU list scrollbar visible instead of relying on overlay scrollbars. */
.sku-picker-options{overflow-y:scroll;scrollbar-gutter:stable;scrollbar-width:thin;scrollbar-color:#91afa3 #edf4f0}.sku-picker-options::-webkit-scrollbar{width:10px}.sku-picker-options::-webkit-scrollbar-track{background:#edf4f0;border-left:1px solid #dce9e2}.sku-picker-options::-webkit-scrollbar-thumb{background:#91afa3;border:2px solid #edf4f0;border-radius:999px}.sku-picker-options::-webkit-scrollbar-thumb:hover{background:#5e8978}
.sku-picker-list{min-height:0;overflow:hidden}.sku-picker-options{height:0;flex:1 1 0}
@media(max-width:720px){
  .sku-selection-panel{grid-template-columns:minmax(0,1fr);grid-template-rows:190px auto;height:auto}
  .quote-editor-modal{scroll-padding-block:90px 150px}
}
@media(max-width:560px){.sku-picker-filters{grid-template-columns:1fr}.sku-picker-options .sku-identifiers{display:block}.sku-picker-options .sku-identifiers span{display:block}}
.currency-hint{display:block!important;white-space:normal!important;overflow:visible!important;color:#8b602c!important;font-size:var(--text-caption);line-height:1.5;margin-top:5px}
</style>

<style scoped>
.sales-rule-notices{padding:14px;background:#f2f8f5;border:1px solid #d9e6df;border-radius:8px;margin:12px 0;font-size:13px}.sales-rule-notices h4{margin:0 0 10px}.sales-rule-notices>div{padding:6px 0}.sales-rule-error{color:#b42318}
.quote-inventory-reference{margin:12px 0 16px;padding:14px;border:1px solid #cfe1d7;border-radius:10px;background:#f8fbf9;color:#35564b}.quote-inventory-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.quote-inventory-head>div{display:grid;gap:3px}.quote-inventory-head>div>strong{font-size:var(--text-body)}.quote-inventory-head small{color:#80938a;font-size:var(--text-caption)}.quote-inventory-head .btn{flex:none;padding:7px 10px;font-size:var(--text-body)}.quote-inventory-disclaimer{margin:9px 0;padding:8px 10px;border-radius:7px;background:#edf5f0;color:#607a6f;font-size:var(--text-caption);line-height:1.5}.quote-inventory-state{margin:8px 0;color:#6b8177;font-size:var(--text-body)}.quote-inventory-state.warning{color:#9a6419}.quote-inventory-rows{display:grid;gap:8px}.quote-inventory-row{padding:10px 11px;border:1px solid #e1ebe5;border-radius:8px;background:#fff}.quote-inventory-row-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.quote-inventory-row-head>strong{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#2a5144;font-size:var(--text-body)}.quote-inventory-row-head>span{flex:none;color:#71857b;font-size:var(--text-caption)}.quote-inventory-row-head>span.covered{color:#24724f}.quote-inventory-row-head>span.shortage{color:#ad3737}.quote-inventory-row dl{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin:8px 0 0}.quote-inventory-row dl>div{min-width:0;padding:6px 8px;border-radius:6px;background:#f5f8f6}.quote-inventory-row dt{color:#819087;font-size:var(--text-caption)}.quote-inventory-row dd{margin:3px 0 0;color:#294d41;font-size:var(--text-body);font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}.quote-inventory-shortage{margin:8px 0 0;color:#ad3737;font-size:var(--text-body);font-weight:700}@media(max-width:760px){.quote-inventory-row dl{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:480px){.quote-inventory-head{align-items:flex-start;flex-direction:column}.quote-inventory-row dl{grid-template-columns:repeat(2,minmax(0,1fr))}}
.currency-hint{display:block!important;white-space:normal!important;overflow:visible!important;color:#8b602c!important;font-size:var(--text-caption);line-height:1.5;margin-top:5px}
</style>
