<script setup>
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Check, X } from 'lucide-vue-next'
import { api } from '../api'

const props = defineProps({ orderId: { type: [Number, String], required: true }, plan: { type: Object, required: true } })
const emit = defineEmits(['close', 'created'])
const saving = ref(false), error = ref(''), groups = ref([])
const guard = useUnsavedChangesGuard({ data: () => groups.value })
const requestClose = () => guard.requestClose(() => emit('close'))

function reset() {
  groups.value = (props.plan.groups || []).map(group => ({
    ...group,
    exchange_rate: group.currency === 'CNY' ? '1' : '',
    expected_arrival_date: group.suggested_expected_arrival_date || '',
    items: group.items.map(id => {
      const item = props.plan.items.find(row => Number(row.order_item) === Number(id))
      return { ...item, quantity: String(item.draftable_quantity || 0), unit_price: String(item.reference_purchase_price || 0) }
    }),
  }))
}
const selectedCount = computed(() => groups.value.reduce((count, group) => count + group.items.filter(item => Number(item.quantity) > 0).length, 0))
const invalidQuantity = computed(() => groups.value.some(group => group.items.some(item => Number(item.quantity) < 0 || Number(item.quantity) > Number(item.draftable_quantity))))
const invalidExchange = computed(() => groups.value.some(group => group.currency !== 'CNY' && Number(group.exchange_rate) <= 0 && group.items.some(item => Number(item.quantity) > 0)))
const canSubmit = computed(() => selectedCount.value > 0 && !invalidQuantity.value && !invalidExchange.value)
function message(err) { return err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join('；') || err.message || '创建采购草稿失败。' }
async function submit() {
  if (!canSubmit.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const response = await api.post(`/orders/${props.orderId}/generate-purchase-drafts/`, {
      groups: groups.value.map(group => ({
        supplier: group.supplier, currency: group.currency,
        exchange_rate: group.currency === 'CNY' ? '1' : group.exchange_rate,
        expected_arrival_date: group.expected_arrival_date || null,
        items: group.items.map(item => ({ order_item: item.order_item, quantity: item.quantity || '0', unit_price: item.unit_price || '0' })),
      })),
    })
    guard.markClean()
    emit('created', response.data)
  } catch (err) { error.value = message(err) } finally { saving.value = false }
}
onMounted(() => { reset(); guard.markClean() })
</script>

<template>
  <div class="procurement-backdrop" @mousedown.self="requestClose">
    <aside class="procurement-drawer" role="dialog" aria-modal="true" aria-label="采购草稿预览">
      <header><div><span>销售订单 {{ plan.order_no }}</span><h2>采购草稿预览</h2><p>按供应商与币种分组。数量和实际单价仅作用于本次新建草稿。</p></div><button type="button" aria-label="关闭" @click="requestClose"><X :size="20" /></button></header>
      <main>
        <div v-if="!groups.length" class="empty"><AlertTriangle :size="24" /><strong>没有可自动生成的采购行</strong><p>请先为有缺口的订单行选择有效供应商。</p></div>
        <section v-for="group in groups" :key="`${group.supplier}-${group.currency}`" class="group-card">
          <h3>{{ group.supplier_name }} · {{ group.currency }}</h3>
          <table><thead><tr><th>SKU</th><th>待采购</th><th>已有草稿</th><th>本次采购</th><th>实际单价</th></tr></thead><tbody><tr v-for="item in group.items" :key="item.order_item"><td><strong>{{ item.sku_code }}</strong><small>{{ item.supplier_sku_code || item.supplier_model || '—' }}</small><p v-for="warning in item.warnings" :key="warning" class="warning">⚠ {{ warning }}</p></td><td>{{ item.to_procure_quantity }}</td><td>{{ item.draft_procurement_quantity }}</td><td><input v-model="item.quantity" type="number" min="0" :max="item.draftable_quantity" step="0.01" /><small>最多 {{ item.draftable_quantity }}</small></td><td><input v-model="item.unit_price" type="number" min="0" step="0.0001" /></td></tr></tbody></table>
          <div class="group-fields"><label>汇率<input v-model="group.exchange_rate" type="number" min="0" step="0.000001" :readonly="group.currency === 'CNY'" /><small v-if="group.currency === 'CNY'">CNY 固定为 1</small><small v-else>非 CNY 必填且必须大于 0</small></label><label>预计到货<input v-model="group.expected_arrival_date" type="date" /></label></div>
        </section>
        <div v-if="(plan.items || []).filter(item => !item.can_generate && Number(item.draftable_quantity) > 0).length" class="blocked"><AlertTriangle :size="18" /><div><strong>以下行暂不能生成</strong><p v-for="item in plan.items.filter(row => !row.can_generate && Number(row.draftable_quantity) > 0)" :key="item.order_item">{{ item.sku_code }}：{{ item.blocking_reason }}</p></div></div>
        <p v-if="invalidQuantity" class="error">本次采购数量必须介于 0 与当前可生成数量之间。</p><p v-if="invalidExchange" class="error">非 CNY 采购草稿必须填写大于 0 的汇率。</p><p v-if="error" class="error">{{ error }}</p>
      </main>
      <footer><button type="button" class="secondary" @click="requestClose">取消</button><button type="button" class="primary" :disabled="saving || !canSubmit" @click="submit"><Check :size="16" />{{ saving ? '创建中…' : `创建 ${selectedCount ? '采购草稿' : ''}` }}</button></footer>
    </aside>
  </div>
