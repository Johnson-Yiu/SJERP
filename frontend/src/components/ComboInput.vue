<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronDown, Plus } from 'lucide-vue-next'

const props = defineProps({ modelValue: { type: String, default: '' }, options: { type: Array, default: () => [] }, required: Boolean, placeholder: { type: String, default: '选择或输入' }, multiple: Boolean })
const emit = defineEmits(['update:modelValue'])
const open = ref(false), text = ref('')
const selectedLabel = computed(() => props.options.find(option => option.value === props.modelValue)?.label || props.modelValue || '')
const values = computed(() => String(props.modelValue || '').split('\n').map(value => value.trim()).filter(Boolean))
const filtered = computed(() => {
  const keyword = text.value.trim().toLowerCase()
  return props.options.filter(option => !keyword || option.label.toLowerCase().includes(keyword) || option.value.toLowerCase().includes(keyword))
})
const isCustom = computed(() => text.value.trim() && !props.options.some(option => option.label === text.value.trim() || option.value === text.value.trim()))

watch(() => props.modelValue, () => { if (!open.value && !props.multiple) text.value = selectedLabel.value }, { immediate: true })
function focus() { if (!props.multiple) text.value = selectedLabel.value; open.value = true }
function input(event) { text.value = event.target.value; if (!props.multiple) emit('update:modelValue', event.target.value); open.value = true }
function append(value) {
  const next = value?.trim()
  if (!next) return
  emit('update:modelValue', [...values.value, next].filter((item, index, list) => list.indexOf(item) === index).join('\n'))
  text.value = ''
}
function choose(option) { if (props.multiple) { append(option.value); return } emit('update:modelValue', option.value); text.value = option.label; open.value = false }
function remove(value) { emit('update:modelValue', values.value.filter(item => item !== value).join('\n')) }
function keydown(event) { if (props.multiple && event.key === 'Enter') { event.preventDefault(); append(text.value) } }
function commit() { if (props.multiple) { append(text.value); setTimeout(() => { open.value = false }, 150); return } if (text.value.trim()) emit('update:modelValue', text.value.trim()); setTimeout(() => { open.value = false; text.value = selectedLabel.value }, 150) }
</script>

<template>
  <div class="combo-input" :class="{ multiple }">
    <div v-if="multiple && values.length" class="combo-tags"><span v-for="value in values" :key="value">{{ value }}<button type="button" aria-label="移除参数值" @mousedown.prevent @click="remove(value)">×</button></span></div>
    <div class="combo-control"><input :value="text" :required="required" autocomplete="off" :placeholder="placeholder" @focus="focus" @input="input" @keydown="keydown" @blur="commit" /><ChevronDown :size="15" /></div>
    <div v-if="open" class="combo-menu">
      <button v-for="option in filtered" :key="option.value" type="button" @mousedown.prevent @click="choose(option)"><span>{{ option.label }}</span><small v-if="option.label !== option.value">{{ option.value }}</small></button>
      <button v-if="isCustom" type="button" class="custom-option" @mousedown.prevent @click="choose({ value: text.trim(), label: text.trim() })"><Plus :size="13" /> 添加“{{ text.trim() }}”</button>
      <div v-if="!filtered.length && !isCustom" class="combo-empty">暂无历史选项，可直接输入新值</div>
    </div>
  </div>
</template>

<style scoped>
.combo-input{position:relative}.combo-control{position:relative}.combo-control input{width:100%;border:1px solid #dce3df;background:#fff;border-radius:8px;padding:10px 34px 10px 11px;outline:none;font-size:14px;color:#182622}.combo-control input:focus{border-color:#83ad9f;box-shadow:0 0 0 3px #e2efeb}.combo-control svg{position:absolute;right:10px;top:12px;color:#788680;pointer-events:none}.combo-tags{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 6px}.combo-tags span{display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border-radius:99px;background:#e7f2ed;color:#276452;font-size:11px}.combo-tags button{border:0;background:transparent;color:#628078;font-size:15px;line-height:1;padding:0}.combo-menu{position:absolute;z-index:15;top:calc(100% + 5px);left:0;right:0;max-height:220px;overflow:auto;background:white;border:1px solid #dce4df;border-radius:9px;box-shadow:0 12px 30px #163c3022;padding:5px}.combo-menu button{width:100%;border:0;background:transparent;border-radius:6px;padding:8px 9px;display:flex;align-items:center;gap:6px;justify-content:space-between;text-align:left;color:#344a43;font-size:12px}.combo-menu button:hover{background:#edf5f1}.combo-menu small{color:#98a39f;font-size:9px}.combo-menu .custom-option{justify-content:flex-start;color:#1d6754}.combo-empty{padding:12px;text-align:center;color:#98a39f;font-size:11px}
</style>
