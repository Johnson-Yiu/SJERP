<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, listAll } = useWorkspaceApi()
import { computed, ref, watch } from 'vue'

import { confirmDialog } from '../dialogs'
import SupplierBatchBindingDrawer from './SupplierBatchBindingDrawer.vue'
const props = defineProps({ productId: [Number, String], initialTab: { type: String, default: 'suppliers' }, refreshKey: Number })
const emit = defineEmits(['changed', 'drill'])
const loading = ref(false), busy = ref(false), error = ref(''), notice = ref('')
const state = ref({ definitions: [], plans: [], skus: [], relationships: [] }), rules = ref([]), suppliers = ref([])
const draft = ref(null), impact = ref(null)
const candidatePool = ref({ rows: [], parameter_options: [], sku_total: 0, with_candidates: 0, coverage_rate: 0 }), poolSearch = ref(''), poolSource = ref(''), poolParameterKey = ref(''), poolParameterValue = ref('')
const rule = ref(null), preview = ref(null), filters = ref({}), traitText = ref(''), skuSearch = ref('')
const draftText = ref(''), planOpen = ref(false)
const skuRows = ref([]), showInactive = ref(false), selectedIds = ref([])
const rulesOpen = ref(props.initialTab === 'rules')
const bindingOpen = ref(false), parameterFilters = ref({})
const selectedActive = computed(() => skuRows.value.filter(s => selectedIds.value.includes(s.id) && s.active))
const selectedInactive = computed(() => skuRows.value.filter(s => selectedIds.value.includes(s.id) && !s.active))
const allSelected = computed(() => candidatePoolRows.value.length > 0 && candidatePoolRows.value.every(s => selectedIds.value.includes(s.sku_id)))
const identityReviewOpen = ref(false), identityReviewSaving = ref(false), identityReviewError = ref('')
watch(() => props.initialTab, value => { rulesOpen.value = value === 'rules'; void load() })
const clone = value => JSON.parse(JSON.stringify(value))
const apiErrorMessage = error => error.response?.data?.detail || Object.values(error.response?.data || {}).flat().join(' ') || error.message || '操作失败。'
const keyFor = d => `${d.category_id}:${d.key}`
const getValue = (values, d) => values[keyFor(d)] ?? values[d.key] ?? values[d.name] ?? Object.entries(values).find(([key]) => [d.key.toLowerCase(), d.key.split('/')[0].toLowerCase()].includes(key.split(':').at(-1).toLowerCase()))?.[1] ?? ''
const visibleSkus = computed(() => state.value.skus.filter(s => `${s.sku} ${s.display_name_cn}`.toLowerCase().includes(skuSearch.value.toLowerCase())))
const candidatePoolRows = computed(() => skuRows.value.map(sku => {
  const candidate = candidatePool.value.rows.find(row => row.sku_id === sku.id)
  return { ...sku, ...candidate, sku_id: sku.id, sku_code: sku.sku_code || sku.sku, sku_name: sku.display_name_cn, parameters: sku.parameter_values || {}, candidate_source_types: candidate?.candidate_source_types || [], candidate_supplier_count: candidate?.candidate_supplier_count || 0 }
}).filter(row => {
  const text = `${row.sku_code} ${row.sku_name} ${row.sales_model} ${row.specification} ${Object.values(row.parameters).join(" ")}`.toLowerCase()
  return (showInactive.value || row.active) &&
    (!poolSearch.value || text.includes(poolSearch.value.toLowerCase()))
    && (!poolSource.value || row.candidate_source_types.includes(poolSource.value))
    && Object.entries(parameterFilters.value).every(([key, values]) => !values.length || values.includes(String(getValue(row.parameters, state.value.definitions.find(d => keyFor(d) === key) || { key: key.split(':').at(-1), category_id: key.split(':')[0] }))))
}))
const candidateSourceLabels = { rule_match: '按供货范围匹配', historical_purchase: '曾采购过', manual: '手动添加', supplier_sku: '已登记供货信息' }
function lastPurchaseSupplier(row) {
  const last = row.last_purchase
  return row.candidates?.find(candidate => candidate.last_purchase && last && candidate.last_purchase.date === last.date && candidate.last_purchase.price === last.price && candidate.last_purchase.currency === last.currency)?.supplier_name || ''
}
const traitString = traits => Object.entries(traits || {}).map(([k,v]) => `${k}：${v}`).join('；') || '未填写'
function parseTraits(text) {
  const result = {}
  for (const line of text.split('\n').filter(v => v.trim())) {
    const parts = line.split(/[:：]/); const key = parts.shift().trim()
    if (!key || !parts.length) throw new Error('供货特点请每行填写“名称：内容”。')
    result[key] = parts.join('：').trim()
  }
  return result
}
async function run(action) {
  if (busy.value) return
  busy.value = true; error.value = ''; notice.value = ''
  try { await action() } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function load() {
  const id = props.productId
  loading.value = true; error.value = ''
  try {
    const [a,b,c,d,e] = await Promise.all([api.get(`/products/${id}/sku-plan/`), props.initialTab === 'rules' ? listAll('/supplier-capabilities/', { params: { product: id } }) : Promise.resolve([]), props.initialTab === 'rules' ? listAll('/suppliers/') : Promise.resolve([]), api.get(`/products/${id}/supplier-candidate-pool/`), listAll('/skus/', { params: { product: id, include_inactive: '1' } })] )
    if (id !== props.productId) return
    state.value = a.data; rules.value = b; suppliers.value = c; candidatePool.value = d.data
    skuRows.value = e
    draft.value = a.data.plans.find(p => p.status === 'draft') || null
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
function openSkuRecord(row) { emit('drill', { id: row.sku_id || row.id, _target_entity: 'skus' }) }
function selectAll(checked) { selectedIds.value = checked ? candidatePoolRows.value.map(row => row.sku_id) : [] }
async function setSelectedActive(active) {
  const rows = active ? selectedInactive.value : selectedActive.value
  if (!rows.length || !await confirmDialog({ title: `确认${active ? '重新启用' : '停用'} SKU`, message: `确认${active ? '重新启用' : '停用'} ${rows.length} 个 SKU？历史单据不受影响。`, confirmText: `确认${active ? '启用' : '停用'}`, danger: !active })) return
  await run(async () => {
    const results = await Promise.allSettled(rows.map(row => api.patch(`/skus/${row.id}/`, { active })))
    const failed = results.filter(result => result.status === 'rejected')
    selectedIds.value = []; await load(); emit('changed')
    notice.value = `成功${active ? '启用' : '停用'} ${results.length - failed.length} 个 SKU。`
    if (failed.length) error.value = `${failed.length} 个操作失败：${failed.map(result => result.reason.message).join('；')}`
  })
}
watch([poolSearch, poolSource, poolParameterKey, poolParameterValue, showInactive], () => { selectedIds.value = [] })
watch(poolParameterKey, () => { poolParameterValue.value = '' })
watch(parameterFilters, () => { selectedIds.value = [] }, { deep: true })
async function bindingSaved() { bindingOpen.value = false; selectedIds.value = []; await load(); emit('changed'); notice.value = '候选供应商已保存。' }
function clearPoolFilters() { parameterFilters.value = {}; poolSearch.value = ''; poolSource.value = ''; poolParameterKey.value = ''; poolParameterValue.value = '' }
function editRule(row = null) {
  rulesOpen.value = true
  rule.value = row ? clone(row) : { product: Number(props.productId), supplier: '', name: '', is_active: true }
  filters.value = Object.fromEntries(Object.entries(row?.filters || {}).map(([k,v]) => [k, v.join('、')]))
  traitText.value = Object.entries(row?.characteristics || {}).map(([k,v]) => `${k}：${v}`).join('\n')
  preview.value = null
}
function rulePayload() {
  return { product: Number(props.productId), supplier: Number(rule.value.supplier), name: rule.value.name,
    is_active: rule.value.is_active, characteristics: parseTraits(traitText.value),
    filters: Object.fromEntries(Object.entries(filters.value).filter(([,v]) => v.trim()).map(([k,v]) => [k, v.split(/[、,，\n]/).map(x => x.trim()).filter(Boolean)])) }
}
const previewRule = () => run(async () => { preview.value = (await api.post('/supplier-capabilities/preview/', rulePayload())).data })
const saveRule = () => run(async () => {
  const payload = rulePayload()
  if (rule.value.id) await api.patch(`/supplier-capabilities/${rule.value.id}/`, payload)
  else await api.post('/supplier-capabilities/', payload)
  rule.value = null; await load(); notice.value = '供应能力已保存，候选名单按规则动态匹配。'
})
const toggleRule = row => run(async () => { await api.patch(`/supplier-capabilities/${row.id}/`, { is_active: !row.is_active }); await load() })
const startDraft = () => run(async () => { draft.value = (await api.post(`/products/${props.productId}/sku-plan/`)).data; planOpen.value = true })
function addDefinition() {
  draft.value.definitions.push({ category_id: 0, key: `attr_${Date.now()}`, name: '', unit: '', default_value: '', required: false, uppercase: false, include_in_sku: true, include_in_sales_model: false })
}
function variants(sku) { return draft.value.assignments[String(sku.id)] || [sku.parameter_values] }
function editValue(sku, index, d, value) {
  const items = clone(variants(sku))
  items[index][keyFor(d)] = value
  draft.value.assignments[String(sku.id)] = items
}
function splitSku(sku) {
  const items = clone(variants(sku)); items.push({ ...items[0] })
  draft.value.assignments[String(sku.id)] = items
}
function removeVariant(sku, index) {
  const items = clone(variants(sku)); items.splice(index, 1)
  draft.value.assignments[String(sku.id)] = items
}
async function saveDraft() {
  draft.value = (await api.patch(`/products/${props.productId}/sku-plan/`, draft.value)).data
}
const analyzeDraft = () => run(async () => {
  await saveDraft()
  impact.value = (await api.post(`/products/${props.productId}/sku-plan/analyze/`, { updated_at: draft.value.updated_at })).data
  draftText.value = JSON.stringify(draft.value)
})
function diffSegments(oldValue, newValue, side = 'new') {
  const oldText = String(oldValue || ''), newText = String(newValue || '')
  if (oldText === newText) return [{ text: oldText || '—', changed: false }]
  let prefix = 0
  while (prefix < oldText.length && prefix < newText.length && oldText[prefix] === newText[prefix]) prefix += 1
  let suffix = 0
  while (suffix < oldText.length - prefix && suffix < newText.length - prefix && oldText[oldText.length - suffix - 1] === newText[newText.length - suffix - 1]) suffix += 1
  const text = side === 'old' ? oldText : newText
  return [{ text: text.slice(0, prefix), changed: false }, { text: text.slice(prefix, text.length - suffix) || '∅', changed: true }, { text: text.slice(text.length - suffix), changed: false }].filter(item => item.text)
}
async function publishPlan() {
  await api.post(`/products/${props.productId}/sku-plan/publish/`, { updated_at: draft.value.updated_at })
  identityReviewOpen.value = false; identityReviewError.value = ''
  impact.value = null; planOpen.value = false; await load(); emit('changed'); notice.value = '方案已发布；旧单据和库存流水保留原关联，当前 SKU 已按新规则刷新。'
}
const publishDraft = () => run(async () => {
  if (!impact.value || draftText.value !== JSON.stringify(draft.value)) throw new Error('方案已修改，请重新分析。')
  if (impact.value.identity_changes?.length) {
    identityReviewError.value = ''
    identityReviewOpen.value = true
    return
  }
  await publishPlan()
})
async function confirmIdentityPublish() {
  if (identityReviewSaving.value) return
  if (!canPublish.value) { identityReviewError.value = '方案已修改或存在缺失值，请重新分析后再发布。'; return }
  identityReviewSaving.value = true; identityReviewError.value = ''; error.value = ''
  try { await publishPlan() } catch (e) { identityReviewError.value = apiErrorMessage(e); error.value = apiErrorMessage(e) } finally { identityReviewSaving.value = false }
}
function cancelIdentityPublish() { identityReviewOpen.value = false; identityReviewError.value = '' }
const discardDraft = () => run(async () => {
  await api.delete(`/products/${props.productId}/sku-plan/`); draft.value = null; impact.value = null; planOpen.value = false
})
const canPublish = computed(() => impact.value && !impact.value.stale && !impact.value.missing.length && draftText.value === JSON.stringify(draft.value))
watch(() => props.refreshKey, () => { void load() })
  watch(() => props.productId, () => { bindingOpen.value = false; selectedIds.value = []; parameterFilters.value = {}; rule.value = null; impact.value = null; planOpen.value = false; identityReviewOpen.value = false; identityReviewError.value = ''; void load() }, { immediate: true })
</script>

<template>
 <section class="sku-management" aria-label="SKU 参数与供应商管理">
  <div class="management-head"><div><h3>{{ initialTab === 'rules' ? '供应能力规则' : 'SKU 档案与供应商分配' }}</h3><p>一份 SKU 清单管理规格与供货候选；实际采购供应商在销售订单或采购单中确认。</p></div></div>
  <p v-if="error" role="alert" class="error">{{ error }}</p><p v-if="notice" role="status" class="notice">{{ notice }}</p>
  <p v-if="loading">正在加载…</p>
  <template v-if="!loading">
   <section v-if="initialTab !== 'rules'" class="candidate-pool-card">
    <div class="pool-heading"><div><h4>已有 SKU · {{ candidatePoolRows.length }} 条</h4><p class="help">筛选参数并勾选 SKU，可批量绑定候选供应商；同一参数多选为任一匹配，不同参数同时满足。</p></div><div class="pool-actions"><button type="button" @click="clearPoolFilters">清空筛选</button></div></div>
    <div class="pool-summary"><div><small>启用 SKU 总数</small><strong>{{ candidatePool.sku_total }}</strong></div><div><small>已有候选供应商</small><strong>{{ candidatePool.with_candidates }}</strong></div><div><small>覆盖率</small><strong>{{ candidatePool.coverage_rate }}%</strong></div></div>
    <div class="pool-filters"><input v-model.trim="poolSearch" placeholder="搜索 SKU 编码、中文名称或 Sales Model" /><select v-model="poolSource"><option value="">全部来源</option><option v-for="(label,key) in candidateSourceLabels" :key="key" :value="key">{{ label }}</option></select></div>
    <div class="pool-parameter-filters"><div v-for="parameter in candidatePool.parameter_options" :key="parameter.key"><strong>{{ parameter.name }}</strong><label v-for="value in parameter.values" :key="value"><input type="checkbox" :checked="(parameterFilters[parameter.key] || []).includes(value)" @change="parameterFilters[parameter.key] = $event.target.checked ? [...(parameterFilters[parameter.key] || []), value] : (parameterFilters[parameter.key] || []).filter(v => v !== value)" />{{ value }}</label></div></div>
    <div class="actions sku-list-actions">
     <label class="inline-check"><input type="checkbox" v-model="showInactive" /> 显示已停用 SKU</label>
     <span>已选 {{ selectedIds.length }} 项（仅当前筛选结果）</span><button class="btn btn-primary batch-bind-button" type="button" :disabled="busy || !selectedActive.length || selectedInactive.length > 0" @click="bindingOpen = true">批量绑定供应商</button>
     <button v-if="selectedActive.length" class="deactivate-button" type="button" :disabled="busy" @click="setSelectedActive(false)">停用 {{ selectedActive.length }} 项</button>
     <button v-if="selectedInactive.length" type="button" :disabled="busy" @click="setSelectedActive(true)">重新启用 {{ selectedInactive.length }} 项</button>
     <button v-if="selectedIds.length" type="button" @click="selectedIds=[]">取消选择</button>
    </div>
    <div class="candidate-table-wrap"><table class="candidate-table"><thead><tr>
     <th><input type="checkbox" aria-label="选择当前筛选的全部 SKU" :checked="allSelected" @change="selectAll($event.target.checked)" /></th>
     <th>SKU Code</th><th>中文名称 / Sales Model</th><th>规格</th><th>库存 / 单位</th><th>成本 / 售价</th><th>可选供应商</th><th>最近采购</th><th>状态</th><th>操作</th>
    </tr></thead><tbody><tr v-for="row in candidatePoolRows" :key="row.sku_id" :class="{ 'selected-sku-row': selectedIds.includes(row.sku_id), 'inactive-sku-row': !row.active }">
     <td><input type="checkbox" v-model="selectedIds" :value="row.sku_id" :aria-label="'选择 ' + row.sku_code" /></td>
     <td><button type="button" class="text-btn" @click="openSkuRecord(row)">{{ row.sku_code }}</button></td>
     <td><strong>{{ row.sku_name }}</strong><small>{{ row.sales_model || '未设置 Sales Model' }}</small></td>
     <td>{{ row.specification || Object.values(row.parameters).join(' / ') || '—' }}</td>
     <td>{{ row.stock_quantity ?? '—' }} <small>{{ row.unit }}</small></td>
     <td>{{ row.cost_price }} / {{ row.default_price }}<small>{{ row.currency }}</small></td>
     <td><span v-if="!row.active">—</span><template v-else-if="row.candidate_supplier_count"><strong v-for="supplier in (row.candidates || [])" :key="supplier.supplier">{{ supplier.supplier_name }}</strong><small v-if="row.preferred_supplier">优先选择：{{ row.preferred_supplier.name }}</small></template><span v-else>暂无可选供应商</span></td>
     <td><template v-if="row.last_purchase"><span>{{ lastPurchaseSupplier(row) }}</span><small>{{ row.last_purchase.date }}</small><small>单价 {{ row.last_purchase.price }} {{ row.last_purchase.currency }}</small></template><span v-else>尚未采购</span></td>
     <td>{{ row.active ? '启用' : '已停用' }}</td>
     <td><button type="button" class="text-btn record-link" @click="openSkuRecord(row)">查看 SKU</button></td>
    </tr></tbody></table></div>
    <p v-if="!candidatePoolRows.length" class="help">当前筛选下暂无 SKU。</p>
   </section>
   <details v-if="initialTab === 'rules'" :open="rulesOpen" @toggle="rulesOpen = $event.target.open" class="rules-panel"><summary>供应能力规则 · {{ rules.length }} 条 <span>批量匹配多个 SKU，不指定订单供应商</span></summary>
   <div class="line"><h4>供应能力规则</h4><button type="button" @click="editRule()">＋ 添加规则</button></div>
   <p class="help">同一参数内任一取值匹配即可，不同参数须同时满足。留空表示不限。规则只推荐候选，实际供应商由采购单确定。</p>
   <div v-for="row in rules" :key="row.id" class="rule-row"><div><strong>{{ row.name }}</strong> · {{ row.supplier_name }} <small>{{ row.is_active ? '启用' : '停用' }}</small><p>{{ Object.entries(row.filters).map(([k,v]) => `${state.definitions.find(d=>keyFor(d)===k)?.name || k}：${v.join(' / ')}`).join('；') || '本产品全部 SKU' }}</p><p>{{ traitString(row.characteristics) }}</p></div><div class="actions"><button type="button" @click="editRule(row)">编辑</button><button type="button" :disabled="busy" @click="toggleRule(row)">{{ row.is_active ? '停用' : '启用' }}</button></div></div>
   <p v-if="!rules.length" class="help">尚无规则。先选择供应商，再填写它能做的参数范围。</p>
   <form v-if="rule" class="editor" @submit.prevent="saveRule">
    <h4>{{ rule.id ? '编辑供应能力' : '新增供应能力' }}</h4><div class="fields"><label>规则名称<input v-model.trim="rule.name" required placeholder="例如：A厂常规灯带" /></label><label>供应商<select v-model="rule.supplier" required><option value="">请选择</option><option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option></select></label><label v-for="d in state.definitions" :key="keyFor(d)">{{ d.name }}<input v-model="filters[keyFor(d)]" placeholder="不限；多个值用顿号隔开" /></label></div>
    <label>共同供货特点<textarea v-model="traitText" rows="4" placeholder="PCB：白色&#10;背胶：3M&#10;包装：10米/卷" /></label><p class="help">共同特点作为供货档案初始值，已有档案和历史采购不会随规则更新。</p>
    <div class="actions"><button type="button" :disabled="busy" @click="previewRule">预览匹配</button><button type="submit" :disabled="busy" class="primary">保存规则</button><button type="button" @click="rule=null">取消</button></div><p v-if="preview">匹配 {{ preview.length }} 个现有 SKU：{{ preview.slice(0,15).map(s=>s.name).join('、') }}{{ preview.length>15 ? '…' : '' }}</p>
   </form>
   </details>
  </template>
  <details v-if="!loading && initialTab !== 'rules'" class="parameter-plan-panel"><summary>参数变更与历史方案 <span>调整已有 SKU 时，先分析影响再确认发布</span></summary>
   <p class="help">新增参数先补值；不再区分商品的参数改为普通属性。需要拆分时只添加实际组合；出现相同组合时合并为新 SKU。旧单据、库存及供货档案保留在原 SKU。</p>
   <div class="actions"><button type="button" class="primary" :disabled="busy" @click="startDraft">{{ draft ? `继续 V${draft.version} 草稿` : '创建参数方案草稿' }}</button><span>已发布：{{ state.plans.filter(p=>p.status==='published').map(p=>`V${p.version}`).join('、') || '尚无' }}</span></div>
   <div v-if="draft && planOpen" class="editor">
    <div class="line"><h4>V{{ draft.version }} 草稿</h4><button type="button" @click="addDefinition">＋ 新增参数</button></div>
    <div class="scroll"><table><thead><tr><th>参数名称</th><th>单位</th><th>补充默认值</th><th>区分 SKU</th><th>参与型号</th><th>必填</th></tr></thead><tbody><tr v-for="d in draft.definitions" :key="keyFor(d)"><td><input v-model="d.name" aria-label="参数名称" /></td><td><input v-model="d.unit" aria-label="单位" /></td><td><input v-model="d.default_value" placeholder="仅补充空值" /></td><td><input type="checkbox" v-model="d.include_in_sku" /></td><td><input type="checkbox" v-model="d.include_in_sales_model" /></td><td><input type="checkbox" v-model="d.required" /></td></tr></tbody></table></div>
    <p class="help">取消“区分 SKU”和“参与型号”即可降为普通属性，原取值仍保留。默认值只用于空缺参数，已有值不会被覆盖。</p>
    <h4>现有 SKU 补值 / 拆分</h4><input v-model="skuSearch" placeholder="搜索 SKU 编码或名称" />
    <div class="sku-assignments"><div v-for="s in visibleSkus" :key="s.id" class="assignment"><div class="line"><strong>{{ s.display_name_cn }} · {{ s.sku }}</strong><button type="button" @click="splitSku(s)">＋ 拆分一个实际组合</button></div><div v-for="(variant,index) in variants(s)" :key="index" class="fields"><label v-for="d in draft.definitions" :key="keyFor(d)">{{ d.name }}<input :value="getValue(variant,d)" :placeholder="d.default_value || '待补值'" @input="editValue(s,index,d,$event.target.value)" /></label><button v-if="variants(s).length>1" type="button" @click="removeVariant(s,index)">移除组合</button></div></div></div>
    <div class="actions"><button type="button" :disabled="busy" @click="analyzeDraft" class="primary">保存草稿并分析影响</button><button type="button" :disabled="busy" @click="discardDraft">丢弃草稿</button></div>
    <div v-if="impact" class="impact"><h4>发布前核对</h4><p>当前 {{ impact.current_count }} 个 SKU → {{ impact.result_count }} 个当前组合；新增 {{ impact.new_count }} 个 SKU；历史单据改写 0 条。</p><p v-if="impact.stale" class="error">现有数据已变化，请丢弃草稿后重新创建。</p><p v-for="(m,i) in impact.missing" :key="i" class="error">{{ m.sku }}：请补充{{ m.parameter }}</p><div v-for="g in impact.groups" :key="g.signature" class="impact-row">{{ g.source_codes.join(' + ') }} → {{ g.action==='keep' ? '保留原 SKU' : g.action==='refresh' ? '刷新原 SKU，保存旧版本' : '建立新 SKU，旧 SKU 归档' }}<p>{{ draft.definitions.filter(d=>d.include_in_sku || d.include_in_sales_model).map(d=>`${d.name}：${getValue(g.values,d)}`).join('；') }}</p><p v-if="g.ordinary_conflicts?.length">普通属性取值不同，新 SKU 暂留空：{{ g.ordinary_conflicts.join('、') }}；旧值保留在历史 SKU。</p></div><p class="help">刷新原 SKU 会保留 SKU Code 并记录旧名称和型号；新 SKU 按当前规则自动生成型号。原库存、报价和订单不会被改写。</p><button type="button" class="primary" :disabled="busy || !canPublish" @click="publishDraft">确认以上结果并发布</button><p v-if="!canPublish && !impact.stale && !impact.missing.length">草稿已修改，请重新分析。</p></div>
   </div>
    <div v-if="identityReviewOpen && impact" class="modal-backdrop plan-identity-review-backdrop"><section class="modal plan-identity-review-modal"><div class="modal-head"><div><h3>确认参数导致的 SKU 身份更新</h3><p>确认后会刷新当前 SKU 的中文名称和 Sales Model，并把修改前的值保存为历史快照；历史单据和库存流水不变。</p></div><button type="button" class="mini-btn" @click="cancelIdentityPublish">×</button></div><div class="modal-body"><div v-for="change in impact.identity_changes" :key="change.sku_id" class="plan-identity-row"><strong>{{ change.sku_code }}</strong><div class="plan-identity-grid"><div><small>内部名称（修改前）</small><p><span v-for="(part,index) in diffSegments(change.old_display_name_cn, change.new_display_name_cn, 'old')" :key="`old-name-${change.sku_id}-${index}`" :class="{ 'diff-removed': part.changed }">{{ part.text }}</span></p></div><div><small>内部名称（修改后）</small><p><span v-for="(part,index) in diffSegments(change.old_display_name_cn, change.new_display_name_cn)" :key="`new-name-${change.sku_id}-${index}`" :class="{ 'diff-added': part.changed }">{{ part.text }}</span></p></div><div><small>Sales Model（修改前）</small><p><span v-for="(part,index) in diffSegments(change.old_sales_model, change.new_sales_model, 'old')" :key="`old-model-${change.sku_id}-${index}`" :class="{ 'diff-removed': part.changed }">{{ part.text }}</span></p></div><div><small>Sales Model（修改后）</small><p><span v-for="(part,index) in diffSegments(change.old_sales_model, change.new_sales_model)" :key="`new-model-${change.sku_id}-${index}`" :class="{ 'diff-added': part.changed }">{{ part.text }}</span></p></div></div></div><p v-if="identityReviewError" class="sku-save-error" role="alert">{{ identityReviewError }}</p><p class="identity-review-hint">确认提交时系统会再次检查当前名称、Sales Model 和参数组合是否重复；发现重复时整次发布不会保存。</p></div><div class="modal-foot"><button type="button" class="btn btn-secondary" @click="cancelIdentityPublish">取消</button><button type="button" class="btn btn-primary" :disabled="identityReviewSaving" @click="confirmIdentityPublish">{{ identityReviewSaving ? '检查并发布中…' : '确认并发布' }}</button></div></section></div>
   <details v-if="state.relationships.length"><summary>历史 SKU 去向（{{ state.relationships.length }} 条）</summary><p v-for="(r,i) in state.relationships" :key="i">{{ r.sku }} → {{ r.successors__target__sku }}</p></details>
  </details>
 </section>
<SupplierBatchBindingDrawer v-if="bindingOpen" :product-id="productId" :sku-ids="selectedActive.map(s => s.id)" @close="bindingOpen = false" @saved="bindingSaved" />
</template>

<style scoped>
.sku-list-actions{margin:12px 0;font-size:var(--text-caption)}
.sku-management .inline-check{display:flex;align-items:center;gap:6px}
.selected-sku-row{background:#edf8f3}.inactive-sku-row{opacity:.65}
.record-link{display:block;margin-top:6px}
.sku-management summary{cursor:pointer;font-weight:700;color:#285d4e;padding:12px 0}
.sku-management summary span{font-weight:400;color:#71857a;font-size:var(--text-caption);margin-left:10px}
.parameter-plan-panel,.rules-panel{border-top:1px solid #dce7e1}
.candidate-table-wrap{max-height:480px}.candidate-table th{position:sticky;top:0;z-index:1}

.sku-management{border:1px solid #dce7e1;border-radius:10px;padding:20px;background:white;color:#203b34;min-width:0}.management-head,.line,.rule-row{display:flex;justify-content:space-between;gap:16px;align-items:center}.management-head h3,h4{margin:0 0 10px}.management-head p,.help,.rule-row p{color:#71857a;font-size:var(--text-caption);line-height:1.7;margin:6px 0}.switcher,.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.switcher{flex:none}.sku-management button{padding:8px 12px;border:1px solid #d4e2da;border-radius:6px;background:#fff;color:#285d4e;cursor:pointer}.sku-management button.primary,.switcher .active{background:#11634f;color:#fff}.sku-management button:disabled{opacity:.5;cursor:default}.rule-row{border-bottom:1px solid #e9efeb;padding:12px 0}.rule-row>div:first-child{flex:1}.sku-management input,.sku-management select,.sku-management textarea{box-sizing:border-box;padding:9px;border:1px solid #d4e2da;border-radius:6px;color:#294e3e;background:white;max-width:100%;font:inherit}.sku-management select{max-width:100%}.fields{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}.fields label{flex:1;min-width:120px}.sku-management label{display:grid;gap:6px;font-size:var(--text-caption)}.editor{margin-top:18px;padding:16px;border:1px solid #dce7e1;border-radius:8px;background:#f8fbf9}.sku-management textarea{width:100%}.error{color:#b42318;background:#fff2f0;padding:10px}.notice{color:#126450;background:#eaf7f0;padding:10px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:8px;font-size:var(--text-body)}td input:not([type=checkbox]){min-width:90px;width:100%}.assignment{border-bottom:1px solid #dce7e1;padding:12px 0}.sku-assignments{max-height:420px;overflow:auto;margin-bottom:14px}.impact{margin-top:16px;padding:15px;border:1px solid #c4dbd0;background:white}.impact-row{padding:8px 0;font-size:var(--text-caption)}.sku-management details{margin-top:16px}@media(max-width:750px){.management-head,.line,.rule-row{align-items:stretch;flex-direction:column}.sku-management{padding:12px}.fields label{min-width:100px}}
.candidate-pool-card{margin:18px 0;padding:16px;border:1px solid #dce7e1;border-radius:9px;background:#fbfdfc}.pool-heading{display:flex;align-items:start;justify-content:space-between;gap:16px}.pool-actions{display:flex;gap:8px;flex-wrap:wrap}.pool-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0}.pool-summary>div{padding:11px 13px;border:1px solid #e4eee9;border-radius:8px;background:#fff}.pool-summary small,.pool-summary strong{display:block}.pool-summary small{color:#7d9087;font-size:var(--text-caption)}.pool-summary strong{margin-top:5px;color:#1d6653;font-size:var(--text-dialog)}.pool-filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.pool-filters input{min-width:240px;flex:1}.pool-filters select{min-width:135px}.candidate-table-wrap{overflow:auto}.candidate-table{min-width:980px;background:#fff}.candidate-table th{background:#f1f7f4;color:#71857b;font-size:var(--text-caption);white-space:nowrap}.candidate-table td{border-top:1px solid #e8efeb;color:#425b51;vertical-align:top}.candidate-table td strong,.candidate-table td small{display:block}.candidate-table td small{margin-top:3px;color:#7a8c84;line-height:1.45}.candidate-pool-card .text-btn{padding:3px 0;border:0;background:transparent;color:#1e755c}@media(max-width:750px){.pool-heading{align-items:stretch;flex-direction:column}.pool-summary{grid-template-columns:1fr}.pool-filters input{min-width:100%}}
.plan-identity-review-backdrop{z-index:140}.plan-identity-review-modal{width:min(980px,calc(100vw - 28px));max-height:calc(100vh - 48px)}.plan-identity-row{padding:12px 0;border-bottom:1px solid #e5eee9}.plan-identity-row>strong{display:block;margin-bottom:8px;color:#285d4e}.plan-identity-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.plan-identity-grid>div{padding:10px;border:1px solid #e3ece7;border-radius:7px;background:#fff}.plan-identity-grid small{display:block;margin-bottom:4px;color:#7a8b83;font-size:var(--text-caption)}.plan-identity-grid p{margin:0;color:#29483e;font-size:var(--text-body);line-height:1.6;word-break:break-word}.diff-removed{background:#ffd9d5;color:#a52f24;text-decoration:line-through;border-radius:3px;padding:1px 2px}.diff-added{background:#ccefdc;color:#176443;border-radius:3px;padding:1px 2px}.identity-review-hint{margin:12px 0 0;color:#687c73;font-size:var(--text-caption);line-height:1.7}.sku-save-error{margin:12px 0 0;padding:10px;border-radius:7px;background:#fff2f0;color:#b42318;font-size:var(--text-body)}@media(max-width:650px){.plan-identity-grid{grid-template-columns:1fr}}
.pool-parameter-filters{display:grid;gap:10px;padding:12px;background:#f0f6f3;border-radius:8px;margin-bottom:12px}.pool-parameter-filters>div{display:flex;align-items:center;flex-wrap:wrap;gap:8px}.pool-parameter-filters strong{min-width:105px;font-size:12px}.pool-parameter-filters label{display:flex;align-items:center;gap:5px;padding:5px 9px;background:white;border:1px solid #dce7e1;border-radius:6px;font-size:12px}

.sku-management .batch-bind-button{background:#11634f;border-color:#11634f;color:#fff;box-shadow:none}
.sku-management .batch-bind-button:hover:not(:disabled){background:#0c503f;border-color:#0c503f}
.sku-management .batch-bind-button:disabled{background:#e5e7eb;border-color:#d9dde2;color:#8a939e;opacity:1;cursor:not-allowed;box-shadow:none}
.sku-management .deactivate-button{background:#fff1f0;border-color:#efb8b3;color:#b42318}
.sku-management .deactivate-button:hover:not(:disabled){background:#fee2df;border-color:#df827b;color:#991b14}
.sku-management .batch-bind-button:focus-visible,.sku-management .deactivate-button:focus-visible{outline:2px solid currentColor;outline-offset:3px}
</style>
