<script setup>
import { computed } from 'vue'
const props = defineProps({ before: { type: Object, default: null }, after: { type: Object, default: null } })
const sides = [['buyer', '买方'], ['seller', '卖方']]
const labels = { name: '名称', country: '国家 / 地区', address: '地址', tax_id: '税号', contact: '联系人', phone: '电话', email: '邮箱', billing_address: '账单地址', shipping_address: '收货地址', recipient: '收件人' }
const changes = computed(() => sides.flatMap(([side, title]) => {
  const before = props.before?.[side] || {}, after = props.after?.[side] || {}
  return [...new Set([...Object.keys(before), ...Object.keys(after)])].filter(key => before[key] !== after[key]).map(key => ({ id: `${side}-${key}`, label: `${title}${labels[key] || key}`, before: before[key], after: after[key] }))
}))
function valueText(value) { return value == null ? '未知' : value === '' ? '已留空' : value }
</script>

<template>
  <div v-if="changes.length" class="party-details-changes">
    <h4>双方资料变更</h4>
    <dl><template v-for="change in changes" :key="change.id"><dt>{{ change.label }}</dt><dd>{{ valueText(change.before) }} → {{ valueText(change.after) }}</dd></template></dl>
  </div>
</template>

<style scoped>
.party-details-changes dl{display:grid;grid-template-columns:minmax(100px,.35fr) minmax(0,1fr);gap:8px;overflow-wrap:anywhere}.party-details-changes dd{margin:0}
</style>
