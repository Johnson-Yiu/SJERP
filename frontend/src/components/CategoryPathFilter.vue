<script setup>
import { useWorkspaceTeleportDisabled } from "../composables/useWorkspaceTeleport"
const workspaceTeleportDisabled = useWorkspaceTeleportDisabled()
import { useWorkspaceNavigation } from '../composables/useWorkspaceNavigation'
const { workspace } = useWorkspaceNavigation()
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'
import { categoryParts, categoryTree } from '../utils/categoryPaths'
const props = defineProps({ modelValue: { type: String, default: '' }, paths: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue'])
const trigger = ref(null), panel = ref(null), open = ref(false), browsing = ref([]), position = ref({})
const tree = computed(() => categoryTree(props.paths))
const columnWidths = ref([140])
const columns = computed(() => {
  const result = [tree.value]
  let nodes = tree.value
  for (const name of browsing.value) {
    const node = nodes.find(item => item.name === name)
    if (!node?.children.length) break
    nodes = node.children; result.push(nodes)
  }
  return columnWidths.value.map((_, level) => result[level] || [])
})
const label = computed(() => categoryParts(props.modelValue).at(-1) || '全部分类')
function close() { open.value = false }
function toggle() {
  if (open.value) { close(); return }
  browsing.value = categoryParts(props.modelValue)
  const rect = trigger.value.getBoundingClientRect()
  const font = window.getComputedStyle(trigger.value)
  const context = document.createElement('canvas').getContext('2d')
  if (context) context.font = `${font.fontWeight} ${font.fontSize} ${font.fontFamily}`
  const widths = []
  for (const path of props.paths) {
    categoryParts(path).forEach((name, level) => {
      // Reserve padding, the next-level arrow, and the vertical scrollbar.
      const textWidth = context?.measureText(name).width ?? name.length * 14
      widths[level] = Math.max(widths[level] || 120, Math.ceil(textWidth) + 64)
    })
  }
  if (!widths.length) widths.push(320)
  const total = widths.reduce((sum, value) => sum + value, 0)
  const extra = Math.max(0, 340 - total) / widths.length
  columnWidths.value = widths.map(value => value + extra)
  const width = Math.min(Math.max(total, 340) + 2, window.innerWidth - 24)
  const below = window.innerHeight - rect.bottom - 12
  position.value = { width: `${width}px`, left: `${Math.max(12, Math.min(rect.left, window.innerWidth - width - 12))}px`, ...(below >= 300 ? { top: `${rect.bottom + 5}px` } : { bottom: `${window.innerHeight - rect.top + 5}px` }), maxHeight: `${Math.max(120, (below >= 300 ? below : rect.top) - 12)}px` }
  open.value = true
}
function choose(node, level) {
  browsing.value = [...browsing.value.slice(0, level), node.name]
  emit('update:modelValue', node.value)
  if (!node.children.length) { close(); trigger.value?.focus() }
}
function all() { emit('update:modelValue', ''); close(); trigger.value?.focus() }
function outside(event) { if (!trigger.value?.contains(event.target) && !panel.value?.contains(event.target)) close() }
function keydown(event) { if (event.key === 'Escape' && open.value) { event.stopPropagation(); close(); trigger.value?.focus() } }
function scroll(event) { if (!panel.value?.contains(event.target)) close() }
function attach() { document.addEventListener('pointerdown', outside); document.addEventListener('keydown', keydown, true); document.addEventListener('scroll', scroll, true); window.addEventListener('resize', close) }
function detach() { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', keydown, true); document.removeEventListener('scroll', scroll, true); window.removeEventListener('resize', close) }
onMounted(() => { if (!workspace || workspace.active) attach() })
watch(() => workspace?.active, active => { detach(); close(); if (active) attach() })
onBeforeUnmount(detach)
</script>
<template>
  <button ref="trigger" type="button" class="category-select" aria-label="按产品分类筛选" aria-haspopup="dialog" :aria-expanded="open" :title="modelValue || '全部分类'" @click="toggle"><span>{{ label }}</span><ChevronDown :size="16" /></button>
  <Teleport to="body" :disabled="workspaceTeleportDisabled"><section v-if="open" ref="panel" class="category-picker" :style="position" role="dialog" aria-label="选择产品分类">
    <button type="button" class="all-categories" :class="{ selected: !modelValue }" @click="all">全部分类</button>
    <div class="cascade-columns"><div v-for="(column, level) in columns" :key="level" class="cascade-column" :style="{ width: `${columnWidths[level]}px` }"><button v-for="node in column" :key="node.value" type="button" class="cascade-option" :class="{ active: browsing[level] === node.name, selected: modelValue === node.value }" :aria-pressed="modelValue === node.value" @click="choose(node, level)"><span>{{ node.name }}</span><ChevronRight v-if="node.children.length" :size="15" /></button></div></div>
  </section></Teleport>
</template>
<style scoped>
.category-picker .cascade-column{box-sizing:border-box;min-width:0;flex:0 0 auto;border-right:1px solid #cfdfd7}.category-picker .cascade-column:last-child{border-right:0}.cascade-option span{white-space:nowrap}
.category-select{width:100%;min-width:0;height:38px;padding:0 11px;display:flex;align-items:center;justify-content:space-between;gap:8px;border:1px solid #d7e1dc;border-radius:8px;background:white;color:#29473e;font:inherit;font-size:var(--text-body);text-align:left;cursor:pointer}.category-select span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.category-select svg{flex:none}.category-select:hover{border-color:#8eb6a8}.category-picker{position:fixed;z-index:200;display:flex;flex-direction:column;border:1px solid #c8ddd5;border-radius:10px;overflow:hidden;background:#fbfdfc;box-shadow:0 12px 26px #173d3624;color:#29473e}.all-categories{border:0;border-bottom:1px solid #e1ebe6;background:white;color:#29473e;padding:9px 14px;text-align:left;font:inherit;font-size:var(--text-body);cursor:pointer}.all-categories.selected{background:#e1f0ea}.cascade-columns{display:flex;min-height:100px;height:230px;overflow:auto;background:white}.cascade-column{min-width:145px;flex:1;padding:6px;overflow-y:auto;border-right:1px solid #e1ebe6}.cascade-column:last-child{border-right:0}.cascade-option{width:100%;min-height:34px;padding:6px 8px;display:flex;align-items:center;justify-content:space-between;gap:8px;border:0;border-radius:6px;background:transparent;color:#29473e;font:inherit;font-size:var(--text-body);text-align:left;cursor:pointer}.cascade-option:hover,.cascade-option.active,.cascade-option.selected{background:#e1f0ea}.cascade-option svg{flex:none;color:#69827a}.cascade-columns p{padding:12px;color:#69827a}button:focus-visible{outline:2px solid #248166;outline-offset:-2px}
</style>
