<script setup>
import { BOOK_RMB_NOTE } from '../utils/financeBasis.js'
import CertificateExpiryBadge from '../components/CertificateExpiryBadge.vue'
import PageLoadState from '../components/PageLoadState.vue'
import { computed, onMounted, ref } from 'vue'
import { RefreshCw, ChevronRight } from 'lucide-vue-next'
import { api } from '../api'
import { apiErrorMessage } from '../utils/apiErrors'
import { useAccessControl } from '../accessControl'

const { can } = useAccessControl()
const data = ref(null), loading = ref(false), error = ref(''), notice = ref(''), loadedAt = ref(null)
let sequence = 0
async function load() {
  if (loading.value) return
  const current = ++sequence
  loading.value = true; error.value = ''; notice.value = ''
  try {
    const result = (await api.get('/dashboard/')).data
    if (current !== sequence) return
    const refreshed = Boolean(data.value)
    data.value = result; loadedAt.value = new Date()
    if (refreshed) notice.value = '经营数据已刷新。'
  } catch (err) { if (current === sequence) error.value = apiErrorMessage(err) || '经营数据暂时无法加载，请点“刷新数据”重试。' }
  finally { if (current === sequence) loading.value = false }
}
const dateRanges = computed(() => data.value?.date_ranges || {})
const yearStart = computed(() => dateRanges.value.year_start || '—')
const asOf = computed(() => dateRanges.value.as_of || '—')
const trendStart = computed(() => dateRanges.value.trend_start || '—')
const trendEnd = computed(() => dateRanges.value.trend_end || asOf.value)
const refreshTime = computed(() => loadedAt.value?.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) || '')
const trend = computed(() => { const a = Number(data.value?.summary.sales_ytd || 0), b = Number(data.value?.summary.sales_last_ytd || 0); return b ? ((a / b - 1) * 100).toFixed(1) : null })
const monthly = computed(() => data.value?.monthly_sales || [])
const chartMax = computed(() => Math.max(...monthly.value.map(i => Number(i.sales)), 1))
const categoryTotal = computed(() => (data.value?.category_sales || []).reduce((s, i) => s + Number(i.sales), 0) || 1)
const navigation = computed(() => [
  { label: '报表中心', path: '/reports', module: 'reports' },
  { label: '订单管理', path: '/orders', module: 'orders' },
  { label: '客户管理', path: '/customers', module: 'customers' },
  { label: '财务概览', path: '/finance', module: 'finance' },
].filter(item => can(item.module, 'view')))
const colors = ['#1d5a50','#e4813e','#6d8ea0','#c49b62','#897aa5']
function money(value) { return `¥ ${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` }
function short(value) { const n = Number(value || 0); return Math.abs(n) >= 10000 ? `${(n / 10000).toFixed(1)}万` : n.toLocaleString('zh-CN') }
onMounted(load)
</script>

