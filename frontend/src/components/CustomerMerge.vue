<script setup>
import { onMounted, ref } from 'vue'
import { useWorkspaceApi } from '../composables/useWorkspaceApi'
import { useAccessControl } from '../accessControl'
const props = defineProps({ historyPending: Boolean, customerId: { type: [Number, String], required: true } })
const emit = defineEmits(['changed'])
const workspace = useWorkspaceApi()
const { can } = useAccessControl()
const aliases = ref([])
const options = ref([])
const target = ref('')
const undoId = ref('')
const reason = ref('')
const preview = ref(null)
const message = ref('')
const busy = ref(false)
const expanded = ref(false)
async function load() {
  try { aliases.value = (await workspace.api.get('/customers/' + props.customerId + '/historical-names/')).data }
  catch { message.value = '历史名称加载失败' }
}
const completionReason = ref('')
async function completeHistory() {
  busy.value = true
  try {
    await workspace.api.post('/customers/' + props.customerId + '/complete-history/', { reason: completionReason.value })
    message.value = '已确认整理完成'
    emit('changed')
  } catch (error) { message.value = String(error.response?.data?.detail || error.response?.data || '确认失败，请重试。') }
  finally { busy.value = false }
}
onMounted(load)
async function open() {
  expanded.value = true
  try { options.value = (await workspace.listAll('/customers/')).filter(item => String(item.id) !== String(props.customerId)) }
  catch { message.value = '主客户列表加载失败' }
}
async function submit(confirm) {
  busy.value = true
  message.value = ''
  const source = undoId.value || props.customerId
  const body = { target: undoId.value ? props.customerId : target.value, undo: Boolean(undoId.value), reason: reason.value }
  try {
    const { data } = await workspace.api.post('/customers/' + source + (confirm ? '/merge/' : '/merge-preview/'), body)
    if (confirm) {
      preview.value = null
      message.value = undoId.value ? '已解除归并' : '已归并客户'
      expanded.value = false
      undoId.value = ''
      reason.value = ''
      await load()
      emit('changed')
    } else preview.value = data
  } catch (error) { message.value = String(error.response?.data?.detail || error.response?.data || '操作失败，请重试。') }
  finally { busy.value = false }
}
</script>
<template>
  <section class="detail-info">
    <fieldset v-if="historyPending && can('customers', 'update')" :disabled="busy">
      <label>整理依据<input v-model.trim="completionReason" /></label>
      <button class="btn btn-secondary" :disabled="!completionReason" @click="completeHistory">确认整理完成</button>
    </fieldset>
    <h3>历史名称</h3>
    <p v-if="!aliases.length">暂无归并记录</p>
    <div v-for="item in aliases" :key="item.id">{{ item.name }} · {{ item.code }}
      <button v-if="can('customers','update')" type="button" class="btn btn-secondary" :disabled="busy" @click="undoId = item.id; preview = null; expanded = true">解除归并</button>
    </div>
    <button v-if="can('customers','update') && !expanded" type="button" class="btn btn-secondary" @click="open">归并到其他客户</button>
    <fieldset v-if="expanded" :disabled="busy">
      <label v-if="!undoId">目标主客户<select v-model="target" @change="preview = null"><option value="">请选择</option><option v-for="item in options" :key="item.id" :value="item.id">{{ item.name }} · {{ item.code }}</option></select></label>
      <label>{{ undoId ? '解除依据' : '归并依据' }}<input v-model.trim="reason" /></label>
      <button type="button" class="btn btn-secondary" :disabled="!target && !undoId" @click="submit(false)">核对客户</button>
      <div v-if="preview">
        <p v-for="(item, key) in {来源客户: preview.source, 主客户: preview.target}" :key="key">{{ key }}：{{ item.name }} · {{ item.code }}<span v-if="item.order_count !== null"> · {{ item.order_count }} 张订单</span></p>
        <p v-if="preview.conflicts.length">资料不同：{{ preview.conflicts.join('、') }}</p>
        <button class="btn btn-primary" :disabled="!reason" @click="submit(true)">{{ undoId ? '确认解除归并' : '确认归并' }}</button>
      </div>
      <button class="btn btn-secondary" @click="expanded = false; undoId = ''; preview = null; reason = ''">取消</button>
    </fieldset>
    <p v-if="message" role="status">{{ message }}</p>
  </section>
</template>

<style scoped>
fieldset { display: flex; flex-wrap: wrap; align-items: end; gap: 12px; border: 0; padding: 0; margin: 12px 0 }
fieldset > div { flex-basis: 100% }
label { display: grid; gap: 6px; min-width: min(100%, 12rem); color: #38554b }
select, input { padding: 8px; border: 1px solid #b9ccc4; border-radius: 6px; font: inherit; background: white }
</style>
