<script setup>
import { downloadBlob } from '../utils/downloadBlob.js'
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api } = useWorkspaceApi()
import { computed, inject, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { UploadCloud, Download, FileSpreadsheet, CheckCircle2, AlertTriangle } from 'lucide-vue-next'

import { confirmDialog } from '../dialogs'
import { useAccessControl } from '../accessControl'
import { useUnsavedChangesGuard } from '../composables/useUnsavedChangesGuard'
import { useWorkspaceNavigation, workspaceManagerKey } from '../composables/useWorkspaceNavigation'

const entity = ref('customers'), file = ref(null), fileInput = ref(null), templates = ref({}), previewing = ref(false), confirming = ref(false), executing = ref(false), result = ref(null), error = ref('')
const templateLoading = ref(false), templateError = ref(''), phase = ref('idle'), errorPage = ref(1)
const importMode = ref('csv'), orderFile = ref(null), orderFileInput = ref(null), orderTemplateLoading = ref(false)
const orderPreviewing = ref(false), orderConfirming = ref(false), orderExecuting = ref(false), orderResult = ref(null), orderError = ref(''), orderPhase = ref('idle')
let version = 0, orderVersion = 0, alive = true, retryOfBatchId = null
const { storageKey } = useWorkspaceNavigation()
const workspaceManager = inject(workspaceManagerKey, null)
const { can, accessState } = useAccessControl()
const recoveryKey = computed(() => {
  if (workspaceManager?.identity) return storageKey('sales-order-import-pending-v1', { accountOnly: true })
  const account = accessState.operator?.id || accessState.operator?.username || 'signed-out'
  return `sales-order-import-pending-v1:${account}`
})
const fileIdentity = value => value ? [value.name, value.size, value.lastModified].join(':') : ''
function pendingOrders() {
  try { const saved = JSON.parse(sessionStorage.getItem(recoveryKey.value) || '[]'); return Array.isArray(saved) ? saved : saved ? [saved] : [] } catch { return [] }
}
function pendingOrder() { return pendingOrders().find(row => row.file === fileIdentity(orderFile.value)) }
function rememberOrder(preview, selected) {
  const pending = pendingOrders(), existing = pending.find(row => row.file === fileIdentity(selected))
  if (existing && existing.preview_token !== preview.preview_token) throw new Error('该文件已有结果待核对的提交，请重新选择原文件恢复原批次。')
  if (!existing) pending.push({ file: fileIdentity(selected), preview_token: preview.preview_token, total_rows: preview.total_rows, total_orders: preview.total_orders, valid_orders: preview.valid_orders, invalid_orders: preview.invalid_orders })
  sessionStorage.setItem(recoveryKey.value, JSON.stringify(pending))
}
function forgetOrder(token) {
  const remaining = pendingOrders().filter(row => row.preview_token !== token)
  if (remaining.length) sessionStorage.setItem(recoveryKey.value, JSON.stringify(remaining))
  else sessionStorage.removeItem(recoveryKey.value)
}
const mayImport = computed(() => can('imports', 'import'))
const busy = computed(() => previewing.value || confirming.value || executing.value)
const types = { customers: ['客户', '按客户编号匹配'], products: ['产品', '分类须预先建立'], skus: ['SKU', '按 SKU 与产品编号匹配'], transactions: ['财务流水', '只新增，不覆盖'] }
const destinations = { customers: '/customers', products: '/products', skus: '/skus', transactions: '/transactions' }
const headers = computed(() => Array.isArray(templates.value[entity.value]) ? templates.value[entity.value] : [])
const canExecute = computed(() => mayImport.value && phase.value === 'ready' && Boolean(result.value?.preview_token) && !result.value?.errors?.length)
const canExecuteOrders = computed(() => mayImport.value && orderPhase.value === 'ready' && Boolean(orderResult.value?.preview_token) && Number(orderResult.value?.valid_orders) > 0)
const orderBusy = computed(() => orderPreviewing.value || orderConfirming.value || orderExecuting.value)
useUnsavedChangesGuard({ data: () => null, enabled: () => false, busy: () => busy.value || orderBusy.value })
const orderStatusCopy = computed(() => ({ idle: '尚未选择文件', selected: '文件已选择，尚未校验', previewing: '正在上传并校验，未写入业务数据', invalid: '没有可导入的完整订单', ready: '校验完成，可确认创建草稿', confirming: '等待确认创建销售草稿', executing: '正在创建销售草稿，请勿离开', completed: '导入结果已保存', 'preview-error': '预览失败，请检查文件后重试', 'execute-error': '提交结果待核对，请先查看订单管理' }[orderPhase.value]))
const errors = computed(() => result.value?.errors || [])
const orderErrors = computed(() => orderResult.value?.errors || [])
const fieldLabels = {
  customers: { code: '客户编号', name: '客户名称', country: '国家/地区', source: '客户来源', website: '网站', address: '地址', notes: '备注' },
  products: { code: '产品编号', name: '产品名称', sales_model_prefix: '销售型号前缀', category: '产品主分类', description: '产品描述', status: '状态' },
  skus: { sku: 'SKU', product_code: '产品编号', specification: '规格', unit: '基础单位', cost_price: '成本价', default_price: '默认售价', currency: '币种' },
  transactions: { transaction_no: '流水号', transaction_date: '发生日期', direction: '收支方向', category: '收支分类', amount: '金额', currency: '币种', exchange_rate: '对人民币汇率', customer_code: '客户编号', order_no: '销售订单号', payment_method: '收付方式', reference: '凭证/参考号', notes: '备注' },
}
function fieldLabel(key) { return fieldLabels[entity.value]?.[key] || key }
function errorCopy(message) {
  const value = String(message || '')
  if (value === 'Product matching query does not exist.') return '未找到对应产品。请核对“产品编号”列，并确认该产品已在系统中建立。'
  if (value.includes('product_code')) return value.replaceAll('product_code', '产品编号')
  if (value.includes('customer_code')) return value.replaceAll('customer_code', '客户编号')
  if (value.includes('sku_code')) return value.replaceAll('sku_code', 'SKU')
  return value
}
const visibleErrors = computed(() => errors.value.slice((errorPage.value - 1) * 20, errorPage.value * 20))
const statusCopy = computed(() => ({ idle: '尚未选择文件', selected: '文件已选择，尚未校验', previewing: '正在上传并校验，尚未写入', invalid: '校验未通过，尚未写入', ready: '校验通过，尚未写入', confirming: '等待确认正式写入', executing: '正在执行导入，请勿离开', completed: '导入完成，已写入数据库', 'preview-error': '预览失败，请检查后重试', 'execute-error': '未确认导入完成，请先核对记录' }[phase.value]))
onMounted(loadTemplates)
onBeforeUnmount(() => { alive = false; version++; orderVersion++ })
watch(() => workspaceManager?.identity?.value, () => {
  orderVersion++; orderResult.value = null; orderError.value = ''; orderPreviewing.value = false
  orderConfirming.value = false; orderExecuting.value = false; orderPhase.value = orderFile.value ? 'selected' : 'idle'
}, { flush: 'sync' })
watch(recoveryKey, () => {
  orderVersion++; orderResult.value = null; orderError.value = ''; orderPreviewing.value = false
  orderConfirming.value = false; orderExecuting.value = false; orderPhase.value = orderFile.value ? 'selected' : 'idle'
}, { flush: 'sync' })
watch(mayImport, allowed => {
  if (allowed) return
  version++; orderVersion++
  result.value = null; orderResult.value = null
  previewing.value = false; confirming.value = false; executing.value = false
  orderPreviewing.value = false; orderConfirming.value = false; orderExecuting.value = false
  phase.value = file.value ? 'selected' : 'idle'; orderPhase.value = orderFile.value ? 'selected' : 'idle'
}, { flush: 'sync' })
async function loadTemplates() {
  if (templateLoading.value) return
  templateLoading.value = true; templateError.value = ''
  try { const response = await api.get('/import/templates/'); if (alive) templates.value = response.data }
  catch (e) { if (alive) templateError.value = e.message }
  finally { if (alive) templateLoading.value = false }
}
function invalidatePreview() { version++; result.value = null; error.value = ''; errorPage.value = 1; phase.value = file.value ? 'selected' : 'idle' }
function choose(e) { if (confirming.value || executing.value) return; retryOfBatchId = null; file.value = e.target.files[0] || null; previewing.value = false; invalidatePreview() }
watch(entity, () => { retryOfBatchId = null; file.value = null; if (fileInput.value) fileInput.value.value = ''; invalidatePreview() }, { flush: 'sync' })
function selectOrderFile(event) {
  if (orderConfirming.value || orderExecuting.value) return
  orderVersion++
  orderPreviewing.value = false
  orderFile.value = event.target.files[0] || null
  orderResult.value = null; orderError.value = ''; orderPhase.value = orderFile.value ? 'selected' : 'idle'
  const pending = pendingOrder()
  if (pending?.file === fileIdentity(orderFile.value)) {
    orderResult.value = { ...pending, orders: [], errors: [] }; orderPhase.value = 'ready'
    orderError.value = '已恢复待核对导入批次。再次确认将使用原文件和预览凭证查询结果，不会创建新订单。'
  }
}
function clearOrderPreview() {
  orderVersion++
  orderResult.value = null; orderError.value = ''; orderPhase.value = orderFile.value ? 'selected' : 'idle'
}
function downloadCsv(text, filename) {
  downloadBlob(new Blob(['\ufeff' + text], { type: 'text/csv;charset=utf-8' }), filename)
}
function downloadTemplate() {
  if (templateLoading.value || !headers.value.length) return
  downloadCsv(headers.value.join(',') + '\r\n', `${entity.value}_template.csv`)
}
async function downloadOrderTemplate() {
  if (orderTemplateLoading.value || !mayImport.value) return
  orderTemplateLoading.value = true; orderError.value = ''
  try {
    const response = await api.get('/import/orders/template/', { responseType: 'blob' })
    if (alive) downloadBlob(response.data, 'sales-order-import-template.xlsx')
  } catch (e) { if (alive) orderError.value = e.message }
  finally { if (alive) orderTemplateLoading.value = false }
}
async function previewOrders() {
  if (orderConfirming.value || orderExecuting.value) return
  if (pendingOrder()) { orderError.value = '存在结果待核对的提交，请选择原文件，再次确认原批次后继续。'; return }
  if (!mayImport.value) { orderError.value = '当前账号没有销售订单导入权限。'; return }
  if (!orderFile.value) { orderError.value = '请先选择销售订单 XLSX 文件。'; return }
  const request = ++orderVersion, selectedFile = orderFile.value
  orderPreviewing.value = true; orderError.value = ''; orderResult.value = null; orderPhase.value = 'previewing'
  const data = new FormData(); data.append('file', selectedFile)
  try {
    const response = (await api.post('/import/orders/preview/', data)).data
    if (!alive || request !== orderVersion || selectedFile !== orderFile.value) return
    if (!Array.isArray(response.errors) || !Array.isArray(response.orders) || ![response.total_rows, response.total_orders, response.valid_orders, response.invalid_orders].every(n => Number.isInteger(n) && n >= 0) || response.valid_orders + response.invalid_orders !== response.total_orders || response.orders.length !== response.total_orders || (response.valid_orders > 0 && !response.preview_token)) throw new Error('预览结果不完整，请重新上传并校验。')
    orderResult.value = response
    orderPhase.value = response.valid_orders > 0 ? 'ready' : 'invalid'
  } catch (e) { if (alive && request === orderVersion) { orderError.value = e.message; orderPhase.value = 'preview-error' } }
  finally { if (alive && request === orderVersion) orderPreviewing.value = false }
}
function downloadOrderFailures() {
  if (!orderErrors.value.length) return
  const cell = value => {
    const raw = String(value ?? '')
    const safe = /^[=+\-@\t\r]/.test(raw) ? `'${raw}` : raw
    return `"${safe.replaceAll('"', '""')}"`
  }
  const csv = ['表格行号,来源订单编号,错误原因', ...orderErrors.value.map(item => [item.row, item.key || '', item.message].map(cell).join(','))].join('\r\n')
  downloadCsv(csv, 'sales-order-import-errors.csv')
}
function downloadOrderResults() {
  if (!orderResult.value) return
  const cell = value => {
    const raw = String(value ?? '')
    const safe = /^[=+\-@\t\r]/.test(raw) ? `'${raw}` : raw
    return `"${safe.replaceAll('"', '""')}"`
  }
  const rows = [['记录类型', '来源订单编号', '销售订单编号', '客户名称', '客户编号', '订单明细数', '币种', '金额', '处理结果', '错误原因', '原表格行号']]
  for (const item of orderResult.value.orders || []) {
    const status = orderResult.value.completed
      ? (item.status === 'draft' ? '已创建草稿' : '待核实')
      : item.valid ? '可导入' : '待修正'
    rows.push(['订单', item.source_order_no, item.order_no, item.customer_name, item.customer_code, item.line_count, item.currency, item.total_amount, status, '', ''])
  }
  for (const item of orderErrors.value) {
    rows.push(['错误', item.key, '', '', '', '', '', '', '待修正', item.message, item.row])
  }
  downloadCsv(rows.map(row => row.map(cell).join(',')).join('\r\n'), 'sales-order-import-results.csv')
}
async function executeOrders() {
  if (orderBusy.value || !canExecuteOrders.value) return
  const previewResult = orderResult.value, selectedFile = orderFile.value, request = orderVersion
  const valid = () => alive && request === orderVersion && selectedFile === orderFile.value && previewResult === orderResult.value
  orderConfirming.value = true; orderPhase.value = 'confirming'
  try {
    const invalidNote = previewResult.invalid_orders ? `另有 ${previewResult.invalid_orders} 张订单含错误，将整单跳过。` : ''
    const approved = await confirmDialog({ title: '确认导入销售草稿', message: `将创建 ${previewResult.valid_orders} 张销售订单草稿，共 ${previewResult.total_rows} 条明细。${invalidNote}导入不会确认订单、占库存、生成应收计划或登记发货。`, confirmText: '确认导入' })
    if (!valid()) return
    if (!approved || !mayImport.value) { orderPhase.value = 'ready'; return }
    rememberOrder(previewResult, selectedFile)
    if (!valid() || !mayImport.value) return
    orderExecuting.value = true; orderPhase.value = 'executing'; orderError.value = ''
    const data = new FormData(); data.append('file', selectedFile); data.append('preview_token', previewResult.preview_token)
    const response = (await api.post('/import/orders/execute/', data)).data
    if (!valid()) return
    if (!response.batch_id || !Array.isArray(response.errors) || !Array.isArray(response.orders) || ![response.total_rows, response.total_orders, response.created_orders, response.failed_orders].every(n => Number.isInteger(n) && n >= 0) || response.created_orders + response.failed_orders !== response.total_orders) throw new Error('返回结果不完整，请核对订单管理后重新预览。')
    forgetOrder(previewResult.preview_token)
    orderResult.value = { ...response, completed: true }; orderPhase.value = 'completed'
  } catch (e) {
    if (valid()) {
      if (e.data?.business_write_performed === false) {
        forgetOrder(previewResult.preview_token); orderResult.value = null; orderPhase.value = 'preview-error'; orderError.value = e.message
      } else {
        orderError.value = `${e.message} 提交结果待核对，请保留原文件和预览再次确认原批次；离开页面不代表回滚。`; orderPhase.value = 'ready'
      }
    }
  } finally { if (alive && request === orderVersion) { orderConfirming.value = false; orderExecuting.value = false } }
}
async function preview() {
  if (previewing.value || confirming.value || executing.value) return
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
  finally { if (alive && request === version) previewing.value = false }
}
function downloadFailures() {
  if (!errors.value.length) return
  downloadCsv('记录行号,业务编号,错误原因\r\n' + errors.value.map(item => [item.row, item.key || '', errorCopy(item.message)].map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\r\n'), `${entity.value}_import_failures.csv`)
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
    <div class="page-head"><div><h2>数据导入</h2><p>上传文件并预览校验；确认后再写入业务数据。</p></div><RouterLink class="history-takeover-link" to="/history-takeover">历史资料预检与承接</RouterLink></div>
    <div v-if="!mayImport" class="result error-result" role="status"><AlertTriangle :size="18" />当前账号仅可查看导入说明，不能预览或执行导入。</div>
    <div class="import-mode-tabs" role="tablist" aria-label="导入类型">
      <button type="button" role="tab" :aria-selected="importMode === 'csv'" :disabled="busy || orderBusy" @click="importMode = 'csv'">客户、产品与财务流水</button>
      <button type="button" role="tab" :aria-selected="importMode === 'orders'" :disabled="busy || orderBusy" @click="importMode = 'orders'">销售订单</button>
    </div>
    <div v-if="importMode === 'orders'" class="import-layout">
      <div class="panel import-main">
        <p v-if="pendingOrders().length" class="stage" role="status">有导入批次结果待核对：{{ pendingOrders().map(row => row.file.split(':')[0]).join('、') }}。请重新选择对应原文件，按原预览凭证查询批次结果；不会创建新订单。</p>
        <div class="step"><span>01</span><div><h3>下载销售订单模板</h3><p>一行填写一条 SKU 明细。同一来源订单编号的多行会合并为一张销售订单草稿。</p></div></div>
        <button class="template-btn" :disabled="orderTemplateLoading || !mayImport" @click="downloadOrderTemplate"><Download :size="16" /><span><strong>{{ orderTemplateLoading ? '正在准备模板…' : '下载销售订单 XLSX 模板' }}</strong><small>包含来源订单编号、客户编号、订单日期、币种、SKU、交易单位、数量和单价</small></span></button>
        <div class="step"><span>02</span><div><h3>上传并检查订单</h3><p>客户编号和 SKU 按系统编号匹配。每张订单的客户、日期、币种和汇率必须一致；预览不会写入业务数据，有明细错误时整单不导入。</p></div></div>
        <label class="drop-zone" :class="{ disabled: !mayImport || orderConfirming || orderExecuting }"><input ref="orderFileInput" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" :disabled="!mayImport || orderConfirming || orderExecuting" @change="selectOrderFile" /><UploadCloud :size="34" /><strong>{{ orderFile ? orderFile.name : '点击选择销售订单 XLSX 文件' }}</strong><small>{{ orderFile ? `${(orderFile.size/1024).toFixed(1)} KB` : '最多 5,000 条订单明细' }}{{ orderPreviewing ? ' · 可改选文件并重新校验' : '' }}</small></label>
        <button class="btn btn-primary upload-btn" :disabled="!mayImport || orderConfirming || orderExecuting || !orderFile" @click="previewOrders">{{ orderPreviewing ? '重新预览并校验' : '预览并校验' }}</button>
        <p class="stage" role="status" aria-live="polite">{{ orderStatusCopy }}</p>
        <div v-if="orderError && (!orderResult || orderResult.completed)" class="result error-result" role="alert"><AlertTriangle :size="18" />{{ orderError }}</div>
        <div v-if="orderResult" class="result" :class="orderResult.completed && orderResult.created_orders ? 'success-result' : orderResult.errors.length ? 'error-result' : 'success-result'"><component :is="orderResult.completed && orderResult.created_orders ? CheckCircle2 : orderResult.errors.length ? AlertTriangle : CheckCircle2" :size="20" /><div>
          <strong v-if="orderResult.completed">已创建 {{ orderResult.created_orders }} 张草稿，{{ orderResult.failed_orders }} 张未创建</strong>
          <strong v-else>共 {{ orderResult.total_rows }} 条明细、{{ orderResult.total_orders }} 张订单：{{ orderResult.valid_orders }} 张可导入，{{ orderResult.invalid_orders }} 张待修正</strong>
          <p v-if="orderResult.completed">导入结果已保存。所有创建的订单均为草稿，后续可在订单管理中按原流程确认。</p>
          <p v-else-if="orderResult.errors.length">仅创建校验通过的整单；含错误的订单会整单跳过。</p>
          <div v-if="orderResult.orders?.length" class="error-table order-result-table"><table><thead><tr><th>来源订单编号</th><th v-if="orderResult.completed">销售订单编号</th><th>客户（编号）</th><th>明细数</th><th>金额</th><th>状态</th></tr></thead><tbody><tr v-for="item in orderResult.orders" :key="item.source_order_no"><td>{{ item.source_order_no }}</td><td v-if="orderResult.completed">{{ item.order_no || '—' }}</td><td>{{ item.customer_name ? `${item.customer_name}（${item.customer_code}）` : item.customer_code }}</td><td>{{ item.line_count }}</td><td>{{ item.currency }} {{ item.total_amount }}</td><td>{{ orderResult.completed ? (item.status === 'draft' ? '草稿' : '待核实') : (item.valid ? '待导入' : '待修正') }}</td></tr></tbody></table></div>
          <div v-if="orderErrors.length" class="error-table"><p>表格行号按 Excel 中的实际行号显示。请按错误原因修正原文件后重新预览。</p><table><thead><tr><th>表格行号</th><th>来源订单编号</th><th>错误原因</th></tr></thead><tbody><tr v-for="(item,index) in orderErrors" :key="index"><td>{{ item.row }}</td><td>{{ item.key || '—' }}</td><td>{{ errorCopy(item.message) }}</td></tr></tbody></table></div>
          <button v-if="orderResult.orders?.length" class="inline-action" @click="downloadOrderResults">下载导入结果 CSV</button>
          <button v-if="orderErrors.length" class="inline-action" @click="downloadOrderFailures">下载错误清单 CSV</button>
          <p v-if="orderError && !orderResult.completed" class="stage" role="alert">{{ orderError }}</p>
          <button v-if="!orderResult.completed && orderResult.valid_orders > 0" class="btn btn-primary execute-btn" :disabled="orderBusy || !canExecuteOrders" @click="executeOrders">{{ orderExecuting ? '正在创建草稿…' : orderConfirming ? '等待确认…' : `确认导入 ${orderResult.valid_orders} 张草稿` }}</button>
          <RouterLink v-if="orderResult.completed && can('orders', 'view')" class="btn" to="/orders">前往订单管理</RouterLink>
        </div></div>
      </div>
      <aside class="panel guide"><h3>销售订单规则</h3><ol><li><span>1</span><div><strong>按编号匹配</strong><small>客户编号、SKU 和交易单位</small></div></li><li><span>2</span><div><strong>整单校验</strong><small>检查表头一致、金额和交易单位</small></div></li><li><span>3</span><div><strong>确认后建草稿</strong><small>使用订单管理中的原有流程确认</small></div></li></ol><div class="tip"><strong>旧订单请走历史流程</strong><p>已结清、已收款、已发货或需要接续的订单，请在历史资料承接页提交；系统会先预检，再进入申请审核。</p><RouterLink class="inline-action history-inline-link" to="/history-takeover">打开历史资料承接</RouterLink></div><div class="tip"><strong>导入范围</strong><p>不会确认订单、占库存、生成应收计划或登记发货。重复来源订单编号会拒绝导入，内容变更也不会覆盖已有订单。</p></div></aside>
    </div>
    <div v-else class="import-layout">
      <div class="panel import-main">
        <div class="step"><span>01</span><div><h3>选择数据类型</h3><p>客户、产品和 SKU 按编号匹配；更新会经过当前业务规则校验，不会绕过主数据保护。</p></div></div>
        <div class="type-grid"><label v-for="(copy,key) in types" :key="key" :class="{ selected: entity === key }"><input v-model="entity" type="radio" :value="key" :disabled="confirming || executing || !mayImport" /><FileSpreadsheet :size="20" /><strong>{{ copy[0] }}</strong><small>{{ copy[1] }}</small></label></div>
        <div class="step"><span>02</span><div><h3>准备并上传 CSV</h3><p>文件须为 UTF-8（支持 BOM），最多 5,000 条记录。选择文件后仍须预览校验，第一行保留模板字段名。</p></div></div>
        <button class="template-btn" :disabled="templateLoading || !headers.length" @click="downloadTemplate"><Download :size="16" /><span><strong>下载 {{ types[entity][0] }} CSV 模板</strong><small>{{ headers.map(fieldLabel).join(' · ') }}</small></span></button>
        <details v-if="headers.length" class="field-key-guide"><summary>查看模板字段对照</summary><p>模板首行保留系统字段名，以确保文件格式和校验兼容。</p><ul><li v-for="key in headers" :key="key"><strong>{{ fieldLabel(key) }}</strong><code>{{ key }}</code></li></ul></details>
        <p v-if="templateLoading" role="status">正在加载模板字段…</p><p v-else-if="templateError || !headers.length" role="alert">{{ templateError || '模板字段不可用' }} <button class="inline-action" @click="loadTemplates">重新加载模板</button></p><label class="drop-zone" :class="{ disabled: !mayImport || confirming || executing }"><input type="file" accept=".csv,text/csv" ref="fileInput" :disabled="!mayImport || confirming || executing" @change="choose" /><UploadCloud :size="34" /><strong>{{ file ? file.name : '点击选择 CSV 文件' }}</strong><small>{{ file ? `${(file.size/1024).toFixed(1)} KB` : '单次建议不超过 5,000 行' }}{{ previewing ? ' · 可改选文件并重新校验' : '' }}</small></label>
        <button class="btn btn-primary upload-btn" :disabled="!mayImport || previewing || confirming || executing || !file" @click="preview">{{ previewing ? '正在预览并校验' : '预览并校验' }}</button>
        <p class="stage" role="status" aria-live="polite">{{ statusCopy }}</p><div v-if="error" class="result error-result" role="alert"><AlertTriangle :size="18" />{{ error }}</div>
        <div v-if="result" class="result" :class="result.completed || !result.errors.length ? 'success-result' : 'error-result'"><component :is="result.completed || !result.errors.length ? CheckCircle2 : AlertTriangle" :size="20" /><div>
          <strong v-if="result.completed">导入成功：共 {{ result.total }} 行，新增 {{ result.created }}，更新 {{ result.updated }}</strong>
          <strong v-else-if="!busy">共 {{ result.total }} 行，将新增 {{ result.created }}，将更新 {{ result.updated }}，错误 {{ result.errors.length }}</strong>
          <p v-if="result.errors.length">校验未通过，不会写入任何数据。</p>
          <div v-if="errors.length" class="error-table"><p>记录行号从表头第 1 行开始计数；字段内换行不另计记录。请按业务编号和错误原因修正文件后重新预览。</p><table><thead><tr><th>记录行号</th><th>业务编号</th><th>错误原因</th></tr></thead><tbody><tr v-for="(e,index) in visibleErrors" :key="index"><td>{{ e.row }}</td><td>{{ e.key || '—' }}</td><td>{{ errorCopy(e.message) }}</td></tr></tbody></table><div v-if="errors.length > 20" class="error-pages"><button :disabled="errorPage === 1" @click="errorPage--">上一页</button><span>{{ errorPage }} / {{ Math.ceil(errors.length / 20) }}</span><button :disabled="errorPage * 20 >= errors.length" @click="errorPage++">下一页</button></div></div>
          <button v-if="result.errors.length" class="inline-action" @click="downloadFailures">下载失败清单 CSV</button>
          <button v-else-if="!result.completed && mayImport" class="btn btn-primary execute-btn" :disabled="busy || !canExecute" @click="execute">{{ executing ? '正在执行...' : confirming ? '等待确认...' : '确认执行导入' }}</button>
        <RouterLink v-if="result.completed && can(entity, 'view')" class="btn" :to="destinations[entity]">前往{{ types[entity][0] }}</RouterLink></div></div>
      </div>
      <aside class="panel guide"><h3>导入规则</h3><ol><li v-for="(copy,key,index) in types" :key="key"><span>{{ index+1 }}</span><div><strong>{{ copy[0] }}</strong><small>{{ copy[1] }}</small></div></li></ol><div class="tip"><strong>关联与历史安全</strong><p>客户、产品和 SKU 按编号匹配。更新时空白字段可能清除原有内容，请先备份并核对。财务流水只新增；重复流水号会报错，绝不覆盖原记录。</p><p>销售订单通过专用 XLSX 模板导入，按整单创建草稿。</p></div></aside>
    </div>
  </div>
</template>

<style scoped>
.import-layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:16px}.import-main,.guide{min-width:0}.import-main{padding:25px}.step{display:flex;gap:12px;margin-bottom:15px;align-items:start}.step>span{background:#123c36;color:white;border-radius:7px;padding:5px 7px;font-size:var(--text-caption)}.step h3,.step p{margin:0}.step h3{font-size:var(--text-section)}.step p{font-size:var(--text-caption);color:#81908b;margin-top:4px}.type-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:28px}.type-grid label{min-width:0;border:1px solid #e0e6e2;border-radius:9px;padding:12px;cursor:pointer;color:#687771}.type-grid label.selected{border-color:#3c7468;background:#edf6f2;color:#17483e;box-shadow:0 0 0 2px #dbece6}.type-grid input{display:none}.type-grid strong,.type-grid small{display:block}.type-grid strong{font-size:var(--text-body);margin-top:8px}.type-grid small{font-size:var(--text-caption);color:#89948f;margin-top:3px}.template-btn{width:100%;min-width:0;border:1px solid #dce4df;background:#f8faf8;padding:11px;border-radius:9px;display:flex;align-items:center;gap:10px;text-align:left;color:#38574e}.template-btn strong,.template-btn small{display:block}.template-btn strong{font-size:var(--text-body)}.template-btn small{font-size:var(--text-caption);color:#87948f;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:650px}.drop-zone{height:150px;border:1.5px dashed #a9bdb6;background:#fbfcfb;border-radius:11px;margin-top:12px;display:flex;flex-direction:column;justify-content:center;align-items:center;color:#527168;cursor:pointer}.drop-zone input{display:none}.drop-zone strong{font-size:var(--text-body);margin-top:7px}.drop-zone small{font-size:var(--text-caption);color:#929e99;margin-top:4px}.upload-btn{width:100%;margin-top:12px}.upload-btn:disabled{opacity:.5}.guide{padding:22px;height:max-content}.guide h3{margin:0 0 17px;font-size:var(--text-section)}.guide ol{list-style:none;padding:0;margin:0}.guide li{display:flex;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid #edf0ee}.guide li>span{width:23px;height:23px;border-radius:50%;background:#e6efeb;color:#285b4e;display:grid;place-items:center;font-size:var(--text-caption)}.guide li strong,.guide li small{display:block}.guide li strong{font-size:var(--text-caption)}.guide li small{font-size:var(--text-caption);color:#8a9691;margin-top:2px}.tip{margin-top:20px;background:#fff6e9;border:1px solid #f0dfc6;border-radius:9px;padding:13px}.tip strong{font-size:var(--text-caption);color:#8c5a29}.tip p{font-size:var(--text-caption);line-height:1.7;color:#826f5c;margin:5px 0 0}.tip code{background:#f8e7d0;padding:1px 3px}.result{margin-top:12px;border-radius:8px;padding:11px;display:flex;gap:8px;font-size:var(--text-caption)}.error-result{background:#fff0f0;color:#a84a4a}.success-result{background:#eaf6f0;color:#276850}.result strong{font-size:var(--text-body)}.result p{margin:5px 0}.result ul{margin:5px 0 0;padding-left:16px}@media(max-width:1200px){.import-layout{grid-template-columns:minmax(0,1fr)}.type-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:550px){.type-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.import-main{padding:16px}}
.history-takeover-link{display:inline-flex;align-items:center;padding:8px 11px;border:1px solid #b9d1c3;border-radius:8px;background:#f3f8f4;color:#245c49;font-weight:700;text-decoration:none;white-space:nowrap}.history-takeover-link:hover{background:#e9f3ec}
.stage{padding:12px;background:#f0f4f2;border-radius:8px;font-weight:600}.drop-zone{padding:12px;height:auto;min-height:150px;text-align:center;overflow-wrap:anywhere}.result>div{min-width:0;flex:1}.error-table{overflow-x:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}td:last-child{min-width:180px}.error-table th:first-child{min-width:76px;white-space:nowrap}.error-table th:nth-child(2){min-width:90px}.inline-action{border:1px solid currentColor;background:white;color:inherit;padding:6px 10px;border-radius:6px;cursor:pointer;margin-top:8px}.error-pages{display:flex;gap:12px;align-items:center;margin-top:8px}button:disabled{cursor:not-allowed;opacity:.55}.type-grid input{display:inline-block;position:absolute;opacity:0}.type-grid label:focus-within{outline:2px solid #397b69}.template-btn small{white-space:normal;overflow-wrap:anywhere}.template-btn>span{min-width:0;flex:1}
.import-mode-tabs{display:flex;gap:8px;margin:0 0 14px}.import-mode-tabs button{border:1px solid #d9e2dd;background:#fff;color:#53645d;border-radius:8px;padding:9px 14px;font-weight:650;cursor:pointer}.import-mode-tabs button[aria-selected="true"]{border-color:#3c7468;background:#edf6f2;color:#17483e}.import-mode-tabs button:focus-visible,.history-inline-link:focus-visible{outline:2px solid #397b69;outline-offset:2px}.order-result-table{margin:10px 0}.history-inline-link{display:inline-flex;text-decoration:none;background:#fff}.order-result-table td:nth-child(4){white-space:nowrap}
@media(max-width:550px){.import-mode-tabs{display:grid;grid-template-columns:1fr 1fr}.import-mode-tabs button{padding:9px 7px;font-size:var(--text-caption)}.order-result-table table{min-width:520px}}
.field-key-guide{margin:9px 0 2px;padding:9px 11px;border:1px solid #e3ebe6;border-radius:8px;background:#fafcfb;color:#53675d;font-size:12px}.field-key-guide summary{cursor:pointer;font-weight:650}.field-key-guide p{margin:7px 0;color:#74847b}.field-key-guide ul{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 12px;margin:0;padding:0;list-style:none}.field-key-guide li{display:flex;justify-content:space-between;gap:8px;min-width:0}.field-key-guide code{overflow-wrap:anywhere;color:#53665c}th,td{word-break:break-word}
@media(max-width:550px){.field-key-guide ul{grid-template-columns:1fr}}
</style>