<template>
  <div class="dashboard" :aria-busy="loading">
    <header class="dashboard-toolbar">
      <div><p class="page-lede">查看销售额、待跟进事项和收支。</p><small v-if="loadedAt">更新于 {{ refreshTime }}</small></div>
      <button type="button" :disabled="loading" @click="load"><RefreshCw :size="15" />{{ loading ? '刷新中…' : '刷新数据' }}</button>
    </header>
    <PageLoadState :loading="loading" :has-loaded="!!data" :error="error" @retry="load" />
    <p v-if="notice" class="page-notice" role="status">{{ notice }}</p>
    <nav v-if="navigation.length" class="dashboard-shortcuts" aria-label="经营快捷入口"><RouterLink v-for="item in navigation" :key="item.path" :to="item.path">{{ item.label }}<ChevronRight :size="14" /></RouterLink></nav>
    <template v-if="data">
      <section class="dashboard-section" aria-labelledby="sales-section-title">
        <div class="section-heading"><div><h2 id="sales-section-title">销售与客户</h2><p>按订单日期和合同金额统计，按订单汇率折算成人民币；不等于实际收款。</p></div><span>{{ yearStart }} — {{ asOf }}</span></div>
        <div class="metric-grid">
          <article v-if="can('orders', 'view')" class="metric-card featured"><span>本年截至今日销售额</span><strong>{{ money(data.summary.sales_ytd) }}</strong><small>{{ yearStart }} — {{ asOf }}</small><small v-if="trend !== null" :class="Number(trend) >= 0 ? 'up' : 'down'">{{ Number(trend) > 0 ? '+' : '' }}{{ trend }}% 较去年同期</small><small v-else>去年同期为零，暂不计算变化率</small></article>
          <article v-if="can('orders', 'view')" class="metric-card"><span>本年截至今日订单数</span><strong>{{ data.summary.orders_ytd }}</strong><small>{{ yearStart }} — {{ asOf }} · 正式订单</small></article>
          <article v-if="can('customers', 'view')" class="metric-card"><span>合作中客户</span><strong>{{ data.summary.active_customers }}</strong><small>按当前客户档案统计</small></article>
          <article v-if="can('followups', 'view')" class="metric-card"><span>当前待跟进</span><strong>{{ data.summary.follow_ups_due }}</strong><small>含今天到期和已逾期的跟进</small></article>
        </div>
        <p v-if="!can('orders', 'view')" class="access-note">当前账号没有订单查看权限。</p>
      </section>
      <div class="dash-grid" v-if="can('orders', 'view')">
        <section class="panel chart-panel" aria-label="销售趋势"><div class="panel-title"><div><h2>销售趋势</h2><p>最近12个自然月（{{ trendStart }} — {{ trendEnd }}）· 人民币</p></div></div>
          <div v-if="monthly.length" class="bar-scroll"><div class="bar-chart" role="img" aria-label="各月份销售额与订单数" :style="{ minWidth: `${Math.max(420, monthly.length * 58)}px` }"><div v-for="item in monthly" :key="item.month" class="bar-slot" :title="`${item.month}：${money(item.sales)}，${item.orders} 单`"><span class="bar-value">{{ short(item.sales) }}</span><div class="bar" :style="{ height: `${Math.max(Number(item.sales) / chartMax * 145, 2)}px` }" /><span class="month-label">{{ item.month }}</span><small>{{ item.orders }} 单</small></div></div></div><p v-else class="empty compact">暂无月度销售数据。</p>
          <p class="scope-note">按订单日期统计，含本月和前 11 个月；无订单的月份按 0 显示。</p>
        </section>
        <section v-if="can('products', 'view') && can('categories', 'view')" class="panel category-panel" aria-label="分类销售额"><div class="panel-title"><div><h2>分类销售额</h2><p>{{ yearStart }} — {{ asOf }} · 销售额最高的 8 个分类</p></div></div>
          <div v-if="data.category_sales.length" class="category-list"><div v-for="(item,index) in data.category_sales" :key="index" class="category-row"><div class="category-meta"><span><i :style="{ background: colors[index%5] }" />{{ item.sku__product__category__name || '未分类' }}</span><strong>{{ money(item.sales) }}</strong></div><div class="progress"><i :style="{ width: `${Number(item.sales)/categoryTotal*100}%`, background: colors[index%5] }" /></div></div></div><p v-else class="empty compact">暂无分类销售数据。</p>
          <p class="scope-note">仅统计产品金额，不含运费、折扣和合同调整；占比按当前显示的分类计算。</p>
        </section>
      </div>
      <div class="dash-bottom">
        <section v-if="can('customers', 'view') && can('orders', 'view')" class="panel list-panel" aria-label="重点客户"><div class="panel-title"><div><h2>重点客户</h2><p>{{ yearStart }} — {{ asOf }} · 销售额前 6 名</p></div><RouterLink to="/customers">客户列表 <ChevronRight :size="14" /></RouterLink></div><div class="customer-list"><RouterLink v-for="(c,index) in data.top_customers" :key="c.id" :to="{ path: '/customers', query: { detail: c.id } }" class="customer-item"><span class="rank">{{ index+1 }}</span><div class="grow"><strong :title="c.name">{{ c.name }}</strong><small>{{ c.country || '未填写国家' }} · {{ c.orders }} 个订单</small></div><strong class="amount">{{ money(c.sales) }}</strong></RouterLink><p v-if="!data.top_customers.length" class="empty compact">暂无客户销售记录。</p></div></section>
        <section v-if="can('followups', 'view')" class="panel list-panel" aria-label="待跟进事项"><div class="panel-title"><div><h2>待跟进事项</h2><p>今天到期和已逾期的跟进，显示前 5 条</p></div><RouterLink to="/follow-ups?due=true">全部待跟进 <ChevronRight :size="14" /></RouterLink></div><RouterLink v-for="f in data.due_follow_ups" :key="f.id" :to="{ path: '/follow-ups', query: { due: 'true', detail: f.id } }" class="follow-item"><div class="date-box"><strong>{{ f.next_follow_up?.slice(8,10) }}</strong><span>{{ f.next_follow_up?.slice(5,7) }}月</span></div><div class="grow"><strong :title="f.customer_name">{{ f.customer_name }}</strong><small :title="f.subject">{{ f.subject }}</small></div><span class="owner" :title="f.owner">{{ f.owner || '未分配' }}</span></RouterLink><p v-if="!data.due_follow_ups.length" class="empty compact">没有待跟进事项。</p></section>
      </div>
      <section v-if="can('certificates', 'view') && can('products', 'view')" class="panel list-panel certificate-reminders" aria-label="证书到期提醒"><div class="panel-title"><div><h2>证书到期提醒</h2><p v-if="data.summary.certificate_attention">需关注 {{ data.summary.certificate_attention }} 个 · 已过期 {{ data.summary.certificate_expired }} 个 · 90 天内到期 {{ data.summary.certificate_expiring }} 个</p><p v-else>暂无已过期或 90 天内到期的证书。</p></div><RouterLink to="/product-certificates?expiry=attention">全部需关注证书 <ChevronRight :size="14" /></RouterLink></div><RouterLink v-for="c in data.certificate_alerts || []" :key="c.id" :to="{ path: '/product-certificates', query: { expiry: 'attention', detail: c.id } }" class="follow-item certificate-item"><div class="grow"><strong :title="c.product_name">{{ c.product_name }}</strong><small :title="c.certificate_name">{{ c.certificate_name }} · {{ c.certificate_no || '无编号' }}</small></div><span>{{ c.expires_on }}</span><CertificateExpiryBadge :certificate="c" /></RouterLink></section>
      <section v-if="can('transactions', 'view')" class="dashboard-section" aria-labelledby="cash-section-title"><div class="section-heading"><div><h2 id="cash-section-title">账面收支（人民币折算参考）</h2><p>按流水发生日期，{{ yearStart }} — {{ asOf }} 汇总；仅已确认流水。{{ BOOK_RMB_NOTE }}</p></div></div><div class="cash-strip"><div><span>账面收入（折算参考）</span><strong>{{ money(data.summary.receipts_rmb) }}</strong></div><div><span>账面支出（折算参考）</span><strong>{{ money(data.summary.payments_rmb) }}</strong></div><div><span>账面净收支（收入 − 支出）</span><strong :class="Number(data.summary.receipts_rmb)-Number(data.summary.payments_rmb)>=0?'positive':'negative'">{{ money(Number(data.summary.receipts_rmb)-Number(data.summary.payments_rmb)) }}</strong></div></div></section>
    </template>
  </div>
