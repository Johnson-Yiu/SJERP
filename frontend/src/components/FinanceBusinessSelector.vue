<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useWorkspaceApi } from '../composables/useWorkspaceApi'

const props = defineProps({ modelValue: [String, Number], type: { type: String, required: true }, direction: { type: String, default: '' }, label: { type: String, required: true }, required: Boolean })
const emit = defineEmits(['update:modelValue'])
const { api } = useWorkspaceApi()
const query = ref(''), items = ref([]), selected = ref(null), error = ref('')
let timer, sequence = 0
async function search() {
  const current = ++sequence
  try {
    const result = await api.get('/finance-ledger/choices/', { params: { type: props.type, q: query.value, direction: props.direction } })
    if (current !== sequence) return
    items.value = result.data.items
    error.value = ''
  } catch {
    if (current === sequence) error.value = '暂时无法搜索，请稍后重试。'
  }
}
function update(event) {
  const value = event.target.value
  selected.value = items.value.find(item => String(item.value) === value) || null
  emit('update:modelValue', value)
}
watch(query, () => { clearTimeout(timer); timer = setTimeout(search, 250) })
watch(() => [props.type, props.direction], () => { query.value = ''; selected.value = null; emit('update:modelValue', ''); search() })
onMounted(search)
onUnmounted(() => { clearTimeout(timer); sequence++ })
</script>

<template>
  <div class="business-selector">
    <label>{{ label }}<input v-model="query" :aria-label="`搜索${label}`" placeholder="搜索单号、账户或往来方"></label>
    <select :value="modelValue" :aria-label="`选择${label}`" :required="required" @change="update">
      <option value="">请选择</option>
      <option v-if="selected && !items.some(item => String(item.value) === String(selected.value))" :value="selected.value">{{ selected.label }}</option>
      <option v-for="item in items" :key="item.value" :value="item.value">{{ item.label }}</option>
    </select>
    <small v-if="error" role="alert">{{ error }}</small>
  </div>
</template>

<style scoped>
.business-selector{display:grid;gap:6px;flex:1 1 260px;min-width:0}.business-selector label{display:grid;gap:6px}.business-selector input,.business-selector select{width:100%;min-width:0;min-height:42px;border:1px solid #c9d3dc;border-radius:8px;padding:9px;box-sizing:border-box;font:inherit;background:white}.business-selector small{color:#943b32}
</style>
