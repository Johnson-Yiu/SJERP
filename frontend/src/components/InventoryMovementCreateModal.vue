<script setup>
import TradeUnitPicker from './TradeUnitPicker.vue'
import { fromTradeLine, tradePayload, baseQuantity, tradeLabel } from '../utils/tradeUnits'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Plus, X } from 'lucide-vue-next'
import { api, listAll } from '../api'
import ComboInput from './ComboInput.vue'
import SkuPickerPanel from './SkuPickerPanel.vue'
import SegmentedDateInput from './SegmentedDateInput.vue'

const emit = defineEmits(['close', 'saved'])
const loading = ref(true), saving = ref(false), error = ref('')
const skus = ref([]), orders = ref([]), selectedSkuIds = ref([]), selectedOrderIds = ref('')
const form = reactive({ movement_date: new Date().toLocaleDateString('en-CA'), type: 'adjust_in' })
const lines = reactive({})
const inboundTypes = [
  { value: 'adjust_in', label: '盘盈入库' },
  { value: 'return_in', label: '客户退回' },
  { value: 'transfer_in', label: '调拨入库' },
  { value: 'other_in', label: '其他入库' },
]
const outboundTypes = [
  { value: 'adjust_out', label: '盘亏出库' },
  { value: 'sample_out', label: '样品出库' },
  { value: 'transfer_out', label: '调拨出库' },
  { value: 'other_out', label: '其他出库' },
]

const orderOptions = computed(() => orders.value.map(order => ({
  value: String(order.id), label: `${order.order_no} · ${order.customer_name || '未命名客户'}`,
  searchText: `${order.order_no || ''} ${order.customer_name || ''}`,
})))
const selectedSkus = computed(() => selectedSkuIds.value.map(id => skus.value.find(sku => String(sku.id) === String(id))).filter(Boolean))
const selectedOrders = computed(() => selectedOrderIds.value.split('\n').filter(Boolean).map(Number))
const movementPreview = computed(() => `保存时自动生成 · 本次 ${selectedSkus.value.length || 0} 条明细`)

watch(selectedSkuIds, () => {
  const activeIds = new Set(selectedSkus.value.map(sku => String(sku.id)))
  selectedSkus.value.forEach(sku => {
    if (!lines[sku.id]) lines[sku.id] = { quantity: '', unit_cost: '', warehouse: '默认仓', reference: '', notes: '' }
  })
  Object.keys(lines).forEach(id => { if (!activeIds.has(id)) delete lines[id] })
})

async function init() {
  try {
    const [skuResponse, orderResponse] = await Promise.all([listAll('/skus/', { params: { include_inactive: 1 } }), listAll('/orders/')])
    skus.value = skuResponse
    orders.value = orderResponse
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || requestError.message || '表单所需数据加载失败。'
  } finally { loading.value = false }
}
function lineFor(sku) { return lines[sku.id] }
async function save() {
  if (saving.value) return
  error.value = ''
  if (!selectedSkus.value.length) { error.value = '请至少选择一个 SKU。'; return }
  if (selectedSkus.value.some(sku => !Number(lineFor(sku)?.quantity) || Number(lineFor(sku).quantity) <= 0)) { error.value = '请为每个 SKU 填写大于 0 的数量。'; return }
  saving.value = true
  try {
    const items = selectedSkus.value.map(sku => tradePayload({ sku: sku.id, ...lineFor(sku), quantity: String(lineFor(sku).quantity), unit_cost: lineFor(sku).unit_cost === '' ? 0 : lineFor(sku).unit_cost }, 'unit_cost'))
    const response = await api.post('/inventory-movements/batch/', { ...form, related_orders: selectedOrders.value, items })
    emit('saved', response.data)
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || requestError.message || '保存库存流水失败。'
  } finally { saving.value = false }
}
onMounted(init)
</script>

