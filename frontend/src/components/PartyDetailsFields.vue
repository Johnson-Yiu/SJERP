<script setup>
const props = defineProps({ modelValue: { type: Object, required: true }, editable: Boolean, preserveUnknown: Boolean })
const emit = defineEmits(['update:modelValue'])
const sides = [['buyer', '买方'], ['seller', '卖方']]
const fields = [['name', '名称'], ['country', '国家 / 地区'], ['address', '地址'], ['tax_id', '税号'], ['contact', '联系人'], ['phone', '电话'], ['email', '邮箱'], ['billing_address', '账单地址'], ['shipping_address', '收货地址'], ['recipient', '收件人']]
function change(side, key, value) {
  emit('update:modelValue', { ...props.modelValue, [side]: { ...props.modelValue[side], [key]: value } })
}
</script>

<template>
  <div class="party-details-fields">
    <section v-for="[side, title] in sides" :key="side">
      <h4>{{ title }}</h4>
      <div v-for="[key, label] in fields" :key="key" class="party-details-field">
        <label v-if="editable">{{ title }}{{ label }}<input :value="modelValue[side][key] ?? ''" :placeholder="modelValue[side][key] == null ? '未知' : ''" :disabled="preserveUnknown && modelValue[side][key] == null" @input="change(side, key, $event.target.value)" /></label>
        <template v-else><span>{{ label }}</span><span>{{ modelValue[side][key] == null ? '未知' : modelValue[side][key] === '' ? '已留空' : modelValue[side][key] }}</span></template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.party-details-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.party-details-field{display:grid;grid-template-columns:1fr 2fr;gap:8px;margin:6px 0;overflow-wrap:anywhere}.party-details-field label{grid-column:1/-1;display:grid;gap:4px}.party-details-field input{width:100%;padding:6px;border:1px solid #b9c9c1;border-radius:5px}
</style>
