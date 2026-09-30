<script setup>
import { ref, watch } from 'vue'
import { api, listAll } from '../api'
import ComboInput from './ComboInput.vue'
const props = defineProps({ productId: [Number, String] })
const rules = ref([]), skus = ref([]), definitions = ref([]), draft = ref(null), filters = ref({}), error = ref(''), busy = ref(false)
const key = d => `${d.category_id}:${d.key}`
async function load() {
  busy.value = true; error.value = ''
  try {
    const [r, s, p] = await Promise.all([listAll('/sales-rules/', { params: { product: props.productId } }), listAll('/skus/', { params: { product: props.productId, include_inactive: '1' } }), api.get(`/products/${props.productId}/sku-plan/`)])
    rules.value = r; skus.value = s; definitions.value = p.data.definitions
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
watch(() => props.productId, () => { draft.value = null; load() }, { immediate: true })
function edit(row) {
  draft.value = row ? { ...row } : { name: '', sku: null, minimum_quantity: 100, unit: 'pcs', effective_from: '', effective_until: '', is_active: true, notes: '' }
  filters.value = Object.fromEntries(Object.entries(row?.filters || {}).map(([k,v]) => [k, v.join('\n')]))
}
const options = d => [...new Set(skus.value.map(s => s.parameter_values?.[key(d)] ?? s.parameter_values?.[d.key]).filter(Boolean))].map(value => ({ value, label: value }))
function selectSku() { if (draft.value.sku) draft.value.unit = skus.value.find(s => s.id === draft.value.sku)?.unit || 'pcs' }
async function save() {
  busy.value = true; error.value = ''
  try {
    const data = { ...draft.value, product: Number(props.productId), rule_type: 'moq', effective_from: draft.value.effective_from || null, effective_until: draft.value.effective_until || null, filters: draft.value.sku ? {} : Object.fromEntries(Object.entries(filters.value).map(([k,v]) => [k, v.split('\n').map(x => x.trim()).filter(Boolean)]).filter(([,v]) => v.length)) }
    if (data.id) await api.patch(`/sales-rules/${data.id}/`, data)
    else await api.post('/sales-rules/', data)
    draft.value = null; await load()
  } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function toggle(row) {
  busy.value = true; error.value = ''
  try { await api.patch(`/sales-rules/${row.id}/`, { is_active: !row.is_active }); await load() }
  catch (e) { error.value = e.message } finally { busy.value = false }
}
const scope = row => row.sku ? (skus.value.find(s => s.id === row.sku)?.sales_model || `SKU #${row.sku}`) : Object.entries(row.filters).map(([k,v]) => `${definitions.value.find(d => key(d) === k)?.name || k} = ${v.join(' / ')}`).join('；') || '本产品全部 SKU'
</script>
<template>
<section class="sales-rules">
  <header><div><h3>销售规则</h3><p>设置 SKU 如何报价。按报价日期生效，每一报价行均须满足最低数量；多条规则命中时取最严格要求。</p><p>MOQ 按 SKU 基础单位判断；使用卷/箱报价时，系统会先换算为基础数量。</p></div><button class="primary" :disabled="busy" @click="edit()">＋ 新增规则</button></header>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <form v-if="draft" @submit.prevent="save">
    <h4>{{ draft.id ? '编辑' : '新增' }}最低报价数量规则</h4>
    <fieldset :disabled="busy"><div class="fields">
      <label>规则名称<input v-model.trim="draft.name" required maxlength="120" placeholder="例如：白色电源最低 100 pcs" /></label>
      <label>适用范围<select v-model="draft.sku" @change="selectSku"><option :value="null">按参数条件（留空则全部 SKU）</option><option v-for="s in skus" :key="s.id" :value="s.id">{{ s.sales_model || s.sku }} · {{ s.display_name_cn }}</option></select></label>
    </div>
    <div v-if="!draft.sku" class="conditions"><p>同一参数多值任选其一，不同参数须同时满足。输入后按回车确认。</p><div class="fields"><label v-for="d in definitions" :key="key(d)">{{ d.name }}<ComboInput v-model="filters[key(d)]" :options="options(d)" multiple placeholder="不限" /></label></div></div>
    <div class="fields"><label>最低报价数量<input v-model="draft.minimum_quantity" type="number" min="0.01" step="0.01" required /></label><label>单位<input v-model.trim="draft.unit" required maxlength="30" /></label><label>生效日期（不填则不限）<input v-model="draft.effective_from" type="date" /></label><label>截止日期（含当天）<input v-model="draft.effective_until" type="date" :min="draft.effective_from" /></label></div>
    <label class="notes">备注<textarea v-model="draft.notes" rows="2" /></label><footer><label><input v-model="draft.is_active" type="checkbox" /> 启用</label><button type="button" @click="draft = null">取消</button><button class="primary">保存规则</button></footer></fieldset>
  </form>
  <article v-for="row in rules" :key="row.id"><div><h4>{{ row.name }} <small>{{ row.is_active ? '启用' : '停用' }}</small></h4><p>{{ scope(row) }}</p><strong>最低报价数量：{{ Number(row.minimum_quantity) }} {{ row.unit }}</strong><p>{{ row.effective_from || '不限开始日期' }} — {{ row.effective_until || '不限截止日期' }}</p><p v-if="row.notes">{{ row.notes }}</p></div><div class="actions"><button :disabled="busy" @click="edit(row)">编辑</button><button :disabled="busy" @click="toggle(row)">{{ row.is_active ? '停用' : '启用' }}</button></div></article>
  <p v-if="!rules.length && !busy" class="empty">暂无销售规则，可为白色、特殊包装等 SKU 设置最低报价数量。</p>
</section>
</template>
<style scoped>
.sales-rules{background:white;border:1px solid #dce7e1;border-radius:12px;padding:22px;min-width:0}.sales-rules header,.sales-rules footer,.sales-rules article{display:flex;align-items:center;justify-content:space-between;gap:16px}.sales-rules h3,.sales-rules h4{margin:0 0 10px}.sales-rules p{font-size:13px;color:#6b8277;line-height:1.6}.sales-rules button{padding:9px 14px;border:1px solid #cfdfd7;border-radius:7px;background:white;color:#28614b;white-space:nowrap;cursor:pointer}.sales-rules button.primary{background:#086550;color:white}.sales-rules button:disabled{opacity:.5}.sales-rules form{background:#f6faf8;border:1px solid #d9e6df;padding:20px;border-radius:9px;margin:20px 0}.sales-rules fieldset{border:0;padding:0;min-width:0}.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.fields label,.notes{display:grid;gap:7px;font-size:13px;min-width:0}.fields input,.fields select,textarea{width:100%;min-width:0;box-sizing:border-box;border:1px solid #d0dfd7;border-radius:6px;padding:10px;background:white;color:#244c3b}.conditions{margin:16px 0;padding:14px;background:white;border-radius:8px}.notes{margin:16px 0}.sales-rules footer>label{margin-right:auto}.sales-rules article{padding:20px 0;border-bottom:1px solid #e4ece7}.sales-rules small{margin-left:10px;color:#73867c;font-weight:normal}.actions{display:flex;gap:8px}.sales-rules .error{color:#b42318;background:#fff0ec;padding:12px}.empty{text-align:center;padding:30px}@media(max-width:650px){.fields{grid-template-columns:1fr}.sales-rules header,.sales-rules article{align-items:start;flex-direction:column}}
</style>
