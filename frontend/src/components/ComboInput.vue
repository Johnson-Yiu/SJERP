<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronDown, Plus } from 'lucide-vue-next'

const props = defineProps({ modelValue: { type: [String, Number], default: '' }, options: { type: Array, default: () => [] }, required: Boolean, disabled: Boolean, placeholder: { type: String, default: '选择或输入' }, multiple: Boolean, allowCustom: { type: Boolean, default: true }, uppercase: Boolean })
const emit = defineEmits(['update:modelValue'])
const open = ref(false), text = ref('')
const selectedLabel = computed(() => props.options.find(option => String(option.value) === String(props.modelValue))?.label || props.modelValue || '')
const values = computed(() => String(props.modelValue || '').split('\n').map(value => value.trim()).filter(Boolean))
const labelFor = value => props.options.find(option => String(option.value) === String(value))?.label || value
const filtered = computed(() => {
  const keywords = text.value.trim().toLowerCase().split(/[\s,，;；/\\|]+/).filter(Boolean)
  return props.options.filter(option => {
    if (!keywords.length) return true
    const searchable = `${option.label || ''} ${option.value || ''} ${option.searchText || ''}`.toLowerCase()
    return keywords.every(keyword => searchable.includes(keyword))
  })
})
const isCustom = computed(() => props.allowCustom && text.value.trim() && !props.options.some(option => option.label === text.value.trim() || option.value === text.value.trim()))

watch(() => props.modelValue, value => {
  const normalized = props.multiple
    ? String(value || '').split('\n').map(item => normalize(item).trim()).filter(Boolean).join('\n')
    : normalize(value).trim()
  if (props.uppercase && String(value || '') !== normalized) {
    emit('update:modelValue', normalized)
    return
  }
  if (!open.value && !props.multiple) text.value = selectedLabel.value
}, { immediate: true })
function focus() { if (props.disabled) return; if (!props.multiple) text.value = selectedLabel.value; open.value = true }
function normalize(value) { return props.uppercase ? String(value || '').toUpperCase() : String(value || '') }
function input(event) { if (props.disabled) return; text.value = normalize(event.target.value); open.value = true }
function append(value) {
  const next = normalize(value).trim()
  if (!next) return
  emit('update:modelValue', [...values.value, next].filter((item, index, list) => list.indexOf(item) === index).join('\n'))
  text.value = ''
}
function choose(option) { if (props.multiple) { append(option.value); return } const value = normalize(option.value); emit('update:modelValue', value); text.value = normalize(option.label); open.value = false }
function remove(value) { emit('update:modelValue', values.value.filter(item => item !== value).join('\n')) }
function keydown(event) {
  if (event.key !== 'Enter') return
  // A combo value is part of the form, not a request to submit the whole form.
  event.preventDefault()
  if (props.multiple) { append(text.value); return }
  const value = normalize(text.value).trim()
  if (!value) return
  const matchingOption = props.options.find(option => option.label === value || String(option.value) === value)
  if (matchingOption) choose(matchingOption)
  else if (props.allowCustom) choose({ value, label: value })
}
function commit() { if (props.multiple) { append(text.value); setTimeout(() => { open.value = false }, 150); return } if (props.allowCustom && text.value.trim()) emit('update:modelValue', normalize(text.value).trim()); setTimeout(() => { open.value = false; text.value = selectedLabel.value }, 150) }
</script>

<template>
  <div class="combo-input" :class="{ multiple }">
    <div class="combo-control"><div v-if="multiple && values.length" class="combo-tags"><span v-for="value in values" :key="value">{{ labelFor(value) }}<button type="button" aria-label="移除参数值" @mousedown.prevent @click="remove(value)">×</button></span></div><input :value="text" :required="required" :disabled="disabled" autocomplete="off" :placeholder="placeholder" @focus="focus" @input="input" @keydown="keydown" @blur="commit" /><ChevronDown :size="15" /></div>
    <div v-if="open" class="combo-menu">
      <button v-for="option in filtered" :key="option.value" type="button" @mousedown.prevent @click="choose(option)"><span>{{ option.label }}</span><small v-if="option.label !== option.value">{{ option.value }}</small></button>
      <button v-if="isCustom" type="button" class="custom-option" @mousedown.prevent @click="choose({ value: text.trim(), label: text.trim() })"><Plus :size="13" /> 添加“{{ text.trim() }}”</button>
      <div v-if="!filtered.length && !isCustom" class="combo-empty">暂无匹配选项</div>
    </div>
  </div>
</template>

<style scoped>
.combo-input{position:relative}.combo-control{position:relative;display:flex;align-items:center;gap:5px;min-height:42px;padding:4px 33px 4px 7px;border:1px solid #dce3df;border-radius:8px;background:#fff}.combo-control:focus-within{border-color:#83ad9f;box-shadow:0 0 0 3px #e2efeb}.combo-control input{width:100%;min-width:72px;flex:1;border:0;background:transparent;padding:5px 2px;outline:none;font-size:var(--text-body);color:#182622}.combo-control input:disabled{color:#5d756b;cursor:not-allowed}.combo-control svg{position:absolute;right:10px;top:12px;color:#788680;pointer-events:none}.combo-tags{display:flex;min-width:0;max-width:calc(100% - 72px);flex:0 1 auto;gap:5px;overflow-x:auto;scrollbar-width:none}.combo-tags::-webkit-scrollbar{display:none}.combo-tags span{display:inline-flex;flex:none;align-items:center;gap:5px;padding:3px 7px;border-radius:99px;background:#e7f2ed;color:#276452;font-size:var(--text-secondary);white-space:nowrap}.combo-tags button{border:0;background:transparent;color:#628078;font-size:var(--text-body);line-height:1;padding:0}.combo-menu{position:absolute;z-index:15;top:calc(100% + 5px);left:0;right:0;max-height:220px;overflow:auto;background:white;border:1px solid #dce4df;border-radius:9px;box-shadow:0 12px 30px #163c3022;padding:5px}.combo-menu button{width:100%;border:0;background:transparent;border-radius:6px;padding:8px 9px;display:flex;align-items:center;gap:6px;justify-content:space-between;text-align:left;color:#344a43;font-size:var(--text-body)}.combo-menu button:hover{background:#edf5f1}.combo-menu small{color:#98a39f;font-size:var(--text-caption)}.combo-menu .custom-option{justify-content:flex-start;color:#1d6754}.combo-empty{padding:12px;text-align:center;color:#98a39f;font-size:var(--text-body)}
</style>
