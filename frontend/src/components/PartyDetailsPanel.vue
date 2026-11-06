<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import PartyDetailsFields from './PartyDetailsFields.vue'

const props = defineProps({ kind: { type: String, required: true }, id: { type: [String, Number], required: true }, status: String, canEdit: Boolean })
const paths = { quote: 'quotes', order: 'orders', purchase_order: 'purchase-orders' }
const endpoint = computed(() => `/${paths[props.kind]}/${props.id}/party-details/`)
const fields = ['name', 'country', 'address', 'tax_id', 'contact', 'phone', 'email', 'billing_address', 'shipping_address', 'recipient']
const unknown = () => ({ schema: 'party-document-details-v1', buyer: Object.fromEntries(fields.map(k => [k, null])), seller: Object.fromEntries(fields.map(k => [k, null])) })
const value = ref(null), original = ref(null), draft = ref(null), loading = ref(false), busy = ref(false), error = ref('')
let generation = 0
async function load() {
  const ticket = ++generation; loading.value = true; error.value = ''
  try {
    const { data } = await api.get(endpoint.value)
    if (ticket !== generation) return
    value.value = data.details; original.value = data.original_details ?? null
    draft.value = structuredClone(data.details || unknown())
  } catch { if (ticket === generation) { value.value = null; draft.value = null; error.value = '主体资料读取失败，请重试。' } }
  finally { if (ticket === generation) loading.value = false }
}
async function save() {
  if (!props.canEdit || props.status !== 'draft' || busy.value || !draft.value) return
  busy.value = true; error.value = ''
  try { await api.put(endpoint.value, { details: draft.value }); await load() }
  catch { error.value = '主体资料保存失败，请检查单据状态后重试。' }
  finally { busy.value = false }
}
watch(() => [props.kind, props.id, props.status], load, { immediate: true })
</script>

<template>
  <section class="party-details-panel">
    <h3>{{ status === 'draft' ? '草稿双方资料' : '当前有效双方资料' }}</h3>
    <p v-if="loading">正在读取主体资料…</p><p v-else-if="error" role="alert">{{ error }} <button type="button" @click="load">重试</button></p>
    <template v-else-if="draft">
      <p v-if="!value">尚未记录；未知资料不会从当前主档补填。</p>
      <PartyDetailsFields v-model="draft" :editable="status === 'draft' && canEdit" />
      <button v-if="status === 'draft' && canEdit" type="button" class="btn btn-secondary" :disabled="busy" @click="save">保存双方资料</button>
      <details v-if="status !== 'draft'"><summary>查看原始双方资料</summary><PartyDetailsFields v-if="original" :model-value="original" /><p v-else>原始双方资料未知。</p></details>
    </template>
  </section>
</template>

<style scoped>.party-details-panel{padding:16px;border:1px solid #dce6df;border-radius:10px}.party-details-panel h3{margin:0 0 10px}.party-details-panel details{margin-top:12px}</style>
