<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import { defaultExchangeRate, skuDefaultPrice, currencyHint, salesRateError, changeDocumentCurrency } from '../utils/documentCurrency'
import { confirmDialog } from '../dialogs'
import { compactDecimalInput } from '../utils/decimalInput'
import TradeUnitPicker from './TradeUnitPicker.vue'
import { fromTradeLine, tradePayload, baseQuantity, tradeLabel, withDefaultTradeUnit, restoreTradeLines } from '../utils/tradeUnits'
import { computed, reactive, ref, watch } from 'vue'
import { MinusCircle, X } from 'lucide-vue-next'

import SegmentedDateInput from './SegmentedDateInput.vue'
import SkuPickerPanel from './SkuPickerPanel.vue'
import { addDays, daysBetween } from '../utils/orderDate'

const props = defineProps({
  draft: { type: Object, required: true },
  customers: { type: Array, default: () => [] },
  skus: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'saved'])
const saving = ref(false)
const error = ref('')
const form = reactive({})
const guard = useUnsavedChangesGuard({ data: () => form })
const requestClose = () => guard.requestClose(() => emit('close'))
const leadTimeDays = ref('')
const tailPolicyHelpOpen = ref(false)
const tailPolicyLabels = { SAME_CARTON: '整箱优先', REPACK: '尾箱待确认', MANUAL: '人工装箱' }

function resetForm(draft) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, {
    ...draft,
    exchange_rate: compactDecimalInput(draft.exchange_rate),
    tail_goods_policy: draft.tail_goods_policy || 'SAME_CARTON',
    customer: draft.customer ? Number(draft.customer) : '',
    quote: draft.quote ? Number(draft.quote) : '',
    items: (draft.items || []).map((item) => ({
      ...item,
      _historical_trade_unit: item.trade_unit,
      sku: item.sku ? Number(item.sku) : '',
      quantity: Number(item.trade_quantity ?? item.quantity ?? 0),
      unit_price: Number(item.trade_unit_price ?? item.unit_price ?? 0),
      cost_price: Number(item.cost_price || 0),
    })),
  })
  leadTimeDays.value = daysBetween(draft.order_date, draft.expected_ship_date)
  guard.markClean()
}
watch(() => props.draft, resetForm, { immediate: true, deep: true })

function selectSku(item) {
  const sku = props.skus.find((row) => row.id === Number(item.sku))
  if (sku) {
    item.unit_price = skuDefaultPrice(sku, form.currency)
    item.cost_price = Number(sku.cost_price || 0)
  }
}
const activeSkuId = ref('')
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
    return withDefaultTradeUnit(item, props.skus.find(s => s.id === Number(id)))
  })())
  form.items = restoreTradeLines(form.items, previousLines)
  if (!selected.includes(String(activeSkuId.value))) activeSkuId.value = selected[0] || ''
}
async function changeCurrency(event) {
  const currency = event.target.value
  event.target.value = form.currency
  await changeDocumentCurrency(form, currency, props.skus, confirmDialog)
  event.target.value = form.currency
}
function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
const subtotal = computed(() => (form.items || []).reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0))
const total = computed(() => subtotal.value + Number(form.shipping_fee || 0) - Number(form.discount || 0))

function setOrderDate(value) {
  form.order_date = value
  if (leadTimeDays.value !== '') form.expected_ship_date = addDays(value, leadTimeDays.value)
  else if (form.expected_ship_date) leadTimeDays.value = daysBetween(value, form.expected_ship_date)
}
function setExpectedShipDate(value) {
  form.expected_ship_date = value
  leadTimeDays.value = daysBetween(form.order_date, value)
}
function setLeadTimeDays() {
  if (leadTimeDays.value === '' || !form.order_date) return
  form.expected_ship_date = addDays(form.order_date, leadTimeDays.value)
}

async function save() {
  if (saving.value) return
  if (!form.items?.length || form.items.some((item) => !item.sku)) {
    error.value = '请至少保留一条有效的 SKU 明细。'
    return
  }
  if (salesRateError(form)) { error.value = salesRateError(form); return }
  if (form.items.some(item => item.unit_price === '' || item.unit_price == null || Number(item.unit_price) < 0)) { error.value = '请填写每条 SKU 的本次售价。'; return }
  saving.value = true
  error.value = ''
  const draftPayload = { ...form }
  delete draftPayload.status
  delete draftPayload.order_no
  const payload = {
    ...draftPayload,
    customer: Number(form.customer),
    quote: Number(form.quote),
    expected_ship_date: form.expected_ship_date || null,
    items: form.items.map((item) => tradePayload({ ...item, sku: Number(item.sku) })),
  }
  try { const response = await api.post('/orders/', payload); guard.markClean(); emit('saved', response.data) }
  catch (err) { error.value = err.message }
  finally { saving.value = false }
}
</script>

