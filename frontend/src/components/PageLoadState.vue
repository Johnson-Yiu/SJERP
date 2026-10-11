<script setup>
defineProps({
  loading: { type: Boolean, default: false },
  hasLoaded: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['retry'])
</script>

<template>
  <div v-if="loading && !hasLoaded" class="page-load-state page-load-state-loading" role="status">正在加载…</div>
  <div v-else-if="loading && hasLoaded" class="page-load-state page-load-state-refreshing" role="status">正在刷新…</div>
  <div v-else-if="error && !hasLoaded" class="page-load-state page-load-state-error" role="alert">
    <strong>数据加载失败</strong><p>{{ error }}</p><button type="button" @click="emit('retry')">重新加载</button>
  </div>
  <div v-else-if="error && hasLoaded" class="page-load-state page-load-state-warning" role="alert">
    <span>刷新失败，当前显示上一次成功加载的数据。{{ error }}</span><button type="button" @click="emit('retry')">重新加载</button>
  </div>
</template>

<style scoped>
.page-load-state{display:flex;align-items:center;justify-content:center;gap:10px;min-height:72px;padding:14px 18px;border:1px solid #dce8e2;border-radius:10px;background:#fff;color:#52685f;font-size:var(--text-body,14px)}
.page-load-state-error{align-items:flex-start;flex-direction:column;border-color:#efc6c2;background:#fff9f8;color:#842f2b}
.page-load-state-error p{margin:0;color:#684c49;overflow-wrap:anywhere}
.page-load-state-warning{justify-content:space-between;border-color:#e8d4a4;background:#fffaf0;color:#6b572f}
.page-load-state-refreshing{justify-content:flex-start;min-height:42px;padding:8px 14px;background:#f7faf8;color:#63776e}
.page-load-state button{flex:none;border:1px solid currentColor;border-radius:7px;padding:7px 11px;background:#fff;color:inherit;font:inherit;font-weight:700;cursor:pointer}
</style>
