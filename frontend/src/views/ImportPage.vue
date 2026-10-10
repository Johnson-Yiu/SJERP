<script setup>
import { computed, onMounted, ref } from 'vue'
import { UploadCloud, Download, FileSpreadsheet, CheckCircle2, AlertTriangle } from 'lucide-vue-next'
import { api } from '../api'
import { confirmDialog } from '../dialogs'

const entity = ref('customers'), file = ref(null), templates = ref({}), previewing = ref(false), executing = ref(false), result = ref(null), error = ref('')
const types = { customers: ['客户', '按客户编号匹配'], products: ['产品', '分类须预先建立'], skus: ['SKU', '按 SKU 与产品编号匹配'], transactions: ['财务流水', '只新增，不覆盖'] }
const canExecute = computed(() => Boolean(result.value?.preview_token) && !result.value?.errors?.length)
onMounted(async () => { try { templates.value = (await api.get('/import/templates/')).data } catch (e) { error.value = e.message } })
function invalidatePreview() { result.value = null; error.value = '' }
function choose(e) { file.value = e.target.files[0]; invalidatePreview() }
function changeEntity() { file.value = null; invalidatePreview() }
function downloadTemplate() {
  const headers = templates.value[entity.value] || []
  const blob = new Blob(['\ufeff' + headers.join(',') + '\n'], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = `${entity.value}_template.csv`; a.click(); URL.revokeObjectURL(url)
}
async function preview() {
  if (!file.value) return error.value = '请先选择 CSV 文件。'
  previewing.value = true; error.value = ''; result.value = null
  const data = new FormData(); data.append('entity', entity.value); data.append('file', file.value)
  try { result.value = (await api.post('/import/csv/preview/', data)).data } catch (e) { error.value = e.message } finally { previewing.value = false }
}
function downloadFailures() {
  const rows = result.value?.errors || []
  const text = '\ufeffrow,key,message\n' + rows.map(item => [item.row, item.key || '', item.message].map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a'); link.href = url; link.download = `${entity.value}_import_failures.csv`; link.click(); URL.revokeObjectURL(url)
}
async function execute() {
  if (!canExecute.value) return
  const approved = await confirmDialog({ title: '确认执行导入', message: `确认导入 ${result.value.total} 行数据？执行成功后将正式修改系统数据。`, confirmText: '确认导入' })
  if (!approved) return
  executing.value = true; error.value = ''
  const data = new FormData(); data.append('entity', entity.value); data.append('file', file.value); data.append('preview_token', result.value.preview_token)
  try { result.value = { ...(await api.post('/import/csv/execute/', data)).data, errors: [], completed: true } }
  catch (e) { error.value = e.message; result.value = null }
  finally { executing.value = false }
}
</script>

<template>
  <div>
    <div class="page-head"><div><h2>历史数据快速导入</h2><p>使用 CSV 将 Excel 数据迁移进系统，并按业务编号自动建立关联。</p></div></div>
    <div class="import-layout">
      <div class="panel import-main">
        <div class="step"><span>01</span><div><h3>选择数据类型</h3><p>客户、产品和 SKU 按编号匹配；更新会经过当前业务规则校验，不会绕过主数据保护。</p></div></div>
        <div class="type-grid"><label v-for="(copy,key) in types" :key="key" :class="{ selected: entity === key }"><input v-model="entity" type="radio" :value="key" @change="changeEntity" /><FileSpreadsheet :size="20" /><strong>{{ copy[0] }}</strong><small>{{ copy[1] }}</small></label></div>
        <div class="step"><span>02</span><div><h3>准备并上传 CSV</h3><p>文件请保存为 UTF-8 编码，第一行字段名保持模板原样。</p></div></div>
        <button class="template-btn" @click="downloadTemplate"><Download :size="16" /><span><strong>下载 {{ types[entity][0] }} CSV 模板</strong><small>{{ (templates[entity] || []).join(' · ') }}</small></span></button>
        <label class="drop-zone"><input type="file" accept=".csv,text/csv" @change="choose" /><UploadCloud :size="34" /><strong>{{ file ? file.name : '点击选择 CSV 文件' }}</strong><small>{{ file ? `${(file.size/1024).toFixed(1)} KB` : '单次建议不超过 5,000 行' }}</small></label>
        <button class="btn btn-primary upload-btn" :disabled="previewing || executing || !file" @click="preview">{{ previewing ? '正在校验...' : '预览并校验' }}</button>
        <div v-if="error" class="result error-result"><AlertTriangle :size="18" />{{ error }}</div>
        <div v-if="result" class="result" :class="result.completed || !result.errors.length ? 'success-result' : 'error-result'"><component :is="result.completed || !result.errors.length ? CheckCircle2 : AlertTriangle" :size="20" /><div>
          <strong v-if="result.completed">导入成功：共 {{ result.total }} 行，新增 {{ result.created }}，更新 {{ result.updated }}</strong>
          <strong v-else>共 {{ result.total }} 行，将新增 {{ result.created }}，将更新 {{ result.updated }}，错误 {{ result.errors.length }}</strong>
          <p v-if="result.errors.length">校验未通过，不会写入任何数据。</p>
          <ul v-if="result.errors.length"><li v-for="e in result.errors.slice(0,20)" :key="e.row">第 {{ e.row }} 行：{{ e.message }}</li></ul>
          <button v-if="result.errors.length" class="inline-action" @click="downloadFailures">下载失败清单 CSV</button>
          <button v-else-if="!result.completed" class="btn btn-primary execute-btn" :disabled="executing" @click="execute">{{ executing ? '正在执行...' : '确认执行导入' }}</button>
        </div></div>
      </div>
      <aside class="panel guide"><h3>导入规则</h3><ol><li v-for="(copy,key,index) in types" :key="key"><span>{{ index+1 }}</span><div><strong>{{ copy[0] }}</strong><small>{{ copy[1] }}</small></div></li></ol><div class="tip"><strong>关联与历史安全</strong><p>客户、产品和 SKU 按编号匹配，修改仍受序列化器及业务完整性规则校验。财务流水只新增；重复流水号会报错，绝不覆盖原记录。</p><p>正式订单导入暂未开放，请通过订单业务流程创建；避免绕过报价、库存预留和收款计划。</p></div></aside>
    </div>
  </div>
</template>

<style scoped>
.import-layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:16px}.import-main,.guide{min-width:0}.import-main{padding:25px}.step{display:flex;gap:12px;margin-bottom:15px;align-items:start}.step>span{background:#123c36;color:white;border-radius:7px;padding:5px 7px;font-size:var(--text-caption)}.step h3,.step p{margin:0}.step h3{font-size:var(--text-section)}.step p{font-size:var(--text-caption);color:#81908b;margin-top:4px}.type-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:28px}.type-grid label{min-width:0;border:1px solid #e0e6e2;border-radius:9px;padding:12px;cursor:pointer;color:#687771}.type-grid label.selected{border-color:#3c7468;background:#edf6f2;color:#17483e;box-shadow:0 0 0 2px #dbece6}.type-grid input{display:none}.type-grid strong,.type-grid small{display:block}.type-grid strong{font-size:var(--text-body);margin-top:8px}.type-grid small{font-size:var(--text-caption);color:#89948f;margin-top:3px}.template-btn{width:100%;min-width:0;border:1px solid #dce4df;background:#f8faf8;padding:11px;border-radius:9px;display:flex;align-items:center;gap:10px;text-align:left;color:#38574e}.template-btn strong,.template-btn small{display:block}.template-btn strong{font-size:var(--text-body)}.template-btn small{font-size:var(--text-caption);color:#87948f;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:650px}.drop-zone{height:150px;border:1.5px dashed #a9bdb6;background:#fbfcfb;border-radius:11px;margin-top:12px;display:flex;flex-direction:column;justify-content:center;align-items:center;color:#527168;cursor:pointer}.drop-zone input{display:none}.drop-zone strong{font-size:var(--text-body);margin-top:7px}.drop-zone small{font-size:var(--text-caption);color:#929e99;margin-top:4px}.upload-btn{width:100%;margin-top:12px}.upload-btn:disabled{opacity:.5}.guide{padding:22px;height:max-content}.guide h3{margin:0 0 17px;font-size:var(--text-section)}.guide ol{list-style:none;padding:0;margin:0}.guide li{display:flex;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid #edf0ee}.guide li>span{width:23px;height:23px;border-radius:50%;background:#e6efeb;color:#285b4e;display:grid;place-items:center;font-size:var(--text-caption)}.guide li strong,.guide li small{display:block}.guide li strong{font-size:var(--text-caption)}.guide li small{font-size:var(--text-caption);color:#8a9691;margin-top:2px}.tip{margin-top:20px;background:#fff6e9;border:1px solid #f0dfc6;border-radius:9px;padding:13px}.tip strong{font-size:var(--text-caption);color:#8c5a29}.tip p{font-size:var(--text-caption);line-height:1.7;color:#826f5c;margin:5px 0 0}.tip code{background:#f8e7d0;padding:1px 3px}.result{margin-top:12px;border-radius:8px;padding:11px;display:flex;gap:8px;font-size:var(--text-caption)}.error-result{background:#fff0f0;color:#a84a4a}.success-result{background:#eaf6f0;color:#276850}.result strong{font-size:var(--text-body)}.result p{margin:5px 0}.result ul{margin:5px 0 0;padding-left:16px}@media(max-width:1000px){.import-layout{grid-template-columns:minmax(0,1fr)}.type-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:550px){.type-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.import-main{padding:16px}}
.template-btn>span{min-width:0;flex:1}
</style>
