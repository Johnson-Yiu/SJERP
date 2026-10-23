<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../../api'
import { apiErrorMessage } from '../../utils/apiErrors'
import { orderDetailLocation, purchaseDetailLocation } from '../../utils/detailNavigation'
import { useRoute } from 'vue-router'

const props = defineProps({
  query: { type: Object, required: true },
  selection: { type: Object, required: true },
  sourceLabel: { type: String, default: '' },
})
const emit = defineEmits(['close'])
const route = useRoute()
const data = ref(null), loading = ref(false), error = ref(''), page = ref(1), ordering = ref('-document_date')
let sequence = 0

const isPurchase = computed(() => props.query.source === 'purchase')
const partyLabel = computed(() => isPurchase.value ? '供应商' : '客户')
const rows = computed(() => data.value?.rows || [])
const pageCount = computed(() => Math.max(1, Number(data.value?.page_count || 1)))
const selectionText = computed(() => (props.selection.groups || []).map(group => `${group.label}`).join(' · '))
const totalText = computed(() => {
  const quantities = Object.entries(data.value?.totals?.quantities || {}).map(([unit, value]) => `${value} ${unit}`)
  return quantities.join(' / ') || '—'
})
const formatNumber = value => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(Number(value || 0))
const formatAmount = value => formatNumber(value)
const detailParams = computed(() => ({
  ...props.query,
  group_value: props.selection.groups?.[0]?.key,
  ...(props.query.group_by_2 ? { group_2_value: props.selection.groups?.[1]?.key } : {}),
  page: page.value,
  page_size: 20,
  ordering: ordering.value,
}))
const orderLink = row => (isPurchase.value ? purchaseDetailLocation(row.document_id, 'overview', route.fullPath) : orderDetailLocation(row.document_id, 'overview', route.fullPath))

async function load() {
  const current = ++sequence
  loading.value = true; error.value = ''
  try {
    const response = await api.get('/reports/details/', { params: detailParams.value })
    if (current === sequence) data.value = response.data
  } catch (err) {
    if (current === sequence) error.value = apiErrorMessage(err) || '构成明细加载失败，请重试。'
  } finally {
    if (current === sequence) loading.value = false
  }
}
function changePage(next) {
  if (next < 1 || next > pageCount.value) return
  page.value = next; void load()
}
function changeOrdering() { page.value = 1; void load() }
watch(() => [props.query, props.selection], () => { page.value = 1; data.value = null; void load() }, { immediate: true, deep: true })
</script>