<template>
  <div class="modal-backdrop order-draft-backdrop" @mousedown.self="requestClose">
    <form class="modal wide order-draft-modal" role="dialog" aria-modal="true" aria-label="销售订单草稿" @submit.prevent="save">
      <div class="modal-head">
        <div><h3>新建销售订单</h3><p>来源报价：{{ draft.source_quote_no || draft.quote_no || '—' }}</p></div>
        <button type="button" class="mini-btn" aria-label="关闭订单草稿" @click="requestClose"><X :size="18" /></button>
      </div>
      <div class="modal-body">
        <p class="draft-hint">商品已从报价带入。保存后为销售订单草稿；确认订单后才会预留库存并生成应收计划。</p>
        <div class="form-grid">
          <div class="field"><label>销售订单号</label><input value="保存后由系统自动生成" readonly aria-label="销售订单号保存后自动生成" /></div>
          <div class="field"><label>客户 *</label><input :value="customers.find((customer) => customer.id === Number(form.customer))?.name || '—'" readonly aria-label="来源报价客户" /></div>
          <div class="field"><label>订单日期 *</label><SegmentedDateInput :model-value="form.order_date" required @update:model-value="setOrderDate" /></div>
          <div class="field"><label>预计出货日期</label><div class="lead-time-input"><input v-model="leadTimeDays" type="number" min="0" step="1" placeholder="天数" aria-label="出货日期天数" @input="setLeadTimeDays" /><span>天</span><SegmentedDateInput :model-value="form.expected_ship_date" @update:model-value="setExpectedShipDate" /></div></div>
          <div class="field"><label>状态</label><input value="草稿" readonly /><small class="field-hint">保存后可在订单工作台确认订单。</small></div>
          <div class="field tail-policy-field"><label>尾货策略 <button type="button" class="policy-help-trigger" aria-label="查看尾货策略说明" @click="tailPolicyHelpOpen = !tailPolicyHelpOpen">?</button></label><select v-model="form.tail_goods_policy"><option v-for="(label, key) in tailPolicyLabels" :key="key" :value="key">{{ label }}</option></select><div v-if="tailPolicyHelpOpen" class="policy-help" role="note"><strong>不同策略的区别</strong><ul><li><b>整箱优先：</b>尾货自动使用标准箱尺寸、皮重和 CBM。</li><li><b>尾箱待确认：</b>保留尾货箱数并标记待确认，尺寸和 CBM 等待补充。</li><li><b>人工装箱：</b>不自动生成尾货箱，余数作为警告交由人工处理。</li></ul><small>此选择对整张订单统一生效，优先于 SKU 包装模板。</small></div></div>
          <div class="field"><label>币种</label><select :value="form.currency" aria-label="单据币种" @change="changeCurrency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
          <div class="field"><label>对人民币汇率</label><input v-model="form.exchange_rate" :readonly="form.currency === 'CNY'" aria-label="对人民币汇率" type="number" step="0.000001" /></div>
        </div>
        <div class="items-head"><div><strong>订单明细</strong><small>先选择一个或多个 SKU，再填写数量与价格。</small></div></div>
        <SkuPickerPanel v-model="selectedSkuIds" v-model:active-id="activeSkuId" :skus="skus" />
        <div class="line-items"><div class="line-header"><span>SKU / Model</span><span>数量 *</span><span>单价 *</span><span>成本</span><span>小计</span><span /></div><div v-for="(item, index) in form.items" :key="index" class="line-row"><span class="sku-cell"><b>{{ skus.find(sku => sku.id === Number(item.sku))?.display_name_cn || skus.find(sku => sku.id === Number(item.sku))?.product_name || '—' }}</b><small>SKU: {{ skus.find(sku => sku.id === Number(item.sku))?.sku_code || item.sku || '—' }} · Sales Model: {{ skus.find(sku => sku.id === Number(item.sku))?.sales_model || '—' }}</small><small v-if="currencyHint(skus.find(sku => sku.id === Number(item.sku)), form.currency, item.unit_price)" class="currency-hint">{{ currencyHint(skus.find(sku => sku.id === Number(item.sku)), form.currency, item.unit_price) }}</small><TradeUnitPicker :line="item" :sku="skus.find(sku => sku.id === Number(item.sku))" /><button type="button" class="text-btn" @click="form.items.splice(index + 1, 0, { ...item })">增加规格行</button></span><input v-model="item.quantity" type="number" min="0.01" step="0.01" required /><input v-model="item.unit_price" v-money-input type="number" min="0" step="any" required /><input v-model="item.cost_price" v-money-input type="number" min="0" step="any" /><span class="amount">{{ money(Number(item.quantity) * Number(item.unit_price)) }}</span><button type="button" class="remove-line" @click="form.items.splice(index, 1)"><MinusCircle :size="17" /></button></div><p v-if="!form.items.length" class="quote-items-empty">请先从上方选择至少一个 SKU。</p></div>
        <div class="totals"><label>运费 <input v-model="form.shipping_fee" v-money-input type="number" step="any" /></label><label>折扣 <input v-model="form.discount" v-money-input type="number" step="any" /></label><div><small>商品小计 {{ form.currency }} {{ money(subtotal) }}</small><span>合计</span><strong>{{ form.currency }} {{ money(total) }}</strong></div></div>
        <div class="field notes"><label>贸易条款 / 备注</label><textarea v-model="form.notes" /></div>
        <p v-if="error" class="draft-error">{{ error }}</p>
      </div>
      <div class="modal-foot"><button type="button" class="btn btn-secondary" @click="requestClose">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存销售订单草稿' }}</button></div>
    </form>
  </div>
