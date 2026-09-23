<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, listAll } from '../api'
import SkuPickerPanel from '../components/SkuPickerPanel.vue'
const route = useRoute()
const skus = ref([]), suppliers = ref([]), units = ref([]), selected = ref(route.query.sku || ''), error = ref(''), loading = ref(false), saving = ref(false)
const form = reactive({ name: '', unit: '卷', factor: '', supplier: '', allow_fraction: false, is_default: false, notes: '' })
const sku = computed(() => skus.value.find(s => s.id === Number(selected.value)))
const rows = computed(() => units.value.filter(u => !selected.value || u.sku === Number(selected.value)))
const selectedSkuIds = computed({
  get: () => selected.value ? [String(selected.value)] : [],
  set: (ids) => { selected.value = ids?.length ? String(ids[ids.length - 1]) : '' },
})
function message(e) { return e.response?.data ? JSON.stringify(e.response.data) : e.message }
async function load() {
  loading.value = true
  try { [skus.value, suppliers.value, units.value] = await Promise.all([listAll('/skus/', { params: { include_inactive: 1 } }), listAll('/suppliers/'), listAll('/sku-trade-units/')]) }
  catch (e) { error.value = message(e) } finally { loading.value = false }
}
async function create() {
  saving.value = true; error.value = ''
  try {
    await api.post('/sku-trade-units/', { ...form, sku: Number(selected.value), supplier: form.supplier ? Number(form.supplier) : null })
    Object.assign(form, { name: '', factor: '', notes: '', is_default: false }); await load()
  } catch (e) { error.value = message(e) } finally { saving.value = false }
}
async function change(row, patch) {
  saving.value = true; error.value = ''
  try { await api.patch(`/sku-trade-units/${row.id}/`, patch); await load() }
  catch (e) { error.value = message(e) } finally { saving.value = false }
}
onMounted(load)
</script>
<template>
  <div class="units-page">
    <header><h2>SKU 交易单位</h2><p>库存统一按基础单位记账；报价、采购和出入库可选择卷、箱等交易规格。</p></header>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <section class="panel unit-filters">
      <SkuPickerPanel v-model="selectedSkuIds" v-model:active-id="selected" :skus="skus" title="选择需要配置交易单位的 SKU" search-placeholder="搜索 SKU、型号或描述" :height="286" :show-price="false">
        <template #preview="{ sku: activeSku }">
          <p class="picker-hint">基础单位：{{ activeSku.unit || 'pcs' }}。选择后可在右侧新增卷、箱等交易规格。</p>
        </template>
      </SkuPickerPanel>
    </section>
    <div class="units-layout">
      <section class="panel"><h3>包装规格 <small>{{ rows.length }} 项</small></h3><p v-if="loading">正在加载…</p><p v-else-if="!rows.length">暂无规格。选择 SKU 后添加，例如 10 米/卷、20 米/卷。</p><div class="table-wrap"><table v-if="rows.length" class="data-table"><thead><tr><th>SKU / 规格</th><th>换算关系</th><th>供应商</th><th>数量规则</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td>{{ row.name }}<small>{{ row.sku_code }}</small></td><td>1 {{ row.unit }} = {{ row.factor }} {{ row.base_unit }}</td><td>{{ row.supplier_name || '通用' }}</td><td>{{ row.allow_fraction ? '允许小数' : '整包装' }}</td><td>{{ row.active ? '启用' : '停用' }}{{ row.is_default ? ' · 默认' : '' }}</td><td><button :disabled="saving" class="btn btn-secondary" @click="change(row, { active: !row.active })">{{ row.active ? '停用' : '启用' }}</button><button v-if="row.active && row.is_default" :disabled="saving" class="btn btn-secondary" @click="change(row, { is_default: false })">取消默认</button><button v-if="row.active && !row.is_default" :disabled="saving" class="btn btn-secondary" @click="change(row, { is_default: true })">设为默认</button></td></tr></tbody></table></div></section>
      <form class="panel unit-form" @submit.prevent="create"><h3>新增规格</h3><p>{{ sku ? `${sku.display_name_cn || sku.sku} · 基础单位：${sku.unit}` : '请先选择一个 SKU' }}</p><label>规格名称<input v-model.trim="form.name" placeholder="例如：10 米卷" maxlength="120" required /></label><div class="unit-pair"><label>交易单位<input v-model.trim="form.unit" maxlength="30" required /></label><label>每单位含 {{ sku?.unit || '基础数量' }}<input v-model="form.factor" type="number" min="0.01" step="0.01" required /></label></div><label>供应商（可选）<select v-model="form.supplier"><option value="">通用规格</option><option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option></select></label><label class="check"><input v-model="form.allow_fraction" type="checkbox" />允许非整包装数量</label><label class="check"><input v-model="form.is_default" type="checkbox" />设为默认规格</label><label>备注<textarea v-model="form.notes" /></label><p class="hint">规格保存后，名称、单位及换算关系固定。变更卷长时停用旧规格并新增，历史单据保留原始快照。装箱模板中的容量和单重仍按基础单位填写。</p><button class="btn btn-primary" :disabled="!sku || saving">{{ saving ? '保存中…' : '添加规格' }}</button></form>
    </div>
  </div>
</template>
<style scoped>
.units-page{display:grid;gap:18px}.units-page h2,.units-page h3{margin:0 0 10px}.units-page p{color:#6b8178;line-height:1.7}.unit-filters{padding:18px}.unit-filters :deep(.sku-selection-panel){margin:0}.picker-hint{margin:0;padding:10px 12px;background:#edf6f1;border-radius:7px;font-size:13px}.units-layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(300px,1fr);gap:18px}.units-layout>.panel{padding:20px;min-width:0}.unit-form{display:grid;gap:14px;align-content:start}label{display:grid;gap:7px;color:#365b4d;font-size:14px}input,select,textarea{padding:9px;border:1px solid #d4e0d9;border-radius:7px;min-width:0;background:white;font:inherit}.unit-pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.check{display:flex;align-items:center}.hint{font-size:13px;background:#eff6f2;padding:12px;border-radius:8px}.error{color:#a33131!important}td small{display:block;color:#7d9087}td button{margin:3px}.table-wrap{overflow:auto}@media(max-width:1000px){.units-layout{grid-template-columns:1fr}}
</style>
