<script setup>
import { formatMoney } from '../utils/money.js'
defineProps({ rows: { type: Array, required: true } })
const states = { pending: '待关联', linked: '已关联', review: '待核实' }
</script>

<template>
  <ul class="historical-product-details">
    <li v-for="(item, index) in rows" :key="index">
      <strong>{{ item.name || '历史商品' }}</strong>
      <span v-if="item.code || item.specification">{{ [item.code, item.specification].filter(Boolean).join(' · ') }}</span>
      <span v-if="item.description">{{ item.description }}</span>
      <span>{{ item.quantity }} {{ item.unit }} · {{ item.currency }} {{ formatMoney(item.amount) }}</span>
      <span v-if="item.status">{{ states[item.status] }}
        <RouterLink v-if="item.sku" :to="{ path: '/skus', query: { detail: item.sku.id } }">查看 SKU {{ item.sku.code }}</RouterLink>
      </span>
      <RouterLink v-if="item.application" :to="{ path: '/history-takeover', query: { application: item.application, group: item.group } }">查看原资料</RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.historical-product-details { list-style: none; padding: 0; margin: 0; min-width: 0; overflow-wrap: anywhere; }
.historical-product-details li { display: grid; gap: 3px; padding: 9px 0; border-bottom: 1px solid #e7eee8; }
</style>