</template>

<style scoped>
.procurement-backdrop{position:fixed;inset:0;z-index:180;display:flex;justify-content:flex-end;background:#0a251e70;backdrop-filter:blur(2px)}.procurement-drawer{width:min(860px,100vw);height:100%;display:flex;flex-direction:column;background:#f7faf8;box-shadow:-18px 0 55px #06221945}.procurement-drawer header{display:flex;justify-content:space-between;gap:15px;padding:23px 25px;background:#103f36;color:#fff}.procurement-drawer header span,.procurement-drawer header p{color:#a6c8bd;font-size:var(--text-caption)}.procurement-drawer h2{margin:7px 0;font-size:var(--text-section)}.procurement-drawer header p{margin:0}.procurement-drawer header button{display:grid;place-items:center;width:34px;height:34px;border:1px solid #ffffff3d;border-radius:8px;background:#ffffff12;color:#fff}.procurement-drawer main{flex:1;overflow:auto;padding:19px 22px}.group-card{margin-bottom:16px;padding:15px;border:1px solid #dce8e2;border-radius:10px;background:#fff}.group-card h3{margin:0 0 12px;color:#214c40;font-size:var(--text-section)}table{width:100%;border-collapse:collapse;font-size:var(--text-body)}th,td{padding:9px;border-top:1px solid #e7efeb;text-align:left;vertical-align:top}th{color:#71867c;font-size:var(--text-caption)}td strong,td small{display:block}td small{margin-top:4px;color:#7c9086;font-size:var(--text-caption)}td input,.group-fields input{box-sizing:border-box;width:100%;min-width:82px;padding:7px;border:1px solid #d4e2db;border-radius:6px;font:inherit}.warning{margin:5px 0 0;color:#91611a;font-size:var(--text-caption)}.group-fields{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}.group-fields label{display:grid;gap:6px;color:#587066;font-size:var(--text-caption)}.group-fields small{color:#7d8d86}.blocked,.error,.empty{display:flex;gap:9px;padding:12px;border-radius:8px}.blocked{margin-top:12px;background:#fff6e5;color:#80591a}.blocked p{margin:5px 0 0;font-size:var(--text-caption)}.error{margin:10px 0 0;background:#fff0ee;color:#af4033}.empty{display:grid;justify-items:center;padding:42px;color:#798e84;text-align:center}.empty p{margin:0;font-size:var(--text-caption)}footer{display:flex;justify-content:flex-end;gap:9px;padding:14px 22px;border-top:1px solid #dfe9e4;background:#fff}.secondary,.primary{display:inline-flex;align-items:center;gap:6px;padding:10px 15px;border-radius:7px;font:inherit;font-weight:700}.secondary{border:1px solid #d2e0d9;background:#fff;color:#315b4c}.primary{border:1px solid #10604d;background:#10604d;color:#fff}.primary:disabled{opacity:.5;cursor:not-allowed}@media(max-width:680px){.procurement-drawer main{padding:14px}.group-fields{grid-template-columns:1fr}table{min-width:620px}.group-card{overflow:auto}}
</style>
