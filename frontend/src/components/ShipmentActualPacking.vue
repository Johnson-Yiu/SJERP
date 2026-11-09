<script setup>
import { useWorkspaceTeleportDisabled } from "../composables/useWorkspaceTeleport"
const workspaceTeleportDisabled = useWorkspaceTeleportDisabled()
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, downloadPackingListExport } = useWorkspaceApi()
import { computed, ref, watch } from 'vue'

import { confirmDialog } from '../dialogs'
import { useAccessControl } from '../accessControl'
import { decimal, packingSummary, scaled, shippedSkus } from '../utils/actualPacking'

const props = defineProps({ shipments: { type: Array, default: () => [] }, hasPlan: Boolean, cache: { type: Object, required: true } })
const { can } = useAccessControl()
const editor = ref(null), editorError = ref(''), saving = ref(false)
const busy = ref({}), errors = ref({}), loading = ref({}), exporting = ref({})
const target = computed(() => props.shipments.find(row => row.id === editor.value?.shipmentId))
const skuOptions = computed(() => target.value ? shippedSkus(target.value) : [])
const mutable = shipment => shipment?.status === 'confirmed'
const packages = shipment => props.cache[shipment.id] || []
const summary = shipment => packingSummary(shipment, packages(shipment))
function errorMessage(error) {
  const data = error.response?.data
  if (!data) return error.message || '操作失败，请重试。'
  const flatten = value => typeof value === 'string' ? value : Array.isArray(value) ? value.map(flatten).join('；') : Object.values(value).map(flatten).join('；')
  return flatten(data)
}
async function load(shipment, force = false) {
  if (loading.value[shipment.id] || (!force && Object.hasOwn(props.cache, shipment.id))) return
  loading.value[shipment.id] = true
  errors.value[shipment.id] = ''
  try { props.cache[shipment.id] = (await api.get(`/shipments/${shipment.id}/packages/`)).data }
  catch (error) { errors.value[shipment.id] = errorMessage(error) }
  finally { loading.value[shipment.id] = false }
}
watch(() => props.shipments, rows => rows.forEach(row => load(row)), { immediate: true })
function openEditor(shipment, existing = null) {
  if (!mutable(shipment) || busy.value[shipment.id] || !Object.hasOwn(props.cache, shipment.id)) return
  editorError.value = ''
  editor.value = {
    shipmentId: shipment.id, id: existing?.id,
    carton_no: existing?.carton_no ?? Math.max(0, ...packages(shipment).map(row => Number(row.carton_no))) + 1,
    length: existing?.length ?? '', width: existing?.width ?? '', height: existing?.height ?? '',
    actual_net_weight: existing?.actual_net_weight ?? '0', actual_gross_weight: existing?.actual_gross_weight ?? '0', notes: existing?.notes ?? '',
    items: existing ? existing.items.map(item => ({ sku: item.sku, quantity: item.quantity })) : [{ sku: '', quantity: '' }],
  }
}
function validateEditor() {
  const form = editor.value
  if (!mutable(target.value)) throw new Error('发货已冲销，实际箱单仅供历史查看。')
  if (!Number.isInteger(Number(form.carton_no)) || Number(form.carton_no) <= 0) throw new Error('箱号必须为正整数。')
  const dims = [form.length, form.width, form.height]
  if (dims.some(v => v !== '') && !dims.every(v => v !== '' && scaled(v) > 0n)) throw new Error('箱长、宽、高须同时填写且大于零，或全部留空。')
  const net = scaled(form.actual_net_weight, 3), gross = scaled(form.actual_gross_weight, 3)
  if (net < 0n || gross < net) throw new Error('净重、毛重不得为负，且毛重不得低于净重。')
  if (!form.items.length) throw new Error('请填写至少一条箱内 SKU 明细。')
  const allowed = new Set(skuOptions.value.map(row => String(row.sku))), seen = new Set()
  for (const item of form.items) {
    if (!allowed.has(String(item.sku))) throw new Error('请选择本次发货的 SKU。')
    if (seen.has(String(item.sku))) throw new Error('同一箱内不能重复填写同一 SKU。')
    seen.add(String(item.sku))
    if (scaled(item.quantity) <= 0n) throw new Error('实际装箱数量必须大于零。')
  }
  // Cumulative quantity is checked by the server under a Shipment lock.
}
async function save() {
  if (saving.value) return
  editorError.value = ''
  try { validateEditor() } catch (error) { editorError.value = error.message; return }
  const form = editor.value, shipment = target.value
  saving.value = true
  busy.value[shipment.id] = true
  try {
    const payload = { carton_no: Number(form.carton_no), length: form.length === '' ? null : form.length, width: form.width === '' ? null : form.width, height: form.height === '' ? null : form.height,
      actual_net_weight: form.actual_net_weight, actual_gross_weight: form.actual_gross_weight, notes: form.notes,
      items: form.items.map(item => ({ sku: Number(item.sku), quantity: item.quantity })) }
    await api.post(`/shipments/${shipment.id}/packages/${form.id ? `${form.id}/` : ''}`, payload)
    editor.value = null
    await load(shipment, true)
  } catch (error) { editorError.value = errorMessage(error) }
  finally { saving.value = false; busy.value[shipment.id] = false }
}
async function remove(shipment, row) {
  if (!mutable(shipment) || busy.value[shipment.id]) return
  busy.value[shipment.id] = true
  errors.value[shipment.id] = ''
  try {
    if (!await confirmDialog({ title: `删除第 ${row.carton_no} 箱？`, message: '仅删除这条实际装箱记录；发货单、库存及订单数量均不受影响。', confirmText: '删除', danger: true })) return
    if (!mutable(shipment)) return
    await api.delete(`/shipments/${shipment.id}/packages/${row.id}/`)
    await load(shipment, true)
  } catch (error) { errors.value[shipment.id] = errorMessage(error) }
  finally { busy.value[shipment.id] = false }
}
async function copy(shipment) {
  if (!mutable(shipment) || !props.hasPlan || busy.value[shipment.id] || !Object.hasOwn(props.cache, shipment.id)) return
  busy.value[shipment.id] = true
  errors.value[shipment.id] = ''
  try {
    const replace = packages(shipment).length > 0
    if (replace && !await confirmDialog({ title: '替换实际箱单？', message: '现有实际箱单将被预计装箱方案替换。复制后可编辑实际尺寸、重量和数量。', confirmText: '确认替换', danger: true })) return
    if (!mutable(shipment)) return
    const result = await api.post(`/shipments/${shipment.id}/copy-estimated-packing/`, replace ? { replace: true } : {})
    props.cache[shipment.id] = result.data
  } catch (error) { errors.value[shipment.id] = errorMessage(error) }
  finally { busy.value[shipment.id] = false }
}
function exportErrorMessage(error) {
  const data = error.response?.data || error.data
  if (data?.differences?.length) {
    const details = data.differences.map(row => `${row.sku}：发货 ${row.shipped_quantity}，已装箱 ${row.packed_quantity}，差额 ${row.difference}`).join('；')
    return `${data.detail || '实际装箱数量不一致。'} ${details}`
  }
  return errorMessage(error)
}
async function exportPackingList(shipment) {
  if (exporting.value[shipment.id] || !can('inventory', 'export') || summary(shipment).complete === false) return
  exporting.value[shipment.id] = true
  errors.value[shipment.id] = ''
  try { await downloadPackingListExport(shipment.id, shipment.shipment_no) }
  catch (error) { errors.value[shipment.id] = exportErrorMessage(error) }
  finally { exporting.value[shipment.id] = false }
}
const skuLabel = (shipment, id) => shippedSkus(shipment).find(row => String(row.sku) === String(id))?.sku_code || `SKU #${id}`
</script>

