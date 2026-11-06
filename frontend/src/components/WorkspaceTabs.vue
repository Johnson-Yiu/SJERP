<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
const props = defineProps({ manager: Object })
const menu = ref(''), bar = ref(null)
let observer
onMounted(() => { if (typeof ResizeObserver === 'undefined') return; observer = new ResizeObserver(() => document.documentElement.style.setProperty('--workspace-top', `${82 + bar.value.offsetHeight}px`)); observer.observe(bar.value) })
onBeforeUnmount(() => observer?.disconnect())
async function keydown(event, tab) {
  const tabs = props.manager.tabs, index = tabs.indexOf(tab)
  const target = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1
  if (target < 0) return
  event.preventDefault(); await props.manager.activate(tabs[target]); bar.value.querySelectorAll('[role=tab]')[target]?.focus()
}
function batch(id, mode) {
  const tabs = props.manager.tabs, index = tabs.findIndex(t => t.id === id)
  menu.value = ''
  void props.manager.close(tabs.filter((t, i) => mode === 'others' ? t.id !== id : i > index).map(t => t.id))
}
</script>
<template>
  <div ref="bar" class="workspace-bar">
    <div class="workspace-tabs" role="tablist" aria-label="业务工作区">
      <div v-for="tab in manager.tabs" :key="tab.id" class="workspace-tab" :class="{ active: tab.id === manager.activeId.value }">
        <button type="button" role="tab" :tabindex="tab.id === manager.activeId.value ? 0 : -1" :aria-controls="`workspace-panel-${tab.id}`" @keydown="keydown($event, tab)" :aria-selected="tab.id === manager.activeId.value" @click="manager.activate(tab)">{{ tab.title }}<span v-if="[...tab.guards].some(g => g.dirty?.value)" aria-label="未保存"> ●</span><span v-if="tab.stale" aria-label="数据有更新"> ↻</span></button>
        <button type="button" :aria-label="`关闭 ${tab.title}`" @click="manager.close([tab.id])">×</button>
        <button type="button" :aria-label="`${tab.title} 标签操作`" :aria-expanded="menu === tab.id" @click="menu = menu === tab.id ? '' : tab.id">⋮</button>
      </div>
    </div>
    <div v-for="tab in manager.tabs.filter(t => t.id === menu)" :key="tab.id" class="workspace-menu" aria-label="标签操作">
      <button @click="batch(tab.id, 'others')">关闭其他</button><button @click="batch(tab.id, 'right')">关闭右侧</button>
      <button @click="manager.move(tab.id, -1)">向左移动</button><button @click="manager.move(tab.id, 1)">向右移动</button>
      <button @click="menu = ''">收起</button>
    </div>
    <div v-if="manager.active.value?.stale" class="workspace-update" role="status"><span>数据已更新。请先保存或取消当前编辑，再重新载入。</span><button type="button" class="btn btn-secondary" @click="manager.reload(manager.active.value)">重新载入</button></div>
    <p v-if="manager.notice.value" role="alert" class="workspace-limit">{{ manager.notice.value }}</p>
  </div>
</template>
