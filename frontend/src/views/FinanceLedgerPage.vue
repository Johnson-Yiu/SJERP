<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { apiErrorMessage } from '../utils/apiErrors.js'
import { useAccessControl } from '../accessControl'

const { can } = useAccessControl()
const route = useRoute()
const state = reactive({ accounts: [], vouchers: [], instructions: [], reviews: [], mappings: [], transfers: [] })
const facts = ref([])
const totals = ref({ inflow: '0', outflow: '0', net: '0' })
const error = ref(''), notice = ref(''), busy = ref(false), ready = ref(false)
const tab = ref('facts')
const period = reactive({ date_from: `${new Date().getFullYear()}-01-01`, date_to: new Date().toLocaleDateString('en-CA') })
const accountForm = reactive({ code: '', name: '', account_type: 'bank', ownership: 'unverified', ownership_reason: '' })
const review = reactive({ account: '', date_from: '', date_to: '', voucher: '', statement_balance: '', completed: false, reason: '' })
const transfer = reactive({ outgoing: '', incoming: '', reason: '', outgoing_voucher: '', incoming_voucher: '' })
const classification = reactive({ fact: '', nature: 'unclassified', reason: '' })
const mapping = reactive({ legacy_code: '', account: '', reason: '' })
const ownership = reactive({ account: '', ownership: 'own', reason: '' })
const file = ref(null)
const draft = reactive({ request_key: '', kind: 'cash', account: '', voucher: '', actual_date: '', amount: '', direction: 'income', nature: 'unclassified', truth: 'needs_verification', source_system: '', source_key: '', reason: '', parent: '', legacy_parent: '', approval: '', excess_reason: '', replaces: '' })
const allocations = reactive([{ order: '', amount: '' }])
const preview = ref(null), duplicateReason = ref(''), checked = ref(false)
const storageKey = 'sunjack:finance-ledger:pending-request:v1'
const attempted = ref(false), storageError = ref(false), recoveredKey = ref('')
const ownAccounts = computed(() => state.accounts.filter(a => a.ownership === 'own' && a.currency === 'CNY'))
const kinds = { cash: '实际收支', opening: '启用余额', correction: '人工更正', refund_approval: '退款批准依据', refund_payment: '实际退款扣款', bank_return: '银行退回', refund_return: '退款扣款后退回' }
const natures = { unclassified: '性质待分类', income: '其他收入', expense: '其他支出', interest: '利息', loan: '借款', capital: '注资', bank_fee: '手续费', commercial_refund: '商业退款', refund_excess: '超额退款', internal_principal: '内部转账本金', correction: '更正' }
const statuses = { pending: '待复核 / 待凭证确认', approved: '已复核', posted: '已记账', cancelled: '已取消', failed: '失败（已核实未扣款）' }

