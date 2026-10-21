<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, listAll } from '../api'
import { apiErrorMessage } from '../utils/apiErrors.js'
import { useAccessControl } from '../accessControl'

const { can } = useAccessControl()
const tab = ref('sales')
const customers = ref([])
const suppliers = ref([])
const skus = ref([])
const salesRows = ref([])
const purchaseRows = ref([])
const analysis = ref(null)
const currentYear = new Date().getFullYear()
const analysisFrom = ref(`${currentYear - 9}-01-01`)
const analysisTo = ref(`${currentYear}-12-31`)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const salesForm = reactive({ customer: '', order_date: '', currency: 'CNY', exchange_rate: '1', notes: '', items: [{ sku: '', quantity: '', unit_price: '', notes: '' }] })
const purchaseForm = reactive({ supplier: '', order_date: '', currency: 'CNY', exchange_rate: '1', notes: '', items: [{ sku: '', quantity: '', unit_price: '', notes: '' }] })
const form = computed(() => tab.value === 'sales' ? salesForm : purchaseForm)
const rows = computed(() => tab.value === 'sales' ? salesRows.value : purchaseRows.value)

function addLine() { form.value.items.push({ sku: '', quantity: '', unit_price: '', notes: '' }) }
function removeLine(index) { if (form.value.items.length > 1) form.value.items.splice(index, 1) }
function resetForm() {
  const target = form.value
  target.order_date = ''
  target.notes = ''
  target.items = [{ sku: '', quantity: '', unit_price: '', notes: '' }]
}
function validateForm() {
  if (tab.value === 'sales' && !can('orders', 'create')) return '当前账号没有历史销售订单录入权限。'
  if (tab.value === 'purchase' && !can('purchases', 'create')) return '当前账号没有历史采购订单录入权限。'
  if (tab.value === 'sales' && !salesForm.customer) return '请选择客户。'
  if (tab.value === 'purchase' && !purchaseForm.supplier) return '请选择供应商。'
  if (!form.value.order_date) return '请填写真实历史订单日期。'
  if (!form.value.items.length || form.value.items.some(item => !item.sku || Number(item.quantity) <= 0 || Number(item.unit_price) < 0)) return '请完整填写 SKU、数量和金额。'
  return ''
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [customerRows, supplierRows, skuRows, sales, purchases, report] = await Promise.all([
      listAll('/customers/'), listAll('/suppliers/'), listAll('/skus/'),
      listAll('/orders/', { params: { status: 'historical' } }),
      listAll('/purchase-orders/', { params: { status: 'historical' } }),
      api.get('/reports/historical/', { params: { date_from: analysisFrom.value, date_to: analysisTo.value } }),
    ])
    customers.value = customerRows
    suppliers.value = supplierRows
    skus.value = skuRows
    salesRows.value = sales
    purchaseRows.value = purchases
    analysis.value = report.data
  } catch (err) { error.value = apiErrorMessage(err) || '历史订单资料加载失败。' } finally { loading.value = false }
}
async function refreshAnalysis() {
  try {
    analysis.value = (await api.get('/reports/historical/', { params: { date_from: analysisFrom.value, date_to: analysisTo.value } })).data
    error.value = ''
  } catch (err) { error.value = apiErrorMessage(err) || '历史分析加载失败。' }
}
async function save() {
  const message = validateForm()
  if (message || saving.value) { if (message) error.value = message; return }
  saving.value = true
  error.value = ''
  notice.value = ''
  const payload = {
    ...form.value,
    ...(tab.value === 'sales' ? { customer: Number(form.value.customer) } : { supplier: Number(form.value.supplier) }),
    items: form.value.items.map(item => ({ sku: Number(item.sku), quantity: item.quantity, unit_price: item.unit_price, notes: item.notes || '' })),
  }
  try {
    await api.post(tab.value === 'sales' ? '/orders/historical/' : '/purchase-orders/historical/', payload)
    notice.value = '历史订单已保存，仅用于经营分析。'
    resetForm()
    await load()
  } catch (err) { error.value = apiErrorMessage(err) || '历史订单保存失败。' } finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <div class="history-page">
    <header class="history-intro">
      <div><p class="eyebrow">Historical ledger</p><h2>历史订单分析</h2><p>录入正式启用前的真实订单，保留原日期；历史订单 · 仅用于经营分析。</p></div>
      <span class="history-badge">不生成应收、应付、采购或库存记录</span>
    </header>
    <p v-if="error" class="history-alert error" role="alert">{{ error }}</p>
    <p v-if="notice" class="history-alert success" role="status">{{ notice }}</p>
    <section class="history-tabs" aria-label="历史订单类型"><button :class="{ active: tab === 'sales' }" @click="tab = 'sales'">历史销售订单</button><button :class="{ active: tab === 'purchase' }" @click="tab = 'purchase'">历史采购订单</button></section>
    <section class="history-card">
      <div class="card-heading"><div><h3>新建{{ tab === 'sales' ? '销售' : '采购' }}历史订单</h3><p>只保存分析所需资料，不进入正式履约流程。</p></div><button class="secondary" @click="resetForm">清空</button></div>
      <div class="history-fields">
        <label v-if="tab === 'sales'">客户<select v-model="salesForm.customer"><option value="">请选择客户</option><option v-for="row in customers" :key="row.id" :value="row.id">{{ row.name }} · {{ row.code }}</option></select></label>
        <label v-else>供应商<select v-model="purchaseForm.supplier"><option value="">请选择供应商</option><option v-for="row in suppliers" :key="row.id" :value="row.id">{{ row.name }} · {{ row.code }}</option></select></label>
        <label>真实订单日期<input v-model="form.order_date" type="date" /></label>
        <label>币种<select v-model="form.currency"><option>CNY</option><option>USD</option><option>EUR</option><option>GBP</option></select></label>
        <label>对人民币汇率<input v-model="form.exchange_rate" inputmode="decimal" /></label>
      </div>
      <div class="history-lines"><div class="line-heading"><h4>商品明细</h4><button class="secondary" @click="addLine">增加 SKU</button></div><div v-for="(item, index) in form.items" :key="index" class="history-line"><select v-model="item.sku" aria-label="SKU"><option value="">选择 SKU</option><option v-for="sku in skus" :key="sku.id" :value="sku.id">{{ sku.sku }} · {{ sku.display_name_cn || sku.product_name || '未命名 SKU' }}</option></select><input v-model="item.quantity" placeholder="数量" inputmode="decimal" aria-label="数量" /><input v-model="item.unit_price" placeholder="单价" inputmode="decimal" aria-label="单价" /><input v-model="item.notes" placeholder="备注（可选）" aria-label="明细备注" /><button class="icon-remove" :disabled="form.items.length === 1" @click="removeLine(index)">移除</button></div></div>
      <label class="history-notes">订单备注<textarea v-model="form.notes" rows="2" placeholder="可记录历史背景，不填写付款或履约状态。" /></label>
      <div class="history-actions"><span>保存后状态为“历史订单 · 仅用于经营分析”</span><button class="primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存历史订单' }}</button></div>
    </section>
    <section class="history-card analysis-card"><div class="card-heading"><div><h3>历史经营分析</h3><p>与正式启用后的经营指标分开显示；没有可靠成本时不计算利润。</p></div><div class="analysis-filter"><label>从<input v-model="analysisFrom" type="date" /></label><label>至<input v-model="analysisTo" type="date" /></label><button class="secondary" @click="refreshAnalysis">刷新分析</button></div></div><div v-if="loading" class="history-empty">加载中…</div><div v-else class="analysis-grid"><div v-if="analysis?.sales"><small>历史销售额（人民币折算）</small><strong>¥ {{ Number(analysis.sales.amount_rmb || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</strong><span>{{ analysis.sales.order_count }} 张订单 · {{ analysis.sales.quantity }} 件</span></div><div v-if="analysis?.purchase"><small>历史采购额（人民币折算）</small><strong>¥ {{ Number(analysis.purchase.amount_rmb || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</strong><span>{{ analysis.purchase.order_count }} 张订单 · {{ analysis.purchase.quantity }} 件</span></div><div><small>利润</small><strong>不计算</strong><span>历史成本未必完整，避免虚构利润</span></div></div></section>
    <section class="history-card"><div class="card-heading"><div><h3>已录入历史{{ tab === 'sales' ? '销售' : '采购' }}订单</h3><p>当前共 {{ rows.length }} 张；历史记录不会出现在待收、待付、采购待办或库存预留中。</p></div></div><div v-if="!rows.length" class="history-empty">暂无历史订单</div><div v-else class="history-list"><article v-for="row in rows" :key="row.id"><div><strong>{{ tab === 'sales' ? row.order_no : row.purchase_no }}</strong><span>{{ tab === 'sales' ? row.customer_name : row.supplier_name }}</span></div><div><span>{{ row.order_date }}</span><b>{{ row.currency }} {{ Number(row.total_amount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</b><em>历史订单 · 仅用于经营分析</em></div></article></div></section>
  </div>
</template>

<style scoped>
.history-page{display:grid;gap:18px;min-width:0}.history-intro,.history-card{background:#fff;border:1px solid #dfe7e2;border-radius:14px;padding:22px}.history-intro{display:flex;justify-content:space-between;align-items:flex-start;gap:18px}.eyebrow{margin:0 0 5px;color:#728477;text-transform:uppercase;letter-spacing:.08em;font-size:12px}.history-intro h2{margin:0;color:#294838;font-size:26px}.history-intro p:not(.eyebrow){margin:8px 0 0;color:#617567;line-height:1.7}.history-badge,.history-list em{display:inline-flex;align-items:center;border-radius:999px;background:#eef5f0;color:#386b50;padding:7px 11px;font-size:12px;white-space:nowrap}.history-tabs{display:flex;gap:8px}.history-tabs button,.secondary,.primary,.icon-remove{border:1px solid #d5dfd6;border-radius:8px;background:#fff;color:#365d47;padding:9px 13px;cursor:pointer;font:inherit}.history-tabs button.active,.primary{background:#286c52;border-color:#286c52;color:#fff}.history-card{display:grid;gap:18px}.card-heading,.history-actions,.line-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.card-heading h3,.line-heading h4{margin:0;color:#294838}.card-heading p,.history-actions span{margin:5px 0 0;color:#718377;font-size:13px;line-height:1.6}.history-fields{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.history-page label{display:grid;gap:6px;color:#5d7164;font-size:13px}.history-page input,.history-page select,.history-page textarea{box-sizing:border-box;width:100%;border:1px solid #d5dfd6;border-radius:7px;padding:9px;background:#fff;color:#314a3c;font:inherit}.history-lines{display:grid;gap:10px}.history-line{display:grid;grid-template-columns:minmax(190px,2fr) minmax(100px,1fr) minmax(100px,1fr) minmax(150px,1.5fr) auto;gap:8px}.history-notes{max-width:720px}.history-actions{border-top:1px solid #e8eee9;padding-top:15px}.history-actions span{margin:0}.history-alert{margin:0;padding:12px;border-radius:8px;line-height:1.6}.history-alert.error{background:#fff5f2;color:#a54335}.history-alert.success{background:#eef8f0;color:#376747}.analysis-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.analysis-grid>div{display:grid;gap:6px;padding:16px;background:#f6f8f5;border-radius:9px}.analysis-grid small{color:#718377}.analysis-grid strong{color:#294838;font-size:20px}.analysis-grid span{color:#718377;font-size:12px}.history-empty{padding:24px;border:1px dashed #c7d4c8;border-radius:10px;text-align:center;color:#718377}.history-list{display:grid;gap:8px}.history-list article{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:13px 0;border-bottom:1px solid #edf1ed}.history-list article>div{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.history-list strong{color:#294838}.history-list span{color:#617567}.history-list b{color:#294838}.history-list em{font-style:normal;font-size:11px}@media(max-width:900px){.history-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.analysis-grid{grid-template-columns:1fr}.history-intro{display:grid}}@media(max-width:700px){.history-intro,.history-card{padding:16px}.history-tabs{overflow:auto}.history-tabs button{white-space:nowrap}.history-fields{grid-template-columns:1fr}.history-line{grid-template-columns:1fr 1fr}.history-line select,.history-line input[aria-label="明细备注"],.history-line .icon-remove{grid-column:1/-1}.history-actions{display:grid}.history-list article{align-items:flex-start;display:grid;gap:8px}}
</style>
