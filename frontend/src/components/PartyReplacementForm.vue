<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, listAll } from '../api'
import { formatApiError } from '../utils/apiErrors'

const props = defineProps({ kind: { type: String, required: true }, sourceId: { type: [String, Number], required: true },
  sourcePartyId: { type: [String, Number], default: null }, baseline: { type: Object, default: null },
  request: { type: Object, default: null }, mode: { type: String, required: true } })
const emit = defineEmits(['completed'])
const moduleName = computed(() => props.kind === 'quote' ? 'quotes' : props.kind === 'order' ? 'orders' : 'purchase-orders')
const endpoint = computed(() => `/${moduleName.value}/${props.sourceId}/party-change/`)
const partyKey = computed(() => props.kind === 'purchase_order' ? 'supplier' : 'customer')
const fields = computed(() => [['name','名称'], ...(props.kind !== 'purchase_order' ? [['country','国家 / 地区']] : []), ['address','地址'], ['contact','联系人'], ['phone','电话'], ['email','邮箱'], ...(props.kind === 'quote' ? [['tax_id','税号']] : [])])
const masters = ref([]), skus = ref([]), targetId = ref(''), proposed = ref({}), reason = ref(''), evidence = ref('')
const structured = ref(null), unknownConfirmed = ref(false)
const busy = ref(false), loading = ref(true), error = ref('')
const date = ref(''), currency = ref(''), exchangeRate = ref(''), shipping = ref(''), discount = ref(''), deposit = ref('')
const tailGoodsPolicy = ref('')
const tradingTerms = ref(''), shippingDetails = ref(''), notes = ref(''), termsConfirmed = ref(false)
const paymentMode = ref(''), paymentStages = ref([{ label: '', ratio: '', due_basis: '', offset_days: '' }])
const rows = ref([{ sku: '', quantity: '', unit_price: '' }])
const available = computed(() => masters.value.filter(row => String(row.id) !== String(props.sourcePartyId)))
onMounted(async () => {
  try {
    if (props.mode === 'propose') {
      masters.value = await listAll(props.kind === 'purchase_order' ? '/suppliers/' : '/customers/', props.kind === 'purchase_order' ? { params: { active_only: 1 } } : {})
      proposed.value = Object.fromEntries(fields.value.map(([key]) => [key, null]))
      const original = props.baseline?.snapshot?.party_details
      if (original) structured.value = { schema: original.schema, buyer: Object.fromEntries(Object.keys(original.buyer || {}).map(key => [key, null])), seller: Object.fromEntries(Object.keys(original.seller || {}).map(key => [key, null])) }
    } else skus.value = (await listAll('/skus/')).filter(row => row.active !== false)
  } catch (err) { error.value = formatApiError(err?.response?.data) || '资料读取失败，请关闭后重试。' }
  finally { loading.value = false }
})
function chooseTarget() {
  const target = available.value.find(row => String(row.id) === String(targetId.value))
  proposed.value.name = target?.name || ''
  if (structured.value) structured.value[props.kind === 'purchase_order' ? 'seller' : 'buyer'].name = target?.name || null
}
async function submit() {
  if (busy.value || loading.value) return
  error.value = ''
  let body, url = endpoint.value
  if (props.mode === 'propose') {
    if (!targetId.value || !reason.value.trim() || !evidence.value.trim() || fields.value.some(([key]) => typeof proposed.value[key] !== 'string') || (structured.value && !unknownConfirmed.value)) {
      error.value = '请选择目标并填写主体资料、原因和依据。'; return
    }
    body = { expected_base_fingerprint: props.baseline?.fingerprint, proposed_snapshot: { ...proposed.value, ...(structured.value ? { party_details: structured.value } : {}) },
      change_type: 'replacement', replacement_target_id: Number(targetId.value), reason: reason.value.trim(), evidence: evidence.value.trim(), source_trust: 'unverified' }
  } else {
    if (!date.value || !currency.value.trim() || !exchangeRate.value || rows.value.some(row => !row.sku || !row.quantity || row.unit_price === '') || !termsConfirmed.value ||
      (props.kind !== 'purchase_order' && (shipping.value === '' || discount.value === '')) || (props.kind === 'quote' && deposit.value === '') || (props.kind === 'order' && !tailGoodsPolicy.value) ||
      (props.kind === 'purchase_order' && (!paymentMode.value || (paymentMode.value === 'stages' && paymentStages.value.some(stage => !stage.label.trim() || !stage.ratio || !stage.due_basis || stage.offset_days === ''))))) {
      error.value = '请填写日期、币种、汇率、商品、金额与条款，并确认资料完整。'; return
    }
    const target = props.request?.replacement_target
    const id = target?.[partyKey.value + '_id']
    if (!id) { error.value = '申请缺少已批准的目标，不能创建新单。'; return }
    body = { [partyKey.value]: id, [props.kind === 'quote' ? 'quote_date' : 'order_date']: date.value,
      currency: currency.value.trim(), exchange_rate: exchangeRate.value, notes: notes.value,
      items: rows.value.map(row => ({ sku: Number(row.sku), quantity: row.quantity, unit_price: row.unit_price })) }
    if (props.kind !== 'purchase_order') Object.assign(body, { shipping_fee: shipping.value, discount: discount.value })
    if (props.kind === 'order') body.tail_goods_policy = tailGoodsPolicy.value
    if (props.kind === 'quote') {
      const p = props.request.proposed_snapshot
      Object.assign(body, { recipient_name: p.contact, buyer_address: p.address, buyer_phone: p.phone, buyer_email: p.email,
        buyer_tax_id: p.tax_id, deposit_ratio: deposit.value, trading_terms: tradingTerms.value, shipping_details: shippingDetails.value })
    } else if (props.kind === 'purchase_order') body.payment_terms_snapshot = paymentMode.value === 'none' ? [] : paymentStages.value.map(stage => ({ ...stage, offset_days: Number(stage.offset_days) }))
    url += `${props.request.id}/create-replacement/`
  }
  busy.value = true
  try { const response = await api.post(url, body); emit('completed', response.data) }
  catch (err) { error.value = formatApiError(err?.response?.data) || '提交失败，请核对后重试。' }
  finally { busy.value = false }
}
</script>

