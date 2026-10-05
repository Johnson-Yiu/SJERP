<script setup>
defineProps({ label: { type: String, required: true } })
defineEmits(['clear'])
</script>

<template>
  <div class="sku-context-banner" aria-label="当前 SKU 筛选">
    <span>当前 SKU 筛选：<strong>{{ label }}</strong></span>
    <button type="button" @click="$emit('clear')">清除 SKU 筛选</button>
  </div>
</template>

<style scoped>
.sku-context-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 14px;
  padding: 9px 12px;
  border: 1px solid #c8d8ed;
  border-radius: 9px;
  background: #f4f8fd;
  color: #42546b;
  font-size: 13px;
}

.sku-context-banner strong { color: #173f70; }
.sku-context-banner button {
  padding: 2px 0;
  border: 0;
  background: transparent;
  color: #245b91;
  font: inherit;
  cursor: pointer;
}
.sku-context-banner button:hover { text-decoration: underline; }
</style>
