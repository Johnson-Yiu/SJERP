<script setup>
import { useWorkspaceTeleportDisabled } from "../composables/useWorkspaceTeleport"
const workspaceTeleportDisabled = useWorkspaceTeleportDisabled()
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { computed, onMounted, ref } from 'vue'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import { apiErrorMessage } from '../utils/apiErrors'

const props = defineProps({ productId: [Number, String], skuIds: Array, parentGuardsRoute: Boolean })
const emit = defineEmits(['close', 'saved'])
const suppliers = ref([]), selected = ref([]), settings = ref({}), search = ref(''), loading = ref(true), busy = ref(false), error = ref('')
const guard=useUnsavedChangesGuard({data:()=>({selected:selected.value,settings:settings.value}),enabled:()=>!loading.value,routeGuard:!props.parentGuardsRoute,busy:()=>busy.value})
const requestClose=()=>guard.requestClose(()=>emit('close'))
const showAll = ref(false)
const visible = computed(() => suppliers.value.filter(s => (showAll.value || s.category_match) && `${s.name} ${s.code} ${(s.supply_category_names || []).join(' ')}`.toLowerCase().includes(search.value.trim().toLowerCase())))
const selectedSuppliers = computed(() => suppliers.value.filter(s => selected.value.includes(s.id)))
const allVisibleSelected = computed(() => visible.value.length > 0 && visible.value.every(s => selected.value.includes(s.id)))
function selectVisible(checked) {
  const ids = visible.value.map(s => s.id)
  selected.value = checked ? [...new Set([...selected.value, ...ids])] : selected.value.filter(id => !ids.includes(id))
}
async function load() {
  loading.value=true;error.value=''
  try {
    suppliers.value = (await api.get(`/products/${props.productId}/supplier-candidate-pool/`, { params: { eligible: '1', all: '1' } })).data
    settings.value = Object.fromEntries(suppliers.value.map(s => [s.id, { supplier: s.id, priority: '中', quality: 'B', stability: '中', delivery: '标准', notes: '' }]))
    guard.markClean()
  } catch (e) { error.value = apiErrorMessage(e) } finally { loading.value = false }
}
onMounted(load)
async function save() {
  if (busy.value || !selected.value.length) return
  busy.value = true; error.value = ''
  try {
    await api.post(`/products/${props.productId}/supplier-candidate-pool/`, { sku_ids: props.skuIds, suppliers: selected.value.map(id => settings.value[id]) })
    guard.markClean(); emit('saved')
  } catch (e) { error.value = e.response?.data?.detail || Object.values(e.response?.data || {}).flat().join('；') || e.message } finally { busy.value = false }
}
</script>
<template>
<Teleport to="body" :disabled="workspaceTeleportDisabled"><div class="binding-backdrop"><section class="binding-drawer" role="dialog" aria-modal="true" aria-label="批量绑定供应商">
<header><div><h3>批量绑定供应商</h3><p>为 {{ skuIds.length }} 个 SKU 添加候选供应商。采购时仍需选择实际供应来源。</p></div><button type="button" :disabled="busy" @click="requestClose">关闭</button></header>
<div class="binding-body" :inert="busy"><p class="hint">优先展示分类匹配的供应商，也可打开开关从全部供应商中选择。切换筛选不会清除已选供应商。</p>
<div class="supplier-filter-bar"><input v-model="search" class="binding-search" placeholder="搜索名称、代码或可供分类" aria-label="搜索供应商" /><label class="all-suppliers-toggle"><input v-model="showAll" type="checkbox" role="switch" />显示全部供应商</label></div>
<p v-if="loading">加载供应商…</p><p v-if="error" role="alert" class="error">{{ error }} <button v-if="!suppliers.length" type="button" @click="load">重新加载</button></p>
<div v-if="!loading" class="supplier-list"><table><thead><tr><th><input type="checkbox" aria-label="全选当前筛选供应商" :checked="allVisibleSelected" :indeterminate="!allVisibleSelected && visible.some(s => selected.includes(s.id))" :disabled="busy || !visible.length" @change="selectVisible($event.target.checked)" /></th><th>供应商 / 代码</th><th>可供分类</th><th>匹配情况</th></tr></thead><tbody><tr v-for="supplier in visible" :key="supplier.id" :class="{ chosen: selected.includes(supplier.id) }"><td><input v-model="selected" type="checkbox" :value="supplier.id" :disabled="busy" :aria-label="`选择${supplier.name}`" /></td><td><strong>{{ supplier.name }}</strong><small>{{ supplier.code }}</small></td><td>{{ (supplier.supply_category_names || []).join(' / ') || '未设置分类' }}</td><td><span :class="['match-badge', { matched: supplier.category_match }]">{{ supplier.category_match ? '分类匹配' : '其他供应商' }}</span></td></tr><tr v-if="!visible.length"><td colspan="4" class="empty-list">{{ search.trim() ? '没有符合搜索条件的供应商' : showAll ? '暂无供应商' : '暂无分类匹配供应商，可开启“显示全部供应商”进行选择' }}</td></tr></tbody></table></div>
<div class="selection-summary"><span>当前显示 {{ visible.length }} 家 · 已选 {{ selected.length }} 家</span><button v-if="selected.length" type="button" :disabled="busy" @click="selected = []">清空已选</button></div>
<h4 v-if="selected.length">已选供应商 · 供货差异</h4>
<article v-for="supplier in selectedSuppliers" :key="supplier.id" class="chosen"><div class="supplier-choice"><strong>{{ supplier.name }}</strong><small>{{ supplier.code }}</small><button type="button" :disabled="busy" @click="selected = selected.filter(id => id !== supplier.id)">移除</button></div>
<div v-if="selected.includes(supplier.id)" class="trait-grid"><label>推荐优先级<select v-model="settings[supplier.id].priority"><option>高</option><option>中</option><option>低</option></select></label><label>质量等级<select v-model="settings[supplier.id].quality"><option>A+</option><option>A</option><option>B</option><option>C</option></select></label><label>供货稳定度<select v-model="settings[supplier.id].stability"><option>高</option><option>中</option><option>低</option></select></label><label>交货期<select v-model="settings[supplier.id].delivery"><option>快</option><option>标准</option><option>慢</option></select></label><label class="notes">其他备注<textarea v-model.trim="settings[supplier.id].notes" maxlength="2000" rows="2" /></label></div></article>
</div><footer><span>已选 {{ selected.length }} 家供应商</span><button class="btn btn-primary" :disabled="busy || !selected.length" @click="save">{{ busy ? '保存中…' : '保存候选供应商' }}</button></footer>
</section></div></Teleport>
</template>
<style scoped>
.binding-backdrop{position:fixed;inset:0;z-index:300;background:#102c3555;display:flex;justify-content:flex-end}.binding-drawer{width:min(640px,100vw);height:100%;display:flex;flex-direction:column;background:#f7faf9;box-shadow:-10px 0 40px #14342a22}.binding-drawer header,.binding-drawer footer{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:20px 24px;background:white;border-bottom:1px solid #dce7e1}.binding-drawer h3{margin:0}.binding-drawer p{font-size:12px;color:#75877e}.binding-body{flex:1;min-height:0;overflow:auto;padding:20px 24px}.binding-search{width:100%;margin:8px 0 16px}.binding-drawer input:not([type=checkbox]),.binding-drawer select,.binding-drawer textarea{border:1px solid #cfdfd7;border-radius:6px;padding:9px;box-sizing:border-box}.binding-body article{background:white;padding:16px;border:1px solid #dbe7e1;border-radius:10px;margin-bottom:12px}.binding-body article.chosen{border-color:#3b9076}.supplier-choice{display:flex;gap:10px;align-items:center}.trait-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.trait-grid label{display:grid;gap:6px;font-size:12px;color:#536d61}.trait-grid .notes{grid-column:1/-1}.binding-drawer .error{color:#b94545}.binding-drawer footer{border-top:1px solid #dce7e1;font-size:13px}

.supplier-filter-bar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0}.supplier-filter-bar .binding-search{flex:1;min-width:200px;width:auto;margin:0}.all-suppliers-toggle{display:flex;gap:7px;align-items:center;white-space:nowrap;font-size:12px;color:#3b6857}.supplier-list{max-height:310px;overflow:auto;border:1px solid #dbe7e1;border-radius:8px;background:white}.supplier-list table{width:100%;border-collapse:collapse;font-size:12px}.supplier-list th{position:sticky;top:0;background:#edf5f1;text-align:left;color:#628071;z-index:1}.supplier-list th,.supplier-list td{padding:11px 9px;border-bottom:1px solid #e6eeea}.supplier-list td:first-child{width:30px}.supplier-list td strong,.supplier-list td small{display:block}.supplier-list td small{margin-top:4px;color:#84988b}.supplier-list tr.chosen{background:#f0f8f4}.match-badge{padding:4px 6px;border-radius:4px;background:#f1f3f4;color:#7e8c84;white-space:nowrap;font-size:11px}.match-badge.matched{background:#def0e7;color:#257758}.supplier-list .empty-list{text-align:center;padding:24px 16px;color:#7b8e82}.selection-summary{display:flex;justify-content:space-between;align-items:center;margin:12px 0 22px;font-size:12px;color:#75877e}.selection-summary button,.supplier-choice button{border:0;background:transparent;color:#267859;font-size:12px;cursor:pointer}.supplier-choice button{margin-left:auto}.trait-grid{margin-top:14px}.binding-body h4{font-size:14px;color:#365747}input[type=checkbox]{accent-color:#17755a}
.supplier-choice strong{min-width:0;overflow-wrap:anywhere}.binding-body label,.trait-grid label{min-width:0}.binding-body input,.binding-body select,.binding-body textarea{max-width:100%;min-width:0}.binding-drawer header p{line-height:1.6}.binding-drawer footer{flex-wrap:wrap}.supplier-list{overflow:auto}.supplier-list table{min-width:470px}.binding-drawer .error{padding:12px;border:1px solid #efc6c2;border-radius:8px;background:#fff8f7;overflow-wrap:anywhere}
:global(body:has(.binding-drawer)){overflow:hidden}
</style>