<template>
  <section class="report-detail-panel" aria-label="构成明细">
    <header class="detail-panel-head">
      <div>
        <small>原始业务记录</small>
        <h3>构成明细<span v-if="selectionText"> · {{ selectionText }}</span></h3>
        <p>{{ sourceLabel }} · {{ data?.date_label || '统计日期' }} · {{ data?.period?.date_from || query.date_from }} — {{ data?.period?.date_to || query.date_to }}</p>
      </div>
      <button type="button" @click="emit('close')">收起明细</button>
    </header>
    <div v-if="loading" role="status" class="detail-panel-state">正在加载构成明细…</div>
    <div v-else-if="error" role="alert" class="detail-panel-error">{{ error }} <button type="button" @click="load">重试</button></div>
    <template v-else-if="data">
      <div class="detail-panel-summary"><span>明细记录 {{ data.count }} 条 · 去重单据 {{ data.totals.count }} 张</span><span>金额合计 ¥ {{ formatAmount(data.totals.amount) }} · 数量 {{ totalText }}</span></div>
      <div v-if="!rows.length" class="detail-panel-state" role="status">该分组暂无可展示的原始业务记录。</div>
      <div v-else class="detail-table-wrap">
        <table class="detail-table">
          <thead><tr><th>{{ isPurchase ? '采购单号' : '销售订单编号' }}</th><th>{{ isPurchase ? '下单日期' : '订单日期' }}</th><th>{{ partyLabel }}</th><th>SKU / 商品名称</th><th>{{ isPurchase ? '采购数量 / 单位' : '商品数量 / 交易单位' }}</th><th>对应金额（人民币）</th><th>状态</th><th>原始单据</th></tr></thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td><strong>{{ row.document_no }}</strong><small v-if="row.is_adjustment">金额调整行</small></td>
              <td>{{ row.document_date }}</td>
              <td>{{ isPurchase ? row.supplier_name : row.customer_name }}</td>
              <td><strong>{{ row.is_adjustment ? '订单金额调整' : row.sku }}</strong><small v-if="!row.is_adjustment">{{ row.product_name }}</small></td>
              <td>{{ row.is_adjustment ? '—' : `${formatNumber(row.quantity)} ${row.unit || ''}` }}</td>
              <td>{{ formatAmount(row.amount) }}</td>
              <td>{{ row.status_display || row.status }}</td>
              <td><RouterLink class="detail-order-link" :to="orderLink(row)">打开详情</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer class="detail-panel-footer"><label>排序<select v-model="ordering" @change="changeOrdering"><option value="-document_date">日期从新到旧</option><option value="document_date">日期从旧到新</option><option value="amount">金额从低到高</option><option value="-amount">金额从高到低</option><option value="document_no">单据编号</option></select></label><span>第 {{ data.page }} / {{ pageCount }} 页</span><button type="button" :disabled="data.page <= 1" @click="changePage(data.page - 1)">上一页</button><button type="button" :disabled="data.page >= pageCount" @click="changePage(data.page + 1)">下一页</button></footer>
    </template>
  </section>
</template>

<style scoped>
.report-detail-panel{margin-top:22px;border:1px solid #d8e5dc;border-radius:12px;background:#fbfdfb;padding:18px;min-width:0}.detail-panel-head,.detail-panel-footer,.detail-panel-summary{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.detail-panel-head small,.detail-panel-head p,.detail-panel-footer,.detail-panel-summary{color:#687b70;font-size:var(--text-caption)}.detail-panel-head h3{margin:5px 0;font-size:var(--text-section);color:#2d5742}.detail-panel-head p{margin:0;line-height:1.7}.detail-panel-head button,.detail-panel-footer button,.detail-panel-footer select{border:1px solid #d5e0d7;border-radius:7px;background:#fff;color:#2e644d;padding:7px 10px}.detail-panel-summary{margin:14px 0;padding:10px 12px;background:#f1f7f2;border-radius:8px;justify-content:flex-start}.detail-table-wrap{overflow:auto}.detail-table{width:100%;border-collapse:collapse;font-size:var(--text-body)}.detail-table th,.detail-table td{padding:10px 9px;border-bottom:1px solid #e8eee9;text-align:left;white-space:nowrap}.detail-table th{background:#f2f6f3;color:#617369;font-size:var(--text-caption)}.detail-table td small{display:block;margin-top:3px;color:#74857a;max-width:220px;overflow:hidden;text-overflow:ellipsis}.detail-order-link{color:#286b50;text-decoration:none}.detail-panel-state{padding:28px;text-align:center;color:#728379}.detail-panel-error{padding:13px;background:#fff8f5;border:1px solid #ebcbc5;border-radius:8px;color:#a34636}.detail-panel-error button{margin-left:8px;border:0;background:transparent;color:#286b50}.detail-panel-footer{justify-content:flex-end;margin-top:14px}.detail-panel-footer label{display:flex;align-items:center;gap:7px;margin-right:auto}.detail-panel-footer select{font:inherit}@media(max-width:700px){.report-detail-panel{padding:14px}.detail-panel-head{align-items:flex-start}.detail-panel-head h3{font-size:18px}.detail-table{font-size:13px}.detail-table th,.detail-table td{padding:8px}.detail-panel-footer{justify-content:flex-start}.detail-panel-footer label{flex-basis:100%}}
</style>
