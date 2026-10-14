<script setup>
import { computed } from 'vue'
import { copyPaymentTerms, paymentTermsError, percentToRatio } from '../utils/paymentTerms'
const props = defineProps({ modelValue: { type: Array, default: () => [] }, description: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const rows = computed(() => props.modelValue)
const error = computed(() => paymentTermsError(rows.value))
const total = computed(() => Number(rows.value.reduce((sum, row) => sum + Number(row.ratio || 0) * 100, 0).toFixed(8)))
function change(index, key, value) { const next = JSON.parse(JSON.stringify(rows.value)); next[index][key] = value; emit('update:modelValue', next) }
function add() { emit('update:modelValue', [...rows.value, { label: '', ratio: '', due_basis: 'no_date', offset_days: 0 }]) }
function remove(index) { emit('update:modelValue', rows.value.filter((_, i) => i !== index)) }
</script>
<template>
  <div class="terms-editor"><p v-if="description" class="terms-description">{{ description }}</p>
    <div class="terms-scroll"><div class="terms-head"><span>阶段名称</span><span>比例 %</span><span>到期依据</span><span>延后天数</span><span /></div>
      <div v-for="(row,index) in rows" :key="index" class="terms-row">
        <input :value="row.label" :aria-label="`阶段名称 ${index + 1}`" required @input="change(index, 'label', $event.target.value)" />
        <input :value="row.ratio === '' ? '' : Number((Number(row.ratio) * 100).toFixed(8))" :aria-label="`比例 % ${index + 1}`" type="number" min="0.000001" max="100" step="any" required @input="change(index, 'ratio', percentToRatio($event.target.value))" />
        <select :value="row.due_basis" :aria-label="`到期依据 ${index + 1}`" @change="change(index, 'due_basis', $event.target.value)"><option value="order_date">下单日期</option><option value="expected_arrival_date">预计到货</option><option value="no_date">暂不设日期</option></select>
        <input :value="row.offset_days" :aria-label="`延后天数 ${index + 1}`" type="number" min="0" step="1" required @input="change(index, 'offset_days', $event.target.value === '' ? null : Number($event.target.value))" />
        <button type="button" :aria-label="`删除付款阶段 ${index + 1}`" @click="remove(index)">删除</button>
      </div>
    </div>
    <div class="terms-footer"><button type="button" :disabled="rows.length >= 5" @click="add">新增付款阶段</button><button v-if="!rows.length" type="button" @click="emit('update:modelValue', copyPaymentTerms())">使用系统默认</button><strong>合计：{{ total }}%</strong></div>
    <p v-if="error" class="terms-error" role="alert">{{ error }}</p>
  </div>
</template>
<style scoped>
.terms-row input,.terms-row select{height:42px;border:1px solid #dfe5e1;border-radius:8px;padding:9px 11px;background:#fff;color:#294a41;font:inherit;font-size:14px}.terms-row input:focus,.terms-row select:focus{outline:2px solid #b8d8cb;outline-offset:1px}
.terms-editor{min-width:0}.terms-scroll{overflow-x:auto}.terms-head,.terms-row{display:grid;grid-template-columns:minmax(130px,1fr) 95px minmax(145px,1fr) 95px 50px;gap:10px;min-width:570px;align-items:center}.terms-head{color:#71817b;font-size:12px;margin-bottom:8px}.terms-row{margin-bottom:10px}.terms-row input,.terms-row select{width:100%;min-width:0;box-sizing:border-box}.terms-row button,.terms-footer button{border:1px solid #cfe1d9;border-radius:7px;padding:7px;background:white;color:#236657;cursor:pointer}.terms-footer{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.terms-footer strong{margin-left:auto;color:#174c41}.terms-error{color:#b34848;font-size:13px;margin-bottom:0}
</style>