function storeIdentity() {
  try { window.sessionStorage.setItem(storageKey, JSON.stringify({ key: draft.request_key, attempted: attempted.value })); storageError.value = false; return true }
  catch { storageError.value = true; error.value = '无法保存请求身份，已阻止提交。请恢复浏览器存储后重试。'; return false }
}
function newDraft() {
  if (attempted.value && !state.instructions.some(i => i.payload.request_key === draft.request_key)) { error.value = '上次请求结果未知，请先刷新核查，暂不能更换请求标识。'; return }
  attempted.value = false; recoveredKey.value = ''; preview.value = null
  draft.request_key = crypto.randomUUID(); storeIdentity()
}
async function load() {
  const [data, rows] = await Promise.all([api.get('/finance-ledger/', { params: period }), api.get('/finance-ledger/facts/', { params: period })])
  Object.assign(state, data.data); facts.value = rows.data.facts; totals.value = rows.data.totals
  ready.value = true
}
async function run(work, success) {
  if (busy.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try { await work(); await load(); if (success) notice.value = success }
  catch (e) { error.value = apiErrorMessage(e) }
  finally { busy.value = false }
}
function payload() {
  const result = Object.fromEntries(Object.entries(draft).filter(([, value]) => value !== ''))
  result.allocations = allocations.filter(a => a.order || a.amount).map(a => ({ order: a.order, amount: a.amount }))
  if (preview.value?.duplicate_candidates.ids.length && duplicateReason.value.trim()) {
    result.duplicate_review_token = preview.value.duplicate_candidates.token
    result.duplicate_review_reason = duplicateReason.value.trim()
  }
  return result
}
async function submit() {
  if (storageError.value || recoveredKey.value) { error.value = '请求身份需核查，暂不能提交新内容。'; return }
  attempted.value = true
  if (!storeIdentity()) return
  await run(async () => { await api.post('/finance-ledger/instructions/', payload()) }, '指令已保存；需要复核的操作请由另一名授权人员处理。')
}
async function instructionAction(action, obj) {
  const body = { id: obj.id }
  if (action === 'post') { if (!checked.value) { error.value = '请先核对实际日期、金额和文件凭证。'; return }; body.voucher_checked = true }
  if (action === 'cancel') { const reason = window.prompt('填写取消原因'); if (!reason) return; body.reason = reason }
  if (action === 'fail') { const reason = window.prompt('请确认未实际扣款并填写失败凭证依据；结果未知请先核查'); if (!reason) return; body.reason = reason; body.no_debit_confirmed = true }
  await run(() => api.post(`/finance-ledger/${action}/`, body), '操作已保存。')
  checked.value = false
}
async function upload() {
  if (!file.value) { error.value = '请选择凭证文件。'; return }
  const body = new FormData(); body.append('file', file.value)
  await run(async () => { const result = await api.post('/finance-ledger/vouchers/', body); draft.voucher = result.data.id }, '私有凭证已保存，摘要由系统读取文件计算。')
}
async function downloadCsv() {
  await run(async () => {
    const response = await api.get('/finance-ledger/facts/', { params: { ...period, export: 'csv' }, responseType: 'blob' })
    const url = URL.createObjectURL(response.data), link = document.createElement('a')
    link.href = url; link.download = 'account-cash-facts.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  })
}
onMounted(async () => {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(storageKey) || 'null')
    if (saved?.key) { draft.request_key = saved.key; attempted.value = saved.attempted === true; if (attempted.value) recoveredKey.value = saved.key }
    else newDraft()
  } catch { storageError.value = true; error.value = '无法恢复请求身份，已阻止提交；请核查历史指令。' }
  await run(async () => {
    let fact
    if (route?.query?.fact) {
      fact = (await api.get('/finance-ledger/fact_detail/', { params: { id: route.query.fact } })).data
      period.date_from = fact.actual_date; period.date_to = fact.actual_date
    }
    await load(); await nextTick()
    if (fact) document.getElementById(`fact-${fact.id}`)?.scrollIntoView({ block: 'center' })
  })
})
</script>

<template>
  <section class="ledger-page">
    <header class="ledger-heading"><div><h1>账户资金</h1><p>按真实账户核对人民币变动、凭证和处理记录。</p></div><button :disabled="busy" @click="run(load)">刷新</button></header>
    <p v-if="error" role="alert" class="ledger-error">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="!ready && !error">正在读取账户资金…</p>
    <nav class="ledger-tabs" aria-label="资金功能"><button v-for="(label, key) in { facts: '资金事实', instructions: '登记与复核', accounts: '账户与映射', reviews: '账户核对', controls: '转账与分类' }" :key="key" :aria-pressed="tab === key" @click="tab = key">{{ label }}</button></nav>
    <div v-if="tab === 'facts'">
      <div class="ledger-form"><label>开始日期<input v-model="period.date_from" type="date"></label><label>结束日期<input v-model="period.date_to" type="date"></label><button :disabled="busy" @click="run(load)">查询</button><button v-if="can('finance', 'export') || can('reports', 'export')" :disabled="busy" @click="downloadCsv">导出 CSV</button></div>
      <div class="ledger-totals"><span>公司流入 ¥{{ totals.inflow }}</span><span>公司流出 ¥{{ totals.outflow }}</span><span>净变动 ¥{{ totals.net }}</span></div>
      <p>本页汇总新承接的账户事实。启用余额不计收入，已核实内部本金不计公司毛流量；账户明细保留两端变动。已有银行事实见人民币资金页，合并统计见财务概览。</p>
      <div class="ledger-cards"><article v-for="a in state.accounts" :key="a.id"><strong>{{ a.name }}</strong><p>{{ a.account_type === 'bank' ? '银行' : '现金' }} · {{ a.ownership === 'own' ? '自有' : a.ownership === 'external' ? '外部' : '归属待核实' }}</p><p>余额：{{ a.balance === null ? '未设置启用基准' : `¥${a.balance}` }}</p></article></div>
      <div class="ledger-cards"><article v-for="f in facts" :key="f.id" :id="`fact-${f.id}`"><strong>#{{ f.id }} · {{ f.account_name }} · {{ f.direction === 'income' ? '+' : '−' }}¥{{ f.amount }}</strong><p>{{ f.actual_date }} · {{ kinds[f.kind] }} · {{ natures[f.nature] }}</p><p>{{ f.company_flow_included ? '计入公司毛流量' : f.flow_exclusion_reason === 'superseded' ? '原版本已核实更正，保留历史' : '基准、零更正或已核实内部本金' }} · 来源 {{ f.source_system }} / {{ f.source_key }}</p><p v-if="Number(f.refund_excess_amount)">超额退款：¥{{ f.refund_excess_amount }}</p><p v-if="Number(f.unallocated_amount)">尚未分配至订单：¥{{ f.unallocated_amount }}</p><a :href="`/api/finance-ledger/voucher-download/?id=${f.voucher}`">下载私有凭证</a><details><summary>凭证摘要与历史分类</summary><code>{{ f.voucher_sha256 }}</code><p v-for="(c, i) in f.classifications" :key="i">{{ natures[c.nature] }} · {{ c.reason }} · {{ c.created_at }}</p></details></article></div>
      <p v-if="!facts.length">所选期间暂无已记账账户事实。</p>
    </div>
    <div v-if="tab === 'accounts'">
      <h2>新增账户</h2><form class="ledger-form" @submit.prevent="run(() => api.post('/finance-ledger/accounts/', accountForm), '账户已建立。')"><label>受控标识<input v-model="accountForm.code" required maxlength="40"></label><label>显示名称<input v-model="accountForm.name" required></label><label>账户类型<select aria-label="账户类型" v-model="accountForm.account_type"><option value="bank">银行</option><option value="cash">现金</option></select></label><label>归属<select aria-label="归属" v-model="accountForm.ownership"><option value="unverified">待核实</option><option value="own">自有</option><option value="external">外部</option></select></label><label>归属核实依据<input v-model="accountForm.ownership_reason" :required="accountForm.ownership !== 'unverified'"></label><button :disabled="busy || !can('finance', 'create')">保存账户</button></form>
      <h2>核实旧账户映射</h2><p>仅明确的一对一映射可承接；显示名称不会自动确定归属。</p><form class="ledger-form" @submit.prevent="run(() => api.post('/finance-ledger/mappings/', mapping), '旧账户映射已留痕。')"><label>旧受控标识<input v-model="mapping.legacy_code" required></label><label>对应自有账户<select aria-label="对应自有账户" v-model="mapping.account" required><option value="">请选择</option><option v-for="a in ownAccounts" :key="a.id" :value="a.id">{{ a.name }}</option></select></label><label>核实依据<input v-model="mapping.reason" required></label><button :disabled="busy || !can('finance', 'update')">保存映射</button></form>
      <h2>核实待定归属</h2><form class="ledger-form" @submit.prevent="run(() => api.post('/finance-ledger/verify_account/', ownership), '账户归属核实已留痕。')"><label>待核实账户<select aria-label="待核实账户" v-model="ownership.account" required><option value="">请选择</option><option v-for="a in state.accounts.filter(a => a.ownership === 'unverified')" :key="a.id" :value="a.id">{{ a.name }}</option></select></label><label>核实归属<select aria-label="核实归属" v-model="ownership.ownership"><option value="own">自有</option><option value="external">外部</option></select></label><label>归属依据<input v-model="ownership.reason" required></label><button :disabled="busy || !can('finance', 'update')">确认归属</button></form>
      <p v-for="m in state.mappings" :key="m.id">{{ m.legacy_code }} → 账户 #{{ m.account_id }} · {{ m.reason }}</p>
    </div>
    <div v-if="tab === 'instructions'">
      <h2>私有凭证</h2><form class="ledger-form" @submit.prevent="upload"><label>凭证文件（PDF / PNG / JPEG，最多10MB）<input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="file = $event.target.files[0]"></label><button :disabled="busy || !can('finance', 'create')">上传凭证</button></form>
      <h2>资金指令</h2><p v-if="recoveredKey">已恢复待核查请求 {{ recoveredKey }}。请先在下方核查保存结果；若结果未知，不得重新生成资金操作。</p>
      <p v-if="draft.kind === 'correction'">更正填写核实后的完整金额、方向和实际日期，不填差额。原版本保留，统计使用经另一人复核的有效版本；已有退款或转账依赖时须先核查。</p>
      <p v-if="draft.kind === 'opening'">基准为所填日期开始时点的独立余额，当日及之后的实际变动另计。请依据对账单选择日期，不把期末余额重复计为当日收入。</p>
      <form class="ledger-form" @submit.prevent="submit"><label>请求标识<input :value="draft.request_key" readonly></label><button type="button" :disabled="busy" @click="newDraft">开始独立新操作</button><label>操作类型<select aria-label="操作类型" v-model="draft.kind"><option v-for="(label, key) in kinds" :key="key" :value="key">{{ label }}</option></select></label><label>自有账户<select aria-label="自有账户" v-model="draft.account" required><option value="">请选择</option><option v-for="a in ownAccounts" :key="a.id" :value="a.id">{{ a.name }}</option></select></label><label>实际日期<input v-model="draft.actual_date" type="date" required></label><label>人民币金额<input v-model="draft.amount" inputmode="decimal" required></label><label>方向<select aria-label="方向" v-model="draft.direction"><option value="income">流入</option><option value="expense">流出</option></select></label><label>资金性质<select aria-label="资金性质" v-model="draft.nature"><option v-for="(label, key) in natures" :key="key" :value="key">{{ label }}</option></select></label><label>真实性<select aria-label="真实性" v-model="draft.truth"><option value="needs_verification">待核实</option><option value="verified">已核实真实资料</option><option value="simulated">模拟资料（不记实际资金）</option></select></label><label>文件凭证<select aria-label="文件凭证" v-model="draft.voucher" required><option value="">请选择</option><option v-for="v in state.vouchers" :key="v.id" :value="v.id">#{{ v.id }} {{ v.name }}</option></select></label><label>来源系统<input v-model="draft.source_system" required></label><label>来源编号<input v-model="draft.source_key" required></label><label>原资金事实编号<input v-model="draft.parent" inputmode="numeric"></label><label>退款批准指令编号<input v-model="draft.approval" inputmode="numeric"></label><label>替代的已取消指令编号<input v-model="draft.replaces" inputmode="numeric"></label><label>原因及凭证依据<input v-model="draft.reason" required></label><label>退款批准及超额性质依据<input v-model="draft.excess_reason"></label>
        <label>既有银行事件编号（需明确账户映射）<input v-model="draft.legacy_parent" inputmode="numeric"></label>
        <fieldset><legend>订单分配（不明确时留空，保留待分配）</legend><div v-for="(a, i) in allocations" :key="i" class="ledger-form"><label>订单编号<input v-model="a.order" inputmode="numeric"></label><label>分配人民币金额<input v-model="a.amount" inputmode="decimal"></label></div><button type="button" @click="allocations.push({ order: '', amount: '' })">增加分配</button></fieldset>
        <button type="button" :disabled="busy" @click="run(async () => { preview = (await api.post('/finance-ledger/preview/', payload())).data }, '只读预检完成，尚未写入。')">只读预检</button><label v-if="preview?.duplicate_candidates.ids.length">疑似重复核实说明<input v-model="duplicateReason"></label><p v-if="preview?.duplicate_candidates.ids.length">疑似重复事实：{{ preview.duplicate_candidates.ids.join('、') }}。请核查后再提交。</p><button :disabled="busy || storageError || !can('finance', 'create')">保存指令</button>
      </form>
      <label class="ledger-check"><input v-model="checked" type="checkbox">已核对实际日期、人民币金额及文件凭证</label>
      <div class="ledger-cards"><article v-for="i in state.instructions" :key="i.id"><strong>指令 #{{ i.id }} · {{ kinds[i.kind] }} · {{ statuses[i.status] }}</strong><p>{{ i.payload.actual_date }} · ¥{{ i.payload.amount }} · {{ i.payload.reason }}</p><p>请求 {{ i.payload.request_key }}</p><p>发起：{{ i.created_actor.kind === 'authenticated_user' ? `用户 #${i.created_actor.user_id}` : '开发身份（非正式审批人）' }}；复核：{{ i.approved_actor.user_id ? `用户 #${i.approved_actor.user_id}` : '尚未复核' }}</p><div class="ledger-actions"><button v-if="i.status === 'pending'" :disabled="busy || !can('finance', 'update')" @click="instructionAction('approve', i)">另一人复核</button><button v-if="['pending', 'approved'].includes(i.status) && i.kind !== 'refund_approval'" :disabled="busy || !can('finance', 'update')" @click="instructionAction('post', i)">确认实际记账</button><button v-if="['pending', 'approved'].includes(i.status)" :disabled="busy || !can('finance', 'update')" @click="instructionAction('cancel', i)">取消并留痕</button><button v-if="['pending', 'approved'].includes(i.status)" :disabled="busy || !can('finance', 'update')" @click="instructionAction('fail', i)">记录失败（未扣款）</button></div></article></div>
    </div>
    <div v-if="tab === 'reviews'"><h2>逐账户核对</h2><p>基准及实际变动可复算；差异未清不得完成核对。迟到记录或更正进入已核对期间后，将重新标记需核对。</p><form class="ledger-form" @submit.prevent="run(() => api.post('/finance-ledger/reviews/', review), '核对记录已保存。')"><label>账户<select aria-label="核对账户" v-model="review.account" required><option value="">请选择</option><option v-for="a in ownAccounts" :key="a.id" :value="a.id">{{ a.name }}</option></select></label><label>核对开始<input v-model="review.date_from" type="date" required></label><label>核对结束<input v-model="review.date_to" type="date" required></label><label>对账单凭证<select aria-label="对账单凭证" v-model="review.voucher" required><option value="">请选择</option><option v-for="v in state.vouchers" :key="v.id" :value="v.id">#{{ v.id }} {{ v.name }}</option></select></label><label>对账单期末余额<input v-model="review.statement_balance" required inputmode="decimal"></label><label>差异及处理依据<input v-model="review.reason" required></label><label class="ledger-check"><input v-model="review.completed" type="checkbox">确认差异为零并完成核对</label><button :disabled="busy || !can('finance', 'update')">保存核对</button></form><div class="ledger-cards"><article v-for="r in state.reviews" :key="r.id"><strong>账户 #{{ r.account }} · {{ r.status === 'completed' ? '核对完成' : r.status === 'needs_review' ? '需重新核对' : '差异待处理' }}</strong><p>{{ r.date_from }} 至 {{ r.date_to }}</p><p>对账单 ¥{{ r.statement_balance }}；复算 ¥{{ r.calculated_balance }}；差异 ¥{{ r.difference }}</p><p>{{ r.reason }} · {{ r.created_at }} · {{ r.actor.user_id ? `用户 #${r.actor.user_id}` : '开发身份' }}</p></article></div></div>
    <div v-if="tab === 'controls'"><h2>核实内部转账</h2><p>须分别保存两端真实事实。允许跨日，差额不能直接认定为手续费；手续费另行登记。</p><form class="ledger-form" @submit.prevent="run(() => api.post('/finance-ledger/transfers/', transfer), '两端本金核实已保存。')"><label>流出事实编号<input v-model="transfer.outgoing" required inputmode="numeric"></label><label>流入事实编号<input v-model="transfer.incoming" required inputmode="numeric"></label><label>两端核实依据<input v-model="transfer.reason" required></label><button :disabled="busy || !can('finance', 'update')">核实两端</button></form><p v-for="t in state.transfers" :key="t.id">事实 #{{ t.outgoing_id }} → #{{ t.incoming_id }} · {{ t.reason }}</p><h2>待分类处理</h2><form class="ledger-form" @submit.prevent="run(() => api.post('/finance-ledger/classifications/', classification), '分类核实已追加，原事实保留。')"><label>事实编号<input v-model="classification.fact" required inputmode="numeric"></label><label>资金性质<select aria-label="分类资金性质" v-model="classification.nature"><option v-for="(label, key) in natures" :key="key" :value="key">{{ label }}</option></select></label><label>核实依据<input v-model="classification.reason" required></label><button :disabled="busy || !can('finance', 'update')">追加分类核实</button></form></div>
    <div v-if="tab === 'controls'"><h2>既有银行事实的转账核实</h2><p>既有银行使用 legacy:编号，新账户事实使用 fact:编号。须先明确账户映射，并分别绑定系统核验的私有文件；不复制或改写原银行事件。</p><form class="ledger-form" @submit.prevent="run(() => api.post('/finance-ledger/transfers/', transfer), '既有两端本金已留痕核实。')"><label>流出引用<input v-model="transfer.outgoing" required placeholder="legacy:1"></label><label>流入引用<input v-model="transfer.incoming" required placeholder="legacy:2 或 fact:2"></label><label>流出文件凭证<select v-model="transfer.outgoing_voucher" aria-label="流出文件凭证" required><option value="">请选择</option><option v-for="v in state.vouchers" :key="v.id" :value="v.id">#{{ v.id }} {{ v.name }}</option></select></label><label>流入文件凭证<select v-model="transfer.incoming_voucher" aria-label="流入文件凭证" required><option value="">请选择</option><option v-for="v in state.vouchers" :key="v.id" :value="v.id">#{{ v.id }} {{ v.name }}</option></select></label><label>历史两端核实依据<input v-model="transfer.reason" required></label><button :disabled="busy || !can('finance', 'update')">核实既有银行两端</button></form><p v-for="t in state.historical_transfers" :key="t.id">流出 {{ t.outgoing_legacy_id ? `银行事件 #${t.outgoing_legacy_id}` : `账户事实 #${t.outgoing_fact_id}` }} → 流入 {{ t.incoming_legacy_id ? `银行事件 #${t.incoming_legacy_id}` : `账户事实 #${t.incoming_fact_id}` }} · {{ t.reason }}</p></div>
  </section>
</template>

<style scoped>
.ledger-page{display:grid;gap:18px;min-width:0}.ledger-heading{display:flex;justify-content:space-between;gap:16px;align-items:start}.ledger-heading h1{margin:0;font-size:24px}.ledger-page p{font-size:14px;line-height:1.65;overflow-wrap:anywhere;color:#526171}.ledger-tabs,.ledger-actions,.ledger-totals{display:flex;flex-wrap:wrap;gap:10px}.ledger-page button{min-height:40px;padding:8px 14px;border:1px solid #ccd5dc;border-radius:8px;background:white;color:#203446;font-size:14px;cursor:pointer}.ledger-page button[aria-pressed=true]{background:#e5f1f7;border-color:#5b8fa4}.ledger-page button:disabled{opacity:.55;cursor:default}.ledger-form{display:flex;flex-wrap:wrap;gap:14px;align-items:end}.ledger-form label{display:grid;gap:6px;flex:1 1 210px;min-width:0;font-size:14px}.ledger-form input,.ledger-form select{width:100%;min-width:0;min-height:42px;border:1px solid #c9d3dc;border-radius:8px;padding:9px;box-sizing:border-box;font:inherit;background:white}.ledger-form fieldset{width:100%;min-width:0;border:1px solid #d9e0e7;border-radius:8px}.ledger-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:14px;margin-top:18px}.ledger-cards article{min-width:0;border:1px solid #dce3e9;border-radius:12px;padding:18px;background:white;overflow-wrap:anywhere}.ledger-cards code{display:block;overflow-wrap:anywhere;white-space:normal;font-size:13px}.ledger-error{padding:12px;border:1px solid #dfaaa6;background:#fff4f2;color:#943b32!important;border-radius:8px}.ledger-check{display:flex!important;align-items:center;gap:8px;font-size:14px;margin:14px 0}.ledger-check input{width:auto;min-height:20px}.ledger-totals span{padding:14px;background:#edf4f7;border-radius:10px}.ledger-page h2{font-size:18px;margin:22px 0 12px}@media(max-width:500px){.ledger-form label{flex-basis:100%}.ledger-tabs button{flex:1 1 42%}.ledger-heading h1{font-size:22px}.ledger-cards article{padding:14px}}
</style>