<template>
  <section class="actual-packing-panel">
    <div class="section-heading"><div><h3>实际装箱（Packing List）</h3><p>记录本次发货的实际箱单；不会改变预计装箱、发货、库存或订单数量。</p></div></div>
    <p v-if="!shipments.length" class="muted">暂无发货记录，确认发货后可登记实际箱单。</p>
    <article v-for="shipment in shipments" :key="shipment.id" class="actual-shipment-card">
      <header><div><h4>{{ shipment.shipment_no }}</h4><small>{{ shipment.shipment_date }}</small></div><span class="status" :class="shipment.status">{{ shipment.status === 'confirmed' ? '已确认' : shipment.status === 'cancelled' ? '已冲销' : shipment.status }}</span></header>
      <p class="shipped-sku-summary"><span v-for="sku in shippedSkus(shipment)" :key="sku.sku">{{ sku.sku_code }} · {{ sku.display_name }} · 发货 {{ decimal(sku.quantity) }} {{ sku.base_unit }} </span></p>
      <p v-if="shipment.status === 'cancelled'" class="packing-history-note">发货已冲销 · 实际箱单仅供历史查看</p>
      <p v-if="loading[shipment.id]" role="status">实际箱单加载中…</p>
      <div v-if="errors[shipment.id]" class="packing-error" role="alert">{{ errors[shipment.id] }} <button v-if="!Object.hasOwn(cache, shipment.id)" type="button" @click="load(shipment, true)">重试</button></div>
      <template v-if="Object.hasOwn(cache, shipment.id)">
        <div class="actual-packing-summary"><span>实际装箱：<strong>{{ summary(shipment).count }} 箱</strong></span><span>净重：{{ summary(shipment).net }} kg</span><span>毛重：{{ summary(shipment).gross }} kg</span><span>CBM：{{ summary(shipment).cbm }} m³</span><button v-if="can('inventory', 'export') && mutable(shipment)" type="button" class="btn btn-secondary" :disabled="!summary(shipment).complete || exporting[shipment.id]" @click="exportPackingList(shipment)">{{ exporting[shipment.id] ? '导出中…' : '导出 Packing List' }}</button></div>
        <div class="packing-progress"><strong>{{ summary(shipment).complete ? '装箱完成' : '尚未装箱完成' }}</strong><p v-for="row in summary(shipment).rows" :key="row.sku">{{ row.sku_code }}：已装 {{ row.packed }} / 发货 {{ row.shipped }} {{ row.base_unit }} <span v-if="!row.complete"> · 未装箱 {{ row.remaining }} {{ row.base_unit }}</span></p></div>
        <div v-if="mutable(shipment)" class="actual-packing-actions"><button type="button" class="btn btn-primary" :disabled="busy[shipment.id]" @click="openEditor(shipment)">新增箱</button><button type="button" class="btn btn-secondary" :disabled="!hasPlan || busy[shipment.id]" @click="copy(shipment)">复制预计装箱方案</button><small v-if="!hasPlan">请先生成预计装箱方案</small></div>
        <p v-if="!packages(shipment).length" class="muted">尚无实际装箱记录。</p>
        <div class="actual-carton-list"><article v-for="row in packages(shipment)" :key="row.id" class="actual-carton-card"><header><strong>第 {{ row.carton_no }} 箱</strong><div v-if="mutable(shipment)"><button type="button" class="text-btn" :disabled="busy[shipment.id]" @click="openEditor(shipment, row)">编辑</button><button type="button" class="text-btn danger" :disabled="busy[shipment.id]" @click="remove(shipment, row)">删除</button></div></header><p>尺寸：{{ row.length ?? '—' }} × {{ row.width ?? '—' }} × {{ row.height ?? '—' }} cm</p><p>净重：{{ row.actual_net_weight }} kg · 毛重：{{ row.actual_gross_weight }} kg · CBM：{{ row.actual_cbm }} m³</p><p v-for="item in row.items" :key="item.id || item.sku">{{ skuLabel(shipment, item.sku) }} × {{ item.quantity }}</p><p v-if="row.notes">备注：{{ row.notes }}</p></article></div>
      </template>
    </article>
    <Teleport to="body" :disabled="workspaceTeleportDisabled"><div v-if="editor" class="actual-packing-mask"><form class="actual-packing-editor" role="dialog" aria-modal="true" aria-labelledby="actual-packing-title" @submit.prevent="save">
      <h3 id="actual-packing-title">{{ editor.id ? '编辑实际装箱记录' : '新增实际装箱记录' }} · {{ target?.shipment_no }}</h3><p>数量采用本次发货的基础单位；CBM 由箱长、宽、高自动计算。</p>
      <div class="packing-editor-fields"><label>箱号<input v-model="editor.carton_no" type="number" min="1" step="1" required /></label><label>长 cm<input :value="editor.length" @input="editor.length = $event.target.value" type="number" min="0.01" step="0.01" /></label><label>宽 cm<input :value="editor.width" @input="editor.width = $event.target.value" type="number" min="0.01" step="0.01" /></label><label>高 cm<input :value="editor.height" @input="editor.height = $event.target.value" type="number" min="0.01" step="0.01" /></label><label>实际净重 kg<input :value="editor.actual_net_weight" @input="editor.actual_net_weight = $event.target.value" type="number" min="0" step="0.001" required /></label><label>实际毛重 kg<input :value="editor.actual_gross_weight" @input="editor.actual_gross_weight = $event.target.value" type="number" min="0" step="0.001" required /></label></div>
      <label>备注<textarea v-model="editor.notes" /></label><h4>箱内 SKU 明细</h4>
      <div v-for="(item, index) in editor.items" :key="index" class="packing-editor-item"><label>SKU<select v-model="item.sku" :aria-label="`SKU ${index + 1}`" required><option value="">请选择本次发货 SKU</option><option v-for="sku in skuOptions" :key="sku.sku" :value="sku.sku">{{ sku.sku_code }} · {{ sku.display_name }} ({{ sku.base_unit }})</option></select></label><label>实际装箱数量<input :value="item.quantity" @input="item.quantity = $event.target.value" :aria-label="`实际装箱数量 ${index + 1}`" type="number" min="0.01" step="0.01" required /></label><button type="button" class="text-btn" :disabled="saving" @click="editor.items.splice(index, 1)">移除</button></div>
      <button type="button" class="text-btn" :disabled="saving" @click="editor.items.push({ sku: '', quantity: '' })">添加 SKU 明细</button><p v-if="editorError" class="packing-error" role="alert">{{ editorError }}</p>
       <footer><button type="button" class="btn btn-secondary" :disabled="saving" @click="editor = null">取消</button><button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存实际装箱' }}</button></footer>
    </form></div></Teleport>
  </section>
