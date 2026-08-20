<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { MinusCircle, PlusCircle, X } from 'lucide-vue-next'
import { api } from '../api'
import SegmentedDateInput from './SegmentedDateInput.vue'
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
const leadTimeDays = ref('')

function resetForm(draft) {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, {
    ...draft,
    customer: draft.customer ? Number(draft.customer) : '',
    quote: draft.quote ? Number(draft.quote) : '',
    items: (draft.items || []).map((item) => ({
      ...item,
      sku: item.sku ? Number(item.sku) : '',
      quantity: Number(item.quantity || 0),
      unit_price: Number(item.unit_price || 0),
      cost_price: Number(item.cost_price || 0),
    })),
  })
  leadTimeDays.value = daysBetween(draft.order_date, draft.expected_ship_date)
}
watch(() => props.draft, resetForm, { immediate: true, deep: true })

function selectSku(item) {
  const sku = props.skus.find((row) => row.id === Number(item.sku))
  if (sku) {
    item.unit_price = Number(sku.default_price || 0)
    item.cost_price = Number(sku.cost_price || 0)
  }
}
function addItem() { form.items.push({ sku: '', quantity: 1, unit_price: 0, cost_price: 0, notes: '' }) }
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
  if (!form.items?.length || form.items.some((item) => !item.sku)) {
    error.value = '请至少保留一条有效的 SKU 明细。'
    return
  }
  saving.value = true
  error.value = ''
  const payload = {
    ...form,
    customer: Number(form.customer),
    quote: Number(form.quote),
    items: form.items.map((item) => ({ ...item, sku: Number(item.sku) })),
  }
  try { emit('saved', (await api.post('/orders/', payload)).data) }
  catch (err) { error.value = err.message }
  finally { saving.value = false }
}
</script>

<template>
  <div class="modal-backdrop order-draft-backdrop" @mousedown.self="emit('close')">
    <form class="modal wide order-draft-modal" role="dialog" aria-modal="true" aria-label="订单草稿" @submit.prevent="save">
      <div class="modal-head">
        <div><h3>创建订单草稿</h3><p>来源报价：{{ draft.source_quote_no || draft.quote_no || '—' }}</p></div>
        <button type="button" class="mini-btn" aria-label="关闭订单草稿" @click="emit('close')"><X :size="18" /></button>
      </div>
      <div class="modal-body">
        <p class="draft-hint">订单草稿由当前报价版本预填。若修改商品、价格、币种、汇率、运费、折扣或条款，保存时会自动生成一份报价迭代版并关联订单。</p>
        <div class="form-grid">
          <div class="field"><label>订单编号 *</label><input v-model="form.order_no" required /></div>
          <div class="field"><label>客户 *</label><input :value="customers.find((customer) => customer.id === Number(form.customer))?.name || '—'" readonly aria-label="来源报价客户" /></div>
          <div class="field"><label>订单日期 *</label><SegmentedDateInput :model-value="form.order_date" required @update:model-value="setOrderDate" /></div>
          <div class="field"><label>预计交期</label><div class="lead-time-input"><input v-model="leadTimeDays" type="number" min="0" step="1" placeholder="天数" aria-label="交期天数" @input="setLeadTimeDays" /><span>天</span><SegmentedDateInput :model-value="form.expected_ship_date" @update:model-value="setExpectedShipDate" /></div></div>
          <div class="field"><label>状态 *</label><select v-model="form.status"><option value="draft">草稿</option><option value="confirmed">已确认</option><option value="production">生产中</option><option value="shipped">已发货</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select></div>
          <div class="field"><label>币种</label><select v-model="form.currency"><option>USD</option><option>CNY</option><option>EUR</option><option>GBP</option></select></div>
          <div class="field"><label>对人民币汇率</label><input v-model="form.exchange_rate" type="number" step="0.000001" /></div>
        </div>
        <div class="items-head"><div><strong>订单明细</strong><small>保存时将以这里的商品、数量与价格创建订单。</small></div><button type="button" class="btn btn-secondary" @click="addItem"><PlusCircle :size="15" /> 添加一行</button></div>
        <div class="line-items"><div class="line-header"><span>SKU</span><span>数量</span><span>单价</span><span>成本</span><span>小计</span><span /></div><div v-for="(item, index) in form.items" :key="index" class="line-row"><select v-model="item.sku" required @change="selectSku(item)"><option value="">选择 SKU</option><option v-for="sku in skus" :key="sku.id" :value="sku.id">{{ sku.sku }} · {{ sku.product_name }}</option></select><input v-model="item.quantity" type="number" min="0.01" step="0.01" required /><input v-model="item.unit_price" type="number" min="0" step="0.0001" required /><input v-model="item.cost_price" type="number" min="0" step="0.0001" /><span class="amount">{{ money(Number(item.quantity) * Number(item.unit_price)) }}</span><button type="button" class="remove-line" :disabled="form.items.length === 1" @click="form.items.splice(index, 1)"><MinusCircle :size="17" /></button></div></div>
        <div class="totals"><label>运费 <input v-model="form.shipping_fee" type="number" step="0.01" /></label><label>折扣 <input v-model="form.discount" type="number" step="0.01" /></label><div><span>合计</span><strong>{{ form.currency }} {{ money(total) }}</strong></div></div>
        <div class="field notes"><label>条款 / 备注</label><textarea v-model="form.notes" /></div>
        <p v-if="error" class="draft-error">{{ error }}</p>
      </div>
      <div class="modal-foot"><button type="button" class="btn btn-secondary" @click="emit('close')">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存订单' }}</button></div>
    </form>
  </div>
