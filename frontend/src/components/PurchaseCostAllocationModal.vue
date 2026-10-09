<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { X, Plus, Layers3, Truck, Check } from 'lucide-vue-next'
import { api } from '../api'
import { confirmDialog } from '../dialogs'
const props = defineProps({ purchase: Object, orders: Array })
const emit = defineEmits(['close', 'saved'])
const form = ref(null), result = ref(null), error = ref(''), busy = ref(false), dirty = ref(false)
const goodsTotal = computed(() => props.purchase.items.reduce((total, item) => total + Number(item.amount ?? Number(item.quantity) * Number(item.unit_price)), 0))
const feeTotal = computed(() => (form.value?.expenses || []).reduce((total, fee) => total + Number(fee.amount || 0), 0))
const labels = { order: '销售订单', inventory: '库存', sample: '样品', loss: '损耗', gift: '赠品', after_sales: '售后补发', research: '研发试制', internal: '内部领用', marketing: '展会推广', other: '其他' }
const money = v => Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
onMounted(async () => {
  try { const { data } = await api.get(`/purchase-orders/${props.purchase.id}/cost-allocation/`); form.value = structuredClone(data); result.value = data }
  catch (e) { error.value = e.message }
})
const previewing = ref(false), previewError = ref('')
let previewTimer, previewSequence = 0
function payload() {
  return {
    version: form.value.version,
    allocations: form.value.allocations.map(a => ({ purchase_item: a.purchase_item, target_type: a.target_type, order: a.target_type === 'order' ? a.order : null, quantity: a.quantity, ...(a.target_type === 'other' ? { target_name: a.target_name?.trim() || '' } : {}) })),
    expenses: form.value.expenses,
  }
}
function changed() {
  dirty.value = true
  previewError.value = ''
  previewing.value = true
  clearTimeout(previewTimer)
  const sequence = ++previewSequence
  previewTimer = setTimeout(() => updatePreview(sequence), 250)
}
function errorText(e) {
  const flatten = value => typeof value === 'string' ? value : Object.values(value || {}).flatMap(flatten).join(' ')
  return flatten(e.response?.data) || e.message || '预览失败，请重试。'
}
async function updatePreview(sequence) {
  try {
    const { data } = await api.post(`/purchase-orders/${props.purchase.id}/cost-allocation-preview/`, payload())
    if (sequence === previewSequence) result.value = data
  } catch (e) {
    if (sequence === previewSequence) previewError.value = errorText(e)
  } finally {
    if (sequence === previewSequence) previewing.value = false
  }
}
onBeforeUnmount(() => { clearTimeout(previewTimer); ++previewSequence })
function remaining(item) { return Number(item.quantity) - (form.value?.allocations || []).filter(a => a.purchase_item === item.id).reduce((sum, a) => sum + Number(a.quantity || 0), 0) }
function add(item) { form.value.allocations.push({ purchase_item: item.id, target_type: 'order', order: null, quantity: Math.max(0, remaining(item)).toFixed(2) }); changed() }
function remove(row) { form.value.allocations.splice(form.value.allocations.indexOf(row), 1); changed() }
async function save() {
  if (busy.value) return
  clearTimeout(previewTimer); ++previewSequence; previewing.value = false
  busy.value = true; error.value = ''
  try {
    const { data } = await api.post(`/purchase-orders/${props.purchase.id}/cost-allocation/`, payload())
    previewError.value = ''
    form.value = structuredClone(data); result.value = data; dirty.value = false; emit('saved')
  } catch (e) { const data = e.response?.data; error.value = typeof data === 'string' ? data : data ? JSON.stringify(data) : e.message }
  finally { busy.value = false }
}
async function requestClose() {
  if (!dirty.value || await confirmDialog({ title: '放弃未保存修改', message: '当前成本分配有尚未保存的修改，确定放弃吗？', confirmText: '放弃修改', danger: true })) emit('close')
}
</script>

