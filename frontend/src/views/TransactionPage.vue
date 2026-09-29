<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, listAll } from '../api'
import SummaryCards from '../components/SummaryCards.vue'
import { formatMoney } from '../utils/money'

const today = new Date().toISOString().slice(0, 10)
const rows = ref([]), error = ref(''), query = ref(''), orderQuery = ref(''), showForm = ref(false), orders = ref([])
const customers = ref([]), suppliers = ref([]), purchases = ref([]), plans = ref([]), saving = ref(false), loading = ref(false)
const allocation = ref(null), allocationPlan = ref(''), allocationAmount = ref('')
const voidTarget = ref(null), voidReason = ref(''), voidSaving = ref(false)
const filters = reactive({ status: 'confirmed', direction: '', date_from: '', date_to: '' })
const contractKinds = ['customer_receipt', 'order_expense', 'freight_expense', 'sample_expense', 'bank_fee', 'refund']
const eligiblePlans = computed(() => plans.value.filter(plan => plan.status === 'open' && plan.currency === allocation.value?.currency && plan.direction === (allocation.value?.direction === 'income' ? 'receivable' : 'payable') && (plan.order ? plan.customer_id === allocation.value?.customer : plan.supplier_id === allocation.value?.supplier)))

const kindGroups = [
  {
    direction: 'income',
    label: '收入',
    options: [
      { value: 'customer_receipt', label: '客户收款' },
      { value: 'unallocated_advance', label: '未分配预收款' },
      { value: 'supplier_refund', label: '供应商退款（原付款退回）' },
      { value: 'other_income', label: '其他收入' },
    ],
  },
  {
    direction: 'expense',
    label: '支出',
    options: [
      { value: 'supplier_payment', label: '供应商付款' },
      { value: 'order_expense', label: '订单费用' },
      { value: 'sample_expense', label: '样品费用' },
      { value: 'freight_expense', label: '运费/物流费' },
      { value: 'bank_fee', label: '银行手续费' },
      { value: 'tax_fee', label: '税费' },
      { value: 'salary_expense', label: '工资/福利' },
      { value: 'office_expense', label: '办公费用' },
      { value: 'travel_expense', label: '差旅/招待' },
      { value: 'marketing_expense', label: '营销推广' },
      { value: 'warehouse_expense', label: '仓储费用' },
      { value: 'asset_expense', label: '设备/固定资产' },
      { value: 'period_expense', label: '其他期间费用' },
      { value: 'unallocated_payment', label: '未分配预付款' },
      { value: 'refund', label: '客户退款（原收款退回）' },
      { value: 'exchange_difference', label: '汇兑损失' },
      { value: 'other_expense', label: '其他支出' },
    ],
  },
]
const kindLookup = new Map(kindGroups.flatMap(group => group.options.map(option => [option.value, { ...option, direction: group.direction }])))
const legacyKindLabels = { other: '其他收支', unallocated_advance: '未分配预收款' }
const currencies = [
  { value: 'CNY', label: 'CNY · 人民币' },
  { value: 'USD', label: 'USD · 美元' },
  { value: 'EUR', label: 'EUR · 欧元' },
  { value: 'GBP', label: 'GBP · 英镑' },
  { value: 'JPY', label: 'JPY · 日元' },
  { value: 'HKD', label: 'HKD · 港币' },
  { value: 'AUD', label: 'AUD · 澳元' },
]

const form = reactive({
  transaction_no: '', transaction_date: today, kind: 'period_expense', direction: 'expense', category: '其他期间费用',
  amount: '', currency: 'CNY', exchange_rate: '1', payment_method: '', reference: '', notes: '', order: null, customer: null, supplier: null, purchase_order: null,
})