</template>

<style scoped>
.order-draft-backdrop{z-index:90;display:grid;place-items:center;padding:24px;background:#07191478;backdrop-filter:blur(3px)}.order-draft-modal{width:min(980px,100%);max-height:92vh;overflow:auto}.modal-head h3{margin:0}.modal-head p{margin:4px 0 0;color:#71817b;font-size:var(--text-body)}.draft-hint{margin:0 0 18px;padding:10px 12px;border-radius:8px;background:#eff7f2;color:#49675d;font-size:var(--text-caption)}.lead-time-input{display:flex;align-items:center;gap:6px}.lead-time-input>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.lead-time-input>span{color:#70817b;font-size:var(--text-body)}.lead-time-input :deep(.segmented-date){flex:1 1 auto;min-width:0}.tail-policy-field{position:relative}.policy-help-trigger{display:inline-grid;place-items:center;width:18px;height:18px;margin-left:4px;border:1px solid #83ab9d;border-radius:50%;background:#f3faf6;color:#26715d;font:700 var(--text-caption)/1 inherit;cursor:pointer}.policy-help-trigger:hover{background:#dff1e8}.policy-help{position:relative;z-index:2;margin-top:8px;padding:10px 12px;border:1px solid #bed8cc;border-radius:8px;background:#f7fcf9;color:#3e5e53;font-size:var(--text-caption);line-height:1.55;box-shadow:0 5px 13px #173f3612}.policy-help strong,.policy-help small{display:block}.policy-help ul{margin:6px 0;padding-left:18px}.policy-help li+li{margin-top:3px}.policy-help small{color:#6c8379}.items-head{display:flex;justify-content:space-between;align-items:center;margin:25px 0 10px;padding-top:21px;border-top:1px solid #e5eae7}.items-head strong,.items-head small{display:block}.items-head small{margin-top:3px;color:#82908b;font-size:var(--text-caption)}.line-items{border:1px solid #e0e6e2;border-radius:10px;overflow:hidden}.line-header,.line-row{display:grid;grid-template-columns:2fr .55fr .7fr .7fr .8fr 34px;gap:8px;align-items:center;padding:8px 10px}.line-header{background:#f5f8f6;color:#7a8984;font-size:var(--text-caption);text-transform:uppercase}.line-row{border-top:1px solid #edf0ee}.line-row select,.line-row input{min-width:0;width:100%;border:1px solid #dce3df;border-radius:7px;padding:8px;font-size:var(--text-body)}.line-row .amount{text-align:right}.remove-line{border:0;background:transparent;color:#b05b5b;display:grid;place-items:center}.remove-line:disabled{opacity:.25}.totals{display:flex;justify-content:flex-end;gap:14px;align-items:end;margin:15px 0 22px}.totals label{color:#778680;font-size:var(--text-body)}.totals input{display:block;width:105px;margin-top:5px;border:1px solid #dce3df;border-radius:7px;padding:8px}.totals div{border-left:1px solid #dae2de;padding-left:18px}.totals span,.totals strong{display:block}.totals span{color:#788680;font-size:var(--text-body)}.totals strong{margin-top:5px;color:#123c36;font-size:var(--text-dialog)}.notes textarea{min-height:65px}.draft-error{margin:14px 0 0;color:#a64444;font-size:var(--text-body)}@media(max-width:700px){.order-draft-backdrop{padding:10px}.line-items{overflow:auto}.line-header,.line-row{min-width:720px}.totals{flex-wrap:wrap}}
.sku-cell{min-width:0}.sku-cell b,.sku-cell small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sku-cell b{color:#294a41;font-size:var(--text-body)}.sku-cell small{margin-top:3px;color:#81908a;font-size:var(--text-caption)}
.policy-help{position:absolute;z-index:12;top:48px;left:0;width:min(360px,calc(100vw - 64px));margin:0;box-shadow:0 8px 20px #173f3624}
.currency-hint{display:block!important;white-space:normal!important;overflow:visible!important;color:#8b602c!important;font-size:var(--text-caption);line-height:1.5;margin-top:5px}
</style>
