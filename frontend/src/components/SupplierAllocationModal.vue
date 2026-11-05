<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Check, CircleHelp, Truck, X } from 'lucide-vue-next'


const props = defineProps({
  orderId: { type: [Number, String], required: true },
  orderItem: { type: Object, required: true },
})
const emit = defineEmits(['close', 'saved'])
const data = ref(null), loading = ref(true), saving = ref(false), error = ref('')
const selectedSupplierSku = ref(null), scope = ref('order_only'), note = ref('')
const sourceLabels = { rule_match: '规则匹配', historical_purchase: '客户历史采购', manual: '人工补充', supplier_sku: '供货档案', customer_preference: '客户优先来源' }
const selectedCandidate = computed(() => data.value?.candidates?.find(row => row.supplier_skus?.some(source => Number(source.id) === Number(selectedSupplierSku.value))))
const currentAllocation = computed(() => data.value?.allocation)
const canSetCustomerPreference = computed(() => data.value?.can_set_customer_preference !== false)
const supplierChangeWarning = computed(() => {
  const currentSupplier = Number(currentAllocation.value?.supplier)
  const nextSupplier = Number(selectedCandidate.value?.supplier)
  return currentSupplier && nextSupplier && currentSupplier !== nextSupplier
})
function sourceForCandidate(candidate) {
  const sourceId = Number(selectedCandidate.value?.supplier) === Number(candidate.supplier)
    ? Number(selectedSupplierSku.value)
    : Number(candidate.recommended_supplier_sku_id)
  return candidate.supplier_skus.find(source => Number(source.id) === sourceId) || null
}
function money(value) { return Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) }
function choose(row) { if (!row.can_allocate) return; selectedSupplierSku.value = row.recommended_supplier_sku_id }
function message(err) { return err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join('；') || err.message || '操作失败。' }
async function load() {
  loading.value = true; error.value = ''
  try {
    const response = await api.get(`/orders/${props.orderId}/items/${props.orderItem.id}/supplier-allocation/`)
    data.value = response.data
    selectedSupplierSku.value = response.data.allocation?.supplier_sku || response.data.recommendation?.supplier_sku || response.data.candidates?.find(row => row.can_allocate)?.recommended_supplier_sku_id || null
    scope.value = response.data.allocation?.scope === 'recommended' ? 'customer_preferred' : (response.data.allocation?.scope || 'order_only')
    note.value = response.data.allocation?.note || ''
  } catch (err) { error.value = message(err) } finally { loading.value = false }
}
async function save() {
  if (!selectedSupplierSku.value) { error.value = '请选择一个已有 Supplier SKU 的供应商。'; return }
  saving.value = true; error.value = ''
  try {
    await api.post(`/orders/${props.orderId}/items/${props.orderItem.id}/supplier-allocation/`, { supplier_sku: selectedSupplierSku.value, scope: scope.value, note: note.value })
    emit('saved')
  } catch (err) { error.value = message(err) } finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <div class="supplier-allocation-backdrop" @mousedown.self="emit('close')">
    <aside class="supplier-allocation-drawer" role="dialog" aria-modal="true" aria-label="选择当前采购来源">
      <header class="allocation-header"><div><span>销售订单 · 采购分配</span><h2>选择当前采购来源</h2></div><button type="button" class="icon-button" aria-label="关闭" @click="emit('close')"><X :size="20" /></button></header>
      <main class="allocation-body">
        <div v-if="loading" class="allocation-state">正在加载候选供应商…</div>
        <div v-else-if="error && !data" class="allocation-state error-state"><AlertTriangle :size="20" /><p>{{ error }}</p><button type="button" @click="load">重试</button></div>
        <template v-else-if="data">
          <section class="order-line-summary"><div><small>订单行信息</small><strong>{{ data.order_item.sku_code }}</strong><p>{{ data.order_item.display_name }}</p><p>{{ data.order_item.description || '—' }}</p></div><dl><div><dt>数量</dt><dd>{{ data.order_item.quantity }} {{ data.order_item.unit }}</dd></div><div><dt>当前采购来源</dt><dd>{{ currentAllocation?.supplier_name || '未选择' }}</dd></div></dl></section>
          <section class="allocation-section"><div class="section-title"><div><h3>候选采购来源（{{ data.candidates.length }}）</h3><p>优先参考该客户此 SKU 的历史采购；SKU 全局首选仅作弱推荐。</p></div><CircleHelp :size="17" /></div>
            <p v-if="data.recommendation_warning" class="recommendation-warning" role="alert"><AlertTriangle :size="16" />{{ data.recommendation_warning }}</p>
            <div v-if="!data.candidates.length" class="empty-candidates"><Truck :size="25" /><strong>当前没有候选供应商</strong><p>请先在产品管理的供应商页维护能力规则或人工加入候选。</p></div>
            <label v-for="candidate in data.candidates" :key="candidate.supplier" class="candidate-card" :class="{ selected: Number(selectedCandidate?.supplier) === Number(candidate.supplier), disabled: !candidate.can_allocate }" @click="choose(candidate)">
              <input type="radio" name="supplier" :value="candidate.recommended_supplier_sku_id" :checked="Number(selectedCandidate?.supplier) === Number(candidate.supplier)" :disabled="!candidate.can_allocate" @change="choose(candidate)" />
              <div class="candidate-main"><div class="candidate-title"><strong>{{ candidate.supplier_name }}</strong><span v-if="candidate.can_allocate && candidate.recommendation_rank === 0" class="recommended-tag">本客户推荐</span><span v-else-if="!candidate.can_allocate" class="pending-tag">待创建 Supplier SKU</span></div><div class="candidate-metrics"><span>单价 <b>{{ sourceForCandidate(candidate) ? `${money(sourceForCandidate(candidate).purchase_price)} ${sourceForCandidate(candidate).currency}` : '—' }}</b></span><span>交期 <b>{{ sourceForCandidate(candidate)?.lead_time_days ?? '—' }} 天</b></span><span>MOQ <b>{{ sourceForCandidate(candidate)?.moq ?? '—' }}</b></span><span>最近采购 <b>{{ candidate.last_purchase?.date || '暂无' }}</b></span></div><p class="candidate-source">{{ candidate.recommendation_reason || candidate.sources.join(' / ') }}<span v-if="candidate.source_types?.length"> · {{ candidate.source_types.map(source => sourceLabels[source] || source).join('、') }}</span></p><select v-if="candidate.supplier_skus.length > 1" :value="selectedSupplierSku" :disabled="!candidate.can_allocate" @click.stop @change="selectedSupplierSku = Number($event.target.value)"><option v-for="source in candidate.supplier_skus" :key="source.id" :value="source.id">{{ source.model || source.code }} · {{ source.purchase_price }} {{ source.currency }}</option></select></div>
            </label>
          </section>
          <section class="allocation-section"><div class="section-title"><div><h3>本次分配说明</h3><p>此选择用于后续采购草稿；已经生成的采购单保留原采购来源，不会被改写。</p></div></div><p v-if="supplierChangeWarning" class="supplier-change-warning" role="status"><AlertTriangle :size="16" />更换供应商前请核对包装、LOGO、认证及供货特点可能存在的差异。</p><label class="scope-option"><input v-model="scope" type="radio" value="order_only" /> <span><strong>仅本次采购使用</strong><small>只为当前订单行记录供应商，不改变该客户或 SKU 的长期优先来源。</small></span></label><label class="scope-option" :class="{ disabled: !canSetCustomerPreference }"><input v-model="scope" type="radio" value="customer_preferred" :disabled="!canSetCustomerPreference" /> <span><strong>设为该客户此 SKU 今后优先来源</strong><small>只更新当前客户与当前 SKU 的优先来源，不修改全局 SKU 首选，也不影响其他客户。</small><small v-if="!canSetCustomerPreference" class="scope-permission-note">需要供应商修改权限。</small></span></label><textarea v-model="note" rows="3" placeholder="可填写价格、交期或本次采购的特殊说明" /></section>
          <div v-if="error" class="allocation-error" role="alert"><AlertTriangle :size="17" />{{ error }}</div>
        </template>
      </main>
      <footer class="allocation-footer"><button type="button" class="secondary-button" @click="emit('close')">取消</button><button type="button" class="primary-button" :disabled="saving || loading || !selectedSupplierSku" @click="save"><Check :size="16" />{{ saving ? '保存中…' : '确认选择' }}</button></footer>
    </aside>
  </div>
</template>

<style scoped>
.supplier-allocation-backdrop{position:fixed;inset:0;z-index:180;display:flex;justify-content:flex-end;background:#0a251e70;backdrop-filter:blur(2px)}.supplier-allocation-drawer{width:min(620px,100vw);height:100%;display:flex;flex-direction:column;background:#f7faf8;box-shadow:-18px 0 55px #06221945}.allocation-header{display:flex;justify-content:space-between;gap:15px;padding:23px 25px;background:#103f36;color:#fff}.allocation-header span{color:#a6c8bd;font-size:var(--text-caption)}.allocation-header h2{margin:7px 0 0;font-size:var(--text-section)}.icon-button{display:grid;place-items:center;width:34px;height:34px;border:1px solid #ffffff3d;border-radius:8px;background:#ffffff12;color:#fff}.allocation-body{flex:1;overflow:auto;padding:19px 22px}.allocation-state{display:grid;place-items:center;gap:10px;min-height:220px;color:#6d8178}.error-state{color:#ad4b4b;text-align:center}.error-state p{margin:0}.error-state button{padding:7px 12px;border:1px solid #c9ded4;border-radius:7px;background:#fff;color:#266953}.order-line-summary{display:flex;justify-content:space-between;gap:16px;padding:15px;border:1px solid #dceae3;border-radius:10px;background:#eef7f2}.order-line-summary small,.order-line-summary p{display:block;margin:4px 0;color:#6e837a;font-size:var(--text-caption)}.order-line-summary strong{display:block;margin-top:5px;color:#173f35}.order-line-summary dl{display:grid;grid-template-columns:repeat(2,auto);gap:12px;margin:0}.order-line-summary dt{color:#7b8d85;font-size:var(--text-caption)}.order-line-summary dd{margin:4px 0 0;color:#224e40;font-weight:700;white-space:nowrap}.allocation-section{margin-top:18px}.section-title{display:flex;justify-content:space-between;gap:12px;align-items:start;margin-bottom:10px}.section-title h3{margin:0;color:#214c40;font-size:var(--text-section)}.section-title p{margin:5px 0 0;color:#789087;font-size:var(--text-caption)}.section-title>svg{color:#7d968b}.candidate-card{display:flex;gap:12px;margin-top:9px;padding:13px 14px;border:1px solid #dce8e2;border-radius:10px;background:#fff;cursor:pointer}.candidate-card.selected{border-color:#1d9674;box-shadow:0 0 0 2px #c8ecdd;background:#fbfffd}.candidate-card.disabled{cursor:not-allowed;background:#f8faf8;opacity:.78}.candidate-card>input{width:17px;height:17px;flex:0 0 auto;margin-top:4px;accent-color:#11785e}.candidate-main{min-width:0;flex:1}.candidate-title{display:flex;align-items:center;gap:8px}.candidate-title strong{color:#234c40;font-size:var(--text-body)}.recommended-tag,.pending-tag{padding:3px 7px;border-radius:5px;font-size:var(--text-caption)}.recommended-tag{background:#d4f3e4;color:#197455}.pending-tag{background:#fff0d8;color:#a86c2b}.candidate-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px;color:#768a81;font-size:var(--text-caption)}.candidate-metrics b{display:block;margin-top:4px;color:#315d4c;font-weight:700}.candidate-source{margin:9px 0 0;color:#809189;font-size:var(--text-caption)}.candidate-main select{width:100%;margin-top:9px;padding:7px;border:1px solid #d7e4de;border-radius:6px;background:#fff;color:#3b5b4e}.scope-option{display:flex;gap:10px;padding:11px 0;border-bottom:1px solid #e7efeb;cursor:pointer}.scope-option input{margin-top:3px;accent-color:#11785e}.scope-option span{display:grid;gap:4px}.scope-option strong{color:#2b5144}.scope-option small{color:#7a8d84;font-size:var(--text-caption)}.allocation-section textarea{width:100%;box-sizing:border-box;margin-top:12px;padding:10px;border:1px solid #d5e3dc;border-radius:7px;resize:vertical;font:inherit}.empty-candidates{display:grid;justify-items:center;gap:7px;padding:29px 12px;color:#82938b;text-align:center}.empty-candidates strong{color:#506a5e}.empty-candidates p{margin:0;font-size:var(--text-caption)}.allocation-error{display:flex;align-items:center;gap:7px;margin-top:13px;padding:10px;border-radius:7px;background:#fff0ee;color:#b24437;font-size:var(--text-body)}.allocation-footer{display:flex;justify-content:flex-end;gap:9px;padding:14px 22px;border-top:1px solid #dfe9e4;background:#fff}.secondary-button,.primary-button{display:inline-flex;align-items:center;gap:6px;padding:10px 15px;border-radius:7px;font:inherit;font-weight:700}.secondary-button{border:1px solid #d2e0d9;background:#fff;color:#315b4c}.primary-button{border:1px solid #10604d;background:#10604d;color:#fff}.primary-button:disabled{opacity:.5;cursor:not-allowed}@media(max-width:600px){.allocation-header{padding:18px}.allocation-body{padding:14px}.order-line-summary{display:block}.order-line-summary dl{margin-top:12px}.candidate-metrics{grid-template-columns:repeat(2,1fr)}}
.recommendation-warning,.supplier-change-warning{display:flex;align-items:flex-start;gap:7px;margin:10px 0;padding:10px;border:1px solid #f0d59c;border-radius:7px;background:#fff8e9;color:#8b621d;font-size:var(--text-caption);line-height:1.6}
.scope-option.disabled{cursor:not-allowed;opacity:.68}.scope-permission-note{color:#9b6d27!important}
</style>
