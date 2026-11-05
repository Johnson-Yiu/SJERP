<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, listAll } = useWorkspaceApi()
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { apiErrorMessage } from '../utils/apiErrors'
import { packagingError } from '../utils/packagingPresentation'
import { internalPagePath } from '../utils/modalNavigation'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import { confirmDialog } from '../dialogs'
import PageLoadState from '../components/PageLoadState.vue'
import SkuPickerPanel from '../components/SkuPickerPanel.vue'
import { useAccessControl } from '../accessControl'
const route=useRoute(),router=useRouter(),{can}=useAccessControl()
const skus=ref([]),suppliers=ref([]),units=ref([]),selected=ref(route.query.sku||''),loading=ref(false),hasLoaded=ref(false),saving=ref(false),error=ref(''),saveError=ref(''),notice=ref(''),editingId=ref(null)
const unitForm=ref(null)
const form=reactive({name:'',unit:'卷',factor:'',supplier:'',allow_fraction:false,is_default:false,active:true,notes:''})
const guard=useUnsavedChangesGuard({data:()=>form,enabled:()=>hasLoaded.value&&!!selected.value,busy:()=>saving.value})
const sku=computed(()=>skus.value.find(s=>s.id===Number(selected.value)))
const rows=computed(()=>units.value.filter(u=>!selected.value||u.sku===Number(selected.value)))
const returnPath=computed(()=>internalPagePath(route.query.returnTo)|| (selected.value?`/skus?detail=${selected.value}`:'/skus'))
const duplicateDefinition=computed(()=>!editingId.value&&rows.value.some(row=>row.name===form.name&&row.unit===form.unit&&Number(row.factor)===Number(form.factor)&&Number(row.supplier||0)===Number(form.supplier||0)&&row.allow_fraction===form.allow_fraction))
const conversion=computed(()=>sku.value&&form.factor?`1 ${form.unit||'交易单位'} = ${form.factor} ${sku.value.unit}`:'填写系数后显示换算关系')
function reset(){editingId.value=null;Object.assign(form,{name:'',unit:'卷',factor:'',supplier:'',allow_fraction:false,is_default:false,active:true,notes:''});saveError.value=''}
async function selectSku(value){const id=String(value||'');if(id===String(selected.value)||saving.value)return;await guard.requestClose(async()=>{if(id===String(selected.value))return;reset();guard.markClean();await router.replace({path:route.path,query:{...route.query,sku:id||undefined}})})}
const selectedBinding=computed({get:()=>selected.value,set:value=>{void selectSku(value)}})
const selectedSkuIds=computed({get:()=>selected.value?[String(selected.value)]:[],set:ids=>{void selectSku(ids?.length?ids[ids.length-1]:'')}})
watch(()=>route.query.sku,async value=>{selected.value=value||'';reset();notice.value='';await nextTick();guard.markClean()})
let loadVersion=0
async function load(){const version=++loadVersion;loading.value=true;error.value='';try{const [s,p,u]=await Promise.all([can('skus','view')?listAll('/skus/',{params:{include_inactive:1}}):[],can('suppliers','view')?listAll('/suppliers/'):[],listAll('/sku-trade-units/')]);if(version!==loadVersion)return;skus.value=s;suppliers.value=p;units.value=u;hasLoaded.value=true}catch(e){if(version===loadVersion)error.value=apiErrorMessage(e)}finally{if(version===loadVersion)loading.value=false}}
async function newUnit(){if(saving.value)return;await guard.requestClose(async()=>{reset();notice.value='';await nextTick();guard.markClean();unitForm.value?.querySelector('input')?.focus()})}
async function edit(row){if(!can('trade_units','update')||saving.value)return;await guard.requestClose(async()=>{selected.value=String(row.sku);await router.replace({path:route.path,query:{...route.query,sku:String(row.sku)}});editingId.value=row.id;Object.assign(form,{name:row.name,unit:row.unit,factor:row.factor,supplier:row.supplier||'',allow_fraction:row.allow_fraction,is_default:row.is_default,active:row.active,notes:row.notes||''});saveError.value='';notice.value='';await nextTick();guard.markClean();unitForm.value?.querySelector('textarea')?.focus()})}
async function create(){
  if(saving.value||!sku.value||!can('trade_units',editingId.value?'update':'create'))return
  saving.value=true;saveError.value='';notice.value=''
  try{
    if(editingId.value)await api.patch(`/sku-trade-units/${editingId.value}/`,{notes:form.notes,is_default:form.is_default,active:form.active})
    else await api.post('/sku-trade-units/',{...form,sku:Number(selected.value),supplier:form.supplier?Number(form.supplier):null})
    const edited=!!editingId.value;reset();await nextTick();guard.markClean();await load();notice.value=edited?'交易规格已更新':'交易规格已添加'
  }catch(e){saveError.value=packagingError(e)}finally{saving.value=false}
}
let changing=false
async function change(row,patch){
  if(changing||saving.value||!can('trade_units','update'))return
  changing=true
  try{if(!await guard.requestClose(async()=>{reset();guard.markClean()}))return
  saving.value=true;saveError.value='';notice.value=''
  if(patch.active===false&&!await confirmDialog({title:'停用交易规格',message:'停用后不能用于新单据，历史单据的换算快照保留。',confirmText:'确认停用',danger:true}))return;await api.patch(`/sku-trade-units/${row.id}/`,patch);await load();notice.value='交易规格已更新'}catch(e){saveError.value=packagingError(e)}finally{saving.value=false;changing=false}
}
onMounted(async()=>{await load();await nextTick();guard.markClean()})
</script>
<template>
  <div class="units-page">
    <header class="page-head"><div><h2>SKU 交易单位</h2><p>设置卷、箱等交易规格；库存仍按 SKU 基础单位记账。</p></div><div class="page-actions"><RouterLink v-if="can('skus','view')" class="btn btn-secondary" :to="returnPath">返回 SKU</RouterLink><button class="btn btn-secondary" :disabled="loading||saving" @click="load">刷新</button></div></header>
    <PageLoadState :loading="loading" :has-loaded="hasLoaded" :error="error" @retry="load" />
    <p v-if="notice" role="status" class="success">{{ notice }}</p>
    <section v-if="hasLoaded" class="panel unit-filters" :inert="saving">
      <SkuPickerPanel v-model="selectedSkuIds" v-model:active-id="selectedBinding" :skus="skus" title="选择 SKU" search-placeholder="搜索 SKU、型号或描述" :height="240" :show-price="false"><template #preview="{sku:activeSku}"><p class="picker-hint">基础单位：{{ activeSku.unit||'pcs' }}。包装规格不会自动改变此单位。</p></template></SkuPickerPanel>
    </section>
    <p v-if="hasLoaded&&selected&&!sku" role="alert">未找到所选 SKU，请重新选择。</p>
    <div v-if="hasLoaded" class="units-layout">
      <section class="panel"><div class="section-heading"><h3>交易规格 <small>{{ rows.length }} 项</small></h3><button v-if="sku&&can('trade_units','create')" class="btn btn-secondary" :disabled="saving" @click="newUnit">新增规格</button></div><p class="hint">1 卷或 1 箱含多少基础单位，由换算系数决定。供应商专用规格只适用于对应供应商。</p><p v-if="!rows.length">{{ selected?'暂无交易规格，可在右侧新增。':'请先选择 SKU；下方展示全部已配置规格。' }}</p><div class="table-wrap"><table v-if="rows.length" class="data-table"><thead><tr><th>SKU / 规格</th><th>换算关系</th><th>供应商</th><th>数量规则 / 状态</th><th>操作</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td><strong>{{ row.name }}</strong><small>{{ row.sku_code }}</small><small v-if="row.notes">{{ row.notes }}</small></td><td class="conversion">1 {{ row.unit }} = {{ row.factor }} {{ row.base_unit }}</td><td>{{ row.supplier_name||'通用规格' }}</td><td>{{ row.allow_fraction?'允许小数':'仅整数数量' }}<small>{{ row.active?'启用':'停用' }}{{ row.is_default?' · 默认':'' }}</small></td><td><div class="unit-actions"><button v-if="can('trade_units','update')" :disabled="saving" class="btn btn-secondary" @click="edit(row)">编辑备注</button><button v-if="can('trade_units','update')" :disabled="saving" class="btn btn-secondary" @click="change(row,{active:!row.active})">{{ row.active?'停用':'启用' }}</button><button v-if="can('trade_units','update')&&row.active" :disabled="saving" class="btn btn-secondary" @click="change(row,{is_default:!row.is_default})">{{ row.is_default?'取消默认':'设为默认' }}</button></div></td></tr></tbody></table></div></section>
      <form ref="unitForm" v-if="can('trade_units',editingId?'update':'create')" class="panel unit-form" @submit.prevent="create"><h3>{{ editingId?'编辑交易规格':'新增交易规格' }}</h3><p>{{ sku?`${sku.display_name_cn||sku.sku} · 基础单位：${sku.unit}`:'请先选择一个 SKU' }}</p><p v-if="saveError" role="alert" class="error">{{ saveError }}</p><fieldset :disabled="saving||!sku"><label>规格名称<input v-model.trim="form.name" :disabled="!!editingId" placeholder="例如：10 米/卷" maxlength="120" required /></label><div class="unit-pair"><label>交易单位<input v-model.trim="form.unit" :disabled="!!editingId" maxlength="30" required /></label><label>换算系数<input v-model="form.factor" :disabled="!!editingId" type="number" min="0.01" step="0.01" required /></label></div><strong class="conversion-preview">{{ conversion }}</strong><p v-if="duplicateDefinition" class="hint" role="note">已有相同名称、换算和供应商的规格，请检查是否重复；需要时仍可继续添加。</p><label>供应商（可选）<select v-model="form.supplier" :disabled="!!editingId||!can('suppliers','view')"><option value="">通用规格</option><option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option></select></label><label class="check"><input v-model="form.allow_fraction" :disabled="!!editingId" type="checkbox" />允许小数交易数量</label><p class="field-help">例如 0.5 卷；未勾选时只能填写整数卷数或箱数。</p><label class="check"><input v-model="form.is_default" type="checkbox" />设为该 SKU 默认规格</label><label v-if="editingId" class="check"><input v-model="form.active" type="checkbox" />启用规格</label><label>备注<textarea v-model="form.notes" /></label></fieldset><p class="hint">名称、单位、换算系数、供应商和小数规则保存后固定。规格变化时请停用旧项后新建；历史单据保留原快照。装箱数量及产品净重仍按基础单位填写。</p><div class="form-actions"><button v-if="editingId||guard.dirty.value" type="button" class="btn btn-secondary" :disabled="saving" @click="newUnit">取消</button><button class="btn btn-primary" :disabled="!sku||saving">{{ saving?'保存中…':editingId?'保存修改':'添加规格' }}</button></div></form>
    </div>
  </div>
