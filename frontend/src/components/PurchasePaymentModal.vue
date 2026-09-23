<script setup>
import { ref } from 'vue'
import { X, CircleDollarSign } from 'lucide-vue-next'
import { api } from '../api'
const props = defineProps({ purchase: Object })
const emit = defineEmits(['close', 'saved'])
const saving = ref(false), error = ref('')
const form = ref({ transaction_date: new Date().toLocaleDateString('en-CA'), amount: '', payment_method: '', reference: '', notes: '' })
const money = value => Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
async function submit() {
  if (saving.value) return
  error.value = ''
  if (!Number.isFinite(Number(form.value.amount)) || Number(form.value.amount) <= 0 || Number(form.value.amount) > Number(props.purchase.unpaid_amount)) {
    error.value = '付款金额须大于零，且不能超过当前未付金额。'; return
  }
  saving.value = true
  try {
    await api.post(`/purchase-orders/${props.purchase.id}/pay/`, { ...form.value, currency: props.purchase.currency, exchange_rate: props.purchase.exchange_rate })
    emit('saved')
  } catch (e) {
    const data = e.response?.data
    error.value = data?.detail || (data ? Object.values(data).flat().join(' ') : e.message) || '付款登记失败，请重试。'
  } finally { saving.value = false }
}
</script>

<template>
  <div class="payment-mask" @mousedown.self="!saving && emit('close')" @keydown.esc="!saving && emit('close')">
    <section class="payment-modal" role="dialog" aria-modal="true" aria-labelledby="payment-title">
      <header><div><span class="payment-eyebrow">供应商付款</span><h3 id="payment-title"><CircleDollarSign :size="20" /> 登记付款</h3><p>{{ purchase.purchase_no }} · {{ purchase.supplier_name }}</p></div><button class="icon-btn" aria-label="关闭付款登记" :disabled="saving" @click="emit('close')"><X :size="18" /></button></header>
      <div class="payment-balance"><span>当前未付金额</span><strong>{{ purchase.currency }} {{ money(purchase.unpaid_amount) }}</strong><small>已付 {{ purchase.currency }} {{ money(purchase.paid_amount) }}</small></div>
      <form @submit.prevent="submit">
        <fieldset :disabled="saving">
          <div class="payment-grid"><label>本次付款金额（{{ purchase.currency }}）<input v-model="form.amount" type="number" min="0.01" :max="purchase.unpaid_amount" step="0.01" placeholder="请输入付款金额" required autofocus /></label><label>付款日期<input v-model="form.transaction_date" type="date" required /></label><label>付款方式<select v-model="form.payment_method"><option value="">请选择（可选）</option><option>银行转账</option><option>支付宝</option><option>微信支付</option><option>现金</option><option>其他</option></select></label><label>凭证 / 参考号<input v-model="form.reference" maxlength="100" placeholder="填写转账流水号（可选）" /></label></div>
          <label class="payment-notes">备注<textarea v-model="form.notes" rows="2" placeholder="补充本次付款说明（可选）" /></label>
        </fieldset>
        <p v-if="error" class="payment-error" role="alert">{{ error }}</p>
        <footer><small>保存后生成供应商支出流水，并更新未付余额。</small><div><button type="button" class="btn btn-secondary" :disabled="saving" @click="emit('close')">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '保存中…' : '确认登记付款' }}</button></div></footer>
      </form>
    </section>
  </div>
</template>

<style scoped>
.payment-mask{position:fixed;inset:0;z-index:110;display:grid;place-items:center;padding:20px;background:#102e2866;backdrop-filter:blur(4px)}
.payment-modal{width:min(620px,100%);max-height:92vh;overflow:auto;background:white;border:1px solid #dbe7e2;border-radius:18px;box-shadow:0 24px 80px #06291e38;color:#26473e}
header{display:flex;justify-content:space-between;align-items:flex-start;padding:24px 26px 18px}h3{display:flex;align-items:center;gap:9px;font-size:var(--text-section);margin:7px 0 8px}header p{font-size:var(--text-body);color:#788a83;margin:0}.payment-eyebrow{font-size:var(--text-caption);font-weight:700;letter-spacing:2px;color:#688c7d}
.payment-balance{display:grid;gap:7px;margin:0 26px;padding:18px 20px;background:#eff7f3;border:1px solid #d8e9df;border-radius:12px}.payment-balance span,.payment-balance small{font-size:var(--text-caption);color:#678075}.payment-balance strong{font-size:var(--text-metric);letter-spacing:-.5px;font-variant-numeric:tabular-nums}
form{padding:22px 26px 0}fieldset{padding:0;border:0;min-width:0}.payment-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}label{display:grid;gap:7px;font-size:var(--text-caption);font-weight:600;color:#536e62}input,select,textarea{box-sizing:border-box;width:100%;min-width:0;border:1px solid #d8e3dd;border-radius:8px;padding:10px 11px;font:inherit;font-size:var(--text-body);color:#29483d;background:#fff;outline:none}input:focus,select:focus,textarea:focus{border-color:#629783;box-shadow:0 0 0 3px #23735312}.payment-notes{margin-top:16px}.payment-error{padding:10px;border-radius:8px;background:#fff1f0;color:#ad4038;font-size:var(--text-body)}footer{margin:22px -26px 0;padding:17px 26px;border-top:1px solid #e5ece7;background:#fafcfb}footer small{display:block;color:#809187;font-size:var(--text-caption);margin-bottom:14px}footer>div{display:flex;justify-content:flex-end;gap:10px}@media(max-width:560px){.payment-grid{grid-template-columns:1fr}.payment-mask{padding:12px}header{padding:20px}.payment-balance{margin:0 20px}form{padding:20px 20px 0}footer{margin:20px -20px 0;padding:16px 20px}}
</style>