</template>

<style scoped>
.actual-packing-panel{margin-top:28px;padding-top:22px;border-top:2px solid #dce8e1}.section-heading h3{margin:0}.section-heading p,.muted{color:#65776e}.actual-shipment-card{margin-top:16px;padding:18px;border:1px solid #dfe8e3;border-radius:12px}.actual-shipment-card>header,.actual-carton-card>header{display:flex;justify-content:space-between;align-items:center;gap:12px}.actual-shipment-card h4{margin:0 0 6px}.shipped-sku-summary{display:flex;flex-wrap:wrap;gap:8px;color:#405b50}.actual-packing-summary,.actual-packing-actions{display:flex;align-items:center;flex-wrap:wrap;gap:14px;margin:14px 0}.packing-progress{padding:12px;background:#f0f6f2;border-radius:8px}.packing-progress p{margin:6px 0}.actual-carton-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.actual-carton-card{padding:14px;border:1px solid #e0e8e3;border-radius:8px;overflow-wrap:anywhere}.actual-carton-card p{margin:9px 0}.packing-history-note{color:#866315;background:#fff6df;padding:10px;border-radius:8px}.packing-error{color:#a02929;background:#fff0ef;padding:10px;border-radius:8px;white-space:pre-wrap}.actual-packing-mask{position:fixed;inset:0;z-index:150;display:grid;place-items:center;background:#10261d77}.actual-packing-editor{width:min(820px,94vw);max-height:90vh;overflow:auto;background:white;border-radius:14px;padding:24px}.actual-packing-editor h3{margin-top:0}.actual-packing-editor label{display:grid;gap:7px;margin:8px 0}.actual-packing-editor input,.actual-packing-editor select,.actual-packing-editor textarea{padding:9px;border:1px solid #cddcd3;border-radius:6px;font:inherit;width:100%;box-sizing:border-box}.packing-editor-fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.packing-editor-item{display:grid;grid-template-columns:2fr 1fr auto;align-items:end;gap:10px}.actual-packing-editor footer{display:flex;justify-content:flex-end;gap:12px;margin-top:18px}.danger{color:#a02929}@media(max-width:700px){.actual-carton-list{grid-template-columns:1fr}.packing-editor-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.packing-editor-item{grid-template-columns:1fr}.actual-packing-editor{padding:16px}}
</style>
