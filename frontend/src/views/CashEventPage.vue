<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
import { apiErrorMessage } from '../utils/apiErrors.js'
import { useAccessControl } from '../accessControl'
import PageLoadState from '../components/PageLoadState.vue'
import ListEmptyState from '../components/ListEmptyState.vue'
import CashEventEntryForm from '../components/CashEventEntryForm.vue'

const { api } = useWorkspaceApi()
const { can } = useAccessControl()
const route = useRoute()
const events = ref([]), loading = ref(true), hasLoaded = ref(false), loadError = ref('')
const error = ref(''), notice = ref(''), statusFilter = ref(''), listSearch = ref('')
const selected = ref(null), showForm = ref(false)

function money(value, currency = 'CNY') {
  if (value === null || value === undefined || value === '') return '待核对'
  const digits = currency === 'JPY' ? 0 : 2
  return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}
function statusLabel(value) { return ({ pending: '待确认', confirmed: '已确认', cancelled: '已放弃' })[value] || value || '—' }
function kindLabel(value) { return ({ fx_settlement: '外币结汇流入', cny_direct: '人民币直接收付', bank_fee: '独立银行扣费' })[value] || value || '—' }
function directionLabel(value) { return value === 'income' ? '流入' : value === 'expense' ? '流出' : '—' }
async function loadEvents({ openRouteDetail = false } = {}) {
  loading.value = true; loadError.value = ''
  try {
    events.value = (await api.get('/rmb-cash-events/')).data.results || []; hasLoaded.value = true
    const detailId = Number(route.query.event)
    if (openRouteDetail && detailId > 0 && !showForm.value && !selected.value) {
      const row = events.value.find(item => item.id === detailId)
      if (row) openDetail(row)
    }
  } catch (err) { loadError.value = apiErrorMessage(err) || '人民币资金记录加载失败，请重试。' }
  finally { loading.value = false }
}
function openCreate() { selected.value = null; showForm.value = true; error.value = ''; notice.value = '' }
function openDetail(row) {
  selected.value = row
  showForm.value = row.status === 'pending' && can('finance', 'update')
  error.value = ''; notice.value = ''
}
function closeEntry() { showForm.value = false }
async function refreshAfterSave(row) {
  if (row) selected.value = row
  // Keep the save response authoritative for the active review. Replacing it
  // with a list row would reset the user's voucher confirmation mid-review.
  await loadEvents()
}
function filteredEvents() {
  const keyword = listSearch.value.trim().toLowerCase()
  return events.value.filter(row => (!statusFilter.value || row.status === statusFilter.value) && (!keyword || `${row.event_no} ${row.bank_reference}`.toLowerCase().includes(keyword)))
}
const filtered = computed(filteredEvents)
onMounted(() => loadEvents({ openRouteDetail: true }))
</script>

