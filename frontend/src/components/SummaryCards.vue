<script setup>
import { ChartNoAxesCombined } from 'lucide-vue-next'

defineProps({ items: { type: Array, default: () => [] } })
</script>

<template>
  <div class="summary-cards-shell">
    <section class="summary-cards" aria-label="页面小计">
      <article v-for="(item, index) in items" :key="item.label" :class="`tone-${item.tone || ['mint', 'amber', 'green', 'blue'][index % 4]}`">
        <span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.hint }}</small>
        <i><component :is="item.icon || ChartNoAxesCombined" :size="19" /></i>
      </article>
    </section>
  </div>
</template>

<style scoped>
.summary-cards-shell{container:summary-cards / inline-size}.summary-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:0 0 16px}.summary-cards article{position:relative;min-width:0;min-height:104px;padding:16px 18px;border:1px solid #e3ebe7;border-radius:12px;background:#fff;box-shadow:0 4px 14px #143f330b}.summary-cards span,.summary-cards small{display:block;color:#80908a;font-size:var(--text-caption)}.summary-cards strong{display:block;margin:11px 44px 6px 0;color:#123f36;font-size:var(--text-metric);line-height:1.15;white-space:normal;overflow:visible;overflow-wrap:anywhere;word-break:break-word;font-variant-numeric:tabular-nums}.summary-cards small{font-size:var(--text-caption)}.summary-cards i{position:absolute;right:18px;top:27px;width:40px;height:40px;border-radius:50%;display:grid;place-items:center;font-style:normal}.tone-mint i{background:#ddf4f0;color:#008a80}.tone-amber i{background:#fff0de;color:#e28b31}.tone-green i{background:#e1f6e8;color:#2da45c}.tone-blue i{background:#e7f0ff;color:#4382df}@container summary-cards (max-width:1100px){.summary-cards{grid-template-columns:repeat(3,minmax(0,1fr))}}@container summary-cards (max-width:760px){.summary-cards{grid-template-columns:repeat(2,minmax(0,1fr))}}@container summary-cards (max-width:520px){.summary-cards{grid-template-columns:1fr}}
</style>