<template>
  <div class="modal-backdrop cost-backdrop">
    <section class="modal wide cost-modal" role="dialog" aria-modal="true" aria-labelledby="cost-title">
      <header class="cost-header"><div><span class="eyebrow">采购管理 / 成本核算</span><h3 id="cost-title">采购成本分配 <span>{{ purchase.purchase_no }}</span></h3><p>将商品成本分配给订单与库存，再统一分摊公共费用。</p></div><button class="icon-btn" aria-label="关闭成本分配" :disabled="busy" @click="requestClose"><X :size="19" /></button></header>
      <div class="cost-overview"><article><span>采购商品金额</span><strong>{{ money(goodsTotal) }} <small>{{ purchase.currency }}</small></strong></article><article><span>公共附加费用</span><strong>{{ money(feeTotal) }} <small>{{ purchase.currency }}</small></strong></article><article class="overview-total"><span>本次核算总成本</span><strong>{{ money(goodsTotal + feeTotal) }} <small>{{ purchase.currency }}</small></strong></article></div>
      <p v-if="error" role="alert" class="cost-error">{{ error }}</p>
      <p v-if="!form && !error">正在加载成本分配…</p>
      <form v-if="form" id="purchase-cost-form" @submit.prevent="save" @input="changed" @change="changed">
        <fieldset :disabled="busy || purchase.status === 'cancelled'">
          <p class="allocation-note"><Check :size="15" />{{ form.version ? `当前为人工成本分配版本 V${form.version}。` : '采购成本默认归来源订单，无来源订单时归库存。保存调整后保留分配版本。' }}</p>
          <div class="block-heading"><div><h4><Layers3 :size="17" /> 明细成本归属</h4><p>展开商品，填写每份归属的数量；未分配的余量自动归库存。</p></div><span class="count-badge">{{ purchase.items.length }} 项商品</span></div>
          <details v-for="item in purchase.items" :key="item.id" open class="cost-item">
            <summary><div class="item-title"><b>{{ item.display_name || item.sku_code }}</b><small>{{ item.sku_code }} · 采购 {{ item.trade_quantity ?? item.quantity }} {{ item.trade_snapshot?.unit }} × {{ purchase.currency }} {{ money(item.trade_unit_price ?? item.unit_price) }} · 分配基数 {{ item.quantity }} {{ item.trade_snapshot?.base_unit }}</small></div><span class="remaining-badge" :class="{ 'cost-error': remaining(item) < -0.001 }">剩余 {{ remaining(item).toFixed(2) }}</span></summary>
            <div v-for="(row, index) in form.allocations.filter(a => a.purchase_item === item.id)" :key="index" class="cost-row">
              <label>成本归属<select v-model="row.target_type" @change="row.order = null; row.target_name = ''"><option v-for="(label, key) in labels" :key="key" :value="key">{{ label }}</option></select></label>
              <label v-if="row.target_type === 'order'">销售订单<select v-model="row.order" required><option :value="null">请选择订单</option><option v-for="order in orders.filter(o => o.status !== 'cancelled')" :key="order.id" :value="order.id">{{ order.order_no }} · {{ order.customer_name }}</option></select></label>
              <label v-if="row.target_type === 'other'">自定义成本归属<input v-model="row.target_name" maxlength="100" placeholder="请输入成本归属名称" required /></label>
              <label>分配数量<input v-model="row.quantity" type="number" min="0.01" step="0.01" required /></label>
              <button type="button" class="text-btn danger" @click="remove(row)">删除</button>
            </div>
            <button type="button" class="text-btn" @click="add(item)"><Plus :size="14" /> 添加成本归属</button>
          </details>
          <div class="block-heading expense-heading"><div><h4><Truck :size="17" /> 公共附加费用</h4><p>将运费、关税或其他费用按统一规则分摊。</p></div></div>
          <div v-if="!form.expenses.length" class="fee-empty">暂无附加费用，可添加运费、关税或杂费。</div>
          <p class="muted">所有成本归属均按所选规则分担。此处记录成本，不生成付款或入库；已在此分摊的费用请勿再次作为订单费用录入。</p>
          <div v-for="(expense, index) in form.expenses" :key="index" class="cost-row">
            <label>费用名称<input v-model="expense.name" required maxlength="100" placeholder="运费 / 关税 / 杂费" /></label>
            <label>金额（{{ purchase.currency }}）<input v-model="expense.amount" type="number" min="0.01" step="0.01" required /></label>
            <label>分摊依据<select v-model="expense.method"><option value="amount">按采购金额比例</option><option value="quantity">按数量比例</option></select></label>
            <button type="button" class="text-btn danger" @click="form.expenses.splice(index, 1); changed()">删除</button>
          </div>
          <button type="button" class="text-btn" @click="form.expenses.push({ name: '运费', amount: '', method: 'amount' }); changed()"><Plus :size="14" /> 添加附加费用</button>

        </fieldset>
      </form>
      <section v-if="result" class="cost-result" aria-live="polite">
        <h4>{{ dirty ? '实时分摊预览' : result.version ? '已保存的成本分摊结果' : '当前成本归属' }} <span v-if="dirty" class="pending-badge">{{ previewing ? '计算中…' : previewError ? '预览未更新' : '未保存' }}</span></h4><p v-if="dirty" class="pending-note">{{ previewing ? '正在更新预览，以下暂为上次计算结果。' : previewError ? '请完善输入后重试，以下暂为上次有效结果：' + previewError : '已按当前输入计算；保存后才会更新订单成本。' }}</p>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>采购明细</th><th>归属</th><th>数量</th><th>商品成本</th><th>附加费用</th><th>合计</th></tr></thead><tbody><tr v-for="(row, index) in result.allocations" :key="index"><td>{{ row.display_name || purchase.items.find(item => item.id === row.purchase_item)?.display_name || row.sku_code }}</td><td>{{ row.order_no || (row.target_type === 'other' ? row.target_name : labels[row.target_type]) }}</td><td>{{ row.quantity }}</td><td>{{ money(row.base_amount) }}</td><td>{{ money(row.additional_amount) }}</td><td>{{ money(row.total_amount) }}</td></tr></tbody></table></div>
        <p>商品成本 {{ money(result.base_amount) }} ＋ 附加费用 {{ money(result.additional_amount) }} ＝ {{ purchase.currency }} {{ money(result.total_amount) }}</p>
        <p class="muted">草稿及取消采购不计入订单预估毛利；库存成本表示成本归属，不代表已到货库存。</p>
      </section>
      <footer class="cost-footer"><span>{{ dirty ? '实时预览尚未保存' : '修改数量、归属或费用，自动更新预览' }}</span><div><button class="btn btn-secondary" :disabled="busy" @click="requestClose">取消</button><button v-if="form" class="btn btn-primary" type="submit" form="purchase-cost-form" :disabled="busy || purchase.status === 'cancelled'"><Check :size="16" />{{ busy ? '保存中…' : '保存成本分配' }}</button></div></footer>
    </section>
  </div>
