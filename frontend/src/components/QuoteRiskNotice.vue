<script setup>
defineProps({
  risks: { type: Array, default: () => [] },
})
const emit = defineEmits(['cancel', 'continue'])
</script>

<template>
  <div class="modal-backdrop quote-risk-backdrop" @mousedown.self="emit('cancel')">
    <section class="modal quote-risk-modal" role="dialog" aria-modal="true" aria-labelledby="quote-risk-title">
      <div class="modal-head">
        <div>
          <h3 id="quote-risk-title">导出前风险提示</h3>
          <p>本次报价包含以下内部提示。风险不会阻止保存或导出，请确认后继续。</p>
        </div>
      </div>
      <div class="modal-body quote-risk-body">
        <article v-for="risk in risks" :key="risk.sku" class="quote-risk-row">
          <div>
            <strong>{{ risk.label || risk.sku_code }}</strong>
            <small>{{ risk.sku_code }}</small>
          </div>
          <ul>
            <li v-for="label in risk.risk_labels" :key="label">{{ label }}</li>
          </ul>
        </article>
      </div>
      <div class="modal-foot">
        <button type="button" class="btn btn-secondary" @click="emit('cancel')">暂不导出</button>
        <button type="button" class="btn btn-primary" @click="emit('continue')">了解风险，继续导出</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.quote-risk-backdrop{z-index:160}.quote-risk-modal{width:min(620px,calc(100vw - 28px));max-height:min(720px,calc(100vh - 44px))}.quote-risk-body{display:grid;gap:10px;max-height:calc(100vh - 230px);overflow:auto}.quote-risk-row{padding:11px 12px;border:1px solid #e1c98d;border-radius:9px;background:#fffaf0}.quote-risk-row strong,.quote-risk-row small{display:block}.quote-risk-row strong{color:#5d481f}.quote-risk-row small{margin-top:2px;color:#89754d;font-size:var(--text-caption)}.quote-risk-row ul{margin:8px 0 0;padding-left:18px;color:#735b2e;font-size:var(--text-body);line-height:1.6}
</style>