</template>

<style scoped>
.order-draft-backdrop{z-index:90;display:grid;place-items:center;padding:24px;background:#07191478;backdrop-filter:blur(3px)}.order-draft-modal{width:min(980px,100%);max-height:92vh;overflow:auto}.modal-head h3{margin:0}.modal-head p{margin:4px 0 0;color:#71817b;font-size:12px}.draft-hint{margin:0 0 18px;padding:10px 12px;border-radius:8px;background:#eff7f2;color:#49675d;font-size:12px}.lead-time-input{display:flex;align-items:center;gap:6px}.lead-time-input>input{flex:0 0 10ch!important;width:10ch!important;min-width:0}.lead-time-input>span{color:#70817b;font-size:12px}.lead-time-input :deep(.segmented-date){flex:1 1 auto;min-width:0}.items-head{display:flex;justify-content:space-between;align-items:center;margin:25px 0 10px;padding-top:21px;border-top:1px solid #e5eae7}.items-head strong,.items-head small{display:block}.items-head small{margin-top:3px;color:#82908b;font-size:11px}.line-items{border:1px solid #e0e6e2;border-radius:10px;overflow:hidden}.line-header,.line-row{display:grid;grid-template-columns:2fr .55fr .7fr .7fr .8fr 34px;gap:8px;align-items:center;padding:8px 10px}.line-header{background:#f5f8f6;color:#7a8984;font-size:10px;text-transform:uppercase}.line-row{border-top:1px solid #edf0ee}.line-row select,.line-row input{min-width:0;width:100%;border:1px solid #dce3df;border-radius:7px;padding:8px;font-size:12px}.line-row .amount{text-align:right}.remove-line{border:0;background:transparent;color:#b05b5b;display:grid;place-items:center}.remove-line:disabled{opacity:.25}.totals{display:flex;justify-content:flex-end;gap:14px;align-items:end;margin:15px 0 22px}.totals label{color:#778680;font-size:11px}.totals input{display:block;width:105px;margin-top:5px;border:1px solid #dce3df;border-radius:7px;padding:8px}.totals div{border-left:1px solid #dae2de;padding-left:18px}.totals span,.totals strong{display:block}.totals span{color:#788680;font-size:11px}.totals strong{margin-top:5px;color:#123c36;font-size:20px}.notes textarea{min-height:65px}.draft-error{margin:14px 0 0;color:#a64444;font-size:12px}@media(max-width:700px){.order-draft-backdrop{padding:10px}.line-items{overflow:auto}.line-header,.line-row{min-width:720px}.totals{flex-wrap:wrap}}
</style>