</template>

<style scoped>
.pending-badge{display:inline-block;margin-left:10px;padding:4px 8px;background:#fff3d8;color:#94621b;border-radius:5px;font-size:var(--text-secondary);font-weight:500}.pending-note{color:#94621b;line-height:1.7}
.cost-backdrop{z-index:105;padding:24px;background:#12362c70;backdrop-filter:blur(4px)}
.cost-modal{box-sizing:border-box;width:min(1080px,calc(100vw - 48px));max-height:92vh;overflow:auto;padding:0;border:1px solid #dce7e1;border-radius:18px;background:#fff;color:#28453a;box-shadow:0 28px 90px #052e2438;font-size:var(--text-body)}
.cost-header{position:sticky;top:0;z-index:3;display:flex;justify-content:space-between;align-items:flex-start;gap:20px;padding:23px 28px 20px;background:#fff;border-bottom:1px solid #e7eee9}.eyebrow{font-size:var(--text-caption);font-weight:700;color:#779589;letter-spacing:2px}.cost-header h3{font-size:var(--text-section);margin:8px 0;color:#153e30;letter-spacing:-.4px}.cost-header h3 span{display:inline-block;margin-left:10px;font-size:var(--text-section);font-weight:500;color:#778b80;letter-spacing:0}.cost-header p{margin:0;color:#7c8d83;font-size:var(--text-caption);line-height:1.6}
.cost-overview{display:grid;grid-template-columns:1fr 1fr 1.2fr;gap:14px;margin:22px 28px}.cost-overview article{padding:17px 19px;background:#f7faf8;border:1px solid #e4ece6;border-radius:12px}.cost-overview article>span{display:block;color:#72877a;font-size:var(--text-caption);margin-bottom:9px}.cost-overview strong{font-size:var(--text-metric);font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.6px}.cost-overview strong small{font-size:var(--text-caption);font-weight:500;color:#819487;letter-spacing:0;margin-left:5px}.cost-overview .overview-total{background:#eff7f2;border-color:#d2e5d8;color:#1b6045}
form{padding:0 28px}fieldset{border:0;padding:0;min-width:0;margin:0}.allocation-note{display:flex;align-items:center;gap:7px;color:#55776a;background:#f4f8f5;border-radius:7px;padding:10px 12px;font-size:var(--text-caption);line-height:1.6}.block-heading{display:flex;align-items:center;justify-content:space-between;gap:15px;margin:23px 0 14px}.block-heading h4{display:flex;align-items:center;gap:8px;margin:0;font-size:var(--text-section);color:#234d3b}.block-heading p{margin:6px 0 0;color:#829185;font-size:var(--text-caption)}.count-badge{padding:5px 9px;border-radius:6px;background:#f0f5f1;color:#7c8d80;font-size:var(--text-secondary);white-space:nowrap}
.cost-item{border:1px solid #dfe9e2;margin:12px 0;border-radius:11px;overflow:hidden;background:#fff}.cost-item summary{display:flex;align-items:center;gap:12px;cursor:pointer;padding:15px 18px;background:#f8faf8;list-style:none}.cost-item summary::-webkit-details-marker{display:none}.cost-item summary:before{content:'›';font-size:var(--text-page);color:#739181;transform:rotate(0);transition:transform .15s}.cost-item[open] summary:before{transform:rotate(90deg)}.cost-item[open] summary{border-bottom:1px solid #e9eee9}.item-title{flex:1;min-width:0}.item-title b{display:block;font-size:var(--text-body);font-weight:600;color:#2b5141}.item-title small{display:block;margin-top:5px;color:#84958b;font-size:var(--text-caption)}.remaining-badge{padding:6px 9px;border-radius:6px;background:#eaf3ec;color:#4c7b60;font-size:var(--text-secondary);white-space:nowrap}
.cost-row{display:flex;gap:12px;align-items:end;margin:13px 0;flex-wrap:wrap}.cost-item .cost-row{margin:16px 18px 10px}.cost-row label{display:grid;gap:7px;flex:1;min-width:145px;color:#6b8073;font-size:var(--text-caption);font-weight:600}.cost-row input,.cost-row select{box-sizing:border-box;width:100%;min-width:0;height:39px;border:1px solid #d8e3dc;border-radius:7px;padding:8px 10px;background:#fff;color:#2c493a;font:inherit;font-size:var(--text-body);font-weight:400;outline:none}.cost-row input:focus,.cost-row select:focus{border-color:#6e9d80;box-shadow:0 0 0 3px #28723e12}.text-btn{display:inline-flex;align-items:center;justify-content:center;gap:5px;border:0;background:#eff6f1;border-radius:7px;padding:9px 12px;color:#347052;font:inherit;font-size:var(--text-body);cursor:pointer}.text-btn:hover{background:#e2eee6}.cost-item>.text-btn{margin:2px 18px 15px}.text-btn.danger{background:transparent;color:#b06b64;font-size:var(--text-body);height:39px}.text-btn.danger:hover{background:#fff1ee}.expense-heading{border-top:1px solid #e7eee8;padding-top:23px;margin-top:23px}.muted{color:#8b998e;font-size:var(--text-secondary);line-height:1.8;margin:10px 0 14px}.fee-empty{border:1px dashed #dce6de;border-radius:8px;background:#fbfcfb;padding:18px;color:#95a397;font-size:var(--text-caption);text-align:center;margin-bottom:12px}
.cost-error{color:#b2473e!important}p.cost-error{margin:16px 28px;background:#fff2ef;padding:12px;border-radius:8px}.cost-result{margin:26px 28px 18px;border:1px solid #dfe9e2;border-radius:11px;overflow:hidden}.cost-result h4{font-size:var(--text-section);margin:0;padding:15px 18px;border-bottom:1px solid #e5ece6;background:#fafcfb}.cost-result .data-table th{font-size:var(--text-body);white-space:nowrap;background:#f5f8f5;padding:12px 16px}.cost-result .data-table td{font-size:var(--text-body);padding:13px 16px;font-variant-numeric:tabular-nums}.cost-result>p{padding:0 18px;font-size:var(--text-caption)}.cost-result>.muted{font-size:var(--text-secondary)}.cost-footer{position:sticky;bottom:0;z-index:3;display:flex;align-items:center;justify-content:space-between;gap:15px;padding:17px 28px;background:#fff;border-top:1px solid #e2ebe4;margin-top:24px;box-shadow:0 -6px 20px #244b3110}.cost-footer>span{font-size:var(--text-caption);color:#8b9b8e}.cost-footer>div{display:flex;gap:10px}.cost-modal button:disabled{opacity:.5;cursor:not-allowed}
@media(max-width:700px){.cost-backdrop{padding:10px}.cost-modal{width:calc(100vw - 20px);max-height:96vh}.cost-header{padding:18px}.cost-header h3{font-size:var(--text-section)}.cost-header h3 span{display:block;margin:5px 0 0}.cost-overview{margin:16px 18px;gap:7px;grid-template-columns:1fr 1fr}.cost-overview article{padding:12px}.cost-overview .overview-total{grid-column:1/-1}.cost-overview strong{font-size:var(--text-dialog)}form{padding:0 18px}.cost-result{margin:20px 18px}.cost-row{gap:8px}.cost-row label{min-width:120px}.cost-footer{padding:14px 18px;flex-wrap:wrap}.cost-footer>div{margin-left:auto}.cost-item summary{padding:12px}.item-title small{font-size:var(--text-caption)}}
</style>
