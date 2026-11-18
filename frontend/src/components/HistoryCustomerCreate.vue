<script setup>
import { ref, watch } from 'vue'
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
const props = defineProps({ endpoint: { type: String, default: "/customers/history-customers/" }, initialNames: { type: Array, default: () => [] } })
const emit = defineEmits(['created'])
const { api } = useWorkspaceApi()
const input = ref('')
const rows = ref([])
const busy = ref(false)
const message = ref('')
watch(() => props.initialNames.join('\n'), value => { input.value = value; rows.value = [] }, { immediate: true })
async function submit(confirm) {
  busy.value = true
  message.value = ''
  try {
    const names = input.value.split(/\r?\n/).map(item => item.trim()).filter(Boolean)
    const { data } = await api.post(props.endpoint, { names, confirm })
    if (confirm) {
      rows.value = []
      message.value = data.map(row => row.name + ' · ' + row.code).join('，')
      emit('created', data)
    } else rows.value = data
  } catch (error) {
    message.value = String(error.response?.data?.detail || error.response?.data || '客户资料加载失败，请重试。')
    rows.value = []
  } finally { busy.value = false }
}
</script>
<template>
  <details class="takeover-resolution">
    <summary>创建历史客户</summary>
    <label>客户名称（每行一个）<textarea v-model="input" :disabled="busy" rows="3" @input="rows = []; message = ''" /></label>
    <button type="button" class="btn btn-secondary" :disabled="busy || !input.trim()" @click="submit(false)">预览客户</button>
    <ul v-if="rows.length"><li v-for="row in rows" :key="row.name">
      <strong>{{ row.name }}</strong> · {{ row.existing ? '已有客户 ' + row.code : '将创建为历史待整理客户' }}
      <div v-if="row.similar_inputs?.length">清单内相近名称：{{ row.similar_inputs.join('、') }}</div>
      <div v-if="row.candidates.length">相近名称：{{ row.candidates.map(item => item.name + ' ' + item.code).join('，') }}</div>
    </li></ul>
    <button v-if="rows.length" class="btn btn-primary" :disabled="busy" @click="submit(true)">确认客户清单</button>
    <p role="status" v-if="message">{{ message }}</p>
  </details>
</template>

<style scoped>
details { background: white; border: 1px solid #dce7e2; border-radius: 10px; padding: 12px 16px; margin-block: 12px }
summary { cursor: pointer; font-weight: 600; color: #235447 }
label { display: grid; gap: 6px; margin-block: 12px; max-width: 34rem }
textarea { padding: 8px; border: 1px solid #b9ccc4; border-radius: 6px; resize: vertical; font: inherit }
li { padding-block: 3px }
</style>