</template>

<style scoped>
.dashboard{display:grid;gap:20px;min-width:0}.dashboard-toolbar,.section-heading,.panel-title{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.dashboard-toolbar button{display:flex;align-items:center;gap:7px;flex:none;border:1px solid #d5dfd8;background:white;border-radius:8px;padding:9px 13px;color:#265c4a;cursor:pointer}.dashboard-toolbar button:disabled{opacity:.5;cursor:default}.page-lede{margin:0;color:#60756a}.dashboard-toolbar small,.section-heading p,.section-heading>span,.panel-title p,.scope-note{font-size:var(--text-caption);color:#6c8075;line-height:1.7}.dashboard-toolbar small{display:block;margin-top:5px}.page-notice{margin:0;padding:10px 14px;border:1px solid #bedbcc;border-radius:9px;background:#f0f8f3;color:#205845}.dashboard-shortcuts{display:flex;gap:10px;flex-wrap:wrap}.dashboard-shortcuts a{display:flex;align-items:center;gap:16px;padding:9px 12px;background:#fff;border:1px solid #dfe7e2;border-radius:8px;text-decoration:none;color:#275d4b;font-size:var(--text-body)}.dashboard h2{margin:0;font-size:var(--text-section);color:#243e32}.section-heading{margin-bottom:12px}.section-heading p,.panel-title p{margin:5px 0 0}.section-heading>span{white-space:nowrap}.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.metric-card{min-width:0;background:#fff;border:1px solid #dfe7e2;border-radius:12px;padding:18px}.metric-card.featured{border-top:3px solid #1d5a50;padding-top:16px}.metric-card>span{font-size:var(--text-body);color:#576e61}.metric-card>strong{display:block;margin:12px 0 8px;font-size:clamp(22px,2vw,30px);color:#173d30;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.metric-card small{display:block;color:#718377;font-size:var(--text-caption);line-height:1.7}.up,.positive{color:#247558!important}.down,.negative{color:#a34636!important}.dash-grid,.dash-bottom{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;min-width:0}.chart-panel,.category-panel,.list-panel{padding:20px;min-width:0}.panel-title a{display:flex;align-items:center;gap:3px;color:#356b54;text-decoration:none;font-size:var(--text-caption);flex:none}.panel-title{margin-bottom:10px}.scope-note{margin:14px 0 0}.bar-scroll{overflow-x:auto;padding-bottom:6px}.bar-chart{height:225px;display:flex;gap:8px;align-items:flex-end;padding:15px 4px}.bar-slot{flex:1;min-width:48px;height:200px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end}.bar{width:28px;background:#2c7467;border-radius:4px 4px 0 0}.bar-value,.month-label,.bar-slot small{font-size:var(--text-caption);color:#607669}.bar-value{margin-bottom:5px}.month-label{margin-top:8px;white-space:nowrap}.bar-slot small{margin-top:3px}.category-list{margin-top:18px}.category-row{margin:14px 0}.category-meta{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;font-size:var(--text-body)}.category-meta span{min-width:0;overflow-wrap:anywhere}.category-meta i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:7px}.category-meta strong{font-size:var(--text-caption);text-align:right;max-width:55%;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.progress{height:5px;background:#edf1ee;border-radius:5px;margin-top:8px;overflow:hidden}.progress i{height:100%;display:block}.customer-item,.follow-item{display:flex;align-items:center;gap:12px;padding:13px 0;border-bottom:1px solid #edf0ee;color:inherit;text-decoration:none}.customer-item:hover,.follow-item:hover{background:#f7faf8}.rank{font-size:var(--text-caption);color:#85968a;flex:none}.grow{flex:1;min-width:0}.grow strong,.grow small{display:block}.grow strong{font-size:var(--text-body);white-space:normal;overflow-wrap:anywhere}.grow small{font-size:var(--text-caption);color:#718377;margin-top:4px;overflow-wrap:anywhere}.amount{max-width:44%;font-size:var(--text-body);text-align:right;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.owner{font-size:var(--text-caption);background:#f0f3f1;border-radius:14px;padding:4px 8px;max-width:26%;overflow-wrap:anywhere;color:#617568}.date-box{flex:none;width:34px;text-align:center;padding:5px;border-radius:7px;background:#fff1df;color:#a96528}.date-box strong,.date-box span{display:block;font-size:var(--text-caption)}.certificate-item>span{flex:none;font-size:var(--text-caption)}.cash-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;background:#fbfaf7;border:1px solid #ebe6dc;border-radius:12px;padding:20px}.cash-strip span{display:block;font-size:var(--text-caption);color:#736f64}.cash-strip strong{display:block;font-size:var(--text-dialog);margin-top:8px;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.compact{margin:0;padding:28px 10px;text-align:center;color:#718377;font-size:var(--text-body)}.access-note{color:#718377;font-size:var(--text-body)}
@media(max-width:1300px){.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.dash-grid,.dash-bottom{grid-template-columns:1fr}}@media(max-width:650px){.dashboard-toolbar,.section-heading,.panel-title{flex-wrap:wrap}.cash-strip{grid-template-columns:1fr}.chart-panel,.category-panel,.list-panel{padding:16px}.certificate-item{flex-wrap:wrap}.certificate-item .grow{flex-basis:100%}.metric-card{padding:14px}}@media(max-width:430px){.metric-grid{grid-template-columns:1fr}}
</style>
