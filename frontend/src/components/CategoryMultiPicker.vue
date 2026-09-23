<script setup>
import { computed, ref } from 'vue'
import { ChevronRight, X } from 'lucide-vue-next'
const props = defineProps({ modelValue: { type: Array, default: () => [] }, categories: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue'])
const path = ref([])
const selected = computed(() => (props.modelValue || []).map(Number))
const byId = computed(() => new Map(props.categories.map(category => [Number(category.id), category])))
const children = id => props.categories.filter(category => Number(category.parent || 0) === Number(id))
function isDescendant(id, ancestor) {
  const seen = new Set()
  let parent = byId.value.get(Number(id))?.parent
  while (parent && !seen.has(Number(parent))) {
    if (Number(parent) === Number(ancestor)) return true
    seen.add(Number(parent))
    parent = byId.value.get(Number(parent))?.parent
  }
  return false
}
const inherited = id => selected.value.some(parent => isDescendant(id, parent))
const checked = id => selected.value.includes(Number(id)) || inherited(id)
const partial = id => !checked(id) && selected.value.some(child => isDescendant(child, id))
const columns = computed(() => {
  const result = [children(0)]
  for (const id of path.value) {
    const next = children(id)
    if (!next.length) break
    result.push(next)
  }
  return result
})
function browse(category, index) { path.value = [...path.value.slice(0, index), Number(category.id)] }
function toggle(category, value) {
  if (inherited(category.id)) return
  const remaining = selected.value.filter(id => id !== Number(category.id) && (!value || !isDescendant(id, category.id)))
  emit('update:modelValue', value ? [...remaining, Number(category.id)] : remaining)
}
function remove(id) { emit('update:modelValue', selected.value.filter(value => value !== Number(id))) }
function labelFor(id) {
  const names = [], seen = new Set()
  let category = byId.value.get(Number(id))
  while (category && !seen.has(category.id)) {
    seen.add(category.id); names.unshift(category.name); category = byId.value.get(Number(category.parent))
  }
  return names.join(' / ') || String(id)
}
</script>
<template>
<div class="multi-category-picker">
  <div class="picker-head"><strong>选择可供分类</strong><span>勾选可多选，点击名称展开下级</span></div>
  <div class="cascade-columns"><section v-for="(column,index) in columns" :key="index" class="cascade-column" :aria-label="`第 ${index + 1} 级分类`"><small>{{ index === 0 ? '产品大类' : '子分类' }}</small><div v-for="category in column" :key="category.id" class="cascade-option" :class="{ active: path[index] === Number(category.id), selected: checked(category.id) }"><input type="checkbox" :aria-label="`选择${category.name}`" :checked="checked(category.id)" :indeterminate="partial(category.id)" :disabled="inherited(category.id)" :title="inherited(category.id) ? '已由上级分类覆盖；取消上级勾选后可单独选择' : ''" @change="toggle(category, $event.target.checked)" /><button type="button" :title="category.name" @click="browse(category,index)"><span>{{ category.name }}</span><ChevronRight v-if="children(category.id).length" :size="15" /></button></div><p v-if="!column.length">暂无分类</p></section></div>
  <div class="selected-categories"><span>已选 {{ selected.length }} 项</span><span v-if="!selected.length" class="empty">请选择大类或子分类</span><button v-for="id in selected" :key="id" type="button" :aria-label="`移除${labelFor(id)}`" @click="remove(id)">{{ labelFor(id) }}<X :size="12" /></button></div>
  <p class="picker-hint">选择大类会覆盖全部下级分类；只供应部分产品时，可展开后单独勾选子分类。</p>
</div>
</template>
<style scoped>
.multi-category-picker{min-width:0;border:1px solid #c8ddd5;border-radius:10px;overflow:hidden;background:#fbfdfc}.picker-head{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:11px 13px;background:#edf5f1;border-bottom:1px solid #dceae4;font-size:12px}.picker-head span{color:#69827a}.cascade-columns{display:flex;overflow-x:auto;background:#fff}.cascade-column{flex:1 0 180px;min-width:0;height:210px;overflow-y:auto;padding:6px;border-right:1px solid #e1ebe6;box-sizing:border-box}.cascade-column:last-child{border-right:0}.cascade-column>small{display:block;padding:5px 8px;color:#87998f;font-size:11px}.cascade-option{display:flex;align-items:center;gap:7px;padding:0 8px;border-radius:6px;min-height:34px}.cascade-option:hover,.cascade-option.active,.cascade-option.selected{background:#e1f0ea}.cascade-option input[type=checkbox]{flex:none;width:14px;height:14px;min-height:0;margin:0;accent-color:#16735a}.cascade-option button{flex:1;min-width:0;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 0;border:0;background:transparent;color:#29473e;font:inherit;font-size:12px;text-align:left;cursor:pointer}.cascade-option button span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.cascade-option svg{flex:none;color:#69827a}.selected-categories{display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:12px;border-top:1px solid #e1ebe6;font-size:12px;color:#526f61}.selected-categories button{display:flex;align-items:center;gap:6px;border:0;border-radius:5px;background:#e1f0ea;padding:5px 8px;color:#28664f;font-size:11px;cursor:pointer}.empty{color:#91a096}.picker-hint{margin:0;padding:0 12px 12px;color:#798f83;font-size:11px;line-height:1.6}
</style>