const transactionMetrics = computed(() => {
  const sum = direction => rows.value.filter(row => row.direction === direction && row.status === 'confirmed').reduce((total, row) => total + Number(row.rmb_amount || 0), 0)
  return [
    { label: '流水笔数', value: rows.value.length, hint: '当前查询结果' },
    { label: '收入合计', value: `¥ ${formatMoney(sum('income'))}`, hint: '折合人民币' },
    { label: '支出合计', value: `¥ ${formatMoney(sum('expense'))}`, hint: '折合人民币' },
    { label: '关联订单', value: new Set(rows.value.map(row => row.order || row.order_no).filter(Boolean)).size, hint: '有业务归属的流水' },
  ]
})

function kindLabel(kind) { return kindLookup.get(kind)?.label || legacyKindLabels[kind] || kind || '—' }
function directionLabel(direction) { return direction === 'income' ? '收入' : direction === 'expense' ? '支出' : '—' }
function syncKind() {
  const meta = kindLookup.get(form.kind)
  if (meta) {
    form.direction = meta.direction
    form.category = meta.label
  }
  form.customer = null; form.supplier = null; form.purchase_order = null
  if (!contractKinds.includes(form.kind)) {
    form.order = null
    orders.value = []
    orderQuery.value = ''
  }
}
function openForm() {
  Object.assign(form, { transaction_no: '', transaction_date: new Date().toLocaleDateString('en-CA'), kind: 'period_expense', direction: 'expense', category: '其他期间费用', amount: '', currency: 'CNY', exchange_rate: '1', payment_method: '', reference: '', notes: '', order: null, customer: null, supplier: null, purchase_order: null })
  orderQuery.value = ''
  orders.value = []
  error.value = ''
  showForm.value = true
}
function onCurrencyChange() {
  if (form.currency === 'CNY') form.exchange_rate = '1'
  else if (form.exchange_rate === '1') form.exchange_rate = ''
}
async function load() {
  loading.value = true; error.value = ''
  try { rows.value = await listAll('/transactions/', { params: { ...filters, search: query.value } }) }
  catch (err) { error.value = err.message } finally { loading.value = false }
}
async function searchOrders() {
  form.order = null
  try { orders.value = (await listAll('/orders/', { params: { search: orderQuery.value } })).filter(row => !['draft', 'cancelled'].includes(row.status)) } catch (err) { error.value = err.message }
}
function chooseOrder(row) {
  form.order = row.id
  orderQuery.value = row.order_no
  if (['customer_receipt', 'refund'].includes(form.kind)) { form.currency = row.currency; form.exchange_rate = row.exchange_rate }
  orders.value = []
}
function choosePurchase() {
  const row = purchases.value.find(row => row.id === form.purchase_order)
  if (row) { form.currency = row.currency; form.exchange_rate = row.exchange_rate }
}
async function save() {
  if (saving.value) return
  saving.value = true
  try {
    const payload = { ...form }
    if (!payload.transaction_no) delete payload.transaction_no
    await api.post('/transactions/', payload)
    showForm.value = false
    await load()
  } catch (err) { error.value = err.message } finally { saving.value = false }
}
function openVoid(row) {
  voidTarget.value = row
  voidReason.value = ''
  error.value = ''
}
async function submitVoid() {
  const reason = voidReason.value.trim()
  if (!reason || voidSaving.value) return
  voidSaving.value = true
  error.value = ''
  try {
    await api.post(`/transactions/${voidTarget.value.id}/void/`, { reason })
    voidTarget.value = null
    voidReason.value = ''
    await load()
  } catch (err) { error.value = err.response?.data?.detail || err.message } finally { voidSaving.value = false }
}
async function openAllocate(row) {
  try { plans.value = await listAll('/payment-plans/', { params: { status: 'open' } }); allocation.value = row; allocationPlan.value = ''; allocationAmount.value = String(Number(row.amount) - Number(row.allocated_amount)) } catch (err) { error.value = err.message }
}
async function allocate() {
  if (saving.value) return
  saving.value = true
  try { await api.post(`/transactions/${allocation.value.id}/allocate/`, { plan: allocationPlan.value, amount: allocationAmount.value }); allocation.value = null; await load() } catch (err) { error.value = err.message } finally { saving.value = false }
}
onMounted(async () => {
  await load()
  try { [customers.value, suppliers.value, purchases.value] = await Promise.all([listAll('/customers/'), listAll('/suppliers/'), listAll('/purchase-orders/')]) } catch (err) { error.value = err.message }
})
</script>

