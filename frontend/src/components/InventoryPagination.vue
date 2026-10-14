<script setup>
import { computed } from 'vue'
const props = defineProps({ total: Number, page: Number, size: { type: Number, default: 25 } })
const emit = defineEmits(['change'])
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))
</script>
<template>
  <nav v-if="total > size" class="inventory-pagination" aria-label="库存列表分页">
    <span>共 {{ total }} 条 · 第 {{ page }} / {{ pages }} 页</span>
    <button class="btn btn-secondary" :disabled="page <= 1" @click="emit('change', page - 1)">上一页</button>
    <button class="btn btn-secondary" :disabled="page >= pages" @click="emit('change', page + 1)">下一页</button>
  </nav>
</template>
<style scoped>
.inventory-pagination{display:flex;align-items:center;justify-content:flex-end;gap:12px;padding:16px;flex-wrap:wrap;border-top:1px solid #e0e8e4}.inventory-pagination span{margin-right:auto;color:#567168;font-size:var(--text-body)}
</style>