<template>
  <section class="cash-events-page">
    <header class="cash-page-head">
      <div><p class="eyebrow">人民币资金</p><h2>银行资金记录</h2><p class="page-lede">登记实际到账信息。只有完成凭证核验的资金事件才计入银行资金汇总；客户收款和应收核销仍按原流程保存。</p></div>
      <div class="head-actions"><RouterLink class="secondary-link" to="/transactions">查看财务流水</RouterLink><button v-if="can('transactions', 'create')" class="primary" type="button" @click="openCreate">新增资金事件</button></div>
    </header>
    <p class="definition-note"><strong>核对口径：</strong>银行净额以实际凭证为准；手续费已计入净额时不再重复扣除。仅已核对并绑定实际银行凭证的事件可以确认。</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <form class="cash-filters" aria-label="人民币资金筛选" @submit.prevent>
      <label>状态<select v-model="statusFilter"><option value="">全部状态</option><option value="pending">待确认</option><option value="confirmed">已确认</option><option value="cancelled">已放弃</option></select></label>
      <label class="search-field">搜索<input v-model="listSearch" type="search" placeholder="事件编号或银行参考号"></label>
      <button type="button" class="secondary" @click="loadEvents">刷新</button>
    </form>
    <p class="field-hint">列表包含待确认、已确认和已放弃记录；只有已确认事件计入银行资金汇总。</p>
    <PageLoadState v-if="loading && !hasLoaded" :loading="loading" />
    <div v-else-if="loadError" class="cash-load-error" role="alert"><p>{{ loadError }}</p><button type="button" @click="loadEvents">重试</button></div>
    <ListEmptyState v-else-if="!filtered.length" entity="人民币资金记录" :filtered="statusFilter || listSearch" @clear="statusFilter='';listSearch=''" />
    <div v-else class="cash-table-wrap"><table class="cash-table"><thead><tr><th>实际到账日期 / 事件编号</th><th>类型 / 方向</th><th>来源金额</th><th>银行净额 / 参考号</th><th>手续费</th><th>状态</th><th>操作</th></tr></thead><tbody>
      <tr v-for="row in filtered" :key="row.id" class="cash-row" @click="openDetail(row)"><td>{{ row.bank_date }}<small>{{ row.event_no }}</small></td><td>{{ kindLabel(row.kind) }}<small>{{ directionLabel(row.direction) }}</small></td><td>{{ row.currency }} {{ money(row.amount, row.currency) }}<small>{{ row.sources?.length || 0 }} 条来源</small></td><td>CNY {{ money(row.bank_net_amount) }}<small>{{ row.bank_reference }}</small></td><td>{{ row.fee_mode === 'included' ? `含扣 CNY ${money(row.fee_amount)}` : '无' }}</td><td><span class="status" :class="row.status">{{ statusLabel(row.status) }}</span></td><td><button type="button" class="row-action" @click.stop="openDetail(row)">查看详情</button></td></tr>
    </tbody></table></div>

    <div v-if="selected && !showForm" class="cash-detail-panel" role="dialog" aria-modal="true" aria-labelledby="cash-detail-title">
      <header><div><p class="eyebrow">银行资金事件</p><h3 id="cash-detail-title">{{ selected.event_no }}</h3></div><button type="button" class="close-button" aria-label="关闭资金详情" @click="selected = null">×</button></header>
      <div class="detail-status"><span class="status" :class="selected.status">{{ statusLabel(selected.status) }}</span><span>{{ kindLabel(selected.kind) }} · {{ directionLabel(selected.direction) }}</span></div>
      <dl class="detail-grid"><dt>实际到账日期</dt><dd>{{ selected.bank_date }}</dd><dt>银行净额</dt><dd>CNY {{ money(selected.bank_net_amount) }}</dd><dt>来源金额</dt><dd>{{ selected.currency }} {{ money(selected.amount, selected.currency) }}</dd><dt>手续费</dt><dd>{{ selected.fee_mode === 'included' ? `含扣 CNY ${money(selected.fee_amount)}` : '无' }}</dd><dt>银行参考号</dt><dd>{{ selected.bank_reference }}</dd><dt>来源账户</dt><dd>{{ selected.source_account_name || '账户名称待配置' }}</dd><dt>人民币账户</dt><dd>{{ selected.rmb_account_name || '账户名称待配置' }}</dd><dt>关联订单</dt><dd>{{ selected.orders?.map(item => item.order_no).filter(Boolean).join('、') || '—' }}</dd><dt>收款流水</dt><dd>{{ selected.source_receipt?.transaction_no || '—' }}</dd><dt>凭证</dt><dd>{{ selected.private_voucher ? '实际凭证已校验' : '历史记录缺少实际凭证文件' }}</dd></dl>
      <p v-if="selected.evidence_note" class="detail-note">{{ selected.evidence_note }}</p>
      <p v-if="!selected.private_voucher" class="field-hint">需要确认此历史事件时，请补传原始银行凭证文件后再核对。</p>
      <p v-if="selected.private_voucher"><a :href="`/api/rmb-cash-events/${selected.id}/voucher-download/`">下载银行凭证</a></p>
      <section><h4>结汇来源</h4><table class="source-detail"><thead><tr><th>来源流水</th><th>本次结汇</th></tr></thead><tbody><tr v-for="source in selected.sources" :key="source.transaction_id"><td>{{ source.snapshot?.transaction_no || `流水 #${source.transaction_id}` }}</td><td>{{ source.currency }} {{ money(source.amount, source.currency) }}</td></tr></tbody></table></section>
      <footer class="detail-actions"><button type="button" class="secondary" @click="selected = null">关闭</button><button v-if="selected.status === 'pending' && can('finance', 'update')" type="button" class="primary" @click="showForm = true">核对并确认</button></footer>
    </div>

    <CashEventEntryForm v-if="showForm" :key="selected?.id || 'new'" mode="standalone" :initial-event="selected" @close="closeEntry" @created="refreshAfterSave" @updated="refreshAfterSave" />
  </section>
</template>