<template>
  <section class="txn">
    <header>
      <div><h2>财务流水</h2><p>统一登记实际收付款、订单费用与期间费用。</p></div>
      <button @click="openForm">新增记账</button>
    </header>
    <SummaryCards :items="transactionMetrics" />
    <div class="toolbar"><input v-model="query" placeholder="搜索流水号、往来方、合同" @keyup.enter="load"><select v-model="filters.status" @change="load"><option value="confirmed">已确认</option><option value="cancelled">已作废</option><option value="">全部状态</option></select><select v-model="filters.direction" @change="load"><option value="">全部收支</option><option value="income">收入</option><option value="expense">支出</option></select><input v-model="filters.date_from" type="date" aria-label="开始日期"><input v-model="filters.date_to" type="date" aria-label="结束日期"><button :disabled="loading" @click="load">查询</button></div>
    <p v-if="error" class="error">{{ error }}</p>
    <table>
      <thead><tr><th>日期 / 流水号</th><th>收支 / 类型</th><th>往来方 / 合同</th><th>原币金额</th><th>人民币</th><th>状态 / 核销</th><th>操作</th></tr></thead>
      <tbody><tr v-if="loading"><td colspan="7">正在加载…</td></tr><tr v-else-if="!rows.length"><td colspan="7">当前条件下暂无流水。</td></tr><tr v-for="row in rows" :key="row.id"><td>{{ row.transaction_date }}<small>{{ row.transaction_no }}<span v-if="row.split_from"> · 拆分记录</span></small></td><td>{{ row.direction_display || directionLabel(row.direction) }}<small>{{ kindLabel(row.kind) }}</small></td><td>{{ row.customer_name || row.supplier_name || '—' }}<small>{{ row.order_no || row.purchase_no || '未关联合同' }}</small></td><td>{{ row.currency }} {{ formatMoney(row.amount) }}</td><td>¥{{ formatMoney(row.rmb_amount) }}</td><td>{{ row.status_display }}<small v-if="['unallocated_advance', 'unallocated_payment'].includes(row.kind)">未核销 {{ row.currency }} {{ formatMoney(Number(row.amount) - Number(row.allocated_amount)) }}</small><small v-for="item in row.allocations" :key="item.id">{{ item.contract_no }}：{{ formatMoney(item.amount) }} {{ item.is_active ? '已核销' : '已撤回' }}</small><small v-if="row.status === 'cancelled' && row.void_reason">作废原因：{{ row.void_reason }}{{ row.voided_at ? ' · ' + row.voided_at : '' }}</small></td><td><button v-if="row.status === 'confirmed' && ['unallocated_advance', 'unallocated_payment'].includes(row.kind) && Number(row.amount) > Number(row.allocated_amount)" @click="openAllocate(row)">核销</button><button v-if="row.status === 'confirmed' && !row.split_from" @click="openVoid(row)">作废</button><small v-if="row.split_from">由原始流水统一作废</small><small v-else-if="row.status === 'cancelled'">已作废</small></td></tr></tbody>
    </table>

    <div v-if="showForm" class="mask" @click.self="showForm = false">
      <form class="dialog" @submit.prevent="save">
        <h3>新增记账</h3>
        <label>类型
          <select v-model="form.kind" required @change="syncKind">
            <optgroup v-for="group in kindGroups" :key="group.direction" :label="group.label"><option v-for="option in group.options" :key="option.value" :value="option.value">{{ option.label }}</option></optgroup>
          </select>
          <small class="field-hint">已按收入 / 支出分组；选择类型后会自动确定收支方向。</small>
        </label>
        <label>日期<input v-model="form.transaction_date" type="date" required></label>
        <p class="category-hint">分类由所选类型自动生成：{{ form.category }}，无需重复填写。</p>
        <label>原币金额<input v-model="form.amount" v-money-input type="number" min="0.0001" step="any" required></label>
        <label>币种<select v-model="form.currency" required @change="onCurrencyChange"><option v-for="currency in currencies" :key="currency.value" :value="currency.value">{{ currency.label }}</option></select></label>
        <label>结汇汇率 <small>1 外币 ≈ 人民币</small><input v-model="form.exchange_rate" type="number" min="0.000001" step="0.000001" required></label>
        <div v-if="contractKinds.includes(form.kind)" class="order-picker">
          <label>关联订单（客户收款必选，费用可选）<input v-model="orderQuery" placeholder="客户或订单号" @input="searchOrders"></label>
          <button v-for="row in orders" :key="row.id" type="button" class="order" @click="chooseOrder(row)">{{ row.customer_name }}｜{{ row.customer_country || '—' }}｜{{ row.order_no }}｜{{ row.currency }} {{ formatMoney(row.total_amount) }}</button>
          <p v-if="form.order">已选择订单：{{ orders.find(row => row.id === form.order)?.order_no || form.order }}</p>
        </div>
        <label v-if="['supplier_payment', 'supplier_refund'].includes(form.kind)">采购单<select v-model="form.purchase_order" required @change="choosePurchase"><option :value="null">请选择采购单</option><option v-for="row in purchases.filter(row => !['draft', 'cancelled'].includes(row.status))" :key="row.id" :value="row.id">{{ row.purchase_no }} · {{ row.supplier_name }} · {{ row.currency }}</option></select></label>
        <label v-if="form.kind === 'unallocated_advance'">客户<select v-model="form.customer" required><option :value="null">请选择客户</option><option v-for="row in customers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        <label v-if="form.kind === 'unallocated_payment'">供应商<select v-model="form.supplier" required><option :value="null">请选择供应商</option><option v-for="row in suppliers" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
        <label>支付方式<input v-model="form.payment_method" placeholder="银行转账、现金等"></label><label>银行参考号<input v-model="form.reference"></label><label>备注<input v-model="form.notes"></label>
        <p v-if="['customer_receipt', 'supplier_payment'].includes(form.kind)">款项将按合同计划顺序核销；超出计划的部分转为未分配预收预付。</p>
        <p v-if="form.kind === 'refund'">用于退回已经收到的订单货款；售后赔偿、运费补贴等请登记为订单费用。</p>
        <p v-else-if="form.kind === 'supplier_refund'">用于供应商退回已经支付的采购款。</p>
        <p v-if="error" class="error">{{ error }}</p>
        <footer><button type="button" @click="showForm = false">取消</button><button :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button></footer>
      </form>
    </div>
    <div v-if="allocation" class="mask" @click.self="allocation = null"><form class="dialog" @submit.prevent="allocate"><h3>核销预收预付款</h3><p>只分配余额，不新增现金流水。{{ allocation.currency }}</p><label>同一往来方的待结计划<select v-model="allocationPlan" required><option value="">请选择</option><option v-for="plan in eligiblePlans" :key="plan.id" :value="plan.id">{{ plan.contract_no }} · {{ plan.notes }} · 待结 {{ formatMoney(plan.remaining_amount) }}</option></select></label><p v-if="!eligiblePlans.length">暂无币种与往来方匹配的待结计划。</p><label>核销金额<input v-model="allocationAmount" type="number" min="0.0001" step="0.0001" required></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="allocation = null">取消</button><button :disabled="saving || !allocationPlan">确认核销</button></footer></form></div>
    <div v-if="voidTarget" class="mask" @click.self="voidTarget = null"><form class="dialog" @submit.prevent="submitVoid"><h3>作废财务流水</h3><dl class="void-summary"><dt>流水号</dt><dd>{{ voidTarget.transaction_no }}</dd><dt>金额</dt><dd>{{ voidTarget.currency }} {{ formatMoney(voidTarget.amount) }}</dd><dt>往来方 / 合同</dt><dd>{{ voidTarget.customer_name || voidTarget.supplier_name || '—' }} / {{ voidTarget.order_no || voidTarget.purchase_no || '未关联合同' }}</dd></dl><p>该操作将同时作废相关拆分流水，并恢复对应收付款计划。</p><label>作废原因<textarea v-model="voidReason" maxlength="500" rows="4" required /></label><p v-if="error" class="error">{{ error }}</p><footer><button type="button" @click="voidTarget = null">取消</button><button :disabled="voidSaving || !voidReason.trim()">{{ voidSaving ? '保存中…' : '确认作废' }}</button></footer></form></div>
  </section>
