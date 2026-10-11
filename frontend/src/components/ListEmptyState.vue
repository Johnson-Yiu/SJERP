<script setup>
defineProps({ entity: { type: String, default: '记录' }, filtered: { type: Boolean, default: false } })
defineEmits(['clear'])
</script>

<template>
  <div class="list-empty-state" role="status">
    <h3>{{ filtered ? '没有符合当前条件的记录' : `暂无${entity}` }}</h3>
    <p v-if="filtered">请调整搜索或筛选条件。</p>
    <slot v-else name="action" />
    <button v-if="filtered" type="button" class="list-empty-clear" @click="$emit('clear')">清除筛选</button>
  </div>
</template>

<style scoped>
.list-empty-state{display:grid;justify-items:center;gap:8px;min-height:130px;padding:26px 18px;border:1px dashed #d4e1da;border-radius:10px;background:#fbfdfc;color:#60766d;text-align:center}
.list-empty-state h3{margin:0;color:#29473d;font-size:var(--text-subsection,16px)}
.list-empty-state p{margin:0;font-size:var(--text-body,14px)}
.list-empty-clear{border:0;background:transparent;color:#28745d;font:inherit;font-weight:700;text-decoration:underline;cursor:pointer}
</style>