<template>
  <Teleport to="body">
    <div class="modal-backdrop inventory-movement-backdrop" @mousedown.self="emit('close')">
      <form class="modal inventory-movement-modal" @submit.prevent="save">
        <div class="modal-head"><div><h3>新建库存流水</h3><p>可一次登记多个 SKU，每个 SKU 独立填写数量和明细。</p></div><button type="button" class="mini-btn" @click="emit('close')"><X :size="17" /></button></div>
        <div class="modal-body">
          <div v-if="error" class="inline-error">{{ error }}</div>
          <div v-if="loading" class="modal-loading">正在加载...</div>
          <template v-else>
            <div class="movement-grid">
              <div class="field"><label>流水号</label><input :value="movementPreview" class="readonly-input" readonly /></div>
              <div class="field"><label>发生日期 <em>*</em></label><SegmentedDateInput :model-value="form.movement_date" required @update:model-value="value => form.movement_date = value" /></div>
              <div class="field"><label>类型 <em>*</em></label><select v-model="form.type"><optgroup label="入库"><option v-for="item in inboundTypes" :key="item.value" :value="item.value">{{ item.label }}</option></optgroup><optgroup label="出库"><option v-for="item in outboundTypes" :key="item.value" :value="item.value">{{ item.label }}</option></optgroup></select></div>
              <div class="field"><label>关联订单 <small>可不选、可多选</small></label><ComboInput v-model="selectedOrderIds" :options="orderOptions" multiple :allow-custom="false" placeholder="搜索并选择订单" /></div>
              <div class="field full"><label>SKU <em>*</em> <small>支持 SKU、中文名称、销售型号模糊搜索、分类筛选和多选</small></label><SkuPickerPanel v-model="selectedSkuIds" :skus="skus" :height="250" /></div>
            </div>

            <section class="movement-lines">
              <div class="movement-lines-head"><div><strong>SKU 明细</strong><span>每一行将生成一条库存流水。</span></div><b>{{ selectedSkus.length }} 项</b></div>
              <p v-if="!selectedSkus.length" class="movement-empty"><Plus :size="17" /> 请先从上方选择 SKU。</p>
              <div v-else class="movement-line-wrap"><table><thead><tr><th>SKU</th><th>数量 *</th><th>单位成本</th><th>仓库</th><th>参考号</th><th>详细备注</th></tr></thead><tbody><tr v-for="sku in selectedSkus" :key="sku.id"><td><strong>{{ sku.display_name_cn || sku.product_name || sku.sku }}</strong><small>{{ sku.sales_model || sku.sku }}</small><TradeUnitPicker :line="lineFor(sku)" :sku="sku" price-field="unit_cost" /></td><td><input v-model="lineFor(sku).quantity" type="number" min="0.01" step="0.01" required /></td><td><input v-model="lineFor(sku).unit_cost" type="number" min="0" step="0.0001" placeholder="0" /></td><td><input v-model="lineFor(sku).warehouse" required /></td><td><input v-model="lineFor(sku).reference" placeholder="选填" /></td><td><input v-model="lineFor(sku).notes" placeholder="选填" /></td></tr></tbody></table></div>
            </section>
          </template>
        </div>
        <div class="modal-foot"><button type="button" class="btn btn-secondary" @click="emit('close')">取消</button><button class="btn btn-primary" :disabled="loading || saving || !selectedSkus.length">{{ saving ? '保存中...' : `保存 ${selectedSkus.length || ''} 条流水` }}</button></div>
      </form>
    </div>
  </Teleport>
</template>

<style scoped>
.inventory-movement-modal{width:min(1100px,calc(100vw - 40px))}.modal-head{align-items:flex-start}.modal-head p{margin:4px 0 0;color:#7b8b84;font-size:var(--text-body);font-weight:400}.movement-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.field small{margin-left:5px;color:#81918a;font-size:var(--text-caption);font-weight:400}.field.full{grid-column:1/-1}.readonly-input{background:#f1f5f3!important;color:#567168!important;cursor:not-allowed}.movement-lines{margin-top:20px;border:1px solid #dce7e1;border-radius:11px;overflow:hidden}.movement-lines-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 15px;background:#f5faf7}.movement-lines-head strong{display:block;color:#21483d;font-size:var(--text-body)}.movement-lines-head span{display:block;margin-top:3px;color:#809088;font-size:var(--text-caption)}.movement-lines-head b{padding:4px 8px;border-radius:99px;background:#e5f1eb;color:#29705c;font-size:var(--text-caption)}.movement-empty{display:flex;align-items:center;justify-content:center;gap:7px;margin:0;padding:28px;color:#82928b;font-size:var(--text-body)}.movement-line-wrap{overflow:auto}.movement-line-wrap table{width:100%;min-width:940px;border-collapse:collapse}.movement-line-wrap th,.movement-line-wrap td{padding:10px;border-top:1px solid #e6eeea;text-align:left;font-size:var(--text-body)}.movement-line-wrap th{border-top:0;background:#fbfdfc;color:#788981;font-size:var(--text-body)}.movement-line-wrap td:first-child{min-width:180px;color:#2b4a40}.movement-line-wrap td strong,.movement-line-wrap td small{display:block}.movement-line-wrap td small{margin-top:3px;color:#84948d;font-size:var(--text-caption)}.movement-line-wrap input{min-width:90px;padding:8px 9px}.inventory-movement-backdrop{z-index:70}@media(max-width:680px){.inventory-movement-modal{width:calc(100vw - 20px)}.movement-grid{grid-template-columns:1fr}.modal-head p{max-width:260px}.movement-lines{margin-top:16px}}
</style>