</template>

<style scoped>
.txn td small{display:block;color:#718078;font-size:var(--text-caption);margin-top:4px}.toolbar{flex-wrap:wrap}.toolbar input[type=date]{min-width:140px}.toolbar select{padding:8px;border:1px solid #d8e1dd;border-radius:8px}
.txn{padding:34px}.txn>header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.txn h2{margin:0}.txn p{color:#718078}.txn button{padding:8px 13px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;cursor:pointer}.txn button:hover{border-color:#8db7a7;background:#f5faf7}.toolbar{display:flex;gap:8px;margin:20px 0}.toolbar input{padding:9px;min-width:280px;border:1px solid #d8e1dd;border-radius:8px}table{background:#fff;width:100%;border-collapse:collapse;border:1px solid #e2e8e4}th,td{padding:12px;text-align:left;border-bottom:1px solid #edf1ee}th{color:#60736b;background:#f6faf8;font-size:var(--text-body)}.mask{position:fixed;inset:0;background:#10261d66;display:grid;place-items:center;z-index:30;padding:16px}.dialog{background:#fff;padding:24px;border-radius:14px;width:min(500px,calc(100vw - 32px));max-height:calc(100vh - 32px);overflow:auto;box-shadow:0 22px 60px #001a1340}.dialog h3{margin:0 0 18px}.dialog label{display:grid;gap:5px;margin:10px 0;color:#3d5149;font-size:var(--text-body)}.dialog input,.dialog select,.dialog textarea{box-sizing:border-box;width:100%;padding:9px;border:1px solid #d8e1dd;border-radius:7px;background:#fff;color:#253b33;font:inherit}.dialog textarea{resize:vertical}.dialog label>small{font-size:var(--text-caption);color:#71847c;font-weight:400}.void-summary{display:grid;grid-template-columns:100px 1fr;gap:8px;margin:0 0 14px;font-size:var(--text-body)}.void-summary dt{color:#718078}.void-summary dd{margin:0;color:#253b33}.field-hint,.category-hint{display:block;margin:-4px 0 10px;color:#71847c;font-size:var(--text-caption)}.category-hint{padding:8px 10px;border-radius:7px;background:#f3f8f5}.order-picker{margin-top:8px}.order-picker>p{margin:8px 0 0;font-size:var(--text-caption)}.order{display:block;width:100%;margin:5px 0;text-align:left}.dialog footer{display:flex;justify-content:end;gap:8px;margin-top:18px}.dialog footer button:last-child{background:#0d4b40;color:#fff;border-color:#0d4b40}.error{color:#b42318}.txn .summary-cards{margin-top:16px}@media(max-width:620px){.txn{padding:20px 14px}.txn>header{flex-direction:column}.txn>header>button{width:100%}.toolbar{flex-wrap:wrap}.toolbar input{min-width:0;width:100%}table{display:block;overflow:auto;white-space:nowrap}.dialog{padding:20px}}
</style>
