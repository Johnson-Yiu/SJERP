<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Check, Copy, Plus, Save, Search } from 'lucide-vue-next'
import { api, listData } from '../api'

const rows = ref([]), templates = ref([]), query = ref(''), status = ref(''), loading = ref(true), saving = ref(false)
const selected = ref(new Set()), toast = reactive({ text: '', error: false })
const edit = reactive({ template: '', unit_net_weight: '', qty_per_carton_override: '', carton_length_override: '', carton_width_override: '', carton_height_override: '', carton_tare_weight_override: '', gross_weight_override: '' })
const filtered = computed(() => rows.value.filter(row => (!status.value || row.packaging.status === status.value) && (!query.value || `${row.sku} ${row.product_name}`.toLowerCase().includes(query.value.toLowerCase()))))
function notice(text, error = false) { Object.assign(toast, { text, error }); setTimeout(() => toast.text = '', 2600) }
async function load() { loading.value = true; try { [rows.value, templates.value] = await Promise.all([api.get('/skus/').then(listData), api.get('/packaging-templates/').then(listData)]) } catch (e) { notice(e.message, true) } finally { loading.value = false } }
function toggle(id) { const next = new Set(selected.value); next.has(id) ? next.delete(id) : next.add(id); selected.value = next }
function copyPrevious(index) { const previous = filtered.value[index - 1]; if (!previous?.packaging_profile) return notice('上一行没有可复制的包装配置。', true); Object.assign(edit, previous.packaging_profile) }
async function saveSelected() {
  if (!selected.value.size) return notice('请先选择 SKU。', true)
  saving.value = true
  try { await Promise.all([...selected.value].map(id => api.put(`/skus/${id}/packaging/`, { packaging_template: edit.template || null, unit_net_weight: edit.unit_net_weight || null, qty_per_carton_override: edit.qty_per_carton_override || null, carton_length_override: edit.carton_length_override || null, carton_width_override: edit.carton_width_override || null, carton_height_override: edit.carton_height_override || null, carton_tare_weight_override: edit.carton_tare_weight_override || null, gross_weight_override: edit.gross_weight_override || null }))); await load(); notice('已更新选中 SKU 的默认包装资料') } catch (e) { notice(e.message, true) } finally { saving.value = false }
}
async function quickTemplate() { const code = window.prompt('包装模板编码'); const name = window.prompt('包装模板名称'); if (!code || !name) return; try { await api.post('/packaging-templates/', { code, name, carton_length: 1, carton_width: 1, carton_height: 1, qty_per_carton: 1, carton_tare_weight: 0 }); await load(); notice('已创建模板，请在模板列表中补充尺寸。') } catch (e) { notice(e.message, true) } }
onMounted(load)
</script>

<template>
  <section>
    <div class="page-head"><div><h2>SKU 包装资料</h2><p>集中维护默认包装；报价、订单和实际出货的历史装箱均保存独立快照。</p></div><button class="btn btn-secondary" @click="quickTemplate"><Plus :size="16" /> 新建包装模板</button></div>
    <div class="panel bulk-panel"><div class="toolbar"><div class="search-box"><Search :size="17" /><input v-model="query" placeholder="搜索 SKU 或产品" /></div><select v-model="status"><option value="">全部包装状态</option><option value="NOT_CONFIGURED">未配置</option><option value="PARTIAL">部分配置</option><option value="COMPLETE">完整</option><option value="VERIFIED">已验证</option></select></div>
      <div class="batch-editor"><strong>批量设置（{{ selected.size }} 个 SKU）</strong><select v-model="edit.template"><option value="">不修改模板</option><option v-for="item in templates" :key="item.id" :value="item.id">{{ item.code }} · {{ item.name }}</option></select><input v-model="edit.unit_net_weight" type="number" min="0" step="0.001" placeholder="单件净重 kg" /><input v-model="edit.qty_per_carton_override" type="number" min="0.01" step="0.01" placeholder="每箱数量覆盖" /><button class="btn btn-primary" :disabled="saving" @click="saveSelected"><Save :size="15" /> 保存</button></div>
      <div v-if="loading" class="loading"><div class="spinner" /></div><div v-else class="table-wrap"><table class="data-table packaging-table"><thead><tr><th></th><th>SKU</th><th>产品</th><th>包装模板</th><th>单件净重</th><th>Qty / Carton</th><th>L × W × H (cm)</th><th>皮重</th><th>CBM</th><th>状态</th><th></th></tr></thead><tbody><tr v-for="(row,index) in filtered" :key="row.id"><td><input type="checkbox" :checked="selected.has(row.id)" @change="toggle(row.id)" /></td><td class="primary-cell">{{ row.sku }}</td><td>{{ row.product_name }}</td><td>{{ templates.find(t => t.id === row.packaging.template)?.code || '—' }}</td><td>{{ row.packaging.unit_net_weight ?? '—' }}</td><td>{{ row.packaging.effective_qty_per_carton ?? '—' }}</td><td>{{ row.packaging.effective_length ? `${row.packaging.effective_length} × ${row.packaging.effective_width} × ${row.packaging.effective_height}` : '—' }}</td><td>{{ row.packaging.effective_carton_tare_weight ?? '—' }}</td><td>{{ row.packaging.effective_cbm ?? '—' }}</td><td><span class="status" :class="row.packaging.status">{{ { NOT_CONFIGURED:'未配置', PARTIAL:'部分配置', COMPLETE:'完整', VERIFIED:'已验证' }[row.packaging.status] }}</span></td><td><button class="mini-btn" title="复制上一行" @click="copyPrevious(index)"><Copy :size="14" /></button></td></tr></tbody></table></div>
    </div><div v-if="toast.text" class="toast" :class="{ error: toast.error }">{{ toast.text }}</div>
  </section>
</template>

<style scoped>
.bulk-panel{padding:0}.toolbar,.batch-editor{padding:16px 20px;display:flex;gap:10px;align-items:center;border-bottom:1px solid var(--line)}.toolbar select,.batch-editor select,.batch-editor input{height:36px;border:1px solid var(--line);border-radius:7px;padding:0 9px;background:#fff}.batch-editor{background:#f8fbf9;flex-wrap:wrap}.batch-editor strong{margin-right:8px}.packaging-table td{white-space:nowrap}.NOT_CONFIGURED{background:#f5f1ee;color:#8c5a43}.PARTIAL{background:#fff4df;color:#9b6813}.COMPLETE{background:#e9f5ef;color:#23714d}.VERIFIED{background:#e7f1fb;color:#28658e}
</style>
