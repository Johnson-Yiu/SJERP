<script setup>
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const { api, listAll } = useWorkspaceApi()
import { computed, onMounted, ref, watch } from 'vue'


const props = defineProps({ contractType: { type: String, required: true }, contract: { type: Object, required: true } })
const emit = defineEmits(['changed'])
const rows = ref([]), error = ref(''), saving = ref(false)
const form = ref({ amount_delta: '', due_date: '', notes: '' })
const key = computed(() => props.contractType === 'order' ? 'order' : 'purchase_order')
const currency = computed(() => props.contract?.currency || '')
const money = value => Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
async function load() {
  if (!props.contract?.id) return
  try { rows.value = await listAll('/contract-changes/', { params: { [key.value]: props.contract.id } }) }
  catch (err) { error.value = err.message }
}
async function create() {
  if (saving.value || !Number(form.value.amount_delta) || !form.value.notes.trim()) return
  saving.value = true; error.value = ''
  try {
    await api.post('/contract-changes/', { [key.value]: props.contract.id, amount_delta: form.value.amount_delta, due_date: form.value.due_date || null, notes: form.value.notes.trim() })
    form.value = { amount_delta: '', due_date: '', notes: '' }; await load()
  } catch (err) { error.value = err.message } finally { saving.value = false }
}
async function act(row, action) {
  if (saving.value) return
  saving.value = true; error.value = ''
  try { await api.post(`/contract-changes/${row.id}/${action}/`); await load(); emit('changed') }
  catch (err) { error.value = err.message } finally { saving.value = false }
}
onMounted(load); watch(() => props.contract?.id, load)
</script>

<template>
  <section class="adjustments">
    <div class="adjustments-head"><div><h4>合同金额调整</h4><p>已确认调整会改变当前合同总额；调减只会减少未结清计划，不会自动退款。</p></div><strong>{{ currency }} {{ money(contract.total_amount) }}</strong></div>
    <div class="adjustment-totals"><span>基础金额 {{ currency }} {{ money(contract.base_amount) }}</span><span>已确认调整 {{ currency }} {{ money(contract.approved_change_amount) }}</span></div>
    <p v-if="error" class="adjustment-error">{{ error }}</p>
    <div class="adjustment-form"><input v-model="form.amount_delta" type="number" step="0.0001" placeholder="调整金额（正/负）"><input v-model="form.due_date" type="date"><input v-model="form.notes" placeholder="调整说明"><button class="btn btn-secondary" :disabled="saving" @click="create">新增调整</button></div>
    <p v-if="!rows.length" class="adjustment-empty">暂无金额调整记录。</p>
    <div v-else class="adjustment-list"><div v-for="row in rows" :key="row.id" class="adjustment-row"><span>{{ row.created_at?.slice(0, 10) }}</span><b :class="Number(row.amount_delta) < 0 ? 'negative' : 'positive'">{{ Number(row.amount_delta) > 0 ? '+' : '' }}{{ currency }} {{ money(row.amount_delta) }}</b><span>{{ row.notes }}</span><span>{{ row.status_display }}</span><button v-if="row.status === 'pending'" class="text-btn" :disabled="saving" @click="act(row, 'approve')">确认</button><button v-if="row.status === 'pending'" class="text-btn danger" :disabled="saving" @click="act(row, 'reject')">拒绝</button></div></div>
  </section>
</template>

<style scoped>
.adjustments{margin-top:16px;padding:16px;border:1px solid #dce8e2;border-radius:10px;background:#fff}.adjustments-head{display:flex;justify-content:space-between;gap:12px}.adjustments h4{margin:0;color:#234a3e}.adjustments p{margin:5px 0;color:#71827a;font-size:13px}.adjustment-totals,.adjustment-form,.adjustment-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.adjustment-totals{margin:10px 0;font-size:13px}.adjustment-form input{min-height:34px;flex:1;min-width:120px;border:1px solid #d8e3de;border-radius:7px;padding:6px 8px}.adjustment-list{margin-top:10px}.adjustment-row{padding:8px 0;border-top:1px solid #edf2ef;font-size:13px}.adjustment-row span:nth-child(3){flex:1}.positive{color:#216348}.negative,.danger{color:#a44343}.adjustment-error{color:#a44343}.adjustment-empty{padding:6px 0}@media(max-width:700px){.adjustment-form input{width:100%}}
</style>