</template>
<style scoped>
.units-page{display:grid;gap:18px;min-width:0}.units-page h2,.units-page h3{margin:0 0 10px}.units-page p{color:#6b8178;line-height:1.7;margin:0}.page-actions,.section-heading,.form-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.section-heading{justify-content:space-between;margin-bottom:12px}.unit-filters{padding:18px;min-width:0}.unit-filters :deep(.sku-selection-panel){margin:0}.picker-hint{margin:0;padding:10px 12px;background:#edf6f1;border-radius:7px;font-size:13px}.units-layout{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(310px,1fr);gap:18px}.units-layout>.panel{padding:20px;min-width:0}.unit-form,.unit-form fieldset{display:grid;gap:14px;align-content:start}.unit-form fieldset{border:0;padding:0;margin:0;min-width:0}label{display:grid;gap:7px;color:#365b4d;font-size:14px;min-width:0}input,select,textarea{padding:9px;border:1px solid #d4e0d9;border-radius:7px;min-width:0;max-width:100%;background:white;font:inherit}textarea{min-height:76px;resize:vertical}.unit-pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.check{display:flex;align-items:center}.hint,.conversion-preview{font-size:13px;background:#eff6f2;padding:12px;border-radius:8px}.field-help{font-size:12px}.conversion-preview{color:#1c6553;overflow-wrap:anywhere}.error{color:#a33131!important;background:#fff4f1;padding:12px;border-radius:8px;overflow-wrap:anywhere}.success{color:#246b50!important;background:#edf8f1;padding:12px}.data-table{min-width:710px;table-layout:fixed}.data-table th:first-child{width:180px}.data-table th:last-child{width:140px}td{overflow-wrap:anywhere}td small{display:block;color:#7d9087;margin-top:5px}.conversion{font-weight:650;color:#245d50}.unit-actions{display:flex;gap:5px;flex-wrap:wrap}.unit-actions .btn{padding:6px 8px;font-size:12px}.table-wrap{overflow:auto}.form-actions{justify-content:flex-end}@media(max-width:1200px){.units-layout{grid-template-columns:1fr}.unit-form fieldset{grid-template-columns:repeat(2,minmax(0,1fr))}.unit-pair,.conversion-preview{grid-column:1/-1}}@media(max-width:700px){.unit-form fieldset{grid-template-columns:1fr}.page-head{flex-wrap:wrap}}
</style>