<style scoped>
.cash-events-page{padding:0}.cash-page-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.cash-page-head h2{margin:0;font-size:var(--text-title)}.eyebrow{margin:0 0 5px;color:#618075;font-size:var(--text-caption);text-transform:uppercase;letter-spacing:.04em}.page-lede{margin:6px 0 0;color:#718078;line-height:1.6}.head-actions{display:flex;gap:8px;align-items:center}.head-actions button,.secondary-link,.cash-filters button,.cash-load-error button{padding:8px 13px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#344d44;text-decoration:none;cursor:pointer}.head-actions .primary{background:#0d4b40;color:white;border-color:#0d4b40}.definition-note{margin:16px 0;padding:12px 14px;border:1px solid #e0e8e2;border-radius:9px;background:#f7faf8;color:#526b5d;line-height:1.6}.notice{margin:12px 0;padding:10px 14px;border:1px solid #b8d8ca;border-radius:9px;background:#eff8f3;color:#1d4d40}.error{color:#b42318}.cash-filters{display:grid;grid-template-columns:180px minmax(220px,1fr) auto;gap:10px;align-items:end;margin:18px 0 8px;padding:14px;border:1px solid #e2e8e4;border-radius:12px;background:#fff}.cash-filters label{display:grid;gap:5px;color:#586b63;font-size:var(--text-body)}.cash-filters input,.cash-filters select{width:100%;height:39px;padding:0 10px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#253b33}.field-hint{color:#718078;font-size:var(--text-caption)}.cash-table-wrap{overflow:auto;margin-top:14px;border:1px solid #e2e8e4;border-radius:12px;background:#fff}.cash-table{width:100%;border-collapse:collapse;white-space:nowrap}.cash-table th,.cash-table td{padding:12px;text-align:left;border-bottom:1px solid #edf1ee}.cash-table th{background:#f6faf8;color:#60736b}.cash-table td small{display:block;margin-top:4px;color:#718078}.cash-row{cursor:pointer}.cash-row:hover{background:#f8fbf9}.status{display:inline-block;padding:3px 8px;border-radius:999px;background:#edf3ef}.status.confirmed{background:#e8f5eb;color:#1f6b41}.status.pending{background:#fff5df;color:#805b14}.status.cancelled{background:#f4eeee;color:#785858}.row-action{padding:5px 9px;border:1px solid #d8e1dd;border-radius:7px;background:#fff;color:#31594b;cursor:pointer}.cash-detail-panel{position:fixed;z-index:55;right:24px;top:84px;width:min(560px,calc(100vw - 48px));max-height:calc(100vh - 108px);overflow:auto;padding:22px;background:#fff;border:1px solid #dce7df;border-radius:14px;box-shadow:0 22px 60px #001a1330}.cash-detail-panel header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.cash-detail-panel h3{margin:0;color:#173d30;font-size:var(--text-dialog);overflow-wrap:anywhere}.close-button{padding:2px 8px;border:0;background:transparent;font-size:22px;cursor:pointer}.detail-status{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:14px 0}.detail-grid{display:grid;grid-template-columns:130px minmax(0,1fr);gap:8px;margin:0}.detail-grid dt{color:#718078;font-size:var(--text-caption)}.detail-grid dd{margin:0;color:#25463a;overflow-wrap:anywhere}.detail-note{padding:10px 12px;background:#f6f8f6;border-radius:8px;color:#62776a;line-height:1.6}.cash-detail-panel section{margin-top:18px}.cash-detail-panel h4{margin:0 0 8px}.source-detail{width:100%;border-collapse:collapse}.source-detail th,.source-detail td{padding:8px;text-align:left;border-bottom:1px solid #edf1ee}.detail-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}.detail-actions button{padding:8px 13px;border:1px solid #d8e1dd;border-radius:8px;background:#fff;color:#344d44;cursor:pointer}.detail-actions .primary{background:#0d4b40;color:#fff;border-color:#0d4b40}.cash-load-error{padding:20px;border:1px solid #f2c9c5;border-radius:10px;background:#fff6f5;color:#913d34}
@media(max-width:760px){.cash-page-head{flex-direction:column}.head-actions{width:100%}.head-actions>*{flex:1;text-align:center}.cash-filters{grid-template-columns:1fr 1fr}.cash-filters .search-field{grid-column:1/-1}.cash-filters button{width:100%}.cash-detail-panel{right:10px;top:70px;width:calc(100vw - 20px);max-height:calc(100vh - 80px);padding:16px}.detail-grid{grid-template-columns:105px minmax(0,1fr)}}
</style>