<template>
  <div class="replacement-form">
    <p v-if="loading" role="status">正在读取可选资料…</p>
    <p v-if="error" role="alert" class="replacement-error">{{ error }}</p>
    <template v-if="mode === 'propose'">
      <p>请选择新的法律主体并人工填写资料；提交后须由另一认证账号审批。原单及其历史事实保持不变。</p>
      <p v-if="structured" class="replacement-error">扩展资料须重新填写；未填写的字段将记录为未知。现有报价模板尚不能展示完整扩展资料，报价暂不能创建替换新单。</p>
      <label>目标{{ partyKey === 'supplier' ? '供应商' : '客户' }}<select v-model="targetId" :disabled="loading || busy" @change="chooseTarget"><option value="">请选择</option><option v-for="row in available" :key="row.id" :value="row.id">{{ row.name }} · {{ row.code }}</option></select></label>
      <label v-for="[key, label] in fields" :key="key">拟议{{ label }}<input :value="proposed[key] ?? ''" :placeholder="proposed[key] == null ? '请填写或确认留空' : ''" :disabled="busy || key === 'name'" @input="proposed[key] = $event.target.value" /><button v-if="key !== 'name' && proposed[key] == null" type="button" @click="proposed[key] = ''">确认留空</button></label>
      <template v-if="structured"><fieldset v-for="side in ['buyer', 'seller']" :key="side"><legend>{{ side === 'buyer' ? '买方扩展资料' : '卖方扩展资料' }}</legend><label v-for="(value, key) in structured[side]" :key="key">{{ ({name:'名称',country:'国家 / 地区',address:'地址',tax_id:'税号',contact:'联系人',phone:'电话',email:'邮箱',billing_address:'账单地址',shipping_address:'收货地址',recipient:'收货人'})[key] || key }}<input :value="value ?? ''" :disabled="key === 'name' && side === (kind === 'purchase_order' ? 'seller' : 'buyer')" :placeholder="value == null ? '未知；输入或确认留空' : ''" @input="structured[side][key] = $event.target.value" /><button v-if="value == null && !(key === 'name' && side === (kind === 'purchase_order' ? 'seller' : 'buyer'))" type="button" @click="structured[side][key] = ''">确认留空</button></label></fieldset><label><input v-model="unknownConfirmed" type="checkbox" /> 已核对，未填写的扩展资料均为未知</label></template>
      <label>原因<textarea v-model="reason" :disabled="busy" /></label><label>依据<textarea v-model="evidence" :disabled="busy" /></label>
      <button type="button" class="btn btn-primary" :disabled="busy || loading" @click="submit">提交替换申请</button>
    </template>
    <template v-else>
      <p>目标：{{ request?.replacement_target?.name }}。请明确填写新单内容；系统不会复制原单明细或收付款。</p>
      <label>单据日期<input v-model="date" type="date" /></label><label>币种<input v-model="currency" /></label><label>汇率<input v-model="exchangeRate" inputmode="decimal" /></label>
      <template v-if="kind !== 'purchase_order'"><label>运费<input v-model="shipping" inputmode="decimal" /></label><label>折扣<input v-model="discount" inputmode="decimal" /></label></template>
      <label v-if="kind === 'order'">尾货策略<select v-model="tailGoodsPolicy"><option value="">请选择</option><option value="SAME_CARTON">使用标准箱</option><option value="REPACK">尾箱待确认</option><option value="MANUAL">人工装箱</option></select></label>
      <template v-if="kind === 'quote'"><label>定金比例<input v-model="deposit" inputmode="decimal" /></label><label>贸易条款<input v-model="tradingTerms" /></label><label>运输说明<input v-model="shippingDetails" /></label></template>
      <template v-if="kind === 'purchase_order'"><label>付款计划<select v-model="paymentMode"><option value="">请选择</option><option value="none">本单不设置付款计划</option><option value="stages">填写付款阶段</option></select></label><template v-if="paymentMode === 'stages'"><fieldset v-for="(stage, index) in paymentStages" :key="index"><legend>付款阶段 {{ index + 1 }}</legend><label>名称<input v-model="stage.label" /></label><label>比例（合计为 1）<input v-model="stage.ratio" inputmode="decimal" /></label><label>到期依据<select v-model="stage.due_basis"><option value="">请选择</option><option value="order_date">下单日期</option><option value="expected_arrival_date">预计到货日期</option><option value="no_date">不设日期</option></select></label><label>延后天数<input v-model="stage.offset_days" type="number" min="0" /></label><button v-if="paymentStages.length > 1" type="button" @click="paymentStages.splice(index, 1)">移除阶段</button></fieldset><button v-if="paymentStages.length < 5" type="button" @click="paymentStages.push({ label: '', ratio: '', due_basis: '', offset_days: '' })">添加付款阶段</button></template></template>
      <fieldset v-for="(row, index) in rows" :key="index"><legend>商品 {{ index + 1 }}</legend><label>SKU<select v-model="row.sku"><option value="">请选择</option><option v-for="sku in skus" :key="sku.id" :value="sku.id">{{ sku.sku }} · {{ sku.display_name_cn || sku.product_name || '' }}</option></select></label><label>数量<input v-model="row.quantity" inputmode="decimal" /></label><label>单价<input v-model="row.unit_price" inputmode="decimal" /></label><button v-if="rows.length > 1" type="button" @click="rows.splice(index, 1)">移除商品</button></fieldset>
      <button type="button" @click="rows.push({ sku: '', quantity: '', unit_price: '' })">添加商品</button>
      <label>备注<textarea v-model="notes" /></label><label><input v-model="termsConfirmed" type="checkbox" /> 已核对全部新单资料和条款</label>
      <button type="button" class="btn btn-primary" :disabled="busy || loading" @click="submit">创建关联草稿</button>
    </template>
  </div>
</template>

<style scoped>
.replacement-form{display:grid;gap:10px;padding:14px;background:#f6faf7;border:1px solid #d7e5dc;border-radius:8px}.replacement-form label{display:grid;gap:4px}.replacement-form input:not([type=checkbox]),.replacement-form select,.replacement-form textarea{width:100%;padding:8px;border:1px solid #b9c9c1;border-radius:6px}.replacement-form fieldset{display:grid;gap:8px;border:1px solid #d7e5dc;padding:10px}.replacement-error{color:#a12e2e}
</style>
