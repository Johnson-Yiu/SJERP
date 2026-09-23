<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import ComboInput from './ComboInput.vue'
import { api } from '../api'
const props = defineProps({ productId: [Number, String], definitions: Array, savedRules: { type: Array, default: () => [] }, validCount: Number, totalCount: Number })
const emit = defineEmits(['preview', 'saved', 'dirty'])
let active = true
onBeforeUnmount(() => { active = false })
const rules = ref([]), error = ref(''), busy = ref(false), message = ref('')
const serialize = () => rules.value.map(r => ({ when: r.when, when_values: r.when ? r.whenText.split('\n').map(v => v.trim()).filter(Boolean) : [], target: r.target, op: r.op, values: r.valueText.split('\n').map(v => v.trim()).filter(Boolean) }))
const dirty = computed(() => JSON.stringify(serialize()) !== JSON.stringify(props.savedRules || []))
watch(() => [props.productId, props.savedRules], () => { rules.value = (props.savedRules || []).map(r => ({ ...r, whenText: (r.when_values || []).join('\n'), valueText: (r.values || []).join('\n') })); error.value = ''; message.value = '' }, { immediate: true })
watch(rules, () => { error.value = ''; message.value = ''; emit('dirty', dirty.value); emit('preview', null) }, { deep: true })
function add() { rules.value.push({ when: '', whenText: '', target: '', op: 'eq', valueText: '' }) }
const options = key => (props.definitions.find(d => d.key === key)?.values || []).map(value => ({ value, label: value }))
async function check(save) {
  if (busy.value) return
  busy.value = true; error.value = ''; message.value = ''
  const payload = serialize()
  try {
    await api.post(`/products/${props.productId}/combination-rules/`, { rules: payload, save })
    if (!active) return
    if (save) { emit('saved', payload); message.value = '规则已保存，仅影响后续创建或参数变更。' }
    else { emit('preview', payload); message.value = '已按当前规则预览下方有效组合；保存规则后可创建。' }
  } catch (e) { error.value = Object.values(e.response?.data || {}).flat().join('；') || e.message }
  finally { busy.value = false }
}
</script>
<template><section class="combination-rule-editor"><div class="rule-title"><h5>SKU 组合规则</h5><button type="button" :disabled="busy || rules.length >= 20" @click="add">＋ 添加规则</button></div><p class="rule-help">同一触发参数可添加多个值（任一值触发）；所有规则必须同时满足。值输入后按回车确认。长度、端口等须先配置为 SKU 参数。</p>
<fieldset v-for="(rule,index) in rules" :key="index" :disabled="busy" class="combination-rule"><legend>规则 {{ index + 1 }}</legend><div class="condition-grid"><label>触发条件<select v-model="rule.when" @change="rule.whenText = ''"><option value="">全部组合（无条件）</option><option v-for="d in definitions" :key="d.key" :value="d.key">{{ d.name }}</option></select></label><label v-if="rule.when">等于 / 属于<ComboInput v-model="rule.whenText" :options="options(rule.when)" multiple placeholder="输入一个或多个触发值" /></label><span v-else class="all-condition">适用于所有组合</span><span class="rule-arrow">→</span><label>约束参数<select v-model="rule.target" @change="rule.valueText = ''"><option value="">选择参数</option><option v-for="d in definitions" :key="d.key" :value="d.key">{{ d.name }}</option></select></label><label>规则<select v-model="rule.op"><option value="eq">必须等于</option><option value="neq">不能等于</option><option value="in">仅允许这些值</option></select></label><label>约束值<ComboInput v-model="rule.valueText" :options="options(rule.target)" multiple :placeholder="rule.op === 'in' ? '输入允许值' : '输入一个值'" /></label><button type="button" class="remove-rule" @click="rules.splice(index,1)">删除</button></div></fieldset>
<p v-if="!rules.length" class="rule-help">未设置规则，按当前参数生成全部组合。</p><p v-if="error" class="rule-error" role="alert">{{ error }}</p><p v-if="message" class="rule-message" role="status">{{ message }}</p><div class="rule-footer"><span>有效 {{ validCount }} / 理论 {{ totalCount }} 个组合<span v-if="dirty"> · 规则尚未保存</span></span><button type="button" :disabled="busy" @click="check(false)">预览有效组合</button><button type="button" class="save-rules" :disabled="busy" @click="check(true)">{{ busy ? '校验中…' : '保存规则' }}</button></div></section></template>
<style scoped>
.combination-rule-editor{margin:12px 0 16px;padding:14px;background:#f5f9f7;border:1px solid #dae7e0;border-radius:9px;container-type:inline-size}.rule-title,.rule-footer{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.rule-title{justify-content:space-between}.rule-title h5{font-size:14px;margin:0;color:#274e3f}.combination-rule-editor button{padding:7px 10px;border:1px solid #cedfd5;border-radius:6px;background:white;color:#2b6850;font-size:12px;cursor:pointer}.combination-rule-editor button:disabled{opacity:.5;cursor:default}.rule-help{font-size:11px;color:#789083;line-height:1.7}.combination-rule{min-width:0;border:1px solid #dbe7e0;border-radius:7px;padding:12px;background:white;margin:12px 0}.combination-rule legend{font-size:12px;color:#648072;padding:0 6px}.condition-grid{display:grid;grid-template-columns:1fr 1.3fr 20px 1fr 1fr 1.3fr auto;gap:9px;align-items:end}.condition-grid label{display:grid;gap:6px;min-width:0;font-size:11px;color:#637c6f}.condition-grid select{width:100%;min-width:0;height:36px;border:1px solid #cedfd5;border-radius:6px;background:white;color:#365c4b;font-size:12px}.rule-arrow,.all-condition{align-self:center;color:#839c8f;font-size:12px}.rule-footer>span{margin-right:auto;font-size:12px;color:#6b8376}.combination-rule-editor .save-rules{background:#12664e;color:white;border-color:#12664e}.combination-rule-editor .remove-rule{color:#b44940}.rule-error{color:#b42318;font-size:12px;background:#fff0ed;padding:10px;border-radius:6px}.rule-message{color:#227252;font-size:12px}@container(max-width:850px){.condition-grid{grid-template-columns:1fr 1fr}.rule-arrow{display:none}.all-condition{min-height:36px}.remove-rule{justify-self:start}}
</style>
