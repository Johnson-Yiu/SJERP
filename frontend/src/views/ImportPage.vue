<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { UploadCloud, Download, FileSpreadsheet, CheckCircle2, AlertTriangle } from 'lucide-vue-next'
import { api } from '../api'
import { confirmDialog } from '../dialogs'
import { useAccessControl } from '../accessControl'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'

const entity = ref('customers'), file = ref(null), fileInput = ref(null), templates = ref({}), previewing = ref(false), confirming = ref(false), executing = ref(false), result = ref(null), error = ref('')
const templateLoading = ref(false), templateError = ref(''), phase = ref('idle'), errorPage = ref(1)
let version = 0, alive = true, retryOfBatchId = null
const { can } = useAccessControl()
const mayImport = computed(() => can('imports', 'import'))
const busy = computed(() => previewing.value || confirming.value || executing.value)
useUnsavedChangesGuard({ data: () => null, enabled: () => false, busy: () => busy.value })
const types = { customers: ['客户', '按客户编号匹配'], products: ['产品', '分类须预先建立'], skus: ['SKU', '按 SKU 与产品编号匹配'], transactions: ['财务流水', '只新增，不覆盖'] }
const destinations = { customers: '/customers', products: '/products', skus: '/skus', transactions: '/transactions' }
const headers = computed(() => Array.isArray(templates.value[entity.value]) ? templates.value[entity.value] : [])
const canExecute = computed(() => mayImport.value && phase.value === 'ready' && Boolean(result.value?.preview_token) && !result.value?.errors?.length)
const errors = computed(() => result.value?.errors || [])
function errorCopy(message) { return message === 'Product matching query does not exist.' ? '找不到所引用的产品，请核对 product_code。' : message }
const visibleErrors = computed(() => errors.value.slice((errorPage.value - 1) * 20, errorPage.value * 20))
const statusCopy = computed(() => ({ idle: '尚未选择文件', selected: '文件已选择，尚未校验', previewing: '正在上传并校验，尚未写入', invalid: '校验未通过，尚未写入', ready: '校验通过，尚未写入', confirming: '等待确认正式写入', executing: '正在执行导入，请勿离开', completed: '导入完成，已写入数据库', 'preview-error': '预览失败，请检查后重试', 'execute-error': '未确认导入完成，请先核对记录' }[phase.value]))
onMounted(loadTemplates)
onBeforeUnmount(() => { alive = false; version++ })
async function loadTemplates() {
  if (templateLoading.value) return
  templateLoading.value = true; templateError.value = ''
  try { const response = await api.get('/import/templates/'); if (alive) templates.value = response.data }
  catch (e) { if (alive) templateError.value = e.message }
  finally { if (alive) templateLoading.value = false }
}
function invalidatePreview() { version++; result.value = null; error.value = ''; errorPage.value = 1; phase.value = file.value ? 'selected' : 'idle' }
function choose(e) { if (busy.value) return; retryOfBatchId = null; file.value = e.target.files[0] || null; invalidatePreview() }
watch(entity, () => { retryOfBatchId = null; file.value = null; if (fileInput.value) fileInput.value.value = ''; invalidatePreview() }, { flush: 'sync' })
function downloadCsv(text, filename) {
  const url = URL.createObjectURL(new Blob(['\ufeff' + text], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
function downloadTemplate() {
  if (templateLoading.value || !headers.value.length) return
  downloadCsv(headers.value.join(',') + '\r\n', `${entity.value}_template.csv`)
}
async function preview() {
  if (busy.value) return
  if (!mayImport.value) return error.value = '当前账号没有数据导入权限。'
  if (!file.value) return error.value = '请先选择 CSV 文件。'
  const request = ++version, selectedEntity = entity.value, selectedFile = file.value
  previewing.value = true; error.value = ''; result.value = null; errorPage.value = 1; phase.value = 'previewing'
  const data = new FormData(); data.append('entity', selectedEntity); data.append('file', selectedFile)
  if (retryOfBatchId) data.append('retry_of_batch_id', retryOfBatchId)
  try {
    const response = (await api.post('/import/csv/preview/', data)).data
    if (!alive || request !== version) return
    if (!Array.isArray(response.errors) || ![response.total, response.created, response.updated].every(n => Number.isInteger(n) && n >= 0) || response.total < 1 || response.created + response.updated > response.total) throw new Error('预览结果不完整，请重新预览。')
    result.value = response
    phase.value = response.errors?.length ? 'invalid' : response.preview_token ? 'ready' : 'preview-error'
    if (phase.value === 'preview-error') error.value = '未取得有效预览凭证，请重新预览。'
  } catch (e) { if (alive && request === version) { error.value = e.message; phase.value = 'preview-error' } }
  finally { if (alive) previewing.value = false }
}
function downloadFailures() {
  if (!errors.value.length) return
  downloadCsv('row,key,message\r\n' + errors.value.map(item => [item.row, item.key || '', item.message].map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\r\n'), `${entity.value}_import_failures.csv`)
}
async function execute() {
  if (busy.value || !canExecute.value) return
  const request = version, selectedEntity = entity.value, selectedFile = file.value, previewResult = result.value
  confirming.value = true; phase.value = 'confirming'
  try {
    const approved = await confirmDialog({ title: '确认执行导入', message: `将正式写入 ${previewResult.total} 行：新增 ${previewResult.created}，更新 ${previewResult.updated}。更新可能覆盖原有字段，请确认已核对文件。`, confirmText: '确认导入' })
    if (!alive || request !== version) return
    if (!approved || !mayImport.value) { phase.value = 'ready'; return }
    executing.value = true; phase.value = 'executing'; error.value = ''
    const data = new FormData(); data.append('entity', selectedEntity); data.append('file', selectedFile); data.append('preview_token', previewResult.preview_token)
    const response = (await api.post('/import/csv/execute/', data)).data
    if (!alive || request !== version) return
    if (![response.total, response.created, response.updated].every(n => Number.isInteger(n) && n >= 0) || response.total !== previewResult.total || response.created + response.updated !== response.total || response.errors?.length) throw new Error('返回结果不完整，请核对业务记录后重新预览。')
    result.value = { ...response, errors: [], completed: true }; phase.value = 'completed'; retryOfBatchId = null
  } catch (e) {
    if (alive && request === version) {
      const batchId = e.data?.import_batch_id || e.response?.data?.import_batch_id
      if (batchId) retryOfBatchId = String(batchId)
      error.value = `${e.message} 未确认导入完成，请核对业务记录后重新预览，不要直接重复执行。`; result.value = null; phase.value = 'execute-error'
    }
  } finally { if (alive) { confirming.value = false; executing.value = false } }
}
</script>

<template>
  <div>
    <div class="page-head"><div><h2>数据导入</h2><p>先校验 CSV，再确认写入；预览不会保存业务数据。</p></div><RouterLink class="history-takeover-link" to="/history-takeover">受控历史资料承接</RouterLink></div>
    <div v-if="!mayImport" class="result error-result" role="status"><AlertTriangle :size="18" />当前账号仅可查看导入说明，不能预览或执行导入。</div>
    <div class="import-layout">
      <div class="panel import-main">
        <div class="step"><span>01</span><div><h3>选择数据类型</h3><p>客户、产品和 SKU 按编号匹配；更新会经过当前业务规则校验，不会绕过主数据保护。</p></div></div>
        <div class="type-grid"><label v-for="(copy,key) in types" :key="key" :class="{ selected: entity === key }"><input v-model="entity" type="radio" :value="key" :disabled="busy || !mayImport" /><FileSpreadsheet :size="20" /><strong>{{ copy[0] }}</strong><small>{{ copy[1] }}</small></label></div>
        <div class="step"><span>02</span><div><h3>准备并上传 CSV</h3><p>文件须为 UTF-8（支持 BOM），最多 5,000 条记录。选择文件后仍须预览校验，第一行保留模板字段名。</p></div></div>
        <button class="template-btn" :disabled="templateLoading || !headers.length" @click="downloadTemplate"><Download :size="16" /><span><strong>下载 {{ types[entity][0] }} CSV 模板</strong><small>{{ headers.join(' · ') }}</small></span></button>
        <p v-if="templateLoading" role="status">正在加载模板字段…</p><p v-else-if="templateError || !headers.length" role="alert">{{ templateError || '模板字段不可用' }} <button class="inline-action" @click="loadTemplates">重新加载模板</button></p><label class="drop-zone" :class="{ disabled: !mayImport }"><input type="file" accept=".csv,text/csv" ref="fileInput" :disabled="!mayImport || busy" @change="choose" /><UploadCloud :size="34" /><strong>{{ file ? file.name : '点击选择 CSV 文件' }}</strong><small>{{ file ? `${(file.size/1024).toFixed(1)} KB` : '单次建议不超过 5,000 行' }}</small></label>
        <button class="btn btn-primary upload-btn" :disabled="!mayImport || busy || !file" @click="preview">{{ previewing ? '正在校验...' : '预览并校验' }}</button>
        <p class="stage" role="status" aria-live="polite">{{ statusCopy }}</p><div v-if="error" class="result error-result" role="alert"><AlertTriangle :size="18" />{{ error }}</div>
        <div v-if="result" class="result" :class="result.completed || !result.errors.length ? 'success-result' : 'error-result'"><component :is="result.completed || !result.errors.length ? CheckCircle2 : AlertTriangle" :size="20" /><div>
          <strong v-if="result.completed">导入成功：共 {{ result.total }} 行，新增 {{ result.created }}，更新 {{ result.updated }}</strong>
          <strong v-else-if="!busy">共 {{ result.total }} 行，将新增 {{ result.created }}，将更新 {{ result.updated }}，错误 {{ result.errors.length }}</strong>
          <p v-if="result.errors.length">校验未通过，不会写入任何数据。</p>
          <div v-if="errors.length" class="error-table"><p>记录行号从表头第 1 行开始计数；字段内换行不另计记录。</p><table><thead><tr><th>记录行号</th><th>业务编号</th><th>错误原因</th></tr></thead><tbody><tr v-for="(e,index) in visibleErrors" :key="index"><td>{{ e.row }}</td><td>{{ e.key || '—' }}</td><td>{{ errorCopy(e.message) }}</td></tr></tbody></table><div v-if="errors.length > 20" class="error-pages"><button :disabled="errorPage === 1" @click="errorPage--">上一页</button><span>{{ errorPage }} / {{ Math.ceil(errors.length / 20) }}</span><button :disabled="errorPage * 20 >= errors.length" @click="errorPage++">下一页</button></div></div>
          <button v-if="result.errors.length" class="inline-action" @click="downloadFailures">下载失败清单 CSV</button>
          <button v-else-if="!result.completed && mayImport" class="btn btn-primary execute-btn" :disabled="busy || !canExecute" @click="execute">{{ executing ? '正在执行...' : confirming ? '等待确认...' : '确认执行导入' }}</button>
        <RouterLink v-if="result.completed && can(entity, 'view')" class="btn" :to="destinations[entity]">前往{{ types[entity][0] }}</RouterLink></div></div>
      </div>
      <aside class="panel guide"><h3>导入规则</h3><ol><li v-for="(copy,key,index) in types" :key="key"><span>{{ index+1 }}</span><div><strong>{{ copy[0] }}</strong><small>{{ copy[1] }}</small></div></li></ol><div class="tip"><strong>关联与历史安全</strong><p>客户、产品和 SKU 按编号匹配。更新时空白字段可能清除原有内容，请先备份并核对。财务流水只新增；重复流水号会报错，绝不覆盖原记录。</p><p>正式订单导入暂未开放，请通过订单业务流程创建；避免绕过报价、库存预留和收款计划。</p></div></aside>
    </div>
  </div>
</template>

<style scoped>
.import-layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:16px}.import-main,.guide{min-width:0}.import-main{padding:25px}.step{display:flex;gap:12px;margin-bottom:15px;align-items:start}.step>span{background:#123c36;color:white;border-radius:7px;padding:5px 7px;font-size:var(--text-caption)}.step h3,.step p{margin:0}.step h3{font-size:var(--text-section)}.step p{font-size:var(--text-caption);color:#81908b;margin-top:4px}.type-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:28px}.type-grid label{min-width:0;border:1px solid #e0e6e2;border-radius:9px;padding:12px;cursor:pointer;color:#687771}.type-grid label.selected{border-color:#3c7468;background:#edf6f2;color:#17483e;box-shadow:0 0 0 2px #dbece6}.type-grid input{display:none}.type-grid strong,.type-grid small{display:block}.type-grid strong{font-size:var(--text-body);margin-top:8px}.type-grid small{font-size:var(--text-caption);color:#89948f;margin-top:3px}.template-btn{width:100%;min-width:0;border:1px solid #dce4df;background:#f8faf8;padding:11px;border-radius:9px;display:flex;align-items:center;gap:10px;text-align:left;color:#38574e}.template-btn strong,.template-btn small{display:block}.template-btn strong{font-size:var(--text-body)}.template-btn small{font-size:var(--text-caption);color:#87948f;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:650px}.drop-zone{height:150px;border:1.5px dashed #a9bdb6;background:#fbfcfb;border-radius:11px;margin-top:12px;display:flex;flex-direction:column;justify-content:center;align-items:center;color:#527168;cursor:pointer}.drop-zone input{display:none}.drop-zone strong{font-size:var(--text-body);margin-top:7px}.drop-zone small{font-size:var(--text-caption);color:#929e99;margin-top:4px}.upload-btn{width:100%;margin-top:12px}.upload-btn:disabled{opacity:.5}.guide{padding:22px;height:max-content}.guide h3{margin:0 0 17px;font-size:var(--text-section)}.guide ol{list-style:none;padding:0;margin:0}.guide li{display:flex;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid #edf0ee}.guide li>span{width:23px;height:23px;border-radius:50%;background:#e6efeb;color:#285b4e;display:grid;place-items:center;font-size:var(--text-caption)}.guide li strong,.guide li small{display:block}.guide li strong{font-size:var(--text-caption)}.guide li small{font-size:var(--text-caption);color:#8a9691;margin-top:2px}.tip{margin-top:20px;background:#fff6e9;border:1px solid #f0dfc6;border-radius:9px;padding:13px}.tip strong{font-size:var(--text-caption);color:#8c5a29}.tip p{font-size:var(--text-caption);line-height:1.7;color:#826f5c;margin:5px 0 0}.tip code{background:#f8e7d0;padding:1px 3px}.result{margin-top:12px;border-radius:8px;padding:11px;display:flex;gap:8px;font-size:var(--text-caption)}.error-result{background:#fff0f0;color:#a84a4a}.success-result{background:#eaf6f0;color:#276850}.result strong{font-size:var(--text-body)}.result p{margin:5px 0}.result ul{margin:5px 0 0;padding-left:16px}@media(max-width:1200px){.import-layout{grid-template-columns:minmax(0,1fr)}.type-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:550px){.type-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.import-main{padding:16px}}
.history-takeover-link{display:inline-flex;align-items:center;padding:8px 11px;border:1px solid #b9d1c3;border-radius:8px;background:#f3f8f4;color:#245c49;font-weight:700;text-decoration:none;white-space:nowrap}.history-takeover-link:hover{background:#e9f3ec}
.stage{padding:12px;background:#f0f4f2;border-radius:8px;font-weight:600}.drop-zone{padding:12px;height:auto;min-height:150px;text-align:center;overflow-wrap:anywhere}.result>div{min-width:0;flex:1}.error-table{overflow-x:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}td:last-child{min-width:180px}.error-table th:first-child{min-width:76px;white-space:nowrap}.error-table th:nth-child(2){min-width:90px}.inline-action{border:1px solid currentColor;background:white;color:inherit;padding:6px 10px;border-radius:6px;cursor:pointer;margin-top:8px}.error-pages{display:flex;gap:12px;align-items:center;margin-top:8px}button:disabled{cursor:not-allowed;opacity:.55}.type-grid input{display:inline-block;position:absolute;opacity:0}.type-grid label:focus-within{outline:2px solid #397b69}.template-btn small{white-space:normal;overflow-wrap:anywhere}.template-btn>span{min-width:0;flex:1}
</style>
